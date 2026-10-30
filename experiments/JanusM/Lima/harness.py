"""E2: one shared perturbation harness for Janus-M border error (Round 1 ruling, section 6 item 2).

Round 1 reported four different subendocardial-third Dice values at "0.5 mm" border error: 0.909 (Golf),
0.927 (India), 0.939 (Kilo) and 0.975 (Hotel). This harness re-implements each advocate's error model on the
same myocardia and measures, for every perturbed wall, the **border error that was actually realised**: the
endocardial and epicardial ASSD (mm) between the perturbed and the reference wall, which is JA8's own unit.

The four models differ in three ways (read from their committed code):

| model | signed distance the noise is added to | grid | correlation length |
|---|---|---|---|
| golf  | half-voxel corrected (slope 1 across the border) | 0.5 mm | 8 mm |
| india | +-0.75 voxel at the border (slope 2/3) | 0.5 mm | 8 mm |
| kilo  | plain edt(~m) - edt(m) at 1.5 mm, linearly zoomed to 0.5 mm (slope 1/2) | 0.5 mm | 10 mm |
| hotel | plain edt(~m) - edt(m) at the working grid (border voxels at +-1 voxel) | 0.75 mm | 6 mm |

`lima` is the proposed shared model: Golf's corrected signed distance, an 8 mm correlation length, and the result
always reported as realised ASSD, never as the nominal sigma.

Outputs per case: myocardium Dice, Dice of each equal-thickness third, realised endo/epi ASSD and signed bias,
median segment-thickness error, and STA (Kilo's segmental transmurality agreement: 16 segments x 4 scar depths).

    python harness.py TS_DIR OUT_JSONL [--jobs 4]

TS_DIR holds Totalsegmentator_dataset/sNNNN/segmentations/*.nii.gz as fetched by fetch_ts.py. Every case passes
heldout.check before a file is opened.
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "Kilo"))
from heldout import check  # noqa: E402
from layers import aha17  # noqa: E402  (Kilo's AHA frame; used only to place STA's virtual scars)

KEYS = ["heart_myocardium", "heart_ventricle_left", "heart_ventricle_right", "heart_atrium_left", "aorta"]
TAUS = (0.15, 0.40, 0.65, 0.90)
KIM = np.array([0.0, 0.25, 0.50, 0.75, 1.0001])
SIGMAS = (0.25, 0.5, 1.0)
MODELS = {  # name: (sdf kind, grid mm, correlation length mm)
    "golf": ("corrected", 0.5, 8.0),
    "india": ("india", 0.5, 8.0),
    "kilo": ("plain_native_zoomed", 0.5, 10.0),
    "hotel": ("plain", 0.75, 6.0),
}
LIMA_CORR = (4.0, 8.0, 16.0)  # correlation-length sweep for the shared model
BIASES = (("endo_in", -0.5, 0.0), ("endo_out", 0.5, 0.0), ("epi_out", 0.0, 0.5))


# ---------------------------------------------------------------- signed distances
def sdf(m, sp, kind):
    """Signed distance (mm, negative inside) in one of the four conventions above."""
    m = m.astype(bool)
    di = ndi.distance_transform_edt(m, sampling=sp)
    do = ndi.distance_transform_edt(~m, sampling=sp)
    h = float(np.mean(sp))
    if kind == "corrected":
        return np.where(m, h / 2 - di, do - h / 2).astype(np.float32)
    if kind == "india":
        return np.where(m, h / 4 - di, do - h / 4).astype(np.float32)
    return (do - di).astype(np.float32)  # plain


def field(shape, grid, sigma, corr, rng):
    if sigma == 0:
        return np.zeros(shape, np.float32)
    f = ndi.gaussian_filter(rng.standard_normal(shape).astype(np.float32), corr / grid)
    return (f * (sigma / (f.std() + 1e-9))).astype(np.float32)


# ---------------------------------------------------------------- geometry on one grid
def surface(m):
    return m & ~ndi.binary_erosion(m, structure=ndi.generate_binary_structure(3, 1))


def assd_and_bias(a, b, sp, ref_sdf):
    """ASSD (mm) between the surfaces of masks a (perturbed) and b (reference); signed bias = mean reference
    signed distance at a's surface voxels (+ outward)."""
    sa, sb = surface(a), surface(b)
    if not sa.any() or not sb.any():
        return float("nan"), float("nan")
    da = ndi.distance_transform_edt(~sb, sampling=sp)[sa]
    db = ndi.distance_transform_edt(~sa, sampling=sp)[sb]
    # a's surface voxels are its inner boundary, whose centres sit half a voxel inside its border
    return (float((da.sum() + db.sum()) / (len(da) + len(db))),
            float(np.mean(ref_sdf[sa]) + float(np.mean(sp)) / 2))


