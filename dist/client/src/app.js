const app = document.getElementById("root");
const MeetingAudio = globalThis.NotesBuddyMeetingAudio;
const runtimeConfig = globalThis.NotesBuddyRuntime || {};
const APP_VERSION = String(runtimeConfig.appVersion || "2026.08.5");
const SUMMARY_VERSION = 2;
const MEETING_ACTIVITY_THRESHOLD = 0.008;
const MEETING_ACTIVITY_LEAD_MS = 250;
const MEETING_ACTIVITY_HANGOVER_MS = 900;

if (!MeetingAudio) {
  throw new Error("NotesBuddy meeting-audio module failed to load.");
}

const ICONS = {
  mic: '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v3"/><path d="M8 22h8"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  home: '<path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M9 20v-6h6v6"/>',
  library: '<path d="m16 6 4 14"/><path d="M12 6v14"/><path d="M8 8v12"/><path d="M4 4v16"/>',
  settings: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.51a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2Z"/><circle cx="12" cy="12" r="3"/>',
  shield: '<path d="M20 13c0 5-3.5 7.5-8 9-4.5-1.5-8-4-8-9V5l8-3 8 3Z"/><path d="m9 12 2 2 4-4"/>',
  plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  calendar: '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
  chevronRight: '<path d="m9 18 6-6-6-6"/>',
  chevronDown: '<path d="m6 9 6 6 6-6"/>',
  audio: '<path d="M3 10v4"/><path d="M7 6v12"/><path d="M11 3v18"/><path d="M15 7v10"/><path d="M19 9v6"/>',
  checkCircle: '<path d="M22 11.1V12a10 10 0 1 1-5.9-9.1"/><path d="m9 11 3 3L22 4"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  lock: '<rect width="16" height="11" x="4" y="11" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  sparkles: '<path d="m12 3-1.7 4.3L6 9l4.3 1.7L12 15l1.7-4.3L18 9l-4.3-1.7L12 3Z"/><path d="M5 3v4"/><path d="M3 5h4"/><path d="M19 17v4"/><path d="M17 19h4"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  arrowLeft: '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
  more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  pause: '<rect width="4" height="16" x="6" y="4"/><rect width="4" height="16" x="14" y="4"/>',
  play: '<path d="m7 3 14 9-14 9Z"/>',
  square: '<rect width="14" height="14" x="5" y="5" rx="1"/>',
  refresh: '<path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 4v5h5"/><path d="M4 13a8.1 8.1 0 0 0 15.5 2M20 20v-5h-5"/>',
  clipboard: '<rect width="14" height="18" x="5" y="3" rx="2"/><path d="M9 3V2h6v1"/><path d="M9 8h6"/><path d="M9 12h6"/>',
  trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 15H6L5 6"/><path d="M10 11v5"/><path d="M14 11v5"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M8 13h8"/><path d="M8 17h6"/>',
  notebook: '<path d="M2 6h4"/><path d="M2 10h4"/><path d="M2 14h4"/><path d="M2 18h4"/><rect width="16" height="20" x="4" y="2" rx="2"/>',
  copy: '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M16 8V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h4"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  menu: '<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/>',
  headphones: '<path d="M4 14a8 8 0 0 1 16 0"/><path d="M18 19v-5h3v5a2 2 0 0 1-2 2h-1Z"/><path d="M6 19v-5H3v5a2 2 0 0 0 2 2h1Z"/>',
  radio: '<circle cx="12" cy="12" r="2"/><path d="M16.2 7.8a6 6 0 0 1 0 8.4"/><path d="M7.8 16.2a6 6 0 0 1 0-8.4"/><path d="M19.1 4.9a10 10 0 0 1 0 14.2"/><path d="M4.9 19.1a10 10 0 0 1 0-14.2"/>',
};

function icon(name, size = 16, className = "") {
  return `<svg class="${className}" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ICONS.sparkles}</svg>`;
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function loadStored(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) || fallback;
  } catch {
    return fallback;
  }
}

function loadSessionFlag(key) {
  try {
    return sessionStorage.getItem(key) === "true";
  } catch {
    return false;
  }
}

function storeSessionFlag(key, enabled) {
  try {
    if (enabled) {
      sessionStorage.setItem(key, "true");
    } else {
      sessionStorage.removeItem(key);
    }
  } catch {
    // The in-memory state still works when sessionStorage is unavailable.
  }
}

function createId(prefix) {
  const uniquePart =
    globalThis.crypto?.randomUUID?.() ||
    `${Math.random().toString(36).slice(2, 12)}-${Math.random()
      .toString(36)
      .slice(2, 12)}`;
  return `${prefix}-${uniquePart}`;
}

function initialsForName(name) {
  const words = String(name)
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!words.length) return "U";
  const first = words[0][0];
  const last = words.length > 1 ? words.at(-1)[0] : words[0][1] || "";
  return `${first}${last}`.toUpperCase();
}

function normaliseProfile(profile) {
  const name = profile?.name?.trim().replace(/\s+/g, " ");
  if (!name) return null;
  return {
    id: profile.id || createId("profile"),
    name,
    initials: initialsForName(name),
    createdAt: profile.createdAt || new Date().toISOString(),
    updatedAt: profile.updatedAt || new Date().toISOString(),
  };
}

