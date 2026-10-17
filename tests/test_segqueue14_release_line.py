"""SegQueue14 as the SegQueue release line (0.14.0 on; project lead, 2026-10-17).

The property that matters: an annotator on SegQueue 0.13 presses *Check for
updates*, is offered SegQueue14, presses *Update and restart*, and ends up with
SegQueue14 and no working 4-class module. That is tested here with the 0.13
updater itself (``slicer/SegQueue/SegQueueLib``), unchanged, against the archive
``build-extension14.py`` really produces. Then: SegQueue14's own updater keeps it
current and refuses to put a pre-0.14 SegQueue archive back over it.
"""

import importlib.util
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
for _lib in (REPO / "slicer" / "SegQueue", REPO / "slicer" / "SegQueue14"):
    if str(_lib) not in sys.path:
        sys.path.insert(0, str(_lib))

from SegQueue14Lib import updater as new_updater  # noqa: E402
from SegQueueLib import updater as old_updater  # noqa: E402

from segqueue import release as rel  # noqa: E402

SLICER = "5.8"
SCRIPTED = "SegQueue/lib/Slicer-{}/qt-scripted-modules/".format(SLICER)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("dist")
    build14 = _load("build14", REPO / "slicer" / "build-extension14.py")
    archive, version, _ = build14.build(str(out))
    return Path(archive), version


@pytest.fixture
def installed_013(tmp_path):
    """A SegQueue 0.13 install, made from the real 0.13-era build of slicer/SegQueue."""
    build = _load("build_live", REPO / "slicer" / "build-extension.py")
    archive, _, _ = build.build(str(tmp_path / "live-dist"))
    root = tmp_path / "Extensions-33241"
    zipfile.ZipFile(archive).extractall(root)
    return root / SCRIPTED.rstrip("/")


def _release(archive, version):
    return {"tag_name": "segqueue-v" + version, "name": "SegQueue " + version,
            "html_url": "https://example.invalid/r",
            "assets": [{"name": archive.name,
                        "browser_download_url": "https://example.invalid/" + archive.name}]}


def _live_version():
    text = (REPO / "slicer" / "SegQueue" / "SegQueue.py").read_text(encoding="utf-8")
    return re.search(r'^__version__ = "([^"]+)"', text, re.M).group(1)


def test_the_version_continues_segqueues_numbering(built):
    _archive, version = built
    assert rel.is_newer(version, _live_version()), (version, _live_version())
    assert version == "0.14.0" or rel.is_newer(version, "0.14.0")


def test_the_archive_is_named_and_rooted_as_a_segqueue_release(built):
    archive, version = built
    assert archive.name == "SegQueue-{}-Slicer-{}.zip".format(version, SLICER)
    assert rel.ASSET_PATTERN.match(archive.name)
    names = zipfile.ZipFile(archive).namelist()
    assert {n.split("/")[0] for n in names} == {"SegQueue"}
    for member in ("SegQueue14.py", "SegQueue.py", "SegQueue14Lib/updater.py",
                   "segqueue/release.py", "segqueue14/protocol.py",
                   "Resources/Icons/SegQueue14.png"):
        assert SCRIPTED + member in names, member
    assert "SegQueue/share/Slicer-{}/SegQueue.s4ext".format(SLICER) in names
    assert not any("/SegQueueLib/" in n for n in names)


def test_segqueue_013_is_offered_it_ahead_of_the_old_segqueue14_tag(built):
    archive, version = built
    releases = [
        {"tag_name": "segqueue14-v0.1.0", "assets": [
            {"name": "SegQueue14-0.1.0-Slicer-5.8.zip", "browser_download_url": "x"}]},
        _release(archive, version),
        {"tag_name": "segqueue-v0.13.0", "assets": [
            {"name": "SegQueue-0.13.0-Slicer-5.8.zip", "browser_download_url": "y"}]},
    ]
    offered = rel.update_available(releases, _live_version(), slicer_version=SLICER)
    assert offered is not None and offered["tag_name"] == "segqueue-v" + version


def test_segqueue_013s_own_updater_installs_it_and_retires_the_old_module(built, installed_013):
    archive, _version = built
    assert "class SegQueueWidget" in (installed_013 / "SegQueue.py").read_text()
    assert "def onUpdateNow" in (installed_013 / "SegQueue.py").read_text()

    backup = old_updater.installArchive(str(archive), str(installed_013), SLICER)

    stub = (installed_013 / "SegQueue.py").read_text()
    assert "replaced by SegQueue14" in stub and "onUpdateNow" not in stub
    assert (installed_013 / "SegQueue14.py").is_file()
    assert (installed_013 / "SegQueue14Lib" / "updater.py").is_file()
    assert "def onUpdateNow" in (Path(backup) / "SegQueue.py").read_text()

    # What Slicer will load from that directory imports cleanly: the vendored
    # packages are the new ones, not 0.13's.
    code = ("import sys; sys.path[:] = [p for p in sys.path if 'src' not in p]; "
            f"sys.path.insert(0, {str(installed_013)!r}); "
            "import segqueue14.protocol, segqueue.release, segqueue.states, segqueue.segcheck; "
            "assert segqueue14.__file__.startswith(sys.path[0]); "
            "print(segqueue14.PROTOCOL_VERSION)")
    out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    stub_path = str(installed_013 / "SegQueue.py")
    parsed = subprocess.run([sys.executable, "-I", "-c",
                             f"import ast; ast.parse(open({stub_path!r}).read())"])
    assert parsed.returncode == 0


def test_segqueue14_updates_itself_from_the_next_release(built, installed_013, tmp_path):
    archive, version = built
    old_updater.installArchive(str(archive), str(installed_013), SLICER)
    # A later release, same shape.
    later = tmp_path / "SegQueue-99.0.0-Slicer-5.8.zip"
    with zipfile.ZipFile(archive) as src, zipfile.ZipFile(later, "w") as dst:
        for item in src.infolist():
            data = src.read(item)
            if item.filename == SCRIPTED + "SegQueue14.py":
                old = '__version__ = "{}"'.format(version).encode()
                assert old in data
                data = data.replace(old, b'__version__ = "99.0.0"')
            dst.writestr(item, data)
    new_updater.installArchive(str(later), str(installed_013), SLICER)
    assert '__version__ = "99.0.0"' in (installed_013 / "SegQueue14.py").read_text()


def test_segqueue14_refuses_to_put_the_old_module_back(installed_013, tmp_path):
    build = _load("build_live2", REPO / "slicer" / "build-extension.py")
    old_archive, _, _ = build.build(str(tmp_path / "old"))
    with pytest.raises(new_updater.UpdateError, match="SegQueue14"):
        new_updater.inspectArchive(old_archive, SLICER)
