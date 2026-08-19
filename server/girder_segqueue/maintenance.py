"""Periodic housekeeping: reclaim cases nobody is working on any more.

A case handed to an annotator who then drops the course is invisible. It is not
unassigned, so nobody else is offered it; it is not submitted, so it never shows
as late; it simply sits at 'assigned' and the project quietly finishes 3% short.
The lease and the heartbeat exist to make that state detectable, and this module
is what acts on it.

Written as a plain function rather than living inside the REST handler so that
the worker container can run it in-process, on a timer, with no credentials and
no HTTP round trip. The admin endpoint calls the same function, which is what
makes ``POST /segqueue/sweep`` and the background sweep provably the same
operation instead of two implementations that drift.
"""

import datetime
import logging

from segqueue import policy as pol
from segqueue import states as st

from .models import Assignment, Case
from .settings import getPolicy

logger = logging.getLogger(__name__)

#: How often the worker sweeps. Leases are measured in days, so hourly is
#: already far more attentive than the policy needs; it just means a released
#: case reaches the next annotator within the hour instead of overnight.
SWEEP_SECONDS = 3600


def sweep(dryRun=False, policy=None, now=None):
    """Release every assignment whose lease or heartbeat has lapsed.

    Returns a list of ``{assignmentId, caseId, userId, reason}``. Idempotent:
    running it twice releases nothing the second time, which is what makes it
    safe on a timer *and* on an impatient admin's button.
    """
    policy = policy or getPolicy()
    now = now or datetime.datetime.now(datetime.timezone.utc)
    released = []

    for assignment in Assignment().reclaimable(policy, now=now):
        assignedAt = assignment.get('assignedAt')
        heartbeat = assignment.get('lastHeartbeat')
        reason = pol.reclaim_reason(
            assignedAt.timestamp() if assignedAt else 0.0,
            heartbeat.timestamp() if heartbeat else None,
            now.timestamp(),
            policy,
        ) or 'lease lapsed'

        record = {
            'assignmentId': str(assignment['_id']),
            'caseId': str(assignment['caseId']),
            'userId': str(assignment['userId']),
            'reason': reason,
        }
        if dryRun:
            released.append(record)
            continue

        try:
            Assignment().transition(assignment, st.EXPIRE, releaseReason=reason)
        except st.TransitionError:
            # It moved on between the scan and now -- the annotator submitted it
            # moments ago. Leave it be; taking the case back from under someone
            # who is actively finishing it is the one outcome worse than a
            # stranded case.
            continue
        Case().releaseSlot(assignment['caseId'])
        released.append(record)

    if released and not dryRun:
        logger.info('sweep released %d stranded assignment(s)', len(released))
    return released
