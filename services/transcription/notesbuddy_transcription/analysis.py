"""Evidence-grounded professional meeting analysis."""

from __future__ import annotations

import json
import math
import os
import re
import threading
from typing import Any


ANALYSIS_SCHEMA_VERSION = 1
ANALYSIS_PROMPT_VERSION = 1
NOT_SPECIFIED = "Not specified"
PRIORITIES = {"High", "Medium", "Low"}
GROUNDING_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "his",
    "i",
    "in",
    "is",
    "it",
    "its",
    "meeting",
    "of",
    "on",
    "or",
    "our",
    "she",
    "that",
    "the",
    "their",
    "them",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "will",
    "with",
    "you",
}
HIGH_URGENCY = re.compile(
    r"\b(?:urgent|urgently|immediately|asap|critical|blocked|blocking|"
    r"must|by today|before today|eod|end of day)\b",
    re.IGNORECASE,
)
LOW_URGENCY = re.compile(
    r"\b(?:optional|when possible|no rush|low priority|later|future|"
    r"nice to have|consider exploring)\b",
    re.IGNORECASE,
)
CONFIRMED_DECISION = re.compile(
    r"\b(?:decided|agreed|approved|confirmed|selected|chose|chosen|settled|"
    r"consensus|going with|will use|will proceed|moving forward with|"
    r"move forward with|let's use|we'll use)\b",
    re.IGNORECASE,
)
UNRESOLVED_DECISION = re.compile(
    r"\b(?:propos(?:e|ed|al)|suggest(?:ed|ion)?|could|might|maybe|consider|"
    r"need to decide|not decided|no decision|decision pending|undecided|"
    r"should we|what if)\b",
    re.IGNORECASE,
)
CONFIRMED_ACTION = re.compile(
    r"\b(?:i|we|you|they|he|she|someone|somebody|the team|team|[A-Z][a-z]+)"
    r"\s+(?:will|must|need(?:s)? to|have to|has to|am going to|are going to|"
    r"is going to)\b|\b(?:i'll|we'll|you'll|they'll|action item|next step|"
    r"follow[- ]?up|please\s+(?:send|review|prepare|complete|submit|update|"
    r"create|schedule|confirm|share))\b",
    re.IGNORECASE,
)

SYSTEM_PROMPT = """You are an expert meeting analyst. Review the complete meeting transcription and produce a clear, accurate, and professional meeting analysis.

Never add assumptions, invented information, or details unsupported by the transcription. Remove repetition, filler words, greetings, and unrelated conversation. Preserve the speakers' meaning, correct only obvious transcription or grammatical errors, and use names, project names, product names, and dates consistently.

Requirements:
1. shortSummary: fewer than 300 words in clear paragraphs. Explain the purpose, main topics, overall outcome, and important next steps only when supported.
2. highlights: concise important discussion points, findings, concerns, updates, risks, opportunities, and recommendations. Combine repeated or related points.
3. decisions: confirmed decisions and agreements only. Include context and responsible person/team when stated. Never turn suggestions, proposals, questions, or unresolved discussion into decisions.
4. actionItems: clear, specific, separate tasks. Use "Not specified" when owner or due date is absent. Do not invent deadlines. Priority must be High, Medium, or Low based only on urgency expressed. Put dependencies, follow-ups, or relevant context in notes; otherwise use "Not specified".

Every summary and list item must cite one or more transcript segment IDs that directly support it. If no confirmed decisions exist, return an empty decisions array. If no action items exist, return an empty actionItems array.

Return valid JSON only. Do not use Markdown or commentary."""

OUTPUT_SHAPE = {
    "shortSummary": "Professional summary under 300 words.",
    "summaryEvidenceSegmentIds": ["S0001"],
    "highlights": [
        {"text": "Concise highlight.", "evidenceSegmentIds": ["S0001"]}
    ],
    "decisions": [
        {
            "decision": "Confirmed decision.",
            "context": "Reason or context, or Not specified.",
            "owner": "Responsible person/team, or Not specified.",
            "evidenceSegmentIds": ["S0001"],
        }
    ],
    "actionItems": [
        {
            "task": "Clear, specific task.",
            "owner": "Owner or Not specified.",
            "dueDate": "Due date or Not specified.",
            "priority": "High, Medium, or Low.",
            "notes": "Dependencies/context or Not specified.",
            "evidenceSegmentIds": ["S0001"],
        }
    ],
}


class MeetingAnalysisUnavailable(RuntimeError):
    """Raised when professional analysis is unavailable or invalid."""


