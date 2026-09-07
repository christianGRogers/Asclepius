"""The self-updater, exercised against scratch directories and a stub GitHub.

This is the one part of the client that writes into a Slicer installation, so
what is tested here is mostly what it *refuses* to do: overwrite a checkout,
unpack an archive that is not a SegQueue package, or leave a half-swapped module
behind when something fails partway.

No Slicer, no Qt, no network -- ``SegQueueLib`` is written free of all three, and
this is what that buys.
"""

import json
import os
import sys
import zipfile
from pathlib import Path

import pytest

_EXTENSION = Path(__file__).resolve().parents[1] / "slicer" / "SegQueue"
if str(_EXTENSION) not in sys.path:
    sys.path.insert(0, str(_EXTENSION))

from SegQueueLib import updater  # noqa: E402
from SegQueueLib.updater import UpdateError  # noqa: E402

SLICER = "5.8"
PREFIX = "SegQueue/lib/Slicer-{}/qt-scripted-modules/".format(SLICER)


# --------------------------------------------------------------------- stubs


class FakeResponse:
    def __init__(self, status_code=200, body=None, chunks=None):
        self.status_code = status_code
        self._body = body
        self.headers = {}
        self._chunks = chunks or []

    def json(self):
        if self._body is None:
            raise ValueError("not json")
        return self._body

    def iter_content(self, chunk_size=None):
        return iter(self._chunks)


class FakeSession:
    """Answers whatever the test queued, and records what it was asked."""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error is not None:
            raise self.error
        return self.response


def _release(version="0.3.0", size=None):
    name = "SegQueue-{}-Slicer-{}.zip".format(version, SLICER)
    asset = {"name": name, "browser_download_url": "https://example.invalid/" + name}
    if size is not None:
        asset["size"] = size
    return {"tag_name": "segqueue-v" + version, "html_url": "https://example.invalid/r",
            "assets": [asset]}


def _package(tmp_path, version="0.3.0", extra=(), omit_module=False, unsafe=False):
    """Build an archive shaped like the one build-extension.py produces."""
    path = tmp_path / "SegQueue-{}-Slicer-{}.zip".format(version, SLICER)
    with zipfile.ZipFile(path, "w") as archive:
        if not omit_module:
            archive.writestr(PREFIX + "SegQueue.py",
                             '__version__ = "{}"\n'.format(version))
            archive.writestr(PREFIX + "SegQueueLib/__init__.py", "# new\n")
            archive.writestr(PREFIX + "Resources/Icons/SegQueue.png", "png-bytes")
        for name, body in extra:
            archive.writestr(name, body)
        if unsafe:
            archive.writestr(PREFIX + "../../../../evil.py", "boom")
        archive.writestr("SegQueue/share/Slicer-{}/SegQueue.s4ext".format(SLICER), "scm git\n")
    return str(path)


def _installed(tmp_path, version="0.2.0"):
    """A directory tree shaped like an installed extension."""
    scripted = tmp_path / "Extensions-33241" / "SegQueue" / "lib" / \
        ("Slicer-" + SLICER) / "qt-scripted-modules"
    (scripted / "SegQueueLib").mkdir(parents=True)
    (scripted / "SegQueue.py").write_text('__version__ = "{}"\n'.format(version))
    (scripted / "SegQueueLib" / "__init__.py").write_text("# old\n")
    (scripted / "keep-me.txt").write_text("not in the archive\n")
    return str(scripted)


# ------------------------------------------------------------------ discovery

def test_check_offers_a_newer_release(tmp_path):
    session = FakeSession(FakeResponse(body=[_release("0.3.0")]))
    found = updater.checkForUpdate("0.2.0", SLICER, session=session)
    assert found["tag_name"] == "segqueue-v0.3.0"
    assert session.calls[0][0] == updater.RELEASES_URL


def test_check_is_silent_when_current():
    session = FakeSession(FakeResponse(body=[_release("0.2.0")]))
    assert updater.checkForUpdate("0.2.0", SLICER, session=session) is None


