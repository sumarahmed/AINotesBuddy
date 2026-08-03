const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const http = require("node:http");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

let chromium;
try {
  ({ chromium } = require("playwright"));
} catch {
  console.error(
    "Playwright is required for this optional browser test. Install it or set NODE_PATH to a runtime containing playwright.",
  );
  process.exit(1);
}

const projectRoot = path.resolve(__dirname, "..");
const mimeTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
};

function staticServer() {
  return http.createServer(async (request, response) => {
    try {
      const requested = decodeURIComponent(
        new URL(request.url || "/", "http://127.0.0.1").pathname,
      );
      const relative = requested === "/" ? "index.html" : requested.slice(1);
      const filePath = path.resolve(projectRoot, relative);
      if (
        filePath !== projectRoot &&
        !filePath.startsWith(`${projectRoot}${path.sep}`)
      ) {
        response.writeHead(403).end();
        return;
      }
      const content = await fs.readFile(filePath);
      response.writeHead(200, {
        "Content-Type":
          mimeTypes[path.extname(filePath)] || "application/octet-stream",
        "Cache-Control": "no-store",
      });
      response.end(content);
    } catch {
      response.writeHead(404).end();
    }
  });
}

function listen(server) {
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      resolve(`http://127.0.0.1:${address.port}`);
    });
  });
}

function close(server) {
  return new Promise((resolve) => server.close(resolve));
}

async function installSyntheticMedia(
  page,
  {
    denyMeeting = false,
    meetingAudio = true,
    meetingSignal = true,
    displaySurface = "window",
  } = {},
) {
  await page.addInitScript(
    ({
      shouldDenyMeeting,
      shouldIncludeMeetingAudio,
      shouldEmitMeetingSignal,
      selectedDisplaySurface,
    }) => {
      const resources = [];
      const captureCalls = [];
      const displayOptions = [];
      const makeAudioStream = (frequency, gainValue = 0.06) => {
        const AudioContextClass =
          globalThis.AudioContext || globalThis.webkitAudioContext;
        const context = new AudioContextClass();
        const oscillator = context.createOscillator();
        const gain = context.createGain();
        const destination = context.createMediaStreamDestination();
        oscillator.frequency.value = frequency;
        gain.gain.value = gainValue;
        oscillator.connect(gain);
        gain.connect(destination);
        oscillator.start();
        resources.push({ context, oscillator });
        return destination.stream;
      };
      const makeDisplayStream = () => {
        if (shouldDenyMeeting) {
          throw new DOMException("Synthetic share denied", "NotAllowedError");
        }
        const audio = shouldIncludeMeetingAudio
          ? makeAudioStream(620, shouldEmitMeetingSignal ? 0.06 : 0)
          : null;
        const canvas = document.createElement("canvas");
        canvas.width = 64;
        canvas.height = 64;
        const context = canvas.getContext("2d");
        let frame = 0;
        const timer = setInterval(() => {
          context.fillStyle = frame++ % 2 ? "#176c62" : "#dd6e5c";
          context.fillRect(0, 0, canvas.width, canvas.height);
        }, 100);
        const video = canvas.captureStream(8);
        const videoTrack = video.getVideoTracks()[0];
        const originalGetSettings = videoTrack.getSettings.bind(videoTrack);
        Object.defineProperty(videoTrack, "getSettings", {
          configurable: true,
          value: () => ({
            ...originalGetSettings(),
            displaySurface: selectedDisplaySurface,
          }),
        });
        const stream = new MediaStream([
          ...(audio?.getAudioTracks() || []),
          ...video.getVideoTracks(),
        ]);
        resources.push({ stream, timer });
        globalThis.__notesBuddyDisplayStream = stream;
        return stream;
      };

      Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
        configurable: true,
        value: async () => {
          captureCalls.push("microphone");
          return makeAudioStream(310);
        },
      });
      Object.defineProperty(navigator.mediaDevices, "getDisplayMedia", {
        configurable: true,
        value: async (options) => {
          captureCalls.push("meeting");
          displayOptions.push(options);
          return makeDisplayStream();
        },
      });
      Object.defineProperty(globalThis, "SpeechRecognition", {
        configurable: true,
        value: undefined,
      });
      Object.defineProperty(globalThis, "webkitSpeechRecognition", {
        configurable: true,
        value: undefined,
      });
      globalThis.__notesBuddyTestMedia = {
        captureCalls,
        displayOptions,
        stopDisplay() {
          const tracks =
            globalThis.__notesBuddyDisplayStream?.getTracks() || [];
          // MediaStreamTrack.stop() itself does not emit "ended"; browser UI
          // termination does, so dispatch it to model that external event.
          tracks
            .find((track) => track.kind === "video")
            ?.dispatchEvent(new Event("ended"));
          tracks.forEach((track) => track.stop());
        },
        dispose() {
          for (const resource of resources) {
            clearInterval(resource.timer);
            resource.stream?.getTracks().forEach((track) => track.stop());
            try {
              resource.oscillator?.stop();
            } catch {
              // Already stopped.
            }
            resource.context?.close();
          }
        },
      };
    },
    {
      shouldDenyMeeting: denyMeeting,
      shouldIncludeMeetingAudio: meetingAudio,
      shouldEmitMeetingSignal: meetingSignal,
      selectedDisplaySurface: displaySurface,
    },
  );
}

