# -*- mode: python ; coding: utf-8 -*-
#
# Identical to NotesBuddySpeakerWorker.spec -- same entry point
# (speaker_worker.py), same collected packages. The only difference is the
# executable name, so it installs into its own component/destination
# (speaker-diarization-cuda -> "speaker-gpu") rather than overwriting the
# CPU worker. What actually makes this build GPU-capable is which torch
# wheel is installed in the build venv before PyInstaller runs here -- a
# CUDA-enabled torch (see .github/workflows/speaker-worker.yml), not
# anything in this spec file itself. speaker_worker.py detects CUDA
# availability at runtime and moves the pipeline to GPU when present,
# falling back to CPU automatically otherwise.

from pathlib import Path
from PyInstaller.utils.hooks import collect_all

project_root = Path(SPECPATH).parent
service_root = project_root / "services" / "transcription"
datas, binaries, hiddenimports = [], [], []
for package in ("pyannote.audio", "soundfile", "torch", "torchaudio"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

analysis = Analysis(
    [str(service_root / "speaker_worker.py")],
    pathex=[str(service_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)
executable = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name="NotesBuddySpeakerWorkerGPU", console=True)
collection = COLLECT(executable, analysis.binaries, analysis.datas, strip=False, upx=False, name="NotesBuddySpeakerWorkerGPU")
