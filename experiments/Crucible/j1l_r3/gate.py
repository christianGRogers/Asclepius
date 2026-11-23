"""Crucible, Janus 1-L round 3: the decision function `collect` runs, written to L-A5, L-A16, L-A17, L-A18 and D49.

`experiments/Crucible/j1l_r1/decide.py gate` is NOT the gate (L-A17): it applies A38's G3 as written, keeps FP outside
H1 and has no -0.015 branch. This file is the reference implementation #306's `collect` calls (or copies verbatim).
It reads only r9_score_icx4.py outputs (rows per case) and the frozen JSONs; it computes nothing from images.

The look (one per candidate; at most two in the track, L-A18):
  baseline  Janus 0 at argmax on the locked 100 (Job 0's scores/locked100_janus0_argmax.json);
  candidate C = E at t_C (Janus 1-L.1), or S at its t_C (Janus 1-L.2, --look S);
  pairing   by case. A case decides tF1 only if it is non-provisional in BOTH rows; a class counts only if it is
            unflagged in BOTH rows (A1a/A1b; flags are drawn from the reference, so the two rows should agree:
            the number of cases where they do not is printed);
  bootstrap 10 000 resamples, seed 0; each bound that GRANTS a claim is one-sided alpha (2.5 % for C, 1.25 % for S).

  H1  lower bound of Delta decisive macro tF1 > -0.02;
      no class mean Delta tF1 < -0.03;
      L3 holds: for no class (scorer's `recall`, L-A17) is the 10 %-trimmed mean Delta < -0.02, or the mean < -0.02
      with its 95 % t upper bound < 0 (as Delta measured it: 3-8 % false alarm, up to ~19 % under a broad shift);
      C's mean FP components per case <= 1.
  H2  (only if H1) lower bound of Delta whole-tree Dice > 0.
  H3  (only if H2) lower bound of Delta decisive macro tF1 > 0.
  Q4  (H1 passes, H2 fails) adopted iff the tF1 lower bound > -0.015 AND (D49 Q-R2-3) the upper bound of Delta
      whole-tree Dice >= 0 (lumen width not shown worse).

Guards versus claims at S's look (Crucible v3 §6.2, for the judge): the 1.25 % applies to the bounds that grant
adoption (H1's, H2's, H3's lower bounds and Q4's -0.015 bound). The guards that deny adoption (L3's 95 % upper bound,
Q-R2-3's Dice upper bound) keep their C-look level, so a smaller alpha never makes a guard more lenient.

Refusals: a locked-100 case missing or errored in either file; any case outside the locked 100; a sealed case;
`--rule_t`/`--select` whose sha256 differs from the posted one; a second run (the ledger file exists).

Usage:
  python gate.py --base J0.json --cand C.json --look C --select select.json --select_sha <posted> \
      --rule_t rule_t.json --rule_t_sha <posted> --identity identity_val80.json --mde mde.txt \
      --report a1_argmax=a1_t050.json a2_argmax=a2_t050.json a1_tC=a1_tC.json a2_tC=a2_tC.json j0_tC=j0_tC.json \
      --ledger $W/looks/C.done --out gate_C.json
  python gate.py --selftest
"""
from __future__ import annotations

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
B, SEED = 10000, 0
ALPHA = {'C': 0.025, 'S': 0.0125}
NAME = {'C': 'Janus 1-L.1', 'S': 'Janus 1-L.2'}
L0_REF = dict(macro=0.909, tol=0.003, cls={'LM': 0.945, 'LAD': 0.903, 'LCx': 0.857, 'RCA': 0.938}, cls_tol=0.01)
L3_TEXT = ("L3's stated false-alarm rate is 3-8 % under the measured heavy-tailed shift and up to about 19 % under "
           "a broad shift")


# ---------------------------------------------------------------- statistics
def boot(x, alpha, b=B, seed=SEED):
    x = np.asarray(x, float)
    if len(x) < 2:
        return [float('nan'), float('nan')]
    m = x[np.random.default_rng(seed).integers(0, len(x), (b, len(x)))].mean(1)
    return [float(np.percentile(m, 100 * alpha)), float(np.percentile(m, 100 * (1 - alpha)))]


def t975(n):
    try:
        from scipy.stats import t
        return float(t.ppf(0.975, n - 1))
    except Exception:  # noqa: BLE001
        return 1.984


