"""Delta, Janus 1-L round 3 (#302, Round 2 ruling §5 item 4, L-A23's calibration rows): the calibration check on
the tuning 60, a report that decides nothing.

It runs only if Job 0 gives t* = 0.30, FP rising at every t < 0.50, or a guard-held t* (L-A23). It reads Job 0's
saved probabilities (`$W/probs/<case>.npz`, nnU-Net's order, beside `<case>.nii.gz`) and the ImageCAS-X labels of the
tuning 60 (training cases under D45), collapsed by `territory.to_four`. **It refuses every case outside the tuning
60**, and any sealed case, so it never reads the locked 100.

On voxels within 3 mm of the reference or of p_fg >= 0.1 (the rim band; far background would swamp the fit),
subsampled to <= 200 000 per case (seed 0), pooled over the 60:
  T        five-class temperature, softmax(log p / T), by NLL (golden section on log T in [0.25, 4]);
  a, b     Platt on the foreground logit, sigma(a * logit(p_fg) + b), by logistic regression;
  ECE      of p_fg, 15 equal-width bins, before and after Platt;
  t_half   sigma(-b / a): the raw threshold that is "0.5 after calibration" (voxel-accuracy boundary);
  t_F      sigma((logit(F*/2) - b) / a), F* = Janus 0's mean whole-tree Dice at t* (select.json): the raw threshold
           at the F1-optimal point of a calibrated score (Lipton et al., arXiv:1402.1892).
Reading (pre-registered, Delta v3 §4): Rule W is not re-run on calibrated probabilities (calib_equiv.py: a foreground
calibration is exactly a threshold, and a five-class temperature nearly one). |t_F - t*| <= 0.05 says t* is the
calibration's own F1 point; otherwise the report says Rule W's choice is not explained by a global miscalibration.

Usage (Trillium login node, after Job 0; ~15 CPU-min):
  python calib60.py --probs $W/probs --icx $J0/icx --select $W/select.json --out $W/scores/calib60.json --np 8
  python calib60.py --selftest
"""
import argparse
import json
import math
import os
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
LISTS = os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')
BAND_MM, NMAX = 3.0, 200000


def sigma(x):
    return 1 / (1 + np.exp(-x))


def logit(p):
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return np.log(p / (1 - p))


def guard(cases):
    L = json.load(open(LISTS))
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    bad = sorted(set(cases) - set(L['tuning60'])) + \
        sorted(set(cases) & (set(S['sealed_icx_test']) | set(S['sealed_quality0'])))
    if bad:
        sys.exit(f'[calib60] REFUSING: cases outside the tuning 60 or sealed: {bad[:5]}')


def band_sample(prob, ref, sp, rng):
    from scipy import ndimage
    pf = 1 - prob[0]
    near = ndimage.distance_transform_edt(~((ref > 0) | (pf >= 0.1)), sampling=sp) <= BAND_MM
    idx = np.flatnonzero(near)
    if len(idx) > NMAX:
        idx = rng.choice(idx, NMAX, replace=False)
    P = prob.reshape(prob.shape[0], -1)[:, idx].T.astype(np.float64)
    return P, ref.reshape(-1)[idx].astype(np.int64)


