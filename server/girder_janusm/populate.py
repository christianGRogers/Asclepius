"""``janusm-populate``: create the Janus-M read cases from the JA6 freeze. Copies no CT.

Runs on the server against the database::

    janusm-populate --seeds-dir /path/to/seeds --dry-run
    janusm-populate --seeds-dir /path/to/seeds

1. Loads ``configs/janusm/sealed-r1.json`` through its pin (``janusm.sealed_r1``) and
   plans 100 cases: 40 decision then 60 seal, two reads each, 10 seal cases blank
   (``janusm_reads.readset``).
2. Runs the **JA12 guard** on all of them, under each set's purpose. Any refusal
   stops the whole run before anything is written.
3. Finds each case's CT in ``ImageCAS-X/cases`` (or ``--ct-folder``), by ImageCAS id
   (``c0001`` is ImageCAS 2), and references it by file id. It reads that collection
   and never writes to it.
4. Uploads each seeded case's seed (``<case>.janusm-seed.nii.gz`` from the Fir seed
   job) into ``JanusM/seeds``, and each **blank** case's seed into
   ``JanusM/check-seeds`` as its ``checkSeedFileId`` (JA66): a folder no reader can
   read, used only by the read check to fit the mitral plane. No route serves it. A
   case with no seed stops the run.

Idempotent by case name: a re-run creates only what is missing, and gives an
existing blank case its check seed if it has none.
"""

import argparse
import os

from janusm_reads import holdout, readset

from .constants import CT_COLLECTION_NAME, CT_FOLDER

SEED_SUFFIX = '.janusm-seed.nii.gz'
_VOLUME_SUFFIXES = ('.nii.gz', '.nii', '.nrrd', '.mha')


def _stem(name):
    lower = name.lower()
    for s in _VOLUME_SUFFIXES:
        if lower.endswith(s):
            return lower[: -len(s)]
    return lower


def ctNames(case):
    """Every spelling a CT item of this case may have, lower-case, without extension."""
    n = readset.imagecas_number(case)
    return {f'imagecas__{n:04d}', f'imagecas__{n}', f'imagecas_{n:04d}', f'{n}.img', f'{n}',
            case.lower()}


def ctFolder(folderId=None):
    from girder.models.collection import Collection
    from girder.models.folder import Folder

    if folderId:
        return Folder().load(folderId, force=True)
    collection = Collection().findOne({'name': CT_COLLECTION_NAME})
    if collection is None:
        return None
    return Folder().findOne({'parentId': collection['_id'], 'parentCollection': 'collection',
                             'name': CT_FOLDER})


def _walk(folder):
    from girder.models.folder import Folder
    from girder.models.item import Item

    yield from Item().find({'folderId': folder['_id']})
    for child in Folder().find({'parentId': folder['_id'], 'parentCollection': 'folder'}):
        yield from _walk(child)


def indexCts(folder):
    """``{stem: [item, ...]}`` for every item under ``folder``."""
    out = {}
    for item in _walk(folder):
        out.setdefault(_stem(item['name']), []).append(item)
    return out


def _firstFile(item):
    from girder.models.item import Item

    return next(iter(Item().childFiles(item, limit=1)), None)


def populate(user, seedsDir=None, freezePath=None, ctFolderId=None, dryRun=False,
             hashCts=True, out=print):
    from girder.models.upload import Upload

    from .models import JanusMCase
    from .utils import checkSeedsFolder, ensureGroups, hashStoredFile, seedsFolder

    sets = readset.load_freeze(freezePath)
    plan = readset.plan(sets)
    holdout.refuse_read_cases([p.name for p in plan], sets, what='janusm-populate')

    folder = ctFolder(ctFolderId)
    if folder is None:
        raise SystemExit('REFUSED: no CT folder (ImageCAS-X/cases, or --ct-folder)')
    index = indexCts(folder)

    problems, rows = [], []
    for p in plan:
        seedPath = os.path.join(seedsDir or '', p.name + SEED_SUFFIX)
        hasSeed = bool(seedsDir) and os.path.isfile(seedPath)
        existing = JanusMCase().findOne({'name': p.name})
        if existing:
            if p.blank and not existing.get('checkSeedFileId'):
                if not hasSeed:
                    problems.append(f'{p.name}: no check seed at {seedPath}')
                    continue
                rows.append((p, existing, seedPath, 'attach'))
            else:
                rows.append((p, None, None, 'exists'))
            continue
        hits = [it for key in ctNames(p.name) for it in index.get(key, [])]
        if len(hits) != 1:
            problems.append(f'{p.name}: {len(hits)} CT items match (ImageCAS '
                            f'{readset.imagecas_number(p.name)})')
            continue
        if not hasSeed:
            problems.append(f'{p.name}: no {"check " if p.blank else ""}seed at {seedPath}')
            continue
        rows.append((p, hits[0], seedPath, 'create'))
    for line in problems:
        out(f'  PROBLEM {line}')
    creating = [r for r in rows if r[3] == 'create']
    attaching = [r for r in rows if r[3] == 'attach']
    out(f"{'would create' if dryRun else 'creating'} {len(creating)} cases; "
        f"{len(rows) - len(creating)} exist; {len(problems)} problems; "
        f"blank {sum(1 for r in creating if r[0].blank)}; "
        f"check seeds to attach {len(attaching)}")
    for p, item, _, _ in creating:
        out(f'  {p.name} {p.read_set:8s} {"blank" if p.blank else "seeded"}  CT {item["name"]}')
    if problems:
        raise SystemExit('REFUSED: fix the problems above; nothing was written')
    if dryRun:
        return {'create': len(creating), 'attach': len(attaching), 'problems': problems}

    ensureGroups(user)
    seeds, checkSeeds = seedsFolder(user), checkSeedsFolder(user)

    def upload(path, folder):
        with open(path, 'rb') as handle:
            return Upload().uploadFromFile(
                handle, size=os.path.getsize(path), name=os.path.basename(path),
                parentType='folder', parent=folder, user=user)['_id']

    for p, item, seedPath, _ in creating:
        ctFile = _firstFile(item)
        checksum = hashStoredFile(ctFile) if hashCts else ''
        if p.blank:
            JanusMCase().createCase(p, ctFile, checksum,
                                    checkSeedFileId=upload(seedPath, checkSeeds))
        else:
            JanusMCase().createCase(p, ctFile, checksum, seedFileId=upload(seedPath, seeds))
    for _p, case, seedPath, _ in attaching:
        JanusMCase().collection.update_one(
            {'_id': case['_id'], 'blank': True},
            {'$set': {'checkSeedFileId': upload(seedPath, checkSeeds)}})
    return {'create': len(creating), 'attach': len(attaching), 'problems': []}


def main(argv=None):
    from girder.models.user import User

    parser = argparse.ArgumentParser(prog='janusm-populate', description=__doc__.split('\n\n')[0])
    parser.add_argument('--seeds-dir', help='directory of <case>.janusm-seed.nii.gz')
    parser.add_argument('--freeze', default=None, help='default: the pinned sealed-r1.json')
    parser.add_argument('--ct-folder', default=None, help='default: ImageCAS-X/cases')
    parser.add_argument('--no-hash', action='store_true')
    parser.add_argument('--admin', default=None)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    user = (User().findOne({'login': args.admin}) if args.admin
            else User().findOne({'admin': True}))
    if user is None:
        parser.error('no admin user found')
    populate(user, seedsDir=args.seeds_dir, freezePath=args.freeze,
             ctFolderId=args.ct_folder, dryRun=args.dry_run, hashCts=not args.no_hash)
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
