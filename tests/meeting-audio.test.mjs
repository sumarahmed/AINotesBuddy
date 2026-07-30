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
  assert.deepEqual(
    Array.from(calls[0].options.body.keys()),
    ["microphone", "meeting", "mixed", "metadata"],
  );
});
