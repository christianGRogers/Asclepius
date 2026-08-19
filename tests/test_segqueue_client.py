"""The Slicer extension's network layer and local cache, with no Slicer in sight.

These are the two parts of the client most likely to be wrong and least likely to
be exercised by hand: a dropped upload halfway through a 20 MB segmentation, a
truncated download that still loads, a cache that quietly keeps every case a
student ever opened. All of it is reachable here because ``SegQueueLib`` was
written free of Slicer, Qt and VTK imports -- which is the whole reason for that
constraint.

The server is a stub session rather than a live Girder, so these tests assert the
*client's* behaviour: what it sends, what it does with what comes back, and what
it leaves on disk. Agreement with the real server is the integration suite's job
(``test_segqueue_server.py``), and agreement about the wire format is
``test_segqueue_protocol.py``'s.
"""

import json
import os
import sys
from pathlib import Path

import pytest

from segqueue import PROTOCOL_VERSION, protocol

# The extension is not an installable package -- Slicer loads it from a path --
# so the tests put its directory on sys.path the same way Slicer does.
_EXTENSION = Path(__file__).resolve().parents[1] / "slicer" / "SegQueue"
if str(_EXTENSION) not in sys.path:
    sys.path.insert(0, str(_EXTENSION))

from SegQueueLib import CacheError, CaseCache, SegQueueClient, SegQueueError  # noqa: E402
from SegQueueLib.client import UPLOAD_CHUNK_BYTES  # noqa: E402

# --------------------------------------------------------------------- stubs


class FakeResponse:
    def __init__(self, status_code=200, body=None, text="", headers=None, chunks=None,
                 reason="OK"):
        self.status_code = status_code
        self._body = body
        self.text = text if text else (json.dumps(body) if body is not None else "")
        self.headers = headers or {}
        self.reason = reason
        self._chunks = chunks or []

    @property
    def content(self):
        return self.text.encode()

    def json(self):
        if self._body is None:
            raise ValueError("not JSON")
        return self._body

    def iter_content(self, chunk_size=1):
        yield from self._chunks


class FakeSession:
    """Answers requests from a scripted list, recording what it was asked."""

    def __init__(self, responses=None):
        #: ``(method, path_suffix) -> FakeResponse`` or a callable taking the call.
        self.responses = responses or {}
        self.calls = []
        self.default = FakeResponse(200, {})

    def request(self, method, url, headers=None, stream=False, **kwargs):
        call = {"method": method, "url": url, "headers": headers or {},
                "stream": stream}
        call.update(kwargs)
        self.calls.append(call)
        # Suffix match before substring match, because "/file" is a prefix of
        # "/file/chunk" and getting that backwards silently routes every chunk
        # to the upload-init stub.
        for test in (str.endswith, str.__contains__):
            for (wantMethod, fragment), response in self.responses.items():
                if method == wantMethod and test(url, fragment):
                    return response(call) if callable(response) else response
        return self.default

    def pathsFor(self, method):
        return [c["url"] for c in self.calls if c["method"] == method]


def girderError(code, message="no", status=409, **detail):
    """A refusal shaped exactly as Girder serialises a ``RestException``."""
    return FakeResponse(status, {
        "message": message,
        "type": "rest",
        "extra": protocol.error_body(code, message, **detail),
    })


def makeClient(session, url="https://segqueue.example.edu"):
    client = SegQueueClient(url, session=session, extensionVersion="9.9")
    client.token = "tok"
    return client


# ------------------------------------------------------------------ plumbing


def test_the_api_root_is_appended_once():
    assert SegQueueClient("https://host").serverUrl == "https://host/api/v1"
    assert SegQueueClient("https://host/").serverUrl == "https://host/api/v1"
    # Someone will paste the URL from their browser's address bar, already
    # including /api/v1, and doubling it produces a 404 with no clue why.
    assert SegQueueClient("https://host/api/v1").serverUrl == "https://host/api/v1"


def test_every_request_declares_the_protocol_and_the_client_version():
    session = FakeSession()
    client = makeClient(session)
    client.whoami()

    headers = session.calls[0]["headers"]
    assert headers[protocol.PROTOCOL_HEADER] == str(PROTOCOL_VERSION)
    assert headers[protocol.CLIENT_VERSION_HEADER] == "9.9"
    assert headers["Girder-Token"] == "tok"


def test_an_anonymous_client_sends_no_token_header():
    session = FakeSession()
    SegQueueClient("https://host", session=session).whoami()
    assert "Girder-Token" not in session.calls[0]["headers"]


