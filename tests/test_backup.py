"""The hourly janus backup (D42, issue #283): deploy/backup/ and its systemd units.

Unit tests run everywhere. The rest need a MongoDB (SEGQUEUE_TEST_MONGO) and,
for the round trip, restic; the restore drill's scratch database is a second
MongoDB (SEGQUEUE_TEST_SCRATCH_MONGO), because the drill refuses to load a
restore into the server it was taken from. Synthetic data only.
"""

import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP = os.path.join(ROOT, 'deploy', 'backup')
SCRIPT = os.path.join(BACKUP, 'segqueue-backup.sh')
SYSTEMD = os.path.join(ROOT, 'deploy', 'systemd')
WORKFLOW = os.path.join(ROOT, '.github', 'workflows', 'segqueue14-janus.yml')

_spec = importlib.util.spec_from_file_location(
    'segqueue_backup', os.path.join(BACKUP, 'segqueue_backup.py'))
sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sb)

MONGO = os.environ.get('SEGQUEUE_TEST_MONGO', '')
SCRATCH_MONGO = os.environ.get('SEGQUEUE_TEST_SCRATCH_MONGO', '')
RESTIC = shutil.which('restic')
needs_flock = pytest.mark.skipif(not shutil.which('flock'), reason='no flock(1)')


def _run(cmd, env, timeout=300):
    full = dict(os.environ, **env)
    return subprocess.run(['bash', SCRIPT, cmd], env=full, capture_output=True,
                          text=True, timeout=timeout)


def _shell_env(tmp_path, **extra):
    conf = tmp_path / 'conf'
    conf.mkdir(exist_ok=True)
    env = {
        'BACKUP_CONF_DIR': str(conf),
        'BACKUP_ENV': str(conf / 'backup.env'),   # absent: no janus settings leak in
        'BACKUP_STATE': str(tmp_path / 'state'),
        'BACKUP_PYTHON': sys.executable,
        'RESTIC_REPOSITORY': str(tmp_path / 'repo'),
        'RESTIC_CACHE_DIR': str(tmp_path / 'cache'),
        'BACKUP_MIN_FREE_MB': '1',
        'BACKUP_MONGOD': '',
    }
    env.update(extra)
    return env


# ---------------------------------------------------------------- unit: the guard

def test_guard_refuses_below_the_floor():
    usage = lambda path: SimpleNamespace(free=100 * 1024 * 1024)  # noqa: E731
    assert sb.short_of_space(['/a', '/b'], 50, usage=usage) == []
    assert sb.short_of_space(['/a'], 200, usage=usage) == [('/a', 100)]


def test_guard_checks_the_parent_of_a_directory_not_made_yet(tmp_path):
    seen = []

    def usage(path):
        seen.append(path)
        return SimpleNamespace(free=10 ** 12)
    sb.short_of_space([str(tmp_path / 'not' / 'yet')], 1, usage=usage)
    assert seen == [str(tmp_path)]


def test_run_refuses_below_the_floor_before_touching_anything(tmp_path):
    env = _shell_env(tmp_path, BACKUP_MIN_FREE_MB=str(10 ** 12),
                     GIRDER_MONGO_URI='mongodb://127.0.0.1:1/never')
    out = _run('run', env)
    assert out.returncode == 3, out.stdout + out.stderr
    assert 'REFUSED' in out.stdout and 'below the' in out.stdout
    assert not (tmp_path / 'state' / 'dump').exists()
    assert not (tmp_path / 'state' / 'dump.tmp').exists()


@needs_flock
def test_a_run_that_would_overlap_is_skipped(tmp_path):
    env = _shell_env(tmp_path, GIRDER_MONGO_URI='mongodb://127.0.0.1:1/never')
    state = tmp_path / 'state'
    state.mkdir()
    with open(state / 'run.lock', 'w') as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        out = _run('run', env, timeout=30)
    assert out.returncode == 0, out.stdout + out.stderr
    assert 'skipped: another backup job is still running' in out.stdout
    assert not (state / 'dump').exists()


def test_the_job_never_asks_for_or_passes_a_password():
    with open(SCRIPT) as handle:
        script = handle.read()
    # Every restic call goes through restic_(), which adds --insecure-no-password.
    assert '--insecure-no-password' in script
    calls = re.findall(r'^\s*(?:"\$RESTIC_BIN"|restic)\s[^\n]*', script, re.M)
    assert calls == ['    "$RESTIC_BIN" "${args[@]}" "$@"'], calls   # restic_() itself
    assert 'restic-password' not in script


