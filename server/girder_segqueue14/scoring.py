"""``segqueue14-score`` -- score every read, and reclaim stranded cases.

The live worker (``girder_segqueue.scoring``) scores gold and duplicate
submissions. This one scores every SegQueue14 read that has something to be
scored against:

* **a reference** -- the case has an ImageCAS-X segmentation
  (``SegQueue/imagecas-x/segmentations/<id>.coronary.nii.gz``): per-class Dice,
  HD95 and presence against it, for all 14 classes;
* **a second read** -- the case wants two reads (the 200 unlabelled cases, a new
  dataset, or an ImageCAS-X blind duplicate): the same numbers between the two.

A read whose scores fall below the ``segqueue14.reference`` thresholds goes to a
reviewer whatever the sampling roll said; one that passes and was not sampled is
approved here, as the live worker does for gold and duplicates. The metric code
is ``segtrain.metrics`` via ``segqueue14.scoring`` -- one implementation of Dice
for the model, the team and the paper.

A submission's grid is not trusted to be the reference's: a Slicer export can
store the same voxels in a different index order (the first real SegQueue
submissions were z-reversed against their CT). Both are put on the reference's
grid by resampling in physical space, nearest neighbour, before anything is
compared.
"""

import logging
import os
import tempfile
import time

from girder.models.file import File
from segqueue import states as st
from segqueue14 import labels
from segqueue14 import scoring as sq

from .maintenance import SWEEP_SECONDS, sweep
from .models import Assignment14, Case14, Submission14
from .models.submission import ANNOTATOR
from .settings import getReference

logger = logging.getLogger(__name__)

POLL_SECONDS = 30


def _deps():
    try:
        import numpy as np
        import SimpleITK as sitk
    except ImportError as exc:  # pragma: no cover - deployment error
        raise ImportError(
            'segqueue14-score needs numpy and SimpleITK:\n'
            '    pip install "./server/girder_segqueue14[scoring]"') from exc
    return np, sitk


def readImage(fileDoc):
    """A Girder file as a SimpleITK image, via a temp file (ITK reads paths)."""
    _, sitk = _deps()
    name = fileDoc.get('name', '')
    suffix = '.nii.gz' if name.endswith('.nii.gz') else (os.path.splitext(name)[1] or '.nrrd')
    handle, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(handle, 'wb') as out:
            for chunk in File().download(fileDoc, headers=False)():
                out.write(chunk)
        return sitk.ReadImage(path)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def sameGrid(a, b, tol=1e-3):
    if tuple(a.GetSize()) != tuple(b.GetSize()):
        return False
    pairs = ((a.GetSpacing(), b.GetSpacing()), (a.GetOrigin(), b.GetOrigin()),
             (a.GetDirection(), b.GetDirection()))
    return all(abs(x - y) <= tol for one, two in pairs for x, y in zip(one, two, strict=False))


def onGrid(image, reference):
    """``image``'s labels as an array on ``reference``'s grid (z, y, x)."""
    np, sitk = _deps()
    if not sameGrid(image, reference):
        image = sitk.Resample(image, reference, sitk.Transform(),
                              sitk.sitkNearestNeighbor, 0, image.GetPixelID())
    return np.asarray(sitk.GetArrayFromImage(image)).astype(np.uint8, copy=False)


def _spacing(image):
    # GetArrayFromImage is (z, y, x); spacing is (x, y, z).
    return tuple(reversed(image.GetSpacing()))


def scoreAgainst(readFile, referenceFile):
    """Score one stored label file against another, on the second one's grid."""
    np, sitk = _deps()
    reference = readImage(referenceFile)
    read = readImage(readFile)
    readArr = onGrid(read, reference)
    refArr = np.asarray(sitk.GetArrayFromImage(reference)).astype(np.uint8, copy=False)
    if np.count_nonzero(readArr) == 0 and np.count_nonzero(sitk.GetArrayViewFromImage(read)):
        # Labels in the file, none after resampling: the two do not overlap in
        # physical space, so every number would be a meaningless zero.
        return {'error': 'geometry_mismatch', 'mean_dice': None}, readArr
    result = sq.score_labels(readArr, refArr, _spacing(reference))
    return result, readArr


def partnerSubmission(submission):
    """The latest annotator read of the same case by somebody else, if any."""
    found = None
    for other in Submission14().forCase(submission['caseId']):
        if other['_id'] == submission['_id'] or other['userId'] == submission['userId']:
            continue
        if other.get('authorRole', ANNOTATOR) != ANNOTATOR:
            continue
        found = other  # forCase is oldest first, so the last one wins
    return found