async function completeOnboarding(
  page,
  name = "Browser Tester",
  { handleCompanion = true } = {},
) {
  const setupName = page.locator("[data-input='profile-setup-name']");
  if (await setupName.isVisible()) {
    await setupName.fill(name);
    await page.locator("[data-form='profile-setup']").evaluate((form) =>
      form.requestSubmit(),
    );
  }
  await page.locator(".home-view").waitFor();
  if (handleCompanion) {
    const defer = page.locator("[data-action='defer-companion-setup']");
    if (await defer.isVisible()) {
      await defer.click();
    }
  }
}

async function idbAssets(page) {
  return page.evaluate(
    () =>
      new Promise((resolve, reject) => {
        const request = indexedDB.open("notesbuddy-audio", 1);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
          const database = request.result;
          const transaction = database.transaction("recordings", "readonly");
          const store = transaction.objectStore("recordings");
          const keysRequest = store.getAllKeys();
          const valuesRequest = store.getAll();
          transaction.oncomplete = () => {
            resolve(
              keysRequest.result.map((key, index) => ({
                key,
                size: valuesRequest.result[index]?.size || 0,
                type: valuesRequest.result[index]?.type || "",
              })),
            );
            database.close();
          };
          transaction.onerror = () => reject(transaction.error);
        };
      }),
  );
}

async function playSelectedRecording(page, source) {
  await page
    .locator(`[data-action='select-recording-source'][data-id='${source}']`)
    .click();
  const player = page.locator("audio[data-audio-id]");
  await page.waitForFunction(
    () => Boolean(document.querySelector("audio[data-audio-id]")?.src),
  );
  const result = await player.evaluate(async (audio) => {
    audio.muted = true;
    await audio.play();
    await new Promise((resolve) => setTimeout(resolve, 450));
    const snapshot = {
      currentTime: audio.currentTime,
      paused: audio.paused,
      error: audio.error?.message || null,
    };
    audio.pause();
    return snapshot;
  });
  assert.equal(result.error, null, `${source} recording has a media error`);
  assert.ok(
    result.currentTime > 0,
    `${source} recording should advance during playback`,
  );
}

