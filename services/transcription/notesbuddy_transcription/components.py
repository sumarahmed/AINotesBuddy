"""Persistent, verified optional components for the desktop companion."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4


def component_root() -> Path:
    configured = os.getenv("NOTESBUDDY_COMPONENT_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    base = os.getenv("LOCALAPPDATA", "").strip()
    return (
        Path(base) / "NotesBuddy" / "components"
        if base
        else Path.home() / ".notesbuddy" / "components"
    )


def configure_component_environment(root: Path | None = None) -> Path:
    target = (root or component_root()).resolve()
    os.environ["NOTESBUDDY_COMPONENT_DIR"] = str(target)
    os.environ["NOTESBUDDY_MODEL_DIR"] = str(target / "models")
    os.environ["NOTESBUDDY_GPU_LIB_DIR"] = str(target / "gpu")
    os.environ["NOTESBUDDY_DIARIZATION_MODEL"] = str(target / "speaker" / "model")
    os.environ["NOTESBUDDY_SPEAKER_WORKER"] = str(target / "speaker" / "NotesBuddySpeakerWorker.exe")
    return target


def bundled_manifest_path() -> Path:
    bundle_root = getattr(__import__("sys"), "_MEIPASS", "")
    if bundle_root:
        return Path(bundle_root) / "component-manifest.json"
    return Path(__file__).parents[3] / "desktop" / "component-manifest.json"


@dataclass
class ComponentJob:
    id: str
    requested: list[str]
    status: str = "queued"
    stage: str = "queued"
    progress: float = 0.0
    error: str | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)
    cancel_event: threading.Event = field(default_factory=threading.Event)

    def public(self) -> dict[str, Any]:
        with self.lock:
            return {
                "jobId": self.id,
                "requested": list(self.requested),
                "status": self.status,
                "stage": self.stage,
                "progress": self.progress,
                "error": self.error,
            }


class ComponentManager:
    """Install release assets once and preserve them across app upgrades."""

    def __init__(
        self,
        *,
        root: Path | None = None,
        manifest_path: Path | None = None,
        opener: Any = urllib.request.urlopen,
    ) -> None:
        self.root = configure_component_environment(root)
        self.manifest_path = manifest_path or bundled_manifest_path()
        self.opener = opener
        self._jobs: dict[str, ComponentJob] = {}
        self._job_lock = threading.Lock()

    def manifest(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {"schemaVersion": 1, "components": {}}
        return payload if isinstance(payload, dict) else {"schemaVersion": 1, "components": {}}

    def _component(self, component_id: str) -> dict[str, Any]:
        value = self.manifest().get("components", {}).get(component_id)
        if not isinstance(value, dict):
            raise ValueError(f"Unknown companion component: {component_id}")
        return value

    def _marker(self, component_id: str) -> Path:
        return self.root / ".installed" / f"{component_id}.json"

    def is_installed(self, component_id: str) -> bool:
        component = self._component(component_id)
        try:
            marker = json.loads(self._marker(component_id).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return False
        target = self.root / str(component.get("destination") or component_id)
        return bool(
            target.is_dir()
            and marker.get("sha256") == component.get("sha256")
        )

    def status(self) -> dict[str, Any]:
        manifest = self.manifest()
        components = manifest.get("components", {})
        public: dict[str, Any] = {}
        for component_id, component in components.items():
            if not isinstance(component, dict):
                continue
            public[component_id] = {
                "name": component.get("name", component_id),
                "version": component.get("version"),
                "downloadBytes": int(component.get("bytes") or 0),
                "installed": self.is_installed(component_id),
                "category": component.get("category", "optional"),
            }
        active = next(
            (job.public() for job in self._jobs.values() if job.status in {"queued", "downloading", "installing"}),
            None,
        )
        speech_ready = any(
            bool(value.get("installed")) and value.get("category") == "speech"
            for value in public.values()
        )
        return {
            "root": str(self.root),
            "components": public,
            "ready": speech_ready and bool(
                "speaker-diarization" in components
                and self.is_installed("speaker-diarization")
            ),
            "activeJob": active,
        }

    def start_install(self, component_ids: list[str]) -> dict[str, Any]:
        requested = list(dict.fromkeys(str(item) for item in component_ids))
        if not requested:
            raise ValueError("Select at least one component.")
        for component_id in requested:
            self._component(component_id)
        with self._job_lock:
            if any(job.status in {"queued", "downloading", "installing"} for job in self._jobs.values()):
                raise RuntimeError("A component installation is already running.")
            job = ComponentJob(id=uuid4().hex, requested=requested)
            self._jobs[job.id] = job
        threading.Thread(target=self._run_install, args=(job,), daemon=True, name="notesbuddy-components").start()
        return job.public()

    def job(self, job_id: str) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        return job.public() if job else None

    def pause(self, job_id: str) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        job.cancel_event.set()
        return job.public()

    def _run_install(self, job: ComponentJob) -> None:
        try:
            pending = [item for item in job.requested if not self.is_installed(item)]
            total = sum(max(1, int(self._component(item).get("bytes") or 0)) for item in pending) or 1
            completed = 0
            for component_id in pending:
                component = self._component(component_id)
                size = max(1, int(component.get("bytes") or 0))
                self._install_one(job, component_id, component, completed, total, size)
                completed += size
            with job.lock:
                job.status = "completed"
                job.stage = "ready"
                job.progress = 1.0
        except InterruptedError:
            with job.lock:
                job.status = "paused"
                job.stage = "download paused"
        except Exception as error:  # noqa: BLE001 - surfaced through localhost API
            with job.lock:
                job.status = "failed"
                job.stage = "failed"
                job.error = str(error)[:1000]

    def _install_one(
        self,
        job: ComponentJob,
        component_id: str,
        component: dict[str, Any],
        completed: int,
        total: int,
        expected_size: int,
    ) -> None:
        downloads = self.root / ".downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        partial = downloads / f"{component_id}.zip.part"
        offset = partial.stat().st_size if partial.exists() else 0
        expected_digest = str(component.get("sha256") or "").lower()

        # A previous run can be interrupted after the last byte is written but
        # before verification/extraction. Requesting bytes=<size>- then causes
        # GitHub to return HTTP 416 even though the local archive is complete.
        if offset > expected_size:
            partial.unlink(missing_ok=True)
            offset = 0
        elif offset == expected_size:
            if self._sha256(partial) == expected_digest:
                offset = expected_size
            else:
                partial.unlink(missing_ok=True)
                offset = 0

        if offset < expected_size:
            offset = self._download(
                job,
                component_id,
                component,
                partial,
                offset,
                expected_size,
                completed,
                total,
            )

        digest = self._sha256(partial)
        if digest != expected_digest:
            partial.unlink(missing_ok=True)
            raise RuntimeError(f"Security check failed for {component.get('name', component_id)}.")
        staging = self.root / ".staging" / f"{component_id}-{uuid4().hex}"
        staging.mkdir(parents=True, exist_ok=False)
        with job.lock:
            job.status = "installing"
            job.stage = f"installing {component.get('name', component_id)}"
        try:
            with zipfile.ZipFile(partial) as archive:
                destination = staging.resolve()
                for member in archive.infolist():
                    resolved = (staging / member.filename).resolve()
                    if destination not in resolved.parents and resolved != destination:
                        raise RuntimeError("The component archive contains an unsafe path.")
                archive.extractall(staging)
            target = self.root / str(component.get("destination") or component_id)
            backup = target.with_name(f"{target.name}.previous")
            if backup.exists():
                shutil.rmtree(backup)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                os.replace(target, backup)
            try:
                os.replace(staging, target)
            except Exception:
                if backup.exists() and not target.exists():
                    os.replace(backup, target)
                raise
            shutil.rmtree(backup, ignore_errors=True)
            marker = self._marker(component_id)
            marker.parent.mkdir(parents=True, exist_ok=True)
            for other_id, other in self.manifest().get("components", {}).items():
                if (
                    other_id != component_id
                    and isinstance(other, dict)
                    and other.get("destination") == component.get("destination")
                ):
                    self._marker(str(other_id)).unlink(missing_ok=True)
            marker.write_text(json.dumps({"version": component.get("version"), "sha256": digest}, indent=2), encoding="utf-8")
            partial.unlink(missing_ok=True)
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    @staticmethod
    def _sha256(path: Path) -> str:
        checksum = hashlib.sha256()
        with path.open("rb") as downloaded:
            for chunk in iter(lambda: downloaded.read(1024 * 1024), b""):
                checksum.update(chunk)
        return checksum.hexdigest().lower()

    def _download(
        self,
        job: ComponentJob,
        component_id: str,
        component: dict[str, Any],
        partial: Path,
        offset: int,
        expected_size: int,
        completed: int,
        total: int,
    ) -> int:
        retried_after_range_error = False
        while True:
            headers = {"User-Agent": "NotesBuddy-Companion-Components/1"}
            if offset:
                headers["Range"] = f"bytes={offset}-"
            request = urllib.request.Request(str(component["url"]), headers=headers)
            try:
                response = self.opener(request, timeout=60)
            except urllib.error.HTTPError as error:
                if error.code == 416 and offset and not retried_after_range_error:
                    error.close()
                    partial.unlink(missing_ok=True)
                    offset = 0
                    retried_after_range_error = True
                    continue
                raise

            with response:
                if offset and getattr(response, "status", 200) != 206:
                    offset = 0
                    partial.unlink(missing_ok=True)
                mode = "ab" if offset else "wb"
                with partial.open(mode) as output:
                    while True:
                        if job.cancel_event.is_set():
                            raise InterruptedError("Component download paused.")
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
                        offset += len(chunk)
                        with job.lock:
                            job.status = "downloading"
                            job.stage = f"downloading {component.get('name', component_id)}"
                            job.progress = min(
                                0.98,
                                (completed + min(offset, expected_size)) / total,
                            )
            return offset
