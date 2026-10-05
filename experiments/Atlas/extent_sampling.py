"""Tree/branch extents vs nnU-Net patch sizes, and patch-sampling statistics, on ImageCAS-X labels mapped to
the project's 4 classes (trunk mapping LM=1,LAD=2,LCx=3,RCA=9; side branches -> background) for ALL available
ImageCAS-X cases. Works on a 2 mm presence grid (max-pool), so it is fast.
Patch geometries (mm, nibabel x,y,z order) come from planner_sweep.py output.
Usage: extent_sampling.py <out.jsonl> [reverse | @idlist]"""
import os, sys, glob, json
import numpy as np, nibabel as nib
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
W = SCR + '/work/Atlas'
out = sys.argv[1]
TRUNK = {1: 1, 2: 2, 3: 3, 9: 4}; NAMES = ['LM', 'LAD', 'LCx', 'RCA']
LEFT = [1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14]; RIGHT = [9, 10, 11]
G = 2.0  # mm grid
PATCHES = {  # x, y, z in mm
    'plainL_native_7.3M': (78.3, 89.5, 64.0),       # ResEncL / plain 24GB native: [128,256,224] zyx
    'plain70_native_19.7M': (111.9, 111.9, 96.0),   # plain 70GB native: [192,320,320]
    'resenc75_native_22.9M': (111.9, 111.9, 112.0), # ResEnc 75GB native: [224,320,320]
    'iso05_70_16.8M': (128.0, 128.0, 128.0),        # 0.5 mm iso, 256^3
    'iso05_XL_12.6M': (128.0, 128.0, 96.0),         # fallback: ResEnc XL preset at 0.5 mm, [192,256,256] zyx
}
done = set()
if os.path.exists(out): done = {json.loads(l)['icx_id'] for l in open(out)}

