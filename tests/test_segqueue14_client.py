"""The SegQueue14 module's network layer and cache, with no Slicer and no server.

Same stub session as the live client's tests (``test_segqueue_client.py``); what
is asserted here is what makes SegQueue14 a separate client: its routes, its
protocol version on every write and at login, the prelabel asset, its own cache
-- and that the live module's library is still importable beside it.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_SRC = REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.append(str(_SRC))
_EXTENSION14 = REPO / "slicer" / "SegQueue14"
if str(_EXTENSION14) not in sys.path:
    sys.path.insert(0, str(_EXTENSION14))

from SegQueue14Lib import CaseCache, SegQueue14Client, SegQueue14Error  # noqa: E402
from SegQueue14Lib import cache as cache14  # noqa: E402
from test_segqueue_client import FakeResponse, FakeSession, girderError  # noqa: E402

from segqueue14 import PROTOCOL_VERSION, protocol  # noqa: E402


def makeClient(session, url="https://segqueue.example.edu"):
    client = SegQueue14Client(url, session=session, extensionVersion="14.0")
    client.token = "tok"
    return client


def _assignment(**extra):
    row = {"assignmentId": "a1", "caseId": "c1", "caseName": "imagecas_0002",
           "state": "assigned", "hasRegion": True, "hasPrelabel": True,
           "prelabelVersion": "icx14-v1", "sizeBytes": 10, "checksum": "0" * 64}
    row.update(extra)
    return row


def test_every_request_declares_the_segqueue14_protocol():
    session = FakeSession()
    makeClient(session).whoami()
    headers = session.calls[0]["headers"]
    assert headers[protocol.PROTOCOL_HEADER] == str(PROTOCOL_VERSION) == "16"
    assert headers[protocol.CLIENT_VERSION_HEADER] == "14.0"


def test_login_fetches_the_project_with_the_protocol_version():
    session = FakeSession({("GET", "segqueue14/project"): FakeResponse(200, {
        "name": "p", "segments": [{"name": "LAD", "label": 2}], "protocolVersion": 14})})
    project = makeClient(session).project()
    call = session.calls[0]
    assert call["url"].endswith("/api/v1/segqueue14/project")
    assert call["params"] == {"clientProtocol": PROTOCOL_VERSION}
    assert project.segments[0].name == "LAD"


def test_an_out_of_date_module_hears_why_at_login():
    message = protocol.too_old_message(13)
    session = FakeSession({("GET", "segqueue14/project"): girderError(
        protocol.ERR_CLIENT_TOO_OLD, message, status=426, minProtocol=14)})
    with pytest.raises(SegQueue14Error) as caught:
        makeClient(session).project()
    assert caught.value.code == protocol.ERR_CLIENT_TOO_OLD
    assert "Update the SegQueue14 module" in str(caught.value)


def test_next_case_sends_the_protocol_and_reads_the_prelabel_fields():
    session = FakeSession({("POST", "segqueue14/next"): FakeResponse(200, _assignment())})
    info = makeClient(session).nextCase()
    assert session.calls[0]["params"] == {"clientProtocol": PROTOCOL_VERSION}
    assert info.has_prelabel and info.prelabel_version == "icx14-v1"
    assert not info.has_seed


def test_an_empty_queue_is_none():
    session = FakeSession({("POST", "segqueue14/next"): girderError(
        protocol.ERR_QUEUE_EMPTY, "none", status=404)})
    assert makeClient(session).nextCase() is None


def test_my_assignments_are_segqueue14_rows():
    session = FakeSession({("GET", "segqueue14/mine"): FakeResponse(200, [_assignment()])})
    rows = makeClient(session).myAssignments()
    assert isinstance(rows[0], protocol.AssignmentInfo14) and rows[0].has_prelabel


def test_the_prelabel_downloads_under_its_own_extension(tmp_path):
    session = FakeSession({("GET", "asset/prelabel"): FakeResponse(
        200, None, text="x", chunks=[b"\x1f\x8bdata"],
        headers={"Content-Disposition": 'attachment; filename="imagecas_0002.prelabel.nii.gz"'})})
    stem = str(tmp_path / "prelabel")
    path = makeClient(session).downloadAsset("c1", protocol.ASSET_PRELABEL, stem)
    assert path == stem + ".nii.gz"
    assert session.calls[0]["url"].endswith("/segqueue14/case/c1/asset/prelabel")


def test_submit_carries_the_protocol_and_goes_to_segqueue14(tmp_path):
    session = FakeSession({("POST", "submit"): FakeResponse(200, {"submissionId": "s"})})
    meta = protocol.SubmissionMeta(checksum="a" * 64, voxel_counts={"LAD": 1})
    makeClient(session).submit("a1", meta, "f1")
    call = session.calls[0]
    assert call["url"].endswith("/segqueue14/assignment/a1/submit")
    assert call["params"]["clientProtocol"] == PROTOCOL_VERSION


def test_a_missing_required_class_refusal_keeps_its_code():
    session = FakeSession({("POST", "submit"): girderError(
        protocol.ERR_MISSING_REQUIRED, "LCx is empty.", status=400, missing=["LCx"])})
    with pytest.raises(SegQueue14Error) as caught:
        makeClient(session).submit("a1", protocol.SubmissionMeta(), "f1")
    assert caught.value.code == protocol.ERR_MISSING_REQUIRED
    assert caught.value.detail["missing"] == ["LCx"]


def test_every_client_error_carries_a_code_and_detail(tmp_path):
    # An unstructured HTTP failure, and one the client raises itself, both have
    # the two attributes a structured refusal has -- empty, not missing.
    session = FakeSession({("GET", "user/me"): FakeResponse(
        502, None, text="Bad gateway")})
    with pytest.raises(SegQueue14Error) as caught:
        makeClient(session).whoami()
    assert (caught.value.code, caught.value.detail) == (None, {})
    assert str(caught.value) == "Bad gateway (HTTP 502)"

    with pytest.raises(SegQueue14Error) as caught:
        makeClient(FakeSession()).addCaseNote("c1", "   ")
    assert (caught.value.code, caught.value.detail) == (None, {})
    assert caught.value.args == ("There is nothing to post.",)


def test_review_routes_are_under_segqueue14(tmp_path):
    session = FakeSession()
    client = makeClient(session)
    client.reviewQueue()
    client.caseOverview()
    client.downloadReviewFile("s1", "download", str(tmp_path / "x"))
    client.downloadCaseAsset("c1", protocol.ASSET_REFERENCE, str(tmp_path / "r"))
    urls = [c["url"] for c in session.calls]
    assert all("/api/v1/segqueue14/" in u for u in urls), urls
    assert urls[2].endswith("/segqueue14/review/s1/download")
    assert urls[3].endswith("/segqueue14/review/case/c1/asset/reference")


def test_the_cache_is_its_own(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert cache14.defaultRoot().endswith(str(Path(".segqueue14") / "cases"))
    assert cache14.MANIFEST_NAME == "segqueue14.json"
    cache = CaseCache(str(tmp_path / "c"))
    manifest = cache.open(protocol.AssignmentInfo14.from_dict(_assignment()))
    assert manifest["assignmentId"] == "a1"
    assert (Path(cache.caseDir("a1")) / "segqueue14.json").is_file()


# The SegQueue14 cache is a separate copy of the live one, so the rules the live
# cache's tests pin are checked against this copy too.


def _info(assignmentId="a1", **extra):
    return protocol.AssignmentInfo14.from_dict(_assignment(assignmentId=assignmentId, **extra))


def test_reopening_a_segqueue14_case_keeps_its_time_and_refreshes_its_attempt(tmp_path):
    cache = CaseCache(str(tmp_path))
    cache.open(_info())
    assert cache.addElapsed("a1", 600) == 600
    cache.open(_info(attempt=2))
    assert cache.elapsed("a1") == 600
    assert cache.manifest("a1")["attempt"] == 2


def test_the_segqueue14_cache_holds_one_case_and_purges_the_oldest(tmp_path):
    cache = CaseCache(str(tmp_path), maxCases=1)
    cache.open(_info("a1"))
    (tmp_path / "case-a1" / "big.nii.gz").write_bytes(b"x" * 5000)
    cache.open(_info("a2"))
    assert cache.assignmentIds() == ["a2"]
    assert cache.purge("a2") >= 0 and cache.assignmentIds() == []


def test_a_submitted_segqueue14_case_is_not_resumable(tmp_path):
    cache = CaseCache(str(tmp_path), maxCases=5)
    cache.open(_info("a1"))
    cache.open(_info("a2"))
    cache.update("a1", submitted=True)
    assert [m["assignmentId"] for m in cache.resumable()] == ["a2"]
    assert cache.purgeAll() >= 0 and cache.assignmentIds() == []


def test_a_corrupt_segqueue14_manifest_reads_as_absent(tmp_path):
    cache = CaseCache(str(tmp_path))
    cache.open(_info())
    Path(cache.manifestPath("a1")).write_text("{ not json")
    assert cache.manifest("a1") is None
    assert cache.update("a1", volumePath="x") is None
    assert cache.elapsed("a1") == 0.0


def test_the_segqueue14_cache_refuses_a_download_that_will_not_fit(tmp_path):
    cache = CaseCache(str(tmp_path))
    cache.freeBytes = lambda: 100 * 1024 * 1024
    with pytest.raises(cache14.CacheError, match="free disk space"):
        cache.checkRoomFor(400 * 1024 * 1024)
    cache.freeBytes = lambda: None
    cache.checkRoomFor(10 ** 12)


def test_a_hostile_case_name_stays_inside_the_segqueue14_cache(tmp_path):
    cache = CaseCache(str(tmp_path))
    path = cache.volumePath("a1", "../../etc/passwd", suffix=".nii.gz")
    assert Path(path).parent == Path(cache.caseDir("a1"))
    assert Path(path).name == "etc_passwd.nii.gz"


def test_both_libraries_load_side_by_side():
    """Slicer puts both modules' directories on one sys.path."""
    live = REPO / "slicer" / "SegQueue"
    if str(live) not in sys.path:
        sys.path.insert(0, str(live))
    import SegQueue14Lib
    import SegQueueLib

    assert SegQueueLib.SegQueueClient is not SegQueue14Lib.SegQueue14Client
    assert Path(SegQueueLib.__file__).parent.parent.name == "SegQueue"
    assert Path(SegQueue14Lib.__file__).parent.parent.name == "SegQueue14"
    assert SegQueueLib.cache.MANIFEST_NAME != SegQueue14Lib.cache.MANIFEST_NAME


