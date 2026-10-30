"""``/api/v1/janusm``: the Janus-M read queue (JA7).

Readers: ``project``, ``mine``, ``next``, then per read ``ct``, ``seed``, ``submit``
and ``release``. Admins (site admins or ``janusm-admins``): the case table, a
case's reads, opening the seal, putting cases in a wave, running the check on a read
now, and opening a flagged wave's drawn third reads (JA47 rule 2, JA68).

A blank case's **check seed** (``checkSeedFileId``, JA66) is touched by no route
here: ``seed`` serves only a seeded case's ``seedFileId``, and ``readInfo`` says
``hasSeed: false``.

Every case served goes through the JA12 guard at claim time, under its set's
purpose, as well as at populate time: a case the guard refuses later (a changed
hold-out list) is retired, not served.
"""

import logging

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import AccessType
from girder.models.file import File
from girder.models.item import Item
from girder.models.setting import Setting
from janusm_reads import (
    BORDER_PROTOCOL,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    holdout,
    niftihead,
    protocol,
    readset,
)
from janusm_reads import labels as L

from .constants import MAX_CLAIM_ATTEMPTS, SETTING_SEAL_OPEN
from .models import JanusMCase, JanusMRead
from .utils import (
    checkClientProtocol,
    ctWorldBounds,
    hashStoredFile,
    incomingFolder,
    maxOpen,
    readsFolder,
    refuse,
    requireAdmin,
    requireReader,
    sealOpen,
)

logger = logging.getLogger(__name__)


def readInfo(read, case=None):
    """What a reader sees of their own read. The half-maximum profiles go with a
    returned read only; nothing names the read set, a third read, the other read or a
    blank case's check seed (``hasSeed`` is the read's own ``seeded``)."""
    case = case or JanusMCase().load(read['caseId'], force=True) or {}
    returned = read['state'] == protocol.RETURNED
    return protocol.ReadInfo(
        read_id=str(read['_id']), case_name=case.get('name', ''), state=read['state'],
        has_seed=bool(read.get('seeded')), checksum=case.get('ctChecksum', ''),
        size_bytes=int(case.get('ctSizeBytes', 0)),
        check_summary=read.get('checkSummary', '') or '',
        flagged=bool(read.get('flagged')),
        check_profile=protocol.profile_for_reader(read.get('check')) if returned else {})


def servableSets():
    return [readset.DECISION, readset.SEAL] if sealOpen() else [readset.DECISION]


def guardCase(case):
    """The JA12 guard on one case, under its set's purpose. A refused case is retired."""
    try:
        holdout.refuse([case['name']], what=f"serving Janus-M case {case['name']}",
                       purpose=holdout.purpose_for(case['readSet']))
        return True
    except holdout.HoldoutError as exc:
        logger.error('Janus-M case %s refused by the JA12 guard and retired: %s',
                     case['name'], exc)
        JanusMCase().collection.update_one(
            {'_id': case['_id']}, {'$set': {'retired': True, 'retiredReason': str(exc)}})
        return False


def claimNext(user):
    """A third read waiting for this reader first (JA47 rule 2), then the next slot."""
    sets = servableSets()
    for _ in range(MAX_CLAIM_ATTEMPTS):
        thirds = list(JanusMCase().thirdCandidates(user['_id'], sets))
        candidates = list(JanusMCase().candidates(user['_id'], sets))
        if not thirds and not candidates:
            return None
        for case in thirds:
            if not guardCase(case):
                continue
            claimed = JanusMCase().claimThird(case['_id'], user['_id'], sets)
            if claimed is not None:
                return JanusMRead().createRead(claimed, user, third=True), claimed
        for case in candidates:
            if not guardCase(case):
                continue
            claimed = JanusMCase().claim(case['_id'], user['_id'], sets)
            if claimed is not None:
                return JanusMRead().createRead(claimed, user), claimed
    return None


