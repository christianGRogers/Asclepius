"""Atlas, Janus 1-L round 3 (§5 item 6): the one look on the locked 100, as L-A5, L-A14 to L-A18 and D46/D49 say.

A reference implementation of `collect`'s gate, for #306 to import or port. It reads only scorer JSONs
(`experiments/Atlas/r9_score_icx4.py --set val --splits split_locked100.json`): rows per case with decisive per-class
tF1, flagged classes, provisional, per-class `recall` (L-A17), FP components, whole-tree Dice.

  Baseline  Janus 0 at argmax (Job 0's `scores/locked100_janus0_argmax.json`).
  Candidate C = E at t_C (Janus 1-L.1), or S at t_S (Janus 1-L.2, alpha 0.0125, L-A18).
  Pairing   by case; bootstrap 10 000 resamples, seed 0, percentile bounds; one-sided alpha per bound
            (0.025 for 1-L.1, 0.0125 for 1-L.2), so "95 % CI" is the two-sided (1 - 2 alpha) interval.
  H1        LB(Δ decisive macro tF1) > -0.02; no class mean Δ tF1 < -0.03; L3 holds; C's FP per case <= 1.
  L3        for no class: 10 %-trimmed mean Δ recall < -0.02, or (mean Δ recall < -0.02 and UB < 0). Recall is
            the scorer's `recall` on decisive trees (non-provisional case, class not flagged), as tF1 is.
  H2        LB(Δ whole-tree Dice) > 0, read only if H1 passes.
  H3        LB(Δ decisive macro tF1) > 0, read only if H2 passes.
  Verdict   L-A16's table. The Q4 row (D46 Q4 as amended by D49 Q-R2-3) adopts only if LB(Δ tF1) > -0.015 AND
            UB(Δ Dice) >= 0 ("whole-tree Dice not shown worse").
  Wording   L-A16's text with the brackets filled; the share sentence when H2 passes (needs Janus 0 at t_C);
            "under-powered" when the stated tF1 MDE (mde_from_job0.py) is above 0.025.

`collect` guards (the CLI below): the locked-100 pin (bbd9c687...5895) on both files, no sealed id, the posted
sha256 of `select.json` and of `rule_t.json`, C's t equal to rule_t.json's t_C, and a looks ledger that refuses a
second look for the same model name and caps the track at two (L-A18).

Usage:
  python gate.py --base J0_argmax.json --cand C.json --cand-t 0.40 --name "Janus 1-L.1" --alpha 0.025 \\
      --select select.json --select-sha256 <posted> --rule-t rule_t.json --rule-t-sha256 <posted> \\
      --j0-tc J0_at_tC.json --mde mde.json --ledger looks.json --out gate.json
  python gate.py --selftest
"""
import argparse
import hashlib
import json
import math
import os
import statistics
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CLASSES = ('LM', 'LAD', 'LCx', 'RCA')
PIN_LOCKED = 'bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895'
B, SEED = 10000, 0
MARGIN_H1, MARGIN_Q4, CLASS_FLOOR, L3_LIM, FP_MAX = -0.02, -0.015, -0.03, -0.02, 1.0
L3_RATE = '3-8 % (heavy-tailed shift, as measured), up to about 19 % under a broad shift'


# ------------------------------------------------------------------------------------------- the numbers
def ok(rows):
    return {r['case']: r for r in rows if 'error' not in r}


def decisive(r):
    if r['provisional']:
        return None
    v = [x for c, x in r['per_class'].items() if c not in r['flagged_classes']]
    return statistics.mean(v) if v else None


def class_val(r, c, field):
    if r['provisional'] or c in r['flagged_classes']:
        return None
    return r.get(field, {}).get(c)


def boot(d, alpha, b=B, seed=SEED):
    d = np.asarray(d, float)
    rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), (b, len(d)))].mean(1)
    return float(np.percentile(m, 100 * alpha)), float(np.percentile(m, 100 * (1 - alpha)))


def trimmed(x, g=0.10):
    x = np.sort(np.asarray(x, float))
    k = int(round(g * len(x)))
    return float(x[k:len(x) - k].mean())


def excess_kurtosis(x):
    x = np.asarray(x, float)
    s = x.std()
    return float(((x - x.mean()) ** 4).mean() / s ** 4 - 3) if s > 0 else 0.0


def deltas(A, B_, f):
    out = {}
    for c in sorted(set(A) & set(B_)):
        a, b = f(A[c]), f(B_[c])
        if a is not None and b is not None:
            out[c] = b - a
    return out


