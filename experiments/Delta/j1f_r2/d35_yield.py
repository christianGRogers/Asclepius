"""Janus 1-F round 2 (Delta), item 6: what a scoring set of n extended-read patients yields for a class present (and
drawn) in a share p of them. Binomial; no data. Prints E[count], P(count >= 20) (report line), P(count >= 30)
(decide line), and the 95 % half-width of a detection rate of 0.85 at the expected count (Wilson)."""
import math
from scipy.stats import binom


def wilson_half(k, n, z=1.96):
    if n == 0: return float('nan')
    p = k / n; d = 1 + z * z / n
    return z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d


print('| n patients | p (class drawn) | E[count] | P(>= 20) | P(>= 30) | detection 0.85 +/- at E[count] |')
print('|---|---|---|---|---|---|')
for n in (35, 60, 100):
    for p in (0.2, 0.4, 0.6, 0.8, 0.9):
        e = n * p
        print(f'| {n} | {p:.1f} | {e:.0f} | {binom.sf(19, n, p):.2f} | {binom.sf(29, n, p):.2f} | '
              f'{wilson_half(round(0.85 * e), round(e)):.2f} |')
