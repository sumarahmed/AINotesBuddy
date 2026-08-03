import assert from "node:assert/strict";
import test from "node:test";

await import("../src/meeting-audio.js");

const MeetingAudio = globalThis.NotesBuddyMeetingAudio;
const profile = { name: "Alex Morgan", initials: "AM" };

test("migrates a legacy single recording without losing its audio id", () => {
  const meeting = {
    audioId: "legacy-audio",
    audioType: "audio/webm",
    durationSeconds: 12,
    transcript: [
      {
        speaker: "Alex Morgan",
        timestamp: "00:03",
        text: "A real legacy transcript segment.",
      },
    ],
  };

  MeetingAudio.ensureMeetingSpeakers(meeting, profile);

  assert.deepEqual(MeetingAudio.recordingAssetIds(meeting), ["legacy-audio"]);
  assert.equal(meeting.recordingAssets.mixed.id, "legacy-audio");
  assert.equal(meeting.transcript[0].speakerId, "local-user");
  assert.equal(meeting.transcript[0].speaker, "You");
});

test("chooses mixed playback first and honours a valid source preference", () => {
  const meeting = {
    recordingAssets: {
      microphone: { id: "mic" },
      meeting: { id: "remote" },
      mixed: { id: "mix" },
    },
  };

  assert.equal(MeetingAudio.primaryRecordingSource(meeting), "mixed");
  assert.equal(
    MeetingAudio.recordingAsset(meeting, "meeting").id,
    "remote",
  );
  assert.equal(
    MeetingAudio.recordingAsset(meeting, "missing").source,
    "mixed",
  );
});

test("prefers companion Windows output when microphone and meeting tracks are separate", () => {
  const meeting = {
    meetingCaptureMode: "companion",
    recordingAssets: {
      microphone: { id: "mic" },
      meeting: { id: "windows-output" },
    },
  };

  assert.equal(MeetingAudio.primaryRecordingSource(meeting), "meeting");
  assert.equal(
    MeetingAudio.primaryRecordingSource(meeting, "microphone"),
    "microphone",
  );
});

test("keeps complete transcript text instead of applying name length limits", () => {
  const longText =
    "This sentence deliberately exceeds eighty characters so a complete spoken thought remains intact in the saved transcript.";
  const meeting = {
    recordingAssets: { microphone: { id: "mic" } },
    speakers: [],
    transcript: [],
  };

  MeetingAudio.applyTranscriptionResult(
    meeting,
    {
      segments: [
        {
          id: "one",
          source: "microphone",
          startMs: 0,
          endMs: 4000,
          text: longText,
        },
      ],
    },
    profile,
  );

  assert.equal(meeting.transcript[0].text, longText);
  assert.ok(meeting.transcript[0].text.length > 80);
});

test("deduplicates microphone echo from the remote meeting track", () => {
  const deduplicated = MeetingAudio.deduplicateEchoSegments([
    {
      id: "mic",
      source: "microphone",
      speakerId: "local-user",
      startMs: 1000,
      endMs: 3500,
      text: "We should ship the updated proposal tomorrow.",
      confidence: 0.88,
    },
    {
      id: "echo",
      source: "meeting",
      speakerId: "remote-1",
      startMs: 1100,
      endMs: 3400,
      text: "We should ship the updated proposal tomorrow",
      confidence: 0.94,
    },
    {
      id: "remote",
      source: "meeting",
      speakerId: "remote-2",
      startMs: 5000,
      endMs: 6500,
      text: "I agree with that deadline.",
      confidence: 0.91,
    },
  ]);

  assert.deepEqual(
    deduplicated.map((segment) => segment.id),
    ["mic", "remote"],
  );
});

