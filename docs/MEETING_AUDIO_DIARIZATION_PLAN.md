# Meeting audio and speaker diarization plan

Status: implemented and verified on `feature/meeting-audio-diarization`

Update for `2026.08.1`: the Windows companion now provides explicit,
user-started WASAPI loopback capture. The browser share path described below is
retained as a fallback for users without the updated companion.

Implementation verification completed 2026-07-30:

- Browser module tests: 8/8 passed.
- Local service unit/API/model-adapter tests: 15/15 passed.
- Synthetic end-to-end browser suite passed in Chrome 150.0.7871.188 and
  Edge 150.0.4078.105 on Windows.
- Verified direct-file load, synchronized and meeting-only capture, stable
  controls, per-source persistence/playback before and after reload, display
  denial fallback, interrupted-share continuity, local API pairing,
  multi-speaker result handling, rename/search/export, cancellation, and
  temporary-file cleanup.
- The production model adapter is implemented. An actual first model download
  and accuracy run still requires the operator's accepted pyannote model access
  and local `HF_TOKEN`; secrets and multi-gigabyte models are intentionally not
  committed or downloaded by repository checks.

The original work was developed on an isolated feature branch. The implemented
capture/diarization foundation is now part of the main application; this file
is retained as its design and verification record.

## Objectives

The feature has four required outcomes:

1. Capture the user's microphone and meeting/system audio as separate,
   synchronized sources.
2. Transcribe the recording with a diarization-capable pipeline.
3. Label the local user separately from detected remote speakers.
4. Let the user rename detected speakers after transcription.

The feature will not claim to recognise a person's real identity from their
voice. Diarization answers "which detected speaker talked when." People begin
as `You`, `Speaker 1`, `Speaker 2`, and so on; the user supplies real names.

## Architecture decision

Use a browser capture client plus a local transcription companion:

```text
Microphone ────────> microphone MediaStream ─> microphone recording ─┐
                                                                    │
Shared tab/system ─> meeting MediaStream ────> meeting recording ───┼─> IndexedDB
                                                                    │
Both sources ──────> Web Audio mixer ─────────> mixed playback ─────┘

microphone + meeting recordings
        │
        v
local transcription companion
  - word-timestamped speech-to-text
  - remote-track speaker diarization
        │
        v
timestamped transcript segments
  - You
  - Speaker 1
  - Speaker 2
        │
        v
speaker rename UI and local persistence
```

The deployed application is a static GitHub Pages site, so it cannot run a
large transcription model itself. It also must not contain a shared cloud API
key. The first implementation will therefore use a local service running on
the same computer. A hosted provider can be added later behind the same
interface, but uploading audio is not part of this branch.

Recommended local pipeline:

- `faster-whisper` for transcription with word timestamps.
- `pyannote.audio` with the `speaker-diarization-community-1` pipeline for
  remote-speaker diarization and exclusive speaker intervals.
- A small localhost API that processes temporary files, returns JSON, and
  removes temporary audio after each job.

The `pyannote.audio` community pipeline can be downloaded and run offline after
its model-access setup. Its exclusive diarization output is designed to make
alignment with transcription timestamps simpler:
<https://github.com/pyannote/pyannote-audio>.

`faster-whisper` exposes word timestamps that can be aligned with those speaker
intervals:
<https://github.com/SYSTRAN/faster-whisper>.

## Milestone 1: synchronized multi-source capture

### Capture flow

1. The user presses **Start capture**.
2. When **Meeting audio** is enabled, NotesBuddy calls `getDisplayMedia()`
   immediately from the start-button gesture so transient activation is not
   lost.
3. NotesBuddy then requests microphone audio with `getUserMedia()`.
4. The user selects a browser tab, window, or screen and explicitly enables
   sharing its audio.
5. NotesBuddy verifies that the returned display stream contains an audio
   track. A selected surface without audio is rejected with a clear recovery
   message.
6. The required display video track remains alive so the browser share stays
   active, but it is never sent to a recorder, rendered, stored, or uploaded.
7. Three recorders start from one monotonic capture clock:
   - microphone source;
   - meeting source;
   - mixed playback source created through `AudioContext` and
     `MediaStreamAudioDestinationNode`.
