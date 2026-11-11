"""How small a Janus 1-L gain the locked 100 can see, and how often the pre-registered rules misfire.

Measured inputs (all in the repo, val 80 = ImageCAS-X val 80, A1c-pinned tF1, A1 aortas):
  * warm replicate: atlas3 F1 - F0 (two warm fine-tunes from one start, same data, 200 epochs);
  * scratch pair:   atlas2 B - run 1 (two from-scratch trainings judged a tie in Round 8).
  * Janus 0's per-case SD from its posted CI (Atlas, Round 10): macro 0.117; LM .121 LAD .126 LCx .135 RCA .079.
No sealed case, no locked-100 score of any Janus model and no image is read.

Model: per-case tF1 of run k on case i is mu_i + delta_k + r_ki, with run noise r iid across runs. Then
SD(a - b) = sqrt(2) * sigma_r for two runs of one recipe, and a1 - J0 and a2 - J0 share J0's noise (corr 0.5).
Per-case run noise is taken from the measured pairs (optimistic) or scaled by Janus 0's larger case spread
(pessimistic: SD(delta)/SD(case) = 0.57-0.64 times 0.117).

Rules simulated (Delta v1, track 1-L, section 4):
  L1  a1 - J0 macro: lower 95 % bootstrap bound > 0, and a2 - J0 mean > 0;
  L2  no class mean delta < -0.03 (a1 - J0);
  L3  no class centreline recall (ImageCAS-X traced) delta < -0.02 (a1 - J0);
  E   ensemble(a1, a2) ships over a1 only if E - a1 lower 95 % bound > 0.
"""
import json, math, os
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT = os.path.join(os.path.dirname(__file__), 'power_locked100.json')
CLS = ['1', '2', '3', '4']
NAMES = dict(zip(CLS, ['LM', 'LAD', 'LCx', 'RCA']))
J0_SD = {'macro': 0.117, '1': 0.121, '2': 0.126, '3': 0.135, '4': 0.079}


def load(p):
    return {x['case']: x for x in json.load(open(os.path.join(ROOT, p)))}


def decisive(x, c):
    v = x['per_class'].get(c)
    return None if v is None or int(c) in x.get('flagged_classes', []) else v


def macro(x):
    """icx4 report.decisive_case_score: the mean over unflagged classes (A1b)."""
    v = [decisive(x, k) for k in CLS]
    v = [u for u in v if u is not None]
    return float(np.mean(v)) if v else None


def pair(pa, pb):
    a, b = load(pa), load(pb)
    cases = sorted(c for c in set(a) & set(b) if macro(a[c]) is not None and macro(b[c]) is not None)
    d = {'macro': np.array([macro(a[c]) - macro(b[c]) for c in cases])}
    for k in CLS:
        d[k] = np.array([(a[c]['per_class'][k] - b[c]['per_class'][k])
                         if decisive(a[c], k) is not None and decisive(b[c], k) is not None else np.nan for c in cases])
        rec = [(a[c]['split']['recall_icx_traced'].get(k), b[c]['split']['recall_icx_traced'].get(k))
               for c in cases if 'split' in a[c] and 'split' in b[c]]
        d['rec' + k] = np.array([u - v for u, v in rec if u is not None and v is not None])
    case_sd = float(np.std([macro(b[c]) for c in cases], ddof=1))
    return cases, d, case_sd


def mde(sd, n, z=2.802):  # two-sided alpha 0.05, power 0.80
    return z * sd / math.sqrt(n)


def lower_bound(x, rng, B=400):
    n = len(x)
    idx = rng.integers(0, n, size=(B, n))
    return float(np.percentile(x[idx].mean(1), 2.5))


def simulate(rng, sd_delta, cls_sd_delta, rec_sd_delta, n, effect, reps=1000, ens_gain=0.0):
    """Per-case Gaussian run noise sigma_r = sd_delta / sqrt(2), per class likewise; J0 noise shared."""
    sr = sd_delta / math.sqrt(2)
    out = dict(L1=0, L2=0, L3=0, E=0)
    for _ in range(reps):
        r0, r1, r2 = rng.normal(0, sr, (3, n))
        d1, d2 = effect + r1 - r0, effect + r2 - r0
        lb = np.percentile(d1[rng.integers(0, n, (400, n))].mean(1), 2.5)
        out['L1'] += (lb > 0) and (d2.mean() > 0)
        l2 = False
        for k in CLS:
            s = cls_sd_delta[k] / math.sqrt(2)
            c0, c1 = rng.normal(0, s, (2, n))
            l2 |= (effect + c1 - c0).mean() < -0.03
        out['L2'] += l2
        l3 = False
        for k in CLS:
            s = rec_sd_delta[k] / math.sqrt(2)
            c0, c1 = rng.normal(0, s, (2, n))
            l3 |= (c1 - c0).mean() < -0.02
        out['L3'] += l3
        de = ens_gain + (r2 - r1) / 2  # E - a1, E's run noise is the mean of the two runs
        out['E'] += np.percentile(de[rng.integers(0, n, (400, n))].mean(1), 2.5) > 0
    return {k: v / reps for k, v in out.items()}


def trim(x, f=0.10):
    """10 % trimmed mean on each side: one whole-tree flip does not move it, a uniform shortening does."""
    x = np.sort(x); k = int(len(x) * f)
    return float(x[k:len(x) - k].mean())


