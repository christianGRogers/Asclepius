"""Janus-M Job JM-0 add-on (India v2), CPU, Fir login node. Runs after Juliet's Job JM-0 on the same 40 cases.

Measures on native ImageCAS-X CCTA (about 0.35-0.43 mm in-plane, 0.5 mm slices) what Round 2 could only simulate
(ruling §6 items 1, 3 and 6):
  A. half-maximum edge offsets of `heartchambers_highres` (Hotel's rule): where the label's endocardial and free-wall
     epicardial borders sit relative to the image's half-way HU between the adjacent plateaus (mm, + = label outside);
  B. equal-thickness (JA2) vs Laplace third agreement at native resolution;
  C. fixed (JA3) vs septal-arc-proportional sectors: share of myocardium that changes segment / AHA territory;
  D. Euclidean (JA4) vs epicardial-geodesic territories, from the ImageCAS-X reference coronary labels: voxel
     disagreement, and segments discordant with the AHA default under each;
  E. rest TPR per segment (inner/outer third mean HU) with no guard band and with a 1 mm guard band (JA11);
  F. the myocardial core-sample HU distribution (>= 1 mm from either border) for the data-driven fat cut-off:
     pooled quantiles and the share of core voxels in -180..0 HU.
Prints and writes aggregates only (no per-case rows, no image).

Guard: reads only the JM-0 list written by Juliet's draw (m0_cases.txt); refuses the whole run if any case is in
the Janus-M seal or decision proposals written next to it, or in the A14 sealed / ImageCAS-X test lists.

    python experiments/JanusM/India/fir/jm0_addon.py --cases $SCRATCH/janusm/m0_cases.txt --hc $SCRATCH/janusm/hc \
        --icx $SCRATCH/icx4/icx --layout $SCRATCH/icx4/layout.json --out $SCRATCH/janusm/m0_india_addon.json
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(REPO / "trillium/icx4/lib"))
import lvgeom as G  # noqa: E402
from e6_depth_sectors import aha_prop, terr  # noqa: E402

HC_FALLBACK = {1: "heart_myocardium", 2: "heart_atrium_left", 3: "heart_ventricle_left", 4: "heart_atrium_right",
               5: "heart_ventricle_right", 6: "aorta", 7: "pulmonary_artery"}
AHA_T = {**{s: "LAD" for s in (1, 2, 7, 8, 13, 14, 17)}, **{s: "RCA" for s in (3, 4, 9, 10, 15)},
         **{s: "LCx" for s in (5, 6, 11, 12, 16)}}


def guard(cases_file):
    cases = Path(cases_file).read_text().split()
    d = Path(cases_file).parent
    bad = set()
    for name in ("janusm_seal_proposal.txt", "janusm_decision_proposal.txt"):
        p = d / name
        if not p.exists():
            sys.exit(f"REFUSED: {p} missing; run Juliet's draw first")
        bad |= set(p.read_text().split())
    import sealed
    S = sealed.load(str(REPO / "trillium/icx4/sealed_test.json"))
    bad |= sealed.sealed_set(S) | set(S["open_icx_test"]) | set(S["excluded_dev_cases_in_test"])
    hit = sorted(set(cases) & bad)
    if hit or len(cases) != 40:
        sys.exit(f"REFUSED: {len(hit)} JM-0 cases are sealed or decision cases, or the list is not 40 long")
    return cases


def hc_map():
    try:
        from totalsegmentator.map_to_binary import class_map
        return {v: k for k, v in class_map["heartchambers_highres"].items()}
    except Exception:  # noqa: BLE001
        return {v: k for k, v in HC_FALLBACK.items()}


def crop(arrs, mask, margin_mm, sp):
    idx = np.argwhere(mask)
    mg = np.ceil(margin_mm / sp).astype(int)
    lo, hi = np.maximum(idx.min(0) - mg, 0), np.minimum(idx.max(0) + mg + 1, mask.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    return [a[sl] for a in arrs], lo


def edge_offset(ct, inside, outside_ok, sp, plateau_in, plateau_out):
    """Half-maximum offset (mm, + = label border outside the image edge) of the border of `inside`."""
    din = ndi.distance_transform_edt(inside, sampling=sp)
    dout = ndi.distance_transform_edt(~inside, sampling=sp)
    sd = np.where(inside, din - sp.mean() / 2, -(dout - sp.mean() / 2))   # + inside the label
    m = inside | outside_ok
    bins = np.arange(-3.0, 3.01, 0.25)
    prof = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        v = ct[m & (sd >= lo) & (sd < hi)]
        prof.append(np.median(v) if v.size > 30 else np.nan)
    prof = np.array(prof)
    mid = (bins[:-1] + bins[1:]) / 2
    pin = np.nanmedian(prof[(mid > plateau_in[0]) & (mid < plateau_in[1])])
    pout = np.nanmedian(prof[(mid > plateau_out[0]) & (mid < plateau_out[1])])
    half = (pin + pout) / 2
    ok = ~np.isnan(prof)
    x, y = mid[ok], prof[ok]
    s = np.sign(y - half)
    k = np.flatnonzero(np.diff(s) != 0)
    if not len(k):
        return None
    k = k[np.argmin(np.abs(x[k]))]                                         # crossing nearest the label border
    xc = x[k] + (half - y[k]) * (x[k + 1] - x[k]) / (y[k + 1] - y[k])
    return float(xc)           # the image edge lies xc mm inside the label: the label border is xc mm outward


def geodesic_territory(myo, sol, cor, sp):
    """Territory by geodesic distance over the epicardial shell from each vessel's projection onto it; each
    myocardial voxel then takes its nearest shell voxel's label. Returns labels (1 LAD, 2 LCx, 3 RCA) on myo."""
    shell = sol & ~ndi.binary_erosion(sol, G.STRUCT)
    P = np.argwhere(shell)
    idx = -np.ones(shell.shape, np.int64)
    idx[tuple(P.T)] = np.arange(len(P))
    rows, cols, w = [], [], []
    for off in np.argwhere(np.ones((3, 3, 3))) - 1:
        if not off.any():
            continue
        Q = P + off
        ok = np.all((Q >= 0) & (Q < shell.shape), 1)
        j = idx[tuple(Q[ok].T)]
        good = j >= 0
        rows.append(np.flatnonzero(ok)[good]); cols.append(j[good])
        w.append(np.full(good.sum(), float(np.linalg.norm(off * sp))))
    A = coo_matrix((np.concatenate(w), (np.concatenate(rows), np.concatenate(cols))), shape=(len(P),) * 2).tocsr()
    tree = cKDTree(P * sp)
    lab_shell = np.zeros(len(P), np.uint8)
    best = np.full(len(P), np.inf)
    for v, cls in ((1, 2), (2, 3), (3, 4)):          # to_four classes: 2 LAD, 3 LCx, 4 RCA
        vp = np.argwhere(cor == cls)
        if len(vp) < 20:
            continue
        dist, src = tree.query(vp * sp)
        src = np.unique(src[dist < 10.0])
        if not len(src):
            continue
        dd = dijkstra(A, indices=src, min_only=True)
        upd = dd < best
        best[upd], lab_shell[upd] = dd[upd], v
    M = np.argwhere(myo)
    _, nn = tree.query(M * sp)
    out = np.zeros(myo.shape, np.uint8)
    out[tuple(M.T)] = lab_shell[nn]
    return out