def et_depth(myo, cav, sp):
    """Equal-thickness depth u = d_endo / (d_endo + d_epi) (JA2), voxel-centre corrected; thickness in mm."""
    s = float(np.mean(sp))
    de = ndi.distance_transform_edt(~cav, sampling=sp)
    dp = ndi.distance_transform_edt(myo | cav, sampling=sp)
    th = de + dp - s
    u = np.clip((de - s / 2) / np.maximum(th, 1e-6), 0, 1)
    return np.where(myo, u, np.nan).astype(np.float32), np.where(myo, th, np.nan).astype(np.float32)


def thirds(u):
    out = np.zeros(u.shape, np.uint8)
    ok = ~np.isnan(u)
    out[ok] = 1 + np.minimum((u[ok] * 3).astype(int), 2)
    return out


def dice(a, b):
    s = a.sum() + b.sum()
    return float(2 * (a & b).sum() / s) if s else float("nan")


class Ref:
    """Reference wall on one grid, built from the 1.5 mm labels through corrected signed distances."""

    def __init__(self, L, sp0, aff0, grid):
        f = sp0 / grid
        self.grid = grid
        self.sp = np.full(3, grid)
        self.aff = aff0.copy()
        self.aff[:3, :3] = aff0[:3, :3] / f
        up = {k: ndi.zoom(sdf(L[k], sp0, "corrected"), f, order=1) for k in KEYS}
        self.S_cav0 = ndi.zoom(sdf(L["heart_ventricle_left"], sp0, "plain"), f, order=1)
        self.S_sol0 = ndi.zoom(sdf(L["heart_ventricle_left"] | L["heart_myocardium"], sp0, "plain"), f, order=1)
        self.cav = up["heart_ventricle_left"] < 0
        self.sol = (up["heart_myocardium"] < 0) | self.cav
        self.myo = self.sol & ~self.cav
        self.rv = (up["heart_ventricle_right"] < 0) & ~self.sol
        self.la = (up["heart_atrium_left"] < 0) & ~self.sol
        self.ao = (up["aorta"] < 0) & ~self.sol
        self.S_cav = sdf(self.cav, self.sp, "corrected")
        self.S_sol = sdf(self.sol, self.sp, "corrected")
        self.u, self.th = et_depth(self.myo, self.cav, self.sp)
        self.tr = thirds(self.u)
        self.seg, _ = aha17(self.myo, self.cav, self.rv, self.la, self.aff)
        self.seg_th = {s: float(np.nanmedian(self.th[self.myo & (self.seg == s)]))
                       for s in range(1, 17) if (self.myo & (self.seg == s)).sum() > 50}
        self.scars = {(s, t): self.myo & (self.seg == s) & (self.u < t) for s in range(1, 17) for t in TAUS}
        self.tm = {k: transm(v, self.myo, self.seg, k[0]) for k, v in self.scars.items()}

    def base_sdfs(self, kind):
        if kind == "plain_native_zoomed":
            return self.S_cav0, self.S_sol0
        return sdf(self.cav, self.sp, kind), sdf(self.sol, self.sp, kind)

    def score(self, cav2, sol2):
        cav2 = cav2 & sol2
        myo2 = sol2 & ~cav2
        u2, th2 = et_depth(myo2, cav2, self.sp)
        tr2 = thirds(u2)
        seg2, _ = aha17(myo2, cav2, self.rv & ~sol2, self.la & ~sol2, self.aff)
        endo = assd_and_bias(cav2, self.cav, self.sp, self.S_cav)
        epi = assd_and_bias(sol2, self.sol, self.sp, self.S_sol)
        agree = []
        for (s, t), sc in self.scars.items():
            a, b = self.tm[(s, t)], transm(sc, myo2, seg2, s)
            if not (np.isnan(a) or np.isnan(b)):
                agree.append(np.digitize(a, KIM) == np.digitize(b, KIM))
        terr = [abs(float(np.nanmedian(th2[myo2 & (seg2 == s)])) - v) for s, v in self.seg_th.items()
                if (myo2 & (seg2 == s)).sum() > 50]
        return {"dice_myo": dice(myo2, self.myo),
                "dice_thirds": [dice(tr2 == k, self.tr == k) for k in (1, 2, 3)],
                "assd_endo": endo[0], "bias_endo": endo[1], "assd_epi": epi[0], "bias_epi": epi[1],
                "seg_thick_err_mm": float(np.median(terr)) if terr else float("nan"),
                "sta": float(np.mean(agree)) if agree else float("nan")}


