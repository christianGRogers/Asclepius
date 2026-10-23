"""SegQueue installs on any Slicer revision through the console installer (#97).

The Extensions Manager ties an archive to the Slicer it runs in (on macOS to the
revisions written into the zip, #94/#95; everywhere to ``lib/Slicer-<running
version>``). ``slicer/install-segqueue.py`` unpacks the release archive into a
folder the annotator owns and registers it as an additional module path. These
tests run it on the archive the build really produces, with Slicer stubbed out;
the real Slicer (5.8.1, latest stable, current preview) runs it in the
``install-anywhere`` job of slicer-selftest.yml.
"""

import ast
import importlib.util
import sys
import types
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_LIB = REPO / "slicer" / "SegQueue14"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from SegQueue14Lib import updater  # noqa: E402

from segqueue import release as rel  # noqa: E402

INSTALLER_PATH = REPO / "slicer" / "install-segqueue.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INSTALLER = _load("install_segqueue", INSTALLER_PATH)
BUILD = _load("build14_any", REPO / "slicer" / "build-extension14.py")


@pytest.fixture(scope="module")
def archive(tmp_path_factory):
    out = tmp_path_factory.mktemp("dist")
    generic, version, _ = BUILD.build(str(out))
    return Path(generic), version


def _release(tag, *names, **flags):
    return dict({"tag_name": tag, "assets": [
        {"name": n, "browser_download_url": "https://example.invalid/" + n, "size": 1}
        for n in names]}, **flags)


# ------------------------------------------------------------ picking a release

def test_picks_the_newest_segqueue_release_and_its_cross_platform_zip():
    releases = [
        _release("segqueue-v0.16.3", "SegQueue-0.16.3-Slicer-5.8.zip"),
        _release("segqueue-v0.16.10", "SegQueue-0.16.10-Slicer-5.8-macOS.zip",
                 "SegQueue-0.16.10-Slicer-5.8.zip"),
        _release("segqueue-v0.17.0", "SegQueue-0.17.0-Slicer-5.8.zip", draft=True),
        _release("segqueue-v0.18.0", "SegQueue-0.18.0-Slicer-5.8.zip", prerelease=True),
        _release("segtrain-v9.0.0", "SegQueue-9.0.0-Slicer-5.8.zip"),
        _release("segqueue-v0.19.0", "notes.txt"),
    ]
    tag, asset = INSTALLER.pick_asset(releases, "5.13")
    assert tag == "segqueue-v0.16.10"
    assert asset["name"] == "SegQueue-0.16.10-Slicer-5.8.zip"


def test_prefers_an_archive_for_the_running_slicer_when_there_is_one():
    releases = [_release("segqueue-v1.0.0", "SegQueue-1.0.0-Slicer-5.8.zip",
                         "SegQueue-1.0.0-Slicer-5.12.zip", "SegQueue-1.0.0-Slicer-5.10.zip")]
    assert INSTALLER.pick_asset(releases, "5.10")[1]["name"].endswith("5.10.zip")
    assert INSTALLER.pick_asset(releases, "5.13")[1]["name"].endswith("5.12.zip")


def test_no_release_means_none():
    assert INSTALLER.pick_asset([], "5.8") is None
    assert INSTALLER.pick_asset([_release("segqueue-v1.0.0")], "5.8") is None


def test_the_asset_pattern_is_the_updaters():
    assert INSTALLER.ASSET_PATTERN.pattern == rel.ASSET_PATTERN.pattern
    assert INSTALLER.TAG_PREFIX == rel.TAG_PREFIX
    assert INSTALLER.GITHUB_REPO == updater.GITHUB_REPO


# ------------------------------------------------------------------- unpacking

def test_unpacks_into_a_folder_the_updater_accepts(archive, tmp_path):
    generic, _version = archive
    base = tmp_path / "home" / "SegQueue"
    folder = Path(INSTALLER.unpack(str(generic), str(base)))
    assert folder == base / "lib" / "Slicer-5.8" / "qt-scripted-modules"
    assert (folder / "SegQueue14.py").is_file()
    assert (folder / "segqueue14" / "protocol.py").is_file()
    assert (base / "share" / "Slicer-5.8" / "SegQueue.s4ext").is_file()

    _scripted, root = updater.moduleRoots(str(folder))
    assert root == str(base)
    assert updater.canInstall(str(folder)) == (True, "")
    assert updater.packagedSlicerVersion(str(folder)) == "5.8"
    # And the update button can install the next release over it.
    updater.installArchive(str(generic), str(folder), "5.8",
                           backupRoot=str(tmp_path / "backup"))
    assert (folder / "SegQueue14.py").is_file()


def test_running_it_again_installs_over_and_deletes_nothing(archive, tmp_path):
    generic, _version = archive
    base = tmp_path / "SegQueue"
    folder = Path(INSTALLER.unpack(str(generic), str(base)))
    (folder / "SegQueue14.py").write_text("old")
    (folder / "annotator-note.txt").write_text("keep me")
    assert Path(INSTALLER.unpack(str(generic), str(base))) == folder
    assert (folder / "SegQueue14.py").read_text() != "old"
    assert (folder / "annotator-note.txt").read_text() == "keep me"


