"""Speech-to-text engine adapters."""

from __future__ import annotations

import os
import sys
import threading
from importlib.util import find_spec
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .core import Word, build_transcript
from .diagnostics import log_diagnostic


class EngineCancelled(RuntimeError):
    """Raised between model stages after a caller cancels a job."""


ProgressCallback = Callable[[float, str], None]
_DLL_DIRECTORY_HANDLES: list[Any] = []


def activate_optional_gpu_runtime() -> bool:
    """Expose the persistent NVIDIA pack to Windows without changing PATH."""
    configured = os.getenv("NOTESBUDDY_GPU_LIB_DIR", "").strip()
    if not configured or not hasattr(os, "add_dll_directory"):
        return False
    directory = Path(configured).expanduser().resolve()
    required = ("cublas64_12.dll", "cudnn64_9.dll")
    if not directory.is_dir() or not all(
        (directory / filename).is_file() for filename in required
    ):
        return False
    try:
        path_entries = os.environ.get("PATH", "").split(os.pathsep)
        if str(directory) not in path_entries:
            os.environ["PATH"] = str(directory) + os.pathsep + os.environ.get(
                "PATH", ""
            )
        if not _DLL_DIRECTORY_HANDLES:
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(directory)))
        return True
    except OSError:
        return False


def local_accelerator(requested_device: str = "auto") -> dict[str, object]:
    """Resolve the fastest locally supported inference device.

    faster-whisper uses CTranslate2, which performs the dominant speech model
    workload. Explicit configuration remains authoritative for operators.
    """

    requested = str(requested_device or "auto").strip().lower() or "auto"
    if requested != "auto":
        return {
            "requested": requested,
            "device": requested,
            "name": "Configured CUDA" if requested.startswith("cuda") else "CPU",
            "available": requested.startswith("cuda"),
        }
    try:
        gpu_runtime_configured = bool(
            os.getenv("NOTESBUDDY_GPU_LIB_DIR", "").strip()
        )
        gpu_runtime_active = activate_optional_gpu_runtime()
        if os.name == "nt" and gpu_runtime_configured and not gpu_runtime_active:
            return {
                "requested": "auto",
                "device": "cpu",
                "name": "CPU (NVIDIA pack not installed)",
                "available": False,
            }
        import ctranslate2
        cuda_available = bool(ctranslate2.get_cuda_device_count() > 0)
        if cuda_available:
            return {
                "requested": "auto",
                "device": "cuda",
                "name": "NVIDIA GPU",
                "available": True,
            }
    except (ImportError, OSError, RuntimeError):
        pass
    return {
        "requested": "auto",
        "device": "cpu",
        "name": "CPU",
        "available": False,
    }