def summary(d, alpha, b=B):
    v = list(d.values())
    lo, hi = boot(v, alpha, b)
    return dict(n=len(v), mean=round(float(np.mean(v)), 4), lb=round(lo, 4), ub=round(hi, 4))


def l3(A, C, alpha, b=B):
    out = {}
    for c in CLASSES:
        d = deltas(A, C, lambda r, c=c: class_val(r, c, 'recall'))
        if len(d) < 2:
            out[c] = dict(n=len(d), fires=False)
            continue
        v = list(d.values())
        tm, m = trimmed(v), float(np.mean(v))
        ub = boot(v, alpha, b)[1]
        out[c] = dict(n=len(v), trimmed10=round(tm, 4), mean=round(m, 4), ub=round(ub, 4),
                      excess_kurtosis=round(excess_kurtosis(v), 2),
                      fires=bool(tm < L3_LIM or (m < L3_LIM and ub < 0)))
    return out


def evaluate(base_rows, cand_rows, alpha=0.025, b=B, j0_tc_rows=None, mde_tf1=None, name='Janus 1-L.1'):
    A, C = ok(base_rows), ok(cand_rows)
    tf1 = summary(deltas(A, C, decisive), alpha, b)
    cls = {c: summary(d, alpha, b) if len(d := deltas(A, C, lambda r, c=c: class_val(r, c, 'per_class'))) > 1
           else dict(n=len(d)) for c in CLASSES}
    dice_d = deltas(A, C, lambda r: r['dice']['tree'])
    dice = summary(dice_d, alpha, b)
    rec = l3(A, C, alpha, b)
    fp = float(np.mean([r['fp_components'] for r in C.values()]))
    h1_parts = dict(tf1_lb=tf1['lb'] > MARGIN_H1,
                    classes=all(v['mean'] >= CLASS_FLOOR for v in cls.values() if v.get('n', 0) > 1),
                    L3=not any(v['fires'] for v in rec.values()),
                    fp=fp <= FP_MAX)
    h1 = all(h1_parts.values())
    h2 = h1 and dice['lb'] > 0
    h3 = h2 and tf1['lb'] > 0
    q4_tf1 = tf1['lb'] > MARGIN_Q4
    q4_dice = dice['ub'] >= 0                                   # D49 Q-R2-3: not shown worse
    if not h1:
        verdict, adopted = 'not adopted (H1 fails)', False
    elif h3:
        verdict, adopted = 'adopted (H1, H2, H3)', True
    elif h2:
        verdict, adopted = 'adopted (H1, H2; D46 Q3)', True
    elif q4_tf1 and q4_dice:
        verdict, adopted = 'adopted (H1 at 0.015, not shown better; D46 Q4 as amended by D49 Q-R2-3)', True
    elif q4_tf1:
        verdict, adopted = 'not adopted (non-inferior at 0.015, but whole-tree Dice shown worse; D49 Q-R2-3)', False
    else:
        verdict, adopted = 'not adopted (non-inferior at 0.02 only; D46 Q4 needs 0.015)', False
    share = None
    if h2 and j0_tc_rows is not None:
        J = ok(j0_tc_rows)
        cases = sorted(set(A) & set(C) & set(J))
        mean = lambda R: float(np.mean([R[c]['dice']['tree'] for c in cases]))  # noqa: E731
        den = mean(C) - mean(A)
        share = round((mean(J) - mean(A)) / den, 3) if den > 0 else None
    g5 = {}
    if not h1:
        for c in CLASSES:
            d = deltas(A, C, lambda r, c=c: class_val(r, c, 'per_class'))
            if d and np.mean(list(d.values())) < -0.05:
                g5[c] = [k for k, _ in sorted(d.items(), key=lambda kv: kv[1])[:5]]
    res = dict(name=name, alpha_one_sided=alpha, n_cases=len(set(A) & set(C)), tf1=tf1, per_class_tf1=cls,
               dice=dice, L3=rec, L3_false_alarm_stated=L3_RATE, fp_per_case=round(fp, 3), H1_parts=h1_parts,
               H1=h1, H2=h2, H3=h3, verdict=verdict, adopted=adopted, share_s=share, G5=g5, mde_tf1=mde_tf1)
    res['wording'] = wording(res)
    return res


