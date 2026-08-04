from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from teams_detection import (  # noqa: E402
    AUDIO_CONFIRM_SECONDS,
    MEETING_CLEAR_SECONDS,
    MICROPHONE_CONFIRM_SECONDS,
    TeamsMeetingState,
    TeamsSignal,
    probe_teams_signal,
    teams_audio_active,
    teams_capture_url,
)


def session(process_name: str, state: object) -> SimpleNamespace:
    return SimpleNamespace(
        Process=SimpleNamespace(name=lambda: process_name),
        State=state,
    )


class TeamsSignalTests(unittest.TestCase):
    def test_only_active_teams_audio_counts(self) -> None:
        self.assertTrue(
            teams_audio_active(
                [
                    session("chrome.exe", 1),
                    session("ms-teams.exe", 1),
                ]
            )
        )
        self.assertFalse(teams_audio_active([session("ms-teams.exe", 0)]))
        self.assertFalse(teams_audio_active([session("notteams.exe", 1)]))
        self.assertFalse(
            teams_audio_active([session("teams.exe", "AudioSessionState.Inactive")])
        )

    def test_probe_combines_audio_and_microphone_without_raising(self) -> None:
        signal = probe_teams_signal(
            session_provider=lambda: [session("teams.exe", 1)],
            microphone_probe=lambda: True,
        )

        self.assertTrue(signal.audio_active)
        self.assertTrue(signal.microphone_active)

        failed = probe_teams_signal(
            session_provider=lambda: (_ for _ in ()).throw(OSError("audio")),
            microphone_probe=lambda: (_ for _ in ()).throw(OSError("mic")),
        )
        self.assertFalse(failed.present)

    def test_notification_url_preserves_safe_existing_query(self) -> None:
        url = teams_capture_url("https://example.test/app/?theme=dark#top")

        self.assertEqual(
            url,
            "https://example.test/app/?theme=dark&action=capture&source=teams#top",
        )


class TeamsMeetingStateTests(unittest.TestCase):
    def test_microphone_signal_confirms_quickly_and_only_once(self) -> None:
        state = TeamsMeetingState()
        signal = TeamsSignal(microphone_active=True)

        self.assertFalse(state.update(signal, now=10))
        self.assertFalse(
            state.update(signal, now=10 + MICROPHONE_CONFIRM_SECONDS - 0.1)
        )
        self.assertTrue(
            state.update(signal, now=10 + MICROPHONE_CONFIRM_SECONDS)
        )
        self.assertFalse(state.update(signal, now=30))

    def test_audio_only_ringtone_must_be_sustained(self) -> None:
        state = TeamsMeetingState()
        audio = TeamsSignal(audio_active=True)

        self.assertFalse(state.update(audio, now=0))
        self.assertFalse(
            state.update(audio, now=AUDIO_CONFIRM_SECONDS - 0.1)
        )
        self.assertTrue(state.update(audio, now=AUDIO_CONFIRM_SECONDS))

    def test_short_ringtone_resets_without_notification(self) -> None:
        state = TeamsMeetingState()

        self.assertFalse(state.update(TeamsSignal(audio_active=True), now=0))
        self.assertFalse(state.update(TeamsSignal(), now=5))
        self.assertFalse(state.update(TeamsSignal(audio_active=True), now=20))
        self.assertFalse(state.update(TeamsSignal(), now=25))

    def test_new_meeting_requires_a_clear_quiet_period(self) -> None:
        state = TeamsMeetingState()
        microphone = TeamsSignal(microphone_active=True)

        state.update(microphone, now=0)
        self.assertTrue(
            state.update(microphone, now=MICROPHONE_CONFIRM_SECONDS)
        )
        state.update(TeamsSignal(), now=20)
        state.update(
            TeamsSignal(),
            now=20 + MEETING_CLEAR_SECONDS,
        )
        self.assertFalse(state.meeting_active)

        self.assertFalse(state.update(microphone, now=100))
        self.assertTrue(
            state.update(microphone, now=100 + MICROPHONE_CONFIRM_SECONDS)
        )


if __name__ == "__main__":
    unittest.main()
