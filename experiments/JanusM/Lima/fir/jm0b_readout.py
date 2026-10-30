"""Job JM-0b (Lima, Janus-M R2 path jm/rest-ccta): CPU read-out on Job JM-0's 40 cases. No GPU, no new model run.

Job JM-0 (Juliet v1 section 7, JA10) leaves `heartchambers_highres` masks for 40 ImageCAS-X *training* cases in
$SCRATCH/janusm/hc. This script reads those masks, the same cases' CT, and their ImageCAS-X coronary labels
(collapsed to D25's four classes), and computes on a 0.5 mm isotropic crop (lima_geom.analyse):

  item 1  thickness, voxels per third, segments needing halves, AHA failures, half-maximum border offsets;
  item 3  equal-thickness vs Laplace vs Yezzi-Prince thirds; fixed vs arc-proportional septal sectors;
          Euclidean vs geodesic territories, and each one's discordance with the AHA default;
  item 6  rest TPR per segment with and without the 1 mm guard band; core HU and fat clusters at four cut-offs;
  Lima E3 each segment's thickness and guarded subendocardial HU relative to the patient's own median.

**Guard (before any file is opened):** every case must be in splits.json 'train', outside the A14 sealed 100 and the
ImageCAS-X test split (trillium/icx4/sealed_test.json), and outside the Janus-M seal 60 and decision 40 (recomputed
here from the JA6 salts). Any hit refuses the whole run.

    python jm0b_readout.py --cases $SCRATCH/janusm/m0_cases.txt --hc $SCRATCH/janusm/hc \
        --layout $SCRATCH/icx4/layout.json --icx $SCRATCH/icx4/icx --splits $SCRATCH/icx4/splits.json \
        --out $SCRATCH/janusm/jm0b --np 8

Writes OUT/summary.json (aggregates only: this is what goes back on #142) and OUT/cases.jsonl (per-case numbers;
stays on Fir).
"""
import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import nibabel as nib
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(REPO / "trillium/icx4/lib"))
import lima_geom as G  # noqa: E402
from summarise import summarise  # noqa: E402

JA6 = [("asclepius-janusm-seal-r1:", 60), ("asclepius-janusm-decision-r1:", 40)]
HC_FALLBACK = {1: "heart_myocardium", 2: "heart_atrium_left", 3: "heart_ventricle_left", 4: "heart_atrium_right",
               5: "heart_ventricle_right", 6: "aorta", 7: "pulmonary_artery"}
SPLITS_SHA_PREFIX = "a53bd426cddc"  # JA6: the committed trillium-results/icx14/results/splits.json


def refused(splits_path):
    raw = open(splits_path, "rb").read()
    if not hashlib.sha256(raw).hexdigest().startswith(SPLITS_SHA_PREFIX):
        committed = json.load(open(REPO / "trillium-results/icx14/results/splits.json"))["train"]
        if sorted(json.loads(raw)["train"]) != sorted(committed):
            sys.exit("REFUSED: splits.json train list differs from the committed one (JA6); stop and send this line")
    train = json.loads(raw)["train"]
    import sealed  # the project's own validated loader
    S = sealed.load(str(REPO / "trillium/icx4/sealed_test.json"))
    bad = sealed.sealed_set(S) | set(S["open_icx_test"]) | set(S["excluded_dev_cases_in_test"])
    left = sorted(train)
    janusm = set()
    for salt, n in JA6:  # the Janus-M seal and decision set: never opened before the freeze and the reads
        pick = sorted(left, key=lambda c: hashlib.sha256((salt + c).encode()).hexdigest())[:n]
        janusm |= set(pick)
        left = [c for c in left if c not in pick]
    return set(train), bad, janusm


def hc_map():
    try:
        from totalsegmentator.map_to_binary import class_map
        return {v: k for k, v in class_map["heartchambers_highres"].items()}
    except Exception:  # noqa: BLE001
        return {v: k for k, v in HC_FALLBACK.items()}


def one(args):
    c, hc_dir, ct_path, icx_dir, ids = args
    t0 = time.time()
    hi = nib.as_closest_canonical(nib.load(str(Path(hc_dir) / f"{c}.nii.gz")))
    ci = nib.as_closest_canonical(nib.load(ct_path))
    li = nib.as_closest_canonical(nib.load(str(Path(icx_dir) / f"{int(c[1:]) + 1}.coronary.nii.gz")))
    for other in (ci, li):
        if other.shape != hi.shape or not np.allclose(other.affine, hi.affine, atol=1e-3):
            return {"frame": "grid mismatch"}
    from territory import to_four
    hc = np.asarray(hi.dataobj).astype(np.int16)
    sp0 = np.asarray(hi.header.get_zooms()[:3], float)
    masks = {"myo": hc == ids["heart_myocardium"], "lv": hc == ids["heart_ventricle_left"],
             "rv": hc == ids["heart_ventricle_right"], "la": hc == ids["heart_atrium_left"],
             "ao": hc == ids["aorta"],
             "other": np.isin(hc, [ids[k] for k in ("heart_atrium_right", "pulmonary_artery") if k in ids])}
    cor = to_four(np.asarray(li.dataobj).astype(np.int64), sp0)
    m, sp, aff = G.to_grid(masks, np.asarray(ci.dataobj), cor, sp0, hi.affine, grid=0.5)
    cor = m.pop("cor")
    r = G.analyse(m, sp, aff, cor=cor, rng=np.random.default_rng(int(c[1:])))
    r["native_spacing"] = sp0.tolist()
    r["seconds"] = round(time.time() - t0, 1)
    return r


def main():
    ap = argparse.ArgumentParser()
    for k in ("cases", "hc", "layout", "icx", "splits", "out"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--np", type=int, default=8)
    a = ap.parse_args()
    cases = Path(a.cases).read_text().split()
    train, bad, janusm = refused(a.splits)
    hits = sorted((set(cases) - train) | (set(cases) & bad) | (set(cases) & janusm))
    if hits:
        sys.exit(f"REFUSED: {len(hits)} of the cases are not JM-0-allowed (not train, sealed, test, or the Janus-M "
                 f"seal/decision draw). Nothing was opened. Send this line back.")
    print(f"guard: {len(cases)} cases, all ImageCAS-X train, 0 sealed, 0 test, 0 Janus-M seal/decision", flush=True)
    ids = hc_map()
    ct = json.load(open(a.layout))["cases"]
    os.makedirs(a.out, exist_ok=True)
    jobs = [(c, a.hc, ct[c]["ct"], a.icx, ids) for c in cases]
    rows = []
    with Pool(a.np) as p, open(Path(a.out) / "cases.jsonl", "w") as fh:
        for c, r in zip(cases, p.imap(one, jobs)):
            fh.write(json.dumps({"id": c, **r}, default=float) + "\n")
            rows.append(r)
            print(c, r.get("frame"), r.get("seconds"), flush=True)
    s = summarise(rows)
    json.dump(s, open(Path(a.out) / "summary.json", "w"), indent=1)
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
