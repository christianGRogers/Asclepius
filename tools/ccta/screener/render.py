"""Render every TotalSegmentator vessel seed in SegQueue/seeds-totalseg as one PNG for the auto screener.

Three depth-shaded projections of the seed in patient orientation (RAS): anterior view, patient's left view, view
from above. Each connected component has its own colour (largest blue, 2nd green, 3rd purple, smaller ones orange,
tiny ones red), so fragments and stray blobs stand out. Header: case name, volume, components, flag, grid.
Usage: GIRDER_TOKEN_FILE=... render.py <out dir> [--only name1,name2]   (skips PNGs already written)"""
import json, os, re, sys, tempfile, time
import numpy as np, nibabel as nib
from scipy import ndimage
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/home/user/ccta/scripts")
sys.path.insert(0, "/home/user/Asclepius/src")
import ccta_ingest
from segqueue14.plan import pool_case_name

OUT = sys.argv[1]
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
os.makedirs(OUT, exist_ok=True)
p = ccta_ingest.Pool()
sq = [c for c in p.req("GET", "collection", {"text": "SegQueue"}) if c["name"] == "SegQueue"][0]
seeds = p.req("GET", "folder", {"parentType": "collection", "parentId": sq["_id"], "name": "seeds-totalseg"})[0]
items, off = [], 0
while True:
    page = p.req("GET", "item", {"folderId": seeds["_id"], "limit": 1000, "offset": off})
    items += page
    if len(page) < 1000:
        break
    off += 1000
COL = np.array([[0, 0, 0], [0.20, 0.45, 0.95], [0.20, 0.75, 0.30], [0.60, 0.35, 0.85],
                [0.95, 0.60, 0.15], [0.90, 0.15, 0.15]])


def project(lab, axis, reverse):
    """First-hit label and depth along ``axis``, seen from its high end when ``reverse``."""
    m = lab > 0
    if reverse:
        m = np.flip(m, axis); lab = np.flip(lab, axis)
    hit = m.any(axis)
    first = np.argmax(m, axis)
    depth = np.where(hit, first, m.shape[axis]).astype(float)
    idx = np.expand_dims(first, axis)
    labs = np.take_along_axis(lab, idx, axis).squeeze(axis)
    return np.where(hit, labs, 0), depth, hit


def colour(labs, depth, hit, sizes_rank):
    d = depth[hit]
    lo, hi = (np.percentile(d, 2), np.percentile(d, 98)) if d.size else (0, 1)
    shade = 1.0 - 0.6 * np.clip((depth - lo) / max(hi - lo, 1), 0, 1)
    cls = np.vectorize(lambda v: sizes_rank.get(int(v), 0))(labs) if labs.any() else labs
    rgb = COL[cls] * shade[..., None]
    rgb[~hit] = 1.0
    return rgb


done = skipped = 0
for it in sorted(items, key=lambda i: i["name"]):
    meta = it.get("meta") or {}
    ct_name = meta.get("ct_name") or it["name"].replace("__totalseg-coronary.nii.gz", ".nii.gz")
    case = pool_case_name(ct_name)
    if ONLY and case not in ONLY:
        continue
    png = os.path.join(OUT, case + ".png")
    if os.path.exists(png):
        skipped += 1
        continue
    with tempfile.TemporaryDirectory() as tmp:
        f = os.path.join(tmp, "seed.nii.gz")
        for attempt in range(6):      # janus restarts (502) and cut-short downloads
            try:
                open(f, "wb").write(p.req("GET", f"item/{it['_id']}/download", raw=True))
                break
            except Exception:  # noqa: BLE001
                if attempt == 5:
                    raise
                time.sleep(15 * (attempt + 1))
        im = nib.as_closest_canonical(nib.load(f))      # RAS+: axis0 -> Right, axis1 -> Anterior, axis2 -> Superior
        m = np.asarray(im.dataobj) > 0
        zooms = im.header.get_zooms()[:3]
    if m.any():     # crop to the seed plus ~15 mm, so the tree fills the frame
        spans = [np.flatnonzero(m.any(axis=tuple(a for a in range(3) if a != k))) for k in range(3)]
        lo = np.array([v[0] for v in spans]); hi = np.array([v[-1] + 1 for v in spans])
        pad = [int(round(15 / max(float(z), 1e-3))) for z in zooms]
        sl = tuple(slice(max(0, l - q), min(s, h + q)) for l, h, q, s in zip(lo, hi, pad, m.shape))
        m = m[sl]
    lab, n = ndimage.label(m, structure=np.ones((3, 3, 3)))
    sizes = np.bincount(lab.ravel())[1:] if n else np.zeros(0, int)
    order = np.argsort(sizes)[::-1]
    vox_ml = float(np.prod(zooms)) / 1000
    rank = {}
    for r, k in enumerate(order):
        ml = sizes[k] * vox_ml
        rank[int(k) + 1] = 1 if r == 0 else 2 if r == 1 else 3 if r == 2 else (4 if ml >= 0.05 else 5)
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 5.2), dpi=80)
    views = [  # (title, projection axis, reverse, image axes (row axis, col axis), flip rows, flip cols, labels)
        # RAS+: index 0 increases to the patient's Right, 1 to Anterior, 2 to Superior.
        ("From the front (patient's R on image left)", 1, True, (2, 0), True, True, ("R", "L")),
        ("From the patient's right (anterior on image right)", 0, True, (2, 1), True, False, ("P", "A")),
        ("From above (anterior up, patient's R on image right)", 2, True, (1, 0), True, False, ("L", "R")),
    ]
    for ax, (title, axis, rev, (ra, ca), fr, fc, (lft, rgt)) in zip(axes, views):
        labs, depth, hit = project(lab, axis, rev)
        rgb = colour(labs, depth, hit, rank)
        keep = [a for a in range(3) if a != axis]
        # rgb dims are the remaining axes in order; put row axis first
        if keep.index(ra) != 0:
            rgb = np.transpose(rgb, (1, 0, 2))
        if fr:
            rgb = rgb[::-1]
        if fc:
            rgb = rgb[:, ::-1]
        aspect = zooms[ra] / zooms[ca]
        ax.imshow(rgb, aspect=aspect, interpolation="nearest")
        ax.set_title(title, fontsize=9); ax.set_xticks([]); ax.set_yticks([])
        ax.text(0.01, 0.5, lft, transform=ax.transAxes, fontsize=10, color="k")
        ax.text(0.97, 0.5, rgt, transform=ax.transAxes, fontsize=10, color="k")
    big = ", ".join(f"{sizes[k] * vox_ml:.2f}" for k in order[:4])
    fig.suptitle(f"{case}   seed {m.sum() * vox_ml:.2f} ml, {n} components (largest ml: {big})   "
                 f"flag: {meta.get('flag') or 'ok'}   crop {m.shape} @ {tuple(round(float(z), 3) for z in zooms)} mm",
                 fontsize=10)
    fig.text(0.5, 0.01, "colours: blue largest piece, green 2nd, purple 3rd, orange other pieces >= 0.05 ml, "
             "red tiny fragments; darker = farther from the viewer", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    fig.savefig(png); plt.close(fig)
    json.dump({"case": case, "ct_name": ct_name, "seed_item": it["_id"], "ml": round(float(m.sum() * vox_ml), 3),
               "components": int(n), "flag": meta.get("flag") or "", "zooms": [float(z) for z in zooms],
               "shape": list(m.shape)}, open(os.path.join(OUT, case + ".json"), "w"))
    done += 1
    if done % 25 == 0:
        print("rendered", done, flush=True)
print(f"rendered {done}, already there {skipped}, seeds {len(items)}")
