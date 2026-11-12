"""Give an annotator back their own submitted reads, for their own revision (#315).

    segqueue14-reopen --login <login> --submitted-before YYYY-MM-DD [--apply]

Without ``--apply`` it is a dry run: it lists what it would reopen and writes nothing.

**Which assignments.** That login's pool assignments (never the annotator benchmark,
D43; never anybody else's) that are still ``submitted`` or ``under_review`` and whose
latest annotator submission was made before ``--submitted-before``, read as midnight
US Eastern time. An ``approved`` read is never touched.

**What happens to each** (``--apply``):

* the assignment goes back to the annotator's open queue (``assigned``), with a fresh
  lease, attempt + 1 and ``submittedAt`` cleared (the ``reopen`` event,
  ``segqueue.states``). A reviewer's claim ends with it; a reviewer who approves the
  old read afterwards is refused (``rest/review.py``);
* the submission stays, as history. It is marked ``reopenedAt`` and from then on it
  is not an annotator read: the quality report, pair scoring and the export leave it
  out. The resubmission is scored and paired as usual;
* ``startFileId`` on the assignment names the old read's file, which the module
  (protocol 19, 0.19.0) loads as the starting point, every class whole (D39). An
  older module is told to update before it can open or submit that case;
* a note on the case thread says the case was reopened, and why. It names no login:
  the pair partner can read the thread, and blind stays blind.

Reopened cases are served before any new case and do not count against the quota.
Running ``--apply`` twice is a no-op: a reopened assignment is no longer submitted.
"""

import argparse
import datetime
import sys

from segqueue import states as st
from segqueue14 import plan as sqplan

#: The issue the lead asked under; named in the audit note.
ISSUE = 315
#: The cut-off date is a calendar day in the project's time zone.
TIME_ZONE = 'America/New_York'
NOTE_TEXT = ("Reopened for the annotator's own revision at the lead's request "
             f"(#{ISSUE}).")


def cutoff(day):
    """``YYYY-MM-DD`` as that day's midnight in US Eastern time, in UTC."""
    from zoneinfo import ZoneInfo

    try:
        date = datetime.date.fromisoformat(str(day))
    except ValueError:
        raise SystemExit(
            f'REFUSED: --submitted-before takes YYYY-MM-DD, not {day!r}') from None
    local = datetime.datetime(date.year, date.month, date.day, tzinfo=ZoneInfo(TIME_ZONE))
    return local.astimezone(datetime.timezone.utc)


def _utc(dt):
    """Mongo hands datetimes back naive; they are UTC."""
    if dt is not None and dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _eastern(dt):
    from zoneinfo import ZoneInfo

    return _utc(dt).astimezone(ZoneInfo(TIME_ZONE)).strftime('%Y-%m-%d %H:%M %Z')


def _latestRead(assignment):
    from .models import Submission14
    from .models.submission import ANNOTATOR

    return Submission14().findOne(
        {'assignmentId': assignment['_id'], 'authorRole': ANNOTATOR},
        sort=[('created', -1), ('_id', -1)])


def matching(user, before):
    """``[(assignment, case, submission)]``: what ``reopen`` would reopen."""
    from .models import Assignment14, Case14

    benchmarkIds = [c['_id'] for c in Case14().find({'benchmark': True}, fields=['_id'])]
    found = []
    for assignment in Assignment14().find({
            'userId': user['_id'], 'state': {'$in': [st.SUBMITTED, st.UNDER_REVIEW]},
            'kind': {'$ne': sqplan.KIND_BENCHMARK}, 'caseId': {'$nin': benchmarkIds}},
            sort=[('submittedAt', 1), ('_id', 1)]):
        case = Case14().load(assignment['caseId'], force=True)
        if case is None or case.get('benchmark'):
            continue
        submission = _latestRead(assignment)
        if submission is None or _utc(submission['created']) >= before:
            continue
        found.append((assignment, case, submission))
    return found


def _reviewer(assignment):
    from girder.models.user import User

    if assignment['state'] != st.UNDER_REVIEW:
        return None
    reviewer = User().load(assignment['reviewerId'], force=True) \
        if assignment.get('reviewerId') else None
    return (reviewer or {}).get('login') or 'a reviewer'


def reopenOne(assignment, submission, policy=None):
    """Reopen one assignment. Returns it, or ``None`` if its state moved meanwhile."""
    from .models import Assignment14, Note14, Submission14
    from .models.submission import ANNOTATOR

    now = datetime.datetime.now(datetime.timezone.utc)
    reads = {'assignmentId': assignment['_id'], 'authorRole': ANNOTATOR,
             'reopenedAt': None}
    # Marked first, so that from the moment the read is back with its annotator no
    # worker pass can pair it, score it or approve on it; undone if the move fails.
    marked = [s['_id'] for s in Submission14().find(reads, fields=['_id'])]
    Submission14().collection.update_many({'_id': {'$in': marked}},
                                          {'$set': {'reopenedAt': now}})
    try:
        reopened = Assignment14().transition(
            assignment, st.REOPEN, policy=policy,
            startFileId=submission['fileId'], startSubmissionId=submission['_id'],
            reviewerId=None, needsReview=False)
    except st.TransitionError:
        Submission14().collection.update_many(
            {'_id': {'$in': marked}, 'reopenedAt': now}, {'$set': {'reopenedAt': None}})
        return None
    Note14().systemNote(assignment['caseId'], NOTE_TEXT)
    return reopened


def runReopen(login, submittedBefore, apply=False, out=print):
    """List (and with ``apply`` reopen) ``login``'s matching reads. Returns the rows."""
    from girder.models.user import User

    from .settings import getPolicy

    login = (login or '').strip().lower()
    if not login or ',' in login:
        raise SystemExit('REFUSED: --login takes exactly one login')
    user = User().findOne({'login': login})
    if user is None:
        raise SystemExit(f'REFUSED: no such login: {login}')
    before = cutoff(submittedBefore)
    policy = getPolicy()

    rows = []
    found = matching(user, before)
    out(f'{login}: {len(found)} pool read(s) submitted before {submittedBefore} '
        f'(midnight {TIME_ZONE}), still submitted or under review:')
    for assignment, case, submission in found:
        row = {'case': case.get('name', str(case['_id'])), 'state': assignment['state'],
               'submitted': _eastern(submission['created']),
               'reviewer': _reviewer(assignment), 'assignmentId': str(assignment['_id'])}
        if apply:
            row['done'] = 'reopened' if reopenOne(assignment, submission, policy) \
                else 'skipped: its state changed meanwhile'
        rows.append(row)
        held = f"held by {row['reviewer']}" if row['reviewer'] else 'no reviewer holds it'
        out(f"  {row['case']}: {row['state']}, submitted {row['submitted']}, {held}"
            + (f"; {row['done']}" if apply else ''))
    if not apply:
        out('dry run: nothing written. --apply reopens them.')
    return rows


def buildParser():
    parser = argparse.ArgumentParser(
        prog='segqueue14-reopen',
        description="Reopen an annotator's own submitted reads for their revision (#315).")
    parser.add_argument('--login', required=True, help='The one annotator, by login.')
    parser.add_argument('--submitted-before', required=True, metavar='YYYY-MM-DD',
                        help=f'Reads submitted before this day (midnight {TIME_ZONE}).')
    parser.add_argument('--apply', action='store_true',
                        help='Reopen them. Without it, a dry run.')
    return parser


def main(argv=None):  # pragma: no cover - CLI entry point
    args = buildParser().parse_args(argv)
    runReopen(args.login, args.submitted_before, apply=args.apply)
    return 0


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
