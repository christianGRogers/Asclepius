"""``segqueue14-score`` -- score every read, and reclaim stranded cases.

The live worker (``girder_segqueue.scoring``) scores gold and duplicate
submissions. This one scores every SegQueue14 read that has something to be
scored against:

* **a reference** -- the case has an ImageCAS-X segmentation
  (``SegQueue/imagecas-x/segmentations/<id>.coronary.nii.gz``): per-class Dice,
  HD95 and presence against it, per class; the reference is always in
  ImageCAS-X's 14 values and is first collapsed to the project's four
  (``labels.icx14_to_four``, D25: "Other" to the nearest LAD/LCx in mm);
* **a second read** -- the case wants two reads (the 200 unlabelled cases, a new
  dataset, or an ImageCAS-X blind duplicate): the same numbers between the two.

The annotator benchmark (D43) is a reference-scored case with two differences:
it is never paired with another annotator's read of it, and it always goes to a
reviewer, scored or not. Each attempt keeps its own score.

A read whose scores fall below the ``segqueue14.reference`` thresholds goes to a
reviewer whatever the sampling roll said; one that passes and was not sampled is
approved here, as the live worker does for gold and duplicates. The metric code
is ``segtrain.metrics`` via ``segqueue14.scoring`` -- one implementation of Dice
for the model, the team and the paper.

A submission is a class stack (one mask per class, every class whole, overlaps
included: D39, ``segqueue14.labelfile``) or, from before protocol 17, one label
volume; each class is scored from its own mask either way, and old submissions
score exactly as they did.

A read with the extended classes (D44) is collapsed to the four before it is
scored: each branch is unioned into its parent and the materials go into no
vessel (``labels.collapse_to_four``), so the headline stays four-class and an
extended read pairs with a 4-class one. A material both reads of a pair have is
scored on its own, under ``materials``; it never moves the headline.

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
from segqueue14 import labelfile, labels
from segqueue14 import plan as sqplan
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


def _downloadTemp(fileDoc):
    """A Girder file at a temp path (ITK and the class-stack reader read paths)."""
    name = fileDoc.get('name', '')
    suffix = '.nii.gz' if name.endswith('.nii.gz') else (os.path.splitext(name)[1] or '.nrrd')
    handle, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(handle, 'wb') as out:
        for chunk in File().download(fileDoc, headers=False)():
            out.write(chunk)
    return path


def readImage(fileDoc):
    """A Girder file as a SimpleITK image, via a temp file (ITK reads paths)."""
    _, sitk = _deps()
    path = _downloadTemp(fileDoc)
    try:
        return sitk.ReadImage(path)
    finally:
        _unlink(path)


class ClassStack(list):
    """A class-stack read: one SimpleITK mask per class, with the class ``names``."""

    def __init__(self, images, names):
        super().__init__(images)
        self.names = list(names)


def readLabels(fileDoc):
    """A stored segmentation, whatever its format.

    A class stack (D39, ``segqueue14.labelfile``) comes back as a ``ClassStack``:
    one SimpleITK 0/1 mask per class the file has (the four, or all 21 with the
    extended classes, D44), each whole -- overlaps included -- and their names.
    Anything else is an old single label volume (or a reference) and comes back
    as one SimpleITK image. The format is read from the file's own header, not
    from what the client declared.
    """
    path = _downloadTemp(fileDoc)
    try:
        if labelfile.sniff(path) == labelfile.FORMAT_CLASS_STACK:
            return classStackImages(path)
        _, sitk = _deps()
        return sitk.ReadImage(path)
    finally:
        _unlink(path)


def classStackImages(path, names=None):
    """A class-stack file as a ``ClassStack``: one SimpleITK mask per class.

    With ``names``, those classes in that order, matched by the names in the
    file's header; a class the file does not name is an empty mask on the same
    grid. Without, every class the file has, in its own order.
    """
    np, sitk = _deps()
    data = labelfile.read_class_stack(path)
    names = list(data['names'] if names is None else names)
    byName = {name: index for index, name in enumerate(data['names'])}
    images = []
    for name in names:
        index = byName.get(name)
        mask = (data['masks'][index] if index is not None
                else np.zeros(data['masks'].shape[1:], np.uint8))
        image = sitk.GetImageFromArray(np.ascontiguousarray(mask, dtype=np.uint8))
        image.SetSpacing(data['spacing'])
        image.SetOrigin(data['origin'])
        image.SetDirection(data['direction'])
        images.append(image)
    return ClassStack(images, names)


def _unlink(path):
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


def stackOnGrid(read, reference, icx14=False):
    """``(masks, names)``: every class of ``read`` (from ``readLabels``) on ``reference``'s grid.

    A class stack is resampled class by class, so each keeps its own voxels, and
    keeps all its classes (the four, or 21, D44); a label volume is resampled once
    and split by value into the four -- after collapsing ImageCAS-X's 14 values to
    the four when ``icx14`` says it is a reference.
    """
    np, _ = _deps()
    if isinstance(read, list):
        names = list(getattr(read, 'names', None) or labels.NAMES[:len(read)])
        masks = np.stack([onGrid(image, reference) != 0 for image in read]).astype(np.uint8)
        return masks, names
    values = onGrid(read, reference)
    if icx14:
        values = labels.icx14_to_four(values, _spacing(reference))
    return sq.as_masks(values), list(labels.NAMES)


def masksOnGrid(read, reference, icx14=False):
    """``(4, z, y, x)`` masks of ``read`` on ``reference``'s grid, in the four classes.

    ``stackOnGrid``, then an extended read collapsed to the four
    (``labels.collapse_to_four``, D44): each branch unioned into its parent,
    materials dropped. A four-class read comes back as it was.
    """
    masks, names = stackOnGrid(read, reference, icx14=icx14)
    return labels.collapse_to_four(masks, names)


def _gridOf(image):
    """The image whose grid a read is put on: a label volume, or a stack's first class."""
    return image[0] if isinstance(image, list) else image


