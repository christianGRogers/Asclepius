"""Round 10 (#43): the check A27's Dice row asks for (Foxtrot v5 F7.1), report only, CPU.

icx4's whole-tree Dice on the open 80 was 87.9, under F7.1's 88.3 line. F7.1 reads that as "the 4-class model or the
recipe loses tree that a default binary nnU-Net finds", and asks to "check the collapse, window and preprocessing before
predictions are used; report to the judge". This script separates the possible causes, per case, on the open 80
(open-36 + dev-44) and the val 80. It never reads a sealed case.

  * preprocessing: the prediction's grid (shape, affine) equals the ImageCAS-X label's and the CT's, and its values
    are within 0..4;
  * collapse: whole-tree Dice is binary (any vessel against any vessel), so the D25 collapse cannot move it; the
    script confirms the prediction's union and the reference union are what is compared;
  * lost tree vs. lumen width: binary centreline recall (reference skeleton within 1 voxel of the prediction) and
    precision; boundary-tolerant Dice (each mask counted as hitting if within 1 voxel of the other); volume ratio
    predicted / reference;
  * window: mean CT HU of the reference voxels the model misses, the predicted voxels the reference lacks, and their
    overlap. Misses much darker than the overlap point at faint lumen edge (window or label convention); misses as
    bright as the overlap point elsewhere.
Nothing here decides anything (A28: Dice decides nothing). It reports numbers for the judge and the lead.

Usage: python r10_dice_check.py --W $SCRATCH/icx4 --out $SCRATCH/icx4/r10_dice_check.json [--np 8]
Self-test: python r10_dice_check.py --selftest
"""
import argparse
import json
import os
import sys
import tempfile
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'trillium', 'icx4', 'lib'))
S26 = np.ones((3, 3, 3), bool)


def _dice(a, b):
    s = int(a.sum()) + int(b.sum())
    return None if s == 0 else 2.0 * int((a & b).sum()) / s


def measure(pred, ref, ct=None):
    """All the per-case numbers from arrays on one grid (pred, ref: 4-class labels; ct: HU or None)."""
    from scipy import ndimage as ndi
    from skimage.morphology import skeletonize
    p, r = pred > 0, ref > 0
    pd, rd = ndi.binary_dilation(p, S26), ndi.binary_dilation(r, S26)
    out = {'tree_dice': _dice(p, r), 'pred_vox': int(p.sum()), 'ref_vox': int(r.sum()),
           'volume_ratio': float(p.sum() / r.sum()) if r.any() else None,
           'tolerant_dice': (float((p & rd).sum() + (r & pd).sum()) / float(p.sum() + r.sum())) if (p.any() or r.any()) else None}
    rs = skeletonize(r) > 0 if r.any() else r
    ps = skeletonize(p) > 0 if p.any() else p
    out['cl_recall'] = float((rs & pd).sum() / rs.sum()) if rs.any() else None
    out['cl_precision'] = float((ps & rd).sum() / ps.sum()) if ps.any() else None
    if ct is not None:
        for k, m in (('hu_overlap', p & r), ('hu_missed', r & ~p), ('hu_extra', p & ~r)):
            out[k] = float(ct[m].mean()) if m.any() else None
    return out


CTX = {}


def _init(ctx):
    CTX.update(ctx)


def one(c):
    import nibabel as nib
    from territory import to_four
    W = CTX['W']
    try:
        pi = nib.load(os.path.join(W, 'predictions', f'{c}.nii.gz'))
        li = nib.load(os.path.join(W, 'icx', f'{int(c[1:]) + 1}.coronary.nii.gz'))
        pred = np.asarray(pi.dataobj)
        icx = np.asarray(li.dataobj).astype(np.int64)
        row = {'case': c, 'group': CTX['group'][c], 'pred_values': sorted(int(v) for v in np.unique(pred)),
               'grid_pred_vs_label': bool(pred.shape == icx.shape and np.allclose(pi.affine, li.affine, atol=1e-3))}
        ct = None
        ctp = CTX['ct'].get(c)
        if ctp and os.path.exists(ctp):
            ci = nib.load(ctp)
            row['grid_ct_vs_label'] = bool(ci.shape[:3] == icx.shape and np.allclose(ci.affine, li.affine, atol=1e-2))
            ct = np.asarray(ci.dataobj).astype(np.float32) if row['grid_ct_vs_label'] else None
        if not row['grid_pred_vs_label']:
            return row
        ref = to_four(icx, li.header.get_zooms()[:3])
        row['collapse_preserves_union'] = bool(((ref > 0) == (icx > 0)).all())
        row.update(measure(pred.astype(np.uint8), ref.astype(np.uint8), ct))
        return row
    except Exception as e:  # noqa: BLE001
        return {'case': c, 'group': CTX['group'].get(c), 'error': repr(e)[:300]}