async function runHostedClientWorkflow(browser, baseUrl) {
  const context = await browser.newContext();
  const page = await context.newPage();
  const hostedEndpoint = "https://transcribe.notesbuddy.test";
  let healthCalls = 0;
  let sessionCalls = 0;
  let jobCalls = 0;
  let receivedSessionToken = "";

  await page.route("**/src/runtime-config.js", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/javascript; charset=utf-8",
      body: `globalThis.NotesBuddyRuntime = Object.freeze({ transcriptionMode: "hosted", transcriptionEndpoint: "${hostedEndpoint}" });`,
    });
  });
  await page.route(`${hostedEndpoint}/v1/**`, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const headers = {
      "access-control-allow-origin": baseUrl,
      "access-control-allow-methods": "GET,POST,DELETE,OPTIONS",
      "access-control-allow-headers":
        "Content-Type,X-NotesBuddy-Session-Token",
      "content-type": "application/json",
    };
    if (request.method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers, body: "" });
      return;
    }
    if (pathname === "/v1/health") {
      healthCalls += 1;
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({
          status: "ok",
          access: "anonymous-session",
          engine: "hosted-test",
        }),
      });
      return;
    }
    if (pathname === "/v1/sessions") {
      sessionCalls += 1;
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({
          sessionToken: "browser-anonymous-session",
          expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
        }),
      });
      return;
    }
    if (pathname === "/v1/transcriptions") {
      jobCalls += 1;
      receivedSessionToken =
        request.headers()["x-notesbuddy-session-token"] || "";
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({
          jobId: "job-hosted-browser",
          status: "queued",
        }),
      });
      return;
    }
    await route.fulfill({ status: 404, headers, body: "{}" });
  });

  await page.goto(baseUrl);
  await completeOnboarding(page, "Hosted Browser Tester");
  await page.locator("[data-action='settings']").first().click();
  await page.locator("[data-panel='settings']").waitFor();
  await page
    .locator(".settings-section", { hasText: "Online speaker transcription" })
    .waitFor();
  assert.equal(
    await page.locator("[data-setting='transcriptionToken']").count(),
    0,
    "hosted users must not see a pairing-token field",
  );
  assert.equal(
    await page.locator("[data-setting='transcriptionEndpoint']").count(),
    0,
    "hosted users must not configure a service URL",
  );
  await page.locator("[data-action='test-transcription-service']").click();
  await page
    .locator(".service-check__status--connected")
    .waitFor({ timeout: 5000 });
  assert.equal(healthCalls, 1);
  assert.equal(sessionCalls, 0, "health checks should not consume a session");

  const created = await page.evaluate(async ({ endpoint }) => {
    const client = new globalThis.NotesBuddyMeetingAudio.TranscriptionClient({
      endpoint,
      mode: "hosted",
    });
    return client.createJob({
      meetingBlob: new Blob(["remote audio"], { type: "audio/webm" }),
      metadata: { meetingId: "hosted-browser" },
    });
  }, { endpoint: hostedEndpoint });
  assert.equal(created.jobId, "job-hosted-browser");
  assert.equal(sessionCalls, 1);
  assert.equal(jobCalls, 1);
  assert.equal(receivedSessionToken, "browser-anonymous-session");
  await context.close();
}

async function runHybridCompanionWorkflow(browser, baseUrl) {
  const context = await browser.newContext();
  const page = await context.newPage();
  const localEndpoint = "http://127.0.0.1:8765";
  const hostedEndpoint = "https://transcribe.notesbuddy.test";
  const downloadUrl =
    "https://github.com/sumarahmed/AINotesBuddy/releases";
  const calls = [];
  let hostedCalls = 0;

  await page.route("**/src/runtime-config.js", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/javascript; charset=utf-8",
      body: `globalThis.NotesBuddyRuntime = Object.freeze({ transcriptionMode: "hybrid", localCompanionEndpoint: "${localEndpoint}", transcriptionEndpoint: "${hostedEndpoint}", companionDownloadUrl: "${downloadUrl}" });`,
    });
  });
  await page.route(`${localEndpoint}/v1/**`, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    calls.push({
      pathname,
      method: request.method(),
      token: request.headers()["x-notesbuddy-pairing-token"] || "",
    });
    const headers = {
      "access-control-allow-origin": baseUrl,
      "access-control-allow-methods": "GET,POST,DELETE,OPTIONS",
      "access-control-allow-headers":
        "Content-Type,X-NotesBuddy-Pairing-Token",
      "access-control-allow-private-network": "true",
      "content-type": "application/json",
    };
    if (request.method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers, body: "" });
      return;
    }
    if (pathname === "/v1/companion") {
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({
          product: "NotesBuddy Desktop Companion",
          version: "0.1.0",
          apiVersion: 1,
          status: "available",
          browserPairing: true,
          modelsReady: true,
          engine: "desktop-browser-test",
        }),
      });
      return;
    }
    if (pathname === "/v1/pairings") {
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({
          pairingToken: "automatic-browser-pairing-token-value",
          expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
        }),
      });
      return;
    }
    const accepted =
      request.headers()["x-notesbuddy-pairing-token"] ===
      "automatic-browser-pairing-token-value";
    await route.fulfill({
      status: accepted ? 200 : 401,
      headers,
      body: JSON.stringify(
        accepted
          ? { status: "ok", engine: "desktop-browser-test" }
          : { detail: "Pairing token is missing or invalid." },
      ),
    });
  });
  await page.route(`${hostedEndpoint}/v1/**`, async (route) => {
    hostedCalls += 1;
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Local mode must not call hosted API." }),
    });
  });

  await page.goto(baseUrl);
  await completeOnboarding(page, "Hybrid Companion Tester", {
    handleCompanion: false,
  });
  await page
    .getByRole("heading", { name: "Desktop companion is working" })
    .waitFor({ timeout: 5000 });
  await page
    .getByText("On-device processing active", { exact: true })
    .waitFor();
  assert.deepEqual(
    calls
      .filter(({ method }) => method !== "OPTIONS")
      .map(({ pathname }) => pathname),
    ["/v1/companion", "/v1/pairings", "/v1/health"],
  );
  assert.equal(calls.at(-1).token, "automatic-browser-pairing-token-value");
  await page.locator("[data-action='complete-companion-setup']").click();
  await page.locator(".companion-setup-backdrop").waitFor({ state: "detached" });
  let persistedSettings = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("notesbuddy-settings") || "{}"),
  );
  assert.equal(persistedSettings.companionSetupCompleted, true);
  assert.equal(persistedSettings.transcriptionToken, "");

  await page.reload();
  await page.locator(".home-view").waitFor();
  assert.equal(
    await page.locator(".companion-setup-backdrop").count(),
    0,
    "confirmed setup must stay dismissed on future visits",
  );
  await page.locator("[data-action='settings']").first().click();
  await page.locator("[data-panel='settings']").waitFor();
  await page
    .locator(".settings-section", {
      hasText: "Desktop speaker transcription",
    })
    .waitFor();

  assert.equal(
    await page.locator("[data-setting='transcriptionToken']").count(),
    0,
    "automatic desktop users must not see a pairing-token field",
  );
  assert.equal(
    await page.locator("[data-setting='transcriptionEndpoint']").count(),
    0,
    "automatic desktop users must not edit the loopback URL",
  );
  assert.equal(
    await page
      .locator(`a[href="${downloadUrl}"]`)
      .getAttribute("target"),
    "_blank",
  );
  assert.equal(
    hostedCalls,
    0,
    "a connected companion must not depend on the hosted API",
  );
  persistedSettings = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("notesbuddy-settings") || "{}"),
  );
  assert.equal(
    persistedSettings.transcriptionToken,
    "",
    "automatic pairing tokens must never be persisted",
  );
  await context.close();
}

