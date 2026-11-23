"""Bridge, Janus 1-L round 3 (#302, Round 2 ruling §5 item 4): is Janus 0's rim miscalibrated? A temperature check
on the tuning 60, run on CPU from Job 0's saved probabilities. It runs only if L-A23 asks for it (t* = 0.30, FP rising
at every t < 0.50, or a guard-held t*).

Reads: Job 0's `$W/probs/<case>.npz` (nnU-Net `probabilities`, (5, *spatial)) and `<case>.nii.gz` for the tuning 60,
and the ImageCAS-X label of the same case (`$J0/icx/<n>.coronary.nii.gz`), collapsed by territory.to_four.
**Refuses every case outside the tuning 60** (lists.json), so never the locked 100, D60 or a sealed case.

What it computes, voxels in each case's reference bounding box + 10 voxels (background far away would swamp the fit):
  T        one temperature for the five-class softmax, p_T = softmax(log p / T), fitted by mean NLL (golden section
           on log T in [-2, 2]), pooled over the 60. REPORT ONLY: a temperature rescales log-odds about 0, so it
           cannot move the 0.5 crossing. Its export equals argmax (t_eq_temperature ~ 0.50, agreement ~ 1), whatever
           the rim does. This is why the ruling's "temperature check" alone cannot see an inward boundary;
  Platt    P(vessel) = sigmoid(a * logit(raw foreground) + b), by NLL on the same voxels. The bias b moves the
           crossing: t_eq = sigmoid(-b / a) is the raw foreground threshold where Janus 0's calibrated vessel
           probability is 0.5. It is a monotone map, so thresholding calibrated probabilities is thresholding raw
           ones at t_eq, exactly;
  rim ECE  reliability of the raw foreground probability on the rim (reference voxels <= 1 voxel inside the
           boundary, background voxels <= 1 voxel outside), 10 bins, raw and calibrated;
  far FP   the mean raw foreground probability of predicted voxels more than 1.5 mm from the reference.

Pre-registered reading (Bridge v3 §4):
  * Rule W is NOT re-run on calibrated probabilities. Platt's map is monotone, so "calibrated >= 0.5" is the raw
    threshold t_eq: Rule W's grid already offers it, if t_eq is in range. Rule W picks by Dice; t_eq is the NLL
    answer to the same question, and it is a cross-check, not a second rule.
  * If t* = 0.30 (the grid's edge) and t_eq < 0.275: Rule W's grid is extended by {0.25, 0.20} on the same 60 with the
    same guards, before #306 freezes t (a choice on the tuning 60 only; Rule T's grid already reaches 0.25).
  * If |t_eq - t*| <= 0.05: calibration agrees with Rule W; nothing changes.
  * If FP rises at every t < 0.50 and the far-FP mean raw probability is >= 0.35: the FP is confident, not a rim
    effect. t* stays as Rule W chose it (the FP guard already bounds it); the next round reads the decomposition's
    `stray` share.
Usage: python calib60.py --probs $W/probs --icx $J0/icx --np 8 --out $W/scores/calib60.json
       python calib60.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'trillium', 'icx4', 'lib'))
sys.path.insert(0, os.path.join(REPO, 'experiments', 'Crucible', 'j1l_r1'))
MARGIN = 10
EPS = 1e-6


def tuning60():
    L = json.load(open(os.path.join(REPO, 'experiments/Crucible/j1l_r1/lists.json')))
    return set(L['tuning60'])


def softmax_T(logp, T):
    z = logp / T
    z = z - z.max(0, keepdims=True)
    e = np.exp(z)
    return e / e.sum(0, keepdims=True)


def nll(logp, lab, T):
    p = softmax_T(logp, T)
    return float(-np.log(np.take_along_axis(p, lab[None], 0)[0] + EPS).sum())


def ece(p, y, bins=10):
    idx = np.minimum((p * bins).astype(int), bins - 1)
    e = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            e += m.sum() * abs(p[m].mean() - y[m].mean())
    return float(e / max(len(p), 1))


def crop_case(prob, lab4):
    nz = np.argwhere(lab4 > 0)
    lo = np.maximum(nz.min(0) - MARGIN, 0); hi = np.minimum(nz.max(0) + MARGIN + 1, lab4.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    return prob[(slice(None),) + sl], lab4[sl]


def stats(prob, lab4, sp):
    """Per-case sufficient pieces: log-probs and labels (subsampled), rim and far-FP arrays."""
    logp = np.log(np.clip(prob, EPS, 1.0)).astype(np.float32)
    ref = lab4 > 0
    inner = ref & ~ndimage.binary_erosion(ref)
    outer = ndimage.binary_dilation(ref) & ~ref
    fg = 1.0 - prob[0]
    dist = ndimage.distance_transform_edt(~ref, sampling=sp)
    far = (fg >= 0.5) & (dist > 1.5)
    return logp, lab4.astype(np.int64), inner | outer, far


def fit_T(pieces):
    f = lambda lt: sum(nll(lp, lb, np.exp(lt)) for lp, lb in pieces)
    a, b = -2.0, 2.0
    g = (np.sqrt(5) - 1) / 2
    c, d = b - g * (b - a), a + g * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(40):
        if fc < fd:
            b, d, fd = d, c, fc; c = b - g * (b - a); fc = f(c)
        else:
            a, c, fc = c, d, fd; d = a + g * (b - a); fd = f(d)
    return float(np.exp((a + b) / 2))


def fit_platt(raw_fg, y):
    """Foreground-vs-background Platt fit, P(vessel) = sigmoid(a * logit(raw_fg) + b), by NLL (scipy, BFGS).
    Unlike a temperature, the bias b moves the 0.5 crossing: its raw-threshold equivalent is sigmoid(-b / a)."""
    from scipy.optimize import minimize
    l = np.log(np.clip(raw_fg, EPS, 1 - EPS) / np.clip(1 - raw_fg, EPS, 1 - EPS))
    y = y.astype(float)

    def f(w):
        z = w[0] * l + w[1]
        return float(np.mean(np.logaddexp(0, z) - y * z))
    w = minimize(f, np.array([1.0, 0.0]), method='BFGS').x
    a, b = float(w[0]), float(w[1])
    return a, b, float(1 / (1 + np.exp(b / a))) if a > 0 else float('nan')


def t_equivalent(raw_fg, cal_fg):
    """Raw threshold whose mask has the calibrated mask's voxel count; and the Dice of the two masks."""
    cal = cal_fg >= 0.5
    k = int(cal.sum())
    if k == 0:
        return float('nan'), float('nan')
    t = float(np.sort(raw_fg)[::-1][k - 1])
    raw = raw_fg >= t
    return t, float(2 * (raw & cal).sum() / (raw.sum() + cal.sum()))


