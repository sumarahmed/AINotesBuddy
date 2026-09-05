# Changelog

All notable changes to NotesBuddy are documented in this file.

The project follows the structure of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions use `Year.Month.MinorRelease`; package metadata omits leading zeroes to
remain compatible with semantic-version tooling.

## Unreleased

### Added

- Applying the unified icon (above) turned out to need two more follow-up
  spots, each reported live from a screenshot after the first round shipped:
  the companion window's own title bar (Tk defaults to its own feather logo
  until `iconbitmap` is set explicitly -- fixing the tray icon separately
  does not cover this) and the in-app sidebar logo (`BRAND.mark` in
  `app.js`, previously an unrelated hand-drawn musical-note glyph). See
  [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#brand-icon-surfaces) for
  the full checklist of every icon surface, kept together specifically so
  a future icon change does not repeat this same one-at-a-time discovery.

- One consistent icon everywhere: a teal roundel with an over-the-head
  headphone band, replacing what were previously several unrelated glyphs
  (the tray icon drew an ad hoc teal-square-with-play-triangle via PIL
  primitives; the website had no favicon at all; the installer and the
  companion `.exe` used Inno Setup's/PyInstaller's own defaults). Now a
  single design renders to every surface from one generator script: the
  website favicon (`favicon.svg`/`favicon.ico`), the Windows installer's
  own icon (`SetupIconFile`), the compiled `NotesBuddyCompanion.exe`'s icon
  (propagates automatically to its Start Menu/desktop shortcuts and the
  uninstaller, all of which already pointed at the exe's own icon), and the
  system tray icon (loaded from a bundled PNG instead of drawn ad hoc).

### Fixed

- Removed every remaining em dash from user-facing product text (the
  website's UI copy, page title, and meta description; the companion's
  status text), replacing each with whichever of a comma, semicolon, or
  parentheses fit the sentence.
- The desktop companion's own update-check (`desktop_app.py`) reported an
  update was available based on comparing version-tag strings alone, with
  no check that the release it found actually contained an installer.
  Reported live: a real notification for `2026.09.11`, a release that only
  ever contained the speaker-diarization-cuda component pack (this repo
  publishes component-only releases under the same `companion-v*` tag
  convention as real installer releases, and GitHub's "latest release" is
  simply whichever published most recently, regardless of content). The
  website's own equivalent check (`parseLatestCompanionRelease` in
  `meeting-audio.js`) already required finding an installer asset; the
  companion's Python version now does too.
- A second manual launch of the companion correctly never started a second
  server (the existing port-bind check already prevented that), but the
  window itself only closed automatically when detected during a silent
  autostart launch, not a manual double-click -- reported live as "I can
  open two companions at once," when in fact only one was ever functional.
  Both cases now close the window automatically, with a longer delay for
  the manual case so there is time to actually read why.
- The live transcript panel reset the reader's scroll position to the
  bottom roughly twice a second during an active capture, reported live as
  the page feeling like it was constantly reloading. The panel's entire
  contents were being replaced and force-scrolled on every tick of the
  500ms companion status poll, even on the (usual) tick where nothing new
  had arrived -- partial captions actually only refresh on a ~5s
  server-side interval. Now skips the update entirely when nothing changed,
  and only auto-scrolls when the reader was already near the bottom.

- Three real bugs caught during the live rollout of the GPU speaker
  recognition component below, none of them by local testing:
  - The `speaker-worker.yml` CI job's CUDA-torch reinstall silently no-op'd
    -- pip treats an installed `torch==2.14.0+cpu` as already satisfying a
    bare `torch==2.14.0` request (PEP 440 local-version matching ignores
    the `+cpu` suffix for `==` without one), so the GPU build's own
    self-test correctly still reported `+cpu` with no error at all until
    `--force-reinstall` was added.
  - The packaged component archive came out at 2.58 GiB using the default
    Deflate compression -- over GitHub's real 2 GiB release-asset limit,
    caught by an actual failed upload, not assumed from the limit alone.
    Switched to `ZIP_LZMA` (the same fix `nvidia-cuda12` already needed for
    the same reason), bringing it to 1.66 GiB.
  - `LocalDiarizationEngine.speaker_worker` was resolved once in `__init__`
    and cached -- harmless for the CPU/GPU choice made at companion
    startup, but this engine is a long-lived singleton for the whole server
    process, so installing `speaker-diarization-cuda` *while the companion
    was already running* (exactly the real install flow) left
    `diarizationDevice` reporting `cpu` until a full restart. Now a
    property that re-resolves from the environment on every access,
    matching the pattern `LocalAnalysisRouter._analyzer()` already used for
    the identical `analysis-cuda` scenario.

  A fourth issue was a test gap, not a shipped bug: `test_engine.py`'s
  shared fake-torch fixture only had `from_numpy()`, so any test resolving
  to `device="cpu"` hit the new CPU thread-tuning call and failed with
  `AttributeError` -- invisible on this GPU-equipped dev machine (`device`
  always resolved to `"cuda"` here, skipping that branch entirely) and
  caught for real only on CI's GPU-less runner.

  End-to-end verification after all four fixes, against the real installed
  companion: installed `speaker-diarization-cuda` through the live
  component-install API while the companion was running, then submitted a
  real ~24 minute meeting recording through `/v1/transcriptions`.
  `nvidia-smi` showed GPU utilization hit 100% specifically during the
  "identifying meeting speakers" stage; the job completed in ~97 seconds
  total (transcription + diarization) and correctly identified 5 distinct
  speakers.

### Added

- Optional **GPU acceleration for speaker recognition** component
  (`speaker-diarization-cuda`), the GPU half of the diarization performance
  investigation below. Sized before building anything: a CUDA-capable
  PyTorch wheel runs ~2.4 GiB (confirmed live against
  `download.pytorch.org`'s real wheel index for the exact torch version
  `pyannote.audio` actually resolves to), a materially bigger download than
  the small DLL packs used for the existing whisper/smart-summary GPU
  options -- and neither the CPU nor a GPU build of the isolated speaker
  worker had any CI automation at all before this (confirmed by checking
  every workflow and `desktop/build.ps1` directly; the previously pinned
  release asset was built by an undocumented manual process). Before
  committing to that cost, ran a real-audio validation gate first: built a
  throwaway CUDA-torch venv on a machine with a working NVIDIA GPU and
  diarized a real ~24 minute meeting recording twice, once on tuned CPU and
  once on GPU. Result: 62s on GPU vs. 731s on tuned CPU, an 11.8x speedup,
  with identical speaker-turn output (741 turns) on both -- confirming real
  speech fully exercises pyannote's clustering stage (an earlier synthetic
  test found zero turns, leaving open whether clustering would stay
  CPU-bound regardless of the neural-net stages moving to GPU; it does
  not). Only after that real signal did the actual packaging begin: a
  second executable, `NotesBuddySpeakerWorkerGPU.exe`, built from the exact
  same `speaker_worker.py` entry point as the CPU worker but with a
  CUDA-enabled torch/torchaudio in its build venv instead (new
  `.github/workflows/speaker-worker.yml`, building both variants for the
  first time); `speaker_worker.py` itself gained a `torch.cuda.is_available()`
  check that moves the pipeline to `cuda` automatically when present,
  falling back to CPU otherwise, so one script serves both builds.
  Deliberately installed into its own `speaker-gpu` destination, never the
  base component's shared `speaker` one -- `analysis-cuda` already hit
  exactly this bug once (see the 2026.09.0x entry below) by sharing a
  destination with a component that had a model file of its own to
  preserve, and component installation is a wholesale directory swap, not a
  file overlay. `LocalDiarizationEngine` prefers
  `NOTESBUDDY_SPEAKER_WORKER_GPU` over `NOTESBUDDY_SPEAKER_WORKER` when
  present; the shared pyannote model is untouched either way. One real trap
  hit and fixed along the way, worth remembering for any future GPU
  packaging work: `pyannote.audio`'s own dependency resolution silently
  replaced an explicitly-installed CUDA torch with a CPU-only build from
  default PyPI the moment it (re-)resolved its own torch pin -- fixed by
  reinstalling torch last, with `--no-deps`, from the CUDA wheel index.

