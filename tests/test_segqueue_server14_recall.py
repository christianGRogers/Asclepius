"""An annotator recalls their own submitted read for revision (protocol 20).

Against a real Girder and MongoDB (``needs_mongo``, through ``test_segqueue_server14``'s
fixtures; run in CI's server job, which refuses skips). Synthetic data only. Reuses
``test_segqueue_server14_reopen``'s scene: anna has a paired read (bobby is the
partner), a read revy has claimed, a late read, an approved read and a benchmark read,
all submitted with review forced; cathy has one read.

What is checked: the list (own reads only, newest first, paginated, each with whether
and why not it can be recalled); the recall (the admin reopen's path: read marked
``reopenedAt``, fresh lease, ``activeCount`` unchanged, a note naming no login); every
refusal; the race with a reviewer's claim; the read out of pairing, the report and
the export until resubmitted, then back; the sweep leaving a fresh recall alone; and
that a recall never costs the read (release and an expired lease put it back).
"""

import datetime
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import test_segqueue_server14 as base  # noqa: E402
import test_segqueue_server14_reopen as reopenTests  # noqa: E402
from test_segqueue_server14 import _as, _refusal, _stackOf, _submitStack  # noqa: E402

girder_db = base.girder_db
world = base.world
header = base.header
scene = reopenTests.scene

pytestmark = pytest.mark.needs_mongo

UTC = datetime.timezone.utc
PROTOCOL = 20
NOTE = "Reopened at the annotator's own request, for revision."


def _a(assignmentId):
    from girder_segqueue14.models import Assignment14

    return Assignment14().load(assignmentId, force=True)


def _sub(submissionId):
    from girder_segqueue14.models import Submission14

    return Submission14().load(submissionId, force=True)


def _active(caseId):
    from girder_segqueue14.models import Case14

    return Case14().load(caseId, force=True)["activeCount"]


def _recall(scene, key, who="anna", clientProtocol=PROTOCOL):
    _as(scene.people[who])
    return scene.queue.recall(assignmentId=str(scene.s[key]["assignmentId"]),
                              clientProtocol=clientProtocol)


def _refused(scene, key, who="anna", clientProtocol=PROTOCOL):
    _as(scene.people[who])
    return _refusal(scene.queue.recall, assignmentId=str(scene.s[key]["assignmentId"]),
                    clientProtocol=clientProtocol)


def _list(scene, who="anna", **page):
    _as(scene.people[who])
    return scene.queue.listMySubmissions(limit=page.get("limit", 20),
                                         offset=page.get("offset", 0))


# ------------------------------------------------------------------- the list


def test_the_list_is_her_own_unapproved_reads_newest_first_with_reasons(scene):
    s = scene.s
    page = _list(scene)
    rows = page["items"]
    assert page["total"] == 4
    ids = [r["assignmentId"] for r in rows]
    # late (Nov 9 00:30 EST), claimed (Nov 8 23:30 EST), then the two from Nov 5.
    assert ids[:2] == [str(s["late"]["assignmentId"]), str(s["claimed"]["assignmentId"])]
    assert set(ids[2:]) == {str(s["paired"]["assignmentId"]),
                            str(s["benchmark"]["assignmentId"])}
    assert str(s["approved"]["assignmentId"]) not in ids, "approved is not listed"
    assert str(s["cathy"]["assignmentId"]) not in ids, "nor anybody else's"
    stamps = [r["submittedAt"] for r in rows]
    assert stamps == sorted(stamps, reverse=True)
    assert stamps[0] == reopenTests.JUST_AFTER.timestamp()

    byKey = {k: next(r for r in rows if r["assignmentId"] == str(s[k]["assignmentId"]))
             for k in ("late", "claimed", "paired", "benchmark")}
    assert byKey["late"]["canRecall"] and byKey["late"]["reason"] == ""
    assert byKey["paired"]["canRecall"]
    assert byKey["late"]["caseName"] and byKey["late"]["state"] == "submitted"
    claimed = byKey["claimed"]
    assert not claimed["canRecall"] and claimed["state"] == "under_review"
    assert claimed["reasonCode"] == "recall_reviewing"
    assert claimed["reason"].startswith("A reviewer is looking at this case now")
    assert not byKey["benchmark"]["canRecall"]
    assert byKey["benchmark"]["reasonCode"] == "recall_benchmark"
    # Nothing a reviewer or the scorer knows leaks into a row.
    assert set(claimed) == {"assignmentId", "caseId", "caseName", "state", "submittedAt",
                            "canRecall", "reason", "reasonCode"}

    # Paginated.
    first, second = _list(scene, limit=2), _list(scene, limit=2, offset=2)
    assert [r["assignmentId"] for r in first["items"]] == ids[:2]
    assert [r["assignmentId"] for r in second["items"]] == ids[2:]
    assert first["total"] == second["total"] == 4
    assert _list(scene, limit=2, offset=4)["items"] == []
    assert len(_list(scene, limit=1000)["items"]) == 4, "capped, not refused"

    cathy = _list(scene, who="cathy")["items"]
    assert [r["assignmentId"] for r in cathy] == [str(s["cathy"]["assignmentId"])]


