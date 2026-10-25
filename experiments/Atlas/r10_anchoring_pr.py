"""Atlas, Round 10 (#113): the signature of seed anchoring in model-vs-read tF1, split into recall and precision.

Companion to r10_anchoring.py (same phantoms and cells). If reads stop at the seed's distal ends and the model
follows the vessel, the model's extra centreline past the read's end is unmatched: model-vs-read *precision*
falls while *recall* (how much of the read the model covers) stays. A diagnostic that needs no seed naming.

    python experiments/Atlas/r10_anchoring_pr.py --cases 12 --out experiments/Atlas/r10/anchoring_pr.json
"""
import argparse, json, os, sys
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path[:0] = [os.path.join(REPO, 'experiments', 'Bridge', 'wave1'), os.path.join(REPO, 'src'), HERE]
import common as C  # noqa: E402
import synth  # noqa: E402
from segtrain import tf1 as T  # noqa: E402
CELLS = [(0.5, 0.0), (0.5, 0.5), (0.8, 0.0), (1.0, 1.0)]


def run(args):
    s0, e, i = args
    rng = np.random.default_rng([int(s0 * 100), int(e * 100), i])     # the same draws as r10_anchoring.py
    truth, aorta = synth.tree(rng)
    s = {c: float(np.clip(rng.uniform(s0 - 0.1, s0 + 0.1), 0.05, 1.0)) for c in ('lad', 'lcx', 'rca')}
    synth.tree(rng, jitter=1.0, lad_len=s['lad'], lcx_len=s['lcx'], rca_len=s['rca'], r=rng.uniform(2.4, 4.2))
    reads = []
    for _ in range(2):
        ek = {c: float(np.clip(rng.uniform(e - 0.15, e + 0.15), 0.0, 1.0)) for c in s}
        lens = {c: s[c] + ek[c] * (1.0 - s[c]) for c in s}
        reads.append(synth.tree(rng, jitter=0.8, lad_len=lens['lad'], lcx_len=lens['lcx'], rca_len=lens['rca'],
                                r=rng.uniform(2.9, 3.5))[0])
    m_lens = {c: float(rng.uniform(0.85, 1.0)) for c in s}
    model = synth.tree(rng, jitter=0.8, lad_len=m_lens['lad'], lcx_len=m_lens['lcx'], rca_len=m_lens['rca'],
                       r=rng.uniform(2.9, 3.5))[0]
    out = {'rec': [], 'prec': [], 'inter_rec': [], 'inter_prec': []}
    for rd, other in ((reads[0], reads[1]), (reads[1], reads[0])):
        rep = T.find_ostia(rd, synth.SP, aorta=aorta)
        t = T.tree_f1(rd, model, synth.SP, ostia=rep)
        u = T.tree_f1(rd, other, synth.SP, ostia=rep)
        out['rec'].append([t.recall.get(c, np.nan) for c in (2, 3, 4)])
        out['prec'].append([t.precision.get(c, np.nan) for c in (2, 3, 4)])
        out['inter_rec'].append([u.recall.get(c, np.nan) for c in (2, 3, 4)])
        out['inter_prec'].append([u.precision.get(c, np.nan) for c in (2, 3, 4)])
    return s0, e, {k: np.nanmean(v, 0).tolist() for k, v in out.items()}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--cases', type=int, default=12); ap.add_argument('--out', required=True)
    a = ap.parse_args(); C.check_tf1_pin()
    with Pool(4) as p:
        rows = p.map(run, [(s0, e, i) for s0, e in CELLS for i in range(a.cases)])
    res = []
    for s0, e in CELLS:
        rr = [r[2] for r in rows if r[0] == s0 and r[1] == e]
        cell = {'s0': s0, 'e': e, 'n': len(rr)}
        for k in ('rec', 'prec', 'inter_rec', 'inter_prec'):
            cell[k] = dict(zip(('LAD', 'LCx', 'RCA'), np.round(np.nanmean([r[k] for r in rr], 0), 3).tolist()))
        res.append(cell)
        print(s0, e, 'model rec', cell['rec'], 'prec', cell['prec'], '| inter rec', cell['inter_rec'], 'prec', cell['inter_prec'])
    json.dump(res, open(a.out, 'w'), indent=1)
