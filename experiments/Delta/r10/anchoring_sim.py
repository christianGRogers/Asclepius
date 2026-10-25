"""Delta, Round 10: what A10 measures when team reads keep the TotalSegmentator seed's extent (A31.2, L5), and what
a one-voxel lumen-width difference (Janus 0 vs ImageCAS-X, icx4 - Results.md) does to it.

On each ImageCAS-X val reference T (non-sealed, collapsed by territory.to_four, D25):
  model   M0 = T itself (a model that reproduces ImageCAS-X exactly)
          M1 = T thinned to a volume ratio of about 0.87 without touching its centreline (Janus 0's measured width:
               volume ratio 0.867 on val, tolerant Dice 0.97)
  seed    S_L = T with every distal tip trimmed by L mm along the vessel (L = 0, 5, 10, 20): a seed that stops
               short of ImageCAS-X's extent. Side branches shorter than L vanish, as a seed's do.
  reads   independent: T with each tip trimmed by its own U[0, E] mm (E = 8), drawn separately for reads a and b
          anchored:    S_L with each tip trimmed by a further U[0, 2] mm (the reader cuts the seed down, D26, and
                       adds nothing)
          wide:        an independent read dilated by one voxel (a reader convention one voxel outside ImageCAS-X)
Trims never reach within 10 mm of an ostium along the vessel, so the LM and the proximal RCA are always kept.
A10's contrast per class is d = model-vs-read (mean over a, b; read as the reference) - inter-read (mean of both
directions). D6 passes a class when the lower 95 % bound of mean(d) is above -0.05.

Ostia: ImageCAS-X's released start points as the pseudo-aorta (Delta v9 P2 mechanics) for every reference, so a
trim never moves an ostium. tF1 is the pinned segtrain.tf1 (A1c 24441cf8...5254), 1.5 mm.
CPU only. Never touches a sealed case (val only; the sealed list is checked).
Usage: anchoring_sim.py <icx_val_dir> <out.jsonl> [--np 4] [--only c0001,...]"""
import argparse
import hashlib
import json
import os
import sys
from multiprocessing import Pool

import nibabel as nib
import numpy as np
from scipy import ndimage
from skimage.graph import MCP_Geometric
from skimage.morphology import skeletonize

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
sys.path.insert(0, os.path.join(REPO, 'trillium', 'icx4', 'lib'))
PIN = '24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254'
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
LS = (0.0, 5.0, 10.0, 20.0)
E_INDEP = 8.0
E_ANCH = 2.0
MARGIN_MM = 8.0
ROOT_EXCLUDE_MM = 8.0
ROOT_KEEP_MM = 10.0     # never trim within 10 mm of an ostium along the vessel (a seed keeps the proximal trunk)


def check_pin():
    h = hashlib.sha256(open(os.path.join(REPO, 'src/segtrain/tf1.py'), 'rb').read()).hexdigest()
    if h != PIN:
        sys.exit(f'tf1.py sha256 {h} is not the A1c pin')


def balls(shape, pts, sp, r_mm=1.0):
    m = np.zeros(shape, bool)
    r = np.ceil(r_mm / sp).astype(int)
    zz, yy, xx = np.mgrid[-r[0]:r[0] + 1, -r[1]:r[1] + 1, -r[2]:r[2] + 1]
    b = (zz * sp[0]) ** 2 + (yy * sp[1]) ** 2 + (xx * sp[2]) ** 2 <= r_mm ** 2
    for p in pts:
        c = np.round(p).astype(int)
        lo, hi = c - r, c + r + 1
        if np.any(hi <= 0) or np.any(lo >= shape):
            continue
        w = tuple(slice(max(lo[k], 0), min(hi[k], shape[k])) for k in range(3))
        bw = b[tuple(slice(w[k].start - lo[k], w[k].stop - lo[k]) for k in range(3))]
        m[w] |= bw
    return m


