from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from desktop import prepare_components  # noqa: E402


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
        return False


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class PrepareComponentsTests(unittest.TestCase):
    def test_verified_download_rejects_changed_upstream_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "runtime.zip"
            with patch(
                "desktop.prepare_components.urllib.request.urlopen",
                return_value=FakeResponse(b"changed"),
            ):
                with self.assertRaisesRegex(RuntimeError, "Security check failed"):
                    prepare_components._download_verified(
                        "https://example.invalid/runtime.zip",
                        destination,
                        expected_bytes=7,
                        expected_sha256="0" * 64,
                    )

            self.assertFalse(destination.exists())
            self.assertFalse(destination.with_suffix(".zip.part").exists())

    def test_analysis_pack_contains_model_runtime_licenses_and_provenance(self) -> None:
        model = b"small-gguf"
        model_license = b"Apache-2.0"
        runtime_license = b"MIT"
        runtime = io.BytesIO()
        with zipfile.ZipFile(runtime, "w") as archive:
            archive.writestr("llama-cli.exe", b"cli")
            archive.writestr("llama-cli-impl.dll", b"cli implementation")
            archive.writestr("llama-common.dll", b"common")
            archive.writestr("llama.dll", b"llama")
            archive.writestr("ggml.dll", b"ggml")
            archive.writestr("ggml-cpu-x64.dll", b"cpu")
            archive.writestr("unrelated-tool.exe", b"omit")
            archive.writestr("nested/unsafe.dll", b"omit")
        runtime_payload = runtime.getvalue()

        tier = dict(prepare_components.ANALYSIS_TIERS_BY_ID["analysis-tiny"])
        tier["model_bytes"] = len(model)
        tier["model_sha256"] = sha256(model)

        def fake_snapshot_download(**kwargs):
            destination = Path(kwargs["local_dir"])
            destination.mkdir(parents=True, exist_ok=True)
            (destination / tier["model_filename"]).write_bytes(model)
            (destination / "LICENSE").write_bytes(model_license)
            return str(destination)

        def fake_download(url, destination, *, expected_bytes, expected_sha256):
            del expected_bytes, expected_sha256
            payload = runtime_payload if url == prepare_components.LLAMA_CPP_ARCHIVE_URL else runtime_license
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / "work"
            output = root / "output"
            work.mkdir()
            output.mkdir()
            with ExitStack() as patches:
                patches.enter_context(
                    patch("desktop.prepare_components.snapshot_download", side_effect=fake_snapshot_download)
                )
                patches.enter_context(
                    patch("desktop.prepare_components._download_verified", side_effect=fake_download)
                )
                component_id, metadata = prepare_components._prepare_analysis_component(
                    work,
                    output,
                    "test-version",
                    tier,
                )

            component_archive = output / "NotesBuddy-analysis-tiny-test-version.zip"
            with zipfile.ZipFile(component_archive) as archive:
                names = set(archive.namelist())
                provenance = json.loads(archive.read("COMPONENT_PROVENANCE.json"))

            self.assertEqual(component_id, "analysis-tiny")
            self.assertEqual(metadata["destination"], "analysis")
            self.assertEqual(metadata["category"], "analysis")
            self.assertEqual(metadata["modelRevision"], tier["model_revision"])
            self.assertEqual(metadata["runtimeRelease"], prepare_components.LLAMA_CPP_RELEASE)
            self.assertIn(tier["model_filename"], names)
            self.assertIn("llama-cli.exe", names)
            self.assertIn("ggml-cpu-x64.dll", names)
            self.assertIn("LICENSE-Qwen2.5.txt", names)
            self.assertIn("LICENSE-llama.cpp.txt", names)
            self.assertNotIn("unrelated-tool.exe", names)
            self.assertNotIn("nested/unsafe.dll", names)
            self.assertEqual(provenance["model"]["sha256"], sha256(model))
            self.assertEqual(provenance["runtime"]["release"], prepare_components.LLAMA_CPP_RELEASE)

    def test_analysis_cuda_pack_contains_gpu_runtime_and_cudart(self) -> None:
        runtime = io.BytesIO()
        with zipfile.ZipFile(runtime, "w") as archive:
            archive.writestr("llama-cli.exe", b"cli")
            archive.writestr("llama-cli-impl.dll", b"cli implementation")
            archive.writestr("llama-common.dll", b"common")
            archive.writestr("llama.dll", b"llama")
            archive.writestr("ggml.dll", b"ggml")
            archive.writestr("ggml-cuda.dll", b"cuda backend")
            archive.writestr("ggml-cpu-x64.dll", b"cpu")
            archive.writestr("llama-server.exe", b"omit")
        runtime_payload = runtime.getvalue()

        cudart = io.BytesIO()
        with zipfile.ZipFile(cudart, "w") as archive:
            archive.writestr("cudart64_12.dll", b"cuda runtime")
            archive.writestr("cublas64_12.dll", b"omit, already have this")
        cudart_payload = cudart.getvalue()

        def fake_download(url, destination, *, expected_bytes, expected_sha256):
            del expected_bytes, expected_sha256
            if url == prepare_components.LLAMA_CPP_CUDA_ARCHIVE_URL:
                payload = runtime_payload
            elif url == prepare_components.LLAMA_CPP_CUDART_ARCHIVE_URL:
                payload = cudart_payload
            else:
                payload = b"MIT"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / "work"
            output = root / "output"
            work.mkdir()
            output.mkdir()
            with patch(
                "desktop.prepare_components._download_verified", side_effect=fake_download
            ):
                component_id, metadata = prepare_components._prepare_analysis_cuda_component(
                    work, output, "test-version"
                )

            component_archive = output / "NotesBuddy-analysis-cuda-test-version.zip"
            with zipfile.ZipFile(component_archive) as archive:
                names = set(archive.namelist())
                provenance = json.loads(archive.read("COMPONENT_PROVENANCE.json"))
                cudart_bytes = archive.read("cudart64_12.dll")

            self.assertEqual(component_id, "analysis-cuda")
            self.assertEqual(metadata["destination"], "analysis")
            self.assertIn("llama-cli.exe", names)
            self.assertIn("ggml-cuda.dll", names)
            self.assertIn("cudart64_12.dll", names)
            self.assertNotIn("llama-server.exe", names)
            self.assertNotIn("cublas64_12.dll", names, "already provided by nvidia-cuda12")
            self.assertEqual(cudart_bytes, b"cuda runtime")
            self.assertEqual(
                provenance["runtime"]["asset"], prepare_components.LLAMA_CPP_CUDA_ARCHIVE
            )
            self.assertEqual(
                provenance["cudaRuntimeRedistributable"]["extractedFile"], "cudart64_12.dll"
            )

    def test_nvidia_pack_folds_in_cudart_without_mutating_input_directory(self) -> None:
        cudart = io.BytesIO()
        with zipfile.ZipFile(cudart, "w") as archive:
            archive.writestr("cudart64_12.dll", b"cuda runtime")
        cudart_payload = cudart.getvalue()

        def fake_download(url, destination, *, expected_bytes, expected_sha256):
            del expected_bytes, expected_sha256
            self.assertEqual(url, prepare_components.LLAMA_CPP_CUDART_ARCHIVE_URL)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(cudart_payload)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gpu_libs = root / "gpu-libs"
            gpu_libs.mkdir()
            (gpu_libs / "cublas64_12.dll").write_bytes(b"existing cublas")
            output = root / "output"

            arguments = [
                "prepare_components.py", "--version", "test-version",
                "--component", "nvidia-cuda12",
                "--output", str(output), "--gpu-libs", str(gpu_libs),
                "--manifest", str(root / "manifest.json"),
            ]
            with patch.object(sys, "argv", arguments), patch(
                "desktop.prepare_components._download_verified", side_effect=fake_download
            ):
                prepare_components.main()

            # The maintainer-provided input directory must never be mutated.
            self.assertEqual(
                sorted(path.name for path in gpu_libs.iterdir()), ["cublas64_12.dll"]
            )
            with zipfile.ZipFile(
                output / "NotesBuddy-nvidia-cuda12-test-version.zip"
            ) as archive:
                names = set(archive.namelist())
            self.assertIn("cublas64_12.dll", names)
            self.assertIn("cudart64_12.dll", names)

    def test_selective_build_retains_existing_manifest_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps({
                    "schemaVersion": 1,
                    "components": {
                        "whisper-small": {
                            "name": "Existing speech",
                            "version": "old",
                            "category": "speech",
                        }
                    },
                }),
                encoding="utf-8",
            )
            output = root / "output"
            analysis_metadata = {
                "name": "Smart meeting summary",
                "version": "new",
                "category": "analysis",
                "destination": "analysis",
                "bytes": 123,
                "sha256": "a" * 64,
                "url": "https://example.invalid/analysis.zip",
            }
            arguments = [
                "prepare_components.py",
                "--version",
                "new",
                "--component",
                "analysis-tiny",
                "--output",
                str(output),
                "--manifest",
                str(manifest),
            ]
            with patch.object(sys, "argv", arguments), patch(
                "desktop.prepare_components._prepare_analysis_component",
                return_value=("analysis-tiny", analysis_metadata),
            ):
                prepare_components.main()

            generated = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(generated["components"]["whisper-small"]["version"], "old")
            self.assertEqual(generated["components"]["analysis-tiny"], analysis_metadata)


if __name__ == "__main__":
    unittest.main()