def test_login_stores_the_token_and_the_user():
    session = FakeSession({("GET", "user/authentication"): FakeResponse(200, {
        "authToken": {"token": "abc123"},
        "user": {"login": "student01"},
    })})
    client = SegQueueClient("https://host", session=session)
    user = client.login("student01", "hunter2")

    assert client.token == "abc123"
    assert client.loggedIn
    assert user["login"] == "student01"
    # Basic auth, over TLS, exactly as Girder expects -- and the password is
    # never put in a URL where a proxy log would keep it.
    assert session.calls[0]["auth"] == ("student01", "hunter2")


def test_logout_forgets_everything():
    client = makeClient(FakeSession())
    client.logout()
    assert not client.loggedIn
    assert client.user is None


def test_a_girder_wrapped_refusal_keeps_its_code():
    session = FakeSession({("POST", "segqueue/next"): girderError(
        protocol.ERR_AT_LIMIT, "You already have a case.", status=409, limit=1)})
    client = makeClient(session)

    with pytest.raises(SegQueueError) as caught:
        client._json("POST", protocol.path(protocol.NEXT))
    assert caught.value.code == protocol.ERR_AT_LIMIT
    assert caught.value.detail["limit"] == 1
    assert "already have a case" in str(caught.value)


def test_an_expired_session_says_so_in_words_a_student_can_act_on():
    session = FakeSession({("GET", "user/me"): FakeResponse(
        401, {"message": "Read access denied."}, reason="Unauthorized")})
    with pytest.raises(SegQueueError) as caught:
        makeClient(session).whoami()
    assert "log in again" in str(caught.value).lower()


def test_an_unreachable_server_suggests_the_vpn():
    import requests

    class Dead(FakeSession):
        def request(self, *args, **kwargs):
            raise requests.ConnectionError("no route to host")

    with pytest.raises(SegQueueError) as caught:
        makeClient(Dead()).whoami()
    message = str(caught.value)
    assert "VPN" in message
    assert "segqueue.example.edu" in message


def test_html_from_a_captive_portal_is_not_reported_as_a_json_bug():
    session = FakeSession({("GET", "segqueue/project"): FakeResponse(
        200, body=None, text="<html>Please sign in to the campus network</html>")})
    with pytest.raises(SegQueueError) as caught:
        makeClient(session).project()
    assert "captive portal" in str(caught.value)


# --------------------------------------------------------------------- queue


def test_an_empty_queue_is_a_return_value_not_an_exception():
    session = FakeSession({("POST", "segqueue/next"): girderError(
        protocol.ERR_QUEUE_EMPTY, "Nothing left.", status=404)})
    assert makeClient(session).nextCase() is None


def test_any_other_refusal_from_next_still_raises():
    session = FakeSession({("POST", "segqueue/next"): girderError(
        protocol.ERR_QUOTA, "You have used your quota.", status=403)})
    with pytest.raises(SegQueueError) as caught:
        makeClient(session).nextCase()
    assert caught.value.code == protocol.ERR_QUOTA


def test_next_case_comes_back_as_an_assignment():
    session = FakeSession({("POST", "segqueue/next"): FakeResponse(200, {
        "assignmentId": "a1", "caseId": "c1", "caseName": "s0042",
        "state": "assigned", "attempt": 1, "sizeBytes": 12345,
        "checksum": "ff" * 32,
    })})
    assignment = makeClient(session).nextCase()
    assert assignment.case_name == "s0042"
    assert assignment.size_bytes == 12345
    # Blind means blind: the server omits `kind` for annotators and the client
    # must not invent one.
    assert assignment.kind is None


def test_a_heartbeat_failure_never_reaches_the_annotator():
    session = FakeSession({("POST", "heartbeat"): FakeResponse(
        503, {"message": "down for maintenance"})})
    # Segmenting must not stop because a status ping failed.
    assert makeClient(session).heartbeat("a1") is False


# ------------------------------------------------------------------ download


def test_download_writes_the_file_and_leaves_no_part_behind(tmp_path):
    payload = b"volume-bytes" * 100
    session = FakeSession({("GET", "download"): FakeResponse(
        200, headers={"Content-Length": str(len(payload))},
        chunks=[payload[:50], payload[50:]])})
    dest = tmp_path / "case.nrrd"

    seen = []
    written = makeClient(session).downloadCase(
        "c1", str(dest), progress=lambda done, total: seen.append((done, total)))

    assert written == len(payload)
    assert dest.read_bytes() == payload
    assert not (tmp_path / "case.nrrd.part").exists()
    assert seen[-1] == (len(payload), len(payload))


