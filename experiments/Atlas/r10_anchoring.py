"""Atlas, Round 10 (#113): what seed-anchored team reads do to A10, scored with the pinned tF1 on phantoms.

D26 starts every class of a pool read as a full copy of the binary TotalSegmentator seed; the reader cuts it to
each vessel and may redraw the outline freely (D12). Two things can carry over from the seed into the reads:
  * its **width** (outline): Janus 0 already draws the lumen about one voxel inside ImageCAS-X's (#43);
  * its **extent**: where each vessel stops distally. A reader who keeps the seed's distal ends instead of
    following the vessel as far as the contrast allows draws a shorter tree than ImageCAS-X's convention.
A10 (D6) compares model-vs-read tF1 with inter-read tF1 at a 0.05 margin. If both reads keep the same seed's
extent, inter-read agreement is inflated by the shared anchor while a model that traces the ImageCAS-X extent
(Janus 0) is charged for every millimetre it draws past the read.

Phantoms: Bridge's wave-1 tree (experiments/Bridge/wave1/synth.py: LM, LAD, LCx, RCA tubes beside an aorta, 0.5 mm
grid) and the scoring of score_wave1.py (segtrain.tf1 at the A1c pin, aorta ostium). Per case:
  truth   the full tree (the ImageCAS-X convention: as far as the vessel goes);
  seed    the tree with its own jitter and width, each vessel's last segment cut to s ~ U(s0 - 0.1, s0 + 0.1);
  read k  starts at the seed's ends and extends each vessel by e_k of what the seed misses,
          e_k ~ U(e - 0.15, e + 0.15) clipped to [0, 1], with its own small jitter; outline redrawn (r 2.9-3.5);
  model   human-level by construction: a third reader who follows each vessel to 85-100 % of its end,
          independent of the seed, the readers' width (width is checked apart, see width_check).
Scored per class: inter-read (symmetric), model-vs-read (mean over both reads), seed-vs-read, model-vs-truth.
The grid crosses seed extent s0 with reader extension e (e = 1: the reads follow the vessel, independent of the
seed's extent; e = 0: fully anchored). Width alone is checked first: the model eroded by one voxel against the
truth.

    python experiments/Atlas/r10_anchoring.py --cases 24 --out experiments/Atlas/r10/anchoring.json --np 4
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'experiments', 'Bridge', 'wave1'))
sys.path.insert(0, os.path.join(REPO, 'src'))

import common as C  # noqa: E402
import score_wave1 as S  # noqa: E402
import synth  # noqa: E402

NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
S0 = (0.5, 0.8)
E = (0.0, 0.5, 1.0)
CELLS = [(s0, e) for s0 in S0 for e in E] + [(1.0, 1.0)]


def dice(a, b):
    a, b = a > 0, b > 0
    return 2 * (a & b).sum() / max(a.sum() + b.sum(), 1)


def one_case(args):
    s0, e, i = args
    rng = np.random.default_rng([int(s0 * 100), int(e * 100), i])
    sp = synth.SP
    truth, aorta = synth.tree(rng)
    s = {c: float(np.clip(rng.uniform(s0 - 0.1, s0 + 0.1), 0.05, 1.0)) for c in ('lad', 'lcx', 'rca')}
    seed, _ = synth.tree(rng, jitter=1.0, lad_len=s['lad'], lcx_len=s['lcx'], rca_len=s['rca'],
                         r=rng.uniform(2.4, 4.2))
    reads = []
    for _ in range(2):
        ek = {c: float(np.clip(rng.uniform(e - 0.15, e + 0.15), 0.0, 1.0)) for c in s}
        lens = {c: s[c] + ek[c] * (1.0 - s[c]) for c in s}
        r, _ = synth.tree(rng, jitter=0.8, lad_len=lens['lad'], lcx_len=lens['lcx'], rca_len=lens['rca'],
                          r=rng.uniform(2.9, 3.5))
        reads.append(r)
    # a human-level model: drawn as a third reader who follows each vessel to its end (e_k ~ U(0.85, 1.0) of the
    # full tree, independent of the seed). Same width as the readers: width is checked apart (width_check), because
    # a thinner phantom tube with its own jitter loses contact where synth.tree carves the aorta, a phantom artefact
    m_lens = {c: float(rng.uniform(0.85, 1.0)) for c in s}
    model, _ = synth.tree(rng, jitter=0.8, lad_len=m_lens['lad'], lcx_len=m_lens['lcx'], rca_len=m_lens['rca'],
                          r=rng.uniform(2.9, 3.5))
    inter = S.pair(reads[0], reads[1], sp, aorta)[0]
    mvr = S.mean_over([S.pair(rd, model, sp, aorta, symmetric=False) for rd in reads])[0]
    svr = S.mean_over([S.pair(rd, seed, sp, aorta) for rd in reads])[0]
    mvt = S.pair(truth, model, sp, aorta, symmetric=False)[0]
    rvt = S.mean_over([S.pair(truth, rd, sp, aorta, symmetric=False) for rd in reads])[0]
    return {'s0': s0, 'e': e, 'i': i, 'inter': inter, 'model_vs_read': mvr, 'seed_vs_read': svr,
            'model_vs_truth': mvt, 'read_vs_truth': rvt, 'dice_model_truth': float(dice(model, truth)),
            'dice_read_truth': float(np.mean([dice(rd, truth) for rd in reads]))}


def width_check(n=6):
    from scipy import ndimage
    out = []
    for i in range(n):
        rng = np.random.default_rng([7, i])
        truth, aorta = synth.tree(rng)
        for name, op in (('eroded 1 voxel', ndimage.binary_erosion), ('dilated 1 voxel', ndimage.binary_dilation)):
            m = op(truth > 0)
            lab = np.where(m, ndimage.grey_dilation(truth, size=3) if name.startswith('dil') else truth, 0)
            per = S.pair(truth, lab, synth.SP, aorta, symmetric=False)[0]
            out.append({'case': i, 'op': name, 'tf1_macro': float(np.mean(list(per.values()))),
                        'dice': float(dice(lab, truth)), 'volume_ratio': float((lab > 0).sum() / (truth > 0).sum())})
    agg = {}
    for op in ('eroded 1 voxel', 'dilated 1 voxel'):
        rows = [r for r in out if r['op'] == op]
        agg[op] = {k: round(float(np.mean([r[k] for r in rows])), 4) for k in ('tf1_macro', 'dice', 'volume_ratio')}
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', type=int, default=16)
    ap.add_argument('--np', type=int, default=4)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    C.check_tf1_pin()
    width = width_check()
    print('width check (model = truth eroded/dilated by one voxel):', json.dumps(width))
    jobs = [(s0, e, i) for s0, e in CELLS for i in range(a.cases)]
    with Pool(a.np) as p:
        rows = p.map(one_case, jobs)
    cells = []
    for s0, e in CELLS:
        if True:
            rr = [r for r in rows if r['s0'] == s0 and r['e'] == e]
            cell = {'s0': s0, 'e': e, 'n': len(rr)}
            for key in ('inter', 'model_vs_read', 'seed_vs_read', 'model_vs_truth', 'read_vs_truth'):
                cell[key] = {NAMES[c]: round(float(np.mean([r[key][c] for r in rr if c in r[key]])), 4)
                             for c in NAMES}
            cell['delta'] = {k: round(cell['model_vs_read'][k] - cell['inter'][k], 4) for k in NAMES.values()}
            # per-case SD of the contrast, for the power model
            cell['sd_contrast'] = {NAMES[c]: round(float(np.std([r['model_vs_read'][c] - r['inter'][c]
                                                                  for r in rr], ddof=1)), 4) for c in NAMES}
            cell['a31_2_seed_flag'] = {k: cell['seed_vs_read'][k] >= cell['inter'][k] - 0.02 for k in NAMES.values()}
            cell['d6_point_pass'] = {k: cell['delta'][k] > -0.05 for k in NAMES.values()}
            cell['dice_model_truth'] = round(float(np.mean([r['dice_model_truth'] for r in rr])), 4)
            cells.append(cell)
    res = {'width_check': width, 'cells': cells, 'rows': rows,
           'tf1_pin': C.TF1_PIN}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(res, open(a.out, 'w'), indent=1)
    print(f"{'s0':>4} {'e':>5} | {'inter':>22} | {'model-vs-read':>22} | {'delta (LAD/LCx/RCA)':>22} | seed flag | D6")
    for c in cells:
        f3 = lambda d: '/'.join(f"{d[k]:.3f}" for k in ('LAD', 'LCx', 'RCA'))  # noqa: E731
        print(f"{c['s0']:4.1f} {c['e']:5.2f} | {f3(c['inter']):>22} | {f3(c['model_vs_read']):>22} | "
              f"{f3(c['delta']):>22} | {''.join('Y' if c['a31_2_seed_flag'][k] else '.' for k in ('LAD', 'LCx', 'RCA'))}"
              f" | {''.join('P' if c['d6_point_pass'][k] else 'F' for k in ('LAD', 'LCx', 'RCA'))}")


if __name__ == '__main__':
    main()
