"""Janus 1-F round 2 (Foxtrot): false-fail rate of F-A6's B gates for a human-level model, by simulation (CPU).

Inputs (no locked label is opened):
  * gated-class counts on the locked 100, as the round-1 ruling gives them (Delta's label count, F-A7):
    D1 98, D2 64, OM1 84, OM2 40, PDA 96, PLB 96;
  * ImageCAS-X Table 1 inter-observer presence agreement a_c (the ruling's lines + 0.05);
  * pieces per present case, drawn from the 620's census (pass1.jsonl).
A "human-level" model disagrees with the reference about class c's presence as often as two ImageCAS-X observers
(1 - a_c of the 100 cases). The disagreement is split between false adds on absent cases (half, capped at half the
absent cases) and misses on present cases (the rest). Whether a miss is a lumen not drawn (a detection miss, B1
recall) or a lumen drawn under another name (a naming error, B2) is not in Table 1, so both attributions are run:
  det  -- every miss is a detection miss;   name -- every miss is a detected, misnamed branch;   half -- 50/50.
On top, each piece independently fails the 50 % coverage rule with prob. delta and is misnamed with prob. eps
(slips a human does not make: they push the model BELOW human level), default 0 (human level = Table 1 exactly);
0.02 and 0.05 are run as sensitivities.
Usage: python3 gate_sim.py <pass1.jsonl> <out.json>
"""
import json, sys
import numpy as np

COUNTS = {'D1': 98, 'D2': 64, 'OM1': 84, 'OM2': 40, 'PDA': 96, 'PLB': 96}
AGREE = {'D1': .969, 'D2': .894, 'OM1': .944, 'OM2': .875, 'PDA': .988, 'PLB': .962}
N, T = 100, 20000
RNG = np.random.default_rng(303)


def piece_dist(rows, c):
    k = [len(r['census'][c]['pieces_mm']) for r in rows if r['census'][c]['pieces_mm']]
    return np.array(k)


def rates(c):
    npres = COUNTS[c]; nabs = N - npres
    e = (1 - AGREE[c]) * N
    fa = min(e / 2, 0.5 * nabs)
    return (e - fa) / npres, (fa / nabs if nabs else 0.0)


def simulate(c, kdist, attrib='det', mult=1.0, delta=0.0, eps=0.0, f_over=None, rule=None, T=T):
    m, f = rates(c); m = min(1.0, m * mult)
    if f_over is not None:
        f = f_over
    npres = COUNTS[c]; nabs = N - npres
    k = RNG.choice(kdist, size=(T, npres))
    miss = RNG.random((T, npres)) < m
    if attrib == 'det':
        det_case, name_case = miss, np.zeros_like(miss)
    elif attrib == 'name':
        det_case, name_case = np.zeros_like(miss), miss
    else:
        h = RNG.random((T, npres)) < .5
        det_case, name_case = miss & h, miss & ~h
    kmax = int(kdist.max())
    valid = np.arange(kmax)[None, None, :] < k[..., None]
    pdet = (RNG.random((T, npres, kmax)) >= delta) & ~det_case[..., None] & valid
    pname = pdet & (RNG.random((T, npres, kmax)) >= eps) & ~name_case[..., None]
    recall = pdet.sum((1, 2)) / valid.sum((1, 2))
    naming = pname.sum((1, 2)) / np.maximum(pdet.sum((1, 2)), 1)
    pred_present = pname.any(2)                       # some piece drawn under its own name
    fadd = RNG.random((T, nabs)) < f
    agree = (pred_present.sum(1) + (nabs - fadd.sum(1))) / N
    r = rule or {'recall': .80, 'presence_drop': .05, 'naming': .85}
    rr = r['recall'](c) if callable(r['recall']) else r['recall']
    rn = r['naming'](c) if callable(r['naming']) else r['naming']
    p_rec = recall >= rr
    p_pres = agree >= AGREE[c] - r['presence_drop']
    p_nam = naming >= rn
    return {'recall_mean': float(recall.mean()), 'naming_mean': float(naming.mean()), 'agree_mean': float(agree.mean()),
            'fail_recall': float(1 - p_rec.mean()), 'fail_presence': float(1 - p_pres.mean()),
            'fail_naming': float(1 - p_nam.mean()), 'fail_B': float(1 - (p_rec & p_pres & p_nam).mean()),
            '_pass': (p_rec & p_pres & p_nam)}


