"""Backend interface shared by local, SSH and SLURM execution."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Optional


class BackendError(RuntimeError):
    pass


@dataclass
class Job:
    """A launched training run."""

    backend: str
    command: Sequence[str]
    run_dir: str
    pid: Optional[int] = None
    job_id: Optional[str] = None
    returncode: Optional[int] = None
    detail: dict = field(default_factory=dict)

    def describe(self) -> str:
        who = f"pid {self.pid}" if self.pid else (f"job {self.job_id}" if self.job_id else "?")
        return f"[{self.backend}] {who} -> {self.run_dir}"


class Backend:
    """Launch a command and let something else watch the event stream.

    Backends deliberately do not stream logs or report progress. Progress lives
    in ``events.jsonl``, which the monitor reads directly; a backend that also
    tried to relay it would be a second, competing source of truth that breaks
    the moment you detach and reattach.
    """

    name = "base"

    def submit(
        self,
        command: Sequence[str],
        run_dir: str,
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
    ) -> Job:
        raise NotImplementedError

    def is_running(self, job: Job) -> bool:
        raise NotImplementedError

    def cancel(self, job: Job) -> bool:
        raise NotImplementedError
