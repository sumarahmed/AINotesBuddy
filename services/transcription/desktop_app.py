"""Windows desktop launcher for the NotesBuddy local companion."""

from __future__ import annotations

import argparse
import importlib
import json
import os
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

COMPANION_VERSION = "0.1.2"
DEFAULT_PORT = 8765
DEFAULT_WEB_URL = "https://sumarahmed.github.io/AINotesBuddy/"
AUTOSTART_VALUE_NAME = "NotesBuddyCompanion"


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


class CompanionServer:
    """Own a loopback-only Uvicorn server running on a background thread."""

    def __init__(self, *, port: int, empty_engine: bool = False) -> None:
        from notesbuddy_transcription.security import ensure_pairing_token

        companion_endpoint(port)
        self.port = port
        self.empty_engine = empty_engine
        self.token, self.token_path, self.token_created = ensure_pairing_token()
        self.server: object | None = None
        self.thread: threading.Thread | None = None
        self.started_here = False
        self.error: str | None = None

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

        self.root = tk.Tk()
        self.root.title("NotesBuddy Desktop Companion")
        self.root.geometry("560x370")
        self.root.minsize(520, 340)
        self.root.protocol("WM_DELETE_WINDOW", self._close_window)

        self.status = tk.StringVar(value="Starting local service…")
        self.detail = tk.StringVar(
            value=f"Private loopback address: {companion_endpoint(server.port)}"
        )
        self.autostart = tk.BooleanVar(value=autostart_enabled())
        self._build()
        self._start_tray()
        self.root.after(0, self._show_server_result, server_result)

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
            text=(
                "Transcribes meeting audio on this computer and securely connects "
                "to the NotesBuddy website."
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

        ttk.Checkbutton(
            frame,
            text="Start the companion when I sign in to Windows",
            variable=self.autostart,
            command=self._toggle_autostart,
        ).pack(anchor="w", pady=(8, 0))
        ttk.Label(
            frame,
            text=(
                "Audio is sent only to 127.0.0.1 while local mode is active. "
                "Models load on the first transcription and may take a moment."
            ),
            foreground="#5b6470",
            wraplength=490,
        ).pack(anchor="w", pady=(18, 0))

    def _show_server_result(self, result: str) -> None:
        if result == "started":
            self.status.set("Connected — local transcription is available")
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
            server_check = {
                "status": "ok",
                "host": "127.0.0.1",
                "apiVersion": discovery.get("apiVersion"),
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
    if server_check is not None:
        result["server"] = server_check
    if require_models:
        for package in (
            "faster_whisper",
            "pyannote.audio",
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
