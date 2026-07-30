"""Anonymous hosted-session access controls for transcription jobs."""

from __future__ import annotations

import hashlib
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


class SessionAccessError(RuntimeError):
    """A safe client-facing hosted-session access failure."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def anonymise_client_key(value: str) -> str:
    """Avoid retaining a raw client IP address in the rate-limit store."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class AnonymousSession:
    token_digest: str
    client_key: str
    created_monotonic: float
    expires_monotonic: float
    expires_at: str
    job_starts: deque[float] = field(default_factory=deque)
    active_jobs: int = 0


class AnonymousSessionStore:
    """Short-lived anonymous sessions with bounded per-client compute usage."""

    def __init__(
        self,
        *,
        session_ttl_seconds: int,
        maximum_sessions: int,
        issue_window_seconds: int,
        maximum_issues_per_client: int,
        job_window_seconds: int,
        maximum_jobs_per_session: int,
        maximum_active_jobs_per_session: int,
    ) -> None:
        self._session_ttl_seconds = session_ttl_seconds
        self._maximum_sessions = maximum_sessions
        self._issue_window_seconds = issue_window_seconds
        self._maximum_issues_per_client = maximum_issues_per_client
        self._job_window_seconds = job_window_seconds
        self._maximum_jobs_per_session = maximum_jobs_per_session
        self._maximum_active_jobs_per_session = maximum_active_jobs_per_session
        self._sessions: dict[str, AnonymousSession] = {}
        self._issues: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _prune_window(values: deque[float], *, now: float, window: int) -> None:
        while values and now - values[0] >= window:
            values.popleft()

    def _cleanup_locked(self, now: float) -> None:
        expired = [
            digest
            for digest, session in self._sessions.items()
            if now >= session.expires_monotonic and session.active_jobs == 0
        ]
        for digest in expired:
            self._sessions.pop(digest, None)

        empty_clients: list[str] = []
        for client_key, issues in self._issues.items():
            self._prune_window(
                issues,
                now=now,
                window=self._issue_window_seconds,
            )
            if not issues:
                empty_clients.append(client_key)
        for client_key in empty_clients:
            self._issues.pop(client_key, None)

    def issue(self, client_key: str) -> tuple[str, AnonymousSession]:
        now = time.monotonic()
        with self._lock:
            self._cleanup_locked(now)
            issues = self._issues.setdefault(client_key, deque())
            self._prune_window(
                issues,
                now=now,
                window=self._issue_window_seconds,
            )
            if len(issues) >= self._maximum_issues_per_client:
                raise SessionAccessError(
                    429,
                    "Too many anonymous sessions were created from this network. "
                    "Try again later.",
                )
            if len(self._sessions) >= self._maximum_sessions:
                raise SessionAccessError(
                    503,
                    "The public transcription service is at capacity.",
                )

            token = secrets.token_urlsafe(32)
            digest = _token_digest(token)
            expires_at = (
                datetime.now(UTC) + timedelta(seconds=self._session_ttl_seconds)
            ).isoformat()
            session = AnonymousSession(
                token_digest=digest,
                client_key=client_key,
                created_monotonic=now,
                expires_monotonic=now + self._session_ttl_seconds,
                expires_at=expires_at,
            )
            self._sessions[digest] = session
            issues.append(now)
            return token, session

    def require(self, token: str | None) -> str:
        if not token:
            raise SessionAccessError(
                401,
                "An anonymous transcription session is required.",
            )
        digest = _token_digest(token)
        now = time.monotonic()
        with self._lock:
            self._cleanup_locked(now)
            session = self._sessions.get(digest)
            if session is None or now >= session.expires_monotonic:
                raise SessionAccessError(
                    401,
                    "The anonymous transcription session expired. Start a new session.",
                )
            return digest

    def reserve_job(self, token_digest: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._cleanup_locked(now)
            session = self._sessions.get(token_digest)
            if session is None or now >= session.expires_monotonic:
                raise SessionAccessError(
                    401,
                    "The anonymous transcription session expired. Start a new session.",
                )
            self._prune_window(
                session.job_starts,
                now=now,
                window=self._job_window_seconds,
            )
            if session.active_jobs >= self._maximum_active_jobs_per_session:
                raise SessionAccessError(
                    429,
                    "This browser already has a transcription in progress.",
                )
            if len(session.job_starts) >= self._maximum_jobs_per_session:
                raise SessionAccessError(
                    429,
                    "This browser reached the public transcription limit. "
                    "Try again later.",
                )
            session.job_starts.append(now)
            session.active_jobs += 1

    def release_job(self, token_digest: str | None) -> None:
        if not token_digest:
            return
        with self._lock:
            session = self._sessions.get(token_digest)
            if session is not None:
                session.active_jobs = max(0, session.active_jobs - 1)
