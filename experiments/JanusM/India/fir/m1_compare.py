"""Job M1 read-out (CPU): compare TotalSegmentator v1 labels (1.5 mm, CC BY 4.0) with heartchambers_highres
predictions on the same public subjects. Two independent sources of the LV borders: their disagreement is a
first estimate of how well the endocardial and epicardial borders, and the layers derived from them, are pinned
down on CT before any project read exists.

    python m1_compare.py TS_DIR HC_DIR OUT.json
Numbers only; no image is written.
"""
import json, os, sys
import numpy as np
import nibabel as nib
from scipy import ndimage as ndi
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import lvgeom as G  # noqa: E402
from fetch_ts_cardiac import pool_subjects  # noqa: E402


def surface_dist(a, b, sp):
    """Symmetric mean surface distance (mm) between masks a and b."""
    sa = a & ~ndi.binary_erosion(a, G.STRUCT)
    sb = b & ~ndi.binary_erosion(b, G.STRUCT)
    da = ndi.distance_transform_edt(~sb, sampling=sp)[sa]
    db = ndi.distance_transform_edt(~sa, sampling=sp)[sb]
    return float((da.sum() + db.sum()) / max(len(da) + len(db), 1))


def resample_to(src_img, ref_img):
    """Nearest-neighbour resample of src (a mask) onto ref's grid via world coordinates."""
    ref = ref_img
    idx = np.indices(ref.shape).reshape(3, -1).T
    w = idx @ ref.affine[:3, :3].T + ref.affine[:3, 3]
    inv = np.linalg.inv(src_img.affine)
    ijk = w @ inv[:3, :3].T + inv[:3, 3]
    out = ndi.map_coordinates(np.asanyarray(src_img.dataobj).astype(np.float32), ijk.T, order=0)
    return out.reshape(ref.shape) > 0


def main(ts, hc, out):
    excl = pool_subjects()
    res = []
    for s in sorted(os.listdir(hc)):
        if s in excl or not os.path.exists(f"{hc}/{s}/heart_myocardium.nii.gz"):
            continue
        sub = G.load_subject(f"{ts}/{s}")
        if sub is None:
            continue
        ref = nib.load(f"{ts}/{s}/segmentations/heart_myocardium.nii.gz")
        hm = resample_to(nib.load(f"{hc}/{s}/heart_myocardium.nii.gz"), ref)
        hl = resample_to(nib.load(f"{hc}/{s}/heart_ventricle_left.nii.gz"), ref)
        tm = np.asanyarray(ref.dataobj) > 0
        tl = np.asanyarray(nib.load(f"{ts}/{s}/segmentations/heart_ventricle_left.nii.gz").dataobj) > 0
        sp = np.array(ref.header.get_zooms()[:3], float)
        r = dict(sid=s, dice_myo=G.dice(hm, tm), dice_lv=G.dice(hl, tl),
                 assd_endo=surface_dist(hl, tl, sp), assd_epi=surface_dist(hm | hl, tm | tl, sp))
        td1, _ = G.depth_distance(tm, tl, sp)
        td2, _ = G.depth_distance(hm, hl, sp)
        L1, L2 = G.layers(td1, tm), G.layers(td2, hm)
        r["dice_layer"] = {k: G.dice(L1 == k, L2 == k) for k in (1, 2, 3)}
        res.append(r)
        print(s, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    json.dump(res, open(out, "w"), indent=1, default=float)


if __name__ == "__main__":
    main(*sys.argv[1:4])
