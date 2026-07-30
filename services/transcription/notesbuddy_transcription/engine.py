"""Speech-to-text and diarization engine adapters."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .core import SpeakerTurn, Word, build_transcript


class EngineCancelled(RuntimeError):
    """Raised between model stages after a caller cancels a job."""


ProgressCallback = Callable[[float, str], None]


class EmptyEngine:
    """Dependency-light API test engine that never invents transcript text."""

    name = "empty-test-engine"

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
        self.whisper_model_name = whisper_model or os.getenv(
            "NOTESBUDDY_WHISPER_MODEL",
            "small",
        )
        self.device = device or os.getenv("NOTESBUDDY_MODEL_DEVICE", "cpu")
        self.compute_type = compute_type or os.getenv(
            "NOTESBUDDY_WHISPER_COMPUTE_TYPE",
            "int8",
        )
        self.diarization_model_name = diarization_model or os.getenv(
            "NOTESBUDDY_DIARIZATION_MODEL",
            "pyannote/speaker-diarization-community-1",
        )
        self.hugging_face_token = hugging_face_token or os.getenv(
            "HF_TOKEN",
            "",
        )
        self._whisper = None
        self._diarization = None
        self._load_lock = threading.Lock()

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
                self._whisper = WhisperModel(
                    self.whisper_model_name,
                    device=self.device,
                    compute_type=self.compute_type,
                )
        return self._whisper

    def _load_diarization(self):
        if self._diarization is not None:
            return self._diarization
        if not self.hugging_face_token:
            raise RuntimeError(
                "HF_TOKEN is required for the pyannote community diarization "
                "model. Accept the model terms and configure the token locally."
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
                    self._diarization = Pipeline.from_pretrained(
                        self.diarization_model_name,
                        token=self.hugging_face_token,
                    )
                except TypeError:
                    # Compatibility with pyannote releases using the previous
                    # Hugging Face keyword.
                    self._diarization = Pipeline.from_pretrained(
                        self.diarization_model_name,
                        use_auth_token=self.hugging_face_token,
                    )

                if self.device.lower().startswith("cuda"):
                    try:
                        import torch

                        self._diarization.to(torch.device(self.device))
                    except (ImportError, RuntimeError):
                        # The pipeline remains on its supported default device.
                        pass
        return self._diarization

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
        model = self._load_whisper()
        model_segments, info = model.transcribe(
            str(path),
            word_timestamps=True,
            vad_filter=True,
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
        return (
            getattr(output, "exclusive_speaker_diarization", None)
            or getattr(output, "speaker_diarization", None)
            or output
        )

    def _diarize(
        self,
        path: Path,
        *,
        cancel_event: threading.Event,
    ) -> list[SpeakerTurn]:
        pipeline = self._load_diarization()
        output = pipeline(str(path))
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
            for item in annotation:
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
