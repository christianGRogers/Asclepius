"""Delta, Round 10: where the D35 decision set can come from. Reads only the pool list and the seal file
(names, no image or read). Counts real patients (segtrain.pool_seal.ingest_patient) by stratum, seal state and
extension rank, per source, and checks the counts quoted on #43 / in the wave-1 note.

Usage: python3 experiments/Delta/r10/pool_census.py [--json out.json]"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
from segtrain.pool_seal import _patient_key, load_pool_seal, ingest_patient  # noqa: E402

POOL = os.path.join(REPO, 'configs/segqueue14/pool-2026-10.txt')
SEAL = os.path.join(REPO, 'configs/segqueue14/sealed-pool-2026-10.json')
REPORT_ONLY = {'ImageCHD', 'ImageALCAPA'}            # experiments/Bridge/r9/seal_pool.py
SPACING_SUSPECT = {'ImageALCAPA', 'HOCMvalvesSeg', 'CCA200-HF'}
RESERVED = 100                                        # experiments/Bridge/wave1/common.py EXTENSION_RESERVED


def stratum(src):
    return 'excluded' if src in SPACING_SUSPECT else 'report_only' if src in REPORT_ONLY else 'primary'


def census():
    vols = [ln.strip() for ln in open(POOL) if ln.strip() and not ln.startswith('#')]
    seal = load_pool_seal(SEAL)                       # checks the pinned sha256
    d = json.load(open(SEAL))
    stem = lambda v: v[:-len('.nii.gz')]  # noqa: E731
    real = {v: ingest_patient(stem(v)) for v in vols}
    members = defaultdict(list)
    for v in vols:
        members[real[v]].append(v)
    src = {p: p.split('__')[0] for p in members}
    ext = list(d['primary']['extension_order'])
    ext_rank = {p: i for i, p in enumerate(ext)}
    state = {}
    for p, vs in members.items():
        if any(seal.is_sealed(v) for v in vs):
            state[p] = 'sealed'
        elif p in ext_rank and ext_rank[p] < 50:
            state[p] = 'reserve_200'                  # ranks 1-50: the seal grows into these first
        elif p in ext_rank and ext_rank[p] < RESERVED:
            state[p] = 'reserve_250'                  # ranks 51-100
        elif p in ext_rank:
            state[p] = 'extension_tail'               # rank 101+: in the order but not reserved
        else:
            state[p] = 'open'
    tab = Counter((stratum(src[p]), state[p]) for p in members)
    by_src = defaultdict(Counter)
    for p in members:
        by_src[src[p]][state[p]] += 1
    name_rule = {_patient_key(stem(v)) for v in vols}
    return dict(
        n_volumes=len(vols), n_real_patients=len(members), n_name_rule_patients=len(name_rule),
        extension_order_len=len(ext),
        by_stratum_state={f'{a}/{b}': n for (a, b), n in sorted(tab.items())},
        by_source={s: dict(c) for s, c in sorted(by_src.items())},
        open_primary_volumes=sum(len(members[p]) for p in members
                                 if stratum(src[p]) == 'primary' and state[p] in ('open', 'extension_tail')),
        members={p: members[p] for p in members}, state=state, src=src)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json')
    a = ap.parse_args()
    c = census()
    out = {k: v for k, v in c.items() if k not in ('members', 'state', 'src')}
    print(json.dumps(out, indent=1))
    st = c['by_stratum_state']
    g = lambda k: st.get(k, 0)  # noqa: E731
    nonsealed_nonchd = sum(n for k, n in st.items() if not k.endswith('/sealed') and not k.startswith('report_only'))
    print('\nReconciling the counts:')
    print(f"  name-rule patients {c['n_name_rule_patients']} - 170 sealed keys = {c['n_name_rule_patients'] - 170}"
          "  (Atlas on #43: 'about 347'; pre-D32 heuristic)")
    print(f"  real patients {c['n_real_patients']}; non-sealed non-ImageCHD/ALCAPA real patients = {nonsealed_nonchd}")
    free = sum(n for k, n in st.items() if not k.endswith('/sealed') and not '/reserve' in k)
    print(f"  non-sealed, non-reserved real patients (all strata) = {free}  (wave-1 note: 198)")
    print(f"  primary: sealed {g('primary/sealed')}, reserve 1-50 {g('primary/reserve_200')}, "
          f"reserve 51-100 {g('primary/reserve_250')}, free {g('primary/open') + g('primary/extension_tail')}")
    if a.json:
        json.dump(out, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
