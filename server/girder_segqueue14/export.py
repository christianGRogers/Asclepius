"""``segqueue14-export`` -- approved SegQueue14 reads, in the training layout.

Adapted from ``girder_segqueue.export``: the same layout and the same manifest,
over SegQueue14's models and its four segments (D25), so ``segtrain convert``
with the ``coronary_icx4`` label set reads the result directly::

    <out>/<case>/ct.nii.gz
    <out>/<case>/segmentations/{LM,LAD,LCx,RCA}.nii.gz

The manifest additionally records each case's prelabel model version, the
provenance a D15 refresh makes necessary.

**Extended reads (D44).** A read with the 17 optional extended classes is written
with every class it has: the four plus ``segmentations/<class>.nii.gz`` for each
extended one (spaces in a name become ``_``: ``Calcified_plaque.nii.gz``). A
four-class read is written as before. ``--four-class`` writes every read as the
four instead, an extended one collapsed first (each branch unioned into its
parent, materials dropped: ``labels.collapse_to_four``) -- what a four-class
training set (D25) wants. The manifest says which was done and lists the extended
reads. In that collapse PDA, PLB and SN go to the vessel they leave, RCA or LCx,
decided from the read by contact (D47 Q1); the manifest counts the components that
touched neither (or both equally) and fell back to RCA.

**Next to each read (D47 Q3):** ``<case>/read.json`` -- the read's classes,
whether it is extended, and the branch groups its annotator marked complete
(``completeGroups``: an empty class in a group listed there means absent; ``null``
when the module did not say, as before 0.20.0), plus, with ``--four-class``, how
its PDA, PLB and SN were assigned (``branchParents``). Original notes follow.

``segqueue-export`` -- write approved work out in the training layout.

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

* A submission from protocol 17 on is a **class stack** (D39,
  ``segqueue14.labelfile``): one 0/1 channel per class, every class whole,
  overlaps included. Each channel is written as that class's mask, as it is --
  two classes that share voxels both keep them here, and ``segtrain convert``
  decides what a training label does with that (#275). An older submission is
  an **integer label volume**, whatever its filename suffix says, in the
  project's label values; it is split by value. The format is read from the
  file's own header.
* The CT written here is the case's **stored** volume, which is the geometry
  corrected one. Going back to the original dataset file would pair labels drawn
  on the corrected grid with an image on the uncorrected one -- and for the ~1 in
  9 obliquely acquired cases those grids differ.

Runs against the models directly rather than over REST, like ``segqueue-ingest``
and for the same reason: the files are already on this disk.

**The annotator benchmark (D43).** Reads of the benchmark case
(``annotator_benchmark_<ImageCAS id>``, ``segqueue14.benchmark``) are never exported:
they measure annotators and are never trained on. There is no option to include
them; the run says how many cases it left out.

**The D27 pool seal.** Reads of the sealed SegQueue14 pool volumes
(``configs/segqueue14/sealed-pool-2026-10.json``, via ``segtrain.pool_seal``) are
left out of every export by default, before any file of theirs is opened, and the
run says how many. ``--acceptance-scoring`` (for acceptance scoring, later) includes
them, and says so; the manifest records the seal's sha256, the mode and the count.
Annotators are unaffected: sealed cases stay in the queue and get their reads (D23).
On a server without a checkout, pass ``--seal-file`` or set ``SEGTRAIN_POOL_SEAL``;
a missing or altered seal file stops the export.
"""

import argparse
import datetime
import json
import os
import socket
import sys
import tempfile

from segqueue import states as st
from segqueue14 import benchmark as sqbench
from segqueue14 import labelfile
from segqueue14 import labels as project_labels

#: Written beside the CT, as ``segtrain convert`` expects.
SEGMENTATIONS_DIR = 'segmentations'
#: Per read, next to ``segmentations/`` (D47 Q3): classes, completeness ticks and,
#: with ``--four-class``, how PDA, PLB and SN were assigned.
READ_INFO = 'read.json'


