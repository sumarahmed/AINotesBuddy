# NotesBuddy Desktop Companion

The Windows companion lets the public NotesBuddy website use this computer for
speech-to-text and speaker diarization. Users install it once; they do not need
Python, Modal, a Hugging Face account, a model token, or a NotesBuddy pairing
token.

The companion is the local **capture and processing host**. Version `2026.08.1`
records the default Windows output through WASAPI loopback while a NotesBuddy
capture is active. It does not join meetings as a bot and does not record while
NotesBuddy is idle.

Version `2026.08.2` adds two update safeguards. The website compares every
connected companion with its public latest-version setting and shows existing
users a persistent warning when it is old. The companion also checks the latest
GitHub Release shortly after startup and every 24 hours, then shows a tray
notification and enables **Download update**. It never downloads or installs an
update without the user's choice, and a failed check does not affect recording.

Version `2026.08.3` aligns microphone and meeting-output words before building
speaker segments. Matching meeting speech that leaked into the microphone is
removed word by word, while unmatched microphone speech remains **You** and the
meeting copy retains its pyannote speaker assignment.

Version `2026.08.5` locally watches Microsoft Teams' Windows audio-session and
microphone-use state. Sustained activity shows one clickable Windows
notification per meeting. Clicking it opens the NotesBuddy capture screen, but
recording still starts only after the user selects **Start capture**. The
control panel includes an on/off preference, and short audio activity is
debounced to reduce ringtone and device-test notifications.

Version `2026.08.6` prefers a compatible NVIDIA GPU automatically for
faster-whisper speech transcription, while speaker diarization remains on the
local CPU. It reports the selected device to the website and falls back to CPU
`int8` if CUDA cannot initialize. A connected companion processes recordings
of every length locally.

Version `2026.08.7` separates the application from reusable AI components.
The core installer does not contain model weights or CUDA/cuDNN. On first
connection the website offers Balanced (`faster-whisper-base`) or Accurate
(`faster-whisper-small`) speech, installs speaker recognition, and adds the
NVIDIA pack only on a compatible machine. Components live under
`%LOCALAPPDATA%\NotesBuddy\components`, are SHA-256 verified, resume after an
interrupted download, and remain installed across application upgrades.

Version `2026.08.8` repairs interrupted component downloads that previously
could fail with HTTP 416. A complete partial archive is verified and installed
without another network request, stale oversized files are reset, and a server
that rejects a resume request is retried once from the beginning.

Version `2026.08.9` supports Windows extended paths while extracting the
speaker runtime, activates optional NVIDIA DLLs through the process search
path, and retries failed CUDA inference on CPU. Stable component checksums are
independent of the core application version, so core-only upgrades reuse
existing model and GPU packs.

Version `2026.08.11` includes private, model-free meeting analysis in the local
companion. Every summary, highlight, decision, and action is validated against
cited transcript segments. The website prefers this local analyzer when the
companion is connected, so a hosted analysis outage does not block refreshes.

Version `2026.09.01` fixes local smart-summary analysis, which previously
failed on every real meeting: the bundled `llama.cpp` runtime's Jinja chat
template was incompatible with JSON-schema-constrained output. The three
smart-summary quality tiers (Fast, Balanced, High quality) are now real,
publicly downloadable components, and Settings can switch or download a
different tier at any time after initial setup. Cross-chunk analysis merging
is deterministic instead of asking the model to re-synthesize partial
results, and the website shows live per-chunk progress and an elapsed timer
while an analysis runs instead of a static "Analyzing…" message.

Versions `2026.09.02` through `2026.09.09` are a rapid bug-fix sequence for
real meeting analyses, each verified against a live retry rather than assumed
fixed from a synthetic test: a widened output-token budget with a retry for
truncated JSON on longer meetings; a reinforced retry when the model's own
summary fails evidence-grounding, before falling back to less readable
concatenated field text; a fix for that fallback, and separately the
cross-chunk merge, discarding a reinforcement retry's own highlights,
decisions, and action items, or re-validating an already-verified
concatenated summary too strictly; and diagnostic logging that now actually
reaches a log file from the packaged `console=False` build, since a plain
`print()` is silently discarded there even when the launching process
redirects output.

