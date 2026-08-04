from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notesbuddy_transcription.analysis import (  # noqa: E402
    MeetingAnalysisUnavailable,
    normalise_analysis,
    prepare_transcript_segments,
)


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


if __name__ == "__main__":
    unittest.main()
