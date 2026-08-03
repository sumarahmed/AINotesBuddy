# NotesBuddy Desktop Companion

The Windows companion lets the public NotesBuddy website use this computer for
speech-to-text and speaker diarization. Users install it once; they do not need
Python, Modal, a Hugging Face account, a model token, or a NotesBuddy pairing
token.

The companion is the local **capture and processing host**. Version `2026.08.1`
records the default Windows output through WASAPI loopback while a NotesBuddy
capture is active. It does not join meetings as a bot and does not record while
NotesBuddy is idle.

Version `2026.08.2` adds two update safeguards. The website compares every
connected companion with its public latest-version setting and shows existing
users a persistent warning when it is old. The companion also checks the latest
GitHub Release shortly after startup and every 24 hours, then shows a tray
notification and enables **Download update**. It never downloads or installs an
update without the user's choice, and a failed check does not affect recording.

## User flow

1. Create the local browser profile on the NotesBuddy website.
2. Follow the displayed **Install the Windows companion** guide and open the
   repository Releases page.
3. Download and run `NotesBuddyCompanion-Setup-<version>.exe`. Administrator
   rights are not required.
4. Leave the companion running in the Windows notification area.
5. Return to the website and choose **I've installed it — check connection**.
   NotesBuddy checks `http://127.0.0.1:8765`, pairs automatically, and verifies
   the API, secure pairing, offline model bundle, and runtime packages before
   showing **Desktop companion is working**.
6. If Chrome or Edge asks whether the site can access devices on the local
   network, allow it. The service remains bound to this computer only.
7. Start a capture and ask another meeting participant to speak. The Meeting
   badge should change from **Waiting for sound** to **Sound detected** without
   opening the browser share picker.

If that permission was denied, open the site controls beside the browser
address bar, set **Local network access** to **Allow**, and choose **I've
installed it — check connection** again.

If the companion is stopped, the site uses the configured hosted service. The
Settings drawer clearly shows **online fallback**. Start the companion and
choose **Look for companion** to return to on-device processing.

Choosing **Use online transcription for now** dismisses setup only for the
current browser session. NotesBuddy asks again in a future session until a
working local connection is confirmed. Confirmed setup is stored with the
local browser settings and can be reopened from **Settings → Setup guide**.

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
- Active Windows output is written to a temporary WAV, transferred over
  `127.0.0.1` when capture finishes, and deleted by the companion immediately
  after the response. It includes all sounds sent to the default Windows
  speaker during that interval.
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
4. When ready, create and push a tag such as `companion-v2026.08.2`.

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
.\desktop\build.ps1 -Python python -Version 2026.08.2 -RequireModels
```

Build output is ignored under `desktop/out/` and `desktop/release/`. The model
directory is also ignored and must never be committed.

For a dependency-light package smoke test, omit model preparation and run:

```powershell
.\desktop\build.ps1 -Python python -Version 2026.08.2 -SkipInstaller
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

- Confirm the website reports companion `2026.08.1` or later. Older companions
  cannot capture Windows output directly.
- In Teams **Device settings**, choose the same speaker that Windows uses as
  its default output.
- Ask another participant to speak and confirm the capture UI says **Sound
  detected**. Microphone activity does not count as meeting-output activity.
- If the website opens a browser share picker, it is using fallback capture;
  restart/update the companion and choose **Look for companion** in Settings.
- Use headphones to reduce the local microphone picking up remote echo.

Speaker diarization distinguishes detected voices by time. It does not know
people's real names; users rename **Speaker 1**, **Speaker 2**, and so on after
processing.