- Diarization now explicitly configures PyTorch's CPU thread pool instead of
  leaving it at whatever default PyTorch picks. Investigated after a real
  ~1 hour meeting on the desktop companion took roughly an hour to diarize;
  confirmed live via `nvidia-smi` (0% GPU utilization throughout) and by
  reading the bundled `torch/version.py` in both the main companion
  (`2.13.0+cpu`) and the separate `NotesBuddySpeakerWorker.exe` subprocess
  it delegates to (also `2.13.0+cpu`) that neither bundled PyTorch build has
  CUDA support at all -- `requirements-models.txt` pins `torch>=2.6` with no
  CUDA index, so pip resolves PyPI's default CPU-only Windows wheel, and a
  CPU-only torch build cannot use the GPU regardless of any `.to(cuda)` call
  already present in `engine.py`. A genuine GPU build is a much larger,
  separately-scoped change (a CUDA torch wheel runs several GB, unlike the
  small DLL packs used for the existing whisper/smart-summary GPU options,
  and the speaker worker currently has no CI build automation at all --
  confirmed by checking every workflow and `desktop/build.ps1`). This change
  is the free, zero-download half of that investigation: neither `engine.py`
  nor `speaker_worker.py` set `torch.set_num_threads`/`OMP_NUM_THREADS`
  anywhere before, so PyTorch's own thread-count default was left to guess.
  New shared `notesbuddy_transcription/cpu_threads.py` resolves a thread
  count (every logical core by default, overridable via
  `NOTESBUDDY_DIARIZATION_CPU_THREADS`) and applies it: as an
  `OMP_NUM_THREADS`/`MKL_NUM_THREADS` env default before the isolated
  speaker worker's first `import torch` (env vars only take effect at
  native thread-pool init, so this has to run before that import, not
  after), and via a direct `torch.set_num_threads()`/
  `set_num_interop_threads(1)` call for the in-process fallback path used
  when no separate worker is configured. The GPU wheel swap remains a
  separate, larger piece of work, sized and scoped on its own before any
  implementation starts.

