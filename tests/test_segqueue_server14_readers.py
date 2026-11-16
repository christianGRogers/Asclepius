"""``segqueue14-report readers`` (#334): cases with more annotators than they want.

Against a real Girder and MongoDB (``needs_mongo``, through ``test_segqueue_server14``'s
fixtures, run in CI's server job, which refuses skips), on synthetic cases written
straight into the database, one per cause: a reviewer's return to the pool, an
annotator's release, an expired lease, a reopened read let go, the benchmark, and a
third annotator with no freed slot behind it. Plus a deliberately wrong
``activeCount``, and the database the same afterwards.
"""

import datetime
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import test_segqueue_server14 as base  # noqa: E402
from test_segqueue_server14_report import _snapshot  # noqa: E402

pytestmark = pytest.mark.needs_mongo

girder_db = base.girder_db
world = base.world


def _at(minutes):
    return datetime.datetime(2026, 11, 2, 15, tzinfo=datetime.timezone.utc) \
        + datetime.timedelta(minutes=minutes)


def _build(world):
    from girder.models.user import User
    from girder_segqueue14.models import Assignment14, Case14, Submission14

    people = dict(world.people)
    for login in ("dave", "erin"):
        people[login] = User().createUser(login, "password1", login, "X",
                                          f"{login}@example.org")

    def case(name, active, approved=0, replicas=2, benchmark=False):
        c = Case14().createCase(name, fileId=None, checksum="", sizeBytes=0,
                                replicasWanted=replicas,
                                extra={"benchmark": True, "benchmarkPending": []}
                                if benchmark else None)
        Case14().collection.update_one({"_id": c["_id"]}, {"$set": {
            "activeCount": active, "approvedCount": approved}})
        return c

    def assign(c, login, state, claimed, submitted=None, decided=None, released=None,
               reason=None, reviewer=None, reopened=None, read=False):
        doc = {"caseId": c["_id"], "userId": people[login]["_id"], "state": state,
               "kind": "benchmark" if c.get("benchmark") else "paired", "attempt": 1,
               "assignedAt": _at(claimed),
               "submittedAt": _at(submitted) if submitted is not None else None,
               "decidedAt": _at(decided) if decided is not None else None,
               "releasedAt": _at(released) if released is not None else None,
               "reopenedAt": _at(reopened) if reopened is not None else None}
        if reason:
            doc["releaseReason"] = reason
        if reviewer:
            doc["reviewerId"] = people[reviewer]["_id"]
        a = Assignment14().collection.insert_one(doc).inserted_id
        if read or submitted is not None:
            Submission14().collection.insert_one({
                "assignmentId": a, "caseId": c["_id"], "userId": people[login]["_id"],
                "authorRole": "annotator", "kind": doc["kind"],
                "created": _at(submitted if submitted is not None else claimed + 5),
                "reopenedAt": _at(reopened) if reopened is not None else None})
        return a

    # return-to-pool: anna's read sent back by revy; cathy took the slot.
    c = case("rtp_case", active=1, approved=1)
    assign(c, "anna", "released", 0, submitted=10, released=20,
           reason="returned to the pool by a reviewer", reviewer="revy")
    assign(c, "bobby", "approved", 5, submitted=15, decided=25)
    assign(c, "cathy", "submitted", 30, submitted=40)

    # release: bobby gave it back unread; dave came in.
    c = case("release_case", active=2)
    assign(c, "anna", "submitted", 0, submitted=10)
    assign(c, "bobby", "released", 5, released=8, reason="released by annotator")
    assign(c, "dave", "downloaded", 9)

    # expired: cathy's lease lapsed; erin came in.
    c = case("expired_case", active=2)
    assign(c, "anna", "submitted", 0, submitted=10)
    assign(c, "cathy", "released", 1, released=60, reason="lease of 7 days expired")
    assign(c, "erin", "assigned", 61)

    # reopen (#315): bobby's read reopened for him, then his lease lapsed; anna came in.
    c = case("reopen_case", active=2)
    assign(c, "cathy", "submitted", 0, submitted=10)
    assign(c, "bobby", "released", 1, submitted=None, released=90, reopened=50,
           reason="no heartbeat for 48 hours", read=True)
    assign(c, "anna", "assigned", 91)

    # benchmark (D43): everyone, on purpose.
    c = case("annotator_benchmark_0001", active=0, replicas=1, benchmark=True)
    for i, login in enumerate(("anna", "bobby", "cathy")):
        assign(c, login, "approved", i, submitted=i + 10, decided=i + 20)

    # unexplained: three open reads and no freed slot; activeCount says 2 (drift).
    c = case("drift_case", active=2)
    for i, login in enumerate(("anna", "bobby", "dave")):
        assign(c, login, "submitted", i, submitted=i + 10)

    # Two annotators, as wanted: not listed at --min 3.
    c = case("normal_case", active=1, approved=1)
    assign(c, "anna", "approved", 0, submitted=10, decided=20)
    assign(c, "erin", "under_review", 1, submitted=11)


