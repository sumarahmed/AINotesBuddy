"""Speech-to-text and diarization engine adapters."""

from __future__ import annotations

import os
import json
import subprocess
import sys
import threading
from importlib.util import find_spec
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .core import SpeakerTurn, Word, build_transcript


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
    workload. Pyannote can remain on CPU when the distributable companion uses
    CPU PyTorch. Explicit configuration remains authoritative for operators.
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


class LocalDiarizationEngine:
    """Lazy faster-whisper + pyannote implementation.

    Models are not loaded until a job actually needs them, allowing the health
    endpoint and browser pairing flow to start quickly.
    """

    name = "faster-whisper + pyannote.audio"

    def __init__(
        self,
        *,
        whisper_model: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        diarization_model: str | None = None,
        hugging_face_token: str | None = None,
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
        self.diarization_model_name = (
            diarization_model
            or os.getenv("NOTESBUDDY_DIARIZATION_MODEL", "").strip()
            or bundled_model_reference(
                "speaker-diarization-community-1",
                "pyannote/speaker-diarization-community-1",
            )
        )
        self.hugging_face_token = hugging_face_token or os.getenv(
            "HF_TOKEN",
            "",
        )
        self.speaker_worker = Path(os.getenv("NOTESBUDDY_SPEAKER_WORKER", "").strip()) if os.getenv("NOTESBUDDY_SPEAKER_WORKER", "").strip() else None
        self._whisper = None
        self._diarization = None
        self._load_lock = threading.Lock()

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
        speaker_runtime_ready = bool(self.speaker_worker and self.speaker_worker.is_file()) or all(
            module_available(package) for package in ("pyannote.audio", "torch")
        )
        dependencies_ready = module_available("faster_whisper") and speaker_runtime_ready
        bundled_models_ready = all(
            Path(model).is_dir()
            for model in (
                self.whisper_model_name,
                self.diarization_model_name,
            )
        )
        downloadable_models_ready = bool(self.hugging_face_token)
        ready = dependencies_ready and (
            bundled_models_ready or downloadable_models_ready
        )
        source = (
            "bundled"
            if bundled_models_ready
            else "configured-download"
            if downloadable_models_ready
            else "missing"
        )
        return {
            "ready": ready,
            "source": source,
            "device": self.device,
            "computeType": self.compute_type,
            "accelerator": str(self.accelerator.get("name") or "CPU"),
            "gpuAvailable": bool(self.accelerator.get("available")),
            "diarizationDevice": "cuda"
            if self.device.startswith("cuda") and self._torch_cuda_available()
            else "cpu",
            "status": (
                "offline models ready"
                if ready and bundled_models_ready
                else "model download configured"
                if ready
                else "offline models or runtime packages are missing"
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

    def _load_diarization(self):
        if self._diarization is not None:
            return self._diarization
        local_model = Path(self.diarization_model_name).is_dir()
        if not self.hugging_face_token and not local_model:
            raise RuntimeError(
                "HF_TOKEN is required for the pyannote community diarization "
                "model when it is not bundled with the desktop companion. "
                "Accept the model terms and configure the token locally."
            )
        with self._load_lock:
            if self._diarization is None:
                try:
                    from pyannote.audio import Pipeline
                except ImportError as error:
                    raise RuntimeError(
                        "pyannote.audio is not installed. Install the companion "
                        "requirements before identifying speakers."
                    ) from error
                try:
                    if local_model:
                        self._diarization = Pipeline.from_pretrained(
                            self.diarization_model_name,
                        )
                    else:
                        self._diarization = Pipeline.from_pretrained(
                            self.diarization_model_name,
                            token=self.hugging_face_token,
                        )
                except TypeError:
                    # Compatibility with pyannote releases using the previous
                    # Hugging Face keyword.
                    if local_model:
                        raise
                    self._diarization = Pipeline.from_pretrained(
                        self.diarization_model_name,
                        use_auth_token=self.hugging_face_token,
                    )

                if (
                    self.device.lower().startswith("cuda")
                    and self._torch_cuda_available()
                ):
                    try:
                        import torch

                        self._diarization.to(torch.device(self.device))
                    except (ImportError, RuntimeError, AssertionError):
                        # The pipeline remains on its supported default device.
                        pass
        return self._diarization

    @staticmethod
    def _torch_cuda_available() -> bool:
        try:
            import torch

            return bool(torch.cuda.is_available())
        except (ImportError, RuntimeError, AssertionError):
            return False

    @staticmethod
    def _probability(word: object) -> float | None:
        value = getattr(word, "probability", None)
        try:
            return round(float(value), 4) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _transcribe(
        self,
        path: Path,
        *,
        cancel_event: threading.Event,
    ) -> tuple[list[Word], str | None]:
        try:
            return self._transcribe_once(path, cancel_event=cancel_event)
        except (RuntimeError, OSError) as error:
            if not (
                str(self.requested_device).lower() == "auto"
                and self.device.startswith("cuda")
            ):
                raise
            self._fallback_to_cpu(error, "inference")
            return self._transcribe_once(path, cancel_event=cancel_event)

    def _transcribe_once(
        self,
        path: Path,
        *,
        cancel_event: threading.Event,
    ) -> tuple[list[Word], str | None]:
        model = self._load_whisper()
        model_segments, info = model.transcribe(
            str(path),
            word_timestamps=True,
            vad_filter=True,
            beam_size=1,
        )
        words: list[Word] = []
        for segment in model_segments:
            if cancel_event.is_set():
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
        language = str(getattr(info, "language", "") or "").strip() or None
        return words, language

    @staticmethod
    def _annotation_from_output(output: object) -> object:
        """Return the annotation without testing it for truthiness.

        ``pyannote.audio`` 4 returns a ``DiarizeOutput`` wrapper.  Its
        annotations can be empty for short or quiet recordings, and an empty
        ``Annotation`` evaluates to ``False``.  A boolean ``or`` chain would
        therefore discard both valid empty annotations and try to iterate the
        non-iterable wrapper itself.
        """

        exclusive = getattr(output, "exclusive_speaker_diarization", None)
        if exclusive is not None:
            return exclusive
        regular = getattr(output, "speaker_diarization", None)
        if regular is not None:
            return regular
        return output

    def _diarize(
        self,
        path: Path,
        *,
        cancel_event: threading.Event,
    ) -> list[SpeakerTurn]:
        if self.speaker_worker and self.speaker_worker.is_file():
            return self._diarize_with_worker(path, cancel_event=cancel_event)
        pipeline = self._load_diarization()
        try:
            import soundfile
            import torch
        except ImportError as error:
            raise RuntimeError(
                "The local audio runtime is incomplete. Reinstall the latest "
                "NotesBuddy Desktop Companion."
            ) from error
        samples, sample_rate = soundfile.read(
            str(path),
            dtype="float32",
            always_2d=True,
        )
        waveform = torch.from_numpy(samples.T.copy())
        output = pipeline(
            {
                "waveform": waveform,
                "sample_rate": int(sample_rate),
            }
        )
        if cancel_event.is_set():
            raise EngineCancelled("Transcription cancelled")
        annotation = self._annotation_from_output(output)
        turns: list[SpeakerTurn] = []

        if hasattr(annotation, "itertracks"):
            iterator = annotation.itertracks(yield_label=True)
            for turn, _track, label in iterator:
                turns.append(
                    SpeakerTurn(
                        start_ms=max(0, round(float(turn.start) * 1000)),
                        end_ms=max(0, round(float(turn.end) * 1000)),
                        label=str(label),
                    )
                )
        else:
            try:
                iterator = iter(annotation)
            except TypeError as error:
                raise RuntimeError(
                    "The speaker model returned an unsupported diarization "
                    "result. Reinstall or update NotesBuddy Companion."
                ) from error
            for item in iterator:
                if len(item) == 2:
                    turn, label = item
                elif len(item) >= 3:
                    turn, _track, label = item[:3]
                else:
                    continue
                turns.append(
                    SpeakerTurn(
                        start_ms=max(0, round(float(turn.start) * 1000)),
                        end_ms=max(0, round(float(turn.end) * 1000)),
                        label=str(label),
                    )
                )
        return turns

    def _diarize_with_worker(
        self,
        path: Path,
        *,
        cancel_event: threading.Event,
    ) -> list[SpeakerTurn]:
        assert self.speaker_worker is not None
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            [
                str(self.speaker_worker),
                "--audio",
                str(path),
                "--model",
                str(self.diarization_model_name),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creation_flags,
        )
        while process.poll() is None:
            if cancel_event.wait(0.1):
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise EngineCancelled("Transcription cancelled")
        stdout, stderr = process.communicate()
        try:
            payload = json.loads(stdout or "{}")
        except ValueError as error:
            raise RuntimeError("The local speaker worker returned invalid output.") from error
        if process.returncode != 0 or payload.get("status") != "ok":
            detail = str(payload.get("error") or stderr or "Speaker recognition failed.").strip()
            raise RuntimeError(detail[:1000])
        return [
            SpeakerTurn(
                start_ms=max(0, round(float(turn.get("start", 0)) * 1000)),
                end_ms=max(0, round(float(turn.get("end", 0)) * 1000)),
                label=str(turn.get("speaker") or "UNKNOWN"),
            )
            for turn in payload.get("turns", [])
            if isinstance(turn, dict)
        ]

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
        """Process isolated sources and return browser-contract JSON."""

        del metadata
        microphone_words: list[Word] = []
        meeting_words: list[Word] = []
        meeting_turns: list[SpeakerTurn] = []
        languages: list[str] = []

        if cancel_event.is_set():
            raise EngineCancelled("Transcription cancelled")

        if microphone_path:
            progress(0.08, "transcribing microphone")
            microphone_words, language = self._transcribe(
                microphone_path,
                cancel_event=cancel_event,
            )
            if language:
                languages.append(language)

        # A mixed-only file is an import with no isolated microphone. When a
        # microphone track exists without a meeting track, mixed is the same
        # local source and must not be diarized as a second voice.
        remote_path = meeting_path or (
            mixed_path if not microphone_path and not meeting_path else None
        )
        if remote_path:
            progress(0.38, "transcribing meeting audio")
            meeting_words, language = self._transcribe(
                remote_path,
                cancel_event=cancel_event,
            )
            if language:
                languages.append(language)
            progress(0.68, "identifying meeting speakers")
            meeting_turns = self._diarize(
                remote_path,
                cancel_event=cancel_event,
            )

        if cancel_event.is_set():
            raise EngineCancelled("Transcription cancelled")
        progress(0.9, "aligning speaker timestamps")
        segments = build_transcript(
            microphone_words=microphone_words,
            meeting_words=meeting_words,
            meeting_turns=meeting_turns,
        )
        progress(1.0, "completed")
        language = max(set(languages), key=languages.count) if languages else None
        return {"language": language, "segments": segments}


def engine_from_environment():
    engine_name = os.getenv("NOTESBUDDY_TRANSCRIPTION_ENGINE", "local").lower()
    if engine_name in {"empty", "test", "mock"}:
        return EmptyEngine()
    if engine_name != "local":
        raise RuntimeError(
            "NOTESBUDDY_TRANSCRIPTION_ENGINE must be 'local' or 'empty'."
        )
    return LocalDiarizationEngine()
