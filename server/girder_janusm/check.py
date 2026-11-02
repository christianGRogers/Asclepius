"""``janusm-check``: the automatic read check (border protocol v1) on every submitted
Janus-M read.

Each submitted read, its case's CT and its case's seed are copied to a scratch
directory and checked with ``janusm_reads.checker`` (label conventions and the
half-maximum rule). The seed is the served seed on a seeded case and the hidden
**check seed** on a blank one (JA66): the mitral plane is fitted to it, so a blank
read is never judged against a plane fitted to itself. Nothing of the check seed
goes back to the reader but the verdict and the height.

* A passed read is **accepted**.
* A failed read is **returned** to its reader with the reasons and the half-maximum
  profiles -- **once** (``protocol.MAX_RETURNS``, counted by ``returns``).
* A read that fails again once it has been returned is **accepted and flagged**
  (``flagged: true``, with ``flagReasons``). A flagged read counts in every analysis,
  and the flag is reported.
* A read the checker crashes on, or **could not check** (no mitral plane; JA66), goes
  back unflagged and is counted in ``crashes``, never in ``returns`` (JA68): the
  reader has not yet seen a real check. It is logged as an error for the PM
  ("COULD NOT BE CHECKED").

The plane comes from the seed only (JA76): the check runs ``queued``, so the read's
own gap is never a plane source, and a seed with no fittable 2-4 interface is "could
not be checked". A blank case with no ``checkSeedFileId`` is **refused** before any
check -- the same crash path, and the PM is alerted; ``janusm-populate
--backfill-check-seeds`` gives it its check seed.

Nothing else is written. Runs on the server against the database::

    janusm-check --once           # check what is waiting, then stop
    janusm-check --every 30       # keep checking (the systemd unit's mode)
"""

import argparse
import datetime
import logging
import os
import tempfile
import time

from girder.models.file import File
from janusm_reads import protocol

# R5-S11: ``decide`` lives in the girder-free half, so every CI job tests it.
from janusm_reads.outcome import ACCEPTED, CRASHED, FLAGGED, RETURNED, decide  # noqa: F401

from .models import JanusMCase, JanusMRead

logger = logging.getLogger(__name__)

#: JA76: why a blank case with no check seed is refused before checking. For the PM
#: (the log and the admin's check report) only.
NO_CHECK_SEED = ('The case has no check seed (checkSeedFileId), so its mitral plane '
                 'cannot be fitted: run janusm-populate --backfill-check-seeds.')
#: What the reader is told instead: nothing about the hidden seed (JA66).
NOT_CHECKED_FOR_READER = ('The read could not be checked on the server; the PM has been '
                          'told. Your read is kept: submit it again later.')


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
    """Check one submitted read and move it to accepted, returned or accepted-flagged."""
    from janusm_reads import BORDER_PROTOCOL, checker

    case = JanusMCase().load(read['caseId'], force=True)
    ctFile = File().load(case['ctFileId'], force=True)
    readFile = File().load(read['fileId'], force=True)
    seedId = JanusMCase().checkSeedId(case)      # JA66: the check seed on a blank case
    seedFile = File().load(seedId, force=True) if seedId else None
    crashed = False
    if seedFile is None:
        # JA76: refused before checking -- never fitted to the read itself.
        report = {'passed': False, 'errors': [], 'warnings': [],
                  'summary': NOT_CHECKED_FOR_READER,
                  'couldNotBeChecked': [NO_CHECK_SEED], 'border_protocol': BORDER_PROTOCOL}
    else:
        with tempfile.TemporaryDirectory(prefix='janusm-check-') as tmp:
            try:
                report = checker.check_files(_copy(readFile, tmp, 'read'),
                                             _copy(ctFile, tmp, 'ct'), cfg,
                                             seed_path=_copy(seedFile, tmp, 'seed'),
                                             queued=True).to_dict()
            except Exception as exc:  # noqa: BLE001 - a read that cannot be checked goes back
                crashed = True
                report = {'passed': False,
                          'errors': [f'The read could not be checked: {exc}'],
                          'warnings': [], 'summary': f'Failed the Janus-M read check: {exc}',
                          'border_protocol': BORDER_PROTOCOL}
    to, flagged, summary, outcome = decide(report, read.get('returns'), crashed=crashed)
    if outcome == CRASHED:
        # JA66 / JA68 / JA76: the PM is alerted; the read goes back without spending
        # its return.
        logger.error('Janus-M read %s of case %s COULD NOT BE CHECKED - tell the PM: %s',
                     read['_id'], case.get('name'),
                     ' '.join(report.get('couldNotBeChecked') or []) or summary)
    inc = {'crashes': 1} if outcome == CRASHED else {'returns': 1} if outcome == RETURNED \
        else {}
    moved = JanusMRead().transition(
        read, to, inc=inc, check=report, checkSummary=summary, flagged=flagged,
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
        if moved.get('crashes', 0) > read.get('crashes', 0):
            out(f"{read['_id']}: COULD NOT BE CHECKED - tell the PM")
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
