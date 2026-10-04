"""Pass 1 (expensive, once per case): binary mask -> components -> TEASAR skeleton per component,
and every mask voxel assigned to its nearest skeleton vertex in the same component.
If ImageCAS-X labels exist for the case, each mask voxel also gets the ImageCAS-X class of the nearest
ImageCAS-X voxel (only if within 2 mm; else 'far'), and we store per-vertex counts per class.
Everything a branch labeller needs, and everything needed to score it voxel-wise, is then in a ~100 kB npz,
so labelling rules can be iterated on all cases in minutes (pass 2: label.py).

usage: extract.py OUTDIR SHARD NSHARDS [--icxmap map.json] [--cases a,b,c]
"""
import sys, os, json, time, argparse
import numpy as np, nibabel as nib, cc3d, kimimaro
from scipy.spatial import cKDTree
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools'); from girder import case_ids, mask_path

# ImageCAS-X 14 classes -> 0 bg, 1 LM, 2 LAD(+D1,D2), 3 LCx(+OM1,OM2,L-PDA,L-PLA), 4 RCA(+R-PDA,R-PLA), 5 IM, 6 Other(D3/D4/OM3/OM4)
ICX4 = np.array([0, 1, 2, 3, 2, 2, 3, 3, 5, 4, 4, 4, 3, 3, 6], np.uint8)
MINCOMP = 100

ap = argparse.ArgumentParser()
ap.add_argument('out'); ap.add_argument('shard', type=int); ap.add_argument('ns', type=int)
ap.add_argument('--icxmap'); ap.add_argument('--cases')
a = ap.parse_args()
cases = (a.cases.split(',') if a.cases else case_ids())[a.shard::a.ns]
icxmap = json.load(open(a.icxmap)) if a.icxmap else {}
os.makedirs(a.out, exist_ok=True)
for c in cases:
    dest = os.path.join(a.out, c + '.npz')
    if os.path.exists(dest):
        continue
    t = time.time()
    im = nib.load(mask_path(c)); A = im.affine; z = np.asarray(im.header.get_zooms(), float)
    m = (np.asarray(im.dataobj) > 0.5)
    shape = np.array(m.shape)
    nz = np.argwhere(m)
    lo = np.maximum(nz.min(0) - 3, 0); hi = np.minimum(nz.max(0) + 4, m.shape)
    mc = m[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]].astype(np.uint8)
    comp, n = cc3d.connected_components(mc, connectivity=26, return_N=True)
    sizes = np.bincount(comp.ravel())
    big = [k for k in range(1, n + 1) if sizes[k] >= MINCOMP]
    sks = kimimaro.skeletonize(np.where(np.isin(comp, big), comp, 0).astype(np.uint32),
                               teasar_params={'scale': 1.5, 'const': 2, 'pdrf_scale': 100000, 'pdrf_exponent': 4},
                               anisotropy=tuple(z), dust_threshold=MINCOMP, fix_branching=True,
                               progress=False, parallel=1)
    # ICX projection
    icx_lab = None
    key = icxmap.get(c)
    if key is not None and os.path.exists(key[1]):
        g = np.asarray(nib.load(key[1]).dataobj)
        gfull = (g > 0).sum()
        gc = ICX4[np.clip(g[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]], 0, 14)]
        gi = np.argwhere(gc > 0)
        oi = np.argwhere(mc > 0)
        d, j = cKDTree(gi * z).query(oi * z)
        icx_lab = np.where(d <= 2.0, gc[tuple(gi[j].T)], 7).astype(np.uint8)  # 7 = no ICX vessel within 2 mm
        icx_stats = dict(icx=key[0], icx_nvox=int(gfull), icx_in_crop=int(len(gi)),
                         icx_in_ours=int((mc[tuple(gi.T)] > 0).sum()), ours_nvox=int(len(oi)),
                         ours_near=int((d <= 2.0).sum()))
        lab_vol = np.zeros(mc.shape, np.uint8); lab_vol[tuple(oi.T)] = icx_lab
        # ICX voxels that are NOT in our mask, per class (what our binary mask misses)
        miss = gc[tuple(gi.T)][mc[tuple(gi.T)] == 0]
        icx_stats['icx_missed_by_ours'] = np.bincount(miss, minlength=7).tolist()
        icx_stats['icx_class_vox'] = np.bincount(gc[tuple(gi.T)], minlength=7).tolist()
    V, E, R, CID, CNT = [], [], [], [], []
    off = 0
    for k, sk in sks.items():
        nv = len(sk.vertices)
        idx = np.argwhere(comp == k)
        _, j = cKDTree(sk.vertices).query(idx * z)
        cnt = np.zeros((nv, 9), np.int32)  # col 0..7 ICX class (7=far), col 8 total voxels
        np.add.at(cnt[:, 8], j, 1)
        if icx_lab is not None:
            np.add.at(cnt, (j, lab_vol[tuple(idx.T)]), 1)
        V.append(sk.vertices / z + lo)  # voxel coordinates in the FULL volume
        E.append(sk.edges + off); R.append(sk.radius); CID.append(np.full(nv, k)); CNT.append(cnt)
        off += nv
    # orphan components (no skeleton): centroid + size + ICX counts
    orph = []
    for k in range(1, n + 1):
        if k in sks:
            continue
        idx = np.argwhere(comp == k)
        row = [*(idx.mean(0) + lo), len(idx)]
        oc = np.zeros(8, int)
        if icx_lab is not None:
            oc = np.bincount(lab_vol[tuple(idx.T)], minlength=8)[:8]
        orph.append(row + oc.tolist())
    out = dict(V=np.concatenate(V).astype(np.float32), E=np.concatenate(E).astype(np.int32),
               R=np.concatenate(R).astype(np.float32), CID=np.concatenate(CID).astype(np.int32),
               CNT=np.concatenate(CNT), ORPH=np.array(orph, np.float32).reshape(-1, 12),
               A=A, zooms=z, shape=shape, comp_sizes=np.sort(sizes[1:])[::-1], ncomp6=cc3d.connected_components(mc, connectivity=6, return_N=True)[1])
    if icx_lab is not None:
        out['icx_stats'] = json.dumps(icx_stats)
    out['sec'] = time.time() - t
    np.savez_compressed(dest + '.part.npz', **out)
    os.replace(dest + '.part.npz', dest)
