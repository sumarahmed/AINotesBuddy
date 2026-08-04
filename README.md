# NotesBuddy

NotesBuddy is a local-first meeting recorder and notes workspace. The browser
client can capture your microphone and supported meeting audio as synchronized
tracks, save them in the current browser profile, play each source back, and
send them to either an optional local companion or a centrally hosted service
for speech-to-text and speaker diarization.

> **Project status:** Functional prototype. The source client uses a
> local-first hybrid mode: it prefers the Windows companion and keeps the
> centrally hosted API as a fallback. NotesBuddy is an
> independent project inspired by local-first meeting tools such as Meetily and
> is not affiliated with Meetily.

**Current version:** `2026.08.6` (`Year.Month.MinorRelease`)

## What works

- Separate **My microphone**, **Meeting audio**, and **Mixed recording** assets
- Meeting-only capture when the local user is listening rather than speaking
- Pause, resume, playback, seeking, source switching, download, and reload
- Microphone-only fallback if meeting sharing is cancelled or unsupported
- Persistent warning when meeting sharing stops during a recording
- Optional browser live-speech draft showing **You** and provisional **Guest**
  labels from synchronized meeting-output activity, with no inserted sample text
- Local faster-whisper transcription and pyannote speaker diarization companion
- Windows tray/control-panel app with automatic short-lived browser pairing
- Existing-user website warnings and daily desktop checks for companion updates
- Local-first website selection with a disclosed online fallback
- First-entry Windows setup guide with download, installation, and live
  connection confirmation
- Hosted anonymous-session API and browser client with per-session job isolation
- Serverless GPU deployment package with a persistent model cache
- Automatic **You** attribution for the isolated microphone track
- Session-local **Speaker 1**, **Speaker 2**, and unknown-speaker labels for
  meeting audio
- Word-level cross-channel echo cleanup that preserves local speech while
  keeping leaked meeting speech under its diarized remote speaker
- Professional analysis of the complete transcript with a sub-300-word short
  summary, consolidated highlights, confirmed decisions, and structured action
  items
- Transcript-segment evidence citations plus server validation that rejects
  unsupported decisions, tasks, owners, dates, priorities, and notes
- Speaker rename, transcript search, copy, and Markdown export
- Local profile, notes, structured action items, and Markdown export
- Backward-compatible playback for legacy single-asset meetings
- Direct `index.html` launch and a dependency-free static client build

NotesBuddy performs speaker *diarization*: it determines which detected voice
spoke when. It does not perform voice biometrics and cannot discover a real
person's name. The user assigns names after transcription.

## Quick start

### Browser client

Open `index.html` directly, or run the local static server:

```bash
npm run dev
```

Then visit <http://127.0.0.1:4173>. Node.js 20 or later is required for the
server and repository checks. The static client itself has no npm dependencies.

For meeting audio:

1. Leave **Meeting audio** enabled.
2. Press **Start capture**.
3. With companion `2026.08.1` or later connected, NotesBuddy records the
   default Windows output directly. No browser share picker is shown. In Teams,
   select the same speaker device that Windows uses as its default output.
4. Without the companion, **Teams on the web** can use a shared Teams tab with
   **Also share tab audio**. For the Teams desktop app, browser fallback requires
   **Entire Screen** with **Also share system audio**; a Teams window alone can
   still return a silent browser track.
5. Ask another participant to speak and confirm the Meeting badge changes from
   **Waiting for sound** to **Sound detected** before continuing.

The companion uses Windows WASAPI loopback only while capture is active. It
saves Windows output and microphone as separate synchronized tracks, which
preserves remote voices for transcription and reliable playback. Browser
fallback temporarily requires a display video track to maintain the share, but
NotesBuddy never records, stores, or displays that video. Current Chrome or
Edge on Windows is recommended.

Speaker separation happens after the recording is transcribed. It can group
distinct voices as **Speaker 1**, **Speaker 2**, and so on, but it cannot learn
their real names from Teams. Rename those session-local labels after
transcription. Very short turns, overlapping speech, low volume, and heavily
compressed meeting audio can still cause two people to be grouped together.

During capture, NotesBuddy can distinguish the isolated microphone as **You**
and active Windows/shared output as a provisional **Guest**. The live Guest
label is a timing hint, not voice recognition. Browser Speech Recognition still
listens to the microphone, so Guest words appear live only when that service
hears the remote voice; with headphones it may show **Guest speaking** without
words. After processing, the saved draft is replaced by the synchronized
microphone transcript plus pyannote's **Speaker 1**, **Speaker 2**, and other
remote groups.

### Local speaker transcription

For normal Windows users, install the companion from the repository's latest
GitHub Release, start it, and reopen NotesBuddy. The website pairs
automatically—there is no Python, model-token, or pairing-token setup per user.
When Chrome or Edge asks for **Local network access**, choose **Allow** so the
public HTTPS page can reach the private companion on `127.0.0.1`. If it was
denied, change that permission in the address-bar site controls and check the
connection again.
See the [Desktop Companion guide](docs/DESKTOP_COMPANION.md).

For source development, run the manual CLI on the same computer:

```powershell
cd services\transcription
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:HF_TOKEN = "your-local-hugging-face-token"
python run.py
```

In another terminal, display the persistent pairing token:

```powershell
cd services\transcription
.\.venv\Scripts\Activate.ps1
python run.py --show-token
```

