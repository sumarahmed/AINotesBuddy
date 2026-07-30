// Public, non-secret deployment configuration. Never put service credentials here.
globalThis.NotesBuddyRuntime = Object.freeze({
  transcriptionMode: "local",
  transcriptionEndpoint: "http://127.0.0.1:8765",
});
