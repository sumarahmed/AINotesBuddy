(function initialiseMeetingAudio(globalObject) {
  "use strict";

  const SPEAKER_COLORS = ["violet", "amber", "coral", "teal"];
  const RECORDING_SOURCES = ["mixed", "microphone", "meeting"];
  const LONG_RECORDING_SECONDS = 8 * 60;
  const MINIMUM_TRANSCRIPTION_TIMEOUT_MS = 30 * 60 * 1000;
  const MAXIMUM_TRANSCRIPTION_TIMEOUT_MS = 6 * 60 * 60 * 1000;

  function createId(prefix) {
    const uniquePart =
      globalObject.crypto?.randomUUID?.() ||
      `${Math.random().toString(36).slice(2, 12)}-${Math.random()
        .toString(36)
        .slice(2, 12)}`;
    return `${prefix}-${uniquePart}`;
  }

  function cleanName(value, fallback = "") {
    const cleaned = String(value || "")
      .trim()
      .replace(/\s+/g, " ")
      .slice(0, 80);
    return cleaned || fallback;
  }

  function cleanTranscriptText(value) {
    return String(value || "")
      .replace(/\u0000/g, "")
      .replace(/[ \t]+/g, " ")
      .replace(/\s*\n\s*/g, "\n")
      .trim();
  }

  function versionParts(value) {
    const match = String(value || "")
      .trim()
      .match(/(?:^|v)(\d+)\.(\d+)\.(\d+)$/i);
    return match ? match.slice(1).map((part) => Number(part)) : null;
  }

  function compareVersions(left, right) {
    const leftParts = versionParts(left);
    const rightParts = versionParts(right);
    if (!leftParts || !rightParts) return null;
    for (let index = 0; index < 3; index += 1) {
      if (leftParts[index] < rightParts[index]) return -1;
      if (leftParts[index] > rightParts[index]) return 1;
    }
    return 0;
  }

  function selectTranscriptionRoute({
    runtimeMode = "local",
    currentMode = "local",
    durationSeconds = 0,
    accelerateLongRecordings = true,
    hostedEndpoint = "",
    longRecordingSeconds = LONG_RECORDING_SECONDS,
    companionConnected = false,
  } = {}) {
    const canAccelerate =
      runtimeMode === "hybrid" &&
      currentMode === "local" &&
      Boolean(String(hostedEndpoint || "").trim()) &&
      companionConnected !== true &&
      accelerateLongRecordings !== false &&
      Number(durationSeconds) >= Number(longRecordingSeconds);
    return canAccelerate ? "hosted" : currentMode;
  }

  function transcriptionTimeoutMs({ durationSeconds = 0, mode = "local" } = {}) {
    const durationMs = Math.max(0, Number(durationSeconds) || 0) * 1000;
    const minimumMs = mode === "hosted"
      ? 60 * 60 * 1000
      : MINIMUM_TRANSCRIPTION_TIMEOUT_MS;
    const estimatedMs = durationMs * (mode === "hosted" ? 2 : 3) +
      15 * 60 * 1000;
    return Math.min(
      MAXIMUM_TRANSCRIPTION_TIMEOUT_MS,
      Math.max(minimumMs, estimatedMs),
    );
  }

  function selectTranscriptionBlobs({
    microphone = null,
    meeting = null,
    mixed = null,
  } = {}) {
    return {
      microphone,
      meeting,
      mixed: microphone || meeting ? null : mixed,
    };
  }

  function isVersionOutdated(installedVersion, latestVersion) {
    return compareVersions(installedVersion, latestVersion) === -1;
  }

  function initialsForName(name) {
    const words = cleanName(name, "Speaker")
      .split(/\s+/)
      .filter(Boolean);
    const first = words[0]?.[0] || "S";
    const last =
      words.length > 1 ? words.at(-1)[0] : words[0]?.[1] || "";
    return `${first}${last}`.toUpperCase();
  }

  function parseTimestamp(value) {
    if (Number.isFinite(value)) return Math.max(0, value);
    const parts = String(value || "")
      .split(":")
      .map((part) => Number(part));
    if (!parts.length || parts.some((part) => !Number.isFinite(part))) return 0;
    const seconds =
      parts.length === 3
        ? parts[0] * 3600 + parts[1] * 60 + parts[2]
        : (parts[0] || 0) * 60 + (parts[1] || 0);
    return Math.max(0, seconds * 1000);
  }

  function formatTimestamp(milliseconds) {
    const totalSeconds = Math.max(
      0,
      Math.floor((Number(milliseconds) || 0) / 1000),
    );
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    return hours
      ? `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`
      : `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }

  function provisionalDraftSpeaker({
    startMs = 0,
    endMs = startMs,
    meetingActivitySpans = [],
  } = {}) {
    const safeStartMs = Math.max(0, Number(startMs) || 0);
    const safeEndMs = Math.max(safeStartMs, Number(endMs) || safeStartMs);
    const alignmentStartMs = Math.max(safeStartMs, safeEndMs - 1400) - 250;
    const alignmentEndMs = safeEndMs + 250;
    const meetingWasActive = (Array.isArray(meetingActivitySpans)
      ? meetingActivitySpans
      : []
    ).some((span) => {
      const spanStartMs = Math.max(0, Number(span?.startMs) || 0);
      const spanEndMs = Math.max(
        spanStartMs,
        Number(span?.endMs) || spanStartMs,
      );
      return (
        spanStartMs <= alignmentEndMs && spanEndMs >= alignmentStartMs
      );
    });
    return meetingWasActive
      ? {
          speakerId: "remote-guest",
          speaker: "Guest",
          initials: "G",
          color: "violet",
          source: "meeting",
          provisional: true,
        }
      : {
          speakerId: "local-user",
          speaker: "You",
          initials: "U",
          color: "teal",
          source: "microphone",
          provisional: false,
        };
  }

  function slug(value) {
    return (
      cleanName(value, "speaker")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "") || "speaker"
    );
  }

  function getRecordingAssets(meeting) {
    const assets = {};
    for (const source of RECORDING_SOURCES) {
      const asset = meeting?.recordingAssets?.[source];
      if (asset?.id) {
        assets[source] = {
          id: asset.id,
          mimeType: asset.mimeType || null,
          durationMs: Number(asset.durationMs) || 0,
          fileName: asset.fileName || null,
        };
      }
    }
    if (!Object.keys(assets).length && meeting?.audioId) {
      assets.mixed = {
        id: meeting.audioId,
        mimeType: meeting.audioType || null,
        durationMs: Math.max(
          0,
          Number(meeting.durationSeconds || 0) * 1000,
        ),
        fileName: meeting.audioFileName || null,
      };
    }
    return assets;
  }

  function recordingAssetIds(meeting) {
    return Array.from(
      new Set(
        [
          meeting?.audioId,
          ...Object.values(getRecordingAssets(meeting)).map(
            (asset) => asset.id,
          ),
        ].filter(Boolean),
      ),
    );
  }

  function primaryRecordingSource(meeting, preferredSource) {
    const assets = getRecordingAssets(meeting);
    if (preferredSource && assets[preferredSource]) return preferredSource;
    if (meeting?.meetingCaptureMode === "companion" && assets.meeting) {
      return "meeting";
    }
    return RECORDING_SOURCES.find((source) => assets[source]) || null;
  }

  function recordingAsset(meeting, preferredSource) {
    const source = primaryRecordingSource(meeting, preferredSource);
    return source ? { source, ...getRecordingAssets(meeting)[source] } : null;
  }

  function recordingDownloadName(meeting, source = "mixed") {
    const asset = getRecordingAssets(meeting)[source];
    const existingName = asset?.fileName || meeting?.audioFileName;
    if (existingName && source === "mixed") {
      return existingName.replace(/[<>:"/\\|?*\u0000-\u001f]/g, "-");
    }
    const type = String(asset?.mimeType || meeting?.audioType || "").toLowerCase();
    const extension = type.includes("wav")
      ? "wav"
      : type.includes("mpeg") || type.includes("mp3")
        ? "mp3"
        : type.includes("mp4") || type.includes("m4a")
          ? "m4a"
          : type.includes("ogg")
            ? "ogg"
            : type.includes("flac")
              ? "flac"
              : "webm";
    const baseName =
      String(meeting?.title || "recording")
        .replace(/[^a-z0-9]+/gi, "-")
        .replace(/^-|-$/g, "")
        .toLowerCase() || "recording";
    const suffix = source === "mixed" ? "" : `-${source}`;
    return `${baseName}${suffix}.${extension}`;
  }

  function speakerLabel(meeting, speakerId, fallback = "Unknown speaker") {
    if (speakerId === "local-user") return "You";
    const speaker = meeting?.speakers?.find((item) => item.id === speakerId);
    return cleanName(speaker?.displayName, fallback);
  }

  function ensureMeetingSpeakers(meeting, profile) {
    if (!meeting || typeof meeting !== "object") return meeting;
    meeting.recordingAssets = getRecordingAssets(meeting);
    const existing = new Map(
      (Array.isArray(meeting.speakers) ? meeting.speakers : [])
        .filter((speaker) => speaker?.id)
        .map((speaker) => [speaker.id, { ...speaker }]),
    );
    const profileName = cleanName(profile?.name, "You");
    let remoteIndex = 0;
    meeting.transcript = Array.isArray(meeting.transcript)
      ? meeting.transcript
      : [];

    for (const segment of meeting.transcript) {
      const legacyName = cleanName(segment.speaker, "");
      const isLocal =
        segment.speakerId === "local-user" ||
        segment.source === "microphone" ||
        (legacyName &&
          profileName &&
          legacyName.toLowerCase() === profileName.toLowerCase());
      let speakerId = segment.speakerId;
      if (!speakerId) {
        if (isLocal) {
          speakerId = "local-user";
        } else {
          remoteIndex += 1;
          speakerId = `legacy-${slug(legacyName || `speaker-${remoteIndex}`)}`;
        }
      }
      segment.speakerId = speakerId;
      segment.source =
        segment.source || (speakerId === "local-user" ? "microphone" : "mixed");
      segment.startMs = Number.isFinite(segment.startMs)
        ? Math.max(0, segment.startMs)
        : parseTimestamp(segment.timestamp);
      segment.endMs = Number.isFinite(segment.endMs)
        ? Math.max(segment.startMs, segment.endMs)
        : segment.startMs;
      segment.timestamp = segment.timestamp || formatTimestamp(segment.startMs);

      if (!existing.has(speakerId)) {
        const displayName =
          speakerId === "local-user"
            ? profileName
            : legacyName || `Speaker ${++remoteIndex}`;
        existing.set(speakerId, {
          id: speakerId,
          displayName,
          source:
            speakerId === "local-user"
              ? "microphone"
              : segment.source || "meeting",
          color:
            speakerId === "local-user"
              ? "teal"
              : segment.color ||
                SPEAKER_COLORS[
                  Math.max(0, remoteIndex - 1) % SPEAKER_COLORS.length
                ],
          isLocalUser: speakerId === "local-user",
        });
      }
      const speaker = existing.get(speakerId);
      segment.speaker =
        speakerId === "local-user" ? "You" : speaker.displayName;
      segment.initials =
        speakerId === "local-user"
          ? profile?.initials || initialsForName(profileName)
          : initialsForName(speaker.displayName);
      segment.color = speaker.color;
    }

    if (
      meeting.recordingAssets.microphone &&
      !existing.has("local-user")
    ) {
      existing.set("local-user", {
        id: "local-user",
        displayName: profileName,
        source: "microphone",
        color: "teal",
        isLocalUser: true,
      });
    }

    meeting.speakers = Array.from(existing.values()).map((speaker) => ({
      id: speaker.id,
      displayName:
        speaker.id === "local-user"
          ? profileName
          : cleanName(speaker.displayName, "Unknown speaker"),
      source:
        speaker.id === "local-user"
          ? "microphone"
          : speaker.source || "meeting",
      color:
        speaker.id === "local-user"
          ? "teal"
          : speaker.color ||
            SPEAKER_COLORS[
              Math.max(
                0,
                Array.from(existing.keys()).indexOf(speaker.id) - 1,
              ) % SPEAKER_COLORS.length
            ],
      isLocalUser: speaker.id === "local-user",
    }));
    return meeting;
  }

  function normaliseText(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s]/gu, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function overlapRatio(first, second) {
    const start = Math.max(first.startMs || 0, second.startMs || 0);
    const end = Math.min(first.endMs || first.startMs || 0, second.endMs || second.startMs || 0);
    const overlap = Math.max(0, end - start);
    const shortest = Math.max(
      1,
      Math.min(
        Math.max(1, (first.endMs || first.startMs || 0) - (first.startMs || 0)),
        Math.max(1, (second.endMs || second.startMs || 0) - (second.startMs || 0)),
      ),
    );
    return overlap / shortest;
  }

  function textSimilarity(first, second) {
    const firstWords = new Set(normaliseText(first).split(" ").filter(Boolean));
    const secondWords = new Set(
      normaliseText(second).split(" ").filter(Boolean),
    );
    if (!firstWords.size || !secondWords.size) return 0;
    const intersection = Array.from(firstWords).filter((word) =>
      secondWords.has(word),
    ).length;
    const union = new Set([...firstWords, ...secondWords]).size;
    return intersection / Math.max(1, union);
  }

  function deduplicateEchoSegments(segments) {
    const sorted = [...segments].sort(
      (first, second) => first.startMs - second.startMs,
    );
    const removed = new Set();
    for (let firstIndex = 0; firstIndex < sorted.length; firstIndex += 1) {
      if (removed.has(firstIndex)) continue;
      const first = sorted[firstIndex];
      for (
        let secondIndex = firstIndex + 1;
        secondIndex < sorted.length;
        secondIndex += 1
      ) {
        if (removed.has(secondIndex)) continue;
        const second = sorted[secondIndex];
        if (second.startMs - first.endMs > 1800) break;
        if (first.source === second.source) continue;
        if (overlapRatio(first, second) < 0.55) continue;
        if (textSimilarity(first.text, second.text) < 0.82) continue;
        const firstIsMicrophone = first.source === "microphone";
        const secondIsMicrophone = second.source === "microphone";
        if (firstIsMicrophone !== secondIsMicrophone) {
          removed.add(firstIsMicrophone ? firstIndex : secondIndex);
        } else if (
          (Number(first.confidence) || 0) >=
          (Number(second.confidence) || 0)
        ) {
          removed.add(secondIndex);
        } else {
          removed.add(firstIndex);
        }
      }
    }
    return sorted.filter((_, index) => !removed.has(index));
  }

  function normaliseResultSegment(segment, index, profile) {
    const source =
      segment.source === "microphone" ? "microphone" : "meeting";
    const speakerId =
      source === "microphone"
        ? "local-user"
        : cleanName(segment.speakerId, `remote-${index + 1}`);
    const startMs = Math.max(0, Number(segment.startMs) || 0);
    const endMs = Math.max(startMs, Number(segment.endMs) || startMs);
    const displayName =
      speakerId === "local-user"
        ? "You"
        : cleanName(segment.speakerLabel, "");
    return {
      id: cleanName(segment.id, "") || createId("speech"),
      speakerId,
      speaker: displayName || "",
      initials:
        speakerId === "local-user"
          ? profile?.initials || "U"
          : initialsForName(displayName || speakerId),
      color:
        speakerId === "local-user"
          ? "teal"
          : SPEAKER_COLORS[index % SPEAKER_COLORS.length],
      source,
      startMs,
      endMs,
      timestamp: formatTimestamp(startMs),
      text: cleanTranscriptText(segment.text),
      confidence: Number.isFinite(Number(segment.confidence))
        ? Number(segment.confidence)
        : null,
      isDraft: false,
    };
  }

  function applyTranscriptionResult(meeting, result, profile) {
    const rawSegments = Array.isArray(result?.segments) ? result.segments : [];
    const normalized = rawSegments
      .map((segment, index) => normaliseResultSegment(segment, index, profile))
      .filter((segment) => segment.text);
    const segments = deduplicateEchoSegments(normalized);
    const existingSpeakers = new Map(
      (meeting.speakers || []).map((speaker) => [speaker.id, speaker]),
    );
    const remoteIds = [];
    for (const segment of segments) {
      if (
        segment.speakerId !== "local-user" &&
        !remoteIds.includes(segment.speakerId)
      ) {
        remoteIds.push(segment.speakerId);
      }
    }
    const speakers = [];
    if (
      segments.some((segment) => segment.speakerId === "local-user") ||
      meeting.recordingAssets?.microphone
    ) {
      speakers.push({
        id: "local-user",
        displayName: cleanName(profile?.name, "You"),
        source: "microphone",
        color: "teal",
        isLocalUser: true,
      });
    }
    remoteIds.forEach((speakerId, index) => {
      const existing = existingSpeakers.get(speakerId);
      const suggestedName = segments.find(
        (segment) => segment.speakerId === speakerId,
      )?.speaker;
      speakers.push({
        id: speakerId,
        displayName: cleanName(
          existing?.displayName || suggestedName,
          `Speaker ${index + 1}`,
        ),
        source: "meeting",
        color:
          existing?.color || SPEAKER_COLORS[index % SPEAKER_COLORS.length],
        isLocalUser: false,
      });
    });
    const speakerMap = new Map(speakers.map((speaker) => [speaker.id, speaker]));
    for (const segment of segments) {
      const speaker = speakerMap.get(segment.speakerId);
      segment.speaker =
        segment.speakerId === "local-user"
          ? "You"
          : speaker?.displayName || "Unknown speaker";
      segment.initials =
        segment.speakerId === "local-user"
          ? profile?.initials || "U"
          : initialsForName(segment.speaker);
      segment.color = speaker?.color || segment.color;
    }
    meeting.transcript = segments;
    meeting.speakers = speakers;
    meeting.transcription = {
      ...(meeting.transcription || {}),
      status: "completed",
      jobId: result?.jobId || meeting.transcription?.jobId || null,
      language: result?.language || null,
      completedAt: new Date().toISOString(),
      error: null,
      segmentCount: segments.length,
    };
    meeting.participants = speakers.map((speaker) => ({
      name:
        speaker.id === "local-user"
          ? cleanName(profile?.name, "You")
          : speaker.displayName,
      initials:
        speaker.id === "local-user"
          ? profile?.initials || "U"
          : initialsForName(speaker.displayName),
      color: speaker.color,
    }));
    return meeting;
  }

  function renameSpeaker(meeting, speakerId, name, profile) {
    const speaker = meeting?.speakers?.find((item) => item.id === speakerId);
    if (!speaker) return false;
    const cleaned = cleanName(name, "");
    if (!cleaned) return false;
    const previousDisplayName = speaker.displayName;
    if (speakerId === "local-user") {
      speaker.displayName = cleanName(profile?.name, cleaned);
    } else {
      speaker.displayName = cleaned;
    }
    for (const segment of meeting.transcript || []) {
      if (segment.speakerId !== speakerId) continue;
      segment.speaker = speakerId === "local-user" ? "You" : speaker.displayName;
      segment.initials =
        speakerId === "local-user"
          ? profile?.initials || "U"
          : initialsForName(speaker.displayName);
    }
    for (const action of meeting.actions || []) {
      if (
        action.sourceSpeakerId === speakerId ||
        (previousDisplayName && action.owner === previousDisplayName)
      ) {
        action.owner =
          speakerId === "local-user"
            ? cleanName(profile?.name, "You")
            : speaker.displayName;
      }
    }
    for (const decision of meeting.decisions || []) {
      if (
        decision.sourceSpeakerId === speakerId ||
        (previousDisplayName && decision.owner === previousDisplayName)
      ) {
        decision.owner =
          speakerId === "local-user"
            ? cleanName(profile?.name, "You")
            : speaker.displayName;
      }
    }
    meeting.participants = (meeting.speakers || []).map((item) => ({
      name:
        item.id === "local-user"
          ? cleanName(profile?.name, "You")
          : item.displayName,
      initials:
        item.id === "local-user"
          ? profile?.initials || "U"
          : initialsForName(item.displayName),
      color: item.color,
    }));
    return true;
  }

  function analysisSourceIds(value, validIds) {
    const sourceIds = [];
    for (const rawId of Array.isArray(value) ? value : []) {
      const sourceId = cleanName(rawId, "");
      if (sourceId && validIds.has(sourceId) && !sourceIds.includes(sourceId)) {
        sourceIds.push(sourceId);
      }
    }
    return sourceIds.slice(0, 12);
  }

  function normaliseMeetingAnalysis(rawAnalysis, transcript) {
    if (!rawAnalysis || typeof rawAnalysis !== "object") return null;
    const validIds = new Set(
      (Array.isArray(transcript) ? transcript : [])
        .map((segment) => cleanName(segment?.id, ""))
        .filter(Boolean),
    );
    const shortSummary = cleanTranscriptText(rawAnalysis.shortSummary);
    const summarySourceSegmentIds = analysisSourceIds(
      rawAnalysis.summarySourceSegmentIds,
      validIds,
    );
    if (
      !shortSummary ||
      shortSummary.split(/\s+/).length >= 300 ||
      !summarySourceSegmentIds.length
    ) {
      return null;
    }

    const highlights = [];
    const seenHighlights = new Set();
    for (const rawItem of Array.isArray(rawAnalysis.highlights)
      ? rawAnalysis.highlights
      : []) {
      const text = cleanTranscriptText(rawItem?.text);
      const sourceSegmentIds = analysisSourceIds(
        rawItem?.sourceSegmentIds,
        validIds,
      );
      const key = normaliseText(text);
      if (!text || !sourceSegmentIds.length || !key || seenHighlights.has(key)) {
        continue;
      }
      seenHighlights.add(key);
      highlights.push({ text, sourceSegmentIds });
      if (highlights.length >= 12) break;
    }

    const decisions = [];
    const seenDecisions = new Set();
    for (const rawItem of Array.isArray(rawAnalysis.decisions)
      ? rawAnalysis.decisions
      : []) {
      const decision = cleanTranscriptText(rawItem?.decision);
      const sourceSegmentIds = analysisSourceIds(
        rawItem?.sourceSegmentIds,
        validIds,
      );
      const key = normaliseText(decision);
      if (!decision || !sourceSegmentIds.length || !key || seenDecisions.has(key)) {
        continue;
      }
      seenDecisions.add(key);
      decisions.push({
        decision,
        context: cleanTranscriptText(rawItem?.context) || "Not specified",
        owner: cleanName(rawItem?.owner, "Not specified"),
        sourceSegmentIds,
      });
      if (decisions.length >= 12) break;
    }

    const actionItems = [];
    const seenActions = new Set();
    for (const rawItem of Array.isArray(rawAnalysis.actionItems)
      ? rawAnalysis.actionItems
      : []) {
      const task = cleanTranscriptText(rawItem?.task);
      const sourceSegmentIds = analysisSourceIds(
        rawItem?.sourceSegmentIds,
        validIds,
      );
      const key = normaliseText(task);
      if (!task || !sourceSegmentIds.length || !key || seenActions.has(key)) {
        continue;
      }
      seenActions.add(key);
      const priority = cleanName(rawItem?.priority, "Medium");
      actionItems.push({
        task,
        owner: cleanName(rawItem?.owner, "Not specified"),
        dueDate: cleanName(rawItem?.dueDate, "Not specified"),
        priority: ["High", "Medium", "Low"].includes(priority)
          ? priority
          : "Medium",
        notes: cleanTranscriptText(rawItem?.notes) || "Not specified",
        sourceSegmentIds,
      });
      if (actionItems.length >= 30) break;
    }

    return {
      schemaVersion: Number(rawAnalysis.schemaVersion) || 1,
      promptVersion: Number(rawAnalysis.promptVersion) || 1,
      model: cleanName(rawAnalysis.model, "Professional meeting analyst"),
      shortSummary,
      summarySourceSegmentIds,
      highlights,
      decisions,
      actionItems,
    };
  }

  class CompanionConnector {
    constructor({
      endpoint = "http://127.0.0.1:8765",
      fetchImpl = globalObject.fetch,
      timeoutMs = 8000,
    } = {}) {
      this.endpoint = String(endpoint).replace(/\/+$/, "");
      this.fetchImpl =
        typeof fetchImpl === "function"
          ? fetchImpl.bind(globalObject)
          : fetchImpl;
      this.timeoutMs = Math.max(250, Number(timeoutMs) || 8000);
    }

    async request(path, options = {}) {
      if (typeof this.fetchImpl !== "function") {
        throw new Error("This browser cannot connect to the desktop companion.");
      }
      const controller = new AbortController();
      const timeout = globalObject.setTimeout(
        () => controller.abort(),
        this.timeoutMs,
      );
      try {
        const response = await this.fetchImpl(`${this.endpoint}${path}`, {
          cache: "no-store",
          mode: "cors",
          targetAddressSpace: "loopback",
          ...options,
          signal: controller.signal,
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch {
          payload = null;
        }
        if (!response.ok) {
          const error = new Error(
            payload?.detail ||
              `Desktop companion returned ${response.status}`,
          );
          error.status = response.status;
          throw error;
        }
        return payload;
      } catch (error) {
        if (error?.name === "AbortError") {
          throw new Error("Desktop companion connection timed out.");
        }
        throw error;
      } finally {
        globalObject.clearTimeout(timeout);
      }
    }

    async discover() {
      const companion = await this.request("/v1/companion", {
        method: "GET",
        headers: { Accept: "application/json" },
      });
      if (
        companion?.product !== "NotesBuddy Desktop Companion" ||
        companion?.status !== "available" ||
        companion?.apiVersion !== 1
      ) {
        throw new Error("An incompatible service is using the companion port.");
      }
      if (!companion.browserPairing) {
        throw new Error(
          "The running companion does not support automatic website pairing.",
        );
      }
      return companion;
    }

    pair() {
      return this.request("/v1/pairings", {
        method: "POST",
        headers: { Accept: "application/json" },
      });
    }

    async connect() {
      const companion = await this.discover();
      const pairing = await this.pair();
      const token = String(pairing?.pairingToken || "");
      if (token.length < 24) {
        throw new Error("The desktop companion returned an invalid pairing.");
      }
      const health = await this.request("/v1/health", {
        method: "GET",
        headers: {
          Accept: "application/json",
          "X-NotesBuddy-Pairing-Token": token,
        },
      });
      if (health?.status !== "ok") {
        throw new Error("The desktop companion is not ready.");
      }
      return {
        endpoint: this.endpoint,
        token,
        companion,
        health,
        expiresAt: pairing?.expiresAt || null,
      };
    }
  }

  class TranscriptionClient {
    constructor({
      endpoint,
      token = "",
      mode = "local",
      fetchImpl = globalObject.fetch,
      sessionStorageImpl,
    } = {}) {
      this.endpoint = String(endpoint || "http://127.0.0.1:8765").replace(
        /\/+$/,
        "",
      );
      this.mode = mode === "hosted" ? "hosted" : "local";
      this.token = String(token || "");
      this.sessionToken = "";
      this.sessionExpiresAt = 0;
      try {
        this.sessionStorage =
          sessionStorageImpl === undefined
            ? globalObject.sessionStorage
            : sessionStorageImpl;
      } catch {
        this.sessionStorage = null;
      }
      this.sessionStorageKey = `notesbuddy-transcription-session:${this.endpoint}`;
      this.fetchImpl =
        typeof fetchImpl === "function"
          ? fetchImpl.bind(globalObject)
          : fetchImpl;
      this.restoreSession();
    }

    restoreSession() {
      if (this.mode !== "hosted" || !this.sessionStorage) return;
      try {
        const stored = JSON.parse(
          this.sessionStorage.getItem(this.sessionStorageKey) || "null",
        );
        const expiresAt = Date.parse(stored?.expiresAt || "");
        if (
          stored?.sessionToken &&
          Number.isFinite(expiresAt) &&
          expiresAt > Date.now() + 30_000
        ) {
          this.sessionToken = String(stored.sessionToken);
          this.sessionExpiresAt = expiresAt;
        }
      } catch {
        // A blocked or malformed session store simply creates a fresh session.
      }
    }

    saveSession(expiresAt) {
      if (!this.sessionStorage) return;
      try {
        this.sessionStorage.setItem(
          this.sessionStorageKey,
          JSON.stringify({
            sessionToken: this.sessionToken,
            expiresAt,
          }),
        );
      } catch {
        // In-memory use still works when sessionStorage is unavailable.
      }
    }

    clearSession() {
      this.sessionToken = "";
      this.sessionExpiresAt = 0;
      if (!this.sessionStorage) return;
      try {
        this.sessionStorage.removeItem(this.sessionStorageKey);
      } catch {
        // The next request can still create an in-memory replacement session.
      }
    }

    async ensureSession() {
      if (this.mode !== "hosted") return;
      if (
        this.sessionToken &&
        this.sessionExpiresAt > Date.now() + 30_000
      ) {
        return;
      }
      const response = await this.fetchImpl(`${this.endpoint}/v1/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      let payload = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      if (!response.ok || !payload?.sessionToken) {
        const error = new Error(
          payload?.detail ||
            payload?.error ||
            `Public transcription service returned ${response.status}`,
        );
        error.status = response.status;
        throw error;
      }
      this.sessionToken = String(payload.sessionToken);
      this.sessionExpiresAt =
        Date.parse(payload.expiresAt || "") || Date.now() + 60 * 60 * 1000;
      this.saveSession(
        payload.expiresAt || new Date(this.sessionExpiresAt).toISOString(),
      );
    }

    headers(extra = {}) {
      return {
        ...(this.mode === "hosted" && this.sessionToken
          ? { "X-NotesBuddy-Session-Token": this.sessionToken }
          : this.token
            ? { "X-NotesBuddy-Pairing-Token": this.token }
            : {}),
        ...extra,
      };
    }

    async request(path, options = {}) {
      const {
        skipSession = false,
        retrySession = true,
        ...fetchOptions
      } = options;
      if (this.mode === "hosted" && !skipSession) {
        await this.ensureSession();
      }
      let response = await this.fetchImpl(`${this.endpoint}${path}`, {
        ...(this.mode === "local"
          ? { targetAddressSpace: "loopback" }
          : {}),
        ...fetchOptions,
        headers: this.headers(fetchOptions.headers),
      });
      if (
        response.status === 401 &&
        this.mode === "hosted" &&
        !skipSession &&
        retrySession
      ) {
        this.clearSession();
        await this.ensureSession();
        response = await this.fetchImpl(`${this.endpoint}${path}`, {
          ...(this.mode === "local"
            ? { targetAddressSpace: "loopback" }
            : {}),
          ...fetchOptions,
          headers: this.headers(fetchOptions.headers),
        });
      }
      let payload = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      if (!response.ok) {
        const error = new Error(
          payload?.detail ||
            payload?.error ||
            `Transcription service returned ${response.status}`,
        );
        error.status = response.status;
        throw error;
      }
      return payload;
    }

    health() {
      return this.request("/v1/health", { skipSession: true });
    }

    componentStatus() {
      this.requireLocalSystemAudio();
      return this.request("/v1/components", { cache: "no-store" });
    }

    installComponents(components) {
      this.requireLocalSystemAudio();
      return this.request("/v1/components/install", {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ components }),
      });
    }

    componentJob(jobId) {
      this.requireLocalSystemAudio();
      return this.request(
        `/v1/components/jobs/${encodeURIComponent(jobId)}`,
        { cache: "no-store" },
      );
    }

    pauseComponentJob(jobId) {
      this.requireLocalSystemAudio();
      return this.request(
        `/v1/components/jobs/${encodeURIComponent(jobId)}`,
        { method: "DELETE", cache: "no-store" },
      );
    }

    requireLocalSystemAudio() {
      if (this.mode !== "local") {
        throw new Error(
          "Windows system audio capture requires the desktop companion.",
        );
      }
    }

    startSystemAudioCapture() {
      this.requireLocalSystemAudio();
      return this.request("/v1/system-audio/captures", {
        method: "POST",
        cache: "no-store",
      });
    }

    getSystemAudioCapture(captureId) {
      this.requireLocalSystemAudio();
      return this.request(
        `/v1/system-audio/captures/${encodeURIComponent(captureId)}`,
        { cache: "no-store" },
      );
    }

    pauseSystemAudioCapture(captureId) {
      this.requireLocalSystemAudio();
      return this.request(
        `/v1/system-audio/captures/${encodeURIComponent(captureId)}/pause`,
        { method: "POST", cache: "no-store" },
      );
    }

    resumeSystemAudioCapture(captureId) {
      this.requireLocalSystemAudio();
      return this.request(
        `/v1/system-audio/captures/${encodeURIComponent(captureId)}/resume`,
        { method: "POST", cache: "no-store" },
      );
    }

    cancelSystemAudioCapture(captureId) {
      this.requireLocalSystemAudio();
      return this.request(
        `/v1/system-audio/captures/${encodeURIComponent(captureId)}`,
        { method: "DELETE", cache: "no-store" },
      );
    }

    async stopSystemAudioCapture(captureId) {
      this.requireLocalSystemAudio();
      const response = await this.fetchImpl(
        `${this.endpoint}/v1/system-audio/captures/${encodeURIComponent(captureId)}/stop`,
        {
          method: "POST",
          cache: "no-store",
          targetAddressSpace: "loopback",
          headers: this.headers({ Accept: "audio/wav" }),
        },
      );
      if (!response.ok) {
        let payload = null;
        try {
          payload = await response.json();
        } catch {
          payload = null;
        }
        const error = new Error(
          payload?.detail ||
            `Desktop companion returned ${response.status}`,
        );
        error.status = response.status;
        throw error;
      }
      const blob = await response.blob();
      if (!blob?.size) {
        throw new Error("Desktop companion returned an empty audio recording.");
      }
      return blob.type
        ? blob
        : new Blob([blob], { type: "audio/wav" });
    }

    async createJob({
      microphoneBlob,
      meetingBlob,
      mixedBlob,
      metadata = {},
      onUploadProgress,
      signal,
    }) {
      if (!microphoneBlob && !meetingBlob && !mixedBlob) {
        throw new Error("At least one recording source is required");
      }
      const form = new FormData();
      if (microphoneBlob) {
        form.append("microphone", microphoneBlob, "microphone.webm");
      }
      if (meetingBlob) {
        form.append("meeting", meetingBlob, "meeting.webm");
      }
      if (mixedBlob) {
        form.append("mixed", mixedBlob, "mixed.webm");
      }
      form.append("metadata", JSON.stringify(metadata));
      if (
        this.mode === "hosted" &&
        typeof onUploadProgress === "function" &&
        typeof globalObject.XMLHttpRequest === "function"
      ) {
        return this.upload("/v1/transcriptions", {
          body: form,
          onUploadProgress,
          signal,
        });
      }
      return this.request("/v1/transcriptions", {
        method: "POST",
        body: form,
        signal,
      });
    }

    async upload(
      path,
      { body, onUploadProgress, signal, retrySession = true } = {},
    ) {
      await this.ensureSession();
      return new Promise((resolve, reject) => {
        const request = new globalObject.XMLHttpRequest();
        const abort = () => request.abort();
        const finish = () => signal?.removeEventListener("abort", abort);
        const fail = (message, status = 0) => {
          finish();
          const error = new Error(message);
          error.status = status;
          reject(error);
        };
        request.open("POST", `${this.endpoint}${path}`);
        for (const [name, value] of Object.entries(this.headers())) {
          request.setRequestHeader(name, value);
        }
        request.responseType = "json";
        request.upload.onprogress = (event) => {
          if (event.lengthComputable && event.total > 0) {
            onUploadProgress?.({
              loaded: event.loaded,
              total: event.total,
              ratio: event.loaded / event.total,
            });
          }
        };
        request.onerror = () =>
          fail("The audio upload failed. Check your connection and retry.");
        request.onabort = () => {
          finish();
          const error = new Error("Transcription cancelled");
          error.name = "AbortError";
          reject(error);
        };
        request.onload = async () => {
          finish();
          const payload =
            request.response && typeof request.response === "object"
              ? request.response
              : (() => {
                  try {
                    return JSON.parse(request.responseText || "null");
                  } catch {
                    return null;
                  }
                })();
          if (request.status === 401 && retrySession) {
            this.clearSession();
            try {
              resolve(
                await this.upload(path, {
                  body,
                  onUploadProgress,
                  signal,
                  retrySession: false,
                }),
              );
            } catch (error) {
              reject(error);
            }
            return;
          }
          if (request.status < 200 || request.status >= 300) {
            fail(
              payload?.detail ||
                payload?.error ||
                `Transcription service returned ${request.status}`,
              request.status,
            );
            return;
          }
          resolve(payload);
        };
        if (signal?.aborted) {
          request.abort();
          return;
        }
        signal?.addEventListener("abort", abort, { once: true });
        request.send(body);
      });
    }

    analyzeTranscript({ meetingTitle = "", segments = [] } = {}) {
      if (!Array.isArray(segments) || !segments.length) {
        throw new Error("A completed transcript is required for meeting analysis.");
      }
      return this.request("/v1/analyses", {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ meetingTitle, segments }),
      });
    }

    getJob(jobId) {
      return this.request(
        `/v1/transcriptions/${encodeURIComponent(jobId)}`,
      );
    }

    cancelJob(jobId) {
      return this.request(
        `/v1/transcriptions/${encodeURIComponent(jobId)}`,
        { method: "DELETE" },
      );
    }

    async waitForJob(
      jobId,
      { intervalMs = 1200, timeoutMs = 30 * 60 * 1000, onProgress, signal } = {},
    ) {
      const startedAt = Date.now();
      while (Date.now() - startedAt < timeoutMs) {
        if (signal?.aborted) {
          throw new DOMException("Transcription cancelled", "AbortError");
        }
        const job = await this.getJob(jobId);
        onProgress?.(job);
        if (job.status === "completed") return job;
        if (job.status === "failed" || job.status === "cancelled") {
          throw new Error(job.error || `Transcription ${job.status}`);
        }
        await new Promise((resolve) => globalObject.setTimeout(resolve, intervalMs));
      }
      try {
        await this.cancelJob(jobId);
      } catch {
        // Preserve the useful timeout error even if the service disappeared.
      }
      throw new Error("Transcription timed out");
    }
  }

  globalObject.NotesBuddyMeetingAudio = Object.freeze({
    RECORDING_SOURCES,
    SPEAKER_COLORS,
    LONG_RECORDING_SECONDS,
    CompanionConnector,
    TranscriptionClient,
    applyTranscriptionResult,
    cleanName,
    cleanTranscriptText,
    compareVersions,
    createId,
    deduplicateEchoSegments,
    ensureMeetingSpeakers,
    formatTimestamp,
    getRecordingAssets,
    initialsForName,
    isVersionOutdated,
    normaliseMeetingAnalysis,
    parseTimestamp,
    primaryRecordingSource,
    provisionalDraftSpeaker,
    recordingAsset,
    recordingAssetIds,
    recordingDownloadName,
    renameSpeaker,
    selectTranscriptionBlobs,
    selectTranscriptionRoute,
    speakerLabel,
    textSimilarity,
    transcriptionTimeoutMs,
  });
})(globalThis);