def test_a_password_in_the_environment_is_ignored(tmp_path):
    env = _shell_env(tmp_path, RESTIC_PASSWORD='should-not-be-used', RESTIC_REPOSITORY='',
                     GIRDER_MONGO_URI='mongodb://127.0.0.1:1/never')
    out = _run('run', env)
    assert 'should-not-be-used' not in out.stdout + out.stderr


def test_run_refuses_without_a_repository(tmp_path):
    env = _shell_env(tmp_path, RESTIC_REPOSITORY='')
    out = _run('run', env)
    assert out.returncode != 0
    assert 'no RESTIC_REPOSITORY' in out.stderr


# ---------------------------------------------------------------- unit: snapshot age

def test_snapshot_age_reads_restics_nanosecond_times():
    now = datetime.datetime(2026, 11, 5, 12, 0, tzinfo=datetime.timezone.utc)
    snaps = json.dumps([{'time': '2026-11-05T06:30:00.123456789-05:00', 'id': 'a'},
                        {'time': '2026-11-05T09:00:00Z', 'id': 'b'}])
    assert sb.snapshot_age_hours(snaps, now=now) == pytest.approx(0.5, abs=1e-3)
    assert sb.snapshot_age_hours('[]', now=now) is None
    assert sb.snapshot_age_hours('null', now=now) is None


