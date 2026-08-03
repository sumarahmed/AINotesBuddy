import struct
import tempfile
import time
import unittest
import wave
from pathlib import Path

from notesbuddy_transcription.system_audio import (
    SystemAudioCaptureConflict,
    SystemAudioCaptureManager,
    SystemAudioCaptureNotFound,
)


class FakePeak:
    def __init__(self, value: float) -> None:
        self.value = value

    def max(self) -> float:
        return self.value


class FakePcm:
    def __init__(self, samples: list[float]) -> None:
        self.samples = samples

    def astype(self, _format: str, copy: bool = False) -> "FakePcm":
        del copy
        return self

    def tobytes(self) -> bytes:
        values = [
            max(-32768, min(32767, round(sample))) for sample in self.samples
        ]
        return struct.pack(f"<{len(values)}h", *values)


class FakeFrames:
    def __init__(self, frame_count: int = 2048, level: float = 0.15) -> None:
        self.frame_count = frame_count
        self.level = level
        self.size = frame_count * 2
        self.shape = (frame_count, 2)

    def __abs__(self) -> FakePeak:
        return FakePeak(self.level)

    def clip(self, _minimum: float, _maximum: float) -> "FakeFrames":
        return self

    def __mul__(self, factor: float) -> FakePcm:
        return FakePcm([self.level * factor] * self.size)


class FakeRecorder:
    def __enter__(self) -> "FakeRecorder":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def record(self, *, numframes: int) -> FakeFrames:
        time.sleep(0.003)
        return FakeFrames(frame_count=numframes)


class FakeLoopbackBackend:
    device_name = "Synthetic Windows speaker"

    def recorder(
        self,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
    ) -> FakeRecorder:
        self.configuration = (sample_rate, channels, block_size)
        return FakeRecorder()


class SystemAudioCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.manager = SystemAudioCaptureManager(
            backend_factory=FakeLoopbackBackend,
            root=Path(self.temporary.name) / "captures",
            platform="win32",
        )

    def tearDown(self) -> None:
        self.manager.shutdown()
        self.temporary.cleanup()

    def wait_for_frames(self, capture_id: str) -> int:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            duration = self.manager.get(capture_id).public()["durationMs"]
            if duration >= 40:
                return int(duration)
            time.sleep(0.005)
        self.fail("Synthetic system-audio capture did not write frames.")

    def test_records_pauses_resumes_and_returns_stereo_wave(self) -> None:
        capture = self.manager.start()
        self.assertEqual(capture.public()["status"], "recording")
        self.assertEqual(
            capture.public()["deviceName"], "Synthetic Windows speaker"
        )
        self.wait_for_frames(capture.id)
        self.assertTrue(capture.public()["signalDetected"])

        self.manager.pause(capture.id)
        paused_duration = int(capture.public()["durationMs"])
        time.sleep(0.025)
        after_pause = int(capture.public()["durationMs"])
        self.assertLessEqual(after_pause - paused_duration, 50)

        self.manager.resume(capture.id)
        deadline = time.monotonic() + 2
        while int(capture.public()["durationMs"]) <= after_pause:
            if time.monotonic() >= deadline:
                self.fail("Synthetic capture did not resume writing frames.")
            time.sleep(0.005)

        completed = self.manager.stop(capture.id)
        self.assertEqual(completed.public()["status"], "completed")
        with wave.open(str(completed.path), "rb") as recording:
            self.assertEqual(recording.getnchannels(), 2)
            self.assertEqual(recording.getframerate(), 48_000)
            self.assertGreater(recording.getnframes(), 0)

    def test_rejects_overlapping_capture_and_deletes_cancelled_file(self) -> None:
        capture = self.manager.start()
        with self.assertRaises(SystemAudioCaptureConflict):
            self.manager.start()
        path = capture.path

        self.manager.cancel(capture.id)
        self.assertFalse(path.exists())
        with self.assertRaises(SystemAudioCaptureNotFound):
            self.manager.get(capture.id)


if __name__ == "__main__":
    unittest.main()
