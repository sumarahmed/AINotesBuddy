"""Local or anonymous-hosted API for NotesBuddy transcription jobs."""

from __future__ import annotations

import hmac
import json
import os
import shutil
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Callable, NoReturn
from uuid import uuid4

from fastapi import (
    Body,
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import FileResponse

from .access import (
    AnonymousSessionStore,
    SessionAccessError,
    anonymise_client_key,
)
from .analysis import (
    MeetingAnalysisUnavailable,
    analyzer_from_environment,
)
from .engine import EngineCancelled, engine_from_environment
from .pairing import BrowserPairingStore
from .security import ensure_pairing_token
from .system_audio import (
    SystemAudioCaptureConflict,
    SystemAudioCaptureManager,
    SystemAudioCaptureNotFound,
    SystemAudioUnavailable,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _allowed_origins() -> list[str]:
    configured = os.getenv("NOTESBUDDY_ALLOWED_ORIGINS", "")
    if configured.strip():
        return [
            origin.strip()
            for origin in configured.split(",")
            if origin.strip()
        ]
    return [
        "null",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "https://sumarahmed.github.io",
    ]


def _environment_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Job:
    id: str
    work_dir: Path
    metadata: dict[str, Any]
    paths: dict[str, Path]
    engine_name: str
    owner_digest: str | None = None
    on_terminal: Callable[[str | None], None] | None = None
    status: str = "queued"
    progress: float = 0.0
    stage: str = "queued"
    language: str | None = None
    segments: list[dict] = field(default_factory=list)
    error: str | None = None
    created_at: str = field(default_factory=_now)
    created_monotonic: float = field(default_factory=time.monotonic)
    started_at: str | None = None
    completed_at: str | None = None
    completed_monotonic: float | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def public(self) -> dict[str, Any]:
        with self.lock:
            return {
                "jobId": self.id,
                "status": self.status,
                "progress": self.progress,
                "stage": self.stage,
                "engine": self.engine_name,
                "language": self.language,
                "segments": list(self.segments),
                "error": self.error,
                "createdAt": self.created_at,
                "startedAt": self.started_at,
                "completedAt": self.completed_at,
            }


class JobStore:
    def __init__(self, *, retention_seconds: int, maximum_jobs: int) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._retention_seconds = retention_seconds
        self._maximum_jobs = maximum_jobs

    def _cleanup_locked(self) -> None:
        now = time.monotonic()
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if job.completed_monotonic is not None
            and now - job.completed_monotonic >= self._retention_seconds
        ]
        for job_id in expired:
            self._jobs.pop(job_id, None)

    def add(self, job: Job) -> bool:
        with self._lock:
            self._cleanup_locked()
            if len(self._jobs) >= self._maximum_jobs:
                completed = sorted(
                    (
                        existing
                        for existing in self._jobs.values()
                        if existing.completed_monotonic is not None
                    ),
                    key=lambda existing: existing.completed_monotonic or 0,
                )
                for existing in completed:
                    self._jobs.pop(existing.id, None)
                    if len(self._jobs) < self._maximum_jobs:
                        break
            if len(self._jobs) >= self._maximum_jobs:
                return False
            self._jobs[job.id] = job
            return True

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            self._cleanup_locked()
            return self._jobs.get(job_id)

    def remove(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.pop(job_id, None)


def _safe_error(error: BaseException, work_dir: Path) -> str:
    message = str(error).replace(str(work_dir), "[temporary audio]").strip()
    return (message or error.__class__.__name__)[:1000]


def _run_job(job: Job, engine: object) -> None:
    with job.lock:
        if job.cancel_event.is_set():
            job.status = "cancelled"
            job.stage = "cancelled"
            job.completed_at = _now()
            job.completed_monotonic = time.monotonic()
            shutil.rmtree(job.work_dir, ignore_errors=True)
            if job.on_terminal is not None:
                job.on_terminal(job.owner_digest)
            return
        job.status = "processing"
        job.stage = "loading local models"
        job.started_at = _now()

    def progress(value: float, stage: str) -> None:
        with job.lock:
            if job.status != "cancelled":
                job.progress = min(1.0, max(0.0, float(value)))
                job.stage = str(stage)[:120]

    try:
        result = engine.process(
            microphone_path=job.paths.get("microphone"),
            meeting_path=job.paths.get("meeting"),
            mixed_path=job.paths.get("mixed"),
            metadata=job.metadata,
            cancel_event=job.cancel_event,
            progress=progress,
        )
        with job.lock:
            if job.cancel_event.is_set():
                job.status = "cancelled"
                job.stage = "cancelled"
            else:
                job.status = "completed"
                job.stage = "completed"
                job.progress = 1.0
                job.language = result.get("language")
                job.segments = list(result.get("segments") or [])
            job.completed_at = _now()
            job.completed_monotonic = time.monotonic()
    except EngineCancelled:
        with job.lock:
            job.status = "cancelled"
            job.stage = "cancelled"
            job.completed_at = _now()
            job.completed_monotonic = time.monotonic()
    except Exception as error:  # noqa: BLE001 - model failures become job state
        with job.lock:
            job.status = "failed"
            job.stage = "failed"
            job.error = _safe_error(error, job.work_dir)
            job.completed_at = _now()
            job.completed_monotonic = time.monotonic()
    finally:
        shutil.rmtree(job.work_dir, ignore_errors=True)
        if job.on_terminal is not None:
            job.on_terminal(job.owner_digest)


async def _save_upload(
    upload: UploadFile,
    *,
    source: str,
    work_dir: Path,
    maximum_bytes: int,
) -> tuple[Path, int]:
    suffix = Path(upload.filename or "").suffix.lower()
    if not suffix or len(suffix) > 10 or not suffix[1:].isalnum():
        suffix = ".webm"
    destination = work_dir / f"{source}{suffix}"
    total = 0
    with destination.open("xb") as output:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > maximum_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"{source} recording exceeds the configured limit.",
                )
            output.write(chunk)
    await upload.close()
    if total == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail=f"{source} recording is empty.",
        )
    return destination, total


