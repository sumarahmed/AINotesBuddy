from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notesbuddy_transcription.analysis import (  # noqa: E402
    MeetingAnalysisUnavailable,
    _repair_summary_from_grounded_items,
    _transcript_chunks,
    normalise_analysis,
    prepare_transcript_segments,
)


class WordTokenizer:
    def encode(self, text: str, *, add_special_tokens: bool = False) -> list[str]:
        del add_special_tokens
        return text.split()

    def decode(
        self,
        tokens: list[str],
        *,
        skip_special_tokens: bool = True,
    ) -> str:
        del skip_special_tokens
        return " ".join(tokens)


class MeetingAnalysisValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prepared = prepare_transcript_segments(
            [
                {
                    "id": "confirmed-decision",
                    "speaker": "Jordan Lee",
                    "timestamp": "00:12",
                    "text": (
                        "We agreed to use the revised scope because it fits the "
                        "customer's budget."
                    ),
                },
                {
                    "id": "confirmed-action",
                    "speaker": "Jordan Lee",
                    "timestamp": "00:26",
                    "text": (
                        "Jordan will urgently send the revised proposal by Friday "
                        "after finance confirms the total."
                    ),
                },
                {
                    "id": "open-question",
                    "speaker": "Sam",
                    "timestamp": "00:41",
                    "text": "Maybe we should use the archive, but we still need to decide.",
                },
                {
                    "id": "unassigned-team-action",
                    "speaker": "CFO",
                    "timestamp": "00:55",
                    "text": "We need to update the budget forecast by next Tuesday.",
                },
            ]
        )

    def test_requires_summary_evidence(self) -> None:
        with self.assertRaises(MeetingAnalysisUnavailable):
            normalise_analysis(
                {
                    "shortSummary": "A plausible but unsupported summary.",
                    "summaryEvidenceSegmentIds": [],
                },
                self.prepared,
            )

    def test_expands_incomplete_but_valid_summary_evidence(self) -> None:
        result = normalise_analysis(
            {
                "shortSummary": (
                    "Jordan will urgently send the proposal after finance confirms "
                    "the total."
                ),
                "summaryEvidenceSegmentIds": ["S0001"],
                "highlights": [],
                "decisions": [],
                "actionItems": [],
            },
            self.prepared,
        )

        self.assertEqual(result["summaryEvidenceSegmentIds"], ["S0001", "S0002"])

    def test_repairs_unverifiable_summary_from_grounded_findings(self) -> None:
        raw = {
            "shortSummary": "A launch was completed in Europe.",
            "summaryEvidenceSegmentIds": ["S0001"],
            "highlights": [
                {
                    "text": "The revised scope fits the customer's budget.",
                    "evidenceSegmentIds": ["S0001"],
                }
            ],
            "decisions": [
                {
                    "decision": "Use the revised scope.",
                    "context": "It fits the customer's budget.",
                    "owner": "Not specified",
                    "evidenceSegmentIds": ["S0001"],
                }
            ],
            "actionItems": [],
        }

        repaired = _repair_summary_from_grounded_items(raw, self.prepared)
        result = normalise_analysis(repaired, self.prepared)

        self.assertEqual(
            result["shortSummary"],
            "The revised scope fits the customer's budget.",
        )
        self.assertEqual(result["summaryEvidenceSegmentIds"], ["S0001"])

    def test_validates_decisions_actions_owners_dates_and_priority(self) -> None:
        result = normalise_analysis(
            {
                "shortSummary": (
                    "The team confirmed the revised scope.\n\n"
                    "Jordan will send the proposal after finance follows up."
                ),
                "summaryEvidenceSegmentIds": ["S0001", "S0002"],
                "highlights": [
                    {
                        "text": "The revised scope fits the customer's budget.",
                        "evidenceSegmentIds": ["S0001"],
                    },
                    {
                        "text": "The launch date moved to September 15.",
                        "evidenceSegmentIds": ["S0001"],
                    }
                ],
                "decisions": [
                    {
                        "decision": "Use the revised scope.",
                        "context": "It fits the customer's budget.",
                        "owner": "Invented Owner",
                        "evidenceSegmentIds": ["S0001"],
                    },
                    {
                        "decision": "Use the archive.",
                        "context": "It was discussed.",
                        "owner": "Sam",
                        "evidenceSegmentIds": ["S0003"],
                    },
                ],
                "actionItems": [
                    {
                        "task": "Send the revised proposal.",
                        "owner": "Jordan Lee",
                        "dueDate": "Friday",
                        "priority": "High",
                        "notes": "Finance must confirm the total first.",
                        "evidenceSegmentIds": ["S0002"],
                    },
                    {
                        "task": "Book a launch meeting.",
                        "owner": "Jordan Lee",
                        "dueDate": "Monday",
                        "priority": "High",
                        "notes": "Not specified",
                        "evidenceSegmentIds": ["S0001"],
                    },
                    {
                        "task": "Launch the production migration.",
                        "owner": "Jordan Lee",
                        "dueDate": "Friday",
                        "priority": "High",
                        "notes": "The migration is blocked by security approval.",
                        "evidenceSegmentIds": ["S0002"],
                    },
                    {
                        "task": "Finance must confirm the total by Thursday.",
                        "owner": "Finance",
                        "dueDate": "Thursday",
                        "priority": "Medium",
                        "notes": "Not specified",
                        "evidenceSegmentIds": ["S0002"],
                    },
                    {
                        "task": "Update the budget forecast.",
                        "owner": "CFO",
                        "dueDate": "Next Tuesday",
                        "priority": "Medium",
                        "notes": "Not specified",
                        "evidenceSegmentIds": ["S0004"],
                    },
                ],
            },
            self.prepared,
        )

        self.assertIn("\n\n", result["shortSummary"])
        self.assertEqual(len(result["highlights"]), 1)
        self.assertEqual(len(result["decisions"]), 1)
        self.assertEqual(result["decisions"][0]["owner"], "Not specified")
        self.assertEqual(len(result["actionItems"]), 2)
        action = result["actionItems"][0]
        self.assertEqual(action["owner"], "Jordan Lee")
        self.assertEqual(action["dueDate"], "Friday")
        self.assertEqual(action["priority"], "High")
        self.assertEqual(result["actionItems"][1]["owner"], "Not specified")

    def test_resets_unsupported_owner_date_and_priority(self) -> None:
        result = normalise_analysis(
            {
                "shortSummary": "Jordan committed to send the proposal.",
                "summaryEvidenceSegmentIds": ["S0002"],
                "highlights": [],
                "decisions": [],
                "actionItems": [
                    {
                        "task": "Send the revised proposal.",
                        "owner": "Taylor",
                        "dueDate": "Monday",
                        "priority": "Low",
                        "notes": "Not specified",
                        "evidenceSegmentIds": ["S0002"],
                    }
                ],
            },
            self.prepared,
        )

        action = result["actionItems"][0]
        self.assertEqual(action["owner"], "Not specified")
        self.assertEqual(action["dueDate"], "Not specified")
        self.assertEqual(action["priority"], "Medium")


