"""Crucible, Round 10: what seed-anchored reads do to A10 and to a fine-tune decided on them (A31.2, L5).

Question. Under D26 every class starts as a full copy of the TotalSegmentator seed. If readers keep the seed's
*extent* (where each vessel stops distally), what does A10 (model-vs-read tF1 minus inter-read tF1, D6) say about
(i) a model that traces the full ImageCAS-X extent (Janus 0-like) and (ii) a model that has learned the seed's
extent (what fine-tuning on anchored reads teaches)? And does a lumen-width difference (Janus 0 draws about one
voxel inside ImageCAS-X, #43) matter as much?

Method. Bridge's synthetic coronary phantom (experiments/Bridge/wave1/synth.py: four classes beside an aorta,
0.5 mm voxels), scored with the pinned segtrain.tf1 (A1c) and the A1 aorta ostium. Per truncation level tau (the
share of each LAD/LCx/RCA distal segment the seed keeps), 16 cases:
  truth            full extent, radius 3.2 voxels
  reads, anchored  two readers keep the seed extent (tau x U(0.95, 1)), own path jitter 0.8 voxel
  reads, independent  two readers draw the true extent (U(0.85, 1)), own jitter 0.8 voxel
  model, full      full extent, jitter 0.8, radius 2.6 (one voxel thinner in diameter: Janus 0's width bias)
  model, seed-like the seed's extent tau, jitter 0.8, radius 2.6
Synthetic: the effect sizes are the phantom's, not the pool's. CPU only; no real data.
Usage: python3 r10_seed_extent.py > r10_seed_extent.json
"""
from __future__ import annotations

import json
import os
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
sys.path.insert(0, os.path.join(REPO, 'experiments', 'Bridge', 'wave1'))

import synth  # noqa: E402  (Bridge's phantom, unchanged)
from segtrain import tf1 as T  # noqa: E402

SP = synth.SP
TAUS = (1.0, 0.8, 0.6, 0.4)
N = 16
CLS = (1, 2, 3, 4)


def one_way(ref, pred, aorta):
    rep = T.find_ostia(ref, SP, aorta=aorta)
    t = T.tree_f1(ref, pred, SP, ostia=rep)
    return {c: (float(t.per_class[c]), float(t.recall[c]), float(t.precision[c]))
            for c in CLS if c in t.per_class and np.isfinite(t.per_class[c])}


def sym(a, b, aorta):
    x, y = one_way(a, b, aorta), one_way(b, a, aorta)
    return {c: float(np.mean([x[c][0], y[c][0]])) for c in CLS if c in x and c in y}


def vs_reads(reads, pred, aorta):
    """A10's left side: the model scored against each read as reference, averaged."""
    ws = [one_way(r, pred, aorta) for r in reads]
    return {c: tuple(float(np.mean([w[c][k] for w in ws])) for k in range(3)) for c in CLS if all(c in w for w in ws)}


def skel_len(m, c):
    return int(T._skeletonise(m == c).sum())


def case(args):
    tau, i = args
    rng = np.random.default_rng(1000 * int(tau * 100) + i)
    truth, aorta = synth.tree(rng)
    L = lambda lo, hi: rng.uniform(lo, hi)
    anch = [synth.tree(rng, jitter=0.8, lad_len=tau * L(0.95, 1), lcx_len=tau * L(0.95, 1),
                       rca_len=tau * L(0.95, 1))[0] for _ in range(2)]
    indep = [synth.tree(rng, jitter=0.8, lad_len=L(0.85, 1), lcx_len=L(0.85, 1), rca_len=L(0.85, 1))[0]
             for _ in range(2)]
    full = synth.tree(rng, jitter=0.8, r=2.6)[0]
    seedlike = synth.tree(rng, jitter=0.8, r=2.6, lad_len=tau, lcx_len=tau, rca_len=tau)[0]
    # width-only control: the full model drawn at the readers' radius
    full_w = synth.tree(rng, jitter=0.8, r=3.2)[0]
    seed_ref = synth.tree(rng, lad_len=tau, lcx_len=tau, rca_len=tau)[0]
    out = {'tau': tau, 'i': i,
           'centreline_kept': {c: skel_len(seed_ref, c) / max(skel_len(truth, c), 1) for c in CLS},
           'inter_anch': sym(*anch, aorta), 'inter_indep': sym(*indep, aorta),
           'full_vs_anch': vs_reads(anch, full, aorta), 'seedlike_vs_anch': vs_reads(anch, seedlike, aorta),
           'full_vs_indep': vs_reads(indep, full, aorta), 'seedlike_vs_indep': vs_reads(indep, seedlike, aorta),
           'fullw_vs_indep': vs_reads(indep, full_w, aorta),
           'full_vs_truth': {c: v[0] for c, v in one_way(truth, full, aorta).items()},
           'seedlike_vs_truth': {c: v[0] for c, v in one_way(truth, seedlike, aorta).items()}}
    return out


def summarise(rows):
    out = []
    for tau in TAUS:
        R = [r for r in rows if r['tau'] == tau]
        s = {'tau': tau}
        for c, name in zip(CLS, ('LM', 'LAD', 'LCx', 'RCA')):
            def m(key, k=None):
                v = [(r[key][c] if k is None else r[key][c][k]) for r in R if c in r[key]]
                return round(float(np.mean(v)), 4) if v else None
            d_full_anch = [r['full_vs_anch'][c][0] - r['inter_anch'][c] for r in R
                           if c in r['full_vs_anch'] and c in r['inter_anch']]
            d_seed_anch = [r['seedlike_vs_anch'][c][0] - r['inter_anch'][c] for r in R
                           if c in r['seedlike_vs_anch'] and c in r['inter_anch']]
            d_full_ind = [r['full_vs_indep'][c][0] - r['inter_indep'][c] for r in R
                          if c in r['full_vs_indep'] and c in r['inter_indep']]
            d_fullw_ind = [r['fullw_vs_indep'][c][0] - r['inter_indep'][c] for r in R
                           if c in r['fullw_vs_indep'] and c in r['inter_indep']]
            s[name] = dict(
                centreline_kept=round(float(np.mean([r['centreline_kept'][c] for r in R])), 3),
                inter_anchored=m('inter_anch'), inter_independent=m('inter_indep'),
                full_vs_anchored_tf1=m('full_vs_anch', 0), full_vs_anchored_recall=m('full_vs_anch', 1),
                full_vs_anchored_precision=m('full_vs_anch', 2),
                seedlike_vs_anchored_tf1=m('seedlike_vs_anch', 0),
                A10_contrast_full_model_anchored=round(float(np.mean(d_full_anch)), 4),
                A10_contrast_seedlike_model_anchored=round(float(np.mean(d_seed_anch)), 4),
                A10_contrast_full_model_independent=round(float(np.mean(d_full_ind)), 4),
                A10_contrast_full_model_independent_same_width=round(float(np.mean(d_fullw_ind)), 4),
                full_vs_truth=m('full_vs_truth'), seedlike_vs_truth=m('seedlike_vs_truth'))
        out.append(s)
    return out


if __name__ == '__main__':
    jobs = [(t, i) for t in TAUS for i in range(N)]
    with Pool(min(8, os.cpu_count() or 2)) as p:
        rows = p.map(case, jobs)
    json.dump({'n_per_level': N, 'summary': summarise(rows), 'rows': rows}, sys.stdout, indent=1, default=float)
