"""Hotel R2, Job JM-0 add-on (CPU, Fir login node or a CPU job): half-maximum border offsets, edge width, rest TPR
with a guard band, and the core-myocardium HU histogram, on the 40 JM-0 ImageCAS-X training cases at native
resolution. Round 1 ruling §6 items 1 (half-maximum offsets) and 6 (rest TPR, fat cut-off).

Inputs are exactly Job JM-0's (Juliet v1 §7): $SCRATCH/janusm/m0_cases.txt, $SCRATCH/janusm/hc/<case>.nii.gz
(heartchambers_highres, --ml) and $SCRATCH/icx4/layout.json for the CT paths. Before any image is opened, every
case goes through Hotel's guard (experiments/JanusM/Hotel/guard_r2.py): anything outside the ImageCAS-X train list,
or in A14, the ImageCAS-X test split or val 80, stops the run.

Conventions (mm, from the label's border, half-voxel corrected):
  endocardium  negative in the LV cavity, positive in the myocardium. The half-maximum crossing between the blood
               and core-myocardium plateaus at +x means the label's endocardium sits x mm into the blood.
  epicardium   positive in the myocardium, negative outside (free wall only: RV, LA and aorta excluded). A crossing
               at +x means the label's epicardium sits x mm out in the fat (TotalSegmentator v1: +0.86).
  TPR          per AHA segment (Juliet's real_labels.geometry), mean HU of the inner third / outer third, equal-
               thickness depth, with guard bands of 0 and 1 mm from each border; septal segments reported apart.

Writes OUT (per-case detail; keep it on Fir) and prints the aggregate JSON, which is all that is sent back.

    python experiments/JanusM/Hotel/r2/fir/halfmax_tpr_m0.py --cases $SCRATCH/janusm/m0_cases.txt \
        --hc $SCRATCH/janusm/hc --layout $SCRATCH/icx4/layout.json --out $SCRATCH/janusm/hotel_r2_m0.json
"""
import argparse
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(HERE.parent.parent))  # experiments/JanusM/Hotel
sys.path.insert(0, str(REPO / "experiments/JanusM/Juliet"))
from guard_r2 import Guard  # noqa: E402
from real_labels import geometry  # noqa: E402

HC_FALLBACK = {1: "heart_myocardium", 2: "heart_atrium_left", 3: "heart_ventricle_left", 4: "heart_atrium_right",
               5: "heart_ventricle_right", 6: "aorta", 7: "pulmonary_artery"}
SEPTAL = {2, 3, 8, 9, 14}
BINS = np.arange(-4.0, 6.01, 0.25)
HIST = np.arange(-200, 301, 10)


def hc_ids():
    try:
        from totalsegmentator.map_to_binary import class_map
        return {v: k for k, v in class_map["heartchambers_highres"].items()}
    except Exception:  # noqa: BLE001
        return {v: k for k, v in HC_FALLBACK.items()}


def crossing(prof, lo, hi, frac):
    half = lo + frac * (hi - lo)
    c = BINS[:-1] + (BINS[1] - BINS[0]) / 2
    v = np.array([np.nan if x is None else x for x in prof])
    ok = ~np.isnan(v)
    c, v = c[ok], v[ok]
    for i in range(len(v) - 1):
        if (v[i] - half) * (v[i + 1] - half) <= 0 and v[i] != v[i + 1]:
            return float(c[i] + (half - v[i]) * (c[i + 1] - c[i]) / (v[i + 1] - v[i]))
    return None


def profile(a, sd):
    out = []
    for lo, hi in zip(BINS[:-1], BINS[1:]):
        m = (sd >= lo) & (sd < hi)
        out.append(float(np.median(a[m])) if m.sum() > 50 else None)
    return out


