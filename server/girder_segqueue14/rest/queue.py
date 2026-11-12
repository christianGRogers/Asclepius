"""Annotator endpoints under ``/segqueue14``: get a case, fetch it and its
prelabel, send the correction back, give it up.

Adapted from ``girder_segqueue.rest.queue``. The differences:

* ``/next`` serves strictly in the order the population tool wrote (priority,
  then serveOrder): no gold injection and no random duplicates, because both are
  data here (D11, D14, D16).
* the ``prelabel`` asset replaces the live binary ``seed`` (D8, D25), and serving
  it records which model version the read starts from; pooled new-dataset cases
  ship their own binary vessel ``seed`` instead (D23), a guide that is never
  submitted;
* ``/submit`` checks nothing about the segmentation (#270, project lead
  2026-11-02): only login, role, ownership, state, protocol and the upload's
  size and checksum. An empty LAD, LCx or RCA (D13) or overlapping classes (D26)
  are accepted; voxel counts and geometry are recorded with the submission;
* every write -- and ``/project``, which the module calls at login -- checks the
  SegQueue14 protocol version, so an out-of-date module is told to update before
  it can do anything. Protocol 17 (0.17.x, four classes) and 18 (0.18.0, the
  optional extended classes, D44) are both accepted; ``/project`` serves the four
  classes either way, and a 0.18 module adds the extended ones itself.
"""

import random

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import AccessType
from girder.models.file import File
from girder.models.item import Item
from segqueue import policy as pol
from segqueue import states as st
from segqueue.checksum import matches
from segqueue14 import plan as sqplan
from segqueue14 import protocol

from ..constants import MAX_ASSIGN_ATTEMPTS, QUOTA_FIELD
from ..models import Assignment14, Case14, Note14, Submission14
from ..models.assignment import NOT_BENCHMARK
from ..settings import getPolicy, getProject
from ..utils import (
    checkClientProtocol,
    checkLabelFormat,
    checkReopenReader,
    fileForCase,
    hashStoredFile,
    incomingFolder,
    loadOwnAssignment,
    refuse,
    requireAnnotator,
    requireCaseInvolvement,
    storedLabelInfo,
    submissionsFolder,
)


def quotaRemaining(user):
    quota = user.get(QUOTA_FIELD)
    if quota is None:
        return None
    # A benchmark read (D43) is not one of the cases a quota counts.
    done = Assignment14().collection.count_documents(
        {'userId': user['_id'], 'state': st.APPROVED, 'kind': NOT_BENCHMARK})
    return max(0, int(quota) - done)


def assignmentInfo(assignment):
    """The annotator's view of one assignment. Never says what kind it is."""
    case = Case14().load(assignment['caseId'], force=True) or {}
    deadline = assignment.get('deadline')
    assignedAt = assignment.get('assignedAt')
    volumeFile = File().load(case['fileId'], force=True) if case.get('fileId') else None
    return protocol.AssignmentInfo14(
        assignment_id=str(assignment['_id']),
        case_id=str(assignment['caseId']),
        case_name=case.get('name', ''),
        state=assignment['state'],
        attempt=assignment.get('attempt', 1),
        size_bytes=case.get('sizeBytes', 0),
        checksum=case.get('checksum', ''),
        volume_name=(volumeFile or {}).get('name', ''),
        assigned_at=assignedAt.timestamp() if assignedAt else None,
        deadline=deadline.timestamp() if deadline else None,
        reviewer_comment=assignment.get('reviewerComment', ''),
        has_region=bool(case.get('regionFileId')),
        has_seed=bool(case.get('seedFileId')),
        has_prelabel=bool(case.get('prelabelFileId')),
        prelabel_version=case.get('prelabelVersion') or '',
        start_from_own=isReopened(assignment),
    )


def isReopened(assignment):
    """Reopened for the annotator's own revision (#315) and not yet resubmitted."""
    return bool(assignment.get('startFileId')) and assignment['state'] in st.OPEN_STATES


