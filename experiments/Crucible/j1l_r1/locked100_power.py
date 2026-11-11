"""Crucible, Janus 1-L Round 1: the locked 100 (D45) and what a paired comparison on it can detect.

1. locked  -- the 20 of open-36 with the smallest sha256('asclepius-janus1-locked100:' + id) (D45), ids as in
              vault/Plans/Sealed test.md; the other 16 go to training. Ids only: no image or label is opened.
2. tf1     -- power of the paired tF1 comparison (candidate - Janus 0) on n = 100, by resampling the two measured
              per-case paired differences on val 80 (trillium-results: atlas2 run 1 - B, two from-scratch runs;
              atlas3 F0 - F1, two warm fine-tunes), centred, optionally scaled up to Janus 0's heavier per-case
              spread (x1.8: macro SD 0.117 from its CI against run 1's 0.065), then shifted by a true effect.
              Rules: superiority (lower 95 % bound > 0) and non-inferiority (lower bound > -m).
3. dice    -- the same for whole-tree Dice, where no paired data exist: a normal model on SD_diff from Janus 0's
              p10/p90 (0.846/0.904 -> per-case SD about 0.023) and a between-model correlation of 0.5-0.9.
4. data    -- what 560 -> 620 training cases can be expected to buy, on a log-linear learning curve.

CPU, seconds. Opens no image, no label, no read and no sealed case. Usage: python3 locked100_power.py > locked100_power.json
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
TR = os.path.join(REPO, 'trillium-results')
RNG = np.random.default_rng(20261111)
N_SIM = 4000
Z = 1.96


def locked():
    txt = open(os.path.join(REPO, 'vault', 'Plans', 'Sealed test.md')).read()
    sec = txt.split('## Open ImageCAS-X test, never used in development (36)')[1].split('##')[0]
    ids = re.findall(r'c\d{4}', sec)
    assert len(ids) == 36, len(ids)
    sealed = json.load(open(os.path.join(REPO, 'trillium', 'sealed_test.json')))
    assert not set(ids) & set(sealed['sealed_icx_test']) and set(ids) == set(sealed['open_icx_test'])
    h = {i: hashlib.sha256(('asclepius-janus1-locked100:' + i).encode()).hexdigest() for i in ids}
    order = sorted(ids, key=lambda i: h[i])
    return dict(salt='asclepius-janus1-locked100:', locked20=sorted(order[:20]), train16=sorted(order[20:]),
                ranked=[(i, h[i][:12]) for i in order])


def decisive_macro(row):
    """Per-case decisive macro: the mean of the per-class tF1 over classes not flagged (A1b), as Atlas's
    r10_paired_power.py and the r9 scorer read it. The raw 'tf1' field keeps flagged trees and doubles the SD."""
    fl = set(row.get('flagged_classes') or [])
    v = [x for k, x in (row.get('per_class') or {}).items() if x is not None and int(k) not in fl]
    return float(np.mean(v)) if v else None


def macro_diffs(fa, fb):
    a = {r['case']: decisive_macro(r) for r in json.load(open(fa))}
    b = {r['case']: decisive_macro(r) for r in json.load(open(fb))}
    common = sorted(c for c in set(a) & set(b) if a[c] is not None and b[c] is not None)
    return np.array([a[c] - b[c] for c in common])


def p_pass(d0, n, delta, margin, scale):
    """P(lower 95 % t-bound of the mean paired difference > -margin)."""
    d = (d0 - d0.mean()) * scale
    s = RNG.choice(d, size=(N_SIM, n), replace=True) + delta
    lb = s.mean(1) - Z * s.std(1, ddof=1) / math.sqrt(n)
    return round(float((lb > -margin).mean()), 3)


def tf1_power():
    pairs = {
        'scratch_run1_minus_B': macro_diffs(os.path.join(TR, 'round6/atlas2/results/per_case_run1.json'),
                                            os.path.join(TR, 'round6/atlas2/results/per_case_b.json')),
        'warm_F0_minus_F1': macro_diffs(os.path.join(TR, 'round7/atlas3/per_case_F0.json'),
                                        os.path.join(TR, 'round7/atlas3/per_case_F1.json'))}
    out = {}
    for name, d in pairs.items():
        rows = []
        for scale in (1.0, 1.8):
            sd = float(d.std(ddof=1) * scale)
            mde = round((Z + 0.84) * sd / math.sqrt(100), 4)
            for delta in (-0.02, -0.01, 0.0, 0.005, 0.01, 0.015, 0.02):
                rows.append(dict(scale=scale, sd_diff=round(sd, 4), delta=delta,
                                 p_superior=p_pass(d, 100, delta, 0.0, scale),
                                 p_noninferior_002=p_pass(d, 100, delta, 0.02, scale),
                                 p_noninferior_001=p_pass(d, 100, delta, 0.01, scale)))
            rows.append(dict(scale=scale, mde_superiority_80pct=mde))
        out[name] = dict(n_pairs=int(len(d)), mean=round(float(d.mean()), 4), sd=round(float(d.std(ddof=1)), 4),
                         rows=rows)
    return out


def dice_power():
    sd_case = (0.904 - 0.846) / (2 * 1.2816)          # Janus 0 val-80 p10/p90 (icx4 - Results)
    rows = []
    for rho in (0.5, 0.7, 0.9):
        sd = sd_case * math.sqrt(2 * (1 - rho))
        se = sd / 10
        row = dict(rho=rho, sd_diff=round(sd, 4), mde_80pct=round((Z + 0.84) * se, 4))
        for delta in (0.005, 0.01, 0.02, 0.03):
            from statistics import NormalDist
            row[f'p_superior_at_{delta}'] = round(1 - NormalDist().cdf(Z - delta / se), 3)
        rows.append(row)
    return dict(sd_case_janus0=round(sd_case, 4), rows=rows)


def data_gain():
    # A log-linear learning curve: error falls by a fraction g per doubling of training cases. g = 5-15 % of the
    # remaining error per doubling brackets the medical-segmentation learning curves cited in Crucible v1 (§3).
    err0 = 1 - 0.909
    doublings = math.log2(620 / 560)
    return dict(doublings=round(doublings, 3),
                gain_tf1={f'g={g}': round(err0 * (1 - (1 - g) ** doublings), 4) for g in (0.05, 0.10, 0.15, 0.25)})


if __name__ == '__main__':
    print(json.dumps(dict(locked=locked(), tf1=tf1_power(), dice=dice_power(), data=data_gain()), indent=1))
