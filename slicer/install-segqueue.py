"""Install SegQueue into any 3D Slicer, from Slicer's Python console (#97).

Open Slicer, then **View -> Python Console**, paste this one line and press Enter::

    import requests; exec(requests.get("https://raw.githubusercontent.com/christianGRogers/Asclepius/main/slicer/install-segqueue.py", timeout=60).text)

Why this exists: the Extensions Manager's *Install from file* is tied to the
Slicer it runs in. On macOS it copies ``Slicer.app/Contents/Extensions-<revision>``
out of the zip, so a zip only installs on the revisions written into it (#94,
#97), and on every OS it loads ``lib/Slicer-<running version>``, which a zip
built for 5.8 does not have. SegQueue is plain Python, so none of that is
needed: this script downloads the newest ``segqueue-v`` release, unpacks the
module into a folder you own (``~/SegQueue``), adds that folder to *Edit ->
Application Settings -> Modules -> Additional module paths*, and restarts
Slicer. It works the same on every Slicer version and revision, on macOS, Linux
and Windows.

The folder keeps the extension's layout (``~/SegQueue/lib/Slicer-5.8/
qt-scripted-modules``), so the module's own *Update and restart* button
recognises it and keeps it current.

Running it again is safe: it installs the newest release over the old files
(deleting none) and re-registers the folder. Do that after installing a new
Slicer, whose settings start empty.

Reads only public GitHub release data; sends nothing, needs no account. Slicer
5.8 bundles Python 3.9, so this file is 3.9-clean. Stdlib plus ``requests``
(bundled with Slicer).
"""  # noqa: E501  (the one-liner above is pasted as is)

import os
import re
import shutil
import tempfile
import zipfile

GITHUB_REPO = "christianGRogers/Asclepius"
RELEASES_URL = "https://api.github.com/repos/{}/releases".format(GITHUB_REPO)
TAG_PREFIX = "segqueue-v"
#: The same pattern as ``segqueue.release.ASSET_PATTERN``; the macOS zip does
#: not match it and is never picked.
ASSET_PATTERN = re.compile(
    r"^SegQueue-(?P<version>[0-9][0-9A-Za-z.\-+]*)-Slicer-(?P<slicer>[0-9]+\.[0-9]+)\.zip$")
EXTENSION = "SegQueue"
MODULE = "SegQueue14"
#: Where the module goes. The folder is named after the extension, which is what
#: the updater (``SegQueue14Lib/updater.py``) expects of an install.
DEFAULT_BASE = os.path.join(os.path.expanduser("~"), EXTENSION)
SETTING = "Modules/AdditionalPaths"
EXTRA_EFFECTS = "SegmentEditorExtraEffects"
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024


class InstallError(RuntimeError):
    """Something stopped the install; the text says what to do."""


def _version_key(text):
    numbers = re.match(r"[0-9]+(?:\.[0-9]+)*", text or "")
    return tuple(int(n) for n in numbers.group(0).split(".")) if numbers else ()


def pick_asset(releases, slicer_minor=None):
    """``(tag, asset)`` of the newest SegQueue release archive, or ``None``.

    Prefers an archive built for ``slicer_minor`` when the release has one, else
    the newest Slicer version it has: the module is plain Python, and the
    archive's Slicer version only names the folder it lives in.
    """
    best = None
    for release in releases or []:
        if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
            continue
        tag = str(release.get("tag_name") or "")
        if not tag.startswith(TAG_PREFIX) or not _version_key(tag[len(TAG_PREFIX):]):
            continue
        assets = []
        for asset in release.get("assets") or []:
            match = ASSET_PATTERN.match(str(asset.get("name") or ""))
            if match and asset.get("browser_download_url"):
                slicer = match.group("slicer")
                assets.append(((slicer == slicer_minor, _version_key(slicer)), asset))
        if not assets:
            continue
        assets.sort(key=lambda pair: pair[0])
        key = _version_key(tag[len(TAG_PREFIX):])
        if best is None or key > best[0]:
            best = (key, tag, assets[-1][1])
    return None if best is None else (best[1], best[2])


def module_prefix(names):
    """``SegQueue/lib/Slicer-X.Y/qt-scripted-modules/`` of a release archive.

    Raises ``InstallError`` unless the archive holds exactly one SegQueue14
    module and nothing that could land outside the target folder.
    """
    for name in names:
        parts = name.replace("\\", "/").split("/")
        if name.startswith(("/", "\\")) or ".." in parts or ":" in parts[0]:
            raise InstallError("The archive contains an unsafe path ({}).".format(name))
        if parts[0] != EXTENSION:
            raise InstallError("This is not a SegQueue archive ({}).".format(name))
    found = sorted({name[:-len(MODULE + ".py")] for name in names
                    if re.match(r"^SegQueue/lib/Slicer-[0-9]+\.[0-9]+/qt-scripted-modules/"
                                + MODULE + r"\.py$", name)})
    if len(found) != 1:
        raise InstallError("The archive does not contain one {} module.".format(MODULE))
    return found[0]


def unpack(zip_path, base):
    """Unpack the archive into ``base`` (without its top ``SegQueue/``).

    Returns the module folder to register. Copies over what is there and deletes
    nothing, like the module's own updater.
    """
    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = archive.namelist()
            if archive.testzip() is not None:
                raise InstallError("The downloaded archive is corrupt; run this again.")
            prefix = module_prefix(names)
            staging = tempfile.mkdtemp(prefix="segqueue-install-")
            try:
                archive.extractall(staging)
                _copy_over(os.path.join(staging, EXTENSION), base)
            finally:
                shutil.rmtree(staging, ignore_errors=True)
    except zipfile.BadZipFile:
        raise InstallError("The downloaded file is not a zip archive; run this again.") from None
    relative = prefix[len(EXTENSION) + 1:].rstrip("/")
    return os.path.join(base, *relative.split("/"))


