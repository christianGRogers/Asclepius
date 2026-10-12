"""``segqueue14-populate`` -- create the SegQueue14 case pool, without copying a CT.

Runs on the server against the database, like ``segqueue-ingest``::

    segqueue14-populate --dry-run                 # say what would be created
    segqueue14-populate                           # create the ImageCAS cases
    segqueue14-populate --extra-folder <folderId> --dataset <tag> --dry-run

**From the live SegQueue.** Every live ``imagecas_NNNN`` case becomes a SegQueue14
case of the same name that references the *same CT file id* -- the ~110 GB of
volumes are never copied, moved or modified, and the live case documents are only
read. The heart-region helper is referenced too; the binary coronary seed is not
(D8).

**ImageCAS-X decides the order and the reads** (D11, D14, D16), read from the live
``SegQueue/imagecas-x`` folder:

* references: the ``segmentations`` items (``<id>.coronary.nii.gz``, item metadata
  ``segqueue_case``) become each case's ``referenceFileId``;
* splits: the first source found of (1) ``--splits-dir``, a local directory of
  ImageCAS-X file lists (``train.txt``, ``val.txt``, ``test.txt``, ``exclude.txt``);
  (2) file-list items of those names anywhere under ``imagecas-x``; (3) the
  ``imagecas-x`` folder's metadata (``splits: {train: [...], ...}`` or top-level
  ``train``/``val``/``test``/``exclude`` lists); (4) a ``split`` key in each
  segmentation item's metadata.

Then: train/val cases priority 400 with one read, the unlabelled cases 300 with two,
test cases 100 with one -- and a deterministic 10 % of the ImageCAS-X cases in each
split get a second, blind read. Priorities and the fraction are options.

**New datasets (D17).** ``--extra-folder`` adds every volume item in a Girder folder
(recursively) as a case named ``<dataset>_<item>``, two reads, tagged with
``--dataset``, priority 200 (after the unlabelled ImageCAS cases, before the
held-out test cases). Their CTs are referenced in place too. They are hashed once
here, because the client verifies every download against the case checksum.

Idempotent by case name: a re-run creates only what is missing. ``--update``
also rewrites the order and read counts of existing cases from the current plan,
never lowering a case's reads below what it has already handed out.
"""

import argparse
import sys

from segqueue14 import plan as sqplan

from .constants import (
    ICX_FOLDER,
    ICX_SEGMENTATIONS_FOLDER,
    LIVE_CASE_COLLECTION,
    LIVE_COLLECTION_NAME,
)

VOLUME_SUFFIXES = ('.nii.gz', '.nii', '.nrrd', '.nhdr', '.mha', '.mhd')


# ------------------------------------------------------------- the sources


def liveCases():
    """The live SegQueue's case documents, read-only."""
    from .models import Case14

    collection = Case14().database[LIVE_CASE_COLLECTION]
    return list(collection.find({}, projection={
        'name': 1, 'fileId': 1, 'checksum': 1, 'sizeBytes': 1, 'regionFileId': 1,
        'geometryFixed': 1, 'retired': 1}))


def icxFolder(folderId=None):
    """``SegQueue/imagecas-x`` (or the folder ``--icx-folder`` names), or None."""
    from girder.models.collection import Collection
    from girder.models.folder import Folder

    if folderId:
        return Folder().load(folderId, force=True)

    collection = Collection().findOne({'name': LIVE_COLLECTION_NAME})
    if collection is None:
        return None
    return Folder().findOne({'parentId': collection['_id'], 'parentCollection': 'collection',
                             'name': ICX_FOLDER})


def _childFolders(folder):
    from girder.models.folder import Folder

    return list(Folder().find({'parentId': folder['_id'], 'parentCollection': 'folder'}))


def _walkItems(folder):
    from girder.models.folder import Folder

    for item in Folder().childItems(folder):
        yield folder, item
    for child in _childFolders(folder):
        yield from _walkItems(child)


def _firstFile(item):
    from girder.models.item import Item

    for fileDoc in Item().childFiles(item, limit=1):
        return fileDoc
    return None


def _readText(fileDoc, limit=1 << 20):
    from girder.models.file import File

    data = b''
    for chunk in File().download(fileDoc, headers=False)():
        data += chunk
        if len(data) > limit:
            raise ValueError(f"{fileDoc.get('name')} is larger than a file list can be")
    return data.decode('utf-8', 'replace')


