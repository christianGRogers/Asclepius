"""Foxtrot, round 8: triage of atlas2 run 1's raw FP components (val) that have a locally cached CT.
Criteria were fixed in this docstring BEFORE the script was run on any case.

Per FP component (raw_prediction: >= 100 voxels, 26-conn, touches no reference voxel):
  core_hu     median HU of the component eroded by 1 voxel (all voxels if erosion empties it)
  art_hu      median HU of reference-mask voxels >= 1 mm inside the mask and within 20 mm of the component
  aorta_hu    median HU of the TotalSegmentator aorta eroded by 2 mm
  r_art       core_hu / art_hu ;  r_ao = core_hu / aorta_hu
  ring_hu     median HU of the shell 1-4 voxels around the component (excluding mask and prediction)
  diam_mm     2 x the 90th-percentile EDT (mm) over the component's skeleton (calibre)
  len_mm      skeleton voxel count x mean spacing (course length)
  dist_ref_mm min distance to the reference mask
  along       fraction of skeleton voxels within 1-10 mm of the reference mask (runs alongside the tree)
  companion   reference class (LM/LAD/LCx/RCA) of the nearest reference voxel
  gcv_region  companion == LCx (the great cardiac vein / coronary sinus run in the left AV groove with the LCx);
              descriptive only: no coronary-sinus label exists in the project, so a CS connection cannot be tested

Classes (first match wins):
  calcium_other  core_hu > max(600, 1.5 x art_hu)
  mask_artefact  r_art >= 0.75 and dist_ref_mm <= 2.0      (artery-bright, abutting the mask: a piece of mask vessel
                                                            the mask failed to cover / a gap at its edge)
  artery_branch  r_art >= 0.75 and dist_ref_mm > 2.0       (artery-bright, separate: unlabelled arterial branch)
  vein           r_art < 0.75 and ring_hu < 0 and along >= 0.5 and diam_mm >= 1.0
                                                           (less enhanced than the artery, in epicardial fat,
                                                            running alongside the tree, vessel calibre)
  indeterminate  anything else
Sensitivity: the 0.75 threshold is re-run at 0.65 and 0.85. Uncertainty: case-level (cluster) bootstrap.
Usage: fp_triage.py OUT.jsonl REF_DIR case ...
"""
import os, sys, json, glob
import numpy as np, nibabel as nib
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, '/home/user/Asclepius/trillium/atlas2/lib')
import segtrain_tf1 as T
VAL = glob.glob(SCR + '/round6/atlas/nnunet_results/*/*/fold_0/validation')[0]
CEN = json.load(open('/home/user/Asclepius/trillium-results/round6/atlas2/results/census_run1.json'))
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}


def classify(f, thr=0.75):
    if f['core_hu'] > max(600.0, 1.5 * f['art_hu']):
        return 'calcium_other'
    if f['r_art'] >= thr:
        return 'mask_artefact' if f['dist_ref_mm'] <= 2.0 else 'artery_branch'
    if f['ring_hu'] < 0 and f['along'] >= 0.5 and f['diam_mm'] >= 1.0:
        return 'vein'
    return 'indeterminate'


def run(c, refdir):
    ci = nib.load(f'{SCR}/data/ct/{c}.nii.gz'); sp = np.array(ci.header.get_zooms()[:3], float)
    CT = np.asanyarray(ci.dataobj).astype(np.float32)
    P = np.asanyarray(nib.load(f'{VAL}/{c}.nii.gz').dataobj).astype(np.uint8)
    R = np.asanyarray(nib.load(f'{refdir}/{c}.nii.gz').dataobj).astype(np.uint8)
    A = np.asanyarray(nib.load(f'{SCR}/round6/atlas2/aorta/{c}_aorta.nii.gz').dataobj) > 0
    ae = ndi.binary_erosion(A, iterations=int(round(2.0 / sp.min())))
    aorta_hu = float(np.median(CT[ae if ae.any() else A])) if A.any() else float('nan')
    raw = T.raw_prediction(P); lab, n = T.components(raw > 0)
    M = R > 0
    touched = set(np.unique(lab[(raw > 0) & M]).tolist()) - {0}
    cen = [r for r in CEN if r['case'] == c]
    objs = ndi.find_objects(lab); out = []
    mg = np.ceil(25 / sp).astype(int)
    for k in range(1, n + 1):
        if k in touched or objs[k - 1] is None:
            continue
        o = objs[k - 1]
        lo = np.maximum([s.start for s in o] - mg, 0); hi = np.minimum([s.stop for s in o] + mg, M.shape)
        sl = tuple(slice(a, b) for a, b in zip(lo, hi))
        m = lab[sl] == k; Mc = M[sl]; Rc = R[sl]; CTc = CT[sl]
        er = ndi.binary_erosion(m); core = er if er.any() else m
        core_hu = float(np.median(CTc[core]))
        dM, ind = ndi.distance_transform_edt(~Mc, sampling=sp, return_indices=True)
        dist_ref = float(dM[m].min())
        inner = ndi.distance_transform_edt(Mc, sampling=sp) >= 1.0
        near = inner & (ndi.distance_transform_edt(~m, sampling=sp) <= 20.0)
        art_hu = float(np.median(CTc[near])) if near.sum() >= 20 else float(np.median(CTc[inner])) if inner.any() else float('nan')
        shell = ndi.binary_dilation(m, iterations=4) & ~ndi.binary_dilation(m, iterations=1) & ~Mc & ~(raw[sl] > 0)
        ring_hu = float(np.median(CTc[shell])) if shell.any() else float('nan')
        sk = skeletonize(m) > 0
        if not sk.any(): sk = m
        edt = ndi.distance_transform_edt(m, sampling=sp)
        diam = float(2 * np.percentile(edt[sk], 90))
        along = float(((dM[sk] >= 1.0) & (dM[sk] <= 10.0)).mean())
        p = np.argwhere(m)[np.argmin(dM[m])]
        comp_cls = int(Rc[tuple(ind[:, p[0], p[1], p[2]])])
        mt = [r for r in cen if r['voxels'] == int(m.sum())]
        f = dict(case=c, voxels=int(m.sum()), census_category=mt[0]['category'] if len(mt) == 1 else None,
                 p90=mt[0].get('p90') if len(mt) == 1 else None,
                 core_hu=core_hu, art_hu=art_hu, aorta_hu=aorta_hu, r_art=core_hu / art_hu, r_ao=core_hu / aorta_hu,
                 ring_hu=ring_hu, diam_mm=diam, len_mm=float(sk.sum() * sp.mean()), dist_ref_mm=dist_ref,
                 along=along, companion=NAMES.get(comp_cls, '?'), gcv_region=comp_cls == 3)
        f['cls'] = classify(f); f['cls_065'] = classify(f, 0.65); f['cls_085'] = classify(f, 0.85)
        out.append(f)
    return out


if __name__ == '__main__':
    o, refdir = sys.argv[1], sys.argv[2]
    with open(o, 'a') as fh:
        for c in sys.argv[3:]:
            try:
                for f in run(c, refdir): fh.write(json.dumps(f) + '\n')
            except Exception as e:
                fh.write(json.dumps(dict(case=c, error=repr(e))) + '\n')
            fh.flush(); print(c, flush=True)
