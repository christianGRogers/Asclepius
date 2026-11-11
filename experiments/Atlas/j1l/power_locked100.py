"""Janus 1-L (D45): what the locked 100 can resolve, and what one warm continuation did on the master family.

CPU only; reads repo files only (no image, no sealed case):
  * experiments/Atlas/r10/paired_power.json: measured paired SD of per-case macro tF1 differences (two pairs, val 80)
    and Janus 0's CI-derived per-case SD (#43);
  * trillium-results/round6/atlas2/results/per_case_b.json and round7/atlas3/per_case_F0.json: run 2 B and the same
    model after a 200-epoch warm continuation on the same data (A17a trainer, peak 1e-2, 2500-iter warm-up).
Writes experiments/Atlas/j1l/power_locked100.json.
"""
import json, math, os, random

H = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(os.path.dirname(os.path.dirname(H)))
PP = json.load(open(os.path.join(R, 'experiments/Atlas/r10/paired_power.json')))
Z_A, Z_B = 1.959964, 0.841621  # two-sided 5 %, 80 % power
def phi(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))

sd_opt = [PP['pairs'][k]['macro']['sd_diff'] for k in ('warm_replicate_F0_F1', 'scratch_pair_run1_B')]
ratio = [PP['pairs'][k]['macro']['ratio_sd_diff_to_sd_case'] for k in ('warm_replicate_F0_F1', 'scratch_pair_run1_B')]
sd_j0 = PP['janus0_sd_case']['macro']
sd_pes = [r * sd_j0 for r in ratio]
out = {'sd_diff_optimistic': sd_opt, 'sd_diff_pessimistic': [round(s, 4) for s in sd_pes], 'janus0_sd_case': sd_j0}

rows = []
for n in (80, 100, 120):
    for label, sds in (('optimistic', sd_opt), ('pessimistic', sd_pes)):
        for sd in sds:
            se = sd / math.sqrt(n)
            rows.append({'n': n, 'sd_label': label, 'sd_diff': round(sd, 4),
                         'mde_superiority': round((Z_A + Z_B) * se, 4),
                         # P(lower 95 % bound > -m) when the true difference is 0 (a neutral model)
                         'p_pass_NI_0.01_if_neutral': round(phi(0.01 / se - Z_A), 3),
                         'p_pass_NI_0.02_if_neutral': round(phi(0.02 / se - Z_A), 3),
                         # P(lower bound > 0) for true gains of 0.005 / 0.01 / 0.02
                         'p_sup_if_gain_0.005': round(phi(0.005 / se - Z_A), 3),
                         'p_sup_if_gain_0.01': round(phi(0.01 / se - Z_A), 3),
                         'p_sup_if_gain_0.02': round(phi(0.02 / se - Z_A), 3)})
out['locked100'] = rows

# Expected macro tF1 gain from 560 -> 620 training cases if error falls as a power law N^-alpha
# (Hestness et al. 2017, arXiv:1712.00409: measured exponents between about -0.07 and -0.35 for generalisation error)
err0 = 1 - 0.909
out['data_gain'] = {f'alpha_{a}': round(err0 * (1 - (560 / 620) ** a), 4) for a in (0.07, 0.2, 0.35, 0.5)}

# B -> F0: warm continuation, same data, paired on val 80 (thick D0-era reference: a sign and a size, not a transfer)
def load(p):
    return {r['case']: r for r in json.load(open(os.path.join(R, p)))}
b = load('trillium-results/round6/atlas2/results/per_case_b.json')
f0 = load('trillium-results/round7/atlas3/per_case_F0.json')
def macro(r):
    v = [x for k, x in r['per_class'].items() if int(k) not in set(r.get('flagged_classes', []))]
    return sum(v) / len(v) if v else None
cases = sorted(set(b) & set(f0))
pairs = [(macro(b[c]), macro(f0[c])) for c in cases]
pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
d = [y - x for x, y in pairs]
m = sum(d) / len(d)
random.seed(0); boots = []
for _ in range(10000):
    s = [d[random.randrange(len(d))] for _ in d]; boots.append(sum(s) / len(s))
boots.sort()
cls = {}
for k in ('1', '2', '3', '4'):
    dd = [f0[c]['per_class'][k] - b[c]['per_class'][k] for c in cases
          if k in f0[c]['per_class'] and k in b[c]['per_class']
          and int(k) not in set(b[c].get('flagged_classes', [])) | set(f0[c].get('flagged_classes', []))]
    cls[k] = {'n': len(dd), 'mean_diff': round(sum(dd) / len(dd), 4)}
fp = [f0[c]['fp_components'] - b[c]['fp_components'] for c in cases]
out['warm_continuation_B_to_F0'] = {
    'n': len(d), 'mean_B': round(sum(x for x, _ in pairs) / len(pairs), 4),
    'mean_F0': round(sum(y for _, y in pairs) / len(pairs), 4), 'mean_diff': round(m, 4),
    'ci95': [round(boots[250], 4), round(boots[9749], 4)],
    'sd_diff': round(math.sqrt(sum((x - m) ** 2 for x in d) / (len(d) - 1)), 4),
    'per_class_mean_diff': cls, 'fp_per_case_diff': round(sum(fp) / len(fp), 3),
    'note': 'macro over unflagged classes per case (the decisive rule); thick D0-era reference'}
json.dump(out, open(os.path.join(H, 'power_locked100.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