def references(folder):
    """``({case name: reference file id}, {case name: split from item meta}, problems)``."""
    from girder.models.folder import Folder

    refs, metaSplits, problems = {}, {}, []
    if folder is None:
        return refs, metaSplits, ['no SegQueue/imagecas-x folder found']
    segs = Folder().findOne({'parentId': folder['_id'], 'parentCollection': 'folder',
                             'name': ICX_SEGMENTATIONS_FOLDER})
    if segs is None:
        return refs, metaSplits, ['no imagecas-x/segmentations folder found']
    for item in Folder().childItems(segs):
        name = sqplan.case_name_for_reference(item.get('name', ''), item.get('meta'))
        if name is None:
            continue
        fileDoc = _firstFile(item)
        if fileDoc is None:
            problems.append(f"{item['name']}: item has no file")
            continue
        if name in refs:
            problems.append(f"{name}: more than one ImageCAS-X segmentation item")
            continue
        refs[name] = fileDoc['_id']
        split = sqplan.normalise_split((item.get('meta') or {}).get('split'))
        if split:
            metaSplits[name] = split
    return refs, metaSplits, problems


def splitsFromDirectory(directory):
    import os

    lists = {}
    for name in sorted(os.listdir(directory)):
        split = sqplan.split_list_name(name)
        if split:
            with open(os.path.join(directory, name), encoding='utf-8') as handle:
                lists[split] = lists.get(split, '') + '\n' + handle.read()
    return sqplan.splits_from_lists(lists) if lists else {}


def splitsFromGirderLists(folder):
    lists = {}
    for _parent, item in _walkItems(folder):
        split = sqplan.split_list_name(item.get('name', ''))
        if not split:
            continue
        fileDoc = _firstFile(item)
        if fileDoc is not None:
            lists[split] = lists.get(split, '') + '\n' + _readText(fileDoc)
    return sqplan.splits_from_lists(lists) if lists else {}


def splitsFromFolderMeta(folder):
    meta = (folder or {}).get('meta') or {}
    block = meta.get('splits') if isinstance(meta.get('splits'), dict) else meta
    lists = {}
    for key, value in block.items():
        if sqplan.normalise_split(key) is None:
            continue
        if isinstance(value, (list, tuple)):
            value = ' '.join(str(v) for v in value)
        if isinstance(value, str):
            lists[key] = value
    return sqplan.splits_from_lists(lists) if lists else {}


def resolveSplits(folder, splitsDir=None, metaSplits=None):
    """``({imagecas id: split}, source description)`` from the first source found."""
    if splitsDir:
        found = splitsFromDirectory(splitsDir)
        if found:
            return found, f'file lists in {splitsDir}'
    if folder is not None:
        found = splitsFromGirderLists(folder)
        if found:
            return found, 'file-list items under SegQueue/imagecas-x'
        found = splitsFromFolderMeta(folder)
        if found:
            return found, 'SegQueue/imagecas-x folder metadata'
    if metaSplits:
        out = {}
        for name, split in metaSplits.items():
            n = sqplan.imagecas_id(name)
            if n is not None:
                out[n] = split
        if out:
            return out, "segmentation items' split metadata"
    return {}, None


# ------------------------------------------------------------- writing


def applyPlan(plan, serveOrder, source, user, referenceFileId=None, dryRun=False,
              update=False):
    """Create (or with ``update``, re-plan) one case. Returns ``(verb, detail)``."""
    from .models import Case14

    existing = Case14().findOne({'name': plan.name})
    wanted = {'priority': plan.priority, 'serveOrder': serveOrder,
              'replicasWanted': plan.replicas, 'tier': plan.tier,
              'dataset': plan.dataset, 'split': plan.split,
              'blindDuplicate': plan.blind_duplicate,
              'referenceFileId': referenceFileId}
    if existing is None:
        if not dryRun:
            Case14().createCase(
                name=plan.name, fileId=source['fileId'], checksum=source.get('checksum', ''),
                sizeBytes=source.get('sizeBytes', 0), creator=user,
                priority=plan.priority, serveOrder=serveOrder, replicasWanted=plan.replicas,
                tier=plan.tier, dataset=plan.dataset, split=plan.split,
                blindDuplicate=plan.blind_duplicate, referenceFileId=referenceFileId,
                regionFileId=source.get('regionFileId'),
                sourceCaseId=source.get('_id'),
                geometryFixed=bool(source.get('geometryFixed', False)))
        return 'create', ''

    if existing.get('fileId') != source['fileId']:
        return 'conflict', ('exists with a different CT file id; left alone -- '
                            'check which volume this case should serve')
    changed = {k: v for k, v in wanted.items() if existing.get(k) != v}
    if not changed:
        return 'same', ''
    if not update:
        return 'differs', ', '.join(sorted(changed)) + ' differ (use --update)'
    used = int(existing.get('activeCount', 0)) + int(existing.get('approvedCount', 0))
    if 'replicasWanted' in changed and changed['replicasWanted'] < used:
        return 'conflict', (f"would lower reads to {changed['replicasWanted']} but "
                            f'{used} are already out or approved')
    # Raising the reads of a started case is fine (one more annotator gets it);
    # moving it between tiers only changes when its *remaining* reads are served.
    if not dryRun:
        Case14().collection.update_one({'_id': existing['_id']}, {'$set': changed})
    return 'update', ', '.join(sorted(changed))


