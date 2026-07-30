"""Pairing-token storage for the localhost companion."""

from __future__ import annotations

import os
import secrets
from pathlib import Path


def default_token_path() -> Path:
    configured = os.getenv("NOTESBUDDY_TOKEN_FILE", "").strip()
    if configured:
        return Path(configured).expanduser()
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data) / "NotesBuddy" / "transcription-pairing-token"
    config_home = os.getenv("XDG_CONFIG_HOME", "").strip()
    if config_home:
        return Path(config_home) / "notesbuddy" / "transcription-pairing-token"
    return Path.home() / ".config" / "notesbuddy" / "transcription-pairing-token"


def ensure_pairing_token(path: Path | None = None) -> tuple[str, Path, bool]:
    """Read or atomically create a persistent 256-bit local pairing token."""

    explicit = os.getenv("NOTESBUDDY_PAIRING_TOKEN", "").strip()
    token_path = path or default_token_path()
    if explicit:
        if len(explicit) < 24:
            raise RuntimeError(
                "NOTESBUDDY_PAIRING_TOKEN must contain at least 24 characters."
            )
        return explicit, token_path, False

    try:
        existing = token_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        existing = ""
    if existing:
        if len(existing) < 24:
            raise RuntimeError(
                f"The pairing token in {token_path} is too short. Remove it "
                "and restart the companion to generate a replacement."
            )
        return existing, token_path, False

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    try:
        descriptor = os.open(
            token_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError:
        token = token_path.read_text(encoding="utf-8").strip()
        return token, token_path, False
    with os.fdopen(descriptor, "w", encoding="utf-8") as token_file:
        token_file.write(f"{token}\n")
    try:
        token_path.chmod(0o600)
    except OSError:
        # Windows permissions are inherited from the user's profile directory.
        pass
    return token, token_path, True