- The website's companion-update check now also queries GitHub's real
  release API directly on page load (`GET /repos/.../releases/latest`,
  which allows unauthenticated cross-origin requests -- confirmed live, not
  assumed) instead of relying solely on a static version string baked into
  `src/runtime-config.js` at deploy time, which only stayed accurate as
  long as someone remembered to bump it on every companion release. Cached
  in `localStorage` for 12 hours to stay well inside GitHub's
  60-requests-per-hour unauthenticated limit even on a shared corporate
  network; a failed or rate-limited check silently falls back to the
  static value, verified live by simulating a network failure. The parsing
  logic (find the installer asset, strip the `companion-v` tag prefix) is
  a pure function in `meeting-audio.js`, directly unit tested rather than
  living inline in the fetch call.

- Optional GPU acceleration for local smart-summary generation, previously
  always CPU-only. Confirmed structural rather than a missed flag: the
  bundled `llama.cpp` runtime is llama.cpp's own official CPU-only Windows
  release asset, with no CUDA backend compiled in at all. Verified feasible
  directly, not assumed -- downloaded and inspected llama.cpp's official
  CUDA build for the exact same pinned release: a complete, self-consistent
  alternate runtime whose only external dependencies (checked via `grep -a`
  on its own import strings) are `cublas64_12.dll` (already provided by the
  existing NVIDIA whisper-acceleration pack) and `cudart64_12.dll` (one
  ~540KB file, extracted at release-build time from a ~391MB redistributable
  so end users never download that whole archive). A new optional
  `analysis-cuda` component carries this alternate runtime, installed into
  its own `analysis-gpu` destination rather than the `analysis` one the
  three quality tiers share. That separation was itself a real fix, not the
  original design: component installation replaces a destination directory
  wholesale (renamed aside, not merged file-by-file), confirmed the hard
  way when an earlier version sharing the tiers' own destination silently
  deleted the installed GGUF the first time `analysis-cuda` -- a
  runtime-only package with no model file of its own -- was installed on a
  real machine, verified live and fixed before this ever reached a
  released build. `LocalAnalysisRouter` now prefers the separate GPU
  runtime, when present, over the CPU-only one; the GGUF always resolves
  from the untouched `analysis` directory regardless of which runtime is
  active. `LlamaCppMeetingAnalyzer` offloads all
  layers only when the installed runtime actually has the CUDA backend *and*
  the same GPU-availability probe `LocalDiarizationEngine` already uses for
  speech-to-text confirms a usable GPU, retrying once on CPU if a
  GPU-flagged run fails. Offered in Settings once a compatible GPU is
  already accelerating transcription, and auto-included during first-time
  setup under the same condition -- an opt-in ~250MB addition, not bundled
  for everyone, since most users don't have a discrete NVIDIA GPU.

