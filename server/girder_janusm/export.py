"""``janusm-export``: one wave's accepted double reads, as an anchoring manifest (JA7,
JA47) with a record per read (border protocol v1).

For every case whose two reference reads are both accepted, writes both reads, any
accepted third read (JA47 rule 2) and the case's seed into ``--out``, and a
``manifest.json`` that ``python -m janusm_reads.anchoring`` reads. Seeds come from
``--seeds-dir`` (the Fir seed job's output), because blank cases' seeds are never on
the server.

Each case row carries ``readRecords``, one per read, with what the analysis needs:
the reader, seeded or blank, seconds, attempts, flagged and its reasons, the read
form (CAD-RADS 2.0 per vessel, lesion points), the half-maximum offsets per border
in the **canonical sign** (JA44: + = the region extends beyond the image
half-maximum) and ``border_protocol``. ``halfMaxOffsets`` holds the reads' offsets
(from their checks) and, with ``--seed-offsets``, the seed's (measured here on the
case's CT, which is read and never copied out).

    janusm-export --out /tmp/wave1 --seeds-dir /path/to/seeds --wave 1
    python -m janusm_reads.anchoring /tmp/wave1/manifest.json --out wave1-anchoring.json
"""

import argparse
import json
import os
import shutil
import tempfile

from girder.models.file import File
from janusm_reads import BORDER_PROTOCOL, protocol

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
        'seconds': float(read.get('seconds') or 0.0),
        'attempts': int(read.get('attempts') or 0),
        'flagged': bool(read.get('flagged')),
        'flagReasons': list(read.get('flagReasons') or []),
        'cadrads': dict(read.get('cadrads') or {}),
        'lesionPoints': dict(read.get('lesionPoints') or {}),
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


def export(outDir, seedsDir, wave='', seedOffsets=False, out=print):
    os.makedirs(os.path.join(outDir, 'reads'), exist_ok=True)
    os.makedirs(os.path.join(outDir, 'seeds'), exist_ok=True)
    rows, skipped = [], []
    for case in JanusMCase().find({}, sort=[('priority', -1), ('serveOrder', 1)]):
        accepted = list(JanusMRead().find({'caseId': case['_id'], 'state': protocol.ACCEPTED},
                                          sort=[('assignedAt', 1)]))
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
            rel = f"reads/{case['name']}__third.nii.gz"
            _download(thirds[0]['fileId'], os.path.join(outDir, rel))
            # JA47: a third read is for rule 2 only, never the reference standard.
            row['thirdRead'] = rel
            row['thirdReadRecord'] = readRecord(thirds[0], case)
        rows.append(row)
    manifest = {'wave': str(wave), 'border_protocol': BORDER_PROTOCOL, 'cases': rows}
    with open(os.path.join(outDir, 'manifest.json'), 'w', encoding='utf-8') as handle:
        json.dump(manifest, handle, indent=1)
    out(f'{len(rows)} double-read cases exported; {len(skipped)} without a seed: {skipped[:5]}')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(prog='janusm-export', description=__doc__.split('\n\n')[0])
    parser.add_argument('--out', required=True)
    parser.add_argument('--seeds-dir', required=True)
    parser.add_argument('--wave', default='')
    parser.add_argument('--seed-offsets', action='store_true',
                        help="measure each seed's half-maximum offsets on its case's CT")
    args = parser.parse_args(argv)
    export(args.out, args.seeds_dir, args.wave, seedOffsets=args.seed_offsets)
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
