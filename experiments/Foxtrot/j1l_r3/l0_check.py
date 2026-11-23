"""Foxtrot, Janus 1-L round 3: L0 (the identity check, L-A8), all three clauses, from one r9 scorer file.

L0 has three clauses (Master plan - Janus 1-L, section 3):
  (1) the val-80 decisive macro tF1 of Janus 0 as re-predicted is 0.909 +/- 0.003 (#43);
  (2) each class's decisive tF1 is within 0.01 of LM 0.945, LAD 0.903, LCx 0.857, RCA 0.938;
  (3) >= 95 % of cases agree within 0.01 (decisive case score) with Fir's own predictions.
The r9 scorer's `--pair` output prints `summary` (clauses 1 and 2) and `paired` (a mean difference and CIs), but no
block gives clause 3: the share of cases within 0.01 is not printed anywhere. This script reads the scorer's JSON
(`rows` = the re-prediction, `rows_pair` = Fir's predictions) and prints all three, with one verdict line.

D50 uses L0 twice, and the script names which use it is:
  --mode fir-determinism    Job 0 ran on Fir: Fir re-predicting reproduces Fir's own predictions. It does NOT show
                            that Trillium reproduces Fir (D50).
  --mode trillium-identity  Janus 0 re-predicted on Trillium against Fir's predictions: the check D50 requires
                            before a1/a2 train on Trillium (job j0t_trillium.sh). Also what Job 0's own L0 is if
                            Job 0 ran on Trillium.

It reads only the val-80 rows. It refuses a file that holds any case outside val 80 (so it never reads a locked-20
row or a sealed case) and a file whose two row sets do not cover the same 80 cases.

Usage:
  python l0_check.py --scores $W/scores/identity_val80.json --mode trillium-identity --out $W/l0.json
  python l0_check.py --selftest
"""
import argparse
import hashlib
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
LISTS = os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')
SEALED = os.path.join(ROOT, 'trillium', 'sealed_test.json')

MACRO_REF, MACRO_TOL = 0.909, 0.003
CLASS_REF = {'LM': 0.945, 'LAD': 0.903, 'LCx': 0.857, 'RCA': 0.938}
CLASS_TOL = 0.01
CASE_TOL, CASE_SHARE = 0.01, 0.95


def val80():
    L = json.load(open(LISTS))
    return sorted(c for c in L['locked100'] if c not in L['locked20_of_open36'])


def decisive(r):
    """A1a/A1b, as icx4's report.decisive_case_score."""
    if r.get('provisional'):
        return None
    v = [x for c, x in r['per_class'].items() if c not in r.get('flagged_classes', [])]
    return statistics.mean(v) if v else None


def summary(rows):
    ok = [r for r in rows if 'error' not in r]
    dec = [d for d in (decisive(r) for r in ok) if d is not None]
    per = {}
    for c in CLASS_REF:
        v = [r['per_class'][c] for r in ok if not r.get('provisional') and c in r['per_class']
             and c not in r.get('flagged_classes', [])]
        per[c] = statistics.mean(v) if v else None
    return dict(n_rows=len(rows), n_errors=len(rows) - len(ok), n_decisive=len(dec),
                macro=statistics.mean(dec) if dec else None, per_class=per)


def check(res, mode):
    V = set(val80())
    S = json.load(open(SEALED))
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    if 'rows_pair' not in res:
        sys.exit('[l0] REFUSING: no rows_pair; run the r9 scorer with --pair <Fir predictions>')
    ids1 = {r['case'] for r in res['rows']}
    ids2 = {r['case'] for r in res['rows_pair']}
    bad = sorted((ids1 | ids2) - V) + sorted((ids1 | ids2) & sealed)
    if bad:
        sys.exit(f'[l0] REFUSING: cases outside val 80 or sealed: {bad[:5]}')
    if ids1 != V or ids2 != V:
        sys.exit(f'[l0] REFUSING: the file does not cover val 80 in both runs ({len(ids1)}, {len(ids2)} of 80)')
    s = summary(res['rows'])
    s_fir = summary(res['rows_pair'])
    a = {r['case']: decisive(r) for r in res['rows'] if 'error' not in r}
    b = {r['case']: decisive(r) for r in res['rows_pair'] if 'error' not in r}
    both = sorted(c for c in V if a.get(c) is not None and b.get(c) is not None)
    # A case decisive in one run and not the other (error, provisional) counts as a disagreement.
    agree = [c for c in both if abs(a[c] - b[c]) <= CASE_TOL + 1e-12]
    worst = sorted(both, key=lambda c: -abs(a[c] - b[c]))[:5]
    one_side = sorted(c for c in V if (a.get(c) is None) != (b.get(c) is None))
    n_ref = len(V) - sum(1 for c in V if a.get(c) is None and b.get(c) is None)
    share = len(agree) / n_ref if n_ref else 0.0
    c1 = s['macro'] is not None and abs(s['macro'] - MACRO_REF) <= MACRO_TOL + 1e-12
    c2 = {c: (v is not None and abs(v - CLASS_REF[c]) <= CLASS_TOL + 1e-12) for c, v in s['per_class'].items()}
    c3 = share >= CASE_SHARE
    ok = bool(c1 and all(c2.values()) and c3 and s['n_errors'] == 0)
    return dict(
        rule='L0 (L-A8), three clauses; D50 mode', mode=mode,
        meaning=('Fir reproduces its own predictions (determinism only; not Trillium = Fir)'
                 if mode == 'fir-determinism' else 'Trillium reproduces Fir (D50: required before a1/a2 train)'),
        clause1_macro=dict(value=round(s['macro'], 4) if s['macro'] is not None else None, ref=MACRO_REF,
                           tol=MACRO_TOL, pass_=c1),
        clause2_per_class={c: dict(value=None if v is None else round(v, 4), ref=CLASS_REF[c], pass_=c2[c])
                           for c, v in s['per_class'].items()},
        clause3_cases=dict(n_agree=len(agree), n_counted=n_ref, share=round(share, 4), need=CASE_SHARE,
                           tol=CASE_TOL, decisive_in_one_run_only=one_side,
                           largest_abs_diff=[[c, round(abs(a[c] - b[c]), 4)] for c in worst], pass_=c3),
        errors=dict(rerun=s['n_errors'], fir=s_fir['n_errors']),
        fir_predictions_summary=dict(macro=None if s_fir['macro'] is None else round(s_fir['macro'], 4),
                                     per_class={c: None if v is None else round(v, 4)
                                                for c, v in s_fir['per_class'].items()}),
        verdict='L0 PASS' if ok else 'L0 FAIL: stop (L-A8)')