# ------------------------------------------------------------------------------------------- the words
def ci(x):
    return f"Δ {x['mean']:+.3f}, {100 - 200 * ALPHA[0]:.1f} % CI [{x['lb']:+.3f}, {x['ub']:+.3f}]"


ALPHA = [0.025]


def wording(r):
    ALPHA[0] = r['alpha_one_sided']
    n, t, d = r['name'], r['tf1'], r['dice']
    smallest = min(((c, v['mean']) for c, v in r['per_class_tf1'].items() if 'mean' in v), key=lambda kv: kv[1])
    if not r['H1']:
        failed = [k for k, v in r['H1_parts'].items() if not v]
        names = {'tf1_lb': 'the tree-F1 margin', 'classes': 'the class guard', 'L3': 'the L3 recall guard',
                 'fp': 'the FP guard'}
        s = (f"{n} was not shown non-inferior to Janus 0 in tree-F1 ({ci(t)}; margin -0.02)"
             + ('' if failed == ['tf1_lb'] else f" [failed {', '.join(names[f] for f in failed)}]")
             + ". Janus 0 remains the model.")
    elif not r['adopted'] and 'Dice shown worse' in r['verdict']:
        s = (f"{n} is non-inferior to Janus 0 in tree-F1 at 0.015 ({ci(t)}), but its lumen width is shown worse "
             f"(whole-tree Dice {ci(d)}). Not adopted (D49 Q-R2-3). Janus 0 remains.")
    elif not r['adopted']:
        s = (f"Non-inferior to Janus 0 at 0.02 ({ci(t)}) but not at the 0.015 that D46 Q4 requires for adoption "
             f"without a width gain; not shown better. Janus 0 remains.")
    elif not r['H2']:
        s = (f"Janus 1-L is non-inferior to Janus 0 in tree-F1 at a pre-specified margin of 0.015 ({ci(t)}), and "
             f"passed the class, recall and FP guards (smallest class mean Δ: {smallest[0]}, {smallest[1]:+.3f}). "
             f"It is not shown better in lumen width (whole-tree Dice {ci(d)}) or in tree-F1. "
             f"Adopted for its larger training set.")
    else:
        s = (f"Janus 1-L is better than Janus 0 in lumen width: whole-tree Dice {ci(d)}. Its tree-F1 is "
             f"non-inferior at 0.02 ({ci(t)}), with the class, recall and FP guards passed.")
        s += " It is also better in tree-F1 (lower bound > 0)." if r['H3'] else " A tree-F1 gain was not shown."
        sh = r['share_s']
        if sh is not None:
            s += (f" Most of the width gain is the export threshold, which applies to Janus 0 as well; the fine-tune "
                  f"adds {1 - sh:.2f}." if sh >= 0.8 else " Most of the width gain is the fine-tune." if sh <= 0.2
                  else " The threshold and the fine-tune each contribute.")
    if r['adopted']:
        s += f" L3's stated false-alarm rate is {L3_RATE}."
    if r['mde_tf1'] is not None and r['mde_tf1'] > 0.025:
        s += f" The look is under-powered (tF1 MDE {r['mde_tf1']:.3f})."
    return s


