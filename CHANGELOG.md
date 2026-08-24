# Changelog

All notable changes to NotesBuddy are documented in this file.

The project follows the structure of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions use `Year.Month.MinorRelease`; package metadata omits leading zeroes to
remain compatible with semantic-version tooling.

## Unreleased

## 2026.08.17 - 2026-08-24

### Fixed

- Companion 2026.08.11 maps raw `local-user` transcript segments to **You**
  during analysis, so first-person commitments retain their established owner.
- Confirmed recommendations such as “assigning work to Alex” are rendered as
  clear decision statements while preserving their proposal and agreement
  source citations.

## 2026.08.16 - 2026-08-23

### Fixed

- Grounded meeting analysis now runs privately in Companion 2026.08.10 when
  the optional hosted service is unavailable; summary, highlight, decision,
  and action fields all retain transcript segment citations.
- Proposals are not reported as decisions unless a later transcript segment
  confirms agreement. Owners, dates, dependencies, and priorities are emitted
  only when the cited words support them.

### Changed

- A connected companion is preferred for professional analysis, removing the
  public website's runtime dependency on Modal for installed users.
- The disabled Modal URL is no longer advertised as an online fallback; users
  are guided to the working companion path until a hosted service is verified.
- The local analyzer is deterministic and model-free, so it adds no download,
  GPU-memory, or startup cost to the optimized companion installer.

## 2026.08.15 - 2026-08-14

### Fixed

- Companion 2026.08.9 extracts deeply nested speaker-runtime files through
  Windows extended paths instead of failing at the legacy 260-character limit.
- Automatic acceleration now selects CPU when the optional NVIDIA runtime is
  absent and retries once on CPU if CUDA fails during first inference.
- The NVIDIA DLL directory is added to the companion process search path so
  CTranslate2 can load cuBLAS and cuDNN from the reusable component pack.

### Changed

- Stable model packs are now versioned independently from the core companion.
  Core-only upgrades reuse compatible Accurate, speaker, and NVIDIA components
  instead of rebuilding and downloading multiple gigabytes again.

## 2026.08.14 - 2026-08-14

### Fixed

- Companion 2026.08.8 no longer fails with HTTP 416 when an Accurate or
  Balanced model download has already reached its expected size.
- Stale oversized component downloads are discarded safely, and a rejected
  HTTP resume request is retried once from byte zero.

## 2026.08.13 - 2026-08-13

### Changed

- Companion 2026.08.7 uses a smaller core installer. Balanced/Accurate speech
  models, speaker recognition, and NVIDIA acceleration are reusable first-run
  component packs stored outside the application directory.
- Component downloads report progress, resume partial transfers, verify
  SHA-256 before extraction, reject unsafe archive paths, and survive companion
  application upgrades.
- CPU-only computers skip the NVIDIA pack; compatible NVIDIA computers install
  it automatically with the selected local model.

## 2026.08.12 - 2026-08-13

### Changed

- A connected Windows companion now remains the preferred transcription path
  for recordings of every length instead of sending long meetings online.
- Companion 2026.08.6 automatically runs faster-whisper's dominant speech
  workload on a compatible local NVIDIA GPU, uses optimized single-beam
  decoding, and safely falls back to CPU `int8` if CUDA cannot initialize.
  Speaker diarization remains local and runs on CPU in the distributable build.
- Companion discovery and health now report the active accelerator, model
  device, and compute type so the website can show where processing runs.

## 2026.08.11 - 2026-08-13

### Fixed

- Hosted jobs now display real byte-level upload progress instead of appearing
  stuck at 0% while a long recording transfers.
- Dual-source meetings no longer upload the redundant mixed recording when
  microphone and meeting tracks are already available.
- Cancelling during upload now aborts the transfer immediately.

## 2026.08.10 - 2026-08-13

### Changed

- Hybrid installations now send recordings of 8 minutes or longer to the
  hosted GPU by default instead of processing near real-time on the local CPU.
- Added a **Speed up long recordings online** privacy control for users who
  prefer local-only audio transcription.
- Speaker transcription now displays its processing stage, percentage,
  elapsed time, and whether work is running online or on this computer.

## 2026.08.9 - 2026-08-12

### Fixed

- Short or quiet recordings no longer fail speaker transcription with
  `'DiarizeOutput' object is not iterable`.
- Recognized meeting words are preserved as an unknown remote speaker when
  diarization detects no usable speaker turns.
- Windows companion 2026.08.5 includes corrected pyannote 4 result handling.

## 2026.08.8 - 2026-08-04

### Added

- Local Microsoft Teams meeting detection in Windows companion 2026.08.4
- A clickable Windows notification that opens NotesBuddy directly on the
  ready-to-record capture screen
- A companion preference for enabling or disabling Teams meeting notifications
- Debouncing, ringtone suppression, one-notification-per-meeting behavior, and
  a quiet-period reset for consecutive calls

### Changed

- Notification handoffs clearly state that recording has not started and still
  require the user to select **Start capture**

## 2026.08.7 - 2026-08-04

### Fixed

- Existing saved meetings with longer transcripts now analyze in bounded,
  token-aware sections instead of exhausting the hosted GPU or truncating input
