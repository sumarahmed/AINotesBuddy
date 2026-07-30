"""Short-lived browser pairing for the local NotesBuddy companion."""

from __future__ import annotations

import hashlib
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class BrowserPairing:
    token_digest: str
    origin: str
    created_monotonic: float
    expires_monotonic: float
    expires_at: str


class BrowserPairingStore:
    """Bounded in-memory tokens issued only after an origin is trusted."""

    def __init__(
        self,
        *,
        ttl_seconds: int,
        maximum_pairings: int,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("Browser pairing TTL must be positive.")
        if maximum_pairings <= 0:
            raise ValueError("Maximum browser pairings must be positive.")
        self._ttl_seconds = ttl_seconds
        self._maximum_pairings = maximum_pairings
        self._monotonic = monotonic
        self._pairings: dict[str, BrowserPairing] = {}
        self._lock = threading.Lock()

    def _cleanup_locked(self, now: float) -> None:
        expired = [
            digest
            for digest, pairing in self._pairings.items()
            if now >= pairing.expires_monotonic
        ]
        for digest in expired:
            self._pairings.pop(digest, None)

    def issue(self, origin: str) -> tuple[str, BrowserPairing]:
        now = self._monotonic()
        token = secrets.token_urlsafe(32)
        pairing = BrowserPairing(
            token_digest=_token_digest(token),
            origin=origin,
            created_monotonic=now,
            expires_monotonic=now + self._ttl_seconds,
            expires_at=(
                datetime.now(UTC) + timedelta(seconds=self._ttl_seconds)
            ).isoformat(),
        )
        with self._lock:
            self._cleanup_locked(now)
            if len(self._pairings) >= self._maximum_pairings:
                oldest = min(
                    self._pairings.values(),
                    key=lambda existing: existing.created_monotonic,
                )
                self._pairings.pop(oldest.token_digest, None)
            self._pairings[pairing.token_digest] = pairing
        return token, pairing

    def accepts(self, token: str | None, *, origin: str | None) -> bool:
        if not token or not origin:
            return False
        now = self._monotonic()
        digest = _token_digest(token)
        with self._lock:
            self._cleanup_locked(now)
            pairing = self._pairings.get(digest)
            return (
                pairing is not None
                and now < pairing.expires_monotonic
                and pairing.origin == origin
            )
