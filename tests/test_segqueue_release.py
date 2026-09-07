"""Update selection. These tests exist because the wrong answer rewrites a working install."""

import pytest

from segqueue.release import (
    TAG_PREFIX,
    archive_members,
    asset_for,
    describe,
    is_newer,
    parse_version,
    select_latest,
    update_available,
)


def _asset(name, url="https://example.invalid/a.zip"):
    return {"name": name, "browser_download_url": url}


def _release(tag, assets=("SegQueue-0.3.0-Slicer-5.8.zip",), **kwargs):
    release = {"tag_name": tag, "assets": [_asset(n) for n in assets]}
    release.update(kwargs)
    return release


# ------------------------------------------------------------------ versions

@pytest.mark.parametrize("text, expected", [
    ("0.3.0", ((0, 3, 0), "")),
    ("v0.3.0", ((0, 3, 0), "")),
    ("segqueue-v0.3.0", ((0, 3, 0), "")),
    ("  segqueue-v1.0  ", ((1, 0), "")),
    ("0.3.0+build7", ((0, 3, 0), "+build7")),
    ("2.10.1", ((2, 10, 1), "")),
])
def test_parse_version_accepts_the_forms_we_publish(text, expected):
    assert parse_version(text) == expected


@pytest.mark.parametrize("text", ["", None, "latest", "vNext", "release-2024", "x1.2"])
def test_parse_version_rejects_everything_else(text):
    assert parse_version(text) is None


@pytest.mark.parametrize("candidate, current", [
    ("0.3.0", "0.2.0"),
    ("0.2.1", "0.2.0"),
    ("1.0.0", "0.99.99"),
    ("0.10.0", "0.9.0"),          # not string ordering
    ("0.3.0+build7", "0.3.0"),    # a rebuild of the same version is newer
    ("segqueue-v0.3.0", "0.2.0"),
])
def test_is_newer_true(candidate, current):
    assert is_newer(candidate, current)


@pytest.mark.parametrize("candidate, current", [
    ("0.2.0", "0.2.0"),
    ("0.2", "0.2.0"),             # padded, so equal
    ("0.2.0", "0.3.0"),
    ("0.9.0", "0.10.0"),
    ("garbage", "0.2.0"),         # unparseable is never newer
    ("0.3.0", "garbage"),         # nor is it newer *than* garbage
    (None, "0.2.0"),
])
def test_is_newer_false(candidate, current):
    assert not is_newer(candidate, current)


# -------------------------------------------------------------------- assets

def test_asset_for_finds_the_archive_among_others():
    release = _release("segqueue-v0.3.0", assets=(
        "SegQueue-0.3.0-Slicer-5.8.zip.sha256",
        "release-notes.md",
        "SegQueue-0.3.0-Slicer-5.8.zip",
    ))
    assert asset_for(release)["name"] == "SegQueue-0.3.0-Slicer-5.8.zip"


def test_asset_for_respects_the_slicer_version():
    release = _release("segqueue-v0.3.0", assets=("SegQueue-0.3.0-Slicer-5.6.zip",))
    assert asset_for(release, slicer_version="5.8") is None
    assert asset_for(release, slicer_version="5.6") is not None


def test_asset_for_ignores_an_asset_with_no_download_url():
    release = {"tag_name": "segqueue-v0.3.0",
               "assets": [{"name": "SegQueue-0.3.0-Slicer-5.8.zip"}]}
    assert asset_for(release) is None


# ------------------------------------------------------------------ selection

def test_select_latest_orders_by_version_not_by_position():
    releases = [_release("segqueue-v0.2.0"), _release("segqueue-v0.10.0"),
                _release("segqueue-v0.9.0")]
    assert select_latest(releases)["tag_name"] == "segqueue-v0.10.0"


def test_select_latest_ignores_another_projects_tags():
    releases = [_release("v9.9.9"), _release("segtrain-v5.0.0"),
                _release("segqueue-v0.2.0")]
    assert select_latest(releases)["tag_name"] == "segqueue-v0.2.0"


def test_select_latest_skips_drafts_and_prereleases():
    releases = [
        _release("segqueue-v0.5.0", draft=True),
        _release("segqueue-v0.4.0", prerelease=True),
        _release("segqueue-v0.3.0"),
    ]
    assert select_latest(releases)["tag_name"] == "segqueue-v0.3.0"


def test_select_latest_can_opt_into_prereleases():
    releases = [_release("segqueue-v0.4.0", prerelease=True), _release("segqueue-v0.3.0")]
    assert select_latest(releases, allow_prerelease=True)["tag_name"] == "segqueue-v0.4.0"


def test_select_latest_skips_a_release_with_no_installable_archive():
    releases = [_release("segqueue-v0.4.0", assets=("notes.txt",)),
                _release("segqueue-v0.3.0")]
    assert select_latest(releases)["tag_name"] == "segqueue-v0.3.0"


@pytest.mark.parametrize("releases", [[], None, [{"tag_name": "nonsense"}], ["not a dict"]])
def test_select_latest_survives_junk(releases):
    assert select_latest(releases) is None


# ------------------------------------------------------------- the whole call

def test_update_available_offers_a_newer_release():
    releases = [_release("segqueue-v0.3.0")]
    assert update_available(releases, "0.2.0")["tag_name"] == "segqueue-v0.3.0"


@pytest.mark.parametrize("current", ["0.3.0", "0.4.0"])
def test_update_available_is_silent_when_current_or_ahead(current):
    assert update_available([_release("segqueue-v0.3.0")], current) is None


def test_update_available_is_silent_when_the_client_version_is_unreadable():
    assert update_available([_release("segqueue-v0.3.0")], "not-a-version") is None


def test_tag_prefix_matches_what_the_workflow_publishes():
    # The workflow builds its tag as segqueue-v$VERSION. If this constant moves,
    # every installed client stops seeing updates, silently.
    assert TAG_PREFIX == "segqueue-v"


def test_describe_is_short_and_never_raises():
    assert describe(_release("segqueue-v0.3.0")) == "0.3.0"
    assert describe({"tag_name": "segqueue-v0.3.0", "name": "Logo and updater"}) \
        == "0.3.0 -- Logo and updater"
    assert describe({}) == "?"


# -------------------------------------------------------------------- archive

def test_archive_members_finds_the_module_and_ignores_the_rest():
    names = [
        "SegQueue/lib/Slicer-5.8/qt-scripted-modules/",
        "SegQueue/lib/Slicer-5.8/qt-scripted-modules/SegQueue.py",
        "SegQueue/lib/Slicer-5.8/qt-scripted-modules/Resources/Icons/SegQueue.png",
        "SegQueue/share/Slicer-5.8/SegQueue.s4ext",
    ]
    members = archive_members(names, "5.8")
    assert "SegQueue/lib/Slicer-5.8/qt-scripted-modules/SegQueue.py" in members
    assert all(not m.endswith("/") for m in members)
    assert not any("share" in m for m in members)


def test_archive_members_is_empty_for_the_wrong_slicer_version():
    names = ["SegQueue/lib/Slicer-5.6/qt-scripted-modules/SegQueue.py"]
    assert archive_members(names, "5.8") == []
