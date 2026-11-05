"""The Python half of the hourly janus backup (D42, issue #283).

``segqueue-backup.sh`` (beside this file) is the job systemd runs; it calls this
for the parts that need the database or are easier to get right in Python:

    guard   --min-free-mb N PATH...          refuse (exit 3) if any PATH's disk is short
    dump    --out DIR                         database + the list of files to back up
    verify  --dump DIR --restored ROOT        the restore drill's checks
    age     (restic snapshots --json on stdin) how old the newest snapshot is

What is backed up (the lead's decision on #283): the whole Girder database, plus
every assetstore file that belongs to a submission or a reviewer's revision,
found **through the database** (``segqueue14_submission.fileId`` -> ``file`` ->
its assetstore's root). Seeds, prelabels and reference labels are included too
when they are small (``--max-extra-mb``). CT volumes never are: a case's
``fileId`` and ``regionFileId`` are excluded even if something else points at
them, and so is anything filed under the CCTA-Pool or ImageCAS-X collections.

Read-only on the live system: the database is read with ordinary queries (no fsync
lock), nothing is written to Mongo or the assetstore. The dump is
uncompressed BSON in mongodump's layout (``mongorestore --dir`` restores it),
each collection in ``_id`` order, so an hour in which a collection did not
change produces the same bytes and restic stores nothing new for it.

Runs with the live venv's Python (pymongo is a Girder dependency). The pymongo
imports are inside the functions so ``guard`` and ``age`` -- and the unit tests
-- need nothing beyond the standard library.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
from typing import Dict, Iterable, List, Optional, Tuple

#: Never backed up, whatever points at them: the CT pool lives elsewhere (D42).
EXCLUDED_COLLECTIONS = ('CCTA-Pool', 'ImageCAS-X')

#: Submission collections: SegQueue14's, and the retired 4-class queue's (D36
#: kept its collections; its submissions are annotators' work too).
SUBMISSION_COLLECTIONS = (
    ('segqueue14_submission', 'submission'),
    ('segqueue_submission', 'old-submission'),
)

#: Case fields that point at small label files (seeds, prelabels, references).
EXTRA_CASE_FIELDS = (
    ('seedFileId', 'seed'),
    ('prelabelFileId', 'prelabel'),
    ('referenceFileId', 'reference'),
)

#: Case fields that point at CT images. Excluded, always.
CT_CASE_FIELDS = ('fileId', 'regionFileId')
CASE_COLLECTIONS = ('segqueue14_case', 'segqueue_case')

FILESYSTEM_ASSETSTORE = 0
SHA256 = re.compile(r'^[0-9a-f]{64}$')

EXIT_MISSING = 2   # backed up, but some referenced files could not be found
EXIT_GUARD = 3     # refused: not enough free disk


def log(msg: str) -> None:
    print('[backup] ' + msg, flush=True)


# ------------------------------------------------------------------ space guard

def short_of_space(paths: Iterable[str], min_free_mb: int, usage=shutil.disk_usage
                   ) -> List[Tuple[str, int]]:
    """``(path, free_mb)`` for each path whose filesystem has less than the floor."""
    short = []
    for path in paths:
        probe = path
        while probe and not os.path.exists(probe):   # a dir not made yet: its parent's disk
            probe = os.path.dirname(probe.rstrip('/')) or '/'
        free_mb = usage(probe or '/').free // (1024 * 1024)
        if free_mb < min_free_mb:
            short.append((path, free_mb))
    return short


# ------------------------------------------------------------------ the dump

def _ids(values) -> Iterable:
    for value in values:
        if value is not None and value != '':
            yield value


def _excluded_folder_roots(db) -> list:
    return [c['_id'] for c in db['collection'].find(
        {'name': {'$in': list(EXCLUDED_COLLECTIONS)}}, {'_id': 1})]


def select_files(db, max_extra_bytes: Optional[int]) -> Dict:
    """Which assetstore files go into the snapshot, found through the database.

    Returns ``{'files': [...], 'missing': [...], 'skipped': [...], 'excludedCt': n}``.
    Each file entry: ``id, kind, path, size, sha256`` (sha256 from the submission
    row, which the server computed over the stored bytes; '' when unknown).
    """
    names = set(db.list_collection_names())

    ct_ids = set()
    for coll in CASE_COLLECTIONS:
        if coll in names:
            for case in db[coll].find({}, {f: 1 for f in CT_CASE_FIELDS}):
                ct_ids.update(_ids(case.get(f) for f in CT_CASE_FIELDS))

    wanted = {}   # fileId -> (kind, sha256, isExtra)
    for coll, kind in SUBMISSION_COLLECTIONS:
        if coll not in names:
            continue
        for row in db[coll].find({}, {'fileId': 1, 'checksum': 1, 'authorRole': 1}):
            if not row.get('fileId'):
                continue
            k = 'revision' if row.get('authorRole') == 'reviewer' else kind
            checksum = str(row.get('checksum') or '').lower()
            wanted[row['fileId']] = (k, checksum if SHA256.match(checksum) else '', False)

    if max_extra_bytes is None or max_extra_bytes > 0:
        for coll in CASE_COLLECTIONS:
            if coll not in names:
                continue
            fields = {f: 1 for f, _ in EXTRA_CASE_FIELDS}
            fields['prelabelHistory'] = 1
            for case in db[coll].find({}, fields):
                for field, kind in EXTRA_CASE_FIELDS:
                    fid = case.get(field)
                    if fid and fid not in wanted:
                        wanted[fid] = (kind, '', True)
                for old in case.get('prelabelHistory') or []:
                    fid = old.get('prelabelFileId') if isinstance(old, dict) else None
                    if fid and fid not in wanted:
                        wanted[fid] = ('prelabel', '', True)

    excluded_roots = _excluded_folder_roots(db)
    assetstores = {a['_id']: a for a in db['assetstore'].find({})}
    out = {'files': [], 'missing': [], 'skipped': [], 'excludedCt': 0}
    for fid, (kind, sha, extra) in wanted.items():
        if fid in ct_ids:
            out['excludedCt'] += 1
            continue
        doc = db['file'].find_one({'_id': fid})
        entry = {'id': str(fid), 'kind': kind}
        if doc is None:
            out['missing'].append(dict(entry, reason='no file document'))
            continue
        if excluded_roots and doc.get('itemId'):
            item = db['item'].find_one({'_id': doc['itemId']}, {'baseParentId': 1})
            if item and item.get('baseParentId') in excluded_roots:
                out['excludedCt'] += 1
                continue
        size = int(doc.get('size') or 0)
        if extra and max_extra_bytes is not None and size > max_extra_bytes:
            out['skipped'].append(dict(entry, size=size, reason='larger than --max-extra-mb'))
            continue
        path, why = file_path(doc, assetstores)
        if path is None:
            out['missing'].append(dict(entry, reason=why))
            continue
        if not os.path.isfile(path):
            out['missing'].append(dict(entry, path=path, reason='not on disk'))
            continue
        out['files'].append(dict(entry, path=path, size=size, sha256=sha))
    out['files'].sort(key=lambda f: f['path'])
    return out


def file_path(doc: dict, assetstores: dict) -> Tuple[Optional[str], str]:
    """The absolute path of a Girder file on disk, or ``(None, why)``."""
    if doc.get('linkUrl'):
        return None, 'a link, not a stored file'
    store = assetstores.get(doc.get('assetstoreId'))
    if store is None:
        return None, 'unknown assetstore'
    if store.get('type') != FILESYSTEM_ASSETSTORE:
        return None, f"not a filesystem assetstore (type {store.get('type')})"
    path = doc.get('path') or ''
    if not path:
        return None, 'no path'
    if doc.get('imported') or os.path.isabs(path):
        return os.path.normpath(path), ''
    return os.path.normpath(os.path.join(store['root'], path)), ''


def dump_database(db, target: str) -> Dict[str, int]:
    """mongodump's layout, uncompressed, each collection in ``_id`` order."""
    from bson import encode
    from bson.json_util import dumps

    os.makedirs(target, exist_ok=True)
    counts = {}
    for name in sorted(db.list_collection_names()):
        if name.startswith('system.'):
            continue
        n = 0
        with open(os.path.join(target, name + '.bson'), 'wb') as handle:
            for doc in db[name].find({}).sort('_id', 1):
                handle.write(encode(doc))
                n += 1
        indexes = [dict(v, key=dict(v['key']), name=k)
                   for k, v in db[name].index_information().items()]
        with open(os.path.join(target, name + '.metadata.json'), 'w') as handle:
            handle.write(dumps({'indexes': indexes, 'collectionName': name}))
        counts[name] = n
    return counts