def trimmed(x, g=0.10):
    x = np.sort(np.asarray(x, float)); k = int(round(g * len(x)))
    return float(x[k:len(x) - k].mean()) if len(x) > 2 * k else float('nan')


def ex_kurtosis(x):
    x = np.asarray(x, float)
    if len(x) < 4 or x.std() == 0:
        return 0.0
    z = (x - x.mean()) / x.std()
    return float((z ** 4).mean() - 3)


def l3_fires(d):
    """L-A5's L3 on one class's per-case recall Delta (Delta's l3_fix.py, rule 'L3')."""
    d = np.asarray(d, float)
    if len(d) < 3:
        return False, {}
    mean, tm = float(d.mean()), trimmed(d)
    ub = mean + t975(len(d)) * float(d.std(ddof=1)) / math.sqrt(len(d))
    return bool(tm < -0.02 or (mean < -0.02 and ub < 0)), dict(mean=mean, trimmed10=tm, ub95=ub)


# ---------------------------------------------------------------- pairing
def ok(rows):
    return {r['case']: r for r in rows if 'error' not in r}


def macro(r, classes):
    v = [r['per_class'][c] for c in classes if c in r['per_class']]
    return statistics.mean(v) if v else None


def pairs(base, cand):
    """Per-case paired Deltas (cand - base) under the shared A1a/A1b exclusions."""
    A, Bc = ok(base), ok(cand)
    cases = sorted(set(A) & set(Bc))
    out = dict(cases=cases, tf1={}, cls={c: {} for c in CLASSES}, rec={c: {} for c in CLASSES}, dice={},
               flag_mismatch=0, prov_mismatch=0)
    for k in cases:
        a, b = A[k], Bc[k]
        if a['provisional'] != b['provisional']:
            out['prov_mismatch'] += 1
        fa, fb = set(a['flagged_classes']), set(b['flagged_classes'])
        if fa != fb:
            out['flag_mismatch'] += 1
        if a.get('dice', {}).get('tree') is not None and b.get('dice', {}).get('tree') is not None:
            out['dice'][k] = b['dice']['tree'] - a['dice']['tree']
        if a['provisional'] or b['provisional']:
            continue
        keep = [c for c in CLASSES if c not in fa | fb and c in a['per_class'] and c in b['per_class']]
        if keep:
            out['tf1'][k] = macro(b, keep) - macro(a, keep)
        for c in keep:
            out['cls'][c][k] = b['per_class'][c] - a['per_class'][c]
            if c in a.get('recall', {}) and c in b.get('recall', {}):
                out['rec'][c][k] = b['recall'][c] - a['recall'][c]
    return out


def summary(d, alpha):
    v = list(d.values())
    if not v:
        return dict(n=0)
    lo, hi = boot(v, alpha)
    return dict(n=len(v), mean=round(float(np.mean(v)), 4), lo=round(lo, 4), hi=round(hi, 4))


def fp_mean(rows):
    return float(np.mean([r['fp_components'] for r in ok(rows).values()]))


def point_macro(base, cand):
    p = pairs(base, cand)['tf1']
    return float(np.mean(list(p.values()))) if p else float('nan')


