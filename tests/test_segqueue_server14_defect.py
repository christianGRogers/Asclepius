"""Defect cases (protocol 21): a reviewer or admin marks a case defect and it is never
served again until unmarked; the reviewer list searches by name across every page.

Against a real Girder and MongoDB (``needs_mongo``, through ``test_segqueue_server14``'s
fixtures; run in CI's server job, which refuses skips). Synthetic data only.

What is checked: mark/unmark is reviewer or admin only; a defect case is never served
by /next (even as the only servable case) nor hand-assigned, and unmarking restores
it; whoever holds it keeps it and can finish, recall and reopen included; nothing of
the case changes but its defect fields and a note naming no login (counters,
assignments, submissions, scores, files); the benchmark (D43) is refused; the name
search and the defect filter cover every page; the stats and the quality report
count defect cases; the export writes exactly what it wrote before, with a
``defect`` flag in ``read.json`` and the manifest.
"""

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import test_segqueue_server14 as base  # noqa: E402
from test_segqueue_server14 import (  # noqa: E402
    _as,
    _readyProject,
    _refusal,
    _resource,
    _stackOf,
    _submitStack,
    _tree,
)

girder_db = base.girder_db
world = base.world
header = base.header

pytestmark = pytest.mark.needs_mongo

#: What the module of this release speaks; 17 is the oldest still accepted.
PROTOCOL = 21
REASON = "Truncated scan: the RCA leaves the field of view"
DEFECT_FIELDS = {"defect", "defectReason", "defectBy", "defectAt", "defectHistory",
                 "updated"}


def _case(name):
    from girder_segqueue14.models import Case14

    return Case14().findOne({"name": name})


def _reload(case):
    from girder_segqueue14.models import Case14

    return Case14().load(case["_id"], force=True)


def _mark(api, who, case, reason=REASON):
    _as(who)
    return api.markDefect(caseId=str(case["_id"]), reason=reason)


def _unmark(api, who, case):
    _as(who)
    return api.unmarkDefect(caseId=str(case["_id"]))


def _onlyServable(name):
    """Retire every case but ``name``, so it is the only one /next could serve."""
    from girder_segqueue14.models import Case14

    Case14().collection.update_many({"name": {"$ne": name}}, {"$set": {"retired": True}})


def _whole(np):
    from segqueue14 import labels

    tree = (_tree(np) > 0).astype(np.uint8)
    return _stackOf(np, {name: tree for name in labels.NAMES})


def _reviewEverything():
    from girder.models.setting import Setting

    Setting().set("segqueue14.policy", {"training_gate_cases": 0, "base_review_rate": 1.0,
                                        "trusted_review_rate": 1.0})


def _snapshot(case):
    """Everything about a case but its defect fields: the case document, and its
    assignments, submissions (scores included), reviews and stored files."""
    from girder.models.file import File
    from girder_segqueue14.models import Assignment14, Review14, Submission14

    doc = {k: v for k, v in _reload(case).items() if k not in DEFECT_FIELDS}
    assignments = sorted(Assignment14().find({"caseId": case["_id"]}), key=lambda a: a["_id"])
    submissions = sorted(Submission14().find({"caseId": case["_id"]}), key=lambda s: s["_id"])
    reviews = sorted(Review14().find({"submissionId": {"$in": [s["_id"] for s in submissions]}}),
                     key=lambda r: r["_id"])
    files = [File().load(s["fileId"], force=True) for s in submissions]
    return json.dumps([doc, assignments, submissions, reviews, files], default=str,
                      sort_keys=True)


# ---------------------------------------------------------------- who may mark


def test_only_a_reviewer_or_admin_marks_and_unmarks(world):
    _readyProject(world)
    api = _resource()
    case = _case("imagecas_0001")
    for who in ("anna", "bobby"):
        err = _refusal(_mark, api, world.people[who], case)
        assert err.code == 403 and err.extra["segqueueError"] == "not_a_reviewer"
        assert not _reload(case).get("defect")

    marked = _mark(api, world.people["revy"], case)
    assert marked["changed"] and marked["defect"] and marked["defectReason"] == REASON
    assert marked["defectBy"] == "revy" and marked["defectAt"] and marked["holders"] == 0
    doc = _reload(case)
    assert doc["defect"] is True and doc["defectBy"] == world.people["revy"]["_id"]
    assert doc["defectReason"] == REASON and doc["defectAt"] is not None

    err = _refusal(_unmark, api, world.people["anna"], case)
    assert err.code == 403 and _reload(case)["defect"] is True

    # Marking again changes nothing; the admin unmarks; unmarking again changes nothing.
    again = _mark(api, world.admin, case, reason="another")
    assert again["changed"] is False and again["defectReason"] == REASON
    gone = _unmark(api, world.admin, case)
    assert gone["changed"] and gone["defect"] is False and gone["defectReason"] == ""
    doc = _reload(case)
    assert doc["defect"] is False and "defectBy" not in doc and "defectReason" not in doc
    assert _unmark(api, world.admin, case)["changed"] is False
    history = doc["defectHistory"]
    assert [(h["defect"], h["by"]) for h in history] == [
        (True, world.people["revy"]["_id"]), (False, world.admin["_id"])]
    assert history[0]["reason"] == REASON


