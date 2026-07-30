from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notesbuddy_transcription.engine import LocalDiarizationEngine


class FakeWhisper:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def transcribe(self, path, *, word_timestamps, vad_filter):
        self.calls.append(Path(path).name)
        self.last_options = (word_timestamps, vad_filter)
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
    def test_bundled_models_are_preferred_without_a_user_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model_root = Path(directory)
            whisper = model_root / "faster-whisper-small"
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


class FakeTurn:
    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end


class FakeAnnotation:
    def itertracks(self, *, yield_label):
        assert yield_label is True
        yield FakeTurn(0.9, 1.8), "track-a", "VOICE_B"
        yield FakeTurn(1.9, 2.8), "track-b", "VOICE_A"


class FakeDiarizationPipeline:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, path):
        self.calls.append(Path(path).name)
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

    def test_dual_source_result_marks_you_and_orders_remote_ids(self) -> None:
        progress = []
        result = self.engine.process(
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
        result = self.engine.process(
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
        result = self.engine.process(
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


if __name__ == "__main__":
    unittest.main()