# ---------------------------------------------------------------- the decision
def decide(base, cand, look='C', alpha_guard=0.025):
    a = ALPHA[look]
    P = pairs(base, cand)
    tf1, dice = summary(P['tf1'], a), summary(P['dice'], a)
    dice_guard = summary(P['dice'], alpha_guard)          # Q-R2-3's upper bound: a guard, kept at the C level
    cls = {c: summary(P['cls'][c], a) for c in CLASSES}
    l3 = {}
    for c in CLASSES:
        f, st = l3_fires(list(P['rec'][c].values()))
        l3[c] = dict(fires=f, **{k: round(v, 4) for k, v in st.items()},
                     excess_kurtosis=round(ex_kurtosis(list(P['rec'][c].values())), 2), n=len(P['rec'][c]))
    fp = fp_mean(cand)
    fails = []
    if not tf1['lo'] > -0.02:
        fails.append('tF1 margin')
    fails += [f'class {c} (mean Delta {cls[c]["mean"]:+.4f} < -0.03)' for c in CLASSES
              if cls[c]['n'] and cls[c]['mean'] < -0.03]
    fails += [f'L3 on {c}' for c in CLASSES if l3[c]['fires']]
    if not fp <= 1.0:
        fails.append(f'FP ({fp:.2f} per case > 1)')
    h1 = not fails
    h2 = h1 and dice['lo'] > 0
    h3 = h2 and tf1['lo'] > 0
    if not h1:
        verdict, branch = 'not adopted', 'H1 fails'
    elif h2:
        verdict, branch = 'adopted', 'H1+H2+H3' if h3 else 'H1+H2 (D46 Q3)'
    elif tf1['lo'] > -0.015 and dice_guard['hi'] >= 0:
        verdict, branch = 'adopted', 'Q4 (D46 Q4, D49 Q-R2-3)'
    elif tf1['lo'] > -0.015:
        verdict, branch = 'not adopted', 'Q4 refused: lumen width shown worse (D49 Q-R2-3)'
    else:
        verdict, branch = 'not adopted', 'H1 passes, lower bound in (-0.02, -0.015], H2 fails'
    g5 = {c: [k for k, _ in sorted(P['cls'][c].items(), key=lambda kv: kv[1])[:5]]
          for c in CLASSES if cls[c]['n'] and cls[c]['mean'] < -0.05}
    return dict(look=look, alpha=a, n_cases=len(P['cases']), flag_mismatch=P['flag_mismatch'],
                prov_mismatch=P['prov_mismatch'], tf1=tf1, dice=dice, dice_guard_ub=dice_guard['hi'],
                per_class_tf1=cls, L3=l3, fp_per_case=round(fp, 3), H1=h1, H1_failed=fails, H2=h2, H3=h3,
                branch=branch, verdict=verdict, G5=g5)


def l0(identity):
    """L-A8's identity check on Job 0's identity_val80.json (r9 scorer with --pair Fir's predictions)."""
    s = identity['summary']
    m = s['decisive_macro_tf1']
    cls = {c: s['decisive_per_class'][c]['tf1'] for c in CLASSES}
    A = ok(identity['rows'])
    Bp = ok(identity['rows_pair'])
    agree, n = 0, 0
    for k in set(A) & set(Bp):
        if A[k]['provisional'] or Bp[k]['provisional']:
            continue
        keep = [c for c in CLASSES if c not in set(A[k]['flagged_classes']) | set(Bp[k]['flagged_classes'])
                and c in A[k]['per_class'] and c in Bp[k]['per_class']]
        if keep:
            n += 1
            agree += abs(macro(A[k], keep) - macro(Bp[k], keep)) <= 0.01
    ok_m = abs(m - L0_REF['macro']) <= L0_REF['tol'] + 1e-12
    ok_c = all(cls[c] is not None and abs(cls[c] - L0_REF['cls'][c]) <= L0_REF['cls_tol'] + 1e-12 for c in CLASSES)
    ok_a = n > 0 and agree / n >= 0.95
    return dict(passed=bool(ok_m and ok_c and ok_a), macro=m, per_class=cls, agree_within_0_01=f'{agree}/{n}')


def s_trigger(g, base, reports, l0_passed):
    """L-A18: H1 fails, a1 AND a2 at argmax both below Janus 0 at the point (macro tF1), and L0 passed."""
    if g['look'] != 'C' or 'a1_argmax' not in reports or 'a2_argmax' not in reports:
        return dict(fires=False, reason='not evaluated (S look, or a member report missing)')
    d1, d2 = point_macro(base, reports['a1_argmax']), point_macro(base, reports['a2_argmax'])
    fires = (not g['H1']) and d1 < 0 and d2 < 0 and l0_passed
    return dict(fires=bool(fires), a1_argmax_point=round(d1, 4), a2_argmax_point=round(d2, 4), l0_passed=l0_passed)


def share(base, cand, j0_tc):
    dc = float(np.mean(list(pairs(base, cand)['dice'].values())))
    dj = float(np.mean(list(pairs(base, j0_tc)['dice'].values())))
    if dc <= 0:
        return None, None
    s = dj / dc
    text = ('Most of the width gain is the export threshold, which applies to Janus 0 as well; the fine-tune adds '
            f'{1 - s:.0%}.' if s >= 0.8 else 'Most of the width gain is the fine-tune.' if s <= 0.2 else
            'The threshold and the fine-tune each contribute.')
    return round(s, 3), text


