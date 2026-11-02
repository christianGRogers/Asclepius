"""Package the JanusMRead module (the Janus-M border reader, #156) as its own extension.

    python slicer/build-extension-janusm.py

Produces ``dist/JanusMRead-<version>-Slicer-<x.y>.zip``, rooted at ``JanusMRead/``::

    JanusMRead/
      lib/Slicer-5.8/qt-scripted-modules/JanusMRead.py
      lib/Slicer-5.8/qt-scripted-modules/JanusMReadLib/...
      lib/Slicer-5.8/qt-scripted-modules/janusm_reads/   <- the client half only
      share/Slicer-5.8/JanusMRead.s4ext

Separate from SegQueue14 in every way an updater or an installer looks: another
archive name, root and descriptor, and its release tag would be
``janusm-read-v<version>`` (never ``segqueue-v*``), from JanusMRead's own
``__version__``. Bumping SegQueue14's version never ships it, and
``build-extension14.py`` never includes it.

Of ``src/janusm_reads`` only what a reader's client needs is vendored
(:data:`VENDORED`): the labels, the wire protocol and the client. The read set,
hold-out guard, checker, seeds and phantom stay on the server and in the
repository.

Building is fine anywhere (CI uploads the zip as a workflow artifact). Publishing
a release is the project lead's decision; this script never does.
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTENSION_NAME = "JanusMRead"
MODULE_NAME = "JanusMRead"
MODULE_DIR = os.path.join(REPO, "slicer", MODULE_NAME)
SHARED = os.path.join(REPO, "src", "janusm_reads")
#: The client half of janusm_reads; nothing that names a case's read set.
VENDORED = ("__init__.py", "labels.py", "protocol.py", "client.py")
DEFAULT_SLICER_VERSION = "5.8"
TAG_PREFIX = "janusm-read-v"
HOMEPAGE = "https://github.com/christianGRogers/Asclepius"
DESCRIPTION = (
    "Janus-M border reads on rest CCTA (LV myocardium, LV blood pool, RV blood pool, LA "
    "blood pool), against the Janus-M read queue: takes a case, loads the CT and its "
    "seed, helps draw each border at its half-maximum, and submits the read.")

S4EXT_TEMPLATE = """#
# JanusMRead extension description, read by Slicer's Extension Manager.
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
    scripted = os.path.join(root, "lib", f"Slicer-{slicerVersion}", "qt-scripted-modules")
    share = os.path.join(root, "share", f"Slicer-{slicerVersion}")
    os.makedirs(scripted)
    os.makedirs(share)
    shutil.copy(os.path.join(MODULE_DIR, MODULE_NAME + ".py"), scripted)
    shutil.copytree(os.path.join(MODULE_DIR, MODULE_NAME + "Lib"),
                    os.path.join(scripted, MODULE_NAME + "Lib"), ignore=_ignore)
    for extra in ("README.md", "Resources"):
        path = os.path.join(MODULE_DIR, extra)
        if os.path.isdir(path):
            shutil.copytree(path, os.path.join(scripted, extra), ignore=_ignore)
        elif os.path.isfile(path):
            shutil.copy(path, scripted)
    package = os.path.join(scripted, "janusm_reads")
    os.makedirs(package)
    for name in VENDORED:
        shutil.copy(os.path.join(SHARED, name), package)
    with open(os.path.join(share, EXTENSION_NAME + ".s4ext"), "w", encoding="utf-8",
              newline="\n") as handle:
        handle.write(S4EXT_TEMPLATE.format(homepage=HOMEPAGE, revision=revision,
                                           description=DESCRIPTION))


def build(outDir, slicerVersion=DEFAULT_SLICER_VERSION):
    """Build the archive. Returns ``(archive path, version, git revision)``."""
    version, revision = moduleVersion(), gitRevision()
    staging = os.path.join(outDir, "_staging-janusm")
    shutil.rmtree(staging, ignore_errors=True)
    _stage(os.path.join(staging, EXTENSION_NAME), slicerVersion, revision)
    archive = os.path.join(outDir, f"{EXTENSION_NAME}-{version}-Slicer-{slicerVersion}.zip")
    if os.path.exists(archive):
        os.unlink(archive)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(staging):
            dirnames.sort()
            for filename in sorted(filenames):
                full = os.path.join(dirpath, filename)
                zf.write(full, os.path.relpath(full, staging).replace(os.sep, "/"))
    shutil.rmtree(staging, ignore_errors=True)
    return archive, version, revision


def main(argv=None):
    parser = argparse.ArgumentParser(prog="build-extension-janusm.py",
                                     description="Package the JanusMRead Slicer module.")
    parser.add_argument("--out", default=os.path.join(REPO, "dist"))
    parser.add_argument("--slicer-version", default=DEFAULT_SLICER_VERSION)
    parser.add_argument("--print-version", action="store_true")
    args = parser.parse_args(argv)
    if args.print_version:
        print(moduleVersion())
        return 0
    os.makedirs(args.out, exist_ok=True)
    archive, version, revision = build(args.out, args.slicer_version)
    print(f"{MODULE_NAME} {version} ({revision}) for Slicer {args.slicer_version}")
    print(f"  {archive}  [{os.path.getsize(archive) / 1024:.0f} KB]")
    print(f"  release tag, if the lead publishes it: {TAG_PREFIX}{version}")
    print("Install: unzip, add JanusMRead/lib/Slicer-{}/qt-scripted-modules under "
          "Application Settings -> Modules -> Additional module paths, restart. The module "
          "is under Segmentation -> Janus-M Read.".format(args.slicer_version))
    return 0


if __name__ == "__main__":
    sys.exit(main())
