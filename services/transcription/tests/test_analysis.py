from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notesbuddy_transcription.analysis import (  # noqa: E402
    ExtractiveMeetingAnalyzer,
    LlamaCppMeetingAnalyzer,
    LocalAnalysisRouter,
    MeetingAnalysisUnavailable,
    _repair_summary_from_grounded_items,
    _transcript_chunks,
    normalise_analysis,
    prepare_transcript_segments,
)


class LlamaCppMeetingAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        # _generate_and_normalise() logs every generation outcome to
        # %LOCALAPPDATA%\NotesBuddy\logs\companion.log for live diagnosis of
        # the packaged companion; point it at a throwaway directory here so
        # running this suite does not write to the real machine's log.
        self._log_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._log_dir.cleanup)
        env_patch = patch.dict(os.environ, {"NOTESBUDDY_LOG_DIR": self._log_dir.name})
        env_patch.start()
        self.addCleanup(env_patch.stop)

    def test_generates_synthesised_grounded_analysis_from_text_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "llama-cli.exe"
            model = Path(directory) / "summary.gguf"
            runtime.touch()
            model.touch()
            analyzer = LlamaCppMeetingAnalyzer(
                runtime_path=runtime,
                model_path=model,
            )
            generated = {
                "shortSummary": "The team reviewed invoice monitoring and agreed to validate failed documents.",
                "summaryEvidenceSegmentIds": ["S0001", "S0002"],
                "highlights": [
                    {
                        "text": "The monitoring view shows failed invoices and SLA status.",
                        "evidenceSegmentIds": ["S0001"],
                    }
                ],
                "decisions": [
                    {
                        "decision": "Validate the failed invoice examples.",
                        "context": "The examples are required by operations.",
                        "owner": "Not specified",
                        "evidenceSegmentIds": ["S0002"],
                    }
                ],
                "actionItems": [
                    {
                        "task": "Send the failed invoice results.",
                        "owner": "Presenter",
                        "dueDate": "Friday",
                        "priority": "Medium",
                        "notes": "Not specified",
                        "evidenceSegmentIds": ["S0002"],
                    }
                ],
            }
            completed = type(
                "Completed", (), {"returncode": 0, "stdout": json.dumps(generated), "stderr": ""}
            )()
            segments = [
                {
                    "id": "monitoring",
                    "speaker": "Presenter",
                    "text": "The monitoring view shows failed invoices and SLA status.",
                },
                {
                    "id": "agreement",
                    "speaker": "Presenter",
                    "text": "We agreed to validate the failed invoice examples because operations requires them, and I will send the failed invoice results by Friday.",
                },
            ]

            with patch("notesbuddy_transcription.analysis.subprocess.run", return_value=completed) as run:
                result = analyzer.analyze(segments=segments, meeting_title="Invoice review")

            command = run.call_args.args[0]
            self.assertIn("--json-schema-file", command)
            self.assertNotIn("audio", " ".join(command).lower())
            self.assertIn("reviewed invoice monitoring", result["shortSummary"])
            self.assertEqual(result["decisions"][0]["sourceSegmentIds"], ["agreement"])
            self.assertEqual(result["actionItems"][0]["dueDate"], "Friday")

    def test_retries_with_a_larger_budget_after_a_truncated_response(self) -> None:
        # A real meeting with more distinct speakers than any transcript this
        # was tuned against truncated mid-JSON on its first attempt (the
        # fixed --predict budget ran out before the object closed) and was
        # reported as "malformed JSON" even though the model was still
        # producing good content. This confirms the one-time retry with a
        # doubled budget actually fires and succeeds instead of failing the
        # analysis outright.
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "llama-cli.exe"
            model = Path(directory) / "summary.gguf"
            runtime.touch()
            model.touch()
            analyzer = LlamaCppMeetingAnalyzer(
                runtime_path=runtime,
                model_path=model,
                output_tokens=2048,
            )
            generated = {
                "shortSummary": "The team reviewed invoice monitoring and agreed to validate failed documents.",
                "summaryEvidenceSegmentIds": ["S0001"],
                "highlights": [],
                "decisions": [],
                "actionItems": [],
            }
            truncated = type(
                "Completed", (), {"returncode": 0, "stdout": '{"shortSummary": "cut off mid', "stderr": ""}
            )()
            valid = type(
                "Completed", (), {"returncode": 0, "stdout": json.dumps(generated), "stderr": ""}
            )()
            segments = [
                {
                    "id": "S0001",
                    "speaker": "Presenter",
                    "text": "The monitoring view shows failed invoices and SLA status.",
                },
            ]

            with patch(
                "notesbuddy_transcription.analysis.subprocess.run",
                side_effect=[truncated, valid],
            ) as run:
                result = analyzer.analyze(segments=segments, meeting_title="Invoice review")

            self.assertEqual(run.call_count, 2)
            first_predict = run.call_args_list[0].args[0][
                run.call_args_list[0].args[0].index("--predict") + 1
            ]
            second_predict = run.call_args_list[1].args[0][
                run.call_args_list[1].args[0].index("--predict") + 1
            ]
            self.assertEqual(first_predict, "2048")
            self.assertEqual(second_predict, "4096")
            self.assertIn("reviewed invoice monitoring", result["shortSummary"])

    def test_retries_with_reinforcement_before_falling_back_to_concatenation(self) -> None:
        # A real result had a well-formed-looking shortSummary reduced to
        # two highlight titles glued together with a period ("Technical
        # Constraints and Timeframe. Discovery Phase Documentation
        # Requirements.") because the model's own summary failed grounding
        # and the old code fell straight back to concatenating structured
        # field text, which reads as labels, not prose. This confirms a
        # capable model gets a second, reinforced attempt first.
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "llama-cli.exe"
            model = Path(directory) / "summary.gguf"
            runtime.touch()
            model.touch()
            analyzer = LlamaCppMeetingAnalyzer(runtime_path=runtime, model_path=model)
            ungrounded = {
                "shortSummary": "A launch was completed in Europe.",
                "summaryEvidenceSegmentIds": ["S0001"],
                "highlights": [
                    {
                        "text": "The revised scope fits the customer's budget.",
                        "evidenceSegmentIds": ["S0001"],
                    }
                ],
                "decisions": [],
                "actionItems": [],
            }
            grounded = {
                "shortSummary": "The team reviewed the revised scope and confirmed it fits the customer's budget.",
                "summaryEvidenceSegmentIds": ["S0001"],
                "highlights": [
                    {
                        "text": "The revised scope fits the customer's budget.",
                        "evidenceSegmentIds": ["S0001"],
                    }
                ],
                "decisions": [],
                "actionItems": [],
            }
            first = type(
                "Completed", (), {"returncode": 0, "stdout": json.dumps(ungrounded), "stderr": ""}
            )()
            second = type(
                "Completed", (), {"returncode": 0, "stdout": json.dumps(grounded), "stderr": ""}
            )()
            segments = [
                {
                    "id": "S0001",
                    "speaker": "Presenter",
                    "text": "The revised scope fits the customer's budget.",
                },
            ]

            responses = iter([first, second])
            captured_prompts: list[str] = []

            def fake_run(command, **_kwargs):
                prompt_path = Path(command[command.index("--file") + 1])
                captured_prompts.append(prompt_path.read_text(encoding="utf-8"))
                return next(responses)

            with patch(
                "notesbuddy_transcription.analysis.subprocess.run",
                side_effect=fake_run,
            ) as run:
                result = analyzer.analyze(segments=segments, meeting_title="Scope review")

            self.assertEqual(run.call_count, 2)
            self.assertIn("used wording not found", captured_prompts[1].lower())
            self.assertEqual(
                result["shortSummary"],
                "The team reviewed the revised scope and confirmed it fits the customer's budget.",
            )

    def test_merge_trusts_already_grounded_partial_summaries_over_repair(self) -> None:
        # A real multi-chunk meeting had every chunk analyse cleanly on its
        # own (each shortSummary individually passed grounding), but the
        # merge step's own re-check of the *concatenated* summary against
        # the combined evidence failed anyway, and merge fell back to
        # _repair_summary_from_grounded_items -- producing the exact same
        # "Technical Constraints and Timeframe. Discovery Phase
        # Documentation Requirements." title-concatenation bug the
        # reinforcement retry was supposed to have fixed, because that
        # retry only covered the per-chunk path, not this separate one.
        # Merge should trust the partials' own already-validated summaries
        # instead of re-deriving from highlight/decision/action text.
        prepared = prepare_transcript_segments(
            [
                {"id": "a", "speaker": "Jordan", "text": "We agreed to launch on time."},
                {
                    "id": "b",
                    "speaker": "Sam",
                    "text": "The team confirmed the budget is fixed at ten thousand.",
                },
            ]
        )
        partial_one = {
            "shortSummary": "We agreed to launch on time.",
            "summaryEvidenceSegmentIds": ["S0001"],
            "highlights": [
                {"text": "Launch date confirmed.", "evidenceSegmentIds": ["S0001"]}
            ],
            "decisions": [],
            "actionItems": [],
        }
        # This chunk's own shortSummary already passed its own per-chunk
        # grounding check in production; the "47" here stands in for
        # wording that was valid against that chunk's evidence but is not
        # a literal number in the combined transcript, which is enough to
        # fail the merge's whole-text numbers-subset re-check.
        partial_two = {
            "shortSummary": "The team confirmed the budget is fixed at 47 dollars.",
            "summaryEvidenceSegmentIds": ["S0002"],
            "highlights": [
                {"text": "Budget review completed.", "evidenceSegmentIds": ["S0002"]}
            ],
            "decisions": [],
            "actionItems": [],
        }

        merged = LlamaCppMeetingAnalyzer._merge_partials(
            [partial_one, partial_two], prepared
        )

        self.assertEqual(
            merged["shortSummary"],
            "We agreed to launch on time. The team confirmed the budget is "
            "fixed at 47 dollars.",
        )
        self.assertNotIn("Launch date confirmed", merged["shortSummary"])
        self.assertNotIn("Budget review completed", merged["shortSummary"])

    def test_router_reports_missing_optional_component_instead_of_extractive_summary(self) -> None:
        with patch.dict("os.environ", {
            "NOTESBUDDY_ANALYSIS_RUNTIME": "missing-runtime.exe",
            "NOTESBUDDY_ANALYSIS_MODEL_PATH": "missing-model.gguf",
        }):
            status = LocalAnalysisRouter().configuration_status()

        self.assertFalse(status["ready"])
        self.assertIn("Smart summary", status["status"])


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

    def test_repair_widens_candidate_pool_with_retry_fallback(self) -> None:
        raw = {
            "shortSummary": "Unsupported claim about Mars colonization.",
            "summaryEvidenceSegmentIds": ["S0001"],
            "highlights": [
                {
                    "text": "A completely unrelated claim not in the transcript.",
                    "evidenceSegmentIds": ["S0001"],
                }
            ],
            "decisions": [],
            "actionItems": [],
        }
        retry_raw = {
            "shortSummary": "Also unsupported.",
            "summaryEvidenceSegmentIds": ["S0002"],
            "highlights": [],
            "decisions": [],
            "actionItems": [
                {
                    "task": (
                        "Jordan will urgently send the revised proposal by "
                        "Friday after finance confirms the total."
                    ),
                    "owner": "Jordan",
                    "dueDate": "Friday",
                    "priority": "High",
                    "notes": "Not specified",
                    "evidenceSegmentIds": ["S0002"],
                }
            ],
        }

        repaired = _repair_summary_from_grounded_items(
            raw, self.prepared, retry_raw
        )
        result = normalise_analysis(repaired, self.prepared)

        self.assertEqual(
            result["shortSummary"],
            "Jordan will urgently send the revised proposal by Friday after "
            "finance confirms the total.",
        )
        self.assertEqual(result["summaryEvidenceSegmentIds"], ["S0002"])

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


class ExtractiveMeetingAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = ExtractiveMeetingAnalyzer()
        self.segments = [
            {
                "id": "remote-intro",
                "speaker": "Speaker 1",
                "timestamp": "00:00",
                "text": "Welcome to the project review.",
            },
            {
                "id": "local-action",
                "speaker": "Syed Ahmed",
                "timestamp": "00:01",
                "text": (
                    "I will document the confirmed decision and send the "
                    "testing checklist to the team by Friday."
                ),
            },
            {
                "id": "remote-need",
                "speaker": "Speaker 1",
                "timestamp": "00:03",
                "text": "We need to finish the ingestion channel before Thursday.",
            },
            {
                "id": "remote-proposal",
                "speaker": "Speaker 1",
                "timestamp": "00:07",
                "text": "I recommend assigning the configuration work to Alex.",
            },
            {
                "id": "remote-agreement",
                "speaker": "Speaker 2",
                "timestamp": "00:11",
                "text": "I agree.",
            },
            {
                "id": "alex-action",
                "speaker": "Speaker 2",
                "timestamp": "00:12",
                "text": "Alex will complete the ingestion configuration by Thursday.",
            },
            {
                "id": "jordan-action",
                "speaker": "Speaker 2",
                "timestamp": "00:17",
                "text": "Jordan will validate the email workflow on Friday.",
            },
        ]

    def test_builds_grounded_sections_without_a_network_model(self) -> None:
        result = self.analyzer.analyze(
            segments=self.segments,
            meeting_title="Project review",
        )

        self.assertEqual(result["model"], "notesbuddy-local-extractive-v1")
        self.assertLess(len(result["shortSummary"].split()), 300)
        self.assertTrue(result["summarySourceSegmentIds"])
        self.assertGreaterEqual(len(result["highlights"]), 3)
        self.assertEqual(len(result["decisions"]), 1)
        self.assertIn("configuration work to Alex", result["decisions"][0]["decision"])
        self.assertEqual(
            result["decisions"][0]["sourceSegmentIds"],
            ["remote-proposal", "remote-agreement"],
        )

        actions = {item["owner"]: item for item in result["actionItems"]}
        self.assertEqual(actions["Syed Ahmed"]["dueDate"], "Friday")
        self.assertEqual(actions["Alex"]["dueDate"], "Thursday")
        self.assertEqual(actions["Jordan"]["dueDate"], "Friday")
        self.assertEqual(actions["Not specified"]["dueDate"], "Before Thursday")
        self.assertTrue(
            all(item["sourceSegmentIds"] for item in result["actionItems"])
        )

    def test_maps_companion_speaker_ids_when_labels_are_not_supplied(self) -> None:
        result = self.analyzer.analyze(
            segments=[
                {
                    "id": "local-action",
                    "speakerId": "local-user",
                    "text": "I will send the checklist by Friday.",
                },
                {
                    "id": "remote-proposal",
                    "speakerId": "remote-1",
                    "text": "I recommend assigning the configuration work to Alex.",
                },
                {
                    "id": "remote-agreement",
                    "speakerId": "remote-2",
                    "text": "I agree.",
                },
            ],
            meeting_title="Project review",
        )

        self.assertEqual(result["actionItems"][0]["owner"], "You")
        self.assertEqual(
            result["decisions"][0]["decision"],
            "Assign the configuration work to Alex.",
        )

    def test_does_not_turn_an_unconfirmed_proposal_into_a_decision(self) -> None:
        result = self.analyzer.analyze(
            segments=[
                {
                    "id": "proposal-only",
                    "speaker": "Sam",
                    "text": "I recommend moving the launch to September.",
                },
                {
                    "id": "open-question",
                    "speaker": "Jordan",
                    "text": "We still need to decide after reviewing the budget.",
                },
            ]
        )

        self.assertEqual(result["decisions"], [])
        self.assertEqual(result["actionItems"], [])

    def test_configuration_is_ready_without_optional_model_environment(self) -> None:
        status = self.analyzer.configuration_status()

        self.assertTrue(status["ready"])
        self.assertEqual(status["model"], "notesbuddy-local-extractive-v1")


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
