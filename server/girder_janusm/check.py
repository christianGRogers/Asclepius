"""``janusm-check``: the automatic read check (JA7) on every submitted Janus-M read.

Each submitted read and its case's CT are copied to a scratch directory and checked
with ``janusm_reads.checker`` (label conventions and the half-maximum rule). A
passed read is **accepted**; a failed one is **returned** to its reader with the
reasons. Nothing else is written. Runs on the server against the database::

    janusm-check --once           # check what is waiting, then stop
    janusm-check --every 30       # keep checking (the systemd unit's mode)
"""

import argparse
import datetime
import os
import tempfile
import time

from girder.models.file import File
from janusm_reads import protocol

from .models import JanusMCase, JanusMRead


def _suffix(name):
    lower = (name or '').lower()
    for s in ('.nii.gz', '.nii', '.nrrd'):
        if lower.endswith(s):
            return s
    return '.nii.gz'


def _copy(file, directory, stem):
    path = os.path.join(directory, stem + _suffix(file.get('name')))
    with open(path, 'wb') as out:
        for chunk in File().download(file, headers=False)():
            out.write(chunk)
    return path


def checkRead(read, cfg=None):
    """Check one submitted read and move it to accepted or returned."""
    from janusm_reads import checker

    case = JanusMCase().load(read['caseId'], force=True)
    ctFile = File().load(case['ctFileId'], force=True)
    readFile = File().load(read['fileId'], force=True)
    with tempfile.TemporaryDirectory(prefix='janusm-check-') as tmp:
        try:
            report = checker.check_files(_copy(readFile, tmp, 'read'),
                                         _copy(ctFile, tmp, 'ct'), cfg).to_dict()
        except Exception as exc:  # noqa: BLE001 - a read that cannot be checked goes back
            report = {'passed': False, 'errors': [f'The read could not be checked: {exc}'],
                      'warnings': [], 'summary': f'Failed the Janus-M read check: {exc}'}
    to = protocol.ACCEPTED if report['passed'] else protocol.RETURNED
    moved = JanusMRead().transition(
        read, to, check=report, checkSummary=report['summary'],
        checkedAt=datetime.datetime.now(datetime.timezone.utc))
    if moved is not None and to == protocol.ACCEPTED:
        JanusMCase().recordAccepted(read['caseId'])
    return moved or JanusMRead().load(read['_id'], force=True)


def runOnce(out=print):
    done = 0
    for read in JanusMRead().submittedQueue():
        moved = checkRead(read)
        out(f"{read['_id']}: {moved['state']} - {moved.get('checkSummary', '')}")
        done += 1
    return done


def main(argv=None):
    parser = argparse.ArgumentParser(prog='janusm-check', description=__doc__.split('\n\n')[0])
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--every', type=float, default=30.0)
    args = parser.parse_args(argv)
    while True:
        runOnce()
        if args.once:
            return 0
        time.sleep(args.every)


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
