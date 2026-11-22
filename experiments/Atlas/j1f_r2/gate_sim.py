"""Janus 1-F round 2 (Atlas): how often do F-A6's B gates fail a HUMAN-LEVEL model on the locked 100? (§5, item 1)

A human-level model is one whose disagreement with ImageCAS-X's reference is distributed like ImageCAS-X's second
analyst's (arXiv:2608.30404, Table 1, 160 test scans, read from the PDF on 2026-11-22):

| segment | n (both drew) | presence agreement % | DSC | centreline clDice |
|---|---|---|---|---|
| D1 | 155 | 96.9 | 79.9 +- 28.7 | 85.0 +- 30.2 |
| D2 | 91 | 89.4 | 82.9 +- 24.3 | 88.1 +- 25.3 |
| OM1 | 132 | 94.4 | 74.1 +- 32.3 | 79.8 +- 34.2 |
| OM2 | 46 | 87.5 | 77.7 +- 29.1 | 83.7 +- 30.6 |
| R-PDA | 150 | 98.8 | 82.6 +- 21.9 | 88.4 +- 22.3 |
| R-PLA | 147 | 96.2 | 83.6 +- 18.6 | 89.4 +- 18.4 |

"Agreement is the percentage of scans in which both analysts either annotate that segment or both omit it. Remaining
metrics were computed over the n scans in which both analysts annotated the segment."

The model of one reference piece of class c, in a case where the reference has c:
  1. OMISSION, prob m_c: the reader does not draw c at all -> the piece is MISSED. m_c comes from Table 1: the
     160 (1 - A) disagreeing scans split evenly between "reference only" and "reader only" (two exchangeable analysts),
     so m_c = (160 (1 - A)/2) / (n + 160 (1 - A)/2); the reader ADDS c to a reference-absent case with
     f_c = (160 (1 - A)/2) / (160 - n - 160 (1 - A)/2).
  2. Otherwise both drew c. The centreline clDice of the pair is a two-part mixture fitted to Table 1's mean and SD:
     with prob p0_c the reader's c is elsewhere (coverage ~ 0: a different branch called c, or a stub), else its
     coverage is Beta with mean h_c and SD SIGMA_H (default 0.08). In the low part, a share S_NAMING of pieces is
     covered by another class (DETECTED, MISNAMED: an ordinal shift); the rest is MISSED (a stub). In the high part
     the piece is DETECTED if coverage >= 0.5, and NAMED RIGHT.
clDice has no 1.5 mm tolerance and is a harmonic mean with precision, so it understates coverage: the rates below
are upper bounds on the false-fail rate in that respect.

Locked-100 counts (Delta v1's label counts, F-A7): cases with D1 98, D2 64, OM1 84, OM2 40, PDA 96, PLB 96 of 100.
Pieces per case are drawn from the 620's empirical distribution (census_r2.jsonl) when given, else 1.

B1: recall (detected / pieces) >= R_LINE and presence agreement >= Table 1 A - 0.05. B2: named / detected >= N_LINE.
A class passes when B1 and B2 pass. The verdict needs >= 4 of 6 classes passing.

Usage: python gate_sim.py [census_r2.jsonl] [out.json]
"""
import json
import sys

import numpy as np

T1 = {  # n, agreement, clDice mean, clDice sd  (ImageCAS-X Table 1)
    'D1': (155, .969, .850, .302), 'D2': (91, .894, .881, .253), 'OM1': (132, .944, .798, .342),
    'OM2': (46, .875, .837, .306), 'PDA': (150, .988, .884, .223), 'PLB': (147, .962, .894, .184)}
LOCKED = {'D1': 98, 'D2': 64, 'OM1': 84, 'OM2': 40, 'PDA': 96, 'PLB': 96}
AS_RULED = {'recall': 0.80, 'naming': 0.85, 'presence_margin': 0.05, 'k_of_6': 4}
REPS = 8000


