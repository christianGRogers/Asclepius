"""Assignments: one annotator's lease on one case, and its whole timeline.

Every state change goes through ``transition``, which asks
``segqueue.states.apply_event`` whether the move is legal before writing
anything. No endpoint sets ``state`` directly. That single chokepoint is what
makes the lifecycle auditable: the timestamps recorded here are the raw material
for every dashboard number, and they are only ever written by the transition
that earned them.
"""

import datetime

from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.model_base import AccessControlledModel
from pymongo import ReturnDocument
from segqueue import policy as pol
from segqueue import states as st


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _epoch(dt):
    """Unix seconds from a tz-aware datetime, or None. The policy module works
    in plain floats so that it stays free of any timezone question."""
    return dt.timestamp() if dt is not None else None


#: Which timestamp each event stamps. Recorded declaratively so that the list of
#: things the dashboard can measure is visible in one place rather than scattered
#: through endpoint handlers.
_TIMESTAMP_FOR_EVENT = {
    st.DOWNLOAD: 'downloadedAt',
    st.SUBMIT: 'submittedAt',
    st.CLAIM_REVIEW: 'reviewClaimedAt',
    st.APPROVE: 'decidedAt',
    st.REJECT: 'decidedAt',
    st.REWORK: 'reworkedAt',
    st.RELEASE: 'releasedAt',
    st.EXPIRE: 'releasedAt',
}