In NotesBuddy, open **Settings**, keep the companion URL at
`http://127.0.0.1:8765`, paste the pairing token, and choose **Test
connection**. After a meeting, open **Transcript** and choose **Transcribe and
identify speakers**.

The pyannote community model requires accepting its model terms before the
first download. See the complete [companion setup and troubleshooting
guide](services/transcription/README.md).

### Public hosted transcription

Public users should not install a companion or configure any token. In hosted
mode, the site creates an expiring anonymous session and sends selected audio
over HTTPS to a centrally managed service. The owner's Hugging Face token stays
in the hosting provider's secret manager.

The deployment package currently targets Modal. See [Public hosted
transcription](docs/HOSTED_TRANSCRIPTION.md) for the deployment, safeguards,
operating limits, and future subscription migration.

## Data and privacy

| Data | Location |
| --- | --- |
| Profile, meeting records, speaker names, transcripts, settings | Browser `localStorage` |
| Microphone, meeting, and mixed audio Blobs | Browser IndexedDB |
| Active Windows-output capture | Companion temporary WAV; transferred locally and deleted when capture finishes |
| Automatic desktop pairing token | Page memory only; expires and is revoked on companion restart |
| Manual recovery token | User-local companion token file; browser storage only in manual CLI mode |
| Transcription job audio | Temporary local/hosted job directory, deleted after terminal state |
| Hosted anonymous session | Browser `sessionStorage`, expiring |
| Professional-analysis request | Completed transcript sent to the configured analysis service; no recording audio in this request |
| Speech and diarization models | Local or hosted model cache |

Windows-output capture includes everything played through the selected default
speaker while recording, including notification sounds. Meeting records are not synchronized between people, devices, browsers, or
site origins. Hosted processing returns the result only to the requesting
anonymous session. The local profile is not an account. Two users sharing one
operating-system browser profile share the same NotesBuddy workspace, while
different browser profiles have separate storage.

The local companion binds to `127.0.0.1` and requires a 256-bit pairing token.
Hosted mode uses expiring anonymous sessions, per-session job ownership, CORS,
rate/size limits, and temporary upload deletion. Browser live speech
recognition is separate and may use the browser provider's service.

See [Privacy and data handling](docs/PRIVACY.md).

## Commands

| Command | Purpose |
| --- | --- |
| `npm run dev` | Serve source at `http://127.0.0.1:4173` |
| `npm run build` | Recreate the static bundle in `dist/` |
| `npm run preview` | Serve `dist/client` locally |
| `npm run test:unit` | Run browser-module state and transcript tests |
| `npm run test:service` | Run Python alignment plus local/hosted API tests after API dependencies are installed |
| `npm run test:browser` | Run the optional Playwright synthetic-media browser suite |
| `npm test` | Syntax-check, unit-test, build, and verify tracked `dist/` |

The browser suite uses generated oscillators rather than a real microphone or
confidential meeting. Its setup is documented in [Testing](docs/TESTING.md).

## Repository layout

```text
.
|-- .github/                       CI and deployment workflows
|-- desktop/                       Windows packaging, installer, model preparation
|-- docs/                          Architecture, privacy, and testing guides
|-- services/transcription/
|   |-- notesbuddy_transcription/  Local API, model adapter, and alignment core
|   |-- tests/                     Python unit and API integration tests
|   |-- modal_app.py               Hosted anonymous GPU API deployment
|   |-- desktop_app.py             Windows tray/control-panel launcher
|   `-- run.py                     Local companion launcher
|-- src/
|   |-- runtime-config.js          Public local/hosted mode and endpoint
|   |-- meeting-audio.js           Recording assets, transcript, and API client
|   |-- app.js                     Application UI, capture, playback, persistence
|   `-- styles.css                 Responsive visual system
|-- tests/                         JavaScript and browser smoke tests
|-- build.mjs                      Static production build
|-- index.html                     Direct-launch entry point
`-- server.mjs                     Local static server
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Meeting-audio implementation plan](docs/MEETING_AUDIO_DIARIZATION_PLAN.md)
- [Desktop Companion user and release guide](docs/DESKTOP_COMPANION.md)
- [Desktop Companion architecture and rollout plan](docs/DESKTOP_COMPANION_PLAN.md)
- [Local transcription companion](services/transcription/README.md)
- [Public hosted transcription](docs/HOSTED_TRANSCRIPTION.md)
- [Configuration and fixed-value audit](docs/CONFIGURATION.md)
- [Privacy and data handling](docs/PRIVACY.md)
- [Testing guide](docs/TESTING.md)
- [GitHub publishing checklist](docs/GITHUB_SETUP.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)

## Current limitations

- Direct system-output capture requires companion `2026.08.1` or later on
  Windows. The browser-only fallback still requires an explicit share prompt
  and some surface/browser combinations do not expose audio.
- The Windows installer is large because it includes offline models. Publishing
  it requires a one-time model-license review and gated build secret.
- A running browser page cannot start the local companion automatically.
- The client has no accounts, encrypted storage, sync, or multi-device data.
- Anonymous hosted access is a prototype safeguard, not a subscription,
  entitlement, or production abuse-prevention boundary.
- Professional analysis depends on model availability and must still be
  reviewed against the transcript for high-impact decisions.
- Overlapping speech and poor audio can reduce diarization accuracy; users
  should review labels before relying on them.

## License

No open-source license has been selected. Until one is added, default copyright
restrictions apply.
