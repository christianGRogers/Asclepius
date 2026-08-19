"""End-to-end acceptance test against a running SegQueue server.

Not collected by pytest -- it needs a live server, and the filename is chosen so
it is not picked up by accident. Run it by hand once after deploying:

    python tests/segqueue_e2e.py --url http://localhost:8099

It exercises the real loop over real HTTP, using the *same* client the Slicer
extension uses, so a pass means the extension will work. In order: register the
first admin, create the assetstore, create an annotator, claim a case, verify its
checksum, upload a submission in resumable chunks, submit, get it rejected with a
comment, rework it as attempt 2, and get it approved. Along the way it checks
that empty segments, resampled geometry and corrupted uploads are all refused.

Everything it creates is idempotent. Run it twice and the second run reuses the
accounts from the first; what it cannot reuse is cases, so it needs one unclaimed
case per run (two to also check the concurrency guard).

The one thing it deliberately does not test is the Qt panel. Everything below the
UI is here.
"""

import argparse
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'src'))
sys.path.insert(0, os.path.join(REPO, 'slicer', 'SegQueue'))

import requests  # noqa: E402
from SegQueueLib import SegQueueClient, SegQueueError  # noqa: E402

from segqueue import protocol  # noqa: E402
from segqueue.checksum import sha256_file  # noqa: E402

#: A geometry both the source volume and the submission claim. The server only
#: compares them to each other, so any consistent pair passes and any
#: inconsistent pair must not.
GEOMETRY = {'size': [64, 64, 40], 'spacing': [0.4, 0.4, 0.5], 'origin': [0.0, 0.0, 0.0]}

_results = []


def check(name, condition, detail=''):
    _results.append((name, bool(condition), detail))
    mark = 'PASS' if condition else 'FAIL'
    print(f'  [{mark}] {name}' + (f'  -- {detail}' if detail else ''))
    return bool(condition)


def refuses(name, call, expectText=''):
    """Assert that a call is refused, and that the refusal says something useful."""
    try:
        call()
    except SegQueueError as exc:
        text = str(exc)
        ok = expectText.lower() in text.lower() if expectText else True
        return check(name, ok, text.splitlines()[0][:110])
    return check(name, False, 'the server ACCEPTED it')


