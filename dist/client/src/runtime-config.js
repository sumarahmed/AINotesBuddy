// Public, non-secret deployment configuration. Never put service credentials here.
globalThis.NotesBuddyRuntime = Object.freeze({
  appVersion: "2026.09.02",
  latestCompanionVersion: "2026.09.08",
  transcriptionMode: "hybrid",
  localCompanionEndpoint: "http://127.0.0.1:8765",
  // Intentionally empty while no verified public service is available. This
  // prevents the UI from advertising a cloud fallback that cannot complete.
  transcriptionEndpoint: "",
  companionDownloadUrl:
    "https://github.com/sumarahmed/AINotesBuddy/releases/download/companion-v2026.09.08/NotesBuddyCompanion-Setup-2026.09.08.exe",
});
