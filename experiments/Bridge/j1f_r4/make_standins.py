"""Janus 1-F round 4 (Bridge): SegQueue14-shaped stand-in exports built from ImageCAS-X training labels, to test the
J1F-2 freeze script without any pool read.

Each stand-in "read" is one of the hash-chosen 620 training cases (fetch_subset.py), converted to stage-1 classes by the
scorer of record's `stage1_labels`, plus synthetic stage-2 branches of known geometry:
  * S1, S2, S3 off the LAD at 10 / 25 / 40 mm from the LM; Conus at 5 mm and SN at 12 mm along the RCA (one SN in five
    off the LCx at 8 mm instead); RMA at 40 mm along the RCA;
  * straight tubes heading towards the tree's centroid (into the heart), +-25 degrees, radius 0.5-0.8 mm;
  * an ostium drawn over the parent (D47 Q4) of known length `ov` mm;
  * optionally a gap: the tube is cut and its distal piece set `gap` mm further on;
  * omissions: a class not drawn (D54: confirmed absent).
A second read (`<name>__r2`) of the first `n_pairs` patients is the same geometry re-drawn: tips shortened 0-4 mm,
radius +-0.1 mm, its own omissions. The layout is segqueue14-export's (`<case>/segmentations/<Class>.nii.gz`, all
21 classes, `read.json`, `manifest.json` with `classes: read`, `replicas: all`, `pool_seal.mode: exclude`).
Names are `Standin<A-D>__p<NNNN>`: no pool, seal or ImageCAS-X id. `truth.json` holds every injected number, with
distances measured by a k-d tree (the freeze uses distance transforms).

Usage: python make_standins.py <icx_dir> <out_dir> <scenario: nominal|stress> [n_pairs=12]
"""
import hashlib
import json
import os
import sys

import numpy as np
import nibabel as nb
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1f2_freeze as F  # noqa: E402

J = F.J
SCEN = {
    'nominal': {'L': (12, 45), 'ov': (0.0, 2.5), 'p_gap': 0.03, 'gap': (3, 10), 'q1': 0.05, 'q2': 0.05},
    'stress':  {'L': (12, 45), 'ov': (3.5, 5.5), 'p_gap': 0.08, 'gap': (38, 38), 'q1': 0.05, 'q2': 0.45},
}
ALL21 = ['LM', 'LAD', 'LCx', 'RCA', 'Stent', 'Calcified plaque', 'Non-calcified plaque', 'D1', 'D2', 'D3', 'S1', 'S2',
         'S3', 'OM1', 'OM2', 'SN', 'Conus', 'RMA', 'PDA', 'PLB', 'Ramus']


def _box(mask, pad=2):
    idx = np.argwhere(mask)
    lo, hi = np.maximum(idx.min(0) - pad, 0), np.minimum(idx.max(0) + pad + 1, mask.shape)
    return tuple(slice(a, b) for a, b in zip(lo, hi))


def arc(mask, z, seeds):
    """Geodesic distance within `mask` from `seeds`, computed on the mask's bounding box only."""
    b = _box(mask)
    off = np.array([s.start for s in b])
    d = np.full(mask.shape, np.inf)
    d[b] = J._geodesic(mask[b], [tuple(np.asarray(q) - off) for q in seeds], z)
    return d


def junction(mask, z, d, s):
    """The parent voxel at arc length ~s with the largest radius (on the centre of the lumen)."""
    b = _box(mask)
    edt = np.zeros(mask.shape)
    edt[b] = ndi.distance_transform_edt(mask[b], sampling=z)
    cand = np.argwhere(mask & np.isfinite(d) & (np.abs(d - s) < 1.0))
    if not len(cand):
        fin = np.argwhere(mask & np.isfinite(d))
        cand = fin[[int(np.argmin(np.abs(d[tuple(fin.T)] - s)))]]
    return cand[int(np.argmax(edt[tuple(cand.T)]))]


def tube(shape, z, p0, u, t0, t1, r):
    """Voxels within r mm of the segment p0 + t u, t in [t0, t1] (mm), clipped to the grid."""
    a, b = p0 + t0 * u, p0 + t1 * u
    lo = np.floor((np.minimum(a, b) - r - 1) / z).astype(int)
    hi = np.ceil((np.maximum(a, b) + r + 1) / z).astype(int) + 1
    lo, hi = np.maximum(lo, 0), np.minimum(hi, shape)
    m = np.zeros(shape, bool)
    if np.any(hi <= lo):
        return m
    g = np.stack(np.meshgrid(*[np.arange(l, h) * zz for l, h, zz in zip(lo, hi, z)], indexing='ij'), -1)
    v = g - p0
    t = np.clip(v @ u, t0, t1)
    near = np.linalg.norm(v - t[..., None] * u, axis=-1) <= r
    m[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] = near
    return m


