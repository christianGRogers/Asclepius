"""Janus-M read cases and reads, in ``janusm_case`` and ``janusm_read``.

A **case** is one frozen Janus-M case (seal or decision) with two read slots
(JA7). Its CT is referenced by file id in the ``ImageCAS-X`` collection and never
copied or changed; its seed, if it has one, is in ``JanusM/seeds``. A **blank** case
has no seed (``seedFileId`` is None) but a **check seed** (``checkSeedFileId``, in
``JanusM/check-seeds``): the same model seed, which only the read check uses to fit
the mitral plane (JA66). It is never served, and nothing a reader receives names it.
A case's **wave** (``wave``) is set by an admin and selects what ``janusm-export``
writes.

A **read** is one reader's slot on one case, from claim to acceptance. The claim
is one atomic Mongo update, as SegQueue's is: the case gives a slot only while
fewer than two are taken and only to someone it has never been given to, so the two
reads of a case are always by two different readers.

A **third read** (JA47 rule 2) is one more slot on a seeded case of a flagged wave,
opened by an admin: it is read from blank (the seed is never served for it), by a
reader who has not read the case, and never counts as a reference read.

Every read record carries ``border_protocol`` (the reading rules it was drawn and
checked under), apart from the wire protocol version.

A read counts its submissions (``attempts``), its genuine returns (``returns``: a
check that ran and failed) and the checks that crashed or could not be checked
(``crashes``). Only ``returns`` spends the one return (JA68). ``seconds`` is the sum
over its submissions, as the client reported them.

PS3-S11 (JA58): every read also records, server-side and in UTC, ``claimed_at`` (set
once at claim, never moved), ``submitted_at`` (the first submission, set once) and
``submitted_at_attempts`` (every submission, in order). ``janusm-export`` writes the
time between them in ``timing.json``, with no identifier.
"""

import datetime

from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.model_base import AccessControlledModel, Model
from janusm_reads import BORDER_PROTOCOL, protocol, readset
from pymongo import ReturnDocument

