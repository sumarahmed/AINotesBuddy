from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import speaker_worker


class FakeAnnotation:
    def itertracks(self, yield_label: bool = True):
        yield SimpleNamespace(start=0.0, end=1.5), "track0", "SPEAKER_00"


def _fake_soundfile() -> SimpleNamespace:
    return SimpleNamespace(
        read=lambda *_a, **_k: (
            SimpleNamespace(T=SimpleNamespace(copy=lambda: "waveform")),
            16000,
        )
    )


class DiarizeTests(unittest.TestCase):
    def test_cpu_only_torch_configures_thread_counts_before_building_the_pipeline(
        self,
    ) -> None:
        calls: list[str] = []
        fake_torch = SimpleNamespace(
            cuda=SimpleNamespace(is_available=lambda: False),
            set_num_threads=lambda _n: calls.append("threads"),
            set_num_interop_threads=lambda _n: calls.append("interop"),
            from_numpy=lambda samples: samples,
        )

        class FakePipeline:
            @staticmethod
            def from_pretrained(_path):
                calls.append("pipeline-loaded")
                return lambda _audio: FakeAnnotation()

        with patch.dict(
            sys.modules,
            {
                "torch": fake_torch,
                "soundfile": _fake_soundfile(),
                "pyannote.audio": SimpleNamespace(Pipeline=FakePipeline),
            },
        ), patch("notesbuddy_transcription.diagnostics.log_diagnostic"):
            turns = speaker_worker.diarize(Path("meeting.wav"), Path("model"))

        # Thread configuration must happen before the pipeline is built, so a
        # slow pyannote load still benefits from the configured thread pool.
        self.assertEqual(calls, ["threads", "interop", "pipeline-loaded"])
        self.assertEqual(
            turns, [{"start": 0.0, "end": 1.5, "speaker": "SPEAKER_00"}]
        )

    def test_cuda_capable_torch_moves_the_pipeline_to_gpu_without_cpu_tuning(
        self,
    ) -> None:
        calls: list[str] = []
        fake_torch = SimpleNamespace(
            cuda=SimpleNamespace(is_available=lambda: True),
            device=lambda name: f"device:{name}",
            set_num_threads=lambda _n: calls.append("threads"),
            set_num_interop_threads=lambda _n: calls.append("interop"),
            from_numpy=lambda samples: samples,
        )

        class FakePipelineInstance:
            def to(self, device):
                calls.append(("to", device))
                return self

            def __call__(self, _audio):
                return FakeAnnotation()

        class FakePipeline:
            @staticmethod
            def from_pretrained(_path):
                calls.append("pipeline-loaded")
                return FakePipelineInstance()

        with patch.dict(
            sys.modules,
            {
                "torch": fake_torch,
                "soundfile": _fake_soundfile(),
                "pyannote.audio": SimpleNamespace(Pipeline=FakePipeline),
            },
        ), patch("notesbuddy_transcription.diagnostics.log_diagnostic"):
            turns = speaker_worker.diarize(Path("meeting.wav"), Path("model"))

        # No CPU thread tuning when moving to GPU -- only the pipeline load
        # and the device move happen.
        self.assertEqual(calls, ["pipeline-loaded", ("to", "device:cuda")])
        self.assertEqual(
            turns, [{"start": 0.0, "end": 1.5, "speaker": "SPEAKER_00"}]
        )

    def test_a_failed_gpu_move_falls_back_to_cpu_tuning(self) -> None:
        calls: list[str] = []
        fake_torch = SimpleNamespace(
            cuda=SimpleNamespace(is_available=lambda: True),
            device=lambda name: f"device:{name}",
            set_num_threads=lambda _n: calls.append("threads"),
            set_num_interop_threads=lambda _n: calls.append("interop"),
            from_numpy=lambda samples: samples,
        )

        class FakePipelineInstance:
            def to(self, _device):
                raise RuntimeError("CUDA runtime unavailable")

            def __call__(self, _audio):
                return FakeAnnotation()

        class FakePipeline:
            @staticmethod
            def from_pretrained(_path):
                calls.append("pipeline-loaded")
                return FakePipelineInstance()

        with patch.dict(
            sys.modules,
            {
                "torch": fake_torch,
                "soundfile": _fake_soundfile(),
                "pyannote.audio": SimpleNamespace(Pipeline=FakePipeline),
            },
        ), patch("notesbuddy_transcription.diagnostics.log_diagnostic"):
            turns = speaker_worker.diarize(Path("meeting.wav"), Path("model"))

        self.assertEqual(calls, ["pipeline-loaded", "threads", "interop"])
        self.assertEqual(
            turns, [{"start": 0.0, "end": 1.5, "speaker": "SPEAKER_00"}]
        )


if __name__ == "__main__":
    unittest.main()
