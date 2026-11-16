"""Janus 1-F round 2, item 6: what the 35 D35 decision patients, read in extended mode (D47 Q6), can yield for a class
ImageCAS-X never traced, as a function of the share p of patients in whom a reader draws it. Binomial, exact.
Reports expected count, P(count >= 20) (F-A11's report line), P(count >= 30) (decide/ship line), and the Wilson 95 %
half-width of a model-vs-read presence agreement of 0.85 at the expected count. Usage: python3 untraced_yield.py"""
import json
from scipy.stats import binom, norm

N = 35


def wilson_half(p, n, z=norm.ppf(0.975)):
    if n <= 0:
        return None
    d = 1 + z * z / n
    return round(z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d, 3)


rows = []
for p in (0.2, 0.3, 0.5, 0.6, 0.7, 0.8, 0.86, 0.9, 0.95):
    rows.append({'p': p, 'E_count': round(N * p, 1), 'P_ge_20': round(float(binom.sf(19, N, p)), 3),
                 'P_ge_30': round(float(binom.sf(29, N, p)), 3),
                 'wilson_half_at_0.85_on_E': wilson_half(0.85, round(N * p)),
                 'wilson_half_presence_all35_at_0.85': wilson_half(0.85, N)})
# both reads must draw the class for a read-vs-read ceiling: p_both = p * agreement (0.85 assumed)
print(json.dumps({'N': N, 'rows': rows}, indent=1))
