"""Shared best-effort diagnostic logging for the desktop companion."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path


def diagnostic_log_path() -> Path:
    configured = os.getenv("NOTESBUDDY_LOG_DIR", "").strip()
    if configured:
        return Path(configured).expanduser() / "companion.log"
    base = os.getenv("LOCALAPPDATA", "").strip()
    root = Path(base) / "NotesBuddy" if base else Path.home() / ".notesbuddy"
    return root / "logs" / "companion.log"


def log_diagnostic(message: str) -> None:
    """Best-effort diagnostic logging for the local companion pipeline.

    A packaged windowed build (``console=False``) has no console, and
    PyInstaller's own bootloader replaces ``sys.stdout``/``sys.stderr`` with a
    null writer for that build type even when the launching process redirects
    them to a real file -- ``print()`` alone is silently discarded in the
    shipped .exe, which is why earlier diagnostic prints never appeared in a
    log file captured that way. Writing to a fixed file directly bypasses
    that bootloader behaviour; the print() call is kept too since it works
    fine when running from source in a real console.
    """

    line = f"{datetime.now(timezone.utc).isoformat()} {message}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        log_path = diagnostic_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass
