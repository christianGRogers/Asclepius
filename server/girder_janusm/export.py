"""``janusm-export``: one wave's accepted double reads, as an anchoring manifest (JA7,
JA47) with a record per read (border protocol v1).

``--wave`` is required: only cases an admin put in that wave
(``POST /janusm/admin/wave``) are exported, and a wave with no case is refused. For
every such case whose two reference reads are both accepted under border protocol 1,
writes both reads (``reads/``), any accepted third read (``third/``, JA47 rule 2;
``reference: false``, never in ``reads/``) and the case's seed into ``--out``, and a
``manifest.json`` that ``python -m janusm_reads.anchoring`` reads. Seeds come from
``--seeds-dir`` (the Fir seed job's output).

A read without ``border_protocol: 1`` was not drawn under protocol v1: it is skipped
and listed in the manifest's ``skippedReads``, and its case is not exported.

Each case row carries ``readRecords``, one per read, with what the analysis needs:
the reader, seeded or blank, seconds (summed over its submissions), attempts,
returns and crashes, flagged and its reasons, the read form (CAD-RADS 2.0 per vessel,
lesion points), the half-maximum offsets per border in the **canonical sign** (JA44:
+ = the region extends beyond the image half-maximum) and ``border_protocol``.
``halfMaxOffsets`` holds the reads' offsets (from their checks) and the seed's
(measured here on the case's CT, which is read and never copied out; off with
``--no-seed-offsets``).

    janusm-export --out /tmp/wave1 --seeds-dir /path/to/seeds --wave 1
    python -m janusm_reads.anchoring /tmp/wave1/manifest.json --out wave1-anchoring.json
"""

import argparse
import json
import os
import shutil
import tempfile

from girder.models.file import File
from janusm_reads import BORDER_PROTOCOL, protocol, readform

from .models import JanusMCase, JanusMRead
from .populate import SEED_SUFFIX


def _offsets(check):
    """Whole-border offsets (mm, canonical sign) from a stored check report."""
    return {name: border.get('offset_mm')
            for name, border in ((check or {}).get('borders') or {}).items()}


def readRecord(read, case):
    """One read, as the export writes it."""
    return {
        'reader': str(read['userId']),
        'seeded': bool(read.get('seeded')),
        'blank': not read.get('seeded'),
        'third': bool(read.get('third')),
        # JA47: a third read is for rule 2 only, never the reference standard.
        'reference': not read.get('third'),
        'seconds': float(read.get('seconds') or 0.0),
        'attempts': int(read.get('attempts') or 0),
        'returns': int(read.get('returns') or 0),
        'crashes': int(read.get('crashes') or 0),
        'flagged': bool(read.get('flagged')),
        'flagReasons': list(read.get('flagReasons') or []),
        # The read form, by the one mapping the table also reads it with (R5-S6 S13).
        **readform.read_form(read),
        'halfMaxOffsetsMm': _offsets(read.get('check')),
        'offsetSign': 'canonical',
        # A read stored before border protocol v1 carries none: it was not read under v1.
        'border_protocol': read.get('border_protocol'),
    }


def _download(fileId, path):
    with open(path, 'wb') as handle:
        for chunk in File().download(File().load(fileId, force=True), headers=False)():
            handle.write(chunk)
    return path


def _seedOffsets(case, seedPath):
    import nibabel as nib
    import numpy as np
    from janusm_reads import anchoring

    with tempfile.TemporaryDirectory(prefix='janusm-export-') as tmp:
        ctName = File().load(case['ctFileId'], force=True).get('name') or 'ct.nii.gz'
        ctPath = _download(case['ctFileId'], os.path.join(
            tmp, 'ct' + ('.nii' if ctName.lower().endswith('.nii') else '.nii.gz')))
        img = nib.load(ctPath)
        seed = np.asarray(nib.load(seedPath).dataobj).astype(np.int16)
        return anchoring.halfmax_offsets(seed, np.asarray(img.dataobj, dtype=np.float32),
                                         img.header.get_zooms()[:3])


