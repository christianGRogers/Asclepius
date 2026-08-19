"""Integration tests for the Girder models, against a real MongoDB.

Marked ``needs_mongo`` and skipped cleanly when no database is reachable, so the
suite still runs on a laptop with nothing installed -- the same bargain
``needs_data`` makes for the training tests.

What is tested here is the half that cannot be tested anywhere else: the atomic
claim. ``Case.claim`` is one ``findAndModify`` precisely because a read-then-write
in Python has a race window, and a test that mocks the database would verify the
mock rather than the property. So these tests run real concurrent claims against
a real server and count what came out.

Run one with::

    docker run -d --name segqueue-mongo -p 27099:27017 mongo:7
    SEGQUEUE_TEST_MONGO=mongodb://localhost:27099 pytest tests/test_segqueue_server.py
"""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from segqueue import policy as pol
from segqueue import states as st

pytestmark = pytest.mark.needs_mongo

MONGO_ENV = "SEGQUEUE_TEST_MONGO"


@pytest.fixture(scope="module")
def girder_db():
    """Point Girder at a scratch database, or skip.

    Girder reads its Mongo URI from configuration at import time and models
    connect in their constructor, so the environment has to be set before any
    girder.models module is imported -- hence the import inside the fixture.
    """
    uri = os.environ.get(MONGO_ENV)
    if not uri:
        pytest.skip(f"set {MONGO_ENV} to a MongoDB URI to run the server tests")

    dbName = f"segqueue_test_{uuid.uuid4().hex[:8]}"
    os.environ["GIRDER_MONGO_URI"] = f"{uri.rstrip('/')}/{dbName}"

    try:
        import pymongo

        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=3000)
        client.server_info()
    except ImportError:
        pytest.skip("pymongo is not installed in this environment")
    except Exception as exc:  # pragma: no cover - depends on the machine
        pytest.skip(f"no MongoDB at {uri}: {exc}")

    try:
        from girder.models import getDbConnection  # noqa: F401
    except ImportError:
        pytest.skip("girder is not installed in this environment")

    yield dbName
    client.drop_database(dbName)


@pytest.fixture
def models(girder_db):
    try:
        from girder_segqueue.models import Assignment, Case
    except ImportError:
        pytest.skip("girder-segqueue is not installed in this environment")

    case, assignment = Case(), Assignment()
    case.collection.delete_many({})
    assignment.collection.delete_many({})
    return case, assignment


def _user(name):
    """A stand-in for a Girder user. Only ``_id`` is ever read by these paths."""
    from bson import ObjectId

    return {"_id": ObjectId(), "login": name}


def _case(caseModel, name, **kwargs):
    return caseModel.createCase(
        name=name, fileId=None, checksum="0" * 64, sizeBytes=1024,
        creator=None, **kwargs)


# ------------------------------------------------------------- the atomic claim


def test_one_case_goes_to_exactly_one_of_two_racing_annotators(models):
    caseModel, _ = models
    case = _case(caseModel, "solo")
    alice, bob = _user("alice"), _user("bob")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda u: caseModel.claim(case["_id"], u["_id"]), (alice, bob)))

    assert sum(1 for r in results if r is not None) == 1
    stored = caseModel.load(case["_id"], force=True)
    assert stored["activeCount"] == 1
    assert len(stored["assignedUserIds"]) == 1


def test_thirty_annotators_racing_thirty_cases_collide_on_nothing(models):
    """The load the design actually has to survive: a class starting together."""
    caseModel, _ = models
    [_case(caseModel, f"case-{i:03d}") for i in range(30)]
    users = [_user(f"student{i}") for i in range(30)]

    def claimAny(user):
        for case in caseModel.candidates(user["_id"]):
            got = caseModel.claim(case["_id"], user["_id"])
            if got is not None:
                return got["_id"]
        return None

    with ThreadPoolExecutor(max_workers=30) as pool:
        claimed = list(pool.map(claimAny, users))

    got = [c for c in claimed if c is not None]
    assert len(got) == 30, "every annotator should have got a case"
    assert len(set(got)) == 30, "no two annotators may hold the same case"
    assert all(c["activeCount"] == 1 for c in caseModel.find({}))


def test_a_case_is_never_served_twice_to_the_same_person(models):
    caseModel, _ = models
    case = _case(caseModel, "sticky")
    alice = _user("alice")

    assert caseModel.claim(case["_id"], alice["_id"]) is not None
    caseModel.releaseSlot(case["_id"])
    # Free again by the counters, but not for her -- she has seen it.
    assert caseModel.claim(case["_id"], alice["_id"]) is None
    assert caseModel.claim(case["_id"], _user("bob")["_id"]) is not None


def test_a_retired_case_stops_being_served(models):
    caseModel, _ = models
    case = _case(caseModel, "withdrawn")
    caseModel.retire(case, "wrong series")
    assert caseModel.claim(case["_id"], _user("alice")["_id"]) is None


