"""Janus 1-F round 2 (Foxtrot), §5 item 6: what D35's 35 decision patients (A33; read in extended mode, D47 Q6)
yield for the six untraced classes, as a function of pi = P(a patient's extended read draws the class), which is
visibility x the annotator tracing it (D47 Q7). Exact binomial; no data are read.
Prints P(n >= 10), P(n >= 20) (F-A11's report line), P(n >= 30) (decide/ship line), the expected n and the 95 %
Wilson half-width of a detection recall of 0.8 at that n. Two reads per patient (D11) do not add patients."""
import json, sys
from math import comb, sqrt

N = 35


def tail(n, p, k):
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def wilson_hw(p, n, zc=1.96):
    if n == 0:
        return None
    d = 1 + zc * zc / n
    return zc * sqrt(p * (1 - p) / n + zc * zc / (4 * n * n)) / d


rows = []
for pi in (.2, .3, .4, .5, .6, .7, .8, .85, .9, .95):
    en = N * pi
    rows.append({'pi': pi, 'E_n': round(en, 1), 'P_n>=10': round(tail(N, pi, 10), 3), 'P_n>=20': round(tail(N, pi, 20), 3),
                 'P_n>=30': round(tail(N, pi, 30), 3), 'recall0.8_hw_at_E_n': round(wilson_hw(.8, round(en)), 3)})
print('| pi | E[n] | P(n>=10) | P(n>=20) | P(n>=30) | +/- on recall 0.8 |')
print('|---|---|---|---|---|---|')
for r in rows:
    print(f"| {r['pi']} | {r['E_n']} | {r['P_n>=10']} | {r['P_n>=20']} | {r['P_n>=30']} | {r['recall0.8_hw_at_E_n']} |")
# smallest decision-set size with P(n >= 30) >= 0.8, per pi
need = {}
for pi in (.3, .5, .7, .9):
    n = 30
    while tail(n, pi, 30) < .8:
        n += 1
    need[pi] = n
print('patients needed for P(n>=30) >= 0.8:', need)
if len(sys.argv) > 1:
    json.dump({'rows': rows, 'patients_for_30_at_0.8': need}, open(sys.argv[1], 'w'), indent=1)
