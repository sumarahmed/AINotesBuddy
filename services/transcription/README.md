# NotesBuddy local transcription companion

The companion processes NotesBuddy recordings on the same computer. It combines:

- faster-whisper speech-to-text with word timestamps;
- pyannote `speaker-diarization-community-1` intervals;
- deterministic timestamp alignment and echo de-duplication.

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

Defaults are chosen for broad CPU compatibility:

```powershell
$env:NOTESBUDDY_WHISPER_MODEL = "small"
$env:NOTESBUDDY_MODEL_DEVICE = "cpu"
$env:NOTESBUDDY_WHISPER_COMPUTE_TYPE = "int8"
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

Every endpoint requires:

```text
X-NotesBuddy-Pairing-Token: <local pairing token>
```

Endpoints:

```text
GET    /v1/health
POST   /v1/transcriptions
GET    /v1/transcriptions/{jobId}
DELETE /v1/transcriptions/{jobId}
```

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