- Guest speech now appears in the live transcript panel while a meeting is
  still recording, whether or not headphones are worn. Previously, live
  "Guest" text only ever appeared by accident: without headphones, the
  other side's audio leaked acoustically out of the speakers into the
  microphone, and the browser's own speech recognition happened to pick it
  up, guessed at "Guest" via a timing heuristic against a meeting-activity
  signal. With headphones there is no leakage path, so nothing guest-side
  ever appeared live -- the real content only existed once "Transcribe and
  identify speakers" ran the full pipeline after Finish. The companion now
  re-transcribes a bounded trailing window (~25s) of the meeting-audio
  loopback recording every ~5 seconds while it's still being captured,
  in-process and read-only against the file `system_audio.py` is still
  writing, and returns the result over a new
  `GET /v1/system-audio/captures/{id}/partial-transcript` route. The
  browser wholesale-replaces the live provisional-guest rows on every poll
  (mirroring how the final diarized transcript already wholesale-replaces
  every provisional row, rather than tracking a cursor/dedup state), and
  sorts the live segment list by timestamp afterward, since a guest word
  from a several-second-delayed poll can arrive with an earlier timestamp
  than a microphone segment already on screen. This mechanism fully
  replaces the old mic-leakage heuristic for everyone -- microphone speech
  is always attributed to the local user now, since it's a strictly
  cleaner signal that no longer depends on acoustic leakage at all.

- `engine.py` and `server.py`, the actual local faster-whisper/pyannote
  pipeline, had no diagnostic logging at all -- confirmed by reading both
  files after a real report of a completed recording (real speech confirmed
  present in the microphone, meeting-output signal correctly detected)
  coming back with a genuinely empty transcript and no visible error
  anywhere, client or server. An empty result is not a failure state today:
  the job still completes with `status: "completed"`, so the existing
  `job.error` field is never populated for it either. `_log_diagnostic`/
  `_diagnostic_log_path`, previously private to `analysis.py`, moved to a new
  shared `diagnostics.py` module; `engine.process()` now logs per-source
  bytes received, transcribed word counts, diarization turn counts, and an
  explicit warning line (with likely cause) whenever it produces zero
  segments; `server.py` logs per-source upload byte sizes and each job's
  final outcome by job id. All of it lands in the same
  `%LOCALAPPDATA%\NotesBuddy\logs\companion.log` the smart-summary stage
  already writes to.

### Fixed

- Running the Python test suite on a real machine was writing directly into
  the real `%LOCALAPPDATA%\NotesBuddy\logs\companion.log` -- confirmed after
  a log tail handed back to diagnose an empty transcript turned out to be a
  previous test run of this suite, with fake job ids and engine names
  indistinguishable at a glance from genuine activity. `test_server.py` and
  `test_engine.py` now redirect `NOTESBUDDY_LOG_DIR` to a throwaway
  directory for their whole module. Separately, the live-caption background
  thread's per-tick work (file read, PCM conversion, transcription) is now
  one unit under a single broad exception handler instead of narrowly around
  just the transcription call -- a failure anywhere in a tick previously
  killed the whole thread permanently, silently stopping live captions for
  the rest of that recording with nothing surfaced anywhere, since a
  thread's exception has nowhere to propagate. Caught by CI, not local
  testing: the lightweight `requirements-test.txt` set didn't include numpy,
  which the local verification venv already had as a transitive
  faster-whisper/torch dependency.

