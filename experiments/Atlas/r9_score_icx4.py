"""Round 9/10 (Atlas): the decisive val-80 score of icx4's predictions, on CPU, after `./icx4 collect` (A26).

One implementation (A9): every case is scored by icx4's own in-job function, `trillium/icx4/lib/tf1_score.py`
`score_case` (the same crop, the same ostium rules, the same flag rule, the same frozen `lib/segtrain_tf1.py`), and
summarised by icx4's own `report.tf1_summary` (the same decisive definition: non-provisional cases, flagged trees
left out per class, A1a/A1b). This script only chooses the cases (val 80 or open-36, never a sealed one), supplies
the inputs (predictions, ImageCAS-X, aortas, CT from icx4's layout.json) and adds per-class Dice (report only, A28).

A26: before its val numbers decide anything, its open-36 rows must equal the in-job `tf1_per_case.json`, per case
and per class (`r10_read_icx4.py` checks this). That holds when both read the same predictions, aortas and CT.

  * metric: `src/segtrain/tf1.py` and icx4's copy must both carry the A1c hash 24441cf8…5254, or it refuses;
  * reference: ImageCAS-X as drawn (D8), collapsed to four classes by `territory.to_four` (D25);
  * ostium: A1, the TotalSegmentator aorta (`<aorta dir>/<case>_aorta.nii.gz`; icx4 makes them for val 80 + open 80);
    the CT (from `layout.json`) adds the `pool_thick` cross-check rule exactly as in the job. A case without an aorta
    is provisional (A1a). Without the CT the cross-check differs from the job's and A26 will (correctly) fail;
  * cases: `--set val` (splits.json val, 80), `open36` (sealed_test.json open_icx_test), or `both`. Any sealed case
    (ImageCAS-X or quality-0) is refused.
Paired mode (`--pair DIR2`): a second run on the same cases, the paired difference of the decisive case scores with
case and seed-inclusive CIs and the one-pair sigma_seed estimate (A22).

Usage (the Master plan's commands; `--layout` defaults to <dir of --splits>/layout.json):
  python r9_score_icx4.py --pred $W/predictions --icx $W/icx --aorta $W/aorta --splits $W/splits.json \
      --set val|open36|both --out OUT.json [--layout $W/layout.json] [--pair DIR2] [--np 8]
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
LIB = os.path.join(ROOT, 'trillium', 'icx4', 'lib')
sys.path.insert(0, LIB)
sys.path.insert(0, os.path.join(ROOT, 'src'))

import tf1_score  # noqa: E402  (icx4's in-job scorer; imports the frozen lib/segtrain_tf1.py after a hash check)
import report     # noqa: E402  (icx4's in-job summary: the decisive definition)

PINNED = '24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254'   # A1c, Round 8
TF1_PATH = os.path.join(ROOT, 'src', 'segtrain', 'tf1.py')
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}


def check_hash():
    """Both copies of the metric must be the frozen one (A1c, A9)."""
    h = hashlib.sha256(open(TF1_PATH, 'rb').read()).hexdigest()
    if h != PINNED:
        sys.exit(f'[score] REFUSING: {TF1_PATH} sha256 {h} != pinned A1c {PINNED}')
    if tf1_score.TF1_SHA256 != PINNED or tf1_score.tf1_hash() != PINNED:
        sys.exit(f'[score] REFUSING: icx4 lib/segtrain_tf1.py is not the pinned A1c {PINNED}')
    tf1_score.load_metric()
    return h


def dice(a, b):
    s = int(a.sum()) + int(b.sum())
    return None if s == 0 else 2.0 * int((a & b).sum()) / s


def _dice_row(pred_path, icx_path):
    import nibabel as nib
    from territory import to_four
    pred = np.asarray(nib.load(pred_path).dataobj).astype(np.uint8)
    li = nib.load(icx_path)
    ref = to_four(np.asarray(li.dataobj).astype(np.int64), li.header.get_zooms()[:3]).astype(np.uint8)
    return {'tree': dice(pred > 0, ref > 0), **{NAMES[k]: dice(pred == k, ref == k) for k in NAMES}}


def score_case(args):
    """One case through icx4's own score_case (+ Dice). Errors are rows, never exceptions."""
    case, pred_dir, icx_dir, aorta_dir, ct_path = args
    p = os.path.join(pred_dir, f'{case}.nii.gz')
    if not os.path.exists(p):
        return {'case': case, 'error': 'prediction missing'}
    icx_path = os.path.join(icx_dir, f'{int(case[1:]) + 1}.coronary.nii.gz')
    try:
        if tf1_score.T is None:
            tf1_score.load_metric()
        r = tf1_score.score_case(case, p, icx_path,
                                 aorta_path=os.path.join(aorta_dir, f'{case}_aorta.nii.gz') if aorta_dir else None,
                                 ct_path=ct_path)
        r['dice'] = _dice_row(p, icx_path)
        return r
    except Exception as e:  # noqa: BLE001 - one bad case must not stop the report
        return {'case': case, 'error': repr(e)[:300]}