def test_a_truncated_download_is_deleted_rather_than_left_to_look_complete(tmp_path):
    # This is the failure requirement N3 is really about. A short NRRD often
    # loads fine and is simply missing its last slices; if it survived as
    # `case.nrrd` the next step would hash it, fail, and blame the network for
    # something already on disk.
    session = FakeSession({("GET", "download"): FakeResponse(
        200, headers={"Content-Length": "1000"}, chunks=[b"x" * 400])})
    dest = tmp_path / "case.nrrd"

    with pytest.raises(SegQueueError) as caught:
        makeClient(session).downloadCase("c1", str(dest))

    assert "stopped early" in str(caught.value)
    assert not dest.exists()
    assert not (tmp_path / "case.nrrd.part").exists()


def test_a_redownload_replaces_the_previous_file(tmp_path):
    dest = tmp_path / "case.nrrd"
    dest.write_bytes(b"stale")
    session = FakeSession({("GET", "download"): FakeResponse(
        200, headers={"Content-Length": "5"}, chunks=[b"fresh"])})

    makeClient(session).downloadCase("c1", str(dest))
    assert dest.read_bytes() == b"fresh"


# -------------------------------------------------------------------- upload


def _uploadSession(size, failAt=None, offsetAfterFailure=None):
    """A stub that accepts chunks, optionally failing one of them once."""
    state = {"received": 0, "failed": False}

    def initUpload(call):
        return FakeResponse(200, {"_id": "up1"})

    def chunk(call):
        offset = int(call["params"]["offset"])
        length = len(call["data"])
        if failAt is not None and offset == failAt and not state["failed"]:
            state["failed"] = True
            # The server did in fact store this chunk; the response is what got
            # lost. That is the case worth testing -- naive retry logic sends it
            # twice and corrupts the file.
            state["received"] = offsetAfterFailure
            return FakeResponse(500, {"message": "gateway timeout"})
        state["received"] = offset + length
        if state["received"] >= size:
            return FakeResponse(200, {"_id": "file1", "size": size})
        return FakeResponse(200, {"_id": "up1", "received": state["received"]})

    def offset(call):
        return FakeResponse(200, {"offset": state["received"]})

    return FakeSession({
        ("POST", "/file"): initUpload,
        ("POST", "file/chunk"): chunk,
        ("GET", "file/offset"): offset,
    }), state


def test_upload_sends_the_whole_file_in_order(tmp_path):
    size = UPLOAD_CHUNK_BYTES + 1024
    path = tmp_path / "submission.seg.nrrd"
    path.write_bytes(b"s" * size)
    session, _state = _uploadSession(size)

    file = makeClient(session).uploadFile(str(path), "folder1")

    assert file["_id"] == "file1"
    offsets = [int(c["params"]["offset"]) for c in session.calls
               if "file/chunk" in c["url"]]
    assert offsets == [0, UPLOAD_CHUNK_BYTES]
    init = next(c for c in session.calls if c["url"].endswith("/file"))
    assert init["params"]["parentId"] == "folder1"
    assert init["params"]["size"] == size
    assert init["params"]["name"] == "submission.seg.nrrd"


def test_a_lost_chunk_response_resumes_from_what_the_server_actually_has(tmp_path):
    size = UPLOAD_CHUNK_BYTES * 2
    path = tmp_path / "submission.seg.nrrd"
    path.write_bytes(b"s" * size)
    # The first chunk lands but the reply is lost. The client must ask, learn the
    # server has 8 MiB, and continue -- not resend the first chunk.
    session, _state = _uploadSession(
        size, failAt=0, offsetAfterFailure=UPLOAD_CHUNK_BYTES)

    file = makeClient(session).uploadFile(str(path), "folder1")

    assert file["_id"] == "file1"
    offsets = [int(c["params"]["offset"]) for c in session.calls
               if "file/chunk" in c["url"]]
    assert offsets == [0, UPLOAD_CHUNK_BYTES]


def test_a_chunk_that_genuinely_failed_is_not_retried_forever(tmp_path):
    size = 1024
    path = tmp_path / "submission.seg.nrrd"
    path.write_bytes(b"s" * size)
    # The server agrees it has nothing, so the chunk really did fail. Spinning
    # here would hang Slicer with no way out; raising surfaces it immediately.
    session, _state = _uploadSession(size, failAt=0, offsetAfterFailure=0)

    with pytest.raises(SegQueueError):
        makeClient(session).uploadFile(str(path), "folder1")