class MeetingAnalysisChunkingTests(unittest.TestCase):
    def test_long_transcripts_are_split_by_model_tokens(self) -> None:
        prepared = prepare_transcript_segments(
            [
                {
                    "id": f"segment-{index}",
                    "speaker": "Speaker",
                    "timestamp": f"00:{index:02d}",
                    "text": " ".join(f"word{item}" for item in range(45)),
                }
                for index in range(5)
            ]
        )
        tokenizer = WordTokenizer()

        chunks = _transcript_chunks(prepared, tokenizer, maximum_tokens=70)

        self.assertGreater(len(chunks), 1)
        self.assertEqual(
            [item["id"] for chunk in chunks for item in chunk],
            [item["id"] for item in prepared],
        )
        for chunk in chunks:
            rendered = "\n".join(
                f"[{item['id']} | {item['timestamp']} | {item['speaker']}] "
                f"{item['text']}"
                for item in chunk
            )
            self.assertLessEqual(len(tokenizer.encode(rendered)), 70)

    def test_one_oversized_segment_is_split_without_losing_its_id(self) -> None:
        prepared = prepare_transcript_segments(
            [
                {
                    "id": "long-segment",
                    "speaker": "Speaker",
                    "timestamp": "01:00",
                    "text": " ".join(f"word{item}" for item in range(180)),
                }
            ]
        )
        tokenizer = WordTokenizer()

        chunks = _transcript_chunks(prepared, tokenizer, maximum_tokens=70)
        parts = [item for chunk in chunks for item in chunk]

        self.assertGreater(len(parts), 1)
        self.assertTrue(all(item["id"] == "S0001" for item in parts))
        self.assertEqual(
            " ".join(item["text"] for item in parts),
            prepared[0]["text"],
        )


if __name__ == "__main__":
    unittest.main()
