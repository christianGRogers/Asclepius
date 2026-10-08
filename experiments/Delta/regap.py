"""E11: gap-centred re-inference. For every predicted piece that is not connected to the ostium
(aorta-anchored component) but lies within MAXD mm of it, re-run the *same* network on one patch
centred on the gap, fuse it with the first-pass probability, and re-threshold.

Usage: TORCH_THREADS=1 python regap.py <model_dir> <pred_dir> <aorta_dir> <out.jsonl> case [case ...]

Rationale: sliding-window inference sees a gap at an arbitrary position in the window (often at a
window border, where the Gaussian weight is low and context is cut). A window centred on the gap
gives the network full context on both sides. Costs one forward pass per gap.
Fusion variants: 'mean' (average of first-pass and gap-centred prob inside the patch) and 'max'.
Scoring as in bridge_eval.py (aorta ostium, oracle names), plus the same geometric bridging (3 mm)
applied after re-inference.
"""
import json
import os
import sys
import time

import cc3d
import nibabel as nib
import numpy as np
import torch
from scipy import ndimage as ndi

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools')
from girder import ct_path  # noqa: E402
import analyse_preds as A  # noqa: E402
import bridge_eval as BE  # noqa: E402
import perturb_metrics as P  # noqa: E402
import postproc  # noqa: E402
import treelib as T  # noqa: E402

torch.set_num_threads(int(os.environ.get('TORCH_THREADS', '1')))
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor  # noqa: E402

MAXD = float(os.environ.get('REGAP_MAXD', '15'))
PATCH = (160, 160, 96)  # nibabel (x, y, z) order of the plans' (z, y, x) = (96, 160, 160)


def gap_sites(pred, anchors, sp):
    cl, n = cc3d.connected_components(pred, connectivity=26, return_N=True)
    sizes = np.bincount(cl.ravel())
    anc_ids = set(np.unique(cl[anchors & pred])) - {0}
    if not anc_ids:
        return []
    anc = np.isin(cl, list(anc_ids))
    dist, inds = ndi.distance_transform_edt(~anc, sampling=sp, return_indices=True)
    sites = []
    for k in range(1, n + 1):
        if k in anc_ids or sizes[k] < 100:
            continue
        m = cl == k
        dk = dist[m]; j = int(np.argmin(dk))
        if dk[j] <= MAXD:
            p = np.argwhere(m)[j]
            q = np.array([inds[a][tuple(p)] for a in range(3)])
            sites.append(dict(comp_vox=int(sizes[k]), gap_mm=float(dk[j]), mid=((p + q) / 2).round().astype(int).tolist()))
    return sites


def audit(br, pred_bin, gt):
    """Per bridge: did the orphan touch the reference (true join) or not (FP blob joined)?"""
    cl = cc3d.connected_components(pred_bin, connectivity=26)
    out = []
    for b in br:
        k = cl[tuple(b['p'])]
        comp = cl == k if k > 0 else np.zeros_like(pred_bin)
        d = dict(gap_mm=round(b['gap_mm'], 2), comp_vox=b['comp_vox'], true_join=bool((comp & gt.m).any()))
        thick = getattr(gt, 'thick', None)
        if thick is not None:  # C4: re-read against the decided thick reference (original ImageCAS mask)
            d['touches_thick'] = bool((comp & thick).any())
            d['frac_in_thick'] = float((comp & thick).sum() / max(comp.sum(), 1))
        out.append(d)
    return out


def score(gt, pred_bin, plab_fn):
    plab = plab_fn(pred_bin)
    t0, r0 = BE.tf1_tol(gt, pred_bin, plab, 0.0)
    t15, r15 = BE.tf1_tol(gt, pred_bin, plab, 1.5)
    pl = cc3d.connected_components(pred_bin, connectivity=26)
    fp = len(set(np.unique(pl[pred_bin])) - set(np.unique(pl[pred_bin & gt.m])))
    return dict(dice=P.dice(gt.m, pred_bin), tf1_0=t0, rooted_0=r0, tf1_15=t15, rooted_15=r15,
                fp_components=fp, ncomp=int(pl.max())), plab


