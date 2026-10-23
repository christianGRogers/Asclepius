"""Package SegQueue14 as the SegQueue extension, for the Extension Manager and
for SegQueue's update button.

    python slicer/build-extension14.py

Produces ``dist/SegQueue-<version>-Slicer-<x.y>.zip``. From 0.14.0 SegQueue14 is
the SegQueue release line (project lead, 2026-10-17): the archive is named,
rooted and tagged (``segqueue-v<version>``) exactly as SegQueue's always were, so
the update button of SegQueue 0.13 and older offers it as the next version and
installs it over the old module::

    SegQueue/
      lib/Slicer-5.8/qt-scripted-modules/SegQueue14.py
      lib/Slicer-5.8/qt-scripted-modules/SegQueue.py        <- stub retiring the old module
      lib/Slicer-5.8/qt-scripted-modules/SegQueue14Lib/...  <- incl. updater.py
      lib/Slicer-5.8/qt-scripted-modules/segqueue14/...     <- vendored
      lib/Slicer-5.8/qt-scripted-modules/segqueue/...       <- vendored
      lib/Slicer-5.8/qt-scripted-modules/Resources/...
      share/Slicer-5.8/SegQueue.s4ext

The old updater copies files over and deletes none, so the stub
(``slicer/SegQueue14/legacy/SegQueue.py``) has to overwrite the 4-class
``SegQueue.py``; it sends anyone who opens "SegQueue" to SegQueue14. The old
``SegQueueLib`` is left on disk and nothing imports it.

**macOS** gets its own archive, ``SegQueue-<version>-Slicer-<x.y>-macOS.zip``
(#94). On a Mac, Slicer's *Install from file* does not copy the archive root: it
copies ``SegQueue/Slicer.app/Contents/Extensions-<revision>/SegQueue`` out of it
(``qSlicerExtensionsManagerModel::extractExtensionArchive``), where ``<revision>``
is the running Slicer's build number. An archive without that path fails to
install with "Failed to copy directory". So the macOS archive carries the same
tree once per released revision of that Slicer minor version
(``MACOS_REVISIONS``); whichever one the Mac's Slicer asks for is there. Once
installed, the layout on disk is the same as on Linux and Windows, so the update
button keeps using the cross-platform archive on every OS, and the updater never
picks the macOS one (its name does not match ``release.ASSET_PATTERN``).

The macOS archive only works on the revisions it lists, so it is a Slicer 5.8
route only. Any other Slicer, on any OS, uses the cross-platform archive
unzipped, with its ``SegQueue/lib/Slicer-<x.y>/qt-scripted-modules`` folder
added under *Additional module paths* (#97); that needs no revision.

Rebuild after any change to ``src/segqueue14``: the server refuses a module whose
protocol version is older than its own, with a message saying to update.
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: The extension (archive, top directory, descriptor) keeps the name SegQueue;
#: the module inside it is SegQueue14.
EXTENSION_NAME = "SegQueue"
MODULE_NAME = "SegQueue14"
MODULE_DIR = os.path.join(REPO, "slicer", MODULE_NAME)
LEGACY_STUB = os.path.join(MODULE_DIR, "legacy", "SegQueue.py")
SHARED_PACKAGES = (os.path.join(REPO, "src", "segqueue14"),
                   os.path.join(REPO, "src", "segqueue"))
DEFAULT_SLICER_VERSION = "5.8"

#: Build revisions of each released Slicer, by minor version, from Slicer's package
#: server (slicer-packages.kitware.com, ``/app/<id>/release``). A Mac's Slicer
#: looks for ``Slicer.app/Contents/Extensions-<its revision>`` inside the archive.
#: Add a revision here when Slicer releases a patch of a version annotators use;
#: the macOS install job in slicer-selftest.yml fails until it is listed.
MACOS_REVISIONS = {
    "5.8": ("33216", "33241"),                              # 5.8.0, 5.8.1
    "5.10": ("34045",),                                     # 5.10.0
    "5.12": ("34621", "34624", "34625", "34627", "34645"),  # 5.12.0 - 5.12.4
}
HOMEPAGE = "https://github.com/christianGRogers/Asclepius"

DESCRIPTION = (
    "4-class coronary annotation for the SegQueue platform (LM, LAD, LCx, RCA; side "
    "branches take their parent's class). Fetches one assigned case with a vessel "
    "seed to divide into the four classes, checks LAD, LCx and RCA are present, and "
    "uploads the result. The module is SegQueue14, shown as SegQueue."
)

S4EXT_TEMPLATE = """#
# SegQueue extension description (the SegQueue14 module), read by Slicer's Extension Manager.
#
scm git
scmurl {homepage}
scmrevision {revision}
depends NA
build_subdirectory .
homepage {homepage}
contributors Christian Rogers
category Segmentation
iconurl
status
description {description}
screenshoturls
enabled 1
"""


def moduleVersion():
    with open(os.path.join(MODULE_DIR, MODULE_NAME + ".py"), encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("__version__"):
                return line.split("=", 1)[1].strip().strip("\"'")
    return "0.0.0"


def gitRevision():
    try:
        return subprocess.check_output(["git", "-C", REPO, "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def _ignore(_directory, names):
    return {n for n in names
            if n == "__pycache__" or n.endswith((".pyc", ".pyo", ".orig", ".rej"))}


def _stage(root, slicerVersion, revision):
    """Lay the extension out under ``root`` (the directory named SegQueue)."""
    scripted = os.path.join(root, "lib", f"Slicer-{slicerVersion}", "qt-scripted-modules")
    share = os.path.join(root, "share", f"Slicer-{slicerVersion}")
    os.makedirs(scripted)
    os.makedirs(share)

    shutil.copy(os.path.join(MODULE_DIR, MODULE_NAME + ".py"), scripted)
    shutil.copy(LEGACY_STUB, os.path.join(scripted, "SegQueue.py"))
    shutil.copytree(os.path.join(MODULE_DIR, MODULE_NAME + "Lib"),
                    os.path.join(scripted, MODULE_NAME + "Lib"), ignore=_ignore)
    for extra in ("README.md", "Resources"):
        path = os.path.join(MODULE_DIR, extra)
        if os.path.isdir(path):
            shutil.copytree(path, os.path.join(scripted, extra), ignore=_ignore)
        elif os.path.isfile(path):
            shutil.copy(path, scripted)
    for package in SHARED_PACKAGES:
        shutil.copytree(package, os.path.join(scripted, os.path.basename(package)),
                        ignore=_ignore)

    with open(os.path.join(share, EXTENSION_NAME + ".s4ext"), "w", encoding="utf-8",
              newline="\n") as handle:
        handle.write(S4EXT_TEMPLATE.format(homepage=HOMEPAGE, revision=revision,
                                           description=DESCRIPTION))


def _zip(staging, archive):
    if os.path.exists(archive):
        os.unlink(archive)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(staging):
            dirnames.sort()
            for filename in sorted(filenames):
                full = os.path.join(dirpath, filename)
                zf.write(full, os.path.relpath(full, staging).replace(os.sep, "/"))


def macosBundlePrefix(slicerRevision):
    """Where a Mac's Slicer looks for the extension inside the archive."""
    return f"{EXTENSION_NAME}/Slicer.app/Contents/Extensions-{slicerRevision}/{EXTENSION_NAME}/"


