"""E5: does label-consistency post-processing (postproc.relabel) repair label errors, and
what does it do to correct labels?

Usage: python postproc_eval.py <out.jsonl> case [case ...]   (ImageCAS-X reference)
For identity + every label perturbation of perturb_metrics, and for 'islands' on top of a
binary 'gaps5' prediction, score before and after relabel().
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import perturb_metrics as P  # noqa: E402
import postproc  # noqa: E402

KEEP = ['macro_dice', 'cl_label_acc', 'swap_rate', 'class_comp_excess', 'tf1', 'class_cldice', 'dice_per_class']

if __name__ == '__main__':
    out = sys.argv[1]
    with open(out, 'a') as f:
        for case in sys.argv[2:]:
            t = time.time()
            gt = P.GT(case, source='icx')
            for k in ['identity'] + P.LAB:
                lab = gt.lab.copy() if k == 'identity' else P.perturb_labels(gt, k)
                if lab is None:
                    continue
                b = P.score(gt, gt.m, lab)
                lab2 = postproc.relabel(gt.m, lab, gt.sp)
                a = P.score(gt, gt.m, lab2)
                r = dict(case=case, kind=k, before={x: b[x] for x in KEEP}, after={x: a[x] for x in KEEP},
                         changed_vox=int((lab2 != lab).sum()), wrong_before=int((lab != gt.lab).sum()),
                         wrong_after=int((lab2 != gt.lab).sum()))
                f.write(json.dumps(r) + '\n'); f.flush()
            print(case, 'done', round(time.time() - t), flush=True)