def test_check_ignores_an_archive_for_another_slicer():
    session = FakeSession(FakeResponse(body=[_release("0.3.0")]))
    assert updater.checkForUpdate("0.2.0", "5.6", session=session) is None


def test_check_explains_a_rate_limit_rather_than_failing_vaguely():
    session = FakeSession(FakeResponse(status_code=403))
    with pytest.raises(UpdateError) as caught:
        updater.checkForUpdate("0.2.0", SLICER, session=session)
    assert "rate-limit" in str(caught.value)


@pytest.mark.parametrize("response, error", [
    (FakeResponse(status_code=500), None),
    (FakeResponse(body=None), None),               # not JSON
    (FakeResponse(body={"not": "a list"}), None),
    (None, OSError("no route to host")),
])
def test_check_raises_update_error_not_something_random(response, error):
    session = FakeSession(response, error)
    with pytest.raises(UpdateError):
        updater.checkForUpdate("0.2.0", SLICER, session=session)


# ------------------------------------------------------------------ download

def test_download_writes_the_file_and_reports_progress(tmp_path):
    chunks = [b"a" * 10, b"b" * 5]
    session = FakeSession(FakeResponse(chunks=chunks))
    seen = []
    dest = str(tmp_path / "out.zip")
    written = updater.downloadAsset(
        {"browser_download_url": "https://example.invalid/x.zip", "size": 15},
        dest, session=session, progress=lambda d, t: seen.append((d, t)))
    assert written == 15
    assert open(dest, "rb").read() == b"a" * 10 + b"b" * 5
    assert seen[-1] == (15, 15)
    assert not os.path.exists(dest + ".part")


def test_download_refuses_a_short_read_and_leaves_nothing_behind(tmp_path):
    session = FakeSession(FakeResponse(chunks=[b"a" * 5]))
    dest = str(tmp_path / "out.zip")
    with pytest.raises(UpdateError) as caught:
        updater.downloadAsset(
            {"browser_download_url": "https://example.invalid/x.zip", "size": 99},
            dest, session=session)
    assert "stopped early" in str(caught.value)
    assert not os.path.exists(dest)
    assert not os.path.exists(dest + ".part")


def test_download_refuses_an_implausible_size(tmp_path):
    session = FakeSession(FakeResponse(chunks=[]))
    with pytest.raises(UpdateError):
        updater.downloadAsset(
            {"browser_download_url": "https://example.invalid/x.zip",
             "size": updater.MAX_ARCHIVE_BYTES + 1},
            str(tmp_path / "out.zip"), session=session)


# --------------------------------------------------------------------- layout

def test_module_roots_finds_the_extension_root(tmp_path):
    scripted = _installed(tmp_path)
    found, root = updater.moduleRoots(scripted)
    assert os.path.basename(root) == "SegQueue"
    assert os.path.basename(found) == "qt-scripted-modules"


def test_module_roots_reports_no_root_for_some_other_directory(tmp_path):
    _found, root = updater.moduleRoots(str(tmp_path))
    assert root is None


def test_is_checkout_walks_up_to_the_git_directory(tmp_path):
    (tmp_path / ".git").mkdir()
    deep = tmp_path / "slicer" / "SegQueue"
    deep.mkdir(parents=True)
    assert updater.isCheckout(str(deep))
    assert not updater.isCheckout(str(tmp_path.parent / "nowhere"))


def test_can_install_refuses_a_checkout(tmp_path):
    (tmp_path / ".git").mkdir()
    module = tmp_path / "slicer" / "SegQueue"
    module.mkdir(parents=True)
    ok, reason = updater.canInstall(str(module))
    assert not ok and "git pull" in reason


def test_can_install_refuses_a_directory_that_is_not_an_extension(tmp_path):
    ok, reason = updater.canInstall(str(tmp_path))
    assert not ok and "Install from file" in reason


def test_can_install_accepts_a_real_install(tmp_path):
    ok, reason = updater.canInstall(_installed(tmp_path))
    assert ok and reason == ""


# -------------------------------------------------------------------- archive

