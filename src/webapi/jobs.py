from __future__ import annotations

import secrets
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable


ProgressUpdater = Callable[[float, str], None]
Worker = Callable[[ProgressUpdater], dict[str, Any]]


class JobStore:
    """Small in-memory job queue for one local application process."""

    def __init__(self, *, workers: int = 1) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="cargolab")

    def submit(self, kind: str, worker: Worker) -> str:
        job_id = f"{kind}-{secrets.token_hex(6)}"
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "kind": kind,
                "status": "queued",
                "progress": 0.0,
                "message": "Menunggu eksekusi",
                "created_at": now,
                "updated_at": now,
                "result": None,
                "error": None,
            }
        self._executor.submit(self._execute, job_id, worker)
        return job_id

    def _update(self, job_id: str, **values: Any) -> None:
        with self._lock:
            self._jobs[job_id].update(values)
            self._jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

    def _execute(self, job_id: str, worker: Worker) -> None:
        self._update(job_id, status="running", message="Sedang diproses")

        def progress(value: float, message: str) -> None:
            self._update(job_id, progress=max(0.0, min(1.0, value)), message=message)

        try:
            result = worker(progress)
        except Exception as error:  # surfaced to the polling client
            self._update(
                job_id,
                status="failed",
                message="Proses gagal",
                error={"type": type(error).__name__, "message": str(error)},
            )
        else:
            self._update(
                job_id,
                status="completed",
                progress=1.0,
                message="Selesai",
                result=result,
            )

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return None if job is None else deepcopy(job)


JOBS = JobStore()


__all__ = ["JOBS", "JobStore", "ProgressUpdater"]