def _copy_over(source, target):
    for dirpath, _dirnames, filenames in os.walk(source):
        relative = os.path.relpath(dirpath, source)
        destination = target if relative == "." else os.path.join(target, relative)
        if not os.path.isdir(destination):
            os.makedirs(destination)
        for filename in filenames:
            shutil.copy2(os.path.join(dirpath, filename), os.path.join(destination, filename))


def with_path(paths, folder):
    """``paths`` (a settings value) as a list of strings, with ``folder`` added once."""
    if paths is None:
        paths = []
    elif isinstance(paths, str):
        paths = [paths] if paths else []
    paths = [str(p) for p in paths if str(p)]
    wanted = os.path.normcase(os.path.abspath(folder))
    if not any(os.path.normcase(os.path.abspath(p)) == wanted for p in paths):
        paths.append(folder)
    return paths


def download_newest(slicer_minor, dest_dir):
    """Download the newest release archive. Returns ``(path, tag)``."""
    import requests

    reply = requests.get(RELEASES_URL, params={"per_page": 30},
                         headers={"Accept": "application/vnd.github+json"}, timeout=(10, 30))
    if reply.status_code == 403:
        raise InstallError("GitHub is rate-limiting this network; try again within the hour.")
    if reply.status_code != 200:
        raise InstallError("GitHub returned HTTP {} for the release list.".format(
            reply.status_code))
    picked = pick_asset(reply.json(), slicer_minor)
    if picked is None:
        raise InstallError("No SegQueue release with an archive was found on GitHub.")
    tag, asset = picked
    if int(asset.get("size") or 0) > MAX_ARCHIVE_BYTES:
        raise InstallError("The published archive is implausibly large; not downloading it.")
    path = os.path.join(dest_dir, str(asset["name"]))
    with requests.get(asset["browser_download_url"], stream=True, timeout=(10, 120)) as data:
        if data.status_code != 200:
            raise InstallError("Downloading {} failed with HTTP {}.".format(
                asset["name"], data.status_code))
        written = 0
        with open(path, "wb") as handle:
            for chunk in data.iter_content(chunk_size=256 * 1024):
                written += len(chunk)
                if written > MAX_ARCHIVE_BYTES:
                    raise InstallError("The download exceeded the size limit.")
                handle.write(chunk)
    return path, tag


def install(zip_path=None, base=None, restart=True, extra_effects=True):
    """Install SegQueue into this Slicer. Returns the registered module folder."""
    import slicer

    base = os.path.abspath(base or DEFAULT_BASE)
    slicer_minor = "{}.{}".format(slicer.app.majorVersion, slicer.app.minorVersion)
    model = slicer.app.extensionsManagerModel()
    if model.isExtensionInstalled(EXTENSION):
        raise InstallError(
            "SegQueue is already installed through the Extensions Manager in this "
            "Slicer, and it keeps itself up to date there. If you want this install "
            "instead, uninstall SegQueue in the Extensions Manager, restart Slicer "
            "and run this again.")
    if os.path.exists(base) and not os.access(base, os.W_OK):
        raise InstallError("{} is not writable by this account.".format(base))

    downloads = tempfile.mkdtemp(prefix="segqueue-download-")
    try:
        tag = None
        if zip_path is None:
            print("Downloading the newest SegQueue release...")
            zip_path, tag = download_newest(slicer_minor, downloads)
        folder = unpack(zip_path, base)
    finally:
        shutil.rmtree(downloads, ignore_errors=True)

    settings = slicer.app.revisionUserSettings()
    settings.setValue(SETTING, with_path(settings.value(SETTING), folder))
    settings.sync()
    print("SegQueue {}installed in {}".format(
        "" if tag is None else tag[len(TAG_PREFIX):] + " ", folder))
    print("Registered under Application Settings -> Modules -> Additional module paths.")

    if extra_effects and not model.isExtensionInstalled(EXTRA_EFFECTS):
        # Draw tube comes from this extension. It is in every Slicer's catalog,
        # so the Extensions Manager installs it for whatever revision this is.
        try:
            print("Installing {} (Draw tube) from the Extensions catalog...".format(
                EXTRA_EFFECTS))
            model.updateExtensionsMetadataFromServer(True, True)
            if not model.downloadAndInstallExtensionByName(EXTRA_EFFECTS, True, True):
                raise RuntimeError("not installed")
        except Exception as exc:
            print("Could not install {} ({}). Install it from the Extensions "
                  "Manager.".format(EXTRA_EFFECTS, exc))

    if restart:
        if slicer.util.confirmOkCancelDisplay(
                "SegQueue is installed. Slicer has to restart to load it; after the "
                "restart it is under Segmentation -> SegQueue.\n\nRestart now?",
                windowTitle="SegQueue"):
            slicer.util.restart()
    return folder


if __name__ == "__main__":
    try:
        install()
    except InstallError as _error:
        print("SegQueue was not installed: {}".format(_error))
        try:
            import slicer

            slicer.util.errorDisplay("SegQueue was not installed:\n\n{}".format(_error))
        except Exception:
            pass
