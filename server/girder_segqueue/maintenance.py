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
from .utils import incomingFolder

logger = logging.getLogger(__name__)

#: How often the worker sweeps. Leases are measured in days, so hourly is
#: already far more attentive than the policy needs; it just means a released
#: case reaches the next annotator within the hour instead of overnight.
SWEEP_SECONDS = 3600

#: How long an item may sit in the incoming drop box before the sweeper discards
#: it. A successful submit moves its item out immediately (``rest/queue.py``), so
#: anything still here is an upload that failed or was abandoned. A day is
#: deliberately generous: the cost of keeping rubbish one extra day is a few
#: megabytes, and the cost of deleting a submission someone is still finishing is
#: their afternoon.
INCOMING_MAX_AGE_SECONDS = 86400


def sweep(dryRun=False, policy=None, now=None):
    """Release every assignment whose lease or heartbeat has lapsed.

    Returns ``{'released': [...], 'discarded': [...]}``. ``released`` holds one
    ``{assignmentId, caseId, userId, reason}`` per reclaimed lease; ``discarded``
    holds one ``{itemId, name, ageSeconds}`` per abandoned upload swept out of the
    incoming drop box. Idempotent: running it twice releases nothing and discards
    nothing the second time, which is what makes it safe on a timer *and* on an
    impatient admin's button.
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

    discarded = sweepIncoming(dryRun=dryRun, now=now)
    return {'released': released, 'discarded': discarded}


def sweepIncoming(dryRun=False, maxAge=INCOMING_MAX_AGE_SECONDS, now=None):
    """Discard uploads abandoned in the incoming drop box.

    The drop box is the one folder annotators may write to, so it is the one
    place the disk can grow without bound: every failed or abandoned upload
    stays there forever otherwise. A successful submit moves its item straight
    out, so age alone separates rubbish from work in progress -- but an upload
    still streaming has an item before it has all its bytes, which is why an
    in-flight upload is skipped regardless of how old its item looks.

    Returns a list of ``{itemId, name, ageSeconds}``, one per discarded item.
    """
    from girder.models.folder import Folder
    from girder.models.item import Item

    now = now or datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(seconds=maxAge)
    discarded = []

    for item in Folder().childItems(incomingFolder()):
        stamp = _asUtc(item.get('updated') or item.get('created'))
        if stamp is None or stamp > cutoff:
            continue
        if _uploadInFlight(item):
            continue

        record = {
            'itemId': str(item['_id']),
            'name': item.get('name', ''),
            'ageSeconds': int((now - stamp).total_seconds()),
        }
        if not dryRun:
            Item().remove(item)
        discarded.append(record)

    if discarded and not dryRun:
        logger.info('sweep discarded %d abandoned upload(s) from incoming',
                    len(discarded))
    return discarded


def _asUtc(stamp):
    """Girder writes naive UTC datetimes; comparisons here are timezone-aware."""
    if stamp is None:
        return None
    if stamp.tzinfo is None:
        return stamp.replace(tzinfo=datetime.timezone.utc)
    return stamp


def _uploadInFlight(item):
    """Whether Girder still has an open upload writing into this item.

    Deleting one of those races the uploader: the item exists from the first
    chunk, so an annotator submitting a 20 MB volume over a slow link is exactly
    the case that must not be swept.
    """
    from girder.models.item import Item
    from girder.models.upload import Upload

    uploads = Upload().collection
    if uploads.find_one({'parentType': 'item', 'parentId': item['_id']}):
        return True
    fileIds = [f['_id'] for f in Item().childFiles(item)]
    return bool(fileIds and uploads.find_one({'fileId': {'$in': fileIds}}))
