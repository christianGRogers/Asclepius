"""D36: consolidate SegQueue and SegQueue14 on janus into one queue, one group pair
and one collection (issue #124).

Run on the server by ``deploy/segqueue14-deploy.sh``, never by hand from a laptop.
Each subcommand is a dry run unless given ``--apply``, and checks its
preconditions before it touches anything:

``groups [--apply]``
    Delete ``segqueue-annotators`` and ``segqueue-reviewers``. Refuses while the
    old plugin is installed (its ``ensureGroups()`` would bring them back).
``collection --phase move|drop [--apply]``
    ``move``: the old queue's ``gold``, ``incoming`` and ``submissions`` folders go
    to ``SegQueue/_archive-4class/``. ``drop``: remove the empty ``SegQueue14``
    collection. Both refuse once SegQueue14 has a submission or a prelabel.

It touches only the ``SegQueue`` and ``SegQueue14`` collections and the two old
groups. ``CCTA-Pool`` and ``ImageCAS-X`` are out of scope (D36) and never read or
written here.
"""

import argparse
import sys
from importlib import metadata

from .constants import (
    ANNOTATOR_GROUP,
    INCOMING_FOLDER,
    LIVE_COLLECTION_NAME,
    PRELABELS_FOLDER,
    REVIEWER_GROUP,
    SUBMISSIONS_FOLDER,
)

#: The old 4-class plugin's distribution and groups.
OLD_DISTRIBUTION = 'girder-segqueue'
OLD_GROUPS = ('segqueue-annotators', 'segqueue-reviewers')
NEW_GROUPS = (ANNOTATOR_GROUP, REVIEWER_GROUP)

#: The collection SegQueue14 wrote into before D36. Removed once empty.
OLD14_COLLECTION = 'SegQueue14'
#: The old queue's folders inside ``SegQueue``, and where they are archived.
OLD_QUEUE_FOLDERS = ('gold', 'incoming', 'submissions')
ARCHIVE_FOLDER = '_archive-4class'


def log(*parts):
    print('[d36]', *parts, flush=True)


# ------------------------------------------------------------------ guards


def oldPluginInstalled() -> bool:
    try:
        metadata.distribution(OLD_DISTRIBUTION)
    except metadata.PackageNotFoundError:
        return False
    return True


def requireOldPluginOff():
    if oldPluginInstalled():
        raise SystemExit(f'refused: {OLD_DISTRIBUTION} is still installed; run the '
                         '`retire-live` step first (its ensureGroups() would undo this)')


def segqueue14Written() -> dict:
    """What SegQueue14 has written that the collection move must not strand."""
    from girder.models.file import File

    from .models import Case14, Submission14

    prelabelled = Case14().collection.count_documents(
        {'$or': [{'prelabelFileId': {'$ne': None}}, {'prelabelVersion': {'$nin': ['', None]}}]})
    return {
        'submissions': Submission14().collection.count_documents({}),
        'prelabelled cases': prelabelled,
        # Prelabel files themselves, wherever they were uploaded.
        'prelabel files': File().collection.count_documents(
            {'name': {'$regex': r'\.prelabel\.nii\.gz$'}}),
    }


def requireNothingWritten():
    written = segqueue14Written()
    if any(written.values()):
        raise SystemExit('refused: SegQueue14 has already written '
                         + ', '.join(f'{v} {k}' for k, v in written.items() if v)
                         + '; moving its collection now would strand them')
    return written


# ------------------------------------------------------------------ tree helpers


def _collection(name):
    from girder.models.collection import Collection

    return Collection().findOne({'name': name})


def _child(parent, parentType, name):
    from girder.models.folder import Folder

    return Folder().findOne({'parentId': parent['_id'], 'parentCollection': parentType,
                             'name': name})


def _itemsUnder(parent, parentType) -> int:
    """Items anywhere below a collection or folder. Plain queries, no user, so no
    access filtering."""
    from girder.models.folder import Folder
    from girder.models.item import Item

    if parentType == 'folder':
        stack, n = [parent], 0
    else:
        stack, n = list(Folder().find({'parentId': parent['_id'],
                                       'parentCollection': 'collection'})), 0
    while stack:
        folder = stack.pop()
        n += Item().collection.count_documents({'folderId': folder['_id']})
        stack.extend(Folder().find({'parentId': folder['_id'], 'parentCollection': 'folder'}))
    return n


# ------------------------------------------------------------------ groups