def test_age_command_fails_past_the_limit(monkeypatch, capsys):
    old = (datetime.datetime.now(datetime.timezone.utc)
           - datetime.timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ')
    monkeypatch.setattr('sys.stdin', __import__('io').StringIO(json.dumps([{'time': old}])))
    assert sb.main(['age', '--max-hours', '2']) == 1
    monkeypatch.setattr('sys.stdin', __import__('io').StringIO(json.dumps([{'time': old}])))
    assert sb.main(['age', '--max-hours', '4']) == 0


def test_same_server_is_recognised_whatever_the_spelling():
    assert sb._same_server('mongodb://localhost/girder', 'mongodb://127.0.0.1:27017/x')
    assert sb._same_server('mongodb://u:p@127.0.0.1:27017/a', 'mongodb://127.0.0.1:27017')
    assert not sb._same_server('mongodb://127.0.0.1:27199', 'mongodb://127.0.0.1:27017/girder')


# ---------------------------------------------------------------- unit: units and workflow

def _unit(name):
    with open(os.path.join(SYSTEMD, name)) as handle:
        return handle.read()


def test_the_timer_is_hourly_and_persistent():
    timer = _unit('segqueue-backup.timer')
    assert re.search(r'^OnCalendar=hourly$', timer, re.M)
    assert re.search(r'^Persistent=true$', timer, re.M)
    assert re.search(r'^RandomizedDelaySec=', timer, re.M)
    assert re.search(r'^Unit=segqueue-backup\.service$', timer, re.M)
    check = _unit('segqueue-backup-check.timer')
    assert re.search(r'^Persistent=true$', check, re.M)


@pytest.mark.parametrize('name', ['segqueue-backup.service', 'segqueue-backup-check.service'])
def test_the_units_run_at_idle_priority_with_a_timeout_and_never_restart(name):
    unit = _unit(name)
    assert re.search(r'^Nice=19$', unit, re.M)
    assert re.search(r'^IOSchedulingClass=idle$', unit, re.M)   # ionice -c3
    assert re.search(r'^TimeoutStartSec=\d+(min|h)$', unit, re.M)
    assert re.search(r'^Type=oneshot$', unit, re.M)
    assert not re.search(r'^Restart=', unit, re.M)
    # Never pulls the database or Girder up or down with it.
    assert not re.search(r'^(Requires|BindsTo|PartOf|Conflicts)=', unit, re.M)
    assert re.search(r'^ProtectHome=read-only$', unit, re.M)


def test_the_job_never_restarts_or_locks_girder_or_mongo():
    with open(SCRIPT) as handle:
        script = handle.read()
    with open(os.path.join(BACKUP, 'segqueue_backup.py')) as handle:
        code = handle.read()
    for forbidden in ('fsyncLock', 'segqueue-girder', 'segqueue-mongod', 'segqueue.sh restart'):
        assert forbidden not in script and forbidden not in code
    # Only its own units are ever started or stopped.
    for line in re.findall(r'systemctl\s+(?:start|stop|restart|enable|disable)[^\n]*', script):
        assert 'segqueue-backup' in line, line
    assert 'StrictHostKeyChecking no' not in script
    assert 'StrictHostKeyChecking=no' not in script


def test_the_workflow_offers_the_backup_steps_and_checks_their_secrets():
    with open(WORKFLOW) as handle:
        wf = handle.read()
    for step in ('backup-install', 'backup-status', 'backup-restore-test', 'backup-off'):
        assert step in wf
    assert 'SSH_PORT_SFTP_SERVER' in wf
    # No repository password (lead, #283): no secret for it, and nothing refuses without one.
    assert 'BACKUP_RESTIC_PASSWORD' not in wf
    assert 'StrictHostKeyChecking=no' not in wf


# ---------------------------------------------------------------- against MongoDB

needs_mongo = pytest.mark.needs_mongo
_skip_mongo = pytest.mark.skipif(not MONGO, reason='SEGQUEUE_TEST_MONGO is not set')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def girder(tmp_path):
    """A synthetic Girder database and filesystem assetstore."""
    pymongo = pytest.importorskip('pymongo')
    from bson import ObjectId

    name = 'segqueue_backup_test_' + uuid.uuid4().hex[:8]
    uri = MONGO.rstrip('/') + '/' + name
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[name]
    store_root = tmp_path / 'assetstore'
    store_root.mkdir()
    store_id = ObjectId()
    db['assetstore'].insert_one({'_id': store_id, 'name': 'store', 'type': 0,
                                 'root': str(store_root)})
    pool = ObjectId()
    db['collection'].insert_many([{'_id': pool, 'name': 'CCTA-Pool'},
                                  {'_id': ObjectId(), 'name': 'SegQueue'}])
    made = {}

    def add_file(label, data, base=None, write=True):
        fid, item = ObjectId(), ObjectId()
        rel = '%s/%s/%s' % (fid.binary.hex()[:2], fid.binary.hex()[2:4], fid.binary.hex())
        if write:
            os.makedirs(os.path.dirname(store_root / rel), exist_ok=True)
            (store_root / rel).write_bytes(data)
        db['item'].insert_one({'_id': item, 'name': label,
                               'baseParentType': 'collection', 'baseParentId': base})
        db['file'].insert_one({'_id': fid, 'itemId': item, 'assetstoreId': store_id,
                               'path': rel, 'size': len(data), 'name': label})
        made[label] = SimpleNamespace(id=fid, path=str(store_root / rel), data=data)
        return fid

    ct = add_file('ct.nii.gz', b'CT' * 4096)
    region = add_file('region.nii.gz', b'RG' * 2048)
    seed = add_file('seed.seg.nrrd', b'seed-bytes')
    prelabel = add_file('prelabel.seg.nrrd', b'prelabel-bytes')
    old_prelabel = add_file('prelabel-v0.seg.nrrd', b'older-prelabel')
    big_prelabel = add_file('big-prelabel.seg.nrrd', b'x' * (2 * 1024 * 1024))
    pooled_seed = add_file('pool-seed.seg.nrrd', b'in-the-pool', base=pool)
    case1, case2 = ObjectId(), ObjectId()
    db['segqueue14_case'].insert_many([
        {'_id': case1, 'name': 'c1', 'fileId': ct, 'regionFileId': region,
         'seedFileId': seed, 'prelabelFileId': prelabel,
         'prelabelHistory': [{'prelabelFileId': old_prelabel}]},
        {'_id': case2, 'name': 'c2', 'fileId': ObjectId(), 'seedFileId': pooled_seed,
         'prelabelFileId': big_prelabel},
    ])
    subs = []
    for i, role in enumerate(['annotator', 'annotator', 'reviewer']):
        data = ('submission-%d' % i).encode() * 100
        fid = add_file('sub%d.seg.nrrd' % i, data)
        subs.append({'_id': ObjectId(), 'assignmentId': ObjectId(), 'caseId': case1,
                     'fileId': fid, 'checksum': _sha(data), 'authorRole': role})
    db['segqueue14_submission'].insert_many(subs)
    old = add_file('old-sub.seg.nrrd', b'old-queue')
    db['segqueue_submission'].insert_one({'_id': ObjectId(), 'assignmentId': ObjectId(),
                                          'fileId': old, 'checksum': _sha(b'old-queue')})
    yield SimpleNamespace(uri=uri, db=db, files=made, store=store_root, add_file=add_file,
                          case=case1, client=client)
    client.drop_database(name)


@needs_mongo
@_skip_mongo
def test_dump_takes_submissions_and_small_labels_but_never_ct(girder, tmp_path):
    out = tmp_path / 'dump'
    assert sb.dump(girder.uri, str(out), max_extra_bytes=1024 * 1024) == 0
    manifest = json.loads((out / 'manifest.json').read_text())
    kinds = sorted(f['kind'] for f in manifest['files'])
    assert kinds == ['old-submission', 'prelabel', 'prelabel', 'revision', 'seed',
                     'submission', 'submission']
    listed = (out / 'files.txt').read_text().split('\n')
    f = girder.files
    for label in ('ct.nii.gz', 'region.nii.gz', 'pool-seed.seg.nrrd', 'big-prelabel.seg.nrrd'):
        assert f[label].path not in listed, label
    for label in ('sub0.seg.nrrd', 'sub2.seg.nrrd', 'old-sub.seg.nrrd', 'seed.seg.nrrd',
                  'prelabel-v0.seg.nrrd'):
        assert f[label].path in listed, label
    assert manifest['excludedCt'] == 1           # the seed filed under CCTA-Pool
    assert [s['kind'] for s in manifest['skipped']] == ['prelabel']
    assert manifest['missing'] == []
    # The database: every collection, uncompressed BSON, mongodump's layout.
    from bson import decode_file_iter
    with open(out / manifest['database'] / 'segqueue14_submission.bson', 'rb') as handle:
        assert len(list(decode_file_iter(handle))) == 3
    assert manifest['documents'] == sum(manifest['collections'].values())
    assert not (tmp_path / 'dump.tmp').exists()


@needs_mongo
@_skip_mongo
def test_a_ct_is_excluded_even_when_a_submission_points_at_it(girder, tmp_path):
    from bson import ObjectId
    girder.db['segqueue14_submission'].insert_one(
        {'_id': ObjectId(), 'assignmentId': ObjectId(), 'authorRole': 'annotator',
         'fileId': girder.files['ct.nii.gz'].id, 'checksum': ''})
    sb.dump(girder.uri, str(tmp_path / 'dump'), None)
    manifest = json.loads((tmp_path / 'dump' / 'manifest.json').read_text())
    assert girder.files['ct.nii.gz'].path not in {f['path'] for f in manifest['files']}
    assert manifest['excludedCt'] == 2


@needs_mongo
@_skip_mongo
def test_dump_can_leave_seeds_and_prelabels_out(girder, tmp_path):
    sb.dump(girder.uri, str(tmp_path / 'dump'), max_extra_bytes=0)
    manifest = json.loads((tmp_path / 'dump' / 'manifest.json').read_text())
    assert {f['kind'] for f in manifest['files']} == {'submission', 'revision', 'old-submission'}


@needs_mongo
@_skip_mongo
def test_dump_is_deterministic_so_restic_deduplicates_it(girder, tmp_path):
    sb.dump(girder.uri, str(tmp_path / 'a'), None)
    sb.dump(girder.uri, str(tmp_path / 'b'), None)
    db = json.loads((tmp_path / 'a' / 'manifest.json').read_text())['database']
    for name in os.listdir(tmp_path / 'a' / db):
        a, b = tmp_path / 'a' / db / name, tmp_path / 'b' / db / name
        assert a.read_bytes() == b.read_bytes()


@needs_mongo
@_skip_mongo
def test_a_missing_submission_file_is_reported_and_the_rest_still_dumped(girder, tmp_path):
    from bson import ObjectId
    fid = girder.add_file('lost.seg.nrrd', b'lost', write=False)
    girder.db['segqueue14_submission'].insert_one(
        {'_id': ObjectId(), 'assignmentId': ObjectId(), 'fileId': fid, 'checksum': _sha(b'lost')})
    assert sb.dump(girder.uri, str(tmp_path / 'dump'), None) == sb.EXIT_MISSING
    manifest = json.loads((tmp_path / 'dump' / 'manifest.json').read_text())
    assert [m['reason'] for m in manifest['missing']] == ['not on disk']
    assert len([f for f in manifest['files'] if f['kind'] == 'submission']) == 2


def _fake_restore(girder, tmp_path):
    """A dump plus copies of its files laid out the way `restic restore` lays them out."""
    dump = tmp_path / 'dump'
    sb.dump(girder.uri, str(dump), None)
    restored = tmp_path / 'restored'
    for f in json.loads((dump / 'manifest.json').read_text())['files']:
        copy = restored / f['path'].lstrip('/')
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f['path'], copy)
    return dump, restored


