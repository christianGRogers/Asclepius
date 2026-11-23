"""Crucible, Janus 1-L round 3: operating characteristics of gate.py with D49's Q-R2-3 clause, and of S's 1.25 % look.

Synthetic paired locked-100 data only (no real score is read: the locked 100 are counts-only for this round). Per case:
  Delta tF1  ~ mu_t + 0.038 z1           (round 1's warm paired SD; 0.055 as a pessimistic row)
  Delta Dice ~ mu_d + sd_d (rho z1 + sqrt(1 - rho^2) z2), sd_d in {0.012, 0.020}, rho = 0.3
  recall     heavy-tailed null per class (6 % of trees flip by 0.2-0.6, either sign), as gate.py's self-test.
gate.decide is called unchanged, with 2 000 bootstrap resamples (B) for speed; 300 draws per cell.

Prints P(adopted), and the share adopted through Q4, with and without Q-R2-3, and C's look against S's.
Usage: python gate_oc.py   (writes gate_oc.json; ~20 min on 4 cores)
"""
import json
import os

import numpy as np

import gate as G

HERE = os.path.dirname(os.path.abspath(__file__))
G.B = 2000
REPS = 300


def draw(rng, base, mu_t, mu_d, sd_t, sd_d, rho=0.3):
    out = []
    for b in base:
        z1, z2 = rng.standard_normal(2)
        dt = mu_t + sd_t * z1
        dd = mu_d + sd_d * (rho * z1 + np.sqrt(1 - rho ** 2) * z2)
        rec = {c: b['recall'][c] + 0.003 * rng.standard_normal()
               + (rng.random() < 0.06) * rng.choice([-1, 1]) * rng.uniform(0.2, 0.6) for c in G.CLASSES}
        out.append(dict(b, per_class={c: v + dt for c, v in b['per_class'].items()}, recall=rec,
                        dice={'tree': b['dice']['tree'] + dd}, fp_components=0))
    return out


def no_q(g):
    """The verdict without D49 Q-R2-3 (D46 Q4 as first written)."""
    if g['verdict'] == 'not adopted' and 'Q-R2-3' in g['branch']:
        return 'adopted'
    return g['verdict']


def main():
    cells = [(k, mt, md, st, sd) for k, (mt, md, st, sd) in enumerate(
        (mt, md, st, sd) for st in (0.038, 0.055) for sd in (0.012, 0.020)
        for mt in (0.0, -0.01) for md in (-0.01, -0.005, 0.0, 0.005, 0.02))]
    from multiprocessing import Pool
    with Pool(4) as p:
        rows = p.map(cell, cells)
    for r in rows:
        print(json.dumps(r))
    json.dump(dict(reps=REPS, bootstrap=G.B, rows=rows), open(os.path.join(HERE, 'gate_oc.json'), 'w'), indent=1)


def cell(arg):
    k, mt, md, st, sd = arg
    base = G.fake(seed=11)
    if True:
        rng = np.random.default_rng(100 + k)
        adopt = adopt_noq = q4 = q_refused = adopt_s = 0
        for _ in range(REPS):
            c = draw(rng, base, mt, md, st, sd)
            g = G.decide(base, c, 'C')
            adopt += g['verdict'] == 'adopted'
            adopt_noq += no_q(g) == 'adopted'
            q4 += g['branch'].startswith('Q4 (')
            q_refused += 'Q-R2-3' in g['branch'] and g['verdict'] == 'not adopted'
            adopt_s += G.decide(base, c, 'S')['verdict'] == 'adopted'
        r = dict(mu_tf1=mt, mu_dice=md, sd_tf1=st, sd_dice=sd, P_adopt=adopt / REPS, P_adopt_without_QR23=adopt_noq / REPS,
                 P_adopt_via_Q4=q4 / REPS, P_refused_by_QR23=q_refused / REPS, P_adopt_S_look=adopt_s / REPS)
        return r


if __name__ == '__main__':
    main()
