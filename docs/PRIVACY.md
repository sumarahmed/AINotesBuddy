# Privacy and data handling

NotesBuddy keeps meeting records and original recordings in the browser profile
that created them. Optional speaker transcription runs either in a paired
service on the same computer or in a centrally hosted service selected by the
deployment owner. This document describes the prototype's data paths; browser,
operating-system, hosting, and model-provider behavior remains outside the
application's control.

## Data inventory

| Data | Storage or processor | Retention |
| --- | --- | --- |
| Local profile name, initials, ID | Browser `localStorage` | Until site data is cleared |
| Meeting metadata, speakers, rename mappings | Browser `localStorage` | Until meeting/site data is deleted |
| Transcript, professional analysis, actions, notes | Browser `localStorage` | Until meeting/site data is deleted |
| Hybrid companion endpoint | Static runtime configuration | Deployment controlled |
| Automatic companion pairing token | Browser page memory | Expiry, reload, or companion restart |
| Companion setup confirmation | Browser `localStorage` | Until site settings are cleared |
| Online-for-now setup deferral | Browser `sessionStorage` | Current browser session |
| Manual CLI URL and recovery token | Browser `localStorage` in explicit local mode | Until settings/site data is cleared |
| Hosted anonymous session token | Browser `sessionStorage` | Session expiry or tab/session storage deletion |
| Microphone, meeting, mixed audio | Browser IndexedDB | Until meeting/site data is deleted |
| Active Windows-output capture | Companion random temporary WAV | Deleted after local transfer, cancellation, or shutdown |
| Browser live-speech audio | Browser speech provider when enabled | Provider/browser controlled |
| Local companion job audio | Random OS temporary directory | Removed after job success, failure, or cancellation |
| Hosted job audio | Host container temporary directory | Removed after job success, failure, or cancellation |
| Hosted job status/result | Host process memory | One hour by default or until process eviction |
| Professional-analysis request/result | Host process memory during the HTTPS request; returned to the originating browser | Request completion or process eviction |
| Hashed hosted client network key | Host process memory | Rate-limit window/session cleanup |
| Companion pairing token | Local OS user configuration directory | Until token file is deleted |
| Companion update response | Companion process memory | Until the next check or application exit |
| Teams audio/microphone activity flags | Companion process memory | Current detection poll only; no audio content is read or stored |
| Speech, diarization, and smart-summary models | Local or hosted model cache | Until the owner removes the cache |
| Hugging Face model token | Source-development environment, host secret manager, or trusted release job | Owner controlled; never included in installer |
| Downloaded audio or Markdown | User-selected filesystem location | User/device controlled |

## Browser capture

Microphone capture uses `getUserMedia()`. With compatible companion `2026.08.1`
or later, meeting audio uses a pairing-protected request to capture the default
Windows output through WASAPI loopback. Capture starts only after the user
presses **Start capture**, stops when the user finishes/cancels, and includes
all sounds played through that output device during the interval.

Without a compatible companion, meeting audio uses an explicit
`getDisplayMedia()` share prompt. The user chooses a tab, window, or screen and
must enable its **Share audio** option.

Browsers require a video track for display capture. NotesBuddy keeps that track
alive only to maintain the share; it does not pass video to `MediaRecorder`,
render it, persist it, or send it to the companion.

New captures can store:

- isolated microphone audio;
- isolated Windows-output or shared meeting audio;
- a local mixed playback track for browser capture. Companion capture keeps
  microphone and Windows output separate and defaults playback to the latter.

The optional Teams meeting notification watches only Windows audio-session
activity and Teams' local microphone-use flag. It does not access Teams chat,
participants, calendars, captions, or audio samples. A detected meeting opens a
ready screen; capture still requires the user's explicit **Start capture**
selection.

The exact set depends on source selection and browser permission. Each Blob is
stored under a source-specific IndexedDB key.

## Local browser workspace

Meeting metadata and settings are stored in `localStorage`; audio Blobs are
stored in IndexedDB. NotesBuddy creates temporary `blob:` URLs for playback and
download. Those URLs exist only in the running browser origin.

The first-run profile personalizes greetings, **You** attribution, initials, and
local follow-up ownership. It does not authenticate a person, create an account,
or establish multi-user isolation. People sharing one unlocked browser profile
share the workspace.

Different origins have separate browser storage, including:

- `file://.../index.html`;
- `http://127.0.0.1:4173`;
- each deployed HTTPS domain.

Data does not automatically migrate between them.

## Browser speech recognition

