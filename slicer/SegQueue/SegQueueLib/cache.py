"""The annotator's local working directory: one case at a time, then gone.

The requirement this file exists for is "no large local storage footprint on the
annotator machine". That is not enforceable by asking undergraduates to tidy up,
so it is enforced structurally: every byte the extension writes goes under one
managed root, each case gets its own subdirectory, and opening case N+1 deletes
case N. If the cap is one case, the disk cost of the whole project is one CT --
about 0.2-0.5 GB -- no matter how many cases a student eventually annotates.

The second job here is crash resilience. A manifest beside each case records the
assignment, the accumulated annotation time and where the autosaved segmentation
sits, so a Slicer that dies at minute forty of a fifty-minute case comes back to
the work rather than to an empty queue slot. That manifest is also why the timer
survives a restart: elapsed time is accumulated into the file, not held in a
widget.

No Slicer imports. This is ordinary filesystem code and it is tested as such.
"""

import errno
import json
import os
import shutil
import time

#: Subdirectory name under the cache root for each case's working files.
_CASE_PREFIX = "case-"

#: Manifest filename inside a case directory.
MANIFEST_NAME = "segqueue.json"

#: Filename the in-progress segmentation is autosaved to.
WORK_NAME = "segmentation.seg.nrrd"

#: Refuse to start a download unless this much space remains free *after* it.
#: A CT that lands on a full disk fails at the worst possible moment -- halfway
#: through, with the case already assigned -- and Slicer itself needs headroom
#: for its own scene and temp files.
FREE_SPACE_MARGIN_BYTES = 2 * 1024 * 1024 * 1024


class CacheError(RuntimeError):
    """A local-storage problem stated in terms the annotator can act on."""


def defaultRoot():
    """Where the cache lives when nobody has chosen otherwise.

    Under the user's home rather than the system temp directory: temp gets swept
    by the OS at unpredictable moments, and losing an in-progress segmentation to
    a cleanup job would be indistinguishable from losing it to a bug.
    """
    return os.path.join(os.path.expanduser("~"), ".segqueue", "cases")


