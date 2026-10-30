"""Golf E3: can scar transmurality be graded on late-iodine-enhancement CT, and where must the borders come from?

A segment of LV wall is simulated as N transmural profiles (wall thickness T mm, from E2's measured range), each
with subendocardial scar of extent e (fraction of T, the Kim et al. 2000 grading: 0, 1-25, 26-50, 51-75, 76-100 %).
Intensities are given relative to remote myocardium in units of the scar-remote contrast (remote 0, scar 1);
blood pool is either "bright" (b = 1, as bright as scar: the hard LIE case) or "dark" (b = 0.3); epicardial fat -2.
The profile is blurred by a Gaussian PSF (FWHM w mm), sampled at voxel v mm, and gets white noise of SD 1/CNR, where
CNR is the scar-remote contrast-to-noise ratio *at the analysis voxel* (after reconstruction and any denoising), so
resolution (w, v) and noise (CNR) are separate axes.

Segment transmurality = scar voxels / wall voxels, with scar = voxel > remote mean + k * remote SD (remote taken
from a scar-free segment of the same image; k = 2, 3, 5), and the wall either
  (G) given: endocardial and epicardial borders known exactly (e.g. from the registered first-pass CCTA), or
  (S) self: the endocardial border found on the LIE profile itself, as the first two voxels that leave the
      blood level by half the smaller blood-remote / blood-scar step (an LIE-only model has nothing else).
Outputs: mean absolute transmurality error (percentage points) and the share of segments put in the right Kim bin.

Usage: python transmural_sim.py   (writes transmural_sim.json next to this file; ~1 min)
"""
import itertools, json
from pathlib import Path

import numpy as np

RNG = np.random.default_rng(130)
DX = 0.05                      # mm, the continuous-profile grid
BINS = np.array([0, 0.005, 0.25, 0.50, 0.75, 1.0001])  # Kim 2000 bins: 0 | 1-25 | 26-50 | 51-75 | 76-100 %


def kim_bin(x):
    return int(np.searchsorted(BINS, x, side="right") - 1)


def profiles(T, ext, b, n, w, v, cnr):
    """n blurred, sampled, noisy profiles; returns samples, voxel centres (mm from endocardium), and truth."""
    pad = 6.0
    x = np.arange(-pad, T + pad, DX)
    ext_i = np.clip(ext + RNG.normal(0, 0.05, n) * (ext > 0), 0, 1)        # mild variation within the segment
    sig = w / 2.3548
    k = np.arange(-4 * sig, 4 * sig + DX, DX)
    kern = np.exp(-0.5 * (k / sig) ** 2); kern /= kern.sum()
    centres = np.arange(-pad + v / 2, T + pad, v) + RNG.uniform(0, v)       # random phase of the voxel grid
    out = np.empty((n, len(centres)))
    for i in range(n):
        f = np.where(x < 0, b, np.where(x > T, -2.0, np.where(x < ext_i[i] * T, 1.0, 0.0)))
        g = np.convolve(f, kern, mode="same")
        # box-average over the voxel, then sample at centres
        box = int(round(v / DX))
        g = np.convolve(g, np.ones(box) / box, mode="same")
        out[i] = np.interp(centres, x, g)
    sd = 1.0 / cnr
    return out + RNG.normal(0, sd, out.shape), centres, float(ext_i.mean())


def grade(samples, centres, T, b, thr, mode):
    scar = wall = 0
    for s in samples:
        if mode == "G":
            inwall = (centres >= 0) & (centres <= T)
        else:  # self: walk out from the blood pool to the first two voxels that leave the blood level
            dev = 0.5 * (min(b, 1 - b) if b < 1 else b)      # half the smaller step blood -> remote / scar
            start = np.searchsorted(centres, -3.0)
            off = np.abs(s[start:] - b) > dev
            two = np.nonzero(off[:-1] & off[1:])[0]
            endo = centres[start + two[0]] - (centres[1] - centres[0]) / 2 if two.size else T
            inwall = (centres >= endo) & (centres <= T)
            # with bright blood, scar as bright as blood is read as cavity: the wall shrinks and the scar is lost
        wall += inwall.sum()
        scar += (inwall & (s > thr)).sum()
    return scar / max(wall, 1)


def main():
    res = []
    Ts, exts = [8.0, 11.0], [0.0, 0.15, 0.35, 0.6, 0.9]
    for w, v, cnr, b, k, mode in itertools.product([0.6, 1.0], [0.5, 1.0, 1.5], [1.5, 2.0, 3.0, 5.0],
                                                   [1.0, 0.3], [2, 3, 5], ["G", "S"]):
        errs, hits = [], []
        for T in Ts:
            # remote reference from a scar-free segment
            rem, c, _ = profiles(T, 0.0, b, 150, w, v, cnr)
            wall = rem[:, (c >= 1.0) & (c <= T - 1.0)]
            thr = wall.mean() + k * wall.std()
            for e in exts:
                for rep in range(4):
                    s, c, truth = profiles(T, e, b, 150, w, v, cnr)
                    est = grade(s, c, T, b, thr, mode)
                    errs.append(abs(est - truth) * 100)
                    hits.append(kim_bin(est) == kim_bin(truth))
        res.append({"psf_fwhm_mm": w, "voxel_mm": v, "cnr_per_voxel": cnr, "blood": "bright" if b == 1.0 else "dark",
                    "k_sd": k, "borders": mode, "mae_pp": round(float(np.mean(errs)), 1),
                    "kim_bin_accuracy": round(float(np.mean(hits)), 3)})
    Path(__file__).with_suffix(".json").write_text(json.dumps(res, indent=1))
    # short table: best k per condition
    best = {}
    for r in res:
        key = (r["psf_fwhm_mm"], r["voxel_mm"], r["cnr_per_voxel"], r["blood"], r["borders"])
        if key not in best or r["kim_bin_accuracy"] > best[key]["kim_bin_accuracy"]:
            best[key] = r
    print("fwhm vox cnr blood borders | best k  MAE(pp)  Kim-bin acc")
    for key, r in sorted(best.items()):
        print(*key, "|", r["k_sd"], r["mae_pp"], r["kim_bin_accuracy"])


if __name__ == "__main__":
    main()
