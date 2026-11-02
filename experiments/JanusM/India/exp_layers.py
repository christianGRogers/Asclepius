"""India v1 experiments E1-E4 on the TotalSegmentator v1 cardiac subjects (pool subjects excluded).

    python exp_layers.py DATA_DIR OUT_DIR [--workers 4]

Per subject, writes OUT_DIR/<sid>.json; `summarise.py` pools them. Images are never written out.

E1  wall geometry: mid-wall thickness (mm), voxels across the wall and per third at 1.5 mm (the label grid of the
    largest open CT myocardium set) and at 0.5 mm (a CCTA-like grid).
E2  border error -> layers and scar: Laplace vs distance thirds; smooth random border displacement (std 0.25,
    0.5, 1.0, 1.5 mm) and a +0.5 mm epicardial bias; Dice of the myocardium and of each third; and synthetic
    subendocardial scar of known depth (10, 20, ..., 90 % of the wall) in the LAD segments, read back on the
    perturbed borders and binned 0 / 1-25 / 26-50 / 51-75 / 76-100 %.
E3  AHA frame: the septal (RV-contact) arc; myocardium mass that changes segment, and default territory, when the
    long axis tilts 5 or 10 degrees, the RV-insertion reference rotates 10 degrees, or the base moves 5 mm.
E4  rest attenuation by layer: mean HU of the subendocardial and subepicardial thirds on the native grid and their
    ratio (a rest "transmural perfusion ratio", George et al. 2009), as a noise-floor for a layer marker.
"""
from __future__ import annotations

import argparse, json, os, sys, traceback
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lvgeom as G  # noqa: E402
from fetch_ts_cardiac import pool_subjects  # noqa: E402

SIGMAS = (0.25, 0.5, 1.0, 1.5)
CORR_MM = 8.0
LAD_SEGS = (1, 2, 7, 8, 13, 14, 17)
BINS = (0, 1, 26, 51, 76, 101)  # transmurality bins in percent: 0, 1-25, 26-50, 51-75, 76-100


def tbin(pct):
    if pct < 0.5:
        return 0
    return int(np.searchsorted(BINS, pct, side="right") - 1)


def qc(sub):
    ct = sub["ct"]
    hu_lv = float(np.median(ct[sub["lv"]])) if sub["lv"].any() else np.nan
    hu_myo = float(np.median(ct[sub["myo"]])) if sub["myo"].any() else np.nan
    # is the cavity enclosed by myocardium (apart from the valve openings)?
    shell = ndi.binary_dilation(sub["lv"], G.STRUCT) & ~sub["lv"]
    enclosed = float((shell & (sub["myo"] | sub["la"] | sub["ao"])).sum() / max(shell.sum(), 1))
    return dict(hu_lv=hu_lv, hu_myo=hu_myo, enclosed=enclosed, touches_edge=sub["touches_edge"],
                myo_ml=float(sub["myo"].sum() * np.prod(sub["spacing"]) / 1000),
                lv_ml=float(sub["lv"].sum() * np.prod(sub["spacing"]) / 1000))


def transmurality(scar, myo, seg, segs):
    """Per segment, scar volume / myocardium volume, in percent (the usual LGE read: extent of the wall)."""
    out = {}
    for s in segs:
        m = myo & (seg == s)
        n = m.sum()
        out[s] = 100.0 * (scar & m).sum() / n if n else np.nan
    return out