# ------------------------------------------------------------------ downloads
#
# Each download route used to carry its own copy of the chunk loop. These pin
# what every copy did -- bytes, progress, return value, the .part rename and the
# absent-asset answer -- so the shared one is held to the same behaviour.


def _streamed(payload, length=True, **headers):
    if length:
        headers["Content-Length"] = str(len(payload))
    return FakeResponse(200, headers=headers, chunks=[payload[:7], b"", payload[7:]])


def test_a_case_download_writes_the_bytes_and_reports_progress(tmp_path):
    payload = b"volume-bytes" * 10
    session = FakeSession({("GET", "segqueue14/case/c1/download"): _streamed(payload)})
    dest = tmp_path / "case.nii.gz"
    seen = []
    written = makeClient(session).downloadCase(
        "c1", str(dest), progress=lambda done, total: seen.append((done, total)))
    assert written == len(payload) and dest.read_bytes() == payload
    assert not (tmp_path / "case.nii.gz.part").exists()
    assert seen == [(7, len(payload)), (len(payload), len(payload))]


def test_a_truncated_case_download_leaves_nothing_behind(tmp_path):
    session = FakeSession({("GET", "download"): FakeResponse(
        200, headers={"Content-Length": "100"}, chunks=[b"x" * 40])})
    dest = tmp_path / "case.nii.gz"
    with pytest.raises(SegQueue14Error, match="stopped early"):
        makeClient(session).downloadCase("c1", str(dest))
    assert not dest.exists()
    assert not (tmp_path / "case.nii.gz.part").exists()


