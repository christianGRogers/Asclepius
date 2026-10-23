"""SegQueue installs on any Slicer revision as a folder on the module paths (#97).

The Extensions Manager ties an archive to the Slicer it runs in: on macOS to the
revisions written into the zip (#94/#95), everywhere to ``lib/Slicer-<running
version>``. The route for every other Slicer is to unzip the release zip and add
``SegQueue/lib/Slicer-5.8/qt-scripted-modules`` under *Additional module paths*.
These tests unzip the archive the build really produces and check that the
folder is one the module's update button accepts, and that the button asks for
the archive of the installed layout rather than the running Slicer's version.
The real Slicer (5.8.1, latest stable, current preview) does it in the
``install-anywhere`` job of slicer-selftest.yml.
"""

import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_LIB = REPO / "slicer" / "SegQueue14"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from SegQueue14Lib import updater  # noqa: E402

from segqueue import release as rel  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILD = _load("build14_any", REPO / "slicer" / "build-extension14.py")


@pytest.fixture(scope="module")
def archive(tmp_path_factory):
    out = tmp_path_factory.mktemp("dist")
    generic, version, _ = BUILD.build(str(out))
    return Path(generic), version


def _unzip(archive, where):
    """What double-clicking the zip does: one top-level ``SegQueue`` folder."""
    with zipfile.ZipFile(archive) as zf:
        assert {n.split("/")[0] for n in zf.namelist()} == {"SegQueue"}
        zf.extractall(where)
    return where / "SegQueue"


def test_the_unzipped_folder_is_the_module_path_to_add(archive, tmp_path):
    generic, _version = archive
    root = _unzip(generic, tmp_path)
    folder = root / "lib" / "Slicer-5.8" / "qt-scripted-modules"
    assert (folder / "SegQueue14.py").is_file()
    assert (folder / "SegQueue14Lib" / "updater.py").is_file()
    assert (folder / "segqueue14" / "protocol.py").is_file()
    # No nested SegQueue/SegQueue: the documented path is the whole story.
    assert not (root / "SegQueue").exists()


def test_the_update_button_accepts_the_unzipped_folder(archive, tmp_path):
    generic, _version = archive
    root = _unzip(generic, tmp_path / "Downloads")
    folder = root / "lib" / "Slicer-5.8" / "qt-scripted-modules"
    _scripted, found = updater.moduleRoots(str(folder))
    assert found == str(root)
    assert updater.canInstall(str(folder)) == (True, "")
    assert updater.packagedSlicerVersion(str(folder)) == "5.8"
    updater.installArchive(str(generic), str(folder), "5.8",
                           backupRoot=str(tmp_path / "backup"))
    assert (folder / "SegQueue14.py").is_file()


def test_the_published_archive_is_offered_whatever_slicer_runs(archive):
    # Only Slicer-5.8 archives are published; asking for the running version
    # (5.13) found none, so 5.10+ was never offered an update.
    generic, version = archive
    release = {"tag_name": "segqueue-v99.0.0", "assets": [
        {"name": generic.name, "browser_download_url": "https://example.invalid/g"}]}
    assert rel.asset_for(release, "5.13") is None
    assert rel.asset_for(release, "5.8")["name"] == generic.name


def test_the_update_button_asks_for_the_installed_archive_not_the_running_slicer(tmp_path):
    extensions = tmp_path / "Slicer.app" / "Contents" / "Extensions-35403" / "SegQueue"
    scripted = extensions / "lib" / "Slicer-5.8" / "qt-scripted-modules"
    assert updater.packagedSlicerVersion(str(scripted)) == "5.8"
    assert updater.packagedSlicerVersion(str(tmp_path / "SegQueue14")) is None
    assert updater.packagedSlicerVersion(
        str(tmp_path / "lib" / "Slicer-x" / "qt-scripted-modules")) is None


def test_the_module_updates_by_the_installed_archive():
    source = (_LIB / "SegQueue14.py").read_text(encoding="utf-8")
    assert "self._updateSlicerVersion()" in source
    for call in ("checkForUpdate(", "asset_for(", "installArchive("):
        for line in source.splitlines():
            if call in line and "def " not in line:
                assert "_slicerMinorVersion" not in line, line


def test_a_folder_that_is_not_an_install_names_both_routes(tmp_path):
    ok, reason = updater.canInstall(str(tmp_path / "SegQueue14"))
    assert not ok
    assert "Additional module paths" in reason and "Install from file" in reason
