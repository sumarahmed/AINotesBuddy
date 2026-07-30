# NotesBuddy

NotesBuddy is a local-first meeting recorder and notes workspace. The browser
client can capture your microphone and supported meeting audio as synchronized
tracks, save them in the current browser profile, play each source back, and
send them to an optional local companion for speech-to-text and speaker
diarization.

> **Project status:** Functional prototype. This implementation is on
> `feature/meeting-audio-diarization`; it does not change or deploy `main`.
> NotesBuddy is an independent project inspired by local-first meeting tools
> such as Meetily and is not affiliated with Meetily.

## What works

- Separate **My microphone**, **Meeting audio**, and **Mixed recording** assets
- Meeting-only capture when the local user is listening rather than speaking
- Pause, resume, playback, seeking, source switching, download, and reload
- Microphone-only fallback if meeting sharing is cancelled or unsupported
- Persistent warning when meeting sharing stops during a recording
- Optional browser live-speech draft with no inserted sample text
- Local faster-whisper transcription and pyannote speaker diarization companion
- Automatic **You** attribution for the isolated microphone track
- Session-local **Speaker 1**, **Speaker 2**, and unknown-speaker labels for
  meeting audio
- Speaker rename, transcript search, copy, and Markdown export
- Local profile, notes, action items, and extractive transcript brief
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
3. Choose the meeting tab, window, or screen in the browser dialog.
4. Enable the dialog's **Share audio** option.

The browser temporarily requires a display video track to maintain the share,
but NotesBuddy never sends it to `MediaRecorder`, stores it, or displays it.
Meeting-audio availability depends on the browser, operating system, and
selected surface. Current Chrome or Edge on Windows is recommended.

### Local speaker transcription

The static client cannot safely contain or run the larger speech models. Run
the companion on the same computer:

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

## Data and privacy

| Data | Location |
| --- | --- |
| Profile, meeting records, speaker names, transcripts, settings | Browser `localStorage` |
| Microphone, meeting, and mixed audio Blobs | Browser IndexedDB |
| Pairing token | Browser settings and a user-local companion token file |
| Companion job audio | OS temporary directory, deleted after terminal job state |
| Speech and diarization models | Local model caches |

Nothing is synchronized between people, devices, browsers, or site origins.
The local profile is not an account. Two users sharing one operating-system
browser profile share the same NotesBuddy workspace, while different browser
profiles have separate storage.

The companion binds to `127.0.0.1`, checks an origin allowlist, requires a
256-bit pairing token, and does not log transcript content. Browser live speech
recognition is separate and may use the browser provider's service; it can be
disabled.

See [Privacy and data handling](docs/PRIVACY.md).

## Commands

| Command | Purpose |
| --- | --- |
| `npm run dev` | Serve source at `http://127.0.0.1:4173` |
| `npm run build` | Recreate the static bundle in `dist/` |
| `npm run preview` | Serve `dist/client` locally |
| `npm run test:unit` | Run browser-module state and transcript tests |
| `npm run test:service` | Run Python alignment and local API tests after API dependencies are installed |
| `npm run test:browser` | Run the optional Playwright synthetic-media browser suite |
| `npm test` | Syntax-check, unit-test, build, and verify tracked `dist/` |

The browser suite uses generated oscillators rather than a real microphone or
confidential meeting. Its setup is documented in [Testing](docs/TESTING.md).

## Repository layout

```text
.
|-- .github/                       CI and deployment workflows
|-- docs/                          Architecture, privacy, and testing guides
|-- services/transcription/
|   |-- notesbuddy_transcription/  Local API, model adapter, and alignment core
|   |-- tests/                     Python unit and API integration tests
|   `-- run.py                     Local companion launcher
|-- src/
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
- [Local transcription companion](services/transcription/README.md)
- [Configuration and fixed-value audit](docs/CONFIGURATION.md)
- [Privacy and data handling](docs/PRIVACY.md)
- [Testing guide](docs/TESTING.md)
- [GitHub publishing checklist](docs/GITHUB_SETUP.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)

## Current limitations

- Display-audio capture always requires an explicit browser share prompt.
- Some surface/browser combinations do not expose audio; there is no silent
  operating-system loopback capture.
- Initial model installation is large and requires network access and pyannote
  model access. Processing speed depends on the computer.
- A running browser page cannot start the local companion automatically.
- The client has no accounts, encrypted storage, sync, or multi-device data.
- Briefs are extractive transcript text, not LLM-generated conclusions.
- Overlapping speech and poor audio can reduce diarization accuracy; users
  should review labels before relying on them.

## License

No open-source license has been selected. Until one is added, default copyright
restrictions apply.
