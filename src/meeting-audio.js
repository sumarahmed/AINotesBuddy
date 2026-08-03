(function initialiseMeetingAudio(globalObject) {
  "use strict";

  const SPEAKER_COLORS = ["violet", "amber", "coral", "teal"];
  const RECORDING_SOURCES = ["mixed", "microphone", "meeting"];

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

  const DECISION_PATTERNS = [
    /\b(?:decided|agreed|approved|confirmed|selected|chose|chosen|settled|committed)\b/i,
    /\b(?:decision|agreement|approval|consensus)\s+(?:is|was|to)\b/i,
    /\b(?:going with|will use|will proceed|will move forward|are moving forward)\b/i,
  ];
  const PENDING_DECISION_PATTERNS = [
    /\b(?:need|needs|needed|have|has|had)\s+to\s+(?:decide|agree|approve|confirm|choose)\b/i,
    /\b(?:not|never|haven't|hasn't|hadn't|didn't|don't|cannot|can't)\b[^.!?]{0,40}\b(?:decided|agreed|approved|confirmed|chosen)\b/i,
    /\b(?:no decision|decision pending|still undecided)\b/i,
  ];
  const ACTION_PATTERNS = [
    /\b(?:i|we|you|they|he|she|someone|somebody|the team|team)\s+(?:will|shall|must|should|need(?:s)? to|have to|has to|am going to|are going to|is going to)\b/i,
    /\bwe\s+(?:still\s+|also\s+)?need\s+to\b/i,
    /\bwe\s+need\s+(?:someone|somebody)\s+to\b/i,
    /\b(?:i'll|we'll|you'll|they'll)\b/i,
    /\b(?:action item|next step|follow[- ]?up|to[- ]?do)\b/i,
    /\b(?:can|could)\s+you\s+\w+/i,
    /\bplease\s+(?:send|review|prepare|complete|submit|update|create|schedule|confirm|share|follow)\b/i,
    /\b[\p{Lu}][\p{L}'-]+(?:\s+[\p{Lu}][\p{L}'-]+){0,2}\s+(?:will|must|should|needs? to|has to|is going to)\b/u,
  ];

  function splitTranscriptStatements(text) {
    const statements = [];
    for (const line of cleanTranscriptText(text).split(/\n+/)) {
      const matches = line.match(/[^.!?]+(?:[.!?]+|$)/g) || [];
      for (const match of matches) {
        const statement = cleanTranscriptText(match);
        if (statement) statements.push(statement);
      }
    }
    return statements;
  }

  function isNearDuplicateText(first, second) {
    const firstNormalised = normaliseText(first);
    const secondNormalised = normaliseText(second);
    if (!firstNormalised || !secondNormalised) return false;
    if (firstNormalised === secondNormalised) return true;
    const shortestLength = Math.min(
      firstNormalised.length,
      secondNormalised.length,
    );
    if (
      shortestLength >= 24 &&
      (firstNormalised.includes(secondNormalised) ||
        secondNormalised.includes(firstNormalised))
    ) {
      return true;
    }
    return textSimilarity(first, second) >= 0.72;
  }

  function isDecisionStatement(text) {
    return (
      !PENDING_DECISION_PATTERNS.some((pattern) => pattern.test(text)) &&
      DECISION_PATTERNS.some((pattern) => pattern.test(text))
    );
  }

  function isActionStatement(text) {
    return ACTION_PATTERNS.some((pattern) => pattern.test(text));
  }

  function actionOwner(statement, { localOwnerName = "You" } = {}) {
    const text = statement.text;
    const explicitName = text.match(
      /\b([\p{Lu}][\p{L}'-]+(?:\s+[\p{Lu}][\p{L}'-]+){0,2})\s+(?:will|must|should|needs? to|has to|is going to)\b/u,
    );
    if (explicitName) {
      const name = cleanName(explicitName[1], "Unassigned");
      if (!/^(?:i|we|you|they|he|she|team|the team)$/i.test(name)) {
        return name;
      }
    }
    if (/\b(?:someone|somebody|can you|could you|please)\b/i.test(text)) {
      return "Unassigned";
    }
    if (/\b(?:we|we'll|the team|team)\b/i.test(text)) return "Team";
    if (/\b(?:i|i'll)\b/i.test(text)) {
      if (statement.speakerId === "local-user") {
        return cleanName(localOwnerName, "You");
      }
      return cleanName(statement.speaker, "Unassigned");
    }
    return "Unassigned";
  }

  function actionDue(text) {
    const match = text.match(
      /\b(?:(?:by|before|on)\s+)?(?:today|tomorrow|tonight|eod|eow|end of (?:the )?(?:day|week|month)|this (?:week|month)|next (?:week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b/i,
    );
    return match ? match[0] : null;
  }

  function highlightScore(statement) {
    const words = normaliseText(statement.text).split(" ").filter(Boolean);
    let score = Math.min(4, words.length / 8);
    if (isDecisionStatement(statement.text)) score += 9;
    if (isActionStatement(statement.text)) score += 7;
    if (
      /\b(?:because|problem|risk|goal|customer|client|deadline|important|blocked|issue|result|requirement|configuration|ingestion|delivery)\b/i.test(
        statement.text,
      )
    ) {
      score += 3;
    }
    if (/\d/.test(statement.text)) score += 1;
    if (/^(?:yeah|okay|ok|right|well|so|and then|you know|i mean)\b/i.test(statement.text)) {
      score -= 2;
    }
    return score;
  }

  function buildExtractiveBrief(
    segments,
    { localOwnerName = "You" } = {},
  ) {
    const statements = [];
    for (const [segmentIndex, segment] of (
      Array.isArray(segments) ? segments : []
    ).entries()) {
      const segmentStatements = splitTranscriptStatements(segment?.text);
      segmentStatements.forEach((text, statementIndex) => {
        const normalised = normaliseText(text);
        if (!normalised || normalised.split(" ").length < 2) return;
        const candidate = {
          text,
          normalised,
          order: statements.length,
          segmentId: cleanName(segment?.id, `segment-${segmentIndex}`),
          statementIndex,
          startMs: Math.max(0, Number(segment?.startMs) || 0),
          speakerId: cleanName(segment?.speakerId, ""),
          speaker: cleanName(segment?.speaker, "Unknown speaker"),
        };
        const duplicateIndex = statements.findIndex((existing) =>
          isNearDuplicateText(existing.text, candidate.text),
        );
        if (duplicateIndex < 0) {
          statements.push(candidate);
        } else if (
          candidate.normalised.length > statements[duplicateIndex].normalised.length
        ) {
          candidate.order = statements[duplicateIndex].order;
          statements[duplicateIndex] = candidate;
        }
      });
    }
    if (!statements.length) return null;

    const substantive = statements.filter((statement) => {
      const wordCount = statement.normalised.split(" ").length;
      return wordCount >= 4 && statement.normalised.length >= 18;
    });
    const rankedHighlights = [...substantive].sort(
      (first, second) =>
        highlightScore(second) - highlightScore(first) ||
        first.order - second.order,
    );
    const highlights = [];
    for (const statement of rankedHighlights) {
      if (
        highlights.some((existing) =>
          isNearDuplicateText(existing, statement.text),
        )
      ) {
        continue;
      }
      highlights.push(statement.text);
      if (highlights.length === 3) break;
    }
    if (!highlights.length) highlights.push(statements[0].text);

    const decisions = statements
      .filter((statement) => isDecisionStatement(statement.text))
      .slice(0, 6)
      .map((statement) => statement.text);
    const actions = statements
      .filter((statement) => isActionStatement(statement.text))
      .slice(0, 12)
      .map((statement) => ({
        text: statement.text,
        owner: actionOwner(statement, { localOwnerName }),
        due: actionDue(statement.text),
        groundingKey: `${statement.segmentId}:${statement.statementIndex}`,
        sourceSegmentId: statement.segmentId,
        sourceStartMs: statement.startMs,
        sourceSpeakerId: statement.speakerId || null,
      }));

    return {
      overview: highlights.slice(0, 2).join(" "),
      highlights,
      decisions,
      actions,
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
      if (companion.modelsReady !== true) {
        throw new Error(
          "The desktop companion is running, but its offline models are missing. Install the latest model-inclusive Windows release.",
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
      return this.request("/v1/transcriptions", {
        method: "POST",
        body: form,
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
      throw new Error("Transcription timed out");
    }
  }

  globalObject.NotesBuddyMeetingAudio = Object.freeze({
    RECORDING_SOURCES,
    SPEAKER_COLORS,
    CompanionConnector,
    TranscriptionClient,
    applyTranscriptionResult,
    buildExtractiveBrief,
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
    parseTimestamp,
    primaryRecordingSource,
    recordingAsset,
    recordingAssetIds,
    recordingDownloadName,
    renameSpeaker,
    speakerLabel,
    textSimilarity,
  });
})(globalThis);
