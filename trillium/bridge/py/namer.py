"""Stage-2 namer as a function: binary mask (any grid crop) -> 4-class label map.
Wraps the frozen labeller in label.py (skeleton graph, learned ostium, plausibility re-rank, AP split,
subtree inheritance, optional gap bridging for naming).

    from namer import name_mask, load_ostium
    lab, info = name_mask(mask_bool, affine_of_crop, zooms, full_shape=None, lo=(0,0,0))
"""
import json, os, sys
import numpy as np, cc3d, kimimaro
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import label as Lb

MINCOMP = 100


def load_ostium(path):
    w = json.load(open(path))
    Lb.OSTIUM_W = dict(F=w['F'], mean=np.array(w['mean']), scale=np.array(w['scale']), coef=np.array(w['coef']))


def skeleton_case(m, A_full, z, lo, full_shape, cnt_lab=None):
    """build the cached-case dict label.py expects. m: bool crop; lo: crop offset in the full grid.
    cnt_lab (optional uint8 crop, 0..7): per-voxel reference class for scoring counts."""
    z = np.asarray(z, float)
    comp, n = cc3d.connected_components(m.astype(np.uint8), connectivity=26, return_N=True)
    sizes = np.bincount(comp.ravel(), minlength=n + 1)
    big = [k for k in range(1, n + 1) if sizes[k] >= MINCOMP]
    sks = kimimaro.skeletonize(np.where(np.isin(comp, big), comp, 0).astype(np.uint32),
                               teasar_params={'scale': 1.5, 'const': 2, 'pdrf_scale': 100000, 'pdrf_exponent': 4},
                               anisotropy=tuple(z), dust_threshold=MINCOMP, fix_branching=True,
                               progress=False, parallel=1)
    V, E, R, CID, CNT, assign = [], [], [], [], [], {}
    off = 0
    for k, sk in sks.items():
        nv = len(sk.vertices)
        idx = np.argwhere(comp == k)
        _, j = cKDTree(sk.vertices).query(idx * z)
        cnt = np.zeros((nv, 9), np.int64)
        np.add.at(cnt[:, 8], j, 1)
        if cnt_lab is not None:
            np.add.at(cnt, (j, cnt_lab[tuple(idx.T)]), 1)
        V.append(sk.vertices / z + lo); E.append(sk.edges + off); R.append(sk.radius)
        CID.append(np.full(nv, k)); CNT.append(cnt); assign[k] = (idx, j + off)
        off += nv
    orph, orph_idx = [], []
    for k in range(1, n + 1):
        if k in sks:
            continue
        idx = np.argwhere(comp == k)
        oc = np.bincount(cnt_lab[tuple(idx.T)], minlength=8)[:8] if cnt_lab is not None else np.zeros(8)
        orph.append([*(idx.mean(0) + lo), len(idx)] + list(oc)); orph_idx.append(idx)
    if not V:
        return None, None, None
    d = dict(V=np.concatenate(V).astype(np.float32), E=np.concatenate(E).astype(np.int32),
             R=np.concatenate(R).astype(np.float32), CID=np.concatenate(CID).astype(np.int32),
             CNT=np.concatenate(CNT), ORPH=np.array(orph, np.float32).reshape(-1, 12),
             A=A_full, zooms=z, shape=np.asarray(full_shape), comp_sizes=np.sort(sizes[1:])[::-1], ncomp6=0,
             icx_stats=None)
    d['P'] = d['V'] * z
    d['RAS'] = d['V'] @ A_full[:3, :3].T + A_full[:3, 3]
    return d, assign, orph_idx


def name_mask(m, A_full, z, lo, full_shape, method='rerank_learned', bridge=4.0, cnt_lab=None, cached=None):
    """cached: (d, assign, orph_idx) from skeleton_case, to name the same mask several times (e.g. ramus modes)"""
    Lb.BRIDGE = bridge
    d, assign, orph_idx = cached if cached is not None else skeleton_case(m, A_full, z, lo, full_shape, cnt_lab)
    out = np.zeros(m.shape, np.uint8)
    if d is None:
        return out, dict(fail='empty'), None
    lab, olab, res, ef = Lb.label_case(d, method)
    for k, (idx, j) in assign.items():
        out[tuple(idx.T)] = lab[j]
    for i, idx in enumerate(orph_idx):
        out[tuple(idx.T)] = olab[i] if len(olab) > i else 0
    return out, res, (d, assign, orph_idx)
