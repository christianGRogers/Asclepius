"""The SegQueue14 lease sweep after a reopen (#315) or a rework.

Against a real Girder and MongoDB (``needs_mongo``, through ``test_segqueue_server14``'s
fixtures, run in CI's server job, which refuses skips). Synthetic data only.

The bug: REOPEN and REWORK gave the assignment a fresh ``deadline`` but left the
first attempt's ``assignedAt`` and ``lastHeartbeat``, and the sweep judged the lease
from ``assignedAt`` and the heartbeat from the stale stamp -- so every read reopened
on Nov 12 was expired by the very next hourly sweep. Here a reopened and a reworked
assignment, both claimed ten days ago and last heard from four days ago, survive
the sweep (and its dry run); they are taken back once the new deadline passes, with
a reason that names it, or after 72 hours of silence following a heartbeat on the
new attempt. ``assignedAt`` stays the original claim.
"""

import datetime
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import test_segqueue_server14 as base  # noqa: E402

pytestmark = pytest.mark.needs_mongo

girder_db = base.girder_db
world = base.world

UTC = datetime.timezone.utc
HOUR = datetime.timedelta(hours=1)
DAY = datetime.timedelta(days=1)


@pytest.fixture
def clock(monkeypatch):
    """The model's clock, so the timestamps transitions write follow the sweep's
    ``now``. Starts at the real time; ``clock.at = ...`` moves it."""
    from girder_segqueue14.models import assignment as model

    class Clock:
        at = datetime.datetime.now(UTC).replace(microsecond=0)

    c = Clock()
    monkeypatch.setattr(model, "_now", lambda: c.at)
    return c


def _naive(dt):
    return dt.replace(tzinfo=None) if dt is not None and dt.tzinfo else dt


def _held(world, login, name, state, claimed, heartbeat):
    """An assignment in ``state`` on a fresh two-read case, its slot taken."""
    from girder_segqueue14.models import Assignment14, Case14

    case = Case14().createCase(name, fileId=None, checksum="", sizeBytes=0,
                               replicasWanted=2)
    Case14().collection.update_one({"_id": case["_id"]}, {"$set": {"activeCount": 1}})
    a = Assignment14().createAssignment(case, world.people[login])
    stamps = {"state": state, "assignedAt": claimed, "lastHeartbeat": heartbeat,
              "deadline": claimed + 7 * DAY, "downloadedAt": claimed + HOUR,
              "submittedAt": claimed + DAY}
    if state == "rejected":
        stamps["decidedAt"] = claimed + 5 * DAY
    Assignment14().collection.update_one({"_id": a["_id"]}, {"$set": stamps})
    return Assignment14().load(a["_id"], force=True)


def _restart(world, clock, login, name, event):
    """Claimed ten days ago, last heartbeat four days ago, reopened or reworked now."""
    from girder_segqueue14.models import Assignment14
    from girder_segqueue14.settings import getPolicy

    from segqueue import states as st

    state = st.SUBMITTED if event == st.REOPEN else st.REJECTED
    a = _held(world, login, name, state, clock.at - 10 * DAY, clock.at - 4 * DAY)
    return Assignment14().transition(a, event, policy=getPolicy())


def _released(result):
    return {r["assignmentId"]: r["reason"] for r in result["released"]}


def _both(world, clock):
    from segqueue import states as st

    return (_restart(world, clock, "anna", "sweep_reopened", st.REOPEN),
            _restart(world, clock, "bobby", "sweep_reworked", st.REWORK))


def test_a_reopened_or_reworked_assignment_survives_the_next_sweep(world, clock):
    from girder_segqueue14 import maintenance
    from girder_segqueue14.models import Assignment14, Case14
    from girder_segqueue14.settings import getPolicy

    claimed = clock.at - 10 * DAY
    reopened, reworked = _both(world, clock)
    for a in (reopened, reworked):
        assert a["state"] == "assigned" and a["lastHeartbeat"] is None
        assert _naive(a["deadline"]) == _naive(clock.at + getPolicy().lease_days * DAY)
        assert _naive(a["assignedAt"]) == _naive(claimed), "the original claim stays"

    # The next hourly sweep -- the one that took the Nov 12 reads -- and the day after.
    restarted = clock.at
    for later in (HOUR, DAY, 6 * DAY):
        clock.at = restarted + later
        assert _released(maintenance.sweep(dryRun=True, now=clock.at)) == {}
        assert _released(maintenance.sweep(now=clock.at)) == {}
    for a in (reopened, reworked):
        assert Assignment14().load(a["_id"], force=True)["state"] == "assigned"
        assert Case14().load(a["caseId"], force=True)["activeCount"] == 1


