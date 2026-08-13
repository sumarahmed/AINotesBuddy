# -*- mode: python ; coding: utf-8 -*-

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
executable = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name="NotesBuddySpeakerWorker", console=True)
collection = COLLECT(executable, analysis.binaries, analysis.datas, strip=False, upx=False, name="NotesBuddySpeakerWorker")