async function runHybridFallbackWorkflow(browser, baseUrl) {
  const context = await browser.newContext();
  const page = await context.newPage();
  const unavailableEndpoint = "http://127.0.0.1:8877";
  let discoveryCalls = 0;

  await page.route("**/src/runtime-config.js", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/javascript; charset=utf-8",
      body: `globalThis.NotesBuddyRuntime = Object.freeze({ transcriptionMode: "hybrid", localCompanionEndpoint: "${unavailableEndpoint}", transcriptionEndpoint: "https://transcribe.notesbuddy.test", companionDownloadUrl: "https://github.com/sumarahmed/AINotesBuddy/releases" });`,
    });
  });
  await page.route(`${unavailableEndpoint}/v1/**`, async (route) => {
    discoveryCalls += 1;
    if (discoveryCalls > 1) {
      await route.abort("connectionrefused");
      return;
    }
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Companion is not running." }),
    });
  });

  await page.goto(baseUrl);
  await completeOnboarding(page, "Hybrid Fallback Tester", {
    handleCompanion: false,
  });
  await page
    .getByRole("heading", { name: "Install the Windows companion" })
    .waitFor();
  assert.equal(
    await page
      .locator(
        "a[href='https://github.com/sumarahmed/AINotesBuddy/releases']",
      )
      .getAttribute("target"),
    "_blank",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  const setupLayout = await page.evaluate(() => {
    const card = document.querySelector(".companion-setup-card");
    const bounds = card?.getBoundingClientRect();
    return {
      viewportWidth: innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      cardLeft: Math.floor(bounds?.left || 0),
      cardRight: Math.ceil(bounds?.right || 0),
    };
  });
  assert.ok(
    setupLayout.documentWidth <= setupLayout.viewportWidth,
    "companion onboarding must not overflow a mobile viewport",
  );
  assert.ok(
    setupLayout.cardLeft >= 0 &&
      setupLayout.cardRight <= setupLayout.viewportWidth,
    "companion onboarding card must remain fully reachable on mobile",
  );
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.locator("[data-action='check-companion-setup']").click();
  await page
    .getByText(
      "Start NotesBuddy Companion and allow Local network access for this site in your browser's address-bar site controls, then check again.",
      { exact: true },
    )
    .waitFor();
  await page.locator("[data-action='defer-companion-setup']").click();
  await page.locator(".companion-setup-backdrop").waitFor({ state: "detached" });
  const deferred = await page.evaluate(() => ({
    session:
      sessionStorage.getItem("notesbuddy-companion-setup-deferred") === "true",
    completed: JSON.parse(
      localStorage.getItem("notesbuddy-settings") || "{}",
    ).companionSetupCompleted,
  }));
  assert.equal(deferred.session, true);
  assert.equal(deferred.completed, false);

  await page.reload();
  await page.locator(".home-view").waitFor();
  assert.equal(
    await page.locator(".companion-setup-backdrop").count(),
    0,
    "online-for-now must suppress setup only for this browser session",
  );
  await page.locator("[data-action='settings']").first().click();
  await page.locator("[data-panel='settings']").waitFor();
  await page
    .locator(".service-check__status--fallback")
    .waitFor({ timeout: 5000 });
  await page.getByText("The online fallback is active.").waitFor();

  assert.equal(discoveryCalls, 2);
  assert.equal(
    await page.locator("[data-setting='transcriptionToken']").count(),
    0,
  );
  assert.equal(
    await page.locator("[data-action='connect-companion']").count(),
    1,
  );
  await context.close();
}