def _one(job):
    import nibabel as nib
    sys.path.insert(0, os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1'))
    sys.path.insert(0, os.path.join(ROOT, 'trillium', 'icx4', 'lib'))
    from threshold_export import orient
    from territory import to_four
    c, probs, icx = job
    img = nib.load(os.path.join(probs, c + '.nii.gz'))
    seg = np.asarray(img.dataobj).astype(np.uint8)
    prob = orient(np.load(os.path.join(probs, c + '.npz'))['probabilities'].astype(np.float32), seg)
    li = nib.load(os.path.join(icx, f'{int(c[1:]) + 1}.coronary.nii.gz'))
    ref = to_four(np.asarray(li.dataobj).astype(np.int64), li.header.get_zooms()[:3]).astype(np.uint8)
    return band_sample(prob, ref, np.array(img.header.get_zooms()[:3], float), np.random.default_rng(0))


def nll_T(P, y, T):
    lp = np.log(np.clip(P, 1e-30, 1)) / T
    lp -= lp.max(1, keepdims=True)
    lse = np.log(np.exp(lp).sum(1))
    return float(np.mean(lse - lp[np.arange(len(y)), y]))


def fit_T(P, y):
    lo, hi = math.log(0.25), math.log(4.0)
    g = (math.sqrt(5) - 1) / 2
    a, b = hi - g * (hi - lo), lo + g * (hi - lo)
    for _ in range(60):
        if nll_T(P, y, math.exp(a)) < nll_T(P, y, math.exp(b)):
            hi = b
        else:
            lo = a
        a, b = hi - g * (hi - lo), lo + g * (hi - lo)
    return math.exp((lo + hi) / 2)


def fit_platt(l, y):
    w = np.array([1.0, 0.0])
    X = np.stack([l, np.ones_like(l)], 1)
    for _ in range(50):
        q = sigma(X @ w)
        g = X.T @ (q - y)
        H = (X * (q * (1 - q))[:, None]).T @ X + 1e-9 * np.eye(2)
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-10:
            break
    return float(w[0]), float(w[1])


def ece(p, y, bins=15):
    e = np.linspace(0, 1, bins + 1)
    k = np.clip(np.digitize(p, e) - 1, 0, bins - 1)
    return float(sum(abs(p[k == i].mean() - y[k == i].mean()) * (k == i).mean() for i in range(bins) if (k == i).any()))


def analyse(P, y, f_star, t_star):
    pf = 1 - P[:, 0]
    yf = (y > 0).astype(float)
    T = fit_T(P, y)
    a, b = fit_platt(logit(pf), yf)
    q = sigma(a * logit(pf) + b)
    t_half = float(sigma(-b / a))
    t_F = float(sigma((logit(f_star / 2) - b) / a))
    return dict(n_voxels=int(len(y)), T=round(T, 4), nll_raw=round(nll_T(P, y, 1.0), 5), nll_T=round(nll_T(P, y, T), 5),
                platt_a=round(a, 4), platt_b=round(b, 4), ece_raw=round(ece(pf, yf), 5), ece_platt=round(ece(q, yf), 5),
                t_half=round(t_half, 4), f_star=round(f_star, 4), t_F=round(t_F, 4), t_star=t_star,
                t_F_within_0p05_of_t_star=abs(t_F - t_star) <= 0.05)


def selftest():
    rng = np.random.default_rng(0)
    n = 300000
    l_true = rng.normal(-1.0, 3.0, n)                         # the true foreground logit
    yf = (rng.random(n) < sigma(l_true)).astype(int)
    # the model is over-confident and biased toward background: logit_model = (l_true - 0.8) * 1.6
    lm = (l_true - 0.8) * 1.6
    pf = sigma(lm)
    split = rng.random(n)                                     # mass split between two vessel classes
    P = np.stack([1 - pf, pf * split, pf * (1 - split), np.zeros(n) + 1e-12, np.zeros(n) + 1e-12], 1)
    y = np.where(yf > 0, 1 + (rng.random(n) > split).astype(int), 0)
    r = analyse(P, y, f_star=0.9, t_star=0.40)
    # Platt must recover a = 1/1.6, b = 0.8 (l_true = lm / 1.6 + 0.8)
    assert abs(r['platt_a'] - 1 / 1.6) < 0.02 and abs(r['platt_b'] - 0.8) < 0.03, r
    assert r['ece_platt'] < r['ece_raw'] and r['ece_platt'] < 0.01, r
    assert abs(r['t_half'] - float(sigma(-0.8 * 1.6))) < 0.01, r
    assert r['T'] > 1.0, r                                    # over-confident -> T > 1
    try:
        guard(['c0000'] + json.load(open(LISTS))['locked100'][:1])
        raise AssertionError('a locked-100 case was not refused')
    except SystemExit as e:
        assert 'REFUSING' in str(e)
    print('[calib60] self-test passed: Platt recovers (a, b) =', (r['platt_a'], r['platt_b']), 'T =', r['T'],
          't_half =', r['t_half'], '; locked-100 case refused')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--probs'); ap.add_argument('--icx'); ap.add_argument('--select'); ap.add_argument('--out')
    ap.add_argument('--np', type=int, default=8)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    cases = json.load(open(LISTS))['tuning60']
    guard(cases)
    S = json.load(open(a.select))
    t_star = round(float(S['chosen_t']), 2)
    f_star = float(S['per_threshold'][f'{t_star:.2f}']['dice'])
    with Pool(a.np) as p:
        parts = p.map(_one, [(c, a.probs, a.icx) for c in cases], chunksize=1)
    P = np.concatenate([q[0] for q in parts]); y = np.concatenate([q[1] for q in parts])
    res = dict(rule='Delta v3 calib60 (report only)', n_cases=len(parts), **analyse(P, y, f_star, t_star))
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
