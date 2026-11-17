"""An annotator takes back their own submitted read for revision, from the module.

The self-service form of the admin reopen (#315, ``reopen.py``): "My submissions" in
SegQueue14 0.22.0 lists the annotator's own pool reads that are submitted and not yet
approved (``listOwn``), and "Revise" recalls one (``recallOne``).

**The same reopen.** A recall goes through ``reopen.reopenOne``: the read is marked
``reopenedAt`` and leaves the export, the quality report and pair scoring until it is
resubmitted; the assignment takes the ``reopen`` event (a fresh lease and no heartbeat,
#341), attempt + 1, and ``startFileId`` names the read, which the module opens every
class whole (D39). The case's ``activeCount`` does not move: a submitted read already
holds its slot. A note on the case thread says what happened and names no login.

**Refused**, with the sentence the list shows on a disabled row
(``protocol.recall_blocker``): somebody else's assignment; an approved read; the
annotator benchmark (D43); a read a reviewer has claimed (``under_review`` with a
``reviewerId``); and while the annotator holds another open case.

**Race-safe.** The move is ``Assignment14.transition``'s guarded update, so a reviewer
claiming (or approving) the read at the same moment either wins, and the recall is
refused as "a reviewer is looking at this case now" with the read unmarked again, or
loses with a 409 of their own.

**Never strands the read.** A recall takes nothing the annotator cannot have back:
releasing a recalled case that has not been resubmitted (``undoRecall``) puts the
submitted read back exactly as it was -- the same state, review flags, lease and
counts, ``reopenedAt`` cleared -- instead of giving the case to the pool, and the lease
sweep does the same if the annotator never comes back to it (the D48 lesson: a reopened
read the sweep expired was lost until a repair restored it). The recall snapshot is
tied to the attempt it created, so a later admin reopen is never undone this way.
"""

import datetime

from pymongo import ReturnDocument
from segqueue import states as st
from segqueue14 import plan as sqplan
from segqueue14 import protocol

#: On the case thread. Names no login: the pair partner can read the thread.
NOTE_TEXT = "Reopened at the annotator's own request, for revision."
UNDO_NOTE_TEXT = ("The annotator's revision was withdrawn; their submitted read is "
                  "back as it was.")
SWEEP_NOTE_TEXT = ("A revision the annotator started was not finished before its lease "
                   "ran out; their submitted read is back as it was.")

#: Recallable states: a read that is in, or waiting for, review.
RECALLABLE = (st.SUBMITTED, st.UNDER_REVIEW)


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _utc(dt):
    if dt is not None and dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _isBenchmark(assignment, case):
    return assignment.get('kind') == sqplan.KIND_BENCHMARK or bool((case or {}).get('benchmark'))


def _reviewerClaimed(assignment):
    return assignment['state'] == st.UNDER_REVIEW and bool(assignment.get('reviewerId'))


def holdsOpenCase(userId):
    from .models import Assignment14

    return Assignment14().countOpenForUser(userId) > 0


def blocker(assignment, case, holdingOpen):
    """``protocol.recall_blocker`` for a stored assignment: an ``ERR_RECALL_*`` or None."""
    return protocol.recall_blocker(
        assignment['state'], reviewer_claimed=_reviewerClaimed(assignment),
        benchmark=_isBenchmark(assignment, case), holding_open=holdingOpen,
        approved_state=st.APPROVED, recallable_states=RECALLABLE)


def listOwn(user, limit=protocol.MY_SUBMISSIONS_PAGE, offset=0):
    """``(rows, total)``: ``user``'s submitted, not yet approved reads, newest first.

    Every one is listed, the ones that cannot be recalled now included, with the
    reason; whether the user holds an open case is asked once for the page.
    """
    from .models import Assignment14, Case14

    limit = max(1, min(int(limit or protocol.MY_SUBMISSIONS_PAGE),
                       protocol.MY_SUBMISSIONS_MAX_PAGE))
    offset = max(0, int(offset or 0))
    query = {'userId': user['_id'], 'state': {'$in': list(RECALLABLE)}}
    total = Assignment14().collection.count_documents(query)
    holding = holdsOpenCase(user['_id'])
    rows = []
    for assignment in Assignment14().find(
            query, sort=[('submittedAt', -1), ('_id', -1)], limit=limit, offset=offset):
        case = Case14().load(assignment['caseId'], force=True) or {}
        code = blocker(assignment, case, holding)
        submitted = _utc(assignment.get('submittedAt'))
        rows.append(protocol.MySubmission(
            assignment_id=str(assignment['_id']), case_id=str(assignment['caseId']),
            case_name=case.get('name', ''), state=assignment['state'],
            submitted_at=submitted.timestamp() if submitted else None,
            can_recall=code is None,
            reason=protocol.RECALL_MESSAGES.get(code, '') if code else '',
            reason_code=code or ''))
    return rows, total