test("applies local and remote speaker labels and persists a rename", () => {
  const meeting = {
    recordingAssets: {
      microphone: { id: "mic" },
      meeting: { id: "remote" },
    },
    speakers: [],
    transcript: [],
  };

  MeetingAudio.applyTranscriptionResult(
    meeting,
    {
      jobId: "job-1",
      language: "en",
      segments: [
        {
          id: "local",
          source: "microphone",
          startMs: 0,
          endMs: 1000,
          text: "Good morning.",
        },
        {
          id: "guest",
          source: "meeting",
          speakerId: "remote-1",
          startMs: 1200,
          endMs: 2400,
          text: "Good morning, Alex.",
        },
      ],
    },
    profile,
  );

  assert.equal(MeetingAudio.speakerLabel(meeting, "local-user"), "You");
  assert.equal(MeetingAudio.speakerLabel(meeting, "remote-1"), "Speaker 1");
  assert.equal(
    MeetingAudio.renameSpeaker(meeting, "remote-1", "Jamie Lee", profile),
    true,
  );
  assert.equal(MeetingAudio.speakerLabel(meeting, "remote-1"), "Jamie Lee");
  assert.equal(meeting.transcript[1].speaker, "Jamie Lee");
  assert.equal(meeting.participants[1].name, "Jamie Lee");
});

test("preserves an explicitly unknown diarization assignment", () => {
  const meeting = {
    recordingAssets: { meeting: { id: "meeting" } },
    speakers: [],
    transcript: [],
  };

  MeetingAudio.applyTranscriptionResult(
    meeting,
    {
      segments: [
        {
          source: "meeting",
          speakerId: "remote-unknown",
          speakerLabel: "Unknown speaker",
          startMs: 500,
          endMs: 1200,
          text: "The model could not assign this voice confidently.",
        },
      ],
    },
    profile,
  );

  assert.equal(
    MeetingAudio.speakerLabel(meeting, "remote-unknown"),
    "Unknown speaker",
  );
});

test("builds an extractive brief only from real transcript text", () => {
  assert.equal(MeetingAudio.buildExtractiveBrief([]), null);

  const brief = MeetingAudio.buildExtractiveBrief([
    { text: "The customer approved the revised scope." },
    { text: "Jordan will send the final schedule tomorrow." },
    { text: "The customer approved the revised scope." },
  ]);

  assert.deepEqual(brief.highlights, [
    "The customer approved the revised scope.",
    "Jordan will send the final schedule tomorrow.",
  ]);
  assert.equal(
    brief.overview,
    "The customer approved the revised scope. Jordan will send the final schedule tomorrow.",
  );
});

test("desktop connector discovers, pairs, and verifies the local service", async () => {
  const calls = [];
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url, options });
    if (url.endsWith("/v1/companion")) {
      return {
        ok: true,
        status: 200,
        async json() {
          return {
            product: "NotesBuddy Desktop Companion",
            apiVersion: 1,
            status: "available",
            browserPairing: true,
            modelsReady: true,
          };
        },
      };
    }
    if (url.endsWith("/v1/pairings")) {
      return {
        ok: true,
        status: 200,
        async json() {
          return {
            pairingToken: "short-lived-browser-token-that-is-valid",
            expiresAt: "2099-01-01T00:00:00Z",
          };
        },
      };
    }
    return {
      ok:
        options.headers["X-NotesBuddy-Pairing-Token"] ===
        "short-lived-browser-token-that-is-valid",
      status: 200,
      async json() {
        return { status: "ok", engine: "local-test-engine" };
      },
    };
  };
  const connector = new MeetingAudio.CompanionConnector({
    endpoint: "http://127.0.0.1:8765/",
    fetchImpl,
  });

  const connection = await connector.connect();

  assert.equal(connection.endpoint, "http://127.0.0.1:8765");
  assert.equal(
    connection.token,
    "short-lived-browser-token-that-is-valid",
  );
  assert.deepEqual(
    calls.map(({ url }) => new URL(url).pathname),
    ["/v1/companion", "/v1/pairings", "/v1/health"],
  );
  assert.equal(calls[1].options.method, "POST");
  assert.equal(calls[2].options.cache, "no-store");
  assert.ok(
    calls.every(
      ({ options }) => options.targetAddressSpace === "loopback",
    ),
  );
});