def claimNext(user, policy):
    """Win the first servable case in serve order. ``None`` if the pool is dry.

    The retry loop is for lost races only: each failed claim means someone else
    took that exact case a moment earlier, so the next scan starts from the
    following one.
    """
    userId = user['_id']
    for _ in range(MAX_ASSIGN_ATTEMPTS):
        candidates = list(Case14().candidates(userId))
        if not candidates:
            return None
        for case in candidates:
            claimed = Case14().claim(case['_id'], userId)
            if claimed is not None:
                return Assignment14().createAssignment(
                    claimed, user, kind=None, policy=policy)
    return None


def claimBenchmark(user, policy):
    """This user's annotator benchmark (D43), if they have been assigned it.

    Checked before the pool, so an invited annotator gets it as their next case.
    Each invitation is one attempt: the lease records which attempt it is, and a
    retest is a fresh invitation (``segqueue14-benchmark assign --retest``).
    """
    claimed = Case14().claimBenchmark(user['_id'])
    if claimed is None:
        return None
    attempt = len(Assignment14().benchmarkHistory(claimed['_id'], user['_id'])) + 1
    return Assignment14().createAssignment(
        claimed, user, kind=sqplan.KIND_BENCHMARK, policy=policy,
        extra={'benchmarkAttempt': attempt})


