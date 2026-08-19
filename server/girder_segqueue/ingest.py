"""``segqueue-ingest`` -- load a directory of volumes into the case pool.

Runs on the server, against the database directly rather than over REST. For
5,000 cases that is not an optimisation so much as the difference between a
coffee break and an afternoon: the REST path would re-authenticate, re-serialise
and re-validate every one of them, and the files are already on the same disk.

Idempotent by case name. Re-running after a partial import picks up where it
stopped instead of creating a second copy of everything, which matters because a
1.5 TB import is exactly the kind of job that gets interrupted.

Two layouts, and the default is the interesting one:

``--layout totalsegmentator`` (default)
    A TotalSegmentator-style tree (the Zenodo release this project uses, see
    ``segqueue.dataset.ZENODO_URL``): ``<root>/<case>/ct.nii.gz`` beside a
    ``segmentations/`` directory of per-structure masks. Because every case
    arrives presegmented, two things fall out for free:

    * **Only cases with a heart are ingested.** TotalSegmentator is whole-body
      and most of it is legs, heads and abdomens with no coronary anatomy in the
      field of view. Assigning those wastes the scarce resource -- annotator
      hours -- so a case with no heart structure is skipped.
    * **A case that already has a coronary mask ships it to the annotator.** The
      mask is a binary lumen, not per-branch labels, so it is a head start
      rather than an answer: the extension loads it as a helper segment and the
      annotator splits it into LM / LAD / LCx / RCA.

``--layout flat``
    Any directory of volume files, one case per file, no masks. What you use for
    a bring-your-own CCTA tree.
"""

import argparse
import os
import sys

from girder.models.assetstore import Assetstore
from girder.models.upload import Upload
from girder.models.user import User
from segqueue import dataset
from segqueue.checksum import sha256_file

from .models import Case
from .utils import casesFolder, goldFolder

#: What a volume can arrive as in the flat layout. DICOM directories are not
#: handled here -- convert them to NRRD or NIfTI first, which is a decision the
#: protocol should make once rather than leaving thirty annotators to Slicer's
#: DICOM import dialogue.
VOLUME_SUFFIXES = ('.nrrd', '.nhdr', '.nii', '.nii.gz', '.mha', '.mhd')


def caseNameFor(path):
    """Strip directories and every known suffix. ``s0042.nii.gz`` -> ``s0042``."""
    name = os.path.basename(path)
    for suffix in sorted(VOLUME_SUFFIXES, key=len, reverse=True):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return os.path.splitext(name)[0]


def findVolumes(root):
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in sorted(filenames):
            if filename.lower().endswith(VOLUME_SUFFIXES):
                yield os.path.join(dirpath, filename)


def flatCases(root, goldRoot=None):
    """The flat layout as ``CaseFiles``, so both layouts share one ingest path."""
    for path in findVolumes(root):
        name = caseNameFor(path)
        yield dataset.CaseFiles(name=name, volume=path,
                                gold=dataset.find_gold(name, goldRoot))


def uploadFile(path, folder, user, assetstore=None):
    """Stream a file into Girder's assetstore and return the file document."""
    size = os.path.getsize(path)
    with open(path, 'rb') as handle:
        return Upload().uploadFromFile(
            handle, size=size, name=os.path.basename(path),
            parentType='folder', parent=folder, user=user,
            assetstore=assetstore,
        )


def ingestOne(caseFiles, user, folder, priority=0, target='',
              replicasWanted=1, withRegion=True, withSeed=True, dryRun=False):
    """Register one case. Returns ``(case, created)``.

    The checksum is computed here, once, from the file on disk, and every later
    transfer of this case is verified against it. Computing it at ingest rather
    than at first download means a file that was already corrupt on arrival is
    caught by the first annotator rather than blamed on their connection.

    Only the CT is checksummed. The helper masks are aids, never submitted and
    never scored, so a corrupt one costs an annotator a puzzled moment rather
    than corrupting the dataset -- not worth an extra full read of every file in
    a 1.5 TB import.
    """
    existing = Case().findOne({'name': caseFiles.name})
    if existing is not None:
        return existing, False
    if dryRun:
        return {'name': caseFiles.name,
                'sizeBytes': os.path.getsize(caseFiles.volume)}, True

    checksum = sha256_file(caseFiles.volume)
    volume = uploadFile(caseFiles.volume, folder, user)

    regionFileId = seedFileId = goldFileId = None
    if withRegion and caseFiles.region:
        regionFileId = uploadFile(caseFiles.region, folder, user)['_id']
    if withSeed and caseFiles.seed:
        seedFileId = uploadFile(caseFiles.seed, folder, user)['_id']
    if caseFiles.gold:
        goldFileId = uploadFile(caseFiles.gold, goldFolder(user), user)['_id']

    case = Case().createCase(
        name=caseFiles.name, fileId=volume['_id'], checksum=checksum,
        sizeBytes=volume['size'], creator=user, target=target,
        priority=priority, replicasWanted=replicasWanted,
        isGold=bool(goldFileId), goldFileId=goldFileId,
        regionFileId=regionFileId, seedFileId=seedFileId,
    )
    return case, True


