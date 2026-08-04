"""Local Microsoft Teams meeting detection and Windows notification handoff."""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TEAMS_PROCESS_NAMES = {
    "ms-teams.exe",
    "msteams.exe",
    "teams.exe",
}
DEFAULT_POLL_SECONDS = 2.0
MICROPHONE_CONFIRM_SECONDS = 4.0
AUDIO_CONFIRM_SECONDS = 14.0
MEETING_CLEAR_SECONDS = 45.0


@dataclass(frozen=True)
class TeamsSignal:
    """One local observation of Teams communication activity."""

    audio_active: bool = False
    microphone_active: bool = False

    @property
    def present(self) -> bool:
        return self.audio_active or self.microphone_active

    @property
    def confirmation_seconds(self) -> float:
        return (
            MICROPHONE_CONFIRM_SECONDS
            if self.microphone_active
            else AUDIO_CONFIRM_SECONDS
        )


class TeamsMeetingState:
    """Debounce Teams signals and notify once for each continuous meeting."""

    def __init__(self, *, clear_seconds: float = MEETING_CLEAR_SECONDS) -> None:
        self.clear_seconds = max(1.0, float(clear_seconds))
        self.candidate_started_at: float | None = None
        self.quiet_started_at: float | None = None
        self.meeting_active = False

    def reset(self) -> None:
        self.candidate_started_at = None
        self.quiet_started_at = None
        self.meeting_active = False

    def update(self, signal: TeamsSignal, *, now: float) -> bool:
        """Return true only when a newly confirmed meeting should notify."""

        if signal.present:
            self.quiet_started_at = None
            if self.meeting_active:
                return False
            if self.candidate_started_at is None:
                self.candidate_started_at = now
                return False
            if now - self.candidate_started_at >= signal.confirmation_seconds:
                self.meeting_active = True
                self.candidate_started_at = None
                return True
            return False

        self.candidate_started_at = None
        if not self.meeting_active:
            self.quiet_started_at = None
            return False
        if self.quiet_started_at is None:
            self.quiet_started_at = now
        elif now - self.quiet_started_at >= self.clear_seconds:
            self.reset()
        return False


def _session_process_name(session: Any) -> str:
    try:
        process = session.Process
        if process is None:
            return ""
        name = process.name() if callable(process.name) else process.name
        return str(name or "").strip().lower()
    except (AttributeError, OSError, RuntimeError):
        return ""


def _session_is_active(session: Any) -> bool:
    try:
        state = session.State
    except (AttributeError, OSError, RuntimeError):
        return False
    value = getattr(state, "value", state)
    if value == 1:
        return True
    return str(state).rsplit(".", 1)[-1].strip().lower() == "active"


def teams_audio_active(sessions: Iterable[Any]) -> bool:
    return any(
        _session_process_name(session) in TEAMS_PROCESS_NAMES
        and _session_is_active(session)
        for session in sessions
    )


def _default_audio_sessions() -> Iterable[Any]:
    if sys.platform != "win32":
        return ()
    from pycaw.pycaw import AudioUtilities

    return AudioUtilities.GetAllSessions()


def teams_microphone_active() -> bool:
    """Read Windows' local microphone-use ledger for Teams only."""

    if sys.platform != "win32":
        return False
    import winreg

    root_path = (
        r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager"
        r"\ConsentStore\microphone"
    )

    def visit(path: str, *, depth: int) -> bool:
        if depth > 8:
            return False
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path)
        except OSError:
            return False
        try:
            if "teams" in path.lower():
                try:
                    started = int(winreg.QueryValueEx(key, "LastUsedTimeStart")[0])
                    stopped = int(winreg.QueryValueEx(key, "LastUsedTimeStop")[0])
                except (OSError, TypeError, ValueError):
                    started = 0
                    stopped = -1
                if started > 0 and stopped == 0:
                    return True
            try:
                subkey_count = winreg.QueryInfoKey(key)[0]
            except OSError:
                subkey_count = 0
            for index in range(subkey_count):
                try:
                    name = winreg.EnumKey(key, index)
                except OSError:
                    continue
                if visit(f"{path}\\{name}", depth=depth + 1):
                    return True
            return False
        finally:
            winreg.CloseKey(key)

    return visit(root_path, depth=0)


def probe_teams_signal(
    *,
    session_provider: Callable[[], Iterable[Any]] = _default_audio_sessions,
    microphone_probe: Callable[[], bool] = teams_microphone_active,
) -> TeamsSignal:
    try:
        audio_active = teams_audio_active(session_provider())
    except Exception:  # noqa: BLE001 - detection must never stop the companion
        audio_active = False
    try:
        microphone_active = bool(microphone_probe())
    except Exception:  # noqa: BLE001 - detection must never stop the companion
        microphone_active = False
    return TeamsSignal(
        audio_active=audio_active,
        microphone_active=microphone_active,
    )


def teams_capture_url(web_url: str) -> str:
    parts = urlsplit(str(web_url).strip())
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update({"action": "capture", "source": "teams"})
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def show_teams_meeting_notification(web_url: str) -> bool:
    """Show a Windows toast whose body opens NotesBuddy's capture screen."""

    if sys.platform != "win32":
        return False
    try:
        from windows_toasts import Toast, WindowsToaster

        toast = Toast(
            text_fields=(
                "Teams meeting detected",
                "Open NotesBuddy to review audio sources and start recording.",
            ),
            launch_action=teams_capture_url(web_url),
        )
        WindowsToaster("NotesBuddy Desktop Companion").show_toast(toast)
        return True
    except Exception:  # noqa: BLE001 - the tray fallback remains available
        return False


class TeamsMeetingMonitor:
    """Poll Teams activity on one daemon thread."""

    def __init__(
        self,
        *,
        on_detected: Callable[[TeamsSignal], None],
        enabled: Callable[[], bool],
        probe: Callable[[], TeamsSignal] = probe_teams_signal,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
        state: TeamsMeetingState | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.on_detected = on_detected
        self.enabled = enabled
        self.probe = probe
        self.poll_seconds = max(0.1, float(poll_seconds))
        self.state = state or TeamsMeetingState()
        self.clock = clock
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="notesbuddy-teams-detector",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(2.0, self.poll_seconds + 0.5))
        self._thread = None

    def _run(self) -> None:
        com_initialized = False
        if sys.platform == "win32":
            try:
                import comtypes

                comtypes.CoInitialize()
                com_initialized = True
            except (ImportError, OSError):
                pass
        try:
            while not self._stop.is_set():
                if not self.enabled():
                    self.state.reset()
                else:
                    signal = self.probe()
                    if self.state.update(signal, now=self.clock()):
                        try:
                            self.on_detected(signal)
                        except Exception:  # noqa: BLE001 - continue monitoring
                            pass
                self._stop.wait(self.poll_seconds)
        finally:
            if com_initialized:
                try:
                    import comtypes

                    comtypes.CoUninitialize()
                except (ImportError, OSError):
                    pass
