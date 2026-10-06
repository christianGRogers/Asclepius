"""Score D (direct 4-class model), R (rule renaming of D's foreground), H (grammar decoding of D's softmax)
and O (oracle naming of D's foreground: upper bound on any naming) against the proxy reference on the
master's validation split (ImageCAS-X val, 80 cases), by tree-F1 @ 1.5 mm (D3), swaps, macro Dice.
Then apply the A7 adoption rule (paired bootstrap 95 % CI of R-D (H-D) excludes 0 in its favour AND swap
rate no higher) and write results.json + SUMMARY.md.

usage: python evaluate_val.py RAW_DIR VALIDATION_DIR OUT_DIR NPROC
"""
import glob
import json
import os
import sys
import time
from multiprocessing import Pool

import cc3d
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import label as Lb  # noqa: E402
from namer import name_mask, load_ostium  # noqa: E402
from hybrid import hybrid  # noqa: E402
import tf1 as TF  # noqa: E402

ARMS = ('D', 'R', 'H', 'O')


def drop_small(lab, k=100):
    fg = lab > 0
    cc = cc3d.connected_components(fg, connectivity=26)
    sz = np.bincount(cc.ravel()); keep = sz >= k; keep[0] = False
    return np.where(keep[cc], lab, 0).astype(np.uint8)


def one(args):
    case, raw, vdir, outdir = args
    dst = os.path.join(outdir, 'cases', case + '.json')
    if os.path.exists(dst):
        return json.load(open(dst))
    t0 = time.time()
    load_ostium(os.path.join(HERE, 'ostium_w.json'))
    Lb.RAMUS = 'LCx'
    ri = nib.load(os.path.join(raw, 'labelsTr', case + '.nii.gz'))
    ref_full = np.asanyarray(ri.dataobj).astype(np.uint8)
    A = ri.affine; sp = np.asarray(ri.header.get_zooms()[:3], float); full = ref_full.shape
    D_full = np.asanyarray(nib.load(os.path.join(vdir, case + '.nii.gz')).dataobj).astype(np.uint8)
    D_full = drop_small(D_full)
    both = (ref_full > 0) | (D_full > 0)
    idx = np.argwhere(both)
    mv = np.ceil(10.0 / sp).astype(int)
    lo = np.maximum(idx.min(0) - mv, 0); hi = np.minimum(idx.max(0) + mv + 1, full)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    ref = ref_full[sl]; D = D_full[sl]
    npz = os.path.join(vdir, case + '.npz')
    prob = None
    if os.path.exists(npz):
        p = np.load(npz)['probabilities']            # (c, z, y, x): NibabelIO transposes to SimpleITK order
        prob = p.transpose(0, 3, 2, 1)[(slice(None),) + sl].astype(np.float32)
        del p
    fg = D > 0
    arms = {'D': D}
    lab, res, _ = name_mask(fg, A, sp, lo, full, bridge=4.0)
    arms['R'] = lab
    if prob is not None:
        arms['H'], hinfo = hybrid(fg, prob, A, sp, lo, full)
    # oracle: D's foreground, reference names (nearest reference voxel)
    o = np.zeros_like(D)
    if fg.any() and (ref > 0).any():
        _, ind = ndi.distance_transform_edt(ref == 0, sampling=sp, return_indices=True)
        o[fg] = ref[tuple(ind)][fg]
    arms['O'] = o
    R = TF.Ref(ref, sp)
    out = dict(case=case, sec=0.0, namer=dict(lm_len=res.get('L_lm_len'), fail=res.get('fail'), n_ramus=res.get('L_n_ramus')))
    for a, L in arms.items():
        out[a] = TF.score(R, L, 1.5)
        out[a]['tf1_per_class'] = {str(k): v for k, v in out[a]['tf1_per_class'].items()}
        out[a]['tf1_tol0'] = TF.score(R, L, 0.0)['tf1']
        # FP components on the raw prediction (A2 gate): predicted components touching no reference voxel
        cc = cc3d.connected_components(L > 0, connectivity=26)
        ids = set(np.unique(cc[L > 0])) - set(np.unique(cc[(L > 0) & (ref > 0)]))
        out[a]['fp_components'] = len(ids - {0})
    out['sec'] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    json.dump(out, open(dst + '.part', 'w')); os.replace(dst + '.part', dst)
    return out