def euclid_territory(myo, cor, sp):
    pts = np.argwhere(np.isin(cor, (2, 3, 4)))
    M = np.argwhere(myo)
    _, nn = cKDTree(pts * sp).query(M * sp)
    out = np.zeros(myo.shape, np.uint8)
    out[tuple(M.T)] = np.array([0, 0, 1, 2, 3])[cor[tuple(pts[nn].T)]]
    return out


def one(c, a, ids, layout):
    from territory import to_four
    hi = nib.as_closest_canonical(nib.load(str(Path(a.hc) / f"{c}.nii.gz")))
    ci = nib.as_closest_canonical(nib.load(layout[c]["ct"]))
    li = nib.as_closest_canonical(nib.load(str(Path(a.icx) / f"{int(c[1:]) + 1}.coronary.nii.gz")))
    if not (hi.shape == ci.shape == li.shape) or not np.allclose(hi.affine, ci.affine, atol=1e-3):
        return None
    sp = np.asarray(hi.header.get_zooms()[:3], float)
    hc = np.asarray(hi.dataobj).astype(np.int16)
    m = {k: hc == ids[k] for k in ("heart_myocardium", "heart_ventricle_left", "heart_ventricle_right",
                                   "heart_atrium_left", "aorta")}
    myo, lv = G.keep_largest(m["heart_myocardium"]), G.keep_largest(m["heart_ventricle_left"])
    myo &= ~lv
    ct = np.asarray(ci.dataobj).astype(np.float32)
    cor = to_four(np.asarray(li.dataobj).astype(np.int64), sp)
    (myo, lv, rv, la, ao, ct, cor), lo = crop([myo, lv, m["heart_ventricle_right"], m["heart_atrium_left"],
                                               m["aorta"], ct, cor], myo | lv, 15.0, sp)
    aff = hi.affine.copy()
    aff[:3, 3] = aff[:3, :3] @ lo + aff[:3, 3]
    sol = myo | lv
    out = {}
    # A. half-maximum offsets: endocardium (blood plateau inside the cavity, myocardium plateau in the wall);
    #    free-wall epicardium (myocardium plateau inside, fat/tissue plateau outside, away from RV/LA/aorta).
    #    Sign: + = the label border lies outward of the image edge (endo: cavity label into the wall; epi: wall
    #    label into the fat).
    other = ndi.binary_dilation(rv | la | ao, G.STRUCT, iterations=6)
    out["endo_offset_mm"] = edge_offset(ct, lv, myo, sp, (1.5, 3.0), (-3.0, -1.5))
    free = ~other
    out["epi_offset_mm"] = edge_offset(ct, sol & free, ~sol & free, sp, (1.5, 3.0), (-3.0, -1.5))
    # B. depth agreement (native grid; Laplace on the native voxels)
    et, _ = G.depth_distance(myo, lv, sp)
    lap = G.depth_laplace(myo, lv)
    out["third_agree_et_laplace"] = float((G.layers(et, myo) == G.layers(lap, myo))[myo].mean())
    # C. sectors
    geo = dict(myo=myo, lv=lv, rv=rv & ~sol, la=la & ~sol, affine=aff)
    fr = G.lv_frame(geo)
    if fr is None:
        out["frame"] = False
        return out
    fx, pr = G.aha17(geo, fr), aha_prop(geo, fr)
    k = myo & (fx > 0)
    out["septal_arc_deg"] = float(fr["septal_arc_deg"])
    out["seg_changed_prop"] = float((fx != pr)[k].mean())
    out["terr_changed_prop"] = float((terr(fx) != terr(pr))[k].mean())
    # D. territories
    if np.isin(cor, (2, 3, 4)).sum() >= 50:
        te, tg = euclid_territory(myo, cor, sp), geodesic_territory(myo, sol, cor, sp)
        out["terr_voxel_disagree_euclid_geodesic"] = float((te != tg)[k].mean())
        names = {1: "LAD", 2: "LCx", 3: "RCA"}
        for nm, tt in (("euclid", te), ("geodesic", tg)):
            disc = 0
            n = 0
            for s in range(1, 18):
                sel = k & (fx == s) & (tt > 0)
                if sel.sum() < 20:
                    continue
                n += 1
                disc += names[int(np.bincount(tt[sel]).argmax())] != AHA_T[s]
            out[f"segments_discordant_{nm}"] = [int(disc), int(n)]
    # E. rest TPR, no guard / 1 mm guard
    d_endo = ndi.distance_transform_edt(~lv, sampling=sp)
    d_epi = ndi.distance_transform_edt(sol, sampling=sp)
    L = G.layers(et, myo)
    for gname, gmm in (("tpr_noguard", 0.0), ("tpr_guard1mm", 1.0)):
        core = myo & (d_endo > gmm + sp.mean() / 2) & (d_epi > gmm)
        v = []
        for s in range(1, 17):
            sel = core & (fx == s)
            i1, i3 = ct[sel & (L == 1)], ct[sel & (L == 3)]
            if i1.size >= 20 and i3.size >= 20 and i3.mean() > 20:
                v.append(float(i1.mean() / i3.mean()))
        out[gname] = v
    # F. core HU sample
    core = myo & (d_endo >= 1.0 + sp.mean() / 2) & (d_epi >= 1.0)
    out["core_hu"] = ct[core][:: max(1, core.sum() // 20000)].tolist()
    out["blood_hu"] = float(np.median(ct[ndi.binary_erosion(lv, G.STRUCT, iterations=3)]))
    return out


def main():
    ap = argparse.ArgumentParser()
    for k in ("cases", "hc", "icx", "layout", "out"):
        ap.add_argument(f"--{k}", required=True)
    a = ap.parse_args()
    cases = guard(a.cases)
    ids = hc_map()
    layout = json.load(open(a.layout))["cases"]
    rows = []
    for c in cases:
        try:
            r = one(c, a, ids, layout)
        except Exception as e:  # noqa: BLE001
            r = {"error": repr(e)[:120]}
        rows.append(r or {"error": "grid mismatch"})
        print(f"case {len(rows)}/40", "ok" if r and "error" not in r else "fail", flush=True)
    ok = [r for r in rows if "error" not in r and r.get("frame", True)]
    med = lambda k: float(np.nanmedian([r[k] for r in ok if r.get(k) is not None])) if ok else None
    q = lambda k, p: float(np.nanpercentile([r[k] for r in ok if r.get(k) is not None], p)) if ok else None
    tpr = {g: np.concatenate([r[g] for r in ok if r.get(g)]) for g in ("tpr_noguard", "tpr_guard1mm")}
    core = np.concatenate([np.asarray(r["core_hu"]) for r in ok]) if ok else np.zeros(0)
    disc = {nm: np.sum([r[f"segments_discordant_{nm}"] for r in ok if f"segments_discordant_{nm}" in r], 0).tolist()
            for nm in ("euclid", "geodesic")}
    summ = {
        "n_cases": len(rows), "n_ok": len(ok),
        "A_endo_offset_mm_median_p10_p90": [med("endo_offset_mm"), q("endo_offset_mm", 10), q("endo_offset_mm", 90)],
        "A_epi_offset_mm_median_p10_p90": [med("epi_offset_mm"), q("epi_offset_mm", 10), q("epi_offset_mm", 90)],
        "B_third_agree_et_laplace_median": med("third_agree_et_laplace"),
        "C_septal_arc_deg_median_p10_p90": [med("septal_arc_deg"), q("septal_arc_deg", 10), q("septal_arc_deg", 90)],
        "C_seg_changed_prop_median": med("seg_changed_prop"), "C_terr_changed_prop_median": med("terr_changed_prop"),
        "D_terr_voxel_disagree_euclid_geodesic_median": med("terr_voxel_disagree_euclid_geodesic"),
        "D_segments_discordant_with_AHA_[n,of]": disc,
        "E_tpr_segments_median_p10_p90": {g: [float(np.median(v)), float(np.percentile(v, 10)),
                                              float(np.percentile(v, 90)), int(v.size)] if v.size else None
                                          for g, v in tpr.items()},
        "E_share_segments_below_0.99": {g: float((v < 0.99).mean()) if v.size else None for g, v in tpr.items()},
        "F_core_hu_quantiles_p0.1_p0.5_p1_p5_p50": [float(np.percentile(core, p)) for p in (0.1, 0.5, 1, 5, 50)]
        if core.size else None,
        "F_core_share_in_-180_0": float(((core >= -180) & (core <= 0)).mean()) if core.size else None,
        "blood_hu_median": med("blood_hu"),
    }
    Path(a.out).write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