def test_an_asset_download_reports_progress_without_a_total(tmp_path):
    payload = b"\x1f\x8bseed-bytes"
    session = FakeSession({("GET", "asset/seed"): _streamed(payload)})
    seen = []
    path = makeClient(session).downloadAsset(
        "c1", protocol.ASSET_SEED, str(tmp_path / "seed"),
        progress=lambda done, total: seen.append((done, total)))
    with open(path, "rb") as handle:
        assert handle.read() == payload
    # The asset route never passed Content-Length on to progress.
    assert seen == [(7, 0), (len(payload), 0)]


def test_a_missing_asset_is_none_on_both_asset_routes(tmp_path):
    session = FakeSession({("GET", "asset/seed"): girderError(
        protocol.ERR_NO_ASSET, "none", status=404)})
    client = makeClient(session)
    assert client.downloadAsset("c1", protocol.ASSET_SEED, str(tmp_path / "a")) is None
    assert client.downloadCaseAsset("c1", protocol.ASSET_SEED, str(tmp_path / "b")) is None
    assert not list(tmp_path.iterdir())


def test_any_other_asset_failure_still_raises(tmp_path):
    session = FakeSession({("GET", "asset/seed"): girderError(
        "something_else", "boom", status=500)})
    with pytest.raises(SegQueue14Error):
        makeClient(session).downloadCaseAsset("c1", protocol.ASSET_SEED, str(tmp_path / "b"))


@pytest.mark.parametrize("call", [
    lambda c, p, cb: c.downloadReviewFile("s1", "volume", p, progress=cb),
    lambda c, p, cb: c.downloadCaseVolume("c1", p, progress=cb),
    lambda c, p, cb: c.downloadCaseAsset("c1", protocol.ASSET_REFERENCE, p, progress=cb),
], ids=["review-file", "case-volume", "case-asset"])
def test_reviewer_downloads_write_the_bytes_and_return_the_count(tmp_path, call):
    payload = b"reviewer-copy" * 5
    session = FakeSession()
    session.default = _streamed(payload)
    dest = tmp_path / "out.nii.gz"
    seen = []
    written = call(makeClient(session), str(dest), lambda d, t: seen.append((d, t)))
    assert written == len(payload) and dest.read_bytes() == payload
    assert seen[-1] == (len(payload), len(payload))
    assert session.calls[0]["stream"] is True