class ExportRefused(SystemExit):
    """The export cannot run as asked; nothing was written."""


def export(outDir, seedsDir, wave, seedOffsets=True, out=print):
    wave = str(wave or '').strip()
    cases = list(JanusMCase().find({'wave': wave}, sort=[('priority', -1), ('serveOrder', 1)])
                 ) if wave else []
    if not cases:
        raise ExportRefused(f'REFUSED: wave {wave!r} has no Janus-M case; put cases in it '
                            'first (POST /janusm/admin/wave)')
    for sub in ('reads', 'third', 'seeds'):
        os.makedirs(os.path.join(outDir, sub), exist_ok=True)
    rows, skipped, offProtocol = [], [], []
    for case in cases:
        accepted = list(JanusMRead().find({'caseId': case['_id'], 'state': protocol.ACCEPTED},
                                          sort=[('assignedAt', 1)]))
        stale = [r for r in accepted if r.get('border_protocol') != BORDER_PROTOCOL]
        offProtocol += [{'case': case['name'], 'read': str(r['_id']),
                         'border_protocol': r.get('border_protocol')} for r in stale]
        accepted = [r for r in accepted if r.get('border_protocol') == BORDER_PROTOCOL]
        reads = [r for r in accepted if not r.get('third')]
        thirds = [r for r in accepted if r.get('third')]
        if len(reads) != 2:
            continue
        seed = os.path.join(seedsDir, case['name'] + SEED_SUFFIX)
        if not os.path.isfile(seed):
            skipped.append(case['name'])
            continue
        shutil.copyfile(seed, os.path.join(outDir, 'seeds', case['name'] + SEED_SUFFIX))
        paths = []
        for k, read in enumerate(reads, 1):
            rel = f"reads/{case['name']}__r{k}.nii.gz"
            _download(read['fileId'], os.path.join(outDir, rel))
            paths.append(rel)
        row = {'case': case['name'], 'blank': case['blank'],
               'seed': f"seeds/{case['name']}{SEED_SUFFIX}", 'reads': paths,
               'readRecords': [readRecord(r, case) for r in reads],
               'halfMaxOffsets': {'reads': [_offsets(r.get('check')) for r in reads]}}
        if seedOffsets:
            row['halfMaxOffsets']['seed'] = _seedOffsets(case, seed)
        if thirds:
            rel = f"third/{case['name']}__third.nii.gz"
            _download(thirds[0]['fileId'], os.path.join(outDir, rel))
            # JA47: a third read is for rule 2 only, never the reference standard.
            row['thirdRead'] = rel
            row['thirdReadRecord'] = readRecord(thirds[0], case)
        rows.append(row)
    manifest = {'wave': wave, 'border_protocol': BORDER_PROTOCOL, 'cases': rows,
                'skippedReads': offProtocol}
    with open(os.path.join(outDir, 'manifest.json'), 'w', encoding='utf-8') as handle:
        json.dump(manifest, handle, indent=1)
    out(f'wave {wave}: {len(rows)} double-read cases exported; {len(skipped)} without a '
        f'seed: {skipped[:5]}; {len(offProtocol)} reads skipped (not border protocol '
        f'{BORDER_PROTOCOL}): {offProtocol[:5]}')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(prog='janusm-export', description=__doc__.split('\n\n')[0])
    parser.add_argument('--out', required=True)
    parser.add_argument('--seeds-dir', required=True)
    parser.add_argument('--wave', required=True, help='the wave to export (never empty)')
    parser.add_argument('--no-seed-offsets', dest='seed_offsets', action='store_false',
                        help="skip measuring each seed's half-maximum offsets on its CT")
    args = parser.parse_args(argv)
    export(args.out, args.seeds_dir, args.wave, seedOffsets=args.seed_offsets)
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
