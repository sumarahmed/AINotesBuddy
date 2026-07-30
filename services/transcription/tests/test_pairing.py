from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notesbuddy_transcription.pairing import BrowserPairingStore


class BrowserPairingStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = 100.0
        self.store = BrowserPairingStore(
            ttl_seconds=60,
            maximum_pairings=2,
            monotonic=lambda: self.now,
        )

    def test_issued_token_is_accepted_until_it_expires(self) -> None:
        token, pairing = self.store.issue("https://example.test")

        self.assertTrue(
            self.store.accepts(token, origin="https://example.test")
        )
        self.assertFalse(
            self.store.accepts(token, origin="https://other.test")
        )
        self.assertEqual(pairing.origin, "https://example.test")
        self.assertNotEqual(pairing.token_digest, token)

        self.now += 60
        self.assertFalse(
            self.store.accepts(token, origin="https://example.test")
        )

    def test_unknown_and_missing_tokens_are_rejected(self) -> None:
        self.assertFalse(self.store.accepts(None, origin="https://example.test"))
        self.assertFalse(self.store.accepts("", origin="https://example.test"))
        self.assertFalse(
            self.store.accepts("unknown-token", origin="https://example.test")
        )
        token, _ = self.store.issue("https://example.test")
        self.assertFalse(self.store.accepts(token, origin=None))

    def test_oldest_pairing_is_removed_when_store_is_full(self) -> None:
        first, _ = self.store.issue("https://one.test")
        self.now += 1
        second, _ = self.store.issue("https://two.test")
        self.now += 1
        third, _ = self.store.issue("https://three.test")

        self.assertFalse(self.store.accepts(first, origin="https://one.test"))
        self.assertTrue(self.store.accepts(second, origin="https://two.test"))
        self.assertTrue(self.store.accepts(third, origin="https://three.test"))


if __name__ == "__main__":
    unittest.main()
