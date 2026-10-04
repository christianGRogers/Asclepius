"""Ruling §4.4 / amendment A5 at target level: on the THIN convention (ImageCAS-X lumen, 4-class subtree
mapping, i.e. Crucible's option A), does resampling the label to 0.5 mm isotropic and back cut trees?
Per case: 4-class label one-hot (incl. background) -> linear resample to T mm iso -> linear back -> argmax
(nnU-Net's own seg/probability resampling path), then Delta's scorer (perturb_metrics.score: tF1 at zero gap
tolerance, rooted recall, beta0 error, per-class clDice, Dice) against the original.
Uses Delta's GT/score code read-only. Usage: thin_roundtrip_tf1.py <out.jsonl> case [case ...]"""
import sys, json, time
import numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import perturb_metrics as PM
out = open(sys.argv[1], 'a')
def roundtrip(lab, sp, t):
    zf = sp / t
    best = None; arg = np.zeros(lab.shape, np.uint8)
    for c in range(5):  # incremental argmax: two arrays in memory instead of five
        lo = ndi.zoom((lab == c).astype(np.float32), zf, order=1)
        back = ndi.zoom(lo, np.array(lab.shape) / np.array(lo.shape), order=1); del lo
        if best is None: best = back
        else:
            upd = back > best; arg[upd] = c; best[upd] = back[upd]
        del back
    return arg
for case in sys.argv[2:]:
    t0 = time.time()
    try:
        gt = PM.GT(case, 'icx')
    except Exception as e:
        print(case, 'fail', repr(e)[:80]); continue
    r = dict(case=case, sp=gt.sp.tolist(), gt_ncomp=int(gt.ncomp))
    for t in (0.5, 0.8):
        pl = roundtrip(gt.lab, gt.sp, t)
        s = PM.score(gt, pl > 0, pl)
        r[str(t)] = {k: s[k] for k in ('tf1', 'tf1_rec', 'tf1_prec', 'rooted_recall', 'beta0_err', 'ncomp', 'class_cldice', 'macro_dice', 'dice', 'swap_rate', 'class_comp_excess')}
        r[str(t)]['tf1_per_class'] = s['tf1_per_class']
    r['sec'] = round(time.time() - t0, 1)
    out.write(json.dumps(r) + '\n'); out.flush(); print(case, r['0.5']['tf1'], r['0.8']['tf1'], r['sec'], flush=True)