class CaseCache:
    """A capped, self-purging store of case working directories.

    ``maxCases`` is normally 1. It is configurable only because the server's
    policy allows raising an annotator's concurrent limit to 2-3, and a cache
    that held one case while the server had handed out three would purge work
    the annotator still owed.
    """

    def __init__(self, root=None, maxCases=1):
        self.root = root or defaultRoot()
        self.maxCases = max(1, int(maxCases))

    # ------------------------------------------------------------- locations

    def caseDir(self, assignmentId):
        return os.path.join(self.root, _CASE_PREFIX + str(assignmentId))

    def manifestPath(self, assignmentId):
        return os.path.join(self.caseDir(assignmentId), MANIFEST_NAME)

    def workPath(self, assignmentId):
        return os.path.join(self.caseDir(assignmentId), WORK_NAME)

    def volumePath(self, assignmentId, caseName, suffix=".nrrd"):
        safe = _safeName(caseName) or "volume"
        return os.path.join(self.caseDir(assignmentId), safe + suffix)

    # ------------------------------------------------------------ open/close

    def open(self, assignment, extra=None):
        """Create (or reopen) the working directory for an assignment.

        Returns its manifest. Reopening is the crash-resume path and must not
        disturb anything already on disk -- in particular it must not reset the
        accumulated time, or a student who crashes twice looks like they did the
        case in five minutes.
        """
        self.enforceCap(keep=assignment.assignment_id)
        directory = self.caseDir(assignment.assignment_id)
        _makedirs(directory)

        manifest = self.manifest(assignment.assignment_id)
        if manifest is None:
            manifest = {
                "assignmentId": assignment.assignment_id,
                "caseId": assignment.case_id,
                "caseName": assignment.case_name,
                "checksum": assignment.checksum,
                "sizeBytes": assignment.size_bytes,
                "attempt": assignment.attempt,
                "state": assignment.state,
                "createdAt": time.time(),
                "elapsedSeconds": 0.0,
                "volumePath": "",
                "workPath": "",
                "submitted": False,
            }
        # Attempt and state can legitimately have moved on since the directory
        # was created -- a rework comes back to the same assignment with a new
        # attempt number -- so refresh them without touching the time.
        manifest["attempt"] = assignment.attempt
        manifest["state"] = assignment.state
        if extra:
            manifest.update(extra)
        self.writeManifest(assignment.assignment_id, manifest)
        return manifest

    def manifest(self, assignmentId):
        """The manifest for an assignment, or None if there is no cached case.

        A corrupt manifest is treated as no manifest: it means a crash during
        the write, the case directory is about to be rebuilt anyway, and raising
        here would leave the annotator permanently unable to open the case.
        """
        path = self.manifestPath(assignmentId)
        try:
            with open(path) as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def writeManifest(self, assignmentId, manifest):
        """Write the manifest atomically, so a crash cannot truncate it."""
        path = self.manifestPath(assignmentId)
        _makedirs(os.path.dirname(path))
        tmp = path + ".tmp"
        with open(tmp, "w") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
        if os.path.exists(path):
            os.unlink(path)
        os.rename(tmp, path)
        return manifest

    def update(self, assignmentId, **fields):
        """Merge fields into a manifest. Returns the new manifest, or None."""
        manifest = self.manifest(assignmentId)
        if manifest is None:
            return None
        manifest.update(fields)
        return self.writeManifest(assignmentId, manifest)

    def addElapsed(self, assignmentId, seconds):
        """Accumulate annotation time. Called on every autosave and on close.

        Accumulating into the file rather than reporting one span at submit time
        is what makes the number honest across a crash, a lunch break with Slicer
        left open, and a case picked up again the next day.
        """
        manifest = self.manifest(assignmentId)
        if manifest is None:
            return 0.0
        total = float(manifest.get("elapsedSeconds", 0.0)) + max(0.0, float(seconds))
        self.writeManifest(assignmentId, dict(manifest, elapsedSeconds=total))
        return total

    def elapsed(self, assignmentId):
        manifest = self.manifest(assignmentId)
        return float((manifest or {}).get("elapsedSeconds", 0.0))

    # ---------------------------------------------------------------- purge

    def purge(self, assignmentId):
        """Delete everything for one assignment. Returns bytes reclaimed.

        Called the moment a submission is accepted or a case is released. Not
        deferred to a later sweep: the promise made to the ethics board is that
        image data does not linger on student laptops, and "we clean it up
        eventually" is a different promise.
        """
        directory = self.caseDir(assignmentId)
        size = _dirSize(directory)
        shutil.rmtree(directory, ignore_errors=True)
        return size

    def purgeAll(self):
        """Delete every cached case. Used at logout and by the panic button."""
        total = 0
        for assignmentId in self.assignmentIds():
            total += self.purge(assignmentId)
        return total

    def enforceCap(self, keep=None):
        """Purge oldest cases until at most ``maxCases`` remain, ``keep`` among them.

        Oldest-first by manifest creation time, because the newest case is the
        one being worked on. A directory with no readable manifest sorts oldest
        and goes first, which is the right treatment for debris.
        """
        entries = []
        for assignmentId in self.assignmentIds():
            if keep is not None and assignmentId == str(keep):
                continue
            manifest = self.manifest(assignmentId)
            created = float((manifest or {}).get("createdAt", 0.0))
            entries.append((created, assignmentId))
        entries.sort()

        slots = self.maxCases - (1 if keep is not None else 0)
        purged = []
        while len(entries) > max(0, slots):
            _created, assignmentId = entries.pop(0)
            self.purge(assignmentId)
            purged.append(assignmentId)
        return purged

    # -------------------------------------------------------------- queries

    def assignmentIds(self):
        """Assignment ids with a directory on disk, in arbitrary order."""
        try:
            names = os.listdir(self.root)
        except OSError:
            return []
        return [n[len(_CASE_PREFIX):] for n in names
                if n.startswith(_CASE_PREFIX)
                and os.path.isdir(os.path.join(self.root, n))]

    def entries(self):
        """Manifests for every cached case, newest first."""
        found = []
        for assignmentId in self.assignmentIds():
            manifest = self.manifest(assignmentId)
            if manifest is not None:
                found.append(manifest)
        found.sort(key=lambda m: m.get("createdAt", 0.0), reverse=True)
        return found

    def resumable(self):
        """Cached cases that still have work in them, newest first.

        A case whose manifest says it was submitted is debris from a purge that
        did not finish -- offering to resume it would invite a second submission
        the server would refuse.
        """
        return [m for m in self.entries() if not m.get("submitted")]

    def totalBytes(self):
        return _dirSize(self.root)

    def freeBytes(self):
        """Free space on the volume holding the cache, or None if unknowable."""
        target = self.root
        while target and not os.path.exists(target):
            parent = os.path.dirname(target)
            if parent == target:
                return None
            target = parent
        try:
            return shutil.disk_usage(target).free
        except OSError:
            return None

    def checkRoomFor(self, sizeBytes, margin=FREE_SPACE_MARGIN_BYTES):
        """Raise ``CacheError`` if a download of ``sizeBytes`` would not fit.

        Checked before asking the server for the file rather than discovering it
        at 90% of a 400 MB transfer, on a connection where that cost ten minutes.
        """
        free = self.freeBytes()
        if free is None:
            return  # unknowable on this filesystem; let the write fail honestly
        needed = int(sizeBytes) + int(margin)
        if free < needed:
            raise CacheError(
                "Not enough free disk space: this case needs "
                "{:.1f} GB including working room, and {:.1f} GB is free on the "
                "drive holding {}.\nFree some space, or point the cache at "
                "another drive in the module settings.".format(
                    needed / 1e9, free / 1e9, self.root))


def _safeName(name):
    """A filename that cannot escape the cache directory or upset Windows."""
    keep = []
    for ch in str(name or ""):
        keep.append(ch if (ch.isalnum() or ch in "-_.") else "_")
    return "".join(keep).strip("._") or ""


def _makedirs(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise CacheError(
                "Could not create the local case folder {}:\n{}".format(path, exc)
            ) from exc


def _dirSize(path):
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for filename in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, filename))
            except OSError:
                pass
    return total
