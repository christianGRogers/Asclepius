"""Round 8: miss census on run 1's 80 val segmentations (Round 6 §2C, approved), plus the two pending
A1c checks for tf1 sha 9bb77e24 (Round 7 tests 3 and 8).

Per case (reference = Atlas's proxy, rebuilt with its own make_label; ostium = A1 aorta rule with the
atlas2 TotalSegmentator aorta; prediction = run 1's exported segmentation):
  * score with segtrain.tf1 (new hash) and compare per_class with atlas2's per_case_run1.json, which
    was scored with the old hash 3c737cbc (test 3: bit-identical, field lists exactly the 7 cases);
  * where a class has no centreline, also score with fallback_centreline=True (test 8, paired);
  * census: replicate tree_f1's recall/precision per centreline voxel (asserted equal to the
    module's numbers) and attribute every lost reference-centreline voxel of class c to
        absent        no predicted voxel there
        misnamed      predicted, other class
        disconnected  predicted class c but its piece does not reach an ostium
    and every predicted class-c centreline voxel outside reference class c to
        outside_ref   outside the reference mask (extra_icx if within 1 mm of ImageCAS-X vessel)
        other_class   inside the reference, another class
    with radius (reference EDT), geodesic distance from the ostium along the reference centreline,
    whether ImageCAS-X traces it (within 1 mm), and distance to the nearest predicted voxel.
Usage: python r8_miss_census.py <out.jsonl> case [case ...]"""
import glob
import json
import sys

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import r5_cut_anatomy as M  # noqa: E402
from segtrain import tf1 as T  # noqa: E402

SCR = M.SCR
PRED = glob.glob(f'{SCR}/round6/atlas/nnunet_results/*/*/fold_0/validation')[0]
AORTA = f'{SCR}/round6/atlas2/aorta'
OLD = {x['case']: x for x in json.load(open(
    '/home/user/Asclepius/trillium-results/round6/atlas2/results/per_case_run1.json'))}
MARGIN_MM = 15.0
R_BINS = (0.75, 1.0, 1.5)        # mm
G_BINS = (20.0, 60.0, 100.0)     # mm from the ostium


def _bin(v, edges):
    return int(np.searchsorted(edges, v, side='right'))


