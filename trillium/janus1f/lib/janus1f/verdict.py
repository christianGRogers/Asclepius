"""V (the vessels) and the verdict table of J1F-A (master plan §3; F-A6, F-A24, F-A32).

V is track 1-L's H1 (V = H1), applied to F's collapsed vessels against a baseline (Janus 0's Fir predictions; for
V_L, Janus 1-L's shipped maps), on rows of `experiments/Atlas/r9_score_icx4.py` (the A1c scorer, icx4's aortas):
  * the one-sided 2.5 % lower bound of mean paired delta decisive macro tF1 > -0.02;
  * no class's mean delta tF1 < -0.03;
  * L3 (L-A17, on the scorer's per-class `recall`): for no class a 10 %-trimmed mean delta < -0.02, or a mean delta
    < -0.02 with its upper bound < 0;
  * the candidate's FP components per case <= 1.
Bounds: paired by case, 10 000 bootstrap resamples, seed 0, percentile. The functions are Delta's
`experiments/Delta/j1l_r3/gate.py` (H1 only), unchanged in arithmetic.

`verdict` is Atlas's `experiments/Atlas/j1f_r3/verdict.py`, ported as F-A32 asks.
"""
import statistics

import numpy as np

CLASSES = ('LM', 'LAD', 'LCx', 'RCA')
NB, SEED = 10000, 0
ALPHA = 0.025


def _ok(rows):
    return {r['case']: r for r in rows if 'error' not in r}


def decisive(r):
    if r.get('provisional'):
        return None
    v = [x for c, x in r['per_class'].items() if c not in r.get('flagged_classes', [])]
    return statistics.mean(v) if v else None


def paired(base, cand, f):
    A, B = _ok(base), _ok(cand)
    d = [f(B[c]) - f(A[c]) for c in sorted(set(A) & set(B)) if f(A[c]) is not None and f(B[c]) is not None]
    return np.asarray(d, float)


def boot(d, alpha=ALPHA):
    rng = np.random.default_rng(SEED)
    m = d[rng.integers(0, len(d), (NB, len(d)))].mean(1)
    return dict(n=len(d), mean=round(float(d.mean()), 4),
                lb=round(float(np.percentile(m, 100 * alpha)), 4),
                ub=round(float(np.percentile(m, 100 * (1 - alpha))), 4),
                ci95=[round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)])


def trimmed(x, g=0.10):
    x = np.sort(x)
    k = int(round(g * len(x)))
    return float(x[k:len(x) - k].mean())


def v_gate(base, cand, alpha=ALPHA, expect_cases=None):
    """V's four clauses. `expect_cases`: the locked ids; refuses if the paired set is not all of them."""
    if expect_cases is not None:
        A, B = _ok(base), _ok(cand)
        miss = sorted(set(expect_cases) - set(A)) + sorted(set(expect_cases) - set(B))
        if miss:
            raise ValueError(f'V: scorer rows missing for {len(miss)} locked case(s), e.g. {miss[:3]}')
    tf = boot(paired(base, cand, decisive), alpha)
    cls, l3 = {}, {}
    for c in CLASSES:
        dcl = paired(base, cand, lambda r, c=c: None if r.get('provisional') or c in r.get('flagged_classes', [])
                     else r['per_class'].get(c))
        cls[c] = boot(dcl, alpha) if len(dcl) else dict(n=0)
        drc = paired(base, cand, lambda r, c=c: r.get('recall', {}).get(c))
        if len(drc):
            b = boot(drc, alpha)
            l3[c] = dict(trimmed_mean=round(trimmed(drc), 4), mean=b['mean'], ub=b['ub'],
                         fires=bool(trimmed(drc) < -0.02 or (b['mean'] < -0.02 and b['ub'] < 0)))
    fp = float(np.mean([r['fp_components'] for r in _ok(cand).values()]))
    parts = dict(macro=tf['lb'] > -0.02, classes=all(v['mean'] >= -0.03 for v in cls.values() if v['n']),
                 L3=not any(v['fires'] for v in l3.values()), fp=fp <= 1.0)
    return dict(alpha_one_sided=alpha, tf1=tf, per_class_tf1=cls, L3=l3, fp_per_case=round(fp, 3),
                parts=parts, passed=all(parts.values()))


def verdict(v_F, b_F, b_T, l_adopted=False, v_L=None, b_TL=None, q3=None):
    """The master plan §3 tables. F-A32's table applies only when q3 == 'yes' and 1-L was adopted in time."""
    if q3 == 'yes' and l_adopted:
        if v_L is None or b_TL is None:
            raise ValueError('1-L adopted under Q-F2-3 = yes: V_L and B(T_L) must both be computed')
        if v_F and b_F:
            if v_L:
                return 'F'
            return 'T_L' if b_TL else 'F'
        if b_TL:
            return 'T_L'
        return 'T' if b_T else 'not adopted'
    if v_F and b_F:
        return 'F'
    return 'T' if b_T else 'not adopted'


def wording(ship, v_F=None, v_L=None, b_F=None):
    """The DECISION.md line for the verdict."""
    if ship == 'F' and v_L is False:
        return 'Janus 1-F.1 ships as F (1-F\'s own vessels), with "vessels below Janus 1-L" (F-A32)'
    return {'F': 'Janus 1-F.1 ships as F: 1-F\'s own vessels and names; failing classes, Ramus and D3 folded into '
                 'their parent',
            'T': 'Janus 1-F.1 ships as T: Janus 0\'s four classes by construction, named by 1-F',
            'T_L': 'Janus 1-F.1 ships as T_L: Janus 1-L\'s vessels, named by 1-F (F-A32)',
            'not adopted': 'Not adopted. Round N+1 chooses the next design; no automatic GPU run'}[ship]