@needs_mongo
@_skip_mongo
def test_verify_finds_every_submission_and_catches_a_bad_copy(girder, tmp_path):
    dump, restored = _fake_restore(girder, tmp_path)
    assert sb.verify(str(dump), str(restored)) == 0
    victim = restored / girder.files['sub1.seg.nrrd'].path.lstrip('/')
    victim.write_bytes(b'corrupted')
    assert sb.verify(str(dump), str(restored)) == 1
    victim.unlink()
    assert sb.verify(str(dump), str(restored)) == 1


@needs_mongo
@_skip_mongo
def test_verify_refuses_to_load_into_the_live_server(girder, tmp_path):
    dump, restored = _fake_restore(girder, tmp_path)
    with pytest.raises(SystemExit, match='live server'):
        sb.verify(str(dump), str(restored), scratch_uri=MONGO, live_uri=girder.uri)


# ---------------------------------------------------------------- the round trip, with restic

def _restic_version():
    if not RESTIC:
        return (0,)
    out = subprocess.run([RESTIC, 'version'], capture_output=True, text=True).stdout
    m = re.match(r'restic (\d+)\.(\d+)', out)
    return (int(m.group(1)), int(m.group(2))) if m else (0,)


_skip_restic = pytest.mark.skipif(_restic_version() < (0, 17),
                                  reason='restic >= 0.17 (--insecure-no-password) is not installed')


