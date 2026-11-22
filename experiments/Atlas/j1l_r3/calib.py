"""Atlas, Janus 1-L round 3: two facts about thresholded probabilities that the converged commands depend on.

A. **E must be made by nnUNetv2_ensemble, not by `nnUNetv2_predict -f 0 1`.** In nnU-Net 2.8.1, `predict -f 0 1`
   averages the folds' *logits* (`predict_from_raw_data.py` l. 524-530), while `nnUNetv2_ensemble` averages their
   *probabilities* (`ensembling/ensemble.py` l. 18-31). L-A14 defines E as the mean softmax and says the two are equal.
   They agree at argmax when the folds' rims are mirror images, but not at a foreground threshold t != 0.5, which is
   where the plan exports E. `tube` below gives the width difference, in mm, of the two ensembles of the same two
   networks, for a vessel rim whose logit falls k per mm and two folds whose rims sit +-delta mm apart.

B. **A temperature fit cannot change what Rule W chooses, beyond re-labelling the grid.** Rule W picks one mask from
   the family {sum of vessel probabilities >= t}. A temperature T (p_T = softmax(log p / T)) is monotone in each
   voxel's foreground logit when one vessel class dominates, so the family is the same set of masks, met at other t.
   Only where two vessel classes compete (a bifurcation) can the order of voxels change. `family` measures that on a
   synthetic bifurcation; `fit` measures it on Janus 0's own tuning-60 probabilities (the lead runs it, CPU, only if
   L-A23's calibration row fires), and fits T by NLL in a 3 mm rim band.

Usage:
  python calib.py tables                                     # A and B on synthetic rims (prints, writes calib.json)
  python calib.py fit --probs $W/probs --icx $J0/icx --np 4 --out $W/scores/calib_tuning60.json
  python calib.py --selftest
"""
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
GRID = (0.50, 0.45, 0.40, 0.35, 0.30, 0.25)


def sig(x):
    return 1.0 / (1.0 + np.exp(-x))


# ------------------------------------------------------------------------------------------------ A. ensembles
def radius(p, r, t):
    """Outer radius (mm) of {p >= t} on a radial profile p(r), r increasing (linear interpolation)."""
    inside = p >= t
    if not inside.any():
        return 0.0
    i = np.nonzero(inside)[0][-1]
    if i + 1 >= len(r):
        return float(r[-1])
    return float(r[i] + (p[i] - t) / (p[i] - p[i + 1]) * (r[i + 1] - r[i]))


def tube(k, delta, t, r0=1.5, asym=1.0):
    """Width of E made two ways. Fold 1's rim at r0 + delta, fold 2's at r0 - delta; fold 2's slope k * asym."""
    r = np.linspace(0, 4, 40001)
    z1, z2 = k * (r0 + delta - r), k * asym * (r0 - delta - r)
    softmax_mean = 0.5 * (sig(z1) + sig(z2))          # nnUNetv2_ensemble (binary rim: fg vs background)
    logit_mean = sig(0.5 * (z1 + z2))                 # nnUNetv2_predict -f 0 1
    return radius(softmax_mean, r, t) - radius(logit_mean, r, t)


# ------------------------------------------------------------------------------------------------ B. the family
def softmax(z, axis=0):
    z = z - z.max(axis, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis, keepdims=True)


def tempered_fg(p, T):
    z = np.log(np.clip(p, 1e-12, 1.0))
    return 1.0 - softmax(z / T, 0)[0]


def family_mismatch(p, T, grid=GRID):
    """For each t: the mask {fg >= t}, and the count-matched mask of the tempered foreground; mismatch / mask size."""
    fg = 1.0 - p[0]
    fgT = tempered_fg(p, T).ravel()
    order = np.sort(fgT)[::-1]
    out = {}
    for t in grid:
        m = (fg >= t).ravel()
        n = int(m.sum())
        if n == 0:
            out[f'{t:.2f}'] = None
            continue
        tT = order[n - 1]
        mT = fgT >= tT
        out[f'{t:.2f}'] = dict(t_equiv=round(float(tT), 4), mismatch=round(float((m ^ mT).sum() / n), 5))
    return out


