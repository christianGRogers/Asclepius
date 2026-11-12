"""``segqueue14-reopen`` (#315) against a real Girder and MongoDB.

An annotator's own submitted reads go back into their queue, starting from what
they submitted. Marked ``needs_mongo`` (through ``test_segqueue_server14``'s
fixtures) and run in CI's server job, which refuses skips. Synthetic data only.

The issue's acceptance list: the dry run lists exactly the matching assignments;
``--apply`` reopens them, keeps the old submission, releases a reviewer's claim and
leaves approved, benchmark, other logins' and the partner's assignments alone; the
annotator's next fetch serves them first, starting from her own read with every
class; an older module is told to update; a resubmission replaces the old read in
pairing and in the quality report; ``--apply`` twice is a no-op.
"""

import datetime
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import test_segqueue_server14 as base  # noqa: E402
from test_segqueue_server14 import (  # noqa: E402  (helpers)
    _as,
    _readyProject,
    _refusal,
    _resource,
    _stackOf,
    _submitStack,
    _tree,
    _uploadStack,
)

girder_db = base.girder_db
world = base.world
header = base.header

pytestmark = pytest.mark.needs_mongo

UTC = datetime.timezone.utc
#: The cut-off: midnight US Eastern on 2026-11-09 is 05:00 UTC.
DAY = "2026-11-09"
BEFORE = datetime.datetime(2026, 11, 5, 15, 0, tzinfo=UTC)
JUST_BEFORE = datetime.datetime(2026, 11, 9, 4, 30, tzinfo=UTC)   # 23:30 EST, the 8th
JUST_AFTER = datetime.datetime(2026, 11, 9, 5, 30, tzinfo=UTC)    # 00:30 EST, the 9th


def _backdate(response, when):
    from girder_segqueue14.models import Assignment14, Submission14

    sub = Submission14().load(response["submissionId"], force=True)
    Submission14().collection.update_one({"_id": sub["_id"]}, {"$set": {"created": when}})
    Assignment14().collection.update_one({"_id": sub["assignmentId"]},
                                         {"$set": {"submittedAt": when}})
    return sub


def _reviewEverything():
    from girder.models.setting import Setting

    # Every read waits for a human, so nothing is approved by the sampling roll.
    Setting().set("segqueue14.policy", {"training_gate_cases": 0, "base_review_rate": 1.0,
                                        "trusted_review_rate": 1.0})


def _run(apply):
    from girder_segqueue14 import reopen

    lines = []
    rows = reopen.runReopen("anna", DAY, apply=apply, out=lines.append)
    return rows, lines


def _docs(ids):
    from girder_segqueue14.models import Assignment14

    return {i: Assignment14().load(i, force=True) for i in ids}


def _bytes(download):
    return b"".join(download())


@pytest.fixture
def scene(world):
    """anna: two reads to reopen (one paired with bobby, one claimed by revy), one
    submitted after the cut-off, one approved and one benchmark read; cathy: one read
    before the cut-off. Every class of anna's reads is a whole copy of the tree, so
    the classes overlap everywhere (D26, D39)."""
    import numpy as np
    from girder_segqueue14 import scoring
    from girder_segqueue14.models import Assignment14, Case14, Submission14

    from segqueue14 import labels

    _readyProject(world)
    _reviewEverything()
    queue = _resource()
    anna, bobby, cathy, revy = (world.people[k] for k in ("anna", "bobby", "cathy", "revy"))
    tree = (_tree(np) > 0).astype(np.uint8)
    whole = _stackOf(np, {name: tree for name in labels.NAMES})
    partial = _stackOf(np, {"LAD": tree})

    # The paired case first: only the two-read tier in the queue.
    retired = [c["_id"] for c in Case14().find({"tier": {"$ne": "imagecas-unlabelled"},
                                                "retired": {"$ne": True}})]
    Case14().collection.update_many({"_id": {"$in": retired}}, {"$set": {"retired": True}})
    _as(anna)
    paired = queue.nextCase(clientProtocol=18)
    _as(bobby)
    assert queue.nextCase(clientProtocol=18)["caseId"] == paired["caseId"]
    bobbyInfo = [a for a in Assignment14().find({"userId": bobby["_id"]})][0]
    s = {}
    s["paired"] = _submitStack(world, queue, anna, paired, whole, clientProtocol=18)
    s["bobby"] = _submitStack(world, queue, bobby,
                              {"caseId": paired["caseId"], "caseName": paired["caseName"],
                               "assignmentId": str(bobbyInfo["_id"])},
                              partial, clientProtocol=18)
    Case14().collection.update_many({"_id": {"$in": retired}}, {"$set": {"retired": False}})

    for key in ("claimed", "late", "approved", "benchmark"):
        _as(anna)
        info = queue.nextCase(clientProtocol=18)
        s[key] = _submitStack(world, queue, anna, info, whole, clientProtocol=18)
    _as(cathy)
    s["cathy"] = _submitStack(world, queue, cathy, queue.nextCase(clientProtocol=18), whole,
                              clientProtocol=18)
    assert scoring.runOnce() >= 2
    assert Submission14().load(s["bobby"]["submissionId"], force=True)["autoScore"][
        "duplicate"]["partnerSubmissionId"] == s["paired"]["submissionId"]

    for key in ("paired", "claimed", "approved", "benchmark", "bobby", "cathy"):
        _backdate(s[key], BEFORE)
    _backdate(s["claimed"], JUST_BEFORE)
    _backdate(s["late"], JUST_AFTER)
    _as(revy)
    queue.claim(submissionId=s["claimed"]["submissionId"])
    queue.claim(submissionId=s["approved"]["submissionId"])
    queue.verdict(submissionId=s["approved"]["submissionId"], verdict="approve")
    bench = Submission14().load(s["benchmark"]["submissionId"], force=True)
    Assignment14().collection.update_one({"_id": bench["assignmentId"]},
                                         {"$set": {"kind": "benchmark"}})
    Case14().collection.update_one({"_id": bench["caseId"]}, {"$set": {"benchmark": True}})

    world.s = {k: Submission14().load(v["submissionId"], force=True) for k, v in s.items()}
    world.queue, world.whole, world.tree = queue, whole, tree
    return world


