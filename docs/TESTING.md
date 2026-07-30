# Testing guide

NotesBuddy combines browser permissions, several live audio tracks, IndexedDB,
playback, and local/hosted model-service modes. Unit, API, browser, and
real-device checks cover different parts of that boundary.

Use only generated or consented non-confidential audio.

## Repository validation

```bash
npm test
```

This command:

1. syntax-checks source/build scripts;
2. runs `tests/meeting-audio.test.mjs` in-process;
3. rebuilds `dist/`;
4. syntax-checks generated client JavaScript;
5. confirms generated files match tracked `dist/`.

The JavaScript tests cover:

- legacy `audioId` migration;
- source preference and asset selection;
- complete transcript text beyond 80 characters;
- cross-source echo de-duplication;
- **You**, detected, renamed, and unknown speaker labels;
- rename propagation to participants;
- extractive briefs with no invented text;
- authenticated local multipart client construction;
- automatic desktop discovery, pairing, token validation, and incompatibility
  rejection;
- hosted anonymous-session creation and session-token multipart requests.
- automatic replacement of hosted sessions lost during scale-to-zero.

The test file runs directly rather than with Node's process-isolated test mode,
which also works in restricted Windows environments that deny child-process
creation.

## Transcription service tests

Install only the lightweight API/test dependencies; model downloads are not
needed:

```powershell
cd services\transcription
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```

The Python suite covers:

- greatest-overlap word/speaker assignment;
- stable first-appearance remote IDs;
- unknown-speaker tolerance;
- speaker-boundary segment collapse;
- microphone **You** attribution;
- cross-source clock merge and echo removal;
- silence returning no fabricated segments;
- pairing-token rejection;
- bounded/expiring browser pairings and exact-origin issuance;
- safe discovery and hosted/manual-CLI route separation;
- desktop CLI, loopback, and Windows autostart command construction;
- bundled offline-model path selection without a per-user model token;
- allowed/denied CORS origins and private-network preflight;
- multipart source upload and asynchronous job polling;
- invalid metadata rejection;
- cancellation signaling and temporary-audio deletion.
- production adapter parsing of fake faster-whisper/pyannote outputs;
- mixed-only diarization and mic-only duplicate-mixed suppression.
- anonymous session opacity, expiry/error handling, issuance limits, active-job
  limits, and compute quotas;
- hosted job ownership isolation and hosted CORS/session headers.

The API tests use `EmptyEngine`, which deliberately returns no transcript text.
They do not prove model accuracy.

## Synthetic browser integration

`tests/browser-smoke.cjs` uses Playwright and an installed Chromium-family
browser. It replaces permission APIs with Web Audio oscillators and a generated
canvas display stream. It never opens a physical microphone.

If Playwright is installed in the project:

```bash
npm run test:browser
```

In the Codex bundled runtime on Windows, the equivalent is:

```powershell
$env:NODE_PATH = "C:\Users\<you>\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"
$env:NOTESBUDDY_CHROME_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
node tests\browser-smoke.cjs
```

Set `NOTESBUDDY_CHROME_PATH` to Edge to repeat the matrix.

The workflow verifies:

- direct `file://.../index.html` loading;
- simultaneous mic/meeting/mixed capture;
- meeting-only capture with the microphone disabled;
- microphone fallback when display sharing is denied;
- persistent warning and microphone continuity when display sharing ends;
- recording-dock position stability while the timer updates;
- opening/testing/closing Settings during recording;
- pause/resume/finish;
- three non-empty source Blobs in IndexedDB;
- playback time advancing for every source;
- reload and replay of every source;
- all three assets included in the transcription request;
- hosted settings without per-user URL/token fields;
- hosted health checks without consuming a session;
- automatic anonymous-session creation and session-token job submission;
- hybrid automatic companion discovery/pairing/health verification;
- first-entry installer prompt, stable Releases link, successful local
  API/pairing/model confirmation, persisted completion, and session-only online
  deferral;
- hybrid settings without URL/token fields and a Windows download action;
- visible online fallback when companion discovery fails;
- **You** plus two remote speakers in a completed result;
- untruncated transcript text;
- speaker rename, name search, and Markdown export;
- transcript/speaker layout without horizontal overflow at 390 px and 320 px;
- no uncaught page or console errors.

## Verified Windows browser matrix