def tip_distance(mask, sp, roots):
    """Geodesic distance (mm, inside the mask) from the distal skeleton ends; ends within ROOT_EXCLUDE_MM of an
    ostium are not tips. Returns (distance, tip-region labels for distance < max(LS) + E_INDEP)."""
    sk = skeletonize(mask)
    nb = ndimage.convolve(sk.astype(np.uint8), np.ones((3, 3, 3), np.uint8), mode='constant') - 1
    ends = np.argwhere(sk & (nb == 1))
    if len(roots):
        rp = np.asarray(roots) * sp
        dist = np.min(np.linalg.norm((ends * sp)[:, None, :] - rp[None], axis=2), axis=1)
        ends = ends[dist > ROOT_EXCLUDE_MM]
    if len(ends) == 0:
        return np.full(mask.shape, np.inf), np.zeros(mask.shape, int), 0
    cost = np.where(mask, 1.0, np.inf)
    d, _ = MCP_Geometric(cost, sampling=tuple(sp)).find_costs([tuple(e) for e in ends])
    if len(roots):
        nz = np.argwhere(mask)
        rv = [tuple(nz[np.argmin(np.linalg.norm((nz - r) * sp, axis=1))]) for r in roots]
        droot, _ = MCP_Geometric(cost, sampling=tuple(sp)).find_costs(rv)
        d = np.where(droot < ROOT_KEEP_MM, np.inf, d)
    reach = mask & (d < max(LS) + E_INDEP + 1.0)
    lab, n = ndimage.label(reach, structure=np.ones((3, 3, 3)))
    return d, lab, len(ends)


def trim(ref, d, lab, t_of_region):
    """Remove voxels whose tip distance is below the trim of their tip region."""
    t = np.zeros(lab.max() + 1)
    t[1:] = t_of_region
    cut = (lab > 0) & (d < t[lab])
    out = ref.copy()
    out[cut] = 0
    return out


def thin(ref, sp, target=0.87, seed=0):
    """Janus 0's width: remove boundary voxels until the volume ratio is about `target`, never a skeleton voxel."""
    rng = np.random.default_rng(seed)
    m = ref > 0
    sk = skeletonize(m)
    out = ref.copy()
    cur = m.copy()
    goal = target * m.sum()
    for _ in range(3):
        if cur.sum() <= goal:
            break
        edge = cur & ~ndimage.binary_erosion(cur, structure=ndimage.generate_binary_structure(3, 1)) & ~sk
        need = cur.sum() - goal
        p = min(1.0, need / max(edge.sum(), 1))
        drop = edge & (rng.random(cur.shape) < p)
        cur &= ~drop
    out[~cur] = 0
    return out


def widen(lbl):
    """One voxel outward, each new voxel taking the nearest class (6-connected)."""
    m = lbl > 0
    grow = ndimage.binary_dilation(m, structure=ndimage.generate_binary_structure(3, 1)) & ~m
    _, idx = ndimage.distance_transform_edt(~m, return_indices=True)
    out = lbl.copy()
    out[grow] = lbl[tuple(i[grow] for i in idx)]
    return out


def score(T, ref, pred, sp, pseudo, rep=None):
    rep = rep if rep is not None else T.find_ostia(ref, sp, aorta=pseudo)
    r = T.tree_f1(ref, pred, sp, ostia=rep)
    return ({NAMES[c]: float(v) for c, v in r.per_class.items()},
            {NAMES[c]: float(v) for c, v in r.recall.items()},
            {NAMES[c]: float(v) for c, v in r.precision.items()})


def mean2(a, b):
    return {k: (a[k] + b[k]) / 2 for k in a if k in b}


