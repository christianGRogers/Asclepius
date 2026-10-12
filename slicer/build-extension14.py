"""Package SegQueue14 as an archive the Slicer Extension Manager will install.

    python slicer/build-extension14.py

Produces ``dist/SegQueue14-<version>-Slicer-<x.y>.zip``, installed through
**Extensions Manager -> Install from file**, *beside* SegQueue: the archive's top
directory, the module, its library and the descriptor are all named SegQueue14,
so neither extension overwrites the other. Same layout as
``build-extension.py`` builds for the live module::

    SegQueue14/
      lib/Slicer-5.8/qt-scripted-modules/SegQueue14.py
      lib/Slicer-5.8/qt-scripted-modules/SegQueue14Lib/...
      lib/Slicer-5.8/qt-scripted-modules/segqueue14/...   <- vendored
      lib/Slicer-5.8/qt-scripted-modules/segqueue/...     <- vendored
      lib/Slicer-5.8/qt-scripted-modules/Resources/...
      share/Slicer-5.8/SegQueue14.s4ext

Two shared packages are vendored. ``segqueue14`` exists only here. ``segqueue``
is the live package, of which SegQueue14 uses only names every released copy has
-- in a Slicer with both extensions installed, whichever ``segqueue`` is first on
``sys.path`` serves both modules, and that must not matter.

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

EXTENSION_NAME = "SegQueue14"
MODULE_DIR = os.path.join(REPO, "slicer", EXTENSION_NAME)
SHARED_PACKAGES = (os.path.join(REPO, "src", "segqueue14"),
                   os.path.join(REPO, "src", "segqueue"))
DEFAULT_SLICER_VERSION = "5.8"
HOMEPAGE = "https://github.com/christianGRogers/Asclepius"

DESCRIPTION = (
    "14-class coronary prelabel correction for the SegQueue platform. Fetches one "
    "assigned case with the 14-class model prediction loaded into the project "
    "segments (LM, LAD, LCx, D1, D2, OM1, OM2, IM, RCA, R-PDA, R-PLA, L-PDA, L-PLA, "
    "Other), checks LAD, LCx and RCA are present, and uploads the correction. "
    "Installs beside SegQueue."
)

S4EXT_TEMPLATE = """#
# SegQueue14 extension description, read by Slicer's Extension Manager.
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
    with open(os.path.join(MODULE_DIR, EXTENSION_NAME + ".py"), encoding="utf-8") as handle:
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

    shutil.copy(os.path.join(MODULE_DIR, EXTENSION_NAME + ".py"), scripted)
    shutil.copytree(os.path.join(MODULE_DIR, EXTENSION_NAME + "Lib"),
                    os.path.join(scripted, EXTENSION_NAME + "Lib"), ignore=_ignore)
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
                                     description="Package SegQueue14 for Slicer.")
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
    print(f"{EXTENSION_NAME} {version} ({revision}) for Slicer {args.slicer_version}")
    print(f"  {archive}  [{os.path.getsize(archive) / 1024:.0f} KB]")
    print("\nInstall beside SegQueue: Slicer -> Extensions Manager -> Install from file "
          "-> pick that zip -> restart. The module is under Segmentation -> SegQueue14.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
