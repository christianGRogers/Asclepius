"""The macOS archive installs on a Mac (#94).

On macOS, Slicer's *Install from file* extracts the zip into
``Extensions-<rev>/SegQueue/`` and then copies only
``SegQueue/Slicer.app/Contents/Extensions-<rev>/SegQueue`` out of it
(``qSlicerExtensionsManagerModel::extractExtensionArchive``, the
``Slicer_OS_MAC_NAME`` branch; the same in 5.8.1 and 5.10.0). The cross-platform
zip has no such path, which is why no Mac could install SegQueue. These tests
replay that copy on the archives the build really produces; the real Slicer does
it in the ``install`` job of slicer-selftest.yml.
"""

import importlib.util
import os
import shutil
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

SLICER = "5.8"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILD = _load("build14_macos", REPO / "slicer" / "build-extension14.py")


@pytest.fixture(scope="module")
def archives(tmp_path_factory):
    out = tmp_path_factory.mktemp("dist")
    generic, version, _ = BUILD.build(str(out))
    macos, macVersion, _ = BUILD.buildMacos(str(out))
    assert macVersion == version
    return Path(generic), Path(macos), version


def _install_from_file(archive, extensions, slicerOs, revision):
    """What Slicer's Extensions Manager does with a zip, by OS. Returns the install dir."""
    work = extensions / "SegQueue"
    work.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(work)
    top = {n.split("/")[0] for n in zipfile.ZipFile(archive).namelist()}
    assert len(top) == 1, top
    src = work / top.pop()
    if slicerOs == "macosx":
        src = src / "Slicer.app" / "Contents" / f"Extensions-{revision}" / "SegQueue"
    if not src.is_dir():
        raise FileNotFoundError(f"Failed to copy directory {src}")  # Slicer's error
    intermediate = extensions / "SegQueue-XXXXXX"
    shutil.copytree(src, intermediate)
    shutil.rmtree(work)
    intermediate.rename(work)
    return work


def _tree(root):
    return sorted(str(p.relative_to(root)).replace(os.sep, "/")
                  for p in root.rglob("*") if p.is_file())


def test_the_cross_platform_zip_cannot_be_installed_on_a_mac(archives, tmp_path):
    generic, _macos, _version = archives
    with pytest.raises(FileNotFoundError, match="Failed to copy directory"):
        _install_from_file(generic, tmp_path / "Extensions-33241", "macosx", "33241")


@pytest.mark.parametrize("revision", BUILD.MACOS_REVISIONS[SLICER])
def test_the_macos_zip_installs_the_same_tree_as_linux(archives, tmp_path, revision):
    generic, macos, _version = archives
    linux = _install_from_file(generic, tmp_path / "linux" / "Extensions-x", "linux", None)
    mac = _install_from_file(macos, tmp_path / "mac" / f"Extensions-{revision}",
                             "macosx", revision)
    assert _tree(mac) == _tree(linux)
    assert "lib/Slicer-5.8/qt-scripted-modules/SegQueue14.py" in _tree(mac)
    assert "share/Slicer-5.8/SegQueue.s4ext" in _tree(mac)
    for name in _tree(linux):
        assert (mac / name).read_bytes() == (linux / name).read_bytes(), name


def test_both_annotator_slicer_58_releases_are_covered():
    # 5.8.0 and 5.8.1, from slicer-packages.kitware.com.
    assert set(BUILD.MACOS_REVISIONS["5.8"]) >= {"33216", "33241"}


def test_an_unknown_revision_is_not_silently_missing(archives, tmp_path):
    _generic, macos, _version = archives
    with pytest.raises(FileNotFoundError):
        _install_from_file(macos, tmp_path / "Extensions-1", "macosx", "1")


def test_a_slicer_version_with_no_known_revisions_fails_the_build(tmp_path):
    with pytest.raises(SystemExit, match="MACOS_REVISIONS"):
        BUILD.buildMacos(str(tmp_path), slicerVersion="9.9")


def test_the_macos_zip_names_one_s4ext_extension(archives):
    # Install from file names the extension after the first .s4ext it lists.
    _generic, macos, _version = archives
    s4ext = {os.path.basename(n) for n in zipfile.ZipFile(macos).namelist()
             if n.endswith(".s4ext")}
    assert s4ext == {"SegQueue.s4ext"}


def test_the_update_button_never_picks_the_macos_zip(archives):
    generic, macos, version = archives
    assert macos.name == f"SegQueue-{version}-Slicer-{SLICER}-macOS.zip"
    assert rel.ASSET_PATTERN.match(macos.name) is None
    release = {"tag_name": "segqueue-v" + version, "assets": [
        {"name": macos.name, "browser_download_url": "https://example.invalid/m"},
        {"name": generic.name, "browser_download_url": "https://example.invalid/g"}]}
    assert rel.asset_for(release, SLICER)["name"] == generic.name


def test_the_update_button_works_on_a_mac_install(archives, tmp_path):
    """After a Mac install the layout is Linux's, so updating needs nothing new."""
    generic, macos, _version = archives
    extensions = tmp_path / "Slicer.app" / "Contents" / "Extensions-33241"
    installed = _install_from_file(macos, extensions, "macosx", "33241")
    scripted = installed / "lib" / "Slicer-5.8" / "qt-scripted-modules"
    _s, root = updater.moduleRoots(str(scripted))
    assert root == str(installed)
    assert updater.canInstall(str(scripted)) == (True, "")
    updater.installArchive(str(generic), str(scripted), SLICER,
                           backupRoot=str(tmp_path / "backup"))
    assert (scripted / "SegQueue14.py").is_file()
