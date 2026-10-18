"""SegQueue14 admin endpoints, adapted from ``girder_segqueue.rest.admin``, plus
the prelabel routes: attach one uploaded prelabel to a case (``POST
/segqueue14/prelabels/attach``) and count prelabels by model version (``GET
/segqueue14/prelabels/status``). Bulk attach and refresh is the
``segqueue14-prelabels`` CLI, which applies the same rules.

Admin endpoints: people, cases, the burn-down, and the lease sweeper.

Thin on purpose. Girder's stock admin UI already creates users, resets
passwords and browses files, so nothing here re-implements any of that -- these
are only the operations that need SegQueue's own data model to make sense.
"""

import datetime

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.models.group import Group
from girder.models.user import User
from segqueue import policy as pol
from segqueue import states as st

from ..constants import ANNOTATOR_GROUP, QUOTA_FIELD, REVIEWER_GROUP
from ..maintenance import sweep as sweepStranded
from ..models import Assignment14 as Assignment
from ..models import Case14 as Case
from ..models import Note14 as Note
from ..models import Submission14 as Submission
from ..settings import getPolicy
from ..utils import ensureGroups, refuse


class AdminResource14(Resource):
    """Registered onto the queue resource so paths read ``/segqueue14/...``."""

    def attachTo(self, parent):
        parent.route('GET', ('stats',), self.stats)
        parent.route('GET', ('stats', 'annotators'), self.annotatorStats)
        parent.route('POST', ('users',), self.createAnnotator)
        parent.route('PATCH', ('users', ':userId'), self.updateAnnotator)
        parent.route('POST', ('case', ':caseId', 'retire'), self.retireCase)
        parent.route('POST', ('case', ':caseId', 'assign'), self.assignCase)
        parent.route('POST', ('sweep',), self.sweep)
        parent.route('POST', ('prelabels', 'attach'), self.attachPrelabel)
        parent.route('GET', ('prelabels', 'status'), self.prelabelStatus)
        parent.route('POST', ('notes', 'auto'), self.addAutoNote)
        return self

    # --------------------------------------------------------------- stats

    @access.admin
    @autoDescribeRoute(
        Description('Project burn-down: case counts and a projected finish date.')
    )
    def stats(self):
        counts = Case().countByStatus()
        total = sum(counts.values())
        done = counts.get(st.CASE_COMPLETE, 0)

        velocity = self._approvalsPerDay(days=14)
        remaining = max(0, total - done - counts.get(st.CASE_RETIRED, 0))
        etaDays = (remaining / velocity) if velocity > 0 else None

        return {
            'cases': counts,
            'total': total,
            'completeFraction': (done / total) if total else 0.0,
            'approvalsPerDay': round(velocity, 2),
            'remaining': remaining,
            'projectedDaysRemaining': round(etaDays, 1) if etaDays is not None else None,
            'projectedFinish': (
                (datetime.datetime.now(datetime.timezone.utc)
                 + datetime.timedelta(days=etaDays)).date().isoformat()
                if etaDays is not None else None
            ),
            'reviewBacklog': Assignment().collection.count_documents(
                {'state': st.SUBMITTED, 'needsReview': True}),
            'underReview': Assignment().collection.count_documents(
                {'state': st.UNDER_REVIEW}),
            # Per serve tier: how far through the D14/D16 order the project is.
            'tiers': Case().countByTier(),
        }

    def _approvalsPerDay(self, days=14):
        """Recent velocity, not all-time.

        All-time average is dominated by the ramp-up weeks and always projects a
        finish date later than reality. A trailing window answers the question
        an admin is actually asking: at the rate we are going *now*, when?
        """
        since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        n = Assignment().collection.count_documents({
            'state': st.APPROVED, 'decidedAt': {'$gte': since}})
        return n / float(days)

    @access.admin
    @autoDescribeRoute(
        Description('Per-annotator throughput, timing and quality.')
        .notes('Median time per case is the single most useful column: work that '
               'is implausibly fast is the best early signal of carelessness, '
               'and it shows up here long before a reviewer notices.')
    )
    def annotatorStats(self):
        rows = []
        group = Group().findOne({'name': ANNOTATOR_GROUP})
        if group is None:
            return rows

        for user in User().find({'groups': group['_id']}):
            rows.append(self._annotatorRow(user))
        rows.sort(key=lambda r: r['approved'], reverse=True)
        return rows

    def _annotatorRow(self, user):
        userId = user['_id']
        record = Assignment().recordFor(userId)
        policy = getPolicy()

        durations = self._caseDurations(userId)
        agreements = self._agreementScores(userId)

        return {
            'userId': str(userId),
            'login': user.get('login', ''),
            'name': f"{user.get('firstName', '')} {user.get('lastName', '')}".strip(),
            'approved': record.approved,
            'rejected': record.rejected,
            'rejectionRate': (record.rejected / record.submitted) if record.submitted else 0.0,
            'open': Assignment().countOpenForUser(userId),
            'medianSecondsPerCase': _median(durations),
            'fastestSeconds': min(durations) if durations else None,
            'meanAgreementDice': (sum(agreements) / len(agreements)) if agreements else None,
            'nScored': len(agreements),
            'currentReviewRate': pol.review_rate(record, policy),
            'quota': user.get(QUOTA_FIELD),
        }

    def _caseDurations(self, userId):
        return [
            s['annotationSeconds']
            for s in Submission().find({'userId': userId}, fields=['annotationSeconds'])
            if s.get('annotationSeconds')
        ]

    def _agreementScores(self, userId):
        """Per-submission mean Dice, skipping anything that is not a real number.

        ``pol.usable_score`` rather than ``is not None``, because NaN is not None:
        it passes an identity check and it propagates through the ``sum()`` below,
        so one stored NaN used to turn this annotator's whole
        ``meanAgreementDice`` into NaN with nothing on the dashboard to say which
        case caused it. ``agreement()`` no longer emits one, but records written
        before that fix are still in the database, and a reader is not the right
        place to assume its inputs.
        """
        scores = []
        for submission in Submission().find(
            {'userId': userId, 'scored': True}, fields=['autoScore']
        ):
            mean = (submission.get('autoScore') or {}).get('mean_dice')
            if pol.usable_score(mean):
                scores.append(mean)
        return scores

    # --------------------------------------------------------------- users

    @access.admin
    @autoDescribeRoute(
        Description('Create an annotator account and put it in the right group.')
        .notes('Wraps Girder user creation so that a new undergraduate is one '
               'call rather than "create user, then remember the group".')
        .param('login', 'Username.')
        .param('email', 'Email address.')
        .param('firstName', 'First name.')
        .param('lastName', 'Last name.')
        .param('password', 'Initial password.')
        .param('reviewer', 'Also grant SegQueue14 reviewer access.', dataType='boolean',
               required=False, default=False)
        .param('quota', 'Maximum cases this person may complete.',
               dataType='integer', required=False)
    )
    def createAnnotator(self, login, email, firstName, lastName, password,
                        reviewer, quota):
        user = User().createUser(login=login, password=password, email=email,
                                 firstName=firstName, lastName=lastName)
        self._setGroups(user, annotator=True, reviewer=reviewer)
        if quota is not None:
            user[QUOTA_FIELD] = int(quota)
            user = User().save(user)
        return User().filter(user, self.getCurrentUser())

    @access.admin
    @autoDescribeRoute(
        Description('Change an annotator\'s quota, roles, or active status.')
        .param('userId', 'The user to update.', paramType='path')
        .param('quota', 'New quota, or -1 to remove the cap.', dataType='integer',
               required=False)
        .param('annotator', 'Whether they may be assigned cases.',
               dataType='boolean', required=False)
        .param('reviewer', 'Whether they may review.', dataType='boolean',
               required=False)
        .param('disabled', 'Disable the account and release their open cases.',
               dataType='boolean', required=False)
    )
    def updateAnnotator(self, userId, quota, annotator, reviewer, disabled):
        user = User().load(userId, force=True)
        if user is None:
            refuse('no_such_user', 'No such user.', status=404)

        if quota is not None:
            user[QUOTA_FIELD] = None if quota < 0 else int(quota)
        if disabled is not None:
            user['status'] = 'disabled' if disabled else 'enabled'
        user = User().save(user)

        if annotator is not None or reviewer is not None:
            self._setGroups(user, annotator=annotator, reviewer=reviewer)

        released = 0
        if disabled:
            # Releasing on disable is the point of the flag: a student who has
            # left the course should not still be holding three cases.
            released = self._releaseAllFor(user, 'account disabled')

        return {'user': User().filter(user, self.getCurrentUser()),
                'releasedCases': released}

    def _setGroups(self, user, annotator=None, reviewer=None):
        # The plugin creates these on load, but a brand-new deployment loads
        # before anyone has registered and therefore before there is an admin to
        # own a group. This is the first moment one certainly exists -- the
        # caller is an admin by decorator -- so it is the right place to catch
        # up, rather than silently declining to grant the role.
        ensureGroups(creator=self.getCurrentUser())

        for flag, groupName in ((annotator, ANNOTATOR_GROUP), (reviewer, REVIEWER_GROUP)):
            if flag is None:
                continue
            group = Group().findOne({'name': groupName})
            if group is None:
                continue
            if flag:
                Group().addUser(group, user)
            else:
                Group().removeUser(group, user)

    def _releaseAllFor(self, user, reason):
        released = 0
        for assignment in Assignment().openForUser(user['_id']):
            try:
                Assignment().transition(assignment, st.RELEASE, releaseReason=reason)
            except st.TransitionError:
                continue
            Case().releaseSlot(assignment['caseId'])
            released += 1
        return released

    # --------------------------------------------------------------- cases

    @access.admin
    @autoDescribeRoute(
        Description('Withdraw a case from the pool.')
        .notes('Work already in progress on it is left alone -- cancelling a '
               'case out from under an annotator mid-session wastes more than '
               'the case is worth.')
        .modelParam('caseId', 'The case to retire.', model=Case, force=True,
                    destName='case')
        .param('reason', 'Why.', required=False, default='')
    )
    def retireCase(self, case, reason):
        return Case().retire(case, reason)

    @access.admin
    @autoDescribeRoute(
        Description('Assign a specific case to a specific annotator.')
        .notes('The escape hatch for everything the queue cannot express: a '
               'case that needs a particular person, or one being handed over '
               'after someone leaves.')
        .modelParam('caseId', 'The case to assign.', model=Case, force=True,
                    destName='case')
        .param('userId', 'Who to assign it to.')
        .errorResponse('That case has no free replica slot.', 409)
    )
    def assignCase(self, case, userId):
        user = User().load(userId, force=True)
        if user is None:
            refuse('no_such_user', 'No such user.', status=404)

        claimed = Case().claim(case['_id'], user['_id'])
        if claimed is None:
            refuse('case_unavailable',
                   'That case is retired, already out with someone, or has '
                   'previously been assigned to this person.',
                   status=409)
        assignment = Assignment().createAssignment(
            claimed, user, kind=None, policy=getPolicy())
        return {'assignmentId': str(assignment['_id']), 'caseId': str(case['_id'])}

    # --------------------------------------------------------------- sweep

    @access.admin
    @autoDescribeRoute(
        Description('Release every assignment whose lease or heartbeat has lapsed.')
        .notes('Safe to run repeatedly; idempotent. The worker container already '
               'sweeps hourly -- this endpoint is for when an admin does not want '
               'to wait, and for checking with dryRun what a sweep would take.')
        .param('dryRun', 'Report what would be released without doing it.',
               dataType='boolean', required=False, default=False)
    )
    def sweep(self, dryRun):
        result = sweepStranded(dryRun=dryRun)
        released, discarded = result['released'], result['discarded']
        return {'released': released, 'count': len(released),
                'discarded': discarded, 'discardedCount': len(discarded),
                'dryRun': bool(dryRun)}

    # ------------------------------------------------------------ prelabels

    @access.admin
    @autoDescribeRoute(
        Description('Attach an uploaded prelabel to one case, or refresh it (D15).')
        .notes('Upload the uint8 14-label NIfTI anywhere in Girder first; its item '
               'is moved into SegQueue14/prelabels/<modelVersion>/. The rules are '
               "segqueue14-prelabels': attach if the case has none, skip the same "
               'version, refresh a different version only if nobody has submitted '
               'the case or is working from the old one, and never refresh a '
               'held-out ImageCAS-X test case unless includeTest is set.')
        .param('caseName', 'The case, by name (e.g. imagecas_0002).')
        .param('fileId', 'Girder file id of the uploaded prelabel.')
        .param('modelVersion', 'Version of the model that produced it.')
        .param('includeTest', 'Allow refreshing an ImageCAS-X test case.',
               dataType='boolean', required=False, default=False)
        .param('dryRun', 'Say what would happen and change nothing.',
               dataType='boolean', required=False, default=False)
    )
    def attachPrelabel(self, caseName, fileId, modelVersion, includeTest, dryRun):
        from girder.models.file import File

        from ..prelabels import attachFile, decide

        try:
            from segqueue14 import plan as sqplan

            modelVersion = sqplan.validate_model_version(modelVersion)
        except ValueError as exc:
            refuse('bad_model_version', str(exc), status=400)
        case = Case().findOne({'name': caseName})
        if case is None:
            refuse('no_such_case', f'No SegQueue14 case named {caseName!r}.', status=404)
        file = File().load(fileId, force=True)
        if file is None:
            refuse('no_such_file', 'That file could not be found.', status=404)
        decision = decide(case, modelVersion, includeTest=includeTest)
        result = {'case': caseName, 'action': decision.action, 'reason': decision.reason,
                  'dryRun': bool(dryRun)}
        if decision.action == 'skip' or dryRun:
            return result
        updated = attachFile(case, file, modelVersion, self.getCurrentUser())
        if updated is None:
            refuse('prelabel_race', 'The case changed while attaching; try again.',
                   status=409)
        result['prelabelVersion'] = updated.get('prelabelVersion')
        return result

    @access.admin
    @autoDescribeRoute(
        Description('Add a note to a case from a named automatic process.')
        .notes('For machine screening of the cases before annotation (the '
               '"auto screener" reads each vessel seed). The note has no Girder '
               'account behind it and shows as a system note under ``author``. '
               'With ``once`` (default) a case that already has a note by that '
               'author is skipped, so a rerun adds nothing twice.')
        .param('caseName', 'The SegQueue14 case name, e.g. ImageCHD__1001.nii.gz.')
        .param('text', 'The note.')
        .param('author', 'Name shown as the author.', required=False,
               default='auto screener')
        .param('once', 'Skip a case that already has a note by this author.',
               dataType='boolean', required=False, default=True)
    )
    def addAutoNote(self, caseName, text, author, once):
        author = (author or '').strip()
        if not author:
            refuse('bad_author', 'An automatic note needs an author name.', status=400)
        case = Case().findOne({'name': caseName})
        if case is None:
            refuse('no_such_case', f'No SegQueue14 case named {caseName!r}.', status=404)
        if once and Note().hasNoteBy(case['_id'], author):
            return {'case': caseName, 'created': False, 'reason': 'already has one'}
        note = Note().namedNote(case['_id'], author, text)
        return {'case': caseName, 'created': True, 'noteId': str(note['_id'])}

    @access.admin
    @autoDescribeRoute(
        Description('Prelabels by model version, and cases still without one.')
    )
    def prelabelStatus(self):
        out = {'byVersion': {}, 'withoutPrelabel': 0}
        for row in Case().collection.aggregate([
            {'$match': {'retired': False}},
            {'$group': {'_id': {'v': '$prelabelVersion', 't': '$tier'}, 'n': {'$sum': 1}}},
        ]):
            version = row['_id'].get('v') or ''
            tier = row['_id'].get('t') or ''
            if not version:
                out['withoutPrelabel'] += row['n']
                continue
            out['byVersion'].setdefault(version, {})[tier] = row['n']
        return out


def _median(values):
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0