# ------------------------------------------------------------------------------------------- collect's guards
def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def guard_cases(rows, what):
    L = json.load(open(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    cases = sorted(r['case'] for r in rows)
    if set(cases) & (set(S['sealed_icx_test']) | set(S['sealed_quality0'])):
        sys.exit(f'[gate] REFUSING: a sealed case in {what}')
    if hashlib.sha256('\n'.join(cases).encode()).hexdigest() != PIN_LOCKED or set(cases) != set(L['locked100']):
        sys.exit(f'[gate] REFUSING: {what} is not exactly the locked 100 (pin {PIN_LOCKED[:8]}...)')


def ledger_check(path, name):
    led = json.load(open(path)) if os.path.exists(path) else {'looks': []}
    if name in [x['name'] for x in led['looks']]:
        sys.exit(f'[gate] REFUSING: {name} has already had its look ({path})')
    if len(led['looks']) >= 2:
        sys.exit('[gate] REFUSING: the track has spent its two candidate looks (L-A18)')
    return led


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--base'); ap.add_argument('--cand'); ap.add_argument('--cand-t', type=float)
    ap.add_argument('--name', default='Janus 1-L.1'); ap.add_argument('--alpha', type=float, default=0.025)
    ap.add_argument('--select'); ap.add_argument('--select-sha256')
    ap.add_argument('--rule-t'); ap.add_argument('--rule-t-sha256')
    ap.add_argument('--j0-tc'); ap.add_argument('--mde'); ap.add_argument('--ledger'); ap.add_argument('--out')
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if {'Janus 1-L.1': 0.025, 'Janus 1-L.2': 0.0125}.get(a.name) != a.alpha:
        sys.exit('[gate] REFUSING: alpha must be 0.025 for Janus 1-L.1 and 0.0125 for Janus 1-L.2 (L-A18)')
    for p, h in ((a.select, a.select_sha256), (a.rule_t, a.rule_t_sha256)):
        if not p or sha(p) != h:
            sys.exit(f'[gate] REFUSING: {p} does not match the sha256 posted on #302')
    tc = json.load(open(a.rule_t))['t_C']
    if a.cand_t is None or abs(a.cand_t - tc) > 1e-9:
        sys.exit(f'[gate] REFUSING: the candidate was exported at t = {a.cand_t}, rule_t.json says t_C = {tc}')
    led = ledger_check(a.ledger, a.name)
    base, cand = json.load(open(a.base))['rows'], json.load(open(a.cand))['rows']
    guard_cases(base, 'the baseline'); guard_cases(cand, 'the candidate')
    j0tc = json.load(open(a.j0_tc))['rows'] if a.j0_tc else None
    mde = None
    if a.mde:
        m = json.load(open(a.mde))['mde']
        mde = max(v['E'][1] if 'E' in v else v['a1'] for k, v in m.items() if k.startswith('tf1'))
    res = evaluate(base, cand, a.alpha, B, j0tc, mde, a.name)
    res['inputs'] = {k: sha(p) for k, p in (('base', a.base), ('cand', a.cand), ('select', a.select),
                                             ('rule_t', a.rule_t)) if p}
    led['looks'].append({'name': a.name, 'verdict': res['verdict'], 'cand_sha256': res['inputs']['cand']})
    json.dump(led, open(a.ledger, 'w'), indent=1)
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ('L3',)}, indent=1))


# ------------------------------------------------------------------------------------------- self-test
def fixture(seed, tf1_shift=0.0, dice_shift=0.0, fp=0, recall_shift=None, sd=0.01, n=100):
    """Baseline and candidate rows. Every paired Δ is the stated shift plus noise of exactly mean 0 and SD sd."""
    rng = np.random.default_rng(seed)

    def noise():
        z = rng.standard_normal(n)
        return (z - z.mean()) / z.std(ddof=1) * sd
    base, cand = [], []
    nt, nd = noise(), noise()
    for i in range(n):
        c = f'c{i:04d}'
        pc = {k: 0.85 + 0.05 * math.sin(i + j) for j, k in enumerate(CLASSES)}
        rc = {k: 0.9 for k in CLASSES}
        base.append(dict(case=c, provisional=False, flagged_classes=[], per_class=pc, recall=rc, fp_components=0,
                         dice={'tree': 0.88}))
        rs = {k: (recall_shift or {}).get(k, 0.0) for k in CLASSES}
        rs = {k: v[i] if isinstance(v, np.ndarray) else v for k, v in rs.items()}
        cand.append(dict(case=c, provisional=False, flagged_classes=[],
                         per_class={k: v + tf1_shift + nt[i] for k, v in pc.items()},
                         recall={k: 0.9 + rs[k] for k in CLASSES}, fp_components=fp,
                         dice={'tree': 0.88 + dice_shift + nd[i]}))
    return base, cand


