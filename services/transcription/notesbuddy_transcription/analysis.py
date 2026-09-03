"""Evidence-grounded professional meeting analysis."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import tempfile
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .diagnostics import diagnostic_log_path as _diagnostic_log_path
from .diagnostics import log_diagnostic as _log_diagnostic


def _field_counts(source: object) -> str:
    """Count highlights/decisions/actionItems for diagnostic logging.

    Used both on a raw (pre-validation) model response and on a validated
    result, so a live log can distinguish "the model produced nothing" from
    "items existed but were filtered out during validation or merge".
    """

    if not isinstance(source, dict):
        return "highlights=? decisions=? actionItems=?"
    return (
        f"highlights={len(source.get('highlights') or [])} "
        f"decisions={len(source.get('decisions') or [])} "
        f"actionItems={len(source.get('actionItems') or [])}"
    )


ANALYSIS_SCHEMA_VERSION = 1
ANALYSIS_PROMPT_VERSION = 3
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
SPECIFIC_TIME_TERM = re.compile(
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"january|february|march|april|may|june|july|august|september|"
    r"october|november|december|today|tomorrow|yesterday|tonight|"
    r"noon|midnight|weekend|eod)\b",
    re.IGNORECASE,
)
CONFIRMED_DECISION = re.compile(
    r"\b(?:decided|agree|agreed|agreement|approved|confirmed|selected|chose|chosen|settled|"
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

SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
GREETING_OR_FILLER = re.compile(
    r"^(?:hello|hi|hey|good (?:morning|afternoon|evening)|welcome|thanks?|"
    r"thank you|okay|ok|all right|alright)\b",
    re.IGNORECASE,
)
AGREEMENT = re.compile(
    r"\b(?:i|we|the team)\s+agree\b|\b(?:sounds good|that works|approved|"
    r"confirmed|let['’]s do that|go with that)\b",
    re.IGNORECASE,
)
PROPOSAL = re.compile(
    r"\b(?:recommend|propose|suggest|proposal|should|could|might|consider)\b",
    re.IGNORECASE,
)
ACTION_LEAD = re.compile(
    r"^(?P<owner>I|We|You|They|He|She|The team|Team|"
    r"(?!I\b|We\b|You\b|They\b|He\b|She\b|The\b|Team\b)"
    r"[A-Z][A-Za-z'’\-]*(?:\s+[A-Z][A-Za-z'’\-]*){0,2})\s+"
    r"(?P<commitment>will|must|needs? to|has to|have to|am going to|"
    r"is going to|are going to)\s+(?P<task>.+)$",
    re.IGNORECASE,
)
ACTION_CONTRACTION = re.compile(
    r"^(?P<owner>I|We|You|They|He|She)['’]ll\s+(?P<task>.+)$",
    re.IGNORECASE,
)
DUE_DATE = re.compile(
    r"\b(?P<prefix>by|before|on)\s+(?P<date>(?:next\s+)?(?:monday|tuesday|"
    r"wednesday|thursday|friday|saturday|sunday|today|tomorrow|tonight|"
    r"weekend|eod|end of day|\d{1,4}(?:[./-]\d{1,2}){1,2}))\b",
    re.IGNORECASE,
)
DEPENDENCY = re.compile(
    r"\b(?P<clause>(?:after|once|when|because|depending on|depends on|"
    r"blocked by)\s+.+)$",
    re.IGNORECASE,
)
DECISION_LEAD = re.compile(
    r"^(?:(?:we|i|they|the team)\s+)?(?:have\s+)?"
    r"(?:decided|agreed|approved|confirmed|selected|chose|settled)\s+"
    r"(?:to|that|on)?\s*(?P<decision>.+)$",
    re.IGNORECASE,
)

SYSTEM_PROMPT = """You are an expert meeting analyst. Review the complete meeting transcription and produce a clear, accurate, and professional meeting analysis.

Never add assumptions, invented information, or details unsupported by the transcription. Remove repetition, filler words, greetings, and unrelated conversation. Preserve the speakers' meaning, correct only obvious transcription or grammatical errors, and use names, project names, product names, and dates consistently.

Requirements:
1. shortSummary: fewer than 300 words in clear paragraphs. Explain the purpose, main topics, overall outcome, and important next steps only when supported.
2. highlights: concise important discussion points, findings, concerns, updates, risks, opportunities, and recommendations. Combine repeated or related points.
3. decisions: confirmed decisions and agreements only. Include context and responsible person/team when stated. Never turn suggestions, proposals, questions, or unresolved discussion into decisions.
4. actionItems: clear, specific, separate tasks. Use "Not specified" when owner or due date is absent. Do not invent a deadline that is not in the cited evidence. The task is the stated commitment itself, not a prerequisite for it -- put prerequisites and dependencies in notes instead. Priority is High, Medium, or Low based only on urgency actually expressed; otherwise Medium.

Look specifically for decisions and action items even when they are mentioned briefly in passing, not only when a speaker announces them formally -- a short sentence agreeing to something, or one person saying they will handle something, still counts. A meeting almost always contains at least one of each if people discussed next steps at all.

Example of an exchange and its correct extraction:
[S0012 | 00:14 | Jordan Lee] We agreed to move the launch date to March 10th since QA needs more time.
[S0013 | 00:19 | Priya Shah] Okay, I will send the updated budget spreadsheet to the team by Friday.
->
"decisions": [{"decision": "Move the launch date to March 10th.", "context": "QA needs more time.", "owner": "Not specified", "evidenceSegmentIds": ["S0012"]}]
"actionItems": [{"task": "Send the updated budget spreadsheet to the team.", "owner": "Priya Shah", "dueDate": "Friday", "priority": "Medium", "notes": "Not specified", "evidenceSegmentIds": ["S0013"]}]

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

