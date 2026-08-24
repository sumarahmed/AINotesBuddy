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

function syntheticWavBuffer({ durationMs = 1600, sampleRate = 16000 } = {}) {
  const channels = 2;
  const bitsPerSample = 16;
  const frameCount = Math.floor((durationMs / 1000) * sampleRate);
  const dataSize = frameCount * channels * (bitsPerSample / 8);
  const output = Buffer.alloc(44 + dataSize);
  output.write("RIFF", 0);
  output.writeUInt32LE(36 + dataSize, 4);
  output.write("WAVE", 8);
  output.write("fmt ", 12);
  output.writeUInt32LE(16, 16);
  output.writeUInt16LE(1, 20);
  output.writeUInt16LE(channels, 22);
  output.writeUInt32LE(sampleRate, 24);
  output.writeUInt32LE(sampleRate * channels * 2, 28);
  output.writeUInt16LE(channels * 2, 32);
  output.writeUInt16LE(bitsPerSample, 34);
  output.write("data", 36);
  output.writeUInt32LE(dataSize, 40);
  for (let frame = 0; frame < frameCount; frame += 1) {
    const sample = Math.round(
      Math.sin((frame / sampleRate) * Math.PI * 2 * 440) * 3500,
    );
    for (let channel = 0; channel < channels; channel += 1) {
      output.writeInt16LE(sample, 44 + (frame * channels + channel) * 2);
    }
  }
  return output;
}