8. Pause, resume, finish, cancellation, and unexpected stream termination act
   on all recorders as one transaction.

`getDisplayMedia()` requires HTTPS, a user permission prompt, and a video track.
System-audio support varies by browser and selected display surface, so this
feature will be capability-driven rather than silently assumed:
<https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia>.

### Capture states

Replace the single recorder state with:

```text
idle
requesting-microphone
requesting-meeting-audio
ready
recording
paused
processing
failed
```

Track each source independently:

```js
{
  microphone: {
    enabled,
    permission,
    stream,
    recorder,
    chunks,
    mimeType
  },
  meeting: {
    enabled,
    permission,
    stream,
    recorder,
    chunks,
    mimeType,
    displaySurface
  },
  mixed: {
    recorder,
    chunks,
    mimeType
  }
}
```

### Capture UX

- Add separate **My microphone** and **Meeting audio** source controls.
- Explain that meeting audio requires selecting a tab/window/screen and
  checking the browser's **Share audio** option.
- Display an active indicator for each source.
- Display a persistent warning if the user stops sharing meeting audio while
  recording.
- Allow microphone-only recording when meeting-audio capture is unsupported.
- Do not treat sound leaking through laptop speakers as a second source.

## Milestone 2: recording storage and migration

Keep existing recordings playable while introducing multi-source assets.

Meeting records will add:

```js
{
  recordingAssets: {
    microphone: {
      id,
      mimeType,
      durationMs
    },
    meeting: {
      id,
      mimeType,
      durationMs
    },
    mixed: {
      id,
      mimeType,
      durationMs
    }
  },
  captureStartedAt,
  captureClockVersion: 1
}
```

IndexedDB keys will use source-specific IDs such as:

```text
meeting_<uuid>:microphone
meeting_<uuid>:meeting
meeting_<uuid>:mixed
```

Compatibility rules:

- Existing `audioId` recordings remain readable.
- New meetings prefer `recordingAssets.mixed` for normal playback.
- A source selector permits playback or download of microphone and meeting
  tracks separately.
- Deleting a meeting deletes every associated asset.
- A failed write for one source does not incorrectly claim all sources were
  saved.

## Milestone 3: diarization-capable transcription

### Local service contract

The browser will call a user-configured localhost endpoint only after explicit
transcription approval.

```text
GET  /v1/health
POST /v1/transcriptions
GET  /v1/transcriptions/{jobId}
DELETE /v1/transcriptions/{jobId}
```

The transcription request contains the microphone and meeting recordings plus
their shared clock metadata. The response shape is:

```js
{
  jobId: "job_<uuid>",
  status: "completed",
  language: "en",
  segments: [
    {
      id: "segment_<uuid>",
      source: "microphone",
      speakerId: "local-user",
      startMs: 1200,
      endMs: 3580,
      text: "I will send the revised proposal.",
      confidence: 0.94
    },
    {
      id: "segment_<uuid>",
      source: "meeting",
      speakerId: "remote-1",
      startMs: 3710,
      endMs: 6900,
      text: "I will review it tomorrow.",
      confidence: 0.91
    }
  ]
}
```

### Attribution rules

- Speech transcribed from the isolated microphone track is assigned to
  `local-user` and displayed as **You**.
- The meeting track is diarized into stable session-local IDs such as
  `remote-1`, `remote-2`, and `remote-3`.
- Word timestamps are assigned to the diarization interval with the greatest
  overlap.
- Microphone and meeting segments are merged by `startMs`.
- Near-identical, overlapping text caused by acoustic echo is de-duplicated
  before display.
- Uncertain assignments remain `Unknown speaker`; NotesBuddy does not guess a
  person's identity.
- The existing browser live transcript can remain as an explicitly marked
  draft, but the post-meeting diarized transcript becomes authoritative.

### Local-service privacy requirements

- Bind only to `127.0.0.1` by default.
- Allow only the configured NotesBuddy origin through CORS.
- Require a random per-install pairing token.
- Store no meeting audio after a job completes or is cancelled.
- Disable optional model telemetry in the documented private mode.
- Never log transcript text or audio paths at normal log level.
- Keep model downloads separate from meeting data.

