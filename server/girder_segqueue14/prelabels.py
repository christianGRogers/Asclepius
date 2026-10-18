"""``segqueue14-prelabels`` -- attach a model's predictions (in the project's classes) to cases,
and swap them for a newer model's (D15) where that is still allowed.

Runs on the server, against the database directly, like ``segqueue-ingest``::

    segqueue14-prelabels attach --dir /incoming/prelabels/icx4-v1 \\
        --model-version icx4-v1 --dry-run
    segqueue14-prelabels attach --dir /incoming/prelabels/icx4-v1 \\
        --model-version icx4-v1 --verify-grid
    segqueue14-prelabels status

``--dir`` holds one uint8 NIfTI per case, named by case (``imagecas_0002.nii.gz``)
or by the model's own ``c0001.nii.gz`` (id - 1, as ``trillium/icx14`` writes them);
either maps to the same case. Each file is uploaded into
``SegQueue14/prelabels/<model_version>/<case>.prelabel.nii.gz`` and recorded on the
case with its version. Nothing is ever deleted: a refreshed case keeps its earlier
prelabel in ``prelabelHistory``, and its file stays where it was.

The rules (``segqueue14.plan.prelabel_decision``):

* a case with no prelabel gets one;
* the same version again is skipped, so a re-run after an interruption picks up
  where it stopped;
* a different version **refreshes** the case only if nobody has submitted it,
  nobody has it downloaded and in progress, and it is not a held-out ImageCAS-X
  test case (D16) -- unless ``--include-test``.
"""

import argparse
import os
import sys

from segqueue import states as st
from segqueue14 import labels, nifti
from segqueue14 import plan as sqplan

#: Assignment states in which somebody is working from the prelabel they were
#: served: swapping it under them would change what their read is a correction of.
WORKING_STATES = (st.DOWNLOADED, st.REJECTED)


def _models():
    from .models import Assignment14, Case14, Submission14
    return Assignment14, Case14, Submission14


def counts(case):
    """``(annotator submissions, working assignments)`` for one case."""
    Assignment14, _, Submission14 = _models()
    submissions = Submission14().collection.count_documents(
        {'caseId': case['_id'], 'authorRole': {'$ne': 'reviewer'}})
    working = Assignment14().collection.count_documents(
        {'caseId': case['_id'], 'state': {'$in': list(WORKING_STATES)}})
    return submissions, working


def decide(case, version, includeTest=False):
    submissions, working = counts(case)
    return sqplan.prelabel_decision(case, version, submissions=submissions,
                                    working_assignments=working,
                                    include_test=includeTest)


def itemName(case):
    return f"{case['name']}.prelabel.nii.gz"


def attachFile(case, fileDoc, version, user=None):
    """Move an already-uploaded prelabel into place and point the case at it."""
    from girder.models.item import Item

    from .utils import prelabelsFolder

    _, Case14, _ = _models()
    item = Item().load(fileDoc['itemId'], force=True)
    if item is not None:
        folder = prelabelsFolder(version, user)
        if item.get('folderId') != folder['_id']:
            item = Item().move(item, folder)
        Item().setMetadata(item, {'segqueue14_case': case['name'],
                                  'model_version': version})
    return Case14().setPrelabel(case, fileDoc['_id'], version,
                                attachedBy=(user or {}).get('_id'))


def uploadPrelabel(path, case, version, user):
    """Upload one local prelabel file and attach it. Returns the updated case."""
    from girder.models.upload import Upload

    from .utils import prelabelsFolder

    folder = prelabelsFolder(version, user)
    size = os.path.getsize(path)
    with open(path, 'rb') as handle:
        fileDoc = Upload().uploadFromFile(
            handle, size=size, name=itemName(case), parentType='folder',
            parent=folder, user=user)
    return attachFile(case, fileDoc, version, user)


# ------------------------------------------------------------- validation


def checkLocalFile(path, ctHeader=None):
    """Problems with a prelabel file on disk, or [] if it can be attached.

    Header checks always run (stdlib only). The value range is checked when
    numpy and nibabel are installed (the ``[scoring]`` extra): a value above
    ``labels.N_CLASSES`` (4) is not one of the project's classes and would land in
    no segment.
    """
    problems = []
    try:
        header = nifti.header_from_path(path)
    except (OSError, nifti.NiftiError) as exc:
        return [f'not a readable NIfTI-1 file: {exc}']
    problem = nifti.check_prelabel_header(header)
    if problem:
        problems.append(problem)
    if ctHeader is not None:
        problem = nifti.same_grid(header, ctHeader)
        if problem:
            problems.append(f'not on the CT grid: {problem}')
    try:
        import nibabel as nib
        import numpy as np
    except ImportError:
        return problems
    if not problems:
        values = np.unique(np.asarray(nib.load(path).dataobj))
        bad = [int(v) for v in values if int(v) < 0 or int(v) > labels.N_CLASSES]
        if bad:
            problems.append(f'label values {bad} are outside 0..{labels.N_CLASSES}')
    return problems


def ctHeaderFor(case):
    """The NIfTI header of the case's CT, read from the first few KB in Girder."""
    from girder.models.file import File

    fileDoc = File().load(case['fileId'], force=True)
    if fileDoc is None or not fileDoc.get('name', '').endswith(('.nii', '.nii.gz')):
        return None
    try:
        return nifti.header_from_chunks(File().download(fileDoc, headers=False)())
    except nifti.NiftiError:
        return None