def dump(uri: str, out: str, max_extra_bytes: Optional[int]) -> int:
    """Write ``out/`` (database, ``manifest.json``, ``files.txt``) atomically.

    Database first, files list second -- but both from the same moment, before
    restic reads a byte, so every file the dumped database refers to is already
    on disk when restic gets to it (files are write-once). A submission that
    lands mid-run is in the next hour's snapshot.
    """
    from pymongo import MongoClient

    client = MongoClient(uri, serverSelectionTimeoutMS=15000)
    db = client.get_default_database()
    tmp = out.rstrip('/') + '.tmp'
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    started = datetime.datetime.now(datetime.timezone.utc)
    counts = dump_database(db, os.path.join(tmp, db.name))
    chosen = select_files(db, max_extra_bytes)
    manifest = {
        'created': started.isoformat(),
        'database': db.name,
        'documents': sum(counts.values()),
        'collections': counts,
        'files': chosen['files'],
        'missing': chosen['missing'],
        'skipped': chosen['skipped'],
        'excludedCt': chosen['excludedCt'],
        'liveUri': _strip_credentials(uri),
    }
    with open(os.path.join(tmp, 'manifest.json'), 'w') as handle:
        json.dump(manifest, handle, indent=1, sort_keys=True)
    with open(os.path.join(tmp, 'files.txt'), 'w') as handle:
        for f in chosen['files']:
            handle.write(f['path'] + '\n')
    shutil.rmtree(out, ignore_errors=True)
    os.rename(tmp, out)

    kinds = {}
    for f in chosen['files']:
        kinds[f['kind']] = kinds.get(f['kind'], 0) + 1
    size_mb = sum(f['size'] for f in chosen['files']) / 1e6
    by_kind = ', '.join(f'{k} {n}' for k, n in sorted(kinds.items())) or 'none'
    log(f"dumped {manifest['documents']} documents from {len(counts)} collections of "
        f"{db.name}; {len(chosen['files'])} files ({size_mb:.1f} MB: {by_kind}); "
        f"CT files excluded: {chosen['excludedCt']}; skipped as too large: "
        f"{len(chosen['skipped'])}; missing: {len(chosen['missing'])}")
    for m in chosen['missing'][:20]:
        log(f"MISSING {m['kind']} {m['id']}: {m['reason']}")
    return EXIT_MISSING if chosen['missing'] else 0


