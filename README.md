# NotesBuddy

NotesBuddy is a private, local-first meeting assistant prototype. It records
microphone audio, keeps the recording in the browser, captures live speech text
when the browser supports it, and turns meetings into searchable summaries,
transcripts, notes, and action items.

> **Project status:** Functional prototype. NotesBuddy is an independent project
> inspired by local-first meeting tools such as Meetily; it is not affiliated
> with or endorsed by Meetily.

[Open the public GitHub Pages site](https://sumarahmed.github.io/notesbuddy/)

[Owner-restricted Sites deployment](https://notesbuddy-local.sumarahmed.chatgpt.site)

## Highlights

- Real microphone recording with pause, resume, playback, seeking, and download
- First-run local profile with personalised greetings and transcript attribution
- Audio import with the original file type and filename preserved
- Browser-provided live speech recognition without fabricated sample text
- Searchable meeting library and transcript filtering
- Structured summaries, decisions, highlights, and action items
- Editable titles and private notes with automatic local persistence
- Markdown export and clipboard copy
- Responsive desktop and mobile layouts
- Direct `index.html` launch with no installation or build step
- Dependency-free source and production bundle

## Quick start

### Open directly

Open `index.html` in a current browser. Chrome or Edge is recommended for the
broadest MediaRecorder and speech-recognition support.

### Run the local server

Requirements:

- Node.js 20 or later
- A browser with microphone access

```bash
npm run dev
```

Then visit <http://127.0.0.1:4173>.

No `npm install` step is required because the app has no runtime or development
dependencies.

## Available commands

| Command | Purpose |
| --- | --- |
| `npm run dev` | Serve the source app at `http://127.0.0.1:4173` |
| `npm run build` | Create the deployable bundle in `dist/` |
| `npm run preview` | Serve the generated `dist/` bundle |
| `npm run check` | Syntax-check the source and verify a clean build |
| `npm test` | Run the same repository validation used by CI |

Pushes to `main` also validate and deploy `dist/client` through the
`Deploy GitHub Pages` workflow.

## How recordings and transcripts work

1. `navigator.mediaDevices.getUserMedia()` requests microphone access.
2. `MediaRecorder` captures the real microphone stream.
3. The completed audio Blob is stored in IndexedDB.
4. The local profile, meeting metadata, notes, and settings are stored in
   `localStorage`.
5. If enabled and supported, the browser Speech Recognition API supplies live
   text. NotesBuddy never inserts a sample transcript into a new recording.
6. Playback controls load the exact stored Blob through a temporary object URL.

Browser speech recognition may use a service operated by the browser provider.
The recording and meeting database remain in the local browser profile unless
the user explicitly downloads or exports them.

See [Privacy and data handling](docs/PRIVACY.md) for the complete data boundary.

## Browser behavior

NotesBuddy detects media and speech capabilities at runtime:

- Recording requires `getUserMedia` and `MediaRecorder`.
- Live text requires `SpeechRecognition` or `webkitSpeechRecognition`.
- Audio recording still works when live speech recognition is unavailable.
- System-audio capture is intentionally disabled in this browser prototype.
- Browser storage is origin-specific. Data recorded through `file://` and data
  recorded through `http://127.0.0.1:4173` may appear in separate libraries.

## Repository layout

```text
.
|-- .github/                 GitHub workflow and contribution templates
|-- docs/                    Architecture, privacy, testing, and publishing guides
|-- dist/                    Generated Sites-compatible production bundle
|-- src/
|   |-- app.js               Application state, views, recording, and persistence
|   `-- styles.css           Responsive visual system
|-- build.mjs                Dependency-free production build
|-- index.html               Direct-launch entry point
|-- server.mjs               Local static development server
`-- site-worker.mjs          Production asset worker and SPA fallback
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Configuration and fixed-value audit](docs/CONFIGURATION.md)
- [Privacy and data handling](docs/PRIVACY.md)
- [Testing guide](docs/TESTING.md)
- [GitHub publishing checklist](docs/GITHUB_SETUP.md)
- [Contributing](CONTRIBUTING.md)
- [Code of conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)

## Current limitations

This browser prototype does not yet provide:

- Fully offline speech-to-text such as Whisper or Parakeet
- Speaker diarization
- Local LLM summarization through Ollama
- Browser system-audio capture
- Cloud synchronization, accounts, or multi-device access
- Encrypted browser storage

Those capabilities require a native/desktop backend or a deliberately designed
server component.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Bug
reports should include the browser, operating system, launch method, and exact
recording or playback steps.

## Security

Do not include real meeting audio, transcripts, credentials, or other sensitive
information in a public issue. Follow [SECURITY.md](SECURITY.md) for private
reporting guidance.

## License

No open-source license has been selected yet. Until a license is added, the
default copyright restrictions apply. Choose and add an appropriate license
before making the repository public or accepting external contributions.
