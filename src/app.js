const { CAPTURE_SCRIPT, INITIAL_MEETINGS } = globalThis.NOTESBUDDY_DATA;

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

const defaultSettings = {
  transcriptionModel: "Parakeet TDT 0.6B",
  summaryModel: "NotesBuddy Local",
  autoSummarize: true,
  keepAudio: true,
  systemAudio: true,
};

const state = {
  meetings: loadStored("notesbuddy-meetings", structuredClone(INITIAL_MEETINGS)),
  settings: loadStored("notesbuddy-settings", defaultSettings),
  view: "home",
  selectedMeetingId: INITIAL_MEETINGS[0].id,
  tab: "summary",
  search: "",
  settingsOpen: false,
  mobileNavOpen: false,
  moreOpen: false,
  regenerating: false,
  toasts: [],
  capture: {
    title: "Untitled meeting",
    status: "idle",
    elapsed: 0,
    segments: [],
    microphoneOn: true,
    systemAudioOn: true,
    permission: "prompt",
  },
};

let captureTimer;
let mediaStream;
let mediaRecorder;
let toastId = 0;

function save() {
  localStorage.setItem("notesbuddy-meetings", JSON.stringify(state.meetings));
  localStorage.setItem("notesbuddy-settings", JSON.stringify(state.settings));
}