def _zip(path, names):
    with zipfile.ZipFile(path, "w") as zf:
        for name in names:
            zf.writestr(name, "x")
    return str(path)


@pytest.mark.parametrize("names, message", [
    (["SegQueue/lib/Slicer-5.8/qt-scripted-modules/SegQueue14.py", "SegQueue/../evil"],
     "unsafe"),
    (["/etc/evil", "SegQueue/lib/Slicer-5.8/qt-scripted-modules/SegQueue14.py"], "unsafe"),
    (["Other/lib/Slicer-5.8/qt-scripted-modules/SegQueue14.py"], "not a SegQueue"),
    (["SegQueue/lib/Slicer-5.8/qt-scripted-modules/SegQueue.py"], "one SegQueue14"),
    (["SegQueue/lib/Slicer-5.8/qt-scripted-modules/SegQueue14.py",
      "SegQueue/lib/Slicer-5.10/qt-scripted-modules/SegQueue14.py"], "one SegQueue14"),
])
def test_refuses_archives_that_are_not_one_segqueue_module(tmp_path, names, message):
    path = _zip(tmp_path / "bad.zip", names)
    with pytest.raises(INSTALLER.InstallError, match=message):
        INSTALLER.unpack(path, str(tmp_path / "SegQueue"))
    assert not (tmp_path / "SegQueue").exists()


def test_refuses_the_macos_zip(tmp_path):
    # Its tree sits under Slicer.app/...; there is no top-level module.
    path = _zip(tmp_path / "m.zip", [
        "SegQueue/Slicer.app/Contents/Extensions-33241/SegQueue/lib/Slicer-5.8/"
        "qt-scripted-modules/SegQueue14.py"])
    with pytest.raises(INSTALLER.InstallError):
        INSTALLER.unpack(path, str(tmp_path / "SegQueue"))


# ------------------------------------------------------------- module paths

@pytest.mark.parametrize("value, expected", [
    (None, ["/x"]), ("", ["/x"]), ("/a", ["/a", "/x"]), (("/a", "/x"), ["/a", "/x"]),
    (["/a", "/x/"], ["/a", "/x/"]),
])
def test_the_folder_is_added_to_the_module_paths_once(value, expected):
    assert INSTALLER.with_path(value, "/x") == expected


class _Settings:
    def __init__(self, value=None):
        self.store = {} if value is None else {INSTALLER.SETTING: value}
        self.synced = False

    def value(self, key):
        return self.store.get(key)

    def setValue(self, key, value):
        self.store[key] = value

    def sync(self):
        self.synced = True


class _Model:
    def __init__(self, installed=()):
        self.installed = set(installed)

    def isExtensionInstalled(self, name):
        return name in self.installed


def _fake_slicer(monkeypatch, settings, model, minor=13):
    app = types.SimpleNamespace(majorVersion=5, minorVersion=minor,
                                revisionUserSettings=lambda: settings,
                                extensionsManagerModel=lambda: model)
    monkeypatch.setitem(sys.modules, "slicer", types.SimpleNamespace(app=app))


def test_install_registers_the_folder_in_slicers_settings(archive, tmp_path, monkeypatch):
    generic, _version = archive
    settings = _Settings(["/somewhere/else"])
    _fake_slicer(monkeypatch, settings, _Model(installed={INSTALLER.EXTRA_EFFECTS}))
    folder = INSTALLER.install(zip_path=str(generic), base=str(tmp_path / "SegQueue"),
                               restart=False)
    assert settings.store[INSTALLER.SETTING] == ["/somewhere/else", folder]
    assert settings.synced
    assert (Path(folder) / "SegQueue14.py").is_file()


def test_install_refuses_next_to_an_extensions_manager_install(archive, tmp_path,
                                                                monkeypatch):
    # Two copies of SegQueue14 on the module path; Slicer would load one at random.
    generic, _version = archive
    settings = _Settings()
    _fake_slicer(monkeypatch, settings, _Model(installed={"SegQueue"}), minor=8)
    with pytest.raises(INSTALLER.InstallError, match="Extensions Manager"):
        INSTALLER.install(zip_path=str(generic), base=str(tmp_path / "SegQueue"),
                          restart=False, extra_effects=False)
    assert settings.store == {}
    assert not (tmp_path / "SegQueue").exists()


# --------------------------------------------------- what the update button asks

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


# ------------------------------------------------------------------ portability

def test_the_installer_is_python_39_clean():
    ast.parse(INSTALLER_PATH.read_text(encoding="utf-8"), feature_version=(3, 9))


def test_the_installer_needs_only_stdlib_and_requests():
    tree = ast.parse(INSTALLER_PATH.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module.split(".")[0])
    allowed = {"os", "re", "shutil", "tempfile", "zipfile", "requests", "slicer"}
    assert imported <= allowed, imported - allowed


def test_the_documented_one_liner_points_at_this_file():
    line = ('import requests; exec(requests.get("https://raw.githubusercontent.com/'
            'christianGRogers/Asclepius/main/slicer/install-segqueue.py", timeout=60).text)')
    assert line in INSTALLER_PATH.read_text(encoding="utf-8")
    assert line in (_LIB / "README.md").read_text(encoding="utf-8")
