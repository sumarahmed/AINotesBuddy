# NotesBuddy Desktop Companion

The Windows companion lets the public NotesBuddy website use this computer for
speech-to-text and speaker diarization. Users install it once; they do not need
Python, Modal, a Hugging Face account, a model token, or a NotesBuddy pairing
token.

The companion is the local **processing host**. Meeting capture still happens
in the browser: at capture start, choose the Teams/Meet/Zoom tab or shared
surface and enable **Share audio**. Version 1 does not silently intercept
Windows system audio or join meetings as a bot.

## User flow

1. Download `NotesBuddyCompanion-Setup-<version>.exe` from the repository's
   latest GitHub Release.
2. Run the per-user installer. Administrator rights are not required.
3. Leave the companion running in the Windows notification area.
4. Open NotesBuddy. The website looks for `http://127.0.0.1:8765`, pairs
   automatically, and shows **local connected** in Settings.
5. If Chrome or Edge asks whether the site can access devices on the local
   network, allow it. The service remains bound to this computer only.

If the companion is stopped, the site uses the configured hosted service. The
Settings drawer clearly shows **online fallback**. Start the companion and
choose **Look for companion** to return to on-device processing.

Closing the control-panel window hides it in the notification area. Use the
tray menu's **Quit** command to stop the service. The **Start when I sign in**
option can be changed in the control panel or selected during installation.

## Privacy and pairing

- The service listens only on IPv4 loopback `127.0.0.1`.
- `GET /v1/companion` exposes safe discovery metadata and no secret.
- `POST /v1/pairings` accepts only exact trusted website origins.
- Missing, `null`, and unknown origins cannot obtain an automatic token.
- The website receives a random, expiring token and holds it only in page
  memory. Restarting the companion revokes all automatic browser pairings.
- A persistent user-local token remains available through **Copy recovery
  token** for manual diagnostics; normal users never need it.
- Job audio uses a random OS temporary directory and is deleted after success,
  failure, or cancellation.
- The application does not open a Windows Firewall port.

The website may use an online fallback when the companion is unavailable.
Settings discloses which path is currently active.

## Offline models and publisher secret

Public installers must include:

- `Systran/faster-whisper-small`;
- `pyannote/speaker-diarization-community-1`.

The publisher—not each customer—accepts the gated model conditions and stores a
read-only token as the GitHub repository secret `HF_TOKEN`. The Windows release
workflow uses it only while downloading weights. It packages local model
directories, records immutable revisions in `MODEL_MANIFEST.json`, and does not
write the token to an artifact.

Before public distribution, review
[`desktop/MODEL_NOTICES.md`](../desktop/MODEL_NOTICES.md). The model preparation
step deliberately requires `--accept-pyannote-terms`.

## Create a release

In GitHub:

1. Open **Settings → Secrets and variables → Actions**.
2. Add a repository secret named `HF_TOKEN` containing the publisher's
   read-only, gated-model token.
3. Run **Windows desktop companion** from the Actions tab with
   `include_models` enabled to test a build.
4. When ready, create and push a tag such as `companion-v0.1.0`.

The tag workflow runs service tests, prepares pinned offline models, builds a
PyInstaller one-directory application, executes the packaged `--self-test`,
creates a per-user Inno Setup installer, uploads the Actions artifact, and
attaches the installer to the matching GitHub Release.

Do not publish a no-model workflow artifact as a functional release. That
option exists only for quick packaging diagnostics.

## Local developer build

Use Python 3.11 on Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r services\transcription\requirements-packaging.txt
$env:HF_TOKEN = "publisher-build-token"
python desktop\prepare_models.py --accept-pyannote-terms
.\desktop\build.ps1 -Python python -Version 0.1.0 -RequireModels
```

Build output is ignored under `desktop/out/` and `desktop/release/`. The model
directory is also ignored and must never be committed.

For a dependency-light package smoke test, omit model preparation and run:

```powershell
.\desktop\build.ps1 -Python python -Version 0.1.0 -SkipInstaller
.\desktop\out\dist\NotesBuddyCompanion\NotesBuddyCompanion.exe --self-test
```

## Troubleshooting

**The website says online fallback**

- Start **NotesBuddy Desktop Companion** from the Start menu.
- In Settings, choose **Look for companion**.
- Allow the browser's local-network permission if prompted.
- Close any older source/CLI companion already occupying port 8765.

**The companion opens but transcription fails**

- Confirm the installer is a model-inclusive release.
- Check that `models\faster-whisper-small` and
  `models\speaker-diarization-community-1` are present in the installed bundle.
- Keep the CPU defaults for the first test; model loading can take time.

**Teams participants are missing**

- The companion can process only audio the browser actually saved.
- At capture start, select the Teams tab/screen and enable **Share audio**.
- Confirm the capture UI says meeting audio is recording.
- Use headphones to reduce the local microphone picking up remote echo.

Speaker diarization distinguishes detected voices by time. It does not know
people's real names; users rename **Speaker 1**, **Speaker 2**, and so on after
processing.
