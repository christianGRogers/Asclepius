"""Round 2: END-TO-END two-stage result on REAL stage-1 output, scored by tree-F1 (the master plan's
deciding metric, A1) against the ImageCAS-X 4-class reference.

Stage 1 (real): ImageCAS-X's released binary nnU-Net, run on CPU on ImageCAS-X *test* cases
(Delta's 8 predictions + mine, identical inference script and settings).
Arms, all on the SAME binary prediction (threshold 0.5, components < 100 voxels removed):
  oracle   : every predicted voxel takes the reference class of the nearest reference voxel.
             = the best ANY direct 4-class model with this lumen could do (perfect naming) -> the
             direct-model proxy is bounded above by this arm.
  namer    : two-stage, frozen Bridge labeller (+4 mm naming bridges), no reference used.
  namer_nb : same, without bridging.
Plus 'ceiling': the namer on the REFERENCE binary lumen (naming error alone).
Metrics: Delta's perturb_metrics.score (tF1 @ 0 mm, swap_rate, cl_label_acc, macro Dice, per-class
clDice), tF1 @ 1.5 mm gap tolerance (same construction as Delta's analyse_preds), case-level swap
(some reference class whose detected centreline is < 50 % correctly named), LM length error.
Ostium for rooting = Delta's reference-ostium definition (thickest reference endpoint, LM preferred).

usage: e2e.py OUT.jsonl OSTIUM_W.json PREDDIR[,PREDDIR2] case [case ...]
"""
import sys, os, json, time
import numpy as np, nibabel as nib, cc3d
from scipy import ndimage as ndi
sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')   # read-only reuse of Delta's metric code
import perturb_metrics as P
import treelib as T
from analyse_preds import CropGT, remove_small
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from namer import name_mask, load_ostium

SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools'); from girder import mask_path


def tf1_tol(gt, pred, plab, d):
    """tree-F1 with gap tolerance d mm: predicted pieces within d mm count as connected (Delta's E8 construction),
    recall needs correct NAME and rooted; precision = predicted centreline labelled c inside reference class c."""
    inside = pred[tuple(gt.pts.T)]
    psk = plab[tuple(gt.pts.T)]
    if d > 0:
        dil = ndi.binary_dilation(pred, P.ball(d / 2, gt.sp))
    else:
        dil = pred
    dl = cc3d.connected_components(dil, connectivity=26)
    rcs = {dl[rt] for rt in gt.roots if dl[rt] > 0}
    rt_ok = np.isin(dl[tuple(gt.pts.T)], list(rcs)) & inside
    sk_pred = T.skeletonise(pred)
    tf, per = [], {}
    for c in (1, 2, 3, 4):
        g = gt.lab_sk == c
        if not g.any():
            continue
        rec = float((rt_ok & g & (psk == c)).sum() / g.sum())
        pc = plab[sk_pred] == c
        prec = float((gt.lab[sk_pred][pc] == c).mean()) if pc.any() else 0.0
        f = 2 * rec * prec / (rec + prec) if rec + prec else 0.0
        tf.append(f); per[c] = f
    return float(np.mean(tf)), per


def case_swap(gt, plab):
    psk = plab[tuple(gt.pts.T)]
    bad = []
    for c in (1, 2, 3, 4):
        g = (gt.lab_sk == c) & (psk > 0)
        if g.sum() >= 10 and (psk[g] == c).mean() < 0.5:
            bad.append(c)
    return bad


def oracle_labels(gt, pred):
    plab = np.where(pred, gt.lab, 0)
    add = pred & (gt.lab == 0)
    if add.any():
        _, inds = ndi.distance_transform_edt(gt.lab == 0, sampling=gt.sp, return_indices=True)
        plab[add] = gt.lab[tuple(inds)][add]
    return plab


def evaluate(gt, pred, plab):
    r = P.score(gt, pred, plab)
    r.pop('dice_per_class', None)
    r['tf1_tol1.5'], per = tf1_tol(gt, pred, plab, 1.5)
    r['tf1_per_class_tol1.5'] = per
    r['swapped_classes'] = case_swap(gt, plab)
    # ramus intermedius is a convention (judge §5): also score with IM reference voxels excluded
    if getattr(gt, 'raw', None) is not None and (gt.raw == 8).any():
        import copy
        g2 = copy.copy(gt)
        im = gt.raw == 8
        g2.lab = np.where(im, 0, gt.lab); g2.lab_sk = np.where(im[tuple(gt.pts.T)], 0, gt.lab_sk)
        r['tf1_tol1.5_noIM'], _ = tf1_tol(g2, pred, np.where(im, 0, plab), 1.5)
        r['has_IM'] = True
    else:
        r['tf1_tol1.5_noIM'] = r['tf1_tol1.5']; r['has_IM'] = False
    return r


if __name__ == '__main__':
    out, ostw, pdirs = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
    import label as Lb
    load_ostium(ostw)
    modes = os.environ.get('RAMUS_MODES', 'inherit').split(',')
    outs = {m: (out if m == 'inherit' else out.replace('.jsonl', f'_{m}.jsonl')) for m in modes}
    done = {m: ({(json.loads(l)['case'], json.loads(l)['arm']) for l in open(o)} if os.path.exists(o) else set())
            for m, o in outs.items()}
    fos = {m: open(o, 'a') for m, o in outs.items()}
    for case in sys.argv[4:]:
        pdir = next((p for p in pdirs if os.path.exists(f'{p}/{case}_prob.npy')), None)
        if pdir is None:
            continue
        todo = [m for m in modes if any((case, a) not in done[m] for a in ('oracle', 'namer', 'namer_nb', 'ceiling'))]
        if not todo:
            continue
        t0 = time.time()
        meta = json.load(open(f'{pdir}/{case}_meta.json'))
        lo, hi = np.array(meta['lo']), np.array(meta['hi'])
        prob = np.load(f'{pdir}/{case}_prob.npy').astype(np.float32)
        gt = CropGT(case, lo, hi)
        img = nib.load(mask_path(case)); A = img.affine; full = img.shape
        pred = remove_small(prob >= 0.5)
        cache = {}
        for mode in todo:
            Lb.RAMUS = mode
            arms = {'oracle': (pred, oracle_labels(gt, pred), {})}
            for nm, br, msk in (('namer', 4.0, pred), ('namer_nb', 0.0, pred), ('ceiling', 4.0, gt.m)):
                key = 'gt' if nm == 'ceiling' else 'pred'
                lab, res, cache[key] = name_mask(msk, A, gt.sp, lo, full, bridge=br, cached=cache.get(key))
                arms[nm] = (msk, lab, res)
            for arm, (pm, pl, res) in arms.items():
                if (case, arm) in done[mode]:
                    continue
                r = evaluate(gt, pm, pl)
                r.update(case=case, arm=arm, ramus_mode=mode, n_ramus=res.get('L_n_ramus'), lm_len=res.get('L_lm_len'),
                         namer_fail=res.get('fail'), n_trees=res.get('n_trees'), sec=round(time.time() - t0, 1))
                fos[mode].write(json.dumps(r) + '\n'); fos[mode].flush()
        print(case, 'done', round(time.time() - t0), flush=True)