def wording(g, t_c, moved, mde_line, l3_text=L3_TEXT, share_text=''):
    n, t, d = NAME[g['look']], g['tf1'], g['dice']
    ci = f"(Delta {t['mean']:+.4f}, 95 % CI [{t['lo']:+.4f}, {t['hi']:+.4f}]; margin -0.02)"
    dci = f"whole-tree Dice Delta {d['mean']:+.4f}, 95 % CI [{d['lo']:+.4f}, {d['hi']:+.4f}]"
    worst = min(CLASSES, key=lambda c: g['per_class_tf1'][c].get('mean', 9))
    smallest = f"{worst}, {g['per_class_tf1'][worst]['mean']:+.4f}"
    what = (f"a two-network ensemble of fine-tunes of Janus 0, exported at foreground threshold t_C = {t_c:.2f}"
            f" ({'moved from t* by Rule T' if moved else 't*, not moved by Rule T'})") if g['look'] == 'C' else \
        f"a from-scratch run on the 620, exported at t_C = {t_c:.2f}"
    tail = f" It is {what}. {mde_line} {l3_text}."
    b = g['branch']
    if b == 'H1 fails':
        guard = '' if g['H1_failed'] == ['tF1 margin'] else f" [failed: {', '.join(g['H1_failed'])}]"
        return f"{n} was not shown non-inferior to Janus 0 in tree-F1 {ci}{guard}. Janus 0 remains the model."
    if b.startswith('H1 passes'):
        return ("Non-inferior to Janus 0 at 0.02 but not at the 0.015 that D46 Q4 requires for adoption without a "
                "width gain; not shown better. Janus 0 remains.")
    if b.startswith('Q4 refused'):
        return (f"Non-inferior to Janus 0 in tree-F1 at 0.015 {ci}, but its lumen width is shown worse than Janus 0's "
                f"({dci}). Under D46 Q4 as amended by D49 Q-R2-3 it is not adopted. Janus 0 remains.")
    if b.startswith('Q4'):
        return (f"Janus 1-L is non-inferior to Janus 0 in tree-F1 at a pre-specified margin of 0.015 {ci}, and passed "
                f"the class, recall and FP guards (smallest class mean Delta: {smallest}). It is not shown better in "
                f"lumen width ({dci}; not shown worse) or in tree-F1. Adopted for its larger training set." + tail)
    s = (f"Janus 1-L is better than Janus 0 in lumen width: {dci}. Its tree-F1 is non-inferior at 0.02 "
         f"(Delta {t['mean']:+.4f}, lower bound {t['lo']:+.4f}), with the class, recall and FP guards passed.")
    s += (f" ... and better in tree-F1 (Delta {t['mean']:+.4f}, lower bound {t['lo']:+.4f} > 0)." if g['H3']
          else ' A tree-F1 gain was not shown.')
    return s + (f' {share_text}' if share_text else '') + tail


def parts(base, cand, ids20, alpha):
    out = {}
    for name, keep in (('val80', lambda k: k not in ids20), ('locked20', lambda k: k in ids20)):
        sub = lambda rows: [r for r in rows if keep(r['case'])]  # noqa: E731
        P = pairs(sub(base), sub(cand))
        out[name] = dict(tf1=summary(P['tf1'], alpha), dice=summary(P['dice'], alpha))
    full = pairs(base, cand)
    out['sign_reversal'] = any(np.sign(out[p]['tf1'].get('mean', 0)) != np.sign(np.mean(list(full['tf1'].values())))
                               for p in ('val80', 'locked20') if out[p]['tf1'].get('n'))
    out['note'] = 'reported, never acted on (A26)'
    return out


# ---------------------------------------------------------------- the run
def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def refuse(msg):
    sys.exit(f'[gate] REFUSING: {msg}')


def check_cases(rows, label, locked):
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    ids = {r['case'] for r in rows}
    if ids & sealed:
        refuse(f'{label}: sealed case(s) {sorted(ids & sealed)[:3]}')
    if ids != set(locked):
        refuse(f'{label}: case set is not the locked 100 (missing {len(set(locked) - ids)}, extra {len(ids - set(locked))})')
    bad = [r['case'] for r in rows if 'error' in r]
    if bad:
        refuse(f'{label}: {len(bad)} errored row(s), e.g. {bad[:3]}')


