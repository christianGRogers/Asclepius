"""Install SegQueue with the console installer, inside a real 3D Slicer (#97).

    Slicer --no-splash --no-main-window --python-script tests/slicer_install_anywhere.py

Run twice, like ``slicer_install_zip.py``. ``SEGQUEUE_INSTALL_PHASE=install``
runs ``slicer/install-segqueue.py`` (what an annotator's one pasted line runs)
on ``$SEGQUEUE_ZIP`` into ``$SEGQUEUE_INSTALL_BASE``, without the restart
prompt. ``load`` is the restart: the module must load from that folder, import,
build its panel, and its update button must accept the folder, pick the
archive for the installed layout, and install over it.

The point is that nothing here depends on the running Slicer's version or
revision, which is what broke the Extensions Manager route on a Mac running a
preview (#97). CI runs it on Slicer 5.8.1, the latest stable and the current
preview.

The report goes to ``$SEGQUEUE_SELFTEST_OUT``; its last line is ``RESULT PASS``
or ``RESULT FAIL``.
"""

import importlib.util
import os
import sys
import traceback

OUT = os.environ.get("SEGQUEUE_SELFTEST_OUT", os.path.abspath("install-anywhere.txt"))
PHASE = os.environ.get("SEGQUEUE_INSTALL_PHASE", "install")
BASE = os.path.abspath(os.environ.get("SEGQUEUE_INSTALL_BASE")
                       or os.path.join(os.path.expanduser("~"), "SegQueue"))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TLS_PROBE = "https://slicer-packages.kitware.com/api/v1/system/version"

log = []
checks = []


def say(*parts):
    log.append(" ".join(str(p) for p in parts))


def check(name, passed, detail=""):
    checks.append(bool(passed))
    say("PASS" if passed else "FAIL", name, detail)


def same(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def registered(slicer):
    value = slicer.app.revisionUserSettings().value("Modules/AdditionalPaths")
    if value is None:
        return []
    return [value] if isinstance(value, str) else [str(v) for v in value]


def installer():
    path = os.path.join(REPO, "slicer", "install-segqueue.py")
    spec = importlib.util.spec_from_file_location("install_segqueue", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def install(slicer):
    archive = os.environ["SEGQUEUE_ZIP"]
    say("archive", archive)
    say("base", BASE)
    folder = installer().install(zip_path=archive, base=BASE, restart=False)
    check("the installer put SegQueue14.py in the folder",
          os.path.isfile(os.path.join(folder, "SegQueue14.py")), folder)
    check("the folder is inside the chosen base", same(os.path.dirname(os.path.dirname(
        os.path.dirname(folder))), BASE), folder)
    paths = registered(slicer)
    check("the folder is an additional module path",
          any(same(p, folder) for p in paths), paths)
    model = slicer.app.extensionsManagerModel()
    check("the Extensions Manager was not involved",
          not model.isExtensionInstalled("SegQueue"))
    say("INFO SegmentEditorExtraEffects installed:",
        model.isExtensionInstalled("SegmentEditorExtraEffects"))


def load(slicer):
    folder = os.path.join(BASE, "lib", "Slicer-5.8", "qt-scripted-modules")
    check("the folder is still registered after the restart",
          any(same(p, folder) for p in registered(slicer)), registered(slicer))
    check("Slicer loaded the SegQueue14 module", hasattr(slicer.modules, "segqueue14"))

    import SegQueue14 as module  # on sys.path because Slicer loaded it

    where = os.path.dirname(os.path.abspath(module.__file__))
    check("from the installed folder, not a checkout", same(where, folder), where)
    check("its shared packages imported", module._IMPORT_ERROR is None, module._IMPORT_ERROR)

    from SegQueue14Lib import updater

    from segqueue import release as rel

    _scripted, root = updater.moduleRoots(where)
    check("the updater recognises the folder", root is not None and same(root, BASE), root)
    ok, reason = updater.canInstall(where)
    check("the update button could install over it", ok, reason)
    check("updates come from the 5.8 archive, whatever Slicer runs",
          updater.packagedSlicerVersion(where) == "5.8", updater.packagedSlicerVersion(where))

    widget = slicer.modules.segqueue14.widgetRepresentation()
    check("the panel builds", widget is not None)
    asked = widget.self()._updateSlicerVersion()
    check("the panel asks for the installed archive's Slicer version", asked == "5.8", asked)
    archive = os.environ["SEGQUEUE_ZIP"]
    name = os.path.basename(archive)
    release = {"tag_name": "segqueue-v99.0.0", "assets": [
        {"name": name, "browser_download_url": "https://example.invalid/" + name}]}
    check("the published archive is offered to this Slicer",
          rel.asset_for(release, asked) is not None, name)
    backup = updater.installArchive(archive, where, asked)
    check("the update button installed the archive over the folder",
          os.path.isdir(backup) and os.path.isfile(os.path.join(where, "SegQueue14.py")),
          backup)

    import requests

    try:
        reply = requests.get(TLS_PROBE, timeout=(10, 30))
        check("HTTPS with certificate verification works", reply.status_code == 200,
              "HTTP {}".format(reply.status_code))
    except requests.exceptions.SSLError as exc:
        check("HTTPS with certificate verification works", False, exc)


def main():
    import slicer

    arch = slicer.app.extensionsManagerModel().slicerArch
    say("slicer", slicer.app.applicationVersion, "revision", slicer.app.revision,
        "arch", arch() if callable(arch) else arch)
    say("python", sys.version.split()[0], sys.platform)
    say("phase", PHASE)
    if PHASE == "install":
        install(slicer)
    elif PHASE == "load":
        load(slicer)
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