def _models():
    """Girder models, imported on use rather than at module scope.

    Importing ``girder.models`` binds Girder's Mongo connection, and binding it
    is not this module's decision to make on import: the test suite redirects it
    to a scratch database in a fixture, and anything that binds earlier sends
    those tests -- which clear collections -- at the live database instead.
    """
    from girder.models.file import File

    from .models import Assignment14, Case14, Submission14
    return File, Assignment14, Case14, Submission14


def _requireDeps():
    """Import numpy and SimpleITK, naming what to install if they are missing."""
    try:
        import numpy as np
        import SimpleITK as sitk
    except ImportError as exc:  # pragma: no cover - a deployment error
        raise ImportError(
            'segqueue14-export needs numpy and SimpleITK. Install the plugin with '
            'its scoring extra:\n    pip install "./server/girder_segqueue14[scoring]"'
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


def splitClassStack(path, segments):
    """A class-stack file as ``{name: (mask, grid image)}`` for every segment.

    Each class is its own channel, whole (D39). A segment the file does not name
    gets an empty mask, so a missing class is reported as empty, never dropped.
    """
    np, sitk = _requireDeps()
    data = labelfile.read_class_stack(path)
    grid = sitk.GetImageFromArray(np.zeros(data['masks'].shape[1:], np.uint8))
    grid.SetSpacing(data['spacing'])
    grid.SetOrigin(data['origin'])
    grid.SetDirection(data['direction'])
    byName = {name: index for index, name in enumerate(data['names'])}
    out = {}
    for spec in segments:
        index = byName.get(spec.name)
        mask = (data['masks'][index].astype(np.uint8) if index is not None
                else np.zeros(data['masks'].shape[1:], np.uint8))
        out[spec.name] = (mask, grid)
    return out


def classStackAll(path, fourClass=False, stats=None):
    """A class-stack file as ``{name: (mask, grid image)}`` for every class it has.

    The read's own classes (the four, or all 21 for an extended read, D44), in the
    file's order; with ``fourClass`` the four, an extended read collapsed first
    (``stats``, a dict, gets the PDA/PLB/SN assignment: ``labels.collapse_to_four``).
    """
    np, sitk = _requireDeps()
    data = labelfile.read_class_stack(path)
    grid = sitk.GetImageFromArray(np.zeros(data['masks'].shape[1:], np.uint8))
    grid.SetSpacing(data['spacing'])
    grid.SetOrigin(data['origin'])
    grid.SetDirection(data['direction'])
    if fourClass:
        masks = project_labels.collapse_to_four(data['masks'], data['names'], stats=stats)
        names = list(project_labels.NAMES)
    else:
        masks, names = data['masks'], list(data['names'])
    return {name: (masks[i].astype(np.uint8), grid) for i, name in enumerate(names)}


def maskFileName(name):
    """``segmentations/<name>.nii.gz``'s stem: a class name with spaces as ``_``."""
    return str(name).replace(' ', '_').replace('/', '_')


def _writeMask(array, reference, path):
    """Write a binary mask sharing ``reference``'s grid exactly."""
    _, sitk = _requireDeps()
    image = sitk.GetImageFromArray(array)
    # Origin, spacing and direction come from the label volume the annotator
    # drew on. Without this the mask lands at the origin with unit spacing and
    # `segtrain convert` rejects the case for geometry mismatch.
    image.CopyInformation(reference)
    sitk.WriteImage(image, path, True)


def exportCase(case, submission, outRoot, segments, name=None, dryRun=False,
               fourClass=False):
    """Write one case's CT and per-vessel masks. Returns a summary dict.

    ``name`` overrides the output directory, which is how a second approved
    annotation of the same case is written without overwriting the first.
    An extended read (D44) is written with all its classes, or, with
    ``fourClass``, collapsed to the four.
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
    stats = {}
    classes = list(submission.get('classes') or project_labels.NAMES)
    completeGroups = submission.get('completeGroups')
    try:
        if labelfile.sniff(labelPath) == labelfile.FORMAT_CLASS_STACK:
            header = labelfile.read_header(labelPath)
            classes = labelfile.class_names(header) or classes
            # The file is the authority; the row says the same unless it predates D47.
            fromFile = labelfile.complete_groups(header)
            completeGroups = fromFile if fromFile is not None else completeGroups
            if fourClass or project_labels.is_extended(classes):
                masks = classStackAll(labelPath, fourClass=fourClass, stats=stats)
            else:
                masks = splitClassStack(labelPath, segments)
        else:
            labelImage = sitk.ReadImage(labelPath)
            masks = {name: (mask, labelImage) for name, mask in
                     splitLabels(sitk.GetArrayFromImage(labelImage), segments).items()}

        empty = []
        shape = None
        for structure, (mask, grid) in masks.items():
            if not mask.any():
                empty.append(structure)
            shape = mask.shape
            _writeMask(mask, grid, os.path.join(
                target, SEGMENTATIONS_DIR, maskFileName(structure) + '.nii.gz'))
        overlap = labelfile.overlaps([m for m, _ in masks.values()], list(masks))
    finally:
        _unlink(labelPath)

    _writeVolume(volume, os.path.join(target, 'ct.nii.gz'))
    parents = project_labels.contact_summary(stats)
    readInfo = {'classes': classes, 'extended': project_labels.is_extended(classes),
                'completeGroups': completeGroups,
                'written': 'four' if fourClass else 'read'}
    if parents:
        readInfo['branchParents'] = parents
    with open(os.path.join(target, READ_INFO), 'w') as handle:
        json.dump(readInfo, handle, indent=2, sort_keys=True)

    return {'case': caseName, 'written': len(masks), 'empty': empty,
            'extended': project_labels.is_extended(masks),
            'completeGroups': completeGroups,
            'branchParents': parents,
            'overlaps': [list(row) for row in overlap],
            'shape': tuple(int(n) for n in shape) if shape else None}


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


#: The ``name`` ``collect`` yields for a case the D27 pool seal leaves out.
SEALED = object()
#: The ``name`` ``collect`` yields for the annotator benchmark (D43), always left out.
BENCHMARK = object()


def isBenchmark(case):
    """The annotator benchmark case (D43), by its flag or its name."""
    return bool(case.get('benchmark')) or sqbench.is_benchmark_name(case.get('name', ''))


def collect(since=None, includeUnreviewed=False, limit=0, replicas='first', seal=None):
    """Pair each exportable case with the submission(s) to write for it.

    Yields ``(case, submission, name)``. For a duplicated case there are two
    approved annotations of the same image; ``replicas='first'`` takes the
    earliest decided one and the caller reports the rest, ``replicas='all'``
    writes the others under ``<case>__r2``, ``<case>__r3``. Never silently
    drops one: exporting the same image twice under one name would overwrite,
    and dropping it without a word would hide a disagreement worth seeing.

    ``seal`` (a ``segtrain.pool_seal.PoolSeal``): each of its cases is yielded once
    as ``(case, None, SEALED)``, before any submission of it is loaded, and does not
    count towards ``limit``. The annotator benchmark (D43) is yielded the same way,
    as ``(case, None, BENCHMARK)``, always.
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
        if isBenchmark(case):
            yield case, None, BENCHMARK
            continue
        if seal is not None and seal.is_sealed(case['name']):
            yield case, None, SEALED
            continue
        for index, assignment in enumerate(group):
            if index and replicas != 'all':
                yield case, None, None      # a replica the caller must report
                continue
            # Never a read reopened for its annotator's revision (#315).
            submission = submissions.findOne({'assignmentId': assignment['_id'],
                                              'reopenedAt': None})
            if submission is None:
                continue
            name = case['name'] if index == 0 else f"{case['name']}__r{index + 1}"
            yield case, submission, name
            produced += 1
            if limit and produced >= limit:
                return


def _writeManifest(out, cases, segments, args, since):
    """Describe what was just written, so the far end can prove it arrived.

    Hashing is the expensive part of an export -- every byte, once -- and it is
    worth it here rather than later: this is the only moment at which the data and
    the authority on what the data should be are on the same disk. A manifest
    generated at the receiving end certifies whatever arrived, including a
    truncated volume.

    ``segments`` is recorded because a label volume is only interpretable against
    the label set that produced it, and that setting is mutable: a manifest whose
    segment list disagrees with ``configs/labels/`` is the one warning anybody
    will get that a 4-class export is being fed to a 14-class task.
    """
    from segqueue.manifest import build

    def progress(path, index, total):
        if total > 50 and index % 50 == 0:
            print(f'  hashing {index}/{total}', flush=True)

    manifest = build(out, cases=sorted(cases), progress=progress, source={
        'kind': 'segqueue14-export',
        'label_set': project_labels.LABEL_SET_NAME,
        'prelabel_versions': getattr(args, 'prelabelVersions', {}),
        'host': socket.gethostname(),
        'segments': [s.name for s in segments],
        'replicas': args.replicas,
        'include_unreviewed': bool(args.include_unreviewed),
        'since': since.isoformat() if since else None,
        'pool_seal': getattr(args, 'poolSeal', None),
        'annotator_benchmark_excluded': getattr(args, 'benchmarkExcluded', 0),
        # D44: 'read' writes each read's own classes (an extended read has 21);
        # 'four' collapses every read to the four.
        'classes': 'four' if getattr(args, 'four_class', False) else 'read',
        'extended_reads': sorted(getattr(args, 'extendedCases', ())),
        # D47 Q3: per case, the branch groups its annotator marked complete (only
        # reads whose module said; also in <case>/read.json).
        'complete_groups': dict(sorted(getattr(args, 'completeGroups', {}).items())),
        # D47 Q1, --four-class only: PDA/PLB/SN components assigned by contact, and
        # how many touched neither vessel (or both equally) and fell back to RCA.
        'branch_parents': getattr(args, 'branchParents', None),
    })
    return manifest.write(out)


def buildParser():
    parser = argparse.ArgumentParser(
        prog='segqueue14-export',
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
    parser.add_argument('--four-class', action='store_true',
                        help='Write every read as LM, LAD, LCx and RCA only: an '
                             'extended read (D44) is collapsed first, each branch into '
                             'its parent, materials dropped. Default: each read\'s own '
                             'classes.')
    parser.add_argument('--limit', type=int, default=0,
                        help='Stop after this many cases (0 = no limit).')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report what would be written and change nothing.')
    parser.add_argument('--seal-file', default=None,
                        help='The D27 pool seal (configs/segqueue14/sealed-pool-2026-10.json); '
                             'default $SEGTRAIN_POOL_SEAL or the checkout\'s copy. It must be '
                             'the pinned file.')
    parser.add_argument('--acceptance-scoring', action='store_true',
                        help='Include reads of D27 sealed pool volumes, for acceptance '
                             'scoring only. Off by default: they are left out and counted.')
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
        print('The segqueue14.project setting defines no segments, so there is '
              'nothing to split a submission into.', file=sys.stderr)
        return 2

    since = _parseSince(args.since)
    from segtrain.pool_seal import load_pool_seal
    try:
        seal = load_pool_seal(args.seal_file)
    except (OSError, RuntimeError) as exc:
        print(f'D27 pool seal: {exc}', file=sys.stderr)
        return 2
    acceptance = bool(args.acceptance_scoring)
    if acceptance:
        print('ACCEPTANCE SCORING: reads of D27 sealed pool volumes are included.')
    if not args.dry_run:
        os.makedirs(args.out, exist_ok=True)

    written = skippedReplicas = failed = sealedExcluded = sealedIncluded = benchmarks = 0
    emptyStructures = {}
    overlapping = []
    exportedCases = []
    extendedCases = []
    args.extendedCases = extendedCases
    prelabelVersions = {}
    args.prelabelVersions = prelabelVersions
    completeGroups = {}
    args.completeGroups = completeGroups
    parents = {'components': 0, 'toLCx': 0, 'fallback': 0, 'fallbackCases': []}
    args.branchParents = parents if args.four_class else None
    verb = 'would export' if args.dry_run else 'exported'

    for case, submission, name in collect(
            since=since, includeUnreviewed=args.include_unreviewed,
            limit=args.limit, replicas=args.replicas,
            seal=None if acceptance else seal):
        if name is SEALED:
            sealedExcluded += 1
            continue
        if name is BENCHMARK:
            benchmarks += 1
            continue
        if submission is None:
            skippedReplicas += 1
            print(f'  ~ {case["name"]}  [extra approved annotation not exported]')
            continue

        result = exportCase(case, submission, args.out, segments,
                            name=name, dryRun=args.dry_run, fourClass=args.four_class)
        if result.get('error'):
            failed += 1
            print(f'  ! {result["case"]}  [{result["error"]}]', file=sys.stderr)
            continue

        written += 1
        if acceptance and seal.is_sealed(case['name']):
            sealedIncluded += 1
        exportedCases.append(result['case'])
        if result.get('extended'):
            extendedCases.append(result['case'])
        prelabelVersions[result['case']] = submission.get('prelabelVersion') or ''
        if result.get('completeGroups') is not None:
            completeGroups[result['case']] = result['completeGroups']
        if result.get('branchParents'):
            bp = result['branchParents']
            parents['components'] += bp['components']
            parents['toLCx'] += bp['byParent'].get('LCx', 0)
            parents['fallback'] += bp['fallback']
            if bp['fallback']:
                parents['fallbackCases'].append(result['case'])
        for structure in result.get('empty', ()):
            emptyStructures[structure] = emptyStructures.get(structure, 0) + 1
        note = f'  [{len(result["empty"])} empty]' if result.get('empty') else ''
        if result.get('overlaps'):
            # Kept whole (D39): every class has all its voxels in its own file.
            overlapping.append(result['case'])
            note += '  [classes overlap: ' + ', '.join(
                f'{a}/{b} {n}' for a, b, n in result['overlaps']) + ']'
        print(f'  + {result["case"]}{note}')

    args.poolSeal = {'sha256': seal.sha256,
                     'mode': 'acceptance' if acceptance else 'exclude',
                     'excluded_cases': sealedExcluded, 'included_reads': sealedIncluded}
    args.benchmarkExcluded = benchmarks
    print(f'\n{verb} {written} case(s) into {args.out}.')
    if extendedCases:
        print(f'{len(extendedCases)} read(s) with extended classes (D44) written with all '
              'their classes; --four-class collapses them to LM/LAD/LCx/RCA.')
    elif args.four_class:
        print('--four-class: every read written as LM, LAD, LCx and RCA (extended reads '
              'collapsed, D44).')
    if args.four_class and parents['components']:
        print(f"PDA/PLB/SN (D47): {parents['components']} component(s) put in the vessel "
              f"they leave, {parents['toLCx']} of them LCx; {parents['fallback']} touched "
              'neither vessel (or both equally) and went to RCA'
              + (f" ({', '.join(parents['fallbackCases'])})" if parents['fallback'] else '')
              + '.')
    if benchmarks:
        print(f'{benchmarks} annotator benchmark case(s) left out (D43; never trained on).')
    if acceptance:
        print(f'ACCEPTANCE SCORING: {sealedIncluded} read(s) of D27 sealed pool volumes '
              'included.')
    else:
        print(f'{sealedExcluded} D27 sealed pool case(s) left out (seal {seal.sha256[:12]}); '
              '--acceptance-scoring includes them, for acceptance scoring only.')

    if written and not args.dry_run:
        path = _writeManifest(args.out, exportedCases, segments, args, since)
        print(f'Wrote {path} -- {len(exportedCases)} case(s) with a SHA-256 each.')
        print('It travels with the data. `segtrain fetch` checks arrivals against '
              'it, and `segtrain verify` re-checks any copy at any time.')
    if emptyStructures:
        print('Structures with no voxels in some cases (absent, not missing): '
              + ', '.join(f'{k} x{v}' for k, v in sorted(emptyStructures.items())))
    if overlapping:
        print(f'{len(overlapping)} case(s) have classes that share voxels; each class '
              'was written whole (D39). How a training label treats them is '
              '`segtrain convert`\'s overlap policy (#275).')
    if skippedReplicas:
        print(f'{skippedReplicas} additional approved annotation(s) of duplicated '
              'cases were not exported. Pass --replicas all to write them.')
    if failed:
        print(f'{failed} case(s) could not be exported.', file=sys.stderr)
    return 1 if failed else 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