def recall_guard(rng, reps=4000):
    """L3 on the measured warm replicate itself, not a Gaussian: resample its per-case recall deltas, centred at 0
    (a neutral model; symmetrised as x and -x so mean, median and trimmed mean are all 0), at n = 80 and 100. 'as written' = any class mean < -0.02 (A38 G3);
    'with CI' = any class mean < -0.02 AND its 95 % upper bound < 0."""
    a = load('trillium-results/round7/atlas3/per_case_F1.json')
    b = load('trillium-results/round7/atlas3/per_case_F0.json')
    d = {}
    for k in CLS:
        x = np.array([a[c]['split']['recall_icx_traced'][k] - b[c]['split']['recall_icx_traced'][k] for c in a
                      if a[c]['split']['recall_icx_traced'].get(k) is not None
                      and b[c]['split']['recall_icx_traced'].get(k) is not None])
        d[k] = np.concatenate([x, -x])  # symmetrised: a neutral model with the measured tails
    out = {'per_class_sd': {NAMES[k]: float(np.std(d[k], ddof=1)) for k in CLS},
           'cases_with_abs_delta_over_0.3': {NAMES[k]: int(np.sum(np.abs(d[k]) > 0.3)) // 2 for k in CLS}}
    for n in (80, 100):
        written = ci = tr = 0
        tr_power = {e: 0 for e in (-0.02, -0.03)}
        for _ in range(reps):
            w = c = t = False
            for k in CLS:
                x = d[k][rng.integers(0, len(d[k]), n)]
                m, se = x.mean(), x.std(ddof=1) / math.sqrt(n)
                w |= m < -0.02
                c |= (m < -0.02) and (m + 1.96 * se < 0)
                t |= trim(x) < -0.02
            written += w; ci += c; tr += t
            # power of the trimmed rule against a uniform shortening of one class (LCx) by e
            x = d['3'][rng.integers(0, len(d['3']), n)]
            for e in tr_power:
                tr_power[e] += trim(x + e) < -0.02
        out[f'n{n}'] = {'false_alarm_as_written': written / reps, 'false_alarm_with_ci': ci / reps,
                        'false_alarm_trimmed10': tr / reps,
                        'trimmed10_detects_uniform_LCx_recall_loss': {str(e): v / reps for e, v in tr_power.items()}}
    return out


def main():
    rng = np.random.default_rng(20261111)
    pairs = {'warm_replicate_F1_minus_F0': ('trillium-results/round7/atlas3/per_case_F1.json',
                                            'trillium-results/round7/atlas3/per_case_F0.json'),
             'scratch_pair_B_minus_run1': ('trillium-results/round6/atlas2/results/per_case_b.json',
                                           'trillium-results/round6/atlas2/results/per_case_run1.json')}
    res = {'measured': {}, 'mde': {}, 'simulation': {}}
    for name, (pa, pb) in pairs.items():
        cases, d, case_sd = pair(pa, pb)
        m = {'n': len(cases), 'mean_delta_macro': float(d['macro'].mean()),
             'sd_delta_macro': float(np.std(d['macro'], ddof=1)), 'sd_case_macro': case_sd,
             'ratio_sd_delta_to_sd_case': float(np.std(d['macro'], ddof=1) / case_sd),
             'lower95_bootstrap': lower_bound(d['macro'], rng)}
        for k in CLS:
            x = d[k][~np.isnan(d[k])]
            m['sd_delta_' + NAMES[k]] = float(np.std(x, ddof=1))
            m['sd_recall_delta_' + NAMES[k]] = float(np.std(d['rec' + k], ddof=1)) if len(d['rec' + k]) > 2 else None
        res['measured'][name] = m
    w, s = res['measured']['warm_replicate_F1_minus_F0'], res['measured']['scratch_pair_B_minus_run1']
    scen = {
        'optimistic (warm replicate SD)': w['sd_delta_macro'],
        'scratch pair SD': s['sd_delta_macro'],
        'pessimistic (Janus 0 case SD x 0.64)': 0.64 * J0_SD['macro'],
    }
    for label, sd in scen.items():
        res['mde'][label] = {'sd_delta': sd, 'n80': mde(sd, 80), 'n100': mde(sd, 100),
                             'ensemble_minus_a1_n100': mde(sd / 2, 100)}
    # per-class SDs: optimistic = warm replicate; pessimistic = Janus 0 class SD x 0.64
    cls_opt = {k: w['sd_delta_' + NAMES[k]] for k in CLS}
    cls_pes = {k: 0.64 * J0_SD[k] for k in CLS}
    rec_opt = {k: (w['sd_recall_delta_' + NAMES[k]] or 0.03) for k in CLS}
    rec_pes = {k: 1.5 * rec_opt[k] for k in CLS}
    for label, sd, csd, rsd in [('optimistic', w['sd_delta_macro'], cls_opt, rec_opt),
                                ('pessimistic', 0.64 * J0_SD['macro'], cls_pes, rec_pes)]:
        for n in (80, 100):
            for eff in (0.0, 0.01, 0.02):
                key = f'{label}_n{n}_effect{eff:+.2f}'
                res['simulation'][key] = simulate(rng, sd, csd, rsd, n, eff,
                                                  ens_gain=0.005 if eff else 0.0)
    res['recall_guard_empirical'] = recall_guard(rng)
    json.dump(res, open(OUT, 'w'), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