OUTPUT_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["shortSummary", "summaryEvidenceSegmentIds", "highlights", "decisions", "actionItems"],
    "properties": {
        "shortSummary": {"type": "string"},
        "summaryEvidenceSegmentIds": {"type": "array", "items": {"type": "string"}},
        "highlights": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["text", "evidenceSegmentIds"],
                "properties": {
                    "text": {"type": "string"},
                    "evidenceSegmentIds": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "decisions": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["decision", "context", "owner", "evidenceSegmentIds"],
                "properties": {
                    "decision": {"type": "string"}, "context": {"type": "string"},
                    "owner": {"type": "string"},
                    "evidenceSegmentIds": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "actionItems": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["task", "owner", "dueDate", "priority", "notes", "evidenceSegmentIds"],
                "properties": {
                    "task": {"type": "string"}, "owner": {"type": "string"},
                    "dueDate": {"type": "string"},
                    "priority": {"type": "string", "enum": ["High", "Medium", "Low"]},
                    "notes": {"type": "string"},
                    "evidenceSegmentIds": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
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
        speaker = _clean_text(
            raw.get("speaker") or raw.get("speakerLabel"), maximum=100
        )
        if not speaker:
            speaker_id = _normalise(raw.get("speakerId"))
            if speaker_id == "local user":
                speaker = "You"
            else:
                remote_match = re.fullmatch(r"remote (\d+)", speaker_id)
                if remote_match:
                    speaker = f"Speaker {remote_match.group(1)}"
        prepared.append(
            {
                "id": f"S{len(prepared) + 1:04d}",
                "sourceId": source_id,
                "speaker": speaker or "Unknown speaker",
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
    output_time_terms = {
        value.lower() for value in SPECIFIC_TIME_TERM.findall(text)
    }
    evidence_time_terms = {
        value.lower() for value in SPECIFIC_TIME_TERM.findall(evidence_text)
    }
    return (
        len(overlap) >= minimum_overlap
        and output_numbers <= evidence_numbers
        and output_time_terms <= evidence_time_terms
    )


def _expanded_summary_evidence(
    summary: str,
    evidence: list[str],
    by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """Add the strongest transcript matches when a model under-cites a summary."""

    output_tokens = _content_tokens(summary)
    output_numbers = set(re.findall(r"\b\d+(?:[./:-]\d+)*\b", summary))
    candidates: list[tuple[int, int, str]] = []
    for segment_id, segment in by_id.items():
        if segment_id in evidence:
            continue
        segment_text = segment["text"]
        overlap = len(output_tokens & _content_tokens(segment_text))
        matched_numbers = len(
            output_numbers
            & set(re.findall(r"\b\d+(?:[./:-]\d+)*\b", segment_text))
        )
        if overlap or matched_numbers:
            candidates.append((matched_numbers, overlap, segment_id))
    candidates.sort(reverse=True)

    expanded = list(evidence)
    for _matched_numbers, _overlap, segment_id in candidates:
        expanded.append(segment_id)
        if len(expanded) >= 12 or _is_grounded_text(
            summary,
            _evidence_text(expanded, by_id),
        ):
            break
    return expanded


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
    *,
    trusted_summary: tuple[str, list[str]] | None = None,
) -> dict[str, Any]:
    if not isinstance(raw_analysis, dict):
        raise MeetingAnalysisUnavailable("The analysis model returned invalid JSON.")
    by_id = {segment["id"]: segment for segment in prepared_segments}
    valid_ids = set(by_id)
    if trusted_summary is not None:
        # Used only when merging multiple already-validated per-chunk
        # results (see _merge_partials): each piece of this text already
        # passed this same grounding check on its own, against its own
        # evidence, inside _generate_and_normalise. Concatenating several
        # independently-verified truthful sentences cannot introduce new
        # hallucinated content, so re-running the check against the
        # combined text is redundant -- and was observed to fail on real
        # multi-chunk meetings anyway, since concatenation dilutes the
        # overlap ratio and a single number or time phrase original to one
        # chunk's own evidence can trip the whole-text subset check, even
        # though every individual chunk was sound.
        summary, summary_evidence = trusted_summary
        summary = _limit_words(summary, 299)
        summary_evidence = [
            segment_id for segment_id in summary_evidence if segment_id in valid_ids
        ]
        if not summary or not summary_evidence:
            raise MeetingAnalysisUnavailable(
                "The analysis model did not ground its summary in the transcript."
            )
    else:
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
            summary_evidence = _expanded_summary_evidence(
                summary,
                summary_evidence,
                by_id,
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


def _repair_summary_from_grounded_items(
    raw_analysis: dict[str, Any],
    prepared_segments: list[dict[str, Any]],
    *fallback_analyses: dict[str, Any],
) -> dict[str, Any]:
    """Replace an unverifiable summary with already-grounded model findings.

    Scans ``raw_analysis`` first, then any ``fallback_analyses`` (e.g. a
    reinforcement retry's own generation). The retry is a second, independent
    generation with different prompt context, so its highlights/decisions/
    actions can be differently worded even under temp=0 determinism -- using
    only ``raw_analysis`` would make this fallback return byte-identical text
    on every retry of the same meeting.
    """

    by_id = {segment["id"]: segment for segment in prepared_segments}
    valid_ids = set(by_id)
    evidence: list[str] = []
    sentences: list[str] = []
    for analysis in (raw_analysis, *fallback_analyses):
        candidate_fields = (
            (analysis.get("highlights") or [], "text"),
            (analysis.get("decisions") or [], "decision"),
            (analysis.get("actionItems") or [], "task"),
        )
        for items, field in candidate_fields:
            for item in items:
                if not isinstance(item, dict):
                    continue
                text = _clean_text(item.get(field), maximum=600)
                item_evidence = _evidence_ids(
                    item.get("evidenceSegmentIds"),
                    valid_ids,
                )
                if not text or not item_evidence or not _is_grounded_text(
                    text,
                    _evidence_text(item_evidence, by_id),
                ):
                    continue
                new_evidence = [
                    segment_id
                    for segment_id in item_evidence
                    if segment_id not in evidence
                ]
                if len(evidence) + len(new_evidence) > 12:
                    continue
                candidate_tokens = _content_tokens(text)
                repeated = any(
                    len(candidate_tokens & _content_tokens(existing))
                    >= max(
                        2,
                        math.ceil(
                            min(
                                len(candidate_tokens),
                                len(_content_tokens(existing)),
                            )
                            * 0.55
                        ),
                    )
                    for existing in sentences
                    if candidate_tokens and _content_tokens(existing)
                )
                if repeated:
                    continue
                sentences.append(text.rstrip(". ") + ".")
                evidence.extend(new_evidence)
                if len(sentences) >= 8:
                    break
            if len(sentences) >= 8:
                break
        if len(sentences) >= 8:
            break

    if not sentences:
        cited = _evidence_ids(
            raw_analysis.get("summaryEvidenceSegmentIds"),
            valid_ids,
        )
        evidence = cited or [segment["id"] for segment in prepared_segments[:3]]
        sentences = [by_id[segment_id]["text"] for segment_id in evidence]

    repaired = dict(raw_analysis)
    repaired["shortSummary"] = _limit_words(" ".join(sentences), 299)
    repaired["summaryEvidenceSegmentIds"] = evidence
    return repaired


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


def _transcript_line(segment: dict[str, Any]) -> str:
    return (
        f"[{segment['id']} | {segment['timestamp'] or 'time unavailable'} | "
        f"{segment['speaker']}] {segment['text']}"
    )


def _token_count(tokenizer: Any, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def _split_segment_for_token_budget(
    segment: dict[str, Any],
    tokenizer: Any,
    maximum_tokens: int,
) -> list[dict[str, Any]]:
    if _token_count(tokenizer, _transcript_line(segment)) <= maximum_tokens:
        return [segment]

    empty_segment = {**segment, "text": ""}
    metadata_tokens = _token_count(tokenizer, _transcript_line(empty_segment))
    text_budget = maximum_tokens - metadata_tokens - 8
    if text_budget < 16:
        raise MeetingAnalysisUnavailable(
            "The analysis transcript token budget is configured too low."
        )

    text_tokens = tokenizer.encode(segment["text"], add_special_tokens=False)
    parts: list[dict[str, Any]] = []
    for start in range(0, len(text_tokens), text_budget):
        text = tokenizer.decode(
            text_tokens[start : start + text_budget],
            skip_special_tokens=True,
        ).strip()
        if text:
            parts.append({**segment, "text": text})
    return parts


def _transcript_chunks(
    segments: list[dict[str, Any]],
    tokenizer: Any,
    maximum_tokens: int,
) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for segment in segments:
        for part in _split_segment_for_token_budget(
            segment,
            tokenizer,
            maximum_tokens,
        ):
            candidate = current + [part]
            candidate_text = "\n".join(_transcript_line(item) for item in candidate)
            if current and _token_count(tokenizer, candidate_text) > maximum_tokens:
                chunks.append(current)
                current = [part]
            else:
                current = candidate
    if current:
        chunks.append(current)
    return chunks


def _sentence_records(
    prepared: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for segment_index, segment in enumerate(prepared):
        for raw_sentence in SENTENCE_BOUNDARY.split(segment["text"]):
            sentence = _clean_text(raw_sentence, maximum=1_200)
            if not sentence:
                continue
            records.append(
                {
                    "id": segment["id"],
                    "speaker": segment["speaker"],
                    "text": sentence,
                    "segmentIndex": segment_index,
                }
            )
    return records


def _without_terminal_punctuation(value: str) -> str:
    return value.strip().rstrip(".?! ")


def _sentence_case(value: str) -> str:
    cleaned = _without_terminal_punctuation(_clean_text(value, maximum=1_000))
    if not cleaned:
        return ""
    return cleaned[0].upper() + cleaned[1:] + "."


def _owner_from_commitment(owner: str, speaker: str) -> str:
    normalized = _normalise(owner)
    if normalized == "i":
        return speaker if _normalise(speaker) not in {"", "unknown speaker"} else NOT_SPECIFIED
    if normalized in {"we", "you", "they", "he", "she"}:
        return NOT_SPECIFIED
    if normalized in {"the team", "team"}:
        return "The team"
    return _clean_text(owner, maximum=100) or NOT_SPECIFIED


def _action_from_record(record: dict[str, Any]) -> dict[str, Any] | None:
    text = record["text"]
    match = ACTION_LEAD.match(text) or ACTION_CONTRACTION.match(text)
    if match:
        task_text = match.group("task")
        owner = _owner_from_commitment(match.group("owner"), record["speaker"])
    else:
        please = re.match(
            r"^(?:action item|next step|follow[- ]?up)\s*[:\-]?\s*(?P<task>.+)$|"
            r"^please\s+(?P<task2>.+)$",
            text,
            re.IGNORECASE,
        )
        if not please:
            return None
        task_text = please.group("task") or please.group("task2")
        owner = NOT_SPECIFIED

    dependency_match = DEPENDENCY.search(task_text)
    notes = (
        _sentence_case(dependency_match.group("clause"))
        if dependency_match
        else NOT_SPECIFIED
    )
    task_without_dependency = (
        task_text[: dependency_match.start()].strip(" ,;-")
        if dependency_match
        else task_text
    )
    due_match = DUE_DATE.search(task_without_dependency)
    due_date = NOT_SPECIFIED
    if due_match:
        prefix = due_match.group("prefix").lower()
        raw_date = _clean_text(due_match.group("date"), maximum=80)
        due_date = (
            f"Before {raw_date}"
            if prefix == "before"
            else raw_date[0].upper() + raw_date[1:]
        )
        task_without_dependency = (
            task_without_dependency[: due_match.start()].strip(" ,;-")
            + task_without_dependency[due_match.end() :]
        ).strip(" ,;-")

    task = _sentence_case(task_without_dependency)
    if not task:
        return None
    priority = (
        "High"
        if HIGH_URGENCY.search(text)
        else "Low"
        if LOW_URGENCY.search(text)
        else "Medium"
    )
    return {
        "task": task,
        "owner": owner,
        "dueDate": due_date,
        "priority": priority,
        "notes": notes,
        "evidenceSegmentIds": [record["id"]],
    }


def _decision_text(value: str) -> str:
    explicit = DECISION_LEAD.match(value)
    if explicit:
        candidate = explicit.group("decision")
    else:
        candidate = re.sub(
            r"^(?:i|we|the team)\s+(?:recommend|propose|suggest)\s+(?:that\s+)?",
            "",
            value,
            flags=re.IGNORECASE,
        )
    candidate = re.sub(r"^we\s+(?:will|should)\s+", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"^assigning\b", "Assign", candidate, flags=re.IGNORECASE)
    return _sentence_case(candidate)


def _decision_items(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, record in enumerate(records):
        text = record["text"]
        evidence = [record["id"]]
        candidate = ""

        explicit = DECISION_LEAD.match(text)
        if explicit:
            remainder = _normalise(explicit.group("decision"))
            if remainder and not re.match(r"^(?:this|that|these|those|it)\b", remainder):
                candidate = _decision_text(text)
        elif AGREEMENT.search(text):
            for previous in reversed(records[max(0, index - 3) : index]):
                if PROPOSAL.search(previous["text"]):
                    candidate = _decision_text(previous["text"])
                    evidence = [previous["id"], record["id"]]
                    break

        key = _normalise(candidate)
        if not candidate or not key or key in seen:
            continue
        seen.add(key)
        decisions.append(
            {
                "decision": candidate,
                "context": NOT_SPECIFIED,
                "owner": NOT_SPECIFIED,
                "evidenceSegmentIds": evidence,
            }
        )
        if len(decisions) >= 12:
            break
    return decisions


def _near_duplicate(value: str, existing: list[str]) -> bool:
    tokens = _content_tokens(value)
    if not tokens:
        return True
    for current in existing:
        other = _content_tokens(current)
        if other and len(tokens & other) / max(1, min(len(tokens), len(other))) >= 0.72:
            return True
    return False


class ExtractiveMeetingAnalyzer:
    """Fast, private analysis that can only use transcript evidence.

    The local analyzer deliberately favors precision over invention. It runs in
    the companion without a network service or another multi-gigabyte model,
    while retaining source-segment citations for every generated field.
    """

    name = "notesbuddy-local-extractive-v1"

    @staticmethod
    def configuration_status() -> dict[str, object]:
        return {
            "ready": True,
            "model": ExtractiveMeetingAnalyzer.name,
            "status": "private grounded analysis ready",
        }

    def analyze(
        self,
        *,
        segments: object,
        meeting_title: object = "",
        progress: Callable[[float, str], None] | None = None,
    ) -> dict[str, Any]:
        # Deterministic and effectively instant; nothing meaningful to
        # report, but accepts the same signature as the other analyzers so
        # a caller can treat active_analyzer.analyze(...) polymorphically.
        if progress is not None:
            progress(1.0, "Completed")
        prepared = prepare_transcript_segments(segments)
        if not prepared:
            raise MeetingAnalysisUnavailable(
                "A completed transcript is required for meeting analysis."
            )
        records = _sentence_records(prepared)
        substantive = [
            record
            for record in records
            if not GREETING_OR_FILLER.search(record["text"])
            or len(_content_tokens(record["text"])) >= 5
        ]
        if not substantive:
            substantive = records

        actions: list[dict[str, Any]] = []
        seen_actions: list[str] = []
        for record in substantive:
            action = _action_from_record(record)
            if action is None or _near_duplicate(action["task"], seen_actions):
                continue
            seen_actions.append(action["task"])
            actions.append(action)
            if len(actions) >= 30:
                break

        decisions = _decision_items(substantive)

        ranked: list[tuple[int, int, dict[str, Any]]] = []
        for index, record in enumerate(substantive):
            text = record["text"]
            score = min(len(_content_tokens(text)), 8)
            if CONFIRMED_ACTION.search(text):
                score += 9
            if CONFIRMED_DECISION.search(text) or AGREEMENT.search(text):
                score += 8
            if PROPOSAL.search(text):
                score += 4
            if re.search(
                r"\b(?:risk|issue|problem|blocked|concern|update|finding|"
                r"opportunity|deadline|budget|scope|recommend)\b",
                text,
                re.IGNORECASE,
            ):
                score += 5
            ranked.append((score, -index, record))
        ranked.sort(reverse=True, key=lambda item: (item[0], item[1]))

        highlights: list[dict[str, Any]] = []
        highlight_texts: list[str] = []
        for _score, _negative_index, record in ranked:
            if AGREEMENT.search(record["text"]) and len(
                _content_tokens(record["text"])
            ) <= 2:
                continue
            text = _sentence_case(record["text"])
            if _near_duplicate(text, highlight_texts):
                continue
            highlight_texts.append(text)
            highlights.append(
                {"text": text, "evidenceSegmentIds": [record["id"]]}
            )
            if len(highlights) >= min(8, max(3, len(substantive))):
                break
        highlights.sort(
            key=lambda item: next(
                index
                for index, record in enumerate(records)
                if record["id"] == item["evidenceSegmentIds"][0]
            )
        )

        summary_parts: list[str] = []
        summary_evidence: list[str] = []
        clean_title = _clean_text(meeting_title, maximum=200)
        title_evidence = [
            segment["id"]
            for segment in prepared
            if clean_title
            and _content_tokens(clean_title)
            and _content_tokens(clean_title) <= _content_tokens(segment["text"])
        ]
        if title_evidence:
            summary_parts.append(f"The meeting purpose was: {clean_title}.")
            summary_evidence.append(title_evidence[0])

        topic_items: list[tuple[str, list[str]]] = []
        for item in decisions[:2]:
            topic_items.append((item["decision"], item["evidenceSegmentIds"]))
        for item in actions:
            if len(topic_items) >= 3:
                break
            if not _near_duplicate(item["task"], [value for value, _ids in topic_items]):
                topic_items.append((item["task"], item["evidenceSegmentIds"]))
        for item in highlights:
            if len(topic_items) >= 3:
                break
            if not _near_duplicate(item["text"], [value for value, _ids in topic_items]):
                topic_items.append((item["text"], item["evidenceSegmentIds"]))
        if topic_items:
            topics = "; ".join(
                _without_terminal_punctuation(text) for text, _ids in topic_items
            )
            summary_parts.append(f"The main topics were: {topics}.")
            summary_evidence.extend(
                evidence_id
                for _text, evidence_ids in topic_items
                for evidence_id in evidence_ids
            )
        if decisions:
            outcomes = "; ".join(
                _without_terminal_punctuation(item["decision"])
                for item in decisions[:2]
            )
            summary_parts.append(f"The confirmed outcome was: {outcomes}.")
            summary_evidence.extend(
                evidence_id
                for item in decisions[:2]
                for evidence_id in item["evidenceSegmentIds"]
            )
        if actions:
            rendered_steps: list[str] = []
            for item in actions[:4]:
                task = _without_terminal_punctuation(item["task"])
                owner = item["owner"]
                due_date = item["dueDate"]
                step = (
                    f"{owner} to {task[0].lower() + task[1:]}"
                    if owner != NOT_SPECIFIED
                    else task
                )
                if due_date != NOT_SPECIFIED:
                    step += (
                        f" by {due_date}"
                        if not due_date.lower().startswith("before ")
                        else f" {due_date[0].lower() + due_date[1:]}"
                    )
                rendered_steps.append(step)
            next_steps = "; ".join(rendered_steps)
            summary_parts.append(f"Next steps: {next_steps}.")
            summary_evidence.extend(
                item["evidenceSegmentIds"][0] for item in actions[:4]
            )

        summary_evidence = list(dict.fromkeys(summary_evidence))[:12]
        if not summary_parts:
            first = prepared[0]
            summary_parts = [_sentence_case(first["text"])]
            summary_evidence = [first["id"]]

        raw = {
            "shortSummary": _limit_words("\n\n".join(summary_parts), 299),
            "summaryEvidenceSegmentIds": summary_evidence,
            "highlights": highlights,
            "decisions": decisions,
            "actionItems": actions,
        }
        normalised = normalise_analysis(raw, prepared)
        return _public_analysis(normalised, prepared, model_name=self.name)


class LlamaCppMeetingAnalyzer:
    """Grounded meeting analysis using a small local GGUF instruction model."""

    def __init__(
        self,
        *,
        runtime_path: str | Path,
        model_path: str | Path,
        context_tokens: int = 32_768,
        output_tokens: int = 2_048,
        maximum_chunk_characters: int = 12_000,
    ) -> None:
        self.runtime_path = Path(runtime_path)
        self.model_path = Path(model_path)
        # Derived from the installed file rather than a fixed constant: the
        # companion can have any of several quality tiers installed
        # (analysis-tiny/standard/pro), each a differently named GGUF, and
        # the reported model name should reflect whichever is actually
        # loaded rather than always claiming the original 0.5B default.
        self.name = (
            f"notesbuddy-smart-summary-{self.model_path.stem.lower()}"
            if self.model_path.name
            else "notesbuddy-smart-summary"
        )
        self.context_tokens = max(8_192, context_tokens)
        self.output_tokens = min(max(900, output_tokens), 4_096)
        # A 0.5B model was observed to lose coherence and fall into
        # degenerate repetition (see _generate's repeat-penalty comment) once
        # asked to track and cite more than roughly a hundred transcript
        # segment IDs in one completion, well before it runs out of raw
        # context window. The limit here is about the model's effective
        # reasoning span, not --ctx-size, so it is deliberately much smaller
        # than the model's real context length. The existing chunk/merge
        # pipeline already handles multi-chunk transcripts; this just makes
        # it actually trigger for real meeting-length transcripts instead of
        # only for unusually long ones.
        self.maximum_chunk_characters = max(6_000, maximum_chunk_characters)
        self._generation_lock = threading.Lock()

    def configuration_status(self) -> dict[str, object]:
        ready = self.runtime_path.is_file() and self.model_path.is_file()
        return {
            "ready": ready,
            "model": self.name if ready else "",
            "status": (
                "smart local meeting analysis ready"
                if ready
                else "install the Smart summary component"
            ),
        }

    @staticmethod
    def _transcript_text(segments: list[dict[str, Any]]) -> str:
        return "\n".join(_transcript_line(item) for item in segments)

    def _chunks(self, prepared: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        chunks: list[list[dict[str, Any]]] = []
        current: list[dict[str, Any]] = []
        current_size = 0
        for segment in prepared:
            size = len(_transcript_line(segment)) + 1
            if current and current_size + size > self.maximum_chunk_characters:
                chunks.append(current)
                current = []
                current_size = 0
            current.append(segment)
            current_size += size
        if current:
            chunks.append(current)
        return chunks

    def _generate(self, prompt: str, *, output_tokens: int | None = None) -> dict[str, Any]:
        if not self.runtime_path.is_file() or not self.model_path.is_file():
            raise MeetingAnalysisUnavailable(
                "Install the Smart summary component before generating professional analysis."
            )
        output_tokens = output_tokens if output_tokens is not None else self.output_tokens
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        with tempfile.TemporaryDirectory(prefix="notesbuddy-analysis-") as directory:
            root = Path(directory)
            prompt_path = root / "prompt.txt"
            schema_path = root / "schema.json"
            prompt_path.write_text(prompt, encoding="utf-8")
            schema_path.write_text(
                json.dumps(OUTPUT_JSON_SCHEMA, ensure_ascii=False), encoding="utf-8"
            )
            command = [
                str(self.runtime_path), "--model", str(self.model_path),
                "-sys", SYSTEM_PROMPT,
                "--file", str(prompt_path), "--json-schema-file", str(schema_path),
                "--ctx-size", str(self.context_tokens), "--predict", str(output_tokens),
                "--threads", str(max(1, (os.cpu_count() or 4) - 1)),
                "--temp", "0", "--single-turn",
                # Pure greedy decoding (temp 0) with a large real transcript
                # was observed to fall into a token-repetition loop while
                # listing evidence segment IDs (e.g. repeating "S0108 | time
                # unavailable | Speaker 3" dozens of times), burning the
                # entire --predict budget before the JSON object could close.
                # A repeat penalty breaks that loop without changing the
                # otherwise-deterministic sampling.
                "--repeat-penalty", "1.15", "--repeat-last-n", "256",
                # The bundled build's Jinja chat-template engine primes the
                # assistant turn with a literal special token
                # (<|im_start|>assistant). Once a --json-schema-file grammar
                # is active, the sampler treats that special token as part of
                # the constrained output and aborts with "Unexpected empty
                # grammar stack" before generating anything -- every call
                # failed instantly this way, then sat inert until Python's
                # subprocess timeout killed it, which looked identical to a
                # slow CPU rather than an immediate hard failure. --no-jinja
                # falls back to the legacy, non-Jinja template path, which
                # does not hit this and was verified end-to-end against the
                # real production system prompt and schema.
                "--no-jinja",
                "--no-display-prompt", "--simple-io", "--color", "off",
            ]
            # CPU decode time is dominated by the number of tokens generated,
            # not the prompt length (prefill is far cheaper per token than
            # decode). A timeout keyed only on prompt length under-budgets
            # short-prompt, full-length completions and was observed to
            # expire mid-generation on real meeting transcripts.
            timeout_seconds = max(
                300,
                min(1_800, 200 + len(prompt) // 120 + output_tokens // 3),
            )
            try:
                with self._generation_lock:
                    completed = subprocess.run(
                        command, capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=timeout_seconds,
                        startupinfo=startupinfo, check=False,
                    )
            except (OSError, subprocess.TimeoutExpired) as error:
                raise MeetingAnalysisUnavailable(
                    "The local smart-summary model could not complete the analysis."
                ) from error
        if completed.returncode != 0:
            _log_diagnostic(
                "[notesbuddy-analysis] llama_cpp_failed "
                f"return_code={completed.returncode} stderr={completed.stderr[-800:]!r}"
            )
            raise MeetingAnalysisUnavailable(
                "The local smart-summary model could not process this transcript."
            )
        try:
            return _extract_json(completed.stdout)
        except MeetingAnalysisUnavailable:
            _log_diagnostic(
                "[notesbuddy-analysis] llama_cpp_invalid_output "
                f"stdout={ascii(completed.stdout[-1200:])} "
                f"stderr={ascii(completed.stderr[-1200:])}"
            )
            raise

    def _generate_and_normalise(
        self, prompt: str, prepared: list[dict[str, Any]]
    ) -> dict[str, Any]:
        try:
            raw = self._generate(prompt)
        except MeetingAnalysisUnavailable as error:
            if "malformed json" not in str(error).lower():
                raise
            # The output was cut off by --predict before the JSON object
            # closed. A real meeting with more distinct speakers than any
            # transcript this was tuned against needed more room than the
            # tier's default budget -- no fixed per-tier ceiling can be
            # sized correctly for every real transcript's content in
            # advance, so retry once with more room rather than failing
            # a professional analysis outright over a budget guess.
            retry_tokens = min(8_192, self.output_tokens * 2)
            raw = self._generate(prompt, output_tokens=retry_tokens)
        try:
            result = normalise_analysis(raw, prepared)
            _log_diagnostic(
                "[notesbuddy-analysis] summary_accepted path=first_attempt "
                f"raw_counts=({_field_counts(raw)}) "
                f"validated_counts=({_field_counts(result)}) "
                f"summary={ascii(result.get('shortSummary'))[:300]}"
            )
            return result
        except MeetingAnalysisUnavailable as error:
            if "summary" not in str(error).lower():
                raise
            # A real result had a well-formed shortSummary reduced to two
            # concatenated highlight titles ("Technical Constraints and
            # Timeframe. Discovery Phase Documentation Requirements.") --
            # the model's own summary had failed grounding, and the old
            # fallback below reused highlight/decision/action text
            # verbatim, which reads as title fragments, not prose, once
            # several are joined. A model capable enough to be worth
            # installing usually writes a grounded summary when explicitly
            # told why the first attempt failed, so try that before
            # resorting to text concatenation.
            try:
                retry_raw = self._generate(
                    prompt
                    + "\n\nYour previous shortSummary used wording not found "
                    "in the transcript segments you cited as evidence. Write "
                    "shortSummary as 1-3 full sentences using only facts and "
                    "wording supported by its cited segments. Do not reuse a "
                    "highlight, decision, or action item verbatim as the "
                    "summary. Still return every highlight, confirmed "
                    "decision, and action item you can find, exactly as "
                    "thoroughly as before -- only the summary needs to "
                    "change."
                )
                # A real chunk's retry returned a summary describing a
                # scheduled follow-up session and a to-be-sent document
                # (facts it clearly extracted), yet its own highlights,
                # decisions, and actionItems arrays came back completely
                # empty in that same response. The retry prompt above
                # narrows the model's attention onto fixing the summary
                # field specifically, and the first attempt's structured
                # findings were never actually invalidated -- they simply
                # never got checked, because normalise_analysis raises on a
                # bad summary before validating anything else. Combine both
                # attempts' raw highlights/decisions/actionItems (letting
                # normalise_analysis's own per-item grounding and dedup
                # decide what survives) instead of discarding whichever the
                # retry happened to omit.
                combined_retry = dict(retry_raw) if isinstance(retry_raw, dict) else {}
                if isinstance(raw, dict):
                    for field in ("highlights", "decisions", "actionItems"):
                        combined_retry[field] = [
                            *(raw.get(field) or []),
                            *(combined_retry.get(field) or []),
                        ]
                result = normalise_analysis(combined_retry, prepared)
                _log_diagnostic(
                    "[notesbuddy-analysis] summary_accepted path=reinforcement_retry "
                    f"first_attempt_counts=({_field_counts(raw)}) "
                    f"retry_raw_counts=({_field_counts(retry_raw)}) "
                    f"validated_counts=({_field_counts(result)}) "
                    f"summary={ascii(result.get('shortSummary'))[:300]}"
                )
                return result
            except MeetingAnalysisUnavailable as retry_error:
                if "summary" not in str(retry_error).lower():
                    raise
                # The reinforcement retry also failed grounding. Its own
                # generation is otherwise independent of the first attempt
                # (different prompt context, same temp=0 determinism), so
                # its highlights/decisions/actions are a second, differently
                # worded candidate pool -- not just the first attempt's,
                # which would otherwise make this fallback produce the exact
                # same concatenated text on every retry of the same meeting.
                retry_candidates = (
                    (retry_raw,) if isinstance(retry_raw, dict) else ()
                )
                _log_diagnostic(
                    "[notesbuddy-analysis] summary_repair_fallback "
                    f"first_attempt={ascii(_clean_text(raw.get('shortSummary')) if isinstance(raw, dict) else raw)[:300]} "
                    f"retry_attempt={ascii(_clean_text(retry_raw.get('shortSummary')) if isinstance(retry_raw, dict) else retry_raw)[:300]}"
                )
                repaired = _repair_summary_from_grounded_items(
                    raw, prepared, *retry_candidates
                )
                result = normalise_analysis(repaired, prepared)
                _log_diagnostic(
                    "[notesbuddy-analysis] summary_accepted path=repair_fallback "
                    f"raw_counts=({_field_counts(repaired)}) "
                    f"validated_counts=({_field_counts(result)}) "
                    f"summary={ascii(result.get('shortSummary'))[:300]}"
                )
                return result

    def analyze(
        self,
        *,
        segments: object,
        meeting_title: object = "",
        progress: Callable[[float, str], None] | None = None,
    ) -> dict[str, Any]:
        def report(value: float, stage: str) -> None:
            if progress is not None:
                progress(value, stage)

        prepared = prepare_transcript_segments(segments)
        if not prepared:
            raise MeetingAnalysisUnavailable(
                "A completed transcript is required for meeting analysis."
            )
        partials: list[dict[str, Any]] = []
        chunks = self._chunks(prepared)
        # Each chunk is a real CPU generation call that can take minutes with
        # no other feedback available, so this is real progress a caller can
        # show, not decoration -- there is no cheaper way to estimate it,
        # since a chunk's generation time depends on its own content.
        for index, chunk in enumerate(chunks):
            report(
                index / len(chunks) * 0.92,
                f"Analyzing part {index + 1} of {len(chunks)}"
                if len(chunks) > 1
                else "Analyzing the complete transcript",
            )
            prompt = (
                f"Meeting title: {_clean_text(meeting_title, maximum=200) or NOT_SPECIFIED}\n"
                f"Transcript part {index + 1} of {len(chunks)} follows. Analyze the meaning; "
                "do not copy long transcript passages. Use only these segment IDs as evidence.\n\n"
                f"{self._transcript_text(chunk)}\n\nReturn the required JSON object."
            )
            partials.append(self._generate_and_normalise(prompt, prepared))
        report(0.95, "Combining results")
        merged = self._merge_partials(partials, prepared)
        report(1.0, "Completed")
        return _public_analysis(merged, prepared, model_name=self.name)

    @staticmethod
    def _merge_partials(
        partials: list[dict[str, Any]],
        prepared: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Combine already-normalised per-chunk analyses without another model call.

        Asking this model to merge multiple chunks by re-reading their JSON
        was observed to be *harder* for it than the original per-chunk
        summarisation: on a real 298-segment meeting, every individual chunk
        analysed cleanly, but the follow-up merge call degenerated into
        empty/repetitive output. Each partial already passed the same
        grounding and validation as a solo result, so concatenating them in
        code and re-running normalise_analysis (which already dedupes by
        normalised text) is simpler and does not depend on model capacity.
        """
        if len(partials) == 1:
            return partials[0]

        def _dedup_ids(ids: list[str]) -> list[str]:
            seen: list[str] = []
            for segment_id in ids:
                if segment_id not in seen:
                    seen.append(segment_id)
            return seen

        summaries = [
            text
            for part in partials
            for text in [str(part.get("shortSummary") or "").strip()]
            if text
        ]
        combined = {
            "shortSummary": " ".join(summaries),
            "summaryEvidenceSegmentIds": _dedup_ids(
                [
                    segment_id
                    for part in partials
                    for segment_id in part.get("summaryEvidenceSegmentIds") or []
                ]
            ),
            "highlights": [item for part in partials for item in part.get("highlights") or []],
            "decisions": [item for part in partials for item in part.get("decisions") or []],
            "actionItems": [item for part in partials for item in part.get("actionItems") or []],
        }
        _log_diagnostic(
            "[notesbuddy-analysis] merge_starting "
            f"per_chunk_counts=[{'; '.join(_field_counts(part) for part in partials)}] "
            f"combined_pre_merge_counts=({_field_counts(combined)})"
        )
        try:
            result = normalise_analysis(combined, prepared)
            _log_diagnostic(
                "[notesbuddy-analysis] merge_summary_accepted "
                f"validated_counts=({_field_counts(result)}) "
                f"summary={ascii(result.get('shortSummary'))[:400]}"
            )
            return result
        except MeetingAnalysisUnavailable as error:
            if "summary" not in str(error).lower():
                raise
            # Concatenating the per-chunk summaries verbatim failed this
            # same check on real multi-chunk meetings even though every
            # chunk analysed cleanly on its own (see normalise_analysis's
            # trusted_summary parameter for why re-checking here is both
            # redundant and too strict). Trust the already-individually-
            # grounded per-chunk summaries instead of falling back to
            # concatenated highlight/decision/action titles, which reads as
            # disconnected labels rather than a summary.
            _log_diagnostic(
                "[notesbuddy-analysis] merge_summary_grounding_failed "
                f"reason={error} combined_summary={ascii(combined['shortSummary'])[:400]}"
            )
            result = normalise_analysis(
                combined,
                prepared,
                trusted_summary=(
                    combined["shortSummary"],
                    combined["summaryEvidenceSegmentIds"],
                ),
            )
            _log_diagnostic(
                "[notesbuddy-analysis] merge_summary_accepted path=trusted_partials "
                f"validated_counts=({_field_counts(result)}) "
                f"summary={ascii(result.get('shortSummary'))[:400]}"
            )
            return result


class LocalAnalysisRouter:
    """Resolve the optional analysis component without restarting the companion."""

    @staticmethod
    def _resolve_model_path(configured: str) -> Path:
        """Find the installed model file inside the shared analysis directory.

        Three quality tiers (analysis-tiny/standard/pro) share one
        destination folder so installing a different tier replaces the
        previous one on disk, matching the existing whisper-base/
        whisper-small pattern. Each tier's GGUF filename differs, so the
        active one is discovered here rather than pinned to one literal
        filename -- this is re-resolved on every call, so a component
        installed after the companion started is picked up immediately.
        """
        path = Path(configured) if configured else Path()
        if path.is_dir():
            found = sorted(path.glob("*.gguf"))
            if found:
                return found[0]
        return path

    @staticmethod
    def _output_tokens_for(model_path: Path) -> int:
        """Give every tier but the smallest more room to finish their JSON.

        A real test against the "pro" (4B) tier showed noticeably richer,
        more specific output (real names, dates, business context) than the
        smaller tiers -- but 2 of 3 chunks hit the 2048-token --predict
        ceiling before the JSON object could close, failing as "malformed
        JSON" even though the content itself was good. A real 6-speaker
        meeting later hit the same failure on "standard" (1.7B) too, which
        the original 1.5 GB threshold had left at 2048 -- how much output a
        chunk needs depends on its content (speaker count, decisions,
        actions), not the model's file size, so no fixed per-tier number can
        be exactly right for every real transcript; _generate_and_normalise
        retries once with more room if this still is not enough. Sized off
        the installed file rather than a filename/tier lookup so it keeps
        working if the exact pinned model file ever changes.
        """
        try:
            size_bytes = model_path.stat().st_size
        except OSError:
            return 2_048
        return 4_096 if size_bytes >= 700_000_000 else 2_048

    @staticmethod
    def _analyzer() -> LlamaCppMeetingAnalyzer:
        model_path = LocalAnalysisRouter._resolve_model_path(
            os.getenv("NOTESBUDDY_ANALYSIS_MODEL_PATH", "")
        )
        return LlamaCppMeetingAnalyzer(
            runtime_path=os.getenv("NOTESBUDDY_ANALYSIS_RUNTIME", ""),
            model_path=model_path,
            output_tokens=LocalAnalysisRouter._output_tokens_for(model_path),
        )

    def configuration_status(self) -> dict[str, object]:
        return self._analyzer().configuration_status()

    def analyze(
        self,
        *,
        segments: object,
        meeting_title: object = "",
        progress: Callable[[float, str], None] | None = None,
    ) -> dict[str, Any]:
        return self._analyzer().analyze(
            segments=segments, meeting_title=meeting_title, progress=progress
        )


class MeetingAnalyzer:
    """Lazy local/hosted instruction-model adapter."""

    name = "professional meeting analyst"

    def __init__(
        self,
        *,
        model_name: str,
        revision: str | None = None,
        device: str = "cuda",
        maximum_chunk_tokens: int = 3_600,
        maximum_input_tokens: int = 6_000,
        maximum_output_tokens: int = 1_600,
        merge_batch_size: int = 3,
    ) -> None:
        self.model_name = model_name
        self.revision = revision or None
        self.device = device
        self.maximum_input_tokens = max(2_500, maximum_input_tokens)
        self.maximum_chunk_tokens = min(
            max(1_000, maximum_chunk_tokens),
            self.maximum_input_tokens - 1_200,
        )
        self.maximum_output_tokens = min(
            max(600, maximum_output_tokens),
            2_000,
        )
        self.merge_batch_size = min(max(2, merge_batch_size), 4)
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
                    dtype=dtype,
                    low_cpu_mem_usage=True,
                ).to(self.device)
                self._model.eval()
        return self._tokenizer, self._model

    @staticmethod
    def _transcript_text(segments: list[dict[str, Any]]) -> str:
        return "\n".join(_transcript_line(item) for item in segments)

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
            truncation=False,
        )
        input_tokens = int(inputs["input_ids"].shape[-1])
        if input_tokens > self.maximum_input_tokens:
            raise MeetingAnalysisUnavailable(
                "A transcript section exceeded the safe analysis size."
            )
        inputs = inputs.to(self.device)
        try:
            import torch

            with self._generation_lock, torch.inference_mode():
                output = model.generate(
                    **inputs,
                    max_new_tokens=self.maximum_output_tokens,
                    do_sample=False,
                    repetition_penalty=1.04,
                    pad_token_id=tokenizer.eos_token_id,
                )
        except RuntimeError as error:
            out_of_memory = "out of memory" in str(error).lower()
            print(
                "[notesbuddy-analysis] generation_failed "
                f"input_tokens={input_tokens} "
                f"error_type={type(error).__name__} "
                f"out_of_memory={str(out_of_memory).lower()}",
                flush=True,
            )
            if out_of_memory and torch.cuda.is_available():
                torch.cuda.empty_cache()
            raise MeetingAnalysisUnavailable(
                "The professional analysis model could not process this transcript."
            ) from error
        generated = output[0][inputs["input_ids"].shape[-1] :]
        return _extract_json(tokenizer.decode(generated, skip_special_tokens=True))

    def _merge_analyses(
        self,
        partials: list[dict[str, Any]],
        prepared: list[dict[str, Any]],
    ) -> dict[str, Any]:
        current = partials
        while len(current) > 1:
            merged: list[dict[str, Any]] = []
            for start in range(0, len(current), self.merge_batch_size):
                batch = current[start : start + self.merge_batch_size]
                if len(batch) == 1:
                    merged.append(batch[0])
                    continue
                merge_prompt = (
                    "The following evidence-grounded analyses cover consecutive "
                    "parts of one meeting. Merge them into one professional analysis. "
                    "Combine repetition, preserve all confirmed decisions and distinct "
                    "tasks, and retain the cited segment IDs. Do not add any fact absent "
                    "from these partial analyses.\n\n"
                    f"{json.dumps(batch, ensure_ascii=False)}\n\n"
                    "Return exactly this JSON shape:\n"
                    f"{json.dumps(OUTPUT_SHAPE, ensure_ascii=False)}"
                )
                merged.append(
                    self._generate_and_normalise(merge_prompt, prepared)
                )
            current = merged
        return current[0]

    def _generate_and_normalise(
        self,
        prompt: str,
        prepared: list[dict[str, Any]],
    ) -> dict[str, Any]:
        raw_analysis = self._generate(prompt)
        try:
            return normalise_analysis(raw_analysis, prepared)
        except MeetingAnalysisUnavailable as error:
            if "summary" not in str(error).lower():
                raise
            repaired = _repair_summary_from_grounded_items(
                raw_analysis,
                prepared,
            )
            return normalise_analysis(repaired, prepared)

    def analyze(
        self,
        *,
        segments: object,
        meeting_title: object = "",
        progress: Callable[[float, str], None] | None = None,
    ) -> dict[str, Any]:
        prepared = prepare_transcript_segments(segments)
        if not prepared:
            raise MeetingAnalysisUnavailable(
                "A completed transcript is required for meeting analysis."
            )
        tokenizer, _model = self._load()
        chunks = _transcript_chunks(
            prepared,
            tokenizer,
            self.maximum_chunk_tokens,
        )
        partials: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks):
            if progress is not None:
                progress(
                    index / len(chunks) * 0.92,
                    f"Analyzing part {index + 1} of {len(chunks)}"
                    if len(chunks) > 1
                    else "Analyzing the complete transcript",
                )
            prompt = (
                f"Meeting title: {_clean_text(meeting_title, maximum=200) or 'Not specified'}\n"
                f"Transcript part {index + 1} of {len(chunks)} follows. Analyze only "
                "what is supported by these segments.\n\n"
                f"{self._transcript_text(chunk)}\n\n"
                "Return exactly this JSON shape:\n"
                f"{json.dumps(OUTPUT_SHAPE, ensure_ascii=False)}"
            )
            partials.append(self._generate_and_normalise(prompt, prepared))

        if len(partials) == 1:
            final = partials[0]
        else:
            if progress is not None:
                progress(0.95, "Combining results")
            final = self._merge_analyses(partials, prepared)
        if progress is not None:
            progress(1.0, "Completed")
        return _public_analysis(final, prepared, model_name=self.model_name)


def analyzer_from_environment() -> MeetingAnalyzer | LocalAnalysisRouter:
    model_name = os.getenv("NOTESBUDDY_ANALYSIS_MODEL", "").strip()
    if not model_name:
        return LocalAnalysisRouter()
    return MeetingAnalyzer(
        model_name=model_name,
        revision=os.getenv("NOTESBUDDY_ANALYSIS_REVISION", "").strip() or None,
        device=os.getenv("NOTESBUDDY_ANALYSIS_DEVICE", "cuda").strip(),
        maximum_chunk_tokens=int(
            os.getenv("NOTESBUDDY_ANALYSIS_CHUNK_TOKENS", "3600")
        ),
        maximum_input_tokens=int(
            os.getenv("NOTESBUDDY_ANALYSIS_INPUT_TOKENS", "6000")
        ),
        maximum_output_tokens=int(
            os.getenv("NOTESBUDDY_ANALYSIS_OUTPUT_TOKENS", "1600")
        ),
        merge_batch_size=int(
            os.getenv("NOTESBUDDY_ANALYSIS_MERGE_BATCH_SIZE", "3")
        ),
    )
