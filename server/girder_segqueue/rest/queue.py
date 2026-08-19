"""Annotator endpoints: get a case, fetch it, send it back, give it up.

The whole loop an undergraduate performs is seven routes wide. Everything
interesting happens in ``next`` -- picking a flavour, winning the race for a
case, and writing the lease -- and in ``submit``, which is the only place the
server accepts data and therefore the only place worth being paranoid.
"""

import random

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import AccessType
from girder.models.file import File
from girder.models.item import Item
from segqueue import policy as pol
from segqueue import protocol
from segqueue import states as st
from segqueue.checksum import matches
from segqueue.segcheck import Geometry, blocking, check_submission, summarise

from ..constants import MAX_ASSIGN_ATTEMPTS
from ..models import Assignment, Case, Submission
from ..settings import getPolicy, getProject
from ..utils import (
    checkClientProtocol,
    fileForCase,
    hashStoredFile,
    incomingFolder,
    loadOwnAssignment,
    refuse,
    requireAnnotator,
    submissionsFolder,
)


class QueueResource(Resource):
    def __init__(self):
        super().__init__()
        self.resourceName = protocol.API_PREFIX

        self.route('GET', ('project',), self.getProject)
        self.route('GET', ('mine',), self.listMine)
        self.route('POST', ('next',), self.nextCase)
        self.route('GET', ('case', ':caseId', 'download'), self.downloadCase)
        self.route('GET', ('case', ':caseId', 'asset', ':kind'), self.downloadAsset)
        self.route('POST', ('assignment', ':assignmentId', 'submit'), self.submit)
        self.route('POST', ('assignment', ':assignmentId', 'release'), self.release)
        self.route('POST', ('assignment', ':assignmentId', 'heartbeat'), self.heartbeat)

    # ------------------------------------------------------------- project

    @access.user
    @autoDescribeRoute(
        Description('Fetch the labelling protocol and this user\'s limits.')
        .notes('Called once at login. The segment list returned here is what the '
               'extension creates in the scene, so changing it server-side '
               'changes what every annotator draws without any reinstall.')
    )
    def getProject(self):
        user = requireAnnotator(self.getCurrentUser())
        quota = user.get('segqueueQuota')
        remaining = None
        if quota is not None:
            done = Assignment().collection.count_documents({
                'userId': user['_id'], 'state': st.APPROVED})
            remaining = max(0, int(quota) - done)
        return getProject(
            quotaRemaining=remaining,
            uploadFolderId=str(incomingFolder(user)['_id']),
        ).to_dict()

    # ---------------------------------------------------------------- mine

    @access.user
    @autoDescribeRoute(
        Description('List the cases currently assigned to me.')
        .param('includeFinished', 'Also return approved and released work.',
               dataType='boolean', required=False, default=False)
    )
    def listMine(self, includeFinished):
        user = requireAnnotator(self.getCurrentUser())
        states = None if includeFinished else sorted(st.OPEN_STATES)
        return [
            self._assignmentInfo(a).to_dict()
            for a in Assignment().forUser(user['_id'], states)
        ]

    # ---------------------------------------------------------------- next

    @access.user
    @autoDescribeRoute(
        Description('Assign me the next case and return it.')
        .notes('Atomic: concurrent callers receive different cases. Returns 404 '
               'with segqueueError=queue_empty when nothing is left, and 409 '
               'with at_limit when the caller already holds their maximum.')
        .param('clientProtocol', 'Wire protocol version the client speaks.',
               dataType='integer', required=False)
        .errorResponse('You already hold the maximum number of cases.', 409)
        .errorResponse('Nothing left to assign.', 404)
    )
    def nextCase(self, clientProtocol):
        checkClientProtocol(clientProtocol)
        user = requireAnnotator(self.getCurrentUser())
        policy = getPolicy()

        openCount = Assignment().countOpenForUser(user['_id'])
        remaining = self._quotaRemaining(user)
        if not pol.can_take_more(openCount, policy, remaining):
            if remaining is not None and remaining <= 0:
                refuse(protocol.ERR_QUOTA,
                       'You have finished your assigned quota. Thank you!',
                       status=403)
            refuse(protocol.ERR_AT_LIMIT,
                   'Finish or release the case you already have before asking '
                   'for another.',
                   status=409, maxConcurrent=policy.max_concurrent)

        assignment = self._claimNext(user, policy)
        if assignment is None:
            refuse(protocol.ERR_QUEUE_EMPTY,
                   'No cases are available for you right now. This usually means '
                   'the pool is finished -- check with the project admin before '
                   'assuming it is a bug.',
                   status=404)
        return self._assignmentInfo(assignment).to_dict()

    def _claimNext(self, user, policy):
        """Pick a flavour, then win a case of it. ``None`` if the pool is dry.

        The retry loop exists for lost races, not for errors: every failed claim
        means another annotator took that exact case microseconds earlier. If
        the preferred flavour runs out mid-flight we fall back to an ordinary
        case rather than telling a student the queue is empty when it is not.
        """
        userId = user['_id']
        record = Assignment().recordFor(userId)
        kind = pol.injection_kind(
            record, policy, random.random(),
            gold_available=Case().hasGoldAvailable(userId),
            duplicate_available=Case().hasDuplicateAvailable(userId),
        )

        for _ in range(MAX_ASSIGN_ATTEMPTS):
            case = self._claimOne(userId, kind)
            if case is not None:
                return Assignment().createAssignment(case, user, kind=kind, policy=policy)
            if kind != pol.NORMAL:
                kind = pol.NORMAL
        return None

    def _claimOne(self, userId, kind):
        if kind == pol.DUPLICATE:
            for case in Case().duplicateCandidates(userId):
                claimed = Case().claimAsDuplicate(case['_id'], userId)
                if claimed is not None:
                    return claimed
            return None

        # Gold cases are never handed out as ordinary work: they are a finite
        # resource, and one spent unscored is one wasted.
        for case in Case().candidates(userId, wantGold=(kind == pol.GOLD)):
            claimed = Case().claim(case['_id'], userId)
            if claimed is not None:
                return claimed
        return None

    # ------------------------------------------------------------ download

    @access.user
    @autoDescribeRoute(
        Description('Download the volume for a case assigned to me.')
        .modelParam('caseId', 'The case to download.', model=Case, force=True,
                    destName='case')
        .notes('Authorised by the assignment, not by an ACL on the case: the '
               'question is "is this yours right now", which changes daily.')
        .errorResponse('That case is not assigned to you.', 403)
    )
    def downloadCase(self, case):
        user = requireAnnotator(self.getCurrentUser())
        assignment = self._requireOpenAssignment(case, user)

        # Picking a rejected case back up *is* starting the rework, so it
        # happens here rather than needing the client to call a separate
        # endpoint first. The transition also renews the lease, which matters:
        # a case rejected on day six of a seven-day lease would otherwise expire
        # before the annotator could act on the comment.
        if assignment['state'] == st.REJECTED:
            assignment = Assignment().transition(
                assignment, st.REWORK, policy=getPolicy())

        # First byte out is what "downloaded" means. Marking it before the
        # stream would call a failed transfer a success; marking it after would
        # require the client to confirm, which a crashed client never does.
        if assignment['state'] == st.ASSIGNED:
            Assignment().transition(assignment, st.DOWNLOAD)

        return File().download(fileForCase(case))

    # --------------------------------------------------------- case assets

    @access.user
    @autoDescribeRoute(
        Description('Download a helper mask that ships with a case.')
        .notes('``region`` is the heart mask from the source dataset; ``seed`` '
               'is a pre-existing binary coronary lumen mask. Neither is a '
               'label the annotator submits -- they exist so the extension can '
               'frame the view, confine editing, and let the annotator split an '
               'existing tree instead of drawing one. Most cases have neither, '
               'and a 404 here is a normal answer.')
        .modelParam('caseId', 'The case.', model=Case, force=True, destName='case')
        .param('kind', 'region or seed.', paramType='path')
        .errorResponse('That case is not assigned to you.', 403)
        .errorResponse('This case has no asset of that kind.', 404)
    )
    def downloadAsset(self, case, kind):
        user = requireAnnotator(self.getCurrentUser())
        if kind not in protocol.ASSET_KINDS:
            refuse(protocol.ERR_NO_ASSET,
                   f'Unknown asset kind {kind!r}.', status=400)

        # Same authorisation as the volume itself, deliberately: these masks are
        # derived from the patient's scan, so "you may see the CT" and "you may
        # see its heart mask" have to be one decision, not two.
        self._requireOpenAssignment(case, user)

        fileId = case.get('regionFileId' if kind == protocol.ASSET_REGION
                          else 'seedFileId')
        if not fileId:
            refuse(protocol.ERR_NO_ASSET,
                   f'This case has no {kind} mask.', status=404)
        file = File().load(fileId, force=True)
        if file is None:
            refuse(protocol.ERR_NO_ASSET,
                   f'The {kind} mask for this case is missing from storage.',
                   status=404)
        return File().download(file)

    def _requireOpenAssignment(self, case, user):
        assignment = Assignment().findOne({
            'caseId': case['_id'],
            'userId': user['_id'],
            'state': {'$in': sorted(st.OPEN_STATES)},
        })
        if assignment is None:
            refuse('not_assigned_to_you',
                   'That case is not currently assigned to you.', status=403)
        return assignment

    # -------------------------------------------------------------- submit

    @access.user
    @autoDescribeRoute(
        Description('Submit a finished segmentation for one of my assignments.')
        .notes('Upload the .seg.nrrd through Girder\'s own chunked upload API '
               'first, then call this with the resulting fileId. Girder\'s '
               'uploader is resumable, which is what makes a dropped home '
               'connection recoverable instead of fatal.')
        .param('assignmentId', 'The assignment being submitted.', paramType='path')
        .param('fileId', 'Girder file id of the uploaded .seg.nrrd.')
        .jsonParam('meta', 'SubmissionMeta as JSON.', requireObject=True)
        .jsonParam('geometry', 'Segmentation and source geometry as JSON.',
                   requireObject=True, required=False)
        .param('clientProtocol', 'Wire protocol version the client speaks.',
               dataType='integer', required=False)
        .errorResponse('The upload did not match its checksum.', 400)
        .errorResponse('This assignment cannot be submitted in its current state.', 409)
    )
    def submit(self, assignmentId, fileId, meta, geometry, clientProtocol):
        checkClientProtocol(clientProtocol)
        user = requireAnnotator(self.getCurrentUser())
        assignment = loadOwnAssignment(Assignment(), assignmentId, user)

        if not st.can(assignment['state'], st.SUBMIT):
            refuse(protocol.ERR_BAD_STATE,
                   f"This case is {assignment['state']}, so it cannot be "
                   'submitted. If you already submitted it, you are done.',
                   status=409, state=assignment['state'])

        submissionMeta = protocol.SubmissionMeta.from_dict(meta)
        file = File().load(fileId, level=AccessType.WRITE, user=user)
        if file is None:
            refuse('no_such_file', 'That upload could not be found.', status=404)

        self._verifyUpload(file, submissionMeta)
        problems = self._recheck(assignment, submissionMeta, geometry or {})
        if blocking(problems):
            refuse('failed_validation',
                   'This segmentation did not pass the submission checks:\n'
                   + summarise(blocking(problems)),
                   status=400,
                   problems=[p.code for p in problems])

        # Move the accepted upload out of `incoming` so that scratch uploads and
        # real submissions never share a folder. Girder files hang off items, not
        # folders, so it is the item that moves.
        item = Item().load(file['itemId'], force=True)
        if item is not None:
            Item().move(item, submissionsFolder(user))

        policy = getPolicy()
        record = Assignment().recordFor(user['_id'])
        roll = random.random()
        needsReview = pol.review_needed(
            record, policy, roll, kind=assignment.get('kind', pol.NORMAL),
            auto_score=None,
        )

        submission = Submission().createSubmission(
            assignment, submissionMeta, file['_id'],
            warnings=[p.code for p in problems], needsReview=needsReview,
        )
        assignment = Assignment().transition(
            assignment, st.SUBMIT,
            submissionId=submission['_id'], needsReview=needsReview, reviewRoll=roll,
        )

        # Nothing to review and nothing to score: finish it here. A gold or
        # duplicate submission waits for the worker, which may still pull it
        # back for a human on a bad score.
        if not needsReview and assignment.get('kind', pol.NORMAL) == pol.NORMAL:
            assignment = Assignment().transition(assignment, st.APPROVE)
            Case().completeSlot(assignment['caseId'])

        return {
            'assignment': self._assignmentInfo(assignment).to_dict(),
            'submissionId': str(submission['_id']),
            'warnings': [p.message for p in problems],
            'awaitingReview': needsReview,
        }

    def _verifyUpload(self, file, meta):
        """Refuse anything whose received bytes disagree with the client."""
        if meta.size_bytes and int(file['size']) != int(meta.size_bytes):
            refuse(protocol.ERR_CHECKSUM,
                   f"The upload is {file['size']} bytes but you declared "
                   f'{meta.size_bytes}. The transfer was incomplete -- please '
                   'submit again.',
                   status=400)
        actual = hashStoredFile(file)
        if not matches(meta.checksum, actual):
            refuse(protocol.ERR_CHECKSUM,
                   'The uploaded file does not match its checksum, so it was '
                   'corrupted in transit. Nothing has been recorded -- please '
                   'submit again.',
                   status=400, expected=meta.checksum, actual=actual)
        meta.checksum = actual

    def _recheck(self, assignment, meta, geometry):
        """Run the client-side checks again on the server.

        The client already ran these and refused to send if they failed, so in
        normal operation this finds nothing. It exists because "the client
        already checked" is not a security property, and because a client one
        version behind may not have had the check at all.
        """
        project = getProject()
        return check_submission(
            voxel_counts=meta.voxel_counts,
            segments=project.segments,
            source_geometry=Geometry.from_dict(geometry.get('source')),
            segmentation_geometry=Geometry.from_dict(geometry.get('segmentation')),
            annotation_seconds=meta.annotation_seconds or None,
        )

    # ------------------------------------------------------------- release

    @access.user
    @autoDescribeRoute(
        Description('Give a case back to the pool.')
        .param('assignmentId', 'The assignment to release.', paramType='path')
        .param('reason', 'Why, for the record.', required=False, default='')
    )
    def release(self, assignmentId, reason):
        user = requireAnnotator(self.getCurrentUser())
        assignment = loadOwnAssignment(Assignment(), assignmentId, user)
        if not st.can(assignment['state'], st.RELEASE):
            refuse(protocol.ERR_BAD_STATE,
                   f"A case in state {assignment['state']} cannot be released.",
                   status=409, state=assignment['state'])

        assignment = Assignment().transition(
            assignment, st.RELEASE, releaseReason=reason or 'released by annotator')
        Case().releaseSlot(assignment['caseId'])
        return {'released': True, 'caseId': str(assignment['caseId'])}

    # ----------------------------------------------------------- heartbeat

    @access.user
    @autoDescribeRoute(
        Description('Report that I am still working on this case.')
        .notes('Distinguishes a slow annotator from one who has left the '
               'course. Without it the only signal is the lease, which is a '
               'week long by design.')
        .param('assignmentId', 'The assignment being worked on.', paramType='path')
    )
    def heartbeat(self, assignmentId):
        user = requireAnnotator(self.getCurrentUser())
        assignment = loadOwnAssignment(Assignment(), assignmentId, user)
        Assignment().heartbeat(assignment)
        return {'ok': True}

    # -------------------------------------------------------------- shared

    def _quotaRemaining(self, user):
        quota = user.get('segqueueQuota')
        if quota is None:
            return None
        done = Assignment().collection.count_documents({
            'userId': user['_id'], 'state': st.APPROVED})
        return max(0, int(quota) - done)

    def _assignmentInfo(self, assignment):
        """Build the annotator's view. Never includes ``kind`` -- blind means blind."""
        case = Case().load(assignment['caseId'], force=True) or {}
        deadline = assignment.get('deadline')
        assignedAt = assignment.get('assignedAt')
        return protocol.AssignmentInfo(
            assignment_id=str(assignment['_id']),
            case_id=str(assignment['caseId']),
            case_name=case.get('name', ''),
            state=assignment['state'],
            attempt=assignment.get('attempt', 1),
            size_bytes=case.get('sizeBytes', 0),
            checksum=case.get('checksum', ''),
            assigned_at=assignedAt.timestamp() if assignedAt else None,
            deadline=deadline.timestamp() if deadline else None,
            reviewer_comment=assignment.get('reviewerComment', ''),
            has_region=bool(case.get('regionFileId')),
            has_seed=bool(case.get('seedFileId')),
        )
