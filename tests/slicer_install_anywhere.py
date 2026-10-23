"""SegQueue installed as a folder on Slicer's module paths, in a real 3D Slicer (#97).

    Slicer --no-splash --no-main-window --python-script tests/slicer_install_anywhere.py

The route for any Slicer other than 5.8 (and any Mac revision): unzip the
release zip and add ``SegQueue/lib/Slicer-5.8/qt-scripted-modules`` under *Edit
-> Application Settings -> Modules -> Additional module paths*, then restart.
Nothing in it depends on the running Slicer's version or revision, which is what
breaks the Extensions Manager route (#97). The workflow unzips the archive the
way the OS does; this script does what the annotator does in Slicer.

Run twice, like ``slicer_install_zip.py``. ``SEGQUEUE_INSTALL_PHASE=install``
adds ``$SEGQUEUE_INSTALL_BASE/lib/Slicer-5.8/qt-scripted-modules`` to the
module paths, as the Application Settings dialog does. ``load`` is the restart:
the module must load from that folder, import, build its panel, show the
project's server, and its update button must accept the folder, pick the archive
for the installed layout, and install ``$SEGQUEUE_ZIP`` over it.

The report goes to ``$SEGQUEUE_SELFTEST_OUT``; its last line is ``RESULT PASS``
or ``RESULT FAIL``.
"""

import os
import sys
import traceback

OUT = os.environ.get("SEGQUEUE_SELFTEST_OUT", os.path.abspath("install-anywhere.txt"))
PHASE = os.environ.get("SEGQUEUE_INSTALL_PHASE", "install")
BASE = os.path.abspath(os.environ.get("SEGQUEUE_INSTALL_BASE")
                       or os.path.join(os.path.expanduser("~"), "SegQueue"))
FOLDER = os.path.join(BASE, "lib", "Slicer-5.8", "qt-scripted-modules")
SETTING = "Modules/AdditionalPaths"
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
    value = slicer.app.revisionUserSettings().value(SETTING)
    if value is None:
        return []
    return [value] if isinstance(value, str) else [str(v) for v in value]


def install(slicer):
    say("folder", FOLDER)
    check("the unzipped folder holds SegQueue14.py",
          os.path.isfile(os.path.join(FOLDER, "SegQueue14.py")), FOLDER)
    paths = registered(slicer)
    if not any(same(p, FOLDER) for p in paths):
        paths.append(FOLDER)
    settings = slicer.app.revisionUserSettings()
    settings.setValue(SETTING, paths)
    settings.sync()
    check("the folder is an additional module path",
          any(same(p, FOLDER) for p in registered(slicer)), registered(slicer))
    check("the Extensions Manager was not involved",
          not slicer.app.extensionsManagerModel().isExtensionInstalled("SegQueue"))


def load(slicer):
    check("the folder is still registered after the restart",
          any(same(p, FOLDER) for p in registered(slicer)), registered(slicer))
    check("Slicer loaded the SegQueue14 module", hasattr(slicer.modules, "segqueue14"))

    import SegQueue14 as module  # on sys.path because Slicer loaded it

    where = os.path.dirname(os.path.abspath(module.__file__))
    check("from the unzipped folder, not a checkout", same(where, FOLDER), where)
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
    server = widget.self().serverEdit.text
    server = server() if callable(server) else server
    check("a fresh install shows the project's server (#99)",
          server == module.DEFAULT_SERVER_URL == "https://janus.bradensbay.com", server)
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
