"""Where a training run executes.

Two backends, one output contract. Both produce the same ``events.jsonl`` in a
run directory, so the preview daemon and the Slicer monitor neither know nor care
which one ran -- and a run can be watched from a laptop while it executes on a
compute node three provinces away.

``local``
    A detached child process on this machine.
``slurm``
    One ``sbatch`` job. For a run longer than the cluster's walltime cap, use
    ``segtrain scinet submit`` instead: it chains jobs across the cap using the
    trainer's pause/resume protocol, which a single submission cannot do.

Inside a SLURM job, training is a *local* foreground run; the job script calls
straight through to ``segtrain train --foreground``.
"""

from __future__ import annotations

from .base import Backend, BackendError, Job
from .local import LocalBackend
from .slurm import SlurmBackend

__all__ = ["Backend", "BackendError", "Job", "LocalBackend", "SlurmBackend", "get_backend"]

BACKENDS = {"local": LocalBackend, "slurm": SlurmBackend}


def get_backend(name: str = "local", **kwargs) -> Backend:
    try:
        cls = BACKENDS[name]
    except KeyError:
        raise BackendError(
            f"unknown backend {name!r}; choose from {', '.join(sorted(BACKENDS))}"
        ) from None
    return cls(**kwargs)
