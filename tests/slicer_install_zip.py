"""Install the release zip the way an annotator does, inside a real 3D Slicer.

    Slicer --no-splash --no-main-window --python-script tests/slicer_install_zip.py

Run twice. ``SEGQUEUE_INSTALL_PHASE=install`` hands ``$SEGQUEUE_ZIP`` to the
Extensions Manager, which is what *Install from file* does. ``load`` (the next
Slicer start, since the Extensions Manager loads what it installed only then)
checks that the module is there, imports, builds its panel, and that its own
update button would accept the install location.

The self-tests (``slicer_selftest*.py``) load the module from the checkout, so
they never exercise the archive. This one exists because on macOS the
Extensions Manager does not copy the archive root: it copies
``<archive>/Slicer.app/Contents/Extensions-<revision>/<extension>``, and a zip
without that path cannot be installed on a Mac at all (#94).

The report goes to ``$SEGQUEUE_SELFTEST_OUT`` (default ``./install.txt``); its
last line is ``RESULT PASS`` or ``RESULT FAIL``.
"""

import os
import traceback

OUT = os.environ.get("SEGQUEUE_SELFTEST_OUT", os.path.abspath("install.txt"))
PHASE = os.environ.get("SEGQUEUE_INSTALL_PHASE", "install")
EXTENSION = "SegQueue"

log = []
checks = []


def say(*parts):
    log.append(" ".join(str(p) for p in parts))


def check(name, passed, detail=""):
    checks.append(bool(passed))
    say("PASS" if passed else "FAIL", name, detail)


def prop(obj, name):
    """A Qt property: PythonQt exposes most as values, some as getters."""
    value = getattr(obj, name)
    return value() if callable(value) else value


def scriptedDir(slicer, model):
    version = "{}.{}".format(slicer.app.majorVersion, slicer.app.minorVersion)
    return os.path.join(prop(model, "extensionsInstallPath"), EXTENSION, "lib",
                        "Slicer-" + version, "qt-scripted-modules")


def install(slicer, model):
    archive = os.environ["SEGQUEUE_ZIP"]
    say("archive", archive)
    # (archiveFile, installDependencies, waitForCompletion). No dependency
    # resolution: Install from file does not do it either, and the runner has
    # already installed SegmentEditorExtraEffects if it is wanted.
    ok = model.installExtension(archive, False, True)
    check("the Extensions Manager accepted the archive", ok)
    check("the extension is registered as installed", model.isExtensionInstalled(EXTENSION))
    target = os.path.join(scriptedDir(slicer, model), "SegQueue14.py")
    check("SegQueue14.py is where Slicer will look for it", os.path.isfile(target), target)


def load(slicer, model):
    check("the extension is still installed", model.isExtensionInstalled(EXTENSION))
    check("Slicer loaded the SegQueue14 module", hasattr(slicer.modules, "segqueue14"))

    import SegQueue14 as module  # on sys.path because Slicer loaded it

    where = os.path.dirname(os.path.abspath(module.__file__))
    expected = os.path.abspath(scriptedDir(slicer, model))
    check("from the installed extension, not a checkout",
          os.path.normcase(where) == os.path.normcase(expected), where)
    check("its shared packages imported", module._IMPORT_ERROR is None, module._IMPORT_ERROR)

    from SegQueue14Lib import updater

    _scripted, root = updater.moduleRoots(where)
    check("the updater recognises the install layout",
          root is not None and os.path.basename(root) == EXTENSION, root)
    ok, reason = updater.canInstall(where)
    check("the update button could install over it", ok, reason)

    widget = slicer.modules.segqueue14.widgetRepresentation()
    check("the panel builds", widget is not None)


def main():
    import slicer

    model = slicer.app.extensionsManagerModel()
    model.interactive = False
    say("slicer", slicer.app.applicationVersion, "revision", slicer.app.revision,
        "os", prop(model, "slicerOs"), "arch", prop(model, "slicerArch"))
    say("extensions", prop(model, "extensionsInstallPath"))
    say("phase", PHASE)
    if PHASE == "install":
        install(slicer, model)
    elif PHASE == "load":
        load(slicer, model)
    else:
        check("known phase", False, PHASE)


try:
    main()
except Exception:
    say("EXCEPTION", traceback.format_exc())
    checks.append(False)

passed = bool(checks) and all(checks)
say("RESULT", "PASS" if passed else "FAIL")
with open(OUT, "w") as handle:
    handle.write("\n".join(log) + "\n")
print("\n".join(log))

import slicer  # noqa: E402  (only importable inside Slicer)

slicer.util.exit(0 if passed else 1)