def build(outDir, slicerVersion=DEFAULT_SLICER_VERSION, keepStaging=False):
    """The cross-platform archive (Linux, Windows, and every update button)."""
    version, revision = moduleVersion(), gitRevision()
    staging = os.path.join(outDir, "_staging14")
    shutil.rmtree(staging, ignore_errors=True)
    _stage(os.path.join(staging, EXTENSION_NAME), slicerVersion, revision)

    archive = os.path.join(outDir, f"{EXTENSION_NAME}-{version}-Slicer-{slicerVersion}.zip")
    _zip(staging, archive)
    if not keepStaging:
        shutil.rmtree(staging, ignore_errors=True)
    return archive, version, revision


def buildMacos(outDir, slicerVersion=DEFAULT_SLICER_VERSION, revisions=None):
    """The macOS archive: the same tree under each Slicer revision's bundle path.

    Installed from file on a Mac, Slicer copies out only the subtree for its own
    revision, which leaves exactly what the cross-platform archive leaves on
    Linux. Raises ``SystemExit`` for a Slicer version with no known revisions.
    """
    revisions = tuple(revisions or MACOS_REVISIONS.get(slicerVersion, ()))
    if not revisions:
        raise SystemExit(f"no known Slicer {slicerVersion} revisions for the macOS "
                         "archive; add them to MACOS_REVISIONS")
    version, revision = moduleVersion(), gitRevision()
    staging = os.path.join(outDir, "_staging14-macos")
    shutil.rmtree(staging, ignore_errors=True)
    for slicerRevision in revisions:
        _stage(os.path.join(staging, *macosBundlePrefix(slicerRevision).rstrip("/").split("/")),
               slicerVersion, revision)

    archive = os.path.join(
        outDir, f"{EXTENSION_NAME}-{version}-Slicer-{slicerVersion}-macOS.zip")
    _zip(staging, archive)
    shutil.rmtree(staging, ignore_errors=True)
    return archive, version, revision


def main(argv=None):
    parser = argparse.ArgumentParser(prog="build-extension14.py",
                                     description="Package SegQueue14 as the SegQueue extension.")
    parser.add_argument("--out", default=os.path.join(REPO, "dist"))
    parser.add_argument("--slicer-version", default=DEFAULT_SLICER_VERSION)
    parser.add_argument("--keep-staging", action="store_true")
    parser.add_argument("--macos-revision", action="append",
                        help="Slicer revision for the macOS archive (repeatable); "
                             "default: MACOS_REVISIONS for --slicer-version")
    parser.add_argument("--print-version", action="store_true")
    args = parser.parse_args(argv)
    if args.print_version:
        print(moduleVersion())
        return 0
    os.makedirs(args.out, exist_ok=True)
    archive, version, revision = build(args.out, args.slicer_version, args.keep_staging)
    macos, _, _ = buildMacos(args.out, args.slicer_version, args.macos_revision)
    print(f"{MODULE_NAME} {version} ({revision}) for Slicer {args.slicer_version}")
    print(f"  {archive}  [{os.path.getsize(archive) / 1024:.0f} KB]")
    print(f"  {macos}  [{os.path.getsize(macos) / 1024:.0f} KB]  (macOS)")
    print("\nSegQueue 0.13 offers this as an update. First install on any Slicer: "
          "unzip the zip and add SegQueue/lib/Slicer-{0}/qt-scripted-modules under "
          "Application Settings -> Modules -> Additional module paths -> restart (#97). "
          "On Slicer {0} also: Extensions Manager -> Install from file -> pick the zip "
          "(the -macOS one on a Mac) -> restart. The module is under "
          "Segmentation -> SegQueue.".format(args.slicer_version))
    return 0


if __name__ == "__main__":
    sys.exit(main())
