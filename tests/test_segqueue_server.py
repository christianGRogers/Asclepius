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

    # Girder binds its connection the first time a girder.models module is
    # imported. If anything did that before this fixture ran -- a test module
    # importing girder.models at collection time, say -- the redirect above was
    # too late and the models below are pointed at the *default* database. The
    # `models` fixture clears collections, so being wrong here empties somebody's
    # real case pool rather than a scratch one. Refuse instead.
    from girder_segqueue.models import Case

    bound = Case().collection.database.name
    if bound != dbName:
        pytest.fail(
            f"girder is bound to database {bound!r}, not the scratch database "
            f"{dbName!r}. Some module imported girder.models before this fixture "
            "ran; import girder inside test functions, not at module scope.")

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


# ------------------------------------------------------- the incoming drop box


def _emptyIncoming():
    """Start each drop-box test from empty, so siblings cannot leak into it."""
    from girder.models.folder import Folder
    from girder.models.item import Item
    from girder.models.upload import Upload
    from girder_segqueue.utils import incomingFolder

    for item in list(Folder().childItems(incomingFolder())):
        Item().remove(item)
    Upload().collection.delete_many({"parentType": "item"})


def _incomingItem(name, ageSeconds):
    """Plant an item in the incoming folder, backdated by ``ageSeconds``."""
    import datetime

    from girder.models.item import Item
    from girder_segqueue.utils import incomingFolder

    folder = incomingFolder()
    item = Item().createItem(name=name, creator=_adminUser(), folder=folder)
    stamp = (datetime.datetime.now(datetime.timezone.utc)
             - datetime.timedelta(seconds=ageSeconds))
    Item().collection.update_one(
        {"_id": item["_id"]}, {"$set": {"created": stamp, "updated": stamp}})
    return Item().load(item["_id"], force=True)


def _adminUser():
    """A real Girder user, because Item().createItem needs a creator."""
    from girder.models.user import User

    existing = User().findOne({"login": "sweeptest"})
    if existing is not None:
        return existing
    return User().createUser(
        login="sweeptest", password="sweeptest-password", email="sweep@example.edu",
        firstName="Sweep", lastName="Test", admin=True)


def test_the_sweeper_empties_only_stale_uploads_from_incoming(girder_db):
    """The drop box is the one folder annotators can write to, so it must drain.

    Its docstring claimed the sweeper emptied it long before anything did.
    """
    _emptyIncoming()
    from girder.models.item import Item
    from girder_segqueue.maintenance import INCOMING_MAX_AGE_SECONDS, sweepIncoming

    stale = _incomingItem("abandoned.nrrd", INCOMING_MAX_AGE_SECONDS + 3600)
    fresh = _incomingItem("in-progress.nrrd", 60)

    discarded = sweepIncoming()

    assert [d["itemId"] for d in discarded] == [str(stale["_id"])]
    assert Item().load(stale["_id"], force=True) is None, "stale upload survived"
    assert Item().load(fresh["_id"], force=True) is not None, "fresh upload deleted"


def test_the_sweeper_leaves_an_upload_still_streaming_alone(girder_db):
    """An item exists from the first chunk; deleting it races the uploader."""
    _emptyIncoming()
    from girder.models.item import Item
    from girder.models.upload import Upload
    from girder_segqueue.maintenance import INCOMING_MAX_AGE_SECONDS, sweepIncoming

    item = _incomingItem("slow-link.nrrd", INCOMING_MAX_AGE_SECONDS + 3600)
    Upload().collection.insert_one(
        {"parentType": "item", "parentId": item["_id"], "received": 1})

    assert sweepIncoming() == []
    assert Item().load(item["_id"], force=True) is not None


def test_sweeping_incoming_twice_discards_nothing_the_second_time(girder_db):
    _emptyIncoming()
    from girder_segqueue.maintenance import INCOMING_MAX_AGE_SECONDS, sweepIncoming

    _incomingItem("abandoned-twice.nrrd", INCOMING_MAX_AGE_SECONDS + 3600)

    assert len(sweepIncoming()) == 1
    assert sweepIncoming() == []