def transm(scar, myo, seg, s):
    m = myo & (seg == s)
    n = m.sum()
    return float((scar & m).sum() / n) if n > 50 else float("nan")


def crop(L, margin_mm, sp):
    box = L["heart_myocardium"] | L["heart_ventricle_left"]
    m = int(np.ceil(margin_mm / sp.min()))
    lo = np.maximum(np.argwhere(box).min(0) - m, 0)
    hi = np.minimum(np.argwhere(box).max(0) + m + 1, box.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    return {k: v[sl] for k, v in L.items()}, lo


def run_case(args):
    case_dir, seed = args
    sid = os.path.basename(case_dir.rstrip("/"))
    check(sid)  # before any file is opened
    t0 = time.time()
    seg_dir = os.path.join(case_dir, "segmentations")
    img = nib.load(os.path.join(seg_dir, "heart_myocardium.nii.gz"))
    sp0 = np.array(img.header.get_zooms()[:3], float)
    L = {k: np.asanyarray(nib.load(os.path.join(seg_dir, f"{k}.nii.gz")).dataobj) > 0 for k in KEYS}
    out = {"case": sid, "spacing": sp0.tolist()}
    if L["heart_myocardium"].sum() * sp0.prod() < 50e3 or L["heart_ventricle_left"].sum() * sp0.prod() < 20e3:
        out["skip"] = "LV myocardium or cavity missing or partial"
        return out
    L, lo = crop(L, 12, sp0)
    aff0 = img.affine.copy()
    aff0[:3, 3] = aff0[:3, :3] @ lo + aff0[:3, 3]
    rng = np.random.default_rng(seed)
    rows = []
    refs = {}
    for name, (kind, grid, corr) in list(MODELS.items()) + [(f"lima_c{int(c)}", ("corrected", 0.5, c))
                                                            for c in LIMA_CORR]:
        if grid not in refs:
            refs[grid] = Ref(L, sp0, aff0, grid)
        R = refs[grid]
        Sc, Ss = R.base_sdfs(kind)
        sig_list = SIGMAS if name in MODELS or name == "lima_c8" else (0.5,)
        for sig in sig_list:
            n1 = field(Sc.shape, grid, sig, corr, rng)
            n2 = field(Sc.shape, grid, sig, corr, rng)
            r = R.score((Sc + n1) < 0, (Ss + n2) < 0)
            r.update(model=name, sigma_nominal=sig, grid=grid, corr_mm=corr)
            rows.append(r)
    R = refs[0.5]
    for name, d_endo, d_epi in BIASES:  # uniform outward shift (mm) of each border, corrected sdf
        r = R.score((R.S_cav - d_endo) < 0, (R.S_sol - d_epi) < 0)
        r.update(model="bias_" + name, sigma_nominal=0.0, grid=0.5, corr_mm=None, shift_endo=d_endo, shift_epi=d_epi)
        rows.append(r)
    out["wall_mm_median_0p5"] = float(np.nanmedian(R.th[R.myo]))
    out["voxels_per_third_0p5"] = out["wall_mm_median_0p5"] / 3 / 0.5
    out["rows"] = rows
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ts_dir"); ap.add_argument("out"); ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    base = os.path.join(a.ts_dir, "Totalsegmentator_dataset")
    subj = sorted(s for s in os.listdir(base) if s.startswith("s"))
    if a.only:
        subj = [s for s in subj if s in a.only]
    for s in subj:
        check(s)
    done = set()
    if os.path.exists(a.out):
        done = {json.loads(x)["case"] for x in open(a.out)}
    todo = [(os.path.join(base, s), int(s[1:])) for s in subj if s not in done]
    with Pool(a.jobs) as p, open(a.out, "a") as fh:
        for r in p.imap_unordered(run_case, todo):
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            print(r["case"], r.get("skip", ""), r.get("seconds", ""), flush=True)


if __name__ == "__main__":
    main()
