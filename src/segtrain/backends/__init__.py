"""Where a training run executes: this machine, a remote box, or a cluster queue.

All three backends launch the *same* command and produce the *same*
``events.jsonl`` in a run directory. Nothing downstream -- not the preview
daemon, not the Slicer monitor -- knows or cares which was used. That is what
lets the pipeline be developed on a laptop and run on rented hardware without a
second code path.
"""

from __future__ import annotations

from typing import Optional

from .base import Backend, BackendError, Job
from .local import LocalBackend
from .slurm import SlurmBackend
from .ssh import SshBackend

__all__ = [
    "Backend",
    "BackendError",
    "Job",
    "LocalBackend",
    "SshBackend",
    "SlurmBackend",
    "get_backend",
]


def get_backend(name: str, **kwargs) -> Backend:
    backends = {"local": LocalBackend, "ssh": SshBackend, "slurm": SlurmBackend}
    if name not in backends:
        raise BackendError(f"unknown backend {name!r}; expected one of {sorted(backends)}")
    return backends[name](**kwargs)


def default_backend(remote: Optional[str] = None) -> Backend:
    return SshBackend(remote) if remote else LocalBackend()
