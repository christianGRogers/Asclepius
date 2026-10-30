"""Janus-M read cases and reads, in ``janusm_case`` and ``janusm_read``.

A **case** is one frozen Janus-M case (seal or decision) with two read slots
(JA7). Its CT is referenced by file id in the ``ImageCAS-X`` collection and never
copied or changed; its seed, if it has one, is in ``JanusM/seeds``.

A **read** is one reader's slot on one case, from claim to acceptance. The claim
is one atomic Mongo update, as SegQueue's is: the case gives a slot only while
fewer than two are taken and only to someone it has never been given to, so the two
reads of a case are always by two different readers.
"""

import datetime

from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.model_base import AccessControlledModel
from janusm_reads import protocol, readset
from pymongo import ReturnDocument

from .constants import CASE_COLLECTION, READ_COLLECTION


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


class JanusMCase(AccessControlledModel):
    def initialize(self):
        self.name = CASE_COLLECTION
        self.ensureIndices([
            'name',
            ([('retired', 1), ('readSet', 1), ('priority', -1), ('serveOrder', 1)], {}),
            'assignedUserIds',
        ])
        # Which set a case is in, and whether it is blank, are queue mechanics a
        # reader must not see (JA7 independence; protocol section 6).
        self.exposeFields(level=AccessType.READ, fields={'_id', 'name'})
        self.exposeFields(level=AccessType.SITE_ADMIN, fields={
            'readSet', 'blank', 'priority', 'serveOrder', 'readsWanted', 'slotsTaken',
            'acceptedCount', 'retired', 'ctFileId', 'seedFileId', 'created'})

    def validate(self, doc):
        doc['name'] = readset.check_case_id(doc.get('name') or '')
        if doc.get('readSet') not in readset.SETS:
            raise ValidationException(f"readSet must be one of {readset.SETS}.", 'readSet')
        doc['blank'] = bool(doc.get('blank'))
        if doc['blank'] and doc.get('seedFileId'):
            raise ValidationException('A blank case must not have a seed (JA7).', 'seedFileId')
        if doc['blank'] and doc['readSet'] != readset.SEAL:
            raise ValidationException('Only seal cases are read from blank (JA7).', 'blank')
        for key in ('readsWanted', 'slotsTaken', 'acceptedCount', 'priority', 'serveOrder'):
            doc[key] = int(doc.get(key, 0))
        if doc['readsWanted'] < 1 or doc['slotsTaken'] < 0:
            raise ValidationException('Bad slot counts.', 'readsWanted')
        doc.setdefault('assignedUserIds', [])
        doc['retired'] = bool(doc.get('retired', False))
        return doc

    def createCase(self, plan, ctFile, checksum, seedFileId=None):
        """``plan`` is a ``janusm_reads.readset.CasePlan``."""
        return self.save({
            'name': plan.name, 'readSet': plan.read_set, 'blank': plan.blank,
            'priority': plan.priority, 'serveOrder': plan.serve_order,
            'readsWanted': plan.reads, 'slotsTaken': 0, 'acceptedCount': 0,
            'ctFileId': ctFile['_id'], 'ctChecksum': (checksum or '').lower(),
            'ctSizeBytes': int(ctFile.get('size', 0)),
            'seedFileId': None if plan.blank else seedFileId,
            'assignedUserIds': [], 'retired': False, 'created': _now(),
        })

    def _servable(self, userId, readSets):
        return {
            'retired': False,
            'readSet': {'$in': list(readSets)},
            'assignedUserIds': {'$ne': userId},
            '$expr': {'$lt': ['$slotsTaken', '$readsWanted']},
        }

    def candidates(self, userId, readSets, limit=16):
        return self.find(self._servable(userId, readSets), limit=limit,
                         sort=[('priority', -1), ('serveOrder', 1)])

    def claim(self, caseId, userId, readSets):
        """Take one slot of ``caseId`` for ``userId``, or None if it is gone."""
        query = self._servable(userId, readSets)
        query['_id'] = caseId
        return self.collection.find_one_and_update(
            query,
            {'$inc': {'slotsTaken': 1}, '$push': {'assignedUserIds': userId}},
            return_document=ReturnDocument.AFTER)

    def releaseSlot(self, caseId):
        """A released read frees its slot. The reader stays in ``assignedUserIds``,
        so the case is never handed back to them."""
        self.collection.update_one({'_id': caseId, 'slotsTaken': {'$gt': 0}},
                                   {'$inc': {'slotsTaken': -1}})

    def recordAccepted(self, caseId):
        self.collection.update_one({'_id': caseId}, {'$inc': {'acceptedCount': 1}})


class JanusMRead(AccessControlledModel):
    def initialize(self):
        self.name = READ_COLLECTION
        self.ensureIndices([
            ([('userId', 1), ('state', 1)], {}),
            ([('caseId', 1), ('state', 1)], {}),
            'state',
        ])
        self.exposeFields(level=AccessType.READ, fields={
            '_id', 'caseId', 'userId', 'state', 'seeded', 'assignedAt', 'submittedAt',
            'checkSummary'})
        self.exposeFields(level=AccessType.SITE_ADMIN, fields={
            'fileId', 'checksum', 'voxelCounts', 'check', 'checkedAt', 'attempts',
            'history', 'seconds', 'clientVersion', 'note'})

    def validate(self, doc):
        if doc.get('state') not in protocol.ALL_STATES:
            raise ValidationException(f"Unknown read state {doc.get('state')!r}.", 'state')
        return doc

    def createRead(self, case, user):
        now = _now()
        return self.save({
            'caseId': case['_id'], 'userId': user['_id'], 'state': protocol.ASSIGNED,
            'seeded': bool(case.get('seedFileId')), 'assignedAt': now,
            'submittedAt': None, 'fileId': None, 'checksum': '', 'voxelCounts': {},
            'check': None, 'checkSummary': '', 'checkedAt': None, 'attempts': 0,
            'history': [{'state': protocol.ASSIGNED, 'at': now}],
        })

    def transition(self, read, to, **fields):
        """Move ``read`` to ``to`` if that is legal from the state it is in *now*.
        Returns the updated read, or None if it moved under us."""
        if not protocol.can_move(read['state'], to):
            raise ValidationException(f"A read cannot go from {read['state']} to {to}.",
                                      'state')
        now = _now()
        update = {'$set': {'state': to, **fields},
                  '$push': {'history': {'state': to, 'at': now}}}
        if to == protocol.SUBMITTED:
            update['$inc'] = {'attempts': 1}
            update['$set']['submittedAt'] = now
        return self.collection.find_one_and_update(
            {'_id': read['_id'], 'state': read['state']}, update,
            return_document=ReturnDocument.AFTER)

    def openForUser(self, userId):
        return list(self.find({'userId': userId, 'state': {'$in': sorted(protocol.OPEN_STATES)}},
                              sort=[('assignedAt', 1)]))

    def forUser(self, userId, states=None):
        query = {'userId': userId}
        if states:
            query['state'] = {'$in': list(states)}
        return list(self.find(query, sort=[('assignedAt', 1)]))

    def submittedQueue(self, limit=25):
        return list(self.find({'state': protocol.SUBMITTED}, limit=limit,
                              sort=[('submittedAt', 1)]))
