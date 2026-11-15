"""Janus 1-F round 2 (Delta), item 1: false-fail rate of the B gates (F-A6) for a human-level model, and their power
against bad models, on the locked 100's own reference branches. CPU, labels only (census/ordinal from j1f_r1).

Generative model of a second reader B against the reference A (ImageCAS-X), per locked case:
  * every reference branch of class c is dropped (not traced) with probability m_c;
  * extra branches are inserted on each parent side (LAD side, LCx side) at a Poisson rate lam_side, at a uniformly
    random rank among that side's siblings;
  * names on the LAD and LCx sides are positional, as ImageCAS-X numbers them (j1f_r1 finding 2): B's k-th LAD-side
    branch is D1, D2, D3, then LAD; B's k-th LCx-side branch is OM1, OM2, then LCx;
  * PDA and PLB are not ordinal: each is dropped with m_c and, if kept, swapped with the other with probability eps.
m_c and lam come from ImageCAS-X Table 1 (arXiv:2608.30404; agreement a_c over 160 scans, n_c scans with both),
with disagreements split evenly between misses and extras (d_c = 160 (1 - a_c); m_c = (d_c/2) / (n_c + d_c/2)).
The emergent presence agreement is printed beside Table 1's so the model can be checked.

Gates (F-A6): B1 = detection recall >= R and presence agreement >= a_c - 0.05; B2 = naming accuracy >= N.
Verdict: >= 4 of 6 gated classes pass.  Usage: python gate_sim.py <j1f_r1 dir> <out.json>
"""
import json, sys
import numpy as np

D = sys.argv[1]
cen = {r['case']: r for r in json.load(open(f'{D}/census.json'))['rows']}
ordi = {r['case']: r for r in json.load(open(f'{D}/ordinal.json'))}
LOCKED = sorted(c for c, r in cen.items() if r['group'] in ('val80', 'locked_open20'))
assert len(LOCKED) == 100
MIN_MM = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0   # presence: centreline >= MIN_MM

# ImageCAS-X Table 1 (re-read 2026-11-15 from the arXiv HTML): segment: (n both, agreement %)
T1 = {'D1': (155, 96.9), 'D2': (91, 89.4), 'OM1': (132, 94.4), 'OM2': (46, 87.5), 'PDA': (150, 98.8),
      'PLB': (147, 96.2)}
GATED = ['D1', 'D2', 'OM1', 'OM2', 'PDA', 'PLB']


def miss_rate(c, k=1.0):
    n, a = T1[c]; d = 160 * (1 - a / 100)
    return min(1.0, k * (d / 2) / (n + d / 2))


def extras_per_case(cs, k=1.0):
    return k * sum(160 * (1 - T1[c][1] / 100) / 2 for c in cs) / 160


def present(r, cls):
    v = r['classes'].get(cls)
    return v is not None and v['cl_mm'] >= MIN_MM


def ref_case(c):
    """Reference sequences: LAD side and LCx side as ordered lists of names; PDA/PLB presence (D47 Q1 (A): a left
    PDA/PLA is PDA/PLB)."""
    r, o = cen[c], ordi[c]
    lad = [n for n in ('D1', 'D2') if present(r, n)]
    if (r.get('other_sides') or {}).get('lad', 0) >= 1 and 'Other' in r['classes']:
        lad.append('D3')   # first LAD-side Other piece (j1f_r1 finding 2); presence by the Other class length
    lcx = [n for n in ('OM1', 'OM2') if present(r, n)]
    pda = present(r, 'R-PDA') or present(r, 'L-PDA')
    plb = present(r, 'R-PLA') or present(r, 'L-PLA')
    return lad, lcx, pda, plb


REF = {c: ref_case(c) for c in LOCKED}
NPOS = {k: sum(1 for c in LOCKED if (k in REF[c][0] or k in REF[c][1] or (k == 'PDA' and REF[c][2])
                                     or (k == 'PLB' and REF[c][3]))) for k in GATED + ['D3']}