async function runMainWorkflow(browser, baseUrl) {
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => {
    if (request.url().includes("127.0.0.1:8765")) {
      failedRequests.push(
        `${request.method()} ${request.url()}: ${request.failure()?.errorText}`,
      );
    }
  });
  await installSyntheticMedia(page);
  await page.route("**/src/runtime-config.js", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/javascript; charset=utf-8",
      body: `globalThis.NotesBuddyRuntime = Object.freeze({ transcriptionMode: "local", transcriptionEndpoint: "http://127.0.0.1:8765" });`,
    });
  });

  let multipartBody = "";
  let healthRouteCalls = 0;
  await page.route("**/v1/**", async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    healthRouteCalls += pathname === "/v1/health" ? 1 : 0;
    const headers = {
      "access-control-allow-origin": baseUrl,
      "access-control-allow-methods": "GET,POST,DELETE,OPTIONS",
      "access-control-allow-headers":
        "Content-Type,X-NotesBuddy-Pairing-Token",
      "access-control-allow-private-network": "true",
      "content-type": "application/json",
    };
    if (request.method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers, body: "" });
      return;
    }
    if (request.method() === "POST") {
      multipartBody = request.postData() || "";
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({
          jobId: "job-browser-smoke",
          status: "queued",
          engine: "synthetic-test",
        }),
      });
      return;
    }
    if (request.method() === "DELETE") {
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({
          jobId: "job-browser-smoke",
          status: "cancelled",
        }),
      });
      return;
    }
    if (pathname === "/v1/health") {
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({ status: "ok", engine: "synthetic-test" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      headers,
      body: JSON.stringify({
        jobId: "job-browser-smoke",
        status: "completed",
        progress: 1,
        language: "en",
        segments: [
          {
            id: "local-segment",
            source: "microphone",
            speakerId: "local-user",
            startMs: 0,
            endMs: 900,
            text: "I will send the revised proposal.",
            confidence: 0.96,
          },
          {
            id: "remote-one",
            source: "meeting",
            speakerId: "remote-1",
            startMs: 1000,
            endMs: 2100,
            text: "I will review it tomorrow.",
            confidence: 0.94,
          },
          {
            id: "remote-two",
            source: "meeting",
            speakerId: "remote-2",
            startMs: 2200,
            endMs: 3400,
            text: "This complete transcript sentence is intentionally longer than eighty characters to catch unwanted truncation.",
            confidence: 0.92,
          },
        ],
      }),
    });
  });

  await page.goto(baseUrl);
  await completeOnboarding(page);
  await page.locator("[data-action='capture']").first().click();
  await page.locator("[data-action='start-capture']").click();
  await page
    .locator("[data-source-status='mixed']")
    .filter({ hasText: "recording" })
    .waitFor();
  await page
    .locator("[data-source-status='meeting']")
    .filter({ hasText: "sound detected" })
    .waitFor();
  assert.deepEqual(
    await page.evaluate(() => globalThis.__notesBuddyTestMedia.captureCalls),
    ["meeting", "microphone"],
    "display capture must be invoked before awaiting microphone permission",
  );
  const displayOptions = await page.evaluate(
    () => globalThis.__notesBuddyTestMedia.displayOptions[0],
  );
  assert.equal(displayOptions.audio.suppressLocalAudioPlayback, false);
  assert.equal(displayOptions.systemAudio, "include");
  assert.equal(displayOptions.windowAudio, "system");
  assert.equal(displayOptions.monitorTypeSurfaces, "include");
  assert.equal(displayOptions.selfBrowserSurface, "exclude");

  await page.waitForTimeout(400);
  const dockBefore = await page.locator(".recording-dock").boundingBox();
  await page.waitForTimeout(1100);
  const dockAfter = await page.locator(".recording-dock").boundingBox();
  assert.ok(dockBefore && dockAfter, "recording dock should remain visible");
  assert.equal(
    Math.round(dockBefore.y),
    Math.round(dockAfter.y),
    "recording controls should not jump while the timer updates",
  );

  await page.locator(".capture-header [data-action='settings']").click();
  await page.locator("[data-panel='settings']").waitFor();
  await page.locator("[data-action='test-transcription-service']").click();
  const healthToastText = await page
    .locator(".toast")
    .last()
    .textContent({ timeout: 1500 })
    .catch(() => "");
  try {
    await page
      .locator(".service-check__status--connected")
      .waitFor({ timeout: 5000 });
  } catch (error) {
    const statusText = await page
      .locator(".service-check__status")
      .textContent()
      .catch(() => "missing");
    const toastText = await page
      .locator(".toast-region")
      .textContent()
      .catch(() => "");
    const directFetch = await page.evaluate(async () => {
      const endpoint = document.querySelector(
        "[data-setting='transcriptionEndpoint']",
      )?.value;
      try {
        const response = await fetch(`${endpoint}/v1/health`);
        return {
          endpoint,
          status: response.status,
          payload: await response.text(),
        };
      } catch (fetchError) {
        return { endpoint, error: String(fetchError) };
      }
    });
    throw new Error(
      `Companion health UI did not connect (routes=${healthRouteCalls}, status=${statusText}, initialToast=${healthToastText}, toast=${toastText}, direct=${JSON.stringify(directFetch)}, failed=${failedRequests.join(" | ")}, console=${consoleErrors.join(" | ")}): ${error.message}`,
    );
  }
  await page.locator("[data-action='close-settings']").last().click();
  await page.locator("[data-source-status='mixed']").waitFor();

  await page.locator("[data-action='pause-capture']").click();
  await page.locator(".recording-status--paused").waitFor();
  await page.waitForTimeout(200);
  await page.locator("[data-action='pause-capture']").click();
  await page.locator(".recording-status--recording").waitFor();
  await page.waitForTimeout(900);
  await page.locator("[data-action='finish-capture']").click();
  await page.locator(".detail-view").waitFor({ timeout: 10000 });

  const assets = await idbAssets(page);
  assert.equal(assets.length, 3, "three synchronized assets should be stored");
  assert.ok(assets.every((asset) => asset.size > 0), "assets must contain audio");
  assert.deepEqual(
    assets.map((asset) => String(asset.key).split(":").at(-1)).sort(),
    ["meeting", "microphone", "mixed"],
  );

  for (const source of ["mixed", "microphone", "meeting"]) {
    await playSelectedRecording(page, source);
  }

  await page.reload();
  await page.locator("[data-action='meeting']").first().click();
  for (const source of ["mixed", "microphone", "meeting"]) {
    await playSelectedRecording(page, source);
  }

  await page.locator("[data-action='tab'][data-id='transcript']").click();
  await page.locator("[data-action='transcribe-meeting']").click();
  await page
    .getByRole("heading", { name: "Speaker transcript ready" })
    .waitFor({ timeout: 10000 });
  assert.match(multipartBody, /name="microphone"/);
  assert.match(multipartBody, /name="meeting"/);
  assert.match(multipartBody, /name="mixed"/);
  await page.getByText("You", { exact: true }).first().waitFor();
  await page.getByText("Speaker 1", { exact: true }).first().waitFor();
  await page.getByText("Speaker 2", { exact: true }).first().waitFor();
  await page
    .getByText(
      "This complete transcript sentence is intentionally longer than eighty characters to catch unwanted truncation.",
      { exact: true },
    )
    .waitFor();

  await page
    .locator("[data-action='focus-speaker'][data-id='remote-1']")
    .first()
    .click();
  const firstRemoteInput = page
    .locator("[data-input='speaker-name'][data-id='remote-1']");
  assert.equal(
    await firstRemoteInput.evaluate((input) => input === document.activeElement),
    true,
    "clicking a transcript speaker label should focus its rename input",
  );
  await firstRemoteInput.fill("Jordan Lee");
  await page
    .locator("[data-speaker-label-id='remote-1']")
    .filter({ hasText: "Jordan Lee" })
    .waitFor();
  await page.locator("[data-input='transcript-search']").fill("Jordan Lee");
  assert.equal(
    await page.locator(".transcript-row--document").count(),
    1,
    "speaker rename should be searchable",
  );
  await page.locator("[data-input='transcript-search']").fill("");

  for (const viewport of [
    { width: 390, height: 844 },
    { width: 320, height: 720 },
  ]) {
    await page.setViewportSize(viewport);
    const layout = await page.evaluate(() => ({
      viewportWidth: innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      speakerInputRight: Math.ceil(
        document
          .querySelector("[data-input='speaker-name']")
          ?.getBoundingClientRect().right || 0,
      ),
    }));
    assert.ok(
      layout.documentWidth <= layout.viewportWidth,
      `transcript should not overflow at ${viewport.width}px`,
    );
    assert.ok(
      layout.speakerInputRight <= layout.viewportWidth,
      `speaker rename input should remain within ${viewport.width}px`,
    );
  }
  await page.setViewportSize({ width: 1280, height: 720 });

  const downloadPromise = page.waitForEvent("download");
  await page.locator("[data-action='export']").first().click();
  const download = await downloadPromise;
  const exported = await fs.readFile(await download.path(), "utf8");
  assert.match(exported, /Jordan Lee/);
  assert.match(exported, /You/);

  assert.deepEqual(pageErrors, [], `page errors: ${pageErrors.join(" | ")}`);
  assert.deepEqual(
    consoleErrors.filter(
      (message) =>
        !message.includes("favicon") && !message.includes("Failed to load"),
    ),
    [],
    `console errors: ${consoleErrors.join(" | ")}`,
  );
  await page.evaluate(() => globalThis.__notesBuddyTestMedia.dispose());
  await context.close();
}