def retireGroups(apply=False):
    from girder.models.group import Group
    from girder.models.user import User

    requireOldPluginOff()
    newIds = [g['_id'] for g in Group().find({'name': {'$in': list(NEW_GROUPS)}})]
    for name in OLD_GROUPS:
        group = Group().findOne({'name': name})
        if group is None:
            log(f'group {name}: already gone')
            continue
        members = User().collection.count_documents({'groups': group['_id']})
        notInNew = User().collection.count_documents(
            {'$and': [{'groups': group['_id']}, {'groups': {'$nin': newIds}}]})
        log(f'group {name}: {members} members, {notInNew} of them in neither '
            f'{" nor ".join(NEW_GROUPS)}')
        if apply:
            Group().remove(group)
            log(f'group {name}: deleted')
    left = sorted(g['name'] for g in Group().find({'name': {'$regex': '^segqueue'}}))
    log(f'segqueue groups {"now" if apply else "today"}: {", ".join(left) or "none"}')
    if not apply:
        log('dry run: nothing deleted')
    elif set(left) != set(NEW_GROUPS):
        raise SystemExit(f'expected exactly {", ".join(NEW_GROUPS)}; have {", ".join(left)}')


# ------------------------------------------------------------------ one collection


def consolidateCollection(phase, apply=False):
    from girder.models.collection import Collection
    from girder.models.folder import Folder
    from girder.models.user import User

    requireOldPluginOff()
    written = requireNothingWritten()
    log('SegQueue14 has written: ' + ', '.join(f'{v} {k}' for k, v in written.items()))
    live = _collection(LIVE_COLLECTION_NAME)
    if live is None:
        raise SystemExit(f'refused: no {LIVE_COLLECTION_NAME} collection')
    old14 = _collection(OLD14_COLLECTION)
    if old14 is not None:
        n = _itemsUnder(old14, 'collection')
        if n:
            raise SystemExit(f'refused: {OLD14_COLLECTION} holds {n} items; it should be empty')

    if phase == 'move':
        admin = User().findOne({'admin': True})
        archive = _child(live, 'collection', ARCHIVE_FOLDER)
        for name in OLD_QUEUE_FOLDERS:
            top = _child(live, 'collection', name)
            done = archive is not None and _child(archive, 'folder', name) is not None
            if top is None:
                log(f'{LIVE_COLLECTION_NAME}/{name}: '
                    + ('already archived' if done else 'absent; nothing to move'))
                continue
            if done:
                raise SystemExit(f'refused: both {LIVE_COLLECTION_NAME}/{name} and '
                                 f'{ARCHIVE_FOLDER}/{name} exist')
            log(f'{LIVE_COLLECTION_NAME}/{name} ({_itemsUnder(top, "folder")} items) -> '
                f'{LIVE_COLLECTION_NAME}/{ARCHIVE_FOLDER}/{name}')
            if apply:
                if archive is None:
                    archive = Folder().createFolder(
                        live, ARCHIVE_FOLDER, parentType='collection', public=False,
                        creator=admin, reuseExisting=True,
                        description='The retired 4-class SegQueue queue (girder_segqueue): '
                                    'its gold, incoming and submissions folders, archived '
                                    'by D36. Not served to anyone.')
                Folder().move(top, archive, 'folder')
        # SegQueue14 creates these at the top of SegQueue from now on; a leftover
        # with items in it would be mixed into its data.
        for name in (PRELABELS_FOLDER, SUBMISSIONS_FOLDER, INCOMING_FOLDER):
            clash = _child(live, 'collection', name)
            if clash is not None and (apply or name == PRELABELS_FOLDER):
                n = _itemsUnder(clash, 'folder')
                if n:
                    raise SystemExit(f'refused: {LIVE_COLLECTION_NAME}/{name} exists with {n} '
                                     'items; SegQueue14 would write into it')
        log('moved' if apply else 'dry run: nothing moved')
    elif phase == 'drop':
        if old14 is None:
            log(f'{OLD14_COLLECTION}: already gone')
        else:
            log(f'{OLD14_COLLECTION}: empty; ' + ('removing' if apply else 'would remove'))
            if apply:
                Collection().remove(old14)
    else:
        raise SystemExit(f'unknown phase {phase!r}')
    top = sorted(f['name'] for f in Folder().find(
        {'parentId': live['_id'], 'parentCollection': 'collection'}))
    log(f'{LIVE_COLLECTION_NAME} top level: {", ".join(top)}')
    log(f'collections: {", ".join(sorted(c["name"] for c in Collection().find({})))}')


# ------------------------------------------------------------------ CLI


def buildParser():
    parser = argparse.ArgumentParser(prog='python -m girder_segqueue14.consolidate',
                                     description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    g = sub.add_parser('groups')
    g.add_argument('--apply', action='store_true')
    c = sub.add_parser('collection')
    c.add_argument('--phase', choices=['move', 'drop'], required=True)
    c.add_argument('--apply', action='store_true')
    return parser


def main(argv=None):
    args = buildParser().parse_args(argv)
    if args.command == 'groups':
        retireGroups(apply=args.apply)
    elif args.command == 'collection':
        consolidateCollection(args.phase, apply=args.apply)
    return 0


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
