"""Per-branch geometry on ImageCAS-X 14-class labels mapped to the project's 4 classes, plus agreement
between our binary masks (original ImageCAS) and the ImageCAS-X lumen.

4-class proxy ("trunk"): LM=1, LAD=2, LCx=3, RCA=9 -> 1..4; side branches -> background.
Territory extents also computed: left tree = {1..8,12,13,14}, right tree = {9,10,11}.
Per case writes one JSON line. Usage: branch_geometry.py <out.jsonl> <worker> <nworkers>
Case mapping: cNNNN == ImageCAS id NNNN+1 (verified by header match, match_icx.py)."""
import os, sys, glob, json, time
import numpy as np, nibabel as nib
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
W = SCR + '/work/Atlas'
out, wk, nw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
TRUNK = {1: 1, 2: 2, 3: 3, 9: 4}
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
LEFT = [1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14]; RIGHT = [9, 10, 11]
done = set()
if os.path.exists(out):
    done = {json.loads(l)['icx_id'] for l in open(out)}
files = sorted(glob.glob(W + '/icx/*.coronary.nii.gz'), key=lambda p: int(os.path.basename(p).split('.')[0]))

def bbox(m):
    idx = np.nonzero(m)
    if len(idx[0]) == 0: return None
    return [int(i.min()) for i in idx], [int(i.max()) for i in idx]

def resample_roundtrip(onehot, sp, tsp):
    """onehot: (C,X,Y,Z) float32 on native grid; linear resample to target spacing tsp and back; argmax."""
    zf = np.array(sp) / tsp
    out = []
    for c in range(onehot.shape[0]):
        lo = ndi.zoom(onehot[c], zf, order=1)
        back = ndi.zoom(lo, np.array(onehot.shape[1:]) / np.array(lo.shape), order=1)
        out.append(back)
    return np.argmax(np.stack(out), 0)

def dice(a, b):
    s = a.sum() + b.sum()
    return float(2 * (a & b).sum() / s) if s else float('nan')

with open(out, 'a') as fo:
    for k, p in enumerate(files):
        i = int(os.path.basename(p).split('.')[0])
        if i % nw != wk or i in done: continue
        try:
            img = nib.load(p); lab = np.asarray(img.dataobj).astype(np.uint8)
        except Exception:
            continue
        t0 = time.time()
        case = 'c%04d' % (i - 1)
        sp = np.array(img.header.get_zooms()[:3], dtype=float)
        r = dict(icx_id=i, case=case, shape=list(lab.shape), sp=sp.tolist())
        r['present14'] = sorted(int(v) for v in np.unique(lab) if v)
        r['vox14'] = {int(v): int(c) for v, c in zip(*np.unique(lab, return_counts=True)) if v}
        t4 = np.zeros_like(lab)
        for a, b in TRUNK.items(): t4[lab == a] = b
        # extents (mm) of trees and classes
        for nm, sel in [('left', np.isin(lab, LEFT)), ('right', np.isin(lab, RIGHT)), ('all', lab > 0)] + \
                       [(NAMES[c], t4 == c) for c in range(1, 5)]:
            bb = bbox(sel)
            r['bb_' + nm] = None if bb is None else [[a for a in bb[0]], [a for a in bb[1]]]
        # caliber: EDT (mm) sampled on skeleton, per trunk class, computed in a crop around the tree
        bb = bbox(lab > 0); lo = np.maximum(np.array(bb[0]) - 8, 0); hi = np.minimum(np.array(bb[1]) + 9, lab.shape)
        sl = tuple(slice(a, b) for a, b in zip(lo, hi))
        crop = t4[sl]; cropall = (lab[sl] > 0)
        edt = ndi.distance_transform_edt(cropall, sampling=sp)  # radius (mm) to lumen boundary, whole lumen
        sk = skeletonize(cropall)
        r['radius_mm'] = {}
        for c in range(1, 5):
            v = edt[sk & (crop == c)]
            r['radius_mm'][NAMES[c]] = np.round(v, 3).tolist() if v.size < 4000 else np.round(np.random.default_rng(0).choice(v, 4000, replace=False), 3).tolist()
        vside = edt[sk & (crop == 0) & cropall]
        r['radius_mm']['side'] = np.round(vside, 3).tolist() if vside.size < 4000 else np.round(np.random.default_rng(0).choice(vside, 4000, replace=False), 3).tolist()
        # resampling round-trip damage to the 4-class label (target spacings in mm)
        # per class, in that class's own bbox (+6 vox), linear down/up, threshold 0.5 (binary per class)
        r['rt_dice'] = {}
        for tsp in (0.5, 0.8):
            d = {}
            for c in range(1, 5):
                b = bbox(crop == c)
                if b is None: continue
                s2 = tuple(slice(max(a - 6, 0), e + 7) for a, e in zip(*b))
                x = (crop[s2] == c).astype(np.float32)
                lo_ = ndi.zoom(x, sp / tsp, order=1)
                back = ndi.zoom(lo_, np.array(x.shape) / np.array(lo_.shape), order=1) >= 0.5
                d[NAMES[c]] = dice(back, x > 0)
            r['rt_dice'][str(tsp)] = d
        # agreement with our binary mask (original ImageCAS label)
        mp = SCR + '/data/masks/%s.nii.gz' % case
        if os.path.exists(mp):
            ours = np.asarray(nib.load(mp).dataobj, dtype=np.float32) > 0.5
            icx = lab > 0
            r['ours_vox'] = int(ours.sum()); r['icx_vox'] = int(icx.sum())
            r['dice_ours_icx'] = dice(ours, icx)
            r['recall_icx_by_ours'] = float((ours & icx).sum() / icx.sum())
            r['recall_by_class_ours'] = {NAMES[c]: float((ours & (t4 == c)).sum() / max((t4 == c).sum(), 1)) for c in range(1, 5)}
        r['sec'] = round(time.time() - t0, 1)
        fo.write(json.dumps(r) + '\n'); fo.flush()