if __name__ == '__main__':
    mdir, pdir, adir, out = sys.argv[1:5]
    predictor = nnUNetPredictor(tile_step_size=0.5, use_gaussian=True, use_mirroring=False,
                                perform_everything_on_device=False, device=torch.device('cpu'),
                                verbose=False, verbose_preprocessing=False, allow_tqdm=False)
    predictor.initialize_from_trained_model_folder(mdir, use_folds=(0,), checkpoint_name='checkpoint_best.pth')
    with open(out, 'a') as f:
        for case in sys.argv[5:]:
            t = time.time()
            meta = json.load(open(f'{pdir}/{case}_meta.json'))
            lo, hi = np.array(meta['lo']), np.array(meta['hi'])
            prob = np.load(f'{pdir}/{case}_prob.npy').astype(np.float32)
            gt = A.CropGT(case, lo.tolist(), hi.tolist())
            gt.thick = (np.asanyarray(nib.load(T.mask_path(case)).dataobj) > 0.5)[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
            ao, kind = BE.anchor_structure(case, lo, hi, gt, adir)
            d_ao = BE.set_aorta_roots(gt, ao, kind)
            _, inds = ndi.distance_transform_edt(gt.lab == 0, sampling=gt.sp, return_indices=True)
            nearest_lab = gt.lab[tuple(inds)]; del inds
            plab_fn = lambda b: np.where(b, nearest_lab, 0).astype(np.uint8)  # oracle names
            pred = A.remove_small(prob >= 0.5)
            anchors = BE.anchor_components(pred, d_ao)
            sites = gap_sites(pred, anchors, gt.sp)
            img = nib.load(ct_path(case)); full = img.shape
            ct = np.asanyarray(img.dataobj)
            sp = gt.sp
            new_mean = prob.copy(); new_max = prob.copy()
            second = np.zeros(prob.shape, np.float32)  # gap-centred second-look probability
            for s in sites:
                c = np.array(s['mid']) + lo  # full-volume coords
                a = np.clip(c - np.array(PATCH) // 2, 0, np.array(full) - np.array(PATCH))
                b = a + np.array(PATCH)
                sub = ct[a[0]:b[0], a[1]:b[1], a[2]:b[2]].astype(np.float32)
                x = sub.transpose(2, 1, 0)[None]
                props = {'spacing': [float(sp[2]), float(sp[1]), float(sp[0])]}
                _, pr = predictor.predict_single_npy_array(x, props, None, None, True)
                pp = pr[1].transpose(2, 1, 0)
                # place into crop coords
                ca = a - lo; cb = b - lo
                s0 = np.maximum(ca, 0); s1 = np.minimum(cb, prob.shape)
                src = tuple(slice(s0[k] - ca[k], s1[k] - ca[k]) for k in range(3))
                dst = tuple(slice(s0[k], s1[k]) for k in range(3))
                new_mean[dst] = 0.5 * (prob[dst] + pp[src])
                new_max[dst] = np.maximum(new_max[dst], pp[src])
                second[dst] = np.maximum(second[dst], pp[src])
            res = dict(case=case, n_sites=len(sites), sites=sites, anchor_kind=kind)
            for name, pm in (('first', prob), ('regap_mean', new_mean), ('regap_max', new_max)):
                pb = A.remove_small(pm >= 0.5)
                sc, plab = score(gt, pb, plab_fn)
                res[name] = sc
                anc2 = BE.anchor_components(pb, d_ao)
                lab2, br = postproc.bridge(plab, anc2, gt.sp, max_gap_mm=3.0, min_vox=100)
                sc2, _ = score(gt, lab2 > 0, lambda b: np.where(b, lab2, 0).astype(np.uint8))
                sc2['n_bridges'] = len(br)
                sc2['audit'] = audit(br, pb, gt)
                res[name + '+bridge3'] = sc2
                if name == 'regap_max':
                    # support rule: join only orphans that the second look predicted again
                    lab3, br3 = postproc.bridge(plab, anc2, gt.sp, max_gap_mm=3.0, min_vox=100,
                                                eligible=second >= 0.5)
                    sc3, _ = score(gt, lab3 > 0, lambda b: np.where(b, lab3, 0).astype(np.uint8))
                    sc3['n_bridges'] = len(br3)
                    sc3['audit'] = audit(br3, pb, gt)
                    res[name + '+bridge3_supported'] = sc3
            res['seconds'] = time.time() - t
            f.write(json.dumps(res) + '\n'); f.flush()
            print(case, 'done', len(sites), round(time.time() - t), flush=True)