def test_the_reason_is_optional_one_line_and_capped(world):
    from segqueue14 import protocol

    _readyProject(world)
    api = _resource()
    case = _case("imagecas_0002")
    assert _mark(api, world.people["revy"], case, reason="")["defectReason"] == ""
    _unmark(api, world.people["revy"], case)
    long = "  motion\n artefact " + "x" * 400
    got = _mark(api, world.people["revy"], case, reason=long)["defectReason"]
    assert got.startswith("motion artefact x") and "\n" not in got
    assert len(got) == protocol.DEFECT_REASON_MAX_CHARS


def test_the_case_note_names_no_login(world):
    from girder_segqueue14.models import Note14

    _readyProject(world)
    api = _resource()
    case = _case("imagecas_0003")
    _mark(api, world.people["revy"], case)
    _unmark(api, world.people["revy"], case)
    notes = [n["text"] for n in Note14().forCase(case["_id"])]
    assert len(notes) == 2
    assert notes[0].startswith("Marked defect by a reviewer: " + REASON)
    assert notes[1].startswith("Defect mark removed")
    for text in notes:
        for login in ("revy", "admin", "anna", "bobby", "cathy"):
            assert login not in text


def test_the_benchmark_cannot_be_marked(world):
    from girder_segqueue14.models import Case14

    from segqueue14 import protocol

    _readyProject(world)
    api = _resource()
    case = _case("imagecas_0004")
    Case14().collection.update_one({"_id": case["_id"]}, {"$set": {"benchmark": True}})
    for who in (world.people["revy"], world.admin):
        err = _refusal(_mark, api, who, case)
        assert err.code == 400 and err.extra["segqueueError"] == protocol.ERR_DEFECT_BENCHMARK
        assert err.extra["message"] == protocol.DEFECT_BENCHMARK_MESSAGE
        assert "benchmark" in err.extra["message"]
    doc = _reload(case)
    assert not doc.get("defect") and not doc.get("defectHistory")
    # The model refuses it too, whoever calls it.
    assert Case14().setDefect(doc, world.admin, on=True) is None
    assert not _reload(case).get("defect")


# -------------------------------------------------------------- never served


@pytest.mark.parametrize("clientProtocol", [17, 20, PROTOCOL])
def test_a_defect_case_is_never_served_even_when_it_is_the_only_one(world, clientProtocol):
    _readyProject(world)
    api = _resource()
    case = _case("imagecas_0005")
    _onlyServable("imagecas_0005")
    _mark(api, world.people["revy"], case)
    before = _snapshot(case)

    for who in ("anna", "bobby", "cathy"):
        _as(world.people[who])
        err = _refusal(api.nextCase, clientProtocol=clientProtocol)
        assert err.code == 404 and err.extra["segqueueError"] == "queue_empty"
    assert _snapshot(case) == before, "asking for it changed nothing"

    _unmark(api, world.people["revy"], case)
    _as(world.people["anna"])
    info = api.nextCase(clientProtocol=clientProtocol)
    assert info["caseId"] == str(case["_id"]), "unmarked, it is served again"
    assert _reload(case)["activeCount"] == 1


def test_next_skips_a_defect_case_for_the_next_one_in_serve_order(world):
    from girder_segqueue14.models import Case14

    _readyProject(world)
    api = _resource()
    first = Case14().candidates(world.people["anna"]["_id"], limit=2)
    first, second = list(first)
    _mark(api, world.people["revy"], first)
    _as(world.people["anna"])
    assert api.nextCase(clientProtocol=PROTOCOL)["caseId"] == str(second["_id"])
    assert all(c["_id"] != first["_id"]
               for c in Case14().candidates(world.people["bobby"]["_id"], limit=100))


def test_a_defect_case_cannot_be_hand_assigned_until_unmarked(world):
    from segqueue14 import protocol

    _readyProject(world)
    api = _resource()
    case = _case("imagecas_0006")
    _mark(api, world.people["revy"], case)
    _as(world.people["revy"])
    err = _refusal(api.assignCase, caseId=str(case["_id"]),
                   userId=str(world.people["anna"]["_id"]))
    assert err.code == 409 and err.extra["segqueueError"] == protocol.ERR_CASE_DEFECT
    assert _reload(case)["activeCount"] == 0
    _unmark(api, world.people["revy"], case)
    _as(world.people["revy"])
    got = api.assignCase(caseId=str(case["_id"]), userId=str(world.people["anna"]["_id"]))
    assert got["annotator"] == "anna"