def selftest():
    import tempfile
    b = 2000
    # the verdict rows of L-A16 (D46 Q3, Q4; D49 Q-R2-3)
    r = evaluate(*fixture(1, -0.015, -0.0005), b=b)                   # LB about -0.017, H2 fails
    assert r['H1'] and not r['H2'] and not r['adopted'] and 'not at the 0.015' in r['wording'], (r['tf1'], r['verdict'])
    r = evaluate(*fixture(1, -0.010, -0.0005), b=b)                   # LB about -0.012, Dice not shown worse
    assert r['H1'] and not r['H2'] and r['adopted'] and 'D46 Q4' in r['verdict'], (r['tf1'], r['dice'], r['verdict'])
    r = evaluate(*fixture(1, -0.010, -0.005), b=b)                    # the same, but Dice shown worse
    assert r['H1'] and not r['adopted'] and 'Q-R2-3' in r['verdict'], (r['dice'], r['verdict'])
    r = evaluate(*fixture(1, 0.0, 0.01), b=b, j0_tc_rows=fixture(1, 0.0, 0.009)[1])
    assert r['H2'] and not r['H3'] and r['adopted'] and r['share_s'] is not None and r['share_s'] >= 0.8, r['share_s']
    assert 'export threshold' in r['wording']
    r = evaluate(*fixture(1, 0.01, 0.01), b=b)
    assert r['H3'] and r['verdict'].startswith('adopted (H1, H2, H3)')
    r = evaluate(*fixture(1, 0.0, 0.01, fp=1.2), b=b)                 # FP of 1.2 per case fails H1
    assert not r['H1'] and not r['H1_parts']['fp'] and 'FP guard' in r['wording']
    r = evaluate(*fixture(1, 0.0, 0.01, recall_shift={'LCx': -0.03}), b=b)   # a uniform -0.03 LCx loss fires L3
    assert r['L3']['LCx']['fires'] and not r['H1']
    r = evaluate(*fixture(1, -0.04, 0.0), b=b)                        # class floor, and G5 lists cases
    assert not r['H1'] and not r['H1_parts']['classes']
    r = evaluate(*fixture(1, -0.06, 0.0), b=b)
    assert len(r['G5']['LAD']) == 5
    # S's look at 1.25 % is wider than C's at 2.5 %
    w1 = evaluate(*fixture(2, 0.0, 0.0, sd=0.03), alpha=0.025, b=b)['tf1']
    w2 = evaluate(*fixture(2, 0.0, 0.0, sd=0.03), alpha=0.0125, b=b)['tf1']
    assert w2['lb'] < w1['lb'] and w2['ub'] > w1['ub']
    # under-powered wording
    assert 'under-powered' in evaluate(*fixture(1, 0.0, 0.01), b=b, mde_tf1=0.03)['wording']
    # L3 under the heavy-tailed null: real sibling recall differences (atlas3 F1 - F0, val 80), resampled as Delta's
    # ensemble_power.draw_v does; a neutral model should rarely be failed.
    sys.path.insert(0, os.path.join(ROOT, 'experiments', 'Delta', 'j1l_r2'))
    from ensemble_power import draw_v, measured
    _, rec = measured()
    rng = np.random.default_rng(302)
    fired, reps = 0, 200
    for _ in range(reps):
        base, cand = fixture(3)
        for j, k in enumerate(CLASSES):
            v = draw_v(rng, rec[str(j + 1)], 100)
            for i in range(100):
                cand[i]['recall'][k] = 0.9 + v[i]
        fired += any(x['fires'] for x in l3(ok(base), ok(cand), 0.025, 500).values())
    null_rate = fired / reps
    assert null_rate < 0.15, null_rate
    # collect's guards
    with tempfile.TemporaryDirectory() as W:
        L = json.load(open(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))
        guard_cases([{'case': c} for c in L['locked100']], 'fixture')
        for bad in ([{'case': c} for c in L['locked100'][:99]],
                    [{'case': c} for c in L['locked100'][:99]] + [{'case': json.load(open(os.path.join(
                        ROOT, 'trillium', 'sealed_test.json')))['sealed_icx_test'][0]}]):
            try:
                guard_cases(bad, 'fixture')
                raise AssertionError('a wrong case set was not refused')
            except SystemExit as e:
                assert 'REFUSING' in str(e)
        p = os.path.join(W, 'looks.json')
        json.dump({'looks': [{'name': 'Janus 1-L.1'}]}, open(p, 'w'))
        for nm in ('Janus 1-L.1',):
            try:
                ledger_check(p, nm)
                raise AssertionError('a second look was not refused')
            except SystemExit as e:
                assert 'already' in str(e)
        ledger_check(p, 'Janus 1-L.2')
        json.dump({'looks': [{'name': 'Janus 1-L.1'}, {'name': 'Janus 1-L.2'}]}, open(p, 'w'))
        try:
            ledger_check(p, 'Janus 1-L.3')
            raise AssertionError('a third look was not refused')
        except SystemExit as e:
            assert 'two candidate looks' in str(e)
    print(f'[gate] self-test passed: L-A16 rows (Q4 at -0.012 adopted, -0.017 not, Dice shown worse not); H2/H3 and '
          f'the share sentence; FP 1.2 fails H1; uniform -0.03 LCx fires L3; heavy-tailed null fires L3 in '
          f'{null_rate:.3f} of {reps}; alpha 0.0125 wider; locked-100 pin, sealed refusal and the looks ledger')


if __name__ == '__main__':
    main()
