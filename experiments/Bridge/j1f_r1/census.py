"""Janus 1-F, Round 1 (Bridge): per-case geometry of ImageCAS-X's 14 classes on the 620 Janus 1 training cases.

Reads ONLY the 620 training cases of D45 (split.json from split620.py); never a locked-100, sealed or quality-0 case.
For each case and class it records:
  * present, voxels, volume (mm^3), connected components (26-conn);
  * skeleton length (mm) and lumen diameter along the skeleton (2 x the distance transform, mm; median and 10th pct);
  * for every side-branch class (D1, D2, OM1, OM2, IM, R-PDA, R-PLA, L-PDA, L-PLA) and every component of "Other":
    the parent class it touches, and its ORIGIN as geodesic distance (mm) along the parent from the parent's
    proximal end (the voxels touching LM, or for the RCA its point farthest from its own distal end).
That is enough to answer: how often "Other" holds a D3 (a third LAD-side branch), whether D1/D2 and OM1/OM2 are
ordered by origin along the parent (ordinal names are a function of type + position), dominance counts, and the
calibre of the thinnest traced branches against the 0.5 mm grid.
Usage: census.py <icx_dir> <out.jsonl> [n_proc]"""
import json, os, sys
from multiprocessing import Pool
import numpy as np, nibabel as nib, cc3d
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
from skimage.graph import MCP_Geometric

NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'D1', 5: 'D2', 6: 'OM1', 7: 'OM2', 8: 'IM', 9: 'RCA', 10: 'R-PDA',
         11: 'R-PLA', 12: 'L-PDA', 13: 'L-PLA', 14: 'Other'}
BRANCH = [4, 5, 6, 7, 8, 10, 11, 12, 13]
PARENTS = [2, 3, 9]          # LAD, LCx, RCA
ST = ndi.generate_binary_structure(3, 3)


def crop(m, pad=2):
    nz = np.argwhere(m)
    lo, hi = np.maximum(nz.min(0) - pad, 0), nz.max(0) + pad + 1
    return tuple(slice(a, b) for a, b in zip(lo, hi))


def skel_stats(m, z):
    if m.sum() < 3:
        return dict(len_mm=0.0, d_med=None, d_p10=None)
    m = m[crop(m)]
    sk = skeletonize(m)
    edt = ndi.distance_transform_edt(m, sampling=z)
    d = 2 * edt[sk > 0]
    n = int((sk > 0).sum())
    if n == 0:
        return dict(len_mm=0.0, d_med=None, d_p10=None)
    return dict(len_mm=round(n * float(np.mean(z)), 1), d_med=round(float(np.median(d)), 2),
                d_p10=round(float(np.percentile(d, 10)), 2))


def geodesic_from(mask, seeds, z):
    sl = crop(mask, 1)
    lo = np.array([s.start for s in sl])
    cost = np.where(mask[sl], 1.0, np.inf)
    mcp = MCP_Geometric(cost, sampling=tuple(z))
    d, _ = mcp.find_costs([tuple(np.asarray(s) - lo) for s in seeds])
    dist = np.full(mask.shape, np.inf)
    dist[sl] = d
    return dist