def fit_mixture(mu, sd, sigma_h):
    """a = 1 - p0, h: a*h = mu, a*sigma_h^2 + a(1-a)h^2 = sd^2. Solved on a grid; h capped at 0.995."""
    best = None
    for a in np.linspace(0.30, 1.0, 70001):
        h = mu / a
        if h > 0.995:
            continue
        v = a * sigma_h ** 2 + a * (1 - a) * h ** 2
        e = abs(v - sd ** 2)
        if best is None or e < best[0]:
            best = (e, a, h)
    return 1 - best[1], best[2]


def params(sigma_h):
    out = {}
    for c, (n, A, mu, sd) in T1.items():
        dis = 160 * (1 - A) / 2
        m = dis / (n + dis)
        f = dis / max(160 - n - dis, 1e-9)
        p0, h = fit_mixture(mu, sd, sigma_h)
        out[c] = {'m': m, 'f': f, 'p0': p0, 'h': h, 'A': A}
    return out


def pieces_dist(census):
    d = {c: [1] for c in T1}
    if not census:
        return d
    rows = [json.loads(l) for l in open(census)]
    for c in T1:
        k = [len(r['pieces'][c]) for r in rows if len(r['pieces'][c])]
        d[c] = k
    return d


def simulate(par, pdist, lines, s_naming=0.5, sigma_h=0.08, reps=REPS, n_cases=100, seed=0, shift=None):
    """Returns per-class pass rates and the k-of-6 verdict pass rate. `shift` (dict of deltas) makes the model worse
    than human: extra omission dm, extra misnaming dn (power)."""
    rng = np.random.default_rng(seed)
    res = {c: {'recall': [], 'naming': [], 'presence': [], 'pass': []} for c in T1}
    npass = np.zeros(reps, int)
    for c in T1:
        p = par[c]
        m = min(p['m'] + (shift or {}).get('dm', 0), 1)
        dn = (shift or {}).get('dn', 0)
        npos = round(LOCKED[c] * n_cases / 100)
        h = p['h']
        ab = h * (1 - h) / sigma_h ** 2 - 1
        al, be = h * ab, (1 - h) * ab
        for r in range(reps):
            k = rng.choice(pdist[c], size=npos)
            omit_case = rng.random(npos) < m                     # reader draws no c in this case
            add_case = rng.random(n_cases - npos) < p['f']
            pres_agree = (npos - omit_case.sum() + (n_cases - npos) - add_case.sum()) / n_cases
            tot = int(k.sum())
            om = np.repeat(omit_case, k)
            low = rng.random(tot) < p['p0']
            low_named_other = rng.random(tot) < s_naming
            cov = rng.beta(al, be, tot)
            det = ~om & ((low & low_named_other) | (~low & (cov >= 0.5)))
            named = det & ~low & (rng.random(tot) >= dn)
            rec = det.sum() / tot
            nam = named.sum() / max(det.sum(), 1)
            ok = (rec >= lines['recall'] - 1e-12) and (nam >= lines['naming'] - 1e-12) and \
                 (pres_agree >= p['A'] - lines['presence_margin'] - 1e-12)
            res[c]['recall'].append(rec); res[c]['naming'].append(nam); res[c]['presence'].append(pres_agree)
            res[c]['pass'].append(ok)
            npass[r] += ok
    out = {}
    for c in T1:
        R = {k: np.asarray(v) for k, v in res[c].items()}
        out[c] = {'fail_rate': round(1 - R['pass'].mean(), 4),
                  'fail_recall': round(float((R['recall'] < lines['recall'] - 1e-12).mean()), 4),
                  'fail_naming': round(float((R['naming'] < lines['naming'] - 1e-12).mean()), 4),
                  'fail_presence': round(float((R['presence'] < par[c]['A'] - lines['presence_margin'] - 1e-12)
                                               .mean()), 4),
                  'recall_mean': round(float(R['recall'].mean()), 4),
                  'recall_p05': round(float(np.percentile(R['recall'], 5)), 4),
                  'naming_mean': round(float(R['naming'].mean()), 4),
                  'naming_p05': round(float(np.percentile(R['naming'], 5)), 4),
                  'presence_mean': round(float(R['presence'].mean()), 4),
                  'presence_p05': round(float(np.percentile(R['presence'], 5)), 4)}
    out['verdict_fail_rate'] = round(float((npass < lines['k_of_6']).mean()), 4)
    out['npass_dist'] = {int(k): round(float((npass == k).mean()), 4) for k in range(7)}
    return out