def _clean_text(value: object, *, maximum: int = 4000) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\x00", " ")).strip()[
        :maximum
    ]


def _normalise(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean_text(value).lower()).strip()


def _limit_words(value: object, maximum_words: int) -> str:
    raw = str(value or "").replace("\x00", " ").replace("\r", "\n")
    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in re.split(r"\n+", raw)
        if paragraph.strip()
    ]
    output: list[str] = []
    remaining = maximum_words
    for paragraph in paragraphs:
        words = paragraph.split()
        if not words or remaining <= 0:
            continue
        output.append(" ".join(words[:remaining]))
        remaining -= min(len(words), remaining)
    return "\n\n".join(output)


def prepare_transcript_segments(raw_segments: object) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    if not isinstance(raw_segments, list):
        return prepared
    for index, raw in enumerate(raw_segments):
        if not isinstance(raw, dict):
            continue
        text = _clean_text(raw.get("text"), maximum=12_000)
        if not text:
            continue
        source_id = _clean_text(raw.get("id"), maximum=120) or f"segment-{index + 1}"
        if source_id in seen_source_ids:
            source_id = f"{source_id}-{index + 1}"
        seen_source_ids.add(source_id)
        prepared.append(
            {
                "id": f"S{len(prepared) + 1:04d}",
                "sourceId": source_id,
                "speaker": _clean_text(
                    raw.get("speaker") or raw.get("speakerLabel"), maximum=100
                )
                or "Unknown speaker",
                "timestamp": _clean_text(raw.get("timestamp"), maximum=20),
                "text": text,
            }
        )
    return prepared


def _evidence_ids(value: object, valid_ids: set[str]) -> list[str]:
    output: list[str] = []
    if not isinstance(value, list):
        return output
    for raw_id in value:
        evidence_id = _clean_text(raw_id, maximum=20).upper()
        if evidence_id in valid_ids and evidence_id not in output:
            output.append(evidence_id)
    return output[:12]


def _evidence_text(ids: list[str], by_id: dict[str, dict[str, Any]]) -> str:
    return " ".join(by_id[item]["text"] for item in ids if item in by_id)