def one(c, ct_path, hc_path, ids):
    ci = nib.as_closest_canonical(nib.load(ct_path))
    hi = nib.as_closest_canonical(nib.load(hc_path))
    if ci.shape != hi.shape or not np.allclose(ci.affine, hi.affine, atol=1e-3):
        return {"id": c, "usable": False, "reason": "grid mismatch"}
    hc = np.asarray(hi.dataobj).astype(np.int16)
    m = {k: hc == ids[k] for k in ("heart_myocardium", "heart_ventricle_left", "heart_ventricle_right",
                                    "heart_atrium_left", "aorta")}
    sp = np.asarray(hi.header.get_zooms()[:3], float)
    summ, det = geometry(c, m["heart_myocardium"], m["heart_ventricle_left"], m["heart_ventricle_right"],
                         m["heart_atrium_left"], m["aorta"], sp)
    if det is None:
        return {"id": c, "usable": False, "reason": summ.get("reason")}
    box = det["box"]
    a = np.asarray(ci.dataobj, dtype=np.float32)[box]
    myo, lv, rv, la, ao = (m[k][box] for k in ("heart_myocardium", "heart_ventricle_left", "heart_ventricle_right",
                                                "heart_atrium_left", "aorta"))
    half = sp.mean() / 2
    solid = myo | lv
    d_lv_in = ndi.distance_transform_edt(lv, sampling=sp) - half
    d_to_lv = ndi.distance_transform_edt(~lv, sampling=sp) - half
    d_epi_in = ndi.distance_transform_edt(solid, sampling=sp) - half
    d_epi_out = ndi.distance_transform_edt(~solid, sampling=sp) - half
    other = ndi.binary_dilation(rv | la | ao, iterations=int(np.ceil(2.0 / sp.min())))
    sd_endo = np.where(lv, -d_lv_in, np.where(myo, d_to_lv, np.nan))
    sd_epi = np.where(myo & ~other, d_epi_in, np.where(~solid & ~other & (d_epi_out < 6), -d_epi_out, np.nan))
    core = myo & (d_to_lv >= 3) & (d_epi_in >= 3)
    myo_core = float(np.median(a[core])) if core.sum() > 50 else None
    blood = float(np.median(a[d_lv_in >= 3])) if (d_lv_in >= 3).sum() > 50 else None
    fat = a[~solid & ~other & (d_epi_out > 1.5) & (d_epi_out < 4.5)]
    fat = fat[(fat > -250) & (fat < -30)]
    fat = float(np.median(fat)) if fat.size > 50 else None
    r = {"id": c, "usable": True, "spacing_mm": [round(float(x), 3) for x in sp],
         "median_thick_mm": summ["median_thick_mm"], "plateaus_blood_myocore_fat": [blood, myo_core, fat]}
    pe, pp = profile(a, sd_endo), profile(a, sd_epi)
    if blood is not None and myo_core is not None:
        r["endo_halfmax_mm"] = crossing(pe, blood, myo_core, 0.5)
        c10, c90 = crossing(pe, blood, myo_core, 0.1), crossing(pe, blood, myo_core, 0.9)
        r["endo_10_90_mm"] = None if c10 is None or c90 is None else abs(c90 - c10)
    if fat is not None and myo_core is not None:
        r["epi_halfmax_mm"] = crossing(pp, fat, myo_core, 0.5)
        c10, c90 = crossing(pp, fat, myo_core, 0.1), crossing(pp, fat, myo_core, 0.9)
        r["epi_10_90_mm"] = None if c10 is None or c90 is None else abs(c90 - c10)
    # TPR per segment, equal-thickness depth, guard 0 and 1 mm
    vox = tuple(det["myo_vox"].T)
    di, do = d_to_lv[vox], d_epi_in[vox]
    u = di / np.maximum(di + do, 1e-6)
    hu = a[vox]
    seg, keep = det["seg"], det["keep"]
    tpr = {}
    for g in (0.0, 1.0):
        per = {}
        for k in range(1, 17):
            s = keep & (seg == k)
            inner = s & (u < 1 / 3) & (di >= g)
            outer = s & (u >= 2 / 3) & (do >= g)
            if inner.sum() >= 30 and outer.sum() >= 30:
                per[k] = round(float(hu[inner].mean() / hu[outer].mean()), 3)
        tpr[str(g)] = per
    r["tpr"] = tpr
    # core HU histogram (>= 1 mm from either border) for the data-driven fat cut-off
    core1 = myo & (d_to_lv >= 1) & (d_epi_in >= 1)
    r["core1_hist"] = np.histogram(a[core1], bins=HIST)[0].tolist()
    r["core1_frac_fat_window"] = round(float(((a[core1] >= -180) & (a[core1] <= 0)).mean()), 4)
    return r