def populateImagecas(user, splitsDir=None, duplicateFraction=sqplan.DEFAULT_DUPLICATE_FRACTION,
                     priorities=None, dryRun=False, update=False, allowNoSplits=False,
                     icxFolderId=None, out=print):
    """The ImageCAS half. Returns a summary dict."""
    from girder.models.file import File

    folder = icxFolder(icxFolderId)
    refs, metaSplits, refProblems = references(folder)
    splits, source = resolveSplits(folder, splitsDir, metaSplits)
    out(f'ImageCAS-X references: {len(refs)}; splits: '
        + (f'{len(splits)} ids from {source}' if source else 'none found'))
    for problem in refProblems:
        out(f'  ! {problem}')
    if not splits and not allowNoSplits:
        raise SystemExit(
            'No ImageCAS-X split lists were found, so every case would be planned as '
            'unlabelled (two reads, middle of the queue) and the 160 test cases would '
            'not be last. Pass --splits-dir with train.txt/val.txt/test.txt, or '
            '--allow-no-splits if that is really intended.')

    live = {c['name']: c for c in liveCases()}
    retired = sorted(n for n, c in live.items() if c.get('retired'))
    active = {n: c for n, c in live.items() if not c.get('retired')}
    plans, problems = sqplan.plan_imagecas_cases(
        active.keys(), splits, refs.keys(), duplicate_fraction=duplicateFraction,
        priorities=priorities)
    for name in retired:
        problems.append(f'{name}: retired in the live SegQueue; skipped')

    summary = {'create': 0, 'same': 0, 'update': 0, 'differs': 0, 'conflict': 0,
               'skipped': len(problems), 'byTier': {}, 'duplicates': 0, 'missingFile': 0}
    for order, plan in enumerate(plans):
        source = active[plan.name]
        if File().load(source.get('fileId'), force=True) is None:
            summary['missingFile'] += 1
            out(f'  ! {plan.name}: its CT file is missing from Girder; skipped')
            continue
        verb, detail = applyPlan(plan, order, source, user, refs.get(plan.name),
                                 dryRun=dryRun, update=update)
        summary[verb] += 1
        tier = summary['byTier'].setdefault(plan.tier, {'cases': 0, 'reads': 0})
        tier['cases'] += 1
        tier['reads'] += plan.replicas
        summary['duplicates'] += int(plan.blind_duplicate)
        if verb != 'same':
            mark = {'create': '+', 'update': '~', 'differs': '=', 'conflict': '!'}[verb]
            extra = '  [blind duplicate]' if plan.blind_duplicate else ''
            out(f'  {mark} {plan.name}  {plan.tier} p{plan.priority} x{plan.replicas}'
                f'{extra}{"  " + detail if detail else ""}')
    for problem in problems:
        out(f'  - {problem}')
    summary['nextServeOrder'] = len(plans)
    return summary


def extraItems(folderId):
    """Every (item, file) under a Girder folder whose file looks like a volume."""
    from girder.models.folder import Folder

    folder = Folder().load(folderId, force=True)
    if folder is None:
        raise SystemExit(f'--extra-folder {folderId}: no such folder')
    for _parent, item in _walkItems(folder):
        fileDoc = _firstFile(item)
        if fileDoc is not None and fileDoc.get('name', '').lower().endswith(VOLUME_SUFFIXES):
            yield item, fileDoc


def populateExtra(user, folderId, dataset, priority=None, replicas=None, startOrder=0,
                  dryRun=False, update=False, hashFiles=True, out=print):
    """The D17 hook: cases from another dataset's CT items, two reads each."""
    from .utils import hashStoredFile

    summary = {'create': 0, 'same': 0, 'update': 0, 'differs': 0, 'conflict': 0}
    for order, (item, fileDoc) in enumerate(sorted(extraItems(folderId),
                                                   key=lambda p: p[0]['name'])):
        name = sqplan.new_case_name(dataset, item['name'])
        plan = sqplan.plan_new_dataset_case(name, dataset, priority=priority,
                                            replicas=replicas)
        source = {'fileId': fileDoc['_id'], 'sizeBytes': fileDoc.get('size', 0),
                  'checksum': '', '_id': None}
        from .models import Case14

        if Case14().findOne({'name': name}) is None and hashFiles and not dryRun:
            source['checksum'] = hashStoredFile(fileDoc)
        verb, detail = applyPlan(plan, startOrder + order, source, user, None,
                                 dryRun=dryRun, update=update)
        summary[verb] += 1
        if verb != 'same':
            out(f'  {"+" if verb == "create" else "~"} {name}  {dataset} '
                f'p{plan.priority} x{plan.replicas}{"  " + detail if detail else ""}')
    return summary


