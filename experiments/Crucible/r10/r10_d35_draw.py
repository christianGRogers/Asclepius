"""Crucible, Round 10: a proposed D35 decision set, and when its reads arrive in the D23 serve order.

Rule (pre-registered in Crucible v11 §2):
- population: the **primary-stratum** pool patients that are **not sealed** (D27/D32/D33), as the project's guard
  groups them (segtrain.pool_seal.ingest_patient). ImageCHD is out (D35); the three spacing-suspect sources
  (ImageALCAPA, HOCMvalvesSeg, CCA200-HF) are out because a mm-based tF1 on a wrong grid decides nothing (D29 keeps
  them out of A10 for the same reason). The 100 reserved extension patients are **in** the population.
- size: 35 patients.
- draw: within source, by sha256(SALT + patient id) ascending; per-source quota by largest remainder of
  35 x n_source / N, at least one patient from every source with >= 5 eligible patients (the seal's own rule,
  experiments/Bridge/r9/seal_pool.py).
- every volume of a drawn patient is in the set; decisions score the patient's first volume in serve order (as
  the seal does, `scoring_volume`); a patient's other volumes are reported, never trained on.
- the seal's extension order is used **skipping D35 patients** (as D32 skipped already-sealed patients). The seal
  file is not changed by this script.

Also: for each D35 patient and each training patient, the serve position of its scoring volume in
configs/segqueue14/pool-2026-10.txt (D23 order, unchanged by D30), so the plan can say when wave-1 reads suffice.
CPU only; reads two config files; opens no image or read. Usage: python3 r10_d35_draw.py > d35_proposal.json
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
from segtrain.pool_seal import ingest_patient, SEAL_SHA256  # noqa: E402

SALT = 'asclepius-d35-round10:'
SIZE = 35
SEAL = os.path.join(REPO, 'configs', 'segqueue14', 'sealed-pool-2026-10.json')
POOL = os.path.join(REPO, 'configs', 'segqueue14', 'pool-2026-10.txt')
REPORT_ONLY = {'ImageCHD', 'ImageALCAPA'}
SPACING = {'ImageALCAPA', 'HOCMvalvesSeg', 'CCA200-HF'}
RESERVE = 100


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def main():
    assert sha(SEAL) == SEAL_SHA256, 'seal file is not the pinned D32 seal'
    d = json.load(open(SEAL))
    vols = [l.strip() for l in open(POOL) if l.strip() and not l.startswith('#')]
    pat = collections.OrderedDict()
    for i, v in enumerate(vols):
        pat.setdefault(ingest_patient(v[:-len('.nii.gz')]), []).append((i, v))
    src = lambda p: p.split('__')[0]
    sealed = set(d['primary']['patients']) | set(d['report_only']['patients'])
    ext = list(d['primary']['extension_order'])
    reserve = ext[:RESERVE]
    eligible = [p for p in pat if src(p) not in SPACING | REPORT_ONLY and p not in sealed]
    by = collections.defaultdict(list)
    for p in eligible:
        by[src(p)].append(p)
    N = len(eligible)
    quota = {s: SIZE * len(v) / N for s, v in by.items()}
    alloc = {s: int(q) for s, q in quota.items()}
    for s, v in by.items():
        if len(v) >= 5 and alloc[s] == 0:
            alloc[s] = 1
    rest = SIZE - sum(alloc.values())
    for s in sorted(quota, key=lambda s: (-(quota[s] - int(quota[s])), s)):
        if rest <= 0:
            break
        if alloc[s] < min(len(by[s]), int(quota[s]) + 1):
            alloc[s] += 1
            rest -= 1
    assert sum(alloc.values()) == SIZE, alloc
    rank = lambda p: hashlib.sha256((SALT + p).encode()).hexdigest()
    chosen = []
    for s in sorted(by):
        chosen += sorted(by[s], key=rank)[:alloc[s]]
    chosen_set = set(chosen)
    volumes = sorted(v for p in chosen for _, v in pat[p])
    scoring = {p: pat[p][0][1] for p in chosen}
    ext_after = [p for p in ext if p not in chosen_set]
    training = [p for p in eligible if p not in chosen_set]
    train_now = [p for p in training if p not in set(reserve)]

    def first_idx(p):
        return pat[p][0][0]

    # serve-order timeline: reads needed (2 per volume, every volume of the pool including sealed ones, in list
    # order) before k D35 patients / k training patients have both reads of their scoring volume
    cum_reads = {i: 2 * (i + 1) for i in range(len(vols))}

    def reads_until(group, k):
        idx = sorted(first_idx(p) for p in group)
        return cum_reads[idx[k - 1]] if k <= len(idx) else None
    timeline = {
        'd35': {k: reads_until(chosen, k) for k in (10, 20, 25, 30, 35)},
        'training_now (not D35, not reserve)': {k: reads_until(train_now, k) for k in (10, 20, 30, 40, 48)
                                               if k <= len(train_now)},
        'training_all (not D35, reserve released)': {k: reads_until(training, k) for k in (25, 50, 75, 100, 126)
                                                    if k <= len(training)},
        'total_reads_in_pool': 2 * len(vols),
    }
    out = {
        'salt': SALT, 'size': SIZE, 'seal_sha256': SEAL_SHA256, 'pool_list_sha256': sha(POOL),
        'population': 'primary stratum, not sealed (D27/D32/D33), reserve included; ImageCHD and spacing-suspect '
                      'sources excluded; patients as segtrain.pool_seal.ingest_patient groups them',
        'n_eligible': N, 'n_eligible_in_reserve': sum(p in set(reserve) for p in eligible),
        'allocation': {s: [alloc[s], len(by[s])] for s in sorted(by)},
        'patients': sorted(chosen), 'n_volumes': len(volumes), 'volumes': volumes,
        'scoring_volume': dict(sorted(scoring.items())),
        'from_reserve': sorted(p for p in chosen if p in set(reserve)),
        'extension_order_skipping_d35': ext_after,
        'max_seal_after_d35': 150 + len(ext_after),
        'training_patients': {'before_reserve_release': len(train_now), 'if_whole_reserve_released': len(training),
                              'sources_before_release': sorted({src(p) for p in train_now}),
                              'sources_after_release': len({src(p) for p in training})},
        'timeline_reads': timeline,
    }
    json.dump(out, sys.stdout, indent=1)


if __name__ == '__main__':
    main()