# ---------------------------------------------------------------- the CLI


def findPredictions(directory):
    """``{case name: path}`` for every NIfTI in ``directory`` (not recursive)."""
    found, clashes = {}, []
    for name in sorted(os.listdir(directory)):
        if not name.lower().endswith(('.nii.gz', '.nii')):
            continue
        case = sqplan.case_name_for_prediction(name)
        if case in found:
            clashes.append(f'{name} and {os.path.basename(found[case])} both map to {case}')
            continue
        found[case] = os.path.join(directory, name)
    return found, clashes


def runAttach(directory, version, user, dryRun=False, includeTest=False,
              verifyGrid=False, limit=0, out=print):
    """Attach or refresh every prediction in ``directory``. Returns a summary."""
    _, Case14, _ = _models()
    version = sqplan.validate_model_version(version)
    predictions, clashes = findPredictions(directory)
    summary = {'attach': 0, 'refresh': 0, 'skip': 0, 'invalid': 0, 'no_case': 0,
               'clashes': clashes}
    for clash in clashes:
        out(f'  ! {clash}')
    done = 0
    for caseName, path in sorted(predictions.items()):
        case = Case14().findOne({'name': caseName})
        if case is None:
            summary['no_case'] += 1
            out(f'  ? {caseName}: no SegQueue14 case with that name')
            continue
        decision = decide(case, version, includeTest=includeTest)
        if decision.action == sqplan.SKIP:
            summary['skip'] += 1
            out(f'  = {caseName}: {decision.reason}')
            continue
        problems = checkLocalFile(path, ctHeaderFor(case) if verifyGrid else None)
        if problems:
            summary['invalid'] += 1
            out(f'  ! {caseName}: ' + '; '.join(problems))
            continue
        verb = '+' if decision.action == sqplan.ATTACH else '~'
        if not dryRun:
            updated = uploadPrelabel(path, case, version, user)
            if updated is None:
                summary['skip'] += 1
                out(f'  = {caseName}: changed while attaching; left as it was')
                continue
        summary[decision.action] += 1
        out(f'  {verb} {caseName}: {decision.reason}')
        done += 1
        if limit and done >= limit:
            break
    return summary


def runStatus(out=print):
    _, Case14, _ = _models()
    byVersion = {}
    without = []
    for case in Case14().find({'retired': False}, sort=[('name', 1)]):
        version = case.get('prelabelVersion') or ''
        if not version:
            without.append(case['name'])
        else:
            byVersion[version] = byVersion.get(version, 0) + 1
    for version, n in sorted(byVersion.items()):
        out(f'  {version}: {n} case(s)')
    out(f'  without a prelabel: {len(without)}'
        + (f" (first: {', '.join(without[:5])})" if without else ''))
    return {'byVersion': byVersion, 'without': len(without)}


def buildParser():
    parser = argparse.ArgumentParser(
        prog='segqueue14-prelabels',
        description='Attach model predictions (the project\'s classes) to SegQueue14 cases, or '
                    'refresh them with a newer model (D15). Touches only SegQueue14 '
                    'data; the CT files are never modified.')
    sub = parser.add_subparsers(dest='command', required=True)
    attach = sub.add_parser('attach', help='Attach or refresh prelabels from a directory.')
    attach.add_argument('--dir', required=True,
                        help='Directory of <case>.nii.gz or cNNNN.nii.gz predictions.')
    attach.add_argument('--model-version', required=True,
                        help='Version of the model that produced them, e.g. icx4-v1. '
                             'Becomes the folder name under SegQueue14/prelabels/.')
    attach.add_argument('--include-test', action='store_true',
                        help='Also refresh held-out ImageCAS-X test cases (D16 says '
                             'not to).')
    attach.add_argument('--verify-grid', action='store_true',
                        help="Check each prelabel's grid against its CT's header "
                             '(reads a few KB of each CT from Girder).')
    attach.add_argument('--limit', type=int, default=0)
    attach.add_argument('--admin', default=None,
                        help='Login of the admin who owns the uploads.')
    attach.add_argument('--dry-run', action='store_true',
                        help='Report what would happen and change nothing.')
    sub.add_parser('status', help='Count prelabels by model version.')
    return parser


def main(argv=None):
    parser = buildParser()
    args = parser.parse_args(argv)
    if args.command == 'status':
        runStatus()
        return 0

    from girder.models.user import User

    if not os.path.isdir(args.dir):
        parser.error(f'--dir {args.dir} is not a directory')
    try:
        sqplan.validate_model_version(args.model_version)
    except ValueError as exc:
        parser.error(str(exc))
    user = (User().findOne({'login': args.admin}) if args.admin
            else User().findOne({'admin': True}))
    if user is None:
        parser.error('no admin user found')
    summary = runAttach(args.dir, args.model_version, user, dryRun=args.dry_run,
                        includeTest=args.include_test, verifyGrid=args.verify_grid,
                        limit=args.limit)
    verb = 'would' if args.dry_run else 'did'
    print(f"\n{verb} attach {summary['attach']}, refresh {summary['refresh']}; "
          f"skipped {summary['skip']}, invalid {summary['invalid']}, "
          f"no such case {summary['no_case']}.")
    return 1 if summary['invalid'] or summary['clashes'] else 0


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