function formatTimer(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function meetingDate(iso) {
  const date = new Date(iso);
  const today = new Date("2026-07-29T12:00:00+10:00");
  const diff = Math.floor(
    (today.setHours(0, 0, 0, 0) - new Date(date).setHours(0, 0, 0, 0)) /
      86400000,
  );
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
      ${meetings.length ? "" : '<p class="meeting-nav__empty">No meetings match your search.</p>'}
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
  const totalMinutes = meetings.reduce(
    (total, meeting) => total + (parseInt(meeting.duration, 10) || 0),
    0,
  );
  const openActions = meetings.reduce(
    (total, meeting) =>
      total + meeting.actions.filter((action) => !action.done).length,
    0,
  );
  return `<main class="main-view home-view">
    <header class="view-header home-header">
      <div><span class="eyebrow">Wednesday, 29 July</span><h1>Good afternoon, Syed.</h1><p>Your conversations are ready when you are.</p></div>
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
          <p>Capture microphone and system audio. Your transcript and summary stay in this browser.</p>
          <button type="button" data-action="capture">Start a new capture ${icon("chevronRight", 17)}</button>
        </div>
        <div class="capture-card__visual" aria-hidden="true">
          <div class="orbit orbit--one"></div><div class="orbit orbit--two"></div>
          <div class="capture-orb">${icon("audio", 32)}</div>
        </div>
      </article>
      <article class="upcoming-card">
        <div class="card-heading">
          <div><span class="eyebrow">Up next</span><h3>Beta readiness review</h3></div>
          <div class="calendar-chip"><span>29</span><small>JUL</small></div>
        </div>
        <div class="upcoming-time">${icon("clock", 16)}<span>3:30–4:15 pm</span><span class="dot-separator">·</span><span>in 42 min</span></div>
        <div class="participant-row">
          <div class="avatar-stack">${avatar("MC", "blue", true)}${avatar("JB", "amber", true)}${avatar("PS", "violet", true)}</div><span>Maya, Jon, Priya + 2</span>
        </div>
        <button type="button" class="upcoming-action" data-action="capture">${icon("radio", 15)} Capture this meeting</button>
      </article>
    </section>
    <section class="insight-strip">
      <div><span class="insight-strip__icon insight-strip__icon--teal">${icon("notebook", 17)}</span><div><strong>${meetings.length}</strong><span>meetings in memory</span></div></div>
      <div><span class="insight-strip__icon insight-strip__icon--amber">${icon("clock", 17)}</span><div><strong>${totalMinutes > 60 ? `${(totalMinutes / 60).toFixed(1)} hrs` : `${totalMinutes} min`}</strong><span>conversation captured</span></div></div>
      <div><span class="insight-strip__icon insight-strip__icon--coral">${icon("checkCircle", 17)}</span><div><strong>${openActions}</strong><span>open action items</span></div></div>
      <div class="insight-strip__privacy">${icon("lock", 15)}<span>Nothing leaves this device</span></div>
    </section>
    <section class="recent-section">
      <div class="section-title-row"><div><span class="eyebrow">Your memory</span><h2>Recent meetings</h2></div><button type="button" class="text-button">View all ${icon("chevronRight", 15)}</button></div>
      <div class="meeting-cards">
        ${meetings
          .slice(0, 4)
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
          .join("")}
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
      <div class="capture-header__privacy">${icon("shield", 15)} Local capture <span>·</span> ${escapeHtml(state.settings.transcriptionModel)}</div>
      ${iconButton("noop", "Capture options", "more")}
    </header>
    <section class="capture-workspace">
      <div class="capture-title-block">
        <span class="recording-status recording-status--${capture.status}"><i></i>${statusLabel}</span>
        <input class="capture-title-input" data-input="capture-title" value="${escapeHtml(capture.title)}" aria-label="Meeting title">
        <div class="capture-meta">${icon("calendar", 14)} Wed, 29 Jul <span>·</span>${icon("clock", 14)}${formatTimer(capture.elapsed)}</div>
      </div>
      ${
        idle
          ? `<div class="capture-ready">
              <div class="capture-ready__visual"><div class="ready-ring ready-ring--outer"></div><div class="ready-ring ready-ring--inner"></div><div class="ready-mic">${icon("mic", 34)}</div></div>
              <h2>Ready for your next conversation</h2>
              <p>We’ll capture audio and show a representative local transcript for this browser prototype.</p>
              <div class="source-options">
                <button type="button" data-action="toggle-mic" class="${capture.microphoneOn ? "source-option--active" : ""}">
                  <span>${icon("mic", 17)}</span><div><strong>Microphone</strong><small>Default input</small></div><i>${capture.microphoneOn ? icon("check", 13) : ""}</i>
                </button>
                <button type="button" data-action="toggle-system" class="${capture.systemAudioOn ? "source-option--active" : ""}">
                  <span>${icon("headphones", 17)}</span><div><strong>System audio</strong><small>Meeting sound</small></div><i>${capture.systemAudioOn ? icon("check", 13) : ""}</i>
                </button>
              </div>
              <button type="button" class="start-recording" data-action="start-capture"><span>${icon("mic", 20)}</span>Start capture</button>
              <div class="prototype-note">${icon("sparkles", 14)}Prototype mode uses a simulated transcript; microphone audio is not uploaded or retained.</div>
            </div>`
          : `<div class="live-workspace">
              <div class="live-meter">
                <div class="live-meter__top"><div><span class="live-pill"><i></i>Live</span><span>${capture.permission === "granted" ? "Microphone" : "Demo audio"}</span></div><strong>${formatTimer(capture.elapsed)}</strong></div>
                ${waveform(capture.status === "recording", true)}
              </div>
              <div class="live-transcript">
                <div class="live-transcript__heading"><div><span class="eyebrow">Live transcript</span><h2>Conversation</h2></div><span class="confidence-pill"><span></span>Local preview</span></div>
                <div class="live-transcript__scroll">
                  ${capture.segments.map(transcriptRow).join("")}
                  ${capture.segments.length ? "" : `<div class="listening-state">${icon("audio", 20)}Listening for speech…</div>`}
                  ${capture.status === "recording" && capture.segments.length ? '<div class="streaming-line"><span></span><span></span><span></span></div>' : ""}
                </div>
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
        ? `<div class="processing-overlay"><div class="processing-card"><div class="processing-orb">${icon("sparkles", 24)}</div><h2>Turning conversation into memory</h2><p>Structuring highlights, decisions, and action items locally.</p><div class="processing-bar"><span></span></div></div></div>`
        : ""
    }
  </main>`;
}

function transcriptRow(segment, documentMode = false) {
  return `<div class="transcript-row ${documentMode ? "transcript-row--document" : ""}">
    ${avatar(segment.initials, segment.color)}
    <div><div class="transcript-row__meta"><strong>${escapeHtml(segment.speaker)}</strong>${documentMode ? `<button type="button">${escapeHtml(segment.timestamp)}</button>` : `<span>${escapeHtml(segment.timestamp)}</span>`}</div><p>${escapeHtml(segment.text)}</p></div>
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
      <section class="privacy-context"><div>${icon("lock", 15)}<strong>Processed locally</strong></div><p>This summary and transcript are stored only in your browser.</p></section>
    </aside>
  </div>`;
}

function transcriptView(meeting) {
  const query = state.transcriptQuery || "";
  const filtered = meeting.transcript.filter(
    (segment) =>
      segment.text.toLowerCase().includes(query.toLowerCase()) ||
      segment.speaker.toLowerCase().includes(query.toLowerCase()),
  );
  return `<div class="transcript-view">
    <div class="transcript-toolbar"><div class="transcript-search">${icon("search", 15)}<input data-input="transcript-search" value="${escapeHtml(query)}" placeholder="Find in transcript" aria-label="Find in transcript"></div><span>${meeting.transcript.length} segments</span></div>
    <div class="transcript-document">
      <div class="transcript-document__rail"><button type="button">${icon("play", 15)}</button><span>00:00</span><div>${waveform(false, true)}</div><span>${escapeHtml(meeting.duration)}</span></div>
      ${filtered.map((segment) => transcriptRow(segment, true)).join("")}
      ${filtered.length ? "" : `<div class="empty-search">${icon("search", 24)}<h3>No matching transcript</h3><p>Try a different word or speaker name.</p></div>`}
    </div>
  </div>`;
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
      <section class="settings-privacy"><div class="settings-privacy__icon">${icon("shield", 22)}</div><div><strong>Local-first by design</strong><p>This prototype keeps its meeting data in your browser’s local storage.</p></div></section>
      <section class="settings-section">
        <span class="eyebrow">AI models</span>
        <label><span>Transcription</span><select data-setting="transcriptionModel"><option ${state.settings.transcriptionModel === "Parakeet TDT 0.6B" ? "selected" : ""}>Parakeet TDT 0.6B</option><option ${state.settings.transcriptionModel === "Whisper Small" ? "selected" : ""}>Whisper Small</option><option ${state.settings.transcriptionModel === "Whisper Large v3" ? "selected" : ""}>Whisper Large v3</option></select></label>
        <label><span>Summary</span><select data-setting="summaryModel"><option ${state.settings.summaryModel === "NotesBuddy Local" ? "selected" : ""}>NotesBuddy Local</option><option ${state.settings.summaryModel === "Ollama · Gemma 3" ? "selected" : ""}>Ollama · Gemma 3</option><option ${state.settings.summaryModel === "Custom endpoint" ? "selected" : ""}>Custom endpoint</option></select></label>
      </section>
      <section class="settings-section"><span class="eyebrow">Capture defaults</span>${toggle("systemAudio", "Capture system audio", "Include sound from the meeting app.")}${toggle("autoSummarize", "Auto-generate summaries", "Create a structured brief when capture ends.")}${toggle("keepAudio", "Keep original audio", "Retain audio alongside the meeting record.")}</section>
      <div class="settings-footer"><span>${icon("checkCircle", 15)}Changes save automatically</span><button type="button" class="button button--primary" data-action="close-settings">Done</button></div>
    </aside>
  </div>`;
}

