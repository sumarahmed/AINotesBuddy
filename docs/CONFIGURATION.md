# Configuration and fixed-value audit

NotesBuddy does not ship a fixed person, fake meeting history, sample
transcript, fixed calendar event, or fixed date. The first-run profile supplies
the user's name and initials, dates come from the browser, and runtime records
use UUID identifiers.

## Browser settings

Settings are stored under `notesbuddy-settings` for the current browser origin.

| Setting | Default | Behavior |
| --- | --- | --- |
| Meeting audio | On | Ask for a tab/window/screen audio source at capture start |
| Browser live transcript draft | On | Use browser speech recognition for microphone draft text when supported |
| Automatically identify speakers | Off | Start the paired local job after saving a recording |
| Create meeting brief | On | Build an extractive brief only from returned transcript segments |
| Keep source recordings | On | Save mic, meeting, and mixed Blobs in IndexedDB |
| Companion URL | `http://127.0.0.1:8765` | Loopback-only local API |
| Pairing token | Empty | Must be copied from the local companion |

Changing a source toggle while capture is already running does not mutate live
streams. It applies to the next capture.

## Intentional browser constants

| Area | Value | Reason / change location |
| --- | --- | --- |
| Product name | `NotesBuddy` | Branding in `index.html`, app templates, docs |
| Locale/language | `en-AU` | Date formatting and browser live speech in `src/app.js` |
| Development address | `127.0.0.1:4173` | Predictable loopback server in `server.mjs` |
| Storage keys | `notesbuddy-profile`, `notesbuddy-meetings`, `notesbuddy-settings`, `notesbuddy-audio` | Namespace isolation in `src/app.js` |
| IndexedDB schema | Version 1, `recordings` store | Blob persistence in `openAudioDatabase()` |
| Recorder preference | Opus WebM, WebM, then MP4 | First browser-supported type in `preferredRecordingType()` |
| Recorder chunk interval | 500 ms | Incremental data without excessive events |
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
| `NOTESBUDDY_MAX_SOURCE_BYTES` | 2 GiB per source | Multipart source limit |
| `NOTESBUDDY_TRANSCRIPTION_ENGINE` | `local` | `empty` allowed only for smoke testing |

The launcher intentionally binds to `127.0.0.1`; there is no environment
setting to expose a LAN host. `--port` defaults to 8765.

The companion does not automatically read `.env`. `.env.example` documents
values only; use a private process environment or launcher.

## Deployment configuration

The static client can be served from any HTTPS host. For a new host, add its
exact origin to `NOTESBUDDY_ALLOWED_ORIGINS` on each user's local companion.
Never put the pairing token or `HF_TOKEN` in static host variables or client
source.

The existing `.openai/hosting.json` project ID and GitHub Pages workflows are
repository deployment metadata. This feature branch does not invoke them. A
future deployment destination is a separate decision.

True server-backed multi-user sharing would require authentication,
authorization, encrypted transport/storage, and per-user meeting ownership.
Those are intentionally outside this local browser profile model.