test("desktop connector rejects incompatible or manually paired services", async () => {
  const connector = new MeetingAudio.CompanionConnector({
    fetchImpl: async () => ({
      ok: true,
      status: 200,
      async json() {
        return {
          product: "NotesBuddy Desktop Companion",
          apiVersion: 1,
          status: "available",
          browserPairing: false,
          modelsReady: true,
        };
      },
    }),
  });

  await assert.rejects(
    connector.connect(),
    /does not support automatic website pairing/,
  );
});

test("desktop connector rejects an installation without offline models", async () => {
  const connector = new MeetingAudio.CompanionConnector({
    fetchImpl: async () => ({
      ok: true,
      status: 200,
      async json() {
        return {
          product: "NotesBuddy Desktop Companion",
          apiVersion: 1,
          status: "available",
          browserPairing: true,
          modelsReady: false,
        };
      },
    }),
  });

  await assert.rejects(
    connector.connect(),
    /offline models are missing/,
  );
});

test("transcription client sends pairing token and all source assets", async () => {
  const calls = [];
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url, options });
    return {
      ok: true,
      status: 200,
      async json() {
        return { jobId: "job-123", status: "queued" };
      },
    };
  };
  const client = new MeetingAudio.TranscriptionClient({
    endpoint: "http://127.0.0.1:8765/",
    token: "pairing-secret",
    fetchImpl,
  });

  const result = await client.createJob({
    microphoneBlob: new Blob(["mic"], { type: "audio/webm" }),
    meetingBlob: new Blob(["meeting"], { type: "audio/webm" }),
    mixedBlob: new Blob(["mixed"], { type: "audio/webm" }),
    metadata: { meetingId: "meeting-1" },
  });

  assert.equal(result.jobId, "job-123");
  assert.equal(calls[0].url, "http://127.0.0.1:8765/v1/transcriptions");
  assert.equal(
    calls[0].options.headers["X-NotesBuddy-Pairing-Token"],
    "pairing-secret",
  );
  assert.equal(calls[0].options.targetAddressSpace, "loopback");
  assert.deepEqual(
    Array.from(calls[0].options.body.keys()),
    ["microphone", "meeting", "mixed", "metadata"],
  );
});

test("local client controls Windows output capture and downloads WAV audio", async () => {
  const calls = [];
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url, options });
    if (url.endsWith("/stop")) {
      return {
        ok: true,
        status: 200,
        async blob() {
          return new Blob(["RIFF synthetic wav"], { type: "audio/wav" });
        },
      };
    }
    return {
      ok: true,
      status: 200,
      async json() {
        return {
          captureId: "capture-test",
          status: url.endsWith("/pause")
            ? "paused"
            : "recording",
          signalDetected: true,
        };
      },
    };
  };
  const client = new MeetingAudio.TranscriptionClient({
    endpoint: "http://127.0.0.1:8765",
    token: "system-audio-pairing-secret",
    fetchImpl,
  });

  const started = await client.startSystemAudioCapture();
  await client.getSystemAudioCapture(started.captureId);
  await client.pauseSystemAudioCapture(started.captureId);
  await client.resumeSystemAudioCapture(started.captureId);
  const recording = await client.stopSystemAudioCapture(started.captureId);

  assert.equal(recording.type, "audio/wav");
  assert.ok(recording.size > 0);
  assert.deepEqual(
    calls.map(({ url, options }) => [
      new URL(url).pathname,
      options.method || "GET",
    ]),
    [
      ["/v1/system-audio/captures", "POST"],
      ["/v1/system-audio/captures/capture-test", "GET"],
      ["/v1/system-audio/captures/capture-test/pause", "POST"],
      ["/v1/system-audio/captures/capture-test/resume", "POST"],
      ["/v1/system-audio/captures/capture-test/stop", "POST"],
    ],
  );
  assert.ok(
    calls.every(
      ({ options }) =>
        options.targetAddressSpace === "loopback" &&
        options.headers["X-NotesBuddy-Pairing-Token"] ===
          "system-audio-pairing-secret",
    ),
  );
});

