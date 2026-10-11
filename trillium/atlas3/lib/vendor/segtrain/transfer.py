"""Moving a training export onto the cluster, and proving it got there.

This is the hop the pipeline did not have. ``segqueue-export`` writes the training
layout on the Girder host; ``segtrain index`` reads it on Trillium; nothing
carried it between them except whatever the operator typed that day, and nothing
checked the result. A transfer that dropped cases produced a smaller training set
and no error.

Four properties, and each one exists because of a specific way long transfers
fail.

**Only what is missing moves.** The manifest is fetched first, compared against
the destination, and the transport is handed the exact list of paths that are
absent or wrong. A retry after 900 of 1000 cases copies 100. Without this, every
interruption restarts an hour of work, which in practice means the operator stops
retrying and starts improvising.

**Interruption is expected, not exceptional.** A multi-hour ssh across a campus
network drops. The transport is retried with backoff, and because the work list is
recomputed from the destination each time, a retry is not a repeat -- it is
strictly less work. Partial files are quarantined in a dot-directory rather than
left in the tree, so a half-written volume can never be mistaken for a complete
one by the next pass or by ``index``.

**Arrival is verified, not assumed.** After the transport reports success the tree
is checked against the manifest by SHA-256. This is the only step that can
distinguish "rsync exited 0" from "the training data is correct", and they are not
the same claim: rsync is faithful about what it was asked to copy, and silent
about what it was never told to.

**It says what happened.** A receipt is written next to the data recording the
manifest it was built from, what moved, what was already there, and the
verification result. Three weeks later, when a per-class Dice looks wrong, the
first question is "what was this model trained on" -- and that question should be
answerable from the disk rather than from memory.

On where this runs: **a login or datamover node, never a compute node.** Trillium's
compute nodes have no outbound network, so a transfer submitted to the queue waits
for its allocation and then fails at the first connection. :func:`advise_host`
says so before the time is spent.
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

from segqueue.manifest import (
    FULL,
    MANIFEST_NAME,
    QUICK,
    Manifest,
    ManifestError,
    VerifyResult,
    needed,
    verify,
)

#: Written beside the data by :func:`pull`. Not part of any manifest.
RECEIPT_NAME = "transfer-receipt.json"

#: rsync keeps in-flight files here, inside the destination. A dot-directory
#: rather than the tree itself: a partial ``ct.nii.gz`` sitting next to the real
#: ones is the failure this whole module exists to prevent, and rsync's own
#: ``--partial`` does exactly that unless told otherwise.
PARTIAL_DIR = ".segtrain-partial"

#: Transport attempts before giving up. Three, because the first failure is
#: usually the network and the third is usually the configuration.
DEFAULT_ATTEMPTS = 3

#: Seconds before the first retry; doubled each time.
DEFAULT_BACKOFF = 5.0


class TransferError(RuntimeError):
    """The transport failed, or the data did not survive it."""


@dataclass
class TransferReport:
    """What one :func:`pull` did."""

    manifest_created: str = ""
    source: Dict[str, object] = field(default_factory=dict)
    totals: Dict[str, int] = field(default_factory=dict)
    already_present: int = 0
    transferred: List[str] = field(default_factory=list)
    attempts: int = 0
    verified: Optional[VerifyResult] = None
    seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return self.verified is not None and self.verified.is_clean

    def to_dict(self) -> Dict[str, object]:
        verified: Dict[str, object] = {}
        if self.verified is not None:
            verified = {
                "mode": self.verified.mode,
                "ok": len(self.verified.ok),
                "missing": self.verified.missing,
                "truncated": [
                    {"path": p, "expected": e, "found": f}
                    for p, e, f in self.verified.truncated
                ],
                "corrupt": self.verified.corrupt,
                "unreadable": [{"path": p, "error": e} for p, e in self.verified.unreadable],
                "extra": self.verified.extra,
                "broken_cases": self.verified.broken_cases,
            }
        return {
            "receipt_version": 1,
            "written": _utc_now(),
            "host": socket.gethostname(),
            "manifest": {"created": self.manifest_created, "source": self.source,
                         "totals": self.totals},
            "transfer": {"already_present": self.already_present,
                         "transferred": len(self.transferred),
                         "attempts": self.attempts,
                         "seconds": round(self.seconds, 1)},
            "verification": verified,
            "ok": self.ok,
        }

    def write(self, root) -> str:
        target = os.path.join(str(root), RECEIPT_NAME)
        scratch = target + ".partial"
        with open(scratch, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n")
        os.replace(scratch, target)
        return target


# -- transports -----------------------------------------------------------


class Transport:
    """Fetch named paths from somewhere into a local root.

    Kept to two methods so the orchestration in :func:`pull` can be tested
    without a network: everything interesting about a transfer is *which* files
    it decides to move and *what it does* when that fails, and neither needs ssh
    to exercise.
    """

    def fetch_manifest(self, destination: str) -> str:  # pragma: no cover - interface
        """Bring ``manifest.json`` into ``destination`` and return its path."""
        raise NotImplementedError

    def fetch(self, destination: str, paths: Sequence[str]) -> None:  # pragma: no cover
        """Bring exactly ``paths`` into ``destination``, or raise TransferError."""
        raise NotImplementedError


@dataclass
class RsyncTransport(Transport):
    """rsync over ssh, given exactly the files to move.

    ``remote`` is an rsync source with a trailing colon-path, as rsync spells it:
    ``segqueue@girder.example.org:/srv/segqueue/export``. The trailing slash is
    added here rather than being the operator's problem, because rsync's
    slash-sensitivity is the single most common way a transfer lands one directory
    deeper than intended.

    Flags chosen deliberately:

    ``--files-from`` so the work list is the plan, not a wildcard. ``--partial-dir``
    so interrupted files are quarantined instead of appearing complete.
    ``--append-verify`` so a resumed file is checksummed rather than assumed to
    match its prefix. No ``--delete``: the destination is ``$SCRATCH`` and may hold
    other work, and a transfer is not entitled to remove what it did not bring.
    """

    remote: str
    ssh_options: Sequence[str] = ()
    rsync: str = "rsync"
    bandwidth_limit: str = ""
    extra_args: Sequence[str] = ()
    runner: Optional[Callable[[Sequence[str]], int]] = None

    def _base(self) -> List[str]:
        command = [self.rsync, "--archive", "--compress", "--human-readable",
                   "--partial-dir=" + PARTIAL_DIR, "--append-verify"]
        if self.bandwidth_limit:
            command.append("--bwlimit=" + self.bandwidth_limit)
        if self.ssh_options:
            command += ["-e", "ssh " + " ".join(self.ssh_options)]
        command += list(self.extra_args)
        return command

    def _source(self) -> str:
        return self.remote if self.remote.endswith("/") else self.remote + "/"

    def _run(self, command: Sequence[str]) -> None:
        run = self.runner if self.runner is not None else _default_runner
        code = run(list(command))
        if code != 0:
            raise TransferError(
                f"rsync exited {code}. The work list is recomputed from the "
                "destination on every attempt, so retrying costs only what is "
                "still missing.")

    def fetch_manifest(self, destination: str) -> str:
        self._run(self._base() + [self._source() + MANIFEST_NAME, destination + os.sep])
        path = os.path.join(destination, MANIFEST_NAME)
        if not os.path.exists(path):
            raise TransferError(
                f"rsync succeeded but {MANIFEST_NAME} is not in {destination}. "
                "The export on the far side did not write one -- run "
                "segqueue-export again with a version that does.")
        return path

    def fetch(self, destination: str, paths: Sequence[str]) -> None:
        if not paths:
            return
        handle, listing = tempfile.mkstemp(prefix="segtrain-files-", suffix=".txt")
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as out:
                for path in paths:
                    out.write(path + "\n")
            self._run(self._base() + ["--files-from=" + listing,
                                      self._source(), destination + os.sep])
        finally:
            _unlink(listing)


@dataclass
class LocalTransport(Transport):
    """Copy from a mounted path.

    Not a toy: the Girder host's export directory is sometimes visible to the
    machine doing the training, and a shared filesystem is the cheapest correct
    transport there is. It also makes the orchestration testable end to end
    without a network.
    """

    source: str

    def _copy(self, relative: str, destination: str) -> None:
        origin = os.path.join(self.source, relative.replace("/", os.sep))
        if not os.path.exists(origin):
            raise TransferError(f"not at the source: {relative}")
        target = os.path.join(destination, relative.replace("/", os.sep))
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        # Write beside the target and rename, so an interrupted copy cannot leave
        # something that looks like a complete volume.
        scratch = target + ".partial"
        shutil.copyfile(origin, scratch)
        os.replace(scratch, target)

    def fetch_manifest(self, destination: str) -> str:
        self._copy(MANIFEST_NAME, destination)
        return os.path.join(destination, MANIFEST_NAME)

    def fetch(self, destination: str, paths: Sequence[str]) -> None:
        for relative in paths:
            self._copy(relative, destination)


def _default_runner(command: Sequence[str]) -> int:
    print("+ " + " ".join(command))
    return subprocess.run(list(command)).returncode


def _unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:  # pragma: no cover - a temp file we just wrote
        pass


# -- the pipeline ---------------------------------------------------------


def pull(transport: Transport, destination, attempts: int = DEFAULT_ATTEMPTS,
         backoff: float = DEFAULT_BACKOFF, mode: str = FULL,
         manifest: Optional[Manifest] = None, progress=None,
         sleep=time.sleep) -> TransferReport:
    """Fetch an export into ``destination`` and verify it against its manifest.

    Returns a report whether or not the data is intact; raises only when the
    transport could not be made to work at all. The caller decides what a broken
    case is worth -- for a training run it is fatal, and for a partial sync
    against a live annotation queue it may be expected.
    """
    destination = str(destination)
    os.makedirs(destination, exist_ok=True)
    started = time.time()
    report = TransferReport()

    if manifest is None:
        transport.fetch_manifest(destination)
        try:
            manifest = Manifest.read(destination)
        except ManifestError as exc:
            raise TransferError(str(exc)) from None

    report.manifest_created = manifest.created
    report.source = dict(manifest.source)
    report.totals = manifest.totals

    outstanding = needed(destination, manifest, mode=QUICK)
    wanted = list(outstanding)
    report.already_present = report.totals.get("files", 0) - len(wanted)

    ceiling = max(1, attempts)
    last: Optional[TransferError] = None
    attempt = 0
    while outstanding and attempt < ceiling:
        attempt += 1
        report.attempts = attempt
        if progress is not None:
            progress(attempt, len(outstanding))

        last = None
        try:
            transport.fetch(destination, outstanding)
        except TransferError as exc:
            last = exc

        # Recompute regardless of outcome. A failed rsync has usually still moved
        # some of it, so the next attempt is strictly smaller -- and a transport
        # that reports success without moving anything must not be mistaken for
        # progress, which is the one case worth failing fast on.
        before = len(outstanding)
        outstanding = needed(destination, manifest, mode=QUICK)
        if outstanding and last is None and len(outstanding) == before:
            raise TransferError(
                f"the transport reported success and moved none of the {before} "
                "outstanding file(s). Either the source does not have them, or "
                "the paths in the manifest do not match the source "
                "layout.")

        if outstanding and attempt < ceiling:
            sleep(backoff * (2 ** (attempt - 1)))

    if outstanding:
        detail = f"Last failure: {last}" if last is not None else (
            "The transport kept succeeding without completing the list.")
        raise TransferError(
            f"{len(outstanding)} file(s) still missing after "
            f"{report.attempts} attempt(s). {detail}")

    report.transferred = sorted(set(wanted))
    report.verified = verify(destination, manifest, mode=mode)
    report.seconds = time.time() - started
    return report


def advise_host(hostname: Optional[str] = None) -> List[str]:
    """Warnings about running a transfer from where we appear to be running it.

    Cheap, printed, and never fatal -- hostname patterns are a heuristic, and
    refusing to run because a node was renamed would be worse than a wrong guess.
    """
    name = (hostname or socket.gethostname()).lower()
    notes: List[str] = []
    if os.environ.get("SLURM_JOB_ID"):
        notes.append(
            "This looks like a SLURM job (SLURM_JOB_ID is set). Compute nodes "
            "have no outbound network, so a transfer here will wait for its "
            "allocation and then fail at the first connection. Run it from a "
            "login or datamover node instead.")
    if name.startswith("tri") and "dm" not in name and "log" not in name:
        notes.append(
            f"Hostname {name!r} does not look like a Trillium datamover or login "
            "node. Large transfers belong on tri-dm1.")
    return notes


def advise_destination(destination) -> List[str]:
    """Warnings about where the data is being put."""
    path = os.path.abspath(str(destination))
    notes: List[str] = []
    scratch = os.environ.get("SCRATCH")
    if scratch and not path.startswith(os.path.abspath(scratch)):
        notes.append(
            f"{path} is not under $SCRATCH ({scratch}). $HOME and $PROJECT are mounted "
            "read-only on Trillium's compute nodes, so a dataset in either is "
            "unusable by a training job -- which you discover after the queue "
            "wait.")
    return notes


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
