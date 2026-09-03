"""Windows system-output capture for the NotesBuddy desktop companion."""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import threading
import time
import wave
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


class SystemAudioUnavailable(RuntimeError):
    """Raised when Windows output capture is not available."""


class SystemAudioCaptureConflict(RuntimeError):
    """Raised when another output capture is already active."""


class SystemAudioCaptureNotFound(RuntimeError):
    """Raised when a requested capture does not exist."""


def _communications_default_render_id(
    *, platform: str | None = None
) -> str | None:
    """Best-effort id of the Windows Communications-role default output device.

    ``soundcard.default_speaker()`` queries the Console role (confirmed in its
    bundled WASAPI backend). Meeting/VoIP apps generally follow the separate
    Communications role instead, which Windows switches to a connected
    Bluetooth headset independently of Console/Multimedia -- the two roles can
    point at different physical devices, which is why loopback capture matched
    against the Console-role speaker can silently listen to the wrong one.
    Returns ``None`` on any failure so callers can fall back to the existing
    speaker-based match untouched.
    """
    if (platform or sys.platform) != "win32":
        return None
    try:
        import comtypes
        from pycaw.api.mmdeviceapi import IMMDeviceEnumerator
        from pycaw.constants import CLSID_MMDeviceEnumerator, EDataFlow, ERole
        from pycaw.utils import AudioUtilities
    except ImportError:
        return None
    com_initialized = False
    try:
        try:
            comtypes.CoInitialize()
            com_initialized = True
        except OSError:
            pass
        enumerator = comtypes.CoCreateInstance(
            CLSID_MMDeviceEnumerator,
            IMMDeviceEnumerator,
            comtypes.CLSCTX_INPROC_SERVER,
        )
        endpoint = enumerator.GetDefaultAudioEndpoint(
            EDataFlow.eRender.value, ERole.eCommunications.value
        )
        device = AudioUtilities.CreateDevice(endpoint)
        return str(device.id) if device is not None else None
    except Exception:  # noqa: BLE001 - purely advisory, never block capture
        return None
    finally:
        if com_initialized:
            try:
                comtypes.CoUninitialize()
            except OSError:
                pass


class SoundCardLoopbackBackend:
    """Open the default Windows render endpoint as a WASAPI loopback source."""

    def __init__(
        self,
        *,
        communications_id_provider: Callable[[], str | None] = (
            _communications_default_render_id
        ),
    ) -> None:
        import soundcard

        self._soundcard = soundcard
        self.speaker = soundcard.default_speaker()
        if self.speaker is None:
            raise SystemAudioUnavailable(
                "Windows does not have a default audio output device."
            )
        loopbacks = [
            microphone
            for microphone in soundcard.all_microphones(include_loopback=True)
            if bool(getattr(microphone, "isloopback", False))
        ]
        speaker_id = str(getattr(self.speaker, "id", ""))
        speaker_name = str(getattr(self.speaker, "name", ""))

        self.microphone = None
        communications_id = communications_id_provider()
        if communications_id:
            self.microphone = next(
                (
                    microphone
                    for microphone in loopbacks
                    if str(getattr(microphone, "id", "")) == communications_id
                ),
                None,
            )
        if self.microphone is None:
            self.microphone = next(
                (
                    microphone
                    for microphone in loopbacks
                    if str(getattr(microphone, "id", "")) == speaker_id
                ),
                None,
            )
        if self.microphone is None:
            self.microphone = next(
                (
                    microphone
                    for microphone in loopbacks
                    if str(getattr(microphone, "name", "")) == speaker_name
                ),
                None,
            )
        if self.microphone is None and speaker_name:
            normalized_speaker = speaker_name.casefold()
            self.microphone = next(
                (
                    microphone
                    for microphone in loopbacks
                    if normalized_speaker
                    in str(getattr(microphone, "name", "")).casefold()
                    or str(getattr(microphone, "name", "")).casefold()
                    in normalized_speaker
                ),
                None,
            )
        if self.microphone is None and len(loopbacks) == 1:
            self.microphone = loopbacks[0]
        if self.microphone is None:
            raise SystemAudioUnavailable(
                "The default Windows speaker does not expose a loopback source."
            )
        matched_name = str(getattr(self.microphone, "name", ""))
        self.device_name = matched_name or speaker_name or "Default Windows output"

    def recorder(self, *, sample_rate: int, channels: int, block_size: int):
        return self.microphone.recorder(
            samplerate=sample_rate,
            channels=channels,
            blocksize=block_size,
        )


