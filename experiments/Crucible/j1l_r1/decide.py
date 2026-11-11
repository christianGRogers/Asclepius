"""Crucible, Janus 1-L Round 1: the pre-registered rules, applied to experiments/Atlas/r9_score_icx4.py outputs.

Two modes, both read only the scorer's JSON (rows per case: decisive per-class tF1, flagged classes, provisional,
per-class centreline recall, FP components, whole-tree Dice).

select  -- Job 0's threshold choice on the 60 tuning cases (dev-44 + the 16 of open-36 that D45 sends to training;
           Janus 0 never trained on them). One scorer JSON per threshold. The rule (Crucible v1 §4.2):
             among t in {0.50, 0.45, 0.40, 0.35, 0.30}, keep the t with the highest mean whole-tree Dice such that
               (i)  mean decisive macro tF1 >= that of t = 0.50 minus 0.005,
               (ii) mean FP components per case <= that of t = 0.50 plus 0.10,
               (iii) no class's mean centreline recall falls (a lower t only adds voxels; a fall is a bug);
             ties (Dice within 0.002) go to the larger t. t = 0.50 always qualifies.

gate    -- the one look at the locked 100 (Crucible v1 §5): candidate vs Janus 0, both fixed predictions, paired by
           case, bootstrap 10 000, seed 0. Fixed sequence; stop at the first failure:
             H1  tF1 non-inferior: lower 95 % bound of mean paired Δ decisive macro tF1 > -0.02,
                 and no class's mean Δ < -0.03, and no class's centreline recall mean Δ < -0.02;
             H2  Dice superior:    lower 95 % bound of mean paired Δ whole-tree Dice > 0;
             H3  tF1 superior:     lower 95 % bound of mean paired Δ decisive macro tF1 > 0.
           Safety (not in the sequence, must hold to ship): FP components per case <= 1 (A15) on the locked 100.
           Verdict: ship if H1 and H2 pass and FP holds; "better than Janus 0 on tF1" only if H3 passes too.

Usage:
  python decide.py select --scores t0.50=s050.json t0.45=s045.json ... > select.json
  python decide.py gate --base janus0_locked.json --cand cand_locked.json > gate.json
  python decide.py --selftest
"""
from __future__ import annotations

import json
import statistics
import sys

import numpy as np

CLASSES = ('LM', 'LAD', 'LCx', 'RCA')


def ok(rows):
    return {r['case']: r for r in rows if 'error' not in r}


def decisive(r):
    if r['provisional']:
        return None
    v = [x for c, x in r['per_class'].items() if c not in r['flagged_classes']]
    return statistics.mean(v) if v else None


def boot_lb(x, n=10000, seed=0):
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), (n, len(x)))].mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def means(rows):
    R = ok(rows)
    dec = [d for d in (decisive(r) for r in R.values()) if d is not None]
    rec = {c: float(np.mean([r['recall'][c] for r in R.values() if c in r.get('recall', {})] or [np.nan]))
           for c in CLASSES}
    return dict(n=len(R), tf1=float(np.mean(dec)), dice=float(np.mean([r['dice']['tree'] for r in R.values()])),
                fp=float(np.mean([r['fp_components'] for r in R.values()])), recall=rec)


def select(scores):
    m = {t: means(json.load(open(p))['rows']) for t, p in scores.items()}
    base = m['0.50']
    ok_t = []
    for t, v in m.items():
        good = (v['tf1'] >= base['tf1'] - 0.005 and v['fp'] <= base['fp'] + 0.10 and
                all(v['recall'][c] >= base['recall'][c] - 1e-9 for c in CLASSES if not np.isnan(base['recall'][c])))
        v['qualifies'] = bool(good or t == '0.50')
        if v['qualifies']:
            ok_t.append(t)
    best = max(m[t]['dice'] for t in ok_t)
    chosen = max(float(t) for t in ok_t if m[t]['dice'] >= best - 0.002)
    return dict(rule='Crucible v1 section 4.2', per_threshold=m, chosen_t=f'{chosen:.2f}')


def paired(base, cand, f):
    A, B = ok(base), ok(cand)
    d = []
    for c in sorted(set(A) & set(B)):
        a, b = f(A[c]), f(B[c])
        if a is not None and b is not None:
            d.append(b - a)
    lo, hi = boot_lb(d)
    return dict(n=len(d), mean=round(float(np.mean(d)), 4), ci=[round(lo, 4), round(hi, 4)])


def gate(base_rows, cand_rows):
    tf1 = paired(base_rows, cand_rows, decisive)
    dice = paired(base_rows, cand_rows, lambda r: r['dice']['tree'])
    cls, rec = {}, {}
    for c in CLASSES:
        cls[c] = paired(base_rows, cand_rows,
                        lambda r, c=c: None if r['provisional'] or c in r['flagged_classes'] else r['per_class'].get(c))
        rec[c] = paired(base_rows, cand_rows, lambda r, c=c: r.get('recall', {}).get(c))
    fp = means(cand_rows)['fp']
    h1 = tf1['ci'][0] > -0.02 and all(v['mean'] >= -0.03 for v in cls.values() if v['n']) and \
        all(v['mean'] >= -0.02 for v in rec.values() if v['n'])
    h2 = h1 and dice['ci'][0] > 0
    h3 = h2 and tf1['ci'][0] > 0
    ship = h2 and fp <= 1.0
    return dict(tf1=tf1, dice=dice, per_class_tf1=cls, centreline_recall=rec, fp_per_case_candidate=round(fp, 3),
                H1_tf1_noninferior=h1, H2_dice_superior=h2, H3_tf1_superior=h3, fp_ok=fp <= 1.0,
                verdict=('ship; better than Janus 0 on tF1 and Dice' if ship and h3 else
                         'ship; tF1 non-inferior, Dice better' if ship else 'do not ship; Janus 0 stays'))


def selftest():
    rng = np.random.default_rng(1)

    def rows(shift_tf1, shift_dice, fp=0):
        out = []
        for i in range(100):
            base = 0.9 + 0.04 * rng.standard_normal()
            pc = {c: min(1.0, base + shift_tf1) for c in CLASSES}
            out.append(dict(case=f'c{i:04d}', provisional=False, flagged_classes=[], per_class=pc,
                            recall={c: 0.95 for c in CLASSES}, fp_components=fp,
                            dice={'tree': 0.88 + shift_dice + 0.01 * rng.standard_normal()}))
        return out
    rng = np.random.default_rng(1); b = rows(0, 0)
    rng = np.random.default_rng(1); c = rows(0, 0.03)
    g = gate(b, c)
    assert g['H1_tf1_noninferior'] and g['H2_dice_superior'] and not g['H3_tf1_superior'], g
    rng = np.random.default_rng(1); c2 = rows(-0.05, 0.03)
    assert not gate(b, c2)['H1_tf1_noninferior']
    rng = np.random.default_rng(1); c3 = rows(0, 0.03, fp=2)
    assert gate(b, c3)['verdict'].startswith('do not ship')
    print('[decide] self-test passed')


def main(argv):
    if argv[:1] == ['--selftest']:
        return selftest()
    if argv[:1] == ['select']:
        sc = dict(a.split('=', 1) for a in argv[argv.index('--scores') + 1:])
        sc = {k[1:] if k.startswith('t') else k: v for k, v in sc.items()}
        print(json.dumps(select(sc), indent=1))
    elif argv[:1] == ['gate']:
        b = json.load(open(argv[argv.index('--base') + 1]))['rows']
        c = json.load(open(argv[argv.index('--cand') + 1]))['rows']
        print(json.dumps(gate(b, c), indent=1))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
