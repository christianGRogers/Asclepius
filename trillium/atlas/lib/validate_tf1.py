"""CPU check (run in the tournament sandbox, not on Trillium): this module's tF1 vs Delta's perturb_metrics.score
on the same reference/prediction pairs (ImageCAS-X thin reference, 0.8 mm round-trip prediction), tol = 0."""
import sys, json
import numpy as np
sys.path.insert(0, '/home/user/Asclepius/experiments/Delta'); sys.path.insert(0, '/home/user/Asclepius/experiments/Atlas')
sys.path.insert(0, '/home/user/Asclepius/trillium/atlas/lib')
import perturb_metrics as PM, tf1
from scipy import ndimage as ndi
def roundtrip(lab, sp, t):  # same as experiments/Atlas/thin_roundtrip_tf1.py
    zf = sp / t; best = None; arg = np.zeros(lab.shape, np.uint8)
    for c in range(5):
        lo = ndi.zoom((lab == c).astype(np.float32), zf, order=1)
        back = ndi.zoom(lo, np.array(lab.shape) / np.array(lo.shape), order=1)
        if best is None: best = back
        else:
            upd = back > best; arg[upd] = c; best[upd] = back[upd]
    return arg
for case in sys.argv[1:]:
    gt = PM.GT(case, 'icx')
    for t in (0.8, 1.0):
        pl = roundtrip(gt.lab, gt.sp, t)
        d = PM.score(gt, pl > 0, pl)
        a = tf1.score(gt.lab, pl, gt.sp, tol=0.0, min_comp=0)
        print(json.dumps(dict(case=case, t=t, delta_tf1=round(d['tf1'], 4), atlas_tf1=round(a['tf1'], 4),
                              delta_cldice=round(d['class_cldice'], 4), atlas_cldice=round(a['class_cldice'], 4),
                              delta_swap=round(d['swap_rate'], 4), atlas_swap=round(a['swap_rate'], 4))), flush=True)
