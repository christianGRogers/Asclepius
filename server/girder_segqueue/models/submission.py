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
        })
        self.exposeFields(level=AccessType.SITE_ADMIN, fields={
            'kind', 'scored', 'autoScore', 'needsReview',
        })

    def validate(self, doc):
        if not doc.get('assignmentId'):
            raise ValidationException('Submission must belong to an assignment.',
                                      'assignmentId')
        doc['annotationSeconds'] = float(doc.get('annotationSeconds', 0.0))
        doc['sizeBytes'] = int(doc.get('sizeBytes', 0))
        doc.setdefault('voxelCounts', {})
        doc.setdefault('warnings', [])
        return doc

    def createSubmission(self, assignment, meta, fileId, warnings=(), needsReview=True):
        """Store one accepted upload.

        ``meta`` is a ``segqueue.protocol.SubmissionMeta``. The checksum stored
        here is the one the *server* computed over the received bytes, not the
        one the client declared -- they have already been compared by the time
        this is called, and recording the verified value means the database
        never holds a number nobody checked.
        """
        doc = {
            'assignmentId': assignment['_id'],
            'caseId': assignment['caseId'],
            'userId': assignment['userId'],
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

    def unscored(self, limit=25):
        """The worker's queue: gold and duplicate submissions not yet scored."""
        return list(self.find(
            {'scored': False, 'kind': {'$in': [pol.GOLD, pol.DUPLICATE]}},
            limit=limit, sort=[('created', 1)],
        ))
