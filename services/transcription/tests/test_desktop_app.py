from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from desktop_app import build_autostart_command, companion_endpoint, parse_arguments


class DesktopUtilityTests(unittest.TestCase):
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
        parsed = parse_arguments(["--self-test", "--require-models"])

        self.assertTrue(parsed.self_test)
        self.assertTrue(parsed.require_models)


if __name__ == "__main__":
    unittest.main()
