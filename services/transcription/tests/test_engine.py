from __future__ import annotations

import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notesbuddy_transcription import engine as engine_module
from notesbuddy_transcription.engine import (
    LocalTranscriptionEngine,
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
    """A fake faster-whisper model keyed by whatever `transcribe()` receives.

    A `str` source (a real file path, as used for the single-source case)
    is keyed by that string. A decoded ndarray (the mixed-audio case) is
    keyed by the fixed string "mixed" -- tests register expected words per
    key via `words_by_key` and can inspect `raw_calls` for the exact object
    (path string or ndarray) passed to `transcribe()`.
    """

    def __init__(self, words_by_key: dict[str, list] | None = None) -> None:
        self.words_by_key = words_by_key if words_by_key is not None else {}
        self.calls: list[str] = []
        self.raw_calls: list = []

    def transcribe(self, source, *, word_timestamps, vad_filter, beam_size):
        self.raw_calls.append(source)
        self.last_options = (word_timestamps, vad_filter, beam_size)
        key = source if isinstance(source, str) else "mixed"
        self.calls.append(key)
        words = self.words_by_key.get(key, [])
        segments = [
            SimpleNamespace(
                start=words[0].start if words else 0.0,
                end=words[-1].end if words else 0.0,
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

        engine = LocalTranscriptionEngine(device="cpu")
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

        engine = LocalTranscriptionEngine(device="cpu")
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

    def test_bundled_whisper_model_is_preferred(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model_root = Path(directory)
            whisper = model_root / "faster-whisper-selected"
            whisper.mkdir()
            with patch.dict(
                "os.environ",
                {"NOTESBUDDY_MODEL_DIR": str(model_root)},
                clear=False,
            ):
                engine = LocalTranscriptionEngine()

            self.assertEqual(
                Path(engine.whisper_model_name).resolve(),
                whisper.resolve(),
            )
            with patch(
                "notesbuddy_transcription.engine.module_available",
                return_value=True,
            ):
                status = engine.configuration_status()
            self.assertTrue(status["ready"])
            self.assertEqual(status["source"], "bundled")

    def test_configuration_status_has_no_diarization_fields(self) -> None:
        engine = LocalTranscriptionEngine(device="cpu")
        with patch(
            "notesbuddy_transcription.engine.module_available",
            return_value=True,
        ):
            status = engine.configuration_status()
        self.assertNotIn("diarizationDevice", status)
        self.assertNotIn("diarizationGpuAvailable", status)


class MixedAudioTests(unittest.TestCase):
    """Direct coverage of `_mixed_audio`'s pad/sum/clip arithmetic."""

    def test_pads_the_shorter_source_and_sums_sample_wise(self) -> None:
        decoded = {
            "a.wav": np.array([0.2, 0.2, 0.2], dtype=np.float32),
            "b.wav": np.array([0.3, 0.3], dtype=np.float32),
        }
        fake_audio_module = SimpleNamespace(
            decode_audio=lambda path, sampling_rate=16000: decoded[str(path)]
        )
        with patch.dict("sys.modules", {"faster_whisper.audio": fake_audio_module}):
            mixed = LocalTranscriptionEngine._mixed_audio(
                [Path("a.wav"), Path("b.wav")]
            )
        np.testing.assert_allclose(
            mixed, np.array([0.5, 0.5, 0.2], dtype=np.float32), atol=1e-6
        )

    def test_clips_a_sum_that_exceeds_full_scale(self) -> None:
        decoded = {
            "a.wav": np.array([1.0, -1.0], dtype=np.float32),
            "b.wav": np.array([1.0, -1.0], dtype=np.float32),
        }
        fake_audio_module = SimpleNamespace(
            decode_audio=lambda path, sampling_rate=16000: decoded[str(path)]
        )
        with patch.dict("sys.modules", {"faster_whisper.audio": fake_audio_module}):
            mixed = LocalTranscriptionEngine._mixed_audio(
                [Path("a.wav"), Path("b.wav")]
            )
        np.testing.assert_allclose(
            mixed, np.array([1.0, -1.0], dtype=np.float32), atol=1e-6
        )

    def test_mixes_three_sources(self) -> None:
        decoded = {
            "a.wav": np.array([0.1, 0.1, 0.1], dtype=np.float32),
            "b.wav": np.array([0.1, 0.1], dtype=np.float32),
            "c.wav": np.array([0.1], dtype=np.float32),
        }
        fake_audio_module = SimpleNamespace(
            decode_audio=lambda path, sampling_rate=16000: decoded[str(path)]
        )
        with patch.dict("sys.modules", {"faster_whisper.audio": fake_audio_module}):
            mixed = LocalTranscriptionEngine._mixed_audio(
                [Path("a.wav"), Path("b.wav"), Path("c.wav")]
            )
        np.testing.assert_allclose(
            mixed, np.array([0.3, 0.2, 0.1], dtype=np.float32), atol=1e-6
        )


class ProcessTests(unittest.TestCase):
    """Covers process()'s new contract: mix every provided source into one
    waveform (skipping the mixing arithmetic entirely for a single source)
    and transcribe once into a flat, speaker-agnostic transcript."""

    def setUp(self) -> None:
        self.words_by_key: dict[str, list] = {}
        self.whisper = FakeWhisper(self.words_by_key)
        self.engine = LocalTranscriptionEngine()
        self.engine._whisper = self.whisper

    def test_no_sources_returns_an_empty_result_without_calling_the_model(
        self,
    ) -> None:
        progress = []
        result = self.engine.process(
            microphone_path=None,
            meeting_path=None,
            mixed_path=None,
            metadata={},
            cancel_event=threading.Event(),
            progress=lambda value, stage: progress.append((value, stage)),
        )

        self.assertEqual(result, {"language": None, "segments": []})
        self.assertEqual(self.whisper.calls, [])
        self.assertEqual(progress[-1], (1.0, "completed"))

    def test_a_single_source_transcribes_directly_from_its_path(self) -> None:
        self.words_by_key["microphone.webm"] = [
            SimpleNamespace(start=0.0, end=0.3, word="I", probability=0.98),
            SimpleNamespace(start=0.31, end=0.7, word="agree.", probability=0.96),
        ]
        progress = []
        result = self.engine.process(
            microphone_path=Path("microphone.webm"),
            meeting_path=None,
            mixed_path=None,
            metadata={},
            cancel_event=threading.Event(),
            progress=lambda value, stage: progress.append((value, stage)),
        )

        # No mixing performed for a single source -- transcribed straight
        # from the file path (better quality, and the common case).
        self.assertEqual(self.whisper.calls, ["microphone.webm"])
        self.assertEqual(result["language"], "en")
        self.assertEqual(len(result["segments"]), 1)
        segment = result["segments"][0]
        self.assertEqual(segment["text"], "I agree.")
        self.assertNotIn("speakerId", segment)
        self.assertNotIn("speakerLabel", segment)
        self.assertNotIn("source", segment)
        self.assertNotIn("mixing audio sources", [stage for _value, stage in progress])
        self.assertEqual(progress[-1], (1.0, "completed"))

    def test_meeting_only_capture_transcribes_directly_too(self) -> None:
        self.words_by_key["meeting.webm"] = [
            SimpleNamespace(start=1.0, end=1.3, word="Remote", probability=0.9),
            SimpleNamespace(start=1.31, end=1.7, word="voice.", probability=0.88),
        ]
        result = self.engine.process(
            microphone_path=None,
            meeting_path=Path("meeting.webm"),
            mixed_path=None,
            metadata={},
            cancel_event=threading.Event(),
            progress=lambda _value, _stage: None,
        )

        self.assertEqual(self.whisper.calls, ["meeting.webm"])
        self.assertEqual(
            [segment["text"] for segment in result["segments"]], ["Remote voice."]
        )

    def test_mixed_only_import_transcribes_directly_too(self) -> None:
        self.words_by_key["mixed.webm"] = [
            SimpleNamespace(start=0.0, end=0.4, word="Imported.", probability=0.9),
        ]
        result = self.engine.process(
            microphone_path=None,
            meeting_path=None,
            mixed_path=Path("mixed.webm"),
            metadata={},
            cancel_event=threading.Event(),
            progress=lambda _value, _stage: None,
        )

        self.assertEqual(self.whisper.calls, ["mixed.webm"])
        self.assertEqual(
            [segment["text"] for segment in result["segments"]], ["Imported."]
        )

    def test_two_sources_are_mixed_into_one_waveform_and_transcribed_once(
        self,
    ) -> None:
        mic = np.array([0.4, 0.4, 0.4], dtype=np.float32)
        meeting = np.array([0.1, 0.1], dtype=np.float32)
        decoded = {"microphone.webm": mic, "meeting.webm": meeting}
        fake_audio_module = SimpleNamespace(
            decode_audio=lambda path, sampling_rate=16000: decoded[str(path)]
        )
        self.words_by_key["mixed"] = [
            SimpleNamespace(start=0.0, end=0.3, word="Hello", probability=0.9),
            SimpleNamespace(start=0.4, end=0.8, word="everyone.", probability=0.85),
        ]

        progress = []
        with patch.dict("sys.modules", {"faster_whisper.audio": fake_audio_module}):
            result = self.engine.process(
                microphone_path=Path("microphone.webm"),
                meeting_path=Path("meeting.webm"),
                mixed_path=None,
                metadata={},
                cancel_event=threading.Event(),
                progress=lambda value, stage: progress.append((value, stage)),
            )

        # Exactly one transcribe() call, against the mixed ndarray, not
        # against either source path individually.
        self.assertEqual(self.whisper.calls, ["mixed"])
        self.assertEqual(len(self.whisper.raw_calls), 1)
        mixed_array = self.whisper.raw_calls[0]
        self.assertIsInstance(mixed_array, np.ndarray)
        np.testing.assert_allclose(
            mixed_array, np.array([0.5, 0.5, 0.4], dtype=np.float32), atol=1e-6
        )
        self.assertEqual(
            [segment["text"] for segment in result["segments"]],
            ["Hello everyone."],
        )
        for segment in result["segments"]:
            self.assertNotIn("speakerId", segment)
            self.assertNotIn("source", segment)
        self.assertIn("mixing audio sources", [stage for _value, stage in progress])

    def test_three_sources_are_all_mixed_together(self) -> None:
        decoded = {
            "microphone.webm": np.array([0.1, 0.1], dtype=np.float32),
            "meeting.webm": np.array([0.1, 0.1], dtype=np.float32),
            "mixed.webm": np.array([0.1, 0.1], dtype=np.float32),
        }
        fake_audio_module = SimpleNamespace(
            decode_audio=lambda path, sampling_rate=16000: decoded[str(path)]
        )
        self.words_by_key["mixed"] = [
            SimpleNamespace(start=0.0, end=0.3, word="All", probability=0.9),
            SimpleNamespace(start=0.4, end=0.6, word="sources.", probability=0.85),
        ]

        with patch.dict("sys.modules", {"faster_whisper.audio": fake_audio_module}):
            result = self.engine.process(
                microphone_path=Path("microphone.webm"),
                meeting_path=Path("meeting.webm"),
                mixed_path=Path("mixed.webm"),
                metadata={},
                cancel_event=threading.Event(),
                progress=lambda _value, _stage: None,
            )

        self.assertEqual(self.whisper.calls, ["mixed"])
        mixed_array = self.whisper.raw_calls[0]
        np.testing.assert_allclose(
            mixed_array, np.array([0.3, 0.3], dtype=np.float32), atol=1e-6
        )
        self.assertEqual(
            [segment["text"] for segment in result["segments"]],
            ["All sources."],
        )

    def test_empty_transcription_returns_no_fabricated_segments(self) -> None:
        # No words registered for this key -- FakeWhisper returns a segment
        # with empty text, which build_transcript must not turn into a
        # fabricated segment.
        result = self.engine.process(
            microphone_path=Path("silence.webm"),
            meeting_path=None,
            mixed_path=None,
            metadata={},
            cancel_event=threading.Event(),
            progress=lambda _value, _stage: None,
        )

        self.assertEqual(result["segments"], [])


class FakeChunkWhisper:
    def __init__(self) -> None:
        self.calls: list = []
        self.feature_extractor = SimpleNamespace(sampling_rate=16000)

    def transcribe(self, audio, *, word_timestamps, vad_filter, beam_size):
        self.calls.append(audio)
        words = [
            SimpleNamespace(start=0.1, end=0.4, word="Hello", probability=0.9),
            SimpleNamespace(start=0.5, end=0.9, word="world", probability=0.85),
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


class LiveChunkTranscriptionTests(unittest.TestCase):
    """transcribe_chunk() powers live captions of the meeting-audio track
    while a recording is still in progress -- confirms the resample-to-the-
    model's-native-rate step, and that it never blocks on or disrupts a
    concurrent full-recording transcription job."""

    def setUp(self) -> None:
        self.whisper = FakeChunkWhisper()
        self.engine = LocalTranscriptionEngine()
        self.engine._whisper = self.whisper

    def test_transcribes_a_chunk_already_at_the_models_native_rate(self) -> None:
        samples = np.zeros(16000, dtype="float32")
        words = self.engine.transcribe_chunk(samples, 16000)
        self.assertEqual(
            words,
            [
                {"startMs": 100, "endMs": 400, "text": "Hello"},
                {"startMs": 500, "endMs": 900, "text": "world"},
            ],
        )
        self.assertEqual(len(self.whisper.calls), 1)
        self.assertEqual(self.whisper.calls[0].shape[0], samples.shape[0])

    def test_resamples_a_chunk_captured_at_a_different_rate(self) -> None:
        samples = np.zeros(48000, dtype="float32")  # 1 second at 48kHz
        self.engine.transcribe_chunk(samples, 48000)
        self.assertEqual(len(self.whisper.calls), 1)
        # 1 second resampled down to the model's native 16kHz.
        self.assertEqual(self.whisper.calls[0].shape[0], 16000)

    def test_skips_the_tick_without_blocking_when_a_job_holds_the_lock(self) -> None:
        samples = np.zeros(16000, dtype="float32")
        self.engine._inference_lock.acquire()
        try:
            words = self.engine.transcribe_chunk(samples, 16000)
        finally:
            self.engine._inference_lock.release()
        self.assertEqual(words, [])
        self.assertEqual(
            self.whisper.calls,
            [],
            "must never call the model while a full job holds the lock",
        )

    def test_swallows_any_error_and_returns_no_words(self) -> None:
        def boom(*_args, **_kwargs):
            raise RuntimeError("model exploded")

        self.whisper.transcribe = boom
        result = self.engine.transcribe_chunk(np.zeros(16000, dtype="float32"), 16000)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
