"""Self-update for SegQueue14, installed as the SegQueue extension (0.14.0 on).

A copy of ``SegQueueLib/updater.py`` with one change: the archive it accepts must
carry ``SegQueue14.py``. Since 0.14.0 the SegQueue release line *is* SegQueue14
(project lead, 2026-10-17): the archive is still named ``SegQueue-<v>-Slicer-<x.y>.zip``,
tagged ``segqueue-v<v>`` and rooted at ``SegQueue/``, so the update button of every
SegQueue 0.13 and older installs it, and this module's button keeps it current.

Safety rules unchanged from the live updater: never touch a checkout, validate the
whole archive before touching anything, back up then swap, delete nothing.
"""

import json
import os
import shutil
import tempfile
import time
import zipfile
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from segqueue import release as rel

#: Where releases are published. Read-only, unauthenticated, public.
GITHUB_REPO = "christianGRogers/Asclepius"
RELEASES_URL = "https://api.github.com/repos/{}/releases".format(GITHUB_REPO)

#: How many releases to look at. Enough to find the newest even if a handful of
#: other tags -- training pipeline releases, prereleases -- sit on top of it.
RELEASE_PAGE_SIZE = 20

#: Connect/read timeouts for the check. Deliberately short: this runs when the
#: annotator opens the module, and a slow GitHub must never be the reason the
#: panel takes ten seconds to appear. Missing an update is free; a hang is not.
CHECK_TIMEOUT = (4, 6)

#: Timeouts for the download itself, which is a hundred kilobytes over whatever
#: connection a student has.
DOWNLOAD_TIMEOUT = (10, 120)

#: Read size while streaming the archive.
CHUNK_BYTES = 256 * 1024

#: Refuse an archive larger than this. A SegQueue package is ~120 KB; anything
#: at this scale is not one, and unpacking it would be somebody else's problem
#: happening on an annotator's disk.
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024


class UpdateError(RuntimeError):
    """An update could not be checked, downloaded or installed, stated usably."""


# ---------------------------------------------------------------- discovery

def checkForUpdate(currentVersion: str, slicerVersion: str, session: Any = None,
                   allowPrerelease: bool = False,
                   timeout: Tuple[float, float] = CHECK_TIMEOUT) -> Optional[Dict[str, Any]]:
    """The release to offer, or ``None``. Raises ``UpdateError`` on a bad reply.

    Callers treat any failure as "no update": an annotator on a train, or behind
    a proxy that blocks GitHub, must still be able to work.
    """
    getter = (session or requests).get
    try:
        response = getter(
            RELEASES_URL,
            params={"per_page": RELEASE_PAGE_SIZE},
            headers={"Accept": "application/vnd.github+json"},
            timeout=timeout)
    except Exception as exc:  # requests raises a family, not a single class
        raise UpdateError("Could not reach GitHub to check for updates: "
                          "{}".format(exc)) from exc

    if response.status_code == 403:
        # Unauthenticated GitHub allows 60 requests an hour per address. A lab
        # of thirty annotators behind one NAT can exhaust that between them, so
        # say what happened rather than implying the update system is broken.
        raise UpdateError(
            "GitHub is rate-limiting update checks from this network. This is "
            "temporary; the check will succeed again within the hour.")
    if response.status_code != 200:
        raise UpdateError("GitHub returned HTTP {} when asked for releases."
                          .format(response.status_code))
    try:
        releases = response.json()
    except ValueError:
        raise UpdateError("GitHub's reply to the update check was not JSON.") from None
    if not isinstance(releases, list):
        raise UpdateError("GitHub's reply to the update check was not a release list.")

    return rel.update_available(releases, currentVersion,
                                slicer_version=slicerVersion,
                                allow_prerelease=allowPrerelease)


# ----------------------------------------------------------------- download

