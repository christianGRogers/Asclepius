"""Delta, Janus 1-L round 3 (#302, Round 2 ruling §5 item 6): a reference implementation of `collect`'s decision,
for #306 to match. It is not the launcher and it scores nothing: it reads two scorer files (r9_score_icx4.py rows,
Janus 0 at argmax and the candidate as exported), and applies the plan's rules exactly as written.

  H1  lower bound of mean paired Δ decisive macro tF1 > -0.02 (one-sided alpha: 2.5 % for 1-L.1, 1.25 % for S);
      no class mean Δ tF1 < -0.03; L3 holds; candidate FP components per case <= 1 (A15)
  L3  (L-A17, on the scorer's per-class `recall`) for no class: 10 %-trimmed mean Δ < -0.02, or mean Δ < -0.02 with
      the upper bound (same alpha) < 0
  H2  lower bound of Δ whole-tree Dice > 0               (read only if H1 passes)
  H3  lower bound of Δ decisive macro tF1 > 0            (read only if H2 passes)
  Q4  (D46 Q4 + D49 Q-R2-3) H1 passes, H2 fails: adopted iff the tF1 lower bound > -0.015 AND the upper bound of
      Δ whole-tree Dice >= 0 (lumen width not shown worse)
  S   trigger (L-A18): H1 fails AND a1 and a2 at argmax both have point Δ macro tF1 < 0 AND L0 passed.
Bounds: paired bootstrap, 10 000 resamples, seed 0, percentile (as L-A5). Every number carries its two-sided CI
(CONSORT form, L-A16). The wording of record is filled in from L-A16's table.

Usage:
  python gate.py --base J0.json --cand C.json [--alpha 0.025] [--a1 A1_argmax.json --a2 A2_argmax.json --l0-pass]
  python gate.py --selftest
"""
import argparse
import json
import statistics
import sys

import numpy as np

CLASSES = ('LM', 'LAD', 'LCx', 'RCA')
NB, SEED = 10000, 0


def ok(rows):
    return {r['case']: r for r in rows if 'error' not in r}


def decisive(r):
    if r.get('provisional'):
        return None
    v = [x for c, x in r['per_class'].items() if c not in r.get('flagged_classes', [])]
    return statistics.mean(v) if v else None


def paired(base, cand, f):
    A, B = ok(base), ok(cand)
    d = [f(B[c]) - f(A[c]) for c in sorted(set(A) & set(B)) if f(A[c]) is not None and f(B[c]) is not None]
    return np.asarray(d, float)


def boot(d, alpha):
    rng = np.random.default_rng(SEED)
    m = d[rng.integers(0, len(d), (NB, len(d)))].mean(1)
    return dict(n=len(d), mean=round(float(d.mean()), 4),
                lb=round(float(np.percentile(m, 100 * alpha)), 4), ub=round(float(np.percentile(m, 100 * (1 - alpha))), 4),
                ci95=[round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)])


def trimmed(x, g=0.10):
    x = np.sort(x); k = int(round(g * len(x)))
    return float(x[k:len(x) - k].mean())


def kurt(x):
    x = np.asarray(x, float); s = x.std()
    return None if s == 0 else round(float(((x - x.mean()) ** 4).mean() / s ** 4 - 3), 2)


def gate(base, cand, alpha=0.025, a1=None, a2=None, l0_pass=True):
    tf = boot(paired(base, cand, decisive), alpha)
    dc = boot(paired(base, cand, lambda r: r['dice']['tree']), alpha)
    cls, l3 = {}, {}
    for c in CLASSES:
        dcl = paired(base, cand, lambda r, c=c: None if r.get('provisional') or c in r.get('flagged_classes', [])
                     else r['per_class'].get(c))
        cls[c] = boot(dcl, alpha) if len(dcl) else dict(n=0)
        drc = paired(base, cand, lambda r, c=c: r.get('recall', {}).get(c))
        if len(drc):
            b = boot(drc, alpha)
            fire = trimmed(drc) < -0.02 or (b['mean'] < -0.02 and b['ub'] < 0)
            l3[c] = dict(trimmed_mean=round(trimmed(drc), 4), mean=b['mean'], ub=b['ub'], excess_kurtosis=kurt(drc),
                         fires=bool(fire))
    fp = float(np.mean([r['fp_components'] for r in ok(cand).values()]))
    h1_parts = dict(macro=tf['lb'] > -0.02, classes=all(v['mean'] >= -0.03 for v in cls.values() if v['n']),
                    L3=not any(v['fires'] for v in l3.values()), fp=fp <= 1.0)
    h1 = all(h1_parts.values())
    h2 = h1 and dc['lb'] > 0
    h3 = h2 and tf['lb'] > 0
    if not h1:
        verdict, branch = 'not adopted', 'H1 fails: ' + ', '.join(k for k, v in h1_parts.items() if not v)
    elif h2:
        verdict, branch = 'adopted', 'H1+H2+H3' if h3 else 'H1+H2 (D46 Q3)'
    elif tf['lb'] > -0.015 and dc['ub'] >= 0:
        verdict, branch = 'adopted', 'H1, H2 fails, Q4 (lower bound > -0.015, Dice not shown worse)'
    elif tf['lb'] > -0.015:
        verdict, branch = 'not adopted', 'H1, H2 fails, Q4 excluded: whole-tree Dice shown worse (D49 Q-R2-3)'
    else:
        verdict, branch = 'not adopted', 'H1 at 0.02 only, below the 0.015 adoption margin (D46 Q4)'
    s_trigger = None
    if a1 is not None and a2 is not None:
        m1 = float(paired(base, a1, decisive).mean()); m2 = float(paired(base, a2, decisive).mean())
        s_trigger = dict(a1_point=round(m1, 4), a2_point=round(m2, 4), l0_pass=l0_pass,
                         fires=bool((not h1) and m1 < 0 and m2 < 0 and l0_pass))
    g5 = {c: v['mean'] for c, v in cls.items() if v['n'] and v['mean'] < -0.05}
    return dict(alpha_one_sided=alpha, tf1=tf, dice_tree=dc, per_class_tf1=cls, L3=l3, fp_per_case=round(fp, 3),
                H1=h1, H1_parts=h1_parts, H2=h2, H3=h3, verdict=verdict, branch=branch, S_trigger=s_trigger,
                G5_classes_to_list=g5)