def _currentRead(assignment):
    """The read the assignment stands on: its ``submissionId``, if it is still an
    annotator read (not already set aside by a reopen)."""
    from .models import Submission14
    from .models.submission import ANNOTATOR

    submissionId = assignment.get('submissionId')
    submission = Submission14().load(submissionId, force=True) if submissionId else None
    if submission is None or submission.get('authorRole') != ANNOTATOR \
            or submission.get('reopenedAt'):
        from .reopen import _latestRead

        submission = _latestRead(assignment)
    if submission is None or submission.get('reopenedAt'):
        return None
    return submission


class RecallRefused(Exception):
    """A recall refused; ``code`` is an ``ERR_RECALL_*``."""

    def __init__(self, code):
        super().__init__(protocol.RECALL_MESSAGES[code])
        self.code = code
        self.status = protocol.RECALL_STATUS[code]


def recallOne(user, assignment, policy=None):
    """Reopen ``assignment`` for ``user``'s own revision. Returns the reopened
    assignment; raises ``RecallRefused``."""
    from .models import Assignment14, Case14
    from .reopen import reopenOne

    if assignment['userId'] != user['_id']:
        raise RecallRefused(protocol.ERR_RECALL_NOT_YOURS)
    case = Case14().load(assignment['caseId'], force=True)
    code = blocker(assignment, case, holdsOpenCase(user['_id']))
    if code:
        raise RecallRefused(code)
    submission = _currentRead(assignment)
    if submission is None:
        raise RecallRefused(protocol.ERR_RECALL_NOT_SUBMITTED)

    # Everything the reopen changes, so that releasing the recalled case (or the
    # sweep) can put the read back exactly as it is now. Tied to the attempt the
    # reopen creates: a later reopen starts another and is never undone by this.
    snapshot = {
        'at': _now(),
        'attempt': st.next_attempt(assignment.get('attempt', 1)),
        'fromAttempt': assignment.get('attempt', 1),
        'state': assignment['state'],
        'submissionId': submission['_id'],
        'submittedAt': assignment.get('submittedAt'),
        'downloadedAt': assignment.get('downloadedAt'),
        'needsReview': assignment.get('needsReview'),
        'reviewerId': assignment.get('reviewerId'),
        'reopenedAt': assignment.get('reopenedAt'),
        'deadline': assignment.get('deadline'),
        'lastHeartbeat': assignment.get('lastHeartbeat'),
    }
    reopened = reopenOne(assignment, submission, policy, note=NOTE_TEXT, recall=snapshot)
    if reopened is None:
        # The guarded move lost: a reviewer claimed or approved it a moment ago, or
        # it moved some other way. Say which, from where it is now.
        now = Assignment14().load(assignment['_id'], force=True) or assignment
        raise RecallRefused(blocker(now, case, False) or protocol.ERR_RECALL_REVIEWING)
    return reopened


def isRecalled(assignment):
    """Recalled by its annotator and not yet resubmitted: the attempt the recall
    created is still open."""
    recall = assignment.get('recall')
    return bool(recall) and assignment['state'] in st.OPEN_STATES \
        and assignment.get('attempt') == recall.get('attempt') \
        and assignment.get('submittedAt') is None


def undoRecall(assignment, note=UNDO_NOTE_TEXT, why='released by annotator'):
    """Put a recalled read back as it was before the recall. Returns the assignment,
    or ``None`` if it is not a recalled, unresubmitted read any more.

    The state is set directly, guarded on what was read, like ``restore.py``: going
    back to ``submitted`` is no event of the lifecycle, and the recall snapshot is
    the only thing that may say what to go back to. ``activeCount`` is not touched:
    the read held its slot all along.
    """
    from .models import Assignment14, Note14, Submission14
    from .models.submission import ANNOTATOR

    if not isRecalled(assignment):
        return None
    recall = assignment['recall']
    now = _now()
    restored = Assignment14().collection.find_one_and_update(
        {'_id': assignment['_id'], 'state': assignment['state'],
         'attempt': recall['attempt'], 'submittedAt': None},
        {'$set': {
            # under_review came back only without a claim; it waits in the queue.
            'state': st.SUBMITTED,
            'attempt': recall['fromAttempt'],
            'submissionId': recall['submissionId'],
            'submittedAt': recall['submittedAt'],
            'downloadedAt': recall['downloadedAt'],
            'needsReview': recall['needsReview'],
            'reviewerId': recall['reviewerId'],
            'reopenedAt': recall['reopenedAt'],
            'deadline': recall['deadline'],
            'lastHeartbeat': recall['lastHeartbeat'],
            'startFileId': None, 'startSubmissionId': None,
            'recall': None,
            'recallUndone': {'at': now, 'why': why, 'recalledAt': recall['at']},
            'updated': now}},
        return_document=ReturnDocument.AFTER)
    if restored is None:
        return None
    # The reads the recall's reopen set aside, and only those: an admin reopen of an
    # earlier attempt stamped its reads before this recall began.
    Submission14().collection.update_many(
        {'assignmentId': assignment['_id'], 'authorRole': ANNOTATOR,
         'reopenedAt': {'$gte': recall['at']}},
        {'$set': {'reopenedAt': None}})
    Note14().systemNote(assignment['caseId'], note)
    return restored
