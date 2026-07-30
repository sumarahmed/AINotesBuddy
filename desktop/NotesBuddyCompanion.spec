# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

project_root = Path(SPECPATH).parent
service_root = project_root / "services" / "transcription"
model_root = project_root / "desktop" / "models"

datas = [
    (
        str(project_root / "desktop" / "MODEL_NOTICES.md"),
        ".",
    ),
]
binaries = []
hiddenimports = collect_submodules("uvicorn")

for package in (
    "av",
    "ctranslate2",
    "faster_whisper",
    "huggingface_hub",
    "PIL",
    "pyannote.audio",
    "pystray",
    "soundfile",
):
    try:
        package_datas, package_binaries, package_hiddenimports = collect_all(package)
    except Exception:
        continue
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

if model_root.is_dir():
    datas.append((str(model_root), "models"))

analysis = Analysis(
    [str(service_root / "desktop_app.py")],
    pathex=[str(service_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="NotesBuddyCompanion",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="NotesBuddyCompanion",
)