# ------------------------------------------------------------------ the recall


def test_recall_reopens_her_read_like_the_admin_reopen(scene, header):
    from girder_segqueue14.models import Note14

    s = scene.s
    late = s["late"]
    active = _active(late["caseId"])
    before = _a(late["assignmentId"])

    info = _recall(scene, "late")
    assert info["assignmentId"] == str(late["assignmentId"])
    assert info["startFromOwn"] is True and info["recalled"] is True
    a = _a(late["assignmentId"])
    assert a["state"] == "assigned" and a["attempt"] == before["attempt"] + 1
    assert a["startFileId"] == late["fileId"] and a["startSubmissionId"] == late["_id"]
    assert a["submittedAt"] is None and a["downloadedAt"] is None
    assert a["lastHeartbeat"] is None, "#341: the heartbeat starts over"
    assert a["deadline"].replace(tzinfo=UTC) > datetime.datetime.now(UTC) \
        + datetime.timedelta(days=6)
    assert a["recall"]["submissionId"] == late["_id"]
    assert _sub(late["_id"])["reopenedAt"] is not None
    assert _active(late["caseId"]) == active, "the slot was already held"
    notes = [n["text"] for n in Note14().forCase(late["caseId"])]
    assert NOTE in notes
    assert not any("anna" in n for n in notes), "the note names no login"

    # Served first and opened from her read, by a protocol-20 module.
    header(PROTOCOL)
    _as(scene.people["anna"])
    assert scene.queue.nextCase(clientProtocol=PROTOCOL)["assignmentId"] == str(
        late["assignmentId"])
    mine = scene.queue.listMine(includeFinished=False)
    assert [(m["assignmentId"], m["recalled"]) for m in mine] == [
        (str(late["assignmentId"]), True)]
    got = b"".join(scene.queue.downloadAsset(caseId=str(late["caseId"]), kind="own")())
    assert got, "the own asset is her read"

    # Every other row is now disabled: she holds a case.
    rows = _list(scene)["items"]
    assert str(late["assignmentId"]) not in [r["assignmentId"] for r in rows]
    paired = next(r for r in rows if r["assignmentId"] == str(s["paired"]["assignmentId"]))
    assert not paired["canRecall"] and paired["reasonCode"] == "recall_holding"
    assert paired["reason"] == "Finish or release your current case first."


def test_every_refusal_says_why_and_changes_nothing(scene):
    from girder_segqueue14.models import Assignment14, Note14, Submission14

    s = scene.s

    def snapshot():
        return (list(Assignment14().find({})), list(Submission14().find({})),
                Note14().collection.count_documents({}))

    def refused(key, status, code, text, **kw):
        before = snapshot()
        err = _refused(scene, key, **kw)
        assert err.code == status, (key, err.code)
        assert err.extra["segqueueError"] == code
        assert text in err.extra["message"]
        assert snapshot() == before, key

    refused("cathy", 403, "recall_not_yours", "not one of your submissions")
    refused("approved", 409, "recall_approved", "already been approved")
    refused("claimed", 409, "recall_reviewing", "A reviewer is looking at this case now")
    refused("benchmark", 403, "recall_benchmark", "benchmark")
    refused("late", 426, "update_to_recall", "Update SegQueue14", clientProtocol=19)
    # Another person's, even for an admin: it would land in someone else's queue.
    _as(scene.admin)
    err = _refusal(scene.queue.recall, assignmentId=str(s["late"]["assignmentId"]),
                   clientProtocol=PROTOCOL)
    assert err.code == 403 and err.extra["segqueueError"] == "recall_not_yours"

    # Holding another case: one recall at a time.
    _recall(scene, "late")
    refused("paired", 409, "recall_holding", "Finish or release your current case first")
    # Recalling it twice: the second finds it no longer submitted.
    _as(scene.people["anna"])
    err = _refusal(scene.queue.recall, assignmentId=str(s["late"]["assignmentId"]),
                   clientProtocol=PROTOCOL)
    assert err.code == 409