def test_the_dry_run_lists_exactly_the_matching_reads_and_writes_nothing(scene):
    from girder_segqueue14.models import Note14

    s = scene.s
    ids = [sub["assignmentId"] for sub in s.values()]
    before = _docs(ids)
    rows, lines = _run(apply=False)
    assert sorted(r["assignmentId"] for r in rows) == sorted(
        str(s[k]["assignmentId"]) for k in ("paired", "claimed"))
    byId = {r["assignmentId"]: r for r in rows}
    claimed = byId[str(s["claimed"]["assignmentId"])]
    assert claimed["state"] == "under_review" and claimed["reviewer"] == "revy"
    assert claimed["submitted"] == "2026-11-08 23:30 EST"
    paired = byId[str(s["paired"]["assignmentId"])]
    assert paired["state"] == "submitted" and paired["reviewer"] is None
    assert any("dry run" in line for line in lines)
    assert _docs(ids) == before
    assert Note14().collection.count_documents({"text": {"$regex": "Reopened"}}) == 0


def test_apply_reopens_them_keeps_the_reads_and_touches_nothing_else(scene):
    from girder_segqueue14.models import Assignment14, Note14, Submission14

    s = scene.s
    untouched = [s[k]["assignmentId"] for k in ("late", "approved", "benchmark", "bobby",
                                                 "cathy")]
    before = _docs(untouched)
    bobbyRead = Submission14().load(s["bobby"]["_id"], force=True)

    rows, _ = _run(apply=True)
    assert sorted(r["done"] for r in rows) == ["reopened", "reopened"]
    for key in ("paired", "claimed"):
        a = Assignment14().load(s[key]["assignmentId"], force=True)
        assert a["state"] == "assigned" and a["attempt"] == 2
        assert a["submittedAt"] is None and a["downloadedAt"] is None
        assert a["deadline"].replace(tzinfo=UTC) > datetime.datetime.now(UTC)
        assert a["startFileId"] == s[key]["fileId"] and a.get("reviewerId") is None
        old = Submission14().load(s[key]["_id"], force=True)
        assert old is not None and old["fileId"] == s[key]["fileId"], "kept as history"
        assert old["reopenedAt"] is not None
        notes = [n["text"] for n in Note14().forCase(s[key]["caseId"])]
        assert "Reopened for the annotator's own revision at the lead's request (#315)." \
            in notes
        assert not any("anna" in n for n in notes), "blind stays blind"
    assert _docs(untouched) == before
    assert Submission14().load(s["bobby"]["_id"], force=True) == bobbyRead

    # The reviewer's claim is gone: approving the old read is refused, now and after.
    _as(scene.people["revy"])
    for sid in (s["claimed"]["_id"], s["paired"]["_id"]):
        assert _refusal(scene.queue.verdict, submissionId=str(sid),
                        verdict="approve").code == 409
        assert _refusal(scene.queue.claim, submissionId=str(sid)).code == 409

    # Twice is a no-op.
    after = _docs([s[k]["assignmentId"] for k in s])
    rows, _ = _run(apply=True)
    assert rows == []
    assert _docs([s[k]["assignmentId"] for k in s]) == after
    assert Note14().collection.count_documents({"text": {"$regex": "Reopened"}}) == 2