## Milestone 4: speaker labels and rename UI

### Speaker roster

Add a **Speakers** panel above the transcript:

```text
[DT] You (Deployment Tester)      Local microphone
[S1] Speaker 1                    Meeting audio    [Rename]
[S2] Speaker 2                    Meeting audio    [Rename]
```

Each speaker record is stored once:

```js
{
  id: "remote-1",
  displayName: "Speaker 1",
  source: "meeting",
  color: "violet",
  isLocalUser: false
}
```

Transcript segments reference `speakerId` rather than duplicating names.

### Rename behavior

- Rename from the speaker roster or any transcript speaker label.
- Validate a non-empty name up to 80 characters.
- Update every matching segment immediately.
- Persist the mapping in the meeting record.
- Use renamed speakers in search, summaries, copy, and Markdown export.
- Preserve the original diarization ID so a rename never changes timestamps or
  model output.
- Keep the local profile synchronized with the special `local-user` label.

## Testing plan

### Automated source and state tests

- Capability detection for microphone, display capture, and system audio.
- Permission denied, no audio track, and user-cancelled share flows.
- Atomic start, pause, resume, finish, and cleanup across three recorders.
- Unexpected meeting-track `ended` event during recording.
- IndexedDB storage, reload, legacy `audioId` compatibility, and deletion.
- Timestamp merge and echo de-duplication.
- Word-to-speaker interval assignment, including overlapping speech.
- Rename persistence and export output.
- No fabricated transcript when either transcription source returns no text.

### Browser integration tests

- Chrome and Edge on Windows with a shared browser tab.
- Chrome and Edge on Windows with supported system-audio sharing.
- Microphone-only fallback when meeting audio is unavailable.
- Headphones test proving remote audio comes from the shared meeting track, not
  acoustic microphone leakage.
- Playback of mixed, microphone, and meeting recordings.
- Reload the page and replay every saved source.
- Recording controls remain stable during live updates.

### Diarization fixtures

Use consented or generated non-personal fixtures:

- one local speaker plus one remote speaker;
- one local speaker plus three remote speakers;
- alternating speakers;
- overlapping remote speakers;
- silence and background noise;
- remote audio echoed faintly into the microphone track.

Expected speaker IDs and approximate time ranges will be checked without
requiring exact wording from every model version.

## Acceptance criteria and result

The implemented branch satisfies these code and synthetic-integration criteria:

- A user can record microphone and supported meeting audio simultaneously.
- The two original sources and a mixed playback recording survive page reload.
- The transcript always labels microphone speech as **You**.
- A two-person remote fixture produces at least two stable remote speaker IDs
  through timestamp alignment and the browser result contract.
- Playback starts from transcript timestamps against the mixed recording.
- Renaming a speaker updates all transcript occurrences and exported Markdown.
- No sample transcript text is generated.
- Unsupported or denied meeting-audio capture falls back without losing the
  microphone recording.
- Automated checks pass and the documented synthetic Windows browser matrix is
  complete.
- No commit has changed `main` or triggered the GitHub Pages deployment.

Before relying on speaker accuracy for real meetings, complete the consented
real-model and meeting-platform regression in `docs/TESTING.md`. Model accuracy
is data/hardware/version dependent and is not represented by mocked text.

## Delivery sequence

1. Capture state machine and dual-source recording.
2. Multi-asset IndexedDB persistence and backward-compatible playback.
3. Local transcription-service skeleton and health/pairing flow.
4. Word-timestamped transcription and remote-speaker diarization.
5. Timestamp merge, **You** attribution, and echo de-duplication.
6. Speaker roster and rename persistence.
7. Automated tests, manual browser matrix, privacy documentation, and migration
   documentation.
8. Draft pull request for review; merge and deployment require a separate,
   explicit decision.

## Explicit non-goals for this branch

- Voice biometric identification or automatic real-name recognition.
- A meeting-platform bot that joins Teams, Zoom, or Google Meet.
- Background system-audio capture without an explicit NotesBuddy start action.
- Uploading meeting recordings to a hosted service.
- Merging to `main` or changing the public deployment.