def test_the_slot_floor_survives_a_double_release(models):
    """A sweeper and a user's release button firing on the same assignment."""
    caseModel, _ = models
    case = _case(caseModel, "double")
    caseModel.claim(case["_id"], _user("alice")["_id"])

    caseModel.releaseSlot(case["_id"])
    caseModel.releaseSlot(case["_id"])

    stored = caseModel.load(case["_id"], force=True)
    assert stored["activeCount"] == 0, "must not go negative and strand the case"
    assert caseModel.claim(case["_id"], _user("bob")["_id"]) is not None


def test_approval_moves_a_slot_from_active_to_approved(models):
    caseModel, _ = models
    case = _case(caseModel, "done")
    caseModel.claim(case["_id"], _user("alice")["_id"])
    caseModel.completeSlot(case["_id"])

    stored = caseModel.load(case["_id"], force=True)
    assert (stored["activeCount"], stored["approvedCount"]) == (0, 1)
    assert caseModel.statusOf(stored) == st.CASE_COMPLETE
    assert caseModel.claim(case["_id"], _user("bob")["_id"]) is None


# ----------------------------------------------------------------- duplicates


def test_a_duplicate_is_drawn_only_from_finished_unclaimed_work(models):
    caseModel, _ = models
    fresh = _case(caseModel, "never-done")
    finished = _case(caseModel, "done-once")
    caseModel.claim(finished["_id"], _user("alice")["_id"])
    caseModel.completeSlot(finished["_id"])

    candidates = [c["_id"] for c in caseModel.duplicateCandidates(_user("bob")["_id"])]
    assert finished["_id"] in candidates
    assert fresh["_id"] not in candidates


def test_claiming_a_duplicate_raises_the_target_and_takes_the_slot_at_once(models):
    caseModel, _ = models
    case = _case(caseModel, "dup")
    alice = _user("alice")
    caseModel.claim(case["_id"], alice["_id"])
    caseModel.completeSlot(case["_id"])

    claimed = caseModel.claimAsDuplicate(case["_id"], _user("bob")["_id"])
    assert claimed is not None
    assert claimed["replicasWanted"] == 2
    assert claimed["activeCount"] == 1
    assert caseModel.statusOf(claimed) == st.CASE_IN_PROGRESS


def test_the_original_annotator_cannot_be_given_the_duplicate(models):
    """Otherwise the agreement score would compare someone with themselves."""
    caseModel, _ = models
    case = _case(caseModel, "dup")
    alice = _user("alice")
    caseModel.claim(case["_id"], alice["_id"])
    caseModel.completeSlot(case["_id"])

    assert caseModel.claimAsDuplicate(case["_id"], alice["_id"]) is None


def test_two_racing_duplicate_claims_yield_one_second_opinion_not_two(models):
    caseModel, _ = models
    case = _case(caseModel, "dup")
    caseModel.claim(case["_id"], _user("alice")["_id"])
    caseModel.completeSlot(case["_id"])
    bob, carol = _user("bob"), _user("carol")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda u: caseModel.claimAsDuplicate(case["_id"], u["_id"]), (bob, carol)))

    assert sum(1 for r in results if r is not None) == 1
    stored = caseModel.load(case["_id"], force=True)
    assert stored["replicasWanted"] == 2
    assert stored["activeCount"] == 1


# ---------------------------------------------------------------- assignments


def test_transitions_are_guarded_against_a_second_writer(models):
    """Two reviewers both hitting Approve: one wins, one is told so."""
    caseModel, assignmentModel = models
    case = _case(caseModel, "contested")
    alice = _user("alice")
    caseModel.claim(case["_id"], alice["_id"])
    assignment = assignmentModel.createAssignment(case, alice)
    assignment = assignmentModel.transition(assignment, st.DOWNLOAD)
    assignment = assignmentModel.transition(assignment, st.SUBMIT)

    assignmentModel.transition(assignment, st.APPROVE)
    # The stale in-memory copy still says "submitted"; the guard catches it.
    with pytest.raises(st.TransitionError):
        assignmentModel.transition(assignment, st.APPROVE)


def test_rework_renews_the_lease_and_bumps_the_attempt(models):
    caseModel, assignmentModel = models
    case = _case(caseModel, "redo")
    alice = _user("alice")
    caseModel.claim(case["_id"], alice["_id"])
    assignment = assignmentModel.createAssignment(case, alice)

    for event in (st.DOWNLOAD, st.SUBMIT, st.REJECT):
        assignment = assignmentModel.transition(assignment, event)
    firstDeadline = assignment["deadline"]

    assignment = assignmentModel.transition(assignment, st.REWORK)
    assert assignment["state"] == st.ASSIGNED
    assert assignment["attempt"] == 2
    assert assignment["deadline"] >= firstDeadline
    assert assignment["submittedAt"] is None