The browser Speech Recognition API is optional and separate from stored
recordings. Depending on browser/configuration, recognition audio may be sent to
the browser provider.

Users can disable **Browser live transcript draft** in Settings. MediaRecorder
continues independently. NotesBuddy stores only results returned by the API,
marks them as draft, and never inserts sample transcript text. While capture is
active, NotesBuddy also keeps in-memory timestamp spans for detected
Windows/shared-output activity. A returned phrase overlapping those spans is
shown as provisional **Guest**; other returned phrases remain **You**. The
spans contain timing only, not voiceprints or names. Final local/hosted
transcription replaces these provisional rows with synchronized source and
pyannote speaker results.

Browser Speech Recognition accepts the microphone chosen by the browser; it
does not consume the isolated Windows-output track. Consequently the UI may
detect **Guest speaking** from system output without receiving live Guest
words, especially when headphones prevent acoustic leakage. The stored meeting
track remains available for the authoritative post-recording transcription.

## Local transcription companion

The installed companion makes a non-authenticated request to GitHub's public
latest-release API shortly after startup and every 24 hours. The request sends
the companion version in its `User-Agent`; it does not contain profile names,
meeting metadata, recordings, transcripts, pairing tokens, or model tokens.
GitHub may process network and request metadata under its own policies. An
update must be downloaded and installed by the user.

When the user chooses **Transcribe and identify speakers**, the browser reads
the meeting's stored audio Blobs and posts them to
`http://127.0.0.1:8765`. This leaves the browser origin but stays on the same
computer's loopback interface.

The packaged launcher:

- binds only to `127.0.0.1`;
- checks a configured browser-origin allowlist;
- supports required browser private-network preflights;
- exposes only non-secret discovery metadata without authentication;
- issues expiring memory-only browser tokens only to exact trusted origins;
- rejects automatic pairing from missing, `null`, and unknown origins;
- authenticates protected endpoints with an automatic or manual random token;
- disables Uvicorn access logs;
- does not log transcript text or audio paths at normal level.

Uploads are written to a random OS temporary directory. The worker removes it
in a `finally` block after completed, failed, or cancelled jobs. Cancellation is
cooperative, so a native inference call may return before cleanup executes.

Active WASAPI capture uses a separate random temporary WAV. The protected stop
route transfers it over loopback and deletes it after the response. Cancellation
or companion shutdown also deletes it. The companion permits only one active
Windows-output capture.

The returned transcript is saved in the browser meeting record. The companion
keeps recent job status/results in process memory for one hour by default (and
evicts older completed entries when its bounded job table fills). It has no
job database or cloud synchronization.

The website's default `hybrid` mode uses this local path for recordings of
every length while a compatible companion is connected. It automatically uses
a supported local NVIDIA GPU and falls back to the local CPU when required. If
the companion is absent, incompatible, blocked by
browser local-network permission, or cannot pair, the UI also shows **online
fallback** and uses the hosted service. Both cases cross the device boundary
described below.

First-entry setup is marked complete only after a successful companion health
check and explicit user confirmation. Choosing the online fallback stores a
session-only deferral so the installation prompt returns in a future session.

## Hosted anonymous transcription

When `src/runtime-config.js` selects `hosted` mode, the user does not configure
a companion URL or token. The deployment contains one public HTTPS endpoint.

The browser first requests a random short-lived anonymous session token and
stores it in `sessionStorage`. It sends that token with transcription job
requests. The service associates each job with a one-way token digest and
returns `404` rather than disclosing another session's job.

Hosted processing changes the privacy boundary: selecting **Transcribe and
identify speakers** uploads the saved source audio from IndexedDB to the
deployment owner's compute provider. Audio is encrypted in transit by HTTPS but
is available in plaintext to the model process while being decoded. Job files
are placed in a random temporary directory and removed in `finally` after
success, failure, or cancellation.

The prototype keeps job status and transcript results in process memory for up
to one hour by default. It does not intentionally write meeting audio,
transcripts, profile names, or job results to the persistent model-cache
volume. The browser receives the transcript and stores it in its local meeting
record.

Anonymous safeguards include bounded upload size, queue size, worker count,
sessions, per-session job starts, active jobs, and CORS origins. A hash of the
requesting network address is retained temporarily for session-issuance rate
limits; the raw address is not stored by NotesBuddy application code. Hosting
providers may independently retain network and request metadata under their
own policies.

Anonymous mode does not provide verified identity, subscription entitlement,
durable account deletion, or strong protection against distributed abuse. It
is a public prototype boundary only.