def mde_line(path, look):
    if not path:
        return 'MDE: not restated (mde_from_job0.py output not given).'
    m = json.load(open(path))['mde']['tf1, warm siblings']
    v = m['E'] if look == 'C' else [m['a1']]
    v = v if isinstance(v, list) else [v]
    hi = max(v)
    return (f"The locked 100 resolve a tree-F1 difference of about {min(v):.3f}-{hi:.3f} (80 % power)"
            + ('; this look is under-powered.' if hi > 0.025 else '.'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--base'); ap.add_argument('--cand'); ap.add_argument('--look', choices=('C', 'S'), default='C')
    ap.add_argument('--select'); ap.add_argument('--select_sha'); ap.add_argument('--rule_t'); ap.add_argument('--rule_t_sha')
    ap.add_argument('--identity'); ap.add_argument('--mde'); ap.add_argument('--report', nargs='*', default=[])
    ap.add_argument('--ledger'); ap.add_argument('--out')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.ledger:
        refuse('--ledger is required (one look per candidate)')
    if os.path.exists(a.ledger):
        refuse(f'this look has already been taken ({a.ledger} exists)')
    if sha(a.select) != a.select_sha:
        refuse('select.json differs from the sha256 posted on #302')
    if sha(a.rule_t) != a.rule_t_sha:
        refuse('rule_t.json differs from the sha256 posted on #302')
    L = json.load(open(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))
    ident = l0(json.load(open(a.identity)))
    if not ident['passed']:
        refuse(f'L0 failed ({ident}); L-A8: stop')
    base = json.load(open(a.base))['rows']; cand = json.load(open(a.cand))['rows']
    check_cases(base, 'baseline', L['locked100']); check_cases(cand, 'candidate', L['locked100'])
    reports = {}
    for kv in a.report:
        k, p = kv.split('=', 1)
        reports[k] = json.load(open(p))['rows']
        check_cases(reports[k], k, L['locked100'])
    open(a.ledger, 'x').write(json.dumps(dict(look=a.look, cand=a.cand, cand_sha=sha(a.cand))))
    RT = json.load(open(a.rule_t))
    t_c, moved = float(RT['t_C']), abs(float(RT['t_C']) - float(RT['t_star'])) > 1e-9
    g = decide(base, cand, a.look)
    sh = share(base, cand, reports['j0_tC']) if 'j0_tC' in reports and g['H2'] else (None, '')
    g['share_s'] = sh[0]
    g['wording'] = wording(g, t_c, moved, mde_line(a.mde, a.look), share_text=sh[1] or '')
    g['identity'] = ident
    g['S_trigger'] = s_trigger(g, base, reports, ident['passed'])
    g['parts'] = parts(base, cand, set(L['locked20_of_open36']), ALPHA[a.look])
    rep = {}
    for k, rows in reports.items():
        P = pairs(base, rows)
        rep[k] = dict(tf1=summary(P['tf1'], 0.025), dice=summary(P['dice'], 0.025), fp=round(fp_mean(rows), 3))
    if 'a1_tC' in reports:
        P = pairs(reports['a1_tC'], cand)
        rep['E_minus_a1'] = dict(tf1=summary(P['tf1'], 0.025), dice=summary(P['dice'], 0.025))
    if 'a1_tC' in reports and 'a2_tC' in reports:
        d = point_macro(reports['a1_tC'], reports['a2_tC'])
        rep['sigma_g'] = dict(value=round(abs(d) / math.sqrt(2), 4), a2_minus_a1=round(d, 4),
                              A37_rule=abs(d) > 0.02)
    g['reports'] = rep
    g['inputs'] = dict(select_sha=a.select_sha, rule_t_sha=a.rule_t_sha, base_sha=sha(a.base), cand_sha=sha(a.cand))
    s = json.dumps(g, indent=1, default=float)
    open(a.out, 'w').write(s)
    print(json.dumps({k: g[k] for k in ('look', 'branch', 'verdict', 'H1', 'H1_failed', 'H2', 'H3', 'tf1', 'dice',
                                         'S_trigger', 'wording')}, indent=1, default=float))


# ---------------------------------------------------------------- self-test
def fake(n=100, tf1=0.0, dice=0.0, rec=None, fp=0, seed=1, base=None, noise_tf1=0.038, noise_dice=0.012,
         heavy=False, cases=None):
    """Rows like r9_score_icx4.py's. With base=None, a baseline; else a candidate paired to it."""
    rng = np.random.default_rng(seed)
    rec = rec or {}
    out = []
    for i in range(n):
        k = cases[i] if cases else f'c{i:04d}'
        if base is None:
            pc = {c: float(np.clip(0.9 + 0.05 * rng.standard_normal(), 0, 1)) for c in CLASSES}
            out.append(dict(case=k, provisional=False, flagged_classes=[], per_class=pc,
                            recall={c: 0.9 for c in CLASSES}, fp_components=0, dice={'tree': 0.85}))
            continue
        b = base[i]
        e = rng.standard_normal()
        pc = {c: b['per_class'][c] + tf1 + noise_tf1 * e for c in CLASSES}
        r = {}
        for c in CLASSES:
            if heavy:     # mostly 0, a few trees flip between rooted and cut (the measured shape)
                x = 0.003 * rng.standard_normal() + (rng.random() < 0.06) * rng.choice([-1, 1]) * rng.uniform(0.2, 0.6)
            else:
                x = 0.01 * rng.standard_normal()
            r[c] = b['recall'][c] + rec.get(c, 0.0) + x
        out.append(dict(case=k, provisional=False, flagged_classes=[], per_class=pc, recall=r, fp_components=fp,
                        dice={'tree': b['dice']['tree'] + dice + noise_dice * rng.standard_normal()}))
    return out


def shift_to_lb(base, cand, target, alpha=0.025):
    """Shift the candidate's tF1 so that the bootstrap lower bound equals `target` (for the -0.017 / -0.012 fixtures)."""
    lo = summary(pairs(base, cand)['tf1'], alpha)['lo']
    return [dict(r, per_class={c: v + (target - lo) for c, v in r['per_class'].items()}) for r in cand]


def selftest():
    import tempfile
    b = fake()
    # 1. a neutral width gain: H1 and H2 pass, H3 does not
    g = decide(b, fake(dice=0.02, base=b))
    assert g['H1'] and g['H2'] and not g['H3'] and g['verdict'] == 'adopted', g['branch']
    # 2. L-A21 #9: lower bound -0.017 with H2 failing -> not adopted; -0.012 -> adopted (Q4)
    c = fake(dice=0.0, base=b, noise_tf1=0.03)
    g = decide(b, shift_to_lb(b, c, -0.017))
    assert g['H1'] and not g['H2'] and g['verdict'] == 'not adopted' and '(-0.02, -0.015]' in g['branch'], g['branch']
    g = decide(b, shift_to_lb(b, c, -0.012))
    assert g['H1'] and not g['H2'] and g['verdict'] == 'adopted' and g['branch'].startswith('Q4 ('), g['branch']
    # 3. D49 Q-R2-3: the same tF1 with Dice shown worse -> not adopted
    cw = [dict(r, dice={'tree': r['dice']['tree'] - 0.01}) for r in shift_to_lb(b, c, -0.012)]
    g = decide(b, cw)
    assert g['dice_guard_ub'] < 0 and g['verdict'] == 'not adopted' and 'Q-R2-3' in g['branch'], g['branch']
    # 4. L-A21 #9: FP of 1.2 per case fails H1
    g = decide(b, [dict(r, fp_components=(1 if i % 5 else 2)) for i, r in enumerate(fake(dice=0.02, base=b))])
    assert abs(g['fp_per_case'] - 1.2) < 1e-9 and not g['H1'] and any('FP' in f for f in g['H1_failed']), g
    # 5. L-A21 #9: a uniform -0.03 LCx recall loss fires L3; a heavy-tailed null mostly does not
    g = decide(b, fake(dice=0.02, rec={'LCx': -0.03}, base=b))
    assert not g['H1'] and g['L3']['LCx']['fires'] and 'L3 on LCx' in g['H1_failed'], g['H1_failed']
    fa = np.mean([any(l3_fires([r['recall'][c] - bb['recall'][c] for r, bb in zip(fake(base=b, seed=s, heavy=True), b)])[0]
                      for c in CLASSES) for s in range(300)])
    assert fa < 0.15, fa                      # any of four classes; per class this is a few %
    # 5b. the shape G3 as written false-alarms on: three trees of 100 flip from rooted to cut (-0.8 each), the rest
    #     unchanged. Mean -0.024 < -0.02, but the trimmed mean is 0 and the 95 % upper bound is above 0: L3 holds.
    flips = np.r_[np.zeros(97), -0.8 * np.ones(3)] + 0.002 * np.random.default_rng(5).standard_normal(100)
    f, st = l3_fires(flips)
    assert st['mean'] < -0.02 and not f, st
    # 6. a class mean below -0.03 fails H1 even when the macro passes
    cc = [dict(r, per_class={**r['per_class'], 'LM': r['per_class']['LM'] - 0.04}) for r in fake(dice=0.02, base=b)]
    assert not decide(b, cc)['H1']
    # 7. S's look is stricter on claims: a lower bound between the 1.25 % and the 2.5 % bound passes C, fails S
    c2 = fake(dice=0.0, base=b, noise_tf1=0.03)
    lo25 = summary(pairs(b, c2)['tf1'], 0.025)['lo']; lo125 = summary(pairs(b, c2)['tf1'], 0.0125)['lo']
    c2 = [dict(r, per_class={k: v + (-0.02 - (lo25 + lo125) / 2) for k, v in r['per_class'].items()}) for r in c2]
    assert decide(b, c2, 'C')['H1'] and not decide(b, c2, 'S')['H1']
    # 8. the S trigger: H1 fails and both members are below at argmax; not when one member is at or above
    bad = fake(tf1=-0.04, base=b)
    g = decide(b, bad)
    assert s_trigger(g, b, {'a1_argmax': bad, 'a2_argmax': fake(tf1=-0.01, base=b, seed=3)}, True)['fires']
    assert not s_trigger(g, b, {'a1_argmax': bad, 'a2_argmax': fake(tf1=+0.01, base=b, seed=3)}, True)['fires']
    assert not s_trigger(g, b, {'a1_argmax': bad, 'a2_argmax': bad}, False)['fires']
    # 9. A1a/A1b: a class flagged in either row is out of both; a provisional case decides nothing
    b2 = [dict(r) for r in b]; b2[0] = dict(b2[0], flagged_classes=['LCx']); b2[1] = dict(b2[1], provisional=True)
    P = pairs(b2, fake(base=b))
    assert 'c0000' not in P['cls']['LCx'] and 'c0001' not in P['tf1'] and P['flag_mismatch'] == 1
    # 10. refusals: a missing case, an errored row, a sealed id
    L = json.load(open(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))['locked100']
    rows = fake(cases=L)
    check_cases(rows, 'ok', L)
    for broken in (rows[:-1], rows[:-1] + [dict(case=L[-1], error='x')]):
        try:
            check_cases(broken, 'broken', L); raise AssertionError('not refused')
        except SystemExit as e:
            assert 'REFUSING' in str(e)
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))['sealed_icx_test'][0]
    try:
        check_cases(rows[:-1] + [dict(rows[-1], case=S)], 'sealed', L); raise AssertionError('sealed not refused')
    except SystemExit as e:
        assert 'sealed' in str(e)
    # 11. L0 on an identity file: exact reference passes, a 0.004 macro miss fails
    rr = fake(); ident = dict(summary=dict(decisive_macro_tf1=0.909, decisive_per_class={c: {'tf1': v} for c, v in L0_REF['cls'].items()}),
                              rows=rr, rows_pair=rr)
    assert l0(ident)['passed']
    ident['summary']['decisive_macro_tf1'] = 0.913
    assert not l0(ident)['passed']
    # 12. the wording fills every bracket
    g = decide(b, shift_to_lb(b, c, -0.012))
    w = wording(g, 0.40, True, 'MDE line.')
    assert '[' in w and 'Adopted for its larger training set' in w and 'moved from t* by Rule T' in w
    # 13. the ledger: a second look is refused
    with tempfile.TemporaryDirectory() as W:
        led = os.path.join(W, 'C.done'); open(led, 'x').write('{}')
        try:
            open(led, 'x'); raise AssertionError('second look not refused')
        except FileExistsError:
            pass
    print(f'[gate] self-test passed: H1/H2/H3 and Q4 branches; -0.017 not adopted, -0.012 adopted (Q4); Dice shown '
          f'worse refused (Q-R2-3); FP 1.2 fails; uniform -0.03 LCx fires L3; heavy-tailed null fires on {fa:.1%} of '
          'draws (any class); S stricter on claims; S trigger; A1a/A1b pairing; refusals; L0; wording; ledger')


if __name__ == '__main__':
    main()