- An empty-but-successfully-completed transcript showed the same "Speaker
  transcript ready" toast as a real result, just with "0 speakers" --
  indistinguishable from success at a glance. It now shows "No speech
  detected" with guidance to check the capture devices instead.

- Companion Windows-output capture never detected sound while connected to a
  Bluetooth headset, confirmed live from a screenshot showing the status card
  stuck on "Listening to Speakers (Realtek(R) Audio)" -- the onboard device --
  while meeting audio was actually playing through the headset. Root cause,
  confirmed by reading the bundled `soundcard` package's own Windows backend:
  `soundcard.default_speaker()` queries Windows' Console-role default output
  device. Meeting/VoIP audio instead follows the separate Communications-role
  default, which Windows switches to a connected Bluetooth headset
  independently of Console/Multimedia -- the two roles can point at different
  physical devices, so loopback capture silently attached to the wrong one
  and never received the meeting's audio. `SoundCardLoopbackBackend` now
  queries the Communications-role default endpoint id directly (via `pycaw`,
  already a companion dependency) and prefers a loopback source matching it,
  falling back to the previous Console-role speaker match unchanged when no
  Communications-role device is found. The reported device name shown in the
  UI now also reflects whichever device was actually matched, rather than
  always the Console-role speaker's name.

- Decisions and action items came back empty for two different real
  meetings, across every chunk and every retry, confirmed live via the
  diagnostic logging above: the model's own raw JSON output never
  contained anything in those arrays, even though its own generated
  summary text clearly described committed actions ("an invite will be
  sent to Ramana", "the agreement was made to hold the workshop on
  Tuesday at 1 PM"). Not a validation or merge bug -- there was nothing to
  validate. The `decisions`/`actionItems` instructions carry noticeably
  more constraints than `highlights` (confirmed-only, strict date
  provenance, "commitment not prerequisite"), which the installed model
  was apparently treating as a bar it could not clear, defaulting to
  empty arrays. The prompt now includes a concrete worked example showing
  a decision and an action item extracted from a short exchange, and
  explicitly asks the model to look for them even when mentioned briefly
  in passing, not only when formally announced. Analysis prompt version
  bumped to 3.

### Added

- Diagnostic logging now records highlights/decisions/actionItems counts
  (both raw model output and post-validation) at every per-chunk and merge
  stage, not only the summary text -- to diagnose a report of highlights,
  decisions, and action items all coming back empty, without guessing at a
  fix again.

### Fixed

- Confirmed with a real retry and the diagnostic logging above: a chunk's
  reinforcement retry (see the 2026.09.02 summary fix) returned a summary
  describing a scheduled follow-up session and a to-be-sent document, yet
  that same response's highlights, decisions, and actionItems arrays came
  back completely empty -- the retry prompt's narrow focus on fixing the
  summary field caused the model to drop structured findings it clearly
  still had, and the first attempt's own findings were discarded even
  though they were never actually invalidated (a bad summary makes
  validation raise before anything else is checked). The retry now
  combines both attempts' highlights, decisions, and action items instead
  of using only whichever attempt happened to include them.
- Found the real cause of the recurring "Technical Constraints and
  Timeframe. Discovery Phase Documentation Requirements." bad-summary
  report, using diagnostic logging: on a real multi-chunk meeting, every
  chunk's own summary passed evidence-grounding individually (confirmed
  live in the log), but the merge step that combines chunks re-checked the
  *concatenated* summary against the combined evidence as if it were a
  single fresh model output, and that stricter re-check failed even though
  nothing in it was ungrounded. Merge then fell back to concatenating
  highlight/decision/action titles, producing the exact same bug the
  2026.09.02 reinforcement-retry fix was believed to have already fixed --
  that fix only ever covered the per-chunk path, not this separate
  merge-time one. Merge now trusts the partials' own already-validated
  summaries instead of re-deriving one from field titles.
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
