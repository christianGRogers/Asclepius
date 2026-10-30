"""``janusm-export``: one wave's accepted double reads, as an anchoring manifest (JA7).

For every case whose two reads are both accepted, writes both reads and the case's
seed into ``--out`` and a ``manifest.json`` that ``python -m janusm_reads.anchoring``
reads. Seeds come from ``--seeds-dir`` (the Fir seed job's output), because blank
cases' seeds are never on the server.

    janusm-export --out /tmp/wave1 --seeds-dir /path/to/seeds --wave 1
    python -m janusm_reads.anchoring /tmp/wave1/manifest.json --out wave1-anchoring.json
"""

import argparse
import json
import os
import shutil

from girder.models.file import File
from janusm_reads import protocol

from .models import JanusMCase, JanusMRead
from .populate import SEED_SUFFIX


def export(outDir, seedsDir, wave='', out=print):
    os.makedirs(os.path.join(outDir, 'reads'), exist_ok=True)
    os.makedirs(os.path.join(outDir, 'seeds'), exist_ok=True)
    rows, skipped = [], []
    for case in JanusMCase().find({}, sort=[('priority', -1), ('serveOrder', 1)]):
        reads = list(JanusMRead().find({'caseId': case['_id'], 'state': protocol.ACCEPTED},
                                       sort=[('assignedAt', 1)]))
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
            with open(os.path.join(outDir, rel), 'wb') as handle:
                for chunk in File().download(File().load(read['fileId'], force=True),
                                             headers=False)():
                    handle.write(chunk)
            paths.append(rel)
        rows.append({'case': case['name'], 'blank': case['blank'],
                     'seed': f"seeds/{case['name']}{SEED_SUFFIX}", 'reads': paths})
    manifest = {'wave': str(wave), 'cases': rows}
    with open(os.path.join(outDir, 'manifest.json'), 'w', encoding='utf-8') as handle:
        json.dump(manifest, handle, indent=1)
    out(f'{len(rows)} double-read cases exported; {len(skipped)} without a seed: {skipped[:5]}')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(prog='janusm-export', description=__doc__.split('\n\n')[0])
    parser.add_argument('--out', required=True)
    parser.add_argument('--seeds-dir', required=True)
    parser.add_argument('--wave', default='')
    args = parser.parse_args(argv)
    export(args.out, args.seeds_dir, args.wave)
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