def downloadAsset(asset: Dict[str, Any], destPath: str, session: Any = None,
                  progress: Optional[Callable[[int, int], None]] = None,
                  timeout: Tuple[float, float] = DOWNLOAD_TIMEOUT) -> int:
    """Stream a release asset to ``destPath``. Returns the byte count.

    Written to ``.part`` and renamed only on success, so an interrupted download
    can never be mistaken for a complete archive by the code that opens it next.
    """
    url = asset.get("browser_download_url")
    if not url:
        raise UpdateError("That release has no downloadable archive attached.")

    declared = int(asset.get("size") or 0)
    if declared and declared > MAX_ARCHIVE_BYTES:
        raise UpdateError("The published archive is implausibly large ({} bytes); "
                          "refusing to download it.".format(declared))

    partPath = destPath + ".part"
    getter = (session or requests).get
    written = 0
    try:
        response = getter(url, stream=True, timeout=timeout)
        if response.status_code != 200:
            raise UpdateError("Downloading the update failed with HTTP {}."
                              .format(response.status_code))
        with open(partPath, "wb") as handle:
            for chunk in response.iter_content(chunk_size=CHUNK_BYTES):
                if not chunk:
                    continue
                written += len(chunk)
                if written > MAX_ARCHIVE_BYTES:
                    raise UpdateError("The download exceeded the size limit and "
                                      "was abandoned.")
                handle.write(chunk)
                if progress is not None:
                    progress(written, declared or written)
    except UpdateError:
        _quietUnlink(partPath)
        raise
    except Exception as exc:
        _quietUnlink(partPath)
        raise UpdateError("Downloading the update failed: {}".format(exc)) from exc

    if declared and written != declared:
        _quietUnlink(partPath)
        raise UpdateError("The download stopped early ({} of {} bytes). Nothing "
                          "has been changed.".format(written, declared))

    os.replace(partPath, destPath)
    return written


# ------------------------------------------------------------------ install

def moduleRoots(moduleDir: str) -> Tuple[str, Optional[str]]:
    """``(scriptedModulesDir, extensionRoot)`` for an installed extension.

    ``extensionRoot`` is the directory named after the extension, the one the
    Extension Manager created:
    ``<Extensions-NNNNN>/SegQueue/lib/Slicer-5.8/qt-scripted-modules`` ->
    ``<Extensions-NNNNN>/SegQueue``. ``None`` when the layout is not that, which
    is the signal that this is not an installed extension at all.
    """
    scripted = os.path.abspath(moduleDir)
    parts = scripted.replace("\\", "/").split("/")
    if len(parts) < 4 or parts[-1] != "qt-scripted-modules" or not parts[-2].startswith("Slicer-"):
        return scripted, None
    root = os.path.abspath(os.path.join(scripted, os.pardir, os.pardir, os.pardir))
    return scripted, root


def packagedSlicerVersion(moduleDir: str) -> Optional[str]:
    """``"5.8"`` for a module installed under ``lib/Slicer-5.8/qt-scripted-modules``.

    The Slicer version the installed archive was built for, which is the one to
    update from. It is not the running Slicer's on 5.10 and later, where every
    install holds the 5.8 archive (#97). ``None`` when the layout is not that.
    """
    scripted, root = moduleRoots(moduleDir)
    if root is None:
        return None
    version = os.path.basename(os.path.dirname(scripted))[len("Slicer-"):]
    parts = version.split(".")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return None
    return version


def isCheckout(moduleDir: str) -> bool:
    """Whether this module is being run out of a git working tree.

    Checked by walking up for a ``.git``. A developer's uncommitted work is not
    something an update button gets to overwrite.
    """
    directory = os.path.abspath(moduleDir)
    previous = None
    while directory and directory != previous:
        if os.path.exists(os.path.join(directory, ".git")):
            return True
        previous, directory = directory, os.path.dirname(directory)
    return False


def canInstall(moduleDir: str) -> Tuple[bool, str]:
    """``(ok, reason)``. ``reason`` is annotator-facing text when ``ok`` is False."""
    if isCheckout(moduleDir):
        return False, ("This module is running from a source checkout, so it "
                       "updates with git rather than from a release. Run "
                       "'git pull' in the repository and restart Slicer.")
    _scripted, root = moduleRoots(moduleDir)
    if root is None:
        return False, ("This module is not installed as a Slicer extension, so "
                       "it cannot update itself. Reinstall it with the one-line "
                       "installer (slicer/install-segqueue.py) or through "
                       "Extensions Manager -> Install from file.")
    if not os.access(moduleDir, os.W_OK):
        return False, ("Slicer's extension folder is not writable by this "
                       "account, so the update cannot be installed. Ask whoever "
                       "administers this machine, or reinstall through "
                       "Extensions Manager -> Install from file.")
    return True, ""


