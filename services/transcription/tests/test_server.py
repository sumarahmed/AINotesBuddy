from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from fastapi.testclient import TestClient
except ImportError:  # API dependencies are installed by CI and documented setup.
    TestClient = None

from notesbuddy_transcription.engine import EmptyEngine, EngineCancelled

PAIRING_TOKEN = "test-pairing-token-that-is-long-enough"


@unittest.skipIf(TestClient is None, "FastAPI test dependencies are not installed")
class LocalApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from notesbuddy_transcription.server import create_app

        cls.client = TestClient(
            create_app(
                engine=EmptyEngine(),
                pairing_token=PAIRING_TOKEN,
                allowed_origins=["http://127.0.0.1:4173"],
            )
        )
        cls.headers = {"X-NotesBuddy-Pairing-Token": PAIRING_TOKEN}

    def test_health_requires_pairing_and_discloses_local_storage_policy(self) -> None:
        self.assertEqual(self.client.get("/v1/health").status_code, 401)

        response = self.client.get("/v1/health", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["storage"], "temporary job files only")

    def test_job_accepts_assets_and_never_fabricates_text(self) -> None:
        response = self.client.post(
            "/v1/transcriptions",
            headers=self.headers,
            files={
                "microphone": (
                    "microphone.webm",
                    b"synthetic-audio-bytes",
                    "audio/webm",
                ),
                "mixed": ("mixed.webm", b"synthetic-mix", "audio/webm"),
            },
            data={"metadata": '{"meetingId":"meeting-test"}'},
        )

        self.assertEqual(response.status_code, 200)
        job_id = response.json()["jobId"]
        result = self._wait_for_terminal(job_id)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["segments"], [])

    def test_rejects_invalid_token_and_invalid_metadata(self) -> None:
        bad_token = self.client.post(
            "/v1/transcriptions",
            headers={"X-NotesBuddy-Pairing-Token": "incorrect"},
            files={"mixed": ("mixed.webm", b"audio", "audio/webm")},
            data={"metadata": "{}"},
        )
        self.assertEqual(bad_token.status_code, 401)

        bad_metadata = self.client.post(
            "/v1/transcriptions",
            headers=self.headers,
            files={"mixed": ("mixed.webm", b"audio", "audio/webm")},
            data={"metadata": "[]"},
        )
        self.assertEqual(bad_metadata.status_code, 400)

    def test_cors_allows_only_the_configured_origin(self) -> None:
        allowed = self.client.options(
            "/v1/health",
            headers={
                "Origin": "http://127.0.0.1:4173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-NotesBuddy-Pairing-Token",
                "Access-Control-Request-Private-Network": "true",
            },
        )
        self.assertEqual(
            allowed.headers.get("access-control-allow-origin"),
            "http://127.0.0.1:4173",
        )
        self.assertEqual(
            allowed.headers.get("access-control-allow-private-network"),
            "true",
        )

        denied = self.client.options(
            "/v1/health",
            headers={
                "Origin": "https://untrusted.invalid",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertNotIn("access-control-allow-origin", denied.headers)

    def test_discovery_discloses_no_pairing_secret(self) -> None:
        response = self.client.get("/v1/companion")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertEqual(response.json()["status"], "available")
        self.assertFalse(response.json()["browserPairing"])
        self.assertTrue(response.json()["modelsReady"])
        self.assertNotIn("token", response.text.lower())

    def test_automatic_pairing_is_disabled_for_the_manual_cli(self) -> None:
        response = self.client.post(
            "/v1/pairings",
            headers={"Origin": "http://127.0.0.1:4173"},
        )

        self.assertEqual(response.status_code, 404)

    def _wait_for_terminal(self, job_id: str) -> dict:
        for _attempt in range(100):
            response = self.client.get(
                f"/v1/transcriptions/{job_id}",
                headers=self.headers,
            )
            payload = response.json()
            if payload["status"] in {"completed", "failed", "cancelled"}:
                return payload
            time.sleep(0.01)
        self.fail("Transcription job did not reach a terminal state")


@unittest.skipIf(TestClient is None, "FastAPI test dependencies are not installed")
class AnonymousHostedApiTests(unittest.TestCase):
    def setUp(self) -> None:
        from notesbuddy_transcription.server import create_app

        self.client = TestClient(
            create_app(
                engine=EmptyEngine(),
                authentication_mode="anonymous",
                allowed_origins=["https://sumarahmed.github.io"],
            )
        )

    def _new_session(self) -> dict[str, str]:
        response = self.client.post("/v1/sessions")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        return {
            "X-NotesBuddy-Session-Token": response.json()["sessionToken"],
        }

    def _wait_for_terminal(self, job_id: str, headers: dict[str, str]) -> dict:
        for _attempt in range(100):
            response = self.client.get(
                f"/v1/transcriptions/{job_id}",
                headers=headers,
            )
            payload = response.json()
            if payload["status"] in {"completed", "failed", "cancelled"}:
                return payload
            time.sleep(0.01)
        self.fail("Hosted transcription job did not reach a terminal state")

    def test_health_is_public_but_jobs_require_anonymous_session(self) -> None:
        health = self.client.get("/v1/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["access"], "anonymous-session")

        missing_session = self.client.post(
            "/v1/transcriptions",
            files={"mixed": ("mixed.webm", b"audio", "audio/webm")},
            data={"metadata": "{}"},
        )
        self.assertEqual(missing_session.status_code, 401)

        too_long = self.client.post(
            "/v1/transcriptions",
            headers=self._new_session(),
            files={"mixed": ("mixed.webm", b"audio", "audio/webm")},
            data={"metadata": '{"durationMs":7200001}'},
        )
        self.assertEqual(too_long.status_code, 413)

    def test_session_owns_job_and_other_sessions_cannot_read_it(self) -> None:
        owner_headers = self._new_session()
        other_headers = self._new_session()
        created = self.client.post(
            "/v1/transcriptions",
            headers=owner_headers,
            files={"meeting": ("meeting.webm", b"remote-voice", "audio/webm")},
            data={"metadata": '{"meetingId":"public-test"}'},
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.headers.get("cache-control"), "no-store")
        job_id = created.json()["jobId"]

        hidden = self.client.get(
            f"/v1/transcriptions/{job_id}",
            headers=other_headers,
        )
        self.assertEqual(hidden.status_code, 404)

        completed = self._wait_for_terminal(job_id, owner_headers)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["segments"], [])

    def test_cors_allows_public_site_and_session_header(self) -> None:
        allowed = self.client.options(
            "/v1/sessions",
            headers={
                "Origin": "https://sumarahmed.github.io",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-NotesBuddy-Session-Token",
            },
        )
        self.assertEqual(
            allowed.headers.get("access-control-allow-origin"),
            "https://sumarahmed.github.io",
        )
        self.assertIn(
            "x-notesbuddy-session-token",
            allowed.headers.get("access-control-allow-headers", "").lower(),
        )

    def test_local_companion_routes_are_not_exposed_by_hosted_service(self) -> None:
        self.assertEqual(self.client.get("/v1/companion").status_code, 404)
        self.assertEqual(self.client.post("/v1/pairings").status_code, 404)


@unittest.skipIf(TestClient is None, "FastAPI test dependencies are not installed")
class DesktopBrowserPairingTests(unittest.TestCase):
    def setUp(self) -> None:
        from notesbuddy_transcription.server import create_app

        self.origin = "https://sumarahmed.github.io"
        self.client = TestClient(
            create_app(
                engine=EmptyEngine(),
                pairing_token=PAIRING_TOKEN,
                allowed_origins=[self.origin],
                allow_browser_pairing=True,
            )
        )

    def test_trusted_origin_can_pair_and_use_the_local_api(self) -> None:
        paired = self.client.post(
            "/v1/pairings",
            headers={"Origin": self.origin},
        )

        self.assertEqual(paired.status_code, 200)
        self.assertEqual(paired.headers.get("cache-control"), "no-store")
        payload = paired.json()
        self.assertEqual(payload["origin"], self.origin)
        self.assertGreaterEqual(len(payload["pairingToken"]), 32)

        health = self.client.get(
            "/v1/health",
            headers={
                "Origin": self.origin,
                "X-NotesBuddy-Pairing-Token": payload["pairingToken"],
            },
        )
        self.assertEqual(health.status_code, 200)

        wrong_origin = self.client.get(
            "/v1/health",
            headers={
                "Origin": "https://untrusted.invalid",
                "X-NotesBuddy-Pairing-Token": payload["pairingToken"],
            },
        )
        self.assertEqual(wrong_origin.status_code, 401)

    def test_pairing_rejects_missing_null_and_untrusted_origins(self) -> None:
        for headers in (
            {},
            {"Origin": "null"},
            {"Origin": "https://untrusted.invalid"},
        ):
            with self.subTest(headers=headers):
                response = self.client.post("/v1/pairings", headers=headers)
                self.assertEqual(response.status_code, 403)

    def test_manual_recovery_token_still_works(self) -> None:
        response = self.client.get(
            "/v1/health",
            headers={"X-NotesBuddy-Pairing-Token": PAIRING_TOKEN},
        )
        self.assertEqual(response.status_code, 200)


@unittest.skipIf(TestClient is None, "FastAPI test dependencies are not installed")
class CancellationTests(unittest.TestCase):
    def test_cancellation_signals_engine_and_removes_temporary_audio(self) -> None:
        from notesbuddy_transcription.server import create_app

        engine = WaitingEngine()
        client = TestClient(
            create_app(
                engine=engine,
                pairing_token=PAIRING_TOKEN,
                allowed_origins=["http://127.0.0.1:4173"],
            )
        )
        headers = {"X-NotesBuddy-Pairing-Token": PAIRING_TOKEN}
        response = client.post(
            "/v1/transcriptions",
            headers=headers,
            files={"mixed": ("mixed.webm", b"synthetic-audio", "audio/webm")},
            data={"metadata": "{}"},
        )
        job_id = response.json()["jobId"]
        self.assertTrue(engine.started.wait(timeout=2))

        cancelled = client.delete(
            f"/v1/transcriptions/{job_id}",
            headers=headers,
        )

        self.assertEqual(cancelled.json()["status"], "cancelled")
        self.assertTrue(engine.stopped.wait(timeout=2))
        self.assertIsNotNone(engine.audio_path)
        for _attempt in range(100):
            if not engine.audio_path.exists():
                break
            time.sleep(0.01)
        self.assertFalse(engine.audio_path.exists())


class WaitingEngine:
    name = "waiting-test-engine"

    def __init__(self) -> None:
        self.started = threading.Event()
        self.stopped = threading.Event()
        self.audio_path: Path | None = None

    def process(
        self,
        *,
        microphone_path,
        meeting_path,
        mixed_path,
        metadata,
        cancel_event,
        progress,
    ):
        del microphone_path, meeting_path, metadata, progress
        self.audio_path = mixed_path
        self.started.set()
        cancel_event.wait(timeout=2)
        self.stopped.set()
        raise EngineCancelled("cancelled in test")


if __name__ == "__main__":
    unittest.main()
