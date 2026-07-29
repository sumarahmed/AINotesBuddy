# Configuration and fixed-value audit

NotesBuddy no longer ships with a fixed person, fake meeting history, sample
transcript, fixed calendar event, or fixed current date. A first-run local
profile supplies the display name and initials, dates come from the browser,
and runtime records use UUID-based identifiers.

The following fixed values remain intentionally in source:

| Area | Current value | Reason | Change location |
| --- | --- | --- | --- |
| Product name | `NotesBuddy` | Application branding | `index.html`, `src/app.js`, and documentation |
| Browser locale | `en-AU` | Date formatting and speech-recognition language | Date helpers and `startSpeechRecognition()` in `src/app.js` |
| Development address | `127.0.0.1:4173` | Predictable local-only server | `server.mjs` |
| Storage namespace | `notesbuddy-profile`, `notesbuddy-meetings`, `notesbuddy-settings`, and `notesbuddy-audio` | Prevent collisions with unrelated browser data | Persistence helpers in `src/app.js` |
| IndexedDB schema | Version `1`, store `recordings` | Current audio persistence schema | `openAudioDatabase()` in `src/app.js` |
| Recorder preference | Opus WebM, WebM, then MP4 | Choose the first media type supported by the browser | `startCapture()` in `src/app.js` |
| Recorder chunk interval | 500 ms | Balance incremental recording with low overhead | `startCapture()` in `src/app.js` |
| Default title | `Untitled meeting` | Safe placeholder until the user names a capture | `resetCapture()` in `src/app.js` |
| Capture defaults | Browser speech, meeting brief, and audio retention enabled; system audio disabled | Match the capabilities and privacy boundary of the browser prototype | `defaultSettings` in `src/app.js` |
| System audio | Disabled | Browser prototype does not implement desktop/system capture | Capture source UI in `src/app.js` |
| Summary model labels | Browser recognition and extractive brief | These controls describe current local behavior and are not remote model selectors | `settingsPanel()` in `src/app.js` |
| Legacy sample IDs | Four historical IDs | One-time migration removes demo records saved by older builds while preserving user records | `LEGACY_SEED_MEETING_IDS` in `src/app.js` |

## Identity and sessions

The profile ID, meeting IDs, import IDs, and transcript-segment IDs use
`crypto.randomUUID()` when available. The random fallback is used only in older
browsers that do not expose that API.

This profile is not authentication. It identifies one browser storage profile
and personalises greetings, transcript attribution, initials, and follow-up
ownership. Different browsers, browser profiles, devices, or origins have
separate storage. Multiple people sharing the same operating-system and browser
profile will also share this NotesBuddy workspace.

## Deployment values

The Sites project ID in `.openai/hosting.json` identifies the deployment target
and must not be copied to a different site. The production URL and repository
remote are deployment metadata, not user data.

For real multi-user isolation, add authentication and a server-side data model
that scopes every meeting and recording to an authenticated user. The current
static browser app intentionally does not imply that boundary.
