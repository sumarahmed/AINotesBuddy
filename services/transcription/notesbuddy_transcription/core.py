"""Pure timestamp alignment and transcript assembly.

This module deliberately has no model or web-framework dependencies so the
speaker-assignment rules can be tested quickly and deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable, Sequence
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Word:
    """A word emitted by speech-to-text with source-clock timestamps."""

    start_ms: int
    end_ms: int
    text: str
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class SpeakerTurn:
    """A raw diarization interval before session-local IDs are assigned."""

    start_ms: int
    end_ms: int
    label: str


@dataclass(frozen=True, slots=True)
class AttributedWord:
    start_ms: int
    end_ms: int
    text: str
    speaker_id: str
    confidence: float | None = None


def _milliseconds(value: int | float) -> int:
    return max(0, int(round(float(value))))


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").replace("\x00", "").split())


def _intersection_ms(
    first_start: int,
    first_end: int,
    second_start: int,
    second_end: int,
) -> int:
    return max(0, min(first_end, second_end) - max(first_start, second_start))


def _speaker_id_map(turns: Sequence[SpeakerTurn]) -> dict[str, str]:
    """Map model labels to stable IDs ordered by first appearance."""

    first_appearance: dict[str, int] = {}
    for turn in turns:
        if not turn.label:
            continue
        first_appearance[turn.label] = min(
            first_appearance.get(turn.label, turn.start_ms),
            turn.start_ms,
        )
    ordered = sorted(first_appearance, key=lambda label: first_appearance[label])
    return {label: f"remote-{index + 1}" for index, label in enumerate(ordered)}


def assign_words_to_speakers(
    words: Iterable[Word],
    turns: Iterable[SpeakerTurn],
) -> list[AttributedWord]:
    """Assign each word to the turn with the greatest timestamp overlap.

    A word whose midpoint is within 350 ms of a turn can be assigned to that
    turn when timestamp rounding leaves no literal overlap. More distant words
    remain ``remote-unknown`` instead of guessing an identity.
    """

    normalized_turns = sorted(
        (
            SpeakerTurn(
                _milliseconds(turn.start_ms),
                max(_milliseconds(turn.start_ms), _milliseconds(turn.end_ms)),
                _clean_text(turn.label),
            )
            for turn in turns
            if _clean_text(turn.label)
        ),
        key=lambda turn: (turn.start_ms, turn.end_ms, turn.label),
    )
    speaker_ids = _speaker_id_map(normalized_turns)
    attributed: list[AttributedWord] = []

    for word in words:
        text = _clean_text(word.text)
        if not text:
            continue
        start_ms = _milliseconds(word.start_ms)
        end_ms = max(start_ms + 1, _milliseconds(word.end_ms))
        best_turn: SpeakerTurn | None = None
        best_overlap = 0
        for turn in normalized_turns:
            if turn.start_ms > end_ms + 350:
                break
            if turn.end_ms < start_ms - 350:
                continue
            overlap = _intersection_ms(
                start_ms,
                end_ms,
                turn.start_ms,
                turn.end_ms,
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best_turn = turn

        if best_turn is None:
            midpoint = start_ms + ((end_ms - start_ms) // 2)
            nearest: tuple[int, SpeakerTurn] | None = None
            for turn in normalized_turns:
                distance = (
                    turn.start_ms - midpoint
                    if midpoint < turn.start_ms
                    else midpoint - turn.end_ms
                    if midpoint > turn.end_ms
                    else 0
                )
                if distance <= 350 and (nearest is None or distance < nearest[0]):
                    nearest = (distance, turn)
            best_turn = nearest[1] if nearest else None

        attributed.append(
            AttributedWord(
                start_ms=start_ms,
                end_ms=end_ms,
                text=text,
                speaker_id=(
                    speaker_ids.get(best_turn.label, "remote-unknown")
                    if best_turn
                    else "remote-unknown"
                ),
                confidence=word.confidence,
            )
        )
    return attributed


def _join_words(parts: Sequence[str]) -> str:
    text = ""
    no_space_before = {".", ",", "!", "?", ":", ";", "%", ")", "]", "}"}
    no_space_after = {"(", "[", "{", "$", "£", "€"}
    for raw_part in parts:
        part = _clean_text(raw_part)
        if not part:
            continue
        if not text:
            text = part
        elif part in no_space_before or part.startswith(("'", "’")):
            text += part
        elif text[-1] in no_space_after:
            text += part
        else:
            text += f" {part}"
    return text.strip()


def collapse_words(
    words: Iterable[AttributedWord],
    *,
    source: str,
    maximum_gap_ms: int = 900,
    maximum_words: int = 42,
) -> list[dict]:
    """Collapse adjacent attributed words into readable speaker segments."""

    ordered = sorted(words, key=lambda word: (word.start_ms, word.end_ms))
    segments: list[dict] = []
    current: list[AttributedWord] = []

    def flush() -> None:
        if not current:
            return
        confidences = [
            word.confidence
            for word in current
            if word.confidence is not None
        ]
        speaker_id = current[0].speaker_id
        segments.append(
            {
                "id": f"segment-{uuid4()}",
                "source": source,
                "speakerId": speaker_id,
                "speakerLabel": (
                    "Unknown speaker"
                    if speaker_id == "remote-unknown"
                    else ""
                ),
                "startMs": current[0].start_ms,
                "endMs": max(word.end_ms for word in current),
                "text": _join_words([word.text for word in current]),
                "confidence": (
                    round(sum(confidences) / len(confidences), 4)
                    if confidences
                    else None
                ),
            }
        )
        current.clear()

    for word in ordered:
        if current:
            previous = current[-1]
            should_split = (
                word.speaker_id != previous.speaker_id
                or word.start_ms - previous.end_ms > maximum_gap_ms
                or len(current) >= maximum_words
            )
            if should_split:
                flush()
        current.append(word)
    flush()
    return segments


def microphone_segments(words: Iterable[Word]) -> list[dict]:
    attributed = [
        AttributedWord(
            start_ms=_milliseconds(word.start_ms),
            end_ms=max(_milliseconds(word.start_ms) + 1, _milliseconds(word.end_ms)),
            text=_clean_text(word.text),
            speaker_id="local-user",
            confidence=word.confidence,
        )
        for word in words
        if _clean_text(word.text)
    ]
    return collapse_words(attributed, source="microphone")


def meeting_segments(
    words: Iterable[Word],
    turns: Iterable[SpeakerTurn],
) -> list[dict]:
    return collapse_words(
        assign_words_to_speakers(words, turns),
        source="meeting",
    )


def _normalised_comparison_text(value: object) -> str:
    return "".join(
        character.lower()
        for character in _clean_text(value)
        if character.isalnum() or character.isspace()
    )


def _segment_overlap_ratio(first: dict, second: dict) -> float:
    overlap = _intersection_ms(
        int(first.get("startMs", 0)),
        int(first.get("endMs", first.get("startMs", 0))),
        int(second.get("startMs", 0)),
        int(second.get("endMs", second.get("startMs", 0))),
    )
    first_length = max(
        1,
        int(first.get("endMs", 0)) - int(first.get("startMs", 0)),
    )
    second_length = max(
        1,
        int(second.get("endMs", 0)) - int(second.get("startMs", 0)),
    )
    return overlap / min(first_length, second_length)


def deduplicate_echo_segments(segments: Iterable[dict]) -> list[dict]:
    """Remove cross-source near-duplicates, preferring isolated microphone."""

    ordered = sorted(
        (dict(segment) for segment in segments if _clean_text(segment.get("text"))),
        key=lambda segment: (
            int(segment.get("startMs", 0)),
            int(segment.get("endMs", 0)),
        ),
    )
    removed: set[int] = set()
    for first_index, first in enumerate(ordered):
        if first_index in removed:
            continue
        for second_index in range(first_index + 1, len(ordered)):
            if second_index in removed:
                continue
            second = ordered[second_index]
            if int(second.get("startMs", 0)) - int(first.get("endMs", 0)) > 1800:
                break
            if first.get("source") == second.get("source"):
                continue
            if _segment_overlap_ratio(first, second) < 0.55:
                continue
            similarity = SequenceMatcher(
                None,
                _normalised_comparison_text(first.get("text")),
                _normalised_comparison_text(second.get("text")),
            ).ratio()
            if similarity < 0.82:
                continue
            if first.get("source") == "microphone":
                removed.add(second_index)
            elif second.get("source") == "microphone":
                removed.add(first_index)
                break
            elif (first.get("confidence") or 0) >= (
                second.get("confidence") or 0
            ):
                removed.add(second_index)
            else:
                removed.add(first_index)
                break
    return [
        segment for index, segment in enumerate(ordered) if index not in removed
    ]


def build_transcript(
    *,
    microphone_words: Iterable[Word] = (),
    meeting_words: Iterable[Word] = (),
    meeting_turns: Iterable[SpeakerTurn] = (),
) -> list[dict]:
    """Build one clock-ordered transcript from isolated capture sources."""

    combined = [
        *microphone_segments(microphone_words),
        *meeting_segments(meeting_words, meeting_turns),
    ]
    return deduplicate_echo_segments(combined)
