"""Janus 1-F round 2 (Crucible), item 1: false-fail rate of F-A6's B gates for a human-level model, by simulation.

Inputs (all fixed before any model exists):
  * locked-100 case counts with each gated class (Delta v1's label count, F-A7): D1 98, D2 64, OM1 84, OM2 40, PDA 96,
    PLB 96;
  * ImageCAS-X Table 1 inter-observer presence agreement A_c (F-A6 lines + 0.05): D1 .969, D2 .894, OM1 .944,
    OM2 .875, PDA .988, PLB .962;
  * pieces per present case, resampled from the 620's census (census620.py's `pieces5`), so R-PDA in two pieces counts
    twice, as the scorer counts it.
A "human-level" model is one that disagrees with the reference as a second ImageCAS-X reader does:
  * presence: it disagrees on (1 - A_c) x 100 cases in expectation, a share f of them false-absent (reference present,
    model absent; every branch of that case missed) and 1 - f false-present (no branch to miss; only presence suffers).
    f = 0.5 is two equally skilled readers;
  * in a present case each reference branch is still missed (< 50 % covered) with probability m (partial misses);
  * each detected branch is named right with probability r;
  * case-level correlation: per case, the miss and naming rates are Beta draws with intra-case correlation rho.
Gates scored exactly as F-A6 defines them (ratio of sums for recall and naming). Usage:
  sim_gates.py <census620.jsonl or -> [n_sim]"""
import json, sys
import numpy as np

CLS = ['D1', 'D2', 'OM1', 'OM2', 'PDA', 'PLB']
NLOCK = {'D1': 98, 'D2': 64, 'OM1': 84, 'OM2': 40, 'PDA': 96, 'PLB': 96}
AGREE = {'D1': .969, 'D2': .894, 'OM1': .944, 'OM2': .875, 'PDA': .988, 'PLB': .962}
N = 100


def piece_dist(path):
    d = {c: [] for c in CLS}
    if path == '-':
        return {c: np.array([1] * 9 + [2]) for c in CLS}
    for l in open(path):
        r = json.loads(l)
        for c in CLS:
            k = len(r['pieces5'][c])
            if k:
                d[c].append(k)
    return {c: np.array(v) for c, v in d.items()}


def beta_draw(rng, mean, rho, size):
    if rho <= 0 or mean <= 0 or mean >= 1:
        return np.full(size, mean)
    s = (1 - rho) / rho
    return rng.beta(mean * s, (1 - mean) * s, size)


def sim(rule, pdist, f=0.5, m=0.03, r=0.93, rho=0.2, nsim=20000, seed=0, model=None):
    """Return per-class pass rates of B1-recall, B1-presence, B2 and of the class, and P(>= 4 of 6 classes pass)."""
    rng = np.random.default_rng(seed)
    passes = {c: np.zeros((nsim, 4), bool) for c in CLS}
    for c in CLS:
        n_c, A = NLOCK[c], AGREE[c]
        d_exp = (1 - A) * N
        if model and 'disagree' in model:
            d_exp = model['disagree'][c] * N
        ff = model.get('f', f) if model else f
        mm = model.get('m', m) if model else m
        rr = model.get('r', r) if model else r
        for s in range(nsim):
            k = rng.choice(pdist[c], n_c)                     # pieces in each reference-present case
            p_fa = min(d_exp * ff / n_c, 1.0)
            p_fp = min(d_exp * (1 - ff) / (N - n_c), 1.0) if N > n_c else 0.0
            fa = rng.random(n_c) < p_fa                       # false-absent cases: every branch missed
            fp = rng.random(N - n_c) < p_fp
            miss_c = beta_draw(rng, mm, rho, n_c)
            name_c = beta_draw(rng, rr, rho, n_c)
            det = np.where(fa, 0, rng.binomial(k, 1 - miss_c))
            named = rng.binomial(det, name_c)
            rec = det.sum() / k.sum()
            agree = 1 - (fa.sum() + fp.sum()) / N
            nam = named.sum() / max(det.sum(), 1)
            b1r = rec >= rule['recall'](c)
            b1p = agree >= rule['presence'](c)
            b2 = nam >= rule['naming'](c)
            passes[c][s] = (b1r, b1p, b2, b1r and b1p and b2)
    cls_pass = np.stack([passes[c][:, 3] for c in CLS], 1)
    out = {c: passes[c].mean(0).round(3).tolist() for c in CLS}
    out['P(>=4 of 6)'] = float((cls_pass.sum(1) >= 4).mean().round(4))
    out['P(6 of 6)'] = float((cls_pass.sum(1) == 6).mean().round(4))
    return out


def human_recall(c, f=0.5, m=0.03):
    return (1 - (1 - AGREE[c]) * N * f / NLOCK[c]) * (1 - m)


RULES = {
    'R1 (F-A6 as ruled): recall >= .80, presence >= A-.05, naming >= .85': {
        'recall': lambda c: .80, 'presence': lambda c: AGREE[c] - .05, 'naming': lambda c: .85},
    'R2 (proposed): recall >= human_c - .10, presence >= A-.05, naming >= .80': {
        'recall': lambda c: human_recall(c) - .10, 'presence': lambda c: AGREE[c] - .05, 'naming': lambda c: .80},
    'R3: recall >= .75, presence >= A-.07, naming >= .80': {
        'recall': lambda c: .75, 'presence': lambda c: AGREE[c] - .07, 'naming': lambda c: .80},
}

if __name__ == '__main__':
    pdist = piece_dist(sys.argv[1] if len(sys.argv) > 1 else '-')
    nsim = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
    res = {'pieces_per_present_case': {c: [round(float(pdist[c].mean()), 3), int(len(pdist[c]))] for c in CLS},
           'human_recall_expected(f=.5,m=.03)': {c: round(human_recall(c), 3) for c in CLS},
           'lines_R2': {c: [round(human_recall(c) - .10, 3), round(AGREE[c] - .05, 3), .80] for c in CLS}}
    scen = {'human f=.5 m=.03 r=.93': {}, 'human f=.5 m=.03 r=.90': {'r': .90},
            'human f=.7 m=.05 r=.90 (worse-than-typical reader)': {'f': .7, 'm': .05, 'r': .90},
            'human f=.5 m=.00 r=.95 (best case)': {'m': 0, 'r': .95}}
    bad = {'BAD recall 0.70 (m=.27), r=.93': {'m': .27},
           'BAD naming 0.75 (r=.75)': {'r': .75},
           'BAD calls every class present (f=0, disagree = 1 - prevalence), m=.03, r=.93':
               {'f': 0.0, 'disagree': {c: (N - NLOCK[c]) / N for c in CLS}},
           'BAD twice human disagreement, f=.5, m=.05, r=.88':
               {'m': .05, 'r': .88, 'disagree': {c: 2 * (1 - AGREE[c]) for c in CLS}}}
    for rn, rule in RULES.items():
        res[rn] = {}
        for sn, mo in {**scen, **bad}.items():
            res[rn][sn] = sim(rule, pdist, nsim=nsim, model={'f': .5, 'm': .03, 'r': .93, **mo}, seed=1)
    print(json.dumps(res, indent=1))