def test_the_readers_report_names_each_cause(world):
    from girder_segqueue14 import report

    _build(world)
    before = _snapshot(world)
    lines = []
    got = report.runReaders(out=lines.append, db=world.db)
    assert _snapshot(world) == before, "the report wrote something"

    cases = {c["case"]: c for c in got["cases"]}
    assert {name: c["cause"] for name, c in cases.items()} == {
        "rtp_case": "return-to-pool", "release_case": "release",
        "expired_case": "expired", "reopen_case": "reopen",
        "annotator_benchmark_0001": "benchmark", "drift_case": "other/unexplained"}
    assert "normal_case" not in cases

    totals = got["causeTotals"]
    assert sum(totals.values()) == len(got["cases"]) == 6
    assert {k: v for k, v in totals.items() if v} == {
        "return-to-pool": 1, "release": 1, "expired": 1, "reopen": 1, "benchmark": 1,
        "other/unexplained": 1}
    # 3+ distinct logins with a submitted read: rtp, benchmark, drift.
    assert got["threeOrMoreSubmitted"] == 3
    assert [c["case"] for c in got["unexplained"]] == ["drift_case"]

    # The per-assignment rows, oldest first, in Eastern time.
    rtp = cases["rtp_case"]
    assert (rtp["replicasWanted"], rtp["activeCount"], rtp["approvedCount"],
            rtp["benchmark"]) == (2, 1, 1, False)
    assert [r["login"] for r in rtp["assignments"]] == ["anna", "bobby", "cathy"]
    anna = rtp["assignments"][0]
    assert anna["state"] == "returned to pool" and anna["submission"] is True
    assert anna["claimed"] == "2026-11-02 10:00 EST"
    assert anna["submitted"] == "2026-11-02 10:10 EST"
    assert anna["decided"] == "2026-11-02 10:20 EST"
    assert anna["releaseReason"] == "returned to the pool by a reviewer"
    assert [r["state"] for r in cases["expired_case"]["assignments"]] == [
        "submitted", "expired", "assigned"]
    assert cases["release_case"]["assignments"][1]["state"] == "released"
    bobby = cases["reopen_case"]["assignments"][1]
    assert bobby["reopened"] is True and bobby["submission"] is True
    assert cases["annotator_benchmark_0001"]["benchmark"] is True

    # activeCount against the open assignments: drift_case is 2 against 3.
    assert got["activeCount"] == {"mismatches": 1, "cases": [
        {"case": "drift_case", "activeCount": 2, "openAssignments": 3}]}
    assert cases["drift_case"]["activeCountMismatch"] is True
    assert cases["rtp_case"]["activeCountMismatch"] is False

    # Reopened, then expired by the sweep 40 minutes later: listed (0.5.1).
    assert got["expiredAfterReopen"] == [{
        "case": "reopen_case", "login": "bobby", "how": "reopened",
        "restarted": "2026-11-02 10:50 EST", "expired": "2026-11-02 11:30 EST",
        "minutes": 40, "releaseReason": "no heartbeat for 48 hours"}]

    text = "\n".join(lines)
    assert "Reopened or reworked, then expired by the sweep within 1 hour: 1: " \
           "reopen_case bobby (reopened 2026-11-02 10:50 EST, expired " \
           "2026-11-02 11:30 EST, 40 min, no heartbeat for 48 hours)" in text
    assert "rtp_case: pool, replicasWanted 2, activeCount 1, approvedCount 1, 3 logins " \
           "-- cause: return-to-pool" in text
    assert "annotator_benchmark_0001: benchmark," in text
    assert "Cases with 3+ submitted annotator reads (distinct logins): 3" in text
    assert "  drift_case: activeCount 2, replicasWanted 2;" in text
    assert "activeCount check: 1 case(s)" in text and "drift_case (2 vs 3)" in text
    assert "@example.org" not in text, "logins only"

    # --min 2 lists the two-annotator case too, as within replicasWanted; --json.
    wide = report.runReaders(minLogins=2, out=lambda _: None, db=world.db)
    assert {c["case"]: c["cause"] for c in wide["cases"]}["normal_case"] \
        == "within-replicasWanted"
    assert sum(wide["causeTotals"].values()) == 7
    js = []
    report.runReaders(asJson=True, out=js.append, db=world.db)
    assert '"cause": "reopen"' in js[0]
    assert _snapshot(world) == before


def test_the_readers_report_with_a_fixed_counter(world):
    """The activeCount check is quiet when the counters match."""
    from girder_segqueue14 import report
    from girder_segqueue14.models import Case14

    _build(world)
    Case14().collection.update_one({"name": "drift_case"}, {"$set": {"activeCount": 3}})
    got = report.runReaders(out=lambda _: None, db=world.db)
    assert got["activeCount"] == {"mismatches": 0, "cases": []}


def test_readers_takes_min():
    pytest.importorskip("girder")
    from girder_segqueue14 import report

    assert report.buildParser().parse_args(["readers"]).minLogins == 3
    args = report.buildParser().parse_args(["readers", "--min", "4", "--json"])
    assert (args.minLogins, args.json) == (4, True)
