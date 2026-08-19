"""Reviewer endpoints: triage the queue, look at one, decide.

Claiming is explicit and separate from deciding. With two or three reviewers in
a lab that is not ceremony -- it is the difference between two people opening the
same submission in Slicer and spending twenty minutes each on it, and them
working through the queue in parallel.
"""

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.models.file import File
from girder.models.user import User
from segqueue import policy as pol
from segqueue import protocol
from segqueue import states as st

from ..models import Assignment, Case, Review, Submission
from ..models.review import APPROVE, REJECT
from ..settings import getPolicy
from ..utils import fileForCase, refuse, requireReviewer


class ReviewResource(Resource):
    """Registered onto the queue resource so the paths read ``/segqueue/review/...``.

    A separate class for readability, but not a separate mount point: Girder
    routes by resource, and two resources cannot share the ``segqueue`` prefix.
    ``attachTo`` hangs these handlers off the queue resource instead, which also
    keeps them under one heading in the generated API docs.
    """

    def attachTo(self, parent):
        parent.route('GET', ('review', 'queue'), self.reviewQueue)
        parent.route('GET', ('review', ':submissionId'), self.getSubmission)
        parent.route('GET', ('review', ':submissionId', 'download'),
                     self.downloadSubmission)
        parent.route('GET', ('review', ':submissionId', 'volume'), self.downloadVolume)
        parent.route('POST', ('review', ':submissionId', 'claim'), self.claim)
        parent.route('POST', ('review', ':submissionId', 'release'), self.releaseClaim)
        parent.route('POST', ('review', ':submissionId', 'verdict'), self.verdict)
        return self

    # --------------------------------------------------------------- queue

    @access.user
    @autoDescribeRoute(
        Description('Submissions waiting for a human verdict, oldest first.')
        .pagingParams(defaultSort='submittedAt', defaultSortDir=1)
    )
    def reviewQueue(self, limit, offset, sort):
        requireReviewer(self.getCurrentUser())
        rows = []
        for assignment in Assignment().pendingReview(limit=limit, offset=offset):
            submission = Submission().latestForAssignment(assignment['_id'])
            if submission is None:
                continue
            rows.append(self._row(assignment, submission))
        return rows

    @access.user
    @autoDescribeRoute(
        Description('Everything a reviewer needs about one submission.')
        .param('submissionId', 'The submission to inspect.', paramType='path')
    )
    def getSubmission(self, submissionId):
        requireReviewer(self.getCurrentUser())
        submission = self._loadSubmission(submissionId)
        assignment = Assignment().load(submission['assignmentId'], force=True)
        row = self._row(assignment, submission)
        row['history'] = [
            {
                'verdict': r['verdict'],
                'comment': r['comment'],
                'reviewerId': str(r['reviewerId']),
                'created': r['created'].isoformat() if r.get('created') else None,
            }
            for r in Review().forSubmission(submission['_id'])
        ]
        return row

    # ------------------------------------------------------------ downloads

    @access.user
    @autoDescribeRoute(
        Description('Download the submitted segmentation.')
        .param('submissionId', 'The submission.', paramType='path')
    )
    def downloadSubmission(self, submissionId):
        requireReviewer(self.getCurrentUser())
        submission = self._loadSubmission(submissionId)
        file = File().load(submission['fileId'], force=True)
        if file is None:
            refuse('submission_file_missing',
                   'The submitted file is missing from storage.', status=500)
        return File().download(file)

    @access.user
    @autoDescribeRoute(
        Description('Download the source volume behind a submission.')
        .notes('A reviewer needs the image as well as the labels; this is the '
               'only route that hands out a volume without an assignment.')
        .param('submissionId', 'The submission.', paramType='path')
    )
    def downloadVolume(self, submissionId):
        requireReviewer(self.getCurrentUser())
        submission = self._loadSubmission(submissionId)
        case = Case().load(submission['caseId'], force=True)
        if case is None:
            refuse('no_such_case', 'That case no longer exists.', status=404)
        return File().download(fileForCase(case))

    # ---------------------------------------------------------- claim/free

    @access.user
    @autoDescribeRoute(
        Description('Claim a submission so no other reviewer duplicates the work.')
        .param('submissionId', 'The submission to claim.', paramType='path')
        .errorResponse('Someone else already claimed it.', 409)
    )
    def claim(self, submissionId):
        user = requireReviewer(self.getCurrentUser())
        submission = self._loadSubmission(submissionId)
        assignment = Assignment().load(submission['assignmentId'], force=True)
        try:
            assignment = Assignment().transition(
                assignment, st.CLAIM_REVIEW, reviewerId=user['_id'])
        except st.TransitionError:
            # The guarded update lost: another reviewer got there first, or the
            # submission was already decided.
            refuse(protocol.ERR_BAD_STATE,
                   'Another reviewer is already looking at this one.',
                   status=409, state=assignment['state'])
        return self._row(assignment, submission)

    @access.user
    @autoDescribeRoute(
        Description('Put a claimed submission back in the queue undecided.')
        .param('submissionId', 'The submission.', paramType='path')
    )
    def releaseClaim(self, submissionId):
        requireReviewer(self.getCurrentUser())
        submission = self._loadSubmission(submissionId)
        assignment = Assignment().load(submission['assignmentId'], force=True)
        try:
            assignment = Assignment().transition(assignment, st.ABANDON_REVIEW)
        except st.TransitionError:
            refuse(protocol.ERR_BAD_STATE,
                   f"That submission is {assignment['state']}, not under review.",
                   status=409, state=assignment['state'])
        return {'released': True}

    # ------------------------------------------------------------- verdict

    @access.user
    @autoDescribeRoute(
        Description('Approve or reject a submission.')
        .notes('A rejection returns the case to the same annotator with the '
               'comment attached. That is deliberate: reassigning it silently '
               'to someone else costs the same effort and teaches nobody.')
        .param('submissionId', 'The submission being decided.', paramType='path')
        .param('verdict', 'approve or reject.', enum=[APPROVE, REJECT])
        .param('comment', 'What to fix. Required when rejecting.',
               required=False, default='')
        .jsonParam('rubric', 'Optional per-criterion scores.', required=False,
                   requireObject=True)
        .param('secondsSpent', 'How long the review took.', dataType='number',
               required=False)
        .errorResponse('A rejection needs a comment.', 400)
        .errorResponse('That submission has already been decided.', 409)
    )
    def verdict(self, submissionId, verdict, comment, rubric, secondsSpent):
        user = requireReviewer(self.getCurrentUser())
        submission = self._loadSubmission(submissionId)
        assignment = Assignment().load(submission['assignmentId'], force=True)

        if verdict == REJECT and not (comment or '').strip():
            refuse('comment_required',
                   'Rejections must say what to fix -- the annotator gets this '
                   'text and nothing else.', status=400)

        event = st.APPROVE if verdict == APPROVE else st.REJECT
        if not st.can(assignment['state'], event):
            refuse(protocol.ERR_BAD_STATE,
                   f"This submission is {assignment['state']} and cannot be "
                   f'{verdict}d.', status=409, state=assignment['state'])

        Review().createReview(submission, user, verdict, comment=comment,
                              rubric=rubric, secondsSpent=secondsSpent)

        extra = {'reviewerComment': (comment or '').strip(), 'reviewerId': user['_id']}
        try:
            assignment = Assignment().transition(assignment, event, **extra)
        except st.TransitionError:
            refuse(protocol.ERR_BAD_STATE,
                   'Another reviewer decided this one first.',
                   status=409, state=assignment['state'])

        if verdict == APPROVE:
            # The replica slot converts from active to approved, which is what
            # moves the project's completion number.
            Case().completeSlot(assignment['caseId'])

        return {
            'verdict': verdict,
            'state': assignment['state'],
            'caseId': str(assignment['caseId']),
        }

    # -------------------------------------------------------------- shared

    def _loadSubmission(self, submissionId):
        submission = Submission().load(submissionId, force=True)
        if submission is None:
            refuse('no_such_submission', 'No such submission.', status=404)
        return submission

    def _row(self, assignment, submission):
        """One review-queue entry: enough to triage without opening Slicer."""
        case = Case().load(submission['caseId'], force=True) or {}
        annotator = User().load(submission['userId'], force=True) or {}
        policy = getPolicy()
        kind = submission.get('kind', pol.NORMAL)

        return {
            'submissionId': str(submission['_id']),
            'assignmentId': str(assignment['_id']),
            'caseId': str(submission['caseId']),
            'caseName': case.get('name', ''),
            'state': assignment['state'],
            'attempt': submission.get('attempt', 1),
            'annotator': {
                'id': str(annotator.get('_id', '')),
                'login': annotator.get('login', ''),
                'name': f"{annotator.get('firstName', '')} "
                        f"{annotator.get('lastName', '')}".strip(),
            },
            'annotationSeconds': submission.get('annotationSeconds'),
            'voxelCounts': submission.get('voxelCounts', {}),
            'annotatorNote': submission.get('annotatorNote', ''),
            'warnings': submission.get('warnings', []),
            'submittedAt': (assignment.get('submittedAt').isoformat()
                            if assignment.get('submittedAt') else None),
            # Reviewers do see the flavour: knowing a case is a gold seed is
            # exactly what lets them read the automatic score as evidence.
            'kind': kind,
            'autoScore': submission.get('autoScore'),
            'scored': submission.get('scored', False),
            'flagged': self._flagged(submission, policy),
        }

    def _flagged(self, submission, policy):
        """Why this submission deserves attention, in plain words."""
        reasons = []
        score = submission.get('autoScore') or {}
        mean = score.get('mean_dice')
        kind = submission.get('kind', pol.NORMAL)
        if mean is not None:
            threshold = (policy.gold_dice_flag if kind == pol.GOLD
                         else policy.duplicate_dice_flag)
            if mean < threshold:
                label = 'the reference' if kind == pol.GOLD else 'the other annotator'
                reasons.append(f'mean Dice {mean:.2f} against {label}')
        seconds = submission.get('annotationSeconds') or 0
        if 0 < seconds < 60:
            reasons.append(f'only {seconds:.0f} s spent on the case')
        reasons.extend(submission.get('warnings', []))
        return reasons
