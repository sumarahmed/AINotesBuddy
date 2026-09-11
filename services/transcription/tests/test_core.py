from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notesbuddy_transcription.core import Word, build_transcript


class BuildTranscriptTests(unittest.TestCase):
    def test_silence_returns_no_fabricated_segments(self) -> None:
        self.assertEqual(build_transcript([]), [])

    def test_collapses_adjacent_words_into_one_segment(self) -> None:
        result = build_transcript(
            [
                Word(0, 200, "Good", 0.9),
                Word(210, 500, "morning", 0.8),
                Word(520, 800, "everyone.", 0.95),
            ]
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "Good morning everyone.")
        self.assertEqual(result[0]["startMs"], 0)
        self.assertEqual(result[0]["endMs"], 800)
        self.assertNotIn("speakerId", result[0])
        self.assertNotIn("speakerLabel", result[0])
        self.assertNotIn("source", result[0])
        self.assertAlmostEqual(result[0]["confidence"], round((0.9 + 0.8 + 0.95) / 3, 4))

    def test_splits_on_pause_gap(self) -> None:
        result = build_transcript(
            [
                Word(0, 200, "First"),
                Word(210, 500, "sentence."),
                # Gap of 950ms > the 900ms default threshold.
                Word(1450, 1700, "Second"),
                Word(1710, 2000, "sentence."),
            ]
        )

        self.assertEqual([segment["text"] for segment in result], [
            "First sentence.",
            "Second sentence.",
        ])

    def test_does_not_split_within_the_gap_threshold(self) -> None:
        result = build_transcript(
            [
                Word(0, 200, "First"),
                # Gap of exactly 900ms should still collapse into one segment.
                Word(1100, 1300, "part."),
            ]
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "First part.")

    def test_splits_after_maximum_word_count(self) -> None:
        words = [
            Word(index * 100, index * 100 + 90, f"word{index}")
            for index in range(45)
        ]

        result = build_transcript(words)

        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]["text"].split()), 42)
        self.assertEqual(len(result[1]["text"].split()), 3)

    def test_sorts_out_of_order_words_by_start_time(self) -> None:
        result = build_transcript(
            [
                Word(500, 700, "second"),
                Word(0, 200, "first"),
            ]
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "first second")

    def test_blank_words_are_ignored(self) -> None:
        result = build_transcript(
            [
                Word(0, 200, "   "),
                Word(210, 400, "hello"),
            ]
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "hello")

    def test_missing_confidence_yields_none(self) -> None:
        result = build_transcript([Word(0, 200, "hello")])

        self.assertIsNone(result[0]["confidence"])

    def test_segment_ids_are_unique(self) -> None:
        result = build_transcript(
            [
                Word(0, 200, "one"),
                Word(1500, 1700, "two"),
            ]
        )

        ids = [segment["id"] for segment in result]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