## Professional meeting analysis

Professional analysis is a separate request from audio transcription. It runs
only after the browser has a completed, non-draft speaker transcript. The
browser sends the meeting title plus timestamped speaker text and stable segment
IDs to `POST /v1/analyses`; it does not include microphone, meeting, or mixed
recording Blobs in this request.

**The browser prefers the paired local companion for this request whenever it
reports a smart-summary component installed**, regardless of whether that same
companion performed audio transcription. In that case the transcript never
leaves the computer: it is sent only to `127.0.0.1`, processed by a local
`llama.cpp` model, and the result returned over the same loopback connection.
The hosted analyzer is used only when no companion is connected, or a
connected companion has no smart-summary component installed yet. The Summary
view and Settings disclose which path served the most recent result.

When the hosted path is used, the hosted analyzer processes the transcript in
memory and returns a structured result with supporting segment IDs. NotesBuddy
does not intentionally write the analysis request or result to the persistent
model-cache volume. Normal application logs do not include transcript request
bodies. The compute and hosting providers can still process network/request
metadata under their own policies.

The browser validates all returned evidence IDs before saving the result. The
server additionally removes unsupported items and normalizes unsupported
owners, dates, priorities, context, and notes. These safeguards reduce model
fabrication but do not make automated analysis infallible; users should verify
high-impact conclusions against the transcript.

## Model access and caches

The pyannote community model requires gated initial access. For public Windows
releases, the publisher supplies a read-only token to the trusted release job,
which downloads immutable model revisions and packages the weights offline.
Customers do not provide a token. The build token is never written to the
executable or installer. Source developers and hosted operators may instead
provide their own process/secret-manager token.

Speech, diarization, smart-summary, and hosted analysis models are cached
locally or in a host-mounted model-cache volume. The smart-summary model is
one of three independently downloadable quality tiers a user selects in the
companion setup screen; installing a different tier replaces the previous one
rather than keeping multiple installed at once. Model cache files contain
model weights, not meeting audio. Their size and deletion method are
controlled by the model libraries/provider.

## Speaker labels

Diarization assigns session-local IDs based on timing, not biometric identity:

- `local-user` is shown as **You** because it comes from the isolated microphone;
- `remote-1`, `remote-2`, and so on are detected meeting voices;
- `remote-unknown` is shown as **Unknown speaker**.

NotesBuddy does not infer real names. User-supplied rename mappings stay with the
local meeting record.

## Deleting data

Deleting a meeting removes:

- its `localStorage` meeting record;
- all unique microphone/meeting/mixed IndexedDB assets.

To remove the entire workspace, clear site data for that exact origin. Delete
downloaded exports separately.

To revoke local-companion access:

1. Quit or restart the companion to revoke all automatic page-memory tokens.
2. For manual CLI/recovery access, delete its persistent token file.
3. Restart it to create a new manual recovery token.

Stopping the companion prevents further local transcription. Model caches and
the Hugging Face token environment are managed separately.

To stop hosted processing, stop or delete the hosted API deployment. Deleting a
browser meeting removes the browser copy but cannot cancel a job that already
reached a terminal state; terminal hosted job files have already been removed.
The deployment owner manages host logs, model caches, secrets, and billing.

## Security considerations

- Browser storage is not encrypted by NotesBuddy.
- Users of the same unlocked device/browser profile may access data.
- Browser extensions or compromised scripts may inspect page data.
- An automatic pairing token is readable by scripts executing in the trusted
  origin while the page is open; keep the static host dependency-free and
  protect its supply chain.
- A hosted anonymous session token can be read by scripts executing in the same
  origin/tab; Content Security Policy and dependency review remain important.
- Hosted transcription sends meeting audio outside the user's device. The UI
  must accurately disclose that behavior before commercial use.
- CORS is a browser control, not authentication for non-browser clients.
- Anonymous IP/session limits reduce but cannot eliminate automated abuse.
- Private/incognito storage may disappear when the session ends.
- Browser quotas/cleanup can remove recordings.
- Imported or captured media may exercise browser/model decoders and should be
  treated as untrusted input.
- Do not bind the companion to a LAN/public interface or forward port 8765.
- Do not put real model tokens, pairing tokens, meeting audio, or transcripts in
  a repository, public issue, or screenshot.

## Responsible testing

Use generated tones and synthetic/non-confidential speech fixtures. The checked
browser test creates oscillator tracks and never opens a real microphone.
