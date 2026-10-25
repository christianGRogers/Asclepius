"""Crucible, Round 10: the numbers behind Crucible v11.

1. census   -- the pool by stratum and seal state (reconciles "about 347" with "198").
2. spread   -- Janus 0's per-case spread per class, from its reported bootstrap CIs (#43), against run 1's.
3. paired   -- the per-case SD of the *difference* between two trained networks on the same 80 val cases
               (run 1 vs B: two from-scratch trainings; F0 vs F1: two warm fine-tunes from B, same seed),
               the quantity a paired fine-tune comparison on the D35 set depends on.
4. a10      -- A10 power (D6) at 150/200/250 sealed patients on Janus 0's spread, with Bridge's power model
               (experiments/Bridge/wave1/power.py, unchanged) and a correlated-contrast sensitivity.
5. d35      -- minimum detectable effect of a paired comparison on n decision-set patients, with A22's seed term.

CPU only. Reads only repository files: trillium-results (val/open ImageCAS cases, never sealed ones), the seal
and pool list. Opens no image, no read and no sealed case. Usage: python3 r10_power.py > r10_power.json
"""
from __future__ import annotations

import collections
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
sys.path.insert(0, os.path.join(REPO, 'experiments', 'Bridge', 'wave1'))

from segtrain.pool_seal import ingest_patient, load_pool_seal  # noqa: E402
import power as bridge_power  # noqa: E402  (Bridge's A10 model, unchanged)

CL = {'1': 'LM', '2': 'LAD', '3': 'LCx', '4': 'RCA'}
SEAL = os.path.join(REPO, 'configs', 'segqueue14', 'sealed-pool-2026-10.json')
POOL = os.path.join(REPO, 'configs', 'segqueue14', 'pool-2026-10.txt')
TR = os.path.join(REPO, 'trillium-results')
REPORT_ONLY = {'ImageCHD', 'ImageALCAPA'}           # as experiments/Bridge/r9/reseal_d32.py
SPACING = {'ImageALCAPA', 'HOCMvalvesSeg', 'CCA200-HF'}
RESERVE = 100                                       # experiments/Bridge/wave1/common.py EXTENSION_RESERVED

# Janus 0 (icx4), val 80, #43 and vault/Plans/Experiments/icx4 - Results.md.
# Macro: r9 scorer (TotalSegmentator ostium, decisive). Per class: Delta's score_tf1 summary (expert ostium, the
# only per-class CIs published; its means are 0.010-0.011 above A1 on the left tree, its spreads are what we use).
J0_MACRO = dict(mean=0.9094, ci=(0.8802, 0.9316), n=80)
J0_CLASS = {'LM': dict(mean=0.9449, ci=(0.9235, 0.9774), n=78),
            'LAD': dict(mean=0.9035, ci=(0.8836, 0.9389), n=80),
            'LCx': dict(mean=0.8566, ci=(0.8347, 0.8939), n=80),
            'RCA': dict(mean=0.9375, ci=(0.9174, 0.9532), n=75)}
SIGMA_SEED = 0.013                                  # A22 (Round 8); used as r9_score_icx4.paired() uses it


def census():
    d = json.load(open(SEAL))
    vols = [l.strip() for l in open(POOL) if l.strip() and not l.startswith('#')]
    pat = collections.OrderedDict()
    for i, v in enumerate(vols):
        pat.setdefault(ingest_patient(v[:-len('.nii.gz')]), []).append((i, v))
    src = lambda p: p.split('__')[0]
    strat = {p: 'excluded_spacing' if src(p) in SPACING else 'report_only' if src(p) in REPORT_ONLY else 'primary'
             for p in pat}
    sealed = set(d['primary']['patients']) | set(d['report_only']['patients'])
    ext = d['primary']['extension_order']
    res = set(ext[:RESERVE])

    def state(p):
        return 'sealed' if p in sealed else 'reserve' if p in res else 'open'
    table = collections.Counter()
    vtab = collections.Counter()
    for p, vs in pat.items():
        table[(strat[p], state(p))] += 1
        vtab[(strat[p], state(p))] += len(vs)
    rows = [dict(stratum=s, state=t, patients=table[(s, t)], volumes=vtab[(s, t)]) for s, t in sorted(table)]
    prim = {t: table[('primary', t)] for t in ('sealed', 'reserve', 'open')}
    return dict(n_volumes=len(vols), n_patients=len(pat), rows=rows, primary=prim,
                non_sealed_non_imagechd=sum(v for (s, t), v in table.items()
                                             if t != 'sealed' and s != 'report_only'),
                non_sealed_primary=prim['reserve'] + prim['open'],
                open_after_seal_and_reserve=sum(v for (s, t), v in table.items() if t == 'open'),
                open_primary_after_seal_and_reserve=prim['open'],
                note_347='517 name-heuristic patients (pre-D32) - 150 sealed - 20 ImageCHD sealed = 347: a stale '
                         'count. On real patients (D32/D33) there are 468.')