def _anyLabel(image):
    np, sitk = _deps()
    images = image if isinstance(image, list) else [image]
    return any(np.count_nonzero(sitk.GetArrayViewFromImage(i)) for i in images)


def _spacing(image):
    # GetArrayFromImage is (z, y, x); spacing is (x, y, z).
    return tuple(reversed(image.GetSpacing()))


def scoreAgainst(readFile, referenceFile, icx14=False):
    """Score one stored segmentation against another, on the second one's grid.

    Either file may be a class stack (every class whole, D39) or an old label
    volume; both are turned into one mask per class and each class is scored
    from its own mask. ``icx14`` says the second file is an ImageCAS-X reference
    (a case's ``referenceFileId``), in its 14 label values: it is collapsed to the
    project's four first (``labels.icx14_to_four``, D25), so like is scored with
    like. It is decided by what the file is, never by its values (#57). A second
    read is already in the four and is compared as stored.

    Either side may have the extended classes (D44): both are collapsed to the
    four for the headline, and a material both have is scored on its own
    (``segqueue14.scoring.score_reads``). A 4-class pair scores as it always did.

    Returns ``(score, readMasks)``; ``readMasks`` is ``(4, z, y, x)``, the read in
    the four classes.
    """
    reference = readLabels(referenceFile)
    read = readLabels(readFile)
    grid = _gridOf(reference)
    readMasks, readNames = stackOnGrid(read, grid)
    refMasks, refNames = stackOnGrid(reference, grid, icx14=icx14)
    four = labels.collapse_to_four(readMasks, readNames)
    if not readMasks.any() and _anyLabel(read):
        # Labels in the file, none after resampling: the two do not overlap in
        # physical space, so every number would be a meaningless zero.
        return {'error': 'geometry_mismatch', 'mean_dice': None}, four
    result = sq.score_reads(readMasks, readNames, refMasks, refNames, _spacing(grid))
    return result, four


def partnerSubmission(submission):
    """The latest annotator read of the same case by somebody else, if any."""
    found = None
    for other in Submission14().forCase(submission['caseId']):
        if other['_id'] == submission['_id'] or other['userId'] == submission['userId']:
            continue
        if other.get('authorRole', ANNOTATOR) != ANNOTATOR:
            continue
        if other.get('reopenedAt'):
            continue  # back with its annotator (#315): her resubmission pairs instead
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

    benchmark = bool(case.get('benchmark')) or submission.get('kind') == sqplan.KIND_BENCHMARK
    score = {'flags': [], 'against': []}
    if benchmark:
        score['benchmark'] = True
    readArr = None
    if case.get('referenceFileId'):
        referenceFile = File().load(case['referenceFileId'], force=True)
        if referenceFile is None:
            score['reference'] = {'error': 'reference_missing', 'mean_dice': None}
        else:
            score['reference'], readArr = scoreAgainst(readFile, referenceFile, icx14=True)
            score['reference']['referenceFileId'] = str(case['referenceFileId'])
        score['against'].append('imagecas-x')
        score['flags'] += sq.reference_flags(score['reference'], thresholds)

    # A benchmark read is the annotator's alone: never paired (D43).
    partner = (partnerSubmission(submission)
               if case.get('replicasWanted', 1) >= 2 and not benchmark else None)
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
        # Each class counted whole, overlaps included (D39).
        counts = sq.mask_counts(readArr)
        score['voxelCounts'] = counts
        missing = labels.missing_required(counts)
        score['missingRequired'] = missing
        if missing:
            score['flags'].append('required class empty in the uploaded file: '
                                  + ', '.join(missing))
    score['mean_dice'] = sq.headline_dice(score)

    # A benchmark read always goes to a reviewer, with its Dice (D43).
    needsReview = bool(score['flags']) or benchmark
    Submission14().recordScore(submission['_id'], score, needsReview=needsReview)
    if needsReview:
        Assignment14().collection.update_one(
            {'_id': submission['assignmentId']}, {'$set': {'needsReview': True}})
        logger.info('%s submission %s: %s', 'benchmark' if benchmark else 'flagged',
                    submission['_id'], '; '.join(score['flags']) or 'for review')
    _autoApproveIfClear(submission, needsReview)
    return score


def _autoApproveIfClear(submission, needsReview):
    if needsReview:
        return
    assignment = Assignment14().load(submission['assignmentId'], force=True)
    if assignment is None or assignment.get('needsReview'):
        return
    if submission.get('reopenedAt') or assignment.get('submissionId') != submission['_id']:
        return  # not the assignment's current read (#315): its score decides nothing
    if assignment.get('kind') == sqplan.KIND_BENCHMARK:
        return  # never auto-approved (D43)
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