def run(sid, data, outdir):
    path = os.path.join(outdir, f"{sid}.json")
    if os.path.exists(path):
        return sid, "cached"
    try:
        rng = np.random.default_rng(int(sid[1:]))
        sub = G.load_subject(os.path.join(data, sid))
        if sub is None:
            json.dump(dict(sid=sid, ok=False, why="no LV"), open(path, "w")); return sid, "no LV"
        r = dict(sid=sid, qc=qc(sub))
        q = r["qc"]
        ok = (q["hu_lv"] > 200) and (q["hu_lv"] - q["hu_myo"] > 100) and (q["enclosed"] > 0.85) and not q["touches_edge"]
        r["ok"] = bool(ok)
        if not ok:
            json.dump(r, open(path, "w")); return sid, "qc fail"

        # ---- E4 on the native grid
        nat_myo = G.keep_largest(sub["myo"])
        td_n, th_n = G.depth_distance(nat_myo, sub["lv"], sub["spacing"])
        L_n = G.layers(td_n, nat_myo)
        ct = sub["ct"]
        hu = {k: float(ct[L_n == k].mean()) for k in (1, 2, 3)}
        sdh = {k: float(ct[L_n == k].std()) for k in (1, 2, 3)}
        med = {k: float(np.median(ct[L_n == k])) for k in (1, 2, 3)}
        # share of subendocardial voxels brighter than half-way between myocardium and blood pool
        blood_like = float((ct[L_n == 1] > 0.5 * (q["hu_lv"] + q["hu_myo"])).mean())
        r["E4"] = dict(hu_layer=hu, sd_layer=sdh, median_layer=med, blood_like_subendo=blood_like,
                       tpr=hu[1] / hu[3] if hu[3] else None,
                       tpr_median=med[1] / med[3] if med[3] else None,
                       n_vox_layer={k: int((L_n == k).sum()) for k in (1, 2, 3)})

        # ---- E1 at native and 0.5 mm
        mid_n = nat_myo & (td_n > 0.4) & (td_n < 0.6)
        g = G.resample_masks(sub, 0.5)
        g["myo"] = G.keep_largest(g["myo"])
        myo, lv, sp = g["myo"], g["lv"], g["spacing"]
        td, th = G.depth_distance(myo, lv, sp)
        mid = myo & (td > 0.4) & (td < 0.6)
        thk = th[mid]
        r["E1"] = dict(thick_mm_p10_50_90=[float(x) for x in np.percentile(thk, [10, 50, 90])],
                       thick_native_mm_p50=float(np.median(th_n[mid_n])),
                       vox_across_1p5=float(np.median(thk) / 1.5), vox_across_0p5=float(np.median(thk) / 0.5),
                       frac_mid_thinner_than_4p5mm=float((thk < 4.5).mean()))

        # ---- frame and AHA
        fr = G.lv_frame(g)
        if fr is None:
            r["ok"] = False; r["why"] = "frame"
            json.dump(r, open(path, "w")); return sid, "frame"
        seg = G.aha17(g, fr)
        r["E3"] = dict(septal_arc_deg=float(fr["septal_arc_deg"]),
                       seg_ml={int(s): float((seg == s).sum() * 0.125 / 1000) for s in range(0, 18)})
        # thickness by segment (mid-wall)
        r["E1"]["thick_by_seg_mm"] = {int(s): float(np.median(th[mid & (seg == s)])) if (mid & (seg == s)).any() else None
                                      for s in range(1, 18)}
        inmyo = myo & (seg > 0)
        terr = np.zeros(seg.shape, np.uint8)
        for s, t in G.AHA_TERRITORY.items():
            terr[seg == s] = {"LAD": 1, "RCA": 2, "LCx": 3}[t]
        pert = {}
        def changed(seg2):
            t2 = np.zeros(seg2.shape, np.uint8)
            for s, t in G.AHA_TERRITORY.items():
                t2[seg2 == s] = {"LAD": 1, "RCA": 2, "LCx": 3}[t]
            return float((seg2[inmyo] != seg[inmyo]).mean()), float((t2[inmyo] != terr[inmyo]).mean())
        for deg in (5, 10):
            vals = []
            for _ in range(4):
                v = rng.standard_normal(3); v -= (v @ fr["axis"]) * fr["axis"]
                vals.append(changed(G.aha17(g, fr, axis_tilt=G.rotation(v, deg))))
            pert[f"tilt{deg}"] = np.mean(vals, 0).tolist()
        pert["ref10"] = np.mean([changed(G.aha17(g, fr, ref_shift_deg=d)) for d in (-10, 10)], 0).tolist()
        pert["ref20"] = np.mean([changed(G.aha17(g, fr, ref_shift_deg=d)) for d in (-20, 20)], 0).tolist()
        pert["base5"] = np.mean([changed(G.aha17(g, fr, base_shift_mm=d)) for d in (-5, 5)], 0).tolist()
        # septal arc as measured vs the fixed 120 degrees of the 60-degree sectors
        r["E3"]["frame_change_seg_terr"] = pert

        # ---- E2 layers
        tl = G.depth_laplace(myo, lv)
        Ld, Ll = G.layers(td, myo), G.layers(tl, myo)
        r["E2"] = dict(agree_dist_laplace=float((Ld[myo] == Ll[myo]).mean()),
                       median_abs_t_diff=float(np.median(np.abs(td[myo] - tl[myo]))))
        # synthetic subendocardial scar in the LAD segments at 25/50/75 % of depth
        lad = np.isin(seg, LAD_SEGS)
        scars = {x: myo & lad & (td < x / 100.0) for x in range(10, 100, 10)}
        ref_tm = {x: transmurality(scars[x], myo, seg, LAD_SEGS) for x in scars}
        runs = []
        for sig in SIGMAS:
            for rep in range(1):
                runs.append(("rand", sig, rep, 0.0))
        runs.append(("bias_epi", 0.0, 0, 0.5))
        runs.append(("bias_endo_in", 0.0, 0, -0.5))
        e2 = []
        for kind, sig, rep, bias in runs:
            if kind == "bias_epi":
                m2, l2 = G.perturb_borders(myo, lv, sp, 0, CORR_MM, rng, bias_epi=bias)
            elif kind == "bias_endo_in":
                m2, l2 = G.perturb_borders(myo, lv, sp, 0, CORR_MM, rng, bias_endo=bias)
            else:
                m2, l2 = G.perturb_borders(myo, lv, sp, sig, CORR_MM, rng)
            td2, _ = G.depth_distance(m2, l2, sp)
            L2 = G.layers(td2, m2)
            seg2 = G.aha17(dict(g, myo=m2, lv=l2), fr)  # same frame, perturbed wall
            row = dict(kind=kind, sigma=sig, rep=rep, bias=bias, dice_myo=float(G.dice(m2, myo)),
                       dice_layer={k: float(G.dice(L2 == k, Ld == k)) for k in (1, 2, 3)})
            # scar read-back: the scar is fixed in the image; the borders moved; segments stay as the reference
            agree, abserr = [], []
            for x in scars:
                tm2 = transmurality(scars[x], m2, seg2, LAD_SEGS)
                for s in LAD_SEGS:
                    a, b = ref_tm[x][s], tm2[s]
                    if np.isnan(a) or np.isnan(b):
                        continue
                    agree.append(tbin(a) == tbin(b)); abserr.append(abs(a - b))
            row["scar_bin_agree"] = float(np.mean(agree)) if agree else None
            row["scar_abs_err_pct"] = float(np.median(abserr)) if abserr else None
            row["scar_abs_err_pct_p90"] = float(np.percentile(abserr, 90)) if abserr else None
            e2.append(row)
        r["E2"]["perturb"] = e2
        r["E2"]["ref_transmurality_bins"] = {x: [tbin(v) for v in ref_tm[x].values() if not np.isnan(v)] for x in ref_tm}
        json.dump(r, open(path, "w"), default=float)
        return sid, "ok"
    except Exception as e:  # keep going; the failure is recorded
        json.dump(dict(sid=sid, ok=False, why="error", err=traceback.format_exc()[-800:]), open(path, "w"))
        return sid, f"error {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("out"); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--done-log")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    subj = sorted(d for d in os.listdir(a.data) if d.startswith("s") and
                  os.path.exists(os.path.join(a.data, d, "segmentations", "aorta.nii.gz")))
    excl = pool_subjects()  # never read a pool (sealed, D35 or trainable) subject
    subj = [s for s in subj if s not in excl]
    if a.only:
        subj = [s for s in subj if s in a.only]
    if a.done_log:  # only subjects whose download has finished (the fetcher logs a subject after its last file)
        done = set(open(a.done_log).read().split())
        subj = [s for s in subj if s in done]
    with ProcessPoolExecutor(a.workers) as ex:
        for sid, st in ex.map(run, subj, [a.data] * len(subj), [a.out] * len(subj)):
            print(sid, st, flush=True)


if __name__ == "__main__":
    main()
