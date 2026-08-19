"""Admin endpoints: people, cases, the burn-down, and the lease sweeper.

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

from ..constants import ANNOTATOR_GROUP, REVIEWER_GROUP
from ..maintenance import sweep as sweepStranded
from ..models import Assignment, Case, Review, Submission
from ..models.review import APPROVE, REJECT
from ..settings import getPolicy
from ..utils import ensureGroups, refuse


class AdminResource(Resource):
    """Registered onto the queue resource so paths read ``/segqueue/...``."""

    def attachTo(self, parent):
        parent.route('GET', ('stats',), self.stats)
        parent.route('GET', ('stats', 'annotators'), self.annotatorStats)
        parent.route('POST', ('users',), self.createAnnotator)
        parent.route('PATCH', ('users', ':userId'), self.updateAnnotator)
        parent.route('POST', ('case', ':caseId', 'retire'), self.retireCase)
        parent.route('POST', ('case', ':caseId', 'assign'), self.assignCase)
        parent.route('POST', ('sweep',), self.sweep)
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
            'quota': user.get('segqueueQuota'),
        }

    def _caseDurations(self, userId):
        return [
            s['annotationSeconds']
            for s in Submission().find({'userId': userId}, fields=['annotationSeconds'])
            if s.get('annotationSeconds')
        ]

    def _agreementScores(self, userId):
        scores = []
        for submission in Submission().find(
            {'userId': userId, 'scored': True}, fields=['autoScore']
        ):
            mean = (submission.get('autoScore') or {}).get('mean_dice')
            if mean is not None:
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
        .param('reviewer', 'Also grant reviewer access.', dataType='boolean',
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
            user['segqueueQuota'] = int(quota)
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
            user['segqueueQuota'] = None if quota < 0 else int(quota)
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
            claimed, user, kind=pol.NORMAL, policy=getPolicy())
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
        released = sweepStranded(dryRun=dryRun)
        return {'released': released, 'count': len(released), 'dryRun': bool(dryRun)}


def _median(values):
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


#: Verdict names re-exported so the dashboard JS has one source for them.
VERDICTS = (APPROVE, REJECT)

__all__ = ['AdminResource', 'Review', 'VERDICTS']