def selftest():
    import random
    V = val80()
    rnd = random.Random(0)

    def rows(shift=0.0, jitter=0.0, n_off=0, err=False):
        out = []
        for i, c in enumerate(V):
            pc = {k: min(1.0, max(0.0, v + shift + rnd.uniform(-jitter, jitter))) for k, v in CLASS_REF.items()}
            if i < n_off:
                pc = {k: v - 0.05 for k, v in pc.items()}
            r = dict(case=c, provisional=False, flagged_classes=[], per_class=pc)
            if err and i == 0:
                r = dict(case=c, error='prediction missing')
            out.append(r)
        return out
    base = rows()
    res = dict(rows=base, rows_pair=[dict(r) for r in base])
    g = check(res, 'trillium-identity')
    assert g['verdict'] == 'L0 PASS' and g['clause3_cases']['share'] == 1.0, g
    # 5 of 80 cases off by 0.05: share 0.9375 < 0.95 fails clause 3, while the macro moves by only 0.003
    off = rows(n_off=5)
    g = check(dict(rows=off, rows_pair=base), 'trillium-identity')
    assert not g['clause3_cases']['pass_'] and g['verdict'].startswith('L0 FAIL'), g
    assert g['clause1_macro']['pass_'], g                          # clause 3 catches what clause 1 cannot
    # 4 of 80 off: 0.95 exactly passes
    g = check(dict(rows=rows(n_off=4), rows_pair=base), 'fir-determinism')
    assert g['clause3_cases']['pass_'], g
    # a uniform shift of 0.012 fails clause 3 and clause 2 (each class 0.012 away)
    g = check(dict(rows=rows(shift=0.012), rows_pair=base), 'trillium-identity')
    assert not g['clause3_cases']['pass_'] and not all(v['pass_'] for v in g['clause2_per_class'].values())
    # an error row fails
    g = check(dict(rows=rows(err=True), rows_pair=base), 'trillium-identity')
    assert g['verdict'].startswith('L0 FAIL'), g
    # a locked-20 case in the file is refused
    L = json.load(open(LISTS))
    try:
        check(dict(rows=base + [dict(case=L['locked20_of_open36'][0], provisional=False, flagged_classes=[],
                                     per_class=dict(CLASS_REF))], rows_pair=base), 'trillium-identity')
        raise AssertionError('a locked-20 row was not refused')
    except SystemExit as e:
        assert 'REFUSING' in str(e)
    try:
        check(dict(rows=base), 'trillium-identity')
        raise AssertionError('a file without rows_pair was not refused')
    except SystemExit as e:
        assert 'REFUSING' in str(e)
    print('[l0] self-test passed: identical runs pass; 5/80 cases off by 0.05 fail clause 3 with clause 1 passing; '
          '4/80 pass; a 0.012 shift fails; an error row fails; locked-20 and pair-less files refused')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--scores'); ap.add_argument('--out')
    ap.add_argument('--mode', choices=('fir-determinism', 'trillium-identity'))
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.scores and a.mode and a.out):
        sys.exit(__doc__)
    g = check(json.load(open(a.scores)), a.mode)
    g['scores_sha256'] = hashlib.sha256(open(a.scores, 'rb').read()).hexdigest()
    s = json.dumps(g, indent=1)
    open(a.out, 'w').write(s)
    print(s)
    print('sha256', hashlib.sha256(s.encode()).hexdigest())
    print(g['verdict'])


if __name__ == '__main__':
    main()
