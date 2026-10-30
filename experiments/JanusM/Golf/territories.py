"""Golf Job M2 (Fir, CPU): patient-specific coronary territories from Janus 0, against the AHA standard mapping.

For each allowed ImageCAS case:
  1. LV myocardium, LV blood pool, RV blood pool and left atrium from TotalSegmentator `heartchambers_highres`
     (Job M1 output, one multilabel file per case; class ids read from TotalSegmentator's own class map);
  2. AHA 17 segments derived from them (layers_ts.aha / aha_labels, the code E2 ran);
  3. Janus 0's four-class prediction (1 LM, 2 LAD, 3 LCx, 4 RCA; configs/labels/coronary_icx4.yaml): every myocardial
     voxel takes the class of the nearest LAD/LCx/RCA voxel (Euclidean Voronoi, as Stalikas 2025; LM is not a seed);
  4. per segment, the majority territory, compared with the standard mapping commonly quoted from Cerqueira 2002:
     LAD 1 2 7 8 13 14 17, RCA 3 4 9 10 15, LCx 5 6 11 12 16 (primary figure not read by Golf: publisher 403).
Outputs per case and a summary: territory share of LV myocardial mass (LAD/LCx/RCA), segments reassigned, patients
with >= 1 reassigned segment.  Published comparators: Javadi 2010 (PET/CT) 72 % of patients, 9.3 % of segments;
Stalikas 2025 (CCTA Voronoi) LAD 42.5 %, LCx 28.8 %, RCA 26.4 % of LV mass.

Seal rules: refuses any coronary-sealed case (trillium/icx4/lib/sealed.py) and any Janus-M seal or decision case
(janusm_seal_proposal.json); runs only on the Janus-M trainable cases.

Usage (Fir login node or a CPU job; ~20-40 s per case):
  python territories.py --chambers DIR --pred DIR --sealed trillium/icx4/sealed_test.json --out OUT.json [--np 8]
  python territories.py --selftest <dir with TotalSegmentator ct + cardiac_label cases>   (synthetic arteries; CI-free check)
"""
import argparse, json, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import layers_ts as L  # noqa: E402

STANDARD = {**{s: 2 for s in (1, 2, 7, 8, 13, 14, 17)}, **{s: 4 for s in (3, 4, 9, 10, 15)},
            **{s: 3 for s in (5, 6, 11, 12, 16)}}
NAME = {2: "LAD", 3: "LCx", 4: "RCA"}
# AHA angle origin: the RV-insertion end pointing more anterior-superior (RAS +y +z), rule B of aha_check.py
# (orientation checks passed 19/23 E2 cases against 17/23 for anterior-only).
ANT_SUP = np.array([0.0, 1.0, 1.0]) / np.sqrt(2)


def chamber_ids():
    """TotalSegmentator's own id for each heartchambers_highres class (never a hard-coded guess)."""
    from totalsegmentator.map_to_binary import class_map
    inv = {v: k for k, v in class_map["heartchambers_highres"].items()}
    need = ["heart_myocardium", "heart_ventricle_left", "heart_ventricle_right", "heart_atrium_left"]
    missing = [n for n in need if n not in inv]
    if missing:
        raise SystemExit(f"heartchambers_highres class map lacks {missing}: {sorted(inv)}")
    return {n: inv[n] for n in need}


def territories(myo, cav, rv, la, art, sp, aff):
    """Return (aha labels, territory labels on myo, per-case dict)."""
    geom, diag = L.aha(myo, cav, rv, la, sp)
    if geom is None:
        return None, None, {"fail": diag.get("fail")}
    R = aff[:3, :3] / np.linalg.norm(aff[:3, :3], axis=0)
    seg = L.aha_labels(myo, geom, R.T @ ANT_SUP)
    seeds = np.isin(art, (2, 3, 4))
    if not seeds.any():
        return seg, None, {"fail": "no LAD/LCx/RCA voxel"}
    _, idx = ndi.distance_transform_edt(~seeds, sampling=sp, return_indices=True)
    nearest = art[tuple(idx)]
    terr = np.where(myo, nearest, 0).astype(np.uint8)
    out = {"septal_arc_deg": diag["septal_arc_deg"]}
    tot = myo.sum()
    out["mass_share"] = {NAME[k]: float((terr == k).sum() / tot) for k in (2, 3, 4)}
    per = {}
    for s in range(1, 18):
        m = seg == s
        if m.sum() == 0:
            continue
        vals, cnt = np.unique(terr[m], return_counts=True)
        maj = int(vals[np.argmax(cnt)])
        per[s] = {"territory": NAME.get(maj, str(maj)), "standard": NAME[STANDARD[s]],
                  "majority_share": float(cnt.max() / m.sum())}
    out["segments"] = per
    out["reassigned"] = [s for s, v in per.items() if v["territory"] != v["standard"]]
    return seg, terr, out


