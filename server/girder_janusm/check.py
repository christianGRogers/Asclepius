"""``janusm-check``: the automatic read check (border protocol v1) on every submitted
Janus-M read.

Each submitted read, its case's CT and, on a seeded case, its seed (the mitral plane
is fitted to it; JA46 (a)) are copied to a scratch directory and checked with
``janusm_reads.checker`` (label conventions and the half-maximum rule).

* A passed read is **accepted**.
* A failed read is **returned** to its reader with the reasons and the half-maximum
  profiles -- **once** (``protocol.MAX_RETURNS``, counted by ``attempts``).
* A read that fails again is **accepted and flagged** (``flagged: true``, with
  ``flagReasons``). A flagged read counts in every analysis, and the flag is reported.
* A read the checker cannot run on at all goes back unflagged: that is not a failed
  check.

Nothing else is written. Runs on the server against the database::

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


def decide(report, attempts, crashed=False):
    """``(state, flagged, summary)`` for a check report on a read's ``attempts``-th
    submission: return once, then accept and flag (Hotel v3 section 5.1 item 7)."""
    if report['passed']:
        return protocol.ACCEPTED, False, report['summary']
    if crashed or int(attempts or 0) <= protocol.MAX_RETURNS:
        return protocol.RETURNED, False, report['summary']
    return (protocol.ACCEPTED, True,
            'Accepted and flagged: the read failed the check again after being returned '
            'once. ' + ' '.join(report.get('errors') or []))


def checkRead(read, cfg=None):
    """Check one submitted read and move it to accepted, returned or accepted-flagged."""
    from janusm_reads import BORDER_PROTOCOL, checker

    case = JanusMCase().load(read['caseId'], force=True)
    ctFile = File().load(case['ctFileId'], force=True)
    readFile = File().load(read['fileId'], force=True)
    seedFile = (File().load(case['seedFileId'], force=True)
                if case.get('seedFileId') else None)
    crashed = False
    with tempfile.TemporaryDirectory(prefix='janusm-check-') as tmp:
        try:
            seedPath = _copy(seedFile, tmp, 'seed') if seedFile is not None else None
            report = checker.check_files(_copy(readFile, tmp, 'read'),
                                         _copy(ctFile, tmp, 'ct'), cfg,
                                         seed_path=seedPath).to_dict()
        except Exception as exc:  # noqa: BLE001 - a read that cannot be checked goes back
            crashed = True
            report = {'passed': False, 'errors': [f'The read could not be checked: {exc}'],
                      'warnings': [], 'summary': f'Failed the Janus-M read check: {exc}',
                      'border_protocol': BORDER_PROTOCOL}
    to, flagged, summary = decide(report, read.get('attempts'), crashed=crashed)
    moved = JanusMRead().transition(
        read, to, check=report, checkSummary=summary, flagged=flagged,
        flagReasons=list(report.get('errors') or []) if flagged else [],
        checkedAt=datetime.datetime.now(datetime.timezone.utc))
    if moved is not None and to == protocol.ACCEPTED:
        if read.get('third'):
            JanusMCase().recordThirdAccepted(read['caseId'])   # never a reference read
        else:
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
