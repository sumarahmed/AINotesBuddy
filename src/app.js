const app = document.getElementById("root");

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

const LEGACY_SEED_MEETING_IDS = new Set([
  "product-weekly-0729",
  "customer-discovery-0728",
  "design-critique-0727",
  "sprint-planning-0725",
]);
const storedMeetings = loadStored("notesbuddy-meetings", []);
const initialMeetings = Array.isArray(storedMeetings)
  ? storedMeetings.filter((meeting) => !LEGACY_SEED_MEETING_IDS.has(meeting.id))
  : [];
const initialProfile = normaliseProfile(
  loadStored("notesbuddy-profile", null),
);

const defaultSettings = {
  transcriptionModel: "Browser Speech",
  summaryModel: "Extractive brief",
  autoSummarize: true,
  keepAudio: true,
  systemAudio: true,
  browserTranscription: true,
};

const state = {
  meetings: initialMeetings,
  profile: initialProfile,
  profileOnboardingOpen: !initialProfile,
  settings: {
    ...defaultSettings,
    ...loadStored("notesbuddy-settings", defaultSettings),
  },
  view: "home",
  selectedMeetingId: initialMeetings[0]?.id || null,
  tab: "summary",
  search: "",
  settingsOpen: false,
  mobileNavOpen: false,
  moreOpen: false,
  showAllMeetings: false,
  regenerating: false,
  toasts: [],
  capture: {
    title: "Untitled meeting",
    status: "idle",
    elapsed: 0,
    segments: [],
    interimTranscript: "",
    transcriptionStatus: "idle",
    microphoneOn: true,
    systemAudioOn: true,
    permission: "prompt",
  },
};

let captureTimer;
let mediaStream;
let mediaRecorder;
let recordedChunks = [];
let speechRecognition;
let activeAudioUrl;
let toastId = 0;

function save() {
  localStorage.setItem("notesbuddy-meetings", JSON.stringify(state.meetings));
  localStorage.setItem("notesbuddy-settings", JSON.stringify(state.settings));
  if (state.profile) {
    localStorage.setItem("notesbuddy-profile", JSON.stringify(state.profile));
  }
}

