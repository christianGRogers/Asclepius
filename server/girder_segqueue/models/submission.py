"""Submissions: an uploaded segmentation and everything known about it.

Append-only. A rework produces a second submission rather than replacing the
first, and nothing here is ever edited after creation except the automatic
scores, which arrive from the worker a few seconds later. That costs a little
storage -- a ``.seg.nrrd`` is single-digit megabytes -- and buys the ability to
answer "what did they actually send the first time?" months afterwards, which is
the question you want when a reviewer and an annotator disagree about what was
asked for.
"""

import datetime

from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.model_base import AccessControlledModel
from pymongo import ReturnDocument
from segqueue import policy as pol

#: Who made a submission. An annotator's is the work; a reviewer's is a
#: correction of it, and the two must never be counted as the same thing.
ANNOTATOR = 'annotator'
REVIEWER = 'reviewer'


class Submission(AccessControlledModel):
    def initialize(self):
        self.name = 'segqueue_submission'
        self.ensureIndices([
            'assignmentId',
            ([('caseId', 1), ('created', 1)], {}),
            ([('userId', 1), ('created', 1)], {}),
            # The worker's scan for submissions whose scores have not run yet.
            ([('kind', 1), ('scored', 1)], {}),
        ])
        self.exposeFields(level=AccessType.READ, fields={
            '_id', 'assignmentId', 'caseId', 'userId', 'fileId', 'checksum',
            'sizeBytes', 'annotationSeconds', 'voxelCounts', 'slicerVersion',
            'extensionVersion', 'annotatorNote', 'warnings', 'attempt', 'created',
            'authorRole', 'revisionOf',
        })
        self.exposeFields(level=AccessType.SITE_ADMIN, fields={
            'kind', 'scored', 'autoScore', 'needsReview',
        })

    def validate(self, doc):
        if not doc.get('assignmentId'):
            raise ValidationException('Submission must belong to an assignment.',
                                      'assignmentId')
        # Defaulted, not required. Every submission written before reviewer
        # revisions existed is an annotator's, and a row saved again for any
        # reason must not start failing validation because of a field that was
        # not invented yet.
        doc.setdefault('authorRole', ANNOTATOR)
        doc.setdefault('revisionOf', None)
        if doc['authorRole'] not in (ANNOTATOR, REVIEWER):
            raise ValidationException(
                f"Unknown submission authorRole {doc['authorRole']!r}.",
                'authorRole')
        doc['annotationSeconds'] = float(doc.get('annotationSeconds', 0.0))
        doc['sizeBytes'] = int(doc.get('sizeBytes', 0))
        doc.setdefault('voxelCounts', {})
        doc.setdefault('warnings', [])
        return doc

    def createSubmission(self, assignment, meta, fileId, warnings=(), needsReview=True,
                         author=None, revisionOf=None):
        """Store one accepted upload.

        ``meta`` is a ``segqueue.protocol.SubmissionMeta``. The checksum stored
        here is the one the *server* computed over the received bytes, not the
        one the client declared -- they have already been compared by the time
        this is called, and recording the verified value means the database
        never holds a number nobody checked.

        ``author`` overrides who gets credited, and is how a reviewer's corrected
        version is stored: as another row on the same assignment rather than as
        an edit of the annotator's. That is the whole reason this model is
        append-only. Crediting the reviewer honestly matters more than it looks --
        per-annotator agreement numbers are computed from ``userId``, and silently
        attributing the reviewer's corrections to the annotator would flatter
        exactly the submissions a human had to fix. ``revisionOf`` records which
        submission was being corrected, so the pair can be told apart later.
        """
        doc = {
            'assignmentId': assignment['_id'],
            'caseId': assignment['caseId'],
            'userId': (author or {}).get('_id') or assignment['userId'],
            'authorRole': REVIEWER if author is not None else ANNOTATOR,
            'revisionOf': revisionOf,
            'attempt': assignment.get('attempt', 1),
            'kind': assignment.get('kind', pol.NORMAL),
            'fileId': fileId,
            'checksum': meta.checksum,
            'sizeBytes': meta.size_bytes,
            'annotationSeconds': meta.annotation_seconds,
            'voxelCounts': meta.voxel_counts,
            'slicerVersion': meta.slicer_version,
            'extensionVersion': meta.extension_version,
            'annotatorNote': meta.annotator_note,
            'warnings': list(warnings),
            # Gold and duplicate submissions are scored asynchronously; ordinary
            # ones have nothing to score against and are marked done immediately.
            'scored': assignment.get('kind', pol.NORMAL) == pol.NORMAL,
            'autoScore': None,
            'needsReview': needsReview,
            'created': datetime.datetime.now(datetime.timezone.utc),
        }
        return self.save(doc)

    def recordScore(self, submissionId, score, needsReview=None):
        """Attach the worker's automatic score.

        ``needsReview`` may be raised from False to True here and never lowered:
        a bad gold score must be able to pull a submission back for a human, but
        a good one must not cancel a review the sampling policy already asked
        for.
        """
        update = {'autoScore': score, 'scored': True}
        if needsReview:
            update['needsReview'] = True
        return self.collection.find_one_and_update(
            {'_id': submissionId},
            {'$set': update},
            return_document=ReturnDocument.AFTER,
        )

    def latestForAssignment(self, assignmentId):
        return self.findOne({'assignmentId': assignmentId}, sort=[('created', -1)])

    def forCase(self, caseId):
        return list(self.find({'caseId': caseId}, sort=[('created', 1)]))

    def countForAssignment(self, assignmentId):
        return self.collection.count_documents({'assignmentId': assignmentId})

    def unscored(self, limit=25):
        """The worker's queue: gold and duplicate submissions not yet scored."""
        return list(self.find(
            {'scored': False, 'kind': {'$in': [pol.GOLD, pol.DUPLICATE]}},
            limit=limit, sort=[('created', 1)],
        ))
