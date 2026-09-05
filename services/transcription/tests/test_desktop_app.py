from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from desktop_app import (
    COMPANION_VERSION,
    RELEASES_URL,
    UPDATE_CHECK_INTERVAL_MS,
    DesktopWindow,
    build_autostart_command,
    companion_endpoint,
    fetch_latest_companion_release,
    is_version_outdated,
    load_companion_settings,
    parse_arguments,
    save_companion_settings,
    version_parts,
)


class DesktopUtilityTests(unittest.TestCase):
    def test_companion_uses_year_month_minor_release_version(self) -> None:
        self.assertEqual(COMPANION_VERSION, "2026.09.04")

    def test_companion_compares_release_versions_numerically(self) -> None:
        self.assertEqual(version_parts("companion-v2026.08.3"), (2026, 8, 3))
        self.assertTrue(is_version_outdated("0.1.2", "2026.08.3"))
        self.assertFalse(is_version_outdated("2026.08.3", "2026.08.3"))

    def test_latest_release_selects_trusted_windows_installer(self) -> None:
        # Far enough ahead of any real COMPANION_VERSION that this test does
        # not silently start asserting the opposite of what it means each
        # time that constant is bumped for a real release -- exactly what
        # broke here once already (fixture pinned to 2026.08.12, which
        # stopped being "newer" the moment COMPANION_VERSION passed it).
        future_tag = "2099.01.1"
        payload = {
            "tag_name": f"companion-v{future_tag}",
            "html_url": f"{RELEASES_URL}/tag/companion-v{future_tag}",
            "assets": [
                {
                    "name": f"NotesBuddyCompanion-Setup-{future_tag}.exe",
                    "browser_download_url": (
                        f"{RELEASES_URL}/download/companion-v{future_tag}/"
                        f"NotesBuddyCompanion-Setup-{future_tag}.exe"
                    ),
                }
            ],
        }
        captured: dict[str, object] = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self) -> bytes:
                return json.dumps(payload).encode("utf-8")

        def opener(request, *, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse()

        result = fetch_latest_companion_release(opener=opener, timeout=2)

        self.assertTrue(result["available"])
        self.assertEqual(result["latestVersion"], future_tag)
        self.assertTrue(str(result["downloadUrl"]).endswith(".exe"))
        self.assertEqual(captured["timeout"], 2)
        self.assertIn(
            f"NotesBuddy-Companion/{COMPANION_VERSION}",
            captured["request"].get_header("User-agent"),
        )

    def test_a_component_only_release_is_not_reported_as_an_available_update(
        self,
    ) -> None:
        # This repo publishes component-only releases (e.g.
        # speaker-diarization-cuda) under the same companion-v* tag
        # convention as real installer releases -- GitHub's "latest
        # release" is whichever published most recently, regardless of
        # content. Reported live (2026-09-05): the companion notified
        # "Update 2026.09.11 is available" for exactly this kind of
        # release, which had no installer .exe at all.
        future_tag = "2099.01.1"
        payload = {
            "tag_name": f"companion-v{future_tag}",
            "html_url": f"{RELEASES_URL}/tag/companion-v{future_tag}",
            "assets": [
                {
                    "name": f"NotesBuddy-speaker-diarization-cuda-{future_tag}.zip",
                    "browser_download_url": (
                        f"{RELEASES_URL}/download/companion-v{future_tag}/"
                        f"NotesBuddy-speaker-diarization-cuda-{future_tag}.zip"
                    ),
                }
            ],
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self) -> bytes:
                return json.dumps(payload).encode("utf-8")

        result = fetch_latest_companion_release(
            opener=lambda *_args, **_kwargs: FakeResponse()
        )

        self.assertFalse(result["available"])
        self.assertEqual(result["latestVersion"], future_tag)

    def test_teams_notification_preference_is_local_and_persistent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "companion-settings.json"

            self.assertTrue(load_companion_settings(path)["teamsMeetingNotifications"])
            save_companion_settings(
                {"teamsMeetingNotifications": False},
                path,
            )

            self.assertFalse(
                load_companion_settings(path)["teamsMeetingNotifications"]
            )

    def test_latest_release_rejects_an_invalid_tag(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self) -> bytes:
                return b'{"tag_name":"latest"}'

        with self.assertRaises(ValueError):
            fetch_latest_companion_release(
                opener=lambda *_args, **_kwargs: FakeResponse()
            )

    def test_available_update_enables_download_and_notifies_tray(self) -> None:
        class Variable:
            value = ""

            def set(self, value):
                self.value = value

        class Button:
            state = ""

            def configure(self, *, state):
                self.state = state

        class Tray:
            calls: list[tuple[str, str]] = []

            def notify(self, message, title):
                self.calls.append((message, title))

        class Root:
            calls: list[tuple[int, object]] = []

            def after(self, interval, callback):
                self.calls.append((interval, callback))

        window = SimpleNamespace(
            update_check_running=True,
            update_url=RELEASES_URL,
            update_status=Variable(),
            update_button=Button(),
            last_notified_version=None,
            tray_icon=Tray(),
            background=True,
            root=Root(),
            tk=SimpleNamespace(TclError=RuntimeError),
            _start_update_check=lambda: None,
        )

        DesktopWindow._show_update_result(
            window,
            {
                "available": True,
                "latestVersion": "2026.08.3",
                "downloadUrl": f"{RELEASES_URL}/download/example/setup.exe",
            },
        )

        self.assertFalse(window.update_check_running)
        self.assertEqual(window.update_button.state, "normal")
        self.assertIn("2026.08.3", window.update_status.value)
        self.assertEqual(len(window.tray_icon.calls), 1)
        self.assertEqual(window.tray_icon.calls[0][1], "NotesBuddy update available")
        self.assertEqual(window.root.calls[0][0], UPDATE_CHECK_INTERVAL_MS)

    def test_a_duplicate_launch_always_closes_itself_eventually(self) -> None:
        # The port-bind check in CompanionServer.start() already guarantees
        # only one server is ever functional, but this window used to stay
        # open indefinitely for a manual (non-background) second launch --
        # reported live as "I can open two companions at once", when in
        # fact only one was ever actually running. Both a silent autostart
        # launch and a manual double-click launch must close the window
        # once a duplicate is detected, just with a longer delay for the
        # manual case so there is time to actually read the message.
        class Root:
            def __init__(self):
                self.calls: list[tuple[int, object]] = []

            def after(self, interval, callback):
                self.calls.append((interval, callback))

        for background in (True, False):
            with self.subTest(background=background):
                window = SimpleNamespace(
                    status=SimpleNamespace(value="", set=lambda v: None),
                    detail=SimpleNamespace(value="", set=lambda v: None),
                    background=background,
                    root=Root(),
                    _quit=lambda: None,
                )
                DesktopWindow._show_server_result(window, "existing")
                self.assertEqual(len(window.root.calls), 1)
                delay, callback = window.root.calls[0]
                self.assertEqual(delay, 250 if background else 2500)
                self.assertIs(callback, window._quit)

    def test_companion_endpoint_is_fixed_to_ipv4_loopback(self) -> None:
        self.assertEqual(companion_endpoint(8765), "http://127.0.0.1:8765")
        for port in (0, 65536):
            with self.subTest(port=port):
                with self.assertRaises(ValueError):
                    companion_endpoint(port)

    def test_frozen_autostart_command_does_not_include_source_script(self) -> None:
        command = build_autostart_command(
            executable=r"C:\Program Files\NotesBuddy\Companion.exe",
            script_path=r"C:\source\desktop_app.py",
            frozen=True,
        )

        self.assertIn("Companion.exe", command)
        self.assertNotIn("desktop_app.py", command)
        self.assertTrue(command.endswith("--background"))

    def test_source_autostart_command_includes_launcher_script(self) -> None:
        command = build_autostart_command(
            executable=r"C:\Python\python.exe",
            script_path=r"C:\source folder\desktop_app.py",
            frozen=False,
        )

        self.assertIn("python.exe", command)
        self.assertIn("desktop_app.py", command)
        self.assertTrue(command.endswith("--background"))

    def test_cli_parses_safe_port_and_empty_engine(self) -> None:
        parsed = parse_arguments(["--port", "9876", "--empty-engine"])

        self.assertEqual(parsed.port, 9876)
        self.assertTrue(parsed.empty_engine)

    def test_cli_can_require_models_during_packaged_self_test(self) -> None:
        parsed = parse_arguments(
            ["--self-test", "--require-models", "--require-server"]
        )

        self.assertTrue(parsed.self_test)
        self.assertTrue(parsed.require_models)
        self.assertTrue(parsed.require_server)


if __name__ == "__main__":
    unittest.main()