def one_case(args):
    case, chambers, pred, ids = args
    try:
        ch = nib.load(chambers)
        lab = np.asanyarray(ch.dataobj).astype(np.int16)
        pr = nib.load(pred)
        art = np.asanyarray(pr.dataobj).astype(np.int16)
        if lab.shape != art.shape or not np.allclose(ch.affine, pr.affine, atol=1e-2):
            return case, {"fail": f"grids differ: {lab.shape} vs {art.shape}"}
        sp = np.array(ch.header.get_zooms()[:3], float)
        myo, cav = lab == ids["heart_myocardium"], lab == ids["heart_ventricle_left"]
        rv, la = lab == ids["heart_ventricle_right"], lab == ids["heart_atrium_left"]
        box = L.crop(myo, cav, rv, la, art, mask=myo | cav, margin=int(np.ceil(25 / sp.min())))
        _, _, out = territories(*box[:4], box[4], sp, ch.affine)
        return case, out
    except Exception as e:  # reported, never hidden
        return case, {"fail": repr(e)}


def allowed_cases(sealed_json):
    sys.path.insert(0, str(ROOT / "trillium/icx4/lib"))
    import sealed as S
    seal = S.load(sealed_json)
    jm = json.loads((HERE / "janusm_seal_proposal.json").read_text())
    blocked = set(jm["janusm_sealed"]) | set(jm["janusm_decision"])
    cases = [c for c in (f"c{i:04d}" for i in range(1000))
             if c not in blocked and c not in S.sealed_set(seal)]   # drop the 100 coronary-sealed cases (A14)
    S.refuse_sealed(cases, seal, "janusm territories")              # and let the A14 guard confirm it
    return cases


def summarise(res):
    ok = {c: r for c, r in res.items() if "fail" not in r}
    n_seg = sum(len(r["segments"]) for r in ok.values())
    n_re = sum(len(r["reassigned"]) for r in ok.values())
    share = {k: float(np.median([r["mass_share"][k] for r in ok.values()])) for k in ("LAD", "LCx", "RCA")} if ok else {}
    by_seg = {s: float(np.mean([s in r["reassigned"] for r in ok.values()])) for s in range(1, 18)} if ok else {}
    return {"n_cases": len(res), "n_ok": len(ok), "fails": {c: r["fail"] for c, r in res.items() if "fail" in r},
            "segments_reassigned_pct": 100 * n_re / max(n_seg, 1),
            "patients_with_any_reassigned_pct": 100 * float(np.mean([len(r["reassigned"]) > 0 for r in ok.values()])) if ok else None,
            "median_mass_share": share, "reassigned_rate_by_segment": by_seg,
            "comparators": {"Javadi2010_patients_pct": 72, "Javadi2010_segments_pct": 9.3,
                            "Stalikas2025_share": {"LAD": 0.425, "LCx": 0.288, "RCA": 0.264}}}


def selftest(ts_dir):
    """Synthetic arteries placed on the epicardium of the standard territories must give ~0 reassignment."""
    res = {}
    for case in sorted(os.listdir(ts_dir))[:4]:
        ct, Lb, sp, aff = L.load(Path(ts_dir) / case)
        la, myo, cav, rv = Lb[L.LA], Lb[L.MYO], Lb[L.LV], Lb[L.RV]
        la, myo, cav, rv = L.crop(la, myo, cav, rv, mask=myo | cav, margin=12)
        R = aff[:3, :3] / np.linalg.norm(aff[:3, :3], axis=0)
        geom, _ = L.aha(myo, cav, rv, la, sp)
        seg = L.aha_labels(myo, geom, R.T @ ANT_SUP)
        # artery = a 1-voxel shell just outside the epicardium, labelled by the standard territory of the nearest segment
        shell = ndi.binary_dilation(myo | cav, iterations=2) & ~ndi.binary_dilation(myo | cav, iterations=1)
        _, idx = ndi.distance_transform_edt(seg == 0, return_indices=True)
        near = seg[tuple(idx)]
        art = np.zeros(myo.shape, np.int16)
        for s, t in STANDARD.items():
            art[shell & (near == s)] = t
        _, _, out = territories(myo, cav, rv, la, art, sp, aff)
        res[case] = out
        print(case, "reassigned:", out.get("reassigned"), {k: round(v, 3) for k, v in out.get("mass_share", {}).items()})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chambers"); ap.add_argument("--pred"); ap.add_argument("--sealed")
    ap.add_argument("--out"); ap.add_argument("--np", type=int, default=8); ap.add_argument("--selftest")
    a = ap.parse_args()
    if a.selftest:
        selftest(a.selftest)
        return
    ids = chamber_ids()
    jobs = []
    for c in allowed_cases(a.sealed):
        ch, pr = Path(a.chambers) / f"{c}.nii.gz", Path(a.pred) / f"{c}.nii.gz"
        if ch.exists() and pr.exists():
            jobs.append((c, str(ch), str(pr), ids))
    print(f"[territories] {len(jobs)} cases with both chambers and Janus 0 prediction", flush=True)
    res = {}
    with ProcessPoolExecutor(a.np) as ex:
        for c, r in ex.map(one_case, jobs):
            res[c] = r
    summ = summarise(res)
    Path(a.out).write_text(json.dumps({"summary": summ, "cases": res}, indent=1))
    print(json.dumps({k: summ[k] for k in ("n_cases", "n_ok", "segments_reassigned_pct",
                                           "patients_with_any_reassigned_pct", "median_mass_share")}, indent=1))


if __name__ == "__main__":
    main()
