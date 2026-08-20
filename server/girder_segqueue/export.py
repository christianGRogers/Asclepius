"""``segqueue-export`` -- write approved work out in the training layout.

The platform's whole point is to produce training data, and until this existed
it did not: approved submissions sat in the assetstore as integer label volumes
on the source grid -- the right *contents* -- with nothing to turn them into
what ``segtrain convert`` reads.

What it writes, per the README's *Your coronary data*::

    <out>/<case>/ct.nii.gz
    <out>/<case>/segmentations/left_main.nii.gz
    <out>/<case>/segmentations/left_anterior_descending.nii.gz
    ...

**One binary mask per vessel, not a merged ``labels.nii.gz``.** The merged form
cannot distinguish "this vessel was not labelled in this case" from "this vessel
is not present in this patient" -- both are absence of a label value. The
per-vessel form keeps that distinction, and ``segtrain convert`` reports absent
structures per case rather than silently training on a hole.

Two things about the inputs that are easy to get wrong:

* A submission is an **integer label volume**, whatever its filename suffix
  says. Label values come from the ``segqueue.project`` setting and match
  ``configs/labels/coronary.yaml``. Splitting is by value, not by channel.
* The CT written here is the case's **stored** volume, which is the geometry
  corrected one. Going back to the original dataset file would pair labels drawn
  on the corrected grid with an image on the uncorrected one -- and for the ~1 in
  9 obliquely acquired cases those grids differ.

Runs against the models directly rather than over REST, like ``segqueue-ingest``
and for the same reason: the files are already on this disk.
"""

import argparse
import datetime
import os
import sys
import tempfile

from segqueue import states as st

#: Written beside the CT, as ``segtrain convert`` expects.
SEGMENTATIONS_DIR = 'segmentations'


def _models():
    """Girder models, imported on use rather than at module scope.

    Importing ``girder.models`` binds Girder's Mongo connection, and binding it
    is not this module's decision to make on import: the test suite redirects it
    to a scratch database in a fixture, and anything that binds earlier sends
    those tests -- which clear collections -- at the live database instead.
    """
    from girder.models.file import File

    from .models import Assignment, Case, Submission
    return File, Assignment, Case, Submission


def _requireDeps():
    """Import numpy and SimpleITK, naming what to install if they are missing."""
    try:
        import numpy as np
        import SimpleITK as sitk
    except ImportError as exc:  # pragma: no cover - a deployment error
        raise ImportError(
            'segqueue-export needs numpy and SimpleITK. Install the plugin with '
            'its scoring extra:\n    pip install "./server[scoring]"'
        ) from exc
    return np, sitk


def _download(fileDoc, suffix):
    """Girder file -> a temp path, because ITK reads paths, not streams."""
    File = _models()[0]
    handle, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(handle, 'wb') as out:
        for chunk in File().download(fileDoc, headers=False)():
            out.write(chunk)
    return path


def splitLabels(labels, segments):
    """Split an integer label volume into one binary mask per segment.

    Returns ``{name: array}`` covering *every* segment, including those with no
    voxels. An empty mask and a missing file mean different things downstream --
    "the annotator drew nothing here" versus "this case was never labelled for
    this structure" -- so the caller decides what to do with empties rather than
    having them silently vanish here.
    """
    np, _ = _requireDeps()
    return {spec.name: (labels == spec.label).astype(np.uint8)
            for spec in segments}


def _writeMask(array, reference, path):
    """Write a binary mask sharing ``reference``'s grid exactly."""
    _, sitk = _requireDeps()
    image = sitk.GetImageFromArray(array)
    # Origin, spacing and direction come from the label volume the annotator
    # drew on. Without this the mask lands at the origin with unit spacing and
    # `segtrain convert` rejects the case for geometry mismatch.
    image.CopyInformation(reference)
    sitk.WriteImage(image, path, True)


def exportCase(case, submission, outRoot, segments, name=None, dryRun=False):
    """Write one case's CT and per-vessel masks. Returns a summary dict.

    ``name`` overrides the output directory, which is how a second approved
    annotation of the same case is written without overwriting the first.
    """
    np, sitk = _requireDeps()
    File = _models()[0]

    caseName = name or case['name']
    target = os.path.join(outRoot, caseName)
    volume = File().load(case['fileId'], force=True) if case.get('fileId') else None
    labelFile = File().load(submission['fileId'], force=True)

    if volume is None or labelFile is None:
        return {'case': caseName, 'error': 'missing_file', 'written': 0}

    if dryRun:
        return {'case': caseName, 'written': len(segments), 'empty': [],
                'dryRun': True}

    os.makedirs(os.path.join(target, SEGMENTATIONS_DIR), exist_ok=True)

    labelPath = _download(labelFile, os.path.splitext(labelFile['name'])[1] or '.nrrd')
    try:
        labelImage = sitk.ReadImage(labelPath)
        labels = sitk.GetArrayFromImage(labelImage)

        empty = []
        for structure, mask in splitLabels(labels, segments).items():
            if not mask.any():
                empty.append(structure)
            _writeMask(mask, labelImage,
                       os.path.join(target, SEGMENTATIONS_DIR, structure + '.nii.gz'))
    finally:
        _unlink(labelPath)

    _writeVolume(volume, os.path.join(target, 'ct.nii.gz'))

    return {'case': caseName, 'written': len(segments), 'empty': empty,
            'shape': tuple(int(n) for n in labels.shape)}


