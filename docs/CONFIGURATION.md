# Configuration and fixed-value audit

NotesBuddy does not ship a fixed person, fake meeting history, sample
transcript, fixed calendar event, or fixed date. The first-run profile supplies
the user's name and initials, dates come from the browser, and runtime records
use UUID identifiers.

The published version uses `Year.Month.MinorRelease`. The current release is
`2026.08.1`; `package.json` represents it as `2026.8.1` for semantic-version
compatibility.

## Browser settings

Settings are stored under `notesbuddy-settings` for the current browser origin.

| Setting | Default | Behavior |
| --- | --- | --- |
| Meeting audio | On | Capture default Windows output through a compatible companion; otherwise ask for a browser tab/window/screen audio source |
| Browser live transcript draft | On | Use browser speech recognition for microphone draft text when supported |
| Automatically identify speakers | Off | Start the paired local job after saving a recording |
| Create meeting brief | On | Build an extractive brief only from returned transcript segments |
| Keep source recordings | On | Save mic, meeting, and mixed Blobs in IndexedDB |
| Transcription mode | From `src/runtime-config.js` | `hybrid`, `local`, or centrally managed `hosted` |
| Companion URL | `http://127.0.0.1:8765` in local mode | Loopback-only local API |
| Pairing token | Empty in local mode | Must be copied from the local companion |
| Companion setup completed | Off until local health confirmation | Controls the first-entry Windows installation guide |

In `hybrid` mode, the browser first discovers and pairs with the fixed loopback
companion. The automatic token remains only in page memory. If discovery or
pairing fails, the centrally managed endpoint becomes the online fallback.
Hybrid and hosted users never see URL/token inputs or configure the owner's
model token. Explicit `local` mode retains manual CLI fields for development.
Deferring installation sets only a `sessionStorage` flag; it does not
permanently mark setup complete.

Changing a source toggle while capture is already running does not mutate live
streams. It applies to the next capture.

## Intentional browser constants

| Area | Value | Reason / change location |
| --- | --- | --- |
| Product name | `NotesBuddy` | Branding in `index.html`, app templates, docs |
| Product version | `2026.08.1` | `Year.Month.MinorRelease` in `src/runtime-config.js` and the companion launcher |
| Locale/language | `en-AU` | Date formatting and browser live speech in `src/app.js` |
| Development address | `127.0.0.1:4173` | Predictable loopback server in `server.mjs` |
| Runtime transcription mode | `hybrid` | Public non-secret setting in `src/runtime-config.js` |
| Local companion endpoint | `http://127.0.0.1:8765` | Fixed loopback discovery/API address |
| Hosted fallback endpoint | Deployment URL | Used when the companion is unavailable |
| Companion download URL | Latest GitHub Release | Public Windows installer destination |
| Storage keys | `notesbuddy-profile`, `notesbuddy-meetings`, `notesbuddy-settings`, `notesbuddy-audio` | Namespace isolation in `src/app.js` |
| IndexedDB schema | Version 1, `recordings` store | Blob persistence in `openAudioDatabase()` |
| Recorder preference | Opus WebM, WebM, then MP4 | First browser-supported type in `preferredRecordingType()` |
| Recorder chunk interval | 500 ms | Incremental data without excessive events |
| Display-audio hints | System audio included; window audio set to system | Encourages Chrome/Edge to expose Teams desktop sound when supported |
| Preferred meeting capture | Windows WASAPI loopback | Used when companion discovery reports `systemAudioCapture`; avoids silent Teams-window browser tracks |
| Meeting signal threshold | RMS 0.008 over 512 samples | Changes the live badge only after actual meeting sound arrives |
| Meeting silence warning | 5 seconds | Warns early while allowing quiet meetings to keep recording |
| Default meeting title | `Untitled meeting` | User-editable safe placeholder |
| Source IDs | `microphone`, `meeting`, `mixed` | Stable storage/API contract |
| Local speaker ID | `local-user` | Stable **You** attribution |
| Remote speaker IDs | `remote-1`, `remote-2`, ... | Session-local, first-appearance ordering |
| Echo thresholds | 55% time overlap, 82% text similarity | Conservative duplicate suppression in browser/service core |
| Unknown timing tolerance | 350 ms | Handles timestamp rounding without distant identity guesses |
| Legacy sample IDs | Four historical IDs | Removes demo records from older builds only |

`Speaker 1` is a generic diarization label, not a hard-coded person. Imported
mixed audio begins with one generic remote speaker record until transcription
returns actual session-local speaker groups.

## Profile and sessions

Profile, meeting, import, speech-segment, and companion-job IDs use UUIDs.
Browser fallback IDs contain independent random components.

The local profile:

- personalizes the greeting and initials;
- identifies isolated microphone speech as **You**;
- supplies the owner for locally created review actions;
- updates existing local participants/follow-ups when renamed.

It is not authentication. Different browser profiles/devices/origins have
separate storage. People sharing one operating-system browser profile share the
same NotesBuddy data.

## Companion environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `HF_TOKEN` | None | Access to the accepted pyannote community model |
| `NOTESBUDDY_MODEL_DIR` | Packaged `models` directory when present | Offline model bundle root |
| `NOTESBUDDY_ALLOWED_ORIGINS` | Direct file, local dev origins, `https://sumarahmed.github.io` | Comma-separated CORS allowlist |
| `NOTESBUDDY_PAIRING_TOKEN` | Persistent generated token | Optional explicit token override, at least 24 characters |
| `NOTESBUDDY_TOKEN_FILE` | OS user config location | Optional persistent token-file override |
| `NOTESBUDDY_WHISPER_MODEL` | `small` | faster-whisper model name/path |
| `NOTESBUDDY_MODEL_DEVICE` | `cpu` | `cpu`, `cuda`, or supported device |
| `NOTESBUDDY_WHISPER_COMPUTE_TYPE` | `int8` | faster-whisper compute type |
| `NOTESBUDDY_DIARIZATION_MODEL` | `pyannote/speaker-diarization-community-1` | pyannote model ID |
| `NOTESBUDDY_MAX_WORKERS` | `1` (clamped 1–2) | Concurrent model jobs |
| `NOTESBUDDY_MAX_JOBS` | `64` (clamped 4–256) | Maximum in-memory active/recent job records |
| `NOTESBUDDY_JOB_RETENTION_SECONDS` | `3600` (clamped 60–86400) | Recent terminal result retention in process memory |
| `NOTESBUDDY_MAX_SOURCE_BYTES` | 2 GiB local / 250 MiB hosted | Multipart per-source limit |
| `NOTESBUDDY_MAX_TOTAL_UPLOAD_BYTES` | 6 GiB local / 400 MiB hosted | Combined multipart limit |
| `NOTESBUDDY_MAX_DURATION_MS` | 7200000 | Declared recording-duration limit |
| `NOTESBUDDY_TRANSCRIPTION_ENGINE` | `local` | `empty` allowed only for smoke testing |
| `NOTESBUDDY_ACCESS_MODE` | `local` | `local` pairing or `anonymous` hosted sessions |
| `NOTESBUDDY_ALLOW_BROWSER_PAIRING` | Off for manual CLI; enabled directly by desktop app | Exact-origin automatic pairing |
| `NOTESBUDDY_BROWSER_PAIRING_TTL_SECONDS` | 86400 | Automatic token lifetime, clamped 15 minutes–7 days |
| `NOTESBUDDY_MAX_BROWSER_PAIRINGS` | 32 | Bounded in-memory automatic pairings |
| `NOTESBUDDY_SESSION_TTL_SECONDS` | 86400 | Hosted anonymous-session lifetime |
| `NOTESBUDDY_MAX_SESSIONS` | 2048 | Maximum hosted sessions retained in process memory |
| `NOTESBUDDY_SESSION_ISSUE_WINDOW_SECONDS` | 3600 | Session-issuance quota window |
| `NOTESBUDDY_MAX_SESSIONS_PER_CLIENT` | 10 | Session issuances per hashed network key/window |
| `NOTESBUDDY_JOB_LIMIT_WINDOW_SECONDS` | 3600 | Hosted per-session job quota window |
| `NOTESBUDDY_MAX_JOBS_PER_SESSION` | 3 | Hosted job starts per session/window |
| `NOTESBUDDY_MAX_ACTIVE_JOBS_PER_SESSION` | 1 | Simultaneous jobs per hosted session |

The launcher intentionally binds to `127.0.0.1`; there is no environment
setting to expose a LAN host. `--port` defaults to 8765.

The companion does not automatically read `.env`. `.env.example` documents
values only; use a private process environment or launcher.

## Deployment configuration

The static client can be served from any HTTPS host. For local/hybrid mode on a
new host, ship its exact origin in the desktop companion allowlist. For hosted
mode, add the origin to the hosted API and set its public HTTPS URL in
`src/runtime-config.js`. Never put a pairing token or `HF_TOKEN` in static host
variables or client source.

The existing `.openai/hosting.json` project ID and GitHub Pages workflows are
repository deployment metadata. Hosted model deployment is separate from the
static GitHub Pages workflow.

Anonymous hosted sessions isolate prototype jobs but are not user accounts.
Subscription operation requires authentication, entitlements, durable quotas,
encrypted lifecycle storage, and per-user meeting ownership.