async function installSyntheticMedia(
  page,
  {
    denyMeeting = false,
    meetingAudio = true,
    meetingSignal = true,
    displaySurface = "window",
    speechRecognition = false,
  } = {},
) {
  await page.addInitScript(
    ({
      shouldDenyMeeting,
      shouldIncludeMeetingAudio,
      shouldEmitMeetingSignal,
      selectedDisplaySurface,
      shouldEnableSpeechRecognition,
    }) => {
      const resources = [];
      const captureCalls = [];
      const displayOptions = [];
      let meetingGain = null;
      let activeRecognition = null;
      const makeAudioStream = (frequency, gainValue = 0.06) => {
        const AudioContextClass =
          globalThis.AudioContext || globalThis.webkitAudioContext;
        const context = new AudioContextClass();
        const oscillator = context.createOscillator();
        const gain = context.createGain();
        const destination = context.createMediaStreamDestination();
        oscillator.frequency.value = frequency;
        gain.gain.value = gainValue;
        if (frequency === 620) meetingGain = gain;
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
      class SyntheticSpeechRecognition {
        start() {
          activeRecognition = this;
          queueMicrotask(() => this.onstart?.());
        }

        stop() {
          if (activeRecognition === this) activeRecognition = null;
          this.onend?.();
        }

        abort() {
          this.stop();
        }
      }
      const RecognitionClass = shouldEnableSpeechRecognition
        ? SyntheticSpeechRecognition
        : undefined;
      Object.defineProperty(globalThis, "SpeechRecognition", {
        configurable: true,
        value: RecognitionClass,
      });
      Object.defineProperty(globalThis, "webkitSpeechRecognition", {
        configurable: true,
        value: RecognitionClass,
      });
      globalThis.__notesBuddyTestMedia = {
        captureCalls,
        displayOptions,
        setMeetingSignal(enabled) {
          if (meetingGain) meetingGain.gain.value = enabled ? 0.06 : 0;
        },
        emitSpeech(text, isFinal = true) {
          if (!activeRecognition) {
            throw new Error("Synthetic speech recognition is not active.");
          }
          const result = [{ transcript: text, confidence: 0.96 }];
          result.isFinal = isFinal;
          activeRecognition.onresult?.({ resultIndex: 0, results: [result] });
        },
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
      shouldEnableSpeechRecognition: speechRecognition,
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
    "https://github.com/sumarahmed/AINotesBuddy/releases/download/companion-v2026.08.3/NotesBuddyCompanion-Setup-2026.08.3.exe";
  const calls = [];
  let hostedCalls = 0;
  const systemAudioWav = syntheticWavBuffer();

  await installSyntheticMedia(page);

  await page.route("**/src/runtime-config.js", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/javascript; charset=utf-8",
      body: `globalThis.NotesBuddyRuntime = Object.freeze({ appVersion: "2026.08.4", latestCompanionVersion: "2026.08.3", transcriptionMode: "hybrid", localCompanionEndpoint: "${localEndpoint}", transcriptionEndpoint: "${hostedEndpoint}", companionDownloadUrl: "${downloadUrl}" });`,
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
          version: "2026.08.3",
          apiVersion: 1,
          status: "available",
          browserPairing: true,
          modelsReady: true,
          systemAudioCapture: true,
          systemAudioBackend: "windows-wasapi-loopback",
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
    if (!accepted) {
      await route.fulfill({
        status: 401,
        headers,
        body: JSON.stringify({ detail: "Pairing token is missing or invalid." }),
      });
      return;
    }
    if (pathname === "/v1/system-audio/captures") {
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({
          captureId: "capture-browser-system-audio",
          status: "recording",
          deviceName: "Synthetic Windows output",
          signalDetected: false,
          durationMs: 0,
        }),
      });
      return;
    }
    if (pathname.endsWith("/stop")) {
      await route.fulfill({
        status: 200,
        headers: { ...headers, "content-type": "audio/wav" },
        body: systemAudioWav,
      });
      return;
    }
    if (
      pathname.endsWith("/pause") ||
      pathname.endsWith("/resume")
    ) {
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({
          captureId: "capture-browser-system-audio",
          status: pathname.endsWith("/pause") ? "paused" : "recording",
          signalDetected: true,
          durationMs: 700,
        }),
      });
      return;
    }
    if (pathname.startsWith("/v1/system-audio/captures/")) {
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({
          captureId: "capture-browser-system-audio",
          status: "recording",
          deviceName: "Synthetic Windows output",
          signalDetected: true,
          durationMs: 900,
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      headers,
      body: JSON.stringify({
        status: "ok",
        engine: "desktop-browser-test",
        systemAudioCapture: true,
      }),
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
  await page.getByText("Version 2026.08.4", { exact: true }).waitFor();
  assert.equal(
    await page.locator(".companion-update-banner").count(),
    0,
    "the current companion must not trigger an update warning",
  );
  let persistedSettings = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("notesbuddy-settings") || "{}"),
  );
  assert.equal(persistedSettings.companionSetupCompleted, true);
  assert.equal(persistedSettings.transcriptionToken, "");

  await page.locator("[data-action='capture']").first().click();
  await page.getByText("Windows output via companion", { exact: true }).waitFor();
  await page.locator("[data-action='start-capture']").click();
  await page
    .locator("[data-source-status='meeting']")
    .filter({ hasText: "sound detected" })
    .waitFor({ timeout: 5000 });
  await page.getByText("Listening to Synthetic Windows output").waitFor();
  assert.deepEqual(
    await page.evaluate(() => globalThis.__notesBuddyTestMedia.captureCalls),
    ["microphone"],
    "companion capture must not open the browser display-share picker",
  );
  await page.locator("[data-action='pause-capture']").click();
  await page.locator(".recording-status--paused").waitFor();
  await page.locator("[data-action='pause-capture']").click();
  await page.locator(".recording-status--recording").waitFor();
  await page.waitForTimeout(900);
  await page.locator("[data-action='finish-capture']").click();
  await page.locator(".detail-view").waitFor({ timeout: 10000 });
  await page
    .locator(
      "[data-action='select-recording-source'][data-id='meeting'][aria-pressed='true']",
    )
    .waitFor();
  assert.deepEqual(
    (await idbAssets(page))
      .map(({ key }) => String(key).split(":").at(-1))
      .sort(),
    ["meeting", "microphone"],
    "companion capture should keep isolated microphone and Windows output",
  );
  await playSelectedRecording(page, "meeting");

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
  await page.evaluate(() => globalThis.__notesBuddyTestMedia.dispose());
  await context.close();
}

async function runExistingUserUpdateNotification(browser, baseUrl) {
  const context = await browser.newContext();
  const page = await context.newPage();
  const localEndpoint = "http://127.0.0.1:8765";
  const downloadUrl =
    "https://github.com/sumarahmed/AINotesBuddy/releases/download/companion-v2026.08.3/NotesBuddyCompanion-Setup-2026.08.3.exe";

  await page.addInitScript(() => {
    localStorage.setItem(
      "notesbuddy-profile",
      JSON.stringify({
        id: "profile-existing-update-user",
        name: "Existing Update User",
        initials: "EU",
        createdAt: "2026-08-01T00:00:00.000Z",
        updatedAt: "2026-08-01T00:00:00.000Z",
      }),
    );
    localStorage.setItem(
      "notesbuddy-settings",
      JSON.stringify({
        companionSetupCompleted: true,
        transcriptionMode: "hosted",
        transcriptionEndpoint: "https://transcribe.notesbuddy.test",
        transcriptionToken: "",
      }),
    );
  });
  await page.route("**/src/runtime-config.js", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/javascript; charset=utf-8",
      body: `globalThis.NotesBuddyRuntime = Object.freeze({ appVersion: "2026.08.4", latestCompanionVersion: "2026.08.3", transcriptionMode: "hybrid", localCompanionEndpoint: "${localEndpoint}", transcriptionEndpoint: "https://transcribe.notesbuddy.test", companionDownloadUrl: "${downloadUrl}" });`,
    });
  });
  await page.route(`${localEndpoint}/v1/**`, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const headers = {
      "access-control-allow-origin": baseUrl,
      "access-control-allow-methods": "GET,POST,OPTIONS",
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
          version: "0.1.2",
          apiVersion: 1,
          status: "available",
          browserPairing: true,
          modelsReady: true,
          systemAudioCapture: false,
          engine: "outdated-browser-test",
        }),
      });
      return;
    }
    if (pathname === "/v1/pairings") {
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({
          pairingToken: "outdated-companion-pairing-token",
          expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      headers,
      body: JSON.stringify({ status: "ok", engine: "outdated-browser-test" }),
    });
  });

  await page.goto(baseUrl);
  await page.locator(".home-view").waitFor();
  const banner = page.locator(".companion-update-banner");
  await banner.waitFor({ timeout: 5000 });
  await banner.getByText("Companion update available", { exact: true }).waitFor();
  await banner.getByText(/You have 0\.1\.2\. Update to 2026\.08\.3/).waitFor();
  assert.equal(await banner.getAttribute("role"), "alert");
  assert.equal(await banner.getAttribute("aria-live"), "assertive");
  const desktopBannerLayout = await banner.evaluate((element) => {
    const bounds = element.getBoundingClientRect();
    return {
      left: bounds.left,
      right: bounds.right,
      viewportWidth: innerWidth,
      messageFontSize: Number.parseFloat(
        getComputedStyle(element.querySelector("p")).fontSize,
      ),
    };
  });
  assert.ok(desktopBannerLayout.left >= 0);
  assert.ok(desktopBannerLayout.right <= desktopBannerLayout.viewportWidth);
  assert.ok(
    desktopBannerLayout.messageFontSize >= 11,
    "the update warning must remain readable",
  );
  assert.equal(
    await page.locator(".companion-setup-backdrop").count(),
    0,
    "an existing user must receive a banner without repeating onboarding",
  );

  await page.locator("[data-action='settings']").first().click();
  await page.locator(".service-check__status--update").waitFor();
  await page
    .locator("[data-panel='settings']")
    .getByRole("link", { name: "Download update", exact: true })
    .waitFor();
  await page.locator("[data-action='close-settings']").last().click();
  await banner.locator("[data-action='dismiss-companion-update']").click();
  await banner.waitFor({ state: "detached" });

  await page.reload();
  await page.locator(".companion-update-banner").waitFor({ timeout: 5000 });
  await page.setViewportSize({ width: 390, height: 844 });
  const mobileBannerLayout = await page
    .locator(".companion-update-banner")
    .evaluate((element) => {
      const bounds = element.getBoundingClientRect();
      return {
        left: bounds.left,
        right: bounds.right,
        viewportWidth: innerWidth,
        documentWidth: document.documentElement.scrollWidth,
      };
    });
  assert.ok(mobileBannerLayout.left >= 0);
  assert.ok(mobileBannerLayout.right <= mobileBannerLayout.viewportWidth);
  assert.ok(mobileBannerLayout.documentWidth <= mobileBannerLayout.viewportWidth);
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
      body: `globalThis.NotesBuddyRuntime = Object.freeze({ transcriptionMode: "hybrid", localCompanionEndpoint: "${unavailableEndpoint}", transcriptionEndpoint: "https://transcribe.notesbuddy.test", companionDownloadUrl: "https://github.com/sumarahmed/AINotesBuddy/releases/download/companion-v2026.08.3/NotesBuddyCompanion-Setup-2026.08.3.exe" });`,
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
        "a[href='https://github.com/sumarahmed/AINotesBuddy/releases/download/companion-v2026.08.3/NotesBuddyCompanion-Setup-2026.08.3.exe']",
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
  let analysisBody = null;
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
      if (pathname === "/v1/analyses") {
        analysisBody = JSON.parse(request.postData() || "{}");
        await route.fulfill({
          status: 200,
          headers,
          body: JSON.stringify({
            schemaVersion: 1,
            promptVersion: 1,
            model: "synthetic-professional-analyst",
            shortSummary:
              "The meeting confirmed the revised scope and assigned follow-up on the proposal.\n\nThe team will send and review the revised proposal.",
            summarySourceSegmentIds: [
              "local-segment",
              "remote-one",
            ],
            highlights: [
              {
                text: "The revised scope was confirmed.",
                sourceSegmentIds: ["local-segment"],
              },
            ],
            decisions: [
              {
                decision: "Use the revised scope.",
                context: "The participants confirmed their agreement.",
                owner: "Browser Tester",
                sourceSegmentIds: ["local-segment"],
              },
            ],
            actionItems: [
              {
                task: "Send the revised proposal.",
                owner: "Browser Tester",
                dueDate: "Not specified",
                priority: "Medium",
                notes: "Use the confirmed scope.",
                sourceSegmentIds: ["local-segment"],
              },
              {
                task: "Review the revised proposal.",
                owner: "Speaker 1",
                dueDate: "tomorrow",
                priority: "Medium",
                notes: "Not specified",
                sourceSegmentIds: ["remote-one"],
              },
            ],
          }),
        });
        return;
      }
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
            text: "I will send the revised proposal. We agreed to use the revised scope.",
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
  assert.equal(
    await page.getByText("Review the recording and transcript", { exact: true }).count(),
    0,
    "a newly recorded meeting must not receive a generic review action",
  );

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
  assert.doesNotMatch(multipartBody, /name="mixed"/);
  await page
    .getByText("Professional analysis ready", { exact: true })
    .waitFor({ timeout: 10000 });
  assert.equal(analysisBody.meetingTitle, "Untitled meeting");
  assert.deepEqual(
    analysisBody.segments.map(({ id, speaker }) => ({ id, speaker })),
    [
      { id: "local-segment", speaker: "You" },
      { id: "remote-one", speaker: "Speaker 1" },
      { id: "remote-two", speaker: "Speaker 2" },
    ],
    "analysis must receive the complete timestamped speaker transcript",
  );
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

  await page.locator("[data-action='tab'][data-id='summary']").click();
  await page
    .locator(".decision-list")
    .getByText("Use the revised scope.", { exact: true })
    .waitFor();
  assert.equal(
    await page.locator(".action-list button").count(),
    2,
    "only transcript-grounded commitments should become action items",
  );
  const actionItems = await page.locator(".action-list button").evaluateAll(
    (buttons) =>
      buttons.map((button) => ({
        text: button.querySelector(".action-text")?.textContent?.trim(),
        owner: button.querySelector(".action-owner")?.textContent?.trim(),
        due: button.querySelector(".action-due")?.textContent?.trim() || null,
      })),
  );
  assert.deepEqual(actionItems, [
    {
      text: "Send the revised proposal.",
      owner: "Browser Tester",
      due: "Not specified",
    },
    {
      text: "Review the revised proposal.",
      owner: "Jordan Lee",
      due: "tomorrow",
    },
  ]);
  assert.equal(
    await page.getByText("Review the recording and transcript", { exact: true }).count(),
    0,
  );

  for (const viewport of [
    { width: 390, height: 844 },
    { width: 320, height: 720 },
  ]) {
    await page.setViewportSize(viewport);
    const summaryLayout = await page.evaluate(() => {
      const action = document.querySelector(".action-list button");
      return {
        viewportWidth: innerWidth,
        documentWidth: document.documentElement.scrollWidth,
        actionRight: Math.ceil(action?.getBoundingClientRect().right || 0),
      };
    });
    assert.ok(
      summaryLayout.documentWidth <= summaryLayout.viewportWidth,
      `structured summary must not overflow at ${viewport.width}px`,
    );
    assert.ok(
      summaryLayout.actionRight <= summaryLayout.viewportWidth,
      `structured actions must remain reachable at ${viewport.width}px`,
    );
  }
  await page.setViewportSize({ width: 1280, height: 720 });

  await page.locator("[data-action='tab'][data-id='transcript']").click();

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

  await page.evaluate(() => {
    const meetings = JSON.parse(localStorage.getItem("notesbuddy-meetings") || "[]");
    meetings[0].transcription = {
      ...(meetings[0].transcription || {}),
      status: "failed",
      error: "Transcription timed out",
    };
    meetings[0].analysis = { status: "not-requested", error: null };
    localStorage.setItem("notesbuddy-meetings", JSON.stringify(meetings));
  });
  await page.reload();
  await page.locator("[data-action='meeting']").first().click();
  await page.locator("[data-action='tab'][data-id='summary']").click();
  const savedTranscriptRefresh = page.locator("[data-action='regenerate']");
  assert.equal(
    await savedTranscriptRefresh.isEnabled(),
    true,
    "a failed speaker retry must not disable analysis of saved transcript text",
  );
  await savedTranscriptRefresh.click();
  await page
    .getByText("Generated from the saved browser transcript", { exact: true })
    .waitFor({ timeout: 10000 });

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