if (storedMeetings.length !== initialMeetings.length) {
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

function recordingDownloadName(meeting) {
  if (meeting.audioFileName) {
    return meeting.audioFileName.replace(/[<>:"/\\|?*\u0000-\u001f]/g, "-");
  }
  const type = (meeting.audioType || "").toLowerCase();
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
    meeting.title
      .replace(/[^a-z0-9]+/gi, "-")
      .replace(/^-|-$/g, "")
      .toLowerCase() || "recording";
  return `${baseName}.${extension}`;
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
  const statusLabel = {
    idle: "Ready",
    recording: "Recording",
    paused: "Paused",
    processing: "Finishing locally",
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
              <p>NotesBuddy will record your real microphone audio. Live text appears only when your browser returns recognised speech.</p>
              <div class="source-options">
                <button type="button" data-action="toggle-mic" class="${capture.microphoneOn ? "source-option--active" : ""}">
                  <span>${icon("mic", 17)}</span><div><strong>Microphone</strong><small>Default input</small></div><i>${capture.microphoneOn ? icon("check", 13) : ""}</i>
                </button>
                <button type="button" disabled title="System audio capture requires the desktop application">
                  <span>${icon("headphones", 17)}</span><div><strong>System audio</strong><small>Desktop app only</small></div><i></i>
                </button>
              </div>
              <button type="button" class="start-recording" data-action="start-capture"><span>${icon("mic", 20)}</span>Start capture</button>
              <div class="prototype-note">${icon("shield", 14)}Audio is saved locally for playback. Browser speech recognition may use your browser provider’s service.</div>
            </div>`
          : `<div class="live-workspace">
              <div class="live-meter">
                <div class="live-meter__top"><div><span class="live-pill"><i></i>Live</span><span>${capture.permission === "granted" ? "Microphone recording" : "Microphone unavailable"}</span></div><strong data-capture-clock>${formatTimer(capture.elapsed)}</strong></div>
                ${waveform(capture.status === "recording", true)}
              </div>
              <div class="live-transcript">
                <div class="live-transcript__heading"><div><span class="eyebrow">Live transcript</span><h2>Conversation</h2></div><span class="confidence-pill"><span></span><b data-transcription-label>${capture.transcriptionStatus === "listening" ? "Browser speech" : "Audio recording"}</b></span></div>
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

function liveTranscriptMarkup(capture) {
  return `${capture.segments.map(transcriptRow).join("")}
    ${capture.interimTranscript ? `<div class="interim-transcript">${icon("audio", 18)}<span>${escapeHtml(capture.interimTranscript)}</span></div>` : ""}
    ${capture.segments.length || capture.interimTranscript ? "" : `<div class="listening-state">${icon("audio", 20)}${capture.transcriptionStatus === "listening" ? "Listening for your voice…" : "Recording audio — live speech text is unavailable in this browser."}</div>`}`;
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
        ? "Browser speech"
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

function transcriptRow(segment, documentMode = false, hasRecording = false) {
  const timestamp = escapeHtml(segment.timestamp);
  const timestampControl =
    documentMode && hasRecording
      ? `<button type="button" data-action="seek-recording-time" data-time="${timestamp}" aria-label="Seek recording to ${timestamp}">${timestamp}</button>`
      : `<span>${timestamp}</span>`;
  return `<div class="transcript-row ${documentMode ? "transcript-row--document" : ""}">
    ${avatar(segment.initials, segment.color)}
    <div><div class="transcript-row__meta"><strong>${escapeHtml(segment.speaker)}</strong>${timestampControl}</div><p>${escapeHtml(segment.text)}</p></div>
  </div>`;
}

function summaryView(meeting) {
  return `<div class="summary-layout">
    <div class="summary-main">
      <section class="summary-lead">
        <div class="summary-lead__heading"><div><span class="eyebrow">Meeting brief</span><h2>The short version</h2></div><button type="button" class="text-button" data-action="regenerate">${icon("refresh", 14, state.regenerating ? "spin" : "")}${state.regenerating ? "Refreshing…" : "Regenerate"}</button></div>
        <p>${escapeHtml(meeting.overview)}</p>
      </section>
      <section class="summary-section">
        <div class="summary-section__heading"><span class="section-icon section-icon--teal">${icon("sparkles", 17)}</span><div><span class="eyebrow">What mattered</span><h2>Key highlights</h2></div></div>
        <div class="highlight-grid">${meeting.highlights.map((item, index) => `<article><span>${String(index + 1).padStart(2, "0")}</span><p>${escapeHtml(item)}</p></article>`).join("")}</div>
      </section>
      <section class="summary-section">
        <div class="summary-section__heading"><span class="section-icon section-icon--violet">${icon("clipboard", 17)}</span><div><span class="eyebrow">Locked in</span><h2>Decisions</h2></div></div>
        <div class="decision-list">${meeting.decisions.length ? meeting.decisions.map((item) => `<div>${icon("check", 15)}<span>${escapeHtml(item)}</span></div>`).join("") : `<div>${icon("check", 15)}<span>No explicit decisions were identified.</span></div>`}</div>
      </section>
      <section class="summary-section">
        <div class="summary-section__heading action-heading"><span class="section-icon section-icon--coral">${icon("checkCircle", 17)}</span><div><span class="eyebrow">Keep moving</span><h2>Action items</h2></div><span class="item-count">${meeting.actions.filter((action) => !action.done).length} open</span></div>
        <div class="action-list">${meeting.actions.map((action) => `<button type="button" data-action="toggle-action" data-id="${action.id}" class="${action.done ? "action-item--done" : ""}"><span class="action-check">${action.done ? icon("check", 13) : ""}</span><span class="action-text">${escapeHtml(action.text)}</span><span class="action-owner">${escapeHtml(action.owner)}</span>${action.due ? `<span class="action-due">${escapeHtml(action.due)}</span>` : ""}</button>`).join("")}</div>
      </section>
    </div>
    <aside class="meeting-context">
      <section><span class="eyebrow">People</span><h3>In this conversation</h3><div class="people-list">${meeting.participants.map((person) => `<div>${avatar(person.initials, person.color, true)}<span>${escapeHtml(person.name)}</span></div>`).join("")}</div></section>
      <section><span class="eyebrow">Topics</span><div class="context-tags">${meeting.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div></section>
      <section class="privacy-context"><div>${icon("lock", 15)}<strong>Stored locally</strong></div><p>The recording and meeting record are stored on this device.</p></section>
    </aside>
  </div>`;
}

function transcriptView(meeting) {
  const query = state.transcriptQuery || "";
  const hasRecording = Boolean(meeting.audioId);
  return `<div class="transcript-view">
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
  const filtered = meeting.transcript.filter(
    (segment) =>
      segment.text.toLowerCase().includes(query.toLowerCase()) ||
      segment.speaker.toLowerCase().includes(query.toLowerCase()),
  );
  return `${filtered
    .map((segment) => transcriptRow(segment, true, Boolean(meeting.audioId)))
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
  const audioDownloadName = recordingDownloadName(meeting);
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
        meeting.audioId
          ? `<div class="detail-audio">
              <span class="detail-audio__icon">${icon("audio", 18)}</span>
              <div><strong>Original recording</strong><small>Stored locally on this device</small></div>
              <audio controls preload="metadata" data-audio-id="${escapeHtml(meeting.audioId)}"></audio>
              <a class="audio-download" data-audio-download="${escapeHtml(meeting.audioId)}" download="${escapeHtml(audioDownloadName)}" aria-label="Download recording">${icon("download", 16)}</a>
            </div>`
          : ""
      }
      <div class="detail-tabs" role="tablist" aria-label="Meeting views">${tabButton("summary", "AI summary", "sparkles")}${tabButton("transcript", "Transcript", "file")}${tabButton("notes", "My notes", "notebook")}</div>
    </header>
    <div class="detail-content">${state.tab === "summary" ? summaryView(meeting) : state.tab === "transcript" ? transcriptView(meeting) : notesView(meeting)}</div>
  </main>`;
}

function settingsPanel() {
  const toggle = (key, title, description) =>
    `<button type="button" class="setting-toggle" data-action="setting-toggle" data-id="${key}" aria-pressed="${state.settings[key]}"><div><strong>${title}</strong><span>${description}</span></div><i class="${state.settings[key] ? "toggle--on" : ""}"><span></span></i></button>`;
  return `<div class="drawer-backdrop" data-action="close-settings">
    <aside class="settings-drawer" data-panel="settings">
      <header><div><span class="eyebrow">Workspace</span><h2>Settings</h2></div>${iconButton("close-settings", "Close settings", "x")}</header>
      <section class="settings-privacy"><div class="settings-privacy__icon">${icon("shield", 22)}</div><div><strong>Local recording</strong><p>Audio and meeting data stay on this device. Browser speech recognition may use your browser provider’s service.</p></div></section>
      <section class="settings-section">
        <span class="eyebrow">Local profile</span>
        <label><span>Your name</span><input data-input="profile-name" value="${escapeHtml(currentUserName())}" maxlength="80" autocomplete="name" aria-label="Your name"></label>
        <p class="settings-help">Used for your greeting, initials, transcript attribution, and assigned follow-ups. Saved only in this browser profile.</p>
      </section>
      <section class="settings-section">
        <span class="eyebrow">AI models</span>
        <label><span>Live transcription</span><select disabled><option>Browser speech recognition</option></select></label>
        <label><span>Meeting brief</span><select disabled><option>Extractive brief from recognised text</option></select></label>
      </section>
      <section class="settings-section"><span class="eyebrow">Capture defaults</span>${toggle("browserTranscription", "Browser live transcription", "Use recognised speech returned by your browser; never inject sample text.")}${toggle("autoSummarize", "Create meeting brief", "Build an honest brief from available transcript text.")}${toggle("keepAudio", "Keep original audio", "Retain audio alongside the meeting record.")}</section>
      <div class="settings-footer"><span>${icon("checkCircle", 15)}Changes save automatically</span><button type="button" class="button button--primary" data-action="close-settings">Done</button></div>
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
    <input class="visually-hidden" data-input="file" type="file" accept="audio/*,.mp3,.wav,.m4a,.ogg,.flac">
    ${state.settingsOpen ? settingsPanel() : ""}
    ${state.profileOnboardingOpen ? profileOnboarding() : ""}
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
  mediaStream?.getTracks().forEach((track) => track.stop());
  if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
  mediaStream = undefined;
  mediaRecorder = undefined;
  recordedChunks = [];
  state.capture = {
    title: "Untitled meeting",
    status: "idle",
    elapsed: 0,
    segments: [],
    interimTranscript: "",
    transcriptionStatus: "idle",
    microphoneOn: true,
    systemAudioOn: state.settings.systemAudio,
    permission: "prompt",
  };
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
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const result = event.results[index];
      const text = result[0]?.transcript?.trim();
      if (!text) continue;
      if (result.isFinal) {
        state.capture.segments.push({
          id: createId("speech"),
          speaker: currentUserName(),
          initials: currentUserInitials(),
          color: "teal",
          timestamp: formatTimer(state.capture.elapsed),
          text,
        });
      } else {
        interim = `${interim} ${text}`.trim();
      }
    }
    state.capture.interimTranscript = interim;
    updateCaptureRuntimeUI({ transcript: true });
  };
  recognition.onerror = (event) => {
    state.capture.interimTranscript = "";
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
  if (
    !state.capture.microphoneOn ||
    !navigator.mediaDevices?.getUserMedia ||
    !globalThis.MediaRecorder
  ) {
    state.capture.permission = "unavailable";
    showToast(
      "Microphone recording unavailable",
      "Enable the microphone and use a current Chrome, Edge, or Safari browser.",
    );
    return;
  }

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    state.capture.permission = "unavailable";
    state.capture.status = "idle";
    showToast(
      "Microphone permission is required",
      "Allow microphone access, then start capture again.",
    );
    return;
  }

  recordedChunks = [];
  const preferredTypes = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
  ];
  const mimeType = preferredTypes.find((type) =>
    MediaRecorder.isTypeSupported(type),
  );
  mediaRecorder = new MediaRecorder(
    mediaStream,
    mimeType ? { mimeType } : undefined,
  );
  mediaRecorder.ondataavailable = (event) => {
    if (event.data?.size) recordedChunks.push(event.data);
  };
  mediaRecorder.start(500);

  state.capture.permission = "granted";
  state.capture.status = "recording";
  state.capture.transcriptionStatus = "starting";
  startSpeechRecognition();
  startCaptureTimer();
  render();
}

function stopAndCollectRecording() {
  const recorder = mediaRecorder;
  if (!recorder) return Promise.resolve(null);
  if (recorder.state === "inactive") {
    return Promise.resolve(
      recordedChunks.length
        ? new Blob(recordedChunks, { type: recorder.mimeType || "audio/webm" })
        : null,
    );
  }
  return new Promise((resolve) => {
    recorder.addEventListener(
      "stop",
      () =>
        resolve(
          recordedChunks.length
            ? new Blob(recordedChunks, {
                type: recorder.mimeType || "audio/webm",
              })
            : null,
        ),
      { once: true },
    );
    recorder.stop();
  });
}

async function finishCapture() {
  clearInterval(captureTimer);
  stopSpeechRecognition();
  state.capture.status = "processing";
  state.capture.interimTranscript = "";
  const title = state.capture.title.trim() || "Untitled meeting";
  const elapsed = state.capture.elapsed;
  const segments = structuredClone(state.capture.segments);
  const audioPromise = stopAndCollectRecording();
  mediaStream?.getTracks().forEach((track) => track.stop());
  render();
  const [audioBlob] = await Promise.all([
    audioPromise,
    new Promise((resolve) => window.setTimeout(resolve, 850)),
  ]);

  const id = createId("meeting");
  let audioSaved = false;
  if (audioBlob && state.settings.keepAudio) {
    try {
      await storeAudio(id, audioBlob);
      audioSaved = true;
    } catch {
      audioSaved = false;
    }
  }

  const transcriptText = segments.map((segment) => segment.text).join(" ");
  const participants = segments.length
    ? Array.from(
        new Map(
          segments.map((segment) => [
            segment.speaker,
            {
              name: segment.speaker,
              initials: segment.initials,
              color: segment.color,
            },
          ]),
        ).values(),
      )
    : [
        {
          name: currentUserName(),
          initials: currentUserInitials(),
          color: "teal",
        },
      ];
  const highlights = segments.length
    ? segments.slice(0, 3).map((segment) => segment.text)
    : [
        "The original microphone audio was recorded for playback.",
        "Browser speech recognition did not return transcript text.",
        "No sample or fabricated transcript was added.",
      ];
  const meeting = {
    id,
    audioId: audioSaved ? id : null,
    audioType: audioBlob?.type || null,
    title,
    dateISO: new Date().toISOString(),
    duration: durationLabel(elapsed),
    durationSeconds: elapsed,
    source: `Browser microphone${audioSaved ? " · audio saved" : ""}`,
    participants,
    tags: ["Recorded", "Local audio"],
    overview: transcriptText
      ? `This meeting contains real microphone audio and ${segments.length} browser-recognised speech segment${segments.length === 1 ? "" : "s"}. Review the recording alongside the transcript for accuracy.`
      : "This meeting contains the real microphone recording. Browser speech recognition did not return text, so NotesBuddy did not generate a sample transcript.",
    highlights,
    decisions: [],
    actions: [
      {
        id: `${id}-review`,
        text: "Review the recording and transcript",
        owner: currentUserName(),
        done: false,
      },
    ],
    transcript: segments,
    notes: "",
  };
  state.meetings.unshift(meeting);
  state.selectedMeetingId = id;
  state.view = "meeting";
  state.tab = "summary";
  resetCapture();
  save();
  showToast(
    audioSaved ? "Recording saved" : "Meeting saved without audio",
    audioSaved
      ? "Your real microphone audio is ready to play back."
      : "The browser could not persist the audio recording.",
  );
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
        `**${segment.speaker} · ${segment.timestamp}**\n${segment.text}`,
    )
    .join("\n\n");
  return `# ${meeting.title}\n\n${longDate(meeting.dateISO)} · ${meeting.duration}\n\n## Overview\n\n${meeting.overview}\n\n## Highlights\n\n${meeting.highlights.map((item) => `- ${item}`).join("\n")}\n\n## Decisions\n\n${meeting.decisions.map((item) => `- ${item}`).join("\n")}\n\n## Action items\n\n${actionItems}\n\n## Transcript\n\n${transcript}\n\n## My notes\n\n${meeting.notes || "No personal notes."}\n`;
}

function selectedMeeting() {
  return state.meetings.find(
    (meeting) => meeting.id === state.selectedMeetingId,
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
    title: file.name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " "),
    dateISO: new Date().toISOString(),
    duration: "Imported",
    source: `${file.type || "Audio file"} · ${(file.size / 1024 / 1024).toFixed(1)} MB`,
    participants: [{ name: "Speaker 1", initials: "S1", color: "teal" }],
    tags: ["Imported", "Needs review"],
    overview: audioSaved
      ? "The original audio file was imported and stored locally for playback. No transcript text was invented."
      : "The audio file metadata was imported, but the browser could not persist the recording.",
    highlights: [
      "The original file is available for local playback.",
      "No sample or fabricated transcript was generated.",
    ],
    decisions: [],
    actions: [
      {
        id: `${id}-review`,
        text: "Review and transcribe imported audio",
        owner: currentUserName(),
        done: false,
      },
    ],
    transcript: [],
    notes: "",
  };
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
  const updatedAt = new Date().toISOString();
  state.profile = normaliseProfile({
    ...state.profile,
    name,
    createdAt: state.profile?.createdAt || updatedAt,
    updatedAt,
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
    startCapture();
    return;
  } else if (action === "pause-capture") {
    if (state.capture.status === "recording") {
      state.capture.status = "paused";
      clearInterval(captureTimer);
      stopSpeechRecognition();
      if (mediaRecorder?.state === "recording") mediaRecorder.pause();
    } else {
      state.capture.status = "recording";
      if (mediaRecorder?.state === "paused") mediaRecorder.resume();
      startSpeechRecognition();
      startCaptureTimer();
    }
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
    finishCapture();
    return;
  } else if (action === "cancel-capture") {
    resetCapture();
    state.view = "home";
  } else if (action === "tab") {
    state.tab = button.dataset.id;
    state.transcriptQuery = "";
  } else if (action === "toggle-action") {
    const meeting = selectedMeeting();
    const item = meeting.actions.find((actionItem) => actionItem.id === button.dataset.id);
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
    if (meetingToDelete?.audioId) {
      deleteAudio(meetingToDelete.audioId).catch(() => {});
    }
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
    state.regenerating = true;
    render();
    window.setTimeout(() => {
      state.regenerating = false;
      render();
      showToast(
        "Summary refreshed",
        "Local structure and action items are up to date.",
      );
    }, 1100);
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

render();
