"""Shared synthetic-LIE benchmark: the case generator (Janus-M Round 3, path jm/paired-scar, ruling section 7 item 1).

One generator for all three advocates. `make_case(heart, blood, cnr, motion, seed)` returns a first-pass CT, a
synthetic late-iodine (LIE) image and its scar-free twin (same noise), the first-pass JA1 labels, and the truth on
the LIE grid. Every JA29-JA30 menu item runs on these cases (menu.py), and run.py scores them.

Hearts
  - 23 public TotalSegmentator v2.0.1 cardiac CTs (CC BY 4.0): the union of Kilo's R2 E5 15 and Golf's R2 22, fetched
    by fetch.py. `load_heart` calls janusm.guard.refuse before opening any file. Hearts whose first-pass LV blood
    has no contrast (median < 150 HU) are skipped, with the reason recorded (Kilo skipped the same two).
  - 'phantom': Juliet R2 E6's static-chest phantom, rendered at pose 0 and used as a 24th heart.

What is real and what is synthetic
  - First pass: the real CT, cropped to the heart + 30 mm and resampled to 1 mm (linear). Labels: TotalSegmentator's
    myocardium, LV, RV and LA (channels 3, 4, 5, 1), carried by signed distance, mapped to JA1 (1 myocardium, 2 LV
    pool, 3 RV pool, 4 LA pool). Channels 0, 2 and 12 have blood HU (great vessels, right atrium) and are "other
    blood"; channel 10 has soft-tissue HU and is left as real CT.
  - LIE: synthetic inside the heart, real outside it.
      * chest (static): the real CT remapped to a late phase: HU < 150 kept; 150-600 (contrast vessels) -> blood
        level; >= 600 (bone) kept. The space the heart occupied at pose 0 is filled with 30 HU.
      * heart + 4 mm shell (moves): myocardium 90 HU; scar 90 + C (C = 60); LV, RV, LA and other blood at the blood
        level; the shell keeps the real (remapped) CT, so epicardial fat moves with the heart.
      * blood level: 'below' 120 (90 + C/2), 'equal' 150 (= scar), 'above' 180 (90 + 1.5 C).
      * Gaussian PSF FWHM 1 mm; white noise SD = C / CNR, CNR in {3, 5} at the 1 mm voxel.
  - Scar: 2-4 segments of one territory (standard AHA map), subendocardial, depth u < T + 0.04 x smooth noise,
    T from {0.15, 0.35, 0.60, 0.90}; placed on the LIE's own geometry (after any phase change), using the shared
    geometry module (janusm.geometry: depth, aha17).
  - Motion of the heart against the static chest, about the heart centroid:
      'none'; 'rigid' (4 mm, mostly cranio-caudal, 2 degrees); 'scale' (rigid + 3 % isotropic scale);
      'phase' (rigid + 5 % phase change: the LV cavity shrinks by 5 % of its equivalent radius, the wall thickens).
  - Truth on the LIE grid: labels, scar, segments, depth u, and per segment both the **volume share** of scar and
    the **depth extent** (share of 10 depth bins called scar per 3-degree x 2 mm column, averaged).

Coordinates: voxel index = millimetres (1 mm grid, origin 0), axes R, A, S.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from janusm import geometry as G  # noqa: E402
from janusm.guard import refuse  # noqa: E402

V = 1.0
CH = {"la": 1, "myo": 3, "lv": 4, "rv": 5}
OTHER_BLOOD = (0, 2, 12)
C_SCAR = 60.0
REMOTE = 90.0
BLOOD = {"below": REMOTE + C_SCAR / 2, "equal": REMOTE + C_SCAR, "above": REMOTE + 1.5 * C_SCAR}
CNRS = (3, 5)
MOTIONS = ("none", "rigid", "scale", "phase", "nonrigid")
#: v3 (Round 4, #251 item 1) adds two motions; the v2 motions and their seeds are unchanged.
#:   phase_neg: rigid + the LIE cavity grown by 5 % of its equivalent radius (a larger LIE cavity, thinner wall);
#:   aniso:     rigid + an anisotropic scale 3 % / 3 % / 6 % in a random orthonormal frame, random sign per case.
MOTIONS_V3 = MOTIONS + ("phase_neg", "aniso")
ANISO = (0.03, 0.03, 0.06)
TS = (0.15, 0.35, 0.60, 0.90)
SHELL_MM = 4.0
A_RAS = np.eye(4)


def _sd(mask):
    return ndi.distance_transform_edt(~mask) - ndi.distance_transform_edt(mask)


def _resample_mask(m, z):
    return ndi.zoom(_sd(m).astype(np.float32), z, order=1) < 0


def load_heart(hid: str, data_dir: Path):
    """First-pass CT (1 mm, HU), JA1 labels and 'other blood' for one heart. Guard first."""
    if hid == "phantom":
        return _phantom()
    import nibabel as nib
    refuse([hid], what="shared LIE benchmark load", source="TotalSegmentator")
    d = Path(data_dir) / hid
    ci = nib.as_closest_canonical(nib.load(str(d / "ct.nii.gz")))
    li = nib.load(str(d / "cardiac_label.nii.gz"))
    if nib.aff2axcodes(li.affine) != ("R", "A", "S") or nib.aff2axcodes(ci.affine) != ("R", "A", "S"):
        return {"id": hid, "skip": "not RAS"}
    ct = np.asanyarray(ci.dataobj).astype(np.float32)
    L = np.asanyarray(li.dataobj) > 0
    sp = np.asarray(ci.header.get_zooms()[:3], float)
    heart = L[CH["myo"]] | L[CH["lv"]] | L[CH["rv"]] | L[CH["la"]]
    nz = np.argwhere(heart)
    m = np.ceil(30 / sp).astype(int)
    lo, hi = np.maximum(nz.min(0) - m, 0), np.minimum(nz.max(0) + m + 1, heart.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    z = sp / V
    ct1 = ndi.zoom(ct[sl], z, order=1)
    rs = {k: _resample_mask(L[c][sl], z) for k, c in CH.items()}
    ob = np.zeros_like(rs["lv"])
    for c in OTHER_BLOOD:
        if L[c].any():
            ob |= _resample_mask(L[c][sl], z)
    lab = np.zeros(ct1.shape, np.int8)
    lab[rs["la"]] = G.LA
    lab[rs["rv"]] = G.RV
    lab[rs["myo"]] = G.MYO
    lab[rs["lv"]] = G.LV
    ob &= lab == 0
    if np.median(ct1[lab == G.LV]) < 150:
        return {"id": hid, "skip": "no contrast in the LV blood pool"}
    return {"id": hid, "ct": ct1, "lab": lab, "ob": ob}


def _phantom():
    sys.path.insert(0, str(ROOT / "experiments/JanusM/Juliet"))
    import register_lie as R
    rng = np.random.default_rng(5)
    img, t = R.render(R.FP, np.zeros(18), (np.eye(3), np.zeros(3)), 0.0, R.FP["scar"], 30.0, rng, want_truth=True)
    flip = (slice(None), slice(None, None, -1), slice(None))       # E6's +y is posterior; make +y anterior
    lab0 = t["lab"][flip]
    lab = np.where(np.isin(lab0, (1, 2, 3, 4)), lab0, 0).astype(np.int8)
    return {"id": "phantom", "ct": img[flip].astype(np.float32), "lab": lab, "ob": lab0 == 12}


def _remap_late(ct, blood):
    out = ct.copy()
    out[(ct >= 150) & (ct < 600)] = blood
    return out


def _rot(axis, deg):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    a = np.deg2rad(deg)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K


def motion_params(motion, rng):
    if motion == "none":
        return np.eye(3), np.zeros(3), 1.0, 0.0
    if motion == "nonrigid":                      # Kilo R2 E5: whole image, rot N(0, 3 deg) per axis, trans N(0, 4 mm)
        ang = rng.normal(0, 3.0, 3)
        R = _rot([1, 0, 0], ang[0]) @ _rot([0, 1, 0], ang[1]) @ _rot([0, 0, 1], ang[2])
        return R, rng.normal(0, 4.0, 3), 1.0, 0.0
    v = rng.normal(0, 1, 3) * np.array([0.35, 0.35, 1.0])
    t = v / np.linalg.norm(v) * 4.0
    R = _rot(rng.normal(0, 1, 3), 2.0)
    if motion == "aniso":                         # v3: draws after the v2 draws, so v2 motions are unchanged
        Q, _ = np.linalg.qr(rng.normal(0, 1, (3, 3)))
        sign = 1.0 if rng.random() < 0.5 else -1.0
        return R, t, Q @ np.diag(1.0 + sign * np.asarray(ANISO)) @ Q.T, 0.0
    e = {"phase": 0.05, "phase_neg": -0.05}.get(motion, 0.0)
    return R, t, (1.03 if motion == "scale" else 1.0), e


def _columns(lab, aha):
    """Per-voxel angle (deg) about the AHA long axis and position along it (mm): the E-D column coordinates."""
    b, a = np.asarray(aha.base_mm), np.asarray(aha.apex_mm)
    ax = (a - b) / np.linalg.norm(a - b)
    ref = np.cross(ax, [0.0, 0.0, 1.0])
    if np.linalg.norm(ref) < 1e-3:
        ref = np.cross(ax, [0.0, 1.0, 0.0])
    ref /= np.linalg.norm(ref)
    ref2 = np.cross(ax, ref)
    idx = np.indices(lab.shape).reshape(3, -1).T.astype(np.float32)
    r = idx - b
    s = (r @ ax).reshape(lab.shape)
    phi = (np.degrees(np.arctan2(r @ ref2, r @ ref)) % 360).reshape(lab.shape)
    return phi.astype(np.float32), s.astype(np.float32)


def depth_extent(call, myo, seg, u, phi, s):
    """E-D: share of 10 depth bins (of u) called scar, per 3-degree x 2 mm column, averaged over the segment."""
    out = np.zeros(18)
    m = myo & (seg > 0) & np.isfinite(u)
    col = (np.floor(phi[m] / 3).astype(np.int64) * 100000 + (np.floor(s[m] / 2).astype(np.int64) + 500) * 100
           + seg[m].astype(np.int64))
    db = np.clip(np.floor(u[m] * 10), 0, 9).astype(np.int64)
    key = col * 10 + db
    uk, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
    binscar = (np.bincount(inv, weights=call[m]) / cnt) > 0.5
    ck = uk // 10
    uc, cinv, ccnt = np.unique(ck, return_inverse=True, return_counts=True)
    colext = np.bincount(cinv, weights=binscar) / ccnt
    colseg = (uc % 100).astype(int)
    ok = ccnt >= 4                                                  # columns spanning most of the wall
    for k in range(1, 18):
        sel = ok & (colseg == k)
        out[k] = colext[sel].mean() if sel.any() else np.nan
    return out[1:]


def volume_share(call, myo, seg):
    out = np.full(17, np.nan)
    for k in range(1, 18):
        m = myo & (seg == k)
        if m.sum() >= 20:
            out[k - 1] = call[m].mean()
    return out


def _smooth_field(shape, rms_mm, corr_mm, rng):
    """A smooth random displacement field (3, *shape), each component with the given RMS (mm), Gaussian correlation."""
    f = np.empty((3,) + tuple(shape), np.float32)
    for k in range(3):
        g = ndi.gaussian_filter(rng.standard_normal(shape).astype(np.float32), corr_mm / V)
        f[k] = g / (g.std() + 1e-9) * rms_mm
    return f


def make_case(heart: dict, blood: str, cnr: int, motion: str, seed: int):
    """One benchmark case. Returns the first-pass CT and labels, three LIE images with the same noise (full;
    scar-free twin; blood set to remote), and the truth on the LIE grid. `tre_pts` holds (LIE point, true first-pass
    point) pairs over the truth wall, for any registration's residual."""
    rng = np.random.default_rng(seed)
    ct0, lab0, ob = heart["ct"], heart["lab"], heart["ob"]
    shape = lab0.shape
    bl = BLOOD[blood]
    R, t, sc, e = motion_params(motion, rng)
    # LIE heart at pose 0, with any phase change (cavity shrinks, wall thickens)
    lab_l = lab0.copy()
    if e < 0:                                     # v3 phase_neg: the cavity grows into the myocardial wall
        cav = lab0 == G.LV
        req = (3 * cav.sum() / (4 * np.pi)) ** (1 / 3)
        grow = (lab0 == G.MYO) & (ndi.distance_transform_edt(~cav) <= -e * req)
        lab_l[grow] = G.LV
    if e > 0:
        cav = lab0 == G.LV
        req = (3 * cav.sum() / (4 * np.pi)) ** (1 / 3)
        # shrink away from the myocardial walls only, so the cavity keeps its contact with the LA (mitral plane)
        shrink = cav & (ndi.distance_transform_edt(cav | (lab0 == G.LA)) <= e * req)
        lab_l[shrink] = G.MYO
    aha_l = G.aha17(lab_l, affine=A_RAS)
    if aha_l.segments is None:
        return {"skip": "AHA failed on the LIE frame: " + "; ".join(aha_l.flags)}
    seg_l = np.nan_to_num(aha_l.segments).astype(np.int16)
    u_l = G.depth(lab_l, affine=A_RAS).u
    phi_l, s_l = _columns(lab_l, aha_l)
    # scar (Golf's mix, agreed on #179): every segment of one territory draws a Kim-bin midpoint with equal weight
    terr = rng.choice(["LAD", "LCx", "RCA"])
    Tseg = np.zeros(18)
    for k in [k for k, v in G.AHA_STANDARD.items() if v == terr and k != 17]:
        Tseg[k] = rng.choice((0.0,) + TS)
    wob = ndi.gaussian_filter(rng.standard_normal(shape).astype(np.float32), 3)
    wob /= wob.std() + 1e-9
    myo_l = lab_l == G.MYO
    tsg = Tseg[np.clip(seg_l, 0, 17)]
    scar0 = myo_l & (tsg > 0) & (np.nan_to_num(u_l, nan=9) < tsg + 0.04 * wob)
    # pose-0 intensities: full, scar-free, and blood set to remote (Golf's spill counterfactual)
    heartmask = lab_l > 0
    region0 = ndi.binary_dilation(heartmask, iterations=int(SHELL_MM / V))
    blood_mask = np.isin(lab_l, (G.LV, G.RV, G.LA)) | ob

    def pose0(blood_level, with_scar):
        late = _remap_late(ct0, blood_level)
        hv = late.copy()
        hv[myo_l] = REMOTE
        hv[blood_mask] = blood_level
        if with_scar:
            hv[scar0] = REMOTE + C_SCAR
        return late, hv

    variants = {"lie": pose0(bl, True), "lie_free": pose0(bl, False), "lie_noblood": pose0(REMOTE, True)}
    # motion: x0(x) = the pose-0 point imaged at LIE voxel x
    c = np.argwhere(heartmask).mean(0)
    idx = np.indices(shape).reshape(3, -1).astype(np.float32)
    if np.ndim(sc) == 2:                         # v3 aniso: x = R S (x0 - c) + c + t
        x0 = np.linalg.inv(sc) @ (R.T @ (idx - (c + t)[:, None])) + c[:, None]
    else:
        x0 = (R.T @ (idx - (c + t)[:, None])) / sc + c[:, None]
    whole = motion == "nonrigid"                 # Kilo E5: the whole image moves (chest too), plus a smooth field
    if whole:
        x0 = x0 - _smooth_field(shape, 1.5, 20.0, rng).reshape(3, -1)

    def mv(a, order):
        return ndi.map_coordinates(a, x0, order=order, mode="nearest").reshape(shape)

    noise = rng.normal(0, C_SCAR / cnr, shape).astype(np.float32)
    psf = 1.0 / 2.355 / V
    out = {}
    reg_m = mv(region0.astype(np.float32), 1) > 0.5
    for name, (late, hv) in variants.items():
        if whole:
            img = mv(np.where(region0, hv, late), 1)
        else:
            bg = late.copy()
            bg[region0] = 30.0
            img = np.where(reg_m, mv(hv, 1), bg)
        out[name] = (ndi.gaussian_filter(img, psf) + noise).astype(np.float32)
    lab_t = mv(lab_l.astype(np.float32), 0).astype(np.int8)
    scar_t = mv(scar0.astype(np.float32), 0) > 0.5
    seg_t = mv(seg_l.astype(np.float32), 0).astype(np.int16)
    u_t = mv(np.nan_to_num(u_l, nan=-1).astype(np.float32), 0)
    u_t[lab_t != G.MYO] = np.nan
    phi_t, s_t = mv(phi_l, 0), mv(s_l, 0)
    myo_t = lab_t == G.MYO
    sel = np.flatnonzero(myo_t.ravel())
    sel = sel[rng.permutation(len(sel))[:20000]]
    truth = {"vol": volume_share(scar_t, myo_t, seg_t), "depth": depth_extent(scar_t, myo_t, seg_t, u_t, phi_t, s_t),
             "T_nominal": Tseg[1:].tolist(), "territory": str(terr)}
    return {"fp": ct0, "lab_fp": lab0, **out,
            "lab_t": lab_t, "seg_t": seg_t, "u_t": u_t, "phi_t": phi_t, "s_t": s_t, "scar_t": scar_t, "truth": truth,
            "tre_pts": (idx[:, sel].T.astype(float), x0[:, sel].T.astype(float)),
            "motion": {"R": R, "t": t, "s": sc, "e": e, "c": c, "whole_image": whole}, "blood": bl, "cnr": cnr,
            "aha_flags": aha_l.flags}