def _writeVolume(fileDoc, destination):
    """The stored CT, as ``ct.nii.gz``.

    Copied byte for byte when it is already gzipped NIfTI, which is the common
    path and cannot perturb the geometry. Anything else is converted through
    ITK, which is what the labels were drawn against anyway.
    """
    _, sitk = _requireDeps()
    File = _models()[0]
    if fileDoc['name'].endswith('.nii.gz'):
        with open(destination, 'wb') as out:
            for chunk in File().download(fileDoc, headers=False)():
                out.write(chunk)
        return

    source = _download(fileDoc, os.path.splitext(fileDoc['name'])[1] or '.nrrd')
    try:
        sitk.WriteImage(sitk.ReadImage(source), destination, True)
    finally:
        _unlink(source)


def _unlink(path):
    try:
        os.unlink(path)
    except OSError:  # pragma: no cover - a temp file we just wrote
        pass


def selectable(includeUnreviewed=False):
    """Assignment states whose submissions are exportable.

    ``approved`` only, by default. ``submitted`` means a reviewer has not looked
    at it -- either it is queued for review or the sampling policy never picked
    it -- and shipping unreviewed work into a training set by default is how a
    dataset quietly acquires whatever a tired undergraduate drew at 2 a.m.
    """
    return [st.APPROVED, st.SUBMITTED] if includeUnreviewed else [st.APPROVED]


def collect(since=None, includeUnreviewed=False, limit=0, replicas='first'):
    """Pair each exportable case with the submission(s) to write for it.

    Yields ``(case, submission, name)``. For a duplicated case there are two
    approved annotations of the same image; ``replicas='first'`` takes the
    earliest decided one and the caller reports the rest, ``replicas='all'``
    writes the others under ``<case>__r2``, ``<case>__r3``. Never silently
    drops one: exporting the same image twice under one name would overwrite,
    and dropping it without a word would hide a disagreement worth seeing.
    """
    _, Assignment, Case, Submission = _models()
    assignments, submissions, cases = Assignment(), Submission(), Case()
    states = selectable(includeUnreviewed)

    query = {'state': {'$in': states}}
    if since is not None:
        query['$or'] = [{'decidedAt': {'$gte': since}},
                        {'submittedAt': {'$gte': since}}]

    byCase = {}
    for assignment in assignments.find(query, sort=[('decidedAt', 1)]):
        byCase.setdefault(assignment['caseId'], []).append(assignment)

    produced = 0
    for caseId, group in byCase.items():
        case = cases.load(caseId, force=True)
        if case is None:
            continue
        for index, assignment in enumerate(group):
            if index and replicas != 'all':
                yield case, None, None      # a replica the caller must report
                continue
            submission = submissions.findOne({'assignmentId': assignment['_id']})
            if submission is None:
                continue
            name = case['name'] if index == 0 else f"{case['name']}__r{index + 1}"
            yield case, submission, name
            produced += 1
            if limit and produced >= limit:
                return


def buildParser():
    parser = argparse.ArgumentParser(
        prog='segqueue-export',
        description='Write approved segmentations out in the layout '
                    '`segtrain convert` reads.')
    parser.add_argument('--out', required=True,
                        help='Directory to write <case>/ct.nii.gz and '
                             '<case>/segmentations/*.nii.gz into.')
    parser.add_argument('--since', default=None,
                        help='Only work decided on or after this date '
                             '(YYYY-MM-DD, or a full ISO timestamp).')
    parser.add_argument('--include-unreviewed', action='store_true',
                        help='Also export submissions no reviewer has approved. '
                             'Off by default.')
    parser.add_argument('--replicas', choices=('first', 'all'), default='first',
                        help='A duplicated case has more than one approved '
                             'annotation. first: write the earliest and report '
                             'the rest. all: write them as <case>__r2 etc.')
    parser.add_argument('--limit', type=int, default=0,
                        help='Stop after this many cases (0 = no limit).')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report what would be written and change nothing.')
    return parser


def _parseSince(text):
    if not text:
        return None
    try:
        stamp = datetime.datetime.fromisoformat(text)
    except ValueError:
        raise SystemExit(f'--since {text!r} is not an ISO date or timestamp.') from None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=datetime.timezone.utc)
    return stamp


def main(argv=None):
    from .settings import getProject

    args = buildParser().parse_args(argv)
    segments = getProject().segments
    if not segments:
        print('The segqueue.project setting defines no segments, so there is '
              'nothing to split a submission into.', file=sys.stderr)
        return 2

    since = _parseSince(args.since)
    if not args.dry_run:
        os.makedirs(args.out, exist_ok=True)

    written = skippedReplicas = failed = 0
    emptyStructures = {}
    verb = 'would export' if args.dry_run else 'exported'

    for case, submission, name in collect(
            since=since, includeUnreviewed=args.include_unreviewed,
            limit=args.limit, replicas=args.replicas):
        if submission is None:
            skippedReplicas += 1
            print(f'  ~ {case["name"]}  [extra approved annotation not exported]')
            continue

        result = exportCase(case, submission, args.out, segments,
                            name=name, dryRun=args.dry_run)
        if result.get('error'):
            failed += 1
            print(f'  ! {result["case"]}  [{result["error"]}]', file=sys.stderr)
            continue

        written += 1
        for structure in result.get('empty', ()):
            emptyStructures[structure] = emptyStructures.get(structure, 0) + 1
        note = f'  [{len(result["empty"])} empty]' if result.get('empty') else ''
        print(f'  + {result["case"]}{note}')

    print(f'\n{verb} {written} case(s) into {args.out}.')
    if emptyStructures:
        print('Structures with no voxels in some cases (absent, not missing): '
              + ', '.join(f'{k} x{v}' for k, v in sorted(emptyStructures.items())))
    if skippedReplicas:
        print(f'{skippedReplicas} additional approved annotation(s) of duplicated '
              'cases were not exported. Pass --replicas all to write them.')
    if failed:
        print(f'{failed} case(s) could not be exported.', file=sys.stderr)
    return 1 if failed else 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
