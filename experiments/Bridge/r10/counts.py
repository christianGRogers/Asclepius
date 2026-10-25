"""Bridge, Round 10: how many pool patients can the D35 decision set be drawn from?

Reconciles the two counts issue #113 quotes:
  * Atlas on #43: "about 50 of about 347 non-sealed, non-ImageCHD patients";
  * the wave-1 note: "198 open patients once the seal and its 100-patient extension reserve (D32) are set aside".

Everything is computed from the pool list and the seal file in force (D32/D33), with the project's patient rule
(``segtrain.pool_seal.ingest_patient``) and, for comparison, the Round 9 name heuristic. No image is read.

Usage: python3 experiments/Bridge/r10/counts.py [--out counts.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
from segtrain.pool_seal import ingest_patient  # noqa: E402

POOL = os.path.join(REPO, 'configs', 'segqueue14', 'pool-2026-10.txt')
SEAL = os.path.join(REPO, 'configs', 'segqueue14', 'sealed-pool-2026-10.json')
REPORT_ONLY = {'ImageCHD', 'ImageALCAPA'}                      # seal_pool.py (Round 9)
SPACING_SUSPECT = {'ImageALCAPA', 'HOCMvalvesSeg', 'CCA200-HF'}  # D29: out of A10 until re-gridded
_SUFFIX = re.compile(r'(_tp\d+|_p\d+|_(diast|syst)|_s\d+)$', re.I)


def stratum_of(src: str) -> str:
    return 'excluded' if src in SPACING_SUSPECT else 'report_only' if src in REPORT_ONLY else 'primary'


def name_rule(v: str) -> str:
    parts = v[:-len('.nii.gz')].split('__')
    return f'{parts[0]}__{_SUFFIX.sub("", parts[1] if len(parts) > 1 else parts[0])}'


def load():
    vols = [ln.strip() for ln in open(POOL) if ln.strip() and not ln.startswith('#')]
    seal = json.load(open(SEAL))
    return vols, seal


def table(vols, seal, reserve: int = 100):
    real = {v: ingest_patient(v[:-len('.nii.gz')]) for v in vols}
    src = {real[v]: v.split('__')[0] for v in vols}
    members = defaultdict(list)
    for v in vols:
        members[real[v]].append(v)
    sealed = set(seal['primary']['patients']) | set(seal['report_only']['patients'])
    ext = list(seal['primary']['extension_order'])
    reserved = set(ext[:reserve])
    rows = defaultdict(Counter)
    for p in members:
        s = src[p]
        st = stratum_of(s)
        if p in sealed:
            state = 'sealed'
        elif p in reserved:
            state = 'reserved'
        else:
            state = 'open'
        rows[st][state] += 1
        rows[st][state + '_volumes'] += len(members[p])
    by_source = defaultdict(Counter)
    for p in members:
        s = src[p]
        state = 'sealed' if p in sealed else 'reserved' if p in reserved else 'open'
        by_source[s][state] += 1
        by_source[s]['stratum:' + stratum_of(s)] = 1
    name_patients = {name_rule(v) for v in vols}
    return {'volumes': len(vols), 'real_patients': len(members), 'name_rule_patients': len(name_patients),
            'by_stratum': {k: dict(v) for k, v in rows.items()},
            'by_source': {k: dict(v) for k, v in sorted(by_source.items())},
            'extension_order_len': len(ext), 'reserve': reserve}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    a = ap.parse_args()
    vols, seal = load()
    t = table(vols, seal)
    bs = t['by_stratum']
    get = lambda st, k: bs.get(st, {}).get(k, 0)  # noqa: E731
    sealed_all = sum(get(s, 'sealed') for s in bs)
    recon = {
        'atlas_347': {
            'formula': 'name-rule patients - 150 sealed primary keys - 20 sealed ImageCHD',
            'value': t['name_rule_patients'] - 150 - 20,
            'note': 'counts on the Round 9 name heuristic (517), which D32 replaced, and still includes the '
                    'non-sealed ImageCHD and the spacing-suspect sets',
        },
        'wave1_198': {
            'formula': 'real patients - sealed (150 + 20 ImageCHD) - 100 reserved',
            'value': t['real_patients'] - sealed_all - get('primary', 'reserved'),
            'note': 'every stratum: includes non-sealed ImageCHD (report only) and spacing-suspect patients',
        },
        'non_sealed_non_imagechd_real': sum(get(s, 'open') + get(s, 'reserved') for s in ('primary', 'excluded'))
        + 0,
        'primary_non_sealed': get('primary', 'open') + get('primary', 'reserved'),
        'primary_open_outside_reserve': get('primary', 'open'),
        'primary_reserved': get('primary', 'reserved'),
        'excluded_non_sealed (spacing-suspect, untf1-able until re-gridded)':
            get('excluded', 'open') + get('excluded', 'reserved'),
        'report_only_non_sealed (ImageCHD)': get('report_only', 'open') + get('report_only', 'reserved'),
    }
    out = {'table': t, 'reconciliation': recon}
    print(json.dumps(recon, indent=1))
    print(json.dumps(t['by_stratum'], indent=1))
    if a.out:
        json.dump(out, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
