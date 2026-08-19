"""Cases: the pool of volumes waiting to be segmented, and the atomic claim.

The single most important method in this plugin is ``claim``. Thirty annotators
clicking "Get next case" within the same second must receive thirty different
cases, and no amount of care in the surrounding Python achieves that -- a
read-then-write in application code has a window between the two, and under load
that window is hit. So the claim is one ``findAndModify``: the condition that
makes a case servable and the increment that consumes the slot are evaluated by
the database in a single operation, and the loser of a race simply gets ``None``
back and tries the next candidate.

Counters (``activeCount``, ``approvedCount``) are stored on the case rather than
recomputed from the assignments collection for the same reason. A query over
assignments cannot be made atomic with the write that claims the slot; a counter
on the document can.
"""

import datetime

from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.model_base import AccessControlledModel
from pymongo import ReturnDocument
from segqueue import states as st

from ..constants import CANDIDATE_BATCH


class Case(AccessControlledModel):
    """One source volume and its accounting.

    Access control is deliberately coarse: cases are readable by the SegQueue
    collection's members and writable only by admins. Per-case ACLs would be the
    natural Girder idiom, but "which annotator may see this case" is a queue
    question that changes several times a day, and encoding it in ACLs would mean
    an ACL write on every assignment. The download endpoint checks the assignment
    instead -- one indexed lookup, always current.
    """

    def initialize(self):
        self.name = 'segqueue_case'
        self.ensureIndices([
            'name',
            'retired',
            # The candidate scan for /next: filter on servability, order by
            # priority. Compound and ordered to match the sort in `candidates`.
            ([('retired', 1), ('priority', -1), ('created', 1)], {}),
            'assignedUserIds',
            'isGold',
        ])
        self.exposeFields(level=AccessType.READ, fields={
            '_id', 'name', 'target', 'priority', 'replicasWanted', 'activeCount',
            'approvedCount', 'retired', 'isGold', 'sizeBytes', 'checksum',
            'created', 'updated',
        })

    def validate(self, doc):
        doc['name'] = (doc.get('name') or '').strip()
        if not doc['name']:
            raise ValidationException('Case name must not be empty.', 'name')

        doc['replicasWanted'] = int(doc.get('replicasWanted', 1))
        if doc['replicasWanted'] < 1:
            raise ValidationException('replicasWanted must be at least 1.', 'replicasWanted')

        for field in ('activeCount', 'approvedCount'):
            doc[field] = int(doc.get(field, 0))
            if doc[field] < 0:
                raise ValidationException(f'{field} must not be negative.', field)

        doc['priority'] = int(doc.get('priority', 0))
        doc['retired'] = bool(doc.get('retired', False))
        doc['isGold'] = bool(doc.get('isGold', False))
        doc['sizeBytes'] = int(doc.get('sizeBytes', 0))
        doc.setdefault('assignedUserIds', [])
        doc.setdefault('target', '')
        doc.setdefault('checksum', '')
        doc.setdefault('regionFileId', None)
        doc.setdefault('seedFileId', None)
        doc['geometryFixed'] = bool(doc.get('geometryFixed', False))
        return doc

    # ------------------------------------------------------------- creation

    def createCase(self, name, fileId, checksum, sizeBytes, creator, target='',
                   priority=0, replicasWanted=1, isGold=False, goldFileId=None,
                   regionFileId=None, seedFileId=None, geometryFixed=False):
        """Register a volume that has already been uploaded into Girder.

        The file is uploaded first and registered second, so a failed transfer
        never leaves a case in the pool with nothing behind it.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        doc = {
            'name': name,
            'fileId': fileId,
            'goldFileId': goldFileId,
            # Optional extras from the source dataset. Both are read-only aids
            # for the annotator and are never part of a submission: the client
            # exports only the project's own segments.
            'regionFileId': regionFileId,
            'seedFileId': seedFileId,
            # Provenance: this case's direction cosines were orthonormalised at
            # ingest so ITK would accept them. Worth recording rather than
            # inferring later -- it is the sort of thing a reviewer of the
            # dataset will ask about.
            'geometryFixed': bool(geometryFixed),
            'checksum': (checksum or '').lower(),
            'sizeBytes': sizeBytes,
            'target': target,
            'priority': priority,
            'replicasWanted': replicasWanted,
            'isGold': isGold,
            'retired': False,
            'activeCount': 0,
            'approvedCount': 0,
            'assignedUserIds': [],
            'creatorId': creator['_id'] if creator else None,
            'created': now,
            'updated': now,
        }
        return self.save(doc)

    # ---------------------------------------------------------- the claim

    #: Mongo predicate for "this case still needs another annotator". Mirrors
    #: ``segqueue.states.servable`` -- the Python version is what the tests and
    #: the dashboard use, this is what the database can evaluate atomically.
    #: They must agree; ``test_servability_predicate_matches_states`` checks it.
    SERVABLE_QUERY = {
        'retired': False,
        '$expr': {
            '$lt': [
                {'$add': ['$activeCount', '$approvedCount']},
                '$replicasWanted',
            ]
        },
    }

    def candidates(self, userId, wantGold=None, limit=CANDIDATE_BATCH):
        """Cases this user could be given, best first.

        Excludes anything they have already been assigned -- including work they
        released or that expired. That is a deliberate one-way door: for a blind
        duplicate the same person must never score their own work, and the cost
        of never re-serving someone a case they abandoned is negligible when
        there are thousands of cases and thirty people.
        """
        query = dict(self.SERVABLE_QUERY)
        query['assignedUserIds'] = {'$ne': userId}
        if wantGold is not None:
            query['isGold'] = bool(wantGold)
        return self.find(
            query,
            limit=limit,
            sort=[('priority', -1), ('created', 1)],
        )

    def claim(self, caseId, userId):
        """Atomically consume one replica slot, or return ``None`` if beaten to it.

        The query repeats every servability condition rather than trusting the
        document that ``candidates`` returned a moment ago: between the scan and
        this call, another annotator may have taken the last slot, an admin may
        have retired the case, or this same user may have claimed it in a
        double-clicked request.
        """
        query = dict(self.SERVABLE_QUERY)
        query['_id'] = caseId
        query['assignedUserIds'] = {'$ne': userId}
        return self.collection.find_one_and_update(
            query,
            {
                '$inc': {'activeCount': 1},
                '$push': {'assignedUserIds': userId},
                '$set': {'updated': datetime.datetime.now(datetime.timezone.utc)},
            },
            return_document=ReturnDocument.AFTER,
        )

    def releaseSlot(self, caseId):
        """Give a replica slot back: the assignment was released or expired.

        ``$max`` guards the floor. A double-release -- a lease sweeper and a
        user's own release button firing on the same assignment -- would
        otherwise drive the counter negative and make the case unservable
        forever, which is a silent and very confusing failure.
        """
        return self.collection.find_one_and_update(
            {'_id': caseId},
            [
                {'$set': {
                    'activeCount': {'$max': [0, {'$subtract': ['$activeCount', 1]}]},
                    'updated': '$$NOW',
                }},
            ],
            return_document=ReturnDocument.AFTER,
        )

    def completeSlot(self, caseId):
        """Convert an active slot into an approved one."""
        return self.collection.find_one_and_update(
            {'_id': caseId},
            [
                {'$set': {
                    'activeCount': {'$max': [0, {'$subtract': ['$activeCount', 1]}]},
                    'approvedCount': {'$add': ['$approvedCount', 1]},
                    'updated': '$$NOW',
                }},
            ],
            return_document=ReturnDocument.AFTER,
        )

    #: A case that is finished, unclaimed, and has only ever been done once --
    #: exactly the population a blind duplicate can be drawn from. Requiring
    #: ``activeCount == 0`` keeps the two annotators genuinely independent: if a
    #: replica were already out, the second would be a concurrent re-do rather
    #: than a check on completed work.
    DUPLICATABLE_QUERY = {
        'retired': False,
        'replicasWanted': 1,
        'approvedCount': 1,
        'activeCount': 0,
    }

    def duplicateCandidates(self, userId, limit=CANDIDATE_BATCH):
        query = dict(self.DUPLICATABLE_QUERY)
        query['assignedUserIds'] = {'$ne': userId}
        return self.find(query, limit=limit, sort=[('priority', -1), ('created', 1)])

    def hasDuplicateAvailable(self, userId):
        query = dict(self.DUPLICATABLE_QUERY)
        query['assignedUserIds'] = {'$ne': userId}
        return self.collection.count_documents(query, limit=1) > 0

    def claimAsDuplicate(self, caseId, userId):
        """Raise the replica target and consume the new slot in one operation.

        Two steps would be a bug: raising ``replicasWanted`` and then losing the
        race to claim would leave a case permanently wanting a second replica
        that the *next* annotator would receive as an ordinary case -- unscored,
        and silently inflating the duplicate rate the dashboard reports.
        """
        query = dict(self.DUPLICATABLE_QUERY)
        query['_id'] = caseId
        query['assignedUserIds'] = {'$ne': userId}
        return self.collection.find_one_and_update(
            query,
            {
                '$set': {'replicasWanted': 2,
                         'updated': datetime.datetime.now(datetime.timezone.utc)},
                '$inc': {'activeCount': 1},
                '$push': {'assignedUserIds': userId},
            },
            return_document=ReturnDocument.AFTER,
        )

    def wantDuplicate(self, caseId):
        """Raise a case's replica target so a second annotator is served it.

        Called when the policy rolls a duplicate. Raising the target rather than
        marking a boolean means the ordinary servability rule does all the work:
        the case simply becomes servable again, to someone who has not seen it.
        """
        return self.collection.find_one_and_update(
            {'_id': caseId, 'retired': False},
            {'$set': {'replicasWanted': 2, 'updated': datetime.datetime.now(
                datetime.timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )

    # -------------------------------------------------------------- queries

    def statusOf(self, case):
        """The case's derived status, via the shared state module."""
        return st.case_status(
            replicas_wanted=case.get('replicasWanted', 1),
            active_assignments=case.get('activeCount', 0),
            approved_assignments=case.get('approvedCount', 0),
            retired=case.get('retired', False),
        )

    def countByStatus(self):
        """``{status: n}`` over the whole project, for the dashboard burn-down.

        One aggregation rather than one query per status, because this runs on
        every dashboard poll.
        """
        counts = {s: 0 for s in (
            st.CASE_PENDING, st.CASE_IN_PROGRESS, st.CASE_COMPLETE, st.CASE_RETIRED)}
        pipeline = [
            {'$group': {
                '_id': {
                    'retired': '$retired',
                    'done': {'$gte': ['$approvedCount', '$replicasWanted']},
                    'busy': {'$gt': [{'$add': ['$activeCount', '$approvedCount']}, 0]},
                },
                'n': {'$sum': 1},
            }},
        ]
        for row in self.collection.aggregate(pipeline):
            key = row['_id']
            if key['retired']:
                counts[st.CASE_RETIRED] += row['n']
            elif key['done']:
                counts[st.CASE_COMPLETE] += row['n']
            elif key['busy']:
                counts[st.CASE_IN_PROGRESS] += row['n']
            else:
                counts[st.CASE_PENDING] += row['n']
        return counts

    def hasGoldAvailable(self, userId):
        """Whether an unseen gold case exists for this user.

        ``count_documents`` on the collection rather than ``.count()`` on the
        cursor: pymongo 4 removed the latter, and Girder 5 requires pymongo 4.
        """
        query = dict(self.SERVABLE_QUERY)
        query['assignedUserIds'] = {'$ne': userId}
        query['isGold'] = True
        return self.collection.count_documents(query, limit=1) > 0

    def retire(self, case, reason=''):
        """Withdraw a case. Existing assignments are left alone deliberately --
        work already in progress is still worth collecting, and cancelling it
        out from under an annotator mid-session is worse than one wasted case."""
        case['retired'] = True
        case['retiredReason'] = reason
        case['updated'] = datetime.datetime.now(datetime.timezone.utc)
        return self.save(case)
