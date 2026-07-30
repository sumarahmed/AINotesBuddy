# Changelog

All notable changes to NotesBuddy are documented in this file.

The project follows the structure of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
but does not yet publish semantic-versioned releases.

## Unreleased

### Added

- Hosted anonymous transcription mode with expiring browser sessions,
  per-session job ownership, hashed client rate-limit keys, and bounded quotas
- Modal serverless GPU deployment package, protected Hugging Face secret, and
  persistent model-cache volume
- Public runtime configuration that switches local/hosted behavior without
  putting credentials in the static client
- Hosted API, browser-client, CORS, ownership, and UI integration tests
- Hosted processing, operations, privacy, and subscription-migration guide
- Synchronized microphone, shared meeting-audio, and mixed recording sources
- Source-specific IndexedDB storage, playback, download, reload, and deletion
- Meeting-only capture and microphone fallback when display sharing is denied
- Persistent interrupted-share warning without re-rendering recording controls
- Local authenticated faster-whisper and pyannote diarization companion
- Session-local **You**, remote speaker, and unknown-speaker attribution
- Speaker roster, rename persistence, speaker search, and named Markdown export
- Local API pairing, origin allowlisting, private-network preflight support,
  bounded job execution, cancellation, and temporary-upload cleanup
- JavaScript, Python core/API, and synthetic Chrome/Edge browser test suites
- GitHub-ready project, architecture, privacy, testing, and contribution
  documentation
- GitHub issue forms, pull request template, and CI validation
- Public GitHub Pages deployment workflow for the generated static client
- First-run local profiles with personalised greetings, initials, transcript
  attribution, and editable names
- UUID-based profile, meeting, import, and speech-segment identifiers

### Changed

- Settings hide the local URL/pairing fields in hosted mode and disclose when
  transcription sends selected audio to the public processing service
- Transcription API supports either local pairing or anonymous hosted access
  behind the same job/model contract
- Meeting briefs are extractive and contain only real transcript segment text
- Profile renames synchronize local speaker metadata and owned follow-ups
- Imported mixed audio can be sent to the local companion for diarization
- Home and capture dates now use the browser's current local date and time
- New browser profiles start with an empty workspace instead of bundled demo
  meetings and a fake upcoming calendar event
- Short recordings show their real elapsed seconds instead of being rounded up
  to one minute

### Fixed

- Bound native browser `fetch` correctly so local companion health/jobs run
- Preserved transcript text longer than the 80-character speaker-name limit
- Added modern private-network preflight handling for HTTPS-to-loopback pairing
- Added the persistent warning when a shared meeting stream ends externally
- Replaced the no-op summary refresh with honest transcript-only extraction
- Opening Settings from mobile navigation now closes the navigation behind it
- Empty libraries say `No meetings yet` instead of reporting a search mismatch
- Removed the repeated full-view fade that made recording and option controls
  appear to flash after state changes

## 2026-07-29

### Added

- Local microphone recording with pause and resume
- IndexedDB audio persistence, playback, seeking, and download
- Browser speech-recognition integration without sample transcript injection
- Audio import, Markdown export, clipboard copy, notes, and action tracking
- Responsive desktop and mobile interfaces
- Direct local-file launch and dependency-free production build

### Fixed

- Connected the transcript waveform play button to the stored recording
- Kept recording controls stable while capture timers and transcripts update
- Preserved playback during transcript filtering and view refreshes
- Preserved imported audio filenames and extensions
- Added explicit unavailable states for missing local recordings
