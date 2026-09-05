"""Build deterministic, independently updatable companion component packs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import urllib.request
import zipfile
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

REPOSITORY = "sumarahmed/AINotesBuddy"
# Three independently selectable smart-summary quality tiers. All three share
# one destination ("analysis"), matching the whisper-base/whisper-small
# pattern: installing one replaces whichever tier was previously installed,
# so a computer never carries more than one analysis model on disk at once.
# Each was verified end to end (real 298-segment meeting, same --no-jinja/
# --single-turn/--repeat-penalty pipeline) before being pinned here -- the
# tiny model's raw output looked plausible but failed evidence-grounding
# validation almost entirely on real speech; Standard was the first tier
# that reliably produced grounded, validated highlights.
ANALYSIS_TIERS = (
    {
        "id": "analysis-tiny",
        "name": "Fast",
        "description": "Smallest download, quickest to install",
        "model_repository": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        "model_revision": "9217f5db79a29953eb74d5343926648285ec7e67",
        "model_filename": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "model_bytes": 491_400_032,
        "model_sha256": "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db",
        "model_license_asset": "LICENSE-Qwen2.5.txt",
        "model_license": "Apache-2.0",
        # This repo carries its own LICENSE file alongside the weights.
        "model_license_bundled": True,
    },
    {
        "id": "analysis-standard",
        "name": "Balanced",
        "description": "Recommended: noticeably better summaries and highlights",
        "model_repository": "unsloth/Qwen3-1.7B-GGUF",
        "model_revision": "d7f544eead698dbd1f15126ef60b45a1e1933222",
        "model_filename": "Qwen3-1.7B-Q4_K_M.gguf",
        "model_bytes": 1_107_409_472,
        "model_sha256": "b139949c5bd74937ad8ed8c8cf3d9ffb1e99c866c823204dc42c0d91fa181897",
        "model_license_asset": "LICENSE-Qwen3.txt",
        "model_license": "Apache-2.0",
        # unsloth's GGUF quantisation repo carries no LICENSE file; it is
        # fetched separately from Qwen's own model repo (QWEN3_LICENSE_URL).
        "model_license_bundled": False,
    },
    {
        "id": "analysis-pro",
        "name": "High quality",
        "description": "Largest download, most capable local summarisation",
        "model_repository": "unsloth/Qwen3-4B-Instruct-2507-GGUF",
        "model_revision": "a06e946bb6b655725eafa393f4a9745d460374c9",
        # Q4_K_M (2.50 GB) was verified first and is the highest-fidelity
        # option, but a single GitHub release asset cannot exceed 2 GiB
        # (2,147,483,648 bytes), so it does not fit. Q3_K_M (1.93 GB) was
        # re-verified against the same real meeting chunk afterward and
        # produced comparable grounded content (6 highlights, 2 action
        # items with real dates) -- swap back to Q4_K_M if GitHub's limit
        # ever changes or another host is used.
        "model_filename": "Qwen3-4B-Instruct-2507-Q3_K_M.gguf",
        "model_bytes": 2_075_618_400,
        "model_sha256": "9c6e0763577125a994a9bea0bbd7a737ac4498b8a6a4e0f788727553af1806c9",
        "model_license_asset": "LICENSE-Qwen3.txt",
        "model_license": "Apache-2.0",
        # unsloth's GGUF quantisation repo carries no LICENSE file; it is
        # fetched separately from Qwen's own model repo (QWEN3_LICENSE_URL).
        "model_license_bundled": False,
    },
)
ANALYSIS_TIERS_BY_ID = {tier["id"]: tier for tier in ANALYSIS_TIERS}
# The unsloth GGUF quantisation repos carry no LICENSE file of their own;
# fetch the authoritative Apache-2.0 text from Qwen's own model repo instead,
# pinned by content hash like every other bundled artifact.
QWEN3_LICENSE_URL = "https://huggingface.co/Qwen/Qwen3-1.7B/raw/70d244cc86ccca08cf5af4e1e306ecf908b1ad5e/LICENSE"
QWEN3_LICENSE_BYTES = 11_343
QWEN3_LICENSE_SHA256 = "832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e"
LLAMA_CPP_RELEASE = "b10516"
LLAMA_CPP_ARCHIVE = f"llama-{LLAMA_CPP_RELEASE}-bin-win-cpu-x64.zip"
LLAMA_CPP_ARCHIVE_BYTES = 18_506_923
LLAMA_CPP_ARCHIVE_SHA256 = "fbbbc55e0eb2e1b07f9dcb9488616c98ed47d9003b90e15e7c8c7812c4307cd3"
LLAMA_CPP_ARCHIVE_URL = (
    f"https://github.com/ggml-org/llama.cpp/releases/download/"
    f"{LLAMA_CPP_RELEASE}/{LLAMA_CPP_ARCHIVE}"
)
LLAMA_CPP_LICENSE_URL = (
    f"https://raw.githubusercontent.com/ggml-org/llama.cpp/"
    f"{LLAMA_CPP_RELEASE}/LICENSE"
)
LLAMA_CPP_LICENSE_BYTES = 1_078
LLAMA_CPP_LICENSE_SHA256 = "94f29bbed6a22c35b992c5c6ebf0e7c92f13b836b90f36f461c9cf2f0f1d010d"
# GPU-capable alternative to LLAMA_CPP_ARCHIVE, same pinned release. Verified
# directly by downloading and inspecting it (not assumed): a complete,
# self-consistent runtime -- llama-cli.exe plus every supporting llama-*/
# ggml-* DLL the CPU-only build also ships, plus ggml-cuda.dll. Its own
# import strings (checked with `grep -a` on the extracted DLL) show its only
# external dependencies are cublas64_12.dll, cudart64_12.dll, and nvcuda.dll
# (the last ships with the NVIDIA display driver itself, never bundled).
LLAMA_CPP_CUDA_ARCHIVE = f"llama-{LLAMA_CPP_RELEASE}-bin-win-cuda-12.4-x64.zip"
LLAMA_CPP_CUDA_ARCHIVE_BYTES = 250_892_658
LLAMA_CPP_CUDA_ARCHIVE_SHA256 = "96d64faeb5b8e655341f32b26ad3e51fbea8bff0bc8120ad3dbffdc0b05b8ad3"
LLAMA_CPP_CUDA_ARCHIVE_URL = (
    f"https://github.com/ggml-org/llama.cpp/releases/download/"
    f"{LLAMA_CPP_RELEASE}/{LLAMA_CPP_CUDA_ARCHIVE}"
)
# Only cudart64_12.dll from this redistributable is actually needed --
# cublas64_12.dll/cublasLt64_12.dll are already provided by the existing
# nvidia-cuda12 pack for faster-whisper's ctranslate2 backend, and
# ggml-cuda.dll links against that exact file. This ~391MB archive is
# downloaded once here, at release-prep time, purely to extract one ~540KB
# file; end users never download it whole.
LLAMA_CPP_CUDART_ARCHIVE = "cudart-llama-bin-win-cuda-12.4-x64.zip"
LLAMA_CPP_CUDART_ARCHIVE_BYTES = 391_443_627
LLAMA_CPP_CUDART_ARCHIVE_SHA256 = "8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6"
LLAMA_CPP_CUDART_ARCHIVE_URL = (
    f"https://github.com/ggml-org/llama.cpp/releases/download/"
    f"{LLAMA_CPP_RELEASE}/{LLAMA_CPP_CUDART_ARCHIVE}"
)
MODELS = (
    ("whisper-base", "Systran/faster-whisper-base", False, "models/faster-whisper-selected", "speech", "Balanced speech model"),
    ("whisper-small", "Systran/faster-whisper-small", False, "models/faster-whisper-selected", "speech", "Accurate speech model"),
    ("speaker-diarization", "pyannote/speaker-diarization-community-1", True, "speaker", "speaker", "Speaker recognition runtime and model"),
)
COMPONENT_IDS = (
    tuple(item[0] for item in MODELS)
    + tuple(ANALYSIS_TIERS_BY_ID)
    + ("nvidia-cuda12", "analysis-cuda", "speaker-diarization-cuda")
)


def _zip_directory(
    source: Path,
    destination: Path,
    *,
    compression: int = zipfile.ZIP_DEFLATED,
) -> None:
    with zipfile.ZipFile(destination, "w", compression=compression, compresslevel=9) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file() or ".cache" in path.parts:
                continue
            info = zipfile.ZipInfo(path.relative_to(source).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = compression
            info.external_attr = 0o644 << 16
            with path.open("rb") as input_file, archive.open(info, "w", force_zip64=True) as output_file:
                shutil.copyfileobj(input_file, output_file, length=1024 * 1024)


def _asset(component_id: str, name: str, version: str, destination: str, category: str, archive: Path) -> tuple[str, dict]:
    filename = archive.name
    return component_id, {
        "name": name,
        "version": version,
        "category": category,
        "destination": destination,
        "bytes": archive.stat().st_size,
        "sha256": _sha256(archive),
        "url": f"https://github.com/{REPOSITORY}/releases/download/companion-v{version}/{filename}",
    }


def _sha256(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest().lower()


def _download_verified(
    url: str,
    destination: Path,
    *,
    expected_bytes: int,
    expected_sha256: str,
) -> None:
    if (
        destination.is_file()
        and destination.stat().st_size == expected_bytes
        and _sha256(destination) == expected_sha256
    ):
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(f"{destination.suffix}.part")
    partial.unlink(missing_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "NotesBuddy-Component-Builder/1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        if partial.stat().st_size != expected_bytes or _sha256(partial) != expected_sha256:
            raise RuntimeError(f"Security check failed for pinned upstream asset: {url}")
        os.replace(partial, destination)
    finally:
        partial.unlink(missing_ok=True)


def _extract_llama_runtime(
    archive_path: Path,
    destination: Path,
    *,
    extra_required: frozenset[str] = frozenset(),
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        selected = [
            member
            for member in archive.infolist()
            if not member.is_dir()
            and Path(member.filename).name == member.filename
            and (member.filename == "llama-cli.exe" or member.filename.lower().endswith(".dll"))
        ]
        names = {member.filename for member in selected}
        required = {
            "llama-cli.exe", "llama-cli-impl.dll", "llama-common.dll", "llama.dll", "ggml.dll",
        } | extra_required
        missing = sorted(required - names)
        if missing:
            raise RuntimeError(
                "The pinned llama.cpp runtime is incomplete: " + ", ".join(missing)
            )
        for member in selected:
            with archive.open(member) as source, (destination / member.filename).open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)


def _extract_cudart_dll(archive_path: Path, destination_file: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive, archive.open("cudart64_12.dll") as source:
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        with destination_file.open("wb") as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)


def _prepare_analysis_component(work: Path, output: Path, version: str, tier: dict) -> tuple[str, dict]:
    component_id = tier["id"]
    source = work / component_id
    source.mkdir(parents=True)
    snapshot_download(
        repo_id=tier["model_repository"],
        revision=tier["model_revision"],
        allow_patterns=[tier["model_filename"], "LICENSE"],
        local_dir=source,
    )
    shutil.rmtree(source / ".cache", ignore_errors=True)
    model_path = source / tier["model_filename"]
    if (
        not model_path.is_file()
        or model_path.stat().st_size != tier["model_bytes"]
        or _sha256(model_path) != tier["model_sha256"]
    ):
        raise RuntimeError(f"Security check failed for the pinned {tier['name']} smart-summary model.")
    if tier["model_license_bundled"]:
        model_license = source / "LICENSE"
        if not model_license.is_file():
            raise RuntimeError("The pinned model license is missing.")
        os.replace(model_license, source / tier["model_license_asset"])
    else:
        _download_verified(
            QWEN3_LICENSE_URL,
            source / tier["model_license_asset"],
            expected_bytes=QWEN3_LICENSE_BYTES,
            expected_sha256=QWEN3_LICENSE_SHA256,
        )

    inputs = work / ".inputs"
    runtime_archive = inputs / LLAMA_CPP_ARCHIVE
    _download_verified(
        LLAMA_CPP_ARCHIVE_URL,
        runtime_archive,
        expected_bytes=LLAMA_CPP_ARCHIVE_BYTES,
        expected_sha256=LLAMA_CPP_ARCHIVE_SHA256,
    )
    _extract_llama_runtime(runtime_archive, source)
    _download_verified(
        LLAMA_CPP_LICENSE_URL,
        source / "LICENSE-llama.cpp.txt",
        expected_bytes=LLAMA_CPP_LICENSE_BYTES,
        expected_sha256=LLAMA_CPP_LICENSE_SHA256,
    )
    provenance = {
        "schemaVersion": 1,
        "model": {
            "repository": tier["model_repository"],
            "revision": tier["model_revision"],
            "filename": tier["model_filename"],
            "bytes": tier["model_bytes"],
            "sha256": tier["model_sha256"],
            "license": tier["model_license"],
        },
        "runtime": {
            "repository": "ggml-org/llama.cpp",
            "release": LLAMA_CPP_RELEASE,
            "asset": LLAMA_CPP_ARCHIVE,
            "bytes": LLAMA_CPP_ARCHIVE_BYTES,
            "sha256": LLAMA_CPP_ARCHIVE_SHA256,
            "license": "MIT",
        },
    }
    (source / "COMPONENT_PROVENANCE.json").write_text(
        json.dumps(provenance, indent=2) + "\n",
        encoding="utf-8",
    )
    archive = output / f"NotesBuddy-{component_id}-{version}.zip"
    _zip_directory(source, archive)
    key, value = _asset(
        component_id,
        f"Smart meeting summary ({tier['name']})",
        version,
        "analysis",
        "analysis",
        archive,
    )
    value["tierDescription"] = tier["description"]
    value["modelRevision"] = tier["model_revision"]
    value["runtimeRelease"] = LLAMA_CPP_RELEASE
    return key, value


def _prepare_analysis_cuda_component(work: Path, output: Path, version: str) -> tuple[str, dict]:
    """GPU-capable llama.cpp runtime, opt-in and separate from the three GGUF
    tiers (the download is ~250MB vs. ~18.5MB for CPU-only, and most users
    don't have a discrete NVIDIA GPU). Ships no model weights of its own; a
    GGUF tier must already be installed for there to be anything to run.

    Deliberately uses its own destination ("analysis-gpu"), NOT the shared
    "analysis" destination the three GGUF tiers use. Component installation
    is a wholesale directory swap, not a file overlay (components.py's
    _install_one renames the whole target directory aside and replaces it) --
    confirmed the hard way: an earlier version of this component shared the
    "analysis" destination and silently deleted the installed GGUF the first
    time it was installed, since this runtime-only package has no model file
    of its own to put back. LocalAnalysisRouter prefers this separate
    runtime, when present, over the CPU-only one; the GGUF always resolves
    from the untouched "analysis" directory regardless of which runtime is
    active.
    """

    component_id = "analysis-cuda"
    source = work / component_id
    source.mkdir(parents=True)

    inputs = work / ".inputs"
    cuda_archive = inputs / LLAMA_CPP_CUDA_ARCHIVE
    _download_verified(
        LLAMA_CPP_CUDA_ARCHIVE_URL,
        cuda_archive,
        expected_bytes=LLAMA_CPP_CUDA_ARCHIVE_BYTES,
        expected_sha256=LLAMA_CPP_CUDA_ARCHIVE_SHA256,
    )
    _extract_llama_runtime(cuda_archive, source, extra_required=frozenset({"ggml-cuda.dll"}))

    cudart_archive = inputs / LLAMA_CPP_CUDART_ARCHIVE
    _download_verified(
        LLAMA_CPP_CUDART_ARCHIVE_URL,
        cudart_archive,
        expected_bytes=LLAMA_CPP_CUDART_ARCHIVE_BYTES,
        expected_sha256=LLAMA_CPP_CUDART_ARCHIVE_SHA256,
    )
    _extract_cudart_dll(cudart_archive, source / "cudart64_12.dll")

    _download_verified(
        LLAMA_CPP_LICENSE_URL,
        source / "LICENSE-llama.cpp.txt",
        expected_bytes=LLAMA_CPP_LICENSE_BYTES,
        expected_sha256=LLAMA_CPP_LICENSE_SHA256,
    )
    provenance = {
        "schemaVersion": 1,
        "runtime": {
            "repository": "ggml-org/llama.cpp",
            "release": LLAMA_CPP_RELEASE,
            "asset": LLAMA_CPP_CUDA_ARCHIVE,
            "bytes": LLAMA_CPP_CUDA_ARCHIVE_BYTES,
            "sha256": LLAMA_CPP_CUDA_ARCHIVE_SHA256,
            "license": "MIT",
        },
        "cudaRuntimeRedistributable": {
            "repository": "ggml-org/llama.cpp",
            "release": LLAMA_CPP_RELEASE,
            "asset": LLAMA_CPP_CUDART_ARCHIVE,
            "extractedFile": "cudart64_12.dll",
            "note": (
                "Only cudart64_12.dll is extracted from this asset -- "
                "cublas64_12.dll/cublasLt64_12.dll are provided by the "
                "nvidia-cuda12 component instead."
            ),
        },
    }
    (source / "COMPONENT_PROVENANCE.json").write_text(
        json.dumps(provenance, indent=2) + "\n",
        encoding="utf-8",
    )
    archive = output / f"NotesBuddy-{component_id}-{version}.zip"
    _zip_directory(source, archive)
    return _asset(
        component_id,
        "GPU acceleration for smart summary",
        version,
        "analysis-gpu",
        "analysis",
        archive,
    )


def _prepare_speaker_cuda_component(
    output: Path, version: str, speaker_runtime_gpu: Path
) -> tuple[str, dict]:
    """CUDA-capable speaker worker, opt-in and separate from the CPU one.

    Confirmed live (2026-09-05) on a real ~24 minute meeting recording:
    diarization ran 11.8x faster on GPU than on CPU with the thread-tuning
    fix, with identical speaker-turn output on both -- pyannote's clustering
    stage does not stay CPU-bound the way it might have.

    Ships no pyannote model of its own -- speaker_worker.py resolves
    NOTESBUDDY_DIARIZATION_MODEL the same way regardless of which worker
    binary runs, and that always points at the shared "speaker" destination
    the base speaker-diarization component installs. Deliberately uses its
    own destination ("speaker-gpu"), NOT that shared one: component
    installation is a wholesale directory swap (components.py's
    _install_one), and analysis-cuda already hit exactly this bug once by
    sharing a destination with a component that has a model file of its own
    to preserve. LocalDiarizationEngine prefers this separate worker, when
    present, over the CPU-only one; the shared model directory is
    untouched either way.

    speaker_runtime_gpu is a pre-built PyInstaller dist directory (same
    speaker_worker.py entry point as the CPU build, built from a venv with
    a CUDA-enabled torch/torchaudio instead) -- this function only packages
    it, the same way the CPU speaker-diarization component's runtime is
    supplied pre-built via --speaker-runtime in main() below.
    """

    component_id = "speaker-diarization-cuda"
    if not speaker_runtime_gpu.is_dir():
        raise RuntimeError("The packaged GPU speaker worker runtime is missing.")
    archive = output / f"NotesBuddy-{component_id}-{version}.zip"
    _zip_directory(speaker_runtime_gpu, archive)
    return _asset(
        component_id,
        "GPU acceleration for speaker recognition",
        version,
        "speaker-gpu",
        "speaker",
        archive,
    )


def _existing_components(manifest_path: Path) -> dict[str, dict]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        components = payload.get("components", {})
    except (OSError, TypeError, ValueError):
        return {}
    return {
        str(component_id): value
        for component_id, value in components.items()
        if isinstance(value, dict)
    } if isinstance(components, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "components-release")
    parser.add_argument("--gpu-libs", type=Path, default=Path(__file__).resolve().parent / "gpu-libs")
    parser.add_argument("--speaker-runtime", type=Path, default=Path(__file__).resolve().parent / "out-speaker" / "dist" / "NotesBuddySpeakerWorker")
    parser.add_argument("--speaker-runtime-gpu", type=Path, default=Path(__file__).resolve().parent / "out-speaker-gpu" / "dist" / "NotesBuddySpeakerWorkerGPU")
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parent / "component-manifest.json")
    parser.add_argument(
        "--component",
        action="append",
        choices=COMPONENT_IDS,
        help="Build only this component; repeat to build several. Unselected manifest entries are retained.",
    )
    parser.add_argument("--accept-pyannote-terms", action="store_true")
    arguments = parser.parse_args()
    selected = set(arguments.component or COMPONENT_IDS)
    if "speaker-diarization" in selected and not arguments.accept_pyannote_terms:
        raise RuntimeError("Review MODEL_NOTICES.md and explicitly accept the pyannote distribution terms.")
    token = os.getenv("HF_TOKEN", "").strip()
    if "speaker-diarization" in selected and not token:
        raise RuntimeError("HF_TOKEN is required for the gated speaker model build.")
    output = arguments.output.resolve()
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True)
    work = output / ".work"
    work.mkdir()
    components = (
        _existing_components(arguments.manifest)
        if arguments.component
        else {}
    )
    api = HfApi(token=token)
    for component_id, repository, gated, destination, category, name in MODELS:
        if component_id not in selected:
            continue
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
    for tier_id, tier in ANALYSIS_TIERS_BY_ID.items():
        if tier_id not in selected:
            continue
        key, value = _prepare_analysis_component(work, output, arguments.version, tier)
        components[key] = value
    if "nvidia-cuda12" in selected:
        if not arguments.gpu_libs.is_dir():
            raise RuntimeError("The pinned NVIDIA runtime directory is missing.")
        # Staged into a work copy rather than writing into --gpu-libs itself,
        # so this script never mutates the maintainer-provided input
        # directory. cudart64_12.dll is folded in here (not shipped whole
        # via the ~391MB cudart-llama archive -- see
        # _prepare_analysis_cuda_component) so the CUDA-capable smart-summary
        # runtime's only other dependency, ggml-cuda.dll, resolves fully from
        # this one existing pack.
        gpu_source = work / "nvidia-cuda12"
        shutil.copytree(arguments.gpu_libs, gpu_source)
        inputs = work / ".inputs"
        cudart_archive = inputs / LLAMA_CPP_CUDART_ARCHIVE
        _download_verified(
            LLAMA_CPP_CUDART_ARCHIVE_URL,
            cudart_archive,
            expected_bytes=LLAMA_CPP_CUDART_ARCHIVE_BYTES,
            expected_sha256=LLAMA_CPP_CUDART_ARCHIVE_SHA256,
        )
        _extract_cudart_dll(cudart_archive, gpu_source / "cudart64_12.dll")
        gpu_archive = output / f"NotesBuddy-nvidia-cuda12-{arguments.version}.zip"
        # CUDA/cuDNN DLLs compress poorly with Deflate. ZIP-LZMA remains readable
        # by Python's standard library and avoids making users download ~1.25 GB.
        _zip_directory(gpu_source, gpu_archive, compression=zipfile.ZIP_LZMA)
        key, value = _asset("nvidia-cuda12", "NVIDIA acceleration pack", arguments.version, "gpu", "accelerator", gpu_archive)
        components[key] = value
    if "analysis-cuda" in selected:
        key, value = _prepare_analysis_cuda_component(work, output, arguments.version)
        components[key] = value
    if "speaker-diarization-cuda" in selected:
        key, value = _prepare_speaker_cuda_component(
            output, arguments.version, arguments.speaker_runtime_gpu
        )
        components[key] = value
    manifest = {"schemaVersion": 1, "releaseVersion": arguments.version, "components": components}
    arguments.manifest.parent.mkdir(parents=True, exist_ok=True)
    arguments.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(work)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
