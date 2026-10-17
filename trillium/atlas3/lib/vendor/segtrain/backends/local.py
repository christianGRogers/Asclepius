"""Run training as a detached subprocess on this machine."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from .base import Backend, BackendError, Job

JOB_FILE = "job.json"


class LocalBackend(Backend):
    """Launches nnU-Net in a child process, detached from the caller's lifetime.

    Detaching matters for the Slicer use case: the module starts a run and the
    user then closes Slicer, or Slicer crashes. Neither should take a two-day
    training run with it. stdout and stderr go to a log file in the run
    directory rather than a pipe, because nothing is guaranteed to be reading a
    pipe and a full pipe buffer would block the trainer.
    """

    name = "local"

    def submit(
        self,
        command: Sequence[str],
        run_dir: str,
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
    ) -> Job:
        run_path = Path(run_dir)
        run_path.mkdir(parents=True, exist_ok=True)
        log_path = run_path / "train.log"

        creationflags = 0
        start_new_session = False
        if os.name == "nt":
            # Detach from this console so Ctrl-C in the launching terminal, or
            # Slicer exiting, does not signal the trainer.
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
                subprocess, "DETACHED_PROCESS", 0
            )
        else:
            start_new_session = True

        log = open(log_path, "ab")
        try:
            proc = subprocess.Popen(
                list(command),
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                env=env or os.environ.copy(),
                cwd=cwd,
                creationflags=creationflags,
                start_new_session=start_new_session,
            )
        except FileNotFoundError as exc:
            log.close()
            raise BackendError(f"could not launch {command[0]!r}: {exc}") from exc
        finally:
            # The child holds its own handle; ours would otherwise keep the file
            # open for as long as this process lives.
            log.close()

        job = Job(backend=self.name, command=list(command), run_dir=str(run_path), pid=proc.pid)
        _write_job(run_path, job)
        return job

    def is_running(self, job: Job) -> bool:
        if not job.pid:
            return False
        try:
            if os.name == "nt":
                out = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {job.pid}", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                return str(job.pid) in out.stdout
            os.kill(job.pid, 0)  # signal 0: existence check only
            return True
        except (OSError, subprocess.SubprocessError):
            return False

    def cancel(self, job: Job) -> bool:
        if not job.pid:
            return False
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(job.pid), "/T", "/F"],
                    capture_output=True,
                    timeout=30,
                )
            else:
                os.kill(job.pid, signal.SIGTERM)
            return True
        except (OSError, subprocess.SubprocessError):
            return False


def _write_job(run_dir: Path, job: Job) -> None:
    """Record the job so a later process -- or Slicer -- can find and stop it."""
    payload = {
        "backend": job.backend,
        "pid": job.pid,
        "job_id": job.job_id,
        "command": list(job.command),
        "run_dir": job.run_dir,
        "python": sys.executable,
    }
    with open(run_dir / JOB_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def read_job(run_dir: Path) -> Optional[Job]:
    path = Path(run_dir) / JOB_FILE
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    return Job(
        backend=data.get("backend", "local"),
        command=data.get("command", []),
        run_dir=data.get("run_dir", str(run_dir)),
        pid=data.get("pid"),
        job_id=data.get("job_id"),
    )
