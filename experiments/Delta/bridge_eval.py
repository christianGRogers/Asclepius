"""E10: an *implemented* gap-bridging step on real nnU-Net predictions, with its false connections.

Usage: python bridge_eval.py <pred_dir> <aorta_dir> <out.jsonl> case [case ...]

Prediction: ImageCAS-X's released binary nnU-Net (see nnunet_infer.py), threshold 0.5, components
< 100 voxels removed. 4-class names: each predicted voxel takes the class of the nearest
ImageCAS-X reference voxel ('oracle naming' -- this experiment is about connectivity, not naming).
Ostium (both for the bridging anchors and for scoring): TotalSegmentator aorta where it was run,
else the blood-pool proxy (treelib.blood_pool; validated against ImageCAS-X start points in
ostium_eval.py).
  * anchors for bridging (deployable, no reference used): the 2 largest predicted components with a
    voxel within 3 mm of the anchor structure
  * reference ostia for tree-F1: reference centreline endpoints within 5 mm of the TS aorta, or the
    endpoint nearest the structure per tree (always, for the pool proxy)
Bridging: postproc.bridge with max gap 1.5 / 3 / 5 mm (tube radius 1 voxel).
Scored: tree-F1 (0 mm and 1.5 mm tolerance), rooted recall, Dice, FP components; per bridge: gap,
whether the orphan touched the reference at all (else a false-positive blob was joined), whether
orphan and anchor point belong to different reference trees (left/right cross-join), and how many
tube voxels lie > 1 mm outside the reference lumen.
"""
import json
import sys

import cc3d
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import analyse_preds as A  # noqa: E402
import perturb_metrics as P  # noqa: E402
import postproc  # noqa: E402


