# Public hosted transcription

NotesBuddy supports two transcription modes:

- `local`: each browser pairs with a loopback companion;
- `hosted`: the public site creates a short-lived anonymous session and sends
  selected audio to one centrally managed transcription service.

The hosted prototype is packaged for Modal because its web endpoints can run a
FastAPI application on a GPU, scale to zero, mount a persistent model cache,
and receive secrets without exposing them to browser code.

## User experience

Hosted users do not install Python, create a Hugging Face account, or enter a
token. They still must grant microphone/display permissions and explicitly
enable shared audio because browsers do not allow a site to bypass that prompt.

When transcription is requested:

1. the browser obtains an opaque anonymous session;
2. the microphone, meeting, and mixed audio assets are uploaded over HTTPS;
3. the service processes one queued model job;
4. the browser polls only that session's job;
5. source files are removed after success, failure, or cancellation;
6. the returned transcript is saved in the originating browser.

When professional analysis is requested, the browser sends the completed
speaker transcript—not recording audio—to `POST /v1/analyses` under the same
anonymous session. The service uses the full transcript to produce a short
summary, consolidated highlights, confirmed decisions, and structured action
items. Every result cites supporting transcript segment IDs.

The hosted service does not automatically know a person's real name. It returns
**You**, **Speaker 1**, **Speaker 2**, and **Unknown speaker** labels that can be
renamed in the browser.

## Prototype safeguards

- exact production-origin CORS allowlist;
- random expiring anonymous session tokens;
- job ownership checked without disclosing another session's job;
- raw client IP addresses hashed before in-memory rate-limit storage;
- bounded sessions, jobs, workers, source sizes, and result retention;
- one active job and three job starts per anonymous session per hour by default;
- one serverless GPU container, which bounds concurrent model spend;
- temporary job directories removed in a `finally` block;
- model credentials held only in the host's secret manager.
- analysis requests limited to 180,000 transcript characters;
- server-side evidence, decision, action, owner, due-date, priority, context,
  and notes validation before a result reaches the browser.

These controls reduce accidental and basic automated abuse. They are not a
substitute for accounts, CAPTCHA/attestation, a durable rate-limit store,
billing limits, audit logs, or subscription entitlements. Do not treat this
anonymous mode as the final commercial security boundary.

## Modal deployment prerequisites

1. Create a Modal account and configure its local CLI.
2. Accept the access conditions for
   `pyannote/speaker-diarization-community-1`.
3. In the Modal dashboard, create a secret named
   `notesbuddy-huggingface` containing:

   ```text
   HF_TOKEN=hf_your_read_token
   ```

   Enter the value in Modal's secret UI. Never commit it, put it in
   `runtime-config.js`, or paste it into the public NotesBuddy site.

4. Install only the deployment CLI locally:

   ```powershell
   python -m pip install -r services/transcription/requirements-deploy.txt
   modal setup
   ```

## Deploy the API

From the repository root:

```powershell
modal deploy services/transcription/modal_app.py
```

Modal returns an HTTPS web endpoint. Verify it before changing the public
client:

```powershell
curl.exe https://YOUR-ENDPOINT.modal.run/v1/health
```

The response must include:

```json
{
  "status": "ok",
  "access": "anonymous-session",
  "analysisAvailable": true,
  "analysisModel": "Qwen/Qwen3-4B-Instruct-2507",
  "storage": "temporary job files only"
}
```

The first real transcription or analysis request downloads and loads the
required Whisper, pyannote, or pinned Qwen instruction model into the
`notesbuddy-model-cache` volume. It will take longer than later requests.

The [Qwen3-4B-Instruct-2507 model](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)
revision is pinned in `services/transcription/modal_app.py`.
Model weights are cached in the host volume; meeting audio and transcript
content are not intentionally written there.

## Connect the static client

Set the non-secret public endpoint in `src/runtime-config.js`:

```js
globalThis.NotesBuddyRuntime = Object.freeze({
  transcriptionMode: "hosted",
  transcriptionEndpoint: "https://YOUR-ENDPOINT.modal.run",
});
```

Run the full checks, commit the generated `dist/` update, and deploy the static
client:

```powershell
npm test
git push
```

The endpoint is public configuration. The Hugging Face token is not.

## Operations

- Keep `max_containers=1` during anonymous testing.
- Configure a Modal spending limit/alert before sharing the link widely.
- Monitor 429, 413, 5xx, queue depth, cold-start time, transcription time, and
  analysis latency/failure rate.
- Use a short non-confidential test recording before real meetings.
- Rotate the Hugging Face token if it is ever exposed.
- Stop or delete the Modal deployment to stop public processing.

Free/credit availability and GPU prices can change; check Modal's current
pricing before enabling the service.

## Subscription migration

The browser client already separates service mode from job processing. A
commercial version should replace anonymous session issuance with signed user
identity and entitlement checks while preserving the transcription contract.
It should also add:

- sign-in and verified email;
- subscription/webhook state;
- durable per-user quotas and job records;
- object storage with encryption and lifecycle deletion;
- idempotent queues and multiple workers;
- consent, retention, export, deletion, and privacy controls;
- abuse prevention and a documented incident-response process.
