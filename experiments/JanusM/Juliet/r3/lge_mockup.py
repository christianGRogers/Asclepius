"""Juliet R3 (Janus-M Round 3, path jm/paired-scar, ruling section 7 item 3): a synthetic LGE mock-up for the
segment read form. Opens no case: every image is drawn from geometry here.

It makes
  - 5 mock patients: short-axis LGE stacks (10 slices, 8 mm thick, 1.5 mm in-plane), each with a truth table per AHA
    segment 1-17 (presence, pattern, hyperenhanced share of the segment's myocardium, Kim bin), so a reader can time
    the form and check their bins against truth before any real CMR is read;
  - the read form's example panel: one mid-ventricular slice per Kim bin (a segment with 10, 35, 60 and 90 % of its
    myocardium enhanced), plus a mid-wall stripe (non-ischaemic) and an epicardial scar for the pattern field.

Model (in the short-axis frame, radiological view: anterior up, septum left):
  LV cavity: truncated ellipsoid, semi-axes 25 mm (in-plane) and 45 mm (long axis); wall 10 mm; 3 mm epicardial fat;
  RV crescent over the septum. Signal (PSIR-like, arbitrary units): nulled myocardium 0.05, blood 0.55, scar 1.0,
  fat 0.45, background 0.20. Gaussian blur 1.5 mm in-plane; noise SD 0.05.
  AHA: slices split into basal / mid / apical thirds of the cavity length; slices beyond the cavity are segment 17.
  Sectors: basal and mid 60 degrees with segment 1 centred anterior; apical 90 degrees; 13 anterior, 14 septal,
  15 inferior, 16 lateral.
  Scar: subendocardial (or transmural, mid-wall, epicardial) over an arc of the segment; the truth share is counted
  on a 0.25 mm grid.

Usage: python lge_mockup.py   -> mock_lge/case_[A-E].nii.gz, mock_lge/truth.json, lge_bin_panel.png
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
OUT = HERE / "mock_lge"
A, B, WALL, FAT = 25.0, 45.0, 10.0, 3.0
INPLANE, NPIX = 1.5, 160
SLICES = np.linspace(8.0, -54.0, 10)          # long-axis positions (mm) of slice centres, base -> apex
THICK = 8.0
SIG = {"myo": 0.05, "blood": 0.55, "scar": 1.0, "fat": 0.45, "bg": 0.20}
CENTRE = {1: 90, 2: 150, 3: 210, 4: 270, 5: 330, 6: 30}                     # basal / mid sector centres (deg)
APICAL = {13: 90, 14: 180, 15: 270, 16: 0}
BINS = (0.005, 0.25, 0.50, 0.75)


def kim(share):
    return 0 if share <= BINS[0] else 1 + int(np.searchsorted(BINS[1:], share, side="left"))


def level_of(w):
    """AHA level of a long-axis position: 0 basal, 1 mid, 2 apical, 3 apex cap (beyond the cavity)."""
    top, bottom = 10.0, -B
    if w < bottom:
        return 3
    return int(np.clip((top - w) / (top - bottom) * 3, 0, 2))


def segment_of(level, ang):
    if level == 3:
        return 17
    if level == 2:
        return min(APICAL, key=lambda k: abs(((ang - APICAL[k]) + 180) % 360 - 180))
    base = min(CENTRE, key=lambda k: abs(((ang - CENTRE[k]) + 180) % 360 - 180))
    return base + 6 * level


def slice_geometry(w, step):
    """Polar fields of one short-axis slice at long-axis position w, on a grid of `step` mm."""
    n = int(round(NPIX * INPLANE / step))
    ax = (np.arange(n) + 0.5) * step - n * step / 2
    X, Y = np.meshgrid(ax, -ax)                       # image x right, y up (anterior)
    r = np.hypot(X, Y)
    ang = (np.degrees(np.arctan2(Y, X)) + 360) % 360
    q = 1 - (w / B) ** 2
    r_in = A * np.sqrt(q) if q > 0 else 0.0
    qo = 1 - (w / (B + WALL)) ** 2
    r_out = (A + WALL) * np.sqrt(qo) if qo > 0 else 0.0
    return X, Y, r, ang, r_in, r_out


def render_slice(w, scars, step=INPLANE):
    """scars: list of dicts {seg, kind, arc (deg), depth (0-1)} -> image, myocardium mask, scar mask, segment map."""
    X, Y, r, ang, r_in, r_out = slice_geometry(w, step)
    img = np.full(r.shape, SIG["bg"])
    myo = (r >= r_in) & (r < r_out)
    cav = r < r_in
    fat = (r >= r_out) & (r < r_out + FAT) & (r_out > 0)
    rv = (np.hypot(X + (A + WALL) * 0.9, Y) < (A + 6)) & ~myo & ~cav & ~fat & (w > -35)
    img[fat] = SIG["fat"]
    img[rv] = SIG["blood"]
    img[cav] = SIG["blood"]
    img[myo] = SIG["myo"]
    lev = level_of(w)
    seg = np.zeros(r.shape, np.int16)
    if myo.any():
        segs = np.vectorize(lambda a: segment_of(lev, a))(ang[myo])
        seg[myo] = segs
    u = np.zeros(r.shape)
    if r_out > r_in:
        u = np.clip((r - r_in) / (r_out - r_in), 0, 1)
    scar = np.zeros(r.shape, bool)
    for s in scars:
        in_seg = myo & (seg == s["seg"])
        if not in_seg.any():
            continue
        c = np.angle(np.exp(1j * np.radians(ang[in_seg])).mean(), deg=True) % 360
        near = np.zeros(r.shape, bool)
        near[in_seg] = np.abs(((ang[in_seg] - c) + 180) % 360 - 180) <= s["arc"] / 2
        d = s["depth"]
        if s["kind"] == "subendocardial":
            band = u < d
        elif s["kind"] == "transmural":
            band = np.ones(r.shape, bool)
        elif s["kind"] == "midwall":
            band = (u > 0.5 - d / 2) & (u < 0.5 + d / 2)
        else:                                          # epicardial
            band = u > 1 - d
        scar |= near & band
    img[scar] = SIG["scar"]
    return img, myo, scar, seg


def stack(scars, rng):
    imgs, truth_vox = [], {}
    for w in SLICES:
        hi, myo, scar, seg = render_slice(w, scars, step=0.25)          # truth on a fine grid
        for k in np.unique(seg[myo]):
            t = truth_vox.setdefault(int(k), [0, 0])
            t[0] += int((scar & (seg == k)).sum())
            t[1] += int((myo & (seg == k)).sum())
        f = int(round(INPLANE / 0.25))
        lo = hi.reshape(NPIX, f, NPIX, f).mean(axis=(1, 3))
        lo = ndi.gaussian_filter(lo, 1.5 / 2.355 / INPLANE) + rng.normal(0, 0.05, lo.shape)
        imgs.append(lo)
    return np.stack(imgs, -1), {k: v[0] / v[1] for k, v in truth_vox.items() if v[1]}


CASES = {
    "A": [],
    "B": [{"seg": 7, "kind": "subendocardial", "arc": 60, "depth": 0.15},
          {"seg": 8, "kind": "subendocardial", "arc": 60, "depth": 0.40},
          {"seg": 13, "kind": "subendocardial", "arc": 90, "depth": 0.65},
          {"seg": 14, "kind": "transmural", "arc": 90, "depth": 1.0}],
    "C": [{"seg": 4, "kind": "transmural", "arc": 60, "depth": 1.0},
          {"seg": 10, "kind": "subendocardial", "arc": 60, "depth": 0.85},
          {"seg": 15, "kind": "subendocardial", "arc": 70, "depth": 0.5}],
    "D": [{"seg": 2, "kind": "midwall", "arc": 50, "depth": 0.22},
          {"seg": 3, "kind": "midwall", "arc": 50, "depth": 0.22},
          {"seg": 9, "kind": "midwall", "arc": 50, "depth": 0.22}],
    "E": [{"seg": 5, "kind": "subendocardial", "arc": 30, "depth": 0.30},
          {"seg": 11, "kind": "subendocardial", "arc": 40, "depth": 0.20},
          {"seg": 12, "kind": "epicardial", "arc": 40, "depth": 0.35}],
}
PATTERN = {"subendocardial": "ischaemic, subendocardial", "transmural": "ischaemic, transmural",
           "midwall": "non-ischaemic, mid-wall", "epicardial": "non-ischaemic, epicardial"}


def main():
    import nibabel as nib
    OUT.mkdir(exist_ok=True)
    rng = np.random.default_rng(20261030)
    truth = {}
    for name, scars in CASES.items():
        vol, share = stack(scars, rng)
        aff = np.diag([INPLANE, INPLANE, THICK + 2.0, 1.0])
        nib.save(nib.Nifti1Image(np.round(vol * 1000).astype(np.int16), aff), str(OUT / f"case_{name}.nii.gz"))
        kinds = {s["seg"]: s["kind"] for s in scars}
        truth[name] = {str(k): {"present": share.get(k, 0) > 0.005, "share": round(share.get(k, 0.0), 3),
                                "kim_bin": kim(share.get(k, 0.0)),
                                "pattern": PATTERN[kinds[k]] if k in kinds and share.get(k, 0) > 0.005 else None}
                       for k in range(1, 18)}
    (OUT / "truth.json").write_text(json.dumps(truth, indent=1) + "\n")
    panel()
    for n, t in truth.items():
        print(n, {k: (v["share"], v["kim_bin"]) for k, v in t.items() if v["present"]})


def panel():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    w = SLICES[4]
    rng = np.random.default_rng(7)
    rows = [("Kim bin 1 (1-25 %)", {"seg": 8, "kind": "subendocardial", "arc": 60, "depth": 0.17}),
            ("Kim bin 2 (26-50 %)", {"seg": 8, "kind": "subendocardial", "arc": 60, "depth": 0.40}),
            ("Kim bin 3 (51-75 %)", {"seg": 8, "kind": "subendocardial", "arc": 60, "depth": 0.66}),
            ("Kim bin 4 (76-100 %)", {"seg": 8, "kind": "subendocardial", "arc": 60, "depth": 0.92}),
            ("Pattern: mid-wall (non-ischaemic)", {"seg": 9, "kind": "midwall", "arc": 50, "depth": 0.22}),
            ("Pattern: epicardial (non-ischaemic)", {"seg": 11, "kind": "epicardial", "arc": 50, "depth": 0.35})]
    fig, axs = plt.subplots(2, 3, figsize=(10.5, 7.2))
    for axp, (title, s) in zip(axs.ravel(), rows):
        hi, myo, scar, seg = render_slice(w, [s], step=0.25)
        share = (scar & (seg == s["seg"])).sum() / max((myo & (seg == s["seg"])).sum(), 1)
        img, *_ = render_slice(w, [s])
        img = ndi.gaussian_filter(img, 1.5 / 2.355 / INPLANE) + rng.normal(0, 0.05, img.shape)
        axp.imshow(img[30:130, 30:130], cmap="gray", vmin=0, vmax=1.1)
        axp.set_title(f"{title}\nsegment {s['seg']}: {100 * share:.0f} % of its myocardium", fontsize=9)
        axp.axis("off")
    fig.suptitle("LGE read form: example panel (synthetic mid-ventricular short axis; anterior up, septum left)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(HERE / "lge_bin_panel.png", dpi=110)


if __name__ == "__main__":
    main()
