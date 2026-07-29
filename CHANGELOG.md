# Changelog

All notable changes to NotesBuddy are documented in this file.

The project follows the structure of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
but does not yet publish semantic-versioned releases.

## Unreleased

### Added

- GitHub-ready project, architecture, privacy, testing, and contribution
  documentation
- GitHub issue forms, pull request template, and CI validation

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
