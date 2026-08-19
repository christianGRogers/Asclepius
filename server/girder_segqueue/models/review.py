"""Reviews: a reviewer's verdict on one submission.

Separate from the submission it judges so that a second opinion is an ordinary
insert rather than a schema change, and so that reviewer throughput can be
measured without touching annotator records. Rubric scores are optional and
free-form on purpose -- a lab that wants to grade "vessel continuity 1-5" should
be able to start doing so without a migration.
"""

import datetime

from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.model_base import AccessControlledModel

APPROVE = 'approve'
REJECT = 'reject'
VERDICTS = (APPROVE, REJECT)


class Review(AccessControlledModel):
    def initialize(self):
        self.name = 'segqueue_review'
        self.ensureIndices([
            'submissionId',
            ([('reviewerId', 1), ('created', 1)], {}),
            'verdict',
        ])
        self.exposeFields(level=AccessType.READ, fields={
            '_id', 'submissionId', 'assignmentId', 'caseId', 'reviewerId',
            'annotatorId', 'verdict', 'comment', 'rubric', 'created',
            'secondsSpent',
        })

    def validate(self, doc):
        if doc.get('verdict') not in VERDICTS:
            raise ValidationException(
                f"Verdict must be one of {VERDICTS}, got {doc.get('verdict')!r}.", 'verdict')
        doc['comment'] = (doc.get('comment') or '').strip()
        if doc['verdict'] == REJECT and not doc['comment']:
            # The rework loop is only a teaching device if it says what to fix.
            # A bare rejection wastes the annotator's next attempt as surely as
            # no feedback at all.
            raise ValidationException(
                'A rejection must carry a comment explaining what to fix.', 'comment')
        doc.setdefault('rubric', {})
        return doc

    def createReview(self, submission, reviewer, verdict, comment='', rubric=None,
                     secondsSpent=None):
        doc = {
            'submissionId': submission['_id'],
            'assignmentId': submission['assignmentId'],
            'caseId': submission['caseId'],
            'annotatorId': submission['userId'],
            'reviewerId': reviewer['_id'],
            'verdict': verdict,
            'comment': comment,
            'rubric': rubric or {},
            'secondsSpent': secondsSpent,
            'created': datetime.datetime.now(datetime.timezone.utc),
        }
        return self.save(doc)

    def forSubmission(self, submissionId):
        return list(self.find({'submissionId': submissionId}, sort=[('created', 1)]))

    def countsByReviewer(self):
        """``{reviewerId: {approve: n, reject: n}}`` for the dashboard."""
        pipeline = [
            {'$group': {
                '_id': {'reviewer': '$reviewerId', 'verdict': '$verdict'},
                'n': {'$sum': 1},
            }},
        ]
        out = {}
        for row in self.collection.aggregate(pipeline):
            reviewer = row['_id']['reviewer']
            out.setdefault(reviewer, {APPROVE: 0, REJECT: 0})
            out[reviewer][row['_id']['verdict']] = row['n']
        return out