Version `2026.09.10` fixes Windows-output capture silently listening to the
wrong device while a Bluetooth headset is connected: `soundcard`'s
`default_speaker()` only ever queries the Console role, while meeting/VoIP
audio generally follows the separate Communications role, which Windows
switches to a connected headset independently of Console/Multimedia --
confirmed by reading the bundled library's own WASAPI backend, not assumed.
Loopback capture now prefers a device matching the Communications-role
default (via `pycaw`, already a dependency), falling back to the previous
Console-role match unchanged when none is found. The same release adds
diagnostic logging to the transcription engine and job pipeline itself
(previously the one part of the companion with none at all -- an empty
transcript was indistinguishable from a genuine failure with nothing to
investigate), and live guest captions: the meeting-audio recording is now
re-transcribed every ~5 seconds while still being captured, so guest speech
appears in the live transcript during recording instead of only after
**Transcribe and identify speakers**, working the same way whether or not
headphones prevent the old mic-leakage-based approach from ever seeing guest
audio at all. The same release also adds an optional **GPU acceleration for
smart summary** component: local smart-summary generation previously always
ran on CPU (the bundled `llama.cpp` runtime had no CUDA backend compiled in
at all), confirmed structural by downloading and inspecting llama.cpp's own
official CUDA build for the same pinned release before adding it as a new
component. Settings offers it once a compatible GPU is already accelerating
transcription. See [`CHANGELOG.md`](../CHANGELOG.md) for the full list.

## User flow

1. Create the local browser profile on the NotesBuddy website.
2. Follow the displayed **Install the Windows companion** guide; its download
   button targets the current versioned `.exe` asset directly.
3. Run `NotesBuddyCompanion-Setup-<version>.exe`. Administrator rights are not
   required.
4. Leave the companion running in the Windows notification area.
5. Return to the website and choose **I've installed it — check connection**.
   NotesBuddy checks `http://127.0.0.1:8765`, pairs automatically, and verifies
   the API and secure pairing. Choose a local model; NotesBuddy downloads and
   verifies the reusable components before showing **Desktop companion is working**.
6. If Chrome or Edge asks whether the site can access devices on the local
   network, allow it. The service remains bound to this computer only.
7. Start a capture and ask another meeting participant to speak. The Meeting
   badge should change from **Waiting for sound** to **Sound detected** without
   opening the browser share picker.

If that permission was denied, open the site controls beside the browser
address bar, set **Local network access** to **Allow**, and choose **I've
installed it — check connection** again.

If the companion is stopped and no verified hosted endpoint is configured,
the site keeps recording and playback local but does not advertise an online
transcription option that cannot complete. Start the companion and choose
**Look for companion** to restore transcription and analysis. Confirmed setup
is stored with the local browser settings and can be reopened from
**Settings → Setup guide**.

Closing the control-panel window hides it in the notification area. Use the
tray menu's **Quit** command to stop the service. The **Start when I sign in**
option can be changed in the control panel or selected during installation.

## Privacy and pairing

- The service listens only on IPv4 loopback `127.0.0.1`.
- `GET /v1/companion` exposes safe discovery metadata and no secret.
- `POST /v1/pairings` accepts only exact trusted website origins.
- Missing, `null`, and unknown origins cannot obtain an automatic token.
- The website receives a random, expiring token and holds it only in page
  memory. Restarting the companion revokes all automatic browser pairings.
- A persistent user-local token remains available through **Copy recovery
  token** for manual diagnostics; normal users never need it.
- Job audio uses a random OS temporary directory and is deleted after success,
  failure, or cancellation.
- Active Windows output is written to a temporary WAV, transferred over
  `127.0.0.1` when capture finishes, and deleted by the companion immediately
  after the response. It includes all sounds sent to the default Windows
  speaker during that interval.
- The application does not open a Windows Firewall port.
- Meeting detection reads only local Windows audio-session state and Teams'
  microphone-use status. It does not read Teams messages, participants,
  calendar events, or meeting content, and it records no audio while watching.

The website may use an online fallback when the companion is unavailable.
Settings discloses which path is currently active.

## Offline models and publisher secret

Public releases provide independent reusable assets for:

- `Systran/faster-whisper-small`;
- `pyannote/speaker-diarization-community-1`;
- three smart-summary quality tiers, each a Q4_K_M GGUF paired with a pinned
  `llama.cpp` Windows runtime: `analysis-tiny` (`Qwen/Qwen2.5-0.5B-Instruct-GGUF`),
  `analysis-standard` (`unsloth/Qwen3-1.7B-GGUF`, recommended default), and
  `analysis-pro` (`unsloth/Qwen3-4B-Instruct-2507-GGUF`). All three share one
  destination folder, so installing a different tier replaces whichever was
  installed before. See [`desktop/MODEL_NOTICES.md`](../desktop/MODEL_NOTICES.md)
  for why Balanced is recommended over Fast;
- `analysis-cuda`, an optional GPU-capable `llama.cpp` runtime for the smart-summary
  step, sharing that same destination folder -- installing it replaces the
  CPU-only runtime in place, the same way switching quality tiers already
  does. Ships no model weights of its own; a quality tier must already be
  installed. Switching tiers afterward reinstalls that tier's own bundled
  CPU-only runtime, silently reverting to CPU until `analysis-cuda` is
  reinstalled -- a known rough edge, not a bug.

The publisher—not each customer—accepts the gated model conditions and uses a
read-only `HF_TOKEN` only when intentionally preparing a new component release.
Core companion releases reuse the pinned public component manifest and do not
need the token. Component preparation records immutable model revisions and
does not write the token to an artifact.

Before public distribution, review
[`desktop/MODEL_NOTICES.md`](../desktop/MODEL_NOTICES.md). The model preparation
step deliberately requires `--accept-pyannote-terms`.

## Create a release

Run **Windows desktop companion** from the Actions tab to test a core installer.
When ready, create and push a tag such as `companion-v2026.09.09`.

The tag workflow runs service tests, builds a PyInstaller one-directory
application, executes the packaged `--self-test`, creates a per-user Inno Setup
installer, uploads the Actions artifact, and attaches the installer to the
matching GitHub Release. It does not rebuild unchanged component ZIPs.

Only when model, speaker-worker, or GPU contents intentionally change, configure
the publisher's gated-model `HF_TOKEN`, run `desktop/prepare_components.py`,
publish those component ZIPs, and update `desktop/component-manifest.json` with
their immutable URLs, sizes, and checksums.

The Smart summary components are public and do not need `HF_TOKEN`. Each tier
can be built independently while retaining existing manifest entries; repeat
`--component` to build more than one in the same run:

```powershell
python desktop/prepare_components.py `
  --version 2026.08.18 `
  --component analysis-tiny `
  --component analysis-standard `
  --component analysis-pro
```

The builder verifies the pinned model and runtime hashes, packages only
`llama-cli.exe` and its required DLLs, includes both upstream license texts,
and records provenance inside the component ZIP. Publish the generated ZIP to
the matching `companion-v<version>` release before committing the generated
manifest entry; the release workflow rejects missing or altered public assets.

## Local developer build

Use Python 3.11 on Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r services\transcription\requirements-packaging.txt
.\desktop\build.ps1 -Python python -Version 2026.09.09
```

Build output is ignored under `desktop/out/` and `desktop/release/`. The model
directory is also ignored and must never be committed.

For a dependency-light package smoke test, omit model preparation and run:

```powershell
.\desktop\build.ps1 -Python python -Version 2026.09.09 -SkipInstaller
.\desktop\out\dist\NotesBuddyCompanion\NotesBuddyCompanion.exe --self-test
```

## Troubleshooting

**The website says online fallback**

- Start **NotesBuddy Desktop Companion** from the Start menu.
- In Settings, choose **Look for companion**.
- Allow the browser's local-network permission if prompted.
- Close any older source/CLI companion already occupying port 8765.

**The companion opens but transcription fails**

- Open the website setup guide and confirm the selected model packs completed.
- Check `%LOCALAPPDATA%\NotesBuddy\components` instead of the application
  installation directory.
- Keep the CPU defaults for the first test; model loading can take time.

**Teams participants are missing**

- Confirm the website reports companion `2026.08.1` or later. Older companions
  cannot capture Windows output directly.
- In Teams **Device settings**, choose the same speaker that Windows uses as
  its default output.
- Ask another participant to speak and confirm the capture UI says **Sound
  detected**. Microphone activity does not count as meeting-output activity.
- If the website opens a browser share picker, it is using fallback capture;
  restart/update the companion and choose **Look for companion** in Settings.
- Use headphones to reduce the local microphone picking up remote echo.

**Live Guest captions never appear during recording**

- Confirm the website reports companion `2026.09.10` or later. Older
  companions only produce guest text after **Transcribe and identify
  speakers**, not live.
- Confirm the Meeting badge reaches **Sound detected** first -- live
  captions transcribe the same captured recording, so they need real audio
  in it. Expect roughly 5-10 seconds of delay after speech starts before the
  first words appear.
- This does not depend on headphones. If it still never appears with a
  current companion and confirmed sound detected, check
  `%LOCALAPPDATA%\NotesBuddy\logs\companion.log`.

Speaker diarization distinguishes detected voices by time. It does not know
people's real names; users rename **Speaker 1**, **Speaker 2**, and so on after
processing.