- Long-meeting partial results now merge hierarchically so every request stays
  within the model's safe input limit
- Supported summaries that under-cite transcript evidence now recover from the
  strongest matching segments rather than failing the entire refresh
- Weekdays, months, relative dates, and numeric dates are rejected when they do
  not appear in the cited transcript evidence
- Summary recovery removes repeated decisions and actions while remaining based
  only on validated transcript findings

## 2026.08.6 - 2026-08-04

### Added

- Professional whole-transcript analysis using a centrally managed instruction
  model and a strict structured JSON contract
- Evidence citations for the summary, highlights, decisions, and action items
- Structured action fields for owner, due date, priority, and notes
- Server-side grounding checks that reject unsupported content and normalize
  invented owners, dates, urgency, context, and notes

### Changed

- **Refresh from transcript** now requests a new professional analysis from the
  complete processed speaker transcript
- Existing keyword-generated insights are marked outdated and cleared so they
  can never be presented as current analysis

### Removed

- Browser keyword scoring and sentence-picking for summaries, highlights,
  decisions, and action items

## 2026.08.4 - 2026-08-04

### Added

- Transcript-grounded decision detection for explicit agreement, approval,
  selection, and commitment wording
- Transcript-grounded action extraction with spoken owners and due phrases
- Automatic migration of existing meeting summaries, preserving completion
  state when an action still matches transcript evidence

### Changed

- Key highlights are ranked from substantive transcript sentences and collapse
  overlapping or repeated transcription output
- **Refresh from transcript** now rebuilds highlights, decisions, and action
  items together

### Removed

- Generic **Review the recording and transcript** and imported-audio review
  actions that were not supported by anything said in the meeting
- Recording-status sentences from the Key highlights section

## 2026.08.3 - 2026-08-03

### Added

- Word-level microphone/meeting alignment using synchronized timestamps,
  normalized text, bounded fuzzy matching, and ordered phrase confirmation
- Regression coverage for partial echo, ASR variation, capture-clock offsets,
  short-word coincidences, and multiple diarized remote speakers

### Changed

- Cross-source cleanup removes only matched meeting leakage from microphone
  words, leaving unmatched local speech attributed to **You**
- Residual whole-segment duplicates now preserve the meeting-output copy and
  its pyannote speaker assignment instead of preferring the microphone copy

### Fixed

- Teams prompts or remote voices picked up acoustically by the microphone are
  no longer automatically retained as **You** when the same speech is present
  on the synchronized meeting-output track

## 2026.08.2 - 2026-08-03

### Added

- Persistent, screen-reader-announced website warning when an existing browser
  profile connects to an outdated desktop companion
- Daily non-blocking companion release check with a Windows notification-area
  alert and an explicit **Download update** action

### Fixed

- Connected legacy companions are no longer shown as fully healthy without an
  upgrade notice; Settings now reports **update required** with both versions
- Update-check network failures cannot prevent local recording or companion
  startup
- Website install and update buttons now target the versioned Windows `.exe`
  asset directly instead of opening the general GitHub Releases page

## 2026.08.1 - 2026-08-03

### Added

- Direct Windows system-output capture through the desktop companion and
  WASAPI loopback, including live signal detection, pause/resume, and WAV
  transfer back to the browser
- Visible `Year.Month.MinorRelease` version in the website, settings, and
  companion
- Windows desktop companion control panel and notification-area lifecycle
- First-entry installer onboarding with live companion confirmation and
  session-only online deferral
- Model/runtime readiness reporting that prevents incomplete installations
  from being confirmed as working
- Exact-origin automatic browser pairing with expiring memory-only tokens
- Hybrid local-first runtime selection with a visible hosted fallback
- Offline model preparation, model revision manifest, PyInstaller bundle, Inno
  Setup installer, and GitHub Actions release workflow
- Desktop architecture, model notice, release, security, and troubleshooting
  documentation
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

- When companion 2026.08.1 or later is connected, meeting capture uses Windows
  output directly instead of opening the browser screen/window share picker
- Companion captures keep Windows output and microphone as separate synchronized
  tracks; playback prefers the meeting track when a mixed track is unavailable
- The public runtime now probes the desktop companion first and does not expose
  URL/token fields in automatic hybrid mode
- Packaged releases can use publisher-bundled offline models without requesting
  a Hugging Face token from each user
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

- Mark loopback fetches for browser Local Network Access permission and show
  actionable Chrome/Edge site-permission recovery guidance
- Bundle the SoundFile decoder explicitly and wait for the model-inclusive
  packaged self-test process instead of reading a stale PowerShell exit code
- Start and probe the packaged loopback API during every Windows build so a
  desktop installer cannot publish with a broken local server runtime
- Disable console-dependent Uvicorn logging and start the loopback API before
  initializing the Windows tray so normal GUI launches can bind port 8765
- Kept unnecessary Torch source, test, and metadata trees out of the Windows
  installer and verified model-inclusive packages during their self-test
- Decode meeting audio into an in-memory waveform before diarization so the
  desktop companion does not depend on a system FFmpeg/TorchCodec installation
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