def test_the_holding_rule_never_strands_her_releasing_puts_the_read_back(scene):
    """She can always clear the case that blocks her, and releasing a recalled case
    loses nothing: the read is back exactly as it was, slot and counts untouched."""
    from girder_segqueue14.models import Assignment14, Note14

    s = scene.s
    paired = s["paired"]
    before = _a(paired["assignmentId"])
    active = _active(paired["caseId"])
    _recall(scene, "paired")
    assert _refused(scene, "late").code == 409

    _as(scene.people["anna"])
    out = scene.queue.release(assignmentId=str(paired["assignmentId"]), reason="")
    assert out["restored"] is True
    a = _a(paired["assignmentId"])
    for field in ("state", "attempt", "submissionId", "submittedAt", "needsReview",
                  "reopenedAt", "deadline", "downloadedAt"):
        assert a.get(field) == before.get(field), field
    assert a["startFileId"] is None and a["recall"] is None
    assert a["recallUndone"]["why"] == "released by annotator"
    assert _sub(paired["_id"])["reopenedAt"] is None
    assert _active(paired["caseId"]) == active
    assert a["_id"] in {x["_id"] for x in Assignment14().pendingReview(limit=500)}
    assert any("withdrawn" in n["text"] for n in Note14().forCase(paired["caseId"]))

    # Nothing holds her now: the next recall goes through, and so does a second
    # recall of the same read.
    assert _recall(scene, "late")["recalled"] is True
    _as(scene.people["anna"])
    scene.queue.release(assignmentId=str(s["late"]["assignmentId"]), reason="")
    assert _recall(scene, "paired")["recalled"] is True


def test_a_later_admin_reopen_is_not_undone_by_release(scene, header):
    """The recall's snapshot belongs to the attempt it created: resubmitted and then
    reopened by an admin, the case releases to the pool as before."""
    import numpy as np
    from girder_segqueue14 import reopen

    s = scene.s
    late = s["late"]
    _recall(scene, "late")
    header(PROTOCOL)
    _as(scene.people["anna"])
    info = scene.queue.listMine(includeFinished=False)[0]
    _submitStack(scene, scene.queue, scene.people["anna"], info,
                 _stackOf(np, {"LAD": scene.tree}), clientProtocol=PROTOCOL)
    a = _a(late["assignmentId"])
    assert a["state"] == "submitted"
    reopen.reopenOne(a, reopen._latestRead(a))
    _as(scene.people["anna"])
    out = scene.queue.release(assignmentId=str(late["assignmentId"]), reason="")
    assert "restored" not in out
    assert _a(late["assignmentId"])["state"] == "released"


# ------------------------------------------------------------------- the race


def test_a_reviewer_claiming_in_the_same_moment_wins_cleanly(scene, monkeypatch):
    """The claim lands between the recall marking the read and moving the
    assignment: the guarded move loses, the read is unmarked, she is told a
    reviewer has it, and the reviewer keeps the claim."""
    from girder_segqueue14.models import Assignment14

    from segqueue import states as st

    s = scene.s
    late = s["late"]
    revy = scene.people["revy"]
    real = Assignment14.transition

    def claimFirst(self, assignment, event, policy=None, **extra):
        if event == st.REOPEN:
            # The reviewer's request passed its checks before the read was marked.
            real(self, _a(assignment["_id"]), st.CLAIM_REVIEW, reviewerId=revy["_id"])
        return real(self, assignment, event, policy=policy, **extra)

    monkeypatch.setattr(Assignment14, "transition", claimFirst)
    err = _refused(scene, "late")
    monkeypatch.setattr(Assignment14, "transition", real)
    assert err.code == 409 and err.extra["segqueueError"] == "recall_reviewing"
    assert "A reviewer is looking at this case now" in err.extra["message"]
    a = _a(late["assignmentId"])
    assert a["state"] == "under_review" and a["reviewerId"] == revy["_id"]
    assert a.get("recall") is None and a.get("startFileId") is None
    assert _sub(late["_id"])["reopenedAt"] is None, "unmarked: still the read to review"
    # The reviewer carries on as if nothing happened.
    _as(revy)
    scene.queue.verdict(submissionId=str(late["_id"]), verdict="approve")
    assert _a(late["assignmentId"])["state"] == "approved"


def test_a_recall_first_leaves_the_reviewer_a_clean_refusal(scene):
    from girder_segqueue14.models import Assignment14

    from segqueue import states as st

    s = scene.s
    late = s["late"]
    stale = _a(late["assignmentId"])        # what the reviewer's request loaded
    _recall(scene, "late")
    with pytest.raises(st.TransitionError):
        Assignment14().transition(stale, st.CLAIM_REVIEW,
                                  reviewerId=scene.people["revy"]["_id"])
    _as(scene.people["revy"])
    assert _refusal(scene.queue.claim, submissionId=str(late["_id"])).code == 409
    assert _refusal(scene.queue.verdict, submissionId=str(late["_id"]),
                    verdict="approve").code == 409
    assert _a(late["assignmentId"])["state"] == "assigned"


# ------------------------------------------- out until resubmitted, then back