def test_she_gets_them_first_from_her_own_read_and_an_old_module_is_told(scene, header):
    from girder.models.file import File
    from girder.models.user import User
    from girder_segqueue14.constants import QUOTA_FIELD
    from girder_segqueue14.models import Assignment14

    from segqueue14 import labelfile, labels

    s, queue = scene.s, scene.queue
    _run(apply=True)
    anna = scene.people["anna"]
    # Her quota is used up: reopened cases are not part of it.
    anna = User().save(dict(User().load(anna["_id"], force=True), **{QUOTA_FIELD: 0}))
    reopened = {str(s[k]["assignmentId"]) for k in ("paired", "claimed")}

    header(19)
    _as(anna)
    mine = queue.listMine(includeFinished=False)
    assert {m["assignmentId"] for m in mine} == reopened
    assert all(m["startFromOwn"] for m in mine)
    first = queue.nextCase(clientProtocol=19)
    assert first["assignmentId"] in reopened and first["startFromOwn"] is True
    assert queue.nextCase(clientProtocol=19)["assignmentId"] == first["assignmentId"]

    # Her read, every class whole: all four are the full tree, overlapping.
    key = "paired" if first["assignmentId"] == str(s["paired"]["assignmentId"]) else "claimed"
    got = _bytes(queue.downloadAsset(caseId=first["caseId"], kind="own"))
    stored = File().load(s[key]["fileId"], force=True)
    assert got == _bytes(File().download(stored, headers=False))
    path = scene.data / "own.seg.nrrd"
    path.write_bytes(got)
    stack = labelfile.read_class_stack(str(path))
    assert stack["names"] == labels.NAMES
    whole = int(scene.tree.sum())
    assert [int(m.sum()) for m in stack["masks"]] == [whole] * 4
    # Nobody else's case: the own asset is only her reopened assignment's.
    _as(scene.people["cathy"])
    assert _refusal(queue.downloadAsset, caseId=first["caseId"], kind="own").code == 403

    # A 0.18 module is told to update, before it can open or submit the case.
    for old in (18, 17):
        header(old)
        _as(anna)
        refused = _refusal(queue.downloadCase, caseId=first["caseId"])
        assert refused.code == 426 and "Update SegQueue14 to open this case" in str(refused)
    header(19)
    _as(anna)
    queue.downloadCase(caseId=first["caseId"])
    fileDoc, meta = _uploadStack(scene, anna, first["caseName"], scene.whole)
    header(18)
    _as(anna)
    assert _refusal(queue.submit, assignmentId=first["assignmentId"],
                    fileId=str(fileDoc["_id"]), meta=json.dumps(meta),
                    labelFormat="class-stack-nrrd/1", clientProtocol=18).code == 426
    assert Assignment14().load(s[key]["assignmentId"], force=True)["state"] == "downloaded"

    # Kept as it is, it is accepted (D38).
    header(19)
    _as(anna)
    done = queue.submit(assignmentId=first["assignmentId"], fileId=str(fileDoc["_id"]),
                        meta=json.dumps(meta), labelFormat="class-stack-nrrd/1",
                        clientProtocol=19)
    assert done["assignment"]["state"] == "submitted"
    assert done["assignment"]["startFromOwn"] is False


def test_the_resubmission_replaces_the_old_read_in_pairing_and_the_report(scene, header):
    import numpy as np
    from girder_segqueue14 import report, scoring
    from girder_segqueue14.models import Assignment14, Submission14

    s, queue = scene.s, scene.queue
    anna, bobby = scene.people["anna"], scene.people["bobby"]

    def figures():
        return report.collect(scene.db, limit=0)["annotators"]

    assert figures()["anna"]["reads"] == 4   # five reads; the benchmark one never counts
    assert figures()["bobby"]["pairs"]["n"] == 1

    _run(apply=True)
    people = figures()
    assert people["anna"]["reads"] == 2, "the two reopened reads no longer count"
    assert people["anna"]["pairs"]["n"] == 0
    assert people["bobby"]["pairs"]["n"] == 0, "nor as the partner's pair"
    assert scoring.partnerSubmission(s["bobby"]) is None

    # She revises the paired case; it is scored against bobby's read again.
    header(19)
    _as(anna)
    paired = next(m for m in queue.listMine(includeFinished=False)
                  if m["assignmentId"] == str(s["paired"]["assignmentId"]))
    tree = scene.tree
    revised = _stackOf(np, {"LAD": tree, "RCA": tree})
    new = _submitStack(scene, queue, anna, paired, revised, clientProtocol=19)
    assert scoring.runOnce() == 1
    newRead = Submission14().load(new["submissionId"], force=True)
    assert newRead["autoScore"]["duplicate"]["partnerSubmissionId"] == str(s["bobby"]["_id"])
    partner = Submission14().load(s["bobby"]["_id"], force=True)
    assert partner["autoScore"]["duplicate"]["partnerSubmissionId"] == new["submissionId"]
    assert Assignment14().load(s["paired"]["assignmentId"], force=True)["submissionId"] \
        == newRead["_id"]
    # The old read is still there, still out of every count.
    assert Submission14().load(s["paired"]["_id"], force=True)["reopenedAt"] is not None
    people = figures()
    assert people["anna"]["reads"] == 3
    assert people["anna"]["pairs"]["n"] == 1 and people["bobby"]["pairs"]["n"] == 1
    _as(bobby)
    assert scoring.partnerSubmission(partner)["_id"] == newRead["_id"]

    # A reviewer acting on the old read never lands on her new one.
    _as(scene.people["revy"])
    old = str(s["paired"]["_id"])
    assert _refusal(queue.claim, submissionId=old).code == 409
    assert _refusal(queue.verdict, submissionId=old, verdict="approve").code == 409
    assert _refusal(queue.returnToPool, submissionId=old, reason="x").code == 409
    assert Assignment14().load(s["paired"]["assignmentId"], force=True)["state"] == "submitted"
