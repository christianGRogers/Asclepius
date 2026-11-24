"""Janus 1-F round 2 (Crucible), item 6: how many scorable patients each scoring set yields for an untraced class
(S1-S3, SN, Conus, RMA), and the 95 % Wilson half-width of a detection rate of 0.8 measured on them.

Patients with the class in at least one read = N x prev x (1 - (1 - s)^r), where prev is the share of patients in
whom the vessel is visible and separable at CCTA (unknown for every untraced class: a grid, not a claim), s is the
chance one extended read draws it when it is there, and r = 2 reads per pool patient (D11). Thresholds: F-A11's
report line (>= 20) and decide line (>= 30). Sets: D35 (35 patients, D47 Q6: read in extended mode), D35 + the 150
sealed pool patients (if the seal is also read in extended mode: acceptance only, one look, D27), and a hypothetical
70-patient held-out pool set (a D35 decision, not asked here)."""
import json
import math

SETS = {'D35 (35)': 35, 'D35 x2 (70, hypothetical)': 70, 'D35 + seal (185, acceptance only)': 185}


def wilson_half(p, n):
    if n <= 0:
        return float('nan')
    z = 1.96
    d = 1 + z * z / n
    return z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d


rows = []
for name, N in SETS.items():
    for prev in (0.3, 0.5, 0.7, 0.9):
        for s in (0.6, 0.9):
            n = N * prev * (1 - (1 - s) ** 2)
            rows.append({'set': name, 'prev': prev, 'read_sens': s, 'patients': round(n, 1),
                         'report(>=20)': n >= 20, 'decide(>=30)': n >= 30,
                         'half_width_at_0.8': round(wilson_half(0.8, int(n)), 3)})
print(json.dumps(rows, indent=0))
