# NotesBuddy local transcription companion

The companion processes NotesBuddy recordings on the same computer. It combines:

- Windows WASAPI loopback capture of the default system output;
- faster-whisper speech-to-text with word timestamps;
- pyannote `speaker-diarization-community-1` intervals;
- deterministic timestamp alignment and echo de-duplication.

This guide covers private `127.0.0.1` operation. The same engine also supports
a centrally hosted anonymous mode where end users install nothing. Deployment
owners should follow [Public hosted
transcription](../../docs/HOSTED_TRANSCRIPTION.md); never expose this local
launcher directly to a LAN or the internet.

Normal Windows users should install the packaged desktop companion described in
the [Desktop Companion guide](../../docs/DESKTOP_COMPANION.md). Packaged
releases contain offline model weights and pair with the public website
automatically; users do not configure Python, `HF_TOKEN`, a URL, or a pairing
token. The source instructions below remain for development and manual
recovery.

The microphone track is always assigned to `local-user` (**You**). Meeting-only
voices receive session-local IDs such as `remote-1`; those IDs are not voice
biometrics and do not identify real people.

## Requirements

- Python 3.11 recommended
- Windows 10/11, macOS, or Linux supported by PyTorch and the model libraries
- Several gigabytes of free disk space for the environment and model cache
- A Hugging Face account/token with access to the pyannote community model
- CPU processing works; a compatible CUDA setup can be faster

Model projects:

- <https://github.com/SYSTRAN/faster-whisper>
- <https://github.com/pyannote/pyannote-audio>

## Windows setup

From the repository root:

```powershell
cd services\transcription
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Before the first diarization job:

1. Accept the terms for
   `pyannote/speaker-diarization-community-1` on Hugging Face.
2. Create a read token.
3. Set it only in the terminal that runs the companion:

```powershell
$env:HF_TOKEN = "hf_replace_with_your_token"
```

Do not paste this model token into NotesBuddy, commit it, or put it in a public
issue. It is different from the NotesBuddy pairing token.

## Start and pair

```powershell
python run.py
```

The launcher:

- listens only on `http://127.0.0.1:8765`;
- creates a persistent random 256-bit pairing token on first start;
- prints the local token-file location;
- loads speech models only when the first job starts.

`desktop_app.py` is the packaged launcher. In addition to the loopback service,
it provides a control panel, notification-area menu, Windows sign-in startup,
safe discovery, exact-origin automatic browser pairing, and opt-out local Teams
meeting notifications that open the website's ready-to-record capture screen.

Display the token without starting a second server:

```powershell
python run.py --show-token
```

Paste that value into **NotesBuddy > Settings > Pairing token**, then choose
**Test connection**.

Default token locations:

- Windows: `%LOCALAPPDATA%\NotesBuddy\transcription-pairing-token`
- Linux: `$XDG_CONFIG_HOME/notesbuddy/transcription-pairing-token` or
  `~/.config/notesbuddy/transcription-pairing-token`

Deleting the token file and restarting creates a new pairing token. Existing
browser settings must then be updated.

## Origin allowlist

The defaults allow:

- direct `file://` launch (`Origin: null`);
- `http://127.0.0.1:4173`;
- `http://localhost:4173`;
- `https://sumarahmed.github.io`.

For another deployment, explicitly set every trusted browser origin:

```powershell
$env:NOTESBUDDY_ALLOWED_ORIGINS = "http://127.0.0.1:4173,https://notes.example.com"
python run.py
```

Use origins only—no paths and no trailing route. The service also responds to
modern browser private-network preflights; origin allowlisting and pairing-token
authentication still apply to the actual API request.

## Model configuration

Defaults automatically use CUDA when CTranslate2 can see the local NVIDIA GPU;
otherwise faster-whisper uses CPU `int8`. The distributable companion keeps
pyannote on CPU to avoid bundling the multi-gigabyte CUDA PyTorch runtime:

```powershell
$env:NOTESBUDDY_WHISPER_MODEL = "small"
$env:NOTESBUDDY_MODEL_DEVICE = "auto"
Remove-Item Env:NOTESBUDDY_WHISPER_COMPUTE_TYPE -ErrorAction SilentlyContinue
```

Example CUDA configuration, only after installing a matching PyTorch/CUDA
stack:

```powershell
$env:NOTESBUDDY_MODEL_DEVICE = "cuda"
$env:NOTESBUDDY_WHISPER_COMPUTE_TYPE = "float16"
```

Do not raise `NOTESBUDDY_MAX_WORKERS` casually. Speech models consume substantial
RAM/VRAM; the default serial worker prevents concurrent meetings exhausting the
computer.

