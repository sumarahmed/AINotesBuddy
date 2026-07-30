# Changelog

All notable changes to NotesBuddy are documented in this file.

The project follows the structure of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
but does not yet publish semantic-versioned releases.

## Unreleased

### Added

- GitHub-ready project, architecture, privacy, testing, and contribution
  documentation
- GitHub issue forms, pull request template, and CI validation
- Public GitHub Pages deployment workflow for the generated static client
- First-run local profiles with personalised greetings, initials, transcript
  attribution, and editable names
- UUID-based profile, meeting, import, and speech-segment identifiers

### Changed

- Home and capture dates now use the browser's current local date and time
- New browser profiles start with an empty workspace instead of bundled demo
  meetings and a fake upcoming calendar event
- Short recordings show their real elapsed seconds instead of being rounded up
  to one minute

### Fixed

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
