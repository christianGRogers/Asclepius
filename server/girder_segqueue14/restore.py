"""Restore reads reopened (#315) and then expired by the sweep as ordinary reads (D48).

    segqueue14-restore-reopened --login <login> [--apply]

Without ``--apply`` it is a dry run: it lists what it would restore and writes nothing.

**Which assignments.** That login's assignments that were reopened (``reopenedAt``),
then expired by the lease sweep after the reopen (released with the sweep's
``releaseReason`` and no ``reviewerId``: ``report.freedBy`` says ``expired``), with no
read resubmitted on them since. Never one its annotator released, one a
reviewer returned to the pool, one resubmitted, or anybody else's. This is what the
0.5.0 sweep did to reopened reads: it judged their new attempt by the old one's
heartbeat and expired them within the hour (fixed in 0.5.1).

**What happens to each** (``--apply``), the reverse of the reopen:

* the original annotator read (the newest one marked ``reopenedAt`` by the reopen)
  has ``reopenedAt`` cleared, so the export, the quality report and pair scoring
  count it again;
* the assignment goes back to ``submitted``, the state a reopen takes it from
  (``under_review`` too, but the reviewer's claim ended with the reopen), with
  ``needsReview`` set so it is in the reviewers' queue to approve or return like any
  read, ``submissionId`` the restored read, ``submittedAt`` its time, and
  ``startFileId``, ``startSubmissionId``, ``reviewerId``, ``releasedAt`` and
  ``releaseReason`` cleared. ``restoredAt`` and ``restoredFrom`` (the release that is
  undone) record the repair; ``reopenedAt`` stays, as history;
* the case's ``activeCount`` goes up by one, for the slot the read holds again. The
  case keeps the reads made since, so it may hold three: D48 accepts that;
* a note on the case thread says the read was restored. It names no login.

The annotator is not sent the cases again (D48). Running ``--apply`` twice is a no-op:
a restored assignment is no longer released. The assignment's state is set directly,
not through ``Assignment14.transition``: ``released -> submitted`` is no event of the
lifecycle and must not become one; this one-off repair is the only writer, guarded on
the state it read.
"""

import argparse
import datetime
import sys

from segqueue import states as st

#: The decision the repair implements; named in the audit note.
DECISION = 'D48'
NOTE_TEXT = ('An annotator read reopened for revision (#315) and then expired by the '
             'lease sweep was restored as an ordinary read at the lead\'s decision '
             f'({DECISION}).')


def _utc(dt):
    """Mongo hands datetimes back naive; they are UTC."""
    if dt is not None and dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _originalRead(assignment):
    """The read the reopen set aside: the newest annotator submission marked
    ``reopenedAt``, made before the reopen. None if there is none."""
    from .models import Submission14
    from .models.submission import ANNOTATOR

    return Submission14().findOne(
        {'assignmentId': assignment['_id'], 'authorRole': ANNOTATOR,
         'reopenedAt': {'$ne': None}, 'created': {'$lt': assignment['reopenedAt']}},
        sort=[('created', -1), ('_id', -1)])


def _resubmitted(assignment):
    from .models import Submission14
    from .models.submission import ANNOTATOR

    return Submission14().findOne({'assignmentId': assignment['_id'],
                                   'authorRole': ANNOTATOR, 'reopenedAt': None}) is not None


def matching(user):
    """``[(assignment, case, submission)]``: what ``restore`` would restore."""
    from .models import Assignment14, Case14
    from .report import freedBy

    found = []
    for assignment in Assignment14().find({
            'userId': user['_id'], 'state': st.RELEASED, 'reopenedAt': {'$ne': None}},
            sort=[('reopenedAt', 1), ('_id', 1)]):
        released = _utc(assignment.get('releasedAt'))
        if freedBy(assignment) != 'expired' or released is None \
                or released < _utc(assignment['reopenedAt']):
            continue
        if _resubmitted(assignment):
            continue
        submission = _originalRead(assignment)
        case = Case14().load(assignment['caseId'], force=True)
        if submission is None or case is None:
            continue
        found.append((assignment, case, submission))
    return found


def restoreOne(assignment, submission):
    """Restore one. Returns the assignment, or ``None`` if its state moved meanwhile."""
    from pymongo import ReturnDocument

    from .models import Assignment14, Case14, Note14, Submission14

    now = datetime.datetime.now(datetime.timezone.utc)
    restored = Assignment14().collection.find_one_and_update(
        {'_id': assignment['_id'], 'state': st.RELEASED,
         'releasedAt': assignment.get('releasedAt')},
        {'$set': {
            'state': st.SUBMITTED, 'submissionId': submission['_id'],
            'submittedAt': submission['created'], 'needsReview': True,
            'startFileId': None, 'startSubmissionId': None, 'reviewerId': None,
            'releasedAt': None, 'releaseReason': None, 'updated': now,
            'restoredAt': now,
            'restoredFrom': {'releasedAt': assignment.get('releasedAt'),
                             'releaseReason': assignment.get('releaseReason'),
                             'decision': DECISION}}},
        return_document=ReturnDocument.AFTER)
    if restored is None:
        return None
    Submission14().collection.update_one({'_id': submission['_id']},
                                         {'$set': {'reopenedAt': None}})
    Case14().collection.update_one({'_id': assignment['caseId']},
                                   {'$inc': {'activeCount': 1}, '$set': {'updated': now}})
    Note14().systemNote(assignment['caseId'], NOTE_TEXT)
    return restored


def runRestore(login, apply=False, out=print):
    """List (and with ``apply`` restore) ``login``'s matching reads. Returns the rows."""
    from girder.models.user import User

    from .reopen import _eastern

    login = (login or '').strip().lower()
    if not login or ',' in login:
        raise SystemExit('REFUSED: --login takes exactly one login')
    user = User().findOne({'login': login})
    if user is None:
        raise SystemExit(f'REFUSED: no such login: {login}')

    rows = []
    found = matching(user)
    out(f'{login}: {len(found)} read(s) reopened (#315), then expired by the sweep, '
        'not resubmitted:')
    for assignment, case, submission in found:
        row = {'case': case.get('name', str(case['_id'])),
               'submitted': _eastern(submission['created']),
               'reopened': _eastern(assignment['reopenedAt']),
               'expired': _eastern(assignment['releasedAt']),
               'reason': assignment.get('releaseReason') or '-',
               'assignmentId': str(assignment['_id'])}
        if apply:
            row['done'] = 'restored' if restoreOne(assignment, submission) \
                else 'skipped: its state changed meanwhile'
        rows.append(row)
        out(f"  {row['case']}: submitted {row['submitted']}, reopened {row['reopened']}, "
            f"expired {row['expired']} ({row['reason']})"
            + (f"; {row['done']}" if apply else ''))
    if not apply:
        out('dry run: nothing written. --apply restores them.')
    return rows


def buildParser():
    parser = argparse.ArgumentParser(
        prog='segqueue14-restore-reopened',
        description='Restore reads reopened (#315) and then expired by the sweep as '
                    f'ordinary annotator reads ({DECISION}).')
    parser.add_argument('--login', required=True, help='The one annotator, by login.')
    parser.add_argument('--apply', action='store_true',
                        help='Restore them. Without it, a dry run.')
    return parser


def main(argv=None):  # pragma: no cover - CLI entry point
    args = buildParser().parse_args(argv)
    runRestore(args.login, apply=args.apply)
    return 0


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