async function runLiveGuestAttribution(browser, baseUrl) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await installSyntheticMedia(page, {
    meetingSignal: false,
    speechRecognition: true,
  });
  await page.route("**/src/runtime-config.js", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/javascript; charset=utf-8",
      body: `globalThis.NotesBuddyRuntime = Object.freeze({ appVersion: "2026.08.8", transcriptionMode: "local", transcriptionEndpoint: "http://127.0.0.1:8765" });`,
    });
  });

  await page.goto(baseUrl);
  await completeOnboarding(page, "Live Identity Tester");
  await page.locator("[data-action='capture']").first().click();
  await page.locator("[data-action='start-capture']").click();
  await page.getByText("You + Guest draft", { exact: true }).waitFor();

  await page.evaluate(() =>
    globalThis.__notesBuddyTestMedia.emitSpeech(
      "I will open the agenda.",
    ),
  );
  const localRow = page
    .locator(".transcript-row")
    .filter({ hasText: "I will open the agenda." });
  await localRow.getByText("You", { exact: true }).waitFor();
  assert.equal(
    await localRow.locator(".provisional-speaker-badge").count(),
    0,
    "microphone-only words should remain You",
  );

  await page.evaluate(() =>
    globalThis.__notesBuddyTestMedia.setMeetingSignal(true),
  );
  await page
    .locator("[data-source-status='meeting']")
    .filter({ hasText: "sound detected" })
    .waitFor({ timeout: 5000 });
  await page.getByText("Guest speaking", { exact: true }).waitFor();
  await page.evaluate(() =>
    globalThis.__notesBuddyTestMedia.emitSpeech(
      "Can you share the report",
      false,
    ),
  );
  const interim = page.locator(".interim-transcript");
  await interim.getByText("Guest", { exact: true }).waitFor();
  await interim.getByText("draft", { exact: true }).waitFor();

  await page.evaluate(() =>
    globalThis.__notesBuddyTestMedia.emitSpeech(
      "Can you share the report?",
    ),
  );
  const guestRow = page
    .locator(".transcript-row")
    .filter({ hasText: "Can you share the report?" });
  await guestRow.getByText("Guest", { exact: true }).waitFor();
  await guestRow.getByText("draft", { exact: true }).waitFor();

  await page.locator("[data-action='finish-capture']").click();
  await page.locator(".detail-view").waitFor({ timeout: 10000 });
  const saved = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("notesbuddy-meetings") || "[]")[0],
  );
  assert.deepEqual(
    saved.transcript.map(({ speakerId, source, provisional }) => ({
      speakerId,
      source,
      provisional: Boolean(provisional),
    })),
    [
      {
        speakerId: "local-user",
        source: "microphone",
        provisional: false,
      },
      {
        speakerId: "remote-guest",
        source: "meeting",
        provisional: true,
      },
    ],
  );
  await context.close();
}