def inspectArchive(zipPath: str, slicerVersion: str) -> List[str]:
    """Validate a downloaded archive. Returns its member list.

    Raises ``UpdateError`` describing what is wrong, in terms of what the
    annotator should do next rather than what the zip module said.
    """
    try:
        with zipfile.ZipFile(zipPath) as archive:
            names = archive.namelist()
            bad = archive.testzip()
    except zipfile.BadZipFile:
        raise UpdateError("The downloaded update is not a valid archive. Nothing "
                          "has been changed; try again.") from None
    if bad is not None:
        raise UpdateError("The downloaded update is corrupt ({}). Nothing has "
                          "been changed; try again.".format(bad))

    for name in names:
        # Belt and braces against a crafted archive escaping the target
        # directory. Python 3.9's extractall does sanitise, but this code writes
        # into a live Slicer install and the check costs nothing.
        parts = name.replace("\\", "/").split("/")
        if name.startswith("/") or name.startswith("\\") or ".." in parts:
            raise UpdateError("The downloaded update contains an unsafe path "
                              "({}) and was rejected.".format(name))

    members = rel.archive_members(names, slicerVersion)
    if not any(m.endswith("/SegQueue14.py") for m in members):
        # An archive without SegQueue14 is a pre-0.14 SegQueue package; installing
        # it would bring the retired module back over this one.
        raise UpdateError(
            "The downloaded archive does not contain a SegQueue14 module for "
            "Slicer {}. Nothing has been changed.".format(slicerVersion))
    return members


def installArchive(zipPath: str, moduleDir: str, slicerVersion: str,
                   backupRoot: Optional[str] = None) -> str:
    """Replace the installed module with the contents of ``zipPath``.

    Returns the path of the backup that was taken. Raises ``UpdateError`` with
    the backup already restored if the swap fails partway.
    """
    ok, reason = canInstall(moduleDir)
    if not ok:
        raise UpdateError(reason)

    members = inspectArchive(zipPath, slicerVersion)
    scripted, _root = moduleRoots(moduleDir)
    prefix = "SegQueue/lib/Slicer-{}/qt-scripted-modules/".format(slicerVersion)

    staging = tempfile.mkdtemp(prefix="segqueue14-update-")
    backup = backupRoot or os.path.join(
        os.path.dirname(scripted), "qt-scripted-modules.backup-{}".format(
            time.strftime("%Y%m%d-%H%M%S")))
    try:
        with zipfile.ZipFile(zipPath) as archive:
            archive.extractall(staging, members=members)

        # Copy the whole tree aside first. It is a few hundred kilobytes, and it
        # is the only thing standing between a failed swap and an annotator with
        # no working module.
        _copyOver(scripted, backup)

        try:
            _copyOver(os.path.join(staging, *prefix.rstrip("/").split("/")), scripted)
        except Exception as exc:
            _restore(backup, scripted)
            raise UpdateError(
                "Installing the update failed and the previous version has been "
                "put back ({}). Nothing is lost; try again, or install the zip "
                "through Extensions Manager.".format(exc)) from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return backup


def _copyOver(sourceDir, targetDir):
    """Copy a tree over another, overwriting files and never deleting any."""
    for dirpath, _dirnames, filenames in os.walk(sourceDir):
        relative = os.path.relpath(dirpath, sourceDir)
        destination = targetDir if relative == "." else os.path.join(targetDir, relative)
        if not os.path.isdir(destination):
            os.makedirs(destination)
        for filename in filenames:
            shutil.copy2(os.path.join(dirpath, filename),
                         os.path.join(destination, filename))


def _restore(backup, targetDir):
    try:
        _copyOver(backup, targetDir)
    except Exception:
        # Nothing useful is left to do here, and raising would replace a
        # specific failure message with a vaguer one.
        pass


def _quietUnlink(path):
    try:
        os.unlink(path)
    except OSError:
        pass


# -------------------------------------------------------------------- cache

def readCache(text: Optional[str]) -> Dict[str, Any]:
    """Parse a cached check result. ``{}`` when it is missing or unreadable."""
    if not text:
        return {}
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def cacheIsFresh(cache: Dict[str, Any], maxAgeSeconds: float,
                 now: Optional[float] = None) -> bool:
    """Whether a cached check is recent enough to skip asking GitHub again.

    Rate limiting is the reason this exists: sixty unauthenticated requests an
    hour is shared by every annotator behind one university NAT, and the module
    is opened many times a day.
    """
    now = time.time() if now is None else now
    try:
        checkedAt = float(cache.get("checkedAt", 0.0))
    except (TypeError, ValueError):
        return False
    if checkedAt <= 0:
        # No timestamp means never checked, not "checked at the epoch". The
        # difference only bites on a machine whose clock is wrong, which is
        # exactly when a cache should be distrusted.
        return False
    # A clock that jumped backwards leaves a future timestamp. Treat that as
    # stale too, or the check never runs again on that machine.
    return 0 <= (now - checkedAt) < maxAgeSeconds