def test_past_the_new_deadline_they_are_reclaimed_by_the_lease(world, clock):
    from girder_segqueue14 import maintenance
    from girder_segqueue14.models import Assignment14, Case14

    reopened, reworked = _both(world, clock)
    deadline = reopened["deadline"].replace(tzinfo=UTC)
    reason = f"lease of 7 days expired (deadline {deadline:%Y-%m-%d %H:%M} UTC)"

    clock.at = deadline - datetime.timedelta(minutes=1)
    assert _released(maintenance.sweep(now=clock.at)) == {}

    clock.at = deadline + datetime.timedelta(minutes=5)
    ids = {str(reopened["_id"]), str(reworked["_id"])}
    dry = _released(maintenance.sweep(dryRun=True, now=clock.at))
    assert dry == {i: reason for i in ids}
    assert Assignment14().load(reopened["_id"], force=True)["state"] == "assigned"

    assert _released(maintenance.sweep(now=clock.at)) == dry
    for a in (reopened, reworked):
        doc = Assignment14().load(a["_id"], force=True)
        assert doc["state"] == "released" and doc["releaseReason"] == reason
        assert Case14().load(a["caseId"], force=True)["activeCount"] == 0
    assert _released(maintenance.sweep(now=clock.at)) == {}, "idempotent"


def test_72_hours_of_silence_after_the_restart_reclaims_by_heartbeat(world, clock):
    from girder_segqueue14 import maintenance
    from girder_segqueue14.models import Assignment14

    reopened, reworked = _both(world, clock)
    # The annotator opens both again a little later, then goes quiet.
    clock.at += 2 * HOUR
    heard = clock.at
    for a in (reopened, reworked):
        Assignment14().heartbeat(a)

    clock.at = heard + 71 * HOUR
    assert _released(maintenance.sweep(dryRun=True, now=clock.at)) == {}
    assert _released(maintenance.sweep(now=clock.at)) == {}

    clock.at = heard + 72 * HOUR + datetime.timedelta(minutes=1)
    reason = "no heartbeat for 72 hours"
    ids = {str(reopened["_id"]), str(reworked["_id"])}
    assert _released(maintenance.sweep(dryRun=True, now=clock.at)) == \
        {i: reason for i in ids}
    assert _released(maintenance.sweep(now=clock.at)) == {i: reason for i in ids}
    for a in (reopened, reworked):
        doc = Assignment14().load(a["_id"], force=True)
        assert doc["state"] == "released" and doc["releaseReason"] == reason


def test_a_heartbeat_from_before_the_restart_is_not_held_against_it(world, clock):
    """An assignment reopened by 0.5.0, whose old heartbeat was never cleared."""
    from girder_segqueue14 import maintenance
    from girder_segqueue14.models import Assignment14

    reopened, reworked = _both(world, clock)
    for a in (reopened, reworked):
        Assignment14().collection.update_one(
            {"_id": a["_id"]}, {"$set": {"lastHeartbeat": clock.at - 4 * DAY}})
    clock.at += HOUR
    assert _released(maintenance.sweep(now=clock.at)) == {}


def test_a_first_attempt_is_swept_exactly_as_before(world, clock):
    from girder_segqueue14 import maintenance

    lapsed = _held(world, "anna", "sweep_lapsed", "assigned",
                   clock.at - 8 * DAY, clock.at - 7 * DAY - HOUR)
    quiet = _held(world, "bobby", "sweep_quiet", "downloaded",
                  clock.at - 4 * DAY, clock.at - 73 * HOUR)
    healthy = _held(world, "cathy", "sweep_healthy", "downloaded",
                    clock.at - 4 * DAY, clock.at - HOUR)
    unopened = _held(world, "anna", "sweep_unopened", "assigned", clock.at - DAY, None)
    deadline = lapsed["deadline"].replace(tzinfo=UTC)
    got = _released(maintenance.sweep(now=clock.at))
    assert got == {
        str(lapsed["_id"]): f"lease of 7 days expired (deadline {deadline:%Y-%m-%d %H:%M} UTC)",
        str(quiet["_id"]): "no heartbeat for 72 hours"}
    assert str(healthy["_id"]) not in got and str(unopened["_id"]) not in got


def test_the_readers_report_lists_a_restart_expired_within_the_hour(world, clock):
    """The report's line (read-only): what the old sweep did, and what it now doesn't."""
    from girder_segqueue14 import maintenance, report
    from girder_segqueue14.models import Assignment14
    from test_segqueue_server14_report import _snapshot

    reopened, reworked = _both(world, clock)
    clock.at = reopened["deadline"].replace(tzinfo=UTC) + HOUR
    maintenance.sweep(now=clock.at)
    got = report.runReaders(out=lambda _: None, db=world.db)
    assert got["expiredAfterReopen"] == [], "a week after the restart is not quick"

    # As 0.5.0 left it: reworked, then expired by a sweep 50 minutes later.
    restarted = clock.at - 10 * DAY
    Assignment14().collection.update_one({"_id": reworked["_id"]}, {"$set": {
        "reworkedAt": restarted, "releasedAt": restarted + 50 * datetime.timedelta(minutes=1),
        "releaseReason": "lease of 7 days expired"}})
    before = _snapshot(world)
    lines = []
    got = report.runReaders(out=lines.append, db=world.db)
    assert _snapshot(world) == before, "the report wrote something"
    assert [(r["case"], r["login"], r["how"], r["minutes"], r["releaseReason"])
            for r in got["expiredAfterReopen"]] == [
        ("sweep_reworked", "bobby", "reworked", 50, "lease of 7 days expired")]
    assert any(line.startswith("Reopened or reworked, then expired by the sweep within "
                               "1 hour: 1: sweep_reworked bobby (reworked ")
               for line in lines)