function normaliseInsightText(value) {
  return MeetingAudio.cleanTranscriptText(value)
    .toLocaleLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function applyTranscriptBriefToMeeting(meeting, brief) {
  if (!meeting || !brief) return false;
  const previousActions = new Map(
    (Array.isArray(meeting.actions) ? meeting.actions : []).map((action) => [
      normaliseInsightText(action.text),
      action,
    ]),
  );
  meeting.overview = brief.overview;
  meeting.highlights = [...brief.highlights];
  meeting.decisions = [...brief.decisions];
  meeting.actions = brief.actions.map((action, index) => {
    const previous = previousActions.get(normaliseInsightText(action.text));
    const stableKey = String(
      action.groundingKey || `${action.sourceSegmentId || "segment"}-${index}`,
    ).replace(/[^a-z0-9_-]+/gi, "-");
    return {
      id: `${meeting.id}-transcript-action-${stableKey}`,
      text: action.text,
      owner: action.owner,
      due: action.due || null,
      done: Boolean(previous?.done),
      grounded: true,
      sourceSegmentId: action.sourceSegmentId || null,
      sourceStartMs: Number(action.sourceStartMs) || 0,
      sourceSpeakerId: action.sourceSpeakerId || null,
    };
  });
  meeting.summaryVersion = SUMMARY_VERSION;
  meeting.summaryGeneratedAt = new Date().toISOString();
  return true;
}

function migrateMeetingInsights(meeting, profile, { enabled = true } = {}) {
  if (!meeting || meeting.summaryVersion === SUMMARY_VERSION) return false;
  const brief = enabled
    ? MeetingAudio.buildExtractiveBrief(meeting.transcript, {
        localOwnerName: profile?.name || "You",
      })
    : null;
  if (brief) {
    applyTranscriptBriefToMeeting(meeting, brief);
  } else {
    meeting.highlights = [];
    meeting.decisions = [];
    meeting.actions = [];
    meeting.summaryVersion = SUMMARY_VERSION;
  }
  return true;
}

const LEGACY_SEED_MEETING_IDS = new Set([
  "product-weekly-0729",
  "customer-discovery-0728",
  "design-critique-0727",
  "sprint-planning-0725",
]);
const storedSettings = loadStored("notesbuddy-settings", {});
const storedMeetings = loadStored("notesbuddy-meetings", []);
let initialMeetings = Array.isArray(storedMeetings)
  ? storedMeetings.filter((meeting) => !LEGACY_SEED_MEETING_IDS.has(meeting.id))
  : [];
const initialProfile = normaliseProfile(
  loadStored("notesbuddy-profile", null),
);
let meetingInsightsMigrated = false;
initialMeetings = initialMeetings.map((meeting) => {
  const normalizedMeeting = MeetingAudio.ensureMeetingSpeakers(
    meeting,
    initialProfile,
  );
  meetingInsightsMigrated =
    migrateMeetingInsights(normalizedMeeting, initialProfile, {
      enabled: storedSettings.autoSummarize !== false,
    }) ||
    meetingInsightsMigrated;
  return normalizedMeeting;
});

const runtimeTranscriptionMode = ["hosted", "hybrid"].includes(
  runtimeConfig.transcriptionMode,
)
  ? runtimeConfig.transcriptionMode
  : "local";
const runtimeLocalCompanionEndpoint = String(
  runtimeConfig.localCompanionEndpoint ||
    (runtimeTranscriptionMode === "local"
      ? runtimeConfig.transcriptionEndpoint
      : "") ||
    "http://127.0.0.1:8765",
).replace(/\/+$/, "");
const runtimeHostedTranscriptionEndpoint = String(
  runtimeTranscriptionMode === "local"
    ? ""
    : runtimeConfig.transcriptionEndpoint || "",
).replace(/\/+$/, "");
const runtimeTranscriptionEndpoint =
  runtimeTranscriptionMode === "local"
    ? runtimeLocalCompanionEndpoint
    : runtimeHostedTranscriptionEndpoint;
const latestCompanionVersion = String(
  runtimeConfig.latestCompanionVersion || APP_VERSION,
);
const companionDownloadUrl = String(
  runtimeConfig.companionDownloadUrl ||
    `https://github.com/sumarahmed/AINotesBuddy/releases/download/companion-v${latestCompanionVersion}/NotesBuddyCompanion-Setup-${latestCompanionVersion}.exe`,
);
const companionSetupSessionKey = "notesbuddy-companion-setup-deferred";
const defaultSettings = {
  autoSummarize: true,
  keepAudio: true,
  systemAudio: true,
  browserTranscription: true,
  autoTranscribe: false,
  transcriptionMode:
    runtimeTranscriptionMode === "hybrid"
      ? "hosted"
      : runtimeTranscriptionMode,
  transcriptionEndpoint: runtimeTranscriptionEndpoint,
  transcriptionToken: "",
  companionSetupCompleted: false,
};
const initialSettings = {
  ...defaultSettings,
  ...storedSettings,
  transcriptionMode:
    runtimeTranscriptionMode === "hybrid"
      ? "hosted"
      : runtimeTranscriptionMode,
  transcriptionEndpoint:
    runtimeTranscriptionMode === "hosted" ||
    runtimeTranscriptionMode === "hybrid"
      ? runtimeTranscriptionEndpoint
      : storedSettings.transcriptionEndpoint ||
        defaultSettings.transcriptionEndpoint,
  transcriptionToken:
    runtimeTranscriptionMode === "hosted" ||
    runtimeTranscriptionMode === "hybrid"
      ? ""
      : storedSettings.transcriptionToken || "",
};

const state = {
  meetings: initialMeetings,
  profile: initialProfile,
  profileOnboardingOpen: !initialProfile,
  settings: initialSettings,
  view: "home",
  selectedMeetingId: initialMeetings[0]?.id || null,
  tab: "summary",
  search: "",
  settingsOpen: false,
  mobileNavOpen: false,
  moreOpen: false,
  showAllMeetings: false,
  transcriptionServiceStatus: "unknown",
  companionSetupOpen:
    runtimeTranscriptionMode === "hybrid" &&
    !initialSettings.companionSetupCompleted &&
    !loadSessionFlag(companionSetupSessionKey),
  preferHostedForSession: loadSessionFlag(companionSetupSessionKey),
  companion: {
    status: runtimeTranscriptionMode === "hybrid" ? "checking" : "disabled",
    pairingToken: "",
    metadata: null,
    error: null,
  },
  companionUpdateDismissed: false,
  playbackSourceByMeeting: {},
  toasts: [],
  capture: {
    title: "Untitled meeting",
    status: "idle",
    elapsed: 0,
    segments: [],
    interimTranscript: "",
    interimSpeakerId: null,
    transcriptionStatus: "idle",
    microphoneOn: true,
    systemAudioOn: true,
    permission: "prompt",
    sourceStatus: {
      microphone: "idle",
      meeting: "idle",
      mixed: "idle",
    },
    meetingDisplaySurface: null,
    meetingCaptureMode: null,
    meetingDeviceName: null,
    meetingAudioEnded: false,
    meetingAudioSignalDetected: false,
    meetingAudioCurrentlyActive: false,
    meetingAudioWarning: "",
    captureStartedAt: null,
  },
};

let captureTimer;
let captureRuntime = createEmptyCaptureRuntime();
let speechRecognition;
let activeAudioUrl;
let toastId = 0;
let companionConnectionPromise;
const transcriptionControllers = new Map();

function createEmptyCaptureRuntime() {
  return {
    streams: {
      microphone: null,
      display: null,
      meeting: null,
      mixed: null,
    },
    recorders: {},
    chunks: {
      microphone: [],
      meeting: [],
      mixed: [],
    },
    audioContext: null,
    audioNodes: [],
    meetingSignalMonitor: null,
    companionStatusTimer: null,
    companionCaptureId: null,
    companionCaptureClient: null,
    captureStartedAt: null,
    captureStartedAtMonotonic: null,
    totalPausedMs: 0,
    pausedAtMonotonic: null,
    meetingActivitySpans: [],
    meetingActivityLastDetectedAtMs: null,
  };
}

function save() {
  localStorage.setItem("notesbuddy-meetings", JSON.stringify(state.meetings));
  const settingsToStore =
    runtimeTranscriptionMode === "hybrid"
      ? {
          ...state.settings,
          transcriptionMode: "hosted",
          transcriptionEndpoint: runtimeHostedTranscriptionEndpoint,
          transcriptionToken: "",
        }
      : state.settings;
  localStorage.setItem(
    "notesbuddy-settings",
    JSON.stringify(settingsToStore),
  );
  if (state.profile) {
    localStorage.setItem("notesbuddy-profile", JSON.stringify(state.profile));
  }
}

if (
  storedMeetings.length !== initialMeetings.length ||
  meetingInsightsMigrated
) {
  localStorage.setItem("notesbuddy-meetings", JSON.stringify(initialMeetings));
}

function openAudioDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("notesbuddy-audio", 1);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains("recordings")) {
        database.createObjectStore("recordings");
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function storeAudio(id, blob) {
  const database = await openAudioDatabase();
  await new Promise((resolve, reject) => {
    const transaction = database.transaction("recordings", "readwrite");
    transaction.objectStore("recordings").put(blob, id);
    transaction.oncomplete = resolve;
    transaction.onerror = () => reject(transaction.error);
  });
  database.close();
}

async function getAudio(id) {
  const database = await openAudioDatabase();
  const blob = await new Promise((resolve, reject) => {
    const transaction = database.transaction("recordings", "readonly");
    const request = transaction.objectStore("recordings").get(id);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  database.close();
  return blob;
}

async function deleteAudio(id) {
  if (!id) return;
  const database = await openAudioDatabase();
  await new Promise((resolve, reject) => {
    const transaction = database.transaction("recordings", "readwrite");
    transaction.objectStore("recordings").delete(id);
    transaction.oncomplete = resolve;
    transaction.onerror = () => reject(transaction.error);
  });
  database.close();
}

async function deleteMeetingAudio(meeting) {
  await Promise.allSettled(
    MeetingAudio.recordingAssetIds(meeting).map((id) => deleteAudio(id)),
  );
}

function formatTimer(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function durationLabel(totalSeconds) {
  const seconds = Math.max(0, Number(totalSeconds) || 0);
  if (seconds < 60) return `${Math.max(1, Math.round(seconds))} sec`;
  if (seconds < 3600) return `${Math.ceil(seconds / 60)} min`;
  return `${(seconds / 3600).toFixed(1)} hrs`;
}

function meetingDurationSeconds(meeting) {
  if (Number.isFinite(meeting.durationSeconds)) {
    return Math.max(0, meeting.durationSeconds);
  }
  const match = String(meeting.duration || "").match(
    /^([\d.]+)\s*(sec|min|hr)/i,
  );
  if (!match) return 0;
  const multiplier = {
    sec: 1,
    min: 60,
    hr: 3600,
  }[match[2].toLowerCase()];
  return Number(match[1]) * multiplier;
}

function currentUserName() {
  return state.profile?.name || "You";
}

function currentUserInitials() {
  return state.profile?.initials || "U";
}

function currentUserFirstName() {
  return currentUserName().split(/\s+/)[0];
}

function usesHostedTranscription() {
  return state.settings.transcriptionMode === "hosted";
}

function usesHybridTranscription() {
  return runtimeTranscriptionMode === "hybrid";
}

function companionSystemAudioAvailable() {
  return Boolean(
    usesHybridTranscription() &&
      !usesHostedTranscription() &&
      state.companion.status === "connected" &&
      state.companion.pairingToken &&
      state.companion.metadata?.systemAudioCapture === true,
  );
}

function companionUpdateRequired() {
  return Boolean(
    state.companion.status === "connected" &&
      state.companion.metadata?.version &&
      MeetingAudio.isVersionOutdated(
        state.companion.metadata.version,
        latestCompanionVersion,
      ),
  );
}

function greetingForTime(date = new Date()) {
  const hour = date.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function homeDateLabel(date = new Date()) {
  return new Intl.DateTimeFormat("en-AU", {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(date);
}

function captureDateLabel(date = new Date()) {
  return new Intl.DateTimeFormat("en-AU", {
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(date);
}

function selectedPlaybackSource(meeting) {
  return MeetingAudio.primaryRecordingSource(
    meeting,
    state.playbackSourceByMeeting[meeting.id],
  );
}

function recordingDownloadName(
  meeting,
  source = selectedPlaybackSource(meeting),
) {
  return MeetingAudio.recordingDownloadName(meeting, source || "mixed");
}

function meetingDate(iso) {
  const date = new Date(iso);
  const today = new Date();
  const todayValue = Date.UTC(
    today.getFullYear(),
    today.getMonth(),
    today.getDate(),
  );
  const dateValue = Date.UTC(
    date.getFullYear(),
    date.getMonth(),
    date.getDate(),
  );
  const diff = Math.round((todayValue - dateValue) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "short",
  }).format(date);
}

function longDate(iso) {
  return new Intl.DateTimeFormat("en-AU", {
    weekday: "long",
    day: "numeric",
    month: "long",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

function brand(compact = false) {
  return `<div class="brand ${compact ? "brand--compact" : ""}">
    <div class="brand__mark" aria-hidden="true"><span></span><span></span><span></span></div>
    ${compact ? "" : '<span class="brand__word">NotesBuddy</span>'}
  </div>`;
}

function avatar(initials, color, small = false) {
  return `<span class="avatar avatar--${color} ${small ? "avatar--small" : ""}" aria-hidden="true">${escapeHtml(initials)}</span>`;
}

function waveform(active, dense = false) {
  return `<div class="waveform ${active ? "waveform--active" : ""} ${dense ? "waveform--dense" : ""}" aria-hidden="true">
    ${Array.from({ length: dense ? 64 : 28 }, (_, index) => `<span style="--wave-height:${18 + ((index * 17) % 60)}%;--wave-delay:${(index % 11) * -0.08}s"></span>`).join("")}
  </div>`;
}

function iconButton(action, label, iconName) {
  return `<button type="button" class="icon-button" data-action="${action}" aria-label="${escapeHtml(label)}" title="${escapeHtml(label)}">${icon(iconName, 18)}</button>`;
}

function filteredMeetings() {
  const query = state.search.trim().toLowerCase();
  if (!query) return state.meetings;
  return state.meetings.filter((meeting) =>
    [
      meeting.title,
      meeting.overview,
      meeting.tags.join(" "),
      meeting.transcript.map((segment) => segment.text).join(" "),
      (meeting.speakers || [])
        .map((speaker) =>
          speaker.id === "local-user"
            ? `You ${currentUserName()}`
            : speaker.displayName,
        )
        .join(" "),
    ]
      .join(" ")
      .toLowerCase()
      .includes(query),
  );
}

function sidebar(meetings) {
  return `<aside class="sidebar">
    <div class="sidebar__top">
      ${brand()}
      <button type="button" class="icon-button mobile-only" data-action="close-nav" aria-label="Close navigation">${icon("x", 18)}</button>
    </div>
    <button type="button" class="new-meeting-button" data-action="capture">
      <span class="new-meeting-button__icon">${icon("mic", 17)}</span>
      <span>New capture</span><kbd>N</kbd>
    </button>
    <nav class="primary-nav" aria-label="Primary">
      <button type="button" data-action="home">${icon("home", 17)} Home</button>
      <button type="button" data-action="home">${icon("library", 17)} All meetings <span class="nav-count">${state.meetings.length}</span></button>
    </nav>
    <div class="sidebar-search">
      ${icon("search", 15)}
      <input data-input="search" value="${escapeHtml(state.search)}" placeholder="Search meetings" aria-label="Search meetings">
      <kbd>⌘K</kbd>
    </div>
    <div class="sidebar__section-heading"><span>Recent</span>${icon("chevronDown", 14)}</div>
    <div class="meeting-nav">
      ${meetings
        .slice(0, 7)
        .map(
          (meeting) => `<button type="button" data-action="meeting" data-id="${meeting.id}" class="${state.selectedMeetingId === meeting.id ? "meeting-nav__item--active" : ""}">
            <span class="meeting-nav__date">${meetingDate(meeting.dateISO)}</span>
            <span class="meeting-nav__title">${escapeHtml(meeting.title)}</span>
          </button>`,
        )
        .join("")}
      ${
        meetings.length
          ? ""
          : `<p class="meeting-nav__empty">${
              state.search.trim()
                ? "No meetings match your search."
                : "No meetings yet."
            }</p>`
      }
    </div>
    <div class="sidebar__footer">
      <div class="local-status">
        <div class="local-status__icon">${icon("shield", 16)}</div>
        <div><strong>Private workspace</strong><span>Saved on this device</span></div>
        <span class="status-dot"></span>
      </div>
      <span class="app-version">Version ${escapeHtml(APP_VERSION)}</span>
      <button type="button" class="settings-link" data-action="settings">${icon("settings", 17)} Settings</button>
    </div>
  </aside>`;
}

function homeView(meetings) {
  const totalDurationSeconds = meetings.reduce(
    (total, meeting) => total + meetingDurationSeconds(meeting),
    0,
  );
  const openActions = meetings.reduce(
    (total, meeting) =>
      total + meeting.actions.filter((action) => !action.done).length,
    0,
  );
  return `<main class="main-view home-view">
    <header class="view-header home-header">
      <div><span class="eyebrow">${escapeHtml(homeDateLabel())}</span><h1>${escapeHtml(greetingForTime())}, ${escapeHtml(currentUserFirstName())}.</h1><p>Your conversations are ready when you are.</p></div>
      <div class="header-actions">
        <button type="button" class="button button--quiet" data-action="import">${icon("upload", 16)} Import audio</button>
        <button type="button" class="button button--primary" data-action="capture">${icon("mic", 16)} Start capture</button>
      </div>
    </header>
    <section class="hero-grid">
      <article class="capture-card">
        <div class="capture-card__glow"></div>
        <div class="capture-card__content">
          <div class="capture-card__kicker"><span class="pulse-ring">${icon("mic", 17)}</span><span>Ready to listen</span></div>
          <h2>Turn the next conversation into clear, useful memory.</h2>
          <p>Record real microphone audio, keep it on this device, and review browser-recognised speech when available.</p>
          <button type="button" data-action="capture">Start a new capture ${icon("chevronRight", 17)}</button>
        </div>
        <div class="capture-card__visual" aria-hidden="true">
          <div class="orbit orbit--one"></div><div class="orbit orbit--two"></div>
          <div class="capture-orb">${icon("audio", 32)}</div>
        </div>
      </article>
      <article class="upcoming-card workspace-card">
        <div class="workspace-card__icon">${icon("shield", 23)}</div>
        <span class="eyebrow">This browser profile</span>
        <h3>Private meeting memory for ${escapeHtml(currentUserFirstName())}</h3>
        <p>There is no shared calendar or server account connected. Recordings and meeting records stay in this browser unless you export them.</p>
        <div class="workspace-card__status">${icon("checkCircle", 15)}Profile saved locally</div>
        <button type="button" class="upcoming-action" data-action="capture">${icon("radio", 15)} Start a private capture</button>
      </article>
    </section>
    <section class="insight-strip">
      <div><span class="insight-strip__icon insight-strip__icon--teal">${icon("notebook", 17)}</span><div><strong>${meetings.length}</strong><span>meetings in memory</span></div></div>
      <div><span class="insight-strip__icon insight-strip__icon--amber">${icon("clock", 17)}</span><div><strong>${totalDurationSeconds ? durationLabel(totalDurationSeconds) : "0 min"}</strong><span>conversation captured</span></div></div>
      <div><span class="insight-strip__icon insight-strip__icon--coral">${icon("checkCircle", 17)}</span><div><strong>${openActions}</strong><span>open action items</span></div></div>
      <div class="insight-strip__privacy">${icon("lock", 15)}<span>Recordings stay on this device</span></div>
    </section>
    <section class="recent-section">
      <div class="section-title-row"><div><span class="eyebrow">Your memory</span><h2>${state.showAllMeetings ? "All meetings" : "Recent meetings"}</h2></div>${state.meetings.length > 4 ? `<button type="button" class="text-button" data-action="view-all">${state.showAllMeetings ? "Show recent" : "View all"} ${icon("chevronRight", 15)}</button>` : ""}</div>
      <div class="meeting-cards">
        ${
          meetings.length
            ? meetings
                .slice(0, state.showAllMeetings ? meetings.length : 4)
                .map(
                  (meeting) => `<button type="button" class="meeting-card" data-action="meeting" data-id="${meeting.id}">
                    <div class="meeting-card__top"><span>${meetingDate(meeting.dateISO)}</span><span class="meeting-card__duration">${icon("audio", 13)}${escapeHtml(meeting.duration)}</span></div>
                    <h3>${escapeHtml(meeting.title)}</h3><p>${escapeHtml(meeting.overview)}</p>
                    <div class="meeting-card__footer">
                      <div class="avatar-stack">${meeting.participants.slice(0, 3).map((person) => avatar(person.initials, person.color, true)).join("")}</div>
                      <div class="meeting-card__tags">${meeting.tags.slice(0, 2).map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div>
                    </div>
                  </button>`,
                )
                .join("")
            : `<div class="meeting-cards__empty">${icon(state.search ? "search" : "notebook", 24)}<div><h3>${state.search ? "No matching meetings" : "Your workspace is ready"}</h3><p>${state.search ? "Try a different title, topic, or transcript phrase." : "Your real recordings, transcripts, and notes will appear here."}</p></div>${state.search ? "" : `<button type="button" class="button button--primary" data-action="capture">${icon("mic", 15)} Record your first meeting</button>`}</div>`
        }
      </div>
    </section>
  </main>`;
}

function captureView() {
  const capture = state.capture;
  const companionAudio = companionSystemAudioAvailable();
  const meetingCaptureSupported = Boolean(
    companionAudio || navigator.mediaDevices?.getDisplayMedia,
  );
  const meetingOptionDescription = !meetingCaptureSupported
    ? "Capture unavailable"
    : !capture.systemAudioOn
      ? "Not recorded"
      : companionAudio
        ? "Windows output via companion"
        : "Choose a tab, window, or screen";
  const meetingSourceLabel =
    capture.meetingCaptureMode === "companion" ? "Windows output" : "Meeting";
  const statusLabel = {
    idle: "Ready",
    "requesting-microphone": "Requesting microphone",
    "requesting-meeting-audio": "Requesting meeting audio",
    ready: "Starting",
    recording: "Recording",
    paused: "Paused",
    processing: "Finishing locally",
    failed: "Needs attention",
  }[capture.status];
  const idle = capture.status === "idle";
  return `<main class="main-view capture-view">
    <header class="capture-header">
      <button type="button" class="back-button" data-action="cancel-capture">${icon("arrowLeft", 17)} Back</button>
      <div class="capture-header__privacy">${icon("shield", 15)} Local audio <span>·</span> ${state.settings.browserTranscription ? "Browser speech" : "Audio only"}</div>
      ${iconButton("settings", "Open capture settings", "more")}
    </header>
    <section class="capture-workspace">
      <div class="capture-title-block">
        <span class="recording-status recording-status--${capture.status}"><i></i>${statusLabel}</span>
        <input class="capture-title-input" data-input="capture-title" value="${escapeHtml(capture.title)}" aria-label="Meeting title">
        <div class="capture-meta">${icon("calendar", 14)} ${escapeHtml(captureDateLabel())} <span>·</span>${icon("clock", 14)}<strong data-capture-clock>${formatTimer(capture.elapsed)}</strong></div>
      </div>
      ${
        idle
          ? `<div class="capture-ready">
              <div class="capture-ready__visual"><div class="ready-ring ready-ring--outer"></div><div class="ready-ring ready-ring--inner"></div><div class="ready-mic">${icon("mic", 34)}</div></div>
              <h2>Ready for your next conversation</h2>
              <p>Keep microphone and meeting audio as synchronized tracks. Companion capture defaults playback to Windows output; browser capture also creates a mixed track.</p>
              <div class="source-options">
                <button type="button" data-action="toggle-mic" class="${capture.microphoneOn ? "source-option--active" : ""}">
                  <span>${icon("mic", 17)}</span><div><strong>My microphone</strong><small>${capture.microphoneOn ? "Saved as You" : "Not recorded"}</small></div><i>${capture.microphoneOn ? icon("check", 13) : ""}</i>
                </button>
                <button type="button" data-action="toggle-system" class="${capture.systemAudioOn && meetingCaptureSupported ? "source-option--active" : ""}" ${meetingCaptureSupported ? "" : 'disabled title="Meeting audio sharing is unavailable in this browser"'}>
                  <span>${icon("headphones", 17)}</span><div><strong>Meeting audio</strong><small>${escapeHtml(meetingOptionDescription)}</small></div><i>${capture.systemAudioOn && meetingCaptureSupported ? icon("check", 13) : ""}</i>
                </button>
              </div>
              <button type="button" class="start-recording" data-action="start-capture"><span>${icon("mic", 20)}</span>Start capture</button>
              <div class="prototype-note">${icon("shield", 14)}${companionAudio ? `Companion ${escapeHtml(state.companion.metadata?.version || "")} will capture the default Windows output directly. Keep the Teams speaker and Windows default output set to the same device. No screen-sharing dialog is required.` : state.companion.status === "connected" ? `Update the Windows companion to <strong>${escapeHtml(APP_VERSION)}</strong> for direct Teams desktop audio. Until then, share <strong>Entire Screen</strong> and enable <strong>Also share system audio</strong>.` : `For Teams on the web, share the <strong>Teams tab</strong> and enable <strong>Also share tab audio</strong>. For Teams desktop, install companion ${escapeHtml(APP_VERSION)} for reliable Windows audio, or share <strong>Entire Screen</strong> with system audio.`}</div>
            </div>`
          : `<div class="live-workspace">
              <div class="live-meter">
                <div class="live-meter__top"><div><span class="live-pill"><i></i>Live</span><span>${capture.permission === "granted" ? "Synchronized local recording" : "Capture starting"}</span></div><strong data-capture-clock>${formatTimer(capture.elapsed)}</strong></div>
                ${waveform(capture.status === "recording", true)}
                <div class="capture-source-live">
                  <span class="capture-source-live__item capture-source-live__item--${capture.sourceStatus.microphone}" data-source-status="microphone">${icon("mic", 13)}Microphone <b>${escapeHtml(captureSourceStatusLabel(capture.sourceStatus.microphone))}</b></span>
                  <span class="capture-source-live__item capture-source-live__item--${capture.sourceStatus.meeting}" data-source-status="meeting">${icon("headphones", 13)}${escapeHtml(meetingSourceLabel)} <b>${escapeHtml(captureSourceStatusLabel(capture.sourceStatus.meeting))}</b></span>
                  <span class="capture-source-live__item capture-source-live__item--${capture.sourceStatus.mixed}" data-source-status="mixed">${icon("audio", 13)}${capture.meetingCaptureMode === "companion" ? "Tracks" : "Mixed"} <b>${escapeHtml(captureSourceStatusLabel(capture.sourceStatus.mixed))}</b></span>
                </div>
                ${capture.meetingCaptureMode === "companion" && capture.meetingDeviceName ? `<div class="capture-device-name">${icon("headphones", 12)}Listening to ${escapeHtml(capture.meetingDeviceName)}</div>` : ""}
                ${capture.meetingAudioEnded ? `<div class="capture-source-warning" data-meeting-audio-warning="ended">${icon("headphones", 14)}Meeting audio sharing stopped. Microphone recording is continuing.</div>` : capture.meetingAudioWarning ? `<div class="capture-source-warning" data-meeting-audio-warning="signal">${icon("headphones", 14)}${escapeHtml(capture.meetingAudioWarning)}</div>` : ""}
              </div>
              <div class="live-transcript">
                <div class="live-transcript__heading"><div><span class="eyebrow">Live transcript</span><h2>Conversation</h2></div><span class="confidence-pill"><span></span><b data-transcription-label>${capture.transcriptionStatus === "listening" ? capture.systemAudioOn ? "You + Guest draft" : "Browser speech" : "Audio recording"}</b></span></div>
                <div class="live-transcript__scroll" data-live-transcript>${liveTranscriptMarkup(capture)}</div>
              </div>
            </div>`
      }
    </section>
    ${
      capture.status === "recording" || capture.status === "paused"
        ? `<div class="recording-dock">
            <button type="button" class="dock-secondary" data-action="pause-capture">${capture.status === "recording" ? icon("pause", 18) + "Pause" : icon("play", 18) + "Resume"}</button>
            <div class="dock-wave">${waveform(capture.status === "recording")}</div>
            <button type="button" class="dock-finish" data-action="finish-capture">${icon("square", 15)}Finish</button>
          </div>`
        : ""
    }
    ${
      capture.status === "processing"
        ? `<div class="processing-overlay"><div class="processing-card"><div class="processing-orb">${icon("audio", 24)}</div><h2>Saving your recording</h2><p>Storing the real audio and available transcript on this device.</p><div class="processing-bar"><span></span></div></div></div>`
        : ""
    }
  </main>`;
}

function liveDraftSpeaker(speakerId) {
  return speakerId === "remote-guest"
    ? { name: "Guest", initials: "G", color: "violet", provisional: true }
    : {
        name: "You",
        initials: currentUserInitials(),
        color: "teal",
        provisional: false,
      };
}

function liveTranscriptMarkup(capture) {
  const interimSpeaker = liveDraftSpeaker(capture.interimSpeakerId);
  const waitingForGuestWords =
    capture.meetingAudioCurrentlyActive && !capture.interimTranscript;
  return `${capture.segments.map(transcriptRow).join("")}
    ${capture.interimTranscript ? `<div class="interim-transcript">${avatar(interimSpeaker.initials, interimSpeaker.color)}<div><div class="interim-transcript__speaker"><strong>${interimSpeaker.name}</strong>${interimSpeaker.provisional ? "<span>draft</span>" : ""}</div><p>${escapeHtml(capture.interimTranscript)}</p></div></div>` : ""}
    ${waitingForGuestWords ? `<div class="guest-speaking-state">${icon("audio", 18)}<span><strong>Guest speaking</strong><small>Matching meeting audio with incoming words…</small></span></div>` : ""}
    ${capture.segments.length || capture.interimTranscript || waitingForGuestWords ? "" : `<div class="listening-state">${icon("audio", 20)}${capture.transcriptionStatus === "listening" ? capture.systemAudioOn ? "Listening for you and meeting guests…" : "Listening for your voice…" : "Recording audio — live speech text is unavailable in this browser."}</div>`}`;
}

function updateCaptureRuntimeUI({ transcript = false } = {}) {
  if (state.view !== "capture") return;
  app.querySelectorAll("[data-capture-clock]").forEach((element) => {
    element.textContent = formatTimer(state.capture.elapsed);
  });
  const transcriptionLabel = app.querySelector("[data-transcription-label]");
  if (transcriptionLabel) {
    transcriptionLabel.textContent =
      state.capture.transcriptionStatus === "listening"
        ? state.capture.systemAudioOn
          ? "You + Guest draft"
          : "Browser speech"
        : "Audio recording";
  }
  if (transcript) {
    const container = app.querySelector("[data-live-transcript]");
    if (container) {
      container.innerHTML = liveTranscriptMarkup(state.capture);
      container.scrollTop = container.scrollHeight;
    }
  }
}

function transcriptRow(
  segment,
  documentMode = false,
  hasRecording = false,
  meeting = null,
) {
  const timestamp = escapeHtml(segment.timestamp);
  const speakerName = meeting
    ? MeetingAudio.speakerLabel(
        meeting,
        segment.speakerId,
        segment.speaker || "Unknown speaker",
      )
    : segment.speaker || "Unknown speaker";
  const timestampControl =
    documentMode && hasRecording
      ? `<button type="button" data-action="seek-recording-time" data-time="${timestamp}" aria-label="Seek recording to ${timestamp}">${timestamp}</button>`
      : `<span>${timestamp}</span>`;
  const canRenameFromLabel =
    documentMode &&
    meeting &&
    segment.speakerId &&
    segment.speakerId !== "local-user";
  const speakerControl = canRenameFromLabel
    ? `<button type="button" class="transcript-speaker-button" data-action="focus-speaker" data-id="${escapeHtml(segment.speakerId)}" data-speaker-label-id="${escapeHtml(segment.speakerId)}" aria-label="Rename ${escapeHtml(speakerName)}">${escapeHtml(speakerName)}</button>`
    : `<strong data-speaker-label-id="${escapeHtml(segment.speakerId || "")}">${escapeHtml(speakerName)}</strong>`;
  const provisionalLabel = segment.provisional
    ? '<span class="provisional-speaker-badge">draft</span>'
    : "";
  return `<div class="transcript-row ${documentMode ? "transcript-row--document" : ""}">
    ${avatar(segment.initials, segment.color)}
    <div><div class="transcript-row__meta">${speakerControl}${provisionalLabel}${timestampControl}</div><p>${escapeHtml(segment.text)}</p></div>
  </div>`;
}

function summaryView(meeting) {
  const highlights = Array.isArray(meeting.highlights)
    ? meeting.highlights
    : [];
  const decisions = Array.isArray(meeting.decisions) ? meeting.decisions : [];
  const actions = Array.isArray(meeting.actions) ? meeting.actions : [];
  return `<div class="summary-layout">
    <div class="summary-main">
      <section class="summary-lead">
        <div class="summary-lead__heading"><div><span class="eyebrow">Meeting brief</span><h2>The short version</h2></div><button type="button" class="text-button" data-action="regenerate">${icon("refresh", 14)}Refresh from transcript</button></div>
        <p>${escapeHtml(meeting.overview)}</p>
      </section>
      <section class="summary-section">
        <div class="summary-section__heading"><span class="section-icon section-icon--teal">${icon("sparkles", 17)}</span><div><span class="eyebrow">What mattered</span><h2>Key highlights</h2></div></div>
        <div class="highlight-grid">${highlights.length ? highlights.map((item, index) => `<article><span>${String(index + 1).padStart(2, "0")}</span><p>${escapeHtml(item)}</p></article>`).join("") : `<div class="insight-empty">No transcript-grounded highlights are available yet.</div>`}</div>
      </section>
      <section class="summary-section">
        <div class="summary-section__heading"><span class="section-icon section-icon--violet">${icon("clipboard", 17)}</span><div><span class="eyebrow">Locked in</span><h2>Decisions</h2></div></div>
        <div class="decision-list">${decisions.length ? decisions.map((item) => `<div>${icon("check", 15)}<span>${escapeHtml(item)}</span></div>`).join("") : `<div>${icon("check", 15)}<span>No transcript sentence explicitly stated a decision.</span></div>`}</div>
      </section>
      <section class="summary-section">
        <div class="summary-section__heading action-heading"><span class="section-icon section-icon--coral">${icon("checkCircle", 17)}</span><div><span class="eyebrow">Keep moving</span><h2>Action items</h2></div><span class="item-count">${actions.filter((action) => !action.done).length} open</span></div>
        <div class="action-list">${actions.length ? actions.map((action) => `<button type="button" data-action="toggle-action" data-id="${action.id}" class="${action.done ? "action-item--done" : ""}"><span class="action-check">${action.done ? icon("check", 13) : ""}</span><span class="action-text">${escapeHtml(action.text)}</span><span class="action-owner">${escapeHtml(action.owner)}</span>${action.due ? `<span class="action-due">${escapeHtml(action.due)}</span>` : ""}</button>`).join("") : `<div class="insight-empty">No transcript-grounded action items were identified.</div>`}</div>
      </section>
    </div>
    <aside class="meeting-context">
      <section><span class="eyebrow">People</span><h3>In this conversation</h3><div class="people-list">${meeting.participants.map((person) => `<div>${avatar(person.initials, person.color, true)}<span>${escapeHtml(person.name)}</span></div>`).join("")}</div></section>
      <section><span class="eyebrow">Topics</span><div class="context-tags">${meeting.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div></section>
      <section class="privacy-context"><div>${icon("lock", 15)}<strong>Stored locally</strong></div><p>The recording and meeting record are stored on this device.</p></section>
    </aside>
  </div>`;
}

function transcriptionWorkspace(meeting) {
  const status = meeting.transcription?.status || "not-requested";
  const statusLabel = {
    "not-requested": "Not transcribed",
    draft: "Browser draft only",
    queued: "Queued",
    processing: "Identifying speakers",
    completed: "Speaker transcript ready",
    failed: "Transcription failed",
    cancelled: "Transcription cancelled",
  }[status] || status;
  const isRunning = status === "queued" || status === "processing";
  const hasRecording = Boolean(MeetingAudio.recordingAsset(meeting));
  const buttonLabel =
    status === "completed"
      ? "Re-transcribe speakers"
      : status === "failed"
        ? "Retry speaker transcription"
        : "Transcribe and identify speakers";
  const serviceDescription = usesHostedTranscription()
    ? "Audio is sent to the public transcription service for this job and removed from its temporary storage after processing."
    : "Uses the paired local companion. Audio is processed on this computer and temporary service files are removed.";
  const failureDescription = usesHostedTranscription()
    ? "The public transcription service could not complete this job."
    : "The local companion could not complete this job.";
  return `<section class="transcription-workspace transcription-workspace--${escapeHtml(status)}">
    <div>
      <span class="eyebrow">Speaker transcription</span>
      <h3>${escapeHtml(statusLabel)}</h3>
      <p>${status === "completed" ? `${meeting.transcript.length} timestamped segment${meeting.transcript.length === 1 ? "" : "s"} · ${(meeting.speakers || []).length} speaker${(meeting.speakers || []).length === 1 ? "" : "s"}` : status === "failed" ? escapeHtml(meeting.transcription?.error || failureDescription) : serviceDescription}</p>
    </div>
    <div class="transcription-workspace__actions">
      ${isRunning ? `<button type="button" class="button button--quiet" data-action="cancel-transcription">Cancel</button>` : ""}
      <button type="button" class="button button--primary" data-action="transcribe-meeting" ${hasRecording && !isRunning ? "" : "disabled"}>${isRunning ? `${icon("refresh", 15, "spin")}Processing…` : `${icon("users", 15)}${buttonLabel}`}</button>
    </div>
  </section>`;
}

function speakerRoster(meeting) {
  const speakers = meeting.speakers || [];
  if (!speakers.length) return "";
  return `<section class="speaker-roster">
    <div class="speaker-roster__heading"><div><span class="eyebrow">Speakers</span><h3>Name the voices in this meeting</h3></div><span>${speakers.length} detected</span></div>
    <p class="speaker-roster__help">Speaker 1 and Speaker 2 are voice groups detected in this recording, not recognised identities. Rename them here after transcription. Short, overlapping, or missing meeting audio can reduce separation accuracy.</p>
    <div class="speaker-roster__list">
      ${speakers
        .map((speaker) => {
          const local = speaker.id === "local-user";
          return `<div class="speaker-card">
            ${avatar(local ? currentUserInitials() : MeetingAudio.initialsForName(speaker.displayName), speaker.color)}
            <div><strong>${local ? "You" : escapeHtml(speaker.displayName)}</strong><small>${local ? `${escapeHtml(currentUserName())} · local microphone` : "Detected in meeting audio"}</small></div>
            ${
              local
                ? `<span class="speaker-card__fixed">${icon("lock", 12)}Profile</span>`
                : `<label><span>Speaker name</span><input data-input="speaker-name" data-id="${escapeHtml(speaker.id)}" value="${escapeHtml(speaker.displayName)}" maxlength="80" aria-label="Rename ${escapeHtml(speaker.displayName)}"></label>`
            }
          </div>`;
        })
        .join("")}
    </div>
  </section>`;
}

function transcriptView(meeting) {
  const query = state.transcriptQuery || "";
  const hasRecording = Boolean(
    MeetingAudio.recordingAsset(meeting, selectedPlaybackSource(meeting)),
  );
  return `<div class="transcript-view">
    ${transcriptionWorkspace(meeting)}
    ${speakerRoster(meeting)}
    <div class="transcript-toolbar"><div class="transcript-search">${icon("search", 15)}<input data-input="transcript-search" value="${escapeHtml(query)}" placeholder="Find in transcript" aria-label="Find in transcript"></div><span>${meeting.transcript.length} segments</span></div>
    <div class="transcript-document">
      <div class="transcript-document__rail">
        <button type="button" class="playback-toggle" ${hasRecording ? 'data-action="toggle-recording-playback" data-playback-toggle' : "disabled"} aria-label="${hasRecording ? "Play recording" : "No recording available"}" aria-pressed="false">${icon("play", 15)}</button>
        <span data-playback-current>00:00</span>
        <button type="button" class="playback-track" ${hasRecording ? 'data-action="seek-recording" data-playback-track' : "disabled"} aria-label="${hasRecording ? "Seek in recording" : "No recording available"}">
          ${waveform(false, true)}
          <i data-playback-progress aria-hidden="true"></i>
        </button>
        <span data-playback-duration data-playback-fallback="${escapeHtml(meeting.duration)}">${escapeHtml(meeting.duration)}</span>
      </div>
      ${transcriptResultsMarkup(meeting, query)}
    </div>
  </div>`;
}

function transcriptResultsMarkup(meeting, query = "") {
  const normalizedQuery = query.toLowerCase();
  const filtered = meeting.transcript.filter(
    (segment) =>
      segment.text.toLowerCase().includes(normalizedQuery) ||
      MeetingAudio.speakerLabel(
        meeting,
        segment.speakerId,
        segment.speaker,
      )
        .toLowerCase()
        .includes(normalizedQuery) ||
      (segment.speakerId === "local-user" &&
        currentUserName().toLowerCase().includes(normalizedQuery)),
  );
  return `${filtered
    .map((segment) =>
      transcriptRow(
        segment,
        true,
        Boolean(MeetingAudio.recordingAsset(meeting)),
        meeting,
      ),
    )
    .join("")}${
    filtered.length
      ? ""
      : `<div class="empty-search">${icon(query ? "search" : "audio", 24)}<h3>${query ? "No matching transcript" : "No speech transcript available"}</h3><p>${query ? "Try a different word or speaker name." : "The original audio is still available above for playback."}</p></div>`
  }`;
}

function updateTranscriptResults() {
  const meeting = selectedMeeting();
  const document = app.querySelector(".transcript-document");
  if (!meeting || !document) return;
  document
    .querySelectorAll(".transcript-row--document, .empty-search")
    .forEach((element) => element.remove());
  document.insertAdjacentHTML(
    "beforeend",
    transcriptResultsMarkup(meeting, state.transcriptQuery || ""),
  );
}

function notesView(meeting) {
  return `<div class="notes-view"><div class="notes-paper">
    <div class="notes-paper__heading"><div><span class="eyebrow">Personal layer</span><h2>My notes</h2></div><span>Saved locally</span></div>
    <textarea data-input="notes" placeholder="Add the context only you know…" aria-label="Personal meeting notes">${escapeHtml(meeting.notes)}</textarea>
    <div class="notes-prompt">${icon("sparkles", 14)}Try noting a follow-up, risk, or question you want to revisit.</div>
  </div></div>`;
}

function meetingView(meeting) {
  const tabButton = (id, label, iconName) =>
    `<button type="button" data-action="tab" data-id="${id}" class="${state.tab === id ? "detail-tab--active" : ""}" role="tab" aria-selected="${state.tab === id}">${icon(iconName, 15)}${label}</button>`;
  const recordingAssets = MeetingAudio.getRecordingAssets(meeting);
  const playbackSource = selectedPlaybackSource(meeting);
  const selectedAsset = MeetingAudio.recordingAsset(
    meeting,
    playbackSource,
  );
  const audioDownloadName = recordingDownloadName(
    meeting,
    playbackSource,
  );
  const sourceLabel = {
    mixed: "Mixed recording",
    microphone: "My microphone",
    meeting: "Meeting audio",
  };
  const sourceButtons = MeetingAudio.RECORDING_SOURCES.filter(
    (source) => recordingAssets[source],
  )
    .map(
      (source) =>
        `<button type="button" data-action="select-recording-source" data-id="${source}" class="${source === playbackSource ? "recording-source--active" : ""}" aria-pressed="${source === playbackSource}">${escapeHtml(sourceLabel[source])}</button>`,
    )
    .join("");
  return `<main class="main-view detail-view">
    <header class="detail-header">
      <div class="detail-header__top">
        <div class="detail-title"><input data-input="meeting-title" value="${escapeHtml(meeting.title)}" aria-label="Meeting title"><div class="detail-meta"><span>${longDate(meeting.dateISO)}</span><span>·</span><span>${escapeHtml(meeting.duration)}</span><span>·</span><span>${escapeHtml(meeting.source)}</span></div></div>
        <div class="detail-actions">
          <button type="button" class="button button--quiet" data-action="copy">${icon("copy", 15)}Copy</button>
          <button type="button" class="button button--quiet" data-action="export">${icon("download", 15)}Export</button>
          <div class="more-menu">${iconButton("more", "More meeting actions", "more")}
            ${state.moreOpen ? `<div class="more-menu__popover"><button type="button" data-action="export">${icon("file", 15)}Export Markdown</button><button type="button" data-action="delete" class="danger-item">${icon("trash", 15)}Delete meeting</button></div>` : ""}
          </div>
        </div>
      </div>
      ${
        selectedAsset
          ? `<div class="detail-audio">
              <span class="detail-audio__icon">${icon("audio", 18)}</span>
              <div class="detail-audio__identity"><strong>${escapeHtml(sourceLabel[playbackSource] || "Original recording")}</strong><small>Stored locally on this device</small><div class="recording-source-switcher">${sourceButtons}</div></div>
              <audio controls preload="metadata" data-audio-id="${escapeHtml(selectedAsset.id)}" data-recording-source="${escapeHtml(playbackSource)}"></audio>
              <a class="audio-download" data-audio-download="${escapeHtml(selectedAsset.id)}" download="${escapeHtml(audioDownloadName)}" aria-label="Download ${escapeHtml(sourceLabel[playbackSource] || "recording")}">${icon("download", 16)}</a>
            </div>`
          : ""
      }
      <div class="detail-tabs" role="tablist" aria-label="Meeting views">${tabButton("summary", "Summary", "sparkles")}${tabButton("transcript", "Transcript", "file")}${tabButton("notes", "My notes", "notebook")}</div>
    </header>
    <div class="detail-content">${state.tab === "summary" ? summaryView(meeting) : state.tab === "transcript" ? transcriptView(meeting) : notesView(meeting)}</div>
  </main>`;
}

function settingsPanel() {
  const toggle = (key, title, description) =>
    `<button type="button" class="setting-toggle" data-action="setting-toggle" data-id="${key}" aria-pressed="${state.settings[key]}"><div><strong>${title}</strong><span>${description}</span></div><i class="${state.settings[key] ? "toggle--on" : ""}"><span></span></i></button>`;
  const hosted = usesHostedTranscription();
  const hybrid = usesHybridTranscription();
  const hybridConnected = hybrid && !hosted;
  const updateRequired = hybridConnected && companionUpdateRequired();
  const statusText = updateRequired
    ? "update required"
    : ({
        unknown: "not tested",
        checking: "checking",
        connected: hybridConnected ? "local connected" : "connected",
        fallback: "online fallback",
        unavailable: "unavailable",
      }[state.transcriptionServiceStatus] || state.transcriptionServiceStatus);
  const privacyMessage = hosted
    ? hybrid
      ? "Recordings stay in this browser. While the desktop companion is unavailable, requested transcription uses the temporary online service."
      : "Recordings stay in this browser until transcription is requested. Selected audio is then sent securely to the public service and removed from its temporary storage after processing."
    : "Audio and meeting data stay on this device. Browser speech recognition may use your browser provider’s service.";
  const transcriptionSettings = hybrid
    ? `<section class="settings-section">
        <span class="eyebrow">${hybridConnected ? "Desktop speaker transcription" : "Speaker transcription"}</span>
        <div class="service-check"><span class="service-check__status service-check__status--${updateRequired ? "update" : escapeHtml(state.transcriptionServiceStatus)}"><i></i>${escapeHtml(statusText)}</span><button type="button" class="button button--quiet" data-action="${hybridConnected ? "test-transcription-service" : "connect-companion"}">${hybridConnected ? "Test local service" : "Look for companion"}</button></div>
        <p class="settings-help">${updateRequired ? `Companion ${escapeHtml(state.companion.metadata?.version || "")} is installed. Update to ${escapeHtml(latestCompanionVersion)} to receive the latest capture and security fixes.` : hybridConnected ? `NotesBuddy ${escapeHtml(state.companion.metadata?.version || "")} is processing audio privately on this computer. Pairing is automatic and expires when the companion restarts.` : "The online fallback is active. Install or start the desktop companion to process recordings privately on this computer."}</p>
        <div class="companion-actions"><button type="button" class="button button--quiet" data-action="show-companion-setup">Setup guide</button><a class="button button--quiet" href="${escapeHtml(companionDownloadUrl)}" target="_blank" rel="noopener noreferrer">${icon("download", 14)}${updateRequired ? "Download update" : "Windows downloads"}</a></div>
      </section>`
    : hosted
      ? `<section class="settings-section">
        <span class="eyebrow">Online speaker transcription</span>
        <div class="service-check"><span class="service-check__status service-check__status--${escapeHtml(state.transcriptionServiceStatus)}"><i></i>${escapeHtml(statusText)}</span><button type="button" class="button button--quiet" data-action="test-transcription-service">Test service</button></div>
        <p class="settings-help">No installation or token is required. Anonymous sessions are temporary and public usage limits apply.</p>
      </section>`
      : `<section class="settings-section">
        <span class="eyebrow">Local speaker transcription</span>
        <label><span>Companion URL</span><input data-setting="transcriptionEndpoint" value="${escapeHtml(state.settings.transcriptionEndpoint)}" inputmode="url" spellcheck="false" aria-label="Transcription companion URL"></label>
        <label><span>Pairing token</span><input data-setting="transcriptionToken" value="${escapeHtml(state.settings.transcriptionToken)}" type="password" autocomplete="off" spellcheck="false" aria-label="Transcription pairing token"></label>
        <div class="service-check"><span class="service-check__status service-check__status--${escapeHtml(state.transcriptionServiceStatus)}"><i></i>${escapeHtml(statusText)}</span><button type="button" class="button button--quiet" data-action="test-transcription-service">Test connection</button></div>
        <p class="settings-help">The companion runs speech-to-text and speaker diarization on this computer. The pairing token stays in this browser profile.</p>
      </section>`;
  const autoTranscribeDescription = hosted
    ? "Send saved source tracks to the public transcription service after capture."
    : "Send saved local tracks to the paired localhost companion after capture.";
  return `<div class="drawer-backdrop" data-action="close-settings">
    <aside class="settings-drawer" data-panel="settings">
      <header><div><span class="eyebrow">Workspace</span><h2>Settings</h2></div>${iconButton("close-settings", "Close settings", "x")}</header>
      <section class="settings-privacy"><div class="settings-privacy__icon">${icon("shield", 22)}</div><div><strong>${hosted ? "Local recording · online transcription" : "Local recording · on-device transcription"}</strong><p>${privacyMessage}</p></div></section>
      <section class="settings-section">
        <span class="eyebrow">Local profile</span>
        <label><span>Your name</span><input data-input="profile-name" value="${escapeHtml(currentUserName())}" maxlength="80" autocomplete="name" aria-label="Your name"></label>
        <p class="settings-help">Used for your greeting, initials, transcript attribution, and assigned follow-ups. Saved only in this browser profile.</p>
      </section>
      ${transcriptionSettings}
      <section class="settings-section"><span class="eyebrow">Capture defaults</span>${toggle("systemAudio", "Meeting audio", "Record Windows output through the companion, or use browser sharing as a fallback.")}${toggle("browserTranscription", "Browser live transcript draft", "Show recognised words as a draft and use meeting-output timing to mark likely Guest speech; never inject sample text.")}${toggle("autoTranscribe", "Automatically identify speakers", autoTranscribeDescription)}${toggle("autoSummarize", "Create meeting brief", "Build an honest brief from available transcript text.")}${toggle("keepAudio", "Keep original source recordings", "Retain microphone, meeting, and mixed audio in this browser.")}</section>
      <div class="settings-footer"><span>${icon("checkCircle", 15)}Version ${escapeHtml(APP_VERSION)} · Changes save automatically</span><button type="button" class="button button--primary" data-action="close-settings">Done</button></div>
    </aside>
  </div>`;
}

function profileOnboarding() {
  return `<div class="profile-setup-backdrop">
    <section class="profile-setup-card" role="dialog" aria-modal="true" aria-labelledby="profile-setup-title">
      ${brand()}
      <span class="eyebrow">Set up this browser</span>
      <h1 id="profile-setup-title">Welcome to NotesBuddy</h1>
      <p>What should NotesBuddy call you? Your name stays in this browser and is used for greetings, transcript attribution, and follow-ups.</p>
      <form data-form="profile-setup" novalidate>
        <label for="profile-setup-name">Your name</label>
        <input id="profile-setup-name" data-input="profile-setup-name" name="name" maxlength="80" autocomplete="name" placeholder="e.g. Alex Morgan" required autofocus>
        <span class="profile-setup-error" data-profile-error hidden>Please enter your name.</span>
        <button type="submit" class="button button--primary">Create local workspace ${icon("chevronRight", 16)}</button>
      </form>
      <small>${icon("lock", 13)}No account is created. This profile and its meetings remain local to this browser.</small>
    </section>
  </div>`;
}

function companionOnboarding() {
  const connected =
    state.companion.status === "connected" && !usesHostedTranscription();
  const checking = state.companion.status === "checking";
  if (connected && companionUpdateRequired()) {
    return `<div class="companion-setup-backdrop">
      <section class="companion-setup-card companion-setup-card--update" role="dialog" aria-modal="true" aria-labelledby="companion-setup-title">
        <div class="companion-setup__update-icon">${icon("download", 28)}</div>
        <span class="eyebrow">Update available</span>
        <h1 id="companion-setup-title">Update the desktop companion</h1>
        <p>Version ${escapeHtml(state.companion.metadata?.version || "unknown")} is installed. NotesBuddy Companion ${escapeHtml(latestCompanionVersion)} is available with the latest recording and security fixes.</p>
        <a class="button button--primary companion-setup__primary" href="${escapeHtml(companionDownloadUrl)}" target="_blank" rel="noopener noreferrer">${icon("download", 16)}Download update ${escapeHtml(latestCompanionVersion)}</a>
        <button type="button" class="button button--quiet companion-setup__check" data-action="check-companion-update">I've updated it — check again</button>
        <button type="button" class="companion-setup__defer" data-action="defer-companion-setup">Use online transcription for now</button>
        <small class="companion-setup__note">${icon("shield", 13)}Quit the old companion before running the update if Windows asks.</small>
      </section>
    </div>`;
  }
  if (connected) {
    return `<div class="companion-setup-backdrop">
      <section class="companion-setup-card companion-setup-card--success" role="dialog" aria-modal="true" aria-labelledby="companion-setup-title">
        <div class="companion-setup__success-icon">${icon("checkCircle", 30)}</div>
        <span class="eyebrow">Connection confirmed</span>
        <h1 id="companion-setup-title">Desktop companion is working</h1>
        <p>${escapeHtml(state.companion.metadata?.version ? `NotesBuddy Companion ${state.companion.metadata.version}` : "NotesBuddy Companion")} is running on this computer. A compatible version captures Windows meeting output directly and transcribes saved recordings locally without a model or pairing token.</p>
        <div class="companion-setup__privacy">${icon("shield", 18)}<div><strong>On-device processing active</strong><span>Audio is sent only to the companion on 127.0.0.1 while it remains connected.</span></div></div>
        <button type="button" class="button button--primary companion-setup__primary" data-action="complete-companion-setup">Continue to NotesBuddy ${icon("chevronRight", 16)}</button>
      </section>
    </div>`;
  }
  const statusMessage = checking
    ? "Looking for the desktop companion…"
    : state.companion.error
      ? state.companion.error
      : "Install and start the companion, then confirm the connection.";
  return `<div class="companion-setup-backdrop">
    <section class="companion-setup-card" role="dialog" aria-modal="true" aria-labelledby="companion-setup-title">
      ${brand()}
      <span class="eyebrow">Private speaker transcription</span>
      <h1 id="companion-setup-title">Install the Windows companion</h1>
      <p>The small desktop app runs speech-to-text and speaker detection on this computer. You install it once—no Python, Hugging Face account, or token is required.</p>
      <ol class="companion-setup__steps">
        <li><span>1</span><div><strong>Download</strong><small>Open Releases and download the newest Windows Setup file.</small></div></li>
        <li><span>2</span><div><strong>Install and start</strong><small>Run the installer, then leave NotesBuddy Companion running in the notification area.</small></div></li>
        <li><span>3</span><div><strong>Confirm</strong><small>Return here, check the connection, and choose Allow if your browser asks for Local network access.</small></div></li>
      </ol>
      <a class="button button--primary companion-setup__primary" href="${escapeHtml(companionDownloadUrl)}" target="_blank" rel="noopener noreferrer">${icon("download", 16)}Download Windows installer</a>
      <button type="button" class="button button--quiet companion-setup__check" data-action="check-companion-setup" ${checking ? "disabled" : ""}>${checking ? "Checking connection…" : "I've installed it — check connection"}</button>
      <div class="companion-setup__status companion-setup__status--${checking ? "checking" : "waiting"}" aria-live="polite"><i></i>${escapeHtml(statusMessage)}</div>
      <button type="button" class="companion-setup__defer" data-action="defer-companion-setup">Use online transcription for now</button>
      <small class="companion-setup__note">${icon("lock", 13)}Windows 10/11 · Per-user installation · No administrator access required</small>
    </section>
  </div>`;
}

function companionUpdateNotice() {
  if (
    !companionUpdateRequired() ||
    state.companionUpdateDismissed ||
    state.profileOnboardingOpen ||
    state.companionSetupOpen
  ) {
    return "";
  }
  const installedVersion = state.companion.metadata?.version || "unknown";
  return `<section class="companion-update-banner" role="alert" aria-live="assertive">
    <span class="companion-update-banner__icon">${icon("download", 18)}</span>
    <div><strong>Companion update available</strong><p>You have ${escapeHtml(installedVersion)}. Update to ${escapeHtml(latestCompanionVersion)} for the latest recording and security fixes.</p></div>
    <a class="button button--primary" href="${escapeHtml(companionDownloadUrl)}" target="_blank" rel="noopener noreferrer">Download update</a>
    <button type="button" class="button button--quiet" data-action="check-companion-update">Check again</button>
    <button type="button" class="companion-update-banner__dismiss" data-action="dismiss-companion-update" aria-label="Remind me about the companion update next time">Remind me later</button>
  </section>`;
}

function toastRegion() {
  return `<div class="toast-region" aria-live="polite">${state.toasts.map((toast) => `<div class="toast"><span>${icon("check", 14)}</span><div><strong>${escapeHtml(toast.title)}</strong>${toast.description ? `<p>${escapeHtml(toast.description)}</p>` : ""}</div></div>`).join("")}</div>`;
}

function render(focusTarget = "") {
  const currentPlayer = app.querySelector("audio[data-audio-id]");
  const playbackSnapshot =
    currentPlayer?.src && (currentPlayer.currentTime > 0 || !currentPlayer.paused)
      ? {
          audioId: currentPlayer.dataset.audioId,
          currentTime: currentPlayer.currentTime,
          playing: !currentPlayer.paused && !currentPlayer.ended,
        }
      : null;
  const meetings = filteredMeetings();
  const selectedMeeting = state.meetings.find(
    (meeting) => meeting.id === state.selectedMeetingId,
  );
  const content =
    state.view === "capture"
      ? captureView()
      : state.view === "meeting" && selectedMeeting
        ? meetingView(selectedMeeting)
        : homeView(meetings);
  app.innerHTML = `<div class="app-shell ${state.mobileNavOpen ? "mobile-nav-open" : ""}">
    <button type="button" class="mobile-scrim" data-action="close-nav" aria-label="Close navigation"></button>
    ${sidebar(meetings)}
    <div class="workspace">
      <div class="mobile-bar">${iconButton("open-nav", "Open navigation", "menu")}${brand(true)}${iconButton("capture", "Start capture", "mic")}</div>
      ${content}
    </div>
    ${companionUpdateNotice()}
    <input class="visually-hidden" data-input="file" type="file" accept="audio/*,.mp3,.wav,.m4a,.ogg,.flac">
    ${state.settingsOpen ? settingsPanel() : ""}
    ${state.profileOnboardingOpen ? profileOnboarding() : ""}
    ${state.companionSetupOpen && !state.profileOnboardingOpen ? companionOnboarding() : ""}
    ${toastRegion()}
  </div>`;

  if (state.view === "capture" && state.capture.segments.length) {
    const transcript = app.querySelector(".live-transcript__scroll");
    if (transcript) transcript.scrollTop = transcript.scrollHeight;
  }
  if (state.view === "meeting") {
    hydrateMeetingAudio().then((player) => {
      if (
        !player ||
        !playbackSnapshot ||
        player.dataset.audioId !== playbackSnapshot.audioId
      ) {
        return;
      }
      const restorePosition = () => {
        try {
          player.currentTime = playbackSnapshot.currentTime;
          syncPlaybackUI(player);
        } catch {
          // Metadata may not be available until the next media event.
        }
      };
      if (player.readyState >= 1) {
        restorePosition();
      } else {
        player.addEventListener("loadedmetadata", restorePosition, {
          once: true,
        });
      }
      if (playbackSnapshot.playing) {
        player
          .play()
          .then(() => syncPlaybackUI(player))
          .catch(() => {
            // Browser autoplay policy may require the user to press play again.
          });
      }
    });
  }
  if (focusTarget) {
    requestAnimationFrame(() => {
      const element = app.querySelector(`[data-input="${focusTarget}"]`);
      if (element) {
        element.focus();
        if ("selectionStart" in element) {
          element.selectionStart = element.value.length;
          element.selectionEnd = element.value.length;
        }
      }
    });
  }
}

function syncPlaybackUI(player) {
  if (!player) return;
  const isPlaying = !player.paused && !player.ended;
  const currentTime = Number.isFinite(player.currentTime)
    ? Math.max(0, player.currentTime)
    : 0;
  const duration =
    Number.isFinite(player.duration) && player.duration > 0
      ? player.duration
      : 0;

  app.querySelectorAll("[data-playback-toggle]").forEach((control) => {
    control.innerHTML = icon(isPlaying ? "pause" : "play", 15);
    control.classList.toggle("playback-toggle--playing", isPlaying);
    control.setAttribute("aria-pressed", String(isPlaying));
    control.setAttribute(
      "aria-label",
      isPlaying ? "Pause recording" : "Play recording",
    );
  });
  app.querySelectorAll("[data-playback-current]").forEach((label) => {
    label.textContent = formatTimer(Math.floor(currentTime));
  });
  app.querySelectorAll("[data-playback-duration]").forEach((label) => {
    label.textContent = duration
      ? formatTimer(Math.max(1, Math.ceil(duration)))
      : label.dataset.playbackFallback || "00:00";
  });
  app.querySelectorAll("[data-playback-track]").forEach((track) => {
    track.setAttribute(
      "aria-valuetext",
      duration
        ? `${formatTimer(Math.floor(currentTime))} of ${formatTimer(Math.ceil(duration))}`
        : formatTimer(Math.floor(currentTime)),
    );
  });
  app.querySelectorAll("[data-playback-progress]").forEach((progress) => {
    progress.style.width = duration
      ? `${Math.min(100, (currentTime / duration) * 100)}%`
      : "0%";
  });
}

function markPlaybackUnavailable(player) {
  app.querySelectorAll("[data-playback-toggle], [data-playback-track]").forEach(
    (control) => {
      control.disabled = true;
      control.removeAttribute("data-action");
      control.setAttribute("aria-label", "Recording unavailable");
    },
  );
  const download = app.querySelector("[data-audio-download]");
  if (download) download.hidden = true;
  if (player?.isConnected) {
    player.outerHTML =
      '<span class="audio-unavailable">Recording could not be loaded.</span>';
  }
}

function connectPlaybackEvents(player) {
  if (player.dataset.playbackEvents === "connected") return;
  player.dataset.playbackEvents = "connected";
  [
    "loadedmetadata",
    "durationchange",
    "timeupdate",
    "play",
    "pause",
    "ended",
    "seeking",
    "seeked",
  ].forEach((eventName) => {
    player.addEventListener(eventName, () => syncPlaybackUI(player));
  });
}

async function hydrateMeetingAudio() {
  const player = app.querySelector("audio[data-audio-id]");
  if (!player) return null;
  connectPlaybackEvents(player);
  if (player.src) return player;
  if (player._notesBuddyHydration) return player._notesBuddyHydration;

  player._notesBuddyHydration = (async () => {
    try {
      const blob = await getAudio(player.dataset.audioId);
      if (!blob || !player.isConnected) {
        if (player.isConnected) markPlaybackUnavailable(player);
        return null;
      }
      if (activeAudioUrl) URL.revokeObjectURL(activeAudioUrl);
      activeAudioUrl = URL.createObjectURL(blob);
      player.src = activeAudioUrl;
      const download = app.querySelector(
        `[data-audio-download="${CSS.escape(player.dataset.audioId)}"]`,
      );
      if (download) download.href = activeAudioUrl;
      syncPlaybackUI(player);
      return player;
    } catch {
      if (player.isConnected) {
        markPlaybackUnavailable(player);
      }
      return null;
    }
  })();
  return player._notesBuddyHydration;
}

async function toggleRecordingPlayback() {
  const player = await hydrateMeetingAudio();
  if (!player?.src) {
    showToast(
      "Recording unavailable",
      "This meeting does not have playable audio stored on this device.",
    );
    return;
  }
  try {
    if (player.paused || player.ended) {
      if (player.ended) player.currentTime = 0;
      await player.play();
    } else {
      player.pause();
    }
    syncPlaybackUI(player);
  } catch {
    showToast(
      "Playback could not start",
      "Check your browser audio permissions and try the recording again.",
    );
  }
}

async function seekRecording(control, event) {
  const player = await hydrateMeetingAudio();
  if (!player?.src) {
    showToast(
      "Recording unavailable",
      "This meeting does not have playable audio stored on this device.",
    );
    return;
  }
  if (!Number.isFinite(player.duration) || player.duration <= 0) {
    try {
      await player.play();
      player.pause();
    } catch {
      // Some recorded WebM files expose duration only after playback begins.
    }
  }
  if (!Number.isFinite(player.duration) || player.duration <= 0) return;
  const bounds = control.getBoundingClientRect();
  const ratio = Math.min(
    1,
    Math.max(0, (event.clientX - bounds.left) / bounds.width),
  );
  player.currentTime = player.duration * ratio;
  syncPlaybackUI(player);
}

async function seekRecordingTime(timestamp) {
  const player = await hydrateMeetingAudio();
  if (!player?.src) {
    showToast(
      "Recording unavailable",
      "This meeting does not have playable audio stored on this device.",
    );
    return;
  }
  const parts = String(timestamp)
    .split(":")
    .map((part) => Number(part));
  const seconds =
    parts.length === 3
      ? parts[0] * 3600 + parts[1] * 60 + parts[2]
      : (parts[0] || 0) * 60 + (parts[1] || 0);
  player.currentTime = Math.max(0, seconds);
  syncPlaybackUI(player);
}

function showToast(title, description = "") {
  const id = ++toastId;
  state.toasts.push({ id, title, description });
  refreshToastRegion();
  window.setTimeout(() => {
    state.toasts = state.toasts.filter((toast) => toast.id !== id);
    refreshToastRegion();
  }, 3600);
}

function refreshToastRegion() {
  const current = app.querySelector(".toast-region");
  const renderedViewMatchesState =
    (state.view === "home" && Boolean(app.querySelector(".home-view"))) ||
    (state.view === "capture" && Boolean(app.querySelector(".capture-view"))) ||
    (state.view === "meeting" && Boolean(app.querySelector(".detail-view")));
  if (current && renderedViewMatchesState) {
    current.outerHTML = toastRegion();
  } else {
    render();
  }
}

function resetCapture() {
  clearInterval(captureTimer);
  stopSpeechRecognition();
  cancelCaptureRuntime();
  state.capture = {
    title: "Untitled meeting",
    status: "idle",
    elapsed: 0,
    segments: [],
    interimTranscript: "",
    interimSpeakerId: null,
    transcriptionStatus: "idle",
    microphoneOn: true,
    systemAudioOn: state.settings.systemAudio,
    permission: "prompt",
    sourceStatus: {
      microphone: "idle",
      meeting: "idle",
      mixed: "idle",
    },
    meetingDisplaySurface: null,
    meetingCaptureMode: null,
    meetingDeviceName: null,
    meetingAudioEnded: false,
    meetingAudioSignalDetected: false,
    meetingAudioCurrentlyActive: false,
    meetingAudioWarning: "",
    captureStartedAt: null,
  };
}

function stopStream(stream) {
  stream?.getTracks?.().forEach((track) => {
    try {
      track.stop();
    } catch {
      // The browser may already have stopped a shared track.
    }
  });
}

function cancelCaptureRuntime() {
  stopMeetingAudioSignalMonitor();
  if (
    captureRuntime.companionCaptureId &&
    captureRuntime.companionCaptureClient
  ) {
    captureRuntime.companionCaptureClient
      .cancelSystemAudioCapture(captureRuntime.companionCaptureId)
      .catch(() => {});
    captureRuntime.companionCaptureId = null;
  }
  Object.values(captureRuntime.recorders).forEach((recorder) => {
    if (recorder?.state && recorder.state !== "inactive") {
      try {
        recorder.stop();
      } catch {
        // A recorder can become inactive when its source ends externally.
      }
    }
  });
  Object.values(captureRuntime.streams).forEach(stopStream);
  captureRuntime.audioNodes.forEach((node) => {
    try {
      node.disconnect();
    } catch {
      // Disconnected audio nodes do not require further cleanup.
    }
  });
  captureRuntime.audioContext?.close?.().catch(() => {});
  captureRuntime = createEmptyCaptureRuntime();
}

function captureSourceStatusLabel(status) {
  return {
    detected: "sound detected",
    listening: "waiting for sound",
    silent: "no sound detected",
    separate: "saved separately",
  }[status] || status;
}

function setCaptureSourceStatus(source, value) {
  state.capture.sourceStatus[source] = value;
  const element = app.querySelector(`[data-source-status="${source}"]`);
  if (!element) return;
  Array.from(element.classList)
    .filter((className) =>
      className.startsWith("capture-source-live__item--"),
    )
    .forEach((className) => element.classList.remove(className));
  element.classList.add(`capture-source-live__item--${value}`);
  const label = element.querySelector("b");
  if (label) label.textContent = captureSourceStatusLabel(value);
}

function replaceMeetingAudioWarning(message, kind = "signal") {
  state.capture.meetingAudioWarning = kind === "ended" ? "" : message;
  const current = app.querySelector("[data-meeting-audio-warning]");
  current?.remove();
  const sources = app.querySelector(".capture-source-live");
  if (!sources || !message) return;
  sources.insertAdjacentHTML(
    "afterend",
    `<div class="capture-source-warning" data-meeting-audio-warning="${escapeHtml(kind)}">${icon("headphones", 14)}${escapeHtml(message)}</div>`,
  );
}

function showMeetingAudioEndedWarning() {
  replaceMeetingAudioWarning(
    "Meeting audio sharing stopped. Microphone recording is continuing.",
    "ended",
  );
}

function meetingAudioTrackHelp(surface) {
  if (surface === "browser") {
    return "No Teams tab audio was received. Share the Teams tab and turn on Also share tab audio.";
  }
  if (surface === "window") {
    return "No audio was received from the shared window. For Teams desktop, choose Entire Screen and turn on Also share system audio.";
  }
  if (surface === "monitor") {
    return "No system audio was received. Share the screen again and turn on Also share system audio.";
  }
  return "No meeting audio was received. Share the Teams tab or Entire Screen and enable the audio option in the browser dialog.";
}

function meetingAudioSilenceHelp(surface) {
  if (surface === "windows-loopback") {
    return "No Windows output has been detected. In Teams device settings, choose the same speaker as the Windows default output and ask another participant to speak.";
  }
  if (surface === "browser") {
    return "No sound is arriving from the Teams tab. Check that Also share tab audio is on and ask another participant to speak.";
  }
  if (surface === "window") {
    return "No sound is arriving from the Teams window. Stop capture, choose Entire Screen, and turn on Also share system audio.";
  }
  return "No meeting sound has been detected. Check the meeting volume and confirm that Also share system audio is on.";
}

function captureClockMs() {
  if (captureRuntime.captureStartedAtMonotonic === null) {
    return Math.max(0, Number(state.capture.elapsed) || 0) * 1000;
  }
  const now = performance.now();
  const currentPauseMs = captureRuntime.pausedAtMonotonic === null
    ? 0
    : Math.max(0, now - captureRuntime.pausedAtMonotonic);
  return Math.max(
    0,
    now -
      captureRuntime.captureStartedAtMonotonic -
      captureRuntime.totalPausedMs -
      currentPauseMs,
  );
}

function setMeetingAudioCurrentlyActive(active) {
  const next = Boolean(active);
  if (state.capture.meetingAudioCurrentlyActive === next) return;
  state.capture.meetingAudioCurrentlyActive = next;
  updateCaptureRuntimeUI({ transcript: true });
}

function recordMeetingAudioActivity(active, atMs = captureClockMs()) {
  const safeAtMs = Math.max(0, Number(atMs) || 0);
  if (active && state.capture.status === "recording") {
    const spans = captureRuntime.meetingActivitySpans;
    const nextStartMs = Math.max(0, safeAtMs - MEETING_ACTIVITY_LEAD_MS);
    const nextEndMs = safeAtMs + MEETING_ACTIVITY_HANGOVER_MS;
    const previous = spans.at(-1);
    if (previous && nextStartMs <= previous.endMs + MEETING_ACTIVITY_LEAD_MS) {
      previous.endMs = Math.max(previous.endMs, nextEndMs);
    } else {
      spans.push({ startMs: nextStartMs, endMs: nextEndMs });
    }
    captureRuntime.meetingActivityLastDetectedAtMs = safeAtMs;
  }
  const lastDetectedAtMs = captureRuntime.meetingActivityLastDetectedAtMs;
  setMeetingAudioCurrentlyActive(
    state.capture.status === "recording" &&
      lastDetectedAtMs !== null &&
      safeAtMs - lastDetectedAtMs <= MEETING_ACTIVITY_HANGOVER_MS,
  );
}

function clearCurrentMeetingAudioActivity() {
  captureRuntime.meetingActivityLastDetectedAtMs = null;
  setMeetingAudioCurrentlyActive(false);
}

function stopMeetingAudioSignalMonitor() {
  if (captureRuntime.meetingSignalMonitor) {
    window.clearInterval(captureRuntime.meetingSignalMonitor);
    captureRuntime.meetingSignalMonitor = null;
  }
  if (captureRuntime.companionStatusTimer) {
    window.clearInterval(captureRuntime.companionStatusTimer);
    captureRuntime.companionStatusTimer = null;
  }
  clearCurrentMeetingAudioActivity();
}

function startMeetingAudioSignalMonitor(stream) {
  stopMeetingAudioSignalMonitor();
  const AudioContextClass =
    globalThis.AudioContext || globalThis.webkitAudioContext;
  if (!AudioContextClass || !stream?.getAudioTracks?.().length) return;
  const audioContext =
    captureRuntime.audioContext || new AudioContextClass();
  captureRuntime.audioContext = audioContext;
  const audioOnlyStream = new MediaStream(stream.getAudioTracks());
  const sourceNode = audioContext.createMediaStreamSource(audioOnlyStream);
  const analyser = audioContext.createAnalyser();
  const silentSink = audioContext.createGain();
  analyser.fftSize = 512;
  analyser.smoothingTimeConstant = 0.35;
  silentSink.gain.value = 0;
  sourceNode.connect(analyser);
  analyser.connect(silentSink);
  silentSink.connect(audioContext.destination);
  captureRuntime.audioNodes.push(sourceNode, analyser, silentSink);
  audioContext.resume?.().catch(() => {});

  const samples = new Uint8Array(analyser.fftSize);
  const startedAt = performance.now();
  let warned = false;
  captureRuntime.meetingSignalMonitor = window.setInterval(() => {
    if (state.capture.status !== "recording") return;
    analyser.getByteTimeDomainData(samples);
    let sumSquares = 0;
    for (const value of samples) {
      const normalized = (value - 128) / 128;
      sumSquares += normalized * normalized;
    }
    const rms = Math.sqrt(sumSquares / samples.length);
    const signalActive = rms >= MEETING_ACTIVITY_THRESHOLD;
    recordMeetingAudioActivity(signalActive);
    if (signalActive) {
      if (!state.capture.meetingAudioSignalDetected) {
        state.capture.meetingAudioSignalDetected = true;
        state.capture.meetingAudioWarning = "";
        setCaptureSourceStatus("meeting", "detected");
        app.querySelector('[data-meeting-audio-warning="signal"]')?.remove();
      }
      return;
    }
    if (!warned && performance.now() - startedAt >= 5000) {
      warned = true;
      const message = meetingAudioSilenceHelp(
        state.capture.meetingDisplaySurface,
      );
      setCaptureSourceStatus("meeting", "silent");
      replaceMeetingAudioWarning(message);
      showToast("No meeting sound detected", message);
    }
  }, 200);
}

function startCompanionMeetingAudioStatusMonitor() {
  stopMeetingAudioSignalMonitor();
  const client = captureRuntime.companionCaptureClient;
  const captureId = captureRuntime.companionCaptureId;
  if (!client || !captureId) return;
  let checking = false;
  let warned = false;
  const poll = async () => {
    if (
      checking ||
      !captureRuntime.companionCaptureId ||
      captureRuntime.companionCaptureId !== captureId
    ) {
      return;
    }
    checking = true;
    try {
      const status = await client.getSystemAudioCapture(captureId);
      if (captureRuntime.companionCaptureId !== captureId) return;
      state.capture.meetingDeviceName = status.deviceName || "Windows output";
      if (status.status === "failed") {
        throw new Error(status.error || "Windows audio capture stopped.");
      }
      recordMeetingAudioActivity(
        Number(status.level) >= MEETING_ACTIVITY_THRESHOLD,
        status.durationMs,
      );
      if (status.signalDetected) {
        state.capture.meetingAudioSignalDetected = true;
        state.capture.meetingAudioWarning = "";
        setCaptureSourceStatus("meeting", "detected");
        app.querySelector('[data-meeting-audio-warning="signal"]')?.remove();
      } else if (!warned && Number(status.durationMs) >= 5000) {
        warned = true;
        const message = meetingAudioSilenceHelp("windows-loopback");
        setCaptureSourceStatus("meeting", "silent");
        replaceMeetingAudioWarning(message);
        showToast("No Windows meeting sound detected", message);
      }
    } catch (error) {
      stopMeetingAudioSignalMonitor();
      const message =
        error?.message || "The desktop companion stopped capturing Windows audio.";
      state.capture.meetingAudioWarning = message;
      setCaptureSourceStatus("meeting", "unavailable");
      replaceMeetingAudioWarning(message);
      showToast("Windows audio capture stopped", message);
    } finally {
      checking = false;
    }
  };
  captureRuntime.companionStatusTimer = window.setInterval(poll, 500);
  poll();
}

async function startCompanionMeetingAudioCapture() {
  let client = createTranscriptionClient();
  let capture;
  try {
    capture = await client.startSystemAudioCapture();
  } catch (error) {
    if (!usesHybridTranscription() || error?.status !== 401) throw error;
    const reconnected = await connectLocalCompanion({
      silent: true,
      force: true,
    });
    if (!reconnected || !companionSystemAudioAvailable()) throw error;
    client = createTranscriptionClient();
    capture = await client.startSystemAudioCapture();
  }
  if (!capture?.captureId) {
    throw new Error("The desktop companion did not start Windows audio capture.");
  }
  captureRuntime.companionCaptureClient = client;
  captureRuntime.companionCaptureId = capture.captureId;
  state.capture.meetingCaptureMode = "companion";
  state.capture.meetingDisplaySurface = "windows-loopback";
  state.capture.meetingDeviceName = capture.deviceName || "Windows output";
  state.capture.sourceStatus.meeting = "ready";
}

function preferredRecordingType() {
  return [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
  ].find((type) => MediaRecorder.isTypeSupported(type));
}

function createSourceRecorder(source, stream) {
  const mimeType = preferredRecordingType();
  const recorder = new MediaRecorder(
    stream,
    mimeType ? { mimeType } : undefined,
  );
  captureRuntime.chunks[source] = [];
  recorder.ondataavailable = (event) => {
    if (event.data?.size) captureRuntime.chunks[source].push(event.data);
  };
  recorder.onerror = () => {
    if (
      state.capture.status !== "recording" &&
      state.capture.status !== "paused"
    ) {
      return;
    }
    setCaptureSourceStatus(source, "unavailable");
    showToast(
      `${source === "meeting" ? "Meeting" : source === "microphone" ? "Microphone" : "Mixed"} recorder stopped`,
      "Finish the capture to keep any audio chunks the browser produced.",
    );
  };
  captureRuntime.recorders[source] = recorder;
  return recorder;
}

function buildMixedStream(sourceStreams) {
  const audioTracks = sourceStreams.flatMap((stream) =>
    stream.getAudioTracks(),
  );
  if (!audioTracks.length) return null;
  if (audioTracks.length === 1) {
    return new MediaStream([audioTracks[0]]);
  }
  const AudioContextClass =
    globalThis.AudioContext || globalThis.webkitAudioContext;
  if (!AudioContextClass) {
    throw new Error(
      "This browser cannot mix microphone and meeting audio locally.",
    );
  }
  const audioContext = new AudioContextClass();
  const destination = audioContext.createMediaStreamDestination();
  captureRuntime.audioContext = audioContext;
  for (const stream of sourceStreams) {
    const audioOnlyStream = new MediaStream(stream.getAudioTracks());
    const sourceNode = audioContext.createMediaStreamSource(audioOnlyStream);
    sourceNode.connect(destination);
    captureRuntime.audioNodes.push(sourceNode);
  }
  return destination.stream;
}

async function stopRecorderAndCollect(source) {
  const recorder = captureRuntime.recorders[source];
  if (!recorder) return null;
  if (recorder.state !== "inactive") {
    await new Promise((resolve) => {
      let settled = false;
      const finish = () => {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeout);
        resolve();
      };
      const timeout = window.setTimeout(finish, 5000);
      recorder.addEventListener("stop", finish, { once: true });
      try {
        recorder.requestData?.();
      } catch {
        // Some browsers reject requestData immediately before stop.
      }
      try {
        recorder.stop();
      } catch {
        finish();
      }
    });
  }
  const chunks = captureRuntime.chunks[source] || [];
  return chunks.length
    ? new Blob(chunks, {
        type: recorder.mimeType || chunks[0]?.type || "audio/webm",
      })
    : null;
}

async function stopCompanionMeetingAudioAndCollect() {
  const client = captureRuntime.companionCaptureClient;
  const captureId = captureRuntime.companionCaptureId;
  if (!client || !captureId) return null;
  stopMeetingAudioSignalMonitor();
  captureRuntime.companionCaptureId = null;
  try {
    return await client.stopSystemAudioCapture(captureId);
  } catch (error) {
    client.cancelSystemAudioCapture(captureId).catch(() => {});
    showToast(
      "Windows meeting audio could not be saved",
      error?.message || "Microphone audio will still be kept.",
    );
    return null;
  }
}

async function collectCaptureRecordings() {
  const sources = Object.keys(captureRuntime.recorders);
  const [blobs, companionMeetingBlob] = await Promise.all([
    Promise.all(
      sources.map(async (source) => [
        source,
        await stopRecorderAndCollect(source),
      ]),
    ),
    stopCompanionMeetingAudioAndCollect(),
  ]);
  const recordings = Object.fromEntries(blobs);
  if (companionMeetingBlob) recordings.meeting = companionMeetingBlob;
  return recordings;
}

async function releaseCaptureRuntime() {
  stopMeetingAudioSignalMonitor();
  Object.values(captureRuntime.streams).forEach(stopStream);
  captureRuntime.audioNodes.forEach((node) => {
    try {
      node.disconnect();
    } catch {
      // The node may already be disconnected.
    }
  });
  if (captureRuntime.audioContext?.state !== "closed") {
    await captureRuntime.audioContext?.close?.().catch(() => {});
  }
  captureRuntime = createEmptyCaptureRuntime();
}

function startCaptureTimer() {
  clearInterval(captureTimer);
  captureTimer = window.setInterval(() => {
    if (state.capture.status !== "recording") return;
    state.capture.elapsed += 1;
    updateCaptureRuntimeUI();
  }, 1000);
}

function stopSpeechRecognition() {
  const recognition = speechRecognition;
  speechRecognition = undefined;
  if (!recognition) return;
  recognition.onend = null;
  try {
    recognition.stop();
  } catch {
    // The service may already be stopped.
  }
}

function startSpeechRecognition() {
  if (!state.settings.browserTranscription) {
    state.capture.transcriptionStatus = "disabled";
    return;
  }
  const SpeechRecognition =
    globalThis.SpeechRecognition || globalThis.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    state.capture.transcriptionStatus = "unavailable";
    return;
  }

  const recognition = new SpeechRecognition();
  speechRecognition = recognition;
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = "en-AU";
  recognition.onstart = () => {
    state.capture.transcriptionStatus = "listening";
    updateCaptureRuntimeUI({ transcript: true });
  };
  recognition.onresult = (event) => {
    let interim = "";
    let interimSpeakerId = null;
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const result = event.results[index];
      const text = result[0]?.transcript?.trim();
      if (!text) continue;
      if (result.isFinal) {
        const endMs = captureClockMs();
        const estimatedDurationMs = Math.min(
          6000,
          Math.max(800, text.split(/\s+/).length * 420),
        );
        const startMs = Math.max(0, endMs - estimatedDurationMs);
        const draftSpeaker = MeetingAudio.provisionalDraftSpeaker({
          startMs,
          endMs,
          meetingActivitySpans: captureRuntime.meetingActivitySpans,
        });
        state.capture.segments.push({
          id: createId("speech"),
          speakerId: draftSpeaker.speakerId,
          speaker: draftSpeaker.speaker,
          initials:
            draftSpeaker.speakerId === "local-user"
              ? currentUserInitials()
              : draftSpeaker.initials,
          color: draftSpeaker.color,
          timestamp: formatTimer(state.capture.elapsed),
          startMs,
          endMs,
          source: draftSpeaker.source,
          text,
          isDraft: true,
          provisional: draftSpeaker.provisional,
        });
      } else {
        interim = `${interim} ${text}`.trim();
        const endMs = captureClockMs();
        interimSpeakerId = MeetingAudio.provisionalDraftSpeaker({
          startMs: Math.max(0, endMs - 1400),
          endMs,
          meetingActivitySpans: captureRuntime.meetingActivitySpans,
        }).speakerId;
      }
    }
    state.capture.interimTranscript = interim;
    state.capture.interimSpeakerId = interim ? interimSpeakerId : null;
    updateCaptureRuntimeUI({ transcript: true });
  };
  recognition.onerror = (event) => {
    state.capture.interimTranscript = "";
    state.capture.interimSpeakerId = null;
    if (event.error === "no-speech" || event.error === "aborted") return;
    state.capture.transcriptionStatus = "unavailable";
    updateCaptureRuntimeUI({ transcript: true });
    if (!state.capture.speechErrorShown) {
      state.capture.speechErrorShown = true;
      showToast(
        "Live transcription unavailable",
        "Your real microphone audio is still being recorded for playback.",
      );
    }
  };
  recognition.onend = () => {
    if (
      speechRecognition === recognition &&
      state.capture.status === "recording"
    ) {
      window.setTimeout(() => {
        try {
          recognition.start();
        } catch {
          state.capture.transcriptionStatus = "unavailable";
          updateCaptureRuntimeUI({ transcript: true });
        }
      }, 250);
    }
  };
  try {
    recognition.start();
  } catch {
    state.capture.transcriptionStatus = "unavailable";
    updateCaptureRuntimeUI({ transcript: true });
  }
}

async function startCapture() {
  const companionAudio = companionSystemAudioAvailable();
  const browserRecorderRequired =
    state.capture.microphoneOn ||
    (state.capture.systemAudioOn && !companionAudio);
  if (
    (browserRecorderRequired && !globalThis.MediaRecorder) ||
    (state.capture.microphoneOn && !navigator.mediaDevices)
  ) {
    state.capture.permission = "unavailable";
    showToast(
      "Audio recording unavailable",
      "Use a current Chrome or Edge browser with media permissions enabled.",
    );
    return;
  }
  if (!state.capture.microphoneOn && !state.capture.systemAudioOn) {
    showToast(
      "Choose a recording source",
      "Enable your microphone, meeting audio, or both.",
    );
    return;
  }

  captureRuntime = createEmptyCaptureRuntime();
  state.capture.interimSpeakerId = null;
  state.capture.meetingAudioEnded = false;
  state.capture.meetingAudioSignalDetected = false;
  state.capture.meetingAudioCurrentlyActive = false;
  state.capture.meetingAudioWarning = "";
  state.capture.meetingCaptureMode = null;
  state.capture.meetingDeviceName = null;
  const useCompanionAudio = companionAudio;

  const requestMicrophone = async () => {
    state.capture.status = "requesting-microphone";
    state.capture.sourceStatus.microphone = "requesting";
    render();
    try {
      captureRuntime.streams.microphone =
        await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
      state.capture.sourceStatus.microphone = "ready";
    } catch {
      state.capture.sourceStatus.microphone = "unavailable";
      showToast(
        "Microphone was not shared",
        captureRuntime.streams.meeting ||
          captureRuntime.companionCaptureId ||
          (useCompanionAudio && state.capture.systemAudioOn)
          ? "NotesBuddy will continue with the meeting audio."
          : "Allow microphone access, then start capture again.",
      );
    }
  };

  // Companion capture has no transient-activation restriction. Ask for the
  // microphone first so a first-time permission prompt cannot put Windows
  // output several seconds ahead of the local track.
  if (useCompanionAudio && state.capture.microphoneOn) {
    await requestMicrophone();
  }

  // Display capture must be invoked from the original click's transient user
  // activation. In browser fallback, microphone permission is intentionally
  // requested only after the share picker returns.
  if (state.capture.systemAudioOn) {
    state.capture.status = "requesting-meeting-audio";
    state.capture.sourceStatus.meeting = "requesting";
    render();
    try {
      if (useCompanionAudio) {
        await startCompanionMeetingAudioCapture();
      } else {
        const displayStream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: {
            suppressLocalAudioPlayback: false,
          },
          systemAudio: "include",
          windowAudio: "system",
          surfaceSwitching: "include",
          selfBrowserSurface: "exclude",
          monitorTypeSurfaces: "include",
        });
        state.capture.meetingCaptureMode = "browser";
        state.capture.meetingDisplaySurface =
          displayStream.getVideoTracks()[0]?.getSettings?.().displaySurface ||
          "shared surface";
        const meetingTracks = displayStream.getAudioTracks();
        if (!meetingTracks.length) {
          stopStream(displayStream);
          throw new Error(
            meetingAudioTrackHelp(state.capture.meetingDisplaySurface),
          );
        }
        captureRuntime.streams.display = displayStream;
        captureRuntime.streams.meeting = new MediaStream(meetingTracks);
        state.capture.sourceStatus.meeting = "ready";
        const sharedTrack =
          displayStream.getVideoTracks()[0] || meetingTracks[0];
        sharedTrack.addEventListener(
          "ended",
          () => {
            if (
              state.capture.status !== "recording" &&
              state.capture.status !== "paused"
            ) {
              return;
            }
            state.capture.meetingAudioEnded = true;
            stopMeetingAudioSignalMonitor();
            setCaptureSourceStatus("meeting", "ended");
            showMeetingAudioEndedWarning();
            showToast(
              "Meeting audio sharing stopped",
              "The microphone and mixed recording will continue until you finish.",
            );
          },
          { once: true },
        );
      }
    } catch (error) {
      state.capture.sourceStatus.meeting = "unavailable";
      state.capture.meetingAudioWarning =
        useCompanionAudio
          ? error?.message ||
            `Windows audio capture could not start. Restart companion ${APP_VERSION} and try again.`
          : error?.name === "NotAllowedError"
          ? "Meeting audio sharing was cancelled or blocked. Start again and choose a Teams tab or Entire Screen with audio enabled."
          : error?.message ||
            meetingAudioTrackHelp(state.capture.meetingDisplaySurface);
      showToast(
        useCompanionAudio
          ? "Windows meeting audio could not start"
          : "Meeting audio was not shared",
        `${state.capture.meetingAudioWarning}${state.capture.microphoneOn ? " Microphone recording will continue." : ""}`,
      );
    }
  }

  if (!useCompanionAudio && state.capture.microphoneOn) {
    await requestMicrophone();
  }

  const sourceStreams = [
    captureRuntime.streams.microphone,
    captureRuntime.streams.meeting,
  ].filter(Boolean);
  const companionMeetingAvailable = Boolean(
    captureRuntime.companionCaptureId,
  );
  if (!sourceStreams.length && !companionMeetingAvailable) {
    state.capture.status = "idle";
    state.capture.permission = "unavailable";
    cancelCaptureRuntime();
    render();
    showToast(
      "No audio source is available",
      "Enable at least one source and grant its browser permission.",
    );
    return;
  }

  try {
    if (!companionMeetingAvailable) {
      captureRuntime.streams.mixed = buildMixedStream(sourceStreams);
    }
    if (captureRuntime.streams.microphone) {
      createSourceRecorder(
        "microphone",
        captureRuntime.streams.microphone,
      );
    }
    if (captureRuntime.streams.meeting) {
      createSourceRecorder("meeting", captureRuntime.streams.meeting);
    }
    if (captureRuntime.streams.mixed) {
      createSourceRecorder("mixed", captureRuntime.streams.mixed);
    }
  } catch (error) {
    state.capture.status = "idle";
    cancelCaptureRuntime();
    render();
    showToast(
      "Audio sources could not start",
      error?.message || "The browser could not initialize its audio recorders.",
    );
    return;
  }

  captureRuntime.captureStartedAt = new Date().toISOString();
  captureRuntime.captureStartedAtMonotonic = performance.now();
  state.capture.captureStartedAt = captureRuntime.captureStartedAt;
  try {
    Object.entries(captureRuntime.recorders).forEach(([source, recorder]) => {
      recorder.start(500);
      state.capture.sourceStatus[source] =
        source === "meeting" ? "listening" : "recording";
    });
    if (companionMeetingAvailable) {
      state.capture.sourceStatus.meeting = "listening";
      state.capture.sourceStatus.mixed = "separate";
    }
  } catch (error) {
    state.capture.status = "idle";
    cancelCaptureRuntime();
    render();
    showToast(
      "Audio recording could not start",
      error?.message || "The browser rejected one of the recording sources.",
    );
    return;
  }

  state.capture.permission = "granted";
  state.capture.status = "recording";
  state.capture.transcriptionStatus = captureRuntime.streams.microphone
    ? "starting"
    : "disabled";
  if (captureRuntime.streams.microphone) startSpeechRecognition();
  startCaptureTimer();
  render();
  if (companionMeetingAvailable) {
    startCompanionMeetingAudioStatusMonitor();
  } else if (captureRuntime.streams.meeting) {
    startMeetingAudioSignalMonitor(captureRuntime.streams.meeting);
  }
}

async function pauseCapture() {
  if (state.capture.status !== "recording") return;
  captureRuntime.pausedAtMonotonic = performance.now();
  state.capture.status = "paused";
  clearCurrentMeetingAudioActivity();
  clearInterval(captureTimer);
  stopSpeechRecognition();
  Object.entries(captureRuntime.recorders).forEach(([source, recorder]) => {
    if (recorder.state === "recording") recorder.pause();
    setCaptureSourceStatus(source, "paused");
  });
  if (
    captureRuntime.companionCaptureId &&
    captureRuntime.companionCaptureClient
  ) {
    setCaptureSourceStatus("meeting", "paused");
    setCaptureSourceStatus("mixed", "separate");
    try {
      await captureRuntime.companionCaptureClient.pauseSystemAudioCapture(
        captureRuntime.companionCaptureId,
      );
    } catch (error) {
      showToast(
        "Windows audio could not pause",
        error?.message || "Finish the capture to preserve available audio.",
      );
    }
  }
  captureRuntime.audioContext?.suspend?.().catch(() => {});
}

async function resumeCapture() {
  if (state.capture.status !== "paused") return;
  if (captureRuntime.pausedAtMonotonic !== null) {
    captureRuntime.totalPausedMs += Math.max(
      0,
      performance.now() - captureRuntime.pausedAtMonotonic,
    );
    captureRuntime.pausedAtMonotonic = null;
  }
  state.capture.status = "recording";
  Object.entries(captureRuntime.recorders).forEach(([source, recorder]) => {
    if (recorder.state === "paused") recorder.resume();
    setCaptureSourceStatus(
      source,
      source === "meeting"
        ? state.capture.meetingAudioSignalDetected
          ? "detected"
          : state.capture.meetingAudioWarning
            ? "silent"
            : "listening"
        : "recording",
    );
  });
  if (
    captureRuntime.companionCaptureId &&
    captureRuntime.companionCaptureClient
  ) {
    try {
      await captureRuntime.companionCaptureClient.resumeSystemAudioCapture(
        captureRuntime.companionCaptureId,
      );
      setCaptureSourceStatus(
        "meeting",
        state.capture.meetingAudioSignalDetected
          ? "detected"
          : state.capture.meetingAudioWarning
            ? "silent"
            : "listening",
      );
      setCaptureSourceStatus("mixed", "separate");
    } catch (error) {
      setCaptureSourceStatus("meeting", "unavailable");
      showToast(
        "Windows audio could not resume",
        error?.message || "Finish the capture to preserve available audio.",
      );
    }
  }
  captureRuntime.audioContext?.resume?.().catch(() => {});
  if (captureRuntime.streams.microphone) startSpeechRecognition();
  startCaptureTimer();
}

async function finishCapture() {
  clearInterval(captureTimer);
  stopSpeechRecognition();
  state.capture.status = "processing";
  state.capture.interimTranscript = "";
  state.capture.interimSpeakerId = null;
  state.capture.meetingAudioCurrentlyActive = false;
  const title = state.capture.title.trim() || "Untitled meeting";
  const elapsed = state.capture.elapsed;
  const segments = structuredClone(state.capture.segments);
  const meetingCaptureMode = state.capture.meetingCaptureMode;
  const captureStartedAt = captureRuntime.captureStartedAt;
  const audioPromise = collectCaptureRecordings();
  render();
  const [audioBlobs] = await Promise.all([
    audioPromise,
    new Promise((resolve) => window.setTimeout(resolve, 850)),
  ]);
  await releaseCaptureRuntime();

  const id = createId("meeting");
  const recordingAssets = {};
  if (state.settings.keepAudio) {
    for (const source of ["microphone", "meeting", "mixed"]) {
      const blob = audioBlobs[source];
      if (!blob) continue;
      const assetId = `${id}:${source}`;
      try {
        await storeAudio(assetId, blob);
        recordingAssets[source] = {
          id: assetId,
          mimeType: blob.type || null,
          durationMs: elapsed * 1000,
        };
      } catch {
        // Other source recordings may still save successfully.
      }
    }
  }
  const primarySource =
    [
      "mixed",
      ...(meetingCaptureMode === "companion"
        ? ["meeting", "microphone"]
        : ["microphone", "meeting"]),
    ].find(
      (source) => recordingAssets[source],
    ) || null;
  const primaryAsset = primarySource
    ? recordingAssets[primarySource]
    : null;
  const audioSaved = Boolean(primaryAsset);

  const transcriptText = segments.map((segment) => segment.text).join(" ");
  const participants = recordingAssets.microphone
    ? [
        {
          name: currentUserName(),
          initials: currentUserInitials(),
          color: "teal",
        },
      ]
    : [];
  const draftBrief = state.settings.autoSummarize
    ? MeetingAudio.buildExtractiveBrief(segments, {
        localOwnerName: currentUserName(),
      })
    : null;
  const meeting = {
    id,
    audioId: primaryAsset?.id || null,
    audioType: primaryAsset?.mimeType || null,
    recordingAssets,
    captureStartedAt,
    captureClockVersion: 1,
    meetingCaptureMode,
    title,
    dateISO: new Date().toISOString(),
    duration: durationLabel(elapsed),
    durationSeconds: elapsed,
    source: `${recordingAssets.microphone ? "Microphone" : ""}${recordingAssets.microphone && recordingAssets.meeting ? " + " : ""}${recordingAssets.meeting ? "meeting audio" : ""}${audioSaved ? " · audio saved" : ""}`,
    participants,
    speakers: recordingAssets.microphone
      ? [
          {
            id: "local-user",
            displayName: currentUserName(),
            source: "microphone",
            color: "teal",
            isLocalUser: true,
          },
        ]
      : [],
    tags: [
      "Recorded",
      "Local audio",
      ...(recordingAssets.meeting ? ["Meeting audio"] : []),
    ],
    overview: draftBrief
      ? draftBrief.overview
      : transcriptText
        ? `This meeting contains synchronized local audio and ${segments.length} draft browser-recognised speech segment${segments.length === 1 ? "" : "s"}. Run speaker transcription to create the authoritative diarized transcript.`
      : "This meeting contains locally stored audio. Speaker transcription has not run, and NotesBuddy did not generate sample transcript text.",
    highlights: [],
    decisions: [],
    actions: [],
    summaryVersion: SUMMARY_VERSION,
    transcript: segments,
    transcription: {
      status: segments.length ? "draft" : "not-requested",
      provider: segments.length ? "browser-speech-draft" : null,
      jobId: null,
      error: null,
    },
    notes: "",
  };
  MeetingAudio.ensureMeetingSpeakers(meeting, state.profile);
  if (draftBrief) applyTranscriptBriefToMeeting(meeting, draftBrief);
  state.meetings.unshift(meeting);
  state.selectedMeetingId = id;
  state.view = "meeting";
  state.tab = "summary";
  resetCapture();
  save();
  showToast(
    audioSaved ? "Recording saved" : "Meeting saved without audio",
    audioSaved
      ? `${Object.keys(recordingAssets).length} synchronized recording source${Object.keys(recordingAssets).length === 1 ? " is" : "s are"} ready to play back.`
      : "The browser could not persist any audio source.",
  );
  if (state.settings.autoTranscribe && audioSaved) {
    startMeetingTranscription(meeting).catch(() => {});
  }
}

function meetingMarkdown(meeting) {
  const actionItems = meeting.actions
    .map(
      (action) =>
        `- [${action.done ? "x" : " "}] ${action.text} — ${action.owner}${action.due ? ` · ${action.due}` : ""}`,
    )
    .join("\n");
  const transcript = meeting.transcript
    .map(
      (segment) =>
        `**${MeetingAudio.speakerLabel(meeting, segment.speakerId, segment.speaker)} · ${segment.timestamp}**\n${segment.text}`,
    )
    .join("\n\n");
  const speakers = (meeting.speakers || [])
    .map(
      (speaker) =>
        `- ${speaker.id === "local-user" ? `You (${currentUserName()})` : speaker.displayName}`,
    )
    .join("\n");
  return `# ${meeting.title}\n\n${longDate(meeting.dateISO)} · ${meeting.duration}\n\n## Overview\n\n${meeting.overview}\n\n## Speakers\n\n${speakers || "No speakers identified."}\n\n## Highlights\n\n${meeting.highlights.map((item) => `- ${item}`).join("\n")}\n\n## Decisions\n\n${meeting.decisions.map((item) => `- ${item}`).join("\n")}\n\n## Action items\n\n${actionItems}\n\n## Transcript\n\n${transcript || "No transcript available."}\n\n## My notes\n\n${meeting.notes || "No personal notes."}\n`;
}

function selectedMeeting() {
  return state.meetings.find(
    (meeting) => meeting.id === state.selectedMeetingId,
  );
}

function activateHostedFallback(error = null) {
  if (!usesHybridTranscription()) return;
  const rawMessage = String(error?.message || "");
  const connectionBlocked =
    error?.name === "TypeError" ||
    /failed to fetch|networkerror|load failed/i.test(rawMessage);
  state.companion = {
    status: "unavailable",
    pairingToken: "",
    metadata: null,
    error: connectionBlocked
      ? "Start NotesBuddy Companion and allow Local network access for this site in your browser's address-bar site controls, then check again."
      : rawMessage || null,
  };
  state.settings.transcriptionMode = "hosted";
  state.settings.transcriptionEndpoint = runtimeHostedTranscriptionEndpoint;
  state.settings.transcriptionToken = "";
  state.transcriptionServiceStatus = "fallback";
}

function setHostedSessionPreference(enabled) {
  state.preferHostedForSession = enabled;
  storeSessionFlag(companionSetupSessionKey, enabled);
}

async function connectLocalCompanion({
  silent = false,
  force = false,
} = {}) {
  if (!usesHybridTranscription()) return false;
  if (force) {
    setHostedSessionPreference(false);
  } else if (state.preferHostedForSession) {
    return false;
  }
  if (!force && state.companion.status === "connected") return true;
  if (companionConnectionPromise) return companionConnectionPromise;

  state.companion.status = "checking";
  state.companion.error = null;
  state.transcriptionServiceStatus = "checking";
  render();

  const attempt = (async () => {
    try {
      const connection = await new MeetingAudio.CompanionConnector({
        endpoint: runtimeLocalCompanionEndpoint,
      }).connect();
      if (state.preferHostedForSession && !force) {
        activateHostedFallback();
        save();
        render();
        return false;
      }
      state.companion = {
        status: "connected",
        pairingToken: connection.token,
        metadata: connection.companion,
        expiresAt: connection.expiresAt,
        error: null,
      };
      state.settings.transcriptionMode = "local";
      state.settings.transcriptionEndpoint = connection.endpoint;
      state.settings.transcriptionToken = "";
      state.transcriptionServiceStatus = "connected";
      save();
      render();
      if (!silent) {
        showToast(
          "Desktop companion connected",
          `${connection.health?.engine || "Local transcription"} will process audio on this computer.`,
        );
      }
      return true;
    } catch (error) {
      activateHostedFallback(error);
      save();
      render();
      if (!silent) {
        showToast(
          "Using online transcription",
          error?.message ||
            "Start the desktop companion and choose Look for companion again.",
        );
      }
      return false;
    }
  })();
  companionConnectionPromise = attempt;
  try {
    return await attempt;
  } finally {
    if (companionConnectionPromise === attempt) {
      companionConnectionPromise = null;
    }
  }
}

function createTranscriptionClient() {
  return new MeetingAudio.TranscriptionClient({
    endpoint: state.settings.transcriptionEndpoint,
    mode: state.settings.transcriptionMode,
    token: usesHostedTranscription()
      ? ""
      : usesHybridTranscription()
        ? state.companion.pairingToken
        : state.settings.transcriptionToken,
  });
}

async function loadMeetingRecordingBlobs(meeting) {
  const assets = MeetingAudio.getRecordingAssets(meeting);
  const entries = await Promise.all(
    Object.entries(assets).map(async ([source, asset]) => [
      source,
      await getAudio(asset.id),
    ]),
  );
  return Object.fromEntries(entries.filter(([, blob]) => blob));
}

async function testTranscriptionService() {
  if (usesHybridTranscription() && usesHostedTranscription()) {
    await connectLocalCompanion({ silent: false, force: true });
    return;
  }
  const testedLocalHybrid =
    usesHybridTranscription() && !usesHostedTranscription();
  state.transcriptionServiceStatus = "checking";
  render();
  try {
    let health;
    try {
      health = await createTranscriptionClient().health();
    } catch (error) {
      if (!testedLocalHybrid || error?.status !== 401) throw error;
      const reconnected = await connectLocalCompanion({
        silent: true,
        force: true,
      });
      if (!reconnected) throw error;
      health = await createTranscriptionClient().health();
    }
    state.transcriptionServiceStatus =
      health?.status === "ok" ? "connected" : "unavailable";
    showToast(
      usesHostedTranscription()
        ? "Public transcription service connected"
        : "Transcription companion connected",
      usesHostedTranscription()
        ? `${health?.engine || "Transcription engine"} is ready. No user token is required.`
        : `${health?.engine || "Local engine"} is ready on this computer.`,
    );
  } catch (error) {
    if (testedLocalHybrid) {
      activateHostedFallback(error);
      save();
    } else {
      state.transcriptionServiceStatus = "unavailable";
    }
    showToast(
      testedLocalHybrid
        ? "Desktop companion disconnected"
        : usesHostedTranscription()
        ? "Public transcription service unavailable"
        : "Companion connection failed",
      testedLocalHybrid
        ? "Online transcription is available as a fallback. Restart the companion to return to private processing."
        : error?.message ||
        (usesHostedTranscription()
          ? "Try again shortly. The service may be starting."
          : "Start the local service and verify its URL and pairing token."),
    );
  }
  render();
}

async function startMeetingTranscription(meeting = selectedMeeting()) {
  if (!meeting) return;
  if (
    meeting.transcription?.status === "queued" ||
    meeting.transcription?.status === "processing"
  ) {
    return;
  }
  if (!MeetingAudio.recordingAsset(meeting)) {
    showToast(
      "No recording is available",
      "Speaker transcription requires a saved audio source.",
    );
    return;
  }

  const controller = new AbortController();
  transcriptionControllers.set(meeting.id, controller);
  let client = createTranscriptionClient();
  meeting.transcription = {
    ...(meeting.transcription || {}),
    status: "queued",
    error: null,
    progress: 0,
    requestedAt: new Date().toISOString(),
  };
  save();
  render();

  try {
    const blobs = await loadMeetingRecordingBlobs(meeting);
    const createJob = () =>
      client.createJob({
        microphoneBlob: blobs.microphone,
        meetingBlob: blobs.meeting,
        mixedBlob: blobs.mixed,
        metadata: {
          meetingId: meeting.id,
          captureStartedAt: meeting.captureStartedAt || meeting.dateISO,
          captureClockVersion: meeting.captureClockVersion || 1,
          ...(usesHostedTranscription()
            ? {}
            : { localSpeakerName: currentUserName() }),
          durationMs: Math.max(
            0,
            Number(meeting.durationSeconds || 0) * 1000,
          ),
        },
      });
    let created;
    try {
      created = await createJob();
    } catch (error) {
      if (
        !usesHybridTranscription() ||
        usesHostedTranscription() ||
        error?.status !== 401
      ) {
        throw error;
      }
      await connectLocalCompanion({ silent: true, force: true });
      client = createTranscriptionClient();
      created = await createJob();
    }
    meeting.transcription = {
      ...meeting.transcription,
      status: created.status || "queued",
      jobId: created.jobId,
      provider:
        created.engine ||
        (usesHostedTranscription()
          ? "public-transcription-service"
          : "local-companion"),
    };
    save();
    render();

    const completed = await client.waitForJob(created.jobId, {
      signal: controller.signal,
      onProgress(job) {
        meeting.transcription.status = job.status || "processing";
        meeting.transcription.progress = Number(job.progress) || 0;
        save();
      },
    });
    MeetingAudio.applyTranscriptionResult(meeting, completed, state.profile);
    const brief = state.settings.autoSummarize
      ? MeetingAudio.buildExtractiveBrief(meeting.transcript, {
          localOwnerName: currentUserName(),
        })
      : null;
    if (brief) {
      applyTranscriptBriefToMeeting(meeting, brief);
    } else {
      meeting.overview = meeting.transcript.length
        ? `Speaker transcription identified ${meeting.speakers.length} speaker${meeting.speakers.length === 1 ? "" : "s"} across ${meeting.transcript.length} timestamped segment${meeting.transcript.length === 1 ? "" : "s"}.`
        : `The ${usesHostedTranscription() ? "public transcription service" : "local transcription companion"} did not return speech text, so NotesBuddy did not generate a transcript.`;
      meeting.highlights = [];
      meeting.decisions = [];
      meeting.actions = [];
      meeting.summaryVersion = SUMMARY_VERSION;
    }
    save();
    render();
    showToast(
      "Speaker transcript ready",
      `${meeting.speakers.length} speaker${meeting.speakers.length === 1 ? "" : "s"} identified ${usesHostedTranscription() ? "by the public service" : "locally"}.`,
    );
  } catch (error) {
    const cancelled =
      error?.name === "AbortError" || controller.signal.aborted;
    meeting.transcription = {
      ...(meeting.transcription || {}),
      status: cancelled ? "cancelled" : "failed",
      error: cancelled
        ? null
        : error?.message || "The local transcription job failed.",
    };
    save();
    render();
    if (!cancelled) {
      showToast(
        "Speaker transcription failed",
        meeting.transcription.error,
      );
    }
  } finally {
    transcriptionControllers.delete(meeting.id);
  }
}

async function cancelMeetingTranscription(meeting = selectedMeeting()) {
  if (!meeting) return;
  transcriptionControllers.get(meeting.id)?.abort();
  const jobId = meeting.transcription?.jobId;
  if (jobId) {
    createTranscriptionClient().cancelJob(jobId).catch(() => {});
  }
  meeting.transcription = {
    ...(meeting.transcription || {}),
    status: "cancelled",
    error: null,
  };
  save();
  render();
  showToast(
    "Speaker transcription cancelled",
    "Your browser recordings were not removed.",
  );
}

async function copyMeeting() {
  try {
    await navigator.clipboard.writeText(meetingMarkdown(selectedMeeting()));
    showToast("Meeting copied", "Summary and transcript are on your clipboard.");
  } catch {
    showToast("Copy unavailable", "Use Export to download the meeting instead.");
  }
}

function exportMeeting() {
  const meeting = selectedMeeting();
  const blob = new Blob([meetingMarkdown(meeting)], {
    type: "text/markdown;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${meeting.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}.md`;
  link.click();
  URL.revokeObjectURL(url);
  showToast("Markdown exported", "The meeting was downloaded to your device.");
}

async function importAudio(file) {
  const id = createId("import");
  let audioSaved = false;
  try {
    await storeAudio(id, file);
    audioSaved = true;
  } catch {
    audioSaved = false;
  }
  const meeting = {
    id,
    audioId: audioSaved ? id : null,
    audioType: file.type || null,
    audioFileName: file.name,
    recordingAssets: audioSaved
      ? {
          mixed: {
            id,
            mimeType: file.type || null,
            durationMs: 0,
            fileName: file.name,
          },
        }
      : {},
    title: file.name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " "),
    dateISO: new Date().toISOString(),
    duration: "Imported",
    source: `${file.type || "Audio file"} · ${(file.size / 1024 / 1024).toFixed(1)} MB`,
    participants: [{ name: "Speaker 1", initials: "S1", color: "violet" }],
    speakers: [
      {
        id: "remote-1",
        displayName: "Speaker 1",
        source: "meeting",
        color: "violet",
        isLocalUser: false,
      },
    ],
    tags: ["Imported", "Needs review"],
    overview: audioSaved
      ? "The original audio file was imported and stored locally for playback. No transcript text was invented."
      : "The audio file metadata was imported, but the browser could not persist the recording.",
    highlights: [],
    decisions: [],
    actions: [],
    summaryVersion: SUMMARY_VERSION,
    transcript: [],
    transcription: {
      status: "not-requested",
      provider: null,
      jobId: null,
      error: null,
    },
    notes: "",
  };
  MeetingAudio.ensureMeetingSpeakers(meeting, state.profile);
  state.meetings.unshift(meeting);
  state.selectedMeetingId = id;
  state.view = "meeting";
  state.tab = "summary";
  save();
  showToast(
    audioSaved ? "Audio imported" : "Audio metadata imported",
    audioSaved
      ? "The original file is ready for playback."
      : "The browser could not save the audio file.",
  );
}

function updateProfileName(rawName) {
  const name = String(rawName).trim().replace(/\s+/g, " ");
  if (!name) return false;
  const previousName = state.profile?.name;
  const updatedAt = new Date().toISOString();
  state.profile = normaliseProfile({
    ...state.profile,
    name,
    createdAt: state.profile?.createdAt || updatedAt,
    updatedAt,
  });
  state.meetings.forEach((meeting) => {
    MeetingAudio.ensureMeetingSpeakers(meeting, state.profile);
    MeetingAudio.renameSpeaker(
      meeting,
      "local-user",
      state.profile.name,
      state.profile,
    );
    if (previousName && previousName !== state.profile.name) {
      for (const action of meeting.actions || []) {
        if (action.owner === previousName) {
          action.owner = state.profile.name;
        }
      }
    }
  });
  save();
  return true;
}

app.addEventListener("submit", (event) => {
  const form = event.target.closest("[data-form='profile-setup']");
  if (!form) return;
  event.preventDefault();
  const input = form.querySelector("[data-input='profile-setup-name']");
  const error = form.querySelector("[data-profile-error]");
  if (!updateProfileName(input.value)) {
    input.setAttribute("aria-invalid", "true");
    error.hidden = false;
    input.focus();
    return;
  }
  state.profileOnboardingOpen = false;
  render();
  showToast(
    `Welcome, ${currentUserFirstName()}`,
    "Your private browser workspace is ready.",
  );
});

app.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  if (action === "noop") return;
  if (action === "home") {
    state.view = "home";
    state.mobileNavOpen = false;
  } else if (action === "capture") {
    resetCapture();
    state.view = "capture";
    state.mobileNavOpen = false;
  } else if (action === "meeting") {
    state.selectedMeetingId = button.dataset.id;
    state.tab = "summary";
    state.view = "meeting";
    state.mobileNavOpen = false;
  } else if (action === "view-all") {
    state.showAllMeetings = !state.showAllMeetings;
  } else if (action === "settings") {
    state.settingsOpen = true;
    state.mobileNavOpen = false;
  } else if (action === "close-settings") {
    if (event.target.closest("[data-panel='settings']") && !event.target.closest("button")) {
      return;
    }
    state.settingsOpen = false;
  } else if (action === "test-transcription-service") {
    await testTranscriptionService();
    return;
  } else if (action === "connect-companion") {
    await connectLocalCompanion({ silent: false, force: true });
    return;
  } else if (action === "check-companion-update") {
    state.companionUpdateDismissed = false;
    const connected = await connectLocalCompanion({ silent: true, force: true });
    if (connected && companionUpdateRequired()) {
      showToast(
        "Update still required",
        `Companion ${state.companion.metadata?.version || "unknown"} is still running. Install ${latestCompanionVersion}, then check again.`,
      );
    } else if (connected) {
      state.companionSetupOpen = false;
      showToast(
        "Companion is up to date",
        `NotesBuddy Companion ${state.companion.metadata?.version || latestCompanionVersion} is connected.`,
      );
    }
    render();
    return;
  } else if (action === "dismiss-companion-update") {
    state.companionUpdateDismissed = true;
    render();
    return;
  } else if (action === "show-companion-setup") {
    state.companionSetupOpen = true;
    state.settingsOpen = false;
  } else if (action === "check-companion-setup") {
    await connectLocalCompanion({ silent: true, force: true });
    return;
  } else if (action === "complete-companion-setup") {
    if (state.companion.status !== "connected") return;
    state.settings.companionSetupCompleted = true;
    state.companionSetupOpen = false;
    setHostedSessionPreference(false);
    save();
    render();
    showToast(
      "Desktop companion ready",
      "Future visits will connect to private on-device transcription automatically.",
    );
    return;
  } else if (action === "defer-companion-setup") {
    setHostedSessionPreference(true);
    state.companionSetupOpen = false;
    activateHostedFallback();
    save();
    render();
    showToast(
      "Using online transcription",
      "NotesBuddy will ask about the Windows companion again in a future browser session.",
    );
    return;
  } else if (action === "open-nav") {
    state.mobileNavOpen = true;
  } else if (action === "close-nav") {
    state.mobileNavOpen = false;
  } else if (action === "import") {
    app.querySelector("[data-input='file']").click();
    return;
  } else if (action === "toggle-mic") {
    state.capture.microphoneOn = !state.capture.microphoneOn;
  } else if (action === "toggle-system") {
    state.capture.systemAudioOn = !state.capture.systemAudioOn;
  } else if (action === "start-capture") {
    await startCapture();
    return;
  } else if (action === "pause-capture") {
    if (state.capture.status === "recording") {
      await pauseCapture();
    } else {
      await resumeCapture();
    }
  } else if (action === "select-recording-source") {
    const meeting = selectedMeeting();
    if (
      meeting &&
      MeetingAudio.getRecordingAssets(meeting)[button.dataset.id]
    ) {
      state.playbackSourceByMeeting[meeting.id] = button.dataset.id;
    }
  } else if (action === "transcribe-meeting") {
    startMeetingTranscription().catch(() => {});
    return;
  } else if (action === "cancel-transcription") {
    await cancelMeetingTranscription();
    return;
  } else if (action === "focus-speaker") {
    const input = app.querySelector(
      `[data-input="speaker-name"][data-id="${CSS.escape(button.dataset.id)}"]`,
    );
    input?.scrollIntoView({ behavior: "smooth", block: "center" });
    input?.focus({ preventScroll: true });
    input?.select();
    return;
  } else if (action === "toggle-recording-playback") {
    await toggleRecordingPlayback();
    return;
  } else if (action === "seek-recording") {
    await seekRecording(button, event);
    return;
  } else if (action === "seek-recording-time") {
    await seekRecordingTime(button.dataset.time);
    return;
  } else if (action === "finish-capture") {
    await finishCapture();
    return;
  } else if (action === "cancel-capture") {
    resetCapture();
    state.view = "home";
  } else if (action === "tab") {
    state.tab = button.dataset.id;
    state.transcriptQuery = "";
  } else if (action === "toggle-action") {
    const meeting = selectedMeeting();
    const item = meeting.actions.find(
      (actionItem) => actionItem.id === button.dataset.id,
    );
    if (item) item.done = !item.done;
    save();
  } else if (action === "copy") {
    copyMeeting();
    return;
  } else if (action === "export") {
    exportMeeting();
    return;
  } else if (action === "more") {
    state.moreOpen = !state.moreOpen;
  } else if (action === "delete") {
    const meetingToDelete = selectedMeeting();
    await deleteMeetingAudio(meetingToDelete);
    transcriptionControllers.get(meetingToDelete?.id)?.abort();
    transcriptionControllers.delete(meetingToDelete?.id);
    state.meetings = state.meetings.filter(
      (meeting) => meeting.id !== state.selectedMeetingId,
    );
    state.selectedMeetingId = state.meetings[0]?.id || null;
    state.view = "home";
    state.moreOpen = false;
    save();
    showToast("Meeting deleted", "The local meeting record was removed.");
    return;
  } else if (action === "regenerate") {
    const meeting = selectedMeeting();
    const brief = MeetingAudio.buildExtractiveBrief(meeting?.transcript, {
      localOwnerName: currentUserName(),
    });
    if (meeting && brief) {
      applyTranscriptBriefToMeeting(meeting, brief);
      save();
      render();
      showToast(
        "Insights refreshed",
        "Highlights, decisions, and actions were rebuilt only from this meeting's transcript.",
      );
    } else {
      showToast(
        "No transcript to summarize",
        "Run speaker transcription first; NotesBuddy will not invent a brief.",
      );
    }
    return;
  } else if (action === "setting-toggle") {
    state.settings[button.dataset.id] = !state.settings[button.dataset.id];
    save();
  }
  render();
});

app.addEventListener("input", (event) => {
  const input = event.target;
  const type = input.dataset.input;
  if (type === "search") {
    state.search = input.value;
    render("search");
  } else if (type === "capture-title") {
    state.capture.title = input.value;
  } else if (type === "profile-name") {
    updateProfileName(input.value);
  } else if (type === "speaker-name") {
    const meeting = selectedMeeting();
    if (
      meeting &&
      MeetingAudio.renameSpeaker(
        meeting,
        input.dataset.id,
        input.value,
        state.profile,
      )
    ) {
      save();
      app
        .querySelectorAll(
          `[data-speaker-label-id="${CSS.escape(input.dataset.id)}"]`,
        )
        .forEach((label) => {
          label.textContent = MeetingAudio.speakerLabel(
            meeting,
            input.dataset.id,
          );
        });
    }
  } else if (type === "profile-setup-name") {
    input.removeAttribute("aria-invalid");
    const error = app.querySelector("[data-profile-error]");
    if (error) error.hidden = true;
  } else if (type === "meeting-title") {
    const meeting = selectedMeeting();
    if (meeting) {
      meeting.title = input.value;
      save();
    }
  } else if (type === "notes") {
    const meeting = selectedMeeting();
    if (meeting) {
      meeting.notes = input.value;
      save();
    }
  } else if (type === "transcript-search") {
    state.transcriptQuery = input.value;
    updateTranscriptResults();
  }
});

app.addEventListener("change", async (event) => {
  const input = event.target;
  if (input.dataset.input === "file" && input.files?.[0]) {
    await importAudio(input.files[0]);
  }
  if (input.dataset.setting) {
    state.settings[input.dataset.setting] = input.value;
    save();
    render();
  }
});

document.addEventListener("keydown", (event) => {
  if (
    event.key.toLowerCase() === "n" &&
    !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)
  ) {
    resetCapture();
    state.view = "capture";
    render();
  }
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    const search = app.querySelector("[data-input='search']");
    search?.focus();
  }
  if (event.key === "Escape") {
    state.settingsOpen = false;
    state.mobileNavOpen = false;
    state.moreOpen = false;
    render();
  }
});

window.addEventListener("pagehide", () => {
  clearInterval(captureTimer);
  stopSpeechRecognition();
  cancelCaptureRuntime();
  transcriptionControllers.forEach((controller) => controller.abort());
  transcriptionControllers.clear();
});

render();
if (usesHybridTranscription()) {
  if (state.preferHostedForSession) {
    activateHostedFallback();
    render();
  } else {
    connectLocalCompanion({ silent: true }).catch(() => {});
  }
}
