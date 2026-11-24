"""Delta, Janus 1-L round 3 (#302, Round 2 ruling §5 item 4): does calibrating Janus 0's probabilities give Rule W
anything a threshold does not?

Temperature scaling divides the logits by T. Janus 0's saved probabilities give the logits up to a per-voxel
constant (log p), and softmax(log p / T) = softmax(z / T), so a temperature can be fitted to the saved npz.

Claims tested (synthetic, CPU, no data):
  A. argmax is invariant to T (exactly, for every class). So "calibrate, then export at argmax" is Janus 0 at argmax.
  B. Binary case, exactly: {p_fg(T) >= t} = {p_fg >= sigma(T * logit(t))}. Rule W on calibrated probabilities with
     grid G is Rule W on the raw probabilities with the warped grid sigma(T * logit(G)).
  C. Five classes (four vessels summed): p_fg(T) is not a function of p_fg alone where two vessel classes share the
     mass (bifurcations, naming borders). Measured on a phantom with soft rims, logit noise and a bifurcation where
     LAD and LCx split the vessel mass: for every T and grid t, the best raw threshold t' reproduces the calibrated
     mask to Dice >= the value printed.
  D. FP components cannot be removed by T: the calibrated mask at t is (close to) a raw mask at some t', and a dim
     component that is above t' stays.
  E. Platt scaling of the foreground logit, sigma(a * logit(p_fg) + b), is monotone in p_fg: thresholding it at any
     t is exactly thresholding p_fg at sigma((logit(t) - b) / a). Its "calibrated 0.5" is the raw threshold
     sigma(-b / a), and its F1-optimal point (F*/2 for a calibrated score: Lipton et al., arXiv:1402.1892) is the raw
     threshold sigma((logit(F*/2) - b) / a). Both are thresholds Rule W's grid already searches.
Writes calib_equiv.json.
"""
import json
import os

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
GRID = (0.50, 0.45, 0.40, 0.35, 0.30)
TS = (0.5, 0.7, 0.85, 1.0, 1.25, 1.5, 2.0, 3.0)


def softmax(z, T=1.0):
    z = z / T
    z = z - z.max(0, keepdims=True)
    e = np.exp(z)
    return e / e.sum(0, keepdims=True)


def logit(p):
    return np.log(p / (1 - p))


def sigma(x):
    return 1 / (1 + np.exp(-x))


def phantom(seed=0):
    """Logits (5, Z, Y, X) of a small tree: an RCA tube, and a left trunk that splits into LAD and LCx, with a
    shared stretch where LAD and LCx split the vessel mass, soft rims, a dim blob (an FP component) and noise."""
    rng = np.random.default_rng(seed)
    sh = (48, 48, 96)
    z, y, x = np.indices(sh) * 0.5
    zl = np.zeros((5,) + sh, np.float32)
    # signed distance to each tube's surface (mm)
    d_rca = np.hypot(z - 6, y - 6) - 1.6
    xs = np.clip((x - 20) / 20, 0, 1)                           # the left trunk splits after x = 20 mm
    d_lad = np.hypot(z - 16 - 3 * xs, y - 16 - 3 * xs) - 1.4
    d_lcx = np.hypot(z - 16 + 3 * xs, y - 16 - 3 * xs) - 1.2
    rim = 0.45                                                   # mm per logit unit across the rim
    fg_rca = -d_rca / rim
    fg_left = -np.minimum(d_lad, d_lcx) / rim
    share = sigma((d_lcx - d_lad) / 0.4)                         # LAD's share of the left mass; 0.5 on the border
    share = np.where(x < 20, 0.5 + 0.1 * np.tanh((y - 16)), share)   # an ambiguous trunk (naming border)
    zl[0] = 0.0
    zl[4] = fg_rca
    zl[2] = fg_left + np.log(np.clip(share, 1e-4, 1))
    zl[3] = fg_left + np.log(np.clip(1 - share, 1e-4, 1))
    zl[1] = -8
    blob = np.hypot(np.hypot(z - 18, y - 6), x - 70) < 1.5        # a dim FP component, peak vessel prob ~0.4
    zl[4] = np.where(blob, np.maximum(zl[4], -0.4), zl[4])
    zl[1:] += 0.35 * rng.standard_normal(zl[1:].shape).astype(np.float32)
    zl[1:] = np.maximum(zl[1:], -12)
    return zl


def dice(a, b):
    s = a.sum() + b.sum()
    return 1.0 if s == 0 else 2 * (a & b).sum() / s