def scoreOne(submission, thresholds=None):
    """Score one submission and record it. Returns the score, or None to wait.

    ``None`` means "not yet": a two-read case without a reference whose second
    read has not arrived. It stays unscored and is retried on the next pass, so
    the first read of a pair is decided when the pair is complete.
    """
    thresholds = thresholds or getReference()
    case = Case14().load(submission['caseId'], force=True)
    if case is None:
        return None
    readFile = File().load(submission['fileId'], force=True)
    if readFile is None:
        return None

    score = {'flags': [], 'against': []}
    readArr = None
    if case.get('referenceFileId'):
        referenceFile = File().load(case['referenceFileId'], force=True)
        if referenceFile is None:
            score['reference'] = {'error': 'reference_missing', 'mean_dice': None}
        else:
            score['reference'], readArr = scoreAgainst(readFile, referenceFile)
            score['reference']['referenceFileId'] = str(case['referenceFileId'])
        score['against'].append('imagecas-x')
        score['flags'] += sq.reference_flags(score['reference'], thresholds)

    partner = partnerSubmission(submission) if case.get('replicasWanted', 1) >= 2 else None
    if partner is not None:
        partnerFile = File().load(partner['fileId'], force=True)
        if partnerFile is not None:
            pair, mine = scoreAgainst(readFile, partnerFile)
            pair['partnerSubmissionId'] = str(partner['_id'])
            score['duplicate'] = pair
            score['against'].append('second-read')
            score['flags'] += sq.duplicate_flags(pair, thresholds)
            if readArr is None:
                readArr = mine
            # The earlier read of the pair was decided before this one existed;
            # give it the pair score too, for the reviewer's view.
            mirrored = dict(pair, partnerSubmissionId=str(submission['_id']))
            Submission14().mergeScore(partner['_id'], 'duplicate', mirrored)
    elif not case.get('referenceFileId'):
        return None  # a paired case waiting for its second read

    if readArr is not None:
        counts = sq.voxel_counts(readArr)
        score['voxelCounts'] = counts
        missing = labels.missing_required(counts)
        score['missingRequired'] = missing
        if missing:
            score['flags'].append('required class empty in the uploaded file: '
                                  + ', '.join(missing))
    score['mean_dice'] = sq.headline_dice(score)

    needsReview = bool(score['flags'])
    Submission14().recordScore(submission['_id'], score, needsReview=needsReview)
    if needsReview:
        Assignment14().collection.update_one(
            {'_id': submission['assignmentId']}, {'$set': {'needsReview': True}})
        logger.info('flagged submission %s: %s', submission['_id'],
                    '; '.join(score['flags']))
    _autoApproveIfClear(submission, needsReview)
    return score


def _autoApproveIfClear(submission, needsReview):
    if needsReview:
        return
    assignment = Assignment14().load(submission['assignmentId'], force=True)
    if assignment is None or assignment.get('needsReview'):
        return
    if not st.can(assignment['state'], st.APPROVE):
        return
    try:
        Assignment14().transition(assignment, st.APPROVE)
    except st.TransitionError:
        return
    Case14().completeSlot(assignment['caseId'])


def runOnce(limit=25):
    thresholds = getReference()
    scored = 0
    for submission in Submission14().unscored(limit=limit):
        try:
            if scoreOne(submission, thresholds) is not None:
                scored += 1
        except Exception:
            logger.exception('failed to score submission %s', submission['_id'])
    return scored


def runForever(pollSeconds=POLL_SECONDS, sweepSeconds=SWEEP_SECONDS):  # pragma: no cover
    logger.info('SegQueue14 worker started; scoring every %ss, sweeping every %ss',
                pollSeconds, sweepSeconds)
    lastSweep = 0.0
    while True:
        try:
            n = runOnce()
            if n:
                logger.info('scored %d submission(s)', n)
        except Exception:
            logger.exception('scoring pass failed; continuing')
        if time.time() - lastSweep >= sweepSeconds:
            lastSweep = time.time()
            try:
                sweep()
            except Exception:
                logger.exception('sweep failed; continuing')
        time.sleep(pollSeconds)


def main(argv=None):  # pragma: no cover - CLI entry point
    import argparse

    parser = argparse.ArgumentParser(
        prog='segqueue14-score',
        description='Score SegQueue14 reads against ImageCAS-X and against each '
                    'other, and reclaim lapsed SegQueue14 assignments. Touches only '
                    'SegQueue14 data.')
    parser.add_argument('--once', action='store_true', help='One pass, then exit.')
    parser.add_argument('--poll', type=int, default=POLL_SECONDS)
    parser.add_argument('--sweep', type=int, default=SWEEP_SECONDS)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    if args.once:
        print(f'scored {runOnce()} submission(s)')
        print(f"released {len(sweep()['released'])} stranded assignment(s)")
        return 0
    runForever(args.poll, args.sweep)
    return 0

