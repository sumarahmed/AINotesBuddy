from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import urllib.error
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notesbuddy_transcription.components import ComponentManager, configure_component_environment


def archive_bytes(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


def lzma_archive_bytes(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_LZMA) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


class FakeResponse(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
        return False


class PartialResponse(FakeResponse):
    status = 206


class ComponentManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        names = (
            "NOTESBUDDY_COMPONENT_DIR",
            "NOTESBUDDY_MODEL_DIR",
            "NOTESBUDDY_GPU_LIB_DIR",
            "NOTESBUDDY_DIARIZATION_MODEL",
            "NOTESBUDDY_SPEAKER_WORKER",
            "NOTESBUDDY_ANALYSIS_RUNTIME",
            "NOTESBUDDY_ANALYSIS_MODEL_PATH",
        )
        self.environment = {name: os.environ.get(name) for name in names}

    def tearDown(self) -> None:
        for name, value in self.environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def manager(self, directory: str, payload: bytes, *, checksum: str | None = None):
        root = Path(directory) / "components"
        manifest = Path(directory) / "manifest.json"
        manifest.write_text(json.dumps({"schemaVersion": 1, "components": {
            "whisper-small": {"name": "Accurate", "version": "1", "category": "speech", "destination": "models/faster-whisper-selected", "bytes": len(payload), "sha256": checksum or hashlib.sha256(payload).hexdigest(), "url": "https://example.invalid/model.zip"},
            "speaker-diarization": {"name": "Speakers", "version": "1", "category": "speaker", "destination": "models/speaker-diarization-community-1", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(), "url": "https://example.invalid/speaker.zip"},
            "analysis-tiny": {"name": "Smart summary", "version": "1", "category": "analysis", "destination": "analysis", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(), "url": "https://example.invalid/analysis.zip"},
        }}), encoding="utf-8")
        return ComponentManager(root=root, manifest_path=manifest, opener=lambda *_args, **_kwargs: FakeResponse(payload))

    def wait(self, manager: ComponentManager, job_id: str) -> dict:
        # The install runs on a background thread doing real filesystem
        # extraction (including, in some tests, deeply nested paths under a
        # live-synced OneDrive folder). A 1-second budget was observed to
        # time out under normal system load even though the job itself was
        # still progressing, not stuck; poll longer before giving up.
        for _ in range(1_000):
            job = manager.job(job_id)
            if job and job["status"] not in {"queued", "downloading", "installing"}:
                return job
            time.sleep(0.01)
        self.fail("component job did not finish")

    def test_verified_component_is_installed_outside_application(self) -> None:
        payload = archive_bytes({"model.bin": b"model"})
        with tempfile.TemporaryDirectory() as directory:
            manager = self.manager(directory, payload)
            job = self.wait(manager, manager.start_install(["whisper-small"])["jobId"])
            self.assertEqual(job["status"], "completed")
            self.assertTrue((manager.root / "models/faster-whisper-selected/model.bin").is_file())
            self.assertTrue(manager.status()["components"]["whisper-small"]["installed"])

    def test_smart_summary_component_installs_at_configured_analysis_path(self) -> None:
        payload = archive_bytes({
            "llama-cli.exe": b"runtime",
            "qwen2.5-0.5b-instruct-q4_k_m.gguf": b"model",
        })
        with tempfile.TemporaryDirectory() as directory:
            manager = self.manager(directory, payload)

            job = self.wait(manager, manager.start_install(["analysis-tiny"])["jobId"])

            self.assertEqual(job["status"], "completed")
            self.assertEqual(
                Path(os.environ["NOTESBUDDY_ANALYSIS_RUNTIME"]),
                manager.root / "analysis/llama-cli.exe",
            )
            # NOTESBUDDY_ANALYSIS_MODEL_PATH names the shared analysis
            # directory, not one fixed filename -- three quality tiers can
            # each land a differently-named *.gguf there, and the active
            # one is discovered by LocalAnalysisRouter at request time.
            self.assertEqual(
                Path(os.environ["NOTESBUDDY_ANALYSIS_MODEL_PATH"]),
                manager.root / "analysis",
            )
            self.assertTrue(Path(os.environ["NOTESBUDDY_ANALYSIS_RUNTIME"]).is_file())
            self.assertTrue(
                (manager.root / "analysis" / "qwen2.5-0.5b-instruct-q4_k_m.gguf").is_file()
            )

    def test_compatible_component_checksum_survives_core_app_upgrades(self) -> None:
        payload = archive_bytes({"model.bin": b"model"})
        with tempfile.TemporaryDirectory() as directory:
            manager = self.manager(directory, payload)
            manifest = json.loads(manager.manifest_path.read_text(encoding="utf-8"))
            component = manifest["components"]["whisper-small"]
            component["compatibleSha256"] = ["a" * 64]
            manager.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            target = manager.root / component["destination"]
            target.mkdir(parents=True)
            marker = manager._marker("whisper-small")
            marker.parent.mkdir(parents=True)
            marker.write_text(json.dumps({"sha256": "a" * 64}), encoding="utf-8")

            self.assertTrue(manager.is_installed("whisper-small"))

    def test_lzma_component_pack_is_supported(self) -> None:
        payload = lzma_archive_bytes({"cudnn64_9.dll": b"gpu-runtime" * 100})
        with tempfile.TemporaryDirectory() as directory:
            manager = self.manager(directory, payload)
            job = self.wait(manager, manager.start_install(["whisper-small"])["jobId"])
            self.assertEqual(job["status"], "completed")
            self.assertTrue((manager.root / "models/faster-whisper-selected/cudnn64_9.dll").is_file())

    def test_deep_component_metadata_installs_with_a_short_windows_staging_path(self) -> None:
        deep_name = (
            "_internal/torch-2.13.0+cpu.dist-info/licenses/third_party/kineto/"
            "libkineto/third_party/dynolog/third_party/prometheus-cpp/3rdparty/"
            "civetweb/src/third_party/duktape-1.5.2/LICENSE.txt"
        )
        payload = archive_bytes({deep_name: b"license", "model.bin": b"model"})
        with tempfile.TemporaryDirectory() as directory:
            manager = self.manager(directory, payload)

            job = self.wait(manager, manager.start_install(["whisper-small"])["jobId"])

            self.assertEqual(job["status"], "completed")
            self.assertTrue(
                manager._filesystem_path(
                    manager.root / "models/faster-whisper-selected" / deep_name
                ).is_file()
            )
            shutil.rmtree(
                manager._filesystem_path(
                    manager.root / "models/faster-whisper-selected"
                )
            )

    def test_invalid_checksum_is_rejected_without_replacing_existing_component(self) -> None:
        payload = archive_bytes({"model.bin": b"new"})
        with tempfile.TemporaryDirectory() as directory:
            manager = self.manager(directory, payload, checksum="0" * 64)
            existing = manager.root / "models/faster-whisper-selected"
            existing.mkdir(parents=True)
            (existing / "model.bin").write_bytes(b"existing")
            job = self.wait(manager, manager.start_install(["whisper-small"])["jobId"])
            self.assertEqual(job["status"], "failed")
            self.assertIn("Security check failed", job["error"])
            self.assertEqual((existing / "model.bin").read_bytes(), b"existing")

    def test_unsafe_archive_path_is_rejected(self) -> None:
        payload = archive_bytes({"../escape.txt": b"bad"})
        with tempfile.TemporaryDirectory() as directory:
            manager = self.manager(directory, payload)
            job = self.wait(manager, manager.start_install(["whisper-small"])["jobId"])
            self.assertEqual(job["status"], "failed")
            self.assertFalse((Path(directory) / "escape.txt").exists())

    def test_partial_download_resumes_with_http_range(self) -> None:
        payload = archive_bytes({"model.bin": b"model-data" * 100})
        with tempfile.TemporaryDirectory() as directory:
            requests = []
            manager = self.manager(directory, payload)
            partial = manager.root / ".downloads/whisper-small.zip.part"
            partial.parent.mkdir(parents=True)
            offset = len(payload) // 3
            partial.write_bytes(payload[:offset])

            def opener(request, **_kwargs):
                requests.append(request)
                return PartialResponse(payload[offset:])

            manager.opener = opener
            job = self.wait(manager, manager.start_install(["whisper-small"])["jobId"])
            self.assertEqual(job["status"], "completed")
            self.assertEqual(requests[0].get_header("Range"), f"bytes={offset}-")

    def test_complete_partial_is_verified_without_an_invalid_range_request(self) -> None:
        payload = archive_bytes({"model.bin": b"complete-model"})
        with tempfile.TemporaryDirectory() as directory:
            manager = self.manager(directory, payload)
            partial = manager.root / ".downloads/whisper-small.zip.part"
            partial.parent.mkdir(parents=True)
            partial.write_bytes(payload)
            manager.opener = lambda *_args, **_kwargs: self.fail(
                "network request was not expected"
            )

            job = self.wait(manager, manager.start_install(["whisper-small"])["jobId"])

            self.assertEqual(job["status"], "completed")
            self.assertTrue((manager.root / "models/faster-whisper-selected/model.bin").is_file())

    def test_oversized_partial_restarts_without_range(self) -> None:
        payload = archive_bytes({"model.bin": b"fresh-model"})
        with tempfile.TemporaryDirectory() as directory:
            requests = []
            manager = self.manager(directory, payload)
            partial = manager.root / ".downloads/whisper-small.zip.part"
            partial.parent.mkdir(parents=True)
            partial.write_bytes(payload + b"stale")

            def opener(request, **_kwargs):
                requests.append(request)
                return FakeResponse(payload)

            manager.opener = opener
            job = self.wait(manager, manager.start_install(["whisper-small"])["jobId"])

            self.assertEqual(job["status"], "completed")
            self.assertIsNone(requests[0].get_header("Range"))

    def test_http_416_resets_partial_and_retries_once_from_zero(self) -> None:
        payload = archive_bytes({"model.bin": b"range-recovery" * 20})
        with tempfile.TemporaryDirectory() as directory:
            requests = []
            manager = self.manager(directory, payload)
            partial = manager.root / ".downloads/whisper-small.zip.part"
            partial.parent.mkdir(parents=True)
            offset = len(payload) // 2
            partial.write_bytes(payload[:offset])

            def opener(request, **_kwargs):
                requests.append(request)
                if len(requests) == 1:
                    raise urllib.error.HTTPError(
                        request.full_url, 416, "Range Not Satisfiable", {}, None
                    )
                return FakeResponse(payload)

            manager.opener = opener
            job = self.wait(manager, manager.start_install(["whisper-small"])["jobId"])

            self.assertEqual(job["status"], "completed")
            self.assertEqual(requests[0].get_header("Range"), f"bytes={offset}-")
            self.assertIsNone(requests[1].get_header("Range"))

    def test_component_environment_is_persistent_and_upgrade_independent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = configure_component_environment(Path(directory) / "persistent")
            self.assertEqual(Path(__import__("os").environ["NOTESBUDDY_MODEL_DIR"]), root / "models")
            self.assertEqual(
                Path(os.environ["NOTESBUDDY_ANALYSIS_RUNTIME"]),
                root / "analysis/llama-cli.exe",
            )
            self.assertEqual(
                Path(os.environ["NOTESBUDDY_ANALYSIS_MODEL_PATH"]),
                root / "analysis",
            )
            self.assertNotIn("Program Files", str(root))


if __name__ == "__main__":
    unittest.main()