def _root_token(token: str) -> str:
    for suffix in ("ingly", "edly", "ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _content_tokens(value: object) -> set[str]:
    return {
        _root_token(token)
        for token in _normalise(value).split()
        if len(token) >= 3 and token not in GROUNDING_STOP_WORDS
    }


def _is_grounded_text(value: object, evidence_text: str) -> bool:
    """Reject content whose meaningful words do not appear in cited evidence."""

    text = _clean_text(value)
    if not text or text.lower() == NOT_SPECIFIED.lower():
        return text.lower() == NOT_SPECIFIED.lower()
    output_tokens = _content_tokens(text)
    evidence_tokens = _content_tokens(evidence_text)
    if not output_tokens:
        return False
    overlap = output_tokens & evidence_tokens
    minimum_overlap = max(
        1,
        2 if len(output_tokens) > 5 else 1,
        math.ceil(len(output_tokens) * 0.2),
    )
    output_numbers = set(re.findall(r"\b\d+(?:[./:-]\d+)*\b", text))
    evidence_numbers = set(
        re.findall(r"\b\d+(?:[./:-]\d+)*\b", evidence_text)
    )
    return len(overlap) >= minimum_overlap and output_numbers <= evidence_numbers


def _validated_owner(
    value: object,
    evidence: list[str],
    by_id: dict[str, dict[str, Any]],
    *,
    allow_first_person_speaker: bool = False,
) -> str:
    owner = _clean_text(value, maximum=100) or NOT_SPECIFIED
    if owner.lower() == NOT_SPECIFIED.lower():
        return NOT_SPECIFIED
    normalised_owner = _normalise(owner)
    evidence_text = _evidence_text(evidence, by_id)
    if len(normalised_owner) < 2:
        return NOT_SPECIFIED
    aliases = [owner]
    evidence_speakers = {
        _normalise(by_id[item]["speaker"])
        for item in evidence
        if item in by_id
    }
    first_name = owner.split()[0] if owner.split() else ""
    if normalised_owner in evidence_speakers and len(first_name) >= 3:
        aliases.append(first_name)
    for alias in aliases:
        owner_pattern = re.escape(alias).replace(r"\ ", r"\s+")
        explicitly_assigned = re.search(
            rf"\b{owner_pattern}\b[^.!?]{{0,40}}\b(?:will|must|needs?\s+to|"
            r"has\s+to|is\s+responsible|owns?|is\s+assigned)\b|"
            rf"\b(?:assigned|owned)\s+(?:to|by)\s+{owner_pattern}\b",
            evidence_text,
            re.IGNORECASE,
        )
        if explicitly_assigned:
            return owner
    if allow_first_person_speaker and len(evidence) == 1:
        segment = by_id.get(evidence[0])
        if (
            segment
            and _normalise(segment["speaker"]) == normalised_owner
            and re.search(
                r"\b(?:i\s+(?:will|must|need\s+to|have\s+to|am\s+going\s+to)|"
                r"i['’]ll)\b",
                segment["text"],
                re.IGNORECASE,
            )
        ):
            return owner
    return NOT_SPECIFIED


def _validated_due_date(
    value: object,
    evidence: list[str],
    by_id: dict[str, dict[str, Any]],
) -> str:
    due_date = _clean_text(value, maximum=100) or NOT_SPECIFIED
    if due_date.lower() == NOT_SPECIFIED.lower():
        return NOT_SPECIFIED
    due_words = [
        word
        for word in _normalise(due_date).split()
        if word not in {"by", "before", "on", "the", "at"}
    ]
    transcript_text = _normalise(_evidence_text(evidence, by_id))
    if due_words and all(word in transcript_text.split() for word in due_words):
        return due_date
    return NOT_SPECIFIED


def _validated_priority(
    value: object,
    evidence: list[str],
    by_id: dict[str, dict[str, Any]],
) -> str:
    priority = _clean_text(value, maximum=20).title()
    if priority not in PRIORITIES:
        priority = "Medium"
    transcript_text = _evidence_text(evidence, by_id)
    if priority == "High" and not HIGH_URGENCY.search(transcript_text):
        return "Medium"
    if priority == "Low" and not LOW_URGENCY.search(transcript_text):
        return "Medium"
    return priority


def normalise_analysis(
    raw_analysis: object,
    prepared_segments: list[dict[str, Any]],
) -> dict[str, Any]:
    if not isinstance(raw_analysis, dict):
        raise MeetingAnalysisUnavailable("The analysis model returned invalid JSON.")
    by_id = {segment["id"]: segment for segment in prepared_segments}
    valid_ids = set(by_id)
    summary = _limit_words(raw_analysis.get("shortSummary"), 299)
    summary_evidence = _evidence_ids(
        raw_analysis.get("summaryEvidenceSegmentIds"), valid_ids
    )
    if not summary or not summary_evidence:
        raise MeetingAnalysisUnavailable(
            "The analysis model did not ground its summary in the transcript."
        )
    if not _is_grounded_text(
        summary,
        _evidence_text(summary_evidence, by_id),
    ):
        raise MeetingAnalysisUnavailable(
            "The analysis model returned a summary unsupported by its cited transcript evidence."
        )

    highlights: list[dict[str, Any]] = []
    seen_highlights: set[str] = set()
    for item in raw_analysis.get("highlights") or []:
        if not isinstance(item, dict):
            continue
        text = _clean_text(item.get("text"), maximum=600)
        evidence = _evidence_ids(item.get("evidenceSegmentIds"), valid_ids)
        key = _normalise(text)
        if (
            not text
            or not evidence
            or not key
            or key in seen_highlights
            or not _is_grounded_text(text, _evidence_text(evidence, by_id))
        ):
            continue
        seen_highlights.add(key)
        highlights.append({"text": text, "evidenceSegmentIds": evidence})
        if len(highlights) >= 12:
            break

    decisions: list[dict[str, Any]] = []
    seen_decisions: set[str] = set()
    for item in raw_analysis.get("decisions") or []:
        if not isinstance(item, dict):
            continue
        decision = _clean_text(item.get("decision"), maximum=600)
        evidence = _evidence_ids(item.get("evidenceSegmentIds"), valid_ids)
        key = _normalise(decision)
        evidence_text = _evidence_text(evidence, by_id)
        confirmed = CONFIRMED_DECISION.search(evidence_text)
        unresolved = UNRESOLVED_DECISION.search(evidence_text)
        if (
            not decision
            or not evidence
            or not key
            or key in seen_decisions
            or not confirmed
            or (unresolved and unresolved.start() > confirmed.start())
            or not _is_grounded_text(decision, evidence_text)
        ):
            continue
        seen_decisions.add(key)
        decisions.append(
            {
                "decision": decision,
                "context": (
                    _clean_text(item.get("context"), maximum=700)
                    if _is_grounded_text(item.get("context"), evidence_text)
                    else NOT_SPECIFIED
                )
                or NOT_SPECIFIED,
                "owner": _validated_owner(item.get("owner"), evidence, by_id),
                "evidenceSegmentIds": evidence,
            }
        )
        if len(decisions) >= 12:
            break

    action_items: list[dict[str, Any]] = []
    seen_actions: set[str] = set()
    for item in raw_analysis.get("actionItems") or []:
        if not isinstance(item, dict):
            continue
        task = _clean_text(item.get("task"), maximum=600)
        evidence = _evidence_ids(item.get("evidenceSegmentIds"), valid_ids)
        key = _normalise(task)
        evidence_text = _evidence_text(evidence, by_id)
        if (
            not task
            or not evidence
            or not key
            or key in seen_actions
            or not CONFIRMED_ACTION.search(evidence_text)
            or not _is_grounded_text(task, evidence_text)
        ):
            continue
        seen_actions.add(key)
        action_items.append(
            {
                "task": task,
                "owner": _validated_owner(
                    item.get("owner"),
                    evidence,
                    by_id,
                    allow_first_person_speaker=True,
                ),
                "dueDate": _validated_due_date(
                    item.get("dueDate"), evidence, by_id
                ),
                "priority": _validated_priority(
                    item.get("priority"), evidence, by_id
                ),
                "notes": (
                    _clean_text(item.get("notes"), maximum=800)
                    if _is_grounded_text(item.get("notes"), evidence_text)
                    else NOT_SPECIFIED
                )
                or NOT_SPECIFIED,
                "evidenceSegmentIds": evidence,
            }
        )
        if len(action_items) >= 30:
            break

    return {
        "shortSummary": summary,
        "summaryEvidenceSegmentIds": summary_evidence,
        "highlights": highlights,
        "decisions": decisions,
        "actionItems": action_items,
    }


def _public_analysis(
    analysis: dict[str, Any],
    prepared_segments: list[dict[str, Any]],
    *,
    model_name: str,
) -> dict[str, Any]:
    source_ids = {segment["id"]: segment["sourceId"] for segment in prepared_segments}

    def mapped(ids: list[str]) -> list[str]:
        return [source_ids[item] for item in ids if item in source_ids]

    return {
        "schemaVersion": ANALYSIS_SCHEMA_VERSION,
        "promptVersion": ANALYSIS_PROMPT_VERSION,
        "model": model_name,
        "shortSummary": analysis["shortSummary"],
        "summarySourceSegmentIds": mapped(
            analysis["summaryEvidenceSegmentIds"]
        ),
        "highlights": [
            {
                "text": item["text"],
                "sourceSegmentIds": mapped(item["evidenceSegmentIds"]),
            }
            for item in analysis["highlights"]
        ],
        "decisions": [
            {
                "decision": item["decision"],
                "context": item["context"],
                "owner": item["owner"],
                "sourceSegmentIds": mapped(item["evidenceSegmentIds"]),
            }
            for item in analysis["decisions"]
        ],
        "actionItems": [
            {
                "task": item["task"],
                "owner": item["owner"],
                "dueDate": item["dueDate"],
                "priority": item["priority"],
                "notes": item["notes"],
                "sourceSegmentIds": mapped(item["evidenceSegmentIds"]),
            }
            for item in analysis["actionItems"]
        ],
    }


def _extract_json(value: str) -> dict[str, Any]:
    text = value.strip().removeprefix("```json").removeprefix("```")
    if text.endswith("```"):
        text = text[:-3].rstrip()
    start = text.find("{")
    if start < 0:
        raise MeetingAnalysisUnavailable("The analysis model returned no JSON.")
    try:
        payload, _end = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as error:
        raise MeetingAnalysisUnavailable(
            "The analysis model returned malformed JSON."
        ) from error
    if not isinstance(payload, dict):
        raise MeetingAnalysisUnavailable("The analysis model returned invalid JSON.")
    return payload


def _transcript_chunks(
    segments: list[dict[str, Any]], maximum_characters: int
) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_size = 0
    for segment in segments:
        segment_size = len(segment["text"]) + len(segment["speaker"]) + 40
        if current and current_size + segment_size > maximum_characters:
            chunks.append(current)
            current = []
            current_size = 0
        current.append(segment)
        current_size += segment_size
    if current:
        chunks.append(current)
    return chunks


class MeetingAnalyzer:
    """Lazy local/hosted instruction-model adapter."""

    name = "professional meeting analyst"

    def __init__(
        self,
        *,
        model_name: str,
        revision: str | None = None,
        device: str = "cuda",
        maximum_chunk_characters: int = 42_000,
    ) -> None:
        self.model_name = model_name
        self.revision = revision or None
        self.device = device
        self.maximum_chunk_characters = max(8_000, maximum_chunk_characters)
        self._tokenizer = None
        self._model = None
        self._load_lock = threading.Lock()
        self._generation_lock = threading.Lock()

    def configuration_status(self) -> dict[str, object]:
        return {
            "ready": bool(self.model_name),
            "model": self.model_name,
            "status": "professional analysis configured",
        }

    def _load(self):
        if self._tokenizer is not None and self._model is not None:
            return self._tokenizer, self._model
        with self._load_lock:
            if self._tokenizer is None or self._model is None:
                try:
                    import torch
                    from transformers import AutoModelForCausalLM, AutoTokenizer
                except ImportError as error:
                    raise MeetingAnalysisUnavailable(
                        "The professional analysis model is not installed."
                    ) from error
                dtype = torch.float16 if self.device.startswith("cuda") else torch.float32
                self._tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name,
                    revision=self.revision,
                )
                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    revision=self.revision,
                    torch_dtype=dtype,
                    low_cpu_mem_usage=True,
                ).to(self.device)
                self._model.eval()
        return self._tokenizer, self._model

    @staticmethod
    def _transcript_text(segments: list[dict[str, Any]]) -> str:
        return "\n".join(
            f"[{item['id']} | {item['timestamp'] or 'time unavailable'} | "
            f"{item['speaker']}] {item['text']}"
            for item in segments
        )

    def _generate(self, user_prompt: str) -> dict[str, Any]:
        tokenizer, model = self._load()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        rendered = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = tokenizer(
            rendered,
            return_tensors="pt",
            truncation=True,
            max_length=15_500,
        ).to(self.device)
        try:
            import torch

            with self._generation_lock, torch.inference_mode():
                output = model.generate(
                    **inputs,
                    max_new_tokens=1_800,
                    do_sample=False,
                    repetition_penalty=1.04,
                    pad_token_id=tokenizer.eos_token_id,
                )
        except RuntimeError as error:
            raise MeetingAnalysisUnavailable(
                "The professional analysis model could not process this transcript."
            ) from error
        generated = output[0][inputs["input_ids"].shape[-1] :]
        return _extract_json(tokenizer.decode(generated, skip_special_tokens=True))

    def analyze(
        self,
        *,
        segments: object,
        meeting_title: object = "",
    ) -> dict[str, Any]:
        prepared = prepare_transcript_segments(segments)
        if not prepared:
            raise MeetingAnalysisUnavailable(
                "A completed transcript is required for meeting analysis."
            )
        chunks = _transcript_chunks(prepared, self.maximum_chunk_characters)
        partials: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks):
            prompt = (
                f"Meeting title: {_clean_text(meeting_title, maximum=200) or 'Not specified'}\n"
                f"Transcript part {index + 1} of {len(chunks)} follows. Analyze only "
                "what is supported by these segments.\n\n"
                f"{self._transcript_text(chunk)}\n\n"
                "Return exactly this JSON shape:\n"
                f"{json.dumps(OUTPUT_SHAPE, ensure_ascii=False)}"
            )
            partials.append(normalise_analysis(self._generate(prompt), prepared))

        if len(partials) == 1:
            final = partials[0]
        else:
            merge_prompt = (
                "The following evidence-grounded analyses cover consecutive parts of "
                "one meeting. Merge them into one professional analysis. Combine "
                "repetition, preserve all confirmed decisions and distinct tasks, and "
                "retain the cited segment IDs. Do not add any fact absent from these "
                "partial analyses.\n\n"
                f"{json.dumps(partials, ensure_ascii=False)}\n\n"
                "Return exactly this JSON shape:\n"
                f"{json.dumps(OUTPUT_SHAPE, ensure_ascii=False)}"
            )
            final = normalise_analysis(self._generate(merge_prompt), prepared)
        return _public_analysis(final, prepared, model_name=self.model_name)


def analyzer_from_environment() -> MeetingAnalyzer | None:
    model_name = os.getenv("NOTESBUDDY_ANALYSIS_MODEL", "").strip()
    if not model_name:
        return None
    return MeetingAnalyzer(
        model_name=model_name,
        revision=os.getenv("NOTESBUDDY_ANALYSIS_REVISION", "").strip() or None,
        device=os.getenv("NOTESBUDDY_ANALYSIS_DEVICE", "cuda").strip(),
        maximum_chunk_characters=int(
            os.getenv("NOTESBUDDY_ANALYSIS_CHUNK_CHARACTERS", "42000")
        ),
    )
