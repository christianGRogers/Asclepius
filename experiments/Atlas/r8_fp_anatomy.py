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
    rows = [r for r in cat.get(case, [])]
    mg = np.ceil(25 / sp).astype(int)
    objs = ndi.find_objects(lab)
    for k in fp:
        o = objs[k - 1]
        lo = np.maximum([s.start for s in o] - mg, 0); hi = np.minimum([s.stop for s in o] + mg, M.shape)
        sl = tuple(slice(a, b) for a, b in zip(lo, hi))
        m = lab[sl] == k
        Mc, Ac, treec = M[sl], A[sl], tree[sl]
        pts = np.argwhere(m)
        rec = dict(case=case, voxels=int(m.sum()), mm3=float(m.sum() * sp.prod()))
        c = pts.mean(0) + lo
        best = min(rows, key=lambda r: np.linalg.norm(np.array(r['centroid']) - c)) if rows else None
        ok = best is not None and np.linalg.norm(np.array(best['centroid']) - c) < 3
        rec['category'] = best['category'] if ok else None
        rec['p90'] = best.get('p90') if ok else None
        rec['cls'] = best.get('cls') if ok else None
        rec['dist_mask_mm'] = float(ndi.distance_transform_edt(~Mc, sampling=sp)[m].min()) if Mc.any() else None
        rec['dist_tree_mm'] = float(ndi.distance_transform_edt(~treec, sampling=sp)[m].min()) if treec.any() else None
        rec['dist_aorta_mm'] = float(ndi.distance_transform_edt(~Ac, sampling=sp)[m].min()) if Ac.any() else None
        if Mc.any():
            ends = np.argwhere(endpoints(skeletonize(Mc)))
            if len(ends):
                P_mm = pts[:: max(1, len(pts) // 400)] * sp
                E_mm = ends * sp
                rec['dist_mask_tip_mm'] = float(np.sqrt(((P_mm[:, None, :] - E_mm[None]) ** 2).sum(-1)).min())
            rad = ndi.distance_transform_edt(Mc, sampling=sp)
            near = Mc & (ndi.distance_transform_edt(~m, sampling=sp) <= 10)
            rec['mask_radius_nearby_mm'] = float(rad[near].max()) if near.any() else None
        X = (pts - pts.mean(0)) * sp
        ev = np.sort(np.linalg.eigvalsh(np.cov(X.T)))[::-1] if len(pts) > 3 else np.array([0, 0, 0])
        rec['elongation'] = float(np.sqrt(ev[0] / max(ev[1], 1e-6)))
        rec['length_mm'] = float(4 * np.sqrt(ev[0]))
        rec['radius_mm'] = float(ndi.distance_transform_edt(np.pad(m, 1), sampling=sp).max())
        if CT is not None:
            ct = CT[sl]
            dm = ndi.distance_transform_edt(m, sampling=sp)
            rec['hu_median'] = float(np.median(ct[m]))
            rec['hu_core'] = float(np.median(ct[m & (dm >= dm.max() * 0.5)]))
            ring = ndi.binary_dilation(m, iterations=4) & ~ndi.binary_dilation(m, iterations=1)
            rec['hu_ring'] = float(np.median(ct[ring]))
            mr = ndi.distance_transform_edt(Mc, sampling=sp)
            rec['local_lumen_core_hu'] = float(np.median(ct[mr >= 1.0])) if (mr >= 1.0).any() else None
        rec['centroid_vox'] = [int(x) for x in c]
        out.write(json.dumps(rec) + '\n')
        out.flush()


if __name__ == '__main__':
    with open(sys.argv[1], 'a') as out:
        for case in sorted(cat):
            try:
                run(case, out)
            except Exception as e:
                print(case, 'ERROR', repr(e), flush=True)
            print(case, flush=True)