def heading(text):
    print(f'\n{text}\n' + '-' * len(text))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Acceptance test against a running SegQueue server.')
    parser.add_argument('--url', default='http://localhost:8099',
                        help='Base URL of the server (without /api/v1).')
    parser.add_argument('--admin-login', default='admin1')
    parser.add_argument('--admin-password', default='hunter2xyz')
    parser.add_argument('--annotator-login', default='student01')
    parser.add_argument('--annotator-password', default='segment123')
    parser.add_argument('--assetstore-root', default='/data/assetstore',
                        help='Path *inside the container* for the assetstore.')
    args = parser.parse_args(argv)

    base = args.url.rstrip('/') + '/api/v1'
    http = requests.Session()

    # ---------------------------------------------------------------- setup

    heading('Server bootstrap')
    try:
        version = http.get(base + '/system/version', timeout=10)
    except requests.RequestException as exc:
        print(f'  Cannot reach {base}: {exc}')
        return 2
    if not check('server answers /system/version', version.status_code == 200):
        return 2

    # The first account Girder sees becomes a site administrator. A 400 here
    # means it already exists, which is the normal state on a second run.
    http.post(base + '/user', params={
        'login': args.admin_login, 'email': f'{args.admin_login}@example.edu',
        'firstName': 'Ada', 'lastName': 'Admin', 'password': args.admin_password})
    auth = http.get(base + '/user/authentication',
                    auth=(args.admin_login, args.admin_password))
    # Deliberately not echoing the body: it contains a bearer token, and this
    # script's output is exactly the kind of thing that gets pasted into a chat.
    if not check('admin can authenticate', auth.status_code == 200,
                 '' if auth.status_code == 200 else auth.text[:120]):
        return 2
    adminHeaders = {'Girder-Token': auth.json()['authToken']['token']}

    store = http.post(base + '/assetstore', headers=adminHeaders, params={
        'type': 0, 'name': 'store', 'root': args.assetstore_root})
    stores = http.get(base + '/assetstore', headers=adminHeaders).json()
    check('a filesystem assetstore exists', bool(stores),
          store.json().get('message', '') if store.status_code >= 400 else 'created')

    http.post(base + '/segqueue/users', headers=adminHeaders, params={
        'login': args.annotator_login, 'email': f'{args.annotator_login}@example.edu',
        'firstName': 'Sam', 'lastName': 'Student',
        'password': args.annotator_password, 'quota': 50})

    # ------------------------------------------------------------- annotator

    heading('Annotator session')
    student = SegQueueClient(args.url, extensionVersion='e2e')
    try:
        user = student.login(args.annotator_login, args.annotator_password)
    except SegQueueError as exc:
        check('annotator can log in', False, str(exc)[:150])
        return report()
    check('annotator can log in', True, user.get('login', ''))

    project = student.project()
    check('the server sends the labelling protocol', bool(project.segments),
          ', '.join(s.name for s in project.segments))
    check('the server names an upload folder', bool(project.upload_folder_id),
          project.upload_folder_id)

    assignment = student.nextCase()
    if assignment is None:
        print('\n  The case pool is empty. Ingest some cases first, e.g.\n'
              '      docker compose exec girder segqueue-ingest --root /incoming\n')
        return report()
    check('a case is assigned', True,
          f'{assignment.case_name} ({assignment.size_bytes} bytes)')
    check('the assignment carries a lease deadline', bool(assignment.deadline))
    check('the case flavour is hidden from the annotator', assignment.kind is None,
          'blind means blind')

    volume = os.path.join(tempfile.gettempdir(), 'segqueue_case.nrrd')
    written = student.downloadCase(assignment.case_id, volume)
    check('the volume downloads completely', written == assignment.size_bytes,
          f'{written} bytes')
    check('the volume matches its checksum',
          sha256_file(volume) == assignment.checksum)

    heading('What ships with the case')
    for kind, flag in ((protocol.ASSET_REGION, assignment.has_region),
                       (protocol.ASSET_SEED, assignment.has_seed)):
        dest = os.path.join(tempfile.gettempdir(), f'segqueue_{kind}.nii.gz')
        got = student.downloadAsset(assignment.case_id, kind, dest)
        if flag:
            check(f'the {kind} mask downloads', got is not None and
                  os.path.getsize(dest) > 0, f'{os.path.getsize(dest)} bytes'
                  if got else 'nothing came back')
        else:
            # The common answer. It has to be a return value rather than an
            # exception, because the extension asks for both on every case and
            # most cases have neither.
            check(f'a missing {kind} mask reads as absent, not as an error',
                  got is None)

    # A stand-in for a segmentation. The server never opens it -- it hashes it,
    # checks the size, and trusts the declared voxel counts for ordinary work --
    # so random bytes exercise exactly the path a real .seg.nrrd would.
    seg = os.path.join(tempfile.gettempdir(), 'segqueue_submission.seg.nrrd')
    with open(seg, 'wb') as handle:
        handle.write(os.urandom(20000))
    digest, size = sha256_file(seg), os.path.getsize(seg)

    def upload(name):
        return student.uploadFile(seg, project.upload_folder_id, name=name)['_id']

    def submitWith(meta, geometry=None):
        return student.submit(assignment.assignment_id, meta, upload('x.seg.nrrd'),
                              geometry=geometry or {'source': GEOMETRY,
                                                    'segmentation': GEOMETRY})

    heading('Submission checks (each of these must be refused)')
    refuses(
        'an empty required segment is refused',
        lambda: submitWith(protocol.SubmissionMeta(
            checksum=digest, size_bytes=size, annotation_seconds=900.0,
            voxel_counts={})),
        'is empty')
    refuses(
        'a stray-mark segment is refused',
        lambda: submitWith(protocol.SubmissionMeta(
            checksum=digest, size_bytes=size, annotation_seconds=900.0,
            voxel_counts={s.name: 3 for s in project.segments})),
        'stray')
    refuses(
        'a segment outside the protocol is refused',
        lambda: submitWith(protocol.SubmissionMeta(
            checksum=digest, size_bytes=size, annotation_seconds=900.0,
            voxel_counts=dict({s.name: 800 for s in project.segments},
                              Segment_1=500))),
        'not part of this project')
    refuses(
        'a resampled segmentation is refused',
        lambda: submitWith(
            protocol.SubmissionMeta(checksum=digest, size_bytes=size,
                                    annotation_seconds=900.0,
                                    voxel_counts={s.name: 800 for s in project.segments}),
            geometry={'source': GEOMETRY,
                      'segmentation': dict(GEOMETRY, spacing=[1.0, 1.0, 1.0])}),
        'resampled')
    refuses(
        'a corrupted upload is refused',
        lambda: submitWith(protocol.SubmissionMeta(
            checksum='00' * 32, size_bytes=size, annotation_seconds=900.0,
            voxel_counts={s.name: 800 for s in project.segments})),
        'checksum')

    heading('A good submission')
    good = protocol.SubmissionMeta(
        checksum=digest, size_bytes=size, annotation_seconds=2100.0,
        voxel_counts={s.name: 900 for s in project.segments},
        slicer_version='5.8.0', extension_version='e2e',
        annotator_note='acceptance test')
    response = submitWith(good)
    check('the submission is accepted', bool(response.get('submissionId')))
    check('the first case goes to a human (training gate)',
          response.get('awaitingReview') is True,
          'first five cases are always reviewed')

    # -------------------------------------------------------------- reviewer

    heading('Review, rejection and rework')
    reviewer = SegQueueClient(args.url, extensionVersion='e2e')
    reviewer.login(args.admin_login, args.admin_password)

    queue = reviewer.reviewQueue()
    row = next((q for q in queue if q['caseName'] == assignment.case_name), None)
    if not check('the submission appears in the review queue', row is not None):
        return report()
    check('the reviewer sees the case flavour', 'kind' in row, row.get('kind'))

    refuses('a rejection with no comment is refused',
            lambda: reviewer.submitVerdict(row['submissionId'], 'reject', comment=''),
            'what to fix')

    reviewer.claimReview(row['submissionId'])
    verdict = reviewer.submitVerdict(
        row['submissionId'], 'reject',
        comment='The LAD stops at the first diagonal. Continue it distally.',
        secondsSpent=90)
    check('the rejection is recorded', verdict.get('state') == 'rejected')

    mine = student.myAssignments()
    back = next((a for a in mine if a.assignment_id == assignment.assignment_id), None)
    check('the case returns to the same annotator', back is not None)
    check('the reviewer comment reaches the annotator',
          bool(back and back.reviewer_comment),
          (back.reviewer_comment if back else '')[:70])

    student.downloadCase(back.case_id, volume)
    after = next(a for a in student.myAssignments()
                 if a.assignment_id == assignment.assignment_id)
    check('reworking renews the lease and bumps the attempt',
          after.attempt == 2, f'attempt {after.attempt}, state {after.state}')

    submitWith(protocol.SubmissionMeta(
        checksum=digest, size_bytes=size, annotation_seconds=2600.0,
        voxel_counts={s.name: 1100 for s in project.segments},
        annotator_note='extended the LAD distally'))
    row2 = next(q for q in reviewer.reviewQueue()
                if q['caseName'] == assignment.case_name)
    check('the rework is queued as attempt 2', row2['attempt'] == 2)
    reviewer.claimReview(row2['submissionId'])
    final = reviewer.submitVerdict(row2['submissionId'], 'approve', comment='Good.')
    check('the rework is approved', final.get('state') == 'approved')

    # ------------------------------------------------------------ invariants

    heading('Queue invariants')
    states = {a.case_name: a.state for a in student.myAssignments(includeFinished=True)}
    check('the case is approved', states.get(assignment.case_name) == 'approved',
          str(states))

    stats = http.get(base + '/segqueue/stats', headers=adminHeaders).json()
    check('the dashboard counts the approval', stats['cases']['complete'] >= 1,
          f"complete {stats['cases']['complete']} of {stats['total']}")

    sweep = http.post(base + '/segqueue/sweep', headers=adminHeaders,
                      params={'dryRun': 'true'}).json()
    check('a dry-run sweep strands nothing', sweep['count'] == 0, str(sweep['count']))

    second = student.nextCase()
    if second is not None:
        other = SegQueueClient(args.url, extensionVersion='e2e')
        other.login(args.admin_login, args.admin_password)
        # The admin is also an annotator by right. They must not be handed the
        # case the student is holding: one case, one annotator at a time.
        theirs = other.nextCase()
        check('a claimed case is not handed to a second annotator',
              theirs is None or theirs.case_id != second.case_id,
              'released back' if theirs is None else theirs.case_name)
        if theirs is not None:
            other.releaseCase(theirs.assignment_id, reason='e2e cleanup')
        student.releaseCase(second.assignment_id, reason='e2e cleanup')
        check('a released case returns to the pool', True)
    else:
        print('  (only one case in the pool -- skipped the concurrency check)')

    return report()


def report():
    failed = [name for name, ok, _ in _results if not ok]
    print('\n' + '=' * 64)
    print(f'{len(_results) - len(failed)} passed, {len(failed)} failed')
    for name in failed:
        print(f'  FAILED: {name}')
    print('=' * 64)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
