# Privacy and data handling

NotesBuddy keeps meeting records and original recordings in the browser profile
that created them. Optional speaker transcription runs in a paired service on
the same computer. This document describes the prototype's data paths; browser,
operating-system, and model-provider behavior remains outside the application's
control.

## Data inventory

| Data | Storage or processor | Retention |
| --- | --- | --- |
| Local profile name, initials, ID | Browser `localStorage` | Until site data is cleared |
| Meeting metadata, speakers, rename mappings | Browser `localStorage` | Until meeting/site data is deleted |
| Transcript, extractive brief, actions, notes | Browser `localStorage` | Until meeting/site data is deleted |
| Companion URL and pairing token | Browser `localStorage` | Until settings/site data is cleared |
| Microphone, meeting, mixed audio | Browser IndexedDB | Until meeting/site data is deleted |
| Browser live-speech audio | Browser speech provider when enabled | Provider/browser controlled |
| Companion job audio | Random OS temporary directory | Removed after job success, failure, or cancellation |
| Companion pairing token | Local OS user configuration directory | Until token file is deleted |
| Speech/diarization models | Local model cache | Until user removes the cache |
| Hugging Face model token | Companion process environment | Process/shell controlled |
| Downloaded audio or Markdown | User-selected filesystem location | User/device controlled |

## Browser capture

Microphone capture uses `getUserMedia()`. Meeting audio uses an explicit
`getDisplayMedia()` share prompt. The user chooses a tab, window, or screen and
must enable its **Share audio** option.

Browsers require a video track for display capture. NotesBuddy keeps that track
alive only to maintain the share; it does not pass video to `MediaRecorder`,
render it, persist it, or send it to the companion.

New captures can store:

- isolated microphone audio;
- isolated shared meeting audio;
- a local mixed playback track.

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
marks them as draft, and never inserts sample transcript text.

## Local transcription companion

When the user chooses **Transcribe and identify speakers**, the browser reads
the meeting's stored audio Blobs and posts them to
`http://127.0.0.1:8765`. This leaves the browser origin but stays on the same
computer's loopback interface.

The launcher:

- binds only to `127.0.0.1`;
- checks a configured browser-origin allowlist;
- supports required browser private-network preflights;
- authenticates every endpoint with a random 256-bit pairing token;
- disables Uvicorn access logs;
- does not log transcript text or audio paths at normal level.

Uploads are written to a random OS temporary directory. The worker removes it
in a `finally` block after completed, failed, or cancelled jobs. Cancellation is
cooperative, so a native inference call may return before cleanup executes.

The returned transcript is saved in the browser meeting record. The companion
keeps recent job status/results in process memory for one hour by default (and
evicts older completed entries when its bounded job table fills). It has no
job database or cloud synchronization.

## Model access and caches

The pyannote community model requires a Hugging Face token for initial access.
That token belongs only in the companion process environment and is not the
same as the NotesBuddy pairing token.

Speech/diarization models are cached locally by their libraries. Model cache
files contain model weights, not meeting audio. Their size and deletion method
are controlled by the model libraries/provider.

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

1. Delete its pairing token file.
2. Restart the companion to create a new token.
3. Clear the old browser pairing token from Settings.

Stopping the companion prevents further local transcription. Model caches and
the Hugging Face token environment are managed separately.

## Security considerations

- Browser storage is not encrypted by NotesBuddy.
- Users of the same unlocked device/browser profile may access data.
- Browser extensions or compromised scripts may inspect page data.
- A pairing token stored in browser storage can be read by scripts executing in
  that same origin; use only trusted static hosting.
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