test("hosted client refuses desktop system audio capture", async () => {
  const client = new MeetingAudio.TranscriptionClient({
    endpoint: "https://transcribe.example.test",
    mode: "hosted",
    fetchImpl: async () => {
      throw new Error("Hosted fetch must not be called");
    },
  });

  assert.throws(
    () => client.startSystemAudioCapture(),
    /requires the desktop companion/,
  );
});

test("hosted transcription client creates an anonymous session automatically", async () => {
  const calls = [];
  const sessionValues = new Map();
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url, options });
    if (url.endsWith("/v1/sessions")) {
      return {
        ok: true,
        status: 200,
        async json() {
          return {
            sessionToken: "anonymous-session-secret",
            expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
          };
        },
      };
    }
    return {
      ok: true,
      status: 200,
      async json() {
        return { jobId: "job-public", status: "queued" };
      },
    };
  };
  const client = new MeetingAudio.TranscriptionClient({
    endpoint: "https://transcribe.example.test/",
    mode: "hosted",
    token: "must-not-be-used",
    fetchImpl,
    sessionStorageImpl: {
      getItem(key) {
        return sessionValues.get(key) || null;
      },
      setItem(key, value) {
        sessionValues.set(key, value);
      },
    },
  });

  const result = await client.createJob({
    meetingBlob: new Blob(["meeting"], { type: "audio/webm" }),
    metadata: { meetingId: "meeting-public" },
  });

  assert.equal(result.jobId, "job-public");
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, "https://transcribe.example.test/v1/sessions");
  assert.equal(
    calls[1].options.headers["X-NotesBuddy-Session-Token"],
    "anonymous-session-secret",
  );
  assert.equal(
    calls[1].options.headers["X-NotesBuddy-Pairing-Token"],
    undefined,
  );
  assert.equal(calls[0].options.targetAddressSpace, undefined);
  assert.equal(calls[1].options.targetAddressSpace, undefined);
  assert.equal(sessionValues.size, 1);
});

test("hosted transcription client replaces a session lost during scale-to-zero", async () => {
  const endpoint = "https://transcribe.example.test";
  const storageKey = `notesbuddy-transcription-session:${endpoint}`;
  const sessionValues = new Map([
    [
      storageKey,
      JSON.stringify({
        sessionToken: "stale-session",
        expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
      }),
    ],
  ]);
  const jobTokens = [];
  let sessionsCreated = 0;
  const fetchImpl = async (url, options = {}) => {
    if (url.endsWith("/v1/sessions")) {
      sessionsCreated += 1;
      return {
        ok: true,
        status: 200,
        async json() {
          return {
            sessionToken: "replacement-session",
            expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
          };
        },
      };
    }
    jobTokens.push(options.headers["X-NotesBuddy-Session-Token"]);
    const accepted =
      options.headers["X-NotesBuddy-Session-Token"] === "replacement-session";
    return {
      ok: accepted,
      status: accepted ? 200 : 401,
      async json() {
        return accepted
          ? { jobId: "job-after-cold-start", status: "queued" }
          : { detail: "The anonymous transcription session expired." };
      },
    };
  };
  const client = new MeetingAudio.TranscriptionClient({
    endpoint,
    mode: "hosted",
    fetchImpl,
    sessionStorageImpl: {
      getItem(key) {
        return sessionValues.get(key) || null;
      },
      setItem(key, value) {
        sessionValues.set(key, value);
      },
      removeItem(key) {
        sessionValues.delete(key);
      },
    },
  });

  const result = await client.createJob({
    mixedBlob: new Blob(["audio"], { type: "audio/webm" }),
  });

  assert.equal(result.jobId, "job-after-cold-start");
  assert.equal(sessionsCreated, 1);
  assert.deepEqual(jobTokens, ["stale-session", "replacement-session"]);
});