def _restic(env, *args):
    # No password: the repository is unencrypted by the lead's decision on #283.
    return subprocess.run([RESTIC, '--insecure-no-password', *args],
                          env=dict(os.environ, **env), capture_output=True, text=True, timeout=120)


@needs_mongo
@_skip_mongo
@_skip_restic
@pytest.mark.parametrize('scratch', ['bson', 'mongo'])
def test_round_trip_dump_snapshot_restore_and_check(girder, tmp_path, scratch):
    if scratch == 'mongo' and not SCRATCH_MONGO:
        pytest.skip('SEGQUEUE_TEST_SCRATCH_MONGO is not set')
    env = _shell_env(tmp_path, GIRDER_MONGO_URI=girder.uri,
                     BACKUP_SCRATCH_MONGO=SCRATCH_MONGO if scratch == 'mongo' else '')
    assert _restic(env, 'init').returncode == 0

    first = _run('run', env)
    assert first.returncode == 0, first.stdout + first.stderr
    assert not (tmp_path / 'state' / 'dump').exists()      # removed once shipped

    # An hour later: one more submission. Only it is new.
    from bson import ObjectId
    data = b'the next hour' * 50
    fid = girder.add_file('sub3.seg.nrrd', data)
    girder.db['segqueue14_submission'].insert_one(
        {'_id': ObjectId(), 'assignmentId': ObjectId(), 'fileId': fid, 'checksum': _sha(data)})
    second = _run('run', env)
    assert second.returncode == 0, second.stdout + second.stderr
    assert '(parent ' in second.stdout

    snaps = json.loads(_restic(env, 'snapshots', '--json').stdout)
    assert len(snaps) == 2
    listing = _restic(env, 'ls', 'latest').stdout
    assert girder.files['sub0.seg.nrrd'].path in listing
    assert girder.files['ct.nii.gz'].path not in listing
    assert girder.files['region.nii.gz'].path not in listing

    drill = _run('restore-test', env)
    assert drill.returncode == 0, drill.stdout + drill.stderr
    assert '5 of 5 submission files present with matching checksums' in drill.stdout
    assert 'restore test passed' in drill.stdout
    if scratch == 'mongo':
        assert 'loaded' in drill.stdout and 'scratch database' in drill.stdout
    assert not (tmp_path / 'state' / 'restore-test').exists()   # scratch copy removed

    status = _run('status', env)
    assert status.returncode == 0, status.stdout + status.stderr
    assert 'snapshots: 2' in status.stdout
    assert 'newest snapshot is 0.0 hours old' in status.stdout

    check = _run('check', env)
    assert check.returncode == 0, check.stdout + check.stderr


@needs_mongo
@_skip_mongo
@_skip_restic
def test_status_fails_when_the_newest_snapshot_is_too_old(girder, tmp_path):
    env = _shell_env(tmp_path, GIRDER_MONGO_URI=girder.uri, BACKUP_MAX_AGE_HOURS='0')
    assert _restic(env, 'init').returncode == 0
    assert _run('run', env).returncode == 0
    status = _run('status', env)
    assert status.returncode != 0
    assert 'older than 0 h' in status.stderr
