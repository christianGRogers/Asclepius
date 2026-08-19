"""Register SegQueue with Slicer, from inside Slicer.

Run this in Slicer's Python Console (View -> Python Console, or Ctrl+3):

    exec(open(r"<where you unzipped>/slicer/install-segqueue.py").read())

It adds the module directory to Slicer's *Additional module paths* and offers to
restart. That is all "installing" a scripted module means -- there is nothing to
compile and nothing to download.

**Why not the Extension Manager?** Its "Install from file" expects a CMake-built
extension package with a ``.s4ext`` descriptor inside, and refuses anything else
with *"No extension description found in archive"*. SegQueue is a scripted
module, like ``SegmentatorTrainMonitor`` next door: a directory of Python that
Slicer loads from a path. The upside is that a student needs no build tools and
no admin rights, and an update is a re-copy rather than a reinstall.

Doing it by hand is three clicks if you prefer:
Edit -> Application Settings -> Modules -> drag ``slicer/SegQueue`` into
*Additional module paths* -> restart.
"""

import os

import slicer

#: Where Slicer keeps extra scripted-module directories. It lives in the
#: *revision* settings rather than the ordinary ones, so a path added for
#: Slicer 5.8 does not silently follow you into an incompatible 5.9.
SETTINGS_KEY = "Modules/AdditionalPaths"


def modulePath():
    """The SegQueue module directory, resolved from this script's location.

    This file sits beside the module rather than inside it on purpose: Slicer
    scans every ``.py`` in a module path expecting a module class, and a stray
    helper in there would log a complaint on every startup for the rest of the
    project.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "SegQueue")


def currentPaths(settings):
    """Existing additional paths, as a list.

    QSettings hands back a bare string when exactly one path is stored and a
    list when there are several. Appending to the string form quietly produces a
    path spelled one character at a time.
    """
    value = settings.value(SETTINGS_KEY)
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def install(path=None, restart=True):
    """Add the module path if it is not already there. Returns True if changed."""
    path = os.path.normpath(path or modulePath())

    if not os.path.isfile(os.path.join(path, "SegQueue.py")):
        slicer.util.errorDisplay(
            "SegQueue.py is not in\n  {}\n\nUnzip the whole bundle and run this "
            "script from where you unzipped it, keeping slicer/ and src/ side by "
            "side.".format(path))
        return False

    # The module reaches two directories up for its shared code. Checking here
    # turns a puzzling ImportError at first launch into a sentence.
    src = os.path.join(os.path.dirname(os.path.dirname(path)), "src", "segqueue")
    if not os.path.isdir(src):
        slicer.util.errorDisplay(
            "The shared 'segqueue' package is missing. Expected it at\n  {}\n\n"
            "Keep the slicer/ and src/ folders together exactly as unzipped -- "
            "the module looks for src/ two directories above itself.".format(src))
        return False

    settings = slicer.app.revisionUserSettings()
    paths = currentPaths(settings)
    if any(os.path.normpath(p) == path for p in paths):
        slicer.util.infoDisplay(
            "SegQueue is already registered at\n  {}\n\nOpen it under "
            "Modules -> Segmentation -> SegQueue.".format(path))
        return False

    paths.append(path)
    settings.setValue(SETTINGS_KEY, paths)
    print("SegQueue: added module path", path)

    if restart and slicer.util.confirmYesNoDisplay(
            "SegQueue registered at\n  {}\n\nSlicer needs to restart to pick it "
            "up. Restart now?".format(path)):
        slicer.util.restart()
    return True


def uninstall(path=None):
    """Remove the module path. Leaves the files alone."""
    path = os.path.normpath(path or modulePath())
    settings = slicer.app.revisionUserSettings()
    keep = [p for p in currentPaths(settings) if os.path.normpath(p) != path]
    settings.setValue(SETTINGS_KEY, keep)
    print("SegQueue: removed module path", path)
    return True


# Run on load, not under a __main__ guard: this is executed with
# exec(open(...).read()), where __name__ is never "__main__". Someone who pasted
# one line expects something to happen.
install()
