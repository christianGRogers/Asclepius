"""Self-update for JanusMRead, from GitHub releases tagged ``janusm-read-v<v>``.

Shaped like ``SegQueue14Lib.updater`` and sharing nothing with it: its own tag,
its own archive name and root (``JanusMRead/``), and it accepts only an archive
that carries ``JanusMRead.py``. A SegQueue archive is refused, and a JanusMRead
archive is refused by SegQueue14's updater (no ``SegQueue14.py``).

Publishing a release is the project lead's decision; until one exists the check
simply finds nothing. Safety rules as SegQueue's: never touch a checkout, validate
the whole archive before touching anything, back up then copy over, delete nothing.
"""

import os
import shutil
import tempfile
import time
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from . import release as rel

GITHUB_REPO = "christianGRogers/Asclepius"
RELEASES_URL = "https://api.github.com/repos/{}/releases".format(GITHUB_REPO)
RELEASE_PAGE_SIZE = 30
CHECK_TIMEOUT = (4, 6)
DOWNLOAD_TIMEOUT = (10, 120)
CHUNK_BYTES = 256 * 1024
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MODULE_FILE = "/JanusMRead.py"


class UpdateError(RuntimeError):
    """An update could not be checked, downloaded or installed, stated usably."""


def checkForUpdate(currentVersion: str, slicerVersion: str, session: Any = None,
                   timeout: Tuple[float, float] = CHECK_TIMEOUT) -> Optional[Dict[str, Any]]:
    """The release to offer, or ``None``. Raises ``UpdateError`` on a bad reply."""
    if session is None:
        import requests as session
    try:
        response = session.get(RELEASES_URL, params={"per_page": RELEASE_PAGE_SIZE},
                               headers={"Accept": "application/vnd.github+json"},
                               timeout=timeout)
    except Exception as exc:
        raise UpdateError("Could not reach GitHub to check for updates: {}".format(exc)) \
            from exc
    if response.status_code == 403:
        raise UpdateError("GitHub is rate-limiting update checks from this network; "
                          "try again within the hour.")
    if response.status_code != 200:
        raise UpdateError("GitHub returned HTTP {} when asked for releases."
                          .format(response.status_code))
    try:
        releases = response.json()
    except ValueError:
        raise UpdateError("GitHub's reply to the update check was not JSON.") from None
    if not isinstance(releases, list):
        raise UpdateError("GitHub's reply to the update check was not a release list.")
    return rel.update_available(releases, currentVersion, slicer_version=slicerVersion)


def downloadAsset(asset: Dict[str, Any], destPath: str, session: Any = None,
                  timeout: Tuple[float, float] = DOWNLOAD_TIMEOUT) -> int:
    url = asset.get("browser_download_url")
    if not url:
        raise UpdateError("That release has no downloadable archive attached.")
    declared = int(asset.get("size") or 0)
    if declared > MAX_ARCHIVE_BYTES:
        raise UpdateError("The published archive is implausibly large; refusing it.")
    if session is None:
        import requests as session
    part, written = destPath + ".part", 0
    try:
        response = session.get(url, stream=True, timeout=timeout)
        if response.status_code != 200:
            raise UpdateError("Downloading the update failed with HTTP {}."
                              .format(response.status_code))
        with open(part, "wb") as handle:
            for chunk in response.iter_content(chunk_size=CHUNK_BYTES):
                if not chunk:
                    continue
                written += len(chunk)
                if written > MAX_ARCHIVE_BYTES:
                    raise UpdateError("The download exceeded the size limit.")
                handle.write(chunk)
    except UpdateError:
        _quietUnlink(part)
        raise
    except Exception as exc:
        _quietUnlink(part)
        raise UpdateError("Downloading the update failed: {}".format(exc)) from exc
    if declared and written != declared:
        _quietUnlink(part)
        raise UpdateError("The download stopped early; nothing has been changed.")
    os.replace(part, destPath)
    return written


