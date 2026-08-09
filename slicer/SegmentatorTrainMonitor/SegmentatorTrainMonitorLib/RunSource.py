"""Reading a run directory that may be local or on the training machine.

The monitor needs exactly two things from a run: the event stream, and the
occasional small preview file. Both are plain files, so a remote run is just a
local run with a copy step in front -- which is why this abstraction is small
and why nothing above it knows where training actually happened.

Remote access shells out to the OpenSSH client that ships with Windows 10+,
macOS and Linux. A Python SSH library would have to be pip-installed into
Slicer's bundled interpreter and would still not understand the user's
``~/.ssh/config``, jump hosts or agent.

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


class RemoteRunSource(RunSource):
    """A run directory on another machine, reached over SSH.

    Files are copied into a local cache directory. Preview segmentations are
    cached by name and never re-fetched, since a given epoch's preview never
    changes; events.jsonl is re-fetched every poll because it is the thing that
    grows.
    """

    kind = "ssh"

    def __init__(self, host, remote_dir, cache_dir=None, ssh_options=None):
        RunSource.__init__(self, "{}:{}".format(host, remote_dir))
        self.host = host
        self.remote_dir = remote_dir.rstrip("/")
        self.cache_dir = cache_dir or tempfile.mkdtemp(prefix="segtrain-monitor-")
        self.ssh_options = list(ssh_options or ["-o", "BatchMode=yes",
                                                "-o", "ConnectTimeout=10"])
        self.last_error = None

    def _scp(self, remote_rel, local_path):
        if shutil.which("scp") is None:
            self.last_error = "no 'scp' on PATH"
            return False
        local_dir = os.path.dirname(local_path)
        if local_dir and not os.path.isdir(local_dir):
            os.makedirs(local_dir)
        remote = "{}:{}/{}".format(self.host, self.remote_dir, remote_rel)
        try:
            result = subprocess.run(
                ["scp", "-q"] + self.ssh_options + [remote, local_path],
                capture_output=True,
                text=True,
                timeout=120,
                creationflags=_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self.last_error = str(exc)
            return False
        if result.returncode != 0:
            self.last_error = (result.stderr or "").strip() or "scp failed"
            return False
        self.last_error = None
        return True

    def events_path(self):
        local = os.path.join(self.cache_dir, EVENTS_FILENAME)
        if self._scp(EVENTS_FILENAME, local):
            return local
        # Fall back to the last successful copy so a dropped connection shows
        # stale data rather than an empty, alarming-looking UI.
        return local if os.path.isfile(local) else None

    def fetch(self, relative_path):
        local = os.path.join(self.cache_dir, relative_path.replace("/", os.sep))
        if os.path.isfile(local):
            return local
        return local if self._scp(relative_path, local) else None

    def available(self):
        if shutil.which("ssh") is None:
            self.last_error = "no 'ssh' on PATH"
            return False
        try:
            result = subprocess.run(
                ["ssh"] + self.ssh_options + [self.host,
                                              "test -d {}".format(self.remote_dir)],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self.last_error = str(exc)
            return False
        if result.returncode != 0:
            self.last_error = (result.stderr or "").strip() or "run directory not found"
            return False
        self.last_error = None
        return True


def make_source(location, cache_dir=None):
    """Build the right source for a location string.

    ``user@host:/path/to/run`` is remote; anything else is a local path. The
    check is deliberately narrow so Windows drive letters (``C:\\runs``) are not
    mistaken for a host:path pair.
    """
    text = str(location).strip()
    if "@" in text and ":" in text.split("@", 1)[1]:
        host, remote_dir = text.split(":", 1)
        return RemoteRunSource(host, remote_dir, cache_dir=cache_dir)
    return LocalRunSource(text)