async function runMeetingDeniedFallback(browser, baseUrl) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await installSyntheticMedia(page, { denyMeeting: true });
  await page.goto(baseUrl);
  await completeOnboarding(page, "Fallback Tester");
  await page.locator("[data-action='capture']").first().click();
  await page.locator("[data-action='start-capture']").click();
  await page
    .locator("[data-source-status='microphone']")
    .filter({ hasText: "recording" })
    .waitFor();
  await page.waitForTimeout(800);
  await page.locator("[data-action='finish-capture']").click();
  await page.locator(".detail-view").waitFor({ timeout: 10000 });
  assert.equal(
    await page.locator("[data-action='select-recording-source']").count(),
    2,
    "microphone fallback should keep microphone and mixed recordings",
  );
  assert.equal(
    await page
      .locator("[data-action='select-recording-source'][data-id='meeting']")
      .count(),
    0,
  );
  await playSelectedRecording(page, "microphone");
  await context.close();
}

async function runMeetingOnlyCapture(browser, baseUrl) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await installSyntheticMedia(page);
  await page.goto(baseUrl);
  await completeOnboarding(page, "Meeting Listener");
  await page.locator("[data-action='capture']").first().click();
  await page.locator("[data-action='toggle-mic']").click();
  await page.locator("[data-action='start-capture']").click();
  await page
    .locator("[data-source-status='meeting']")
    .filter({ hasText: "sound detected" })
    .waitFor();
  await page.waitForTimeout(800);
  await page.locator("[data-action='finish-capture']").click();
  await page.locator(".detail-view").waitFor({ timeout: 10000 });
  assert.equal(
    await page
      .locator("[data-action='select-recording-source'][data-id='microphone']")
      .count(),
    0,
  );
  assert.equal(
    await page.locator("[data-action='select-recording-source']").count(),
    2,
    "meeting-only capture should retain meeting and mixed assets",
  );
  await playSelectedRecording(page, "meeting");
  await context.close();
}

