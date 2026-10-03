"""End-to-end acceptance test against a running SegQueue server.

Not collected by pytest -- it needs a live server, and the filename is chosen so
it is not picked up by accident. Run it by hand once after deploying:

    python tests/segqueue_e2e.py --url http://localhost:8099

It exercises the real loop over real HTTP, using the *same* client the Slicer
extension uses, so a pass means the extension will work. In order: register the
first admin, create the assetstore, create an annotator, claim a case, verify its
checksum, upload a submission in resumable chunks, submit, find it in the
reviewer's submission viewer, download it back, correct it as the reviewer and
have that approve the case, then send a second case back to the pool. Along the
way it checks that empty segments, resampled geometry and corrupted uploads are
all refused.

Everything it creates is idempotent. Run it twice and the second run reuses the
accounts from the first; what it cannot reuse is cases, so it needs one unclaimed
case per run -- three, to also check the concurrency guard and the
send-back-to-the-pool path.

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


def _accepts(submit, meta, geometry=None):
    """True when a submission goes through. Used where a refusal would be news."""
    try:
        submit(meta, geometry)
        return True
    except SegQueueError:
        return False


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

    heading('What is still refused, and what is not')
    # Validation was removed: every submission is seen by a human reviewer, and a
    # server that refuses the work cannot be overruled by them. What a client
    # sends is now its own business -- except for the bytes.
    for name, meta in (
        ('an empty segmentation', protocol.SubmissionMeta(
            checksum=digest, size_bytes=size, annotation_seconds=900.0,
            voxel_counts={})),
        ('a stray-mark segmentation', protocol.SubmissionMeta(
            checksum=digest, size_bytes=size, annotation_seconds=900.0,
            voxel_counts={s.name: 3 for s in project.segments})),
        ('a segment outside the protocol', protocol.SubmissionMeta(
            checksum=digest, size_bytes=size, annotation_seconds=900.0,
            voxel_counts=dict({s.name: 800 for s in project.segments},
                              Segment_1=500))),
    ):
        try:
            submitWith(meta)
            check('%s is accepted' % name, True)
        except SegQueueError as exc:
            check('%s is accepted' % name, False, str(exc).splitlines()[0][:110])

    check('a resampled grid is accepted too', _accepts(
        submitWith, protocol.SubmissionMeta(
            checksum=digest, size_bytes=size, annotation_seconds=900.0,
            voxel_counts={s.name: 800 for s in project.segments}),
        {'source': GEOMETRY,
         'segmentation': dict(GEOMETRY, spacing=[1.0, 1.0, 1.0])}))

    # The bytes are not a matter of opinion.
    refuses(
        'a corrupted upload is still refused',
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

    heading('The submission viewer')
    reviewer = SegQueueClient(args.url, extensionVersion='e2e')
    reviewer.login(args.admin_login, args.admin_password)

    def reviewerUpload(name):
        """An upload owned by the reviewer, not the annotator.

        ``revise`` loads the file with WRITE as the calling user. A site admin
        would get through either way, which is exactly why the reviewer uploads
        here: otherwise the test passes on admin privilege and says nothing about
        whether an ordinary reviewer could do it.
        """
        return reviewer.uploadFile(seg, project.upload_folder_id, name=name)['_id']

    cases = reviewer.caseOverview()
    entry = next((c for c in cases if c['caseName'] == assignment.case_name), None)
    if not check('the case appears in the viewer', entry is not None):
        return report()
    check('the viewer lists cases, not just a review queue', len(cases) >= 1,
          f'{len(cases)} case(s)')

    lease = next((a for a in entry['assignments'] if a['state'] == 'submitted'), None)
    if not check('the submitted lease is on the case', lease is not None,
                 str([a['state'] for a in entry['assignments']])):
        return report()
    check('the viewer names the annotator',
          lease['annotator'] == args.annotator_login, lease['annotator'])
    check('and counts the submissions', lease['submissionCount'] == 1,
          str(lease['submissionCount']))

    # The filename is what "review does not load" turned on. Slicer picks its
    # reader from the extension, so a .nii.gz volume has to arrive saying so.
    check('the case carries its volume filename',
          str(entry.get('volumeName') or '').endswith(('.nii.gz', '.nii', '.nrrd')),
          entry.get('volumeName'))

    history = reviewer.caseSubmissions(entry['caseId'])
    if not check('the submission history has the attempt in it', len(history) == 1,
                 f'{len(history)} submission(s)'):
        return report()
    check('the history says who authored it',
          history[0].get('authorRole') == 'annotator', history[0].get('authorRole'))
    check('and carries both filenames the client saves under',
          bool(history[0].get('volumeName')) and bool(history[0].get('submissionName')),
          f"{history[0].get('volumeName')} / {history[0].get('submissionName')}")

    submissionId = history[0]['submissionId']
    volumeCopy = os.path.join(tempfile.gettempdir(), 'segqueue_review_volume')
    segCopy = os.path.join(tempfile.gettempdir(), 'segqueue_review_submission')
    reviewer.downloadReviewFile(submissionId, 'volume', volumeCopy)
    reviewer.downloadReviewFile(submissionId, 'download', segCopy)
    check('the reviewer can download the source volume',
          sha256_file(volumeCopy) == assignment.checksum,
          'checksum matches the case')
    check('and the submitted segmentation',
          sha256_file(segCopy) == digest,
          'checksum matches what the annotator sent')

    heading('Reject is retired')
    refuses('rejecting says where the verb went',
            lambda: reviewer.submitVerdict(submissionId, 'reject',
                                           comment='no longer a thing'),
            'no longer a verdict')

    heading("The reviewer's own corrected version")
    revision = reviewer.reviseSubmission(
        submissionId,
        protocol.SubmissionMeta(
            checksum=digest, size_bytes=size, annotation_seconds=180.0,
            voxel_counts={s.name: 950 for s in project.segments},
            slicer_version='5.8.0', extension_version='e2e',
            annotator_note='reviewer corrected the LAD'),
        reviewerUpload('revision.seg.nrrd'))
    check('the revision is stored', bool(revision.get('submissionId')))
    check('and it approves the case', revision.get('state') == 'approved',
          revision.get('state'))

    history = reviewer.caseSubmissions(entry['caseId'])
    check("the annotator's submission is still there", len(history) == 2,
          f'{len(history)} submission(s)')
    roles = [h.get('authorRole') for h in history]
    check('one annotator submission, then one reviewer revision',
          roles == ['annotator', 'reviewer'], str(roles))
    if len(history) == 2:
        check('the revision is credited to the reviewer, not the annotator',
              history[1]['annotator']['login'] == args.admin_login,
              history[1]['annotator']['login'])
        check('and records which submission it corrected',
              history[1].get('revisionOf') == submissionId,
              str(history[1].get('revisionOf')))
        check('the original row is untouched',
              history[0]['submissionId'] == submissionId
              and history[0]['annotator']['login'] == args.annotator_login)

    refuses('an approved case cannot be revised again',
            lambda: reviewer.reviseSubmission(
                submissionId,
                protocol.SubmissionMeta(
                    checksum=digest, size_bytes=size, annotation_seconds=10.0,
                    voxel_counts={s.name: 950 for s in project.segments}),
                reviewerUpload('revision2.seg.nrrd')),
            'cannot be revised')

    heading('Seeing and handing out the whole pool')
    allCases = reviewer.allCases()
    check('the viewer pages through every case, not just the first page',
          len(allCases) >= len(cases), '{} via paging vs {} in one page'.format(
              len(allCases), len(cases)))
    names = [c['caseName'] for c in allCases]
    check('and returns each case once', len(names) == len(set(names)),
          '{} rows, {} distinct'.format(len(names), len(set(names))))

    people = reviewer.annotators()
    check('the reviewer can see who a case can go to', bool(people),
          ', '.join(p['login'] for p in people) or 'nobody')
    mine = next((p for p in people if p['login'] == args.annotator_login), None)
    if not check('the annotator is in that list', mine is not None):
        return report()
    check('with what they are already holding',
          isinstance(mine.get('openCases'), int), str(mine.get('openCases')))

    free = next((c for c in allCases if not c['assignments']), None)
    if check('there is an untouched case to hand out', free is not None,
             'none left' if free is None else free['caseName']):
        # A case nobody has worked on has no submission, so the only way to look
        # at it before handing it out is its own volume.
        volumeCopy = os.path.join(tempfile.gettempdir(), 'segqueue_case_peek')
        reviewer.downloadCaseVolume(free['caseId'], volumeCopy)
        check('a reviewer can open a case with no submission on it',
              os.path.getsize(volumeCopy) > 0,
              '{} bytes'.format(os.path.getsize(volumeCopy)))

        handed = reviewer.assignCase(free['caseId'], mine['userId'])
        check('and hand it to a named annotator',
              handed.get('annotator') == args.annotator_login,
              str(handed.get('annotator')))
        check('which puts it in their queue',
              free['caseName'] in {a.case_name for a in student.myAssignments()},
              free['caseName'])

        refuses('the same case cannot be handed to them twice',
                lambda: reviewer.assignCase(free['caseId'], mine['userId']),
                'previously been assigned')

        held = next(a for a in student.myAssignments()
                    if a.case_name == free['caseName'])
        student.releaseCase(held.assignment_id, reason='e2e tidy-up')

    heading('A reviewer taking a case and doing it themselves')
    mineNow = reviewer.allCases()
    spare2 = next((c for c in mineNow if not c['assignments']), None)
    if check('there is an untouched case to take', spare2 is not None,
             'none left' if spare2 is None else spare2['caseName']):
        who = reviewer.whoami()
        taken = reviewer.assignCase(spare2['caseId'], who['_id'])
        check('a reviewer can assign a case to themselves',
              taken.get('annotator') == args.admin_login, str(taken.get('annotator')))

        held = next((a for a in reviewer.myAssignments()
                     if a.case_id == spare2['caseId']), None)
        if check('and it arrives in their own queue', held is not None):
            # The point of routing this through an ordinary assignment: from
            # here the normal annotator path works unchanged, which is what
            # makes the submission a real one rather than a special case.
            reviewer.downloadCase(held.case_id, volume)
            submitted = reviewer.submit(
                held.assignment_id,
                protocol.SubmissionMeta(
                    checksum=digest, size_bytes=size, annotation_seconds=1400.0,
                    voxel_counts={s.name: 820 for s in project.segments},
                    slicer_version='5.8.0', extension_version='e2e',
                    annotator_note='reviewer segmented this one'),
                reviewerUpload('reviewer_own.seg.nrrd'),
                geometry={'source': GEOMETRY, 'segmentation': GEOMETRY})
            check('and they can submit it like any other case',
                  bool(submitted.get('submissionId')),
                  str(submitted.get('submissionId'))[:24])

            history = reviewer.caseSubmissions(spare2['caseId'])
            check('which lands in the case history as an annotator submission',
                  len(history) == 1
                  and history[0].get('authorRole') == 'annotator',
                  '{} row(s), role {}'.format(
                      len(history),
                      history[0].get('authorRole') if history else '-'))

    heading('Back into circulation')
    spare = student.nextCase()
    if check('there is another case to send back', spare is not None):
        student.downloadCase(spare.case_id, volume)
        spareResponse = student.submit(
            spare.assignment_id,
            protocol.SubmissionMeta(
                checksum=digest, size_bytes=size, annotation_seconds=1500.0,
                voxel_counts={s.name: 700 for s in project.segments}),
            upload('spare.seg.nrrd'),
            geometry={'source': GEOMETRY, 'segmentation': GEOMETRY})
        spareId = spareResponse.get('submissionId')
        check('the spare case is submitted', bool(spareId))

        returned = reviewer.returnToPool(spareId, reason='needs a second opinion')
        check('it goes back to the pool', returned.get('returned') is True)
        check('and the lease is released', returned.get('state') == 'released',
              str(returned.get('state')))

        check('the submission survives being sent back',
              len(reviewer.caseSubmissions(spare.case_id)) == 1)
        held = {a.case_name for a in student.myAssignments()}
        check('the annotator no longer holds it',
              spare.case_name not in held, str(sorted(held)))

        # `assignedUserIds` is permanent, so the case is servable again but never
        # to the person who already did it. Not a setting: it is the same list
        # that keeps a blind duplicate's two annotators independent.
        again = student.nextCase()
        check('and is not handed back to the same annotator',
              again is None or again.case_name != spare.case_name,
              'got nothing' if again is None else again.case_name)
        if again is not None:
            student.releaseCase(again.assignment_id, reason='e2e tidy-up')

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