Synthetic end-to-end suite run on 2026-07-30:

| Browser | Version | Result |
| --- | --- | --- |
| Google Chrome | 150.0.7871.188 | Passed |
| Microsoft Edge | 150.0.4078.105 | Passed |

Update this matrix when a release candidate is verified; test counts are
reported by the commands and intentionally not hard-coded here.

These runs validate NotesBuddy logic and browser media plumbing with generated
tracks. They do not replace a real Teams/Zoom/Meet share test because platforms,
surface types, audio drivers, and enterprise policies vary.

## Real meeting-audio regression

Use headphones to prevent acoustic feedback and a non-confidential source tab.

### Capture

- Start microphone + meeting capture.
- Choose the meeting tab and enable **Share audio**.
- Confirm all three status chips show `recording`.
- Speak locally and play a remote voice in the shared tab.
- Open Settings while recording; confirm controls do not flash or move.
- Pause at least five seconds, resume, and finish.
- Repeat with the microphone disabled.
- Repeat after cancelling the share dialog; confirm microphone-only fallback.
- Repeat after sharing a surface that has no audio; confirm the recovery message.
- Stop sharing from the browser toolbar mid-recording; confirm the persistent
  warning and microphone continuation.

### Playback and persistence

- Play mixed, microphone, and meeting assets with the native player.
- Open Transcript and use its play/seek controls.
- Click a transcript timestamp and confirm mixed playback seeks.
- Reload, reopen the meeting, and replay/download every source.
- Confirm the mic track does not contain a fabricated remote channel. Some
  acoustic leakage is possible without headphones.
- Delete the meeting and confirm every source asset disappears.

### Speaker transcription

- Install a model-inclusive Windows release and confirm automatic local
  connection without entering a model or pairing token.
- Quit/restart the companion and confirm the page re-pairs.
- Deny then allow the browser local-network prompt and confirm the online
  fallback remains clear.
- Transcribe one local plus one remote speaker.
- Transcribe one local plus two or three alternating remote speakers.
- Test silence/background noise and confirm no placeholder text.
- Test a remote voice faintly echoed into the microphone.
- Check approximate timestamp ranges and stable IDs within that job.
- Rename each remote speaker and verify search, copy, and exported Markdown.
- Confirm microphone speech is **You**.
- Confirm uncertain unassigned words are **Unknown speaker**, not a guessed name.
- Cancel a long job and confirm no `notesbuddy-job-*` temporary directory
  remains after the worker reaches terminal state.

Model output varies by language, overlap, noise, model version, and hardware.
Set timing/speaker-count tolerances rather than asserting exact wording.

## Profile and integrity

- First launch asks for a name and rejects an empty submission.
- Greeting, initials, **You** details, and new follow-up owner use that profile.
- Rename the profile and verify existing local participants/follow-ups update.
- Confirm separate site origins have separate data.
- Import WAV/MP3 and transcribe it as a mixed-only remote recording.
- Refresh a brief with no transcript; confirm no brief is fabricated.
- Confirm browser live text is explicitly marked as a draft.

## Responsive and accessibility checks

At 390 x 844 and 320 px wide:

- no horizontal overflow;
- capture source controls remain reachable;
- recording dock remains visible;
- transcription and speaker panels stack correctly;
- source switcher is usable;
- Settings remains scrollable during recording;
- focus outlines, labels, and keyboard actions remain functional;
- reduced-motion mode disables nonessential animation.

## Pull request evidence

Include:

- operating system and exact browser versions;
- launch path (`file://`, development server, or static host);
- JavaScript, Python API, and browser-suite results;
- real meeting platform/surface tested, if any;
- screenshots for visual changes;
- model/device configuration without tokens;
- confirmation that no confidential audio or credentials were used;
- confirmation that the feature branch did not deploy `main`.

## Packaged Windows verification

The trusted release workflow must:

1. run all Python service tests;
2. prepare both offline model directories and a revision manifest;
3. build the PyInstaller one-directory application;
4. run `NotesBuddyCompanion.exe --self-test`;
5. compile the Inno Setup installer;
6. install it as a non-administrator test user;
7. start from the Start menu and Windows sign-in entry;
8. pair from the deployed HTTPS site and complete a real two-speaker
   transcription;
9. uninstall and confirm the program/autostart entry is removed.

Do not publish a model-free packaging smoke artifact as a working product.