LADN, LCXN = ['D1', 'D2', 'D3'], ['OM1', 'OM2']


def read_side(rng, ref, names, m, lam):
    """Return B's names for each reference branch (None if dropped) and the set of names B has."""
    kept = [(i, rng.random() >= m[n]) for i, n in enumerate(ref)]
    seq = [('ref', i) for i, k in kept if k]
    for _ in range(rng.poisson(lam)):
        seq.insert(rng.integers(0, len(seq) + 1), ('extra', None))
    bname = {}
    have = set()
    for rank, (kind, i) in enumerate(seq):
        nm = names[rank] if rank < len(names) else None
        if nm: have.add(nm)
        if kind == 'ref': bname[i] = nm
    return [bname.get(i, 'DROPPED') for i in range(len(ref))], have


def simulate(rng, m, lam_lad, lam_lcx, eps, extra_pp):
    """One draw of reader B on the locked 100 -> per class (recall, agreement, naming)."""
    det = {k: [0, 0] for k in GATED}; agree = {k: 0 for k in GATED}; nam = {k: [0, 0] for k in GATED}
    for c in LOCKED:
        lad, lcx, pda, plb = REF[c]
        for ref, names, lam in ((lad, LADN, lam_lad), (lcx, LCXN, lam_lcx)):
            bn, have = read_side(rng, ref, names, m, lam)
            for n, b in zip(ref, bn):
                if n not in det: continue
                det[n][1] += 1
                if b != 'DROPPED':
                    det[n][0] += 1; nam[n][1] += 1; nam[n][0] += (b == n)
            for n in names:
                if n in agree: agree[n] += ((n in ref) == (n in have))
        bpp = {}
        for n, p in (('PDA', pda), ('PLB', plb)):
            if p:
                det[n][1] += 1
                if rng.random() >= m[n]:
                    det[n][0] += 1; nam[n][1] += 1
                    swap = rng.random() < eps
                    nam[n][0] += (not swap)
                    bpp[n if not swap else ('PLB' if n == 'PDA' else 'PDA')] = True
            elif rng.random() < extra_pp[n]:
                bpp[n] = True
        for n, p in (('PDA', pda), ('PLB', plb)):
            agree[n] += (p == bpp.get(n, False))
    out = {}
    for k in GATED:
        out[k] = (det[k][0] / max(det[k][1], 1), agree[k] / 100, nam[k][0] / max(nam[k][1], 1))
    return out


def run(label, m, lam_lad, lam_lcx, eps, extra_pp, R=0.80, N=0.85, margin=0.05, draws=4000, seed=0,
        alt=None):
    rng = np.random.default_rng(seed)
    acc = {k: [] for k in GATED}
    for _ in range(draws):
        s = simulate(rng, m, lam_lad, lam_lcx, eps, extra_pp)
        if alt: s = alt(rng, s)
        for k in GATED: acc[k].append(s[k])
    res = {'label': label, 'classes': {}}
    npass = np.zeros(draws, int)
    for k in GATED:
        a = np.array(acc[k])
        line = T1[k][1] / 100 - margin
        f_rec, f_agr, f_nam = a[:, 0] < R, a[:, 1] < line, a[:, 2] < N
        ok = ~(f_rec | f_agr | f_nam)
        npass += ok
        res['classes'][k] = {
            'n_ref': NPOS[k], 'mean_recall': a[:, 0].mean(), 'p2.5_recall': np.percentile(a[:, 0], 2.5),
            'mean_agree': a[:, 1].mean(), 'table1_agree': T1[k][1] / 100, 'line_agree': line,
            'p2.5_agree': np.percentile(a[:, 1], 2.5),
            'mean_naming': a[:, 2].mean(), 'p2.5_naming': np.percentile(a[:, 2], 2.5),
            'fail_B1_recall': f_rec.mean(), 'fail_B1_agree': f_agr.mean(), 'fail_B2': f_nam.mean(),
            'fail_class': 1 - ok.mean()}
    res['p_lt4_of_6'] = float((npass < 4).mean())
    res['p_all6'] = float((npass == 6).mean())
    res['mean_classes_passing'] = float(npass.mean())
    return res


