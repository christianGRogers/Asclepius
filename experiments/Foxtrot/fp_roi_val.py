"""Foxtrot, round 8: A20 condition 2 on atlas2 run 1's val segmentations.

For each val case whose CT is cached locally:
  * ROI = TotalSegmentator fast (3 mm) heart ∪ aorta from the CT (same procedure as heart_roi_ref.py);
  * every raw predicted component (segtrain_tf1.raw_prediction, 26-conn): min distance (mm) to the ROI;
  * FP components (touch no reference voxel) matched to census_run1.json rows by voxel count (category);
  * the A20 rule: delete components with min ROI distance > D (25 mm), unless heart < 5000 3-mm voxels;
  * A1 tF1 (atlas2's own score.a1_score, frozen metric copy) and FP count before and after;
  * reference max distance to the ROI (A20 condition 1 on this case).
Usage: TOTALSEG_HOME_DIR=... python3 fp_roi_val.py OUT.jsonl REF_DIR case ...
"""
import os, sys, json, time, tempfile
import numpy as np, nibabel as nib
from scipy import ndimage as ndi
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, '/home/user/Asclepius/trillium/atlas2/lib')
import score as S  # read-only use of atlas2's scoring
T = S.T
D = 25.0
VAL = [p for p in __import__('glob').glob(SCR + '/round6/atlas/nnunet_results/*/*/fold_0/validation')][0]
CENSUS = json.load(open('/home/user/Asclepius/trillium-results/round6/atlas2/results/census_run1.json'))


def roi_mask(ctimg, td, c):
    from totalsegmentator.python_api import totalsegmentator
    sp = np.array(ctimg.header.get_zooms()[:3], float)
    ct = np.asanyarray(ctimg.dataobj).astype(np.float32)
    ct3 = ndi.zoom(ct, sp / 3.0, order=1, prefilter=False); del ct
    A3 = ctimg.affine.copy(); A3[:3, :3] = ctimg.affine[:3, :3] @ np.diag(3.0 / sp)
    p = os.path.join(td, f'{c}_3mm.nii.gz'); nib.save(nib.Nifti1Image(ct3.astype(np.int16), A3), p)
    seg = np.asanyarray(totalsegmentator(p, None, fast=True, roi_subset=['heart', 'aorta'], device='cpu',
                                         nr_thr_resamp=1, nr_thr_saving=1, quiet=True, ml=True).dataobj)
    os.remove(p)
    roi3 = np.isin(seg, [51, 52]); heart = int((seg == 51).sum())
    roi1 = ndi.zoom(roi3.astype(np.float32), 3.0, order=1, prefilter=False) > 0.5
    return ndi.distance_transform_edt(~roi1), heart  # mm on a 1 mm grid


def sample(dist1, idx, sp):
    g = np.minimum(np.floor(idx * sp[None, :]).astype(int), np.array(dist1.shape) - 1)
    return dist1[g[:, 0], g[:, 1], g[:, 2]]


def run(c, refdir, td):
    ctimg = nib.load(f'{SCR}/data/ct/{c}.nii.gz'); sp = np.array(ctimg.header.get_zooms()[:3], float)
    pred = np.asanyarray(nib.load(f'{VAL}/{c}.nii.gz').dataobj).astype(np.uint8)
    ref = np.asanyarray(nib.load(f'{refdir}/{c}.nii.gz').dataobj).astype(np.uint8)
    ao = np.asanyarray(nib.load(f'{SCR}/round6/atlas2/aorta/{c}_aorta.nii.gz').dataobj) > 0
    ctv = np.asanyarray(ctimg.dataobj).astype(np.float32)
    dist1, heart = roi_mask(ctimg, td, c)
    ref_max = float(sample(dist1, np.argwhere(ref > 0), sp).max())
    raw = T.raw_prediction(pred)
    lab, n = T.components(raw > 0)
    touched = set(np.unique(lab[(raw > 0) & (ref > 0)]).tolist()) - {0}
    comps, delete = [], []
    cen = [r for r in CENSUS if r['case'] == c]
    for k in range(1, n + 1):
        idx = np.argwhere(lab == k)
        md = float(sample(dist1, idx, sp).min())
        fp = k not in touched
        row = dict(voxels=len(idx), fp=fp, min_roi_mm=md)
        if fp:
            m = [r for r in cen if r['voxels'] == len(idx)]
            row['category'] = m[0]['category'] if len(m) == 1 else ('ambiguous' if m else 'unmatched')
            if m: row['dist_to_ref_mm'] = m[0]['dist_to_ref_mm']
        comps.append(row)
        if md > D and heart >= 5000:
            delete.append(k)
    after = raw.copy()
    if delete:
        after[np.isin(lab, delete)] = 0
    # score like atlas2 (same crop rule, same ostia for both arms)
    sl = S._bbox([ref > 0, pred > 0], sp, ref.shape)
    rep = T.find_ostia(ref[sl], sp, aorta=ao[sl], ct=ctv[sl])
    a = S.a1_score(ref[sl], pred[sl], sp, aorta=ao[sl], ct=ctv[sl], rep=rep)
    b = S.a1_score(ref[sl], after[sl], sp, aorta=ao[sl], ct=ctv[sl], rep=rep)
    dec = lambda x: S.decisive_case_score(x)
    return dict(case=c, heart_vox3mm=heart, ref_max_roi_mm=ref_max, n_comp=n, comps=comps,
                deleted=len(delete), deleted_touching_ref=sum(1 for k in delete if k in touched),
                before=dict(tf1=a['tf1'], decisive=dec(a), fp=a['fp_components']),
                after=dict(tf1=b['tf1'], decisive=dec(b), fp=b['fp_components']))


if __name__ == '__main__':
    out, refdir = sys.argv[1], sys.argv[2]
    done = {json.loads(l)['case'] for l in open(out)} if os.path.exists(out) else set()
    with tempfile.TemporaryDirectory(dir=SCR + '/work/Foxtrot') as td:
        for c in sys.argv[3:]:
            if c in done: continue
            t = time.time()
            try: r = run(c, refdir, td)
            except Exception as e:
                import traceback; r = dict(case=c, error=traceback.format_exc()[-800:])
            r['sec'] = round(time.time() - t, 1)
            open(out, 'a').write(json.dumps(r) + '\n')
            print(c, r.get('deleted'), r.get('before'), r.get('after'), r['sec'], flush=True)
