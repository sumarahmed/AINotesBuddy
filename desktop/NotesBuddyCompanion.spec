# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

project_root = Path(SPECPATH).parent
service_root = project_root / "services" / "transcription"
datas = [
    (
        str(project_root / "desktop" / "MODEL_NOTICES.md"),
        ".",
    ),
    (
        str(project_root / "desktop" / "component-manifest.json"),
        ".",
    ),
    (
        str(project_root / "desktop" / "assets" / "notesbuddy.png"),
        ".",
    ),
    (
        str(project_root / "desktop" / "assets" / "notesbuddy.ico"),
        ".",
    ),
]
binaries = []
hiddenimports = collect_submodules("uvicorn") + ["soundfile"]

for package in (
    "av",
    "ctranslate2",
    "faster_whisper",
    "huggingface_hub",
    "PIL",
    "pycaw",
    "pystray",
    "soundcard",
    "windows_toasts",
):
    try:
        package_datas, package_binaries, package_hiddenimports = collect_all(package)
    except Exception:
        continue
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

analysis = Analysis(
    [str(service_root / "desktop_app.py")],
    pathex=[str(service_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch",
        "torchaudio",
        "pyannote",
        "pyannote.audio",
        "transformers",
        "lightning",
        "torchmetrics",
    ],
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
    icon=str(project_root / "desktop" / "assets" / "notesbuddy.ico"),
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