def _strip_credentials(uri: str) -> str:
    return re.sub(r'//[^@/]*@', '//', uri)


# ------------------------------------------------------------------ the restore drill

def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _read_bson(path: str) -> list:
    from bson import decode_file_iter
    if not os.path.exists(path):
        return []
    with open(path, 'rb') as handle:
        return list(decode_file_iter(handle))


def _same_server(a: str, b: str) -> bool:
    def hostport(uri):
        m = re.match(r'^mongodb://(?:[^@/]*@)?([^/?]+)', uri or '')
        hp = (m.group(1) if m else '').lower().replace('localhost', '127.0.0.1')
        return hp if ':' in hp else hp + ':27017'
    return hostport(a) == hostport(b)


def load_into_scratch(dump_db_dir: str, scratch_uri: str, live_uri: str, db_name: str):
    """Load the dumped BSON into a scratch database. Refuses the live server."""
    from pymongo import MongoClient
    if live_uri and _same_server(scratch_uri, live_uri):
        raise SystemExit(f'refusing: the scratch Mongo {_strip_credentials(scratch_uri)} '
                         'is the live server')
    client = MongoClient(scratch_uri, serverSelectionTimeoutMS=15000)
    client.drop_database(db_name)
    db = client[db_name]
    loaded = 0
    for name in sorted(os.listdir(dump_db_dir)):
        if not name.endswith('.bson'):
            continue
        docs = _read_bson(os.path.join(dump_db_dir, name))
        if docs:
            db[name[:-5]].insert_many(docs, ordered=False)
            loaded += len(docs)
    return client, db, loaded


def verify(dump_dir: str, restored_root: str, scratch_uri: str = '', live_uri: str = '',
           scratch_db: str = 'segqueue_backup_restore_test') -> int:
    """Check a restored snapshot: every submission's file is there with its checksum.

    ``dump_dir`` is the restored dump (``manifest.json`` + ``<db>/``). Files were
    backed up at their absolute paths, so the copy of ``/a/b`` is ``restored_root/a/b``.
    With ``scratch_uri`` the database is loaded into a scratch Mongo first (and the
    checks query that), which proves the dump restores; without it they read the
    BSON directly.
    """
    with open(os.path.join(dump_dir, 'manifest.json')) as handle:
        manifest = json.load(handle)
    db_dir = os.path.join(dump_dir, manifest['database'])

    client = None
    if scratch_uri:
        client, sdb, loaded = load_into_scratch(db_dir, scratch_uri, live_uri, scratch_db)
        log(f'loaded {loaded} documents into the scratch database {scratch_db} '
            f"(manifest says {manifest['documents']})")
        problems = [] if loaded == manifest['documents'] else [
            f"scratch database holds {loaded} documents, the dump {manifest['documents']}"]

        def rows(coll):
            return list(sdb[coll].find({}))
    else:
        log('no scratch Mongo: checking the dumped BSON directly')
        problems = []

        def rows(coll):
            return _read_bson(os.path.join(db_dir, coll + '.bson'))

    try:
        files = {f['_id']: f for f in rows('file')}
        stores = {a['_id']: a for a in rows('assetstore')}
        checked = ok = 0
        for coll, _kind in SUBMISSION_COLLECTIONS:
            for sub in rows(coll):
                if not sub.get('fileId'):
                    continue
                checked += 1
                where = f"{coll} {sub['_id']}"
                doc = files.get(sub['fileId'])
                if doc is None:
                    problems.append(f'{where}: no file document')
                    continue
                path, why = file_path(doc, stores)
                if path is None:
                    problems.append(f'{where}: {why}')
                    continue
                copy = os.path.join(restored_root, path.lstrip('/'))
                if not os.path.isfile(copy):
                    problems.append(f'{where}: file not in the snapshot ({path})')
                    continue
                want = str(sub.get('checksum') or '').lower()
                if SHA256.match(want):
                    got = _sha256(copy)
                    if got != want:
                        problems.append(f'{where}: checksum {got}, expected {want}')
                        continue
                ok += 1
        extras = [f for f in manifest['files'] if f['kind'] not in
                  ('submission', 'revision', 'old-submission')]
        for f in extras:
            copy = os.path.join(restored_root, f['path'].lstrip('/'))
            if not os.path.isfile(copy) or os.path.getsize(copy) != f['size']:
                problems.append(f"{f['kind']} {f['id']}: missing or wrong size in the snapshot")
    finally:
        if client is not None:
            client.drop_database(scratch_db)

    log(f'restore test: {ok} of {checked} submission files present with matching '
        f'checksums; {len(extras)} seed/prelabel/reference files checked; '
        f"snapshot of {manifest['created']}")
    for p in problems[:50]:
        log('PROBLEM ' + p)
    if problems:
        log(f'restore test FAILED: {len(problems)} problem(s)')
        return 1
    log('restore test passed')
    return 0