def load_pc(rel):
    out = {}
    for r in json.load(open(os.path.join(TR, rel))):
        fl = {str(x) for x in (r.get('flagged_classes') or [])}
        out[r['case']] = {c: (None if c in fl else v) for c, v in r['per_class'].items()}
    return out


RUNS = {'run1': 'round6/atlas2/results/per_case_run1.json', 'B': 'round6/atlas2/results/per_case_b.json',
        'F0': 'round7/atlas3/per_case_F0.json', 'F1': 'round7/atlas3/per_case_F1.json'}


def sd_from_ci(ci, n):
    return (ci[1] - ci[0]) / (2 * 1.96) * math.sqrt(n)


def spread():
    run1 = load_pc(RUNS['run1'])
    out = {}
    for c, name in CL.items():
        x = np.array([v[c] for v in run1.values() if v.get(c) is not None])
        j = J0_CLASS[name]
        sj = sd_from_ci(j['ci'], j['n'])
        out[name] = dict(run1_sd=round(float(x.std(ddof=1)), 4), run1_n=len(x), janus0_sd_from_ci=round(sj, 4),
                         ratio=round(sj / float(x.std(ddof=1)), 2))
    m = []
    for v in run1.values():
        cl = [v[c] for c in CL if v.get(c) is not None]
        if cl:
            m.append(np.mean(cl))
    sjm = sd_from_ci(J0_MACRO['ci'], J0_MACRO['n'])
    out['macro'] = dict(run1_sd=round(float(np.std(m, ddof=1)), 4), janus0_sd_from_ci=round(sjm, 4),
                        ratio=round(sjm / float(np.std(m, ddof=1)), 2),
                        janus0_ci_asymmetry=dict(lower=round(J0_MACRO['mean'] - J0_MACRO['ci'][0], 4),
                                                 upper=round(J0_MACRO['ci'][1] - J0_MACRO['mean'], 4)))
    return out


def paired():
    A = {k: load_pc(v) for k, v in RUNS.items()}
    out = {}
    for a, b, what in [('run1', 'B', 'two from-scratch trainings (window ablation, Round 6)'),
                       ('F0', 'F1', 'two warm fine-tunes from B, same seed and data stream (Round 7)'),
                       ('B', 'F1', 'base B vs its warm fine-tune F1')]:
        cs = sorted(set(A[a]) & set(A[b]))
        res = {'what': what}
        for c, name in CL.items():
            x, y = [], []
            for k in cs:
                u, w = A[a][k].get(c), A[b][k].get(c)
                if u is not None and w is not None:
                    x.append(u)
                    y.append(w)
            x, y = np.array(x), np.array(y)
            res[name] = dict(n=len(x), sd_diff=round(float((y - x).std(ddof=1)), 4),
                             rho=round(float(np.corrcoef(x, y)[0, 1]), 3))
        x, y = [], []
        for k in cs:
            cl = [c for c in CL if A[a][k].get(c) is not None and A[b][k].get(c) is not None]
            if cl:
                x.append(np.mean([A[a][k][c] for c in cl]))
                y.append(np.mean([A[b][k][c] for c in cl]))
        x, y = np.array(x), np.array(y)
        res['macro'] = dict(n=len(x), sd_diff=round(float((y - x).std(ddof=1)), 4),
                            rho=round(float(np.corrcoef(x, y)[0, 1]), 3))
        out[f'{a}_vs_{b}'] = res
    return out


def janus0_shaped():
    """Per class: run 1's empirical per-case shape (heavy left tail kept), rescaled to Janus 0's mean and SD."""
    run1 = load_pc(RUNS['run1'])
    base = {}
    for c, name in CL.items():
        x = np.array([v[c] for v in run1.values() if v.get(c) is not None])
        z = (x - x.mean()) / x.std(ddof=1)
        j = J0_CLASS[name]
        base[name] = np.clip(j['mean'] + sd_from_ci(j['ci'], j['n']) * z, 0.0, 1.0)
    return base


