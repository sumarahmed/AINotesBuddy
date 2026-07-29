# NotesBuddy

NotesBuddy is a high-fidelity, local-first meeting assistant prototype inspired by
Meetily's core workflow: capture a meeting, review a live transcript, generate a
structured summary, and keep searchable meeting memory.

## What works

- Desktop-style meeting library with full-text filtering
- Real microphone recording with persistent local playback and download
- Live text from browser speech recognition when the browser supports it
- Recording, pause, resume, finish, and discard flows
- Audio import with locally persisted playback
- Summary, transcript, and notes workspaces
- Action-item completion, editable titles, notes, and local persistence
- Markdown export and clipboard copy
- Local model/privacy settings
- Responsive layout for desktop and mobile

The app never injects a sample transcript into a new recording. Browser speech
recognition can depend on the browser provider's speech service, while the
original recording and meeting data remain stored locally. Meetily's fully local
Whisper/Parakeet transcription, diarization, and Ollama summarization still
require a desktop/native backend.

## Run locally

You can double-click `index.html` to run the app directly from disk, or use the
local server:

```bash
npm run dev
```

No package installation is required. Build the dependency-free production bundle
with `npm run build`. The bundle includes a lightweight Sites worker entrypoint
and the static client under `dist/client`.
