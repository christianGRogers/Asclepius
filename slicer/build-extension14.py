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
HOMEPAGE = "https://github.com/christianGRogers/Asclepius"

DESCRIPTION = (
    "14-class coronary prelabel correction for the SegQueue platform. Fetches one "
    "assigned case with the 14-class model prediction loaded into the project "
    "segments (LM, LAD, LCx, D1, D2, OM1, OM2, IM, RCA, R-PDA, R-PLA, L-PDA, L-PLA, "
    "Other), checks LAD, LCx and RCA are present, and uploads the correction. "
    "Replaces the 4-class SegQueue module from version 0.14.0."
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


def build(outDir, slicerVersion=DEFAULT_SLICER_VERSION, keepStaging=False):
    version, revision = moduleVersion(), gitRevision()
    staging = os.path.join(outDir, "_staging14")
    shutil.rmtree(staging, ignore_errors=True)
    root = os.path.join(staging, EXTENSION_NAME)
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

    archive = os.path.join(outDir, f"{EXTENSION_NAME}-{version}-Slicer-{slicerVersion}.zip")
    if os.path.exists(archive):
        os.unlink(archive)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in sorted(filenames):
                full = os.path.join(dirpath, filename)
                zf.write(full, os.path.relpath(full, staging).replace(os.sep, "/"))
    if not keepStaging:
        shutil.rmtree(staging, ignore_errors=True)
    return archive, version, revision


def main(argv=None):
    parser = argparse.ArgumentParser(prog="build-extension14.py",
                                     description="Package SegQueue14 as the SegQueue extension.")
    parser.add_argument("--out", default=os.path.join(REPO, "dist"))
    parser.add_argument("--slicer-version", default=DEFAULT_SLICER_VERSION)
    parser.add_argument("--keep-staging", action="store_true")
    parser.add_argument("--print-version", action="store_true")
    args = parser.parse_args(argv)
    if args.print_version:
        print(moduleVersion())
        return 0
    os.makedirs(args.out, exist_ok=True)
    archive, version, revision = build(args.out, args.slicer_version, args.keep_staging)
    print(f"{MODULE_NAME} {version} ({revision}) for Slicer {args.slicer_version}")
    print(f"  {archive}  [{os.path.getsize(archive) / 1024:.0f} KB]")
    print("\nSegQueue 0.13 offers this as an update. First install: Slicer -> Extensions "
          "Manager -> Install from file -> pick that zip -> restart. The module is under "
          "Segmentation -> SegQueue14.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
