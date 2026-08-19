"""The background worker: score gold and duplicate work, reclaim stranded cases.

Runs as a separate process on a timer. Deliberately not inline in the submit
handler: reading two label volumes and computing HD95 takes seconds, and an
annotator who clicks Submit should get their next case immediately rather than
waiting on a distance transform.

The metrics themselves come from ``segtrain.metrics`` -- the same Dice and the
same surface machinery the training pipeline reports. Using one implementation
for "how good is the model" and "how well do two students agree" is not just
tidiness: the numbers end up in the same paper, and two implementations would
eventually disagree in a way nobody could explain.
"""

import logging
import os
import tempfile
import time

from girder.models.file import File
from segqueue import policy as pol

from .maintenance import SWEEP_SECONDS, sweep
from .models import Assignment, Case, Submission
from .settings import getPolicy

logger = logging.getLogger(__name__)

#: Seconds between scans when run as a daemon.
POLL_SECONDS = 30


def _requireScoringDeps():
    """Import the heavy dependencies, with an error that says what to install."""
    try:
        import numpy as np  # noqa: F401
        import SimpleITK as sitk  # noqa: F401
    except ImportError as exc:  # pragma: no cover - deployment error
        raise ImportError(
            'The SegQueue scoring worker needs numpy and SimpleITK:\n'
            '    pip install "girder-segqueue[scoring]"\n'
            'The web server does not need them, which is why they are an extra.'
        ) from exc
    return np, sitk


def _readLabels(fileDoc):
    """Download a Girder file to a temp path and read it as a label array.

    Via a temp file because SimpleITK reads paths, not streams, and because the
    NRRD reader needs to seek. Segmentations are single-digit megabytes, so this
    costs nothing worth optimising away.
    """
    np, sitk = _requireScoringDeps()
    suffix = os.path.splitext(fileDoc['name'])[1] or '.nrrd'
    handle, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(handle, 'wb') as out:
            for chunk in File().download(fileDoc, headers=False)():
                out.write(chunk)
        image = sitk.ReadImage(path)
        # GetArrayFromImage returns (z, y, x); spacing is (x, y, z). Reverse the
        # spacing to match, or every surface distance is silently wrong along
        # the anisotropic axis -- which for cardiac CT is the one that matters.
        array = sitk.GetArrayFromImage(image)
        spacing = tuple(reversed(image.GetSpacing()))
        return array, spacing
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _structureNames():
    from .settings import getProject

    return [s.name for s in getProject().segments]


def scoreGold(submission):
    """Score a gold submission against its expert reference.

    Returns the ``segtrain.metrics.agreement`` dict, or None when the case has
    no reference on file -- which is a data problem worth logging, not a crash.
    """
    from segtrain.metrics import agreement

    case = Case().load(submission['caseId'], force=True)
    if case is None or not case.get('goldFileId'):
        logger.warning('submission %s is marked gold but its case has no '
                       'reference segmentation', submission['_id'])
        return None

    reference = File().load(case['goldFileId'], force=True)
    submitted = File().load(submission['fileId'], force=True)
    if reference is None or submitted is None:
        return None

    refLabels, spacing = _readLabels(reference)
    subLabels, _ = _readLabels(submitted)
    if refLabels.shape != subLabels.shape:
        logger.warning('submission %s has shape %s against reference %s',
                       submission['_id'], subLabels.shape, refLabels.shape)
        return {'error': 'geometry_mismatch', 'mean_dice': 0.0}

    return agreement(subLabels, refLabels, _structureNames(), spacing)


def scoreDuplicate(submission):
    """Score a duplicate against the other annotator's approved work.

    Symmetric: neither annotator is treated as ground truth, because on a
    duplicate pair there is none. Returns None while the partner submission does
    not exist yet -- the second of the pair scores both.
    """
    from segtrain.metrics import agreement

    partner = _partnerSubmission(submission)
    if partner is None:
        return None

    mine, spacing = _readLabels(File().load(submission['fileId'], force=True))
    theirs, _ = _readLabels(File().load(partner['fileId'], force=True))
    if mine.shape != theirs.shape:
        return {'error': 'geometry_mismatch', 'mean_dice': 0.0}

    result = agreement(mine, theirs, _structureNames(), spacing)
    result['partnerSubmissionId'] = str(partner['_id'])
    return result