class JanusMResource(Resource):
    def __init__(self):
        super().__init__()
        self.resourceName = protocol.API_PREFIX
        self.route('GET', ('project',), self.getProject)
        self.route('GET', ('mine',), self.listMine)
        self.route('POST', ('next',), self.nextRead)
        self.route('GET', ('read', ':readId', 'ct'), self.downloadCt)
        self.route('GET', ('read', ':readId', 'seed'), self.downloadSeed)
        self.route('POST', ('read', ':readId', 'submit'), self.submit)
        self.route('POST', ('read', ':readId', 'release'), self.release)
        self.route('GET', ('admin', 'cases'), self.adminCases)
        self.route('GET', ('admin', 'case', ':caseId', 'reads'), self.adminReads)
        self.route('POST', ('admin', 'seal', 'open'), self.adminOpenSeal)
        self.route('POST', ('admin', 'read', ':readId', 'check'), self.adminCheck)
        self.route('POST', ('admin', 'wave'), self.adminWave)
        self.route('POST', ('admin', 'third-reads'), self.adminThirdReads)

    # ------------------------------------------------------------ readers

    @access.user
    @autoDescribeRoute(
        Description('The Janus-M read protocol and the labels a read uses.')
        .param('clientProtocol', 'Janus-M read protocol the client speaks.',
               dataType='integer', required=False)
    )
    def getProject(self, clientProtocol):
        checkClientProtocol(clientProtocol)
        user = requireReader(self.getCurrentUser())
        return {
            'protocol': PROTOCOL_NAME, 'protocolVersion': PROTOCOL_VERSION,
            'border_protocol': BORDER_PROTOCOL,
            'protocolDocument': 'docs/JANUSM-READ-PROTOCOL.md',
            'readForm': {'vessels': list(protocol.VESSELS),
                         'cadrads': list(protocol.CADRADS_GRADES),
                         'grades': {v: list(protocol.grades_for(v))
                                    for v in protocol.VESSELS},
                         'lesionGrades': sorted(protocol.LESION_GRADES)},
            'labels': [{'value': v, 'name': n, 'includes': L.CONVENTIONS[v],
                        'color': list(L.COLORS[v])} for v, n in L.CLASSES.items()],
            'maxOpen': maxOpen(),
            'uploadFolderId': str(incomingFolder(user)['_id']),
        }

    @access.user
    @autoDescribeRoute(Description('My Janus-M reads.'))
    def listMine(self):
        user = requireReader(self.getCurrentUser())
        return [readInfo(r).to_dict() for r in JanusMRead().forUser(user['_id'])]

    @access.user
    @autoDescribeRoute(
        Description('Take the next Janus-M case to read.')
        .param('clientProtocol', 'Janus-M read protocol the client speaks.',
               dataType='integer', required=False)
        .errorResponse('Finish the read you hold first.', 409)
        .errorResponse('Nothing left for you to read.', 404)
        .errorResponse('The client is not a current Janus-M read client.', 426)
    )
    def nextRead(self, clientProtocol):
        checkClientProtocol(clientProtocol)
        user = requireReader(self.getCurrentUser())
        if len(JanusMRead().openForUser(user['_id'])) >= maxOpen():
            refuse(protocol.ERR_AT_LIMIT, 'Finish or release the read you hold first.',
                   status=409)
        got = claimNext(user)
        if got is None:
            refuse(protocol.ERR_QUEUE_EMPTY, 'No Janus-M case is waiting for you.',
                   status=404)
        read, case = got
        return readInfo(read, case).to_dict()

    def _ownOpenRead(self, readId, user):
        read = JanusMRead().load(readId, force=True)
        if read is None or read['userId'] != user['_id']:
            refuse(protocol.ERR_NOT_YOURS, 'That read is not yours.', status=403)
        if read['state'] not in protocol.OPEN_STATES:
            refuse(protocol.ERR_BAD_STATE, f"That read is {read['state']}.", status=409,
                   state=read['state'])
        return read

    @access.user
    @autoDescribeRoute(
        Description('Download the CT of one of my open reads.')
        .param('readId', 'The read.', paramType='path')
    )
    def downloadCt(self, readId):
        user = requireReader(self.getCurrentUser())
        read = self._ownOpenRead(readId, user)
        case = JanusMCase().load(read['caseId'], force=True)
        file = File().load(case['ctFileId'], force=True)
        if file is None:
            refuse('janusm_ct_missing', 'The CT for this case is missing from storage.',
                   status=500)
        return File().download(file)

    @access.user
    @autoDescribeRoute(
        Description('Download the seed of one of my open reads. 404 on a blank case.')
        .param('readId', 'The read.', paramType='path')
    )
    def downloadSeed(self, readId):
        user = requireReader(self.getCurrentUser())
        read = self._ownOpenRead(readId, user)
        case = JanusMCase().load(read['caseId'], force=True)
        # Only the served seed, never a blank case's check seed (JA66).
        if not read.get('seeded') or not case.get('seedFileId'):
            refuse(protocol.ERR_NO_SEED, 'This case is read from blank: it has no seed.',
                   status=404)
        return File().download(File().load(case['seedFileId'], force=True))

    @access.user
    @autoDescribeRoute(
        Description('Submit one of my reads.')
        .notes('Upload the label volume (values 0-4, on the CT grid) into the Janus-M '
               'incoming folder first, then call this with its file id.')
        .param('readId', 'The read.', paramType='path')
        .param('fileId', 'Girder file id of the uploaded read.')
        .jsonParam('meta', 'ReadSubmission as JSON.', requireObject=True)
        .param('clientProtocol', 'Janus-M read protocol the client speaks.',
               dataType='integer', required=False)
    )
    def submit(self, readId, fileId, meta, clientProtocol):
        checkClientProtocol(clientProtocol)
        user = requireReader(self.getCurrentUser())
        read = self._ownOpenRead(readId, user)
        sub = protocol.ReadSubmission.from_dict(meta)
        missing = L.missing_required(sub.voxel_counts)
        if missing:
            refuse(protocol.ERR_MISSING_CLASS, L.missing_message(missing), status=400,
                   missing=missing)
        problems = sub.form_problems()
        if not problems and sub.lesion_points:
            # JA67: a lesion point lies inside the CT's world bounding box.
            case = JanusMCase().load(read['caseId'], force=True)
            bounds = ctWorldBounds(case)
            if bounds is None:
                logger.error('Janus-M case %s: the CT header could not be read; lesion '
                             'points were not bounds-checked.', case.get('name'))
            problems = niftihead.points_outside(sub.lesion_points, bounds)
        if problems:
            refuse(protocol.ERR_READ_FORM, ' '.join(problems), status=400, problems=problems)
        file = File().load(fileId, level=AccessType.WRITE, user=user)
        if file is None:
            refuse('no_such_file', 'That upload could not be found.', status=404)
        if sub.size_bytes and int(file['size']) != sub.size_bytes:
            refuse(protocol.ERR_CHECKSUM, 'The upload is incomplete; submit again.', status=400)
        actual = hashStoredFile(file)
        if sub.checksum and sub.checksum != actual:
            refuse(protocol.ERR_CHECKSUM, 'The upload does not match its checksum; submit '
                   'again.', status=400, expected=sub.checksum, actual=actual)
        item = Item().load(file['itemId'], force=True)
        if item is not None:
            Item().move(item, readsFolder())
        # ``seconds`` is this submission's; the read's is the sum over them (S5.8).
        moved = JanusMRead().transition(
            read, protocol.SUBMITTED, inc={'seconds': max(0.0, float(sub.seconds))},
            fileId=file['_id'], checksum=actual,
            sizeBytes=int(file['size']), voxelCounts=sub.voxel_counts,
            clientVersion=sub.client_version, note=sub.note, check=None, checkSummary='',
            cadrads=dict(sub.cadrads), lesionPoints=dict(sub.lesion_points),
            border_protocol=BORDER_PROTOCOL)
        if moved is None:
            refuse(protocol.ERR_BAD_STATE, 'That read changed state; reload.', status=409)
        return readInfo(moved).to_dict()

    @access.user
    @autoDescribeRoute(
        Description('Give a read back. The case is never handed back to you.')
        .param('readId', 'The read.', paramType='path')
    )
    def release(self, readId):
        user = requireReader(self.getCurrentUser())
        read = self._ownOpenRead(readId, user)
        moved = JanusMRead().transition(read, protocol.RELEASED)
        if moved is None:
            refuse(protocol.ERR_BAD_STATE, 'That read changed state; reload.', status=409)
        if read.get('third'):
            JanusMCase().releaseThird(read['caseId'])
        else:
            JanusMCase().releaseSlot(read['caseId'])
        return readInfo(moved).to_dict()

    # ------------------------------------------------------------- admins

    @access.user
    @autoDescribeRoute(Description('Every Janus-M case and its read counts (admins).'))
    def adminCases(self):
        requireAdmin(self.getCurrentUser())
        out = []
        for case in JanusMCase().find({}, sort=[('priority', -1), ('serveOrder', 1)]):
            out.append({
                'caseId': str(case['_id']), 'name': case['name'], 'readSet': case['readSet'],
                'blank': case['blank'], 'slotsTaken': case['slotsTaken'],
                'accepted': case['acceptedCount'], 'retired': case['retired'],
                'wave': case.get('wave'), 'hasSeed': bool(case.get('seedFileId')),
                'hasCheckSeed': bool(JanusMCase().checkSeedId(case)),
                'thirdRead': ('accepted' if case.get('thirdReadAccepted') else 'taken'
                              if case.get('thirdReadTaken') else 'waiting'
                              if case.get('thirdReadWanted') else None),
            })
        return {'sealOpen': sealOpen(), 'cases': out}

    @access.user
    @autoDescribeRoute(
        Description('The reads of one case, with their check reports (admins).')
        .modelParam('caseId', 'The case.', model=JanusMCase, force=True, destName='case')
    )
    def adminReads(self, case):
        requireAdmin(self.getCurrentUser())
        return [{'readId': str(r['_id']), 'userId': str(r['userId']), 'state': r['state'],
                 'seeded': r.get('seeded'), 'check': r.get('check'),
                 'attempts': r.get('attempts', 0), 'returns': r.get('returns', 0),
                 'crashes': r.get('crashes', 0), 'flagged': bool(r.get('flagged')),
                 'flagReasons': r.get('flagReasons') or [], 'third': bool(r.get('third')),
                 'border_protocol': r.get('border_protocol')}
                for r in JanusMRead().find({'caseId': case['_id']}, sort=[('assignedAt', 1)])]

    @access.user
    @autoDescribeRoute(
        Description('Open (or close) the seal cases for reading (admins).')
        .notes('JA6: only after the seal is re-powered on the first 20 double-read '
               'decision cases.')
        .param('open', 'Open the seal.', dataType='boolean', required=False, default=True)
    )
    def adminOpenSeal(self, open):
        requireAdmin(self.getCurrentUser())
        Setting().set(SETTING_SEAL_OPEN, bool(open))
        return {'sealOpen': sealOpen()}

    @access.user
    @autoDescribeRoute(
        Description('Run the automatic read check on a submitted read now (admins).')
        .param('readId', 'The read.', paramType='path')
    )
    def adminCheck(self, readId):
        requireAdmin(self.getCurrentUser())
        from .check import checkRead

        read = JanusMRead().load(readId, force=True)
        if read is None or read['state'] != protocol.SUBMITTED:
            refuse(protocol.ERR_BAD_STATE, 'Only a submitted read can be checked.', status=409)
        done = checkRead(read)
        return {'state': done['state'], 'check': done.get('check')}

    @access.user
    @autoDescribeRoute(
        Description('Put cases in a read wave (admins); janusm-export writes one wave.')
        .param('wave', 'The wave, e.g. "1".')
        .jsonParam('cases', 'Case names, as a JSON list.', requireArray=True)
    )
    def adminWave(self, wave, cases):
        requireAdmin(self.getCurrentUser())
        wave = str(wave or '').strip()
        if not wave:
            refuse(protocol.ERR_BAD_STATE, 'A wave needs a name.', status=400)
        names = [str(c) for c in cases]
        found = {c['name'] for c in JanusMCase().find({'name': {'$in': names}})}
        unknown = [n for n in names if n not in found]
        if unknown or not names:
            refuse(protocol.ERR_BAD_STATE, 'No wave set: not Janus-M cases: '
                   + ', '.join(unknown or ['(none given)']), status=400, unknown=unknown)
        JanusMCase().collection.update_many({'name': {'$in': names}}, {'$set': {'wave': wave}})
        return {'wave': wave, 'cases': sorted(found)}

    def _seededDoubleRead(self, wave):
        """The wave's seeded cases whose two reference reads are both accepted: the
        cases the wave's anchoring report counts as seeded."""
        return sorted(c['name'] for c in JanusMCase().find({'wave': wave, 'blank': False})
                      if c['acceptedCount'] >= c['readsWanted'])

    @access.user
    @autoDescribeRoute(
        Description("Open third reads from blank on a flagged wave's drawn cases (admins).")
        .notes('JA47 rule 2, as JA68 rules it: refused unless the wave\'s anchoring report '
               'has rule2.flagged and `cases` is exactly '
               'anchoring.third_read_cases(wave, its seeded double-read cases). The third '
               'read is served without the seed to a reader who has not read the case, '
               'and never enters the reference standard.')
        .param('wave', 'The flagged wave.')
        .jsonParam('report', "The wave's anchoring report (janusm_reads.anchoring).",
                   requireObject=True)
        .jsonParam('cases', 'Case names, as a JSON list.', requireArray=True)
    )
    def adminThirdReads(self, wave, report, cases):
        requireAdmin(self.getCurrentUser())
        wave = str(wave or '').strip()
        names = [str(c) for c in cases]
        seeded = self._seededDoubleRead(wave) if wave else []
        drawn = readset.third_read_cases(wave, seeded)
        reported = {r.get('case') for r in report.get('rows') or [] if not r.get('blank')}
        problems = []
        if not wave or str(report.get('wave', '')) != wave:
            problems.append(f'the report is for wave {report.get("wave")!r}, not {wave!r}')
        elif not (report.get('rule2') or {}).get('flagged'):
            problems.append(f'wave {wave} is not flagged by rule 2')
        elif reported != set(seeded):
            problems.append(f"the report's seeded cases are not wave {wave}'s "
                            f'{len(seeded)} seeded double-read cases')
        elif len(names) != len(set(names)) or sorted(names) != sorted(drawn):
            problems.append(f'the cases are not wave {wave}\'s rule-2 draw '
                            f'({len(drawn)} cases: {", ".join(drawn)})')
        if problems:
            refuse(protocol.ERR_BAD_STATE, 'No third read opened: ' + '; '.join(problems),
                   status=400, problems=problems)
        found = {c['name']: c for c in JanusMCase().find({'name': {'$in': names}})}
        opened = [name for name in names if JanusMCase().openThirdRead(found[name])]
        return {'opened': opened, 'alreadyOpen': [n for n in names if n not in opened]}