Other variables are shown in `.env.example`. The launcher does not
automatically read `.env`; set values in the process environment or your own
private launcher.

## API

Transcription and health endpoints require:

```text
X-NotesBuddy-Pairing-Token: <local pairing token>
```

Endpoints:

```text
GET    /v1/companion
POST   /v1/pairings
GET    /v1/health
POST   /v1/system-audio/captures
GET    /v1/system-audio/captures/{captureId}
POST   /v1/system-audio/captures/{captureId}/pause
POST   /v1/system-audio/captures/{captureId}/resume
POST   /v1/system-audio/captures/{captureId}/stop
DELETE /v1/system-audio/captures/{captureId}
POST   /v1/transcriptions
GET    /v1/transcriptions/{jobId}
DELETE /v1/transcriptions/{jobId}
POST   /v1/analyses
```

`GET /v1/companion` returns only non-secret discovery metadata. Packaged desktop
builds enable `POST /v1/pairings`; it rejects missing, `null`, and untrusted
origins and returns a short-lived in-memory token. The manual `run.py` launcher
keeps automatic pairing disabled, so its persistent token workflow remains
explicit.

`POST` accepts multipart fields named `microphone`, `meeting`, `mixed`, and
`metadata`. At least one audio field is required. New NotesBuddy captures send
isolated sources plus the mixed playback track; imported files send `mixed`.

The completed response includes clock-aligned segments:

```json
{
  "jobId": "job-...",
  "status": "completed",
  "language": "en",
  "segments": [
    {
      "id": "segment-...",
      "source": "microphone",
      "speakerId": "local-user",
      "startMs": 0,
      "endMs": 1250,
      "text": "I will send the update.",
      "confidence": 0.94
    }
  ]
}
```

If no speech is detected, `segments` is empty. The test engine and production
engine never generate placeholder transcript text.

`POST /v1/analyses` accepts JSON containing `meetingTitle` and a non-empty
`segments` array. It returns a versioned short summary, highlights, confirmed
decisions, and structured action items. The production analyzer requires every
item to cite a real request segment ID and applies server-side grounding checks
before returning it. Local companion builds report `analysisAvailable: false`
unless `NOTESBUDDY_ANALYSIS_MODEL` is configured; the public hosted deployment
configures the managed analyzer.

System-audio routes are local-companion-only and pairing protected. Only one
capture can run at a time. The stop route returns a stereo 48 kHz WAV and
deletes the companion's temporary file after delivery. The default Windows
output—not only Teams—is captured, so notification sounds are included.

## Temporary data and logs

Uploads are written to one randomly named OS temporary directory per job. The
directory is removed in the worker's `finally` path after success, failure, or
cancellation. Cancellation cannot interrupt every native model operation
mid-inference, but the cancellation flag is checked between stages and cleanup
runs before the worker exits.

Normal application logs do not include transcript text or audio paths. Uvicorn
access logging is disabled by the launcher. Model caches are separate from job
audio and remain until removed using the model provider's cache instructions.
Recent status/results stay only in process memory for one hour by default; the
bounded job table evicts older terminal entries and disappears on process exit.

## Tests

API-only tests do not download speech models:

```powershell
python -m pip install -r requirements-api.txt
python -m pip install httpx
python -m unittest discover -s tests -v
```

The empty API smoke engine can be run manually:

```powershell
python run.py --empty-engine
```

It accepts jobs and intentionally returns an empty transcript. It is for
connection/security testing only.

## Troubleshooting

**Test connection says pairing token is invalid**

- Run `python run.py --show-token`.
- Paste the exact token into the same browser origin's Settings.
- Confirm another old companion process is not still using port 8765.

**The browser blocks the companion**

- Add the exact site origin to `NOTESBUDDY_ALLOWED_ORIGINS`.
- Accept any browser prompt allowing local-network access.
- Confirm the endpoint remains `http://127.0.0.1:8765`, not a LAN address.

**The job fails before diarization**

- Confirm `HF_TOKEN` is set in the companion process.
- Confirm the model terms were accepted by the same Hugging Face account.
- Start with the CPU defaults before changing CUDA options.

**Meeting track is missing**

- Restart capture and choose a surface that exposes audio.
- Enable **Share audio** in the browser dialog.
- Sharing a tab is generally more predictable than a window or entire screen.

**Processing is slow**

- The first job downloads/loads models.
- Keep one worker and try a smaller Whisper model.
- Consider a supported local GPU setup; do not upload confidential recordings
  to an arbitrary hosted service.