def one(args):
    icx, c = args
    img = nib.load(os.path.join(icx, 'segmentations', f'{int(c[1:]) + 1}.coronary.nii.gz'))
    lab = np.asarray(img.dataobj).astype(np.uint8)
    z = np.array(img.header.get_zooms()[:3], float)
    nz = np.argwhere(lab > 0)
    lo, hi = np.maximum(nz.min(0) - 2, 0), nz.max(0) + 3
    lab = lab[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    out = dict(case=c, spacing=[round(float(v), 3) for v in z], classes={}, branches=[])
    vv = float(np.prod(z))
    for k, n in NAMES.items():
        m = lab == k
        if not m.any():
            continue
        cc, nc = cc3d.connected_components(m.astype(np.uint8), connectivity=26, return_N=True)
        out['classes'][n] = dict(vox=int(m.sum()), mm3=round(m.sum() * vv, 1), comps=int(nc), **skel_stats(m, z))
    # proximal ends of the parents
    geo = {}
    for p in PARENTS:
        pm = lab == p
        if not pm.any():
            continue
        if p in (2, 3):
            lm = lab == 1
            touch = np.zeros_like(pm)
            if lm.any():
                sl = crop(lm, 2)
                touch[sl] = pm[sl] & ndi.binary_dilation(lm[sl], ST)
            if not touch.any():          # no LM drawn: the parent voxel nearest the other left parent
                other = lab == (3 if p == 2 else 2)
                if other.any():
                    d = ndi.distance_transform_edt(~other, sampling=z)
                    touch = pm & (d <= d[pm].min() + 1e-6)
                else:
                    touch = None
            seeds = np.argwhere(touch) if touch is not None else None
        else:
            seeds = None
        if seeds is None or len(seeds) == 0:
            # endpoint-to-endpoint: farthest from an arbitrary voxel, then the farther end of the two is unknown;
            # for the RCA use the end farthest from its R-PDA/R-PLA (its distal end), else the most cranial voxel
            pts = np.argwhere(pm)
            dist0 = geodesic_from(pm, [pts[0]], z)
            e1 = np.unravel_index(np.where(np.isfinite(dist0), dist0, -1).argmax(), pm.shape)
            dist1 = geodesic_from(pm, [e1], z)
            e2 = np.unravel_index(np.where(np.isfinite(dist1), dist1, -1).argmax(), pm.shape)
            distal = (lab == 10) | (lab == 11)
            if distal.any():
                dd = ndi.distance_transform_edt(~distal, sampling=z)
                prox = e1 if dd[e1] > dd[e2] else e2
            else:
                prox = e1
            seeds = [prox]
        geo[p] = geodesic_from(pm, seeds, z)
        out['classes'][NAMES[p]]['geo_len_mm'] = round(float(np.nanmax(np.where(np.isfinite(geo[p]), geo[p], np.nan))), 1)
    # side branches and Other components: parent and origin
    items = [(k, None) for k in BRANCH if (lab == k).any()]
    if (lab == 14).any():
        cc, nc = cc3d.connected_components((lab == 14).astype(np.uint8), connectivity=26, return_N=True)
        items += [(14, j) for j in range(1, nc + 1)]
    for k, j in items:
        m = (lab == k) if j is None else (cc == j)
        sl = crop(m, 2)
        ms, ls = m[sl], lab[sl]
        dil = ndi.binary_dilation(ms, ST)
        ring = dil & ~ms
        nb = np.bincount(ls[ring], minlength=15)
        nb[0] = 0
        nb[k] = 0
        touch = {NAMES[i]: int(nb[i]) for i in np.nonzero(nb)[0]}
        par = None
        for p in PARENTS:
            if nb[p] > 0 and (par is None or nb[p] > nb[par]):
                par = p
        origin = None
        if par is not None and par in geo:
            contact = dil & (ls == par)
            g = geo[par][sl][contact]
            g = g[np.isfinite(g)]
            origin = round(float(g.min()), 1) if len(g) else None
        out['branches'].append(dict(cls=NAMES[k], comp=j, vox=int(m.sum()), mm3=round(m.sum() * vv, 1),
                                    parent=NAMES[par] if par else None, origin_mm=origin, touch=touch,
                                    **skel_stats(m, z)))
    return out


if __name__ == '__main__':
    icx, outp = sys.argv[1], sys.argv[2]
    npr = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    sp = json.load(open(os.path.join(icx, 'split.json')))
    cases = sp['train620']
    assert len(cases) == 620 and not set(cases) & set(sp['locked100'])
    done = set()
    if os.path.exists(outp):
        done = {json.loads(l)['case'] for l in open(outp)}
    todo = [(icx, c) for c in cases if c not in done]
    with Pool(npr) as p, open(outp, 'a') as f:
        for i, r in enumerate(p.imap_unordered(one, todo)):
            f.write(json.dumps(r) + '\n'); f.flush()
            if i % 50 == 0:
                print(i, len(todo), flush=True)
    print('done')
