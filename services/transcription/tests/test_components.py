from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import time
import unittest
import os
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
        names = ("NOTESBUDDY_COMPONENT_DIR", "NOTESBUDDY_MODEL_DIR", "NOTESBUDDY_GPU_LIB_DIR", "NOTESBUDDY_DIARIZATION_MODEL", "NOTESBUDDY_SPEAKER_WORKER")
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
        }}), encoding="utf-8")
        return ComponentManager(root=root, manifest_path=manifest, opener=lambda *_args, **_kwargs: FakeResponse(payload))

    def wait(self, manager: ComponentManager, job_id: str) -> dict:
        for _ in range(100):
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

    def test_lzma_component_pack_is_supported(self) -> None:
        payload = lzma_archive_bytes({"cudnn64_9.dll": b"gpu-runtime" * 100})
        with tempfile.TemporaryDirectory() as directory:
            manager = self.manager(directory, payload)
            job = self.wait(manager, manager.start_install(["whisper-small"])["jobId"])
            self.assertEqual(job["status"], "completed")
            self.assertTrue((manager.root / "models/faster-whisper-selected/cudnn64_9.dll").is_file())

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

    def test_component_environment_is_persistent_and_upgrade_independent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = configure_component_environment(Path(directory) / "persistent")
            self.assertEqual(Path(__import__("os").environ["NOTESBUDDY_MODEL_DIR"]), root / "models")
            self.assertNotIn("Program Files", str(root))


if __name__ == "__main__":
    unittest.main()