# ----------------------------------------------------- current holders keep it


def test_a_holder_keeps_the_case_and_finishes_and_nothing_else_changes(world, header):
    import numpy as np
    from girder_segqueue14.models import Assignment14, Note14

    _readyProject(world)
    _reviewEverything()
    api = _resource()
    _onlyServable("imagecas_0001")
    case = _case("imagecas_0001")
    _as(world.people["anna"])
    info = api.nextCase(clientProtocol=PROTOCOL)
    assert info["caseId"] == str(case["_id"])
    before = _snapshot(case)
    notes = Note14().forCase(case["_id"])

    marked = _mark(api, world.people["revy"], case)
    assert marked["holders"] == 1, "the confirmation says how many hold it"
    assert _snapshot(case) == before, "marking changed nothing but the defect fields"
    assert len(Note14().forCase(case["_id"])) == len(notes) + 1

    # She still has it, downloads it and submits it.
    _as(world.people["anna"])
    assert [a["assignmentId"] for a in api.listMine(includeFinished=False)] == [
        info["assignmentId"]]
    sent = _submitStack(world, api, world.people["anna"], info, _whole(np),
                        clientProtocol=PROTOCOL)
    assignment = Assignment14().load(info["assignmentId"], force=True)
    assert assignment["state"] == "submitted"

    # Her own read stays reachable: she recalls it and resubmits.
    header(PROTOCOL)
    _as(world.people["anna"])
    page = api.listMySubmissions(limit=20, offset=0)
    row = next(r for r in page["items"] if r["assignmentId"] == info["assignmentId"])
    assert row["canRecall"]
    reopened = api.recall(assignmentId=info["assignmentId"], clientProtocol=PROTOCOL)
    assert reopened["startFromOwn"] and reopened["recalled"]
    _as(world.people["anna"])
    again = _submitStack(world, api, world.people["anna"], reopened, _whole(np),
                         clientProtocol=PROTOCOL)
    assert again["submissionId"] != sent["submissionId"]

    # A reviewer approves it as usual; the counters move as for any case.
    _as(world.people["revy"])
    api.claim(submissionId=again["submissionId"])
    api.verdict(submissionId=again["submissionId"], verdict="approve")
    doc = _reload(case)
    assert doc["defect"] is True
    assert doc["activeCount"] == 0 and doc["approvedCount"] == 1


def test_the_admin_reopen_still_works_on_a_defect_case(world, header):
    import numpy as np
    from girder_segqueue14 import reopen
    from girder_segqueue14.models import Assignment14, Submission14

    _readyProject(world)
    _reviewEverything()
    api = _resource()
    _onlyServable("imagecas_0002")
    case = _case("imagecas_0002")
    _as(world.people["anna"])
    info = api.nextCase(clientProtocol=PROTOCOL)
    sent = _submitStack(world, api, world.people["anna"], info, _whole(np),
                        clientProtocol=PROTOCOL)
    _mark(api, world.people["revy"], case)

    assignment = Assignment14().load(info["assignmentId"], force=True)
    submission = Submission14().load(sent["submissionId"], force=True)
    assert reopen.reopenOne(assignment, submission) is not None
    header(PROTOCOL)
    _as(world.people["anna"])
    served = api.nextCase(clientProtocol=PROTOCOL)
    assert served["assignmentId"] == info["assignmentId"] and served["startFromOwn"]
    assert _reload(case)["defect"] is True


def test_unmarking_changes_nothing_but_the_defect_fields(world):
    _readyProject(world)
    api = _resource()
    case = _case("imagecas_0007")
    _as(world.people["cathy"])
    _onlyServable("imagecas_0007")
    api.nextCase(clientProtocol=PROTOCOL)
    before = _snapshot(case)
    counters = {k: _reload(case)[k] for k in ("activeCount", "approvedCount",
                                              "assignedUserIds", "replicasWanted")}
    _mark(api, world.people["revy"], case)
    _unmark(api, world.people["revy"], case)
    assert _snapshot(case) == before
    assert {k: _reload(case)[k] for k in counters} == counters


# ------------------------------------------------------- the reviewer list