async function runMeetingTrackMissing(browser, baseUrl) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await installSyntheticMedia(page, {
    meetingAudio: false,
    displaySurface: "window",
  });
  await page.goto(baseUrl);
  await completeOnboarding(page, "Missing Audio Tester");
  await page.locator("[data-action='capture']").first().click();
  await page.locator("[data-action='start-capture']").click();
  await page
    .locator("[data-source-status='microphone']")
    .filter({ hasText: "recording" })
    .waitFor();
  await page
    .getByText(
      "No audio was received from the shared window. For Teams desktop, choose Entire Screen and turn on Also share system audio.",
      { exact: true },
    )
    .waitFor();
  await page
    .locator("[data-source-status='meeting']")
    .filter({ hasText: "unavailable" })
    .waitFor();
  await page.waitForTimeout(700);
  await page.locator("[data-action='finish-capture']").click();
  await page.locator(".detail-view").waitFor({ timeout: 10000 });
  assert.equal(
    await page.locator("[data-action='select-recording-source']").count(),
    2,
    "a missing meeting track should preserve microphone and mixed audio",
  );
  assert.equal(
    await page
      .locator("[data-action='select-recording-source'][data-id='meeting']")
      .count(),
    0,
  );
  await context.close();
}

async function runSilentMeetingTrack(browser, baseUrl) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await installSyntheticMedia(page, {
    meetingSignal: false,
    displaySurface: "window",
  });
  await page.goto(baseUrl);
  await completeOnboarding(page, "Silent Audio Tester");
  await page.locator("[data-action='capture']").first().click();
  await page.locator("[data-action='start-capture']").click();
  await page
    .locator("[data-source-status='meeting']")
    .filter({ hasText: "waiting for sound" })
    .waitFor();
  await page
    .locator("[data-source-status='meeting']")
    .filter({ hasText: "no sound detected" })
    .waitFor({ timeout: 8000 });
  await page
    .locator(".capture-source-warning")
    .filter({
      hasText:
        "No sound is arriving from the Teams window. Stop capture, choose Entire Screen, and turn on Also share system audio.",
    })
    .waitFor();
  await page.locator("[data-action='finish-capture']").click();
  await page.locator(".detail-view").waitFor({ timeout: 10000 });
  assert.equal(
    await page
      .locator("[data-action='select-recording-source'][data-id='meeting']")
      .count(),
    1,
    "a silent but valid meeting track should remain available for review",
  );
  await context.close();
}

