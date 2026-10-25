"""Bridge, Round 10: as the D23 queue is read in order, what exists for Janus 1?

At each queue position q (the first q volumes of ``pool-2026-10.txt`` have both reads approved), counts:
  * decision patients (D35 proposal) whose scoring volume is read;
  * open primary patients read (A31 measurements: decision + open primary, never sealed or reserved);
  * trainable reads: volumes of patients that are neither sealed, reserved nor decision patients, by stratum;
  * reserve volumes read (trainable only once the seal size is decided and the rest is released).
Sealed volumes are read by the team like any other (A30) and are counted only to show the queue's pace.

Usage: python3 experiments/Bridge/r10/queue_timeline.py --out experiments/Bridge/r10/queue_timeline.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
sys.path.insert(0, HERE)
from segtrain.pool_seal import ingest_patient  # noqa: E402
from counts import POOL, SEAL, stratum_of  # noqa: E402

PROPOSAL = os.path.join(HERE, 'decision_set_proposal.json')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    a = ap.parse_args()
    vols = [ln.strip() for ln in open(POOL) if ln.strip() and not ln.startswith('#')]
    seal = json.load(open(SEAL))
    dec = json.load(open(PROPOSAL))
    sealed = set(seal['primary']['patients']) | set(seal['report_only']['patients'])
    decision = set(dec['patients'])
    scoring = set(dec['scoring_volume'].values())
    step1 = set(dec['reserve_200_step (extension_order[:50], unchanged)'])
    step2 = set(dec['reserve_250_step (extension_order[50:] skipping decision patients, then continued)'])
    rows = []
    for q in (50, 100, 150, 200, 242, 300, 350, 400, 450, 500, 550, 600, 675):
        c = {'q': q, 'sealed_vols': 0, 'decision_scoring_read': 0, 'decision_vols': 0, 'reserve200_vols': 0,
             'reserve250_vols': 0, 'train_primary_vols': 0, 'train_imagechd_vols': 0, 'train_suspect_vols': 0}
        pats_open_primary = set()
        for v in vols[:q]:
            p = ingest_patient(v[:-len('.nii.gz')])
            st = stratum_of(v.split('__')[0])
            if p in sealed:
                c['sealed_vols'] += 1
            elif p in decision:
                c['decision_vols'] += 1
                c['decision_scoring_read'] += v in scoring
                pats_open_primary.add(p)
            elif p in step1:
                c['reserve200_vols'] += 1
            elif p in step2:
                c['reserve250_vols'] += 1
            elif st == 'primary':
                c['train_primary_vols'] += 1
                pats_open_primary.add(p)
            elif st == 'report_only':
                c['train_imagechd_vols'] += 1
            else:
                c['train_suspect_vols'] += 1
        c['a31_open_primary_patients'] = len(pats_open_primary)
        c['trainable_now_vols'] = c['train_primary_vols'] + c['train_imagechd_vols'] + c['train_suspect_vols']
        c['trainable_if_seal_150_vols'] = c['trainable_now_vols'] + c['reserve200_vols'] + c['reserve250_vols']
        c['trainable_if_seal_200_vols'] = c['trainable_now_vols'] + c['reserve250_vols']
        rows.append(c)
        print(json.dumps(c))
    if a.out:
        json.dump({'proposal': os.path.relpath(PROPOSAL, REPO), 'rows': rows}, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