# ------------------------------------------------------------------ snapshot age

def snapshot_age_hours(snapshots_json: str, now: Optional[datetime.datetime] = None
                       ) -> Optional[float]:
    """Age in hours of the newest snapshot in ``restic snapshots --json`` output."""
    snaps = json.loads(snapshots_json or '[]') or []
    if not snaps:
        return None
    newest = max(_parse_time(s['time']) for s in snaps)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return (now - newest).total_seconds() / 3600.0


def _parse_time(text: str) -> datetime.datetime:
    # restic: 2026-11-05T03:00:12.123456789-05:00 (nanoseconds; fromisoformat wants <= 6)
    m = re.match(r'^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?(Z|[+-]\d\d:\d\d)?$', text.strip())
    if not m:
        raise ValueError(f'unrecognised snapshot time {text!r}')
    frac = (m.group(2) or '.0')[:7]
    tz = m.group(3) or '+00:00'
    tz = '+00:00' if tz == 'Z' else tz
    return datetime.datetime.fromisoformat(m.group(1) + frac + tz)


# ------------------------------------------------------------------ command line

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = p.add_subparsers(dest='cmd', required=True)

    g = sub.add_parser('guard', help='refuse if free disk is below the floor')
    g.add_argument('--min-free-mb', type=int, required=True)
    g.add_argument('paths', nargs='+')

    d = sub.add_parser('dump', help='dump the database and list the files to back up')
    d.add_argument('--out', required=True)
    d.add_argument('--uri', default=os.environ.get('GIRDER_MONGO_URI',
                                                   'mongodb://127.0.0.1:27017/girder'))
    d.add_argument('--max-extra-mb', type=float, default=50.0,
                   help='largest seed/prelabel/reference file to include; 0 leaves them out')

    v = sub.add_parser('verify', help='check a restored snapshot')
    v.add_argument('--dump', required=True)
    v.add_argument('--restored', required=True)
    v.add_argument('--scratch-mongo', default='')
    v.add_argument('--live-uri', default=os.environ.get('GIRDER_MONGO_URI', ''))

    a = sub.add_parser('age', help='hours since the newest snapshot (restic JSON on stdin)')
    a.add_argument('--max-hours', type=float, default=2.0)

    args = p.parse_args(argv)
    if args.cmd == 'guard':
        short = short_of_space(args.paths, args.min_free_mb)
        for path, free in short:
            log(f'REFUSED: {path} has {free} MB free, below the {args.min_free_mb} MB '
                'floor; no backup taken')
        return EXIT_GUARD if short else 0
    if args.cmd == 'dump':
        cap = None if args.max_extra_mb < 0 else int(args.max_extra_mb * 1024 * 1024)
        return dump(args.uri, args.out, cap)
    if args.cmd == 'verify':
        return verify(args.dump, args.restored, args.scratch_mongo, args.live_uri)
    if args.cmd == 'age':
        hours = snapshot_age_hours(sys.stdin.read())
        if hours is None:
            log('no snapshots yet')
            return 1
        log(f'newest snapshot is {hours:.1f} hours old (limit {args.max_hours:.1f})')
        return 0 if hours <= args.max_hours else 1
    return 2


if __name__ == '__main__':
    sys.exit(main())
