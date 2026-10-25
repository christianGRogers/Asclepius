"""Bridge, Round 10 (A31.2, L5 groundwork): what seed-anchored reads do to A10, on real coronary trees.

D26 starts every class of a pool read as a full copy of the TotalSegmentator seed; annotators cut it down and may
redraw freely (D12). TotalSegmentator's coronary mask is 70.5 Dice against ImageCAS-X (arXiv:2608.30404, Table 2).
tF1 is centreline-based, so a lumen-*width* convention (Janus 0 draws about one voxel inside ImageCAS-X, #43) barely
moves it. What tF1 does see is **extent**: where each vessel stops distally, and which thin branches exist. A seed
that stops early, kept by readers who do not extend it, changes both sides of A10:

  inter-read tF1   two reads share the seed's stopping points        -> agreement rises;
  model-vs-read    a model that traces ImageCAS-X's extent runs past -> its precision against the read falls.

This measures both on the 80 ImageCAS-X val references (fold 0; non-sealed, inspected since Round 5). No CT, no
prediction, no pool data: every mask is a deterministic edit of the reference.

* **Truth T:** ImageCAS-X collapsed to four classes (``trillium/icx4/lib/territory.py``, D25).
* **Truncation trunc(T, r):** keep voxels whose nearest centreline point has radius >= r mm (radius = distance to
  the background along the skeleton), then only components touching an ostium of T. Thin distal vessels and
  thin side branches go first, as a seed that cannot see small vessels would lose them.
* **Seed S = trunc(T, r_s)**, r_s in {0.6, 0.8, 1.0} mm; its retained share of T's centreline is reported.
* **Reader i = trunc(T, u_i)**, u_i ~ U(0.20, 0.45) mm per reader and case (two readers who stop at slightly
  different calibres). An **anchored** reader stops at the seed instead: trunc(T, max(u_i, r_s)). alpha is the
  share of anchored readers: 0 (both independent), 1 (both anchored), 0.5 (one each; r_s = 0.8 only).
* **Model M = T:** a model with ImageCAS-X's extent (Janus 0 is trained on it; its val centreline recall against T
  is 0.94, #43).

Per case and class (tF1 @ 1.5 mm, segtrain.tf1, thick-rule ostia; aorta-free, so provisional, which is fine for a
paired contrast on identical references):
  inter = mean(tF1(R1 -> R2), tF1(R2 -> R1));  model = mean(tF1(R1 -> M), tF1(R2 -> M));  contrast = model - inter;
  seed  = mean(tF1(R1 -> S), tF1(S -> R1))   (A31.2's seed-vs-read, one read, both directions).

Usage: python3 experiments/Bridge/r10/anchoring.py --icx DIR_OF_cNNNN.nii.gz --out anchoring.json [--np 4]
Fetch the references (val 80 only, CC BY 4.0): python3 experiments/Bridge/r10/fetch_val_refs.py DIR
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
sys.path.insert(0, os.path.join(REPO, 'trillium', 'icx4', 'lib'))
import nibabel as nib  # noqa: E402
from scipy import ndimage  # noqa: E402
from skimage.morphology import skeletonize  # noqa: E402
from segtrain.tf1 import find_ostia, tree_f1  # noqa: E402
from territory import to_four  # noqa: E402

CLASSES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
SEED_R = (0.6, 0.8, 1.0)
READER_U = (0.20, 0.45)
SEALED = os.path.join(REPO, 'trillium', 'sealed_test.json')


def load(path):
    img = nib.load(path)
    icx = np.asarray(img.dataobj).astype(np.int16)
    sp = tuple(float(z) for z in img.header.get_zooms()[:3])
    four = to_four(icx, sp)
    nz = np.argwhere(four > 0)
    lo = np.maximum(nz.min(0) - 6, 0)
    hi = np.minimum(nz.max(0) + 7, four.shape)
    return four[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]], sp


def radius_map(T, sp):
    m = T > 0
    edt = ndimage.distance_transform_edt(m, sampling=sp)
    sk = skeletonize(m)
    if not sk.any():
        return edt
    _, idx = ndimage.distance_transform_edt(~sk, sampling=sp, return_indices=True)
    return np.where(m, edt[tuple(idx)], 0.0)


def truncate(T, rad, r, keep_zone):
    m = (T > 0) & (rad >= r)
    lab, n = ndimage.label(m, structure=np.ones((3, 3, 3)))
    if n == 0:
        return np.zeros_like(T)
    ids = np.unique(lab[keep_zone & m])
    ids = ids[ids > 0]
    return np.where(np.isin(lab, ids), T, 0).astype(T.dtype)


def cl_len(mask, sp):
    return int(skeletonize(mask > 0).sum())


def tf(ref, pred, sp):
    r = tree_f1(ref, pred, sp)
    return {CLASSES[c]: float(v) for c, v in r.per_class.items() if c in CLASSES and v == v}


def mean_dicts(ds):
    out = {}
    for c in CLASSES.values():
        v = [d[c] for d in ds if c in d]
        if v:
            out[c] = float(np.mean(v))
    return out


def one(path):
    case = os.path.basename(path).split('.')[0]
    T, sp = load(path)
    rng = np.random.default_rng(int(case[1:]) + 20261025)
    rad = radius_map(T, sp)
    rep = find_ostia(T, sp)
    zone = np.zeros(T.shape, bool)
    for o in rep.ostia:
        zone[tuple(o.point)] = True
    zone = ndimage.binary_dilation(zone, iterations=4)
    full = cl_len(T, sp)
    u = rng.uniform(*READER_U, size=2)
    ind = [truncate(T, rad, u[i], zone) for i in range(2)]
    res = {'case': case, 'cl_full': full, 'scen': []}

    def score(reads):
        return {'inter': mean_dicts([tf(reads[0], reads[1], sp), tf(reads[1], reads[0], sp)]),
                'model': mean_dicts([tf(R, T, sp) for R in reads])}

    base = score(ind)
    for rs in SEED_R:
        S = truncate(T, rad, rs, zone)
        seed_share = cl_len(S, sp) / max(full, 1)
        anch = [truncate(T, rad, max(u[i], rs), zone) for i in range(2)]
        for alpha, reads in ((0.0, ind), (1.0, anch)) + (((0.5, [anch[0], ind[1]]),) if rs == 0.8 else ()):
            sc = dict(base) if alpha == 0.0 else score(reads)
            sc['seed'] = mean_dicts([tf(reads[0], S, sp), tf(S, reads[0], sp)])
            res['scen'].append({'seed_r': rs, 'alpha': alpha, 'seed_cl_share': round(seed_share, 4), **sc})
    return res


def summarise(rows):
    out = []
    keys = sorted({(s['seed_r'], s['alpha']) for r in rows for s in r['scen']})
    for rs, a in keys:
        sc = [s for r in rows for s in r['scen'] if s['seed_r'] == rs and s['alpha'] == a]
        row = {'seed_r': rs, 'alpha': a, 'seed_cl_share': round(float(np.mean([s['seed_cl_share'] for s in sc])), 3)}
        for c in CLASSES.values():
            inter = [s['inter'][c] for s in sc if c in s['inter'] and c in s['model']]
            model = [s['model'][c] for s in sc if c in s['inter'] and c in s['model']]
            seed = [s['seed'][c] for s in sc if c in s['seed']]
            d = np.asarray(model) - np.asarray(inter)
            row[c] = {'n': len(d), 'inter': round(float(np.mean(inter)), 4), 'model': round(float(np.mean(model)), 4),
                      'seed_vs_read': round(float(np.mean(seed)), 4),
                      'contrast': round(float(d.mean()), 4), 'contrast_sd': round(float(d.std(ddof=1)), 4),
                      'seed_flag (seed >= inter - 0.02)': bool(np.mean(seed) >= np.mean(inter) - 0.02)}
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--icx', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--np', type=int, default=4)
    ap.add_argument('--limit', type=int)
    a = ap.parse_args()
    s = json.load(open(SEALED))
    sealed = set(s['sealed_icx_test']) | set(s['sealed_quality0'])
    paths = sorted(glob.glob(os.path.join(a.icx, 'c*.nii.gz')))
    bad = [p for p in paths if os.path.basename(p).split('.')[0] in sealed]
    if bad:
        sys.exit(f'refusing: sealed cases in {a.icx}: {bad}')
    if a.limit:
        paths = paths[:a.limit]
    with Pool(a.np) as pool:
        rows = pool.map(one, paths)
    summ = summarise(rows)
    for r in summ:
        print(r['seed_r'], r['alpha'], r['seed_cl_share'],
              {c: (r[c]['inter'], r[c]['model'], r[c]['contrast'], r[c]['seed_vs_read']) for c in CLASSES.values()})
    json.dump({'summary': summ, 'rows': rows, 'n_cases': len(rows)}, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
