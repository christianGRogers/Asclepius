"""Who may read and add to a SegQueue14 case's note thread, against a real Girder
and MongoDB.

Marked ``needs_mongo`` (through ``test_segqueue_server14``'s fixtures) and run in
CI's server job, which refuses skips. Synthetic data only.

Plugin 0.7.1: a reviewer (or an admin) reads the thread of any case without being
in the annotator group, so module 0.24.1 can show it while a submission is open for
review. An annotator still reads only cases they have worked on, and adding a note
still needs an annotator.
"""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import test_segqueue_server14 as base  # noqa: E402
from test_segqueue_server14 import _as, _readyProject, _refusal, _resource  # noqa: E402

girder_db = base.girder_db
world = base.world

pytestmark = pytest.mark.needs_mongo


def _reviewerOnly(world):
    """A user in the reviewer group and not the annotator group, and not an admin."""
    from girder.models.group import Group
    from girder.models.user import User

    user = User().createUser("rita", "password1", "rita", "X", "rita@example.org")
    Group().addUser(Group().findOne({"name": "segqueue14-reviewers"}), user)
    return User().load(user["_id"], force=True)


def _threadOn(world):
    """Anna takes a case and posts to it: the case, and the thread on it."""
    _readyProject(world)
    queue = _resource()
    _as(world.people["anna"])
    info = queue.nextCase(clientProtocol=21)
    queue.addNote(caseId=info["caseId"], text="Distal RCA is faint, left it short.")
    return queue, info["caseId"]


def test_a_reviewer_who_is_not_an_annotator_reads_the_thread(world):
    queue, caseId = _threadOn(world)
    _as(_reviewerOnly(world))
    [note] = queue.listNotes(caseId=caseId)
    assert note["text"] == "Distal RCA is faint, left it short."
    assert note["author"] and note["caseId"] == caseId


def test_an_admin_reads_the_thread(world):
    queue, caseId = _threadOn(world)
    _as(world.admin)
    assert [n["text"] for n in queue.listNotes(caseId=caseId)] == [
        "Distal RCA is faint, left it short."]


def test_an_involved_annotator_reads_the_thread(world):
    queue, caseId = _threadOn(world)
    _as(world.people["anna"])
    assert [n["text"] for n in queue.listNotes(caseId=caseId)] == [
        "Distal RCA is faint, left it short."]


def test_an_annotator_not_on_the_case_is_still_refused(world):
    queue, caseId = _threadOn(world)
    _as(world.people["cathy"])
    err = _refusal(queue.listNotes, caseId=caseId)
    assert err.code == 403 and err.extra["segqueueError"] == "not_your_case"


def test_a_user_in_neither_group_is_still_refused(world):
    from girder.models.user import User

    queue, caseId = _threadOn(world)
    nobody = User().createUser("nora", "password1", "nora", "X", "nora@example.org")
    _as(nobody)
    err = _refusal(queue.listNotes, caseId=caseId)
    assert err.code == 403 and err.extra["segqueueError"] == "not_an_annotator"


def test_a_reviewer_who_is_not_an_annotator_still_cannot_add_a_note(world):
    from girder_segqueue14.models import Note14

    queue, caseId = _threadOn(world)
    _as(_reviewerOnly(world))
    err = _refusal(queue.addNote, caseId=caseId, text="Reviewer comment.")
    assert err.code == 403 and err.extra["segqueueError"] == "not_an_annotator"
    from bson import ObjectId

    assert len(Note14().forCase(ObjectId(caseId))) == 1


def test_a_reviewer_gets_the_whole_thread_every_annotator_and_the_auto_screener(world):
    """The lead's rule: the reviewer reads the case's whole thread, not just the
    open submission's annotator -- every annotator's notes and the auto screener's
    ``namedNote`` (``authorId`` None, ``system``), oldest first."""
    import datetime

    from bson import ObjectId
    from girder_segqueue14.models import Case14, Note14

    queue, caseId = _threadOn(world)                 # anna's note
    # A two-read case, so a second annotator can be given it by hand.
    Case14().collection.update_one({"_id": ObjectId(caseId)},
                                   {"$set": {"replicasWanted": 2}})
    _as(world.admin)
    queue.assignCase(caseId=caseId, userId=str(world.people["bobby"]["_id"]))
    _as(world.people["bobby"])
    queue.addNote(caseId=caseId, text="Second read: LCx ends early here too.")
    case = base_case(caseId)
    _as(world.admin)
    assert queue.addAutoNote(caseName=case["name"], text="Seed looks complete.",
                             author="auto screener", once=True)["created"] is True

    # Mongo keeps milliseconds: give the notes distinct times, in the order
    # they were written (ObjectIds from one process increase).
    start = datetime.datetime(2026, 11, 20, 12, 0, tzinfo=datetime.timezone.utc)
    written = sorted(Note14().collection.find({"caseId": ObjectId(caseId)}),
                     key=lambda n: n["_id"])
    for i, note in enumerate(written):
        Note14().collection.update_one(
            {"_id": note["_id"]},
            {"$set": {"created": start + datetime.timedelta(minutes=i)}})

    _as(_reviewerOnly(world))
    thread = queue.listNotes(caseId=caseId)
    assert [n["text"] for n in thread] == [
        "Distal RCA is faint, left it short.",
        "admin assigned this case to bobby.",       # a system note, kept too
        "Second read: LCx ends early here too.",
        "Seed looks complete.",
    ]
    people = [n for n in thread if not n["system"]]
    assert [n["authorId"] for n in people] == [
        str(world.people["anna"]["_id"]), str(world.people["bobby"]["_id"])]
    screener = thread[-1]
    assert screener["author"] == "auto screener" and screener["system"] is True
    assert not screener["authorId"]
    assert thread[1]["system"] is True


def base_case(caseId):
    from bson import ObjectId
    from girder_segqueue14.models import Case14

    return Case14().load(ObjectId(caseId), force=True)
