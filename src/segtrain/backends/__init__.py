"""Where a training run executes.

Only local execution lives here. Training on Modal is not a backend: Modal
functions are launched through its SDK rather than by running a command
somewhere, so that path lives in ``segtrain.modal_app``. What the two share is
the output contract -- both produce the same ``events.jsonl`` in a run directory,
so the preview daemon and the Slicer monitor neither know nor care which ran.

Inside a Modal container, training is a *local* run; the Modal function calls
straight through to this backend.
"""

from __future__ import annotations

from .base import Backend, BackendError, Job
from .local import LocalBackend

__all__ = ["Backend", "BackendError", "Job", "LocalBackend", "get_backend"]


def get_backend(name: str = "local", **kwargs) -> Backend:
    if name != "local":
        raise BackendError(
            f"unknown backend {name!r}; only 'local' is supported. "
            "For GPU training use `segtrain modal train`."
        )
    return LocalBackend(**kwargs)