def test_a_dry_run_sweep_of_incoming_deletes_nothing(girder_db):
    _emptyIncoming()
    from girder.models.item import Item
    from girder_segqueue.maintenance import INCOMING_MAX_AGE_SECONDS, sweepIncoming

    item = _incomingItem("dry-run.nrrd", INCOMING_MAX_AGE_SECONDS + 3600)

    assert [d["itemId"] for d in sweepIncoming(dryRun=True)] == [str(item["_id"])]
    assert Item().load(item["_id"], force=True) is not None


# ------------------------------------------------------------ segqueue-export
#
# These live here rather than in their own module for a reason worth keeping:
# importing `girder_segqueue` binds Girder's Mongo connection, and a separate
# test file would do that at its own execution time -- before this file's
# fixture can redirect the connection at a scratch database. The `models`
# fixture then clears collections, so the pool it clears would be the live one.


def _segments():
    from segqueue.protocol import SegmentSpec

    return [
        SegmentSpec(name="left_main", label=1),
        SegmentSpec(name="left_anterior_descending", label=2),
        SegmentSpec(name="left_circumflex", label=3),
        SegmentSpec(name="right_coronary_artery", label=4),
    ]


def _labelVolume(np):
    """A label volume holding three of the four vessels; LCx is never drawn."""
    labels = np.zeros((4, 4, 4), dtype=np.uint8)
    labels[0, 0, 0] = 1
    labels[1, 1, :2] = 2
    labels[3, 3, 3] = 4
    return labels


def test_each_vessel_becomes_its_own_binary_mask(girder_db):
    np = pytest.importorskip("numpy")
    pytest.importorskip("SimpleITK")
    from girder_segqueue.export import splitLabels

    masks = splitLabels(_labelVolume(np), _segments())

    assert set(masks) == {s.name for s in _segments()}
    assert masks["left_main"].sum() == 1
    assert masks["left_anterior_descending"].sum() == 2
    assert masks["right_coronary_artery"].sum() == 1
    assert set(np.unique(masks["left_main"])) <= {0, 1}, "not binary"


def test_a_vessel_nobody_drew_is_an_empty_mask_not_a_missing_one(girder_db):
    """The distinction the per-vessel layout exists to preserve.

    A merged labels.nii.gz cannot tell "not labelled here" from "not present";
    an empty mask can, so it must still be produced rather than skipped.
    """
    np = pytest.importorskip("numpy")
    pytest.importorskip("SimpleITK")
    from girder_segqueue.export import splitLabels

    masks = splitLabels(_labelVolume(np), _segments())

    assert "left_circumflex" in masks
    assert masks["left_circumflex"].sum() == 0


def test_a_label_value_outside_the_project_is_not_exported(girder_db):
    """A stray value must not silently become somebody else's vessel."""
    np = pytest.importorskip("numpy")
    pytest.importorskip("SimpleITK")
    from girder_segqueue.export import splitLabels

    labels = np.zeros((2, 2, 2), dtype=np.uint8)
    labels[0, 0, 0] = 9

    assert all(m.sum() == 0 for m in splitLabels(labels, _segments()).values())


def test_exported_masks_do_not_overlap(girder_db):
    """Splitting by value cannot produce a voxel claimed by two vessels."""
    np = pytest.importorskip("numpy")
    pytest.importorskip("SimpleITK")
    from girder_segqueue.export import splitLabels

    masks = splitLabels(_labelVolume(np), _segments())

    assert sum(m.astype(int) for m in masks.values()).max() <= 1


def test_unreviewed_work_is_excluded_from_export_by_default(girder_db):
    from girder_segqueue.export import selectable

    assert selectable() == [st.APPROVED]
    assert st.SUBMITTED not in selectable()


def test_unreviewed_work_is_exported_only_when_asked_for(girder_db):
    from girder_segqueue.export import selectable

    assert set(selectable(includeUnreviewed=True)) == {st.APPROVED, st.SUBMITTED}