def p_pass_rho(base, f, k, keep, n, rho, delta=0.0, sims=4000, seed=20261025):
    """Bridge's model with a shared case-difficulty term: model and inter-read deviations correlate at rho."""
    rng = np.random.default_rng(seed)
    passes = np.ones(sims, bool)
    per = {}
    for c, x in base.items():
        nc = max(5, int(round(n * keep[c])))
        mu = x.mean()
        i1 = rng.integers(0, len(x), (sims, nc))
        i2 = rng.integers(0, len(x), (sims, nc))
        e1, e2 = x[i1] - mu, x[i2] - mu
        model = mu + f * e1
        inter = mu + k * f * (rho * e1 + math.sqrt(1 - rho * rho) * e2)
        d = model - inter + delta
        lo = d.mean(1) - 1.96 * d.std(1, ddof=1) / math.sqrt(nc)
        p = lo > -bridge_power.MARGIN
        per[c] = round(float(p.mean()), 3)
        passes &= p
    return round(float(passes.mean()), 3), per


def a10():
    base = janus0_shaped()
    keep = {'LM': 0.85, 'LAD': 0.95, 'LCx': 0.95, 'RCA': 0.95}   # Bridge's 'reviewed' scorable shares
    rows = []
    for f in (1.0, 1.2, 1.5):
        for k in (1.0, 1.2):
            for n in (150, 200, 250):
                for delta in (0.0, -0.02):
                    ff = {c: f for c in base}
                    kk = {c: k for c in base}
                    p, per = bridge_power.p_pass(base, ff, kk, keep, n, delta)
                    pr, _ = p_pass_rho(base, f, k, keep, n, 0.5, delta)
                    rows.append(dict(f=f, k=k, n=n, delta=delta, p_all4=p, per_class=per, p_all4_rho05=pr))
    shaped = {c: dict(mean=round(float(v.mean()), 4), sd=round(float(v.std(ddof=1)), 4)) for c, v in base.items()}
    # false pass: a model 0.05 worse than a reader, f = k = 1, n = 150
    fp_, _ = bridge_power.p_pass(base, {c: 1 for c in base}, {c: 1 for c in base}, keep, 150, -0.05)
    return dict(janus0_shaped=shaped, keep=keep, rows=rows, p_pass_when_0p05_worse_n150=fp_)


def d35(pair_sd):
    """MDE (two-sided alpha 0.05, power 0.8) of a paired arm-vs-arm comparison on n patients:
    se^2 = (f * sd_diff)^2 / n + sigma_seed^2 / s (A22's seed term, as r9_score_icx4.paired() applies it,
    shared over s seeds per arm)."""
    z = 1.96 + 0.8416
    rows = []
    for label, sd in pair_sd.items():
        for f in (1.0, 1.25, 1.5):
            for s in (1, 2):
                for n in (20, 30, 35, 40, 50, 60, 80):
                    se = math.sqrt((f * sd) ** 2 / n + SIGMA_SEED ** 2 / s)
                    se_case = f * sd / math.sqrt(n)
                    rows.append(dict(contrast=label, f=f, seeds_per_arm=s, n=n, mde=round(z * se, 4),
                                     case_share_of_var=round(se_case ** 2 / se ** 2, 2)))
    return rows


def main():
    out = {'census': census(), 'spread': spread(), 'paired': paired()}
    sp, pr = out['spread'], out['paired']
    # paired SD on Janus 0's scale: the measured paired SD times Janus 0's / run 1's per-case SD ratio
    pair_sd = {
        'macro, warm-vs-warm (F0/F1) as measured': pr['F0_vs_F1']['macro']['sd_diff'],
        'macro, warm-vs-warm (F0/F1) x J0 ratio': pr['F0_vs_F1']['macro']['sd_diff'] * sp['macro']['ratio'],
        'macro, scratch-vs-scratch (run1/B) x J0 ratio': pr['run1_vs_B']['macro']['sd_diff'] * sp['macro']['ratio'],
        'LCx, scratch-vs-scratch x J0 ratio': pr['run1_vs_B']['LCx']['sd_diff'] * sp['LCx']['ratio'],
        'LCx, warm-vs-warm x J0 ratio': pr['F0_vs_F1']['LCx']['sd_diff'] * sp['LCx']['ratio'],
    }
    out['pair_sd_used'] = {k: round(v, 4) for k, v in pair_sd.items()}
    out['a10'] = a10()
    out['d35_mde'] = d35(pair_sd)
    json.dump(out, sys.stdout, indent=1)


if __name__ == '__main__':
    main()
