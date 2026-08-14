"""Reading a run directory that may be local or on a cluster login node.

The monitor needs exactly two things from a run: the event stream, and the
occasional small preview file. Both are plain files, so a remote run is just a
local run with a copy step in front -- which is why this abstraction is small and
why nothing above it knows where training actually happened.

Cluster runs are reached with the system ``ssh``/``scp`` rather than a Python SSH
library, because nothing may be pip-installed into Slicer's bundled Python. That
also means ``~/.ssh/config`` applies, so a host alias with ``ControlMaster``
configured costs one TCP handshake for the whole session instead of one per poll
-- worth setting up, since SciNet's login nodes are several hundred milliseconds
away and the monitor polls every ten seconds.

A run on SciNet lives on ``$SCRATCH``, which the login nodes share with the
compute nodes, so the monitor reads the live file while the job writes it. There
is no staging step and nothing to synchronise.

Stdlib only: this runs inside Slicer's Python 3.9.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile

# Windows: keep subprocess from flashing a console window on every poll.
_NO_WINDOW = 0
if os.name == "nt":
    _NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

EVENTS_FILENAME = "events.jsonl"

# user@host:/path, or host:/path. Anchored on a colon followed by a slash so a
# Windows drive letter (C:\runs, and even C:/runs) can never match: a drive
# letter is one character, and this needs at least two before the colon.
_SSH_LOCATION = re.compile(r"^(?P<host>[^:/\\]{2,}):(?P<path>/.*)$")


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


class SshRunSource(RunSource):
    """A run directory on another machine, read with ``ssh`` and ``scp``.

    Files are cached locally. Preview segmentations are cached by name and never
    re-fetched, since a given epoch's preview never changes; events.jsonl is
    re-fetched every poll because it is the thing that grows.

    events.jsonl is pulled with ``ssh cat`` rather than ``scp`` because it is
    append-only and small: a single stream avoids scp's second round trip, and
    the file is complete-as-of-read by construction. A truncated final line --
    the job appending while we read -- is the reader's problem to tolerate, and
    ``segtrain.events`` already skips unparseable lines for exactly this reason.
    """

    kind = "ssh"

    def __init__(self, host, run_path, cache_dir=None, identity_file=None,
                 ssh_options=None):
        RunSource.__init__(self, "{}:{}".format(host, run_path))
        self.host = host
        self.run_path = run_path.rstrip("/")
        self.cache_dir = cache_dir or tempfile.mkdtemp(prefix="segtrain-ssh-")
        self.identity_file = identity_file or None
        self.ssh_options = list(ssh_options or [])
        self.last_error = None

    def _base_options(self):
        # BatchMode: never sit at a password prompt with no terminal to type
        # into -- a missing key must fail fast and visibly in the panel instead
        # of hanging the UI thread until the timeout.
        options = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=15"]
        if self.identity_file:
            options += ["-i", self.identity_file]
        return options + self.ssh_options

    def _run(self, argv, timeout, stdout_path=None):
        handle = None
        try:
            if stdout_path is not None:
                handle = open(stdout_path, "wb")
            result = subprocess.run(
                argv,
                stdout=handle if handle is not None else subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                creationflags=_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self.last_error = str(exc)
            return None
        finally:
            if handle is not None:
                handle.close()

        if result.returncode != 0:
            detail = (result.stderr or b"").decode("utf-8", "replace").strip()
            self.last_error = detail[:300] or "exit code {}".format(result.returncode)
            return None
        self.last_error = None
        return result

    def _remote(self, relative_path):
        return "{}/{}".format(self.run_path, relative_path.lstrip("/"))

    def events_path(self):
        local = os.path.join(self.cache_dir, EVENTS_FILENAME)
        argv = ["ssh"] + self._base_options() + [
            self.host, "cat -- {}".format(_quote(self._remote(EVENTS_FILENAME)))]
        # Write to a temporary and move into place: a failed or partial transfer
        # must not destroy the previous good copy, which is what the UI falls
        # back to.
        staging = local + ".part"
        if self._run(argv, timeout=120, stdout_path=staging) is not None:
            try:
                os.replace(staging, local)
            except OSError as exc:
                self.last_error = str(exc)
        elif os.path.isfile(staging):
            os.remove(staging)

        # Fall back to the last successful copy so a transient network failure
        # shows stale data rather than an empty, alarming-looking UI.
        return local if os.path.isfile(local) else None

    def fetch(self, relative_path):
        local = os.path.join(self.cache_dir, relative_path.replace("/", os.sep))
        if os.path.isfile(local):
            return local
        local_dir = os.path.dirname(local)
        if local_dir and not os.path.isdir(local_dir):
            os.makedirs(local_dir)

        remote = "{}:{}".format(self.host, self._remote(relative_path))
        argv = ["scp"] + self._base_options() + ["-p", remote, local]
        # Previews are whole NIfTI volumes over a WAN link; a few MB at a few
        # MB/s wants a much wider window than the event stream.
        if self._run(argv, timeout=600) is None:
            return None
        return local if os.path.isfile(local) else None

    def available(self):
        return self.events_path() is not None


def _quote(path):
    """Single-quote a path for the remote shell.

    ssh concatenates its command arguments and hands the result to the login
    shell, so quoting is ours to do. Run directories are named after nnU-Net
    datasets and contain no quotes, but a path with a space would otherwise
    silently read the wrong file.
    """
    return "'" + str(path).replace("'", "'\\''") + "'"


def parse_ssh_location(location):
    """``user@host:/path/to/run`` -> ``(host, path)``, or None if not remote."""
    match = _SSH_LOCATION.match(str(location).strip())
    if not match:
        return None
    return match.group("host"), match.group("path")


def make_source(location, cache_dir=None, identity_file=None, ssh_options=None):
    """Build the right source for a location string.

    ``user@host:/path`` is read over SSH; anything else is a local path.
    """
    text = str(location).strip()
    remote = parse_ssh_location(text)
    if remote:
        host, path = remote
        return SshRunSource(host, path, cache_dir=cache_dir,
                            identity_file=identity_file, ssh_options=ssh_options)
    return LocalRunSource(text)