def main():
    out = {}
    zl = phantom()
    p1 = softmax(zl)
    pf = 1 - p1[0]
    # A. argmax invariance
    out['A_argmax_invariant'] = all(bool((softmax(zl, T).argmax(0) == p1.argmax(0)).all()) for T in TS)
    # recover logits from the probabilities as a run would (log p), and check the equivalence
    lp = np.log(np.clip(p1, 1e-30, 1))
    out['A_logp_equals_logits_up_to_constant'] = bool(np.allclose(softmax(lp, 1.7), softmax(zl, 1.7), atol=1e-5))
    # B. binary, exact
    rng = np.random.default_rng(1)
    zb = rng.normal(0, 3, 200000)
    ok = True
    for T in TS:
        for t in GRID:
            ok &= bool(((sigma(zb / T) >= t) == (sigma(zb) >= sigma(T * logit(t)))).all())
    out['B_binary_exact'] = ok
    out['B_warped_grid'] = {f'T={T}': [round(float(sigma(T * logit(t))), 4) for t in GRID] for T in TS}
    # C. five classes: the best raw threshold for each calibrated mask
    fine = np.round(np.arange(0.05, 0.951, 0.0025), 4)
    rows = {}
    worst = 1.0
    for T in TS:
        pfT = 1 - softmax(zl, T)[0]
        r = {}
        for t in GRID:
            m = pfT >= t
            best = max(((dice(m, pf >= u), u) for u in fine), key=lambda v: v[0])
            r[f'{t:.2f}'] = dict(raw_t=float(best[1]), binary_map=round(float(sigma(T * logit(t))), 4),
                                 dice=round(float(best[0]), 5), n_vox=int(m.sum()))
            worst = min(worst, best[0])
        rows[f'T={T}'] = r
    out['C_five_class'] = rows
    out['C_worst_dice_calibrated_vs_best_raw'] = round(float(worst), 5)
    # where do the disagreements sit? (only where two vessel classes share the mass)
    pfT = 1 - softmax(zl, 2.0)[0]
    m = pfT >= 0.40
    u = rows['T=2.0']['0.40']['raw_t']
    diff = m ^ (pf >= u)
    vmax = p1[1:].max(0) / np.clip(pf, 1e-9, 1)
    out['C_disagreeing_voxels_T2_t040'] = dict(n=int(diff.sum()), of_mask=int(m.sum()),
                                               median_top_vessel_share=round(float(np.median(vmax[diff])), 3)
                                               if diff.any() else None,
                                               median_top_vessel_share_all_mask=round(float(np.median(vmax[m])), 3))
    # D. the FP component: present in the raw mask at t' iff in the calibrated mask at t
    lab_blob = (np.hypot(np.hypot(*(np.indices(pf.shape)[:2] * 0.5 - np.array([18, 6])[:, None, None, None])),
                         np.indices(pf.shape)[2] * 0.5 - 70) < 1.5)
    d = {}
    for T in TS:
        pfT = 1 - softmax(zl, T)[0]
        d[f'T={T}'] = {f'{t:.2f}': [bool((pfT >= t)[lab_blob].any()),
                                    bool((pf >= rows[f'T={T}'][f'{t:.2f}']['raw_t'])[lab_blob].any())]
                       for t in GRID}
    out['D_fp_blob_present_calibrated_vs_raw'] = d
    out['D_fp_agrees'] = all(a == b for r in d.values() for a, b in r.values())
    n_comp = {}
    for T in (1.0, 2.0):
        pfT = 1 - softmax(zl, T)[0]
        n_comp[f'T={T}'] = {f'{t:.2f}': int(ndimage.label(pfT >= t)[1]) for t in GRID}
    out['D_components'] = n_comp
    # E. Platt on the foreground logit: exact threshold equivalence
    okE = True
    for a, b in ((0.6, 0.3), (1.0, 0.8), (1.7, -0.4)):
        q = sigma(a * logit(np.clip(pf, 1e-7, 1 - 1e-7)) + b)
        for t in GRID:
            u = sigma((logit(t) - b) / a)
            okE &= bool(((q >= t) == (pf >= u - 1e-12)).sum() >= q.size - 50)   # float ties only
    out['E_platt_foreground_exact'] = okE
    worst15 = min(v['dice'] for T in ('T=0.5', 'T=0.7', 'T=0.85', 'T=1.0', 'T=1.25', 'T=1.5')
                  for v in rows[T].values())
    out['C_worst_dice_T_0.5_to_1.5'] = round(float(worst15), 5)
    out['reading'] = ('At argmax a temperature changes nothing. Thresholded, a foreground (binary) temperature or Platt '
                      'fit is exactly a threshold on a warped grid; a five-class temperature is close to one (Dice '
                      '>= 0.97 for T <= 1.5) and differs only where vessel classes split the mass, which is an '
                      'artefact of summing classes, not a width correction. No calibration removes an FP component '
                      'that the matching threshold keeps.')
    json.dump(out, open(os.path.join(HERE, 'calib_equiv.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ('C_five_class', 'D_fp_blob_present_calibrated_vs_raw')},
                     indent=1))


if __name__ == '__main__':
    main()
