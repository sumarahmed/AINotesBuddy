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
    remove_microphone_echo_words,
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

    def test_residual_segment_deduplication_preserves_meeting_speaker(self) -> None:
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

        self.assertEqual([segment["id"] for segment in result], ["echo"])

    def test_removes_only_aligned_meeting_leakage_from_microphone(self) -> None:
        result = build_transcript(
            microphone_words=[
                Word(100, 350, "To"),
                Word(360, 650, "test"),
                Word(660, 980, "your"),
                Word(990, 1380, "call"),
                Word(1390, 1800, "quality."),
                Word(1900, 2200, "Alright,"),
                Word(2210, 2460, "I"),
                Word(2470, 2850, "am"),
                Word(2860, 3300, "recording."),
            ],
            meeting_words=[
                Word(180, 430, "To"),
                Word(440, 730, "test"),
                Word(740, 1060, "your"),
                Word(1070, 1460, "call"),
                Word(1470, 1880, "quality."),
            ],
            meeting_turns=[SpeakerTurn(0, 1900, "REMOTE")],
        )

        self.assertEqual(
            [(segment["speakerId"], segment["text"]) for segment in result],
            [
                ("remote-1", "To test your call quality."),
                ("local-user", "Alright, I am recording."),
            ],
        )

    def test_preserves_unmatched_local_words_inside_echo_phrase(self) -> None:
        result = remove_microphone_echo_words(
            [
                Word(1000, 1200, "Please"),
                Word(1210, 1350, "I"),
                Word(1360, 1600, "agree"),
                Word(1610, 1900, "review"),
            ],
            [
                Word(1050, 1250, "Please"),
                Word(1650, 1940, "review"),
            ],
        )

        self.assertEqual([word.text for word in result], ["I", "agree"])

    def test_aligns_minor_asr_variation_and_source_clock_offset(self) -> None:
        result = remove_microphone_echo_words(
            [
                Word(1900, 2350, "configured"),
                Word(2360, 2750, "Teams"),
                Word(3000, 3300, "Thanks"),
            ],
            [
                Word(1000, 1450, "configure"),
                Word(1460, 1850, "Teams"),
            ],
        )

        self.assertEqual([word.text for word in result], ["Thanks"])

    def test_does_not_remove_short_or_time_distant_coincidences(self) -> None:
        result = remove_microphone_echo_words(
            [
                Word(1000, 1200, "yes"),
                Word(5000, 5400, "deadline"),
            ],
            [
                Word(1050, 1250, "yes"),
                Word(1000, 1400, "deadline"),
            ],
        )

        self.assertEqual([word.text for word in result], ["yes", "deadline"])

    def test_requires_a_consistent_offset_across_the_matching_phrase(self) -> None:
        result = remove_microphone_echo_words(
            [
                Word(1000, 1300, "project"),
                Word(1400, 1800, "deadline"),
            ],
            [
                Word(0, 300, "project"),
                Word(2400, 2800, "deadline"),
            ],
        )

        self.assertEqual(
            [word.text for word in result],
            ["project", "deadline"],
        )

    def test_requires_matching_words_to_form_a_time_local_phrase(self) -> None:
        result = remove_microphone_echo_words(
            [
                Word(1000, 1300, "project"),
                Word(10_000, 10_400, "deadline"),
            ],
            [
                Word(1050, 1350, "project"),
                Word(10_050, 10_450, "deadline"),
            ],
        )

        self.assertEqual(
            [word.text for word in result],
            ["project", "deadline"],
        )

    def test_remote_speakers_remain_diarized_after_echo_cleanup(self) -> None:
        result = build_transcript(
            microphone_words=[
                Word(1050, 1350, "Remote"),
                Word(1360, 1650, "one."),
                Word(2000, 2300, "My"),
                Word(2310, 2700, "reply."),
            ],
            meeting_words=[
                Word(1000, 1300, "Remote"),
                Word(1310, 1600, "one."),
                Word(3000, 3400, "Second"),
                Word(3410, 3800, "voice."),
            ],
            meeting_turns=[
                SpeakerTurn(900, 1700, "VOICE_A"),
                SpeakerTurn(2900, 3900, "VOICE_B"),
            ],
        )

        self.assertEqual(
            [(segment["speakerId"], segment["text"]) for segment in result],
            [
                ("remote-1", "Remote one."),
                ("local-user", "My reply."),
                ("remote-2", "Second voice."),
            ],
        )

    def test_silence_returns_no_fabricated_segments(self) -> None:
        self.assertEqual(build_transcript(), [])


if __name__ == "__main__":
    unittest.main()