def unit(rng, base):
    for _ in range(100):
        w = base / (np.linalg.norm(base) + 1e-9) + rng.normal(0, 0.45, 3)
        w /= np.linalg.norm(w)
        if np.degrees(np.arccos(np.clip(w @ (base / (np.linalg.norm(base) + 1e-9)), -1, 1))) <= 25:
            return w
    return base / np.linalg.norm(base)


def build_case(path, rng, sc):
    im = nb.load(path)
    z = np.array(im.header.get_zooms()[:3], float)
    raw = np.asarray(im.dataobj).astype(np.uint8)
    idx = np.argwhere(raw > 0)
    m = np.ceil(25.0 / z).astype(int)                                # 25 mm around the tree
    lo, hi = np.maximum(idx.min(0) - m, 0), np.minimum(idx.max(0) + m + 1, raw.shape)
    raw = raw[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    aff = im.affine.copy(); aff[:3, 3] = im.affine[:3, :3] @ lo + im.affine[:3, 3]
    lab1, _ = J.stage1_labels(raw, z)
    ch = {n: lab1 == J.NAMES.index(n) for n in J.NAMES[1:]}           # whole stage-1 channels, no overlap
    tree = (lab1 > 0) & (lab1 != J.IGNORE)
    cen = np.argwhere(tree).mean(0) * z
    plan = []
    lad, lm, rca, lcx = ch['LAD'], ch['LM'], ch['RCA'], ch['LCx']
    if lad.any():
        seeds = np.argwhere(lad & ndi.binary_dilation(lm, iterations=2)) if lm.any() else np.zeros((0, 3), int)
        if not len(seeds):
            bb = _box(lad)
            seeds = F._ostium_seed(lad[bb], z) + np.array([q.start for q in bb])
        d = arc(lad, z, seeds)
        for c, s in (('S1', 10), ('S2', 25), ('S3', 40)):
            plan.append((c, 'LAD', junction(lad, z, d, s)))
    if rca.any():
        bb = _box(rca)
        d = arc(rca, z, F._ostium_seed(rca[bb], z) + np.array([q.start for q in bb]))
        plan.append(('Conus', 'RCA', junction(rca, z, d, 5)))
        plan.append(('RMA', 'RCA', junction(rca, z, d, 40)))
        if rng.random() >= 0.2:
            plan.append(('SN', 'RCA', junction(rca, z, d, 12)))
    if lcx.any() and not any(p[0] == 'SN' for p in plan):
        seeds = np.argwhere(lcx & ndi.binary_dilation(lm, iterations=2)) if lm.any() else np.zeros((0, 3), int)
        if not len(seeds):
            bb = _box(lcx)
            seeds = F._ostium_seed(lcx[bb], z) + np.array([q.start for q in bb])
        plan.append(('SN', 'LCx', junction(lcx, z, arc(lcx, z, seeds), 8)))
    geo = []
    for c, host, j in plan:
        p0 = j * z
        u = unit(rng, cen - p0)
        L = float(rng.uniform(*sc['L']))
        r = float(rng.uniform(0.5, 0.8))
        ov = float(rng.uniform(*sc['ov']))
        gap = float(rng.uniform(*sc['gap'])) if rng.random() < sc['p_gap'] else 0.0
        geo.append({'class': c, 'host': host, 'j': [int(v) for v in j], 'u': u.tolist(), 'L': L, 'r': r, 'ov': ov,
                    'gap': gap})
    return raw.shape, z, ch, geo, aff


def draw(shape, z, ch, geo, rng, q, shorten=(0.0, 0.0), rjit=0.0):
    out = {n: m.copy() for n, m in ch.items()}
    for n in F.STAGE2_NAMES:
        out[n] = np.zeros(shape, bool)
    truth = []
    for g in geo:
        omitted = bool(rng.random() < q)
        rec = dict(g, omitted=omitted)
        if not omitted:
            p0, u = np.array(g['j']) * z, np.array(g['u'])
            L = max(g['L'] - float(rng.uniform(*shorten)), 6.0)
            r = max(g['r'] + float(rng.uniform(-rjit, rjit)), 0.45)
            if g['gap'] > 0:
                cut = L / 3
                m = tube(shape, z, p0, u, 0, cut, r) | tube(shape, z, p0, u, cut + g['gap'], cut + g['gap'] + L / 2, r)
            else:
                m = tube(shape, z, p0, u, 0, L, r)
            host = ch[g['host']]
            ball = tube(shape, z, p0, u, 0.0, 0.0, max(g['ov'] / 2, 1e-3))   # a ball of radius ov/2 at the junction
            m |= ball & host                                  # the ostium drawn over its parent (D47 Q4)
            out[g['class']] |= m
            rec['L_drawn'], rec['r_drawn'], rec['vox'] = L, r, int(m.sum())
        truth.append(rec)
    return out, truth


def far_truth(out, z):
    """Independent truth for the band and L2d: k-d-tree distances."""
    t = {}
    lab = F.labels_d54(out)
    fg = (lab > 0) & (lab != F.IGNORE)
    for c in F.STAGE2_NAMES:
        m = lab == F.V[c]
        if not m.any():
            continue
        comp, nc = ndi.label(m, J.S26)
        gaps = []
        for i in range(1, nc + 1):
            ci = comp == i
            if ci.sum() < J.MIN_PIECE_VOX:
                continue
            rest = np.argwhere(fg & ~ci)
            gaps.append(float(cKDTree(rest * z).query(np.argwhere(ci) * z)[0].min()))
        t[c] = {'gaps': gaps}
    return t


def write_read(root, name, out, affine, info):
    d = os.path.join(root, name, 'segmentations')
    os.makedirs(d, exist_ok=True)
    shape = next(iter(out.values())).shape
    for n in ALL21:
        m = out.get(n, np.zeros(shape, bool))
        nb.save(nb.Nifti1Image(m.astype(np.uint8), affine), os.path.join(d, n.replace(' ', '_') + '.nii.gz'))
    json.dump(info, open(os.path.join(root, name, 'read.json'), 'w'), indent=1, sort_keys=True)


def main(icx, outroot, scen, n_pairs=12):
    sc = SCEN[scen]
    ids = json.load(open(os.path.join(icx, 'ids.json')))
    os.makedirs(outroot, exist_ok=True)
    truth = {'scenario': scen, 'params': sc, 'reads': {}}
    for k, cid in enumerate(ids):
        seed = int(hashlib.sha256(f'{scen}:{cid}'.encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        path = os.path.join(icx, f'{int(cid[1:]) + 1}.coronary.nii.gz')
        shape, z, ch, geo, aff = build_case(path, rng, sc)
        name = f'Standin{"ABCD"[k % 4]}__p{k:04d}'
        reads = [(name, sc['q1'], (0.0, 0.0), 0.0)]
        if k < n_pairs:
            reads.append((name + '__r2', sc['q2'], (0.0, 4.0), 0.1))
        for rn, q, sh, rj in reads:
            out, tr = draw(shape, z, ch, geo, rng, q, sh, rj)
            if k == 1 and rn == name:
                out['Calcified plaque'] = ndi.binary_dilation(ch['LAD'], iterations=1) & ~ch['LAD']
                out['Calcified plaque'][:, :, : shape[2] // 2] = False
            info = {'classes': ALL21, 'extended': True, 'written': 'read', 'exportedRole': 'annotator',
                    'completeGroups': ['LAD branches'] if k % 2 else None, 'defect': (k == 3 and rn == name)}
            write_read(outroot, rn, out, aff, info)
            truth['reads'][rn] = {'case': cid, 'zooms': z.tolist(), 'tubes': tr, 'far': far_truth(out, z),
                                  'defect': info['defect']}
        print(k, name, flush=True)
    man = {'version': 1, 'source': {'kind': 'segqueue14-export', 'classes': 'read', 'replicas': 'all',
                                    'pool_seal': {'mode': 'exclude', 'sha256': 'stand-in'}}, 'cases': []}
    json.dump(man, open(os.path.join(outroot, 'manifest.json'), 'w'), indent=1)
    json.dump(truth, open(os.path.join(os.path.dirname(os.path.abspath(outroot)),
                                       os.path.basename(os.path.normpath(outroot)) + '_truth.json'), 'w'))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 12)