class Assignment(AccessControlledModel):
    def initialize(self):
        self.name = 'segqueue_assignment'
        self.ensureIndices([
            # "What am I holding?" -- the client's most frequent query.
            ([('userId', 1), ('state', 1)], {}),
            # "Who has this case?" -- duplicate pairing and admin reassignment.
            ([('caseId', 1), ('state', 1)], {}),
            # The lease sweeper's scan.
            ([('state', 1), ('deadline', 1)], {}),
            'submittedAt',
        ])
        self.exposeFields(level=AccessType.READ, fields={
            '_id', 'caseId', 'userId', 'state', 'attempt', 'assignedAt',
            'downloadedAt', 'submittedAt', 'decidedAt', 'deadline',
            'lastHeartbeat', 'reviewerComment', 'submissionId',
        })
        # `kind` is exposed only to admins: an annotator who can see that their
        # case is a gold seed can look up the answer, and a duplicate that is
        # known to be a duplicate measures nothing.
        self.exposeFields(level=AccessType.SITE_ADMIN, fields={'kind', 'reviewRoll'})

    def validate(self, doc):
        if doc.get('state') not in st.ALL_STATES:
            raise ValidationException(f"Unknown assignment state {doc.get('state')!r}.", 'state')
        doc['attempt'] = int(doc.get('attempt', 1))
        doc.setdefault('reviewerComment', '')
        return doc

    # ------------------------------------------------------------- creation

    def createAssignment(self, case, user, kind=pol.NORMAL, policy=None):
        """Record the lease. The case's slot must already have been claimed.

        Ordering matters and is not arbitrary: ``Case.claim`` consumes the slot
        first, and only if it succeeds is this document written. Doing it the
        other way round would leave an assignment pointing at a case somebody
        else got.
        """
        policy = policy or pol.SamplingPolicy()
        now = _now()
        doc = {
            'caseId': case['_id'],
            'userId': user['_id'],
            'state': st.ASSIGNED,
            'attempt': 1,
            'kind': kind,
            'assignedAt': now,
            'downloadedAt': None,
            'submittedAt': None,
            'decidedAt': None,
            'releasedAt': None,
            'lastHeartbeat': None,
            'deadline': now + datetime.timedelta(days=policy.lease_days),
            'reviewerComment': '',
            'submissionId': None,
        }
        return self.save(doc)

    # ----------------------------------------------------------- transitions

    def transition(self, assignment, event, policy=None, **extra):
        """Apply ``event``, stamping the timestamp it earns.

        Raises ``segqueue.states.TransitionError`` if the move is illegal --
        which the REST layer turns into a 409 rather than a 500, because an
        illegal move is almost always a client that retried a request whose
        first attempt actually succeeded.
        """
        newState = st.apply_event(assignment['state'], event)
        now = _now()

        update = {'state': newState, 'updated': now}
        stamp = _TIMESTAMP_FOR_EVENT.get(event)
        if stamp:
            update[stamp] = now

        if event == st.REWORK:
            # A new attempt gets a fresh lease; otherwise a case rejected on day
            # six of a seven-day lease would expire before it could be fixed.
            policy = policy or pol.SamplingPolicy()
            update['attempt'] = st.next_attempt(assignment.get('attempt', 1))
            update['deadline'] = now + datetime.timedelta(days=policy.lease_days)
            update['downloadedAt'] = None
            update['submittedAt'] = None

        update.update(extra)

        # Guarded update: the state we transitioned *from* must still be the
        # state in the database. Two reviewers hitting Approve on the same
        # submission both compute a legal transition; only one may apply it.
        result = self.collection.find_one_and_update(
            {'_id': assignment['_id'], 'state': assignment['state']},
            {'$set': update},
            return_document=ReturnDocument.AFTER,
        )
        if result is None:
            raise st.TransitionError(assignment['state'], event)
        return result

    def heartbeat(self, assignment):
        """Record contact from a client that is still working.

        A bare timestamp write, not a transition: heartbeats are frequent and
        must never be able to move the state machine.
        """
        return self.collection.find_one_and_update(
            {'_id': assignment['_id']},
            {'$set': {'lastHeartbeat': _now()}},
            return_document=ReturnDocument.AFTER,
        )

    # -------------------------------------------------------------- queries

    def forUser(self, userId, states=None):
        query = {'userId': userId}
        if states:
            query['state'] = {'$in': list(states)}
        return self.find(query, sort=[('assignedAt', 1)])

    def openForUser(self, userId):
        """Assignments that count against this user's concurrency limit."""
        return list(self.forUser(userId, sorted(st.OPEN_STATES)))

    def countOpenForUser(self, userId):
        return self.collection.count_documents({
            'userId': userId,
            'state': {'$in': sorted(st.OPEN_STATES)},
        })

    def activeForCase(self, caseId):
        return list(self.find({
            'caseId': caseId,
            'state': {'$in': sorted(st.ACTIVE_STATES)},
        }))

    def approvedForCase(self, caseId):
        """Approved assignments, oldest first -- the duplicate partner lookup."""
        return list(self.find({'caseId': caseId, 'state': st.APPROVED},
                              sort=[('decidedAt', 1)]))

    def pendingReview(self, limit=50, offset=0):
        """The reviewer queue: submitted, unclaimed, oldest first.

        Oldest first on purpose. Newest-first would let a backlog's oldest
        submissions age indefinitely, and the annotator waiting on one of them
        is blocked from reworking it.
        """
        return list(self.find(
            {'state': st.SUBMITTED, 'needsReview': True},
            limit=limit, offset=offset, sort=[('submittedAt', 1)],
        ))

    def reclaimable(self, policy, now=None):
        """Assignments whose lease has expired or whose client has gone quiet.

        The deadline half is an indexed range query. The heartbeat half cannot
        be, since "stale" is relative to a configurable window, so it is
        evaluated in Python over the (small) set of open assignments -- there
        are at most a few dozen at any moment, one per annotator.
        """
        now = now or _now()
        nowEpoch = now.timestamp()
        openStates = sorted(st.OPEN_STATES)

        expired = list(self.find({
            'state': {'$in': openStates},
            'deadline': {'$lte': now},
        }))
        seen = {a['_id'] for a in expired}

        for assignment in self.find({'state': {'$in': openStates}}):
            if assignment['_id'] in seen:
                continue
            if pol.heartbeat_stale(
                _epoch(assignment.get('lastHeartbeat')), nowEpoch, policy
            ):
                expired.append(assignment)
        return expired

    def recordFor(self, userId):
        """Build the ``AnnotatorRecord`` the sampling policy reads.

        One aggregation over this user's decided assignments. The streak
        counters need ordering, so they are folded in Python over a projection
        of decision times -- a few hundred documents per user per semester, and
        only on submit.
        """
        decided = list(self.find(
            {'userId': userId, 'state': {'$in': [st.APPROVED, st.REJECTED]}},
            fields=['state', 'decidedAt'],
            sort=[('decidedAt', 1)],
        ))
        approved = sum(1 for a in decided if a['state'] == st.APPROVED)
        rejected = sum(1 for a in decided if a['state'] == st.REJECTED)

        cleanStreak = 0
        for assignment in reversed(decided):
            if assignment['state'] != st.APPROVED:
                break
            cleanStreak += 1

        # Submissions since the last rejection, counting ones still awaiting a
        # verdict -- probation is about work done since the mistake, not about
        # verdicts returned since then.
        lastRejection = None
        for assignment in reversed(decided):
            if assignment['state'] == st.REJECTED:
                lastRejection = assignment.get('decidedAt')
                break

        query = {'userId': userId, 'submittedAt': {'$ne': None}}
        if lastRejection is not None:
            query['submittedAt'] = {'$gt': lastRejection}
        sinceRejection = self.collection.count_documents(query)

        return pol.AnnotatorRecord(
            approved=approved,
            rejected=rejected,
            clean_streak=cleanStreak,
            since_rejection=sinceRejection,
        )