async function runLegacyInsightMigration(browser, baseUrl) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.route("**/src/runtime-config.js", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/javascript; charset=utf-8",
      body: `globalThis.NotesBuddyRuntime = Object.freeze({ transcriptionMode: "local", transcriptionEndpoint: "http://127.0.0.1:8765" });`,
    });
  });
  await page.addInitScript(() => {
    localStorage.setItem(
      "notesbuddy-profile",
      JSON.stringify({
        id: "legacy-profile",
        name: "Migration Tester",
        initials: "MT",
      }),
    );
    localStorage.setItem(
      "notesbuddy-meetings",
      JSON.stringify([
        {
          id: "legacy-insights",
          title: "Legacy insights",
          dateISO: "2026-08-04T00:00:00.000Z",
          duration: "4 min",
          source: "Stored meeting",
          participants: [
            { name: "Migration Tester", initials: "MT", color: "teal" },
          ],
          speakers: [],
          tags: ["Recorded"],
          overview: "Old summary",
          highlights: ["Old placeholder highlight"],
          decisions: [],
          actions: [
            {
              id: "legacy-review",
              text: "Review the recording and transcript",
              owner: "Migration Tester",
              done: false,
            },
            {
              id: "previous-grounded-action",
              text: "I will send the configuration tomorrow.",
              owner: "Migration Tester",
              done: true,
            },
          ],
          transcript: [
            {
              id: "legacy-local",
              source: "microphone",
              speakerId: "local-user",
              speaker: "You",
              startMs: 1000,
              endMs: 3000,
              text: "We agreed to keep the ingestion flow. I will send the configuration tomorrow.",
            },
          ],
          notes: "",
        },
      ]),
    );
  });

  await page.goto(baseUrl);
  await completeOnboarding(page, "Migration Tester");
  await page.locator("[data-action='meeting']").first().click();
  await page
    .getByText("This meeting uses the previous summary format", {
      exact: true,
    })
    .waitFor();
  await page
    .getByText("No confirmed decisions were recorded.", { exact: true })
    .waitFor();
  await page
    .getByText("No action items were recorded.", { exact: true })
    .waitFor();
  assert.equal(
    await page.getByText("Review the recording and transcript", { exact: true }).count(),
    0,
    "legacy placeholder actions must be removed instead of regenerated by keywords",
  );
  const migrated = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("notesbuddy-meetings") || "[]")[0],
  );
  assert.equal(migrated.summaryVersion, 3);
  assert.equal(migrated.analysis.status, "outdated");
  assert.deepEqual(migrated.highlights, []);
  assert.deepEqual(migrated.decisions, []);
  assert.deepEqual(migrated.actions, []);
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
  const installer = page.getByRole("link", {
    name: "Download Windows installer",
  });
  await installer.waitFor();
  assert.match(
    await installer.getAttribute("href"),
    /companion-v2026\.08\.11\/NotesBuddyCompanion-Setup-2026\.08\.11\.exe$/,
  );
  assert.equal(
    await page.locator("[data-action='defer-companion-setup']").count(),
    0,
    "production must not offer a disabled hosted fallback",
  );
  assert.equal(
    await page.locator("link[href='./src/styles.css']").count(),
    1,
  );
  await context.close();
}

