# NotesBuddy

NotesBuddy is a high-fidelity, local-first meeting assistant prototype inspired by
Meetily's core workflow: capture a meeting, review a live transcript, generate a
structured summary, and keep searchable meeting memory.

## What works

- Desktop-style meeting library with full-text filtering
- Microphone capture permission and a clearly labelled simulated local transcript
- Recording, pause, resume, finish, and discard flows
- Audio import flow with local-only file metadata handling
- Summary, transcript, and notes workspaces
- Action-item completion, editable titles, notes, and local persistence
- Markdown export and clipboard copy
- Local model/privacy settings
- Responsive layout for desktop and mobile

The browser prototype does not bundle Meetily's native Rust audio engine, Whisper,
Parakeet, diarization, or Ollama. Those require a desktop/native backend. The UI
keeps that boundary explicit while providing a realistic end-to-end product demo.

## Run locally

```bash
npm run dev
```

No package installation is required. Build the dependency-free production bundle
with `npm run build`.
