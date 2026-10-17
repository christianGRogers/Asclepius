"""Naming ceiling on the THIN (ImageCAS-X) lumen convention: run the frozen namer on the ImageCAS-X reference
binary lumen itself and score its names against ImageCAS-X's own voxel labels (no projection, no shared
nearest-skeleton logic between truth and namer), by tree-F1 and swaps (Delta's metric code).
usage: ceiling.py OUT.jsonl OSTIUM_W.json case [case ...]
"""
import sys, os, json, time
import numpy as np, nibabel as nib
sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import perturb_metrics as P
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from namer import name_mask, load_ostium
from e2e import evaluate
import treelib as T

if __name__ == '__main__':
    out, ostw = sys.argv[1], sys.argv[2]
    load_ostium(ostw)
    import label as Lb
    modes = os.environ.get('RAMUS_MODES', 'inherit').split(',')
    outs = {m: (out if m == 'inherit' else out.replace('.jsonl', f'_{m}.jsonl')) for m in modes}
    done = {m: ({json.loads(l)['case'] for l in open(o)} if os.path.exists(o) else set()) for m, o in outs.items()}
    fos = {m: open(o, 'a') for m, o in outs.items()}
    for case in sys.argv[3:]:
        todo = [m for m in modes if case not in done[m]]
        if not todo or T.icx_path(case) is None:
            continue
        t0 = time.time()
        try:
            gt = P.GT(case, 'icx')
            img = nib.load(T.icx_path(case))
            # P.GT crops with a 12 mm margin; recover the crop offset the same way treelib does
            m_full = np.asanyarray(img.dataobj) > 0
            idx = [np.nonzero(m_full.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
            mv = np.ceil(12.0 / gt.sp).astype(int)
            lo = np.maximum([a[0] for a in idx] - mv, 0)
            cached = None
            for mode in todo:
                Lb.RAMUS = mode
                lab, res, cached = name_mask(gt.m, img.affine, gt.sp, lo, img.shape, bridge=4.0, cached=cached)
                r = evaluate(gt, gt.m, lab)
                r.update(case=case, arm='ceiling_icx', ramus_mode=mode, n_ramus=res.get('L_n_ramus'), lm_len=res.get('L_lm_len'),
                         namer_fail=res.get('fail'), n_trees=res.get('n_trees'), sec=round(time.time() - t0, 1))
                fos[mode].write(json.dumps(r) + '\n'); fos[mode].flush()
        except Exception as e:
            for mode in todo:
                fos[mode].write(json.dumps(dict(case=case, arm='ceiling_icx', ramus_mode=mode, error=repr(e)[:200])) + '\n'); fos[mode].flush()
        print(case, 'done', round(time.time() - t0), flush=True)
