"""Foxtrot, Round 10: the sampling frame for the D35 decision set, counted on real patients.

Reads only the pool list and the seal file (names, no image, no read). Prints, per stratum and source, how many
real patients (segtrain.pool_seal.ingest_patient) and volumes are sealed, reserved for the seal's pre-registered
extension (A30/A31: the first 100 of the extension order), or open. Reconciles the two counts quoted on #43 and in
the wave-1 note. Output: results/d35_frame.json.
Usage: python experiments/Foxtrot/r10/d35_frame.py
"""
import json, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
from segtrain.pool_seal import ingest_patient, load_pool_seal  # noqa: E402

POOL = os.path.join(REPO, 'configs', 'segqueue14', 'pool-2026-10.txt')
SEAL = os.path.join(REPO, 'configs', 'segqueue14', 'sealed-pool-2026-10.json')
REPORT_ONLY = {'ImageCHD', 'ImageALCAPA'}
SPACING_SUSPECT = {'ImageALCAPA', 'HOCMvalvesSeg', 'CCA200-HF'}   # as experiments/Bridge/r9/seal_pool.py
RESERVED = 100                                                      # as experiments/Bridge/wave1/common.py


def stratum(src):
    return 'excluded' if src in SPACING_SUSPECT else 'report_only' if src in REPORT_ONLY else 'primary'


def main():
    vols = [l.strip() for l in open(POOL) if l.strip() and not l.startswith('#')]
    seal = json.load(open(SEAL))
    guard = load_pool_seal(SEAL)
    ext = list(seal['primary']['extension_order'])
    reserved = set(ext[:RESERVED])
    by_pat = defaultdict(list)
    for v in vols:
        by_pat[ingest_patient(v[:-len('.nii.gz')])].append(v)
    sealed_p = set(seal['primary']['patients']) | set(seal['report_only']['patients'])
    status = {}
    for p, vs in by_pat.items():
        sealed = p in sealed_p or any(guard.is_sealed(v) for v in vs)
        status[p] = 'sealed' if sealed else 'reserved' if p in reserved else 'open'
    src = {p: p.split('__')[0] for p in by_pat}
    table = Counter((stratum(src[p]), status[p]) for p in by_pat)
    vtable = Counter()
    for p, vs in by_pat.items():
        vtable[(stratum(src[p]), status[p])] += len(vs)
    per_src = defaultdict(Counter)
    for p in by_pat:
        if stratum(src[p]) == 'primary':
            per_src[src[p]][status[p]] += 1
    out = {
        'pool_volumes': len(vols), 'real_patients': len(by_pat),
        'patients': {f'{a}/{b}': n for (a, b), n in sorted(table.items())},
        'volumes': {f'{a}/{b}': n for (a, b), n in sorted(vtable.items())},
        'extension_order_len': len(ext), 'reserved_in_order': RESERVED,
        'extension_tail_beyond_reserve': ext[RESERVED:],
        'primary_by_source': {s: dict(c) for s, c in sorted(per_src.items())},
        'reconcile': {
            '#43 "about 347" = name-heuristic patients 517 - 150 sealed - 20 sealed ImageCHD': 517 - 150 - 20,
            'wave-1 note "198 open" = real 468 - 170 sealed - 100 reserved':
                len(by_pat) - sum(1 for p in by_pat if status[p] == 'sealed') - sum(1 for p in by_pat if status[p] == 'reserved'),
            'non-sealed, non-ImageCHD real patients (all strata)':
                sum(1 for p in by_pat if status[p] != 'sealed' and src[p] != 'ImageCHD'),
            'non-sealed primary real patients (reserve included)':
                sum(1 for p in by_pat if status[p] != 'sealed' and stratum(src[p]) == 'primary'),
            'open primary real patients (reserve excluded)':
                sum(1 for p in by_pat if status[p] == 'open' and stratum(src[p]) == 'primary'),
        },
    }
    os.makedirs(os.path.join(HERE, 'results'), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, 'results', 'd35_frame.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ('extension_tail_beyond_reserve',)}, indent=1))


if __name__ == '__main__':
    main()
