from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notesbuddy_transcription.access import (  # noqa: E402
    AnonymousSessionStore,
    SessionAccessError,
    anonymise_client_key,
)


class AnonymousSessionStoreTests(unittest.TestCase):
    def make_store(self, **overrides) -> AnonymousSessionStore:
        settings = {
            "session_ttl_seconds": 3600,
            "maximum_sessions": 4,
            "issue_window_seconds": 3600,
            "maximum_issues_per_client": 2,
            "job_window_seconds": 3600,
            "maximum_jobs_per_session": 2,
            "maximum_active_jobs_per_session": 1,
        }
        settings.update(overrides)
        return AnonymousSessionStore(**settings)

    def test_issues_opaque_session_and_never_retains_raw_client_key(self) -> None:
        store = self.make_store()
        raw_client_key = "203.0.113.10"

        token, session = store.issue(anonymise_client_key(raw_client_key))

        self.assertGreaterEqual(len(token), 24)
        self.assertNotEqual(session.client_key, raw_client_key)
        self.assertEqual(store.require(token), session.token_digest)
        with self.assertRaises(SessionAccessError) as context:
            store.require("incorrect-token")
        self.assertEqual(context.exception.status_code, 401)

    def test_limits_session_creation_and_job_compute(self) -> None:
        store = self.make_store()
        client_key = anonymise_client_key("203.0.113.11")
        token, session = store.issue(client_key)
        store.issue(client_key)

        with self.assertRaises(SessionAccessError) as issue_context:
            store.issue(client_key)
        self.assertEqual(issue_context.exception.status_code, 429)

        store.reserve_job(session.token_digest)
        with self.assertRaises(SessionAccessError) as active_context:
            store.reserve_job(session.token_digest)
        self.assertEqual(active_context.exception.status_code, 429)

        store.release_job(session.token_digest)
        store.reserve_job(session.token_digest)
        store.release_job(session.token_digest)
        with self.assertRaises(SessionAccessError) as quota_context:
            store.reserve_job(session.token_digest)
        self.assertEqual(quota_context.exception.status_code, 429)


if __name__ == "__main__":
    unittest.main()