def test_open_count_ignores_submitted_work(models):
    """A submitted case must not block the annotator's next one."""
    caseModel, assignmentModel = models
    case = _case(caseModel, "waiting")
    alice = _user("alice")
    caseModel.claim(case["_id"], alice["_id"])
    assignment = assignmentModel.createAssignment(case, alice)

    assert assignmentModel.countOpenForUser(alice["_id"]) == 1
    assignment = assignmentModel.transition(assignment, st.DOWNLOAD)
    assignmentModel.transition(assignment, st.SUBMIT)
    assert assignmentModel.countOpenForUser(alice["_id"]) == 0


def test_the_annotator_record_drives_the_sampling_policy(models):
    caseModel, assignmentModel = models
    alice = _user("alice")

    for i in range(3):
        case = _case(caseModel, f"c{i}")
        caseModel.claim(case["_id"], alice["_id"])
        assignment = assignmentModel.createAssignment(case, alice)
        assignment = assignmentModel.transition(assignment, st.DOWNLOAD)
        assignment = assignmentModel.transition(assignment, st.SUBMIT)
        assignmentModel.transition(assignment, st.APPROVE)

    record = assignmentModel.recordFor(alice["_id"])
    assert record.approved == 3
    assert record.rejected == 0
    assert record.clean_streak == 3
    # Still inside the five-case training gate, so everything is reviewed.
    assert pol.review_rate(record, pol.SamplingPolicy()) == 1.0


def test_a_rejection_resets_the_clean_streak(models):
    caseModel, assignmentModel = models
    alice = _user("alice")

    def run(name, finalEvent):
        case = _case(caseModel, name)
        caseModel.claim(case["_id"], alice["_id"])
        assignment = assignmentModel.createAssignment(case, alice)
        assignment = assignmentModel.transition(assignment, st.DOWNLOAD)
        assignment = assignmentModel.transition(assignment, st.SUBMIT)
        assignmentModel.transition(assignment, finalEvent)

    for i in range(6):
        run(f"ok{i}", st.APPROVE)
    run("bad", st.REJECT)

    record = assignmentModel.recordFor(alice["_id"])
    assert record.approved == 6
    assert record.rejected == 1
    assert record.clean_streak == 0
    assert pol.review_rate(record, pol.SamplingPolicy()) == 1.0, "probation"


def test_the_sweeper_finds_an_expired_lease(models):
    import datetime

    caseModel, assignmentModel = models
    case = _case(caseModel, "abandoned")
    alice = _user("alice")
    caseModel.claim(case["_id"], alice["_id"])
    assignment = assignmentModel.createAssignment(case, alice)

    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    assignmentModel.collection.update_one(
        {"_id": assignment["_id"]}, {"$set": {"deadline": past}})

    reclaimable = assignmentModel.reclaimable(pol.SamplingPolicy())
    assert [a["_id"] for a in reclaimable] == [assignment["_id"]]


def test_the_sweeper_leaves_a_healthy_lease_alone(models):
    caseModel, assignmentModel = models
    case = _case(caseModel, "in-progress")
    alice = _user("alice")
    caseModel.claim(case["_id"], alice["_id"])
    assignment = assignmentModel.createAssignment(case, alice)
    assignmentModel.heartbeat(assignment)

    assert assignmentModel.reclaimable(pol.SamplingPolicy()) == []


# -------------------------------------------------------------- burn-down


def test_case_counts_match_the_shared_state_module(models):
    caseModel, _ = models
    pending = _case(caseModel, "pending")  # noqa: F841
    busy = _case(caseModel, "busy")
    done = _case(caseModel, "done")
    gone = _case(caseModel, "gone")

    caseModel.claim(busy["_id"], _user("a")["_id"])
    caseModel.claim(done["_id"], _user("b")["_id"])
    caseModel.completeSlot(done["_id"])
    caseModel.retire(gone, "bad data")

    counts = caseModel.countByStatus()
    assert counts[st.CASE_PENDING] == 1
    assert counts[st.CASE_IN_PROGRESS] == 1
    assert counts[st.CASE_COMPLETE] == 1
    assert counts[st.CASE_RETIRED] == 1


def test_the_mongo_servability_predicate_agrees_with_the_python_one(models):
    """Two implementations of one rule; this is what keeps them honest."""
    caseModel, _ = models
    scenarios = [
        (1, 0, 0, False), (1, 1, 0, False), (1, 0, 1, False),
        (2, 0, 1, False), (2, 1, 1, False), (2, 2, 0, False),
        (1, 0, 0, True),
    ]
    for i, (wanted, active, approved, retired) in enumerate(scenarios):
        case = _case(caseModel, f"scenario-{i}", replicasWanted=wanted)
        caseModel.collection.update_one({"_id": case["_id"]}, {"$set": {
            "activeCount": active, "approvedCount": approved, "retired": retired}})

        expected = st.servable(wanted, active, approved, retired)
        query = dict(caseModel.SERVABLE_QUERY)
        query["_id"] = case["_id"]
        actual = caseModel.collection.count_documents(query) == 1
        assert actual == expected, (wanted, active, approved, retired)