def _partnerSubmission(submission):
    """The other annotator's submission for the same case, if there is one."""
    for other in Submission().forCase(submission['caseId']):
        if other['_id'] != submission['_id'] and other['userId'] != submission['userId']:
            return other
    return None


def scoreOne(submission, policy=None):
    """Score one submission and record the result. Returns the score or None."""
    policy = policy or getPolicy()
    kind = submission.get('kind', pol.NORMAL)

    if kind == pol.GOLD:
        score = scoreGold(submission)
    elif kind == pol.DUPLICATE:
        score = scoreDuplicate(submission)
    else:
        score = None

    if score is None:
        return None

    mean = score.get('mean_dice')
    threshold = (policy.gold_dice_flag if kind == pol.GOLD
                 else policy.duplicate_dice_flag)
    # A bad automatic score pulls the submission back for a human even if the
    # sampling roll had already let it through. This is the mechanism the whole
    # gold-seeding idea exists for; without it the scores are just a report.
    needsReview = mean is not None and mean < threshold

    Submission().recordScore(submission['_id'], score, needsReview=needsReview)
    if needsReview:
        Assignment().collection.update_one(
            {'_id': submission['assignmentId']},
            {'$set': {'needsReview': True}})
        logger.info('flagged submission %s for review: mean Dice %.3f < %.2f',
                    submission['_id'], mean, threshold)

    _autoApproveIfClear(submission, needsReview)
    return score


def _autoApproveIfClear(submission, needsReview):
    """Finish a scored submission that nobody needs to look at.

    Ordinary submissions are approved in the submit handler; gold and duplicate
    ones wait here, because until the score exists we do not know whether a
    human is needed. Without this they would sit in ``submitted`` forever,
    holding a replica slot and never counting toward completion.
    """
    from segqueue import states as st

    if needsReview:
        return
    assignment = Assignment().load(submission['assignmentId'], force=True)
    if assignment is None or assignment.get('needsReview'):
        return
    if not st.can(assignment['state'], st.APPROVE):
        return
    try:
        Assignment().transition(assignment, st.APPROVE)
    except st.TransitionError:
        return  # a reviewer got there first
    Case().completeSlot(assignment['caseId'])


def runOnce(limit=25):
    """Score every submission waiting for it. Returns how many were scored."""
    policy = getPolicy()
    scored = 0
    for submission in Submission().unscored(limit=limit):
        try:
            if scoreOne(submission, policy) is not None:
                scored += 1
        except Exception:
            # One unreadable file must not stop the queue. It stays unscored and
            # is retried next pass; if it is permanently broken a reviewer sees
            # it as an unscored gold case, which is the right thing to look at.
            logger.exception('failed to score submission %s', submission['_id'])
    return scored


def runForever(pollSeconds=POLL_SECONDS,
               sweepSeconds=SWEEP_SECONDS):  # pragma: no cover - a daemon loop
    """Score continuously, and sweep stranded assignments on the slower beat.

    Both jobs live in one process because both are small, both need the Girder
    models loaded, and a deployment with one background container is meaningfully
    easier for one grad student to keep alive than a deployment with two plus a
    cron entry holding admin credentials.
    """
    logger.info('SegQueue worker started; scoring every %ss, sweeping every %ss',
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
                # A failed sweep is not worth stopping scoring for: the next one
                # is an hour away and finds exactly the same stranded work.
                logger.exception('sweep failed; continuing')
        time.sleep(pollSeconds)


def main(argv=None):  # pragma: no cover - CLI entry point
    import argparse

    parser = argparse.ArgumentParser(
        prog='segqueue-score',
        description='Score gold and duplicate submissions, and reclaim '
                    'assignments whose lease has lapsed.')
    parser.add_argument('--once', action='store_true',
                        help='Do one pass of each job and exit.')
    parser.add_argument('--poll', type=int, default=POLL_SECONDS,
                        help='Seconds between scoring passes in daemon mode.')
    parser.add_argument('--sweep', type=int, default=SWEEP_SECONDS,
                        help='Seconds between lease sweeps in daemon mode.')
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    if args.once:
        print(f'scored {runOnce()} submission(s)')
        print(f'released {len(sweep())} stranded assignment(s)')
        return 0
    runForever(args.poll, args.sweep)
    return 0