def ok_rows(rows):
    return [r for r in rows if 'error' not in r]


def boot_ci(x, n=10000, seed=0):
    x = np.asarray(x, float)
    if len(x) < 2:
        return [None, None]
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), (n, len(x)))].mean(1)
    return [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)]


def summarise(rows):
    """icx4's report.tf1_summary (the in-job decisive definition), plus a bootstrap CI and Dice (report only)."""
    ok = ok_rows(rows)
    out = report.tf1_summary(ok, [r for r in rows if 'error' in r])
    dec = [d for d in (report.decisive_case_score(r) for r in ok) if d is not None]
    out['decisive_macro_tf1_ci'] = boot_ci(dec)
    out['dice_mean'] = {k: round(float(np.mean(v)), 4) for k in ['tree'] + list(NAMES.values())
                        if (v := [r['dice'][k] for r in ok if r['dice'][k] is not None])}
    return out


def paired(rows1, rows2, sigma_prior=0.013):
    a = {r['case']: report.decisive_case_score(r) for r in ok_rows(rows1)}
    b = {r['case']: report.decisive_case_score(r) for r in ok_rows(rows2)}
    common = sorted(c for c in set(a) & set(b) if a[c] is not None and b[c] is not None)
    diff = [b[c] - a[c] for c in common]
    if not diff:
        return {'n': 0}
    m = float(np.mean(diff))
    se_case = float(np.std(diff, ddof=1) / np.sqrt(len(diff))) if len(diff) > 1 else float('nan')
    se_seed = float(np.sqrt(se_case ** 2 + sigma_prior ** 2))
    fa = {r['case']: r['fp_components'] for r in ok_rows(rows1)}
    fb = {r['case']: r['fp_components'] for r in ok_rows(rows2)}
    return {'n': len(common), 'mean_diff_run2_minus_run1': round(m, 4), 'case_ci': boot_ci(diff),
            'seed_inclusive_ci': [round(m - 1.96 * se_seed, 4), round(m + 1.96 * se_seed, 4)],
            # with one pair of runs, Var(run mean difference) = 2 sigma_seed^2 + case noise; a 1-df estimate:
            'sigma_seed_estimate_1df': round(float(np.sqrt(max(m * m - se_case ** 2, 0.0) / 2.0)), 4),
            'fp_diff': round(float(np.mean([fb[c] - fa[c] for c in common])), 3)}


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


def ct_paths(layout_json):
    if layout_json and os.path.exists(layout_json):
        return {c: v.get('ct') for c, v in json.load(open(layout_json))['cases'].items()}
    return {}


def run(pred, icx, aorta, cases, n_proc, cts=None):
    cts = cts or {}
    with Pool(n_proc, initializer=tf1_score.load_metric, maxtasksperchild=4) as p:
        return p.map(score_case, [(c, pred, icx, aorta, cts.get(c)) for c in cases], chunksize=1)


# ----------------------------------------------------------------------------------------- self-test
def synthetic():
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


def write_case(W, c, pred, ref, aorta, ct=None, aff=None):
    """Write one synthetic case in icx4's workdir layout (predictions/, icx/, aorta/, ct/)."""
    import nibabel as nib
    aff = np.diag([0.5, 0.5, 0.5, 1.0]) if aff is None else aff
    for d in ('predictions', 'icx', 'aorta', 'ct'):
        os.makedirs(os.path.join(W, d), exist_ok=True)
    icx = np.zeros_like(ref)
    for four, x in ((1, 1), (2, 2), (3, 3), (4, 9)):   # ImageCAS-X values: LM 1, LAD 2, LCx 3, RCA 9
        icx[ref == four] = x
    nib.save(nib.Nifti1Image(icx.astype(np.uint8), aff), os.path.join(W, 'icx', f'{int(c[1:]) + 1}.coronary.nii.gz'))
    nib.save(nib.Nifti1Image(pred.astype(np.uint8), aff), os.path.join(W, 'predictions', f'{c}.nii.gz'))
    if aorta is not None:
        nib.save(nib.Nifti1Image(aorta.astype(np.uint8), aff), os.path.join(W, 'aorta', f'{c}_aorta.nii.gz'))
    if ct is None:
        ct = np.zeros(ref.shape, np.float32)
        ct[aorta if aorta is not None else np.zeros(ref.shape, bool)] = 400.0
        ct[ref > 0] = 400.0
    p = os.path.join(W, 'ct', f'{c}.nii.gz')
    nib.save(nib.Nifti1Image(ct.astype(np.float32), aff), p)
    return p