def run(case):
    mpath = f'{SCR}/data/masks/{case}.nii.gz'
    L, _, _ = M.AP.make_label(mpath, M.T.icx_path(case))
    sp = np.array(nib.load(mpath).header.get_zooms()[:3], float)
    P = np.asarray(nib.load(f'{PRED}/{case}.nii.gz').dataobj).astype(np.uint8)
    ao = np.asarray(nib.load(f'{AORTA}/{case}_aorta.nii.gz').dataobj) > 0
    raw = np.asarray(nib.load(M.T.icx_path(case)).dataobj).astype(np.uint8)
    if P.shape != L.shape or ao.shape != L.shape:
        raise ValueError(f'grid mismatch {P.shape} {ao.shape} {L.shape}')
    u = (L > 0) | (P > 0) | ao
    idx = [np.nonzero(u.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
    mv = np.ceil(MARGIN_MM / sp).astype(int)
    lo = np.maximum([a[0] for a in idx] - mv, 0)
    hi = np.minimum([a[-1] + 1 for a in idx] + mv, L.shape)
    sl = tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))
    R, P, ao, icx = L[sl].copy(), P[sl].copy(), ao[sl].copy(), raw[sl] > 0
    del L, raw
    rep = T.find_ostia(R, sp, aorta=ao)
    res = T.tree_f1(R, P, sp, ostia=rep)
    old = OLD[case]['per_class']
    out = dict(case=case, identical_to_atlas2=({int(k): v for k, v in old.items()} == res.per_class),
               missing=res.classes_without_centreline, tf1=res.tf1,
               per_class={int(k): v for k, v in res.per_class.items()},
               flagged_classes=OLD[case]['flagged_classes'])
    if res.classes_without_centreline:
        fb = T.tree_f1(R, P, sp, ostia=rep, fallback_centreline=True)
        out['fallback'] = dict(tf1=fb.tf1, per_class={int(k): v for k, v in fb.per_class.items()})
    # ---- replicate tree_f1 per voxel (same steps as the module)
    pred = np.where(T.remove_small_components(P > 0, T.MIN_COMPONENT_VOXELS), P, 0)
    cl = T._Centreline(R > 0, sp)
    pm = pred > 0
    grown = ndi.binary_dilation(pm, structure=T._ball(T.TOLERANCE_MM / 2.0, sp)) if pm.any() else pm
    gl, _ = T.components(grown)
    cop = np.where(pm, gl, 0)
    reach = max(T.TOLERANCE_MM, float(sp.max()))
    rr = np.ceil(reach / sp).astype(int)
    rooted_comps = set()
    for p in rep.points:
        win = tuple(slice(max(p[k] - rr[k], 0), min(p[k] + rr[k] + 1, R.shape[k])) for k in range(3))
        sub = cop[win]
        g = np.argwhere(sub > 0)
        if len(g):
            off = np.array([s.start for s in win])
            d = np.linalg.norm((g + off - np.array(p)) * sp, axis=1)
            rooted_comps |= set(sub[tuple(g[d <= reach].T)].tolist())
    pts = cl.pts
    rl, pl = R[tuple(pts.T)], pred[tuple(pts.T)]
    rooted = np.isin(cop[tuple(pts.T)], list(rooted_comps)) if rooted_comps else np.zeros(len(pts), bool)
    psk = T._skeletonise(pm)
    ppts = np.argwhere(psk)
    ppl, prl = pred[tuple(ppts.T)], R[tuple(ppts.T)]
    # geodesic distance from the ostia along the reference centreline
    n = len(pts)
    src = np.repeat(np.arange(n), np.diff(cl._start))
    w = np.linalg.norm((pts[src] - pts[cl._dst]) * sp, axis=1)
    G = csr_matrix((w, (src, cl._dst)), shape=(n, n))
    index = {tuple(q): i for i, q in enumerate(map(tuple, pts))}
    srcs = [index[tuple(p)] for p in rep.points if tuple(p) in index]
    geo = dijkstra(G, indices=srcs, min_only=True) if srcs else np.full(n, np.inf)
    d_icx = ndi.distance_transform_edt(~icx, sampling=sp)
    d_pred = ndi.distance_transform_edt(~pm, sampling=sp) if pm.any() else np.full(R.shape, np.inf)
    rad = cl.radius
    census = {}
    for c in T.CLASSES:
        g = rl == c
        if not g.any():
            continue
        ok = (pl == c) & rooted & g
        rec = float(ok.sum() / g.sum())
        pc = ppl == c
        prec = float((prl[pc] == c).mean()) if pc.any() else 0.0
        assert abs(rec - res.recall[c]) < 1e-12 and abs(prec - res.precision[c]) < 1e-12, (case, c)
        lost = g & ~ok
        kind = np.where(pl == 0, 'absent', np.where(pl != c, 'misnamed', 'disconnected'))
        rows = {}
        for i in np.nonzero(lost)[0]:
            key = (kind[i], _bin(rad[i], R_BINS), _bin(geo[i], G_BINS),
                   bool(d_icx[tuple(pts[i])] <= 1.0))
            rows[key] = rows.get(key, 0) + 1
        fp = pc & (prl != c)
        fkind = np.where(prl[fp] == 0, np.where(d_icx[tuple(ppts[fp].T)] <= 1.0, 'extra_icx', 'outside_ref'),
                         'other_class')
        census[c] = dict(n_ref=int(g.sum()), n_lost=int(lost.sum()), recall=rec,
                         n_pred=int(pc.sum()), n_fp=int(fp.sum()), precision=prec,
                         lost=[[k[0], k[1], k[2], k[3], v] for k, v in rows.items()],
                         fp={k: int((fkind == k).sum()) for k in ('outside_ref', 'extra_icx', 'other_class')},
                         lost_dist_to_pred_mm=np.percentile(d_pred[tuple(pts[lost].T)], [25, 50, 75]).round(2).tolist()
                         if lost.any() else None,
                         ref_icx_frac=float((d_icx[tuple(pts[g].T)] <= 1.0).mean()))
    out['census'] = {int(k): v for k, v in census.items()}
    return out


if __name__ == '__main__':
    with open(sys.argv[1], 'a') as fh:
        for c in sys.argv[2:]:
            try:
                r = run(c)
            except Exception as e:  # noqa
                r = dict(case=c, error=repr(e))
            fh.write(json.dumps(r) + '\n')
            fh.flush()
            print(c, r.get('error', ''), flush=True)