def bifurcation(k=4.0, comp=0.0, seed=0):
    """5-class probabilities on a 0.25 mm grid: LM (1) splitting into LAD (2) and LCx (3), rims with slope k per mm.
    comp > 0 blurs the LAD/LCx boundary (the two vessels' logits compete over comp mm)."""
    rng = np.random.default_rng(seed)
    g = np.mgrid[0:120, 0:80, 0:40] * 0.25
    x, y, zc = g[0], g[1], g[2] - 5.0

    def seg_d(ax, ay, bx, by):
        abx, aby = bx - ax, by - ay
        s = np.clip(((x - ax) * abx + (y - ay) * aby) / (abx ** 2 + aby ** 2), 0, 1)
        return np.sqrt((x - ax - s * abx) ** 2 + (y - ay - s * aby) ** 2 + zc ** 2)
    dlm = seg_d(2, 10, 12, 10)
    dlad = seg_d(12, 10, 28, 3)
    dlcx = seg_d(12, 10, 28, 17)
    logits = np.stack([np.zeros_like(x), k * (1.8 - dlm), k * (1.5 - dlad), k * (1.5 - dlcx), np.full_like(x, -20)])
    if comp > 0:
        logits[2] += rng.normal(0, comp, x.shape); logits[3] += rng.normal(0, comp, x.shape)
    return softmax(logits, 0)


