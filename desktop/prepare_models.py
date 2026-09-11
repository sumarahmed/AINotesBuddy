"""Prepare redistributable offline model directories for a trusted release build."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

MODELS = (
    {
        "name": "faster-whisper-small",
        "repository": "Systran/faster-whisper-small",
        "license": "MIT",
    },
)


def resolve_revision(repository: str) -> str:
    information = HfApi().model_info(repository)
    if not information.sha:
        raise RuntimeError(f"Could not resolve an immutable revision for {repository}.")
    return information.sha


def download_model(
    *,
    model: dict[str, object],
    output: Path,
) -> dict[str, str]:
    repository = str(model["repository"])
    revision = resolve_revision(repository)
    destination = output / str(model["name"])
    destination.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=repository,
        revision=revision,
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
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    output = arguments.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "preparedAt": datetime.now(UTC).isoformat(),
        "models": [
            download_model(model=model, output=output)
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