def selftest():
    check_hash()
    ref, aorta, _ = synthetic()
    cut = ref.copy()
    sl = cut[60:66]
    sl[sl == 2] = 0                                            # a 3 mm cut across the LAD: distal LAD lost
    swap = ref.copy()
    swap[ref == 3] = 2                                         # LCx named LAD
    blob = ref.copy()
    blob[95:105, 2:10, 2:10] = 4                               # one FP component away from the tree
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    val = ['c0001', 'c0003', 'c0004', 'c0005']                 # never sealed (checked below)
    assert not set(val) & set(S['sealed_icx_test'])
    with tempfile.TemporaryDirectory() as W:
        cts = {}
        for c, p in zip(val, (ref, cut, swap, blob)):
            cts[c] = write_case(W, c, p, ref, aorta)
        json.dump({'val': val, 'train': [], 'test': []}, open(os.path.join(W, 'splits.json'), 'w'))
        json.dump({'cases': {c: {'ct': cts[c]} for c in val}}, open(os.path.join(W, 'layout.json'), 'w'))
        rows = {r['case']: r for r in run(os.path.join(W, 'predictions'), os.path.join(W, 'icx'),
                                          os.path.join(W, 'aorta'), val, 2, cts)}
        assert all('error' not in r for r in rows.values()), rows
        assert abs(rows['c0001']['tf1'] - 1.0) < 1e-9 and rows['c0001']['fp_components'] == 0
        assert not rows['c0001']['provisional'] and rows['c0001']['has_ct']
        assert rows['c0003']['per_class']['LAD'] < 0.9 and rows['c0003']['per_class']['RCA'] == 1.0
        assert rows['c0004']['per_class']['LCx'] == 0.0
        assert rows['c0005']['fp_components'] == 1
        assert rows['c0001']['dice']['tree'] == 1.0
        s = summarise(list(rows.values()))
        assert s['n_decisive_cases'] == 4 and s['fp_components_mean'] == 0.25, s
        # identical inputs give identical rows to the in-job function itself (A26 by construction)
        r_job = tf1_score.score_case('c0003', os.path.join(W, 'predictions', 'c0003.nii.gz'),
                                     os.path.join(W, 'icx', '4.coronary.nii.gz'),
                                     aorta_path=os.path.join(W, 'aorta', 'c0003_aorta.nii.gz'), ct_path=cts['c0003'])
        assert {k: v for k, v in rows['c0003'].items() if k != 'dice'} == r_job
        pr = paired(list(rows.values()), [dict(r, per_class={**r['per_class'], 'LM': 0.0}) for r in rows.values()])
        assert pr['n'] == 4 and pr['mean_diff_run2_minus_run1'] < 0, pr
        bad = os.path.join(W, 'splits_bad.json')
        json.dump({'val': [S['sealed_icx_test'][0]], 'train': [], 'test': []}, open(bad, 'w'))
        try:
            cases_for('val', bad, os.path.join(ROOT, 'trillium', 'sealed_test.json'))
            raise AssertionError('sealed case was not refused')
        except SystemExit as e:
            assert 'REFUSING' in str(e)
    print('[score] self-test passed: in-job rows reproduced; perfect 1.0; LAD cut', round(rows['c0003']['per_class']['LAD'], 3),
          '; LCx->LAD swap 0.0; FP blob 1; pairing and the sealed refusal OK')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--pred'); ap.add_argument('--pair'); ap.add_argument('--icx'); ap.add_argument('--aorta')
    ap.add_argument('--sealed', default=os.path.join(ROOT, 'trillium', 'sealed_test.json'))
    ap.add_argument('--splits'); ap.add_argument('--set', default='both'); ap.add_argument('--out')
    ap.add_argument('--layout', help='icx4 layout.json (CT paths); default: next to --splits')
    ap.add_argument('--np', type=int, default=8)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    h = check_hash()
    cases = cases_for(a.set, a.splits, a.sealed)
    layout = a.layout or os.path.join(os.path.dirname(os.path.abspath(a.splits)), 'layout.json')
    cts = ct_paths(layout)
    if not cts:
        print(f'[score] WARNING: no layout.json at {layout}: scoring without CT, so the pool_thick cross-check '
              'differs from the job and A26 will fail', flush=True)
    rows = run(a.pred, a.icx, a.aorta, cases, a.np, cts)
    res = {'tf1_sha256': h, 'set': a.set, 'pred': a.pred, 'aorta': a.aorta, 'layout': layout if cts else None,
           'summary': summarise(rows), 'rows': rows}
    if a.pair:
        rows2 = run(a.pair, a.icx, a.aorta, cases, a.np, cts)
        res.update(pair=a.pair, summary_pair=summarise(rows2), paired=paired(rows, rows2), rows_pair=rows2)
    json.dump(res, open(a.out, 'w'), indent=1, default=float)
    print(json.dumps({k: v for k, v in res.items() if k.startswith('summary') or k == 'paired'}, indent=1))


if __name__ == '__main__':
    main()