def _rows(n, d_tf, d_dice, seed, rec=0.0, fp=0.3, heavy=False, base=False):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        b = 0.9 + 0.04 * np.random.default_rng(1000 + i).standard_normal()
        e = 0.0 if base else (rng.standard_t(2) * 0.01 if heavy else 0.02 * rng.standard_normal())
        out.append(dict(case=f'c{i:04d}', provisional=False, flagged_classes=[],
                        per_class={c: float(b + (0 if base else d_tf) + e) for c in CLASSES},
                        recall={c: float(0.95 + (0 if base else (rec if c == 'LCx' else 0.0) + e)) for c in CLASSES},
                        fp_components=fp,
                        dice={'tree': float(0.88 + (0 if base else d_dice) + (0 if base else 0.01 * rng.standard_normal()))}))
    return out


def selftest():
    B = _rows(100, 0, 0, 0, base=True)
    # L3: a uniform -0.03 LCx recall loss fires; a heavy-tailed null mostly does not
    g = gate(B, _rows(100, 0.0, 0.01, 1, rec=-0.03))
    assert g['L3']['LCx']['fires'] and not g['H1'], g['L3']
    fires = sum(gate(B, _rows(100, 0.0, 0.0, s, heavy=True))['L3']['LCx']['fires'] for s in range(40))
    assert fires <= 6, fires
    # Q4 branch: lower bound about -0.017 -> not adopted; about -0.012 -> adopted (H2 failing in both)
    def find(target, d_dice):
        for s in range(400):
            c = _rows(100, target, d_dice, 50 + s)
            r = gate(B, c)
            if r['H1'] and not r['H2']:
                return r
    r1 = find(-0.0130, 0.0); r2 = find(-0.0080, 0.0)
    assert r1 is not None and r2 is not None
    assert r1['tf1']['lb'] <= -0.015 and r1['verdict'] == 'not adopted', r1['tf1']
    assert r2['tf1']['lb'] > -0.015 and r2['verdict'] == 'adopted', r2['tf1']
    # D49 Q-R2-3: the same tF1 but Dice shown worse -> not adopted
    r3 = gate(B, _rows(100, -0.0080, -0.01, 7))
    assert r3['H1'] and r3['dice_tree']['ub'] < 0 and r3['verdict'] == 'not adopted' and 'Q-R2-3' in r3['branch'], r3
    # FP of 1.2 per case fails H1
    r4 = gate(B, _rows(100, 0.01, 0.02, 3, fp=1.2))
    assert not r4['H1'] and not r4['H1_parts']['fp']
    # H1 + H2: adopted under Q3
    r5 = gate(B, _rows(100, 0.0, 0.02, 4))
    assert r5['H2'] and r5['verdict'] == 'adopted'
    # S trigger: both members below Janus 0 at argmax and H1 failing
    bad = _rows(100, -0.04, 0.0, 5)
    r6 = gate(B, bad, a1=_rows(100, -0.01, 0, 8), a2=_rows(100, -0.005, 0, 9))
    assert r6['S_trigger']['fires']
    r7 = gate(B, bad, a1=_rows(100, -0.01, 0, 8), a2=_rows(100, 0.005, 0, 9))
    assert not r7['S_trigger']['fires']
    # alpha 1.25 % gives a wider (lower) bound than 2.5 %
    c = _rows(100, 0.0, 0.0, 11)
    assert gate(B, c, alpha=0.0125)['tf1']['lb'] < gate(B, c)['tf1']['lb']
    print(f'[gate] self-test passed: L3 fires on a uniform -0.03 LCx loss, {fires}/40 on a heavy-tailed null; '
          f'lb {r1["tf1"]["lb"]} -> not adopted, lb {r2["tf1"]["lb"]} -> adopted (Q4); Dice shown worse -> not '
          'adopted (Q-R2-3); FP 1.2 fails H1; S trigger needs both members < 0; 1.25 % bound wider')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--base'); ap.add_argument('--cand'); ap.add_argument('--alpha', type=float, default=0.025)
    ap.add_argument('--a1'); ap.add_argument('--a2'); ap.add_argument('--l0-pass', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    L = lambda p: json.load(open(p))['rows'] if p else None  # noqa: E731
    print(json.dumps(gate(L(a.base), L(a.cand), a.alpha, L(a.a1), L(a.a2), a.l0_pass), indent=1))


if __name__ == '__main__':
    sys.exit(main())
