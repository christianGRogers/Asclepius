"""Reading a run directory that may be local or on a Modal volume.

The monitor needs exactly two things from a run: the event stream, and the
occasional small preview file. Both are plain files, so a remote run is just a
local run with a copy step in front -- which is why this abstraction is small and
why nothing above it knows where training actually happened.

Modal runs are reached by shelling out to the ``modal`` CLI rather than importing
its SDK. The SDK would have to be pip-installed into Slicer's bundled Python,
which this module deliberately avoids; the CLI already holds the user's
authentication token and lives in the project venv.

Stdlib only: this runs inside Slicer's Python 3.9.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

# Windows: keep subprocess from flashing a console window on every poll.
_NO_WINDOW = 0
if os.name == "nt":
    _NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

EVENTS_FILENAME = "events.jsonl"
MODAL_SCHEME = "modal://"


class RunSource:
    """A run directory the monitor can read files out of."""

    def __init__(self, location):
        self.location = location

    @property
    def label(self):
        return str(self.location)

    def events_path(self):
        """Local path to a readable copy of events.jsonl, or None."""
        raise NotImplementedError

    def fetch(self, relative_path):
        """Local path to a readable copy of a file inside the run, or None."""
        raise NotImplementedError

    def available(self):
        raise NotImplementedError


class LocalRunSource(RunSource):
    """A run directory on this machine, or on a mounted network share."""

    kind = "local"

    def events_path(self):
        path = os.path.join(self.location, EVENTS_FILENAME)
        return path if os.path.isfile(path) else None

    def fetch(self, relative_path):
        path = os.path.join(self.location, relative_path.replace("/", os.sep))
        return path if os.path.isfile(path) else None

    def available(self):
        return os.path.isdir(self.location)


class ModalRunSource(RunSource):
    """A run directory on a Modal volume, read through the ``modal`` CLI.

    Files are cached locally. Preview segmentations are cached by name and never
    re-fetched, since a given epoch's preview never changes; events.jsonl is
    re-fetched every poll because it is the thing that grows.
    """

    kind = "modal"

    def __init__(self, volume, run_path, cache_dir=None, modal_cli=None):
        RunSource.__init__(self, "{}{}/{}".format(MODAL_SCHEME, volume,
                                                  run_path.lstrip("/")))
        self.volume = volume
        self.run_path = run_path.strip("/")
        self.cache_dir = cache_dir or tempfile.mkdtemp(prefix="segtrain-modal-")
        self.modal_cli = modal_cli or find_modal_cli()
        self.last_error = None

    def _get(self, remote_rel, local_path):
        if not self.modal_cli:
            self.last_error = (
                "the modal CLI was not found. Install it in the project venv "
                "(pip install modal) or set the CLI path in the module panel."
            )
            return False

        local_dir = os.path.dirname(local_path)
        if local_dir and not os.path.isdir(local_dir):
            os.makedirs(local_dir)
        remote = "{}/{}".format(self.run_path, remote_rel.lstrip("/"))
        try:
            result = subprocess.run(
                [self.modal_cli, "volume", "get", "--force",
                 self.volume, remote, local_path],
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self.last_error = str(exc)
            return False
        if result.returncode != 0:
            self.last_error = (result.stderr or result.stdout or "").strip()[:300]
            return False
        self.last_error = None
        return os.path.isfile(local_path)

    def events_path(self):
        local = os.path.join(self.cache_dir, EVENTS_FILENAME)
        if self._get(EVENTS_FILENAME, local):
            return local
        # Fall back to the last successful copy so a transient CLI failure shows
        # stale data rather than an empty, alarming-looking UI.
        return local if os.path.isfile(local) else None

    def fetch(self, relative_path):
        local = os.path.join(self.cache_dir, relative_path.replace("/", os.sep))
        if os.path.isfile(local):
            return local
        return local if self._get(relative_path, local) else None

    def available(self):
        if not self.modal_cli:
            self.last_error = "modal CLI not found"
            return False
        return self.events_path() is not None


def find_modal_cli():
    """Locate the modal CLI.

    Slicer's Python does not have the SDK, and Slicer's PATH is not the shell's,
    so PATH alone is unreliable. Check the project venv next to this module
    first, then fall back to PATH.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo = os.path.dirname(os.path.dirname(here))
    candidates = [
        os.path.join(repo, ".venv", "Scripts", "modal.exe"),
        os.path.join(repo, ".venv", "bin", "modal"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return shutil.which("modal")


def parse_modal_location(location):
    """``modal://volume/path/to/run`` -> ``(volume, path)``."""
    body = str(location)[len(MODAL_SCHEME):].strip("/")
    if "/" not in body:
        return body, ""
    volume, path = body.split("/", 1)
    return volume, path


def make_source(location, cache_dir=None, modal_cli=None):
    """Build the right source for a location string.

    ``modal://volume/path`` is a Modal volume; anything else is a local path.
    Windows drive letters (``C:\\runs``) are never mistaken for a scheme because
    the check is an explicit prefix match.
    """
    text = str(location).strip()
    if text.lower().startswith(MODAL_SCHEME):
        volume, path = parse_modal_location(text)
        return ModalRunSource(volume, path, cache_dir=cache_dir, modal_cli=modal_cli)
    return LocalRunSource(text)
