from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notesbuddy_transcription import engine as engine_module
from notesbuddy_transcription.engine import (
    LocalDiarizationEngine,
    activate_optional_gpu_runtime,
    local_accelerator,
)

# engine.process() logs to the real companion log file
# (%LOCALAPPDATA%\NotesBuddy\logs\companion.log) by default -- confirmed to
# actually happen after a real log tail handed back to diagnose an empty
# transcript turned out to be this test suite's own previous run. Redirect
# it for the whole module.
_log_dir_handle: tempfile.TemporaryDirectory | None = None
_previous_log_dir: str | None = None


def setUpModule() -> None:
    global _log_dir_handle, _previous_log_dir
    _previous_log_dir = os.environ.get("NOTESBUDDY_LOG_DIR")
    _log_dir_handle = tempfile.TemporaryDirectory()
    os.environ["NOTESBUDDY_LOG_DIR"] = _log_dir_handle.name


def tearDownModule() -> None:
    if _previous_log_dir is None:
        os.environ.pop("NOTESBUDDY_LOG_DIR", None)
    else:
        os.environ["NOTESBUDDY_LOG_DIR"] = _previous_log_dir
    if _log_dir_handle is not None:
        _log_dir_handle.cleanup()


class FakeWhisper:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def transcribe(self, path, *, word_timestamps, vad_filter, beam_size):
        self.calls.append(Path(path).name)
        self.last_options = (word_timestamps, vad_filter, beam_size)
        if "microphone" in str(path):
            words = [
                SimpleNamespace(
                    start=0.0,
                    end=0.3,
                    word="I",
                    probability=0.98,
                ),
                SimpleNamespace(
                    start=0.31,
                    end=0.7,
                    word="agree.",
                    probability=0.96,
                ),
                SimpleNamespace(
                    start=1.05,
                    end=1.35,
                    word="Remote",
                    probability=0.9,
                ),
                SimpleNamespace(
                    start=1.36,
                    end=1.72,
                    word="one.",
                    probability=0.89,
                ),
            ]
        else:
            words = [
                SimpleNamespace(
                    start=1.0,
                    end=1.3,
                    word="Remote",
                    probability=0.94,
                ),
                SimpleNamespace(
                    start=1.31,
                    end=1.7,
                    word="one.",
                    probability=0.92,
                ),
                SimpleNamespace(
                    start=2.0,
                    end=2.3,
                    word="Remote",
                    probability=0.93,
                ),
                SimpleNamespace(
                    start=2.31,
                    end=2.7,
                    word="two.",
                    probability=0.91,
                ),
            ]
        segments = [
            SimpleNamespace(
                start=words[0].start,
                end=words[-1].end,
                text=" ".join(word.word for word in words),
                words=words,
            )
        ]
        return segments, SimpleNamespace(language="en")


class BundledModelConfigurationTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows DLL search path behavior")
    def test_optional_gpu_runtime_is_added_to_the_process_dll_search_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            for filename in ("cublas64_12.dll", "cudnn64_9.dll"):
                (runtime / filename).touch()
            previous_handles = list(engine_module._DLL_DIRECTORY_HANDLES)
            engine_module._DLL_DIRECTORY_HANDLES.clear()
            try:
                with patch.dict(
                    "os.environ",
                    {"NOTESBUDDY_GPU_LIB_DIR": str(runtime), "PATH": "existing"},
                    clear=False,
                ), patch.object(os, "add_dll_directory", return_value=object()):
                    self.assertTrue(activate_optional_gpu_runtime())
                    self.assertEqual(
                        os.environ["PATH"].split(os.pathsep)[0],
                        str(runtime.resolve()),
                    )
            finally:
                engine_module._DLL_DIRECTORY_HANDLES[:] = previous_handles

    def test_automatic_device_uses_cuda_when_both_runtimes_see_the_gpu(self) -> None:
        fake_ctranslate = SimpleNamespace(get_cuda_device_count=lambda: 1)
        with patch.dict(
            "sys.modules",
            {"ctranslate2": fake_ctranslate},
        ):
            accelerator = local_accelerator("auto")
        self.assertEqual(accelerator["device"], "cuda")
        self.assertEqual(accelerator["name"], "NVIDIA GPU")

    def test_explicit_cpu_configuration_never_probes_cuda(self) -> None:
        accelerator = local_accelerator("cpu")
        self.assertEqual(accelerator["device"], "cpu")
        self.assertFalse(accelerator["available"])

    @unittest.skipUnless(os.name == "nt", "Windows optional GPU pack behavior")
    def test_missing_optional_nvidia_pack_does_not_select_unusable_cuda(self) -> None:
        fake_ctranslate = SimpleNamespace(get_cuda_device_count=lambda: 1)
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            "os.environ",
            {"NOTESBUDDY_GPU_LIB_DIR": str(Path(directory) / "missing")},
            clear=False,
        ), patch.dict("sys.modules", {"ctranslate2": fake_ctranslate}):
            accelerator = local_accelerator("auto")

        self.assertEqual(accelerator["device"], "cpu")
        self.assertIn("pack not installed", accelerator["name"])

    def test_automatic_cuda_initialization_safely_retries_on_cpu(self) -> None:
        attempts = []

        class FakeWhisperModel:
            def __init__(self, _model, *, device, compute_type):
                attempts.append((device, compute_type))
                if device == "cuda":
                    raise RuntimeError("CUDA runtime unavailable")

        engine = LocalDiarizationEngine(device="cpu")
        engine.requested_device = "auto"
        engine.device = "cuda"
        engine.compute_type = "float16"
        with patch.dict(
            "sys.modules",
            {"faster_whisper": SimpleNamespace(WhisperModel=FakeWhisperModel)},
        ):
            engine._load_whisper()
        self.assertEqual(attempts, [("cuda", "float16"), ("cpu", "int8")])
        self.assertEqual(engine.device, "cpu")
        self.assertIn("initialization failed", engine.accelerator["name"])

    def test_automatic_cuda_inference_failure_retries_once_on_cpu(self) -> None:
        attempts = []

        class FakeWhisperModel:
            def __init__(self, _model, *, device, compute_type):
                self.device = device
                attempts.append(("load", device, compute_type))

            def transcribe(self, *_args, **_kwargs):
                attempts.append(("transcribe", self.device))
                if self.device == "cuda":
                    raise RuntimeError("cublas64_12.dll is not found")
                return [], SimpleNamespace(language="en")

        engine = LocalDiarizationEngine(device="cpu")
        engine.requested_device = "auto"
        engine.device = "cuda"
        engine.compute_type = "float16"
        with patch.dict(
            "sys.modules",
            {"faster_whisper": SimpleNamespace(WhisperModel=FakeWhisperModel)},
        ):
            words, language = engine._transcribe(
                Path("audio.wav"),
                cancel_event=threading.Event(),
            )

        self.assertEqual(words, [])
        self.assertEqual(language, "en")
        self.assertEqual(
            attempts,
            [
                ("load", "cuda", "float16"),
                ("transcribe", "cuda"),
                ("load", "cpu", "int8"),
                ("transcribe", "cpu"),
            ],
        )
        self.assertEqual(engine.device, "cpu")
        self.assertIn("inference failed", engine.accelerator["name"])

    def test_bundled_models_are_preferred_without_a_user_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model_root = Path(directory)
            whisper = model_root / "faster-whisper-selected"
            diarization = model_root / "speaker-diarization-community-1"
            whisper.mkdir()
            diarization.mkdir()
            with patch.dict(
                "os.environ",
                {
                    "NOTESBUDDY_MODEL_DIR": str(model_root),
                    "HF_TOKEN": "",
                },
                clear=False,
            ):
                engine = LocalDiarizationEngine()

            self.assertEqual(
                Path(engine.whisper_model_name).resolve(),
                whisper.resolve(),
            )
            self.assertEqual(
                Path(engine.diarization_model_name).resolve(),
                diarization.resolve(),
            )
            self.assertEqual(engine.hugging_face_token, "")
            with patch(
                "notesbuddy_transcription.engine.module_available",
                return_value=True,
            ):
                status = engine.configuration_status()
            self.assertTrue(status["ready"])
            self.assertEqual(status["source"], "bundled")

    def test_reusable_speaker_worker_returns_local_turns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            worker = Path(directory) / "NotesBuddySpeakerWorker.exe"
            worker.touch()
            engine = LocalDiarizationEngine(device="cpu")
            engine.speaker_worker = worker

            class Process:
                returncode = 0

                def communicate(self, timeout=None):
                    del timeout
                    return ('{"status":"ok","turns":[{"start":1.25,"end":2.5,"speaker":"VOICE_1"}]}', "")

            with patch("notesbuddy_transcription.engine.subprocess.Popen", return_value=Process()):
                turns = engine._diarize_with_worker(Path("meeting.wav"), cancel_event=threading.Event())
            self.assertEqual([(turn.start_ms, turn.end_ms, turn.label) for turn in turns], [(1250, 2500, "VOICE_1")])

    def test_speaker_worker_drains_large_output_without_pipe_deadlock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            worker = Path(directory) / "NotesBuddySpeakerWorker.exe"
            worker.touch()
            engine = LocalDiarizationEngine(device="cpu")
            engine.speaker_worker = worker
            turn_count = 5_000
            child_code = (
                "import json,sys; "
                f"n={turn_count}; "
                "turns=[{'start':i,'end':i+0.5,'speaker':f'VOICE_{i%2}'} for i in range(n)]; "
                "sys.stdout.write(json.dumps({'status':'ok','turns':turns}))"
            )
            real_popen = subprocess.Popen

            def start_large_worker(_command, **options):
                return real_popen([sys.executable, "-c", child_code], **options)

            with patch(
                "notesbuddy_transcription.engine.subprocess.Popen",
                side_effect=start_large_worker,
            ):
                turns = engine._diarize_with_worker(
                    Path("meeting.wav"),
                    cancel_event=threading.Event(),
                )

            self.assertEqual(len(turns), turn_count)
            self.assertEqual(turns[-1].label, "VOICE_1")