class QueueResource14(Resource):
    def __init__(self):
        super().__init__()
        self.resourceName = protocol.API_PREFIX

        self.route('GET', ('project',), self.getProject)
        self.route('GET', ('mine',), self.listMine)
        self.route('POST', ('next',), self.nextCase)
        self.route('GET', ('case', ':caseId', 'download'), self.downloadCase)
        self.route('GET', ('case', ':caseId', 'asset', ':kind'), self.downloadAsset)
        self.route('GET', ('case', ':caseId', 'notes'), self.listNotes)
        self.route('POST', ('case', ':caseId', 'notes'), self.addNote)
        self.route('POST', ('assignment', ':assignmentId', 'submit'), self.submit)
        self.route('POST', ('assignment', ':assignmentId', 'release'), self.release)
        self.route('POST', ('assignment', ':assignmentId', 'heartbeat'), self.heartbeat)

    # ------------------------------------------------------------- project

    @access.user
    @autoDescribeRoute(
        Description('Fetch the SegQueue14 protocol and this user\'s limits.')
        .notes('Called at login. Refuses an out-of-date SegQueue14 module (426), '
               'so the annotator is told to update before opening a case.')
        .param('clientProtocol', 'SegQueue14 protocol version the client speaks.',
               dataType='integer', required=False)
    )
    def getProject(self, clientProtocol):
        checkClientProtocol(clientProtocol)
        user = requireAnnotator(self.getCurrentUser())
        return getProject(
            quotaRemaining=quotaRemaining(user),
            uploadFolderId=str(incomingFolder(user)['_id']),
        ).to_dict()

    # ---------------------------------------------------------------- mine

    @access.user
    @autoDescribeRoute(
        Description('List my SegQueue14 assignments.')
        .param('includeFinished', 'Also return approved and released work.',
               dataType='boolean', required=False, default=False)
    )
    def listMine(self, includeFinished):
        user = requireAnnotator(self.getCurrentUser())
        states = None if includeFinished else sorted(st.OPEN_STATES)
        return [assignmentInfo(a).to_dict()
                for a in Assignment14().forUser(user['_id'], states)]

    # ---------------------------------------------------------------- next

    @access.user
    @autoDescribeRoute(
        Description('Assign me the next SegQueue14 case and return it.')
        .notes('Atomic, and in serve order as set by segqueue14-populate. An '
               'annotator assigned the annotator benchmark (D43) gets it first.')
        .param('clientProtocol', 'SegQueue14 protocol version the client speaks.',
               dataType='integer', required=False)
        .errorResponse('You already hold the maximum number of cases.', 409)
        .errorResponse('Nothing left to assign.', 404)
        .errorResponse('The SegQueue14 module is out of date.', 426)
    )
    def nextCase(self, clientProtocol):
        checkClientProtocol(clientProtocol)
        user = requireAnnotator(self.getCurrentUser())
        policy = getPolicy()

        # A read reopened for her own revision (#315) comes before anything new,
        # and is not one of the cases a quota counts.
        reopened = Assignment14().reopenedForUser(user['_id'])
        if reopened:
            return assignmentInfo(reopened[0]).to_dict()

        openCount = Assignment14().countOpenForUser(user['_id'])
        # The annotator benchmark (D43) comes first, whatever the quota says: it
        # is not one of the cases a quota counts. An annotator holding a case
        # gets it right after, as the concurrency limit still applies.
        if openCount < policy.max_concurrent:
            assignment = claimBenchmark(user, policy)
            if assignment is not None:
                return assignmentInfo(assignment).to_dict()
        remaining = quotaRemaining(user)
        if not pol.can_take_more(openCount, policy, remaining):
            if remaining is not None and remaining <= 0:
                refuse(protocol.ERR_QUOTA,
                       'You have finished your assigned quota. Thank you!', status=403)
            refuse(protocol.ERR_AT_LIMIT,
                   'Finish or release the case you already have before asking for '
                   'another.', status=409, maxConcurrent=policy.max_concurrent)

        assignment = claimNext(user, policy)
        if assignment is None:
            refuse(protocol.ERR_QUEUE_EMPTY,
                   'No SegQueue14 cases are available for you right now. Check with '
                   'the project admin before assuming it is a bug.', status=404)
        return assignmentInfo(assignment).to_dict()

    # ------------------------------------------------------------ download

    @access.user
    @autoDescribeRoute(
        Description('Download the CT for a case assigned to me.')
        .modelParam('caseId', 'The case.', model=Case14, force=True, destName='case')
        .errorResponse('That case is not assigned to you.', 403)
    )
    def downloadCase(self, case):
        user = requireAnnotator(self.getCurrentUser())
        assignment = self._requireOpenAssignment(case, user)
        if isReopened(assignment):
            # An older module would open it from the seed, not from her read.
            checkReopenReader()
        if assignment['state'] == st.REJECTED:
            assignment = Assignment14().transition(
                assignment, st.REWORK, policy=getPolicy())
        if assignment['state'] == st.ASSIGNED:
            Assignment14().transition(assignment, st.DOWNLOAD)
        return File().download(fileForCase(case))

    @access.user
    @autoDescribeRoute(
        Description('Download a case\'s prelabel, vessel seed or heart-region mask.')
        .notes('``prelabel`` is a model prediction the annotator corrects; '
               '``seed`` is a binary vessel mask to divide into the four classes '
               '(D23, D25); ``region`` is the heart mask that frames the view. '
               'A 404 means the case has none of that kind.')
        .modelParam('caseId', 'The case.', model=Case14, force=True, destName='case')
        .param('kind', 'prelabel, seed, region or own (#315: the annotator\'s own '
               'read, on a case reopened for their revision).', paramType='path')
        .errorResponse('That case is not assigned to you.', 403)
        .errorResponse('This case has no asset of that kind.', 404)
    )
    def downloadAsset(self, case, kind):
        user = requireAnnotator(self.getCurrentUser())
        if kind not in protocol.ASSET_KINDS:
            refuse(protocol.ERR_NO_ASSET, f'Unknown asset kind {kind!r}.', status=400)
        assignment = self._requireOpenAssignment(case, user)
        if kind == protocol.ASSET_OWN:
            # Her own submitted read, on a case reopened for her revision (#315).
            fileId = assignment.get('startFileId') if isReopened(assignment) else None
        else:
            fileId = case.get({protocol.ASSET_PRELABEL: 'prelabelFileId',
                               protocol.ASSET_SEED: 'seedFileId',
                               protocol.ASSET_REGION: 'regionFileId'}[kind])
        if not fileId:
            refuse(protocol.ERR_NO_ASSET, f'This case has no {kind}.', status=404)
        file = File().load(fileId, force=True)
        if file is None:
            refuse(protocol.ERR_NO_ASSET,
                   f'The {kind} for this case is missing from storage.', status=404)
        if kind == protocol.ASSET_PRELABEL:
            Assignment14().recordPrelabelServed(assignment, case)
        return File().download(file)

    def _requireOpenAssignment(self, case, user):
        assignment = Assignment14().findOne({
            'caseId': case['_id'], 'userId': user['_id'],
            'state': {'$in': sorted(st.OPEN_STATES)},
        })
        if assignment is None:
            refuse('not_assigned_to_you',
                   'That case is not currently assigned to you.', status=403)
        return assignment

    # -------------------------------------------------------------- submit

    @access.user
    @autoDescribeRoute(
        Description('Submit a corrected segmentation for one of my cases.')
        .notes('Upload the label volume through Girder\'s chunked upload API into '
               'the SegQueue14 incoming folder first, then call this with its file '
               'id. Nothing about the segmentation is checked (#270): empty or '
               'overlapping classes are accepted, and voxel counts and geometry '
               'are recorded, not enforced.')
        .param('assignmentId', 'The assignment being submitted.', paramType='path')
        .param('fileId', 'Girder file id of the uploaded label volume.')
        .jsonParam('meta', 'SubmissionMeta as JSON.', requireObject=True)
        .jsonParam('geometry', 'Segmentation and source geometry as JSON.',
                   requireObject=True, required=False)
        .param('labelFormat', 'What the uploaded file is (segqueue14.labelfile): '
               '"class-stack-nrrd/1", every class whole (protocol 17, D39), or '
               '"labelmap", one label volume. Missing means "labelmap".',
               required=False)
        .param('clientProtocol', 'SegQueue14 protocol version the client speaks.',
               dataType='integer', required=False)
        .errorResponse('The upload is corrupt, or its labelFormat is unknown.', 400)
        .errorResponse('This assignment cannot be submitted in its current state.', 409)
        .errorResponse('The SegQueue14 module is out of date.', 426)
    )
    def submit(self, assignmentId, fileId, meta, geometry, labelFormat, clientProtocol):
        checkClientProtocol(clientProtocol)
        labelFormat = checkLabelFormat(labelFormat)
        user = requireAnnotator(self.getCurrentUser())
        assignment = loadOwnAssignment(Assignment14(), assignmentId, user)
        if isReopened(assignment):
            # #315: never a seed-started read in place of her own from an old module.
            checkReopenReader(clientProtocol)

        if not st.can(assignment['state'], st.SUBMIT):
            refuse(protocol.ERR_BAD_STATE,
                   f"This case is {assignment['state']}, so it cannot be submitted. "
                   'If you already submitted it, you are done.',
                   status=409, state=assignment['state'])

        # Nothing about the segmentation is checked (#270, project lead
        # 2026-11-02): an empty LAD, LCx or RCA (D13) or overlapping classes
        # (D26) are accepted. The voxel counts and geometry are recorded only.
        submissionMeta = protocol.SubmissionMeta.from_dict(meta)
        file = File().load(fileId, level=AccessType.WRITE, user=user)
        if file is None:
            refuse('no_such_file', 'That upload could not be found.', status=404)
        self._verifyUpload(file, submissionMeta)
        # Recorded as the stored bytes say, not as declared (an unknown declared
        # name was already refused above): the format, and which classes the read
        # has -- the four, or the four and the extended ones (D44).
        labelFormat, classes = storedLabelInfo(file)

        item = Item().load(file['itemId'], force=True)
        if item is not None:
            Item().move(item, submissionsFolder(user))

        policy = getPolicy()
        kind = assignment.get('kind', sqplan.KIND_NORMAL)
        if kind == sqplan.KIND_BENCHMARK:
            # The annotator benchmark (D43) always goes to a reviewer, with its
            # Dice against ImageCAS-X; no roll decides it.
            roll, needsReview = None, True
        else:
            record = Assignment14().recordFor(user['_id'])
            roll = random.random()
            # The sampled review rate (training gate, probation, trusted rate)
            # applies as in the live project. The automatic scores add to it in
            # the worker.
            needsReview = pol.review_needed(record, policy, roll, kind=pol.NORMAL)

        submission = Submission14().createSubmission(
            assignment, submissionMeta, file['_id'], needsReview=needsReview,
            geometry=geometry, labelFormat=labelFormat, classes=classes)
        assignment = Assignment14().transition(
            assignment, st.SUBMIT,
            submissionId=submission['_id'], needsReview=needsReview, reviewRoll=roll)

        if not needsReview and kind == sqplan.KIND_NORMAL:
            assignment = Assignment14().transition(assignment, st.APPROVE)
            Case14().completeSlot(assignment['caseId'])

        return {
            'assignment': assignmentInfo(assignment).to_dict(),
            'submissionId': str(submission['_id']),
            'warnings': [],
            'awaitingReview': needsReview,
        }

    def _verifyUpload(self, file, meta):
        if meta.size_bytes and int(file['size']) != int(meta.size_bytes):
            refuse(protocol.ERR_CHECKSUM,
                   f"The upload is {file['size']} bytes but you declared "
                   f'{meta.size_bytes}. The transfer was incomplete -- please submit '
                   'again.', status=400)
        actual = hashStoredFile(file)
        if not matches(meta.checksum, actual):
            refuse(protocol.ERR_CHECKSUM,
                   'The uploaded file does not match its checksum. Nothing has been '
                   'recorded -- please submit again.',
                   status=400, expected=meta.checksum, actual=actual)
        meta.checksum = actual

    # ------------------------------------------------------------- release

    @access.user
    @autoDescribeRoute(
        Description('Give a SegQueue14 case back to the pool.')
        .param('assignmentId', 'The assignment to release.', paramType='path')
        .param('reason', 'Why, for the record.', required=False, default='')
    )
    def release(self, assignmentId, reason):
        user = requireAnnotator(self.getCurrentUser())
        assignment = loadOwnAssignment(Assignment14(), assignmentId, user)
        if not st.can(assignment['state'], st.RELEASE):
            refuse(protocol.ERR_BAD_STATE,
                   f"A case in state {assignment['state']} cannot be released.",
                   status=409, state=assignment['state'])
        assignment = Assignment14().transition(
            assignment, st.RELEASE, releaseReason=reason or 'released by annotator')
        Case14().releaseSlot(assignment['caseId'])
        return {'released': True, 'caseId': str(assignment['caseId'])}

    @access.user
    @autoDescribeRoute(
        Description('Report that I am still working on this case.')
        .param('assignmentId', 'The assignment being worked on.', paramType='path')
    )
    def heartbeat(self, assignmentId):
        user = requireAnnotator(self.getCurrentUser())
        assignment = loadOwnAssignment(Assignment14(), assignmentId, user)
        Assignment14().heartbeat(assignment)
        return {'ok': True}

    # --------------------------------------------------------------- notes

    @access.user
    @autoDescribeRoute(
        Description('Read the note thread on a SegQueue14 case.')
        .modelParam('caseId', 'The case.', model=Case14, force=True, destName='case')
        .param('limit', 'How many of the newest notes to return.',
               dataType='integer', required=False)
    )
    def listNotes(self, case, limit):
        user = requireAnnotator(self.getCurrentUser())
        requireCaseInvolvement(Assignment14(), case['_id'], user)
        return [noteInfo(n).to_dict() for n in Note14().forCase(case['_id'], limit)]

    @access.user
    @autoDescribeRoute(
        Description('Add a note to a SegQueue14 case.')
        .modelParam('caseId', 'The case.', model=Case14, force=True, destName='case')
        .param('text', 'The note.')
    )
    def addNote(self, case, text):
        user = requireAnnotator(self.getCurrentUser())
        requireCaseInvolvement(Assignment14(), case['_id'], user)
        cleaned = protocol.clean_note(text)
        if not cleaned:
            refuse('empty_note', 'A note cannot be empty.', status=400)
        return noteInfo(Note14().createNote(case['_id'], user, cleaned)).to_dict()


def noteInfo(note):
    created = note.get('created')
    return protocol.CaseNote(
        id=str(note['_id']), case_id=str(note.get('caseId', '')),
        author=note.get('author', '') or '', author_id=str(note.get('authorId') or ''),
        text=note.get('text', '') or '',
        created_at=created.timestamp() if created else None,
        system=bool(note.get('system', False)),
    )
