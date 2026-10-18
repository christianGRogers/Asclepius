"""Round 9 (Atlas v11): score icx4 predictions with the decisive metric, on CPU, after `./icx4 collect`.

icx4's own score.py reports Dice only. This adds what decides under the master's amendments:
  * macro tF1 @ 1.5 mm (D3) from src/segtrain/tf1.py **at the pinned A1c hash** (refuses any other file);
  * A1 ostium of record from TotalSegmentator aortas (run 2's masks: $SCRATCH/atlas2/aorta/<case>_aorta.nii.gz);
    a case without an aorta is provisional (A1a) and a flagged tree is reported apart (A1b);
  * the A2/A15 FP gate on the raw prediction; per-class Dice beside it, for comparison with the literature;
  * reference = ImageCAS-X as drawn (D8) collapsed to four classes exactly as icx4 trains (D25, territory.py).
  * cases: the 80 ImageCAS-X val cases and/or the 36 clean open test cases. **Refuses any sealed case (A14).**
Paired mode (--pair DIR2): the same cases scored for a second run (seed 2) and the paired difference, case-bootstrap
CI and the one-pair estimate of sigma_seed (A22). Ensemble predictions are scored like any other directory.

Usage:
  python r9_score_icx4.py --pred DIR --icx ICX_DIR --aorta AORTA_DIR --sealed sealed_test.json \
      --splits splits.json --set val|open36|both --out OUT.json [--pair DIR2] [--np 8]
Self-test (synthetic trees, no data needed):  python r9_score_icx4.py --selftest
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))
sys.path.insert(0, os.path.join(ROOT, 'trillium', 'icx4', 'lib'))

PINNED = '24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254'   # A1c, Round 8
TF1_PATH = os.path.join(ROOT, 'src', 'segtrain', 'tf1.py')
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}


def check_hash():
    h = hashlib.sha256(open(TF1_PATH, 'rb').read()).hexdigest()
    if h != PINNED:
        sys.exit(f'[score] REFUSING: {TF1_PATH} sha256 {h} != pinned A1c {PINNED}')
    return h


def dice(a, b):
    s = int(a.sum()) + int(b.sum())
    return None if s == 0 else 2.0 * int((a & b).sum()) / s


def score_arrays(case, pred, ref, spacing, aorta):
    from segtrain import tf1
    r = tf1.tree_f1(ref, pred, spacing, aorta=aorta)
    row = {'case': case, 'tf1': r.tf1, 'per_class': {NAMES[c]: v for c, v in r.per_class.items()},
           'provisional': r.provisional, 'flagged': r.flagged,
           'classes_without_centreline': [NAMES[int(c)] for c in r.classes_without_centreline],
           'fp_components': tf1.fp_components(ref, pred),
           'dice': {NAMES[k]: dice(pred == k, ref == k) for k in NAMES}}
    return row


def score_case(args):
    case, pred_dir, icx_dir, aorta_dir = args
    import nibabel as nib
    from territory import to_four
    p = os.path.join(pred_dir, f'{case}.nii.gz')
    if not os.path.exists(p):
        return {'case': case, 'error': 'prediction missing'}
    try:
        pi = nib.load(p)
        pred = np.asarray(pi.dataobj).astype(np.uint8)
        li = nib.load(os.path.join(icx_dir, f'{int(case[1:]) + 1}.coronary.nii.gz'))
        zooms = li.header.get_zooms()[:3]
        ref = to_four(np.asarray(li.dataobj).astype(np.int64), zooms).astype(np.uint8)
        if pred.shape != ref.shape:
            return {'case': case, 'error': f'grid mismatch {pred.shape} vs {ref.shape}'}
        af = os.path.join(aorta_dir, f'{case}_aorta.nii.gz') if aorta_dir else ''
        aorta = (np.asarray(nib.load(af).dataobj) > 0) if af and os.path.exists(af) else None
        return score_arrays(case, pred, ref, zooms, aorta)
    except Exception as e:  # noqa: BLE001 - one bad case must not stop the report
        return {'case': case, 'error': repr(e)[:300]}


def decisive(rows):
    """A1a/A1b: only rows with an aorta ostium and no flagged tree enter decisive aggregates."""
    return [r for r in rows if 'error' not in r and not r['provisional'] and not r['flagged']
            and r['tf1'] == r['tf1']]


def boot_ci(x, n=10000, seed=0):
    x = np.asarray(x, float)
    if len(x) < 2:
        return [None, None]
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), (n, len(x)))].mean(1)
    return [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)]


def summarise(rows):
    d = decisive(rows)
    out = {'n_cases': len(rows), 'n_decisive': len(d),
           'n_provisional': sum(1 for r in rows if r.get('provisional')),
           'n_flagged': sum(1 for r in rows if r.get('flagged')),
           'errors': [r['case'] for r in rows if 'error' in r]}
    if d:
        out['macro_tf1'] = round(float(np.mean([r['tf1'] for r in d])), 4)
        out['macro_tf1_ci'] = boot_ci([r['tf1'] for r in d])
        out['per_class_tf1'] = {n: round(float(np.mean(v)), 4) for n in NAMES.values()
                                if (v := [r['per_class'][n] for r in d if n in r['per_class']])}
    ok = [r for r in rows if 'error' not in r]
    if ok:
        out['fp_per_case'] = round(float(np.mean([r['fp_components'] for r in ok])), 3)
        out['dice_when_in_ref'] = {n: round(float(np.mean(v)), 4) for n in NAMES.values()
                                   if (v := [r['dice'][n] for r in ok if r['dice'][n] is not None])}
    return out


def paired(rows1, rows2, sigma_prior=0.013):
    a = {r['case']: r for r in decisive(rows1)}
    b = {r['case']: r for r in decisive(rows2)}
    common = sorted(set(a) & set(b))
    diff = [b[c]['tf1'] - a[c]['tf1'] for c in common]
    if not diff:
        return {'n': 0}
    m = float(np.mean(diff))
    se_case = float(np.std(diff, ddof=1) / np.sqrt(len(diff))) if len(diff) > 1 else float('nan')
    se_seed = float(np.sqrt(se_case ** 2 + sigma_prior ** 2))
    return {'n': len(common), 'mean_diff_run2_minus_run1': round(m, 4), 'case_ci': boot_ci(diff),
            'seed_inclusive_ci': [round(m - 1.96 * se_seed, 4), round(m + 1.96 * se_seed, 4)],
            # with one pair of runs, Var(run mean difference) = 2 sigma_seed^2 + case noise; a 1-df estimate:
            'sigma_seed_estimate_1df': round(float(np.sqrt(max(m * m - se_case ** 2, 0.0) / 2.0)), 4),
            'fp_diff': round(float(np.mean([b[c]['fp_components'] - a[c]['fp_components'] for c in common])), 3)}


def cases_for(which, splits_json, sealed_json):
    S = json.load(open(sealed_json))
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    sp = json.load(open(splits_json))
    cases = []
    if which in ('val', 'both'):
        cases += sorted(sp['val'])
    if which in ('open36', 'both'):
        cases += sorted(S['open_icx_test'])
    bad = sorted(set(cases) & sealed)
    if bad:
        sys.exit(f'[score] REFUSING: sealed cases requested: {bad[:5]}')
    return cases


def run(pred, icx, aorta, cases, n_proc):
    with Pool(n_proc) as p:
        return p.map(score_case, [(c, pred, icx, aorta) for c in cases], chunksize=1)


# ----------------------------------------------------------------------------------------- self-test
def _synthetic():
    """The tests/test_tf1.py fixture: LM -> LAD + LCx and a tapering RCA on a 0.5 mm grid, aorta box beside both."""
    shape, x0 = (110, 64, 48), 30
    segs = [(1, ((x0, 30, 20), (x0 + 15, 30, 20), 3.0, 3.0)), (2, ((x0 + 15, 30, 20), (x0 + 70, 46, 20), 2.0, 2.0)),
            (3, ((x0 + 15, 30, 20), (x0 + 70, 12, 20), 2.0, 2.0)), (4, ((x0, 54, 36), (x0 + 70, 54, 36), 3.0, 1.6))]
    g = np.indices(shape).reshape(3, -1).T.astype(float)
    ref = np.zeros(shape, np.uint8)
    best = np.full(shape, np.inf)
    for c, (a, b, ra, rb) in segs:
        a, b = np.asarray(a, float), np.asarray(b, float)
        ab = b - a
        t = np.clip((g - a) @ ab / (ab @ ab), 0, 1)
        d = np.linalg.norm(g - (a + t[:, None] * ab), axis=1).reshape(shape)
        m = d <= (ra + t * (rb - ra)).reshape(shape)
        take = m & (d < best)
        ref[take] = c
        best[take] = d[take]
    aorta = np.zeros(shape, bool)
    aorta[:x0 - 4, 4:60, 4:44] = True
    return ref, aorta, (0.5, 0.5, 0.5)


def selftest():
    check_hash()
    ref, aorta, sp = _synthetic()
    perfect = score_arrays('t', ref.copy(), ref, sp, aorta)
    assert abs(perfect['tf1'] - 1.0) < 1e-9, perfect
    assert perfect['fp_components'] == 0 and not perfect['provisional'], perfect
    cut = ref.copy()
    sl = cut[60:66]
    sl[sl == 2] = 0                                            # a 3 mm cut across the LAD: distal LAD lost
    rc = score_arrays('t', cut, ref, sp, aorta)
    assert rc['per_class']['LAD'] < 0.9 and rc['per_class']['RCA'] == 1.0, rc
    swap = ref.copy()
    swap[ref == 3] = 2                                         # LCx named LAD
    rs = score_arrays('t', swap, ref, sp, aorta)
    assert rs['per_class']['LCx'] == 0.0, rs
    blob = ref.copy()
    blob[95:105, 2:10, 2:10] = 4                               # one FP component away from the tree
    assert score_arrays('t', blob, ref, sp, aorta)['fp_components'] == 1
    noaorta = score_arrays('t', ref.copy(), ref, sp, None)
    assert noaorta['provisional'], noaorta
    # end to end through files, including the sealed refusal and paired mode
    import nibabel as nib
    with tempfile.TemporaryDirectory() as td:
        for d in ('p1', 'p2', 'icx', 'ao'):
            os.makedirs(os.path.join(td, d))
        aff = np.diag([0.5, 0.5, 0.5, 1.0])
        icx_ref = np.zeros_like(ref)
        icx_ref[ref == 1], icx_ref[ref == 2], icx_ref[ref == 3], icx_ref[ref == 4] = 1, 2, 3, 9
        for c in ('c0001', 'c0003'):
            nib.save(nib.Nifti1Image(icx_ref.astype(np.uint8), aff), os.path.join(td, 'icx', f'{int(c[1:]) + 1}.coronary.nii.gz'))
            nib.save(nib.Nifti1Image(ref, aff), os.path.join(td, 'p1', f'{c}.nii.gz'))
            nib.save(nib.Nifti1Image(cut if c == 'c0003' else ref, aff), os.path.join(td, 'p2', f'{c}.nii.gz'))
            nib.save(nib.Nifti1Image(aorta.astype(np.uint8), aff), os.path.join(td, 'ao', f'{c}_aorta.nii.gz'))
        r1 = run(os.path.join(td, 'p1'), os.path.join(td, 'icx'), os.path.join(td, 'ao'), ['c0001', 'c0003'], 2)
        r2 = run(os.path.join(td, 'p2'), os.path.join(td, 'icx'), os.path.join(td, 'ao'), ['c0001', 'c0003'], 2)
        s1 = summarise(r1)
        assert s1['macro_tf1'] == 1.0 and s1['n_decisive'] == 2, s1
        pr = paired(r1, r2)
        assert pr['n'] == 2 and pr['mean_diff_run2_minus_run1'] < 0, pr
        sp_json = os.path.join(td, 'splits.json')
        json.dump({'val': ['c0001'], 'train': [], 'test': ['c0002']}, open(sp_json, 'w'))
        S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
        bad = os.path.join(td, 'splits_bad.json')
        json.dump({'val': [S['sealed_icx_test'][0]], 'train': [], 'test': []}, open(bad, 'w'))
        try:
            cases_for('val', bad, os.path.join(ROOT, 'trillium', 'sealed_test.json'))
            raise AssertionError('sealed case was not refused')
        except SystemExit as e:
            assert 'REFUSING' in str(e)
        assert cases_for('open36', sp_json, os.path.join(ROOT, 'trillium', 'sealed_test.json')) == sorted(S['open_icx_test'])
    print('[score] self-test passed: perfect 1.0; LAD cut', round(rc['per_class']['LAD'], 3),
          '; LCx->LAD swap 0.0; FP blob 1; no aorta provisional; files, pairing and the sealed refusal OK')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--pred'); ap.add_argument('--pair'); ap.add_argument('--icx'); ap.add_argument('--aorta')
    ap.add_argument('--sealed', default=os.path.join(ROOT, 'trillium', 'sealed_test.json'))
    ap.add_argument('--splits'); ap.add_argument('--set', default='both'); ap.add_argument('--out')
    ap.add_argument('--np', type=int, default=8)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    h = check_hash()
    cases = cases_for(a.set, a.splits, a.sealed)
    rows = run(a.pred, a.icx, a.aorta, cases, a.np)
    res = {'tf1_sha256': h, 'set': a.set, 'pred': a.pred, 'summary': summarise(rows), 'rows': rows}
    if a.pair:
        rows2 = run(a.pair, a.icx, a.aorta, cases, a.np)
        res.update(pair=a.pair, summary_pair=summarise(rows2), paired=paired(rows, rows2), rows_pair=rows2)
    json.dump(res, open(a.out, 'w'), indent=1, default=float)
    print(json.dumps({k: v for k, v in res.items() if k.startswith('summary') or k == 'paired'}, indent=1))


if __name__ == '__main__':
    main()
