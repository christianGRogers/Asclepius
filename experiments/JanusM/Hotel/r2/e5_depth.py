"""Hotel R2 E5: equal-thickness depth against Yezzi-Prince depth (and raw Laplace) at 0.5 mm (ruling §6 item 3).

Synthetic only: the E2 phantom with its continuous SDF, voxelised at 0.5 mm. Also a thinned variant (a 6 mm
lateral wall made 4 mm by moving the cavity), where the definitions should disagree most.

Yezzi-Prince (2003): solve Laplace u (0 at the cavity, 1 outside), take T = grad u / |grad u|; L0 and L1 are the
lengths of the streamline of T from a voxel to the endocardium and to the epicardium. Here they are traced
directly (RK2, 0.1 mm steps) on 20,000 random myocardial voxels, which is what the PDE of Yezzi and Prince computes
everywhere. (An upwind fixed-point solver was tried first and diverged where neighbouring streamlines point at
each other.) Depth = L0 / (L0 + L1), thickness = L0 + L1.
Each depth is cut into thirds at 1/3, 2/3. Reported: voxel agreement of thirds, volume share of each third, and
the median thickness each definition gives in the thin and thick wall.

    python experiments/JanusM/Hotel/r2/e5_depth.py OUT.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e2_harness import depth_equal, depth_laplace, phantom_sdf, sectors, thirds  # noqa: E402

G = 0.5


def yezzi_prince(u, cav, sol, g, pts, step=0.1, max_mm=40.0):
    """Streamline lengths L0 (to the endocardium) and L1 (to the epicardium) for voxel indices pts, by RK2 tracing
    through T = grad u / |grad u|. A path ends where the trilinear cavity (or outside) indicator reaches 0.5, which
    is the voxel border. Paths longer than max_mm are returned as NaN (reported, not hidden)."""
    from scipy.ndimage import map_coordinates
    uu = np.where(cav, 0.0, np.where(sol, u, 1.0)).astype(np.float32)
    grads = [x.astype(np.float32) for x in np.gradient(uu, g)]
    icav, iout = cav.astype(np.float32), (~sol).astype(np.float32)

    def T(p):
        v = np.stack([map_coordinates(gr, p.T, order=1, mode="nearest") for gr in grads], 1)
        return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)

    res = []
    for sign, stop in ((-1.0, icav), (1.0, iout)):
        p = pts.astype(np.float64).copy()
        L = np.zeros(len(p))
        alive = np.ones(len(p), bool)
        h = step / g  # step in voxel units
        for _ in range(int(max_mm / step)):
            if not alive.any():
                break
            q = p[alive]
            k1 = sign * T(q)
            k2 = sign * T(q + 0.5 * h * k1)
            q = q + h * k2
            p[alive] = q
            L[alive] += step
            done = map_coordinates(stop, q.T, order=1, mode="nearest") >= 0.5
            idx = np.flatnonzero(alive)
            alive[idx[done]] = False
        L[alive] = np.nan
        res.append(L)
    return res[0], res[1]


def run(Sc, Ss, label):
    sol = Ss < 0
    cav = (Sc < 0) & sol
    myo = sol & ~cav
    seg = sectors(Sc.shape, G, 42.0, 42.0)
    roi = myo & (seg >= 0)
    ue, th_e = depth_equal(cav, myo, G)
    ul = depth_laplace(cav, sol, G)
    idx = np.argwhere(roi)
    idx = idx[np.random.default_rng(7).choice(len(idx), min(20000, len(idx)), replace=False)]
    L0, L1 = yezzi_prince(ul, cav, sol, G, idx)
    ok = ~(np.isnan(L0) | np.isnan(L1))
    idx, L0, L1 = idx[ok], L0[ok], L1[ok]
    # every comparison below is on the traced sample, so all three depths are compared on the same voxels
    sel = tuple(idx.T)
    uy_s = L0 / np.maximum(L0 + L1, 1e-9)
    ty_s = (1 + (uy_s >= 1 / 3) + (uy_s >= 2 / 3)).astype(np.int8)
    te, tl = thirds(ue, myo)[sel], thirds(ul, myo)[sel]
    ty, th_e, th_y = ty_s, th_e[sel], L0 + L1
    roi = np.ones(len(ty), bool)
    r = {"case": label, "n_traced": int(len(ty)), "n_untraced": int((~ok).sum())}
    for a, b, n in ((te, ty, "equal_vs_yezzi"), (te, tl, "equal_vs_laplace"), (tl, ty, "laplace_vs_yezzi")):
        r["agree_" + n] = round(float((a[roi] == b[roi]).mean()), 4)
    for t, n in ((te, "equal"), (tl, "laplace"), (ty, "yezzi")):
        r["share_" + n] = [round(float((t[roi] == k).mean()), 4) for k in (1, 2, 3)]
    for lab, sel in (("thin", th_e < 7.0), ("thick", th_e > 12.0)):
        m = roi & sel
        r[f"n_{lab}"] = int(m.sum())
        if m.any():
            r[f"agree_equal_vs_yezzi_{lab}"] = round(float((te[m] == ty[m]).mean()), 4)
            r[f"thick_equal_median_{lab}"] = round(float(np.median(th_e[m])), 2)
            r[f"thick_yezzi_median_{lab}"] = round(float(np.median(th_y[m])), 2)
            r[f"share_equal_{lab}"] = [round(float((te[m] == k).mean()), 3) for k in (1, 2, 3)]
            r[f"share_yezzi_{lab}"] = [round(float((ty[m] == k).mean()), 3) for k in (1, 2, 3)]
    r["thick_median_equal_yezzi"] = [round(float(np.median(th_e[roi])), 2), round(float(np.median(th_y[roi])), 2)]
    print(json.dumps(r), flush=True)
    return r


def main(out):
    Sc, Ss = phantom_sdf(G)
    res = [run(Sc, Ss, "phantom")]
    # thinned variant: move the cavity 2 mm further toward +x, so the thin wall goes from about 6 to 4 mm
    Sc2, _ = phantom_sdf(G)
    Sc2 = np.roll(Sc2, int(2.0 / G), axis=0)
    res.append(run(Sc2, Ss, "thinned_lateral_4mm"))
    Path(out).write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
