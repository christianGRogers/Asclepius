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
  4-class model's prediction the annotator corrects (D25; D23 pooled cases are
  seeded from TotalSegmentator instead); ``referenceFileId`` is
  the ImageCAS-X segmentation every read is scored against, never served to an
  annotator.
* **The annotator benchmark** (D43, ``segqueue14.benchmark``): one case with
  ``benchmark: True`` is never in the pool. ``SERVABLE_QUERY`` leaves it out, so
  neither ``/next``'s pool scan nor a reviewer's hand-assignment can hand it out,
  and its ``replicasWanted`` is never consulted; it is served only to the users
  in its ``benchmarkPending`` list (``claimBenchmark``), once per invitation.
* **Extended mode** (D47 Q6): ``extendedMode: True`` asks the annotator to read
  the case with the extended classes; the module turns them on
  (``setExtendedMode``). Which cases get it (the D35 decision patients) waits
  for #116.
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


def _unseenBy(query, userId):
    """``query`` narrowed to cases ``userId`` has never been assigned.

    Every way of handing out a case applies this, including to a case the user
    released or let expire -- see the live plugin's ``Case.candidates`` for why
    that door is one-way.
    """
    query = dict(query)
    query['assignedUserIds'] = {'$ne': userId}
    return query


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
            'benchmark',
        ])
        self.exposeFields(level=AccessType.READ, fields={
            '_id', 'name', 'target', 'priority', 'serveOrder', 'replicasWanted',
            'activeCount', 'approvedCount', 'retired', 'sizeBytes', 'checksum',
            'created', 'updated', 'dataset', 'prelabelVersion', 'extendedMode',
        })
        # Which tier a case is in, whether it is a blind duplicate and whether it
        # has a reference are queue mechanics an annotator must not see.
        self.exposeFields(level=AccessType.SITE_ADMIN, fields={
            'tier', 'split', 'blindDuplicate', 'referenceFileId', 'prelabelFileId',
            'prelabelHistory', 'sourceCaseId', 'fileId', 'regionFileId',
            'seedFileId', 'seedSource', 'benchmark', 'benchmarkPick', 'benchmarkPending',
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
        doc.setdefault('seedFileId', None)
        doc.setdefault('seedSource', '')
        doc.setdefault('referenceFileId', None)
        doc.setdefault('prelabelFileId', None)
        doc.setdefault('prelabelVersion', '')
        doc.setdefault('prelabelHistory', [])
        doc.setdefault('dataset', '')
        doc.setdefault('tier', '')
        doc.setdefault('split', None)
        doc.setdefault('sourceCaseId', None)
        doc['benchmark'] = bool(doc.get('benchmark', False))
        if doc['benchmark']:
            doc.setdefault('benchmarkPending', [])
        # D47 Q6: read with the extended classes on. Off for every case unless set.
        doc['extendedMode'] = bool(doc.get('extendedMode', False))
        return doc

    # ------------------------------------------------------------- creation

    def createCase(self, name, fileId, checksum, sizeBytes, creator=None,
                   priority=0, serveOrder=0, replicasWanted=1, tier='', dataset='',
                   split=None, blindDuplicate=False, referenceFileId=None,
                   regionFileId=None, sourceCaseId=None, geometryFixed=False,
                   target='coronary-14', seedFileId=None, seedSource='', extra=None):
        now = _now()
        doc = {
            'name': name,
            'fileId': fileId,
            'sourceCaseId': sourceCaseId,
            'regionFileId': regionFileId,
            'seedFileId': seedFileId,
            'seedSource': seedSource or '',
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
        }
        # Written with the case, not after it: a benchmark case must never exist,
        # even for a moment, without the flag that keeps it out of the pool.
        doc.update(extra or {})
        return self.save(doc)

    # ---------------------------------------------------------- the claim

    SERVABLE_QUERY = {
        'retired': False,
        # The annotator benchmark (D43) is never a pool case.
        'benchmark': {'$ne': True},
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
        query = _unseenBy(self.SERVABLE_QUERY, userId)
        return self.find(query, limit=limit, sort=self.SORT)

    def claim(self, caseId, userId):
        """Atomically consume one replica slot, or ``None`` if beaten to it."""
        query = _unseenBy(self.SERVABLE_QUERY, userId)
        query['_id'] = caseId
        return self.collection.find_one_and_update(
            query,
            {
                '$inc': {'activeCount': 1},
                '$push': {'assignedUserIds': userId},
                '$set': {'updated': _now()},
            },
            return_document=ReturnDocument.AFTER,
        )

    # ------------------------------------------------- the benchmark (D43)

    BENCHMARK_QUERY = {'benchmark': True}

    def benchmarkCase(self):
        """The annotator benchmark case, or None. Raises if there is more than one."""
        found = list(self.find(self.BENCHMARK_QUERY, limit=2))
        if len(found) > 1:
            raise ValidationException('More than one annotator benchmark case exists.')
        return found[0] if found else None

    def invite(self, caseId, userId):
        """Make the benchmark the next case for ``userId``. True if newly invited."""
        result = self.collection.update_one(
            {'_id': caseId, 'benchmark': True, 'benchmarkPending': {'$ne': userId}},
            {'$push': {'benchmarkPending': userId}, '$set': {'updated': _now()}})
        return bool(result.modified_count)

    def claimBenchmark(self, userId):
        """Atomically take this user's benchmark invitation, or ``None``.

        One invitation, one lease: the user leaves ``benchmarkPending`` in the same
        update that takes the slot, so two ``/next`` calls cannot both win it. A
        case with no seed is never served (it would open with nothing to correct).
        Replica counters move as for any case, but ``replicasWanted`` is never
        consulted: every invited annotator gets it.
        """
        return self.collection.find_one_and_update(
            {'benchmark': True, 'retired': False, 'seedFileId': {'$ne': None},
             'benchmarkPending': userId},
            {
                '$pull': {'benchmarkPending': userId},
                '$inc': {'activeCount': 1},
                '$addToSet': {'assignedUserIds': userId},
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

    def setExtendedMode(self, case, on=True):
        """Flag a case to be read in extended mode (D47 Q6), or clear the flag.

        The module turns the extended classes on for a flagged case and asks the
        annotator to use them. Nothing else changes: reads already submitted keep
        whatever classes they have, and a module before 0.20.0 ignores the flag.
        """
        return self.collection.find_one_and_update(
            {'_id': case['_id']},
            {'$set': {'extendedMode': bool(on), 'updated': _now()}},
            return_document=ReturnDocument.AFTER)

    def retire(self, case, reason=''):
        case['retired'] = True
        case['retiredReason'] = reason
        case['updated'] = _now()
        return self.save(case)