def test_inspect_accepts_a_real_package(tmp_path):
    members = updater.inspectArchive(_package(tmp_path), SLICER)
    assert any(m.endswith("/SegQueue.py") for m in members)


def test_inspect_rejects_a_package_for_another_slicer(tmp_path):
    with pytest.raises(UpdateError) as caught:
        updater.inspectArchive(_package(tmp_path), "5.6")
    assert "Slicer 5.6" in str(caught.value)


def test_inspect_rejects_an_archive_with_no_module(tmp_path):
    with pytest.raises(UpdateError):
        updater.inspectArchive(_package(tmp_path, omit_module=True), SLICER)


def test_inspect_rejects_a_path_that_escapes(tmp_path):
    with pytest.raises(UpdateError) as caught:
        updater.inspectArchive(_package(tmp_path, unsafe=True), SLICER)
    assert "unsafe path" in str(caught.value)


def test_inspect_rejects_something_that_is_not_a_zip(tmp_path):
    path = tmp_path / "not.zip"
    path.write_text("hello")
    with pytest.raises(UpdateError) as caught:
        updater.inspectArchive(str(path), SLICER)
    assert "not a valid archive" in str(caught.value)


# -------------------------------------------------------------------- install

def test_install_replaces_the_module_and_keeps_a_backup(tmp_path):
    scripted = _installed(tmp_path, version="0.2.0")
    backup = updater.installArchive(_package(tmp_path, "0.3.0"), scripted, SLICER)

    assert '0.3.0' in open(os.path.join(scripted, "SegQueue.py")).read()
    assert open(os.path.join(scripted, "SegQueueLib", "__init__.py")).read() == "# new\n"
    assert os.path.isfile(os.path.join(scripted, "Resources", "Icons", "SegQueue.png"))
    # The backup holds the version that was there before.
    assert '0.2.0' in open(os.path.join(backup, "SegQueue.py")).read()


def test_install_never_deletes_files_it_did_not_ship(tmp_path):
    # Stale files are untidy; deleting the wrong one mid-swap is not recoverable.
    scripted = _installed(tmp_path)
    updater.installArchive(_package(tmp_path, "0.3.0"), scripted, SLICER)
    assert os.path.isfile(os.path.join(scripted, "keep-me.txt"))


def test_install_refuses_a_checkout_before_touching_anything(tmp_path):
    (tmp_path / ".git").mkdir()
    module = tmp_path / "slicer" / "SegQueue"
    module.mkdir(parents=True)
    (module / "SegQueue.py").write_text('__version__ = "0.2.0"\n')
    with pytest.raises(UpdateError):
        updater.installArchive(_package(tmp_path, "0.3.0"), str(module), SLICER)
    assert '0.2.0' in (module / "SegQueue.py").read_text()


def test_install_refuses_a_bad_archive_before_touching_anything(tmp_path):
    scripted = _installed(tmp_path, version="0.2.0")
    bad = tmp_path / "bad.zip"
    bad.write_text("not a zip")
    with pytest.raises(UpdateError):
        updater.installArchive(str(bad), scripted, SLICER)
    assert '0.2.0' in open(os.path.join(scripted, "SegQueue.py")).read()


# ---------------------------------------------------------------------- cache

def test_cache_round_trips():
    assert updater.readCache(json.dumps({"checkedAt": 1.0})) == {"checkedAt": 1.0}


@pytest.mark.parametrize("text", ["", None, "{", "[]", '"a string"'])
def test_cache_treats_junk_as_no_cache(text):
    assert updater.readCache(text) == {}


def test_cache_is_fresh_inside_the_window_and_stale_outside():
    cache = {"checkedAt": 1000.0}
    assert updater.cacheIsFresh(cache, 3600, now=1000.0 + 60)
    assert not updater.cacheIsFresh(cache, 3600, now=1000.0 + 3601)
    # A clock that jumped backwards must not freeze the check forever.
    assert not updater.cacheIsFresh(cache, 3600, now=900.0)
    assert not updater.cacheIsFresh({}, 3600, now=1000.0)