def simulate_lines(par, pdist, prop, s_naming, sigma_h, reps, seed, shift=None):
    """simulate() with per-class lines {c: {recall, naming, presence}}; verdict needs >= 4 of 6."""
    per = {}
    for i, c in enumerate(T1):
        lines = {'recall': prop[c]['recall'], 'naming': prop[c]['naming'],
                 'presence_margin': par[c]['A'] - prop[c]['presence'], 'k_of_6': 0}
        one = {c: par[c]}
        r = _simulate_subset(one, pdist, lines, s_naming, sigma_h, reps, seed + 17 * i, shift)
        per[c] = r
    out = {c: per[c]['stats'] for c in T1}
    npass = np.sum([per[c]['pass'] for c in T1], axis=0)
    out['verdict_fail_rate'] = round(float((npass < 4).mean()), 4)
    out['npass_dist'] = {int(k): round(float((npass == k).mean()), 4) for k in range(7)}
    return out


def _simulate_subset(par1, pdist, lines, s_naming, sigma_h, reps, seed, shift):
    c = next(iter(par1))
    full = {k: par1[c] for k in T1}           # simulate() loops over T1; only c is used
    rng_seed = seed
    r = simulate_one(c, par1[c], pdist, lines, s_naming, sigma_h, reps, rng_seed, shift)
    return r


def simulate_one(c, p, pdist, lines, s_naming, sigma_h, reps, seed, shift=None, n_cases=100):
    rng = np.random.default_rng(seed)
    m = min(p['m'] + (shift or {}).get('dm', 0), 1)
    dn = (shift or {}).get('dn', 0)
    npos = round(LOCKED[c] * n_cases / 100)
    h = p['h']
    ab = h * (1 - h) / sigma_h ** 2 - 1
    al, be = h * ab, (1 - h) * ab
    R, N, P, ok = [], [], [], []
    for r in range(reps):
        k = rng.choice(pdist[c], size=npos)
        omit_case = rng.random(npos) < m
        add_case = rng.random(n_cases - npos) < p['f']
        pa = (npos - omit_case.sum() + (n_cases - npos) - add_case.sum()) / n_cases
        tot = int(k.sum())
        om = np.repeat(omit_case, k)
        low = rng.random(tot) < p['p0']
        lno = rng.random(tot) < s_naming
        cov = rng.beta(al, be, tot)
        det = ~om & ((low & lno) | (~low & (cov >= 0.5)))
        named = det & ~low & (rng.random(tot) >= dn)
        rec = det.sum() / tot
        nam = named.sum() / max(det.sum(), 1)
        R.append(rec); N.append(nam); P.append(pa)
        ok.append((rec >= lines['recall'] - 1e-12) and (nam >= lines['naming'] - 1e-12) and
                  (pa >= p['A'] - lines['presence_margin'] - 1e-12))
    R, N, P, ok = map(np.asarray, (R, N, P, ok))
    stats = {'fail_rate': round(1 - ok.mean(), 4),
             'fail_recall': round(float((R < lines['recall'] - 1e-12).mean()), 4),
             'fail_naming': round(float((N < lines['naming'] - 1e-12).mean()), 4),
             'fail_presence': round(float((P < p['A'] - lines['presence_margin'] - 1e-12).mean()), 4),
             'recall_mean': round(float(R.mean()), 4), 'naming_mean': round(float(N.mean()), 4),
             'presence_mean': round(float(P.mean()), 4)}
    return {'stats': stats, 'pass': ok}


