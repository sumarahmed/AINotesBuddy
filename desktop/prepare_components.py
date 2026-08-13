"""Build deterministic, independently updatable companion component packs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

REPOSITORY = "sumarahmed/AINotesBuddy"
MODELS = (
    ("whisper-base", "Systran/faster-whisper-base", False, "models/faster-whisper-selected", "speech", "Balanced speech model"),
    ("whisper-small", "Systran/faster-whisper-small", False, "models/faster-whisper-selected", "speech", "Accurate speech model"),
    ("speaker-diarization", "pyannote/speaker-diarization-community-1", True, "speaker", "speaker", "Speaker recognition runtime and model"),
)


def _zip_directory(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file() or ".cache" in path.parts:
                continue
            info = zipfile.ZipInfo(path.relative_to(source).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with path.open("rb") as input_file, archive.open(info, "w", force_zip64=True) as output_file:
                shutil.copyfileobj(input_file, output_file, length=1024 * 1024)


def _asset(component_id: str, name: str, version: str, destination: str, category: str, archive: Path) -> tuple[str, dict]:
    checksum = hashlib.sha256()
    with archive.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(chunk)
    filename = archive.name
    return component_id, {
        "name": name,
        "version": version,
        "category": category,
        "destination": destination,
        "bytes": archive.stat().st_size,
        "sha256": checksum.hexdigest(),
        "url": f"https://github.com/{REPOSITORY}/releases/download/companion-v{version}/{filename}",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "components-release")
    parser.add_argument("--gpu-libs", type=Path, default=Path(__file__).resolve().parent / "gpu-libs")
    parser.add_argument("--speaker-runtime", type=Path, default=Path(__file__).resolve().parent / "out-speaker" / "dist" / "NotesBuddySpeakerWorker")
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parent / "component-manifest.json")
    parser.add_argument("--accept-pyannote-terms", action="store_true")
    arguments = parser.parse_args()
    if not arguments.accept_pyannote_terms:
        raise RuntimeError("Review MODEL_NOTICES.md and explicitly accept the pyannote distribution terms.")
    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN is required for the gated speaker model build.")
    output = arguments.output.resolve()
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True)
    work = output / ".work"
    work.mkdir()
    components: dict[str, dict] = {}
    api = HfApi(token=token)
    for component_id, repository, gated, destination, category, name in MODELS:
        revision = api.model_info(repository, token=token if gated else None).sha
        if not revision:
            raise RuntimeError(f"Could not pin {repository}.")
        source = work / component_id
        model_destination = source / "model" if component_id == "speaker-diarization" else source
        snapshot_download(repo_id=repository, revision=revision, token=token if gated else None, local_dir=model_destination)
        shutil.rmtree(model_destination / ".cache", ignore_errors=True)
        if component_id == "speaker-diarization":
            if not arguments.speaker_runtime.is_dir():
                raise RuntimeError("The packaged speaker worker runtime is missing.")
            shutil.copytree(arguments.speaker_runtime, source, dirs_exist_ok=True)
        archive = output / f"NotesBuddy-{component_id}-{arguments.version}.zip"
        _zip_directory(source, archive)
        key, value = _asset(component_id, name, arguments.version, destination, category, archive)
        value["revision"] = revision
        components[key] = value
    if not arguments.gpu_libs.is_dir():
        raise RuntimeError("The pinned NVIDIA runtime directory is missing.")
    gpu_archive = output / f"NotesBuddy-nvidia-cuda12-{arguments.version}.zip"
    _zip_directory(arguments.gpu_libs, gpu_archive)
    key, value = _asset("nvidia-cuda12", "NVIDIA acceleration pack", arguments.version, "gpu", "accelerator", gpu_archive)
    components[key] = value
    manifest = {"schemaVersion": 1, "releaseVersion": arguments.version, "components": components}
    arguments.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(work)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
