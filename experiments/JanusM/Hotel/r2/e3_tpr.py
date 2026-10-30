"""Hotel R2 E3: can rest TPR be read per segment at native 0.5 mm with a guard band? (ruling §6 item 6)

A 1-D model of the wall along its normal. No image is opened.
  blood (LV cavity) | myocardium, thickness T, linear transmural HU gradient | epicardial fat (or RV blood: septum)
The true TPR is mean(inner third) / mean(outer third). The profile is blurred by a Gaussian PSF (FWHM f),
integrated over voxels of size v at a random phase, and read the way Janus-M would: thirds by equal thickness
between the *estimated* borders (true borders shifted by a border error), each third trimmed by a guard band g
measured from its own border, TPR = mean(inner) / mean(outer).

The PSF is expressed through the measurable 10-90 % edge width (= 2.563 sigma for a Gaussian): Hotel R1 E1 measured
4.7 mm at the endocardium on 1.5 mm TotalSegmentator CT, and the Fir add-on (r2/fir/halfmax_tpr_m0.py) measures it
on native ImageCAS. This script turns that width into a predicted TPR bias.

    python experiments/JanusM/Hotel/r2/e3_tpr.py OUT.json
"""
import json
import sys

import numpy as np

BLOOD, MYO_EPI, FAT, RV = 450.0, 100.0, -80.0, 350.0
DX = 0.01  # mm, fine grid


def profile(T, tpr, outside):
    """HU on a fine grid from -12 mm (cavity) to T + 12 mm. Myocardium linear in depth with the given TPR."""
    x = np.arange(-12.0, T + 12.0, DX)
    hu = np.full_like(x, outside)
    hu[x < 0] = BLOOD
    m = (x >= 0) & (x < T)
    # linear a + b*u, u = x/T. mean(inner third) = a + b/6, mean(outer third) = a + 5b/6; outer third mean = MYO_EPI
    # solve a + 5b/6 = MYO_EPI, a + b/6 = tpr * MYO_EPI
    b = (MYO_EPI - tpr * MYO_EPI) / (4 / 6)
    a = MYO_EPI - 5 * b / 6
    hu[m] = a + b * x[m] / T
    return x, hu


def blur(x, hu, edge1090):
    if edge1090 <= 0:
        return hu
    s = edge1090 / 2.563
    k = np.arange(-5 * s, 5 * s + DX, DX)
    w = np.exp(-0.5 * (k / s) ** 2)
    w /= w.sum()
    pad = len(k) // 2
    hp = np.pad(hu, pad, mode="edge")
    return np.convolve(hp, w, mode="valid")[: len(hu)]


def voxels(x, hb, v, phase):
    """Voxel centres and voxel-averaged HU, voxel grid offset by phase*v."""
    start = x[0] + phase * v
    edges = np.arange(start, x[-1], v)
    idx = np.searchsorted(x, edges)
    cs = np.concatenate([[0], np.cumsum(hb)])
    vals = (cs[idx[1:]] - cs[idx[:-1]]) / np.maximum(idx[1:] - idx[:-1], 1)
    return (edges[:-1] + edges[1:]) / 2, vals


def read_tpr(T, tpr, outside, edge, v, guard, d_endo, d_epi, phases=16):
    x, hu = profile(T, tpr, outside)
    hb = blur(x, hu, edge)
    out = []
    for p in np.linspace(0, 1, phases, endpoint=False):
        c, val = voxels(x, hb, v, p)
        e0, e1 = 0.0 + d_endo, T + d_epi  # estimated borders (positive d_endo: endocardium read outward into wall)
        Te = e1 - e0
        inner = (c >= e0 + guard) & (c < e0 + Te / 3)
        outer = (c >= e0 + 2 * Te / 3) & (c < e1 - guard)
        if inner.sum() == 0 or outer.sum() == 0:
            return None
        out.append(val[inner].mean() / val[outer].mean())
    return float(np.mean(out)), float(np.std(out))


def main(outp):
    res = {"assumptions": {"blood_HU": BLOOD, "outer_third_HU": MYO_EPI, "fat_HU": FAT, "rv_blood_HU": RV,
                           "myocardium": "linear transmural gradient; TPR is mean(inner third)/mean(outer third)"},
           "rows": []}
    edges = [0.0, 0.8, 1.2, 1.6, 2.4, 3.2, 4.7]
    for wall, outside in (("free", FAT), ("septum", RV)):
        for T in (6.0, 8.0, 10.0, 12.0):
            for tpr in (1.10, 1.00, 0.85):
                for edge in edges:
                    for v in (0.5, 1.5):
                        for guard in (0.0, 0.5, 1.0, 1.5):
                            for d in ((0, 0), (0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5)):
                                r = read_tpr(T, tpr, outside, edge, v, guard, *d)
                                res["rows"].append({"wall": wall, "T_mm": T, "tpr_true": tpr, "edge1090_mm": edge,
                                                    "voxel_mm": v, "guard_mm": guard, "d_endo_mm": d[0],
                                                    "d_epi_mm": d[1],
                                                    "tpr_read": None if r is None else round(r[0], 4),
                                                    "phase_sd": None if r is None else round(r[1], 4)})
    # headline table: free wall, 10 mm, no border error, 0.5 mm voxel
    def get(**k):
        for r in res["rows"]:
            if all(r[a] == b for a, b in k.items()):
                return r["tpr_read"]
    head = {}
    for edge in edges:
        head[str(edge)] = {f"guard{g}": [get(wall="free", T_mm=10.0, tpr_true=t, edge1090_mm=edge, voxel_mm=0.5,
                                             guard_mm=g, d_endo_mm=0, d_epi_mm=0) for t in (1.10, 1.00, 0.85)]
                           for g in (0.0, 1.0)}
    res["headline_free_10mm_v05_[1.10,1.00,0.85]"] = head
    with open(outp, "w") as fh:
        json.dump(res, fh, indent=1)
    for e, h in head.items():
        print("edge", e, h)


if __name__ == "__main__":
    main(sys.argv[1])
