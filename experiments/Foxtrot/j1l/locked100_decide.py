"""Foxtrot, track 1-L: the pre-registered locked-100 decision (Foxtrot v1 §4), applied to two scorer outputs.

Inputs are two JSON files written by experiments/Atlas/r9_score_icx4.py (A1 ostia, pinned tF1): one for Janus 0, one
for the candidate, either with --set val on a splits file whose val is the locked 100 (the plan's commands) or with
--set both (val 80 + open-36). Only the locked 100 are used: the non-open-36 rows (val 80) plus the 20 open-36 ids in
results/locked100.json; any other open-36 case is dropped (the candidate trained on it).
A sealed id anywhere in either file is refused.

Rule (decisive case score = report.decisive_case_score: macro tF1 @ 1.5 mm over unflagged classes, provisional out):
  d = candidate - Janus 0 per case; 95 % CI = patient bootstrap (10 000, seed 0);
  class guard: no class mean delta (unflagged in both) < -0.03;  FP: candidate FP components per case <= 1 (A15);
  BETTER          CI lower bound > 0 and guard and FP;
  NON-INFERIOR    CI lower bound > -0.01 and guard and FP (not BETTER);
  NOT ADOPTED     otherwise.
Reported, never deciding: the same on the 20 open cases alone, per-class deltas, Dice deltas if present.
Usage: python locked100_decide.py --janus0 J0.json --cand C.json --out OUT.json [--expect-val 80]
       python locked100_decide.py --selftest
"""
import argparse, json, os, statistics
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
NAMES = ('LM', 'LAD', 'LCx', 'RCA')


def dec(r):
    if r.get('provisional') or 'error' in r:
        return None
    v = [x for c, x in r['per_class'].items() if c not in r['flagged_classes'] and x is not None]
    return statistics.mean(v) if v else None


def boot(x, n=10000, seed=0):
    x = np.asarray(x, float); rng = np.random.default_rng(seed)
    b = x[rng.integers(0, len(x), (n, len(x)))].mean(1)
    return [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]


def decide(rows0, rows1, locked20, sealed, expect_val=80):
    for rows in (rows0, rows1):
        bad = sorted({r['case'] for r in rows} & sealed)
        if bad:
            raise SystemExit(f'sealed ids in a scorer output: {bad[:5]}: refusing')
    open36_all = {r['case'] for r in rows0 if r.get('set') == 'open36'}
    keep = lambda r: r['case'] in locked20 or r.get('set') == 'val'   # noqa: E731
    A = {r['case']: r for r in rows0 if keep(r)}; B = {r['case']: r for r in rows1 if keep(r)}
    n_val = sum(r.get('set') == 'val' for r in A.values())
    if n_val != expect_val or len(set(A) & locked20) != 20:
        raise SystemExit(f'expected {expect_val} val + 20 locked open cases, found {n_val} + {len(set(A) & locked20)}')
    common = sorted(c for c in set(A) & set(B) if dec(A[c]) is not None and dec(B[c]) is not None)
    d = np.array([dec(B[c]) - dec(A[c]) for c in common])
    ci = boot(d)
    per = {}
    for n in NAMES:
        v = [B[c]['per_class'][n] - A[c]['per_class'][n] for c in common
             if n in A[c]['per_class'] and n in B[c]['per_class'] and n not in A[c]['flagged_classes']
             and n not in B[c]['flagged_classes'] and A[c]['per_class'][n] is not None and B[c]['per_class'][n] is not None]
        per[n] = {'n': len(v), 'mean_delta': round(float(np.mean(v)), 4) if v else None}
    guard = all(p['mean_delta'] is None or p['mean_delta'] >= -0.03 for p in per.values())
    fp = float(np.mean([B[c]['fp_components'] for c in B]))
    if ci[0] > 0 and guard and fp <= 1:
        verdict = 'BETTER'
    elif ci[0] > -0.01 and guard and fp <= 1:
        verdict = 'NON-INFERIOR'
    else:
        verdict = 'NOT ADOPTED'
    o = [c for c in common if c in locked20]
    od = [dec(B[c]) - dec(A[c]) for c in o]
    return {'verdict': verdict, 'n_cases': len(common), 'mean_delta': round(float(d.mean()), 4),
            'ci95': [round(x, 4) for x in ci], 'per_class': per, 'class_guard_ok': guard,
            'cand_fp_per_case': round(fp, 3),
            'janus0_macro': round(float(np.mean([dec(A[c]) for c in common])), 4),
            'cand_macro': round(float(np.mean([dec(B[c]) for c in common])), 4),
            'report_only_open20': {'n': len(o), 'mean_delta': round(float(np.mean(od)), 4) if od else None},
            'dropped_trained_open16': sorted(open36_all - locked20)}


def selftest():
    rng = np.random.default_rng(1)
    locked20 = {f'c{i:04d}' for i in range(1000, 1020)}; sealed = {'c0999'}
    def rows(shift, extra=()):
        out = []
        for i in range(80):
            out.append({'case': f'c{i:04d}', 'set': 'val', 'provisional': False, 'flagged_classes': [], 'fp_components': 0,
                        'per_class': {n: float(np.clip(0.9 + 0.05 * rng.standard_normal() + shift, 0, 1)) for n in NAMES}})
        for i in range(1000, 1036):
            out.append({'case': f'c{i:04d}', 'set': 'open36', 'provisional': False, 'flagged_classes': [],
                        'fp_components': 0, 'per_class': {n: 0.9 + shift for n in NAMES}})
        return out + list(extra)
    r0 = rows(0.0)
    import copy
    r_better = copy.deepcopy(r0)
    for r in r_better:
        r['per_class'] = {k: v + 0.03 for k, v in r['per_class'].items()}
    assert decide(r0, r_better, locked20, sealed)['verdict'] == 'BETTER'
    r_same = copy.deepcopy(r0)
    out = decide(r0, r_same, locked20, sealed)
    assert out['verdict'] == 'NON-INFERIOR' and out['n_cases'] == 100 and len(out['dropped_trained_open16']) == 16
    r_lm = copy.deepcopy(r0)
    for r in r_lm:
        r['per_class']['LM'] -= 0.05; r['per_class']['LAD'] += 0.05
    assert decide(r0, r_lm, locked20, sealed)['verdict'] == 'NOT ADOPTED'          # class guard
    r_fp = copy.deepcopy(r_better)
    for r in r_fp:
        r['fp_components'] = 2
    assert decide(r0, r_fp, locked20, sealed)['verdict'] == 'NOT ADOPTED'          # A15
    try:
        decide(r0, rows(0.0, [{'case': 'c0999', 'set': 'val'}]), locked20, sealed); raise AssertionError
    except SystemExit as e:
        assert 'sealed' in str(e)
    print('[decide] self-test passed: BETTER, NON-INFERIOR, class guard, FP gate, sealed refusal, 16 trained open dropped')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true'); ap.add_argument('--janus0'); ap.add_argument('--cand')
    ap.add_argument('--out'); ap.add_argument('--expect-val', type=int, default=80)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    L = json.load(open(os.path.join(HERE, 'results', 'locked100.json')))
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    def rows_of(p):
        R = json.load(open(p))
        rows = R['rows']
        for r in rows:   # r9_score_icx4 rows carry no set label: tag them from sealed_test.json's open-36 list
            r.setdefault('set', 'open36' if r['case'] in set(S['open_icx_test']) else 'val')
        return rows
    res = decide(rows_of(a.janus0), rows_of(a.cand), set(L['locked20_from_open36']), sealed, a.expect_val)
    res.update(janus0=a.janus0, cand=a.cand)
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
