"""SegQueue14 cases: one CT, its prelabel, and its accounting.

Adapted from ``girder_segqueue.models.case`` -- the atomic ``claim`` and the
replica counters are the same design and the same queries -- under its own Mongo
collection (``segqueue14_case``) so both plugins can load at once.

What is different:

* **The CT is referenced, not owned.** ``fileId`` is the id of a file already in
  the live SegQueue collection. Nothing here copies, moves or modifies it.
* **Serve order is data** (D14, D16): ``priority`` (highest first) and then
  ``serveOrder``, both written by ``segqueue14-populate``. There is no gold flag
  and no random duplicate claim: blind duplicates are cases whose
  ``replicasWanted`` the population tool set to 2 (D11).
* **A prelabel and a reference.** ``prelabelFileId`` / ``prelabelVersion`` is the
  14-class model's prediction the annotator corrects (D10); ``referenceFileId`` is
  the ImageCAS-X segmentation every read is scored against, never served to an
  annotator.
"""

import datetime

from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.model_base import AccessControlledModel
from pymongo import ReturnDocument
from segqueue import states as st

from ..constants import CANDIDATE_BATCH


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


class Case14(AccessControlledModel):
    def initialize(self):
        self.name = 'segqueue14_case'
        self.ensureIndices([
            'name',
            'retired',
            'sourceCaseId',
            'dataset',
            'tier',
            'prelabelVersion',
            # The /next scan: servability filter, then serve order. Matches the
            # sort in `candidates`.
            ([('retired', 1), ('priority', -1), ('serveOrder', 1), ('created', 1)], {}),
            'assignedUserIds',
        ])
        self.exposeFields(level=AccessType.READ, fields={
            '_id', 'name', 'target', 'priority', 'serveOrder', 'replicasWanted',
            'activeCount', 'approvedCount', 'retired', 'sizeBytes', 'checksum',
            'created', 'updated', 'dataset', 'prelabelVersion',
        })
        # Which tier a case is in, whether it is a blind duplicate and whether it
        # has a reference are queue mechanics an annotator must not see.
        self.exposeFields(level=AccessType.SITE_ADMIN, fields={
            'tier', 'split', 'blindDuplicate', 'referenceFileId', 'prelabelFileId',
            'prelabelHistory', 'sourceCaseId', 'fileId', 'regionFileId',
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
        doc['serveOrder'] = int(doc.get('serveOrder', 0))
        doc['retired'] = bool(doc.get('retired', False))
        doc['blindDuplicate'] = bool(doc.get('blindDuplicate', False))
        doc['sizeBytes'] = int(doc.get('sizeBytes', 0))
        doc.setdefault('assignedUserIds', [])
        doc.setdefault('target', 'coronary-14')
        doc.setdefault('checksum', '')
        doc.setdefault('regionFileId', None)
        doc.setdefault('referenceFileId', None)
        doc.setdefault('prelabelFileId', None)
        doc.setdefault('prelabelVersion', '')
        doc.setdefault('prelabelHistory', [])
        doc.setdefault('dataset', '')
        doc.setdefault('tier', '')
        doc.setdefault('split', None)
        doc.setdefault('sourceCaseId', None)
        return doc

    # ------------------------------------------------------------- creation

    def createCase(self, name, fileId, checksum, sizeBytes, creator=None,
                   priority=0, serveOrder=0, replicasWanted=1, tier='', dataset='',
                   split=None, blindDuplicate=False, referenceFileId=None,
                   regionFileId=None, sourceCaseId=None, geometryFixed=False,
                   target='coronary-14'):
        now = _now()
        return self.save({
            'name': name,
            'fileId': fileId,
            'sourceCaseId': sourceCaseId,
            'regionFileId': regionFileId,
            'referenceFileId': referenceFileId,
            'prelabelFileId': None,
            'prelabelVersion': '',
            'prelabelHistory': [],
            'geometryFixed': bool(geometryFixed),
            'checksum': (checksum or '').lower(),
            'sizeBytes': int(sizeBytes or 0),
            'target': target,
            'priority': int(priority),
            'serveOrder': int(serveOrder),
            'replicasWanted': int(replicasWanted),
            'tier': tier,
            'dataset': dataset,
            'split': split,
            'blindDuplicate': bool(blindDuplicate),
            'retired': False,
            'activeCount': 0,
            'approvedCount': 0,
            'assignedUserIds': [],
            'creatorId': creator['_id'] if creator else None,
            'created': now,
            'updated': now,
        })

    # ---------------------------------------------------------- the claim

    SERVABLE_QUERY = {
        'retired': False,
        '$expr': {
            '$lt': [
                {'$add': ['$activeCount', '$approvedCount']},
                '$replicasWanted',
            ]
        },
    }

    SORT = [('priority', -1), ('serveOrder', 1), ('created', 1)]

    def candidates(self, userId, limit=CANDIDATE_BATCH):
        """Servable cases this user has never held, in serve order."""
        query = dict(self.SERVABLE_QUERY)
        query['assignedUserIds'] = {'$ne': userId}
        return self.find(query, limit=limit, sort=self.SORT)

    def claim(self, caseId, userId):
        """Atomically consume one replica slot, or ``None`` if beaten to it."""
        query = dict(self.SERVABLE_QUERY)
        query['_id'] = caseId
        query['assignedUserIds'] = {'$ne': userId}
        return self.collection.find_one_and_update(
            query,
            {
                '$inc': {'activeCount': 1},
                '$push': {'assignedUserIds': userId},
                '$set': {'updated': _now()},
            },
            return_document=ReturnDocument.AFTER,
        )

    def releaseSlot(self, caseId):
        return self.collection.find_one_and_update(
            {'_id': caseId},
            [{'$set': {
                'activeCount': {'$max': [0, {'$subtract': ['$activeCount', 1]}]},
                'updated': '$$NOW',
            }}],
            return_document=ReturnDocument.AFTER,
        )

    def completeSlot(self, caseId):
        return self.collection.find_one_and_update(
            {'_id': caseId},
            [{'$set': {
                'activeCount': {'$max': [0, {'$subtract': ['$activeCount', 1]}]},
                'approvedCount': {'$add': ['$approvedCount', 1]},
                'updated': '$$NOW',
            }}],
            return_document=ReturnDocument.AFTER,
        )

    # ------------------------------------------------------------ prelabels

    def setPrelabel(self, case, fileId, version, attachedBy=None):
        """Point a case at a new prelabel, guarded on the one it had.

        Guarded so that two attach runs racing on one case cannot both "win": the
        update only applies if the case still carries the version this caller
        decided against. The previous prelabel is kept in ``prelabelHistory``
        (its file is never deleted), so the provenance of every earlier read can
        still be traced to the prediction it started from.
        """
        now = _now()
        entry = {'fileId': fileId, 'version': version, 'attachedAt': now,
                 'attachedBy': attachedBy}
        return self.collection.find_one_and_update(
            {'_id': case['_id'],
             'prelabelVersion': case.get('prelabelVersion') or '',
             'prelabelFileId': case.get('prelabelFileId')},
            {'$set': {'prelabelFileId': fileId, 'prelabelVersion': version,
                      'updated': now},
             '$push': {'prelabelHistory': entry}},
            return_document=ReturnDocument.AFTER,
        )

    # -------------------------------------------------------------- queries

    def statusOf(self, case):
        return st.case_status(
            replicas_wanted=case.get('replicasWanted', 1),
            active_assignments=case.get('activeCount', 0),
            approved_assignments=case.get('approvedCount', 0),
            retired=case.get('retired', False),
        )

    def countByStatus(self):
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

    def countByTier(self):
        """``{tier: {cases, readsWanted, readsApproved}}`` for the dashboard."""
        out = {}
        for row in self.collection.aggregate([
            {'$match': {'retired': False}},
            {'$group': {'_id': '$tier', 'cases': {'$sum': 1},
                        'readsWanted': {'$sum': '$replicasWanted'},
                        'readsApproved': {'$sum': '$approvedCount'},
                        'priority': {'$max': '$priority'}}},
        ]):
            out[row['_id'] or ''] = {k: row[k] for k in
                                     ('cases', 'readsWanted', 'readsApproved', 'priority')}
        return out

    def retire(self, case, reason=''):
        case['retired'] = True
        case['retiredReason'] = reason
        case['updated'] = _now()
        return self.save(case)