def _flags(caseFiles):
    marks = []
    if caseFiles.seed:
        marks.append('coronary seed')
    if caseFiles.region:
        marks.append('heart')
    if caseFiles.gold:
        marks.append('GOLD')
    return f"  [{', '.join(marks)}]" if marks else ''


def buildParser():
    parser = argparse.ArgumentParser(
        prog='segqueue-ingest',
        description='Load CT volumes into the SegQueue case pool.',
        epilog=f'Default source dataset: {dataset.ZENODO_URL}')
    parser.add_argument('--root', required=True,
                        help='Directory to scan. For the totalsegmentator '
                             'layout this holds one subdirectory per case.')
    parser.add_argument('--layout', choices=('totalsegmentator', 'flat'),
                        default='totalsegmentator',
                        help='totalsegmentator: <case>/ct.nii.gz plus a '
                             'segmentations/ directory (default). '
                             'flat: a directory of volume files.')
    parser.add_argument('--all-cases', action='store_true',
                        help='Ingest cases with no heart segmentation too. Off '
                             'by default: most of a whole-body dataset has no '
                             'coronary anatomy in the field of view at all.')
    parser.add_argument('--no-seed', action='store_true',
                        help='Do not ship pre-existing coronary masks to '
                             'annotators. Use this if you want every tree drawn '
                             'from scratch, e.g. to measure unaided time.')
    parser.add_argument('--no-region', action='store_true',
                        help='Do not ship heart masks. The extension then '
                             'cannot frame the view on the heart.')
    parser.add_argument('--gold-root', default=None,
                        help='Directory of expert per-branch references. A '
                             'volume with a matching case name here registers '
                             'that case as a gold seed.')
    parser.add_argument('--admin', default=None,
                        help='Login of the Girder user to own the uploads. '
                             'Defaults to the first site admin.')
    parser.add_argument('--target', default='coronary',
                        help='Anatomical target recorded on each case.')
    parser.add_argument('--priority', type=int, default=0,
                        help='Higher priority cases are served first.')
    parser.add_argument('--replicas', type=int, default=1,
                        help='How many independent annotations each case wants.')
    parser.add_argument('--limit', type=int, default=0,
                        help='Stop after this many new cases (0 = no limit).')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report what would be ingested and change nothing.')
    return parser


def main(argv=None):
    parser = buildParser()
    args = parser.parse_args(argv)

    if not os.path.isdir(args.root):
        parser.error(f'--root {args.root} is not a directory')

    user = (User().findOne({'login': args.admin}) if args.admin
            else User().findOne({'admin': True}))
    if user is None:
        parser.error('no admin user found; create one through the web UI first')

    if not args.dry_run and Assetstore().findOne() is None:
        parser.error('Girder has no assetstore configured; create one in the '
                     'admin console before ingesting.')

    if args.layout == 'totalsegmentator':
        summary = dataset.scan_summary(args.root, args.gold_root)
        print(f'Scanned {args.root}\n'
              f'  {summary["cases"]} case(s) with a CT\n'
              f'  {summary["with_heart"]} with a heart segmentation, '
              f'{summary["without_heart"]} without\n'
              f'  {summary["with_coronary_seed"]} with a pre-existing coronary mask\n'
              f'  {summary["with_gold"]} with an expert reference\n')
        if summary['cases'] and not summary['with_heart']:
            print('None of these cases has a heart segmentation. If this tree '
                  'is not a TotalSegmentator-style layout, try --layout flat.\n')
        cases = dataset.find_cases(args.root, requireHeart=not args.all_cases,
                                   goldRoot=args.gold_root)
    else:
        cases = flatCases(args.root, args.gold_root)

    folder = casesFolder(user) if not args.dry_run else None
    created = skipped = 0
    seeded = withHeart = goldCount = 0

    for caseFiles in cases:
        case, isNew = ingestOne(
            caseFiles, user, folder, priority=args.priority, target=args.target,
            replicasWanted=args.replicas,
            withRegion=not args.no_region, withSeed=not args.no_seed,
            dryRun=args.dry_run)
        if not isNew:
            skipped += 1
            continue

        created += 1
        seeded += 1 if (caseFiles.seed and not args.no_seed) else 0
        withHeart += 1 if caseFiles.region else 0
        goldCount += 1 if caseFiles.gold else 0
        print(f'  + {case["name"]}{_flags(caseFiles)}')
        if args.limit and created >= args.limit:
            break

    verb = 'would ingest' if args.dry_run else 'ingested'
    print(f'\n{verb} {created} case(s): {withHeart} with a heart mask, '
          f'{seeded} with a coronary head start, {goldCount} gold. '
          f'{skipped} already present.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
