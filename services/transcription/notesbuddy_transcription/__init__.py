"""Local transcription and speaker diarization companion for NotesBuddy."""

from .core import (
    SpeakerTurn,
    Word,
    assign_words_to_speakers,
    build_transcript,
    collapse_words,
    deduplicate_echo_segments,
)

__all__ = [
    "SpeakerTurn",
    "Word",
    "assign_words_to_speakers",
    "build_transcript",
    "collapse_words",
    "deduplicate_echo_segments",
]