def one(args):
    case, icx_dir, ostia = args
    from segtrain import tf1 as T
    from territory import to_four
    try:
        i = int(case[1:]) + 1
        li = nib.load(os.path.join(icx_dir, f'{i}.coronary.nii.gz'))
        sp = np.asarray(li.header.get_zooms()[:3], float)
        ref = to_four(np.asarray(li.dataobj).astype(np.int64), sp).astype(np.uint8)
        nz = np.argwhere(ref > 0)
        mv = np.ceil(MARGIN_MM / sp).astype(int)
        lo = np.maximum(nz.min(0) - mv, 0)
        hi = np.minimum(nz.max(0) + 1 + mv, ref.shape)
        ref = ref[tuple(slice(a, b) for a, b in zip(lo, hi))]
        inv = np.linalg.inv(li.affine)
        o = ostia.get(case, {})
        pts = [nib.affines.apply_affine(inv, np.asarray(q) * [-1, -1, 1]) - lo for s in ('left', 'right')
               for q in o.get(s, [])]
        pseudo = balls(ref.shape, pts, sp)
        d, lab, n_tips = tip_distance(ref > 0, sp, pts)
        nreg = lab.max()
        rng = np.random.default_rng(int(hashlib.sha256(case.encode()).hexdigest()[:8], 16))
        M = {'M0': ref, 'M1': thin(ref, sp)}
        row = dict(case=case, n_tips=int(n_tips), n_regions=int(nreg),
                   vol_ratio_M1=float((M['M1'] > 0).sum() / (ref > 0).sum()))
        conds = {}
        ia = trim(ref, d, lab, rng.uniform(0, E_INDEP, nreg))
        ib = trim(ref, d, lab, rng.uniform(0, E_INDEP, nreg))
        conds['indep'] = (ia, ib)
        conds['indep_wide'] = (widen(ia), widen(ib))
        for L in LS:
            aa = trim(ref, d, lab, L + rng.uniform(0, E_ANCH, nreg))
            ab = trim(ref, d, lab, L + rng.uniform(0, E_ANCH, nreg))
            conds[f'anch{int(L)}'] = (aa, ab)
        for name, (a, b) in conds.items():
            ra_, rb_ = T.find_ostia(a, sp, aorta=pseudo), T.find_ostia(b, sp, aorta=pseudo)
            i_ab, _, _ = score(T, a, b, sp, pseudo, ra_)
            i_ba, _, _ = score(T, b, a, sp, pseudo, rb_)
            res = dict(inter=mean2(i_ab, i_ba))
            for mn, m in M.items():
                if mn == 'M1' and name not in ('indep', 'anch10'):
                    continue
                fa, ra, pa = score(T, a, m, sp, pseudo, ra_)
                fb, rb, pb = score(T, b, m, sp, pseudo, rb_)
                res[mn] = mean2(fa, fb)
                res[mn + '_recall'] = mean2(ra, rb)
                res[mn + '_precision'] = mean2(pa, pb)
            row[name] = res
        # the seed itself against an independent read (A31.2's seed-vs-read, extent only)
        rep_ia = T.find_ostia(ia, sp, aorta=pseudo)
        for L in LS:
            s = trim(ref, d, lab, np.full(nreg, L))
            fa, _, _ = score(T, ia, s, sp, pseudo, rep_ia)
            row[f'seed{int(L)}_vs_indep'] = fa
        return row
    except Exception as e:  # noqa: BLE001
        return dict(case=case, error=repr(e)[:300])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('icx_dir')
    ap.add_argument('out')
    ap.add_argument('--np', type=int, default=4)
    ap.add_argument('--only')
    a = ap.parse_args()
    check_pin()
    sealed = set(json.load(open(os.path.join(REPO, 'trillium', 'sealed_test.json')))['sealed_icx_test'])
    val_ids = [int(x) for x in open(os.path.join(a.icx_dir, 'val.txt')).read().split()]
    cases = [f'c{i - 1:04d}' for i in val_ids]
    if a.only:
        cases = [c for c in cases if c in set(a.only.split(','))]
    bad = [c for c in cases if c in sealed]
    if bad:
        sys.exit(f'sealed cases in the list: {bad[:3]}')
    ostia = json.load(open(os.path.join(REPO, 'experiments', 'Delta', 'r9_expert_ostia.json')))['ostia']
    done = set()
    if os.path.exists(a.out):
        done = {json.loads(ln)['case'] for ln in open(a.out) if ln.strip()}
    todo = [(c, a.icx_dir, ostia) for c in cases if c not in done]
    print(f'{len(cases)} val cases, {len(todo)} to run', flush=True)
    with Pool(a.np) as p, open(a.out, 'a') as f:
        for k, row in enumerate(p.imap_unordered(one, todo), 1):
            f.write(json.dumps(row) + '\n')
            f.flush()
            if k % 10 == 0:
                print(f'{k}/{len(todo)}', flush=True)


if __name__ == '__main__':
    main()