async function runTeamsNotificationHandoff(browser, baseUrl) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.addInitScript(() => {
    localStorage.setItem(
      "notesbuddy-profile",
      JSON.stringify({
        id: "teams-notification-profile",
        name: "Teams Tester",
        initials: "TT",
      }),
    );
    localStorage.setItem(
      "notesbuddy-settings",
      JSON.stringify({ companionSetupCompleted: true }),
    );
  });

  await page.goto(`${baseUrl}?action=capture&source=teams`);
  await page
    .getByText("Teams meeting detected", { exact: true })
    .waitFor();
  await page
    .getByText(
      "Review your audio sources, then start capture when you are ready. Recording has not started.",
      { exact: true },
    )
    .waitFor();
  await page.locator("[data-action='start-capture']").waitFor();
  assert.equal(
    await page.locator(".recording-status--idle").count(),
    1,
    "a notification handoff must never start recording automatically",
  );
  assert.equal(
    new URL(page.url()).search,
    "",
    "the one-time notification launch parameters should be consumed",
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
    const scenarios = [
      ["main", () => runMainWorkflow(browser, baseUrl)],
      ["meeting-denied", () => runMeetingDeniedFallback(browser, baseUrl)],
      ["meeting-only", () => runMeetingOnlyCapture(browser, baseUrl)],
      ["meeting-track-missing", () => runMeetingTrackMissing(browser, baseUrl)],
      ["silent-meeting", () => runSilentMeetingTrack(browser, baseUrl)],
      ["unexpected-stop", () => runUnexpectedMeetingStop(browser, baseUrl)],
      ["live-guest", () => runLiveGuestAttribution(browser, baseUrl)],
      ["legacy-migration", () => runLegacyInsightMigration(browser, baseUrl)],
      ["direct-file", () => runDirectFileLoad(browser)],
      ["teams-notification", () => runTeamsNotificationHandoff(browser, baseUrl)],
      ["hosted", () => runHostedClientWorkflow(browser, baseUrl)],
      ["hybrid", () => runHybridCompanionWorkflow(browser, baseUrl)],
      ["existing-update", () => runExistingUserUpdateNotification(browser, baseUrl)],
      ["hybrid-fallback", () => runHybridFallbackWorkflow(browser, baseUrl)],
    ];
    const requestedScenario = process.env.NOTESBUDDY_BROWSER_SCENARIO || "";
    const selectedScenarios = requestedScenario
      ? scenarios.filter(([name]) => name === requestedScenario)
      : scenarios;
    if (!selectedScenarios.length) {
      throw new Error(`Unknown browser smoke scenario: ${requestedScenario}`);
    }
    for (const [name, run] of selectedScenarios) {
      await run();
      if (requestedScenario) console.log(`Browser smoke scenario passed: ${name}`);
    }
    console.log(
      "Browser smoke passed: direct-file load, version display, Teams notification handoff without auto-recording, first-entry installer onboarding and confirmation, existing-user companion update warnings, browser and companion Windows-output capture, live You/Guest draft attribution, signal detection, pause/resume, stable controls, source persistence/default playback, structured meeting analysis, obsolete-insight migration, local, hosted, and hybrid transcription clients, automatic desktop pairing, hosted fallback, anonymous sessions, rename/search/export, mic fallback, and interrupted-share continuity.",
    );
  } finally {
    await browser?.close();
    await close(server);
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
