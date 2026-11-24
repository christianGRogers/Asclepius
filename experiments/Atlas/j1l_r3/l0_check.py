"""Atlas, Janus 1-L round 3: L0, the identity check (L-A8), read in full from Job 0's `identity_val80.json`.

L0 has three clauses. The master plan (§5, "When it has ended") asks the lead to post the `summary` and `paired`
blocks of `r9_score_icx4.py --pred $W/thr/t0.50 --pair $J0/pred_fir`. Those blocks hold clauses 1 and 2, but not
clause 3: `paired` gives the mean per-case difference and its CI, not the share of cases that agree within 0.01.
This reads the rows the scorer already writes (`rows`: Trillium; `rows_pair`: Fir) and prints all three:

  1. Trillium's val-80 decisive macro tF1 = 0.909 +- 0.003;
  2. each class's decisive tF1 within 0.01 of LM 0.945, LAD 0.903, LCx 0.857, RCA 0.938;
  3. >= 95 % of the decisive cases have |Trillium - Fir| <= 0.01 in decisive macro tF1.
It prints counts and pass/fail only (no per-case row), so its output can be posted on #302 as it is.

Usage: python l0_check.py $W/scores/identity_val80.json
       python l0_check.py --selftest
"""
import json
import statistics
import sys

REF_MACRO, TOL_MACRO = 0.909, 0.003
REF_CLASS, TOL_CLASS = {'LM': 0.945, 'LAD': 0.903, 'LCx': 0.857, 'RCA': 0.938}, 0.01
AGREE, AGREE_SHARE = 0.01, 0.95


def decisive(r):
    if r['provisional']:
        return None
    v = [x for c, x in r['per_class'].items() if c not in r['flagged_classes']]
    return statistics.mean(v) if v else None


def check(res):
    s = res['summary']
    m = s['decisive_macro_tf1']
    c1 = m is not None and abs(m - REF_MACRO) <= TOL_MACRO + 1e-12
    pc = {c: s['decisive_per_class'][c]['tf1'] for c in REF_CLASS}
    c2 = {c: v is not None and abs(v - REF_CLASS[c]) <= TOL_CLASS + 1e-12 for c, v in pc.items()}
    a = {r['case']: decisive(r) for r in res['rows'] if 'error' not in r}
    b = {r['case']: decisive(r) for r in res.get('rows_pair', []) if 'error' not in r}
    common = [c for c in sorted(set(a) & set(b)) if a[c] is not None and b[c] is not None]
    n_agree = sum(abs(a[c] - b[c]) <= AGREE + 1e-12 for c in common)
    share = n_agree / len(common) if common else 0.0
    c3 = bool(common) and share >= AGREE_SHARE
    errors = sum('error' in r for r in res['rows']) + sum('error' in r for r in res.get('rows_pair', []))
    out = dict(macro=m, macro_pass=c1, per_class=pc, per_class_pass=c2, n_paired=len(common), n_agree=n_agree,
               agree_share=round(share, 4), agree_pass=c3, n_errors=errors,
               L0=bool(c1 and all(c2.values()) and c3 and errors == 0))
    return out


def selftest():
    def row(c, v, prov=False):
        return dict(case=c, provisional=prov, flagged_classes=[], per_class={k: v for k in REF_CLASS})
    rows = [row(f'c{i:04d}', 0.9) for i in range(80)]
    pair = [row(f'c{i:04d}', 0.9 + (0.02 if i < 3 else 0.0)) for i in range(80)]
    summ = dict(decisive_macro_tf1=0.909, decisive_per_class={k: {'tf1': v} for k, v in REF_CLASS.items()})
    r = check(dict(summary=summ, rows=rows, rows_pair=pair))
    assert r['L0'] and r['n_agree'] == 77, r                    # 77/80 = 0.9625
    pair = [row(f'c{i:04d}', 0.9 + (0.02 if i < 5 else 0.0)) for i in range(80)]
    assert not check(dict(summary=summ, rows=rows, rows_pair=pair))['agree_pass']   # 75/80 = 0.9375
    s2 = dict(summ, decisive_macro_tf1=0.905)
    assert not check(dict(summary=s2, rows=rows, rows_pair=rows))['L0']
    s3 = dict(summ, decisive_per_class=dict(summ['decisive_per_class'], LCx={'tf1': 0.845}))
    assert not check(dict(summary=s3, rows=rows, rows_pair=rows))['L0']
    assert not check(dict(summary=summ, rows=rows))['L0']       # no Fir rows: clause 3 cannot pass
    print('[l0] self-test passed: 77/80 agree passes, 75/80 fails; macro and class tolerances; missing pair fails')


if __name__ == '__main__':
    if sys.argv[1:2] == ['--selftest']:
        selftest()
    else:
        print(json.dumps(check(json.load(open(sys.argv[1]))), indent=1))