function toastRegion() {
  return `<div class="toast-region" aria-live="polite">${state.toasts.map((toast) => `<div class="toast"><span>${icon("check", 14)}</span><div><strong>${escapeHtml(toast.title)}</strong>${toast.description ? `<p>${escapeHtml(toast.description)}</p>` : ""}</div></div>`).join("")}</div>`;
}

function render(focusTarget = "") {
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
    ${toastRegion()}
  </div>`;

  if (state.view === "capture" && state.capture.segments.length) {
    const transcript = app.querySelector(".live-transcript__scroll");
    if (transcript) transcript.scrollTop = transcript.scrollHeight;
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

function showToast(title, description = "") {
  const id = ++toastId;
  state.toasts.push({ id, title, description });
  render();
  window.setTimeout(() => {
    state.toasts = state.toasts.filter((toast) => toast.id !== id);
    render();
  }, 3600);
}

function resetCapture() {
  clearInterval(captureTimer);
  mediaStream?.getTracks().forEach((track) => track.stop());
  if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
  mediaStream = undefined;
  mediaRecorder = undefined;
  state.capture = {
    title: "Untitled meeting",
    status: "idle",
    elapsed: 0,
    segments: [],
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
    const next = CAPTURE_SCRIPT.find(
      (segment) =>
        Number(segment.timestamp.split(":")[1]) <= state.capture.elapsed &&
        !state.capture.segments.some((existing) => existing.id === segment.id),
    );
    if (next) state.capture.segments.push(structuredClone(next));
    render();
  }, 1000);
}

async function startCapture() {
  state.capture.status = "recording";
  render();
  if (state.capture.microphoneOn && navigator.mediaDevices?.getUserMedia) {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      state.capture.permission = "granted";
      if (window.MediaRecorder) {
        mediaRecorder = new MediaRecorder(mediaStream);
        mediaRecorder.start();
      }
    } catch {
      state.capture.permission = "unavailable";
      showToast(
        "Microphone unavailable",
        "Continuing with the simulated local transcript.",
      );
    }
  } else {
    state.capture.permission = "unavailable";
  }
  startCaptureTimer();
  render();
}

function finishCapture() {
  clearInterval(captureTimer);
  state.capture.status = "processing";
  if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
  mediaStream?.getTracks().forEach((track) => track.stop());
  render();
  window.setTimeout(() => {
    const id = `meeting-${Date.now()}`;
    const segments = state.capture.segments.length
      ? structuredClone(state.capture.segments)
      : structuredClone(CAPTURE_SCRIPT.slice(0, 3));
    const participants = Array.from(
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
    );
    const meeting = {
      id,
      title: state.capture.title.trim() || "Untitled meeting",
      dateISO: new Date().toISOString(),
      duration: `${Math.max(1, Math.ceil(state.capture.elapsed / 60))} min`,
      source: "Browser microphone · prototype",
      participants,
      tags: ["New", "Local"],
      overview:
        "The team aligned on a focused milestone, keeping the first reporting release intentionally small. Metric definitions will be validated before the final review.",
      highlights: [
        "The core prototype is ready for a focused reporting layer.",
        "Three high-value metrics will be included in the first release.",
        "Custom dashboards move to the next iteration.",
      ],
      decisions: [
        "Ship the focused reporting view in the next milestone.",
        "Validate metric definitions with support before review.",
      ],
      actions: [
        {
          id: `${id}-a1`,
          text: "Share the focused reporting screen",
          owner: "Jordan",
          due: "Thu",
          done: false,
        },
        {
          id: `${id}-a2`,
          text: "Confirm the final metric definitions",
          owner: "Priya",
          due: "Tomorrow",
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
    showToast("Meeting saved", "Transcript and structured summary are ready.");
  }, 1100);
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

function importAudio(file) {
  const id = `import-${Date.now()}`;
  const meeting = {
    id,
    title: file.name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " "),
    dateISO: new Date().toISOString(),
    duration: "Imported",
    source: `${file.type || "Audio file"} · ${(file.size / 1024 / 1024).toFixed(1)} MB`,
    participants: [{ name: "Speaker 1", initials: "S1", color: "teal" }],
    tags: ["Imported", "Needs review"],
    overview:
      "Audio metadata was imported locally. Connect a native transcription engine to replace this prototype record with a generated transcript and summary.",
    highlights: [
      "The file was handled in the browser and was not uploaded.",
      "Audio transcription requires the native local processing layer.",
    ],
    decisions: [],
    actions: [
      {
        id: `${id}-review`,
        text: "Review and transcribe imported audio",
        owner: "You",
        done: false,
      },
    ],
    transcript: [
      {
        id: `${id}-segment`,
        speaker: "NotesBuddy",
        initials: "NB",
        color: "teal",
        timestamp: "00:00",
        text: "Imported audio is ready. This web prototype stores file metadata only; native transcription is not connected.",
      },
    ],
    notes: "",
  };
  state.meetings.unshift(meeting);
  state.selectedMeetingId = id;
  state.view = "meeting";
  state.tab = "summary";
  save();
  showToast("Audio added locally", "A meeting record was created for review.");
}

app.addEventListener("click", (event) => {
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
  } else if (action === "settings") {
    state.settingsOpen = true;
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
      if (mediaRecorder?.state === "recording") mediaRecorder.pause();
    } else {
      state.capture.status = "recording";
      if (mediaRecorder?.state === "paused") mediaRecorder.resume();
      startCaptureTimer();
    }
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
    render("transcript-search");
  }
});

app.addEventListener("change", (event) => {
  const input = event.target;
  if (input.dataset.input === "file" && input.files?.[0]) {
    importAudio(input.files[0]);
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