def test_search_covers_every_page_and_the_defect_filter(world):
    _readyProject(world)
    api = _resource()
    _as(world.people["revy"])
    every = api.listCases(name="", defect=False, limit=100,
                          offset=0)
    assert len(every) >= 12
    last = every[-1]["caseName"]

    # The last case by name is on the last two-row page, and a search finds it on
    # the first.
    hit = api.listCases(name=last[-4:].upper(), defect=False,
                        limit=2, offset=0)
    assert [r["caseName"] for r in hit] == [last]
    some = api.listCases(name=" IMAGECAS_001 ", defect=False,
                         limit=2, offset=0)
    rest = api.listCases(name="imagecas_001", defect=False,
                         limit=2, offset=2)
    assert [r["caseName"] for r in some + rest] == [
        "imagecas_0010", "imagecas_0011", "imagecas_0012"]
    # A literal substring, not a pattern.
    for literal in (".", "imagecas_00.1", "[0-9]", "*"):
        assert api.listCases(name=literal, defect=False,
                             limit=50, offset=0) == []

    for name in ("imagecas_0003", "imagecas_0011"):
        _mark(api, world.people["revy"], _case(name))
    _as(world.people["revy"])
    defect = api.listCases(name="", defect=True, limit=1,
                           offset=1)
    assert [r["caseName"] for r in defect] == ["imagecas_0011"], "paged in the query"
    rows = api.listCases(name="", defect=True, limit=50,
                         offset=0)
    assert [r["caseName"] for r in rows] == ["imagecas_0003", "imagecas_0011"]
    assert all(r["defect"] and r["defectReason"] == REASON and r["defectBy"] == "revy"
               and r["defectAt"] for r in rows)
    both = api.listCases(name="0011", defect=True, limit=50,
                         offset=0)
    assert [r["caseName"] for r in both] == ["imagecas_0011"]
    plain = next(r for r in api.listCases(name="0001",
                                          defect=False, limit=5, offset=0))
    assert plain["defect"] is False and plain["defectReason"] == ""
    assert plain["defectAt"] is None and plain["defectBy"] == "" and plain["holders"] == 0

    _as(world.people["anna"])
    err = _refusal(api.listCases, name="x", defect=False,
                   limit=5, offset=0)
    assert err.code == 403


# ------------------------------------------------------------------ reporting


def test_stats_and_the_quality_report_count_defect_cases(world):
    from girder_segqueue14 import report

    from segqueue14.quality import render

    _readyProject(world)
    api = _resource()
    _as(world.admin)
    before = api.stats()
    assert before["defect"] == 0
    for name in ("imagecas_0001", "imagecas_0002"):
        _mark(api, world.people["revy"], _case(name))
    _as(world.admin)
    after = api.stats()
    assert after["defect"] == 2
    assert {k: v for k, v in after.items() if k != "defect"} == {
        k: v for k, v in before.items() if k != "defect"}, "nothing else moves"

    quality = report.collect(world.db, limit=0)
    assert quality["totals"]["defect"] == 2
    assert any("2 of them marked defect" in line for line in render(quality, []))


def test_the_export_writes_the_same_reads_with_a_defect_flag(world, tmp_path):
    import numpy as np
    from girder_segqueue14 import export, scoring

    _readyProject(world)
    api = _resource()
    reads = []
    for who in ("anna", "bobby"):
        _as(world.people[who])
        info = api.nextCase(clientProtocol=PROTOCOL)
        base._submit(world, api, world.people[who], info, _tree(np))
        reads.append(info["caseName"])
    scoring.runOnce()

    plainOut = tmp_path / "plain"
    assert export.main(["--out", str(plainOut)]) == 0
    plain = json.loads((plainOut / "manifest.json").read_text())
    assert plain["source"]["defect_cases"] == {}
    for name in reads:
        info = json.loads((plainOut / name / "read.json").read_text())
        assert info["defect"] is False and info["defectReason"] is None

    _mark(api, world.people["revy"], _case(reads[0]))
    flaggedOut = tmp_path / "flagged"
    assert export.main(["--out", str(flaggedOut)]) == 0
    flagged = json.loads((flaggedOut / "manifest.json").read_text())
    assert flagged["source"]["defect_cases"] == {reads[0]: REASON}
    assert json.loads((flaggedOut / reads[0] / "read.json").read_text())["defect"] is True
    assert json.loads((flaggedOut / reads[0] / "read.json").read_text())[
        "defectReason"] == REASON
    assert json.loads((flaggedOut / reads[1] / "read.json").read_text())["defect"] is False

    # What is exported is unchanged: the same cases, the same files, the same bytes
    # (read.json aside, which now says defect).
    def data(manifest):
        return [(c["case"], [f for f in c["files"] if not f["path"].endswith("read.json")])
                for c in manifest["cases"]]

    assert data(plain) == data(flagged)
    assert [c["case"] for c in plain["cases"]] == sorted(reads)
    for name in reads:
        a = sorted(p.relative_to(plainOut / name).as_posix()
                   for p in (plainOut / name).rglob("*"))
        b = sorted(p.relative_to(flaggedOut / name).as_posix()
                   for p in (flaggedOut / name).rglob("*"))
        assert a == b