def moduleRoots(moduleDir: str) -> Tuple[str, Optional[str]]:
    """``(qt-scripted-modules dir, extension root)``; root is None if not installed."""
    scripted = os.path.abspath(moduleDir)
    parts = scripted.replace("\\", "/").split("/")
    if len(parts) < 4 or parts[-1] != "qt-scripted-modules" or \
            not parts[-2].startswith("Slicer-"):
        return scripted, None
    return scripted, os.path.abspath(os.path.join(scripted, os.pardir, os.pardir, os.pardir))


def packagedSlicerVersion(moduleDir: str) -> Optional[str]:
    scripted, root = moduleRoots(moduleDir)
    if root is None:
        return None
    version = os.path.basename(os.path.dirname(scripted))[len("Slicer-"):]
    parts = version.split(".")
    return version if len(parts) == 2 and all(p.isdigit() for p in parts) else None


def isCheckout(moduleDir: str) -> bool:
    directory, previous = os.path.abspath(moduleDir), None
    while directory and directory != previous:
        if os.path.exists(os.path.join(directory, ".git")):
            return True
        previous, directory = directory, os.path.dirname(directory)
    return False


def canInstall(moduleDir: str) -> Tuple[bool, str]:
    if isCheckout(moduleDir):
        return False, ("JanusMRead is running from a source checkout; update it with "
                       "git and restart Slicer.")
    if moduleRoots(moduleDir)[1] is None:
        return False, ("JanusMRead is not installed as an extension, so it cannot update "
                       "itself. Unzip the release and add its JanusMRead/lib/Slicer-<x.y>/"
                       "qt-scripted-modules folder under Additional module paths.")
    if not os.access(moduleDir, os.W_OK):
        return False, "The module folder is not writable by this account."
    return True, ""


def inspectArchive(zipPath: str, slicerVersion: str) -> List[str]:
    try:
        with zipfile.ZipFile(zipPath) as archive:
            names = archive.namelist()
            bad = archive.testzip()
    except zipfile.BadZipFile:
        raise UpdateError("The downloaded update is not a valid archive.") from None
    if bad is not None:
        raise UpdateError("The downloaded update is corrupt ({}).".format(bad))
    for name in names:
        parts = name.replace("\\", "/").split("/")
        if name.startswith(("/", "\\")) or ".." in parts:
            raise UpdateError("The downloaded update contains an unsafe path ({})."
                              .format(name))
    members = rel.archive_members(names, slicerVersion)
    if not any(m.endswith(MODULE_FILE) for m in members):
        raise UpdateError("The archive does not contain a JanusMRead module for Slicer "
                          "{}. Nothing has been changed.".format(slicerVersion))
    return members


def installArchive(zipPath: str, moduleDir: str, slicerVersion: str,
                   backupRoot: Optional[str] = None) -> str:
    """Copy the archive's module over the installed one. Returns the backup path."""
    ok, reason = canInstall(moduleDir)
    if not ok:
        raise UpdateError(reason)
    members = inspectArchive(zipPath, slicerVersion)
    scripted, _root = moduleRoots(moduleDir)
    prefix = rel.scripted_prefix(slicerVersion)
    staging = tempfile.mkdtemp(prefix="janusm-read-update-")
    backup = backupRoot or os.path.join(os.path.dirname(scripted),
                                        "qt-scripted-modules.backup-" +
                                        time.strftime("%Y%m%d-%H%M%S"))
    try:
        with zipfile.ZipFile(zipPath) as archive:
            archive.extractall(staging, members=members)
        _copyOver(scripted, backup)
        try:
            _copyOver(os.path.join(staging, *prefix.rstrip("/").split("/")), scripted)
        except Exception as exc:
            _copyOver(backup, scripted)
            raise UpdateError("Installing the update failed and the previous version was "
                              "put back ({}).".format(exc)) from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return backup


def _copyOver(sourceDir, targetDir):
    for dirpath, _dirnames, filenames in os.walk(sourceDir):
        relative = os.path.relpath(dirpath, sourceDir)
        destination = targetDir if relative == "." else os.path.join(targetDir, relative)
        os.makedirs(destination, exist_ok=True)
        for filename in filenames:
            shutil.copy2(os.path.join(dirpath, filename), os.path.join(destination, filename))


def _quietUnlink(path):
    try:
        os.unlink(path)
    except OSError:
        pass