def create_app(
    *,
    engine: object | None = None,
    analyzer: object | None = None,
    pairing_token: str | None = None,
    allowed_origins: list[str] | None = None,
    authentication_mode: str | None = None,
    allow_browser_pairing: bool | None = None,
    companion_version: str | None = None,
    system_audio_capture: object | None = None,
) -> FastAPI:
    active_engine = engine or engine_from_environment()
    active_analyzer = analyzer or analyzer_from_environment()
    access_mode = (
        authentication_mode
        or os.getenv("NOTESBUDDY_ACCESS_MODE", "local")
    ).strip().lower()
    if access_mode not in {"local", "anonymous"}:
        raise RuntimeError(
            "NOTESBUDDY_ACCESS_MODE must be 'local' or 'anonymous'."
        )
    hosted = access_mode == "anonymous"
    active_system_audio = system_audio_capture or SystemAudioCaptureManager()
    trusted_origins = (
        list(allowed_origins)
        if allowed_origins is not None
        else _allowed_origins()
    )
    browser_pairing_enabled = (
        allow_browser_pairing
        if allow_browser_pairing is not None
        else _environment_flag("NOTESBUDDY_ALLOW_BROWSER_PAIRING")
    ) and not hosted
    if not hosted:
        if pairing_token is None:
            pairing_token, _token_path, _created = ensure_pairing_token()
        if len(pairing_token) < 24:
            raise RuntimeError("The NotesBuddy pairing token is too short.")

    browser_pairings = BrowserPairingStore(
        ttl_seconds=max(
            15 * 60,
            min(
                7 * 24 * 60 * 60,
                int(os.getenv("NOTESBUDDY_BROWSER_PAIRING_TTL_SECONDS", "86400")),
            ),
        ),
        maximum_pairings=max(
            4,
            min(
                128,
                int(os.getenv("NOTESBUDDY_MAX_BROWSER_PAIRINGS", "32")),
            ),
        ),
    )
    sessions = (
        AnonymousSessionStore(
            session_ttl_seconds=max(
                15 * 60,
                min(
                    48 * 60 * 60,
                    int(
                        os.getenv(
                            "NOTESBUDDY_SESSION_TTL_SECONDS",
                            str(24 * 60 * 60),
                        )
                    ),
                ),
            ),
            maximum_sessions=max(
                16,
                min(
                    100_000,
                    int(os.getenv("NOTESBUDDY_MAX_SESSIONS", "2048")),
                ),
            ),
            issue_window_seconds=max(
                60,
                int(os.getenv("NOTESBUDDY_SESSION_ISSUE_WINDOW_SECONDS", "3600")),
            ),
            maximum_issues_per_client=max(
                1,
                int(os.getenv("NOTESBUDDY_MAX_SESSIONS_PER_CLIENT", "10")),
            ),
            job_window_seconds=max(
                60,
                int(os.getenv("NOTESBUDDY_JOB_LIMIT_WINDOW_SECONDS", "3600")),
            ),
            maximum_jobs_per_session=max(
                1,
                int(os.getenv("NOTESBUDDY_MAX_JOBS_PER_SESSION", "3")),
            ),
            maximum_active_jobs_per_session=max(
                1,
                min(
                    2,
                    int(os.getenv("NOTESBUDDY_MAX_ACTIVE_JOBS_PER_SESSION", "1")),
                ),
            ),
        )
        if hosted
        else None
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
            shutdown_system_audio = getattr(active_system_audio, "shutdown", None)
            if callable(shutdown_system_audio):
                shutdown_system_audio()

    app = FastAPI(
        title=(
            "NotesBuddy public transcription service"
            if hosted
            else "NotesBuddy local transcription companion"
        ),
        version="1.2.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=trusted_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "X-NotesBuddy-Pairing-Token",
            "X-NotesBuddy-Session-Token",
        ],
        max_age=600,
    )

    @app.middleware("http")
    async def allow_authenticated_local_network_preflight(
        request: Request,
        call_next,
    ):
        response = await call_next(request)
        if (
            not hosted
            and request.headers.get("access-control-request-private-network")
            == "true"
        ):
            response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response

    retention_seconds = max(
        60,
        min(
            24 * 60 * 60,
            int(os.getenv("NOTESBUDDY_JOB_RETENTION_SECONDS", "3600")),
        ),
    )
    maximum_jobs = max(
        4,
        min(256, int(os.getenv("NOTESBUDDY_MAX_JOBS", "64"))),
    )
    jobs = JobStore(
        retention_seconds=retention_seconds,
        maximum_jobs=maximum_jobs,
    )
    executor = ThreadPoolExecutor(
        max_workers=max(
            1,
            min(2, int(os.getenv("NOTESBUDDY_MAX_WORKERS", "1"))),
        ),
        thread_name_prefix="notesbuddy-transcription",
    )
    maximum_source_bytes = max(
        1024 * 1024,
        int(
            os.getenv(
                "NOTESBUDDY_MAX_SOURCE_BYTES",
                str(250 * 1024**2 if hosted else 2 * 1024**3),
            )
        ),
    )
    maximum_total_bytes = max(
        maximum_source_bytes,
        int(
            os.getenv(
                "NOTESBUDDY_MAX_TOTAL_UPLOAD_BYTES",
                str(400 * 1024**2 if hosted else 6 * 1024**3),
            )
        ),
    )
    maximum_duration_ms = max(
        60_000,
        int(
            os.getenv(
                "NOTESBUDDY_MAX_DURATION_MS",
                str(2 * 60 * 60 * 1000),
            )
        ),
    )
    maximum_analysis_characters = max(
        10_000,
        int(os.getenv("NOTESBUDDY_MAX_ANALYSIS_CHARACTERS", "180000")),
    )

    def _raise_session_error(error: SessionAccessError) -> NoReturn:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.detail,
        ) from error

    def model_configuration() -> dict[str, object]:
        status_provider = getattr(active_engine, "configuration_status", None)
        if callable(status_provider):
            return dict(status_provider())
        return {
            "ready": True,
            "source": "custom",
            "status": "custom engine configured",
        }

    def analysis_configuration() -> dict[str, object]:
        if active_analyzer is None:
            return {
                "ready": False,
                "model": None,
                "status": "professional analysis is not configured",
            }
        status_provider = getattr(active_analyzer, "configuration_status", None)
        if callable(status_provider):
            return dict(status_provider())
        return {
            "ready": True,
            "model": getattr(active_analyzer, "name", "configured analyzer"),
            "status": "professional analysis configured",
        }

    def system_audio_configuration() -> dict[str, object]:
        return {
            "available": bool(
                not hosted and getattr(active_system_audio, "available", False)
            ),
            "backend": str(
                getattr(active_system_audio, "backend_name", "unavailable")
            ),
        }

    def _raise_system_audio_error(error: BaseException) -> NoReturn:
        if isinstance(error, SystemAudioCaptureNotFound):
            status_code = 404
        elif isinstance(error, SystemAudioCaptureConflict):
            status_code = 409
        else:
            status_code = 503
        raise HTTPException(status_code=status_code, detail=str(error)) from error

    def require_access(
        request: Request,
        supplied_pairing_token: Annotated[
            str | None,
            Header(alias="X-NotesBuddy-Pairing-Token"),
        ] = None,
        supplied_session_token: Annotated[
            str | None,
            Header(alias="X-NotesBuddy-Session-Token"),
        ] = None,
    ) -> str | None:
        if hosted:
            assert sessions is not None
            try:
                return sessions.require(supplied_session_token)
            except SessionAccessError as error:
                _raise_session_error(error)
        assert pairing_token is not None
        persistent_token_matches = bool(
            supplied_pairing_token
            and hmac.compare_digest(supplied_pairing_token, pairing_token)
        )
        if not persistent_token_matches and not browser_pairings.accepts(
            supplied_pairing_token,
            origin=request.headers.get("origin"),
        ):
            raise HTTPException(
                status_code=401,
                detail="Pairing token is missing or invalid.",
            )
        return None

    def health_access(
        request: Request,
        supplied_pairing_token: Annotated[
            str | None,
            Header(alias="X-NotesBuddy-Pairing-Token"),
        ] = None,
    ) -> None:
        if hosted:
            return
        assert pairing_token is not None
        persistent_token_matches = bool(
            supplied_pairing_token
            and hmac.compare_digest(supplied_pairing_token, pairing_token)
        )
        if not persistent_token_matches and not browser_pairings.accepts(
            supplied_pairing_token,
            origin=request.headers.get("origin"),
        ):
            raise HTTPException(
                status_code=401,
                detail="Pairing token is missing or invalid.",
            )

    def require_local_system_audio_access(
        request: Request,
        supplied_pairing_token: Annotated[
            str | None,
            Header(alias="X-NotesBuddy-Pairing-Token"),
        ] = None,
    ) -> None:
        if hosted:
            raise HTTPException(status_code=404, detail="Route was not found.")
        require_access(
            request,
            supplied_pairing_token=supplied_pairing_token,
        )

    @app.get("/v1/companion")
    def companion_discovery(response: Response) -> dict[str, Any]:
        if hosted:
            raise HTTPException(status_code=404, detail="Route was not found.")
        response.headers["Cache-Control"] = "no-store"
        model_status = model_configuration()
        analysis_status = analysis_configuration()
        system_audio_status = system_audio_configuration()
        return {
            "product": "NotesBuddy Desktop Companion",
            "version": companion_version or "development",
            "apiVersion": 1,
            "status": "available",
            "browserPairing": browser_pairing_enabled,
            "engine": getattr(
                active_engine,
                "name",
                active_engine.__class__.__name__,
            ),
            "modelsReady": bool(model_status.get("ready")),
            "modelSource": str(model_status.get("source") or "unknown"),
            "modelStatus": str(model_status.get("status") or "unknown"),
            "modelDevice": str(model_status.get("device") or "unknown"),
            "modelComputeType": str(
                model_status.get("computeType") or "unknown"
            ),
            "accelerator": str(model_status.get("accelerator") or "CPU"),
            "gpuAvailable": bool(model_status.get("gpuAvailable")),
            "analysisAvailable": bool(analysis_status.get("ready")),
            "analysisModel": analysis_status.get("model"),
            "systemAudioCapture": bool(system_audio_status["available"]),
            "systemAudioBackend": system_audio_status["backend"],
            "storage": "temporary job files only",
        }

    @app.post("/v1/pairings")
    def create_browser_pairing(
        request: Request,
        response: Response,
    ) -> dict[str, Any]:
        if hosted or not browser_pairing_enabled:
            raise HTTPException(status_code=404, detail="Route was not found.")
        origin = request.headers.get("origin", "")
        if (
            not origin
            or origin == "null"
            or origin not in trusted_origins
        ):
            raise HTTPException(
                status_code=403,
                detail="This website is not trusted by the desktop companion.",
            )
        token, pairing = browser_pairings.issue(origin)
        response.headers["Cache-Control"] = "no-store"
        return {
            "pairingToken": token,
            "expiresAt": pairing.expires_at,
            "origin": pairing.origin,
        }

    @app.get("/v1/health", dependencies=[Depends(health_access)])
    def health(response: Response) -> dict[str, Any]:
        response.headers["Cache-Control"] = "no-store"
        model_status = model_configuration()
        analysis_status = analysis_configuration()
        system_audio_status = system_audio_configuration()
        return {
            "status": "ok",
            "engine": getattr(
                active_engine,
                "name",
                active_engine.__class__.__name__,
            ),
            "modelsReady": bool(model_status.get("ready")),
            "modelSource": str(model_status.get("source") or "unknown"),
            "modelStatus": str(model_status.get("status") or "unknown"),
            "modelDevice": str(model_status.get("device") or "unknown"),
            "modelComputeType": str(
                model_status.get("computeType") or "unknown"
            ),
            "accelerator": str(model_status.get("accelerator") or "CPU"),
            "gpuAvailable": bool(model_status.get("gpuAvailable")),
            "analysisAvailable": bool(analysis_status.get("ready")),
            "analysisModel": analysis_status.get("model"),
            "systemAudioCapture": bool(system_audio_status["available"]),
            "systemAudioBackend": system_audio_status["backend"],
            "storage": "temporary job files only",
            "access": "anonymous-session" if hosted else "local-pairing",
        }

    @app.post("/v1/system-audio/captures")
    def start_system_audio_capture(
        response: Response,
        _access: None = Depends(require_local_system_audio_access),
    ) -> dict[str, Any]:
        if hosted:
            raise HTTPException(status_code=404, detail="Route was not found.")
        try:
            capture = active_system_audio.start()
        except (
            SystemAudioUnavailable,
            SystemAudioCaptureConflict,
            SystemAudioCaptureNotFound,
        ) as error:
            _raise_system_audio_error(error)
        response.headers["Cache-Control"] = "no-store"
        return capture.public()

    @app.get("/v1/system-audio/captures/{capture_id}")
    def get_system_audio_capture(
        capture_id: str,
        response: Response,
        _access: None = Depends(require_local_system_audio_access),
    ) -> dict[str, Any]:
        if hosted:
            raise HTTPException(status_code=404, detail="Route was not found.")
        try:
            capture = active_system_audio.get(capture_id)
        except (
            SystemAudioUnavailable,
            SystemAudioCaptureConflict,
            SystemAudioCaptureNotFound,
        ) as error:
            _raise_system_audio_error(error)
        response.headers["Cache-Control"] = "no-store"
        return capture.public()

    @app.post("/v1/system-audio/captures/{capture_id}/pause")
    def pause_system_audio_capture(
        capture_id: str,
        response: Response,
        _access: None = Depends(require_local_system_audio_access),
    ) -> dict[str, Any]:
        if hosted:
            raise HTTPException(status_code=404, detail="Route was not found.")
        try:
            capture = active_system_audio.pause(capture_id)
        except (
            SystemAudioUnavailable,
            SystemAudioCaptureConflict,
            SystemAudioCaptureNotFound,
        ) as error:
            _raise_system_audio_error(error)
        response.headers["Cache-Control"] = "no-store"
        return capture.public()

    @app.post("/v1/system-audio/captures/{capture_id}/resume")
    def resume_system_audio_capture(
        capture_id: str,
        response: Response,
        _access: None = Depends(require_local_system_audio_access),
    ) -> dict[str, Any]:
        if hosted:
            raise HTTPException(status_code=404, detail="Route was not found.")
        try:
            capture = active_system_audio.resume(capture_id)
        except (
            SystemAudioUnavailable,
            SystemAudioCaptureConflict,
            SystemAudioCaptureNotFound,
        ) as error:
            _raise_system_audio_error(error)
        response.headers["Cache-Control"] = "no-store"
        return capture.public()

    @app.post("/v1/system-audio/captures/{capture_id}/stop")
    def stop_system_audio_capture(
        capture_id: str,
        _access: None = Depends(require_local_system_audio_access),
    ) -> Response:
        if hosted:
            raise HTTPException(status_code=404, detail="Route was not found.")
        try:
            capture = active_system_audio.stop(capture_id)
        except (
            SystemAudioUnavailable,
            SystemAudioCaptureConflict,
            SystemAudioCaptureNotFound,
        ) as error:
            _raise_system_audio_error(error)
        return FileResponse(
            capture.path,
            media_type="audio/wav",
            filename="notesbuddy-windows-audio.wav",
            headers={"Cache-Control": "no-store"},
            background=BackgroundTask(active_system_audio.discard, capture_id),
        )

    @app.delete("/v1/system-audio/captures/{capture_id}")
    def cancel_system_audio_capture(
        capture_id: str,
        response: Response,
        _access: None = Depends(require_local_system_audio_access),
    ) -> dict[str, Any]:
        if hosted:
            raise HTTPException(status_code=404, detail="Route was not found.")
        try:
            capture = active_system_audio.cancel(capture_id)
        except (
            SystemAudioUnavailable,
            SystemAudioCaptureConflict,
            SystemAudioCaptureNotFound,
        ) as error:
            _raise_system_audio_error(error)
        response.headers["Cache-Control"] = "no-store"
        return capture.public()

    @app.post("/v1/sessions")
    def create_session(request: Request, response: Response) -> dict[str, Any]:
        if not hosted or sessions is None:
            raise HTTPException(status_code=404, detail="Route was not found.")
        client_host = request.client.host if request.client else "unknown"
        try:
            token, session = sessions.issue(anonymise_client_key(client_host))
        except SessionAccessError as error:
            _raise_session_error(error)
        response.headers["Cache-Control"] = "no-store"
        return {
            "sessionToken": token,
            "expiresAt": session.expires_at,
            "access": "anonymous",
        }

    @app.post("/v1/analyses")
    def create_meeting_analysis(
        response: Response,
        payload: Annotated[dict[str, Any], Body()],
        owner_digest: str | None = Depends(require_access),
    ) -> dict[str, Any]:
        if active_analyzer is None:
            raise HTTPException(
                status_code=503,
                detail="Professional meeting analysis is not configured on this service.",
            )
        segments = payload.get("segments")
        if not isinstance(segments, list) or not segments:
            raise HTTPException(
                status_code=400,
                detail="A completed transcript is required for meeting analysis.",
            )
        transcript_characters = sum(
            len(str(segment.get("text") or ""))
            for segment in segments
            if isinstance(segment, dict)
        )
        if transcript_characters > maximum_analysis_characters:
            raise HTTPException(
                status_code=413,
                detail="The transcript exceeds the configured analysis limit.",
            )

        reservation_owned = False
        if hosted:
            assert sessions is not None
            assert owner_digest is not None
            try:
                sessions.reserve_job(owner_digest)
                reservation_owned = True
            except SessionAccessError as error:
                _raise_session_error(error)
        try:
            result = active_analyzer.analyze(
                segments=segments,
                meeting_title=payload.get("meetingTitle"),
            )
        except MeetingAnalysisUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except Exception as error:  # noqa: BLE001 - return a safe service error
            raise HTTPException(
                status_code=503,
                detail="Professional meeting analysis failed. Try again shortly.",
            ) from error
        finally:
            if reservation_owned and sessions is not None:
                sessions.release_job(owner_digest)
        response.headers["Cache-Control"] = "no-store"
        return dict(result)

    @app.post("/v1/transcriptions")
    async def create_transcription(
        response: Response,
        owner_digest: str | None = Depends(require_access),
        microphone: Annotated[UploadFile | None, File()] = None,
        meeting: Annotated[UploadFile | None, File()] = None,
        mixed: Annotated[UploadFile | None, File()] = None,
        metadata: Annotated[str, Form()] = "{}",
    ) -> dict[str, Any]:
        uploads = {
            source: upload
            for source, upload in {
                "microphone": microphone,
                "meeting": meeting,
                "mixed": mixed,
            }.items()
            if upload is not None
        }
        if not uploads:
            raise HTTPException(
                status_code=400,
                detail="At least one recording source is required.",
            )
        if len(metadata.encode("utf-8")) > 64 * 1024:
            raise HTTPException(status_code=413, detail="Metadata is too large.")
        try:
            parsed_metadata = json.loads(metadata)
        except json.JSONDecodeError as error:
            raise HTTPException(
                status_code=400,
                detail="Metadata must be a valid JSON object.",
            ) from error
        if not isinstance(parsed_metadata, dict):
            raise HTTPException(
                status_code=400,
                detail="Metadata must be a JSON object.",
            )
        if hosted:
            try:
                requested_duration_ms = int(parsed_metadata.get("durationMs", 0))
            except (TypeError, ValueError):
                requested_duration_ms = 0
            if requested_duration_ms > maximum_duration_ms:
                raise HTTPException(
                    status_code=413,
                    detail="The recording duration exceeds the public service limit.",
                )

        reservation_owned = False
        if hosted:
            assert sessions is not None
            assert owner_digest is not None
            try:
                sessions.reserve_job(owner_digest)
                reservation_owned = True
            except SessionAccessError as error:
                _raise_session_error(error)

        work_dir = Path(tempfile.mkdtemp(prefix="notesbuddy-job-"))
        paths: dict[str, Path] = {}
        total_upload_bytes = 0
        try:
            for source, upload in uploads.items():
                path, source_bytes = await _save_upload(
                    upload,
                    source=source,
                    work_dir=work_dir,
                    maximum_bytes=maximum_source_bytes,
                )
                paths[source] = path
                total_upload_bytes += source_bytes
                if total_upload_bytes > maximum_total_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail="The combined recordings exceed the configured limit.",
                    )
            job = Job(
                id=f"job-{uuid4()}",
                work_dir=work_dir,
                metadata=parsed_metadata,
                paths=paths,
                engine_name=getattr(
                    active_engine,
                    "name",
                    active_engine.__class__.__name__,
                ),
                owner_digest=owner_digest,
                on_terminal=sessions.release_job if sessions is not None else None,
            )
            if not jobs.add(job):
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "The public transcription queue is full."
                        if hosted
                        else "The local transcription queue is full."
                    ),
                )
            try:
                executor.submit(_run_job, job, active_engine)
            except RuntimeError as error:
                jobs.remove(job.id)
                raise HTTPException(
                    status_code=503,
                    detail="The transcription worker is unavailable.",
                ) from error
            reservation_owned = False
            response.headers["Cache-Control"] = "no-store"
            return job.public()
        except Exception:
            shutil.rmtree(work_dir, ignore_errors=True)
            if reservation_owned and sessions is not None:
                sessions.release_job(owner_digest)
            raise

    def _owned_job(job_id: str, owner_digest: str | None) -> Job:
        job = jobs.get(job_id)
        if job is None or job.owner_digest != owner_digest:
            raise HTTPException(status_code=404, detail="Job was not found.")
        return job

    @app.get("/v1/transcriptions/{job_id}")
    def get_transcription(
        job_id: str,
        response: Response,
        owner_digest: str | None = Depends(require_access),
    ) -> dict[str, Any]:
        job = _owned_job(job_id, owner_digest)
        response.headers["Cache-Control"] = "no-store"
        return job.public()

    @app.delete("/v1/transcriptions/{job_id}")
    def cancel_transcription(
        job_id: str,
        response: Response,
        owner_digest: str | None = Depends(require_access),
    ) -> dict[str, Any]:
        job = _owned_job(job_id, owner_digest)
        job.cancel_event.set()
        with job.lock:
            if job.status in {"queued", "processing"}:
                job.status = "cancelled"
                job.stage = "cancellation requested"
                job.completed_at = _now()
                job.completed_monotonic = time.monotonic()
        response.headers["Cache-Control"] = "no-store"
        return job.public()

    return app