class FakeTurn:
    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end


class FakeAnnotation:
    def itertracks(self, *, yield_label):
        assert yield_label is True
        yield FakeTurn(0.9, 1.8), "track-a", "VOICE_B"
        yield FakeTurn(1.9, 2.8), "track-b", "VOICE_A"


class FakeEmptyAnnotation:
    def __bool__(self):
        return False

    def itertracks(self, *, yield_label):
        assert yield_label is True
        return iter(())


class FakeDiarizationPipeline:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, audio):
        self.calls.append(audio["waveform"]["source"])
        assert audio["sample_rate"] == 16000
        return SimpleNamespace(
            exclusive_speaker_diarization=FakeAnnotation(),
        )


class LocalEngineAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.whisper = FakeWhisper()
        self.diarization = FakeDiarizationPipeline()
        self.engine = LocalDiarizationEngine(hugging_face_token="test-token")
        self.engine._whisper = self.whisper
        self.engine._diarization = self.diarization

    def _process(self, **kwargs):
        fake_soundfile = SimpleNamespace(
            read=lambda path, **_options: (
                SimpleNamespace(
                    T=SimpleNamespace(
                        copy=lambda: SimpleNamespace(source=Path(path).name)
                    )
                ),
                16000,
            )
        )
        fake_torch = SimpleNamespace(
            from_numpy=lambda samples: {"source": samples.source}
        )
        with patch.dict(
            "sys.modules",
            {
                "soundfile": fake_soundfile,
                "torch": fake_torch,
            },
        ):
            return self.engine.process(**kwargs)

    def test_dual_source_result_marks_you_and_orders_remote_ids(self) -> None:
        progress = []
        result = self._process(
            microphone_path=Path("microphone.webm"),
            meeting_path=Path("meeting.webm"),
            mixed_path=None,
            metadata={},
            cancel_event=threading.Event(),
            progress=lambda value, stage: progress.append((value, stage)),
        )

        self.assertEqual(result["language"], "en")
        self.assertEqual(
            [segment["speakerId"] for segment in result["segments"]],
            ["local-user", "remote-1", "remote-2"],
        )
        self.assertEqual(
            [segment["text"] for segment in result["segments"]],
            ["I agree.", "Remote one.", "Remote two."],
        )
        self.assertEqual(self.diarization.calls, ["meeting.webm"])
        self.assertEqual(progress[-1], (1.0, "completed"))

    def test_mixed_only_import_is_diarized_as_meeting_audio(self) -> None:
        result = self._process(
            microphone_path=None,
            meeting_path=None,
            mixed_path=Path("mixed.webm"),
            metadata={},
            cancel_event=threading.Event(),
            progress=lambda _value, _stage: None,
        )

        self.assertTrue(
            all(segment["source"] == "meeting" for segment in result["segments"])
        )
        self.assertEqual(self.diarization.calls, ["mixed.webm"])

    def test_mic_only_capture_does_not_diarize_duplicate_mixed_track(self) -> None:
        result = self._process(
            microphone_path=Path("microphone.webm"),
            meeting_path=None,
            mixed_path=Path("mixed.webm"),
            metadata={},
            cancel_event=threading.Event(),
            progress=lambda _value, _stage: None,
        )

        self.assertEqual(self.whisper.calls, ["microphone.webm"])
        self.assertEqual(self.diarization.calls, [])
        self.assertEqual(
            [segment["speakerId"] for segment in result["segments"]],
            ["local-user"],
        )

    def test_empty_pyannote_4_output_preserves_transcription(self) -> None:
        empty = FakeEmptyAnnotation()
        self.engine._diarization = lambda _audio: SimpleNamespace(
            exclusive_speaker_diarization=empty,
            speaker_diarization=empty,
        )

        result = self._process(
            microphone_path=None,
            meeting_path=Path("meeting.webm"),
            mixed_path=None,
            metadata={},
            cancel_event=threading.Event(),
            progress=lambda _value, _stage: None,
        )

        self.assertEqual(
            [segment["speakerId"] for segment in result["segments"]],
            ["remote-unknown"],
        )
        self.assertEqual(
            [segment["text"] for segment in result["segments"]],
            ["Remote one. Remote two."],
        )

    def test_regular_annotation_is_used_when_exclusive_is_unavailable(self) -> None:
        regular = FakeAnnotation()
        output = SimpleNamespace(
            exclusive_speaker_diarization=None,
            speaker_diarization=regular,
        )

        self.assertIs(self.engine._annotation_from_output(output), regular)

    def test_unsupported_diarization_wrapper_has_actionable_error(self) -> None:
        self.engine._diarization = lambda _audio: SimpleNamespace()

        with self.assertRaisesRegex(
            RuntimeError,
            "unsupported diarization result",
        ):
            self._process(
                microphone_path=None,
                meeting_path=Path("meeting.webm"),
                mixed_path=None,
                metadata={},
                cancel_event=threading.Event(),
                progress=lambda _value, _stage: None,
            )


if __name__ == "__main__":
    unittest.main()
