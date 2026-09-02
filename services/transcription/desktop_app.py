"""Windows desktop launcher for the NotesBuddy local companion."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

from teams_detection import (
    TeamsMeetingMonitor,
    TeamsSignal,
    show_teams_meeting_notification,
    teams_capture_url,
)

COMPANION_VERSION = "2026.09.02"
DEFAULT_PORT = 8765
DEFAULT_WEB_URL = "https://sumarahmed.github.io/AINotesBuddy/"
AUTOSTART_VALUE_NAME = "NotesBuddyCompanion"
RELEASES_URL = "https://github.com/sumarahmed/AINotesBuddy/releases"
LATEST_RELEASE_API_URL = (
    "https://api.github.com/repos/sumarahmed/AINotesBuddy/releases/latest"
)
UPDATE_CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000
DEFAULT_COMPANION_SETTINGS = {"teamsMeetingNotifications": True}


def version_parts(value: str) -> tuple[int, int, int] | None:
    match = re.search(r"(?:^|v)(\d+)\.(\d+)\.(\d+)$", str(value).strip(), re.I)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def is_version_outdated(installed: str, latest: str) -> bool:
    installed_parts = version_parts(installed)
    latest_parts = version_parts(latest)
    return bool(
        installed_parts is not None
        and latest_parts is not None
        and installed_parts < latest_parts
    )


def fetch_latest_companion_release(
    *,
    opener: Any = urllib.request.urlopen,
    timeout: float = 4,
) -> dict[str, Any]:
    request = urllib.request.Request(
        LATEST_RELEASE_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"NotesBuddy-Companion/{COMPANION_VERSION}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    with opener(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    tag = str(payload.get("tag_name") or "")
    latest_version_parts = version_parts(tag)
    if latest_version_parts is None:
        raise ValueError("The latest companion release has an invalid version tag.")
    latest_version = (
        f"{latest_version_parts[0]:04d}."
        f"{latest_version_parts[1]:02d}."
        f"{latest_version_parts[2]}"
    )
    release_url = str(payload.get("html_url") or RELEASES_URL)
    if not release_url.startswith(f"{RELEASES_URL}/"):
        release_url = RELEASES_URL
    asset_url = ""
    for asset in payload.get("assets") or []:
        name = str(asset.get("name") or "")
        candidate = str(asset.get("browser_download_url") or "")
        if (
            name.lower().endswith(".exe")
            and candidate.startswith(
                "https://github.com/sumarahmed/AINotesBuddy/releases/download/"
            )
        ):
            asset_url = candidate
            break
    return {
        "available": is_version_outdated(COMPANION_VERSION, latest_version),
        "currentVersion": COMPANION_VERSION,
        "latestVersion": latest_version,
        "releaseUrl": release_url,
        "downloadUrl": asset_url or release_url,
    }


def companion_endpoint(port: int) -> str:
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535.")
    return f"http://127.0.0.1:{port}"


def probe_companion(port: int, *, timeout: float = 0.5) -> dict[str, Any] | None:
    request = urllib.request.Request(
        f"{companion_endpoint(port)}/v1/companion",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (
        OSError,
        TimeoutError,
        ValueError,
        urllib.error.URLError,
    ):
        return None
    if payload.get("product") != "NotesBuddy Desktop Companion":
        return None
    return payload


def build_autostart_command(
    *,
    executable: str | None = None,
    script_path: str | None = None,
    frozen: bool | None = None,
) -> str:
    active_executable = executable or sys.executable
    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    arguments = [active_executable]
    if not is_frozen:
        arguments.append(script_path or str(Path(__file__).resolve()))
    arguments.append("--background")
    return subprocess.list2cmdline(arguments)


def autostart_enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
        ) as key:
            winreg.QueryValueEx(key, AUTOSTART_VALUE_NAME)
            return True
    except FileNotFoundError:
        return False


def set_autostart(enabled: bool) -> None:
    if sys.platform != "win32":
        raise RuntimeError("Start at sign-in is supported only on Windows.")
    import winreg

    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
    ) as key:
        if enabled:
            winreg.SetValueEx(
                key,
                AUTOSTART_VALUE_NAME,
                0,
                winreg.REG_SZ,
                build_autostart_command(),
            )
            return
        try:
            winreg.DeleteValue(key, AUTOSTART_VALUE_NAME)
        except FileNotFoundError:
            pass


def companion_settings_path() -> Path:
    base = os.getenv("LOCALAPPDATA")
    if base:
        return Path(base) / "NotesBuddy" / "companion-settings.json"
    return Path.home() / ".notesbuddy" / "companion-settings.json"


def load_companion_settings(path: Path | None = None) -> dict[str, Any]:
    settings = dict(DEFAULT_COMPANION_SETTINGS)
    target = path or companion_settings_path()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return settings
    if isinstance(payload, dict):
        settings["teamsMeetingNotifications"] = bool(
            payload.get("teamsMeetingNotifications", True)
        )
    return settings


def save_companion_settings(
    settings: dict[str, Any],
    path: Path | None = None,
) -> None:
    target = path or companion_settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "teamsMeetingNotifications": bool(
            settings.get("teamsMeetingNotifications", True)
        )
    }
    temporary = target.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temporary, target)


class CompanionServer:
    """Own a loopback-only Uvicorn server running on a background thread."""

    def __init__(self, *, port: int, empty_engine: bool = False) -> None:
        from notesbuddy_transcription.security import ensure_pairing_token
        from notesbuddy_transcription.components import ComponentManager

        companion_endpoint(port)
        self.port = port
        self.empty_engine = empty_engine
        self.token, self.token_path, self.token_created = ensure_pairing_token()
        self.server: object | None = None
        self.thread: threading.Thread | None = None
        self.started_here = False
        self.error: str | None = None
        self.components = ComponentManager()

    def start(self) -> str:
        if probe_companion(self.port) is not None:
            return "existing"

        try:
            import uvicorn

            from notesbuddy_transcription.engine import EmptyEngine
            from notesbuddy_transcription.server import create_app

            engine = EmptyEngine() if self.empty_engine else None
            api = create_app(
                engine=engine,
                pairing_token=self.token,
                allow_browser_pairing=True,
                companion_version=COMPANION_VERSION,
                component_manager=self.components,
            )
            config = uvicorn.Config(
                api,
                host="127.0.0.1",
                port=self.port,
                access_log=False,
                log_level="warning",
                log_config=None,
            )
            self.server = uvicorn.Server(config)
            self.server.install_signal_handlers = lambda: None
            self.thread = threading.Thread(
                target=self.server.run,
                name="notesbuddy-local-api",
                daemon=True,
            )
            self.thread.start()
        except Exception as error:  # noqa: BLE001 - surfaced in the control panel
            self.error = str(error)
            return "failed"

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if probe_companion(self.port) is not None:
                self.started_here = True
                return "started"
            if self.thread is not None and not self.thread.is_alive():
                break
            time.sleep(0.05)
        self.error = (
            f"The local service could not start on 127.0.0.1:{self.port}. "
            "The port may already be used by another application."
        )
        return "failed"

    def stop(self) -> None:
        if not self.started_here or self.server is None:
            return
        self.server.should_exit = True
        if self.thread is not None:
            self.thread.join(timeout=5)
        self.started_here = False


class DesktopWindow:
    def __init__(
        self,
        *,
        server: CompanionServer,
        server_result: str,
        web_url: str,
        background: bool,
    ) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.server = server
        self.web_url = web_url
        self.background = background
        self.tray_icon = None
        self.update_check_running = False
        self.update_url = RELEASES_URL
        self.last_notified_version: str | None = None
        self.companion_settings = load_companion_settings()
        self.teams_notifications_enabled = bool(
            self.companion_settings["teamsMeetingNotifications"]
        )
        self.teams_monitor: TeamsMeetingMonitor | None = None

        self.root = tk.Tk()
        self.root.title(f"NotesBuddy Desktop Companion {COMPANION_VERSION}")
        self.root.geometry("580x590")
        self.root.minsize(540, 550)
        self.root.protocol("WM_DELETE_WINDOW", self._close_window)

        self.status = tk.StringVar(value="Starting local service…")
        self.detail = tk.StringVar(
            value=f"Private loopback address: {companion_endpoint(server.port)}"
        )
        self.update_status = tk.StringVar(value="Checking for updates shortly…")
        self.autostart = tk.BooleanVar(value=autostart_enabled())
        self.teams_notifications = tk.BooleanVar(
            value=self.teams_notifications_enabled
        )
        self.teams_detection_status = tk.StringVar(
            value=(
                "Watching for Microsoft Teams calls on this computer."
                if self.teams_notifications_enabled
                else "Teams meeting notifications are turned off."
            )
        )
        self._build()
        self._start_tray()
        if server_result == "started":
            self._start_teams_detection()
        self.root.after(0, self._show_server_result, server_result)
        self.root.after(800, self._start_update_check)

        if background:
            if self.tray_icon is not None:
                self.root.withdraw()
            else:
                self.root.iconify()

    def _build(self) -> None:
        ttk = self.ttk
        frame = ttk.Frame(self.root, padding=28)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="NotesBuddy Desktop Companion",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text=f"Version {COMPANION_VERSION}",
            foreground="#5b6470",
        ).pack(anchor="w", pady=(2, 0))
        ttk.Label(
            frame,
            text=(
                "Captures Windows meeting audio, transcribes it on this computer, "
                "and securely connects to the NotesBuddy website."
            ),
            wraplength=490,
        ).pack(anchor="w", pady=(8, 24))

        status_frame = ttk.LabelFrame(frame, text="Service status", padding=16)
        status_frame.pack(fill="x")
        ttk.Label(
            status_frame,
            textvariable=self.status,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            status_frame,
            textvariable=self.detail,
            wraplength=460,
        ).pack(anchor="w", pady=(5, 0))

        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(18, 10))
        ttk.Button(
            actions,
            text="Open NotesBuddy",
            command=self._open_site,
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Copy recovery token",
            command=self._copy_token,
        ).pack(side="left", padx=(10, 0))
        self.update_button = ttk.Button(
            actions,
            text="Download update",
            command=self._open_update,
            state="disabled",
        )
        self.update_button.pack(side="left", padx=(10, 0))

        ttk.Label(
            frame,
            textvariable=self.update_status,
            foreground="#5b6470",
            wraplength=490,
        ).pack(anchor="w", pady=(0, 4))

        ttk.Checkbutton(
            frame,
            text="Start the companion when I sign in to Windows",
            variable=self.autostart,
            command=self._toggle_autostart,
        ).pack(anchor="w", pady=(8, 0))

        meeting_frame = ttk.LabelFrame(
            frame,
            text="Teams meeting detection",
            padding=14,
        )
        meeting_frame.pack(fill="x", pady=(18, 0))
        ttk.Checkbutton(
            meeting_frame,
            text="Notify me when a Microsoft Teams meeting starts",
            variable=self.teams_notifications,
            command=self._toggle_teams_notifications,
        ).pack(anchor="w")
        ttk.Label(
            meeting_frame,
            textvariable=self.teams_detection_status,
            foreground="#5b6470",
            wraplength=480,
        ).pack(anchor="w", pady=(5, 0))
        ttk.Label(
            frame,
            text=(
                "Windows output is captured through WASAPI only while a recording "
                "is active. Audio stays on this computer and is sent only to "
                "127.0.0.1 for local processing."
            ),
            foreground="#5b6470",
            wraplength=490,
        ).pack(anchor="w", pady=(18, 0))

    def _show_server_result(self, result: str) -> None:
        if result == "started":
            self.status.set("Connected — Windows audio capture is available")
            self.detail.set(
                "Keep this companion running. The website will connect "
                "automatically without asking users for a token."
            )
            return
        if result == "existing":
            self.status.set("A NotesBuddy companion is already running")
            self.detail.set(
                "The existing loopback service will continue handling website "
                "requests. Close it first if you want to restart this version."
            )
            if self.background:
                self.root.after(250, self._quit)
            return
        self.status.set("Local service could not start")
        self.detail.set(self.server.error or "An unknown startup error occurred.")
        if self.background:
            self.root.deiconify()

    def _open_site(self) -> None:
        webbrowser.open(self.web_url)

    def _open_update(self) -> None:
        webbrowser.open(self.update_url)

    def _start_update_check(self) -> None:
        if self.update_check_running:
            return
        self.update_check_running = True
        self.update_status.set("Checking for companion updates…")
        threading.Thread(
            target=self._check_for_update,
            name="notesbuddy-update-check",
            daemon=True,
        ).start()

    def _check_for_update(self) -> None:
        try:
            result = fetch_latest_companion_release()
        except Exception as error:  # noqa: BLE001 - update checks must not stop capture
            result = {"error": str(error)}
        try:
            self.root.after(0, self._show_update_result, result)
        except (RuntimeError, self.tk.TclError):
            pass

    def _show_update_result(self, result: dict[str, Any]) -> None:
        self.update_check_running = False
        if result.get("available"):
            latest_version = str(result.get("latestVersion") or "a newer version")
            self.update_url = str(result.get("downloadUrl") or RELEASES_URL)
            self.update_status.set(
                f"Update {latest_version} is available. Recording will keep working."
            )
            self.update_button.configure(state="normal")
            if self.last_notified_version != latest_version:
                self.last_notified_version = latest_version
                if self.tray_icon is not None:
                    try:
                        self.tray_icon.notify(
                            f"Version {latest_version} is ready to download.",
                            "NotesBuddy update available",
                        )
                    except (AttributeError, NotImplementedError, OSError):
                        pass
                elif self.background:
                    self._show_window()
        elif result.get("error"):
            self.update_status.set(
                "Could not check for updates. Recording is still available."
            )
            self.update_button.configure(state="disabled")
        else:
            self.update_status.set(f"Version {COMPANION_VERSION} is up to date.")
            self.update_button.configure(state="disabled")
        try:
            self.root.after(UPDATE_CHECK_INTERVAL_MS, self._start_update_check)
        except self.tk.TclError:
            pass

    def _copy_token(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self.server.token)
        self.root.update()
        self.status.set("Recovery token copied")
        self.detail.set(
            "Use this only for manual troubleshooting. Normal website pairing "
            "does not require copying a token."
        )

    def _toggle_autostart(self) -> None:
        from tkinter import messagebox

        desired = bool(self.autostart.get())
        try:
            set_autostart(desired)
        except (OSError, RuntimeError) as error:
            self.autostart.set(not desired)
            messagebox.showerror("NotesBuddy", str(error), parent=self.root)

    def _toggle_teams_notifications(self) -> None:
        desired = bool(self.teams_notifications.get())
        self.teams_notifications_enabled = desired
        self.companion_settings["teamsMeetingNotifications"] = desired
        try:
            save_companion_settings(self.companion_settings)
        except OSError:
            self.teams_notifications_enabled = not desired
            self.teams_notifications.set(not desired)
            self.teams_detection_status.set(
                "The notification preference could not be saved."
            )
            return
        self.teams_detection_status.set(
            "Watching for Microsoft Teams calls on this computer."
            if desired
            else "Teams meeting notifications are turned off."
        )

    def _start_teams_detection(self) -> None:
        if self.teams_monitor is not None:
            return
        self.teams_monitor = TeamsMeetingMonitor(
            on_detected=self._teams_meeting_detected,
            enabled=lambda: self.teams_notifications_enabled,
        )
        self.teams_monitor.start()

    def _teams_meeting_detected(self, signal: TeamsSignal) -> None:
        actionable = show_teams_meeting_notification(self.web_url)
        try:
            self.root.after(
                0,
                self._show_teams_detection_result,
                actionable,
                signal,
            )
        except (RuntimeError, self.tk.TclError):
            pass

    def _show_teams_detection_result(
        self,
        actionable: bool,
        signal: TeamsSignal,
    ) -> None:
        evidence = (
            "microphone and meeting audio"
            if signal.microphone_active and signal.audio_active
            else "microphone activity"
            if signal.microphone_active
            else "meeting audio"
        )
        self.teams_detection_status.set(
            f"Teams {evidence} detected. Recording has not started."
        )
        if not actionable and self.tray_icon is not None:
            try:
                self.tray_icon.notify(
                    "Open NotesBuddy from the tray to start a capture.",
                    "Teams meeting detected",
                )
            except (AttributeError, NotImplementedError, OSError):
                pass

    def _start_tray(self) -> None:
        try:
            import pystray
            from PIL import Image, ImageDraw
        except ImportError:
            return

        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((4, 4, 60, 60), radius=16, fill="#176f67")
        draw.polygon(((25, 18), (25, 46), (47, 32)), fill="white")
        menu = pystray.Menu(
            pystray.MenuItem("Show companion", self._tray_show, default=True),
            pystray.MenuItem("Open NotesBuddy", self._tray_open),
            pystray.MenuItem(
                "Open NotesBuddy for Teams meeting",
                self._tray_open_teams,
            ),
            pystray.MenuItem("Quit", self._tray_quit),
        )
        self.tray_icon = pystray.Icon(
            "notesbuddy-companion",
            image,
            "NotesBuddy Desktop Companion",
            menu,
        )
        self.tray_icon.run_detached()

    def _tray_show(self, _icon=None, _item=None) -> None:
        self.root.after(0, self._show_window)

    def _tray_open(self, _icon=None, _item=None) -> None:
        self.root.after(0, self._open_site)

    def _tray_open_teams(self, _icon=None, _item=None) -> None:
        self.root.after(0, self._open_teams_capture)

    def _open_teams_capture(self) -> None:
        webbrowser.open(teams_capture_url(self.web_url))

    def _tray_quit(self, _icon=None, _item=None) -> None:
        self.root.after(0, self._quit)

    def _show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _close_window(self) -> None:
        if self.tray_icon is not None:
            self.root.withdraw()
            return
        self._quit()

    def _quit(self) -> None:
        if self.teams_monitor is not None:
            self.teams_monitor.stop()
            self.teams_monitor = None
        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
        self.server.stop()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def _available_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        return int(server_socket.getsockname()[1])


def self_test(
    *,
    require_models: bool = False,
    require_server: bool = False,
) -> dict[str, Any]:
    server_check: dict[str, Any] | None = None
    if require_server:
        companion_server = CompanionServer(
            port=_available_loopback_port(),
            empty_engine=True,
        )
        original_stdout, original_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout = None
            sys.stderr = None
            server_result = companion_server.start()
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
        try:
            if server_result != "started":
                raise RuntimeError(
                    companion_server.error
                    or "The packaged loopback API did not start."
                )
            discovery = probe_companion(companion_server.port)
            if discovery is None:
                raise RuntimeError(
                    "The packaged loopback API started but did not answer discovery."
                )
            if sys.platform == "win32" and not discovery.get("systemAudioCapture"):
                raise RuntimeError(
                    "The packaged loopback API cannot capture Windows output."
                )
            server_check = {
                "status": "ok",
                "host": "127.0.0.1",
                "apiVersion": discovery.get("apiVersion"),
                "systemAudioCapture": discovery.get("systemAudioCapture"),
            }
        finally:
            companion_server.stop()

    from notesbuddy_transcription.engine import EmptyEngine, LocalDiarizationEngine
    from notesbuddy_transcription.server import create_app

    app = create_app(
        engine=EmptyEngine(),
        pairing_token="self-test-pairing-token-is-long-enough",
        allowed_origins=["https://self-test.invalid"],
        allow_browser_pairing=True,
        companion_version=COMPANION_VERSION,
    )
    routes = {route.path for route in app.routes}
    expected = {
        "/v1/companion",
        "/v1/pairings",
        "/v1/health",
        "/v1/system-audio/captures",
        "/v1/system-audio/captures/{capture_id}",
        "/v1/system-audio/captures/{capture_id}/pause",
        "/v1/system-audio/captures/{capture_id}/resume",
        "/v1/system-audio/captures/{capture_id}/stop",
        "/v1/transcriptions",
        "/v1/transcriptions/{job_id}",
    }
    missing = sorted(expected - routes)
    if missing:
        raise RuntimeError(f"Packaged API routes are missing: {', '.join(missing)}")
    result: dict[str, Any] = {
        "status": "ok",
        "version": COMPANION_VERSION,
        "routes": sorted(expected),
    }
    if sys.platform == "win32":
        for package in ("pycaw.pycaw", "windows_toasts"):
            if importlib.util.find_spec(package) is None:
                raise RuntimeError(
                    f"Packaged notification dependency is missing: {package}"
                )
        result["teamsMeetingNotifications"] = {
            "status": "ok",
            "actionUrl": teams_capture_url(DEFAULT_WEB_URL),
        }
    if server_check is not None:
        result["server"] = server_check
    if require_models:
        for package in (
            "faster_whisper",
            "pyannote.audio",
            "soundcard",
            "soundfile",
            "torch",
        ):
            importlib.import_module(package)
        model_status = LocalDiarizationEngine().configuration_status()
        if not model_status["ready"] or model_status["source"] != "bundled":
            raise RuntimeError(
                "The packaged runtime or offline model directories are incomplete."
            )
        result["models"] = model_status
    return result


def parse_arguments(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run NotesBuddy transcription privately on this computer.",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--web-url",
        default=os.getenv("NOTESBUDDY_WEB_URL", DEFAULT_WEB_URL),
    )
    parser.add_argument("--background", action="store_true")
    parser.add_argument(
        "--show-token",
        action="store_true",
        help="Print the persistent manual recovery token and exit.",
    )
    parser.add_argument(
        "--empty-engine",
        action="store_true",
        help="Use a dependency-light smoke-test engine.",
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--require-models",
        action="store_true",
        help="Require bundled runtime packages and offline models during self-test.",
    )
    parser.add_argument(
        "--require-server",
        action="store_true",
        help="Start and probe the packaged loopback API during self-test.",
    )
    parser.add_argument("--version", action="store_true")
    parsed = parser.parse_args(arguments)
    try:
        companion_endpoint(parsed.port)
    except ValueError as error:
        parser.error(str(error))
    return parsed


def main(arguments: list[str] | None = None) -> int:
    parsed = parse_arguments(arguments)
    if parsed.version:
        print(COMPANION_VERSION)
        return 0
    if parsed.self_test:
        print(
            json.dumps(
                self_test(
                    require_models=parsed.require_models,
                    require_server=parsed.require_server,
                ),
                indent=2,
            )
        )
        return 0

    server = CompanionServer(
        port=parsed.port,
        empty_engine=parsed.empty_engine,
    )
    if parsed.show_token:
        print(server.token)
        return 0
    server_result = server.start()

    window = DesktopWindow(
        server=server,
        server_result=server_result,
        web_url=parsed.web_url,
        background=parsed.background,
    )
    window.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
