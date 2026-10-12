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
    assert headers[protocol.PROTOCOL_HEADER] == str(PROTOCOL_VERSION) == "14"
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