def test_an_upload_the_server_never_confirms_is_not_reported_as_success(tmp_path):
    path = tmp_path / "submission.seg.nrrd"
    path.write_bytes(b"s" * 64)
    session = FakeSession({
        ("POST", "/file"): FakeResponse(200, {"_id": "up1"}),
        ("POST", "file/chunk"): FakeResponse(200, {"_id": "up1", "received": 64}),
    })
    with pytest.raises(SegQueueError) as caught:
        makeClient(session).uploadFile(str(path), "folder1")
    assert "Nothing has been submitted" in str(caught.value)


def test_submit_sends_the_metadata_and_geometry_as_json():
    session = FakeSession({("POST", "submit"): FakeResponse(200, {"ok": True})})
    meta = protocol.SubmissionMeta(
        checksum="ab" * 32, size_bytes=10, annotation_seconds=1800.0,
        voxel_counts={"left_main": 120})

    makeClient(session).submit("a1", meta, "file1",
                               geometry={"source": {"size": [1, 2, 3]}})

    params = session.calls[0]["params"]
    assert params["fileId"] == "file1"
    assert json.loads(params["meta"])["voxelCounts"] == {"left_main": 120}
    assert json.loads(params["geometry"])["source"]["size"] == [1, 2, 3]
    assert params["clientProtocol"] == PROTOCOL_VERSION


# --------------------------------------------------------------------- cache


def assignment(assignmentId="a1", name="s0042", size=1000, attempt=1,
               state="assigned"):
    return protocol.AssignmentInfo(
        assignment_id=assignmentId, case_id="c1", case_name=name, state=state,
        attempt=attempt, size_bytes=size, checksum="ff" * 32)


def test_opening_a_case_creates_one_directory_with_a_manifest(tmp_path):
    cache = CaseCache(str(tmp_path))
    manifest = cache.open(assignment())

    assert manifest["caseName"] == "s0042"
    assert os.path.isfile(cache.manifestPath("a1"))
    assert cache.assignmentIds() == ["a1"]


def test_reopening_a_case_keeps_the_accumulated_time(tmp_path):
    # The crash-resume path. Resetting the clock here would make a student who
    # crashed twice look like they did a coronary tree in five minutes, which is
    # exactly the signal the QA dashboard uses to spot careless work.
    cache = CaseCache(str(tmp_path))
    cache.open(assignment())
    cache.addElapsed("a1", 600)

    cache.open(assignment(attempt=2, state="assigned"))
    assert cache.elapsed("a1") == 600
    assert cache.manifest("a1")["attempt"] == 2


def test_opening_a_second_case_deletes_the_first(tmp_path):
    # The storage-footprint requirement, enforced structurally rather than by
    # asking anyone to tidy up.
    cache = CaseCache(str(tmp_path), maxCases=1)
    cache.open(assignment("a1"))
    (tmp_path / "case-a1" / "big.nrrd").write_bytes(b"x" * 5000)

    cache.open(assignment("a2"))

    assert cache.assignmentIds() == ["a2"]
    assert not (tmp_path / "case-a1").exists()


def test_a_higher_concurrency_limit_keeps_that_many_cases(tmp_path):
    cache = CaseCache(str(tmp_path), maxCases=3)
    for i in range(3):
        cache.open(assignment("a%d" % i))
    assert sorted(cache.assignmentIds()) == ["a0", "a1", "a2"]

    cache.open(assignment("a3"))
    ids = sorted(cache.assignmentIds())
    assert len(ids) == 3
    assert "a3" in ids
    assert "a0" not in ids  # oldest first


def test_debris_with_no_manifest_is_purged_before_real_work(tmp_path):
    cache = CaseCache(str(tmp_path), maxCases=1)
    os.makedirs(str(tmp_path / "case-junk"))
    cache.open(assignment("a1"))
    assert cache.assignmentIds() == ["a1"]


def test_purge_reports_what_it_reclaimed(tmp_path):
    cache = CaseCache(str(tmp_path))
    cache.open(assignment())
    (tmp_path / "case-a1" / "volume.nrrd").write_bytes(b"x" * 4096)

    reclaimed = cache.purge("a1")

    assert reclaimed >= 4096
    assert not (tmp_path / "case-a1").exists()
    assert cache.manifest("a1") is None