def buildParser():
    parser = argparse.ArgumentParser(
        prog='segqueue14-populate',
        description='Create SegQueue14 cases that reference the live SegQueue CT files '
                    '(nothing is copied), ordered and replicated from ImageCAS-X.')
    parser.add_argument('--splits-dir', default=None,
                        help='Local directory with ImageCAS-X train.txt / val.txt / '
                             'test.txt / exclude.txt. Default: look in SegQueue/imagecas-x.')
    parser.add_argument('--icx-folder', default=None,
                        help='Girder folder id of the ImageCAS-X folder, if it is not '
                             'SegQueue/imagecas-x.')
    parser.add_argument('--duplicate-fraction', type=float,
                        default=sqplan.DEFAULT_DUPLICATE_FRACTION,
                        help='Fraction of ImageCAS-X cases (per split) given a second, '
                             'blind read. Default 0.10 (D11).')
    for tier, flag in ((sqplan.TIER_ICX_TRAINVAL, '--priority-trainval'),
                       (sqplan.TIER_UNLABELLED, '--priority-unlabelled'),
                       (sqplan.TIER_NEW_DATASET, '--priority-new'),
                       (sqplan.TIER_ICX_TEST, '--priority-test')):
        parser.add_argument(flag, type=int, default=sqplan.DEFAULT_PRIORITIES[tier],
                            dest='p_' + tier.replace('-', '_'),
                            help=f'Priority for {tier} cases (higher is served first). '
                                 f'Default {sqplan.DEFAULT_PRIORITIES[tier]}.')
    parser.add_argument('--extra-folder', action='append', default=[],
                        help='Girder folder id of another dataset\'s CT items (D17). '
                             'Repeatable; needs --dataset.')
    parser.add_argument('--dataset', default=None,
                        help='Dataset tag for --extra-folder cases, e.g. asoca.')
    parser.add_argument('--extra-replicas', type=int, default=None,
                        help='Reads per --extra-folder case. Default 2.')
    parser.add_argument('--skip-imagecas', action='store_true',
                        help='Only add --extra-folder cases.')
    parser.add_argument('--no-hash', action='store_true',
                        help='Do not compute checksums for --extra-folder volumes '
                             '(clients then verify size only).')
    parser.add_argument('--allow-no-splits', action='store_true')
    parser.add_argument('--update', action='store_true',
                        help='Rewrite order and reads of existing SegQueue14 cases.')
    parser.add_argument('--admin', default=None)
    parser.add_argument('--dry-run', action='store_true',
                        help='Report what would be done and change nothing.')
    return parser


def main(argv=None):
    from girder.models.user import User

    parser = buildParser()
    args = parser.parse_args(argv)
    if args.extra_folder and not args.dataset:
        parser.error('--extra-folder needs --dataset')
    user = (User().findOne({'login': args.admin}) if args.admin
            else User().findOne({'admin': True}))
    if user is None:
        parser.error('no admin user found')
    priorities = {tier: getattr(args, 'p_' + tier.replace('-', '_'))
                  for tier in sqplan.DEFAULT_PRIORITIES}

    nextOrder = 0
    if not args.skip_imagecas:
        summary = populateImagecas(
            user, splitsDir=args.splits_dir, duplicateFraction=args.duplicate_fraction,
            priorities=priorities, dryRun=args.dry_run, update=args.update,
            allowNoSplits=args.allow_no_splits, icxFolderId=args.icx_folder)
        verb = 'would create' if args.dry_run else 'created'
        print(f"\n{verb} {summary['create']}, updated {summary['update']}, unchanged "
              f"{summary['same']}, differing {summary['differs']}, conflicts "
              f"{summary['conflict']}, skipped {summary['skipped']}, missing CT "
              f"{summary['missingFile']}; blind duplicates {summary['duplicates']}.")
        for tier, row in sorted(summary['byTier'].items(),
                                key=lambda kv: -priorities.get(kv[0], 0)):
            print(f"  {tier:22s} p{priorities.get(tier)}  {row['cases']} cases, "
                  f"{row['reads']} reads")
        nextOrder = summary['nextServeOrder']
    for folderId in args.extra_folder:
        extra = populateExtra(
            user, folderId, args.dataset, priority=priorities[sqplan.TIER_NEW_DATASET],
            replicas=args.extra_replicas, startOrder=nextOrder, dryRun=args.dry_run,
            update=args.update, hashFiles=not args.no_hash)
        print(f"{args.dataset}: created {extra['create']}, updated {extra['update']}, "
              f"unchanged {extra['same']}, conflicts {extra['conflict']}.")
        nextOrder += sum(extra.values())
    return 0


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