@dataclass(slots=True)
class SystemAudioCapture:
    id: str
    path: Path
    stop_event: threading.Event = field(default_factory=threading.Event)
    pause_event: threading.Event = field(default_factory=threading.Event)
    ready_event: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)
    thread: threading.Thread | None = None
    status: str = "starting"
    device_name: str = "Windows output"
    signal_detected: bool = False
    level: float = 0.0
    frame_count: int = 0
    sample_rate: int = 48_000
    channels: int = 2
    error: str | None = None
    created_at: str = field(default_factory=_now)
    started_at: str | None = None
    completed_at: str | None = None

    def public(self) -> dict[str, Any]:
        with self.lock:
            duration_ms = round(
                self.frame_count / max(1, self.sample_rate) * 1000
            )
            return {
                "captureId": self.id,
                "status": self.status,
                "deviceName": self.device_name,
                "signalDetected": self.signal_detected,
                "level": round(self.level, 4),
                "durationMs": duration_ms,
                "sampleRate": self.sample_rate,
                "channels": self.channels,
                "error": self.error,
                "createdAt": self.created_at,
                "startedAt": self.started_at,
                "completedAt": self.completed_at,
            }


class SystemAudioCaptureManager:
    """Own one temporary WASAPI loopback capture at a time."""

    def __init__(
        self,
        *,
        backend_factory: Callable[[], object] = SoundCardLoopbackBackend,
        root: Path | None = None,
        platform: str | None = None,
    ) -> None:
        self._backend_factory = backend_factory
        self._root = root or Path(
            tempfile.mkdtemp(prefix="notesbuddy-system-audio-")
        )
        self._platform = platform or sys.platform
        self._captures: dict[str, SystemAudioCapture] = {}
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        if self._backend_factory is not SoundCardLoopbackBackend:
            return True
        return (
            self._platform == "win32"
            and importlib.util.find_spec("soundcard") is not None
        )

    @property
    def backend_name(self) -> str:
        return "windows-wasapi-loopback"

    def _active_locked(self) -> SystemAudioCapture | None:
        return next(
            (
                capture
                for capture in self._captures.values()
                if capture.status in {"starting", "recording", "paused"}
            ),
            None,
        )

    def start(self) -> SystemAudioCapture:
        if not self.available:
            raise SystemAudioUnavailable(
                "Install the latest Windows companion to capture system audio."
            )
        with self._lock:
            if self._active_locked() is not None:
                raise SystemAudioCaptureConflict(
                    "Another Windows audio capture is already running."
                )
            capture_id = f"capture-{uuid4()}"
            capture = SystemAudioCapture(
                id=capture_id,
                path=self._root / f"{capture_id}.wav",
            )
            self._captures[capture_id] = capture
            capture.thread = threading.Thread(
                target=self._record,
                args=(capture,),
                name="notesbuddy-system-audio",
                daemon=True,
            )
            capture.thread.start()
        if not capture.ready_event.wait(timeout=8):
            capture.stop_event.set()
            if capture.thread is not None:
                capture.thread.join(timeout=2)
            self.discard(capture.id)
            raise SystemAudioUnavailable(
                "Windows audio capture did not start in time."
            )
        with capture.lock:
            if capture.status == "failed":
                message = capture.error or "Windows audio capture could not start."
            else:
                message = None
        if message:
            self.discard(capture.id)
            raise SystemAudioUnavailable(message)
        return capture

    def _record(self, capture: SystemAudioCapture) -> None:
        try:
            backend = self._backend_factory()
            device_name = str(
                getattr(backend, "device_name", "Windows output")
            )
            capture.path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(capture.path), "wb") as output:
                output.setnchannels(capture.channels)
                output.setsampwidth(2)
                output.setframerate(capture.sample_rate)
                with backend.recorder(
                    sample_rate=capture.sample_rate,
                    channels=capture.channels,
                    block_size=4096,
                ) as recorder:
                    with capture.lock:
                        capture.status = "recording"
                        capture.device_name = device_name
                        capture.started_at = _now()
                    capture.ready_event.set()
                    while not capture.stop_event.is_set():
                        frames = recorder.record(numframes=2048)
                        if getattr(frames, "size", 0) == 0:
                            continue
                        absolute_peak = float(abs(frames).max())
                        with capture.lock:
                            capture.level = absolute_peak
                            if absolute_peak >= 0.008:
                                capture.signal_detected = True
                        if capture.pause_event.is_set():
                            continue
                        clipped = frames.clip(-1.0, 1.0)
                        pcm = (clipped * 32767.0).astype("<i2", copy=False)
                        output.writeframesraw(pcm.tobytes())
                        with capture.lock:
                            capture.frame_count += int(frames.shape[0])
            with capture.lock:
                if capture.status != "cancelled":
                    capture.status = "completed"
                capture.level = 0.0
                capture.completed_at = _now()
        except Exception as error:  # noqa: BLE001 - exposed as safe local state
            with capture.lock:
                capture.status = "failed"
                capture.error = (str(error).strip() or error.__class__.__name__)[:500]
                capture.completed_at = _now()
        finally:
            capture.ready_event.set()

    def get(self, capture_id: str) -> SystemAudioCapture:
        with self._lock:
            capture = self._captures.get(capture_id)
        if capture is None:
            raise SystemAudioCaptureNotFound("System audio capture was not found.")
        return capture

    def pause(self, capture_id: str) -> SystemAudioCapture:
        capture = self.get(capture_id)
        with capture.lock:
            if capture.status != "recording":
                raise SystemAudioCaptureConflict(
                    "System audio capture is not currently recording."
                )
            capture.pause_event.set()
            capture.status = "paused"
        return capture

    def resume(self, capture_id: str) -> SystemAudioCapture:
        capture = self.get(capture_id)
        with capture.lock:
            if capture.status != "paused":
                raise SystemAudioCaptureConflict(
                    "System audio capture is not currently paused."
                )
            capture.pause_event.clear()
            capture.status = "recording"
        return capture

    def stop(self, capture_id: str) -> SystemAudioCapture:
        capture = self.get(capture_id)
        capture.stop_event.set()
        capture.pause_event.clear()
        if capture.thread is not None:
            capture.thread.join(timeout=12)
            if capture.thread.is_alive():
                raise SystemAudioUnavailable(
                    "Windows audio capture did not stop cleanly."
                )
        with capture.lock:
            if capture.status == "failed":
                raise SystemAudioUnavailable(
                    capture.error or "Windows audio capture failed."
                )
        if not capture.path.is_file() or capture.path.stat().st_size <= 44:
            raise SystemAudioUnavailable(
                "Windows audio capture did not produce a recording."
            )
        return capture

    def cancel(self, capture_id: str) -> SystemAudioCapture:
        capture = self.get(capture_id)
        with capture.lock:
            capture.status = "cancelled"
        capture.stop_event.set()
        capture.pause_event.clear()
        if capture.thread is not None:
            capture.thread.join(timeout=5)
        self.discard(capture_id)
        return capture

    def discard(self, capture_id: str) -> None:
        with self._lock:
            capture = self._captures.pop(capture_id, None)
        if capture is not None:
            capture.path.unlink(missing_ok=True)

    def shutdown(self) -> None:
        with self._lock:
            captures = list(self._captures.values())
        for capture in captures:
            capture.stop_event.set()
            capture.pause_event.clear()
            if capture.thread is not None:
                capture.thread.join(timeout=3)
        shutil.rmtree(self._root, ignore_errors=True)
        with self._lock:
            self._captures.clear()