def test_the_recalled_read_is_out_until_resubmitted_then_scored_and_paired(scene, header):
    import numpy as np
    from girder_segqueue14 import export, report, scoring
    from girder_segqueue14.models import Assignment14

    s = scene.s
    paired, bobby = s["paired"], s["bobby"]

    def people():
        return report.collect(scene.db, limit=0)["annotators"]

    assert people()["anna"]["pairs"]["n"] == 1 and people()["bobby"]["pairs"]["n"] == 1
    reads = people()["anna"]["reads"]
    active = _active(paired["caseId"])

    _recall(scene, "paired")
    assert people()["anna"]["reads"] == reads - 1
    assert people()["anna"]["pairs"]["n"] == 0 and people()["bobby"]["pairs"]["n"] == 0
    assert scoring.partnerSubmission(bobby) is None
    assert export.exportedSubmission(_a(paired["assignmentId"])) is None

    header(PROTOCOL)
    _as(scene.people["anna"])
    info = next(m for m in scene.queue.listMine(includeFinished=False)
                if m["assignmentId"] == str(paired["assignmentId"]))
    new = _submitStack(scene, scene.queue, scene.people["anna"], info,
                       _stackOf(np, {"LAD": scene.tree, "RCA": scene.tree}),
                       clientProtocol=PROTOCOL)
    a = _a(paired["assignmentId"])
    assert a["state"] == "submitted" and a["needsReview"] is True, "back to review"
    assert new["assignment"]["recalled"] is False
    assert a["_id"] in {x["_id"] for x in Assignment14().pendingReview(limit=500)}
    assert _active(paired["caseId"]) == active, "activeCount never moved"

    assert scoring.runOnce() == 1
    newRead = _sub(new["submissionId"])
    assert newRead["autoScore"]["duplicate"]["partnerSubmissionId"] == str(bobby["_id"])
    assert scoring.partnerSubmission(_sub(bobby["_id"]))["_id"] == newRead["_id"]
    assert people()["anna"]["reads"] == reads
    assert people()["anna"]["pairs"]["n"] == 1 and people()["bobby"]["pairs"]["n"] == 1
    assert _sub(paired["_id"])["reopenedAt"] is not None, "the old read stays history"

    # It is hers to recall again, and releasing then leaves the new read standing.
    rows = {r["assignmentId"]: r for r in _list(scene)["items"]}
    assert rows[str(paired["assignmentId"])]["canRecall"]


# -------------------------------------------------------------------- the sweep


def test_the_sweep_leaves_a_fresh_recall_alone_and_a_lapsed_one_restored(scene):
    from girder_segqueue14 import maintenance
    from girder_segqueue14.models import Note14
    from girder_segqueue14.settings import getPolicy

    s = scene.s
    late = s["late"]
    before = _a(late["assignmentId"])
    active = _active(late["caseId"])
    _recall(scene, "late")
    now = datetime.datetime.now(UTC)

    # Within the hour, and four days on without a heartbeat (#341): not swept.
    for later in (datetime.timedelta(hours=1), datetime.timedelta(days=4)):
        out = maintenance.sweep(now=now + later)
        assert str(late["assignmentId"]) not in {r["assignmentId"] for r in out["released"]}
        assert _a(late["assignmentId"])["state"] == "assigned"

    # Past the fresh lease she never came back: the read is put back, not lost.
    lapsed = now + datetime.timedelta(days=getPolicy().lease_days + 1)
    dry = maintenance.sweep(dryRun=True, now=lapsed)
    assert [r.get("restored") for r in dry["released"]
            if r["assignmentId"] == str(late["assignmentId"])] == [True]
    assert _a(late["assignmentId"])["state"] == "assigned", "a dry run writes nothing"
    out = maintenance.sweep(now=lapsed)
    assert [r.get("restored") for r in out["released"]
            if r["assignmentId"] == str(late["assignmentId"])] == [True]
    a = _a(late["assignmentId"])
    assert a["state"] == "submitted" and a["submissionId"] == before["submissionId"]
    assert a["attempt"] == before["attempt"] and a["releasedAt"] is None
    assert _sub(late["_id"])["reopenedAt"] is None
    assert _active(late["caseId"]) == active
    assert any("lease ran out" in n["text"] for n in Note14().forCase(late["caseId"]))
    again = maintenance.sweep(now=lapsed)["released"]
    assert str(late["assignmentId"]) not in {r["assignmentId"] for r in again}


def test_old_modules_see_nothing_different(scene, header):
    """A protocol-19 module never calls the new routes; everything it does call
    answers as before, and the server says it speaks 20 or newer (21: defect cases)."""
    _as(scene.people["anna"])
    project = scene.queue.getProject(clientProtocol=19)
    assert project["protocolVersion"] >= PROTOCOL
    header(19)
    mine = scene.queue.listMine(includeFinished=True)
    assert mine and all(m["recalled"] is False for m in mine)