def load(job):
    import nibabel as nib
    from territory import to_four
    from threshold_export import orient
    c, probs, icx = job
    img = nib.load(os.path.join(probs, c + '.nii.gz'))
    seg = np.asarray(img.dataobj).astype(np.uint8)
    prob = orient(np.load(os.path.join(probs, c + '.npz'))['probabilities'].astype(np.float32), seg)
    li = nib.load(os.path.join(icx, f'{int(c[1:]) + 1}.coronary.nii.gz'))
    lab4 = to_four(np.asarray(li.dataobj).astype(np.int16), li.header.get_zooms())
    assert lab4.shape == seg.shape, (c, lab4.shape, seg.shape)
    p, l = crop_case(prob, lab4)
    return c, stats(p, l, np.asarray(li.header.get_zooms()[:3], float))


def analyse(cases_stats, subsample=4):
    pieces = [(lp[:, ::subsample, ::subsample, ::subsample], lb[::subsample, ::subsample, ::subsample])
              for lp, lb, _, _ in cases_stats]
    T = fit_T(pieces)
    raw_fg, cal_fg, rim_raw, rim_cal, rim_y, far = [], [], [], [], [], []
    for lp, lb, rim, farm in cases_stats:
        p = np.exp(lp); pc = softmax_T(lp, T)
        rf, cf = 1 - p[0], 1 - pc[0]
        raw_fg.append(rf.ravel()); cal_fg.append(cf.ravel())
        rim_raw.append(rf[rim]); rim_cal.append(cf[rim]); rim_y.append((lb[rim] > 0).astype(float))
        far.append(rf[farm])
    ys = np.concatenate([(lb > 0).ravel() for _, lb, _, _ in cases_stats])
    raw_fg, cal_fg = np.concatenate(raw_fg), np.concatenate(cal_fg)
    t_eq_T, agree = t_equivalent(raw_fg, cal_fg)
    sub = slice(None, None, max(1, len(raw_fg) // 2_000_000))
    a, b, t_eq = fit_platt(raw_fg[sub], ys[sub])
    rr = np.concatenate(rim_raw)
    lr = np.log(np.clip(rr, EPS, 1 - EPS) / np.clip(1 - rr, EPS, 1 - EPS))
    rim_platt = 1 / (1 + np.exp(-(a * lr + b)))
    ry = np.concatenate(rim_y)
    farv = np.concatenate(far)
    return dict(T=round(T, 4), t_eq_temperature=round(t_eq_T, 4), agreement_dice=round(agree, 4),
                platt_a=round(a, 4), platt_b=round(b, 4), t_eq=round(t_eq, 4),
                rim_ece_platt=round(ece(rim_platt, ry), 4),
                rim_ece_raw=round(ece(np.concatenate(rim_raw), ry), 4),
                rim_ece_cal=round(ece(np.concatenate(rim_cal), ry), 4),
                rim_mean_p_raw=round(float(np.concatenate(rim_raw).mean()), 4), rim_frac_vessel=round(float(ry.mean()), 4),
                far_fp_voxels=int(len(farv)), far_fp_mean_p=round(float(farv.mean()), 4) if len(farv) else None)


def reading(res, tstar, fp_rises):
    out = []
    if tstar is not None and abs(res['t_eq'] - tstar) <= 0.05:
        out.append('calibration agrees with Rule W; nothing changes')
    if tstar is not None and abs(tstar - 0.30) < 1e-9 and res['t_eq'] < 0.275:
        out.append("extend Rule W's grid by {0.25, 0.20} on the tuning 60, same guards, before #306 freezes t")
    if fp_rises and res['far_fp_mean_p'] is not None and res['far_fp_mean_p'] >= 0.35:
        out.append('the FP is confident, not a rim effect: t* stays; the next round reads the stray share')
    return out or ['no pre-registered action; report only']


def selftest():
    rng = np.random.default_rng(0)
    # A tube whose rim the network under-calls: true boundary at r = 4 voxels, network's p crosses 0.5 at r = 3.
    z, y, x = np.indices((24, 24, 40))
    r = np.hypot(z - 12, y - 12)
    lab = np.where(r <= 4, 2, 0).astype(np.int64)
    logit_fg = 2.0 * (3.0 - r) + rng.normal(0, 0.3, r.shape)       # over-confident and inward
    pf = 1 / (1 + np.exp(-logit_fg))
    prob = np.stack([1 - pf, 0.01 * pf, 0.97 * pf, 0.01 * pf, 0.01 * pf]).astype(np.float32)
    st = stats(prob, lab, np.array([0.5, 0.5, 0.5]))
    res = analyse([st], subsample=1)
    # A temperature cannot move the 0.5 crossing (it rescales log-odds about 0): its export is still ~argmax.
    assert res['agreement_dice'] >= 0.99 and abs(res['t_eq_temperature'] - 0.5) < 0.02, res
    # The Platt bias does: the true boundary (r = 4) sits at raw logit -2, p = 0.12.
    assert 0.06 < res['t_eq'] < 0.20, res
    assert res['rim_ece_platt'] < res['rim_ece_raw'], res
    assert 'extend' in reading(dict(res, t_eq=0.2), 0.30, False)[0]
    try:
        check(['c0000'])
        raise AssertionError('a non-tuning case was not refused')
    except SystemExit as e:
        assert 'REFUSING' in str(e)
    print(f"[calib60] self-test passed: T {res['T']} (t_eq {res['t_eq_temperature']}), Platt t_eq {res['t_eq']}, "
          f"rim ECE raw {res['rim_ece_raw']}, temperature {res['rim_ece_cal']}, Platt {res['rim_ece_platt']}")


def check(cases):
    from threshold_export import sealed
    bad = sorted(set(cases) - tuning60()) + sorted(set(cases) & sealed())
    if bad:
        sys.exit(f'[calib60] REFUSING: cases outside the tuning 60 or sealed: {bad[:5]}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--probs'); ap.add_argument('--icx'); ap.add_argument('--out'); ap.add_argument('--np', type=int, default=8)
    ap.add_argument('--select', help="Job 0's select.json (for the reading)")
    ap.add_argument('--fp-rises', action='store_true', help='FP rose at every t < 0.50 in select.json')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    cases = sorted(tuning60())
    check(cases)
    with Pool(a.np) as p:
        got = p.map(load, [(c, a.probs, a.icx) for c in cases], chunksize=1)
    res = analyse([s for _, s in got])
    tstar = float(json.load(open(a.select))['chosen_t']) if a.select else None
    res['reading'] = reading(res, tstar, a.fp_rises)
    res['n'] = len(got)
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