def pool(m, sp):
    f = np.maximum(np.round(G / np.array(sp)).astype(int), 1)
    sh = [int(np.ceil(s / k)) * k for s, k in zip(m.shape, f)]
    p = np.zeros(sh, bool); p[:m.shape[0], :m.shape[1], :m.shape[2]] = m
    return p.reshape(sh[0] // f[0], f[0], sh[1] // f[1], f[1], sh[2] // f[2], f[2]).any((1, 3, 5)), f * np.array(sp)

def boxsum(a, k):
    """sum of a over a box of size k (cells) whose lower corner is at each valid position -> via cumsum"""
    c = np.pad(a.astype(np.int64), [(1, 0)] * 3).cumsum(0).cumsum(1).cumsum(2)
    X, Y, Z = [a.shape[i] - k[i] + 1 for i in range(3)]
    if min(X, Y, Z) <= 0: return None
    kx, ky, kz = k
    return (c[kx:kx + X, ky:ky + Y, kz:kz + Z] - c[:X, ky:ky + Y, kz:kz + Z] - c[kx:kx + X, :Y, kz:kz + Z] - c[kx:kx + X, ky:ky + Y, :Z]
            + c[:X, :Y, kz:kz + Z] + c[:X, ky:ky + Y, :Z] + c[kx:kx + X, :Y, :Z] - c[:X, :Y, :Z])

files = sorted(glob.glob(W + '/icx/*.coronary.nii.gz'), key=lambda p: int(os.path.basename(p).split('.')[0]))
if len(sys.argv) > 2 and sys.argv[2] == 'reverse': files = files[::-1]  # second worker walks from the other end
if len(sys.argv) > 2 and sys.argv[2].startswith('@'):  # explicit id list file (one ImageCAS-X id per line)
    keep = set(int(x) for x in open(sys.argv[2][1:]).read().split())
    files = [f for f in files if int(os.path.basename(f).split('.')[0]) in keep]
with open(out, 'a') as fo:
    for p in files:
        i = int(os.path.basename(p).split('.')[0])
        if i in done: continue
        try:
            img = nib.load(p); lab = np.asarray(img.dataobj).astype(np.uint8)
        except Exception:
            continue
        sp = np.array(img.header.get_zooms()[:3], float)
        r = dict(icx_id=i, case='c%04d' % (i - 1), sp=sp.tolist(), shape=list(lab.shape))
        f = np.maximum(np.round(G / sp).astype(int), 1)
        idx = np.nonzero(lab)
        lo0 = np.array([ix.min() for ix in idx]) // f * f; hi0 = np.array([ix.max() + 1 for ix in idx])
        full_shape = lab.shape
        lab = lab[lo0[0]:hi0[0], lo0[1]:hi0[1], lo0[2]:hi0[2]]
        masks = {nm: lab == k for nm, k in zip(NAMES, [1, 2, 3, 9])}
        masks['left'] = np.isin(lab, LEFT); masks['right'] = np.isin(lab, RIGHT); masks['all'] = lab > 0
        masks['left_trunk'] = np.isin(lab, [1, 2, 3])
        r['vox'] = {k: int(v.sum()) for k, v in masks.items()}
        r['ext_mm'] = {}
        for k, v in masks.items():
            idx = np.nonzero(v)
            r['ext_mm'][k] = None if len(idx[0]) == 0 else [float((idx[a].max() - idx[a].min() + 1) * sp[a]) for a in range(3)]
        # coarse grids
        P = {}
        gshape = [int(np.ceil(full_shape[a] / f[a])) for a in range(3)]
        for k in NAMES + ['left', 'right', 'all']:
            pc, cell = pool(masks[k], sp)
            g = np.zeros(gshape, bool); o = lo0 // f
            g[o[0]:o[0] + pc.shape[0], o[1]:o[1] + pc.shape[1], o[2]:o[2] + pc.shape[2]] = pc
            P[k] = g
        r['cell_mm'] = cell.tolist()
        r['samp'] = {}
        for pn, pmm in PATCHES.items():
            # a patch larger than the image along an axis is padded by nnU-Net -> equivalent to clamping to the image
            k = [min(max(int(round(pmm[a] / cell[a])), 1), P['all'].shape[a]) for a in range(3)]
            # nnU-Net pads the image so a random patch can extend half a patch beyond the border; we ignore padding
            # (conservative: only fully-inside positions) -- valid lower corners on the coarse grid
            d = {}
            tot = {c: P[c].sum() for c in P}
            sums = {c: boxsum(P[c], k) for c in P}
            if sums['all'] is None: r['samp'][pn] = None; continue
            nvalid = sums['all'].size
            # P(random patch contains class c)
            d['p_contains_random'] = {c: float((sums[c] > 0).mean()) for c in NAMES}
            # whole-tree-in-one-patch: does any position contain ALL of the class's cells?
            d['fits'] = {c: bool((sums[c] == tot[c]).any()) if tot[c] else None for c in NAMES + ['left', 'right', 'all']}
            # best-case fraction of the class captured by one patch
            d['best_frac'] = {c: float(sums[c].max() / tot[c]) if tot[c] else None for c in ['left', 'right', 'all']}
            # anchored on class a, nnU-Net-faithful: foreground patches are CENTRED on a random voxel of the class,
            # lower corner clamped at 0 (approx.: nnU-Net allows a small negative pad), upper side may overhang the
            # image (zero padding). Average over a's cells of P(patch contains >=1 cell of class b).
            half = [kk // 2 for kk in k]
            anch, anch_clamped = {}, {}
            spad = {c: boxsum(np.pad(P[c], [(0, kk) for kk in k]), k) for c in NAMES}
            for a in NAMES:
                ia = np.argwhere(P[a])
                if len(ia) == 0: continue
                lo = np.maximum(ia - half, 0)
                anch[a] = {b: float((spad[b][lo[:, 0], lo[:, 1], lo[:, 2]] > 0).mean()) for b in NAMES}
                loc = np.clip(ia - half, 0, np.array(sums['all'].shape) - 1)
                anch_clamped[a] = {b: float((sums[b][loc[:, 0], loc[:, 1], loc[:, 2]] > 0).mean()) for b in NAMES}
            d['p_contains_anchored_clamped'] = anch_clamped
            d['p_contains_anchored'] = anch
            r['samp'][pn] = d
        fo.write(json.dumps(r) + '\n'); fo.flush()
print('done')