from .constants import CASE_COLLECTION, READ_COLLECTION, WAVE_COLLECTION


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
            'acceptedCount', 'retired', 'ctFileId', 'seedFileId', 'checkSeedFileId',
            'wave', 'created', 'thirdReadWanted', 'thirdReadTaken', 'thirdReadAccepted'})

    def validate(self, doc):
        doc['name'] = readset.check_case_id(doc.get('name') or '')
        if doc.get('readSet') not in readset.SETS:
            raise ValidationException(f"readSet must be one of {readset.SETS}.", 'readSet')
        doc['blank'] = bool(doc.get('blank'))
        if doc['blank'] and doc.get('seedFileId'):
            raise ValidationException('A blank case must not have a seed (JA7).', 'seedFileId')
        if doc['blank'] and doc['readSet'] != readset.SEAL:
            raise ValidationException('Only seal cases are read from blank (JA7).', 'blank')
        if doc.get('checkSeedFileId') and not doc['blank']:
            raise ValidationException('Only a blank case has a check seed (JA66); a seeded '
                                      "case's seed is its check seed.", 'checkSeedFileId')
        wave = doc.get('wave')
        doc['wave'] = None if wave in (None, '') else str(wave)
        for key in ('readsWanted', 'slotsTaken', 'acceptedCount', 'priority', 'serveOrder'):
            doc[key] = int(doc.get(key, 0))
        if doc['readsWanted'] < 1 or doc['slotsTaken'] < 0:
            raise ValidationException('Bad slot counts.', 'readsWanted')
        doc.setdefault('assignedUserIds', [])
        doc['retired'] = bool(doc.get('retired', False))
        for key in ('thirdReadWanted', 'thirdReadTaken', 'thirdReadAccepted'):
            doc[key] = bool(doc.get(key, False))
        if doc['thirdReadWanted'] and doc['blank']:
            raise ValidationException('A third read is only for a seeded case (JA47).',
                                      'thirdReadWanted')
        return doc

    def createCase(self, plan, ctFile, checksum, seedFileId=None, checkSeedFileId=None):
        """``plan`` is a ``janusm_reads.readset.CasePlan``. A blank case keeps only its
        ``checkSeedFileId``; a seeded case only its ``seedFileId``."""
        return self.save({
            'name': plan.name, 'readSet': plan.read_set, 'blank': plan.blank,
            'priority': plan.priority, 'serveOrder': plan.serve_order,
            'readsWanted': plan.reads, 'slotsTaken': 0, 'acceptedCount': 0,
            'ctFileId': ctFile['_id'], 'ctChecksum': (checksum or '').lower(),
            'ctSizeBytes': int(ctFile.get('size', 0)),
            'seedFileId': None if plan.blank else seedFileId,
            'checkSeedFileId': checkSeedFileId if plan.blank else None,
            'wave': None, 'assignedUserIds': [], 'retired': False, 'created': _now(),
        })

    def checkSeedId(self, case):
        """The seed the read check fits the mitral plane to (JA66): the served seed on a
        seeded case, the hidden check seed on a blank one. Server-side only."""
        return case.get('seedFileId') or case.get('checkSeedFileId')

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

    # ------------------------------------------------------------ third reads

    def openThirdRead(self, case):
        """JA47 rule 2: one more slot on a seeded, double-read case, read from blank."""
        return self.collection.find_one_and_update(
            {'_id': case['_id'], 'blank': False, 'thirdReadWanted': {'$ne': True}},
            {'$set': {'thirdReadWanted': True, 'thirdReadTaken': False,
                      'thirdReadAccepted': False}},
            return_document=ReturnDocument.AFTER)

    def _thirdServable(self, userId, readSets):
        return {'retired': False, 'readSet': {'$in': list(readSets)},
                'thirdReadWanted': True, 'thirdReadTaken': {'$ne': True},
                'assignedUserIds': {'$ne': userId}}

    def thirdCandidates(self, userId, readSets, limit=16):
        return self.find(self._thirdServable(userId, readSets), limit=limit,
                         sort=[('priority', -1), ('serveOrder', 1)])

    def claimThird(self, caseId, userId, readSets):
        """Take a case's third-read slot for ``userId`` -- never someone who has read
        it -- or None if it is gone."""
        query = self._thirdServable(userId, readSets)
        query['_id'] = caseId
        return self.collection.find_one_and_update(
            query, {'$set': {'thirdReadTaken': True}, '$push': {'assignedUserIds': userId}},
            return_document=ReturnDocument.AFTER)

    def releaseThird(self, caseId):
        self.collection.update_one({'_id': caseId}, {'$set': {'thirdReadTaken': False}})

    def recordThirdAccepted(self, caseId):
        self.collection.update_one({'_id': caseId}, {'$set': {'thirdReadAccepted': True}})

    # ------------------------------------------------------------------ waves

    def frozenInWave(self, case):
        """JA78: a case that has an accepted read, a third read wanted, or an open third
        read never changes wave."""
        if case.get('acceptedCount') or case.get('thirdReadWanted') \
                or case.get('thirdReadTaken') or case.get('thirdReadAccepted'):
            return True
        return JanusMRead().collection.count_documents(
            {'caseId': case['_id'], 'state': protocol.ACCEPTED}, limit=1) > 0


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
            'checkSummary', 'flagged'})
        self.exposeFields(level=AccessType.SITE_ADMIN, fields={
            'fileId', 'checksum', 'voxelCounts', 'check', 'checkedAt', 'attempts',
            'returns', 'crashes', 'history', 'seconds', 'clientVersion', 'note',
            'flagReasons', 'third', 'cadrads', 'lesionPoints', 'border_protocol',
            protocol.CLAIMED_AT, protocol.SUBMITTED_AT, protocol.SUBMITTED_AT_ATTEMPTS})

    def validate(self, doc):
        if doc.get('state') not in protocol.ALL_STATES:
            raise ValidationException(f"Unknown read state {doc.get('state')!r}.", 'state')
        return doc

    def createRead(self, case, user, third=False):
        """A third read (JA47 rule 2) is read from blank whatever the case has."""
        now = _now()
        return self.save({
            'caseId': case['_id'], 'userId': user['_id'], 'state': protocol.ASSIGNED,
            'seeded': bool(case.get('seedFileId')) and not third, 'third': bool(third),
            'assignedAt': now,
            # PS3-S11: set once here; a returned and resubmitted read keeps it.
            protocol.CLAIMED_AT: now, protocol.SUBMITTED_AT: None,
            protocol.SUBMITTED_AT_ATTEMPTS: [],
            'submittedAt': None, 'fileId': None, 'checksum': '', 'voxelCounts': {},
            'check': None, 'checkSummary': '', 'checkedAt': None, 'attempts': 0,
            'returns': 0, 'crashes': 0, 'seconds': 0.0,
            'flagged': False, 'flagReasons': [], 'cadrads': {}, 'lesionPoints': {},
            'border_protocol': BORDER_PROTOCOL,
            'history': [{'state': protocol.ASSIGNED, 'at': now}],
        })

    def transition(self, read, to, inc=None, **fields):
        """Move ``read`` to ``to`` if that is legal from the state it is in *now*, adding
        ``inc`` (``{field: amount}``) to its counters. Returns the updated read, or None
        if it moved under us."""
        if not protocol.can_move(read['state'], to):
            raise ValidationException(f"A read cannot go from {read['state']} to {to}.",
                                      'state')
        now = _now()
        update = {'$set': {'state': to, **fields},
                  '$push': {'history': {'state': to, 'at': now}}}
        counters = dict(inc or {})
        if to == protocol.SUBMITTED:
            counters['attempts'] = counters.get('attempts', 0) + 1
            update['$set']['submittedAt'] = now
            # PS3-S11: every submission's time, and the first one once.
            update['$push'][protocol.SUBMITTED_AT_ATTEMPTS] = now
        if counters:
            update['$inc'] = counters
        moved = self.collection.find_one_and_update(
            {'_id': read['_id'], 'state': read['state']}, update,
            return_document=ReturnDocument.AFTER)
        if moved is not None and to == protocol.SUBMITTED \
                and moved.get(protocol.SUBMITTED_AT) is None:
            self.collection.update_one(
                {'_id': moved['_id'], protocol.SUBMITTED_AT: None},
                {'$set': {protocol.SUBMITTED_AT: now}})
            moved = self.collection.find_one({'_id': moved['_id']})
        return moved

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


class JanusMWave(Model):
    """One document per wave whose anchoring report opened third reads (JA78): the
    report's sha256, so a different report for that wave is refused later, and the
    export records which report the wave was judged on."""

    def initialize(self):
        self.name = WAVE_COLLECTION
        self.ensureIndices([([('wave', 1)], {'unique': True})])

    def validate(self, doc):
        doc['wave'] = str(doc.get('wave') or '').strip()
        if not doc['wave']:
            raise ValidationException('A wave needs a name.', 'wave')
        return doc

    def reportHash(self, wave):
        doc = self.findOne({'wave': str(wave)})
        return doc.get('anchoringReportSha256') if doc else None

    def recordReport(self, wave, sha256, user):
        """Store ``sha256`` as the wave's report unless it has one. Returns the hash the
        wave holds afterwards (a different one means the report was refused)."""
        self.collection.update_one(
            {'wave': str(wave)},
            {'$setOnInsert': {'wave': str(wave), 'anchoringReportSha256': sha256,
                              'recordedBy': user.get('login') if user else None,
                              'recordedAt': _now()}},
            upsert=True)
        return self.reportHash(wave)
