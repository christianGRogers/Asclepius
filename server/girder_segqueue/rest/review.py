"""Reviewer endpoints: triage the queue, look at one, decide.

Claiming is explicit and separate from deciding. With two or three reviewers in
a lab that is not ceremony -- it is the difference between two people opening the
same submission in Slicer and spending twenty minutes each on it, and them
working through the queue in parallel.
"""

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import AccessType
from girder.models.file import File
from girder.models.group import Group
from girder.models.item import Item
from girder.models.user import User
from segqueue import policy as pol
from segqueue import protocol
from segqueue import states as st
from segqueue.checksum import matches

from ..constants import ANNOTATOR_GROUP
from ..models import Assignment, Case, Note, Review, Submission
from ..models import submission as sub
from ..models.review import APPROVE
from ..settings import getPolicy
from ..utils import (
    fileForCase,
    hashStoredFile,
    isAnnotator,
    refuse,
    requireReviewer,
    submissionsFolder,
)


def _iso(value):
    return value.isoformat() if value is not None else None


class ReviewResource(Resource):
    """Registered onto the queue resource so the paths read ``/segqueue/review/...``.

    A separate class for readability, but not a separate mount point: Girder
    routes by resource, and two resources cannot share the ``segqueue`` prefix.
    ``attachTo`` hangs these handlers off the queue resource instead, which also
    keeps them under one heading in the generated API docs.
    """

    def attachTo(self, parent):
        parent.route('GET', ('review', 'queue'), self.reviewQueue)
        parent.route('GET', ('review', 'cases'), self.listCases)
        parent.route('GET', ('review', 'annotators'), self.listAnnotators)
        parent.route('POST', ('review', 'case', ':caseId', 'assign'),
                     self.assignCase)
        parent.route('GET', ('review', 'case', ':caseId', 'volume'),
                     self.downloadCaseVolume)
        parent.route('GET', ('review', 'case', ':caseId', 'asset', ':kind'),
                     self.downloadCaseAsset)
        parent.route('GET', ('review', 'case', ':caseId', 'submissions'),
                     self.caseSubmissions)
        parent.route('GET', ('review', ':submissionId'), self.getSubmission)
        parent.route('GET', ('review', ':submissionId', 'download'),
                     self.downloadSubmission)
        parent.route('GET', ('review', ':submissionId', 'volume'), self.downloadVolume)
        parent.route('POST', ('review', ':submissionId', 'claim'), self.claim)
        parent.route('POST', ('review', ':submissionId', 'release'), self.releaseClaim)
        parent.route('POST', ('review', ':submissionId', 'verdict'), self.verdict)
        parent.route('POST', ('review', ':submissionId', 'revise'), self.revise)
        parent.route('POST', ('review', ':submissionId', 'pool'), self.returnToPool)
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

    # ------------------------------------------------------------- approve

    @access.user
    @autoDescribeRoute(
        Description('Approve a submission.')
        .notes('Approve is the only verdict. Rejecting a case back to the same '
               'annotator was retired in 0.9.0 -- a reviewer who can open the '
               'submission and correct it in Slicer has a faster path to a '
               'correct label than a round trip, and where the work genuinely '
               'needs redoing, `pool` hands it to somebody else. Approval is '
               'also the only state the training export selects.')
        .param('submissionId', 'The submission being approved.', paramType='path')
        # Deliberately no `enum`. autoDescribeRoute validates an enum itself
        # and answers "invalid value for parameter verdict", which is exactly the
        # message an old client sending `reject` must not get: it reads like a
        # malformed request rather than a retired verb. The handler checks the
        # value so that it can say where the verb went.
        .param('verdict', 'approve. Anything else is refused by name.',
               required=False, default=APPROVE)
        .param('comment', 'Optional note for the case thread.',
               required=False, default='')
        .jsonParam('rubric', 'Optional per-criterion scores.', required=False,
                   requireObject=True)
        .param('secondsSpent', 'How long the review took.', dataType='number',
               required=False)
        .errorResponse('That submission has already been decided.', 409)
    )
    def verdict(self, submissionId, verdict, comment, rubric, secondsSpent):
        user = requireReviewer(self.getCurrentUser())
        submission = self._loadSubmission(submissionId)
        assignment = Assignment().load(submission['assignmentId'], force=True)

        if verdict != APPROVE:
            # An old client asking to reject. Say where the verb went rather
            # than 400 with a schema complaint.
            refuse('verdict_retired',
                   f'{verdict!r} is no longer a verdict. Approve the '
                   'submission, correct it yourself and approve that, or send '
                   'the case back to the pool for another annotator.',
                   status=400)

        if not st.can(assignment['state'], st.APPROVE):
            refuse(protocol.ERR_BAD_STATE,
                   f"This submission is {assignment['state']} and cannot be "
                   'approved.', status=409, state=assignment['state'])

        Review().createReview(submission, user, APPROVE, comment=comment,
                              rubric=rubric, secondsSpent=secondsSpent)

        extra = {'reviewerComment': (comment or '').strip(), 'reviewerId': user['_id']}
        try:
            assignment = Assignment().transition(assignment, st.APPROVE, **extra)
        except st.TransitionError:
            refuse(protocol.ERR_BAD_STATE,
                   'Another reviewer decided this one first.',
                   status=409, state=assignment['state'])

        # The verdict goes onto the case thread as well as onto the assignment,
        # so the next person to open this case sees who accepted it and why.
        # systemNote never raises: losing a line of the thread must not cost a
        # reviewer their verdict.
        Note().systemNote(
            assignment['caseId'],
            '{} approved attempt {}{}'.format(
                user.get('login') or 'A reviewer',
                assignment.get('attempt', 1),
                ': ' + (comment or '').strip() if (comment or '').strip() else '.'))

        # The replica slot converts from active to approved, which is what moves
        # the project's completion number.
        Case().completeSlot(assignment['caseId'])

        return {
            'verdict': APPROVE,
            'state': assignment['state'],
            'caseId': str(assignment['caseId']),
        }

    # --------------------------------------------------------- the viewer

    @access.user
    @autoDescribeRoute(
        Description('Every case and what has happened to it.')
        .notes('The submission viewer. Unlike the review queue this answers '
               '"where is case s0042?" rather than "what is waiting for me?", so '
               'it lists cases nobody has been assigned and cases already '
               'approved alongside the ones needing attention.')
        .param('state', 'Only cases with an assignment in this state.',
               required=False, enum=list(st.ALL_STATES))
        .param('unassigned', 'Only cases nobody is working on or has finished.',
               dataType='boolean', required=False, default=False)
        .pagingParams(defaultSort='name', defaultSortDir=1)
    )
    def listCases(self, state, unassigned, limit, offset, sort):
        requireReviewer(self.getCurrentUser())

        # Filtered in the query, not after the page is read. Post-filtering
        # returns a short -- or empty -- page while later pages still match,
        # which makes honest paging impossible: a caller walking the list cannot
        # tell "no matches on this page" from "no more cases", and stops early on
        # a project where the matches happen to start at page two.
        query = {}
        if state:
            query['_id'] = {'$in': Assignment().collection.distinct(
                'caseId', {'state': state})}
        elif unassigned:
            query['_id'] = {'$nin': Assignment().collection.distinct('caseId')}

        cases = list(Case().find(query, limit=limit, offset=offset, sort=sort))
        if not cases:
            return []

        # Batched deliberately. A row needs the case's assignments, each
        # assignment's annotator, and each one's latest submission and count --
        # four lookups per assignment done one at a time. Over a thousand cases
        # that is thousands of round trips for a list the reviewer expects to
        # scroll, so it is four queries for the whole page instead.
        caseIds = [c['_id'] for c in cases]
        assignments = list(Assignment().find({'caseId': {'$in': caseIds}},
                                             sort=[('assignedAt', 1)]))
        byCase = {}
        for assignment in assignments:
            byCase.setdefault(assignment['caseId'], []).append(assignment)

        userIds = {a['userId'] for a in assignments}
        self._userCache = {
            u['_id']: u for u in User().find({'_id': {'$in': list(userIds)}})
        } if userIds else {}

        assignmentIds = [a['_id'] for a in assignments]
        self._latest, self._counts = {}, {}
        if assignmentIds:
            for submission in Submission().find(
                    {'assignmentId': {'$in': assignmentIds}},
                    sort=[('created', 1)]):
                key = submission['assignmentId']
                # Ascending, so the last one seen for a key is the latest.
                self._latest[key] = submission
                self._counts[key] = self._counts.get(key, 0) + 1

        try:
            return [self._caseRow(case, byCase.get(case['_id'], []))
                    for case in cases]
        finally:
            # Per-request scratch, not state: leaving it set would have the next
            # request read a cache built for different cases.
            self._userCache = self._latest = self._counts = None

    def _caseRow(self, case, assignments):
        """One case, with every lease ever taken on it.

        A case is not a single row of state and never was -- it can be out with
        two annotators at once (a blind duplicate), and each of them has their own
        lifecycle. So the row carries the case's own counts and a list, rather
        than pretending there is one annotator and one state per case.
        """
        return {
            'caseId': str(case['_id']),
            'caseName': case.get('name', ''),
            'volumeName': self._volumeName(case),
            'replicasWanted': case.get('replicasWanted', 1),
            'activeCount': case.get('activeCount', 0),
            'approvedCount': case.get('approvedCount', 0),
            'retired': bool(case.get('retired', False)),
            'isGold': bool(case.get('isGold', False)),
            'assignments': [self._assignmentRow(a) for a in assignments],
        }

    def _assignmentRow(self, assignment):
        # Served from the page's batch when listCases built one, and fetched
        # singly otherwise -- caseSubmissions and claim both call this for one
        # assignment, where a batch would be more work than the lookup.
        cache = getattr(self, '_userCache', None)
        if cache is not None:
            annotator = cache.get(assignment['userId']) or {}
            submission = self._latest.get(assignment['_id'])
            count = self._counts.get(assignment['_id'], 0)
        else:
            annotator = User().load(assignment['userId'], force=True) or {}
            submission = Submission().latestForAssignment(assignment['_id'])
            count = Submission().countForAssignment(assignment['_id'])
        row = {
            'assignmentId': str(assignment['_id']),
            'state': assignment['state'],
            'attempt': assignment.get('attempt', 1),
            'annotator': annotator.get('login', ''),
            'assignedAt': _iso(assignment.get('assignedAt')),
            'submittedAt': _iso(assignment.get('submittedAt')),
            'decidedAt': _iso(assignment.get('decidedAt')),
            'submissionCount': count,
            'submissionId': None,
            'autoScore': None,
            'flagged': [],
        }
        if submission is not None:
            row['submissionId'] = str(submission['_id'])
            row['autoScore'] = submission.get('autoScore')
            row['flagged'] = self._flagged(submission, getPolicy())
            row['authorRole'] = submission.get('authorRole', sub.ANNOTATOR)
        return row

    def _volumeName(self, case):
        """The volume's own filename, so a client can save it under the right one.

        Not cosmetic. Slicer picks its reader from the extension, and this
        project's volumes are ``.nii.gz``: a gzipped NIfTI written to disk as
        ``volume.nrrd`` downloads cleanly, verifies cleanly and then fails to
        open with a message that never mentions the name. The annotator path
        learned that in 0.2.0 and the review path never did -- which is why
        opening a submission did nothing at all before 0.9.0.
        """
        file = File().load(case.get('fileId'), force=True) if case.get('fileId') else None
        return (file or {}).get('name', '') or ''

    def _submissionName(self, submission):
        """The stored segmentation's own filename, for the same reason."""
        if not submission.get('fileId'):
            return ''
        file = File().load(submission['fileId'], force=True)
        return (file or {}).get('name', '') or ''

    @access.user
    @autoDescribeRoute(
        Description('Every submission ever made against one case, oldest first.')
        .notes('Submissions are append-only, so this includes superseded '
               'attempts and any reviewer revisions. Nothing is ever replaced, '
               'which is what makes "what did they actually send the first '
               'time?" answerable months later.')
        .param('caseId', 'The case.', paramType='path')
    )
    def caseSubmissions(self, caseId):
        requireReviewer(self.getCurrentUser())
        case = Case().load(caseId, force=True)
        if case is None:
            refuse('no_such_case', 'That case no longer exists.', status=404)

        rows = []
        for submission in Submission().forCase(case['_id']):
            assignment = Assignment().load(submission['assignmentId'], force=True)
            if assignment is None:
                continue
            row = self._row(assignment, submission)
            row['authorRole'] = submission.get('authorRole', sub.ANNOTATOR)
            row['revisionOf'] = (str(submission['revisionOf'])
                                 if submission.get('revisionOf') else None)
            row['created'] = _iso(submission.get('created'))
            rows.append(row)
        return rows

    # ------------------------------------------------------------- revise

    @access.user
    @autoDescribeRoute(
        Description("Store a reviewer's corrected version, and approve the case.")
        .notes('Saved as another submission on the same assignment rather than '
               'as an edit of the annotator\'s, which is left exactly as it was '
               'sent. The correction is credited to the reviewer: per-annotator '
               'agreement numbers come from the author, and attributing a '
               "reviewer's fixes to the annotator would flatter precisely the "
               'submissions that needed fixing.')
        .param('submissionId', 'The submission being corrected.', paramType='path')
        .param('fileId', 'Girder file id of the uploaded .seg.nrrd.')
        .jsonParam('meta', 'Submission metadata.', requireObject=True)
        .errorResponse('That case has already been decided.', 409)
    )
    def revise(self, submissionId, fileId, meta):
        user = requireReviewer(self.getCurrentUser())
        original = self._loadSubmission(submissionId)
        assignment = Assignment().load(original['assignmentId'], force=True)

        if not st.can(assignment['state'], st.APPROVE):
            refuse(protocol.ERR_BAD_STATE,
                   f"This case is {assignment['state']} and cannot be revised.",
                   status=409, state=assignment['state'])

        submissionMeta = protocol.SubmissionMeta.from_dict(meta)
        file = File().load(fileId, level=AccessType.WRITE, user=user)
        if file is None:
            refuse('no_such_file', 'That upload could not be found.', status=404)

        actual = hashStoredFile(file)
        if not matches(submissionMeta.checksum, actual):
            refuse(protocol.ERR_CHECKSUM,
                   'The uploaded revision does not match its checksum, so it '
                   'was corrupted in transit. Nothing has been recorded.',
                   status=400, expected=submissionMeta.checksum, actual=actual)
        submissionMeta.checksum = actual

        item = Item().load(file['itemId'], force=True)
        if item is not None:
            Item().move(item, submissionsFolder(user))

        revision = Submission().createSubmission(
            assignment, submissionMeta, file['_id'],
            needsReview=False, author=user, revisionOf=original['_id'],
        )

        Review().createReview(revision, user, APPROVE,
                              comment='Corrected by the reviewer.')
        try:
            assignment = Assignment().transition(
                assignment, st.APPROVE,
                reviewerId=user['_id'], submissionId=revision['_id'])
        except st.TransitionError:
            refuse(protocol.ERR_BAD_STATE,
                   'Another reviewer decided this one first. The revision has '
                   'been stored but the case was not approved again.',
                   status=409, state=assignment['state'])

        Note().systemNote(
            assignment['caseId'],
            '{} corrected and approved attempt {}.'.format(
                user.get('login') or 'A reviewer', assignment.get('attempt', 1)))
        Case().completeSlot(assignment['caseId'])

        return {
            'submissionId': str(revision['_id']),
            'state': assignment['state'],
            'caseId': str(assignment['caseId']),
        }

    # ------------------------------------------------------- back to the pool

    @access.user
    @autoDescribeRoute(
        Description('Send a submitted case back to the pool for another annotator.')
        .notes('The assignment is released and the replica slot freed, so the '
               'case is servable again to whoever asks next -- including the '
               'annotator who did it, which is deliberate: carrying a per-case '
               'exclusion list for the rest of the project is a lot of machinery '
               'for a case that is about to be segmented by one of thirty '
               'people. The submission stays on record either way.')
        .param('submissionId', 'A submission on the assignment to return.',
               paramType='path')
        .param('reason', 'Why it is going back. Recorded on the case thread.',
               required=False, default='')
        .errorResponse('That case is not out with anybody.', 409)
    )
    def returnToPool(self, submissionId, reason):
        user = requireReviewer(self.getCurrentUser())
        submission = self._loadSubmission(submissionId)
        assignment = Assignment().load(submission['assignmentId'], force=True)

        try:
            assignment = Assignment().transition(
                assignment, st.RETURN_TO_POOL,
                reviewerId=user['_id'],
                releaseReason=(reason or '').strip() or 'returned to the pool by a reviewer')
        except st.TransitionError:
            refuse(protocol.ERR_BAD_STATE,
                   f"This case is {assignment['state']}, so there is nothing to "
                   'send back.',
                   status=409, state=assignment['state'])

        # The slot has to be freed or the case stays unservable: `activeCount`
        # is what /next filters on, and an assignment released without it is a
        # case that looks busy forever.
        Case().releaseSlot(assignment['caseId'])

        Note().systemNote(
            assignment['caseId'],
            '{} returned attempt {} to the pool{}'.format(
                user.get('login') or 'A reviewer',
                assignment.get('attempt', 1),
                ': ' + reason.strip() if (reason or '').strip() else '.'))

        return {
            'returned': True,
            'state': assignment['state'],
            'caseId': str(assignment['caseId']),
        }

    # ------------------------------------------------- handing work out

    @access.user
    @autoDescribeRoute(
        Description('Who a case can be assigned to.')
        .notes('Members of the annotator group, with how much each is already '
               'holding -- which is the number that decides who gets the next '
               'one, and is otherwise a question nobody can answer from the '
               'case list.')
    )
    def listAnnotators(self):
        requireReviewer(self.getCurrentUser())
        group = Group().findOne({'name': ANNOTATOR_GROUP})
        if group is None:
            return []

        rows = []
        for user in Group().listMembers(group):
            rows.append({
                'userId': str(user['_id']),
                'login': user.get('login', ''),
                'name': f"{user.get('firstName', '')} "
                        f"{user.get('lastName', '')}".strip(),
                'openCases': Assignment().countOpenForUser(user['_id']),
                'quota': user.get('segqueueQuota'),
                'disabled': user.get('status') == 'disabled',
            })
        return sorted(rows, key=lambda r: (r['disabled'], r['login']))

    @access.user
    @autoDescribeRoute(
        Description('Assign a specific case to a specific annotator.')
        .notes('The escape hatch for everything the queue cannot express: a '
               'case that needs a particular person, a hand-over after someone '
               'leaves, or simply getting a thousand cases moving without '
               'waiting for each annotator to ask.\n\n'
               'Reviewer-gated rather than admin-gated, because handing work out '
               'is what the people watching the queue actually do; the identical '
               'admin route stays for scripts.')
        .param('caseId', 'The case to assign.', paramType='path')
        .param('userId', 'Who to assign it to.')
        .errorResponse('That case has no free replica slot.', 409)
    )
    def assignCase(self, caseId, userId):
        requireReviewer(self.getCurrentUser())
        case = Case().load(caseId, force=True)
        if case is None:
            refuse('no_such_case', 'That case no longer exists.', status=404)
        user = User().load(userId, force=True)
        if user is None:
            refuse('no_such_user', 'No such user.', status=404)
        if not isAnnotator(user):
            refuse('not_an_annotator',
                   f"{user.get('login')!r} is not in the annotator group, so "
                   'they cannot be given a case.', status=400)

        # `claim` is the atomic one: it consumes a replica slot and records the
        # person in `assignedUserIds` in a single update, so two reviewers
        # assigning the same case at the same moment cannot both win.
        claimed = Case().claim(case['_id'], user['_id'])
        if claimed is None:
            refuse('case_unavailable',
                   'That case is retired, already out with someone, or has '
                   'previously been assigned to this person.',
                   status=409)

        assignment = Assignment().createAssignment(
            claimed, user, kind=pol.NORMAL, policy=getPolicy())
        Note().systemNote(
            case['_id'],
            '{} assigned this case to {}.'.format(
                self.getCurrentUser().get('login') or 'A reviewer',
                user.get('login') or 'an annotator'))
        return {
            'assignmentId': str(assignment['_id']),
            'caseId': str(case['_id']),
            'caseName': case.get('name', ''),
            'annotator': user.get('login', ''),
            'state': assignment['state'],
        }

    # ------------------------------------------- opening a case with no work

    @access.user
    @autoDescribeRoute(
        Description('Download any case\'s source volume.')
        .notes('The reviewer-side counterpart of the annotator download, which '
               'requires holding the case. A reviewer looking over a thousand '
               'cases holds none of them, and a case nobody has touched has no '
               'submission to open either -- so without this there is no way to '
               'look at one before deciding who should get it.')
        .param('caseId', 'The case.', paramType='path')
    )
    def downloadCaseVolume(self, caseId):
        requireReviewer(self.getCurrentUser())
        case = Case().load(caseId, force=True)
        if case is None:
            refuse('no_such_case', 'That case no longer exists.', status=404)
        return File().download(fileForCase(case))

    @access.user
    @autoDescribeRoute(
        Description('Download a helper mask that ships with any case.')
        .param('caseId', 'The case.', paramType='path')
        .param('kind', 'region or seed.', paramType='path',
               enum=list(protocol.ASSET_KINDS))
    )
    def downloadCaseAsset(self, caseId, kind):
        requireReviewer(self.getCurrentUser())
        case = Case().load(caseId, force=True)
        if case is None:
            refuse('no_such_case', 'That case no longer exists.', status=404)
        if kind not in protocol.ASSET_KINDS:
            refuse(protocol.ERR_NO_ASSET, f'Unknown asset kind {kind!r}.',
                   status=400)
        fileId = case.get('regionFileId' if kind == protocol.ASSET_REGION
                          else 'seedFileId')
        if not fileId:
            # Most cases ship neither, and the client asks for both on every one,
            # so absence is an answer rather than a failure -- the same contract
            # the annotator-side route has.
            refuse(protocol.ERR_NO_ASSET, f'This case has no {kind} mask.',
                   status=404)
        file = File().load(fileId, force=True)
        if file is None:
            refuse(protocol.ERR_NO_ASSET,
                   f'The {kind} mask for this case is missing from storage.',
                   status=404)
        return File().download(file)

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
            # Both filenames travel with the row, because Slicer chooses its
            # reader from the extension: a `.nii.gz` volume saved as `volume.nrrd`
            # downloads cleanly, verifies cleanly and then will not open. See
            # ``_volumeName``.
            'volumeName': self._volumeName(case),
            'submissionName': self._submissionName(submission),
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
        if pol.usable_score(mean):
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
