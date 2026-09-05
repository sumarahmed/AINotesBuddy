from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notesbuddy_transcription import cpu_threads


class ResolveThreadCountTests(unittest.TestCase):
    def test_defaults_to_cpu_count(self) -> None:
        with patch.dict(os.environ, {"NOTESBUDDY_DIARIZATION_CPU_THREADS": ""}, clear=False), patch(
            "os.cpu_count", return_value=6
        ):
            self.assertEqual(cpu_threads.resolve_thread_count(), 6)

    def test_falls_back_to_four_when_cpu_count_is_unknown(self) -> None:
        with patch.dict(os.environ, {"NOTESBUDDY_DIARIZATION_CPU_THREADS": ""}, clear=False), patch(
            "os.cpu_count", return_value=None
        ):
            self.assertEqual(cpu_threads.resolve_thread_count(), 4)

    def test_env_override_takes_precedence(self) -> None:
        with patch.dict(
            os.environ, {"NOTESBUDDY_DIARIZATION_CPU_THREADS": "3"}, clear=False
        ):
            self.assertEqual(cpu_threads.resolve_thread_count(), 3)

    def test_invalid_env_override_falls_back_to_cpu_count(self) -> None:
        with patch.dict(
            os.environ, {"NOTESBUDDY_DIARIZATION_CPU_THREADS": "not-a-number"}, clear=False
        ), patch("os.cpu_count", return_value=8):
            self.assertEqual(cpu_threads.resolve_thread_count(), 8)

    def test_zero_or_negative_env_override_is_clamped_to_one(self) -> None:
        with patch.dict(
            os.environ, {"NOTESBUDDY_DIARIZATION_CPU_THREADS": "0"}, clear=False
        ):
            self.assertEqual(cpu_threads.resolve_thread_count(), 1)


class ApplyEnvDefaultsTests(unittest.TestCase):
    def test_sets_omp_and_mkl_when_unset(self) -> None:
        environment = {"NOTESBUDDY_DIARIZATION_CPU_THREADS": "5"}
        with patch.dict(os.environ, environment, clear=True):
            threads = cpu_threads.apply_env_defaults()
            self.assertEqual(threads, 5)
            self.assertEqual(os.environ["OMP_NUM_THREADS"], "5")
            self.assertEqual(os.environ["MKL_NUM_THREADS"], "5")

    def test_does_not_override_an_existing_value(self) -> None:
        environment = {
            "NOTESBUDDY_DIARIZATION_CPU_THREADS": "5",
            "OMP_NUM_THREADS": "2",
        }
        with patch.dict(os.environ, environment, clear=True):
            cpu_threads.apply_env_defaults()
            self.assertEqual(os.environ["OMP_NUM_THREADS"], "2")


class ConfigureTorchTests(unittest.TestCase):
    def test_sets_thread_counts_and_logs(self) -> None:
        calls: list[tuple[str, object]] = []
        fake_torch = SimpleNamespace(
            set_num_threads=lambda n: calls.append(("threads", n)),
            set_num_interop_threads=lambda n: calls.append(("interop", n)),
        )
        with patch.dict(
            os.environ, {"NOTESBUDDY_DIARIZATION_CPU_THREADS": "7"}, clear=False
        ), patch("notesbuddy_transcription.diagnostics.log_diagnostic") as log:
            threads = cpu_threads.configure_torch(fake_torch)

        self.assertEqual(threads, 7)
        self.assertEqual(calls, [("threads", 7), ("interop", 1)])
        log.assert_called_once()
        self.assertIn("7", log.call_args.args[0])

    def test_a_second_interop_call_in_the_same_process_is_swallowed(self) -> None:
        def _raise_already_set(_n: int) -> None:
            raise RuntimeError("cannot set number of interop threads after parallel work has started")

        fake_torch = SimpleNamespace(
            set_num_threads=lambda _n: None,
            set_num_interop_threads=_raise_already_set,
        )
        with patch.dict(
            os.environ, {"NOTESBUDDY_DIARIZATION_CPU_THREADS": "2"}, clear=False
        ):
            threads = cpu_threads.configure_torch(fake_torch, log=False)
        self.assertEqual(threads, 2)

    def test_log_false_suppresses_diagnostic_logging(self) -> None:
        fake_torch = SimpleNamespace(
            set_num_threads=lambda _n: None,
            set_num_interop_threads=lambda _n: None,
        )
        with patch.dict(
            os.environ, {"NOTESBUDDY_DIARIZATION_CPU_THREADS": "2"}, clear=False
        ), patch("notesbuddy_transcription.diagnostics.log_diagnostic") as log:
            cpu_threads.configure_torch(fake_torch, log=False)
        log.assert_not_called()


if __name__ == "__main__":
    unittest.main()
