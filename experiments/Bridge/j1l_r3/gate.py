"""Bridge, Janus 1-L round 3 (#302, Round 2 ruling §5 item 6): a reference implementation of `collect`'s gate.

`experiments/Crucible/j1l_r1/decide.py gate` is not the gate (L-A17: G3 as written, FP outside H1, no -0.015
branch). This file implements the plan in force, so #306 can import it or check its own gate against it:
  L-A5   H1 -> H2 -> H3, fixed sequence, paired by case, bootstrap 10 000 (seed 0), percentile bounds;
  H1     one-sided lower bound of mean paired delta decisive macro tF1 > -0.02, AND no class mean delta < -0.03,
         AND L3 holds, AND the candidate's FP components per case <= 1;
  L3     (L-A17, on the scorer's per-class `recall`) for no class: 10 %-trimmed mean delta < -0.02, or
         (mean delta < -0.02 and the 95 % upper bound < 0). The excess kurtosis of each class's delta is printed;
  H2     lower bound of mean paired delta whole-tree Dice > 0;      H3   lower bound of delta macro tF1 > 0;
  Q4     (D46 Q4 + D49 Q-R2-3) H1 passes, H2 fails: adopted iff the tF1 lower bound > -0.015 AND the upper bound of
         delta whole-tree Dice >= 0 (lumen width not shown worse);
  L-A16  the verdict and its wording of record, with brackets filled; the share sentence when the Janus 0 at t_C
         rows are given; CONSORT form (two-sided CI printed beside every margin);
  L-A18  --alpha 0.025 for Janus 1-L.1 (C), 0.0125 for Janus 1-L.2 (S). Alpha sets the decision bounds (H1's
         macro bound, Q4's bound, Q-R2-3's Dice bound, H2, H3). L3's 95 % bound is a guard and stays as L-A17
         fixes it.
Inputs are r9_score_icx4.py JSONs (`rows`). Cases must be exactly the locked 100 (pin checked), never a sealed id.
A looks ledger (--ledger) refuses a second look of the same model.

Usage:
  python gate.py --base J0_argmax.json --cand C_tC.json --model "Janus 1-L.1" --alpha 0.025 \
      [--j0tc J0_tC.json] [--ledger looks.json] > gate.json
  python gate.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CLASSES = ('LM', 'LAD', 'LCx', 'RCA')
LOCKED_PIN = 'bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895'
NB, SEED = 10000, 0


def locked_ids():
    sp = json.load(open(os.path.join(REPO, 'experiments/Delta/j1l_r1/janus1_split_proposal.json')))
    L = sorted(sp['locked100'])
    assert hashlib.sha256('\n'.join(L).encode()).hexdigest() == LOCKED_PIN, 'locked-100 pin mismatch'
    se = json.load(open(os.path.join(REPO, 'trillium/sealed_test.json')))
    return set(L), set(se['sealed_icx_test']) | set(se['sealed_quality0'])


def rows_ok(rows, check=True):
    R = {r['case']: r for r in rows if 'error' not in r}
    if check:
        locked, sealed = locked_ids()
        bad = sorted(set(R) - locked) + sorted(set(R) & sealed)
        if bad:
            sys.exit(f'[gate] REFUSING: cases outside the locked 100 or sealed: {bad[:5]}')
    return R


def decisive(r):
    if r.get('provisional'):
        return None
    v = [x for c, x in r['per_class'].items() if c not in r.get('flagged_classes', [])]
    return statistics.mean(v) if v else None


def boot(d, alpha):
    d = np.asarray(d, float)
    rng = np.random.default_rng(SEED)
    m = d[rng.integers(0, len(d), (NB, len(d)))].mean(1)
    return (float(np.mean(d)), float(np.percentile(m, 100 * alpha)), float(np.percentile(m, 100 * (1 - alpha))),
            float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)))


def pair(A, B, f):
    d = []
    for c in sorted(set(A) & set(B)):
        a, b = f(A[c]), f(B[c])
        if a is not None and b is not None:
            d.append(b - a)
    return d


def trimmed(x, g=0.10):
    x = np.sort(np.asarray(x, float)); k = int(round(g * len(x)))
    return float(x[k:len(x) - k].mean())


def kurt(x):
    x = np.asarray(x, float)
    s = x.std()
    return float(((x - x.mean()) ** 4).mean() / s ** 4 - 3) if s > 0 else 0.0


def cls_val(c, key):
    def f(r):
        if key == 'per_class' and (r.get('provisional') or c in r.get('flagged_classes', [])):
            return None
        return r.get(key, {}).get(c)
    return f


def gate(base_rows, cand_rows, alpha=0.025, j0tc_rows=None, check=True):
    A, B = rows_ok(base_rows, check), rows_ok(cand_rows, check)
    out = {'alpha_one_sided': alpha, 'n_base': len(A), 'n_cand': len(B)}
    tf = boot(pair(A, B, decisive), alpha)
    dc = boot(pair(A, B, lambda r: r['dice']['tree']), alpha)
    out['tf1'] = dict(mean=round(tf[0], 4), lb=round(tf[1], 4), ub=round(tf[2], 4), ci95=[round(tf[3], 4), round(tf[4], 4)],
                      n=len(pair(A, B, decisive)))
    out['dice'] = dict(mean=round(dc[0], 4), lb=round(dc[1], 4), ub=round(dc[2], 4), ci95=[round(dc[3], 4), round(dc[4], 4)])
    out['class_mean_delta'] = {c: round(float(np.mean(pair(A, B, cls_val(c, 'per_class')) or [0])), 4) for c in CLASSES}
    l3 = {}
    for c in CLASSES:
        d = pair(A, B, cls_val(c, 'recall'))
        if not d:
            continue
        m, _, _, lo95, hi95 = boot(d, 0.025)
        tm = trimmed(d)
        l3[c] = dict(trimmed_mean=round(tm, 4), mean=round(m, 4), ub95=round(hi95, 4), excess_kurtosis=round(kurt(d), 2),
                     fires=bool(tm < -0.02 or (m < -0.02 and hi95 < 0)))
    out['L3'] = l3
    fp = float(np.mean([r['fp_components'] for r in B.values()]))
    out['fp_per_case'] = round(fp, 3)
    fails = []
    if not tf[1] > -0.02:
        fails.append('tF1 margin')
    worst = min(out['class_mean_delta'], key=out['class_mean_delta'].get)
    if out['class_mean_delta'][worst] < -0.03:
        fails.append(f'class guard ({worst})')
    fails += [f'L3 ({c})' for c, v in l3.items() if v['fires']]
    if fp > 1.0:
        fails.append('FP guard')
    h1 = not fails
    h2 = h1 and dc[1] > 0
    h3 = h2 and tf[1] > 0
    out.update(H1=h1, H1_failed_clauses=fails, H2=h2, H3=h3)
    ci = lambda v: f"95 % CI [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}]"
    T, D = out['tf1'], out['dice']
    if not h1:
        out['verdict'] = 'not adopted'
        out['wording'] = (f"Janus 1-L.1 was not shown non-inferior to Janus 0 in tree-F1 (Δ {T['mean']:+.4f}, {ci(T)}; "
                          f"margin −0.02)" + ('' if fails == ['tF1 margin'] else f" [failed: {', '.join(fails)}]")
                          + ". Janus 0 remains the model.")
    elif not h2:
        q4_tf1 = tf[1] > -0.015
        q4_dice = dc[2] >= 0                              # D49 Q-R2-3: whole-tree Dice not shown worse
        out['Q4'] = {'tf1_lb_above_-0.015': bool(q4_tf1), 'dice_not_shown_worse': bool(q4_dice)}
        if q4_tf1 and q4_dice:
            out['verdict'] = 'adopted (D46 Q4)'
            out['wording'] = (f"Janus 1-L is non-inferior to Janus 0 in tree-F1 at a pre-specified margin of 0.015 "
                              f"(Δ {T['mean']:+.4f}, {ci(T)}), and passed the class, recall and FP guards (smallest class "
                              f"mean Δ: {worst}, {out['class_mean_delta'][worst]:+.4f}). It is not shown better in lumen "
                              f"width (whole-tree Dice Δ {D['mean']:+.4f}, {ci(D)}) or in tree-F1. Adopted for its larger "
                              f"training set.")
        elif q4_tf1:
            out['verdict'] = 'not adopted (Q-R2-3: lumen width shown worse)'
            out['wording'] = (f"Non-inferior to Janus 0 in tree-F1 at 0.015 (Δ {T['mean']:+.4f}, {ci(T)}), but its "
                              f"whole-tree Dice is shown worse (Δ {D['mean']:+.4f}, {ci(D)}). Janus 0 remains.")
        else:
            out['verdict'] = 'not adopted'
            out['wording'] = (f"Non-inferior to Janus 0 at 0.02 (Δ {T['mean']:+.4f}, {ci(T)}) but not at the 0.015 that "
                              f"D46 Q4 requires for adoption without a width gain; not shown better. Janus 0 remains.")
    else:
        out['verdict'] = 'adopted'
        w = (f"Janus 1-L is better than Janus 0 in lumen width: whole-tree Dice {D['mean']:+.4f} ({ci(D)}). Its tree-F1 is "
             f"non-inferior at 0.02 (Δ {T['mean']:+.4f}, lower bound {T['lb']:+.4f}), with the class, recall and FP "
             f"guards passed.")
        w += (f" … and better in tree-F1 (Δ {T['mean']:+.4f}, lower bound {T['lb']:+.4f} > 0)." if h3
              else " A tree-F1 gain was not shown.")
        out['wording'] = w
    if j0tc_rows is not None:
        J = rows_ok(j0tc_rows, check)
        num = float(np.mean(pair(A, J, lambda r: r['dice']['tree'])))
        s = num / dc[0] if dc[0] > 0 else float('nan')
        out['share_s'] = round(s, 3)
        out['share_sentence'] = ('Most of the width gain is the export threshold, which applies to Janus 0 as well; the '
                                 f'fine-tune adds {1 - s:.2f}.' if s >= 0.8 else 'Most of the width gain is the fine-tune.'
                                 if s <= 0.2 else 'The threshold and the fine-tune each contribute.')
        if out['verdict'] == 'adopted':
            out['wording'] += ' ' + out['share_sentence']
    return out


# ----------------------------------------------------------------------------------------- self-test
def fake(n, rng, tf1_delta=0.0, dice_delta=0.0, recall_delta=None, fp=0.3, sd=0.04, base=None, z=None):
    """Synthetic rows: base rows if base is None, else candidate rows = base + deltas (+ case noise z * sd)."""
    rows = []
    for i in range(n):
        c = f'x{i:03d}'
        if base is None:
            rows.append(dict(case=c, provisional=False, flagged_classes=[], fp_components=fp,
                             per_class={k: 0.9 for k in CLASSES}, recall={k: 0.9 for k in CLASSES}, dice={'tree': 0.88}))
            continue
        b = base[i]
        e = (z[i] if z is not None else rng.normal()) * sd
        rec = {k: b['recall'][k] + (recall_delta.get(k, lambda i: 0.0)(i) if recall_delta else 0.0) for k in CLASSES}
        rows.append(dict(case=c, provisional=False, flagged_classes=[], fp_components=fp,
                         per_class={k: b['per_class'][k] + tf1_delta + e for k in CLASSES}, recall=rec,
                         dice={'tree': b['dice']['tree'] + dice_delta + 0.5 * e}))
    return rows


def selftest():
    rng = np.random.default_rng(1)
    n = 100
    z = rng.normal(size=n); z = (z - z.mean()) / z.std(ddof=1)          # exact mean 0, SD 1
    base = fake(n, rng)
    # LB = m - ~1.645 * sd / 10 at alpha 0.025?  bootstrap percentile at 2.5 % one-sided: m - 1.96 * sd / 10.
    sd = 0.04
    cand = lambda m, dd=0.0, **k: fake(n, rng, tf1_delta=m, dice_delta=dd, base=base, z=z, sd=sd, **k)
    # 1. LB about -0.017, H2 fails -> not adopted
    g = gate(base, cand(-0.017 + 1.96 * sd / 10, dd=-0.004), check=False)
    assert -0.0185 < g['tf1']['lb'] < -0.0155, g['tf1']
    assert g['H1'] and not g['H2'] and g['verdict'] == 'not adopted', g
    # 2. LB about -0.012, H2 fails, Dice CI straddles 0 -> adopted (Q4)
    g = gate(base, cand(-0.012 + 1.96 * sd / 10, dd=-0.001), check=False)
    assert -0.0135 < g['tf1']['lb'] < -0.0105, g['tf1']
    assert g['verdict'] == 'adopted (D46 Q4)', g
    # 3. the same, but Dice shown worse -> not adopted (D49 Q-R2-3)
    g = gate(base, cand(-0.012 + 1.96 * sd / 10, dd=-0.02), check=False)
    assert g['dice']['ub'] < 0 and g['verdict'].startswith('not adopted (Q-R2-3'), g
    # 4. FP 1.2 per case fails H1
    g = gate(base, cand(0.01, dd=0.02, fp=1.2), check=False)
    assert not g['H1'] and 'FP guard' in g['H1_failed_clauses'], g
    # 5. a uniform -0.03 LCx recall loss fires L3
    g = gate(base, cand(0.01, dd=0.02, recall_delta={'LCx': lambda i: -0.03}), check=False)
    assert g['L3']['LCx']['fires'] and not g['H1'], g['L3']
    # 6. a heavy-tailed null mostly does not fire L3 (t3 noise, SD 0.05 as measured)
    fires = 0
    for k in range(100):
        r2 = np.random.default_rng(100 + k)
        noise = r2.standard_t(3, size=(4, n)) * 0.05 / np.sqrt(3)
        rd = {c: (lambda i, a=noise[j]: float(a[i])) for j, c in enumerate(CLASSES)}
        g = gate(base, fake(n, r2, tf1_delta=0.01, dice_delta=0.02, base=base, z=z, sd=sd, recall_delta=rd), check=False)
        fires += any(v['fires'] for v in g['L3'].values())
    assert fires <= 25, fires
    # 7. H1 + H2 + H3 and the share sentence
    g = gate(base, cand(0.02, dd=0.03), j0tc_rows=fake(n, rng, dice_delta=0.027, base=base, z=np.zeros(n)), check=False)
    assert g['H3'] and g['verdict'] == 'adopted' and g['share_s'] >= 0.8 and 'export threshold' in g['wording'], g
    # 8. S's look at 1.25 %: the same data whose LB clears -0.02 at 2.5 % by a hair fails at 1.25 %
    c8 = cand(-0.02 + 1.96 * sd / 10 + 0.0005, dd=0.0)
    assert gate(base, c8, 0.025, check=False)['H1'] and not gate(base, c8, 0.0125, check=False)['H1']
    # 9. refusals: a non-locked id
    try:
        gate(base, base)
        raise AssertionError('a non-locked id was not refused')
    except SystemExit as e:
        assert 'REFUSING' in str(e)
    print(f'[gate] self-test passed (heavy-tailed null: L3 fired in {fires} of 100)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--base'); ap.add_argument('--cand'); ap.add_argument('--j0tc')
    ap.add_argument('--model', default='Janus 1-L.1'); ap.add_argument('--alpha', type=float, default=0.025)
    ap.add_argument('--ledger')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.ledger and os.path.exists(a.ledger):
        led = json.load(open(a.ledger))
        if a.model in led or len(led) >= 2:
            sys.exit(f'[gate] REFUSING: {a.model} already looked, or the track has spent its two looks: {list(led)}')
    else:
        led = {}
    res = gate(json.load(open(a.base))['rows'], json.load(open(a.cand))['rows'], a.alpha,
               json.load(open(a.j0tc))['rows'] if a.j0tc else None)
    res['model'] = a.model
    s = json.dumps(res, indent=1)
    if a.ledger:
        led[a.model] = hashlib.sha256(s.encode()).hexdigest()
        json.dump(led, open(a.ledger, 'w'), indent=1)
    print(s)


if __name__ == '__main__':
    main()
