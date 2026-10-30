"""E7 (Juliet, Janus-M Round 2, path jm/paired-scar): the rule scar head's presence cut, and what registration error
does to it. Re-scores E6's per-segment outputs (e6_registration.json); opens no case.

Stage 1 (presence): segment scar-present if the depth-binned transmural extent T >= tau.
Stage 2 (bin): Kim bin of T, clipped to 1-4 when present, else 0.
For each registration method and condition, and tau in a grid, pools all segments over seeds and reports
sensitivity, specificity, Kim-bin accuracy over scarred segments, quadratic-weighted kappa (5 classes), and the
99th percentile of T read in truly scar-free segments (the floor tau must clear).

Usage: python scar_head.py -> e7_scar_head.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BINS = (0.0, 0.01, 0.26, 0.51, 0.76, 1.01)
TAUS = (0.03, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20)
W = 1 - (np.subtract.outer(np.arange(5), np.arange(5)) ** 2) / 16.0


def kim(x, present):
    return np.where(present, np.clip(np.digitize(x, BINS) - 1, 1, 4), 0)


def kappa_w(a, b):
    M = np.zeros((5, 5))
    np.add.at(M, (a, b), 1)
    P = M / M.sum()
    E = P.sum(1)[:, None] * P.sum(0)[None, :]
    return float(((W * P).sum() - (W * E).sum()) / (1 - (W * E).sum()))


def main():
    sys.path.insert(0, str(HERE))
    import guard_r2
    guard_r2.gate([])
    d = json.loads((HERE / 'e6_registration.json').read_text())
    groups = {}
    for r in d['runs']:
        for m, x in r['methods'].items():
            key = (m, r['d_mm'], r['contrast_HU'], r['noise_sd_HU'], r['phase_e'])
            g = groups.setdefault(key, {'est': [], 'true': []})
            g['est'] += x['est']
            g['true'] += x['true']
    rows = []
    for key, g in sorted(groups.items()):
        est, tru = np.array(g['est']), np.array(g['true'])
        pt = tru >= 0.01
        bt = kim(tru, pt)
        row = {'method': key[0], 'd_mm': key[1], 'contrast_HU': key[2], 'noise_sd_HU': key[3], 'phase_e': key[4],
               'n_segments': int(len(est)), 'n_scarred': int(pt.sum()),
               'scarfree_T_p99': round(float(np.percentile(est[~pt], 99)), 3),
               'scarfree_T_max': round(float(est[~pt].max()), 3),
               'mae_T_scarred': round(float(np.abs(est - tru)[pt].mean()), 3), 'by_tau': {}}
        for tau in TAUS:
            pe = est >= tau
            be = kim(est, pe)
            row['by_tau'][str(tau)] = {'sens': round(float(pe[pt].mean()), 3), 'spec': round(float((~pe[~pt]).mean()), 3),
                                       'bin_acc_scarred': round(float((be[pt] == bt[pt]).mean()), 3),
                                       'kappa_w': round(kappa_w(bt, be), 3)}
        rows.append(row)
        t = row['by_tau']['0.1']
        print(key, row['n_scarred'], row['scarfree_T_p99'], row['mae_T_scarred'], t, flush=True)
    out = HERE / 'e7_scar_head.json'
    out.write_text(json.dumps({'taus': TAUS, 'rows': rows}, indent=1) + '\n')
    guard_r2.scan_outputs([out])


if __name__ == '__main__':
    main()