def summarise(rows):
    out = {}
    for g in ('open36', 'dev44', 'open80', 'val80'):
        rs = [r for r in rows if 'error' not in r and (r['group'] == g or (g == 'open80' and r['group'] in ('open36', 'dev44')))]
        if not rs:
            continue
        s = {'n': len(rs), 'grid_mismatch': [r['case'] for r in rs if not r['grid_pred_vs_label'] or not r.get('grid_ct_vs_label', True)],
             'bad_values': [r['case'] for r in rs if not set(r['pred_values']) <= {0, 1, 2, 3, 4}],
             'collapse_changes_union': [r['case'] for r in rs if r.get('collapse_preserves_union') is False]}
        for k in ('tree_dice', 'tolerant_dice', 'volume_ratio', 'cl_recall', 'cl_precision', 'hu_overlap', 'hu_missed', 'hu_extra'):
            v = [r[k] for r in rs if r.get(k) is not None]
            if v:
                s[k] = {'mean': round(float(np.mean(v)), 4), 'median': round(float(np.median(v)), 4),
                        'p10': round(float(np.percentile(v, 10)), 4), 'p90': round(float(np.percentile(v, 90)), 4)}
        s['worst10_tree_dice'] = [(r['case'], round(r['tree_dice'], 4)) for r in sorted(
            [r for r in rs if r.get('tree_dice') is not None], key=lambda r: r['tree_dice'])[:10]]
        out[g] = s
    return out


def cases(W):
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    group = {c: 'open36' for c in S['open_icx_test']}
    group.update({c: 'dev44' for c in S['excluded_dev_cases_in_test']})
    sp = os.path.join(W, 'splits.json')
    if os.path.exists(sp):
        group.update({c: 'val80' for c in json.load(open(sp))['val']})
    bad = sorted(set(group) & sealed)
    if bad:
        sys.exit(f'[dice-check] REFUSING: sealed cases in the list {bad[:5]}')
    return group


def run(W, n_proc, only=None):
    group = cases(W)
    todo = sorted(c for c in group if os.path.exists(os.path.join(W, 'predictions', f'{c}.nii.gz'))
                  and (only is None or c in only))
    lay = os.path.join(W, 'layout.json')
    ct = {c: v.get('ct') for c, v in json.load(open(lay))['cases'].items()} if os.path.exists(lay) else {}
    with Pool(n_proc, initializer=_init, initargs=({'W': W, 'group': group, 'ct': ct},)) as p:
        rows = p.map(one, todo, chunksize=1)
    return {'n_cases': len(rows), 'errors': [r['case'] for r in rows if 'error' in r], 'summary': summarise(rows),
            'rows': rows}


def selftest():
    sys.path.insert(0, HERE)
    import r9_score_icx4 as R9
    ref, aorta, _ = R9.synthetic()
    thin = ref.copy()
    thin[(ref > 0) & ~__import__('scipy.ndimage', fromlist=['x']).binary_erosion(ref > 0, S26)] = 0   # a lumen 1 voxel thinner
    cut = ref.copy()
    sl = cut[60:110]
    sl[sl == 2] = 0                                             # the distal LAD lost
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    a, b, c = S['open_icx_test'][:3]
    with tempfile.TemporaryDirectory() as W:
        cts = {}
        for case, p in ((a, ref), (b, thin), (c, cut)):
            cts[case] = R9.write_case(W, case, p, ref, aorta)
        json.dump({'cases': {k: {'ct': v} for k, v in cts.items()}}, open(os.path.join(W, 'layout.json'), 'w'))
        json.dump({'val': [], 'train': [], 'test': []}, open(os.path.join(W, 'splits.json'), 'w'))
        res = run(W, 2, only={a, b, c})
    r = {x['case']: x for x in res['rows']}
    assert not res['errors'], res['errors']
    assert r[a]['tree_dice'] == 1.0 and r[a]['cl_recall'] == 1.0 and r[a]['grid_pred_vs_label'] and r[a]['grid_ct_vs_label']
    # a thinner lumen: Dice falls, the tree is all there, the tolerant Dice and the centreline recall stay high
    assert r[b]['tree_dice'] < 0.5 and r[b]['volume_ratio'] < 0.5 and r[b]['tolerant_dice'] > 0.9 and r[b]['cl_recall'] > 0.95
    # a lost distal LAD: the centreline recall falls with it
    assert r[c]['cl_recall'] < 0.85 and r[c]['cl_precision'] > 0.95
    assert res['summary']['open80']['n'] == 3 and not res['summary']['open80']['grid_mismatch']
    print('[dice-check] self-test passed: identity 1.0; thin lumen -> Dice', round(r[b]['tree_dice'], 3), 'but tolerant',
          round(r[b]['tolerant_dice'], 3), 'and centreline recall', round(r[b]['cl_recall'], 3),
          '; lost LAD -> centreline recall', round(r[c]['cl_recall'], 3))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--W'); ap.add_argument('--out'); ap.add_argument('--np', type=int, default=8)
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    res = run(a.W, a.np)
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps({'n_cases': res['n_cases'], 'errors': res['errors'], 'summary': res['summary']}, indent=1))
    return 1 if res['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
