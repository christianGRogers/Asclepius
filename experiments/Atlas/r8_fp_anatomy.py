"""Round 8: what are run 1's `confident_other` FP components? (A15 routed the recipe open on them.)
Per raw FP component (>= 100 voxels, 26-conn, touching no ImageCAS-mask voxel) of run 1's 80 val predictions:
geometry against the ImageCAS mask (the reference's extent) and the TotalSegmentator aorta, its relation to the
predicted tree, its shape, and -- where the CT is cached locally -- its HU against the same case's lumen.
Reads only (never writes) the round-6 volumes in the scratchpad. Usage: r8_fp_anatomy.py <out.jsonl>"""
import glob, json, os, sys
import numpy as np, nibabel as nib
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
R6 = '/home/user/Asclepius/trillium-results/round6/atlas2/results'
S26 = np.ones((3, 3, 3), bool)
cen = json.load(open(f'{R6}/census_run1.json'))
cat = {}
for r in cen:
    cat.setdefault(r['case'], []).append(r)
val_dir = glob.glob(f'{SCR}/round6/atlas/nnunet_results/*/*/fold_0/validation')[0]


def endpoints(sk):
    nb = ndi.convolve(sk.astype(np.uint8), S26.astype(np.uint8), mode='constant') - 1
    return sk & (nb == 1)


def run(case, out):
    pi = nib.load(f'{val_dir}/{case}.nii.gz'); P = np.asarray(pi.dataobj).astype(np.uint8)
    M = np.asarray(nib.load(f'{SCR}/data/masks/{case}.nii.gz').dataobj) > 0
    A = np.asarray(nib.load(f'{SCR}/round6/atlas2/aorta/{case}_aorta.nii.gz').dataobj) > 0
    ctp = f'{SCR}/data/ct/{case}.nii.gz'
    CT = np.asarray(nib.load(ctp).dataobj).astype(np.float32) if os.path.exists(ctp) else None
    sp = np.array(pi.header.get_zooms()[:3], float)
    lab, n = ndi.label(P > 0, structure=S26)
    sizes = np.bincount(lab.ravel())
    keep = sizes >= 100; keep[0] = False
    touched = set(np.unique(lab[M & (P > 0)]).tolist()) - {0}
    fp = [k for k in range(1, n + 1) if keep[k] and k not in touched]
    if not fp:
        return
    tree = np.isin(lab, list(touched))                      # predicted pieces that touch the reference
    # crop everything to the bbox of mask | prediction + 30 mm
    u = M | (P > 0); idx = np.nonzero(u); mg = np.ceil(30 / sp).astype(int)
    lo = np.maximum([i.min() for i in idx] - mg, 0); hi = np.minimum([i.max() + 1 for i in idx] + mg, M.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    Mc, Ac, labc, treec = M[sl], A[sl], lab[sl], tree[sl]
    d_mask = ndi.distance_transform_edt(~Mc, sampling=sp)
    d_tree = ndi.distance_transform_edt(~treec, sampling=sp) if treec.any() else None
    d_ao = ndi.distance_transform_edt(~Ac, sampling=sp) if Ac.any() else None
    msk = skeletonize(Mc); ends = np.argwhere(endpoints(msk))
    rad = ndi.distance_transform_edt(Mc, sampling=sp)
    lumen_hu = float(np.median(CT[sl][Mc])) if CT is not None else None
    core_hu = float(np.median(CT[sl][rad > 1.0])) if CT is not None and (rad > 1.0).any() else None
    # census rows of this case, matched by centroid
    rows = [r for r in cat.get(case, [])]
    for k in fp:
        m = labc == k
        pts = np.argwhere(m)
        rec = dict(case=case, voxels=int(m.sum()), mm3=float(m.sum() * sp.prod()))
        c = pts.mean(0) + lo
        best = min(rows, key=lambda r: np.linalg.norm(np.array(r['centroid']) - c)) if rows else None
        rec['category'] = best['category'] if best is not None and np.linalg.norm(np.array(best['centroid']) - c) < 3 else None
        rec['p90'] = best.get('p90') if best else None
        rec['dist_mask_mm'] = float(d_mask[m].min())
        rec['dist_tree_mm'] = float(d_tree[m].min()) if d_tree is not None else None
        rec['dist_aorta_mm'] = float(d_ao[m].min()) if d_ao is not None else None
        # nearest mask skeleton tip: is the component beyond the end of the annotated tree?
        if len(ends):
            P_mm = pts * sp; E_mm = ends * sp
            dd = np.sqrt(((P_mm[:, None, :] - E_mm[None, :, :]) ** 2).sum(-1)) if len(pts) * len(ends) < 4e6 else None
            rec['dist_mask_tip_mm'] = float(dd.min()) if dd is not None else None
        # shape: PCA elongation and skeleton length
        X = (pts - pts.mean(0)) * sp
        ev = np.sort(np.linalg.eigvalsh(np.cov(X.T)))[::-1] if len(pts) > 3 else np.array([0, 0, 0])
        rec['elongation'] = float(np.sqrt(ev[0] / max(ev[1], 1e-6)))
        rec['length_mm'] = float(4 * np.sqrt(ev[0]))
        sub = m[tuple(slice(p.min(), p.max() + 1) for p in pts.T)]
        rec['skeleton_vox'] = int(skeletonize(sub).sum())
        rec['radius_mm'] = float(ndi.distance_transform_edt(np.pad(sub, 1), sampling=sp).max())
        if CT is not None:
            ct = CT[sl]
            rec['hu_median'] = float(np.median(ct[m]))
            rec['hu_core'] = float(np.median(ct[m & (ndi.distance_transform_edt(m, sampling=sp) > 0.6)])) if (ndi.distance_transform_edt(m, sampling=sp) > 0.6).any() else None
            rec['case_lumen_hu'] = lumen_hu; rec['case_core_hu'] = core_hu
            ring = ndi.binary_dilation(m, iterations=4) & ~ndi.binary_dilation(m, iterations=1)
            rec['hu_ring'] = float(np.median(ct[ring]))
        rec['centroid_vox'] = [int(x) for x in c]
        out.write(json.dumps(rec) + '\n'); out.flush()


if __name__ == '__main__':
    with open(sys.argv[1], 'a') as out:
        for case in sorted(cat):
            try:
                run(case, out)
            except Exception as e:
                print(case, 'ERROR', repr(e), flush=True)
            print(case, flush=True)