def q(x):
    x = [v for v in x if v is not None]
    return None if not x else [round(float(np.percentile(x, p)), 3) for p in (25, 50, 75)] + [len(x)]


def main():
    ap = argparse.ArgumentParser()
    for k in ("cases", "hc", "layout", "out"):
        ap.add_argument("--" + k, required=True)
    a = ap.parse_args()
    cases = Path(a.cases).read_text().split()
    Guard().check_all("imagecas", cases)  # stops the run on any held-out case, before an image is opened
    print(f"guard: {len(cases)} cases, 0 refused", flush=True)
    layout = json.load(open(a.layout))["cases"]
    ids = hc_ids()
    rows = []
    for c in cases:
        try:
            rows.append(one(c, layout[c]["ct"], str(Path(a.hc) / f"{c}.nii.gz"), ids))
        except Exception as e:  # noqa: BLE001
            rows.append({"id": c, "usable": False, "reason": repr(e)[:200]})
        r = rows[-1]
        print(c, r.get("usable"), r.get("endo_halfmax_mm"), r.get("epi_halfmax_mm"), r.get("endo_10_90_mm"), flush=True)
    ok = [r for r in rows if r.get("usable")]
    agg = {"n_cases": len(rows), "n_usable": len(ok),
           "spacing_inplane_mm_q": q([r["spacing_mm"][0] for r in ok]),
           "spacing_z_mm_q": q([r["spacing_mm"][2] for r in ok]),
           "endo_halfmax_offset_mm_q25_50_75_n": q([r.get("endo_halfmax_mm") for r in ok]),
           "epi_halfmax_offset_mm_q25_50_75_n": q([r.get("epi_halfmax_mm") for r in ok]),
           "endo_10_90_mm_q": q([r.get("endo_10_90_mm") for r in ok]),
           "epi_10_90_mm_q": q([r.get("epi_10_90_mm") for r in ok]),
           "plateau_blood_q": q([r["plateaus_blood_myocore_fat"][0] for r in ok]),
           "plateau_myocore_q": q([r["plateaus_blood_myocore_fat"][1] for r in ok]),
           "plateau_fat_q": q([r["plateaus_blood_myocore_fat"][2] for r in ok]),
           "core1_frac_fat_window_q": q([r.get("core1_frac_fat_window") for r in ok]),
           "core1_hist_bins_HU": HIST.tolist(),
           "core1_hist_sum": np.sum([r["core1_hist"] for r in ok], axis=0).tolist() if ok else None}
    for g in ("0.0", "1.0"):
        free = [v for r in ok for k, v in r["tpr"][g].items() if int(k) not in SEPTAL]
        sept = [v for r in ok for k, v in r["tpr"][g].items() if int(k) in SEPTAL]
        pat = [np.median([v for k, v in r["tpr"][g].items() if int(k) not in SEPTAL]) for r in ok
               if any(int(k) not in SEPTAL for k in r["tpr"][g])]
        agg[f"tpr_guard{g}"] = {"free_wall_segments_q": q(free), "septal_segments_q": q(sept),
                                "patient_median_free_q": q(pat),
                                "share_free_segments_lt_0p99": round(float(np.mean(np.array(free) < 0.99)), 3)
                                if free else None}
    json.dump({"aggregate": agg, "cases": rows}, open(a.out, "w"), indent=1)
    print(json.dumps(agg, indent=1))


if __name__ == "__main__":
    main()