def anchor_structure(case, lo, hi, gt, adir):
    """TotalSegmentator aorta if available, else the blood-pool proxy (treelib.blood_pool)."""
    import os
    p = f'{adir}/{case}_aorta.nii.gz'
    if os.path.exists(p):
        return (np.asanyarray(nib.load(p).dataobj) > 0)[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]], 'ts_aorta'
    ct = np.asanyarray(nib.load(P.T.ct_path(case)).dataobj)[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    return P.T.blood_pool(ct, gt.sp, exclude=gt.m), 'pool'


def anchor_components(pred, d_struct, maxd=3.0, keep=2):
    """Deployable anchors: the `keep` largest predicted components with a voxel within maxd mm
    of the anchor structure (aorta / blood pool)."""
    cl = cc3d.connected_components(pred, connectivity=26)
    ids = np.unique(cl[pred & (d_struct <= maxd)]); ids = ids[ids > 0]
    if len(ids) == 0:
        return np.zeros_like(pred)
    sz = np.bincount(cl.ravel())
    ids = sorted(ids, key=lambda k: -sz[k])[:keep]
    return np.isin(cl, ids)


def set_aorta_roots(gt, ao, kind='ts_aorta'):
    d_ao = ndi.distance_transform_edt(~ao, sampling=gt.sp) if ao.any() else None
    deg = np.array([gt.G.degree(i) for i in range(len(gt.pts))])
    roots = []
    for cls in ((1, 2, 3), (4,)):
        ends = np.nonzero(np.isin(gt.lab_sk, cls) & (deg == 1))[0]
        if len(ends) == 0 or d_ao is None:
            continue
        de = d_ao[tuple(gt.pts[ends].T)]
        if kind == 'ts_aorta' and (de <= 5.0).any():
            sel = ends[de <= 5.0]
        else:  # pool proxy contains chambers too: take only the nearest endpoint per tree
            sel = ends[[int(np.argmin(de))]]
        roots += [tuple(gt.pts[v]) for v in sel]
    if roots:
        gt.roots = roots
    return d_ao


def tf1_tol(gt, pred, plab, d):
    inside = pred[tuple(gt.pts.T)]
    dil = ndi.binary_dilation(pred, P.ball(d / 2, gt.sp)) if d > 0 else pred
    dl = cc3d.connected_components(dil, connectivity=26)
    rcs = {dl[rt] for rt in gt.roots if dl[rt] > 0}
    ok = np.isin(dl[tuple(gt.pts.T)], list(rcs)) & inside
    sk = P.T.skeletonise(pred)
    tf = []
    for c in (1, 2, 3, 4):
        g = gt.lab_sk == c
        if not g.any():
            continue
        psk = plab[tuple(gt.pts.T)]
        rec = float((ok & g & (psk == c)).sum() / g.sum())
        pc = plab[sk] == c
        prec = float((gt.lab[sk][pc] == c).mean()) if pc.any() else 0.0
        tf.append(2 * rec * prec / (rec + prec) if rec + prec else 0.0)
    return float(np.mean(tf)), float(ok.mean())


if __name__ == '__main__':
    pdir, adir, out = sys.argv[1:4]
    with open(out, 'a') as f:
        for case in sys.argv[4:]:
            meta = json.load(open(f'{pdir}/{case}_meta.json'))
            lo, hi = meta['lo'], meta['hi']
            prob = np.load(f'{pdir}/{case}_prob.npy').astype(np.float32)
            gt = A.CropGT(case, lo, hi)
            ao, kind = anchor_structure(case, lo, hi, gt, adir)
            d_ao = set_aorta_roots(gt, ao, kind)
            pred = A.remove_small(prob >= 0.5)
            plab = np.where(pred, gt.lab, 0).astype(np.uint8)
            add = pred & (gt.lab == 0)
            if add.any():
                _, inds = ndi.distance_transform_edt(gt.lab == 0, sampling=gt.sp, return_indices=True)
                plab[add] = gt.lab[tuple(inds)][add]
                del inds
            anchors = anchor_components(pred, d_ao) if d_ao is not None else np.zeros_like(pred)
            near_ref = ndi.binary_dilation(gt.m, P.ball(1.0, gt.sp))
            for gap in (0.0, 1.5, 3.0, 5.0):
                if gap == 0:
                    lab2, br = plab, []
                else:
                    lab2, br = postproc.bridge(plab, anchors, gt.sp, max_gap_mm=gap, min_vox=100)
                p2 = lab2 > 0
                # false-connection audit
                cl0 = cc3d.connected_components(pred, connectivity=26)
                for b in br:
                    k = cl0[tuple(b['p'])]
                    comp = cl0 == k if k > 0 else np.zeros_like(pred)
                    b['orphan_touches_ref'] = bool((comp & gt.m).any())
                    # sides from the (oracle) names: RCA = right tree, LM/LAD/LCx = left tree
                    side = lambda c: 2 if c == 4 else (1 if c > 0 else 0)
                    oc = plab[comp]
                    o_side = side(int(np.bincount(oc, minlength=5)[1:].argmax() + 1)) if len(oc) else 0
                    a_side = side(int(plab[tuple(b['q'])]))
                    b['cross_tree'] = bool(o_side and a_side and o_side != a_side)
                tube = p2 & ~pred
                r = dict(case=case, gap=gap, n_bridges=len(br),
                         bridges=[{k: b[k] for k in ('gap_mm', 'comp_vox', 'cls', 'added_vox',
                                                       'orphan_touches_ref', 'cross_tree')} for b in br],
                         tube_vox=int(tube.sum()), tube_vox_off_ref=int((tube & ~near_ref).sum()),
                         n_anchor_vox=int(anchors.sum()), n_roots=len(gt.roots), anchor_kind=kind)
                r['dice'] = P.dice(gt.m, p2)
                r['tf1_0'], r['rooted_0'] = tf1_tol(gt, p2, lab2, 0.0)
                r['tf1_15'], r['rooted_15'] = tf1_tol(gt, p2, lab2, 1.5)
                pl = cc3d.connected_components(p2, connectivity=26)
                r['fp_components'] = len(set(np.unique(pl[p2])) - set(np.unique(pl[p2 & gt.m])))
                r['ncomp'] = int(pl.max())
                f.write(json.dumps(r) + '\n'); f.flush()
            print(case, 'done', flush=True)
