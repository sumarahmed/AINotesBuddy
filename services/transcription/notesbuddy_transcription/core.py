"""Pure transcript assembly from a single mixed-audio word stream.

This module deliberately has no model or web-framework dependencies so the
segment-collapsing rules can be tested quickly and deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Word:
    """A word emitted by speech-to-text with source-clock timestamps."""

    start_ms: int
    end_ms: int
    text: str
    confidence: float | None = None


def _milliseconds(value: int | float) -> int:
    return max(0, int(round(float(value))))


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").replace("\x00", "").split())


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


def build_transcript(
    words: Iterable[Word],
    *,
    maximum_gap_ms: int = 900,
    maximum_words: int = 42,
) -> list[dict]:
    """Collapse a clock-ordered word stream into readable transcript segments.

    There is only one mixed-audio source and no speaker attribution, so the
    only split condition is a pause gap (or a maximum segment length) --
    unlike the old per-speaker collapse, there is no speaker-change
    condition to check. Silence (no words) returns an empty list rather than
    fabricating a segment.
    """

    ordered = sorted(
        (word for word in words if _clean_text(word.text)),
        key=lambda word: (word.start_ms, word.end_ms),
    )
    segments: list[dict] = []
    current: list[Word] = []

    def flush() -> None:
        if not current:
            return
        confidences = [
            word.confidence for word in current if word.confidence is not None
        ]
        segments.append(
            {
                "id": f"segment-{uuid4()}",
                "startMs": _milliseconds(current[0].start_ms),
                "endMs": max(_milliseconds(word.end_ms) for word in current),
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
                _milliseconds(word.start_ms) - _milliseconds(previous.end_ms)
                > maximum_gap_ms
                or len(current) >= maximum_words
            )
            if should_split:
                flush()
        current.append(word)
    flush()
    return segments
