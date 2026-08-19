"""``segqueue-ingest`` -- load a directory of volumes into the case pool.

Runs on the server, against the database directly rather than over REST. For
5,000 cases that is not an optimisation so much as the difference between a
coffee break and an afternoon: the REST path would re-authenticate, re-serialise
and re-validate every one of them, and the files are already on the same disk.

Idempotent by case name. Re-running after a partial import picks up where it
stopped instead of creating a second copy of everything, which matters because a
1.5 TB import is exactly the kind of job that gets interrupted.
"""

import argparse
import os
import sys

from girder.models.assetstore import Assetstore
from girder.models.upload import Upload
from girder.models.user import User
from segqueue.checksum import sha256_file

from .models import Case
from .utils import casesFolder, goldFolder

#: What a CT volume can arrive as. DICOM directories are not handled here --
#: convert them to NRRD first, which is a decision the protocol should make once
#: rather than leaving thirty annotators to Slicer's DICOM import dialogue.
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


def uploadFile(path, folder, user, assetstore=None):
    """Stream a file into Girder's assetstore and return the file document."""
    size = os.path.getsize(path)
    with open(path, 'rb') as handle:
        return Upload().uploadFromFile(
            handle, size=size, name=os.path.basename(path),
            parentType='folder', parent=folder, user=user,
            assetstore=assetstore,
        )


def ingestOne(path, user, folder, goldPath=None, priority=0, target='',
              replicasWanted=1, dryRun=False):
    """Register one volume. Returns ``(case, created)``.

    The checksum is computed here, once, from the file on disk, and every later
    transfer of this case is verified against it. Computing it at ingest rather
    than at first download means a file that was already corrupt on arrival is
    caught by the first annotator rather than blamed on their connection.
    """
    name = caseNameFor(path)
    existing = Case().findOne({'name': name})
    if existing is not None:
        return existing, False
    if dryRun:
        return {'name': name, 'sizeBytes': os.path.getsize(path)}, True

    checksum = sha256_file(path)
    volume = uploadFile(path, folder, user)

    goldFileId = None
    if goldPath:
        goldFile = uploadFile(goldPath, goldFolder(user), user)
        goldFileId = goldFile['_id']

    case = Case().createCase(
        name=name, fileId=volume['_id'], checksum=checksum,
        sizeBytes=volume['size'], creator=user, target=target,
        priority=priority, replicasWanted=replicasWanted,
        isGold=bool(goldPath), goldFileId=goldFileId,
    )
    return case, True


def goldPathFor(volumePath, goldRoot):
    """Find the expert reference for a volume, by matching case name.

    Gold references live in a parallel directory rather than beside the volumes
    so that a mis-scoped ``--root`` cannot sweep the answers into the case pool
    -- which would hand annotators the segmentation they were meant to produce.
    """
    if not goldRoot:
        return None
    name = caseNameFor(volumePath)
    for suffix in VOLUME_SUFFIXES:
        candidate = os.path.join(goldRoot, name + suffix)
        if os.path.isfile(candidate):
            return candidate
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='segqueue-ingest',
        description='Load CT volumes into the SegQueue case pool.')
    parser.add_argument('--root', required=True,
                        help='Directory to scan for volumes (recursively).')
    parser.add_argument('--gold-root', default=None,
                        help='Directory of expert reference segmentations. A '
                             'volume with a matching name here is registered as '
                             'a gold case.')
    parser.add_argument('--admin', default=None,
                        help='Login of the Girder user to own the uploads. '
                             'Defaults to the first site admin.')
    parser.add_argument('--target', default='',
                        help='Anatomical target recorded on each case.')
    parser.add_argument('--priority', type=int, default=0,
                        help='Higher priority cases are served first.')
    parser.add_argument('--replicas', type=int, default=1,
                        help='How many independent annotations each case wants.')
    parser.add_argument('--limit', type=int, default=0,
                        help='Stop after this many new cases (0 = no limit).')
    parser.add_argument('--dry-run', action='store_true',
                        help='List what would be ingested and change nothing.')
    args = parser.parse_args(argv)

    if not os.path.isdir(args.root):
        parser.error(f'--root {args.root} is not a directory')

    user = (User().findOne({'login': args.admin}) if args.admin
            else User().findOne({'admin': True}))
    if user is None:
        parser.error('no admin user found; create one with `girder-shell` first')

    if not args.dry_run and Assetstore().findOne() is None:
        parser.error('Girder has no assetstore configured; create one in the '
                     'admin console before ingesting.')

    folder = casesFolder(user) if not args.dry_run else None
    created = skipped = 0
    goldCount = 0

    for path in findVolumes(args.root):
        goldPath = goldPathFor(path, args.gold_root)
        case, isNew = ingestOne(
            path, user, folder, goldPath=goldPath, priority=args.priority,
            target=args.target, replicasWanted=args.replicas, dryRun=args.dry_run)
        if isNew:
            created += 1
            goldCount += 1 if goldPath else 0
            print(f'  + {case["name"]}' + ('  [gold]' if goldPath else ''))
        else:
            skipped += 1
        if args.limit and created >= args.limit:
            break

    verb = 'would ingest' if args.dry_run else 'ingested'
    print(f'\n{verb} {created} case(s), {goldCount} with a gold reference; '
          f'{skipped} already present.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
