"""Package SegQueue as an archive the Slicer Extension Manager will install.

    python slicer/build-extension.py

Produces ``dist/SegQueue-<version>-Slicer-<x.y>.zip``, which installs through
**Extensions Manager -> Install from file**. Plain Python, no CMake, no Slicer
needed to build it.

The layout is copied from the extensions Slicer itself ships, checked against a
real installation rather than inferred::

    SegQueue/
      lib/Slicer-5.8/qt-scripted-modules/SegQueue.py
      lib/Slicer-5.8/qt-scripted-modules/SegQueueLib/...
      lib/Slicer-5.8/qt-scripted-modules/segqueue/...     <- vendored
      share/Slicer-5.8/SegQueue.s4ext                     <- the descriptor

Two things about that are worth knowing.

**The shared package is vendored, not referenced.** In a checkout the module
finds ``segqueue`` at ``<repo>/src``; inside an installed extension there is no
repository, so a copy goes in beside ``SegQueueLib`` where Slicer's own module
path already finds it. The copy is made here, from ``src/segqueue``, so the two
cannot drift -- but it does mean **rebuilding after any change to
``src/segqueue``**, or annotators run an old wire protocol against a new server.

**The descriptor is what the Extension Manager reads.** Without a ``.s4ext`` in
``share/Slicer-<x.y>/`` the manager refuses the archive with "No extension
description found in archive", which is the error that sends people looking for
a corrupt download.
"""

import argparse
import os
import shutil
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXTENSION_NAME = "SegQueue"
CATEGORY = "Segmentation"
CONTRIBUTORS = "Christian Rogers"
HOMEPAGE = "https://github.com/christianGRogers/Asclepius"
DESCRIPTION = (
    "Distributed coronary artery segmentation. Fetches one assigned CT case at a "
    "time from a SegQueue server, creates the project's segments already named "
    "and coloured, validates the result before upload, and deletes the local copy "
    "on submit.<br><br>Built for annotating the coronary tree by branch (left "
    "main, LAD, left circumflex, RCA) with a team of annotators, with review, "
    "rework and automatic quality scoring handled server-side."
)

#: Slicer's default for a released version. Extensions are per minor version, so
#: a 5.8 package is not offered to 5.9 -- which is the point.
DEFAULT_SLICER_VERSION = "5.8"

#: What travels. Everything else in the repository is server-side or test code.
MODULE_DIR = os.path.join(REPO, "slicer", EXTENSION_NAME)
SHARED_PACKAGE = os.path.join(REPO, "src", "segqueue")

S4EXT_TEMPLATE = """#
# SegQueue extension description, read by Slicer's Extension Manager.
# First token of each non-comment line is the keyword; the rest is the value.
#

scm git
scmurl {homepage}
scmrevision {revision}

# No other extensions are required. The module talks to its server with
# `requests`, which Slicer already ships, so there is nothing to pip install.
depends NA

build_subdirectory .

homepage {homepage}
contributors {contributors}
category {category}
iconurl
status
description {description}
screenshoturls
enabled 1
"""


def moduleVersion():
    """Read ``__version__`` out of the module without importing it.

    Importing would pull in ``slicer``, ``qt`` and ``ctk``, none of which exist
    in the Python running this script.
    """
    path = os.path.join(MODULE_DIR, EXTENSION_NAME + ".py")
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("__version__"):
                return line.split("=", 1)[1].strip().strip("\"'")
    return "0.0.0"


def gitRevision():
    """Short commit hash, or ``unknown`` outside a checkout."""
    try:
        import subprocess

        return subprocess.check_output(
            ["git", "-C", REPO, "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def _ignore(_directory, names):
    """Keep build artefacts and editor debris out of what students install."""
    return {n for n in names
            if n == "__pycache__" or n.endswith((".pyc", ".pyo", ".orig", ".rej"))}


def build(outDir, slicerVersion=DEFAULT_SLICER_VERSION, keepStaging=False):
    version = moduleVersion()
    revision = gitRevision()

    staging = os.path.join(outDir, "_staging")
    shutil.rmtree(staging, ignore_errors=True)

    root = os.path.join(staging, EXTENSION_NAME)
    scripted = os.path.join(root, "lib", f"Slicer-{slicerVersion}", "qt-scripted-modules")
    share = os.path.join(root, "share", f"Slicer-{slicerVersion}")
    os.makedirs(scripted)
    os.makedirs(share)

    # The module and its private library.
    shutil.copy(os.path.join(MODULE_DIR, EXTENSION_NAME + ".py"), scripted)
    shutil.copytree(os.path.join(MODULE_DIR, EXTENSION_NAME + "Lib"),
                    os.path.join(scripted, EXTENSION_NAME + "Lib"), ignore=_ignore)

    # The shared wire-protocol package, vendored beside them.
    shutil.copytree(SHARED_PACKAGE, os.path.join(scripted, "segqueue"), ignore=_ignore)

    with open(os.path.join(share, EXTENSION_NAME + ".s4ext"), "w",
              encoding="utf-8", newline="\n") as handle:
        handle.write(S4EXT_TEMPLATE.format(
            homepage=HOMEPAGE, revision=revision, contributors=CONTRIBUTORS,
            category=CATEGORY, description=DESCRIPTION))

    archive = os.path.join(
        outDir, f"{EXTENSION_NAME}-{version}-Slicer-{slicerVersion}.zip")
    if os.path.exists(archive):
        os.unlink(archive)

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in sorted(filenames):
                full = os.path.join(dirpath, filename)
                # Paths inside the archive are relative to the staging root, so
                # the archive has exactly one top-level directory named after the
                # extension. The manager keys on that name.
                zf.write(full, os.path.relpath(full, staging).replace(os.sep, "/"))

    if not keepStaging:
        shutil.rmtree(staging, ignore_errors=True)
    return archive, version, revision


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="build-extension.py",
        description="Package SegQueue for the Slicer Extension Manager.")
    parser.add_argument("--out", default=os.path.join(REPO, "dist"),
                        help="Where to write the archive (default: dist/).")
    parser.add_argument("--slicer-version", default=DEFAULT_SLICER_VERSION,
                        help="Slicer minor version the package targets.")
    parser.add_argument("--keep-staging", action="store_true",
                        help="Leave the unzipped tree beside the archive.")
    args = parser.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    archive, version, revision = build(
        args.out, args.slicer_version, args.keep_staging)

    size = os.path.getsize(archive)
    print(f"{EXTENSION_NAME} {version} ({revision}) for Slicer {args.slicer_version}")
    print(f"  {archive}  [{size / 1024:.0f} KB]")
    print("\nInstall: Slicer -> Extensions Manager -> Install from file -> "
          "pick that zip -> restart.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
