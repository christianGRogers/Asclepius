"""Self-test of lima_geom.analyse on the public TotalSegmentator v1 cardiac cases that Lima's guard allows.

The labels are model-made at 1.5 mm, so absolute numbers (thickness, half-maximum offsets) describe those labels,
not CCTA truth; they are the 1.5 mm baseline that Job JM-0b repeats on native ImageCAS. Territories are checked
with **synthetic** coronaries (a ring just outside the epicardium, coloured by the AHA default of the nearest
segment), so they test the wiring, not anatomy.

    python local_check.py TS_DIR OUT_JSONL [--jobs 2]
"""
import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from heldout import check  # noqa: E402
import lima_geom as G  # noqa: E402

KEYS = {"myo": "heart_myocardium", "lv": "heart_ventricle_left", "rv": "heart_ventricle_right",
        "la": "heart_atrium_left", "ao": "aorta"}
CODE = {"LAD": 2, "LCx": 3, "RCA": 4}


def synthetic_coronaries(m, sp, aff):
    fr, why = G.frame(m, aff)
    if fr is None:
        return None
    seg = G.segments(fr, "fixed")
    pts = np.argwhere(m["myo"])
    sol = m["myo"] | m["lv"]
    ring = ~sol & (ndi.distance_transform_edt(~sol, sampling=sp) <= 2.0) & ~m["rv"] & ~m["la"]
    rp = np.argwhere(ring)
    _, nn = cKDTree(pts * sp).query(rp * sp)
    cor = np.zeros(m["myo"].shape, np.uint8)
    cor[tuple(rp.T)] = [CODE[G.AHA_DEFAULT[int(s)]] for s in seg[nn]]
    return cor


def run(case_dir):
    sid = os.path.basename(case_dir)
    check(sid)  # before any file is opened
    t0 = time.time()
    d = os.path.join(case_dir, "segmentations")
    ref = nib.as_closest_canonical(nib.load(os.path.join(d, "heart_myocardium.nii.gz")))
    sp0 = np.array(ref.header.get_zooms()[:3], float)
    masks = {k: np.asanyarray(nib.as_closest_canonical(nib.load(os.path.join(d, f"{v}.nii.gz"))).dataobj) > 0
             for k, v in KEYS.items()}
    if masks["myo"].sum() * sp0.prod() < 50e3 or masks["lv"].sum() * sp0.prod() < 20e3:
        return {"case": sid, "skip": "LV myocardium or cavity missing or partial"}
    ct = np.asanyarray(nib.as_closest_canonical(nib.load(os.path.join(case_dir, "ct.nii.gz"))).dataobj)
    m, sp, aff = G.to_grid(masks, ct, None, sp0, ref.affine, grid=0.5)
    cor = synthetic_coronaries(m, sp, aff)
    out = {"case": sid, "spacing_native": sp0.tolist()}
    out.update(G.analyse(m, sp, aff, cor=cor, rng=np.random.default_rng(int(sid[1:]))))
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ts_dir"); ap.add_argument("out"); ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    base = os.path.join(a.ts_dir, "Totalsegmentator_dataset")
    subj = sorted(s for s in os.listdir(base) if s.startswith("s") and (not a.only or s in a.only))
    for s in subj:
        check(s)
    done = {json.loads(x)["case"] for x in open(a.out)} if os.path.exists(a.out) else set()
    todo = [os.path.join(base, s) for s in subj if s not in done]
    with Pool(a.jobs) as p, open(a.out, "a") as fh:
        for r in p.imap_unordered(run, todo):
            fh.write(json.dumps(r, default=float) + "\n")
            fh.flush()
            print(r["case"], r.get("skip", r.get("frame")), r.get("seconds"), flush=True)


if __name__ == "__main__":
    main()
