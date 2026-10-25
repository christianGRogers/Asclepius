"""Bridge, Round 10 (proposal; binding only if the judge adopts it): the D35 pool decision set.

What D35 asks for: about 15 % of the non-sealed, non-ImageCHD pool patients, drawn at patient level by salted hash
within source, frozen before any read of them is looked at or trained on. Their reads decide fine-tune and
recipe questions (A17, A22) and are never trained on.

What this draws, and why (Bridge v9 §2):
* **Size: 35 patients** = 15 % of the 235 real non-sealed, non-ImageCHD patients (D32's patient rule;
  counts.py). The "about 347" on #43 counted the retired name rule and included ImageCHD.
* **Universe: the primary stratum, outside the seal and its 200-patient step** (``extension_order[:50]``), which
  leaves 111 patients. The spacing-suspect sets cannot be scored in mm (D29) and ImageCHD is excluded by D35.
  Drawing outside the whole 100-patient reserve instead would leave 61 patients from five sources (71 %
  Taiwan); outside the 200 step the set spans eight sources.
* **The reserve stays 100 patients and stays intact.** Decision patients are looked at, so none can ever join the
  seal. The 250 step is therefore re-stated, before any read exists, as the first 50 patients of
  ``extension_order[50:]`` that are not decision patients, continued if needed by the Round 9 rule (round-robin
  by source, smallest sha256(seal salt + patient)) over the primary patients the order never listed. This is
  D32's skip rule, applied to decision patients instead of sealed ones; the seal's salted ranking is kept.
* **Draw:** proportional allocation by source over those 61 (largest remainder), then within each source the
  patients with the smallest sha256(SALT + patient) are taken. The salt is fixed in this file before the draw.
* **Scoring volume:** the patient's first volume in the D23 serving order (``pool-2026-10.txt``), so its reads
  exist as early as the queue allows. Every volume of a decision patient is withheld from training.

Usage: python3 experiments/Bridge/r10/draw_d35.py --out experiments/Bridge/r10/decision_set_proposal.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
sys.path.insert(0, HERE)
from segtrain.pool_seal import ingest_patient  # noqa: E402
from counts import POOL, SEAL, stratum_of  # noqa: E402

SALT = 'asclepius-decision-round10-pool:'
N_DECISION = 35
SEAL_STEP = 50         # extension_order[:50]: the 200 step (A30, D27); the decision set is drawn outside it
STEP2 = 50             # the 250 step, re-stated around the decision set


def sha(p: str) -> str:
    return hashlib.sha256((SALT + p).encode()).hexdigest()


def build(n=N_DECISION):
    vols = [ln.strip() for ln in open(POOL) if ln.strip() and not ln.startswith('#')]
    serve_pos = {v: i for i, v in enumerate(vols)}
    seal_raw = open(SEAL, 'rb').read()
    seal = json.loads(seal_raw)
    real = {v: ingest_patient(v[:-len('.nii.gz')]) for v in vols}
    members = defaultdict(list)
    for v in vols:
        members[real[v]].append(v)
    src = {p: m[0].split('__')[0] for p, m in members.items()}
    sealed = set(seal['primary']['patients']) | set(seal['report_only']['patients'])
    ext = list(seal['primary']['extension_order'])
    step1 = list(ext[:SEAL_STEP])
    eligible = sorted(p for p in members if stratum_of(src[p]) == 'primary' and p not in sealed
                      and p not in set(step1))
    by_src = defaultdict(list)
    for p in eligible:
        by_src[src[p]].append(p)
    for s in by_src:
        by_src[s].sort(key=sha)
    tot = len(eligible)
    quota = {s: n * len(v) / tot for s, v in by_src.items()}
    alloc = {s: int(q) for s, q in quota.items()}
    left = n - sum(alloc.values())
    for s in sorted(quota, key=lambda s: (-(quota[s] - int(quota[s])), s)):
        if left <= 0:
            break
        alloc[s] += 1
        left -= 1
    chosen = sorted(p for s, v in by_src.items() for p in v[:alloc[s]])
    chosen_set = set(chosen)
    # the 250 step: extension_order[50:] skipping decision patients, continued by the Round 9 rule
    seal_rank = lambda p: hashlib.sha256((seal['salt'] + p).encode()).hexdigest()  # noqa: E731
    in_order = set(ext)
    rest = defaultdict(list)
    for p in members:
        if (stratum_of(src[p]) == 'primary' and p not in sealed and p not in in_order and p not in chosen_set):
            rest[src[p]].append(p)
    for s_ in rest:
        rest[s_].sort(key=seal_rank)
    continuation = []
    while any(rest.values()):
        for s_ in sorted(rest):
            if rest[s_]:
                continuation.append(rest[s_].pop(0))
    step2 = [p for p in ext[SEAL_STEP:] + continuation if p not in chosen_set][:STEP2]
    skipped = [p for p in ext[SEAL_STEP:SEAL_STEP + STEP2] if p in chosen_set]
    scoring = {p: min(members[p], key=lambda v: serve_pos[v]) for p in chosen}
    volumes = sorted(v for p in chosen for v in members[p])
    positions = sorted(serve_pos[scoring[p]] for p in chosen)
    timing = {f'q{int(q * 100)}': positions[min(len(positions) - 1, int(q * len(positions)))]
              for q in (0.5, 0.8, 0.86, 1.0)}
    timing['served_by_242 (end of the QC-annotatable block)'] = sum(1 for x in positions if x < 242)
    timing['served_by_300'] = sum(1 for x in positions if x < 300)
    timing['served_by_400'] = sum(1 for x in positions if x < 400)
    timing['n_volumes_in_queue'] = len(vols)
    open_train = sorted(p for p in eligible if p not in chosen_set and p not in set(step2))
    trainable = {
        'primary_open_not_decision (patients)': len(open_train),
        'primary_open_not_decision (volumes)': sum(len(members[p]) for p in open_train),
        'spacing_suspect (patients/volumes)': [sum(1 for p in members if stratum_of(src[p]) == 'excluded'),
                                               sum(len(m) for p, m in members.items()
                                                   if stratum_of(src[p]) == 'excluded')],
        'imagechd_non_sealed (patients/volumes)': [
            sum(1 for p in members if src[p] == 'ImageCHD' and p not in sealed),
            sum(len(m) for p, m in members.items() if src[p] == 'ImageCHD' and p not in sealed)],
        'reserve_200_step_until_released (patients/volumes)': [
            len(step1), sum(len(members[p]) for p in step1)],
        'reserve_250_step_until_released (patients/volumes)': [
            len(step2), sum(len(members[p]) for p in step2)],
    }
    return {
        'what': 'D35 pool decision set, Bridge v9 proposal (Round 10). Never trained on; decides A17/A22 '
                'fine-tune questions on the pool. Frozen before any read of its patients is looked at.',
        'salt': SALT,
        'rule': 'primary stratum, not sealed, not in extension_order[:50]; proportional by source (largest '
                'remainder, ties by source name); within source the smallest sha256(salt + patient)',
        'patient_rule': 'segtrain.pool_seal.ingest_patient (D32/D33)',
        'inputs': {'pool_list': os.path.relpath(POOL, REPO),
                   'pool_list_sha256': hashlib.sha256(open(POOL, 'rb').read()).hexdigest(),
                   'seal': os.path.relpath(SEAL, REPO),
                   'seal_sha256': hashlib.sha256(seal_raw).hexdigest()},
        'n_eligible_patients': tot,
        'n_patients': len(chosen),
        'n_volumes': len(volumes),
        'allocation_[chosen,eligible]_by_source': {s: [alloc[s], len(v)] for s, v in sorted(by_src.items())},
        'patients': chosen,
        'volumes': volumes,
        'scoring_volume': scoring,
        'serve_position_of_scoring_volumes': timing,
        'reserve_200_step (extension_order[:50], unchanged)': step1,
        'reserve_250_step (extension_order[50:] skipping decision patients, then continued)': step2,
        'extension_entries_50_100_skipped_as_decision_patients': skipped,
        'n_continuation_used_in_250_step': sum(1 for p in step2 if p not in in_order),
        'reserve_volumes (never trained on or inspected until the seal size is decided)':
            sorted(v for p in step1 + step2 for v in members[p]),
        'trainable_pool_after_this': trainable,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    ap.add_argument('--n', type=int, default=N_DECISION)
    a = ap.parse_args()
    d = build(a.n)
    show = {k: v for k, v in d.items() if not isinstance(v, (list, dict)) or k.startswith(('allocation', 'serve',
                                                                                            'trainable', 'inputs',
                                                                                            'extension_entries'))}
    print(json.dumps(show, indent=1))
    if a.out:
        json.dump(d, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
