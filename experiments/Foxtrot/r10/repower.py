"""Foxtrot, Round 10: (1) A31.1 -- the A10 seal re-powered on Janus 0's own val spread; (2) the power a D35
decision set buys for paired fine-tune comparisons, with the A22 seed term.

(1) Bridge's power model unchanged (experiments/Bridge/wave1/power.py: model and inter-read per-case tF1 resampled
from a real per-case distribution, pass a class when the lower 95 % bound of mean(model - inter + delta) > -0.05,
all four classes). Janus 0's per-case val file is on Fir only ($SCRATCH/icx4/r9_tf1_val.json), so its spread is
recovered from the 95 % bootstrap CIs posted on #43 (SD ~= CI width / 3.92 * sqrt(n)) and imposed on run 1's
per-case shape (the power model uses only deviations from the mean, so the shape's location does not matter).
The scorable share (keep) is the Janus 0 val share: decisive trees / 80 per class.

(2) A paired comparison of arm A against arm B on n decision patients: SE^2 = (r * f * s_d)^2 / n
+ sigma_seed^2 * (1/kA + 1/kB), where s_d is the measured SD of the per-case paired difference (paired_noise.py),
r the Janus 0 / run-1 spread ratio, f the pool / val spread ratio (A31.1), sigma_seed = 0.013 (A22), k seeds per
arm. kB = inf for a fixed, already-trained control (Janus 0 itself: a model decision, not a recipe decision).
MDE = (1.96 + 0.84) * SE (two-sided 5 %, 80 % power). Output: results/repower.json.
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'experiments', 'Bridge', 'wave1'))
from power import p_pass  # noqa: E402

CL = {'1': 'LM', '2': 'LAD', '3': 'LCx', '4': 'RCA'}
# Janus 0, val 80, decisive per-class 95 % bootstrap CIs (Delta's score_tf1.py, #43; expert ostium -- the only
# per-class CIs posted; the TotalSegmentator-ostium means differ by <= 0.011 on the left tree, RCA identical)
J0_CI = {'LM': (0.9235, 0.9774, 78), 'LAD': (0.8836, 0.9389, 80), 'LCx': (0.8347, 0.8939, 80), 'RCA': (0.9174, 0.9532, 75)}
J0_MACRO_CI = (0.8802, 0.9316, 80)          # r9 scorer, A1 as written
J0_KEEP = {'LM': 78 / 80, 'LAD': 80 / 80, 'LCx': 80 / 80, 'RCA': 75 / 80}
SIGMA_SEED = 0.013


def sd_from_ci(lo, hi, n):
    return (hi - lo) / 3.92 * math.sqrt(n)


def run1_base():
    rows = json.load(open(os.path.join(REPO, 'trillium-results/round6/atlas2/results/per_case_run1.json')))
    s = {c: [] for c in CL}
    for r in rows:
        fl = {str(x) for x in r.get('flagged_classes', [])}
        for c in CL:
            v = r['per_class'].get(c)
            if v is not None and c not in fl:
                s[c].append(v)
    return {CL[c]: np.array(v) for c, v in s.items()}


def main():
    out = {}
    base = run1_base()
    j0_sd = {c: sd_from_ci(*J0_CI[c]) for c in J0_CI}
    run1_sd = {c: float(base[c].std(ddof=1)) for c in base}
    ratio = {c: j0_sd[c] / run1_sd[c] for c in base}
    out['janus0_sd_from_ci'] = {c: round(v, 4) for c, v in j0_sd.items()}
    out['janus0_macro_sd_from_ci'] = round(sd_from_ci(*J0_MACRO_CI), 4)
    out['run1_sd'] = {c: round(v, 4) for c, v in run1_sd.items()}
    out['ratio_janus0_over_run1'] = {c: round(v, 3) for c, v in ratio.items()}

    # sanity: Bridge's Round 9 number (run 1 spread, f = k = 1, keep reviewed) must reproduce ~0.966 at 150
    keep_r9 = {'LM': 0.85, 'LAD': 0.95, 'LCx': 0.95, 'RCA': 0.95}
    one = {c: 1.0 for c in base}
    out['check_bridge_r9_n150'] = p_pass(base, one, one, keep_r9, 150)[0]

    # (1) the seal, re-powered
    grid = []
    for scen, fpool in (('pool like val (f=1)', 1.0), ('f=1.2 (trigger line)', 1.2), ('pool 1.5x more varied', 1.5)):
        for k in (1.0, 1.2):
            for n in (150, 200, 250):
                for delta in (0.0, -0.02):
                    f = {c: ratio[c] * fpool for c in base}
                    kk = {c: k for c in base}
                    p, per = p_pass(base, f, kk, J0_KEEP, n, delta)
                    grid.append({'scenario': scen, 'f_pool': fpool, 'k': k, 'n': n, 'delta': delta,
                                 'p_all': p, 'per_class': per})
    out['seal_power'] = grid
    # the same grid on run 1's spread (Round 9's basis), for comparison
    out['seal_power_run1_spread'] = [
        {'f_pool': fp, 'n': n, 'p_all': p_pass(base, {c: fp for c in base}, one, J0_KEEP, n)[0]}
        for fp in (1.0, 1.5) for n in (150, 200, 250)]

    # (2) D35 MDE table
    pn = json.load(open(os.path.join(HERE, 'results', 'paired_noise.json')))['pairs']
    s_d = {'macro': max(pn[p]['macro']['sd_diff'] for p in pn),
           'LCx': max(pn[p]['LCx']['sd_diff'] for p in pn),
           'LAD': max(pn[p]['LAD']['sd_diff'] for p in pn)}
    r_macro = out['janus0_macro_sd_from_ci'] / float(np.std(
        [np.mean(list(v.values())) for v in [
            {c: r['per_class'][c] for c in CL if r['per_class'].get(c) is not None and c not in {str(x) for x in r.get('flagged_classes', [])}}
            for r in json.load(open(os.path.join(REPO, 'trillium-results/round6/atlas2/results/per_case_run1.json')))] if v], ddof=1))
    rr = {'macro': r_macro, 'LCx': ratio['LCx'], 'LAD': ratio['LAD']}
    out['d35_inputs'] = {'s_d_measured_max_over_pairs': s_d, 'r_janus0_over_run1': {k: round(v, 3) for k, v in rr.items()},
                         'sigma_seed': SIGMA_SEED}
    mde = []
    for metric in ('macro', 'LAD', 'LCx'):
        for scale_name, rsc in (('scaled to Janus 0', rr[metric]), ('measured (r=1)', 1.0)):
          for fpool in (1.0, 1.5):
            for design, ka, kb in (('model decision: two fixed checkpoints (no seed term)', math.inf, math.inf),
                                   ('recipe decision, 1 seed vs fixed Janus 0', 1, math.inf),
                                   ('recipe decision, 1 seed per arm', 1, 1),
                                   ('recipe decision, 2 seeds per arm', 2, 2),
                                   ('recipe decision, 3 seeds per arm', 3, 3)):
                for n in (10, 30, 50, 61, 100, 200):
                    case = (rsc * fpool * s_d[metric]) ** 2 / n
                    seed = SIGMA_SEED ** 2 * ((0 if ka == math.inf else 1 / ka) + (0 if kb == math.inf else 1 / kb))
                    se = math.sqrt(case + seed)
                    mde.append({'metric': metric, 'scale': scale_name, 'f_pool': fpool, 'design': design, 'n': n,
                                'se_case': round(math.sqrt(case), 4), 'se_seed': round(math.sqrt(seed), 4),
                                'mde': round(2.80 * se, 4)})
    out['d35_mde'] = mde
    os.makedirs(os.path.join(HERE, 'results'), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, 'results', 'repower.json'), 'w'), indent=1)

    print('janus0 sd', out['janus0_sd_from_ci'], 'macro', out['janus0_macro_sd_from_ci'])
    print('run1 sd', out['run1_sd'], 'ratio', out['ratio_janus0_over_run1'], 'check r9 0.966 ->', out['check_bridge_r9_n150'])
    print('\nSEAL POWER (Janus 0 spread)')
    for g in grid:
        print(f"{g['scenario']:24s} k={g['k']} n={g['n']} d={g['delta']:+.2f}  P(all)={g['p_all']:.3f}  {g['per_class']}")
    print('run1 spread:', out['seal_power_run1_spread'])
    print('\nD35 MDE', out['d35_inputs'])
    for m in mde:
        if m['n'] not in (30, 50, 61, 100): continue
        print(f"{m['metric']:5s} {m['scale'][:8]} f={m['f_pool']} {m['design']:50s} n={m['n']:3d} se_case={m['se_case']:.4f} se_seed={m['se_seed']:.4f} MDE={m['mde']:.3f}")


if __name__ == '__main__':
    main()
