"""Janus 1-F round 2 (Atlas), §5 item 6: what the D35 decision set (35 patients, two reads each, D47 Q6 = extended
mode) yields for S1-S3, SN, Conus and RMA, at a grid of per-patient prevalences pi of 'visible and drawn by a reader'.
No prevalence is sourced here except SN's origin (Kosar et al.: RCA 79 %, circumflex 20 %); the grid is the answer.

A patient COUNTS for a class when at least one of its two reads draws it: P = 1 - (1 - pi)^2 if the reads are
independent given the anatomy; the 'anatomy-limited' column assumes both reads draw it or neither (P = pi).
Report line (F-A11): >= 20 patients; decide/ship line: >= 30. The detection-recall 95 % half-width is for a model at
recall 0.8 (binomial, normal approximation) on the expected number of patients.
Usage: python untraced_yield.py"""
import math
from scipy.stats import binom

N = 35
print('| pi | patients, reads correlated (P = pi): E, P(>=20), P(>=30) | reads independent: E, P(>=20), P(>=30) '
      '| recall 0.8 half-width at E (correlated) |')
print('|---|---|---|---|')
for pi in (0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
    row = []
    for P in (pi, 1 - (1 - pi) ** 2):
        e = N * P
        row.append(f'{e:.1f}, {1 - binom.cdf(19, N, P):.2f}, {1 - binom.cdf(29, N, P):.2f}')
    hw = 1.96 * math.sqrt(0.16 / (N * pi))
    print(f'| {pi} | {row[0]} | {row[1]} | ±{hw:.2f} |')
for k in (20, 30):
    lo = next(p / 1000 for p in range(1, 1000) if 1 - binom.cdf(k - 1, N, p / 1000) >= 0.8)
    print(f'pi needed for P(>= {k} patients) >= 0.8 with correlated reads: {lo:.3f}')
