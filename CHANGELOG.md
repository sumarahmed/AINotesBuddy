# Changelog

All notable changes to NotesBuddy are documented in this file.

The project follows the structure of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions use `Year.Month.MinorRelease`; package metadata omits leading zeroes to
remain compatible with semantic-version tooling.

## Unreleased

### Added

- Diagnostic logging now records highlights/decisions/actionItems counts
  (both raw model output and post-validation) at every per-chunk and merge
  stage, not only the summary text -- to diagnose a report of highlights,
  decisions, and action items all coming back empty after the merge fix
  below, without guessing at a fix again.

### Fixed

- Found the real cause of the recurring "Technical Constraints and
  Timeframe. Discovery Phase Documentation Requirements." bad-summary
  report, using the diagnostic logging shipped just before this fix: on a
  real multi-chunk meeting, every chunk's own summary passed
  evidence-grounding individually (confirmed live in the new log), but the
  merge step that combines chunks re-checked the *concatenated* summary
  against the combined evidence as if it were a single fresh model output,
  and that stricter re-check failed even though nothing in it was
  ungrounded. Merge then fell back to concatenating highlight/decision/
  action titles, producing the exact same bug the 2026.09.02
  reinforcement-retry fix was believed to have already fixed -- that fix
  only ever covered the per-chunk path, not this separate merge-time one.
  Merge now trusts the partials' own already-validated summaries instead
  of re-deriving one from field titles.
- Local smart-summary diagnostic logging (`llama_cpp_failed`,
  `llama_cpp_invalid_output`, `summary_repair_fallback`) relied on `print()`,
  which is silently discarded in the packaged Windows companion: PyInstaller
  builds it with `console=False`, and its bootloader replaces
  `sys.stdout`/`sys.stderr` with a null writer for that build type even when
  the launching process redirects them to a real file. A real bad-summary
  report could therefore never be diagnosed from the shipped .exe's output,
  no matter how the process was launched. Diagnostics are now also written
  directly to `%LOCALAPPDATA%\NotesBuddy\logs\companion.log`, and every
  generation outcome (first attempt, reinforcement retry, or repair
  fallback) is now logged, not only failures, so a poor-quality-but-grounded
  summary that never hits the retry/repair path is still visible.

## 2026.09.02 - 2026-09-02

### Added

- Meeting analysis shows a live progress bar and elapsed timer instead of a
  static "Analyzing…" message with no sense of how long it will take. The
  local and hosted analyzers now report per-chunk progress through a
  pollable token while the main analysis request is still in flight, so the
  UI can show percentage and stage ("Analyzing part 2 of 3", "Combining
  results") without changing the request/response shape callers depend on.
- The Settings panel now lets you switch or download a different smart
  summary model tier (Fast, Balanced, High quality) at any time, not only
  during first-time setup. Installing a different tier downloads it once and
  replaces whichever tier is currently installed.

### Fixed

- The summary-repair fallback (used when the model's own summary fails
  evidence-grounding twice in a row) only ever drew candidate sentences from
  the *first* generation attempt, so a meeting whose content the model
  genuinely struggled to summarize kept producing the exact same
  concatenated-fragment text on every retry, even after the 2026.09.01
  reinforcement-retry fix shipped. The reinforcement retry's own generation
  is now a second, independently worded candidate pool for that fallback, and
  a diagnostic log line now records both attempts' summaries whenever this
  path fires.

## 2026.09.01 - 2026-09-02

### Fixed

- Local smart-summary analysis no longer fails on every real meeting. The
  bundled `llama.cpp` runtime's Jinja chat template primed the assistant turn
  with a special token that a JSON-schema grammar could not accept, so every
  analysis call failed instantly and then idled until the timeout, which
  looked identical to a slow CPU. Every real generation call is now verified
  end to end.
- The evidence-grounded cross-chunk merge no longer asks the local model to
  re-synthesize already-valid partial analyses; it combines them
  deterministically instead, which was silently degrading merged output on
  real meetings even though each chunk had analyzed correctly on its own.
- Long local-only diarization no longer appears to hang at a fixed progress
  percentage; progress now visibly advances while it runs.
- Companion 2026.08.11 shipped with its own `COMPANION_VERSION` constant
  disconnected from the installer's own version, so it kept self-reporting
  2026.08.11 forever, no matter how many times it was reinstalled -- the
  update banner could never be satisfied. Companion 2026.09.02 fixes this
  and `desktop/build.ps1` now synchronises that constant from the build
  version automatically, so it cannot drift again at the next release.
- A real 6-speaker meeting failed professional analysis with "The analysis
  model returned malformed JSON": the Balanced tier's fixed 2048-token
  output budget was tuned against simpler test transcripts and ran out
  before the JSON object could close on one with more speakers and
  discussion points. The output-budget threshold is now wider, and a
  truncated response is retried once with double the budget before the
  analysis is reported as failed, since no fixed per-tier number can be
  exactly right for every real transcript's content in advance.
- A real result showed a short summary reduced to two highlight titles
  glued together ("Technical Constraints and Timeframe. Discovery Phase
  Documentation Requirements.") instead of a sentence: the model's own
  summary had failed evidence-grounding, and the fallback for that case
  concatenated structured highlight/decision/action text verbatim, which
  reads as labels once several are joined, not narrative prose. That
  fallback is now a last resort -- the model gets one reinforced retry,
  explicitly told its previous summary was not grounded in its cited
  evidence, before falling back to concatenation.

### Added

- Three selectable smart-summary quality tiers (Fast, Balanced, High
  quality), each an independently downloadable local model. The one-time
  companion setup screen lets a user pick one by name and download size
  before installing. Balanced is the new recommended default; Fast is kept
  for the smallest download only, since it was found to fail evidence
  grounding almost entirely on real meeting speech.

## 2026.08.18 - 2026-08-24

### Fixed

- Local speaker-transcription timeouts now scale with recording duration, so
  long meetings are not incorrectly marked failed after the fixed 30-minute
  browser waiting limit.
- Existing saved transcript segments can be analyzed after speaker processing
  fails or is cancelled. NotesBuddy clearly identifies summaries generated
  from a provisional browser transcript instead of disabling refresh.

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