def human(k=1.0):
    m = {c: miss_rate(c, k) for c in GATED}
    m['D3'] = m['D2']
    lam_lad = extras_per_case(['D1', 'D2'], k); lam_lcx = extras_per_case(['OM1', 'OM2'], k)
    # extras for PDA/PLB: reference-negative cases are few (1-4 of 100); rate from Table 1's split
    xpp = {c: min(1.0, k * (160 * (1 - T1[c][1] / 100) / 2) / max(160 - T1[c][0] - 160 * (1 - T1[c][1] / 100) / 2,
                                                               1)) for c in ('PDA', 'PLB')}
    return m, lam_lad, lam_lcx, xpp


if __name__ == '__main__':
    out = {'npos_locked': NPOS, 'min_mm': MIN_MM, 'miss_rates_human': {c: miss_rate(c) for c in GATED},
           'runs': []}
    LINES = {'F-A6 as ruled (R 0.80, N 0.85, margin 0.05)': (0.80, 0.85, 0.05),
             'proposed (R 0.75, N 0.80, margin 0.05)': (0.75, 0.80, 0.05),
             'looser (R 0.75, N 0.80, margin 0.07)': (0.75, 0.80, 0.07)}

    def always(rng, s):   # calls every class present in every case, otherwise human
        return {k: (v[0] if k not in ('D2', 'OM2') else 1.0, NPOS[k] / 100, v[2]) for k, v in s.items()}

    def shift(f):         # ordinal shift on each side in a share f of cases: naming down by f
        return lambda rng, s: {k: (v[0], v[1], v[2] - (f if k in ('D1', 'D2', 'OM1', 'OM2') else 0.0))
                               for k, v in s.items()}
    for lname, (R, N, mg) in LINES.items():
        for k, eps in ((1.0, 0.01), (1.5, 0.01), (1.0, 0.02)):
            m, ll, lc, xpp = human(k)
            out['runs'].append(run(f'{lname} | human x{k}, PDA/PLB swap {eps}', m, ll, lc, eps, xpp, R=R, N=N,
                                   margin=mg))
        m, ll, lc, xpp = human(1.0)
        out['runs'].append(run(f'{lname} | bad: every class in every case', m, ll, lc, 0.01, xpp, R=R, N=N,
                               margin=mg, alt=always))
        for f in (0.25, 0.15):
            out['runs'].append(run(f'{lname} | bad: ordinal shift in {f:.0%} of cases', m, ll, lc, 0.01, xpp,
                                   R=R, N=N, margin=mg, alt=shift(f)))
        for q in (0.35, 0.20):
            mq = {c: q for c in m}
            out['runs'].append(run(f'{lname} | bad: misses {q:.0%} of every branch', mq, ll, lc, 0.01, xpp,
                                   R=R, N=N, margin=mg))
    json.dump(out, open(sys.argv[2], 'w'), indent=1, default=float)
    print('locked reference counts (presence >= %.0f mm):' % MIN_MM, NPOS)
    print('human miss rates:', {k: round(v, 3) for k, v in out['miss_rates_human'].items()})
    for r in out['runs']:
        print('\n##', r['label'], '| P(<4 of 6) = %.3f, P(6 of 6) = %.3f, mean passing %.2f' % (
            r['p_lt4_of_6'], r['p_all6'], r['mean_classes_passing']))
        for k, v in r['classes'].items():
            print('  %-4s n=%3d rec %.3f agr %.3f [T1 %.3f, line %.3f] nam %.3f | '
                  'fail rec %.3f agr %.3f nam %.3f class %.3f' % (
                      k, v['n_ref'], v['mean_recall'], v['mean_agree'], v['table1_agree'],
                      v['line_agree'], v['mean_naming'], v['fail_B1_recall'],
                      v['fail_B1_agree'], v['fail_B2'], v['fail_class']))