async function runUnexpectedMeetingStop(browser, baseUrl) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await installSyntheticMedia(page);
  await page.goto(baseUrl);
  await completeOnboarding(page, "Continuity Tester");
  await page.locator("[data-action='capture']").first().click();
  await page.locator("[data-action='start-capture']").click();
  await page
    .locator("[data-source-status='mixed']")
    .filter({ hasText: "recording" })
    .waitFor();
  await page.evaluate(() => globalThis.__notesBuddyTestMedia.stopDisplay());
  await page
    .getByText(
      "Meeting audio sharing stopped. Microphone recording is continuing.",
      { exact: true },
    )
    .waitFor();
  await page
    .locator("[data-source-status='microphone']")
    .filter({ hasText: "recording" })
    .waitFor();
  await page.waitForTimeout(500);
  await page.locator("[data-action='finish-capture']").click();
  await page.locator(".detail-view").waitFor({ timeout: 10000 });
  await playSelectedRecording(page, "microphone");
  await context.close();
}

async function runDirectFileLoad(browser) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(pathToFileURL(path.join(projectRoot, "index.html")).href);
  await completeOnboarding(page, "Direct File Tester");
  await page
    .getByRole("heading", { name: /Private meeting memory for Direct/ })
    .waitFor();
  assert.equal(
    await page.locator("link[href='./src/styles.css']").count(),
    1,
  );
  await context.close();
}

(async () => {
  const server = staticServer();
  const baseUrl = await listen(server);
  const executablePath =
    process.env.NOTESBUDDY_CHROME_PATH ||
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
  let browser;
  try {
    browser = await chromium.launch({
      executablePath,
      headless: true,
      args: [
        "--autoplay-policy=no-user-gesture-required",
        "--use-fake-ui-for-media-stream",
        "--no-default-browser-check",
      ],
    });
    await runMainWorkflow(browser, baseUrl);
    await runMeetingDeniedFallback(browser, baseUrl);
    await runMeetingOnlyCapture(browser, baseUrl);
    await runMeetingTrackMissing(browser, baseUrl);
    await runSilentMeetingTrack(browser, baseUrl);
    await runUnexpectedMeetingStop(browser, baseUrl);
    await runDirectFileLoad(browser);
    await runHostedClientWorkflow(browser, baseUrl);
    await runHybridCompanionWorkflow(browser, baseUrl);
    await runHybridFallbackWorkflow(browser, baseUrl);
    console.log(
      "Browser smoke passed: direct-file load, first-entry installer onboarding and confirmation, synchronized and meeting-only capture, system/window audio request hints, live meeting-sound detection, missing/silent meeting-audio guidance, stable controls, three-source persistence/playback, reload, local, hosted, and hybrid transcription clients, automatic desktop pairing, hosted fallback, anonymous sessions, rename/search/export, mic fallback, and interrupted-share continuity.",
    );
  } finally {
    await browser?.close();
    await close(server);
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
