from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notesbuddy_transcription.core import (
    AttributedWord,
    SpeakerTurn,
    Word,
    assign_words_to_speakers,
    build_transcript,
    collapse_words,
    deduplicate_echo_segments,
)


class TimestampAlignmentTests(unittest.TestCase):
    def test_assigns_words_by_greatest_turn_overlap(self) -> None:
        words = [
            Word(100, 450, "hello", 0.9),
            Word(500, 900, "there", 0.8),
            Word(1200, 1500, "welcome", 0.95),
        ]
        turns = [
            SpeakerTurn(0, 1000, "SPEAKER_01"),
            SpeakerTurn(1100, 1800, "SPEAKER_00"),
        ]

        result = assign_words_to_speakers(words, turns)

        self.assertEqual(
            [word.speaker_id for word in result],
            ["remote-1", "remote-1", "remote-2"],
        )

    def test_leaves_distant_word_unknown(self) -> None:
        result = assign_words_to_speakers(
            [Word(5000, 5200, "uncertain")],
            [SpeakerTurn(0, 1000, "SPEAKER_00")],
        )

        self.assertEqual(result[0].speaker_id, "remote-unknown")

    def test_collapses_adjacent_words_but_splits_speakers(self) -> None:
        result = collapse_words(
            [
                AttributedWord(0, 200, "Good", "remote-1", 0.9),
                AttributedWord(210, 500, "morning", "remote-1", 0.8),
                AttributedWord(520, 800, "Hello", "remote-2", 0.95),
            ],
            source="meeting",
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["text"], "Good morning")
        self.assertEqual(result[1]["speakerId"], "remote-2")


class TranscriptAssemblyTests(unittest.TestCase):
    def test_marks_microphone_as_local_user(self) -> None:
        result = build_transcript(
            microphone_words=[
                Word(0, 300, "I"),
                Word(310, 600, "agree."),
            ]
        )

        self.assertEqual(result[0]["source"], "microphone")
        self.assertEqual(result[0]["speakerId"], "local-user")
        self.assertEqual(result[0]["text"], "I agree.")

    def test_merges_sources_in_clock_order(self) -> None:
        result = build_transcript(
            microphone_words=[Word(1000, 1300, "Local")],
            meeting_words=[Word(100, 400, "Remote")],
            meeting_turns=[SpeakerTurn(0, 700, "A")],
        )

        self.assertEqual(
            [segment["source"] for segment in result],
            ["meeting", "microphone"],
        )

    def test_removes_remote_echo_of_microphone(self) -> None:
        result = deduplicate_echo_segments(
            [
                {
                    "id": "local",
                    "source": "microphone",
                    "speakerId": "local-user",
                    "startMs": 1000,
                    "endMs": 3200,
                    "text": "We will send the proposal tomorrow.",
                    "confidence": 0.9,
                },
                {
                    "id": "echo",
                    "source": "meeting",
                    "speakerId": "remote-1",
                    "startMs": 1050,
                    "endMs": 3150,
                    "text": "We will send the proposal tomorrow",
                    "confidence": 0.95,
                },
            ]
        )

        self.assertEqual([segment["id"] for segment in result], ["local"])

    def test_silence_returns_no_fabricated_segments(self) -> None:
        self.assertEqual(build_transcript(), [])


if __name__ == "__main__":
    unittest.main()