def boot(d, n=10000, seed=0):
    d = np.asarray(d, float)
    rng = np.random.default_rng(seed)
    m = rng.choice(d, (n, len(d))).mean(1)
    return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def summarise(rows, outdir, meta):
    res = dict(meta=meta, n_cases=len(rows), arms={}, paired={}, verdict={})
    for a in ARMS:
        S = [r[a] for r in rows if a in r]
        if not S:
            continue
        res['arms'][a] = dict(n=len(S), tf1_1p5=float(np.mean([s['tf1'] for s in S])),
                              tf1_0=float(np.mean([s['tf1_tol0'] for s in S])),
                              macro_dice=float(np.mean([s['macro_dice'] for s in S])),
                              cases_with_swap=int(sum(1 for s in S if s['swapped_classes'])),
                              swap_rate=float(np.mean([bool(s['swapped_classes']) for s in S])),
                              centreline_label_acc=float(np.mean([s['centreline_label_acc'] for s in S])),
                              fp_components=float(np.mean([s['fp_components'] for s in S])),
                              per_class={c: float(np.mean([s['tf1_per_class'].get(c, np.nan) for s in S
                                                           if c in s['tf1_per_class']]))
                                         for c in ('1', '2', '3', '4') if any(c in s['tf1_per_class'] for s in S)})
    for a in ('R', 'H', 'O'):
        pairs = [(r[a]['tf1'], r['D']['tf1']) for r in rows if a in r and 'D' in r]
        if not pairs:
            continue
        diff = [x - y for x, y in pairs]
        mean, lo, hi = boot(diff)
        res['paired'][f'{a}-D'] = dict(n=len(diff), mean=mean, ci95=[lo, hi],
                                       better=int(sum(x > 1e-9 for x in diff)), worse=int(sum(x < -1e-9 for x in diff)))
        if a in ('R', 'H'):
            adopt = lo > 0 and res['arms'][a]['swap_rate'] <= res['arms']['D']['swap_rate']
            res['verdict'][a] = 'ADOPT (A7 rule met)' if adopt else 'do not adopt (A7 rule not met)'
    json.dump(dict(res, cases=rows), open(os.path.join(outdir, 'results.json'), 'w'), indent=1)
    L = ['# Bridge Trillium experiment: does rule naming (R) or grammar decoding (H) beat the direct model\'s own names (D)?', '',
         f"Model: direct 4-class nnU-Net, master recipe (ResEnc, 0.5 mm iso, plan `{meta.get('plans')}`, patch {meta.get('patch')}, "
         f"no mirroring), trained {meta.get('epochs_trained')} epochs ({meta.get('train_hours')} h) on the territory proxy "
         f"of {meta.get('n_train')} ImageCAS-X train cases (D0/D1/D1b). Scored on the master's val split "
         f"({len(rows)} cases), reference = the same proxy. tF1 @ 1.5 mm with reference-derived ostia (provisional per A9).", '',
         '| Arm | n | tF1 @1.5 | tF1 @0 | macro Dice | cases with swap | centreline name acc. | FP comps |',
         '|---|---|---|---|---|---|---|---|']
    names = dict(D='D: direct model names', R='R: rule renaming of D foreground', H='H: grammar decode of D softmax',
                 O='O: oracle names on D foreground (naming upper bound)')
    for a, v in res['arms'].items():
        L.append(f"| {names[a]} | {v['n']} | {v['tf1_1p5']:.3f} | {v['tf1_0']:.3f} | {v['macro_dice']:.3f} | "
                 f"{v['cases_with_swap']} | {v['centreline_label_acc']:.3f} | {v['fp_components']:.2f} |")
    L += ['', '| Paired | mean diff tF1 | 95 % CI | better / worse cases |', '|---|---|---|---|']
    for k, v in res['paired'].items():
        L.append(f"| {k} | {v['mean']:+.4f} | [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] | {v['better']} / {v['worse']} |")
    L += ['', '**A7 verdict** (adopt only if CI excludes 0 in its favour and swap rate is no higher):', '']
    for k, v in res['verdict'].items():
        L.append(f'- {k}: {v}')
    L += ['', 'Reading guide: O−D is how much naming headroom the direct model leaves on its own lumen. If R−D or H−D is '
          'positive with a CI above 0, structure out-names the network and Bridge v3 / A7 ship R or H; if the CIs '
          'sit at or below 0, the direct model names as well as the rules and R/H stay QA only.']
    open(os.path.join(outdir, 'SUMMARY.md'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    raw, vdir, outdir, nproc = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    os.makedirs(outdir, exist_ok=True)
    split = json.load(open(os.path.join(raw, 'splits_bridge.json')))[0]
    cases = [c for c in split['val'] if os.path.exists(os.path.join(vdir, c + '.nii.gz'))]
    print(f'evaluating {len(cases)} val cases with {nproc} workers', flush=True)
    rows = []
    with Pool(nproc, maxtasksperchild=4) as p:
        for r in p.imap_unordered(one, [(c, raw, vdir, outdir) for c in cases]):
            rows.append(r); print(r['case'], {a: round(r[a]['tf1'], 3) for a in ARMS if a in r}, r['sec'], flush=True)
    meta = json.load(open(os.path.join(outdir, 'meta.json'))) if os.path.exists(os.path.join(outdir, 'meta.json')) else {}
    summarise(sorted(rows, key=lambda r: r['case']), outdir, meta)
