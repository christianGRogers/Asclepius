"""Janus 1-F round 3 (Atlas): do F-A15's lines survive (a) the scorer of record's own piece counts on the 620 and
(b) F-A25's corrected locked-100 counts? (ruling §5 item 1, §7 "re-run gate_sim.py with the scorer's counts")

Re-uses round 2's simulation unchanged (`experiments/Atlas/j1f_r2/gate_sim.py`, the code F-A15 was set with) and
changes only its two inputs:
  * pieces per case per class: from <census> (round 2's census_r2.jsonl, or this round's check_620.jsonl, which the
    round-3 scorer wrote; both carry 'pieces');
  * the locked counts: round 1's 98/64/84/40/96/96, or F-A25's 97/64/84/40/98/99 (D47 (A), 5 mm).
For each combination it re-derives the lines by Atlas's rule (5th percentile, worst scenario, rounded down) and
reports the per-class false-fail of the FROZEN F-A15 lines over the nine human models, and the verdict's power
against a model with +0.10 omission and with 10 % / 20 % extra misnaming.
Usage: python gate_refreeze.py <census.jsonl> <out.json>
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../j1f_r2'))
import gate_sim as G  # noqa: E402

FA15 = json.load(open(os.path.join(HERE, 'j1f_gates.json')))['lines']
COUNTS = {'round1': {'D1': 98, 'D2': 64, 'OM1': 84, 'OM2': 40, 'PDA': 96, 'PLB': 96},
          'FA25': {'D1': 97, 'D2': 64, 'OM1': 84, 'OM2': 40, 'PDA': 98, 'PLB': 99}}


def derive(pdist):
    free = {'recall': 0, 'naming': 0, 'presence_margin': 1, 'k_of_6': 0}
    wr = G.simulate(G.params(0.12), pdist, free, 0.0, 0.12, seed=3)
    wn = G.simulate(G.params(0.05), pdist, free, 1.0, 0.05, seed=4)
    return {c: {'recall': float(np.floor(wr[c]['recall_p05'] * 100) / 100),
                'naming': float(np.floor(wn[c]['naming_p05'] * 100) / 100),
                'presence': float(np.floor(min(wr[c]['presence_p05'], wn[c]['presence_p05']) * 100) / 100)}
            for c in G.T1}


def evaluate(pdist, lines):
    ff = {}
    for sh in (0.05, 0.08, 0.12):
        for s in (0.0, 0.5, 1.0):
            r = G.simulate_lines(G.params(sh), pdist, lines, s, sh, reps=2000, seed=1)
            ff[f'sigma_h={sh} s={s}'] = {**{c: r[c]['fail_rate'] for c in G.T1}, 'verdict': r['verdict_fail_rate']}
    worst = {c: float(max(v[c] for v in ff.values())) for c in list(G.T1) + ['verdict']}
    pw = {}
    for lab, shift in (('omission +0.10', {'dm': 0.10}), ('misnaming 0.10', {'dn': 0.10}),
                       ('misnaming 0.20', {'dn': 0.20})):
        r = G.simulate_lines(G.params(0.08), pdist, lines, 0.5, 0.08, reps=2000, seed=2, shift=shift)
        pw[lab] = r['verdict_fail_rate']           # a worse-than-human model: the verdict failing = rejected
    return ff, worst, pw


def main(census, outp):
    pdist = G.pieces_dist(census)
    rep = {'census': os.path.basename(census),
           'pieces_per_case': {c: {int(k): int((np.asarray(v) == k).sum()) for k in sorted(set(v))}
                               for c, v in pdist.items()}}
    for name, cnt in COUNTS.items():
        G.LOCKED = dict(cnt)
        lines = derive(pdist)
        ff, worst, pw = evaluate(pdist, FA15)
        ffr, worstr, pwr = evaluate(pdist, lines)
        rep[name] = {'locked_counts': cnt, 'rederived_lines': lines,
                     'differs_from_FA15': {c: {m: (lines[c][m], FA15[c][m]) for m in lines[c]
                                               if lines[c][m] != FA15[c][m]} for c in G.T1},
                     'FA15_false_fail_9_models': ff, 'FA15_false_fail_worst': worst,
                     'FA15_P_reject_verdict': pw,
                     'rederived_false_fail_9_models': ffr, 'rederived_false_fail_worst': worstr,
                     'rederived_P_reject_verdict': pwr}
        print(name, 'differs:', {c: v for c, v in rep[name]['differs_from_FA15'].items() if v})
        print(name, 'FA15 worst false-fail', worst, 'P(reject)', pw, flush=True)
        print(name, 'rederived worst false-fail', worstr, 'P(reject)', pwr, flush=True)
    json.dump(rep, open(outp, 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