# ------------------------------------------------------------------------------------------------ fit (real data)
def _fit_one(job):
    import nibabel as nib
    from scipy import ndimage
    sys.path.insert(0, os.path.join(ROOT, 'trillium', 'icx4', 'lib'))
    sys.path.insert(0, os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1'))
    from territory import to_four
    from threshold_export import orient
    npz, icx_dir, nsamp = job
    c = os.path.basename(npz)[:-4]
    seg = np.asarray(nib.load(npz[:-4] + '.nii.gz').dataobj).astype(np.uint8)
    p = orient(np.load(npz)['probabilities'].astype(np.float32), seg)
    li = nib.load(os.path.join(icx_dir, f'{int(c[1:]) + 1}.coronary.nii.gz'))
    sp = li.header.get_zooms()[:3]
    ref = to_four(np.asarray(li.dataobj).astype(np.int64), sp).astype(np.uint8)
    band = ndimage.distance_transform_edt(~((ref > 0) | (seg > 0)), sampling=sp) <= 3.0
    idx = np.flatnonzero(band.ravel())
    rng = np.random.default_rng(int(c[1:]))
    pick = rng.choice(idx, min(nsamp, len(idx)), replace=False)
    P = p.reshape(5, -1)[:, pick]
    y = ref.ravel()[pick]
    bb = tuple(slice(max(0, a.min() - 8), a.max() + 9) for a in np.nonzero(band))
    fam = {T: family_mismatch(p[(slice(None),) + bb], T) for T in (0.7, 1.5)}
    return c, P, y, fam


def nll(P, y, T):
    z = np.log(np.clip(P, 1e-12, 1.0)) / T
    z -= z.max(0, keepdims=True)
    return float(-(z[y, np.arange(len(y))] - np.log(np.exp(z).sum(0))).mean())


def fit(probs, icx, n_proc, out, nsamp=100000):
    L = json.load(open(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))
    files = sorted(os.path.join(probs, c + '.npz') for c in L['tuning60'])
    with Pool(n_proc) as pool:
        res = pool.map(_fit_one, [(f, icx, nsamp) for f in files], chunksize=1)
    P = np.concatenate([r[1] for r in res], 1)
    y = np.concatenate([r[2] for r in res])
    Ts = np.exp(np.linspace(np.log(0.3), np.log(4.0), 121))
    nl = [nll(P, y, T) for T in Ts]
    T_hat = float(Ts[int(np.argmin(nl))])
    fam = {f'T={T}': {t: float(np.mean([r[3][T][t]['mismatch'] for r in res if r[3][T][t]]))
                      for t in (f'{g:.2f}' for g in GRID)} for T in (0.7, 1.5)}
    fg = 1 - P[0]
    bins = np.linspace(0, 1, 11)
    ece = float(sum(abs(fg[(fg >= a) & (fg < b)].mean() - (y[(fg >= a) & (fg < b)] > 0).mean()) *
                    ((fg >= a) & (fg < b)).mean() for a, b in zip(bins[:-1], bins[1:]) if ((fg >= a) & (fg < b)).any()))
    o = dict(n_cases=len(res), n_voxels=int(len(y)), T_hat=round(T_hat, 3), nll_T1=round(nll(P, y, 1.0), 5),
             nll_That=round(min(nl), 5), ece_fg_band=round(ece, 4), family_mismatch_mean=fam)
    json.dump(o, open(out, 'w'), indent=1)
    print(json.dumps(o, indent=1))


# ------------------------------------------------------------------------------------------------ outputs
def tables():
    A = []
    for k in (2.0, 4.0, 8.0):
        for d in (0.1, 0.25, 0.5):
            row = dict(k_per_mm=k, delta_mm=d)
            for t in (0.50, 0.45, 0.40, 0.35, 0.30):
                row[f'{t:.2f}'] = round(tube(k, d, t), 4)
            row['0.50_asym1.5'] = round(tube(k, d, 0.5, asym=1.5), 4)
            row['0.40_asym1.5'] = round(tube(k, d, 0.40, asym=1.5), 4)
            A.append(row)
    Bt = []
    for k in (2.0, 4.0):
        for comp in (0.0, 1.0, 3.0):
            p = bifurcation(k, comp)
            for T in (0.7, 1.5):
                Bt.append(dict(k_per_mm=k, competition_sd=comp, T=T, per_t=family_mismatch(p, T)))
    res = dict(A_softmax_minus_logit_mean_width_mm=A, B_family_mismatch=Bt)
    json.dump(res, open(os.path.join(HERE, 'calib.json'), 'w'), indent=1)
    for r in A:
        print('A', r)
    for r in Bt:
        print('B', r['k_per_mm'], r['competition_sd'], r['T'], {t: v['mismatch'] for t, v in r['per_t'].items() if v})


def selftest():
    # A: mirror rims agree at argmax, differ below it; the mean softmax is the wider one at t < 0.5
    assert abs(tube(4, 0.25, 0.5)) < 1e-3
    assert tube(4, 0.25, 0.40) > 0.005 and tube(4, 0.5, 0.35) > tube(4, 0.25, 0.35)
    assert abs(tube(4, 0.0, 0.40)) < 1e-3                         # identical folds: no difference
    # B: a single vessel class keeps the mask family exactly
    r = np.linspace(0, 4, 400)
    z = 4 * (1.5 - r)
    p = np.stack([1 - sig(z), sig(z), np.zeros_like(z) + 1e-9, np.zeros_like(z) + 1e-9, np.zeros_like(z) + 1e-9])
    p /= p.sum(0)
    fm = family_mismatch(p.reshape(5, 400, 1, 1), 1.7)
    assert all(v['mismatch'] == 0.0 for v in fm.values() if v), fm
    # NLL: labels drawn at temperature 2 are fitted near 2
    rng = np.random.default_rng(0)
    zz = rng.normal(0, 3, (2, 20000))
    pr = softmax(zz / 2.0, 0)
    y = (rng.random(20000) < pr[1]).astype(int)
    Ts = np.linspace(0.5, 4, 141)
    That = Ts[int(np.argmin([nll(softmax(zz, 0), y, T) for T in Ts]))]
    assert 1.7 < That < 2.3, That
    print('[calib] self-test passed: logit vs softmax mean agree at argmax for mirror rims and differ below it; '
          'one-class temperature keeps the mask family; NLL recovers T')


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['--selftest']:
        selftest()
    elif a[:1] == ['tables']:
        tables()
    elif a[:1] == ['fit']:
        kw = dict(zip(a[1::2], a[2::2]))
        fit(kw['--probs'], kw['--icx'], int(kw.get('--np', 4)), kw['--out'])
    else:
        sys.exit(__doc__)