def test_purge_all_empties_the_cache(tmp_path):
    cache = CaseCache(str(tmp_path), maxCases=5)
    for i in range(3):
        cache.open(assignment("a%d" % i))
    cache.purgeAll()
    assert cache.assignmentIds() == []


def test_a_submitted_case_is_not_offered_as_resumable_work(tmp_path):
    # Debris from a purge that did not finish. Offering it back would invite a
    # second submission the server would refuse, and the annotator would have no
    # idea why.
    cache = CaseCache(str(tmp_path), maxCases=5)
    cache.open(assignment("a1"))
    cache.open(assignment("a2"))
    cache.update("a1", submitted=True)

    assert [m["assignmentId"] for m in cache.resumable()] == ["a2"]


def test_a_corrupt_manifest_reads_as_absent_rather_than_raising(tmp_path):
    cache = CaseCache(str(tmp_path))
    cache.open(assignment())
    Path(cache.manifestPath("a1")).write_text("{ this is not json")

    assert cache.manifest("a1") is None
    assert cache.update("a1", volumePath="x") is None
    # And the case can still be reopened rather than being permanently stuck.
    assert cache.open(assignment())["caseName"] == "s0042"


def test_a_full_disk_is_refused_before_the_download_starts(tmp_path):
    cache = CaseCache(str(tmp_path))
    cache.freeBytes = lambda: 100 * 1024 * 1024

    with pytest.raises(CacheError) as caught:
        cache.checkRoomFor(400 * 1024 * 1024)
    assert "free disk space" in str(caught.value)

    # Plenty of room: no complaint.
    cache.freeBytes = lambda: 50 * 1024 * 1024 * 1024
    cache.checkRoomFor(400 * 1024 * 1024)


def test_an_unknowable_free_space_does_not_block_work(tmp_path):
    cache = CaseCache(str(tmp_path))
    cache.freeBytes = lambda: None
    cache.checkRoomFor(10 ** 12)  # no exception


def test_a_hostile_case_name_cannot_escape_the_cache(tmp_path):
    # Case names come from the server, but "the server is trusted" is a thin
    # reason to allow ../../ into a path join on a student's laptop.
    cache = CaseCache(str(tmp_path))
    path = cache.volumePath("a1", "../../etc/passwd")
    assert os.path.commonpath([str(tmp_path), os.path.abspath(path)]) == str(tmp_path)
    assert ".." not in os.path.basename(path)


# --------------------------------------------------- case asset filenames


def _assetResponse(disposition, payload=b"mask"):
    headers = {"Content-Length": str(len(payload))}
    if disposition:
        headers["Content-Disposition"] = disposition
    return FakeResponse(200, headers=headers, chunks=[payload])


def test_a_helper_mask_is_saved_under_the_servers_own_extension(tmp_path):
    # Slicer picks its reader from the filename. A NIfTI written as .nrrd
    # downloads and verifies perfectly, then refuses to open.
    session = FakeSession({("GET", "asset/seed"): _assetResponse(
        'attachment; filename="coronary_arteries.nii.gz"')})
    stem = str(tmp_path / "seed")

    path = makeClient(session).downloadAsset("c1", "seed", stem)

    assert path == stem + ".nii.gz"
    assert os.path.isfile(path)


def test_a_server_that_names_an_nrrd_gets_an_nrrd(tmp_path):
    session = FakeSession({("GET", "asset/region"): _assetResponse(
        "attachment; filename=heart.nrrd")})
    path = makeClient(session).downloadAsset("c1", "region", str(tmp_path / "region"))
    assert path.endswith(".nrrd")


def test_a_missing_content_disposition_falls_back_rather_than_failing(tmp_path):
    session = FakeSession({("GET", "asset/seed"): _assetResponse(None)})
    path = makeClient(session).downloadAsset("c1", "seed", str(tmp_path / "seed"))
    assert path.endswith(".nii.gz")


def test_a_stem_that_already_carries_the_extension_is_not_doubled(tmp_path):
    session = FakeSession({("GET", "asset/seed"): _assetResponse(
        'attachment; filename="x.nii.gz"')})
    stem = str(tmp_path / "seed.nii.gz")
    assert makeClient(session).downloadAsset("c1", "seed", stem) == stem


def test_a_case_with_no_such_asset_still_reads_as_absent(tmp_path):
    session = FakeSession({("GET", "asset/seed"): girderError(
        protocol.ERR_NO_ASSET, "This case has no seed mask.", status=404)})
    assert makeClient(session).downloadAsset("c1", "seed", str(tmp_path / "s")) is None