def main():
    census = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != '-' else None
    outp = sys.argv[2] if len(sys.argv) > 2 else None
    pdist = pieces_dist(census)
    report = {'pieces_per_case': {c: {int(k): int((np.asarray(v) == k).sum()) for k in sorted(set(v))}
                                  for c, v in pdist.items()}}
    for sh in (0.05, 0.08, 0.12):
        report[f'params_sigma{sh}'] = {c: {k: round(v, 4) for k, v in d.items()} for c, d in params(sh).items()}
    runs = {}
    for sh in (0.05, 0.08, 0.12):
        par = params(sh)
        for s in (0.0, 0.5, 1.0):
            runs[f'as_ruled sigma_h={sh} s_naming={s}'] = simulate(par, pdist, AS_RULED, s, sh, reps=REPS // 4)
    report['as_ruled'] = runs
    # proposed: per-class lines, each at the 5th percentile of a human-level model in the WORST scenario for that
    # statistic (recall: all low-mode pieces are stubs, s=0, sigma_h=0.12; naming: all are ordinal shifts, s=1,
    # sigma_h=0.05; presence: Table 1's binomial), rounded DOWN to 0.01.
    free = {'recall': 0, 'naming': 0, 'presence_margin': 1, 'k_of_6': 0}
    wr = simulate(params(0.12), pdist, free, 0.0, 0.12, seed=3)
    wn = simulate(params(0.05), pdist, free, 1.0, 0.05, seed=4)
    report['worst_recall_scenario'], report['worst_naming_scenario'] = wr, wn
    prop = {c: {'recall': float(np.floor(wr[c]['recall_p05'] * 100) / 100),
                'naming': float(np.floor(wn[c]['naming_p05'] * 100) / 100),
                'presence': float(np.floor(min(wr[c]['presence_p05'], wn[c]['presence_p05']) * 100) / 100)}
            for c in T1}
    report['proposed_lines'] = prop
    pr = {}
    for sh in (0.05, 0.08, 0.12):
        for s_ in (0.0, 0.5, 1.0):
            pr[f'proposed sigma_h={sh} s_naming={s_}'] = simulate_lines(params(sh), pdist, prop, s_, sh,
                                                                     reps=REPS // 4, seed=1)
    report['proposed_human'] = pr
    uni = prop
    par = params(0.08)
    # power: models worse than human
    pw = {}
    for lab, shift in (('omission +0.10', {'dm': 0.10}), ('omission +0.20', {'dm': 0.20}),
                       ('misnaming 0.10', {'dn': 0.10}), ('misnaming 0.20', {'dn': 0.20}),
                       ('both +0.10/0.10', {'dm': 0.10, 'dn': 0.10}), ('icx14: all misnamed', {'dn': 1.0})):
        pw[lab + ' | as_ruled'] = simulate(par, pdist, AS_RULED, 0.5, 0.08, reps=REPS // 4, seed=2, shift=shift)
        pw[lab + ' | proposed'] = simulate_lines(par, pdist, prop, 0.5, 0.08, reps=REPS // 4, seed=2, shift=shift)
    report['power'] = pw
    s = json.dumps(report, indent=1)
    if outp:
        open(outp, 'w').write(s)
    for k in ('as_ruled sigma_h=0.08 s_naming=0.5',):
        print(k, {c: v['fail_rate'] for c, v in runs[k].items() if c in T1}, 'verdict', runs[k]['verdict_fail_rate'])
    print('proposed', prop)
    for k in pr:
        print(k, {c: v['fail_rate'] for c, v in pr[k].items() if c in T1}, 'verdict', pr[k]['verdict_fail_rate'])


if __name__ == '__main__':
    main()