def packaged_models_root() -> Path | None:
    configured = os.getenv("NOTESBUDDY_MODEL_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    bundle_root = getattr(sys, "_MEIPASS", "")
    if bundle_root:
        return Path(bundle_root) / "models"
    executable_models = Path(sys.executable).resolve().parent / "models"
    if executable_models.is_dir():
        return executable_models
    return None


def bundled_model_reference(directory_name: str, fallback: str) -> str:
    root = packaged_models_root()
    candidate = root / directory_name if root is not None else None
    return str(candidate) if candidate is not None and candidate.is_dir() else fallback


def module_available(name: str) -> bool:
    try:
        return find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


class EmptyEngine:
    """Dependency-light API test engine that never invents transcript text."""

    name = "empty-test-engine"

    @staticmethod
    def configuration_status() -> dict[str, object]:
        return {
            "ready": True,
            "source": "test",
            "status": "dependency-light test engine",
        }

    def process(
        self,
        *,
        microphone_path: Path | None,
        meeting_path: Path | None,
        mixed_path: Path | None,
        metadata: dict[str, Any],
        cancel_event: threading.Event,
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        del microphone_path, meeting_path, mixed_path, metadata
        if cancel_event.is_set():
            raise EngineCancelled("Transcription cancelled")
        progress(1.0, "completed")
        return {"language": None, "segments": []}


class LocalTranscriptionEngine:
    """Lazy faster-whisper implementation.

    Models are not loaded until a job actually needs them, allowing the health
    endpoint and browser pairing flow to start quickly.

    Every provided isolated recording (microphone/meeting/mixed) is mixed
    into a single waveform and transcribed once, producing one flat,
    speaker-agnostic transcript -- there is no per-speaker attribution or
    diarization stage. See core.build_transcript for the segment-collapsing
    rules.
    """

    name = "faster-whisper"

    def __init__(
        self,
        *,
        whisper_model: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
    ) -> None:
        self.whisper_model_name = (
            whisper_model
            or os.getenv("NOTESBUDDY_WHISPER_MODEL", "").strip()
            or bundled_model_reference("faster-whisper-selected", "small")
        )
        self.requested_device = (
            device or os.getenv("NOTESBUDDY_MODEL_DEVICE", "auto")
        )
        self.accelerator = local_accelerator(self.requested_device)
        self.device = str(self.accelerator["device"])
        configured_compute_type = (
            compute_type
            or os.getenv("NOTESBUDDY_WHISPER_COMPUTE_TYPE", "").strip()
        )
        self.compute_type = configured_compute_type or (
            "float16" if self.device.startswith("cuda") else "int8"
        )
        self._whisper = None
        self._load_lock = threading.Lock()
        # Guards every call into the whisper model. faster-whisper is not
        # guaranteed safe for concurrent inference, and once live partial
        # transcription exists this is the first thing that can call
        # .transcribe() concurrently with a full-recording job. The
        # full-file path (process()) acquires this blocking -- correctness
        # matters, a job can afford to wait. The live-chunk path
        # (transcribe_chunk) acquires it non-blocking and just skips that
        # tick on contention, so a live caption never queues behind a
        # multi-minute transcription job.
        self._inference_lock = threading.Lock()

    def _fallback_to_cpu(self, error: BaseException, phase: str) -> None:
        self._whisper = None
        self.device = "cpu"
        self.compute_type = "int8"
        self.accelerator = {
            "requested": "auto",
            "device": "cpu",
            "name": f"CPU (CUDA {phase} failed)",
            "available": False,
            "fallbackReason": str(error)[:240],
        }

    def configuration_status(self) -> dict[str, object]:
        if (
            str(self.requested_device).strip().lower() == "auto"
            and self._whisper is None
            and self.device == "cpu"
        ):
            refreshed = local_accelerator("auto")
            if bool(refreshed.get("available")):
                self.accelerator = refreshed
                self.device = "cuda"
                self.compute_type = "float16"
        dependencies_ready = module_available("faster_whisper")
        bundled_models_ready = Path(self.whisper_model_name).is_dir()
        # Whisper's public models (the non-bundled fallback, e.g. "small")
        # download from the Hugging Face hub with no token required, unlike
        # the gated diarization model this engine used to also need --
        # readiness here depends only on the runtime package being
        # installed, not on any configured credential.
        ready = dependencies_ready
        source = "bundled" if bundled_models_ready else "configured-download"
        return {
            "ready": ready,
            "source": source,
            "device": self.device,
            "computeType": self.compute_type,
            "accelerator": str(self.accelerator.get("name") or "CPU"),
            "gpuAvailable": bool(self.accelerator.get("available")),
            "status": (
                "offline models ready"
                if ready and bundled_models_ready
                else "model download configured"
                if ready
                else "the faster-whisper runtime package is missing"
            ),
        }

    def _load_whisper(self):
        if self._whisper is not None:
            return self._whisper
        with self._load_lock:
            if self._whisper is None:
                try:
                    from faster_whisper import WhisperModel
                except ImportError as error:
                    raise RuntimeError(
                        "faster-whisper is not installed. Install the companion "
                        "requirements before transcribing."
                    ) from error
                try:
                    self._whisper = WhisperModel(
                        self.whisper_model_name,
                        device=self.device,
                        compute_type=self.compute_type,
                    )
                except (RuntimeError, OSError) as error:
                    if not (
                        str(self.requested_device).lower() == "auto"
                        and self.device.startswith("cuda")
                    ):
                        raise
                    self._fallback_to_cpu(error, "initialization")
                    self._whisper = WhisperModel(
                        self.whisper_model_name,
                        device="cpu",
                        compute_type="int8",
                    )
        return self._whisper

    @staticmethod
    def _probability(word: object) -> float | None:
        value = getattr(word, "probability", None)
        try:
            return round(float(value), 4) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _transcribe(
        self,
        audio: Path | Any,
        *,
        cancel_event: threading.Event,
    ) -> tuple[list[Word], str | None]:
        try:
            return self._transcribe_once(audio, cancel_event=cancel_event)
        except (RuntimeError, OSError) as error:
            if not (
                str(self.requested_device).lower() == "auto"
                and self.device.startswith("cuda")
            ):
                raise
            self._fallback_to_cpu(error, "inference")
            return self._transcribe_once(audio, cancel_event=cancel_event)

    def _words_from_model_segments(
        self,
        model_segments: Any,
        *,
        cancel_event: threading.Event | None = None,
    ) -> list[Word]:
        words: list[Word] = []
        for segment in model_segments:
            if cancel_event is not None and cancel_event.is_set():
                raise EngineCancelled("Transcription cancelled")
            segment_words = getattr(segment, "words", None) or []
            if segment_words:
                for word in segment_words:
                    text = str(getattr(word, "word", "") or "").strip()
                    if not text:
                        continue
                    start_seconds = getattr(word, "start", None)
                    end_seconds = getattr(word, "end", None)
                    if start_seconds is None:
                        start_seconds = getattr(segment, "start", 0.0)
                    if end_seconds is None:
                        end_seconds = getattr(segment, "end", start_seconds)
                    words.append(
                        Word(
                            start_ms=max(0, round(float(start_seconds) * 1000)),
                            end_ms=max(0, round(float(end_seconds) * 1000)),
                            text=text,
                            confidence=self._probability(word),
                        )
                    )
            else:
                text = str(getattr(segment, "text", "") or "").strip()
                if text:
                    words.append(
                        Word(
                            start_ms=max(
                                0,
                                round(float(getattr(segment, "start", 0.0)) * 1000),
                            ),
                            end_ms=max(
                                0,
                                round(float(getattr(segment, "end", 0.0)) * 1000),
                            ),
                            text=text,
                        )
                    )
        return words

    def _transcribe_once(
        self,
        audio: Path | Any,
        *,
        cancel_event: threading.Event,
    ) -> tuple[list[Word], str | None]:
        model = self._load_whisper()
        # A Path goes through faster-whisper's own ffmpeg-quality file
        # decoder (best quality, and the common single-source case avoids
        # a redundant decode/mix round trip entirely -- see process()).
        # A decoded ndarray (produced when two or three sources had to be
        # mixed first) is passed straight through; faster-whisper's numpy
        # input path assumes it is already at the model's native rate,
        # which _mixed_audio guarantees by decoding every source at 16kHz.
        source = str(audio) if isinstance(audio, Path) else audio
        # Held for the full transcribe-and-consume span, not just the
        # transcribe() call: faster-whisper's segment iterator is lazy, so
        # the actual model inference happens while _words_from_model_segments
        # iterates it, not during transcribe() itself.
        with self._inference_lock:
            model_segments, info = model.transcribe(
                source,
                word_timestamps=True,
                vad_filter=True,
                beam_size=1,
            )
            words = self._words_from_model_segments(
                model_segments, cancel_event=cancel_event
            )
            language = str(getattr(info, "language", "") or "").strip() or None
        return words, language

    def transcribe_chunk(
        self, samples: Any, sample_rate: int
    ) -> list[dict[str, Any]]:
        """Best-effort transcription of a short in-progress recording chunk.

        Used for live captions while a meeting-audio capture is still
        running. Skips the tick rather than waiting if a full-recording job
        already holds the inference lock -- a missed 5-second tick is
        harmless, queuing several behind a multi-minute job is not. Any
        failure is swallowed for the same reason: this must never disrupt
        the recording it runs alongside.
        """

        if not self._inference_lock.acquire(blocking=False):
            return []
        try:
            model = self._load_whisper()
            # faster-whisper's numpy-array input path skips resampling
            # entirely -- it assumes the array is already at the model's
            # native rate (transcribe.py: `if not isinstance(audio,
            # np.ndarray): audio = decode_audio(...)`). Only the file-path
            # input goes through ffmpeg-quality resampling, so a chunk
            # captured at a different rate must be resampled here first.
            target_rate = int(model.feature_extractor.sampling_rate)
            audio = self._resample_for_whisper(samples, sample_rate, target_rate)
            model_segments, _info = model.transcribe(
                audio,
                word_timestamps=True,
                vad_filter=True,
                beam_size=1,
            )
            words = self._words_from_model_segments(model_segments)
        except Exception:  # noqa: BLE001 - best-effort live tick, never propagate
            return []
        finally:
            self._inference_lock.release()
        return [
            {"startMs": word.start_ms, "endMs": word.end_ms, "text": word.text}
            for word in words
        ]

    @staticmethod
    def _resample_for_whisper(samples: Any, source_rate: int, target_rate: int) -> Any:
        """Cheap linear-interpolation resample for the live-caption tick.

        Not used by the full-recording path, which resamples through
        faster-whisper's own ffmpeg-quality file decoder instead -- this is
        deliberately a lower-quality, dependency-free stand-in acceptable
        only for a best-effort live draft.
        """

        import numpy as np

        if source_rate == target_rate or samples.size == 0:
            return samples.astype("float32", copy=False)
        duration = samples.shape[0] / float(source_rate)
        target_length = max(1, int(round(duration * target_rate)))
        source_indices = np.linspace(0, samples.shape[0] - 1, num=target_length)
        return np.interp(
            source_indices, np.arange(samples.shape[0]), samples
        ).astype("float32")

    @staticmethod
    def _mixed_audio(paths: list[Path]) -> Any:
        """Decode two or three isolated recordings and sum them into one.

        Each source is decoded to mono float32 at 16kHz (faster-whisper's
        native rate) via faster_whisper's own decoder, so every array is
        already aligned to a shared sample rate before mixing. Shorter
        arrays are zero-padded to the longest length, summed sample-wise,
        then clipped to [-1.0, 1.0] -- summing two full-scale waveforms can
        otherwise exceed that range and distort.

        Only called when there are 2 or 3 provided sources; a single source
        is transcribed directly from its file path instead (see process()),
        which is both cheaper and higher quality.
        """

        import numpy as np
        from faster_whisper.audio import decode_audio

        sample_rate = 16000
        arrays = [
            decode_audio(str(path), sampling_rate=sample_rate) for path in paths
        ]
        max_length = max(array.shape[0] for array in arrays)
        mixed = np.zeros(max_length, dtype=np.float32)
        for array in arrays:
            mixed[: array.shape[0]] += array
        np.clip(mixed, -1.0, 1.0, out=mixed)
        return mixed

    def process(
        self,
        *,
        microphone_path: Path | None,
        meeting_path: Path | None,
        mixed_path: Path | None,
        metadata: dict[str, Any],
        cancel_event: threading.Event,
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        """Mix every provided isolated source and transcribe it once.

        Accepts the same microphone/meeting/mixed upload contract as
        before, but no longer transcribes them separately or diarizes the
        remote source -- all provided sources are combined into one
        waveform (or, when only one is provided, transcribed directly from
        its own file) and turned into a single flat transcript with no
        speaker attribution.
        """

        del metadata

        def source_size(path: Path | None) -> int:
            try:
                return path.stat().st_size if path else 0
            except OSError:
                return -1

        log_diagnostic(
            "engine.process starting: microphone=%s (%d bytes) meeting=%s "
            "(%d bytes) mixed=%s (%d bytes) model=%s device=%s"
            % (
                bool(microphone_path),
                source_size(microphone_path),
                bool(meeting_path),
                source_size(meeting_path),
                bool(mixed_path),
                source_size(mixed_path),
                self.whisper_model_name,
                self.device,
            )
        )

        if cancel_event.is_set():
            raise EngineCancelled("Transcription cancelled")

        provided_paths = [
            path for path in (microphone_path, meeting_path, mixed_path) if path
        ]
        if not provided_paths:
            progress(1.0, "completed")
            return {"language": None, "segments": []}

        if len(provided_paths) == 1:
            audio_source: Path | Any = provided_paths[0]
        else:
            progress(0.15, "mixing audio sources")
            audio_source = self._mixed_audio(provided_paths)
            log_diagnostic(
                f"engine.process mixed {len(provided_paths)} sources into one waveform"
            )

        if cancel_event.is_set():
            raise EngineCancelled("Transcription cancelled")

        progress(0.3, "transcribing")
        words, language = self._transcribe(audio_source, cancel_event=cancel_event)
        log_diagnostic(
            f"engine.process transcribed: {len(words)} words, language={language}"
        )

        if cancel_event.is_set():
            raise EngineCancelled("Transcription cancelled")
        progress(0.9, "building transcript")
        segments = build_transcript(words)
        progress(1.0, "completed")
        if not segments:
            log_diagnostic(
                "engine.process WARNING: produced an empty transcript -- "
                f"words={len(words)}. If the word count is 0 despite audible "
                "speech, faster-whisper's VAD filter likely classified the "
                "source audio as silence (low gain, wrong capture device, or "
                "heavy noise reduction)."
            )
        else:
            log_diagnostic(f"engine.process completed: {len(segments)} segments")
        return {"language": language, "segments": segments}


def engine_from_environment():
    engine_name = os.getenv("NOTESBUDDY_TRANSCRIPTION_ENGINE", "local").lower()
    if engine_name in {"empty", "test", "mock"}:
        return EmptyEngine()
    if engine_name != "local":
        raise RuntimeError(
            "NOTESBUDDY_TRANSCRIPTION_ENGINE must be 'local' or 'empty'."
        )
    return LocalTranscriptionEngine()
