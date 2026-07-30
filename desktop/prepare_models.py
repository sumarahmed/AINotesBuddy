"""Prepare redistributable offline model directories for a trusted release build."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

MODELS = (
    {
        "name": "faster-whisper-small",
        "repository": "Systran/faster-whisper-small",
        "license": "MIT",
        "requires_token": False,
    },
    {
        "name": "speaker-diarization-community-1",
        "repository": "pyannote/speaker-diarization-community-1",
        "license": "CC-BY-4.0",
        "requires_token": True,
    },
)


def resolve_revision(repository: str, token: str | None) -> str:
    information = HfApi(token=token).model_info(repository)
    if not information.sha:
        raise RuntimeError(f"Could not resolve an immutable revision for {repository}.")
    return information.sha


def download_model(
    *,
    model: dict[str, object],
    output: Path,
    token: str | None,
) -> dict[str, str]:
    repository = str(model["repository"])
    revision = resolve_revision(
        repository,
        token if bool(model["requires_token"]) else None,
    )
    destination = output / str(model["name"])
    destination.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=repository,
        revision=revision,
        token=token if bool(model["requires_token"]) else None,
        local_dir=destination,
    )
    cache_directory = destination / ".cache"
    if cache_directory.is_dir():
        shutil.rmtree(cache_directory)
    return {
        "name": str(model["name"]),
        "repository": repository,
        "revision": revision,
        "license": str(model["license"]),
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "models",
    )
    parser.add_argument(
        "--accept-pyannote-terms",
        action="store_true",
        help=(
            "Confirm that the publisher accepted the model access conditions "
            "and reviewed redistribution/attribution obligations."
        ),
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if not arguments.accept_pyannote_terms:
        raise RuntimeError(
            "Model packaging is gated. Re-run with --accept-pyannote-terms "
            "after reviewing desktop/MODEL_NOTICES.md."
        )
    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "HF_TOKEN must be supplied to the trusted release build. "
            "It is used only for download and is never written to the artifact."
        )

    output = arguments.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "preparedAt": datetime.now(UTC).isoformat(),
        "models": [
            download_model(model=model, output=output, token=token)
            for model in MODELS
        ],
    }
    (output / "MODEL_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Prepared {len(MODELS)} offline models in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