RULES = {
    'R0_ruled': {'recall': .80, 'presence_drop': .05, 'naming': .85},
    'R1_flat_looser': {'recall': .75, 'presence_drop': .07, 'naming': .80},
    # R2 (Foxtrot v2's proposal): the ruled lines, capped at the human-level value - 0.10 under the worst attribution
    'R2_human_capped': {'recall': lambda c: round(min(.80, 1 - rates(c)[0] - .10), 3), 'presence_drop': .05,
                        'naming': lambda c: round(min(.85, 1 - rates(c)[0] - .10), 3)},
}


def main(p1, out):
    rows = [json.loads(l) for l in open(p1)]
    kd = {c: piece_dist(rows, c) for c in COUNTS}
    res = {'rules': {rn: {c: [r['recall'](c) if callable(r['recall']) else r['recall'], r['presence_drop'],
                              r['naming'](c) if callable(r['naming']) else r['naming']] for c in COUNTS}
                     for rn, r in RULES.items()},
           'n_cases_620': len(rows), 'rates_m_f': {c: rates(c) for c in COUNTS},
           'pieces_620': {c: {'mean': float(kd[c].mean()), 'share_ge2': float((kd[c] >= 2).mean())} for c in COUNTS}}
    for rn, rule in RULES.items():
        res[rn] = {}
        for attrib in ('det', 'half', 'name'):
            for mult in (1.0, 1.5, 2.0, 3.0):
                key = f'{attrib}_x{mult}'
                per, passes = {}, []
                for c in COUNTS:
                    s = simulate(c, kd[c], attrib, mult, rule=rule)
                    passes.append(s.pop('_pass')); per[c] = {k: round(v, 4) for k, v in s.items()}
                P = np.stack(passes, 1).sum(1)
                res[rn][key] = {'per_class': per, 'fail_read_lt4of6': float((P < 4).mean()),
                                'mean_classes_passing': float(P.mean())}
        # an "always present" caller for every class: presence by false adds f = 1
        res[rn]['always_present'] = {c: round(simulate(c, kd[c], 'det', 1.0, f_over=1.0, rule=rule)['fail_presence'], 4)
                                     for c in COUNTS}
        # sensitivity to the per-piece slips
        for sl in (.02, .05):
            res[rn][f'slips_{sl}'] = {c: round(simulate(c, kd[c], 'half', 1.0, delta=sl, eps=sl, rule=rule)['fail_B'], 4)
                                      for c in COUNTS}
    json.dump(res, open(out, 'w'), indent=1)
    for rn in RULES:
        r = RULES[rn]
        print(f'\n== {rn}', {c: (r['recall'](c) if callable(r['recall']) else r['recall'],
                                r['naming'](c) if callable(r['naming']) else r['naming']) for c in COUNTS})
        for key, v in res[rn].items():
            if isinstance(v, dict) and 'per_class' in v:
                print(f'{key:10s} read<4/6 {v["fail_read_lt4of6"]:.3f} | ' + ' '.join(
                    f'{c}:{d["fail_B"]:.2f}(r{d["fail_recall"]:.2f} p{d["fail_presence"]:.2f} n{d["fail_naming"]:.2f})'
                    for c, d in v['per_class'].items()))
        print('always-present presence fail:', res[rn]['always_present'])
        print('slips 0.02 fail_B:', res[rn]['slips_0.02']); print('slips 0.05 fail_B:', res[rn]['slips_0.05'])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
