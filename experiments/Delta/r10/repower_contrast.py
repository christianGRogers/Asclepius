"""Delta, Round 10: re-power A10 (D6) directly on the measured per-patient contrast, beside Bridge's f/k rule (A31.1).

A10 tests, per class, the mean over patients of d = model-vs-read tF1 - inter-read tF1 against -0.05. Its power at a
seal size depends only on the distribution of d. Bridge's f and k rebuild that distribution from two SD ratios and
assume rho = 0 between a patient's model-vs-read and inter-read. On Janus 0's spread, rho alone moves P(pass at
human level, n = 150) from 0.81 (rho 0) to 0.95 (rho 0.3) (power_r10.py). Wave 1 measures d itself, so this tool
resamples it:
  - per class, d_p for each primary patient with both comparisons (unflagged, a patient's volumes averaged), from
    experiments/Bridge/wave1/score_wave1.py's per_volume.jsonl;
  - patients are weighted to the seal's source mix (the D27/D32 file's per-source sealed counts), so a wave that is
    70 % one source does not set the seal size alone;
  - P(all four pass) at n = 150 / 175 / 200 / 228, with d centred at 0 (human level, delta = 0) and at its measured
    mean; the reported rho and SD(d) per class, with patient-bootstrap CIs.
Rule proposed (Delta v10 §4): extend to the smallest size whose P(pass | delta = 0) >= 0.80, using the lower 80 %
bootstrap bound of that power; if none does, report to the lead.
Usage: repower_contrast.py <per_volume.jsonl> [--out OUT.json]   |   repower_contrast.py --selftest"""
import argparse
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'experiments', 'Bridge', 'wave1'))
CL = ['LM', 'LAD', 'LCx', 'RCA']
NS = (150, 175, 200, 228)
MARGIN = 0.05


def stratum(src):
    if src in ('ImageCHD', 'ImageALCAPA'):
        return 'anomalous'
    if src in ('HOCMvalvesSeg', 'CCA200-HF'):
        return 'spacing_suspect'
    return 'primary'


def per_patient(rows, comp):
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        c = r.get(comp)
        if not c or r.get('error') or r.get('provisional'):
            continue
        for n, v in c['per_class'].items():
            if n not in c.get('flagged', []) and v is not None and np.isfinite(v):
                acc[r['patient']][n].append(v)
    return {p: {n: float(np.mean(v)) for n, v in d.items()} for p, d in acc.items()}


def seal_weights(src_of, seal_alloc):
    """Per-patient weight so that sources count as in the seal (sealed patients per source / sample patients)."""
    cnt = defaultdict(int)
    for s in src_of.values():
        cnt[s] += 1
    w = {p: seal_alloc.get(s, 0) / cnt[s] for p, s in src_of.items()}
    tot = sum(w.values())
    if tot == 0:          # no source in common with the seal: unweighted
        return {p: 1.0 for p in src_of}
    return {p: v * len(w) / tot for p, v in w.items()}


def power(d_by_class, w_by_class, n, centre, sims=4000, seed=7):
    rng = np.random.default_rng(seed)
    ok = np.ones(sims, bool)
    per = {}
    for c in CL:
        d = d_by_class.get(c)
        if d is None or len(d) < 3:
            per[c] = None
            continue
        d = np.asarray(d, float)
        w = np.asarray(w_by_class[c], float)
        w = w / w.sum()
        x = d - (np.sum(w * d) if centre else 0.0)
        idx = rng.choice(len(x), size=(sims, n), p=w)
        s = x[idx]
        lo = s.mean(1) - 1.96 * s.std(1, ddof=1) / math.sqrt(n)
        p = lo > -MARGIN
        per[c] = round(float(p.mean()), 3)
        ok &= p
    return round(float(ok.mean()), 3), per


def analyse(rows, seal_alloc, n_boot=200):
    src_of = {r['patient']: r['source'] for r in rows if 'patient' in r and stratum(r.get('source', '')) == 'primary'}
    model, inter = per_patient(rows, 'model'), per_patient(rows, 'inter')
    w = seal_weights(src_of, seal_alloc)
    d, wd, rho, sd = {}, {}, {}, {}
    for c in CL:
        pts = sorted(p for p in src_of if c in model.get(p, {}) and c in inter.get(p, {}))
        if len(pts) < 3:
            continue
        m = np.array([model[p][c] for p in pts])
        i = np.array([inter[p][c] for p in pts])
        d[c] = list(m - i)
        wd[c] = [w[p] for p in pts]
        rho[c] = round(float(np.corrcoef(m, i)[0, 1]), 3) if m.std() > 0 and i.std() > 0 else None
        sd[c] = round(float(np.std(m - i, ddof=1)), 4)
    res = dict(n_primary_patients=len(src_of), n_by_class={c: len(v) for c, v in d.items()}, rho=rho, sd_d=sd,
               mean_d={c: round(float(np.average(v, weights=wd[c])), 4) for c, v in d.items()})
    res['power_human_level'] = {n: power(d, wd, n, True) for n in NS}
    res['power_observed'] = {n: power(d, wd, n, False) for n in NS}
    # bootstrap over patients for the lower 80 % bound of the human-level power
    rng = np.random.default_rng(11)
    pts_all = sorted(src_of)
    lows = {n: [] for n in NS}
    for b in range(n_boot):
        pick = rng.choice(len(pts_all), len(pts_all))
        rb = [p for k in pick for p in [pts_all[k]]]
        db, wb = {}, {}
        for c in d:
            vals = [(model[p][c] - inter[p][c], w[p]) for p in rb if c in model.get(p, {}) and c in inter.get(p, {})]
            if len(vals) >= 3:
                db[c], wb[c] = [v for v, _ in vals], [x for _, x in vals]
        for n in NS:
            lows[n].append(power(db, wb, n, True, sims=500, seed=b)[0])
    res['power_human_level_lower80'] = {n: round(float(np.percentile(v, 20)), 3) for n, v in lows.items()}
    extend = next((n for n in NS if res['power_human_level_lower80'][n] >= 0.80), None)
    res['rule'] = ('seal size = the smallest n in (150, 175, 200, 228) whose lower-80 % human-level power >= 0.80; '
                   'none -> report to the lead')
    res['seal_size'] = extend if extend is not None else 'report to the lead'
    return res


def selftest():
    rng = np.random.default_rng(0)
    alloc = {'A': 20, 'B': 130}

    def rows(rho, sd):
        out = []
        for k in range(60):
            s = 'A' if k < 40 else 'B'
            z = rng.normal(size=2)
            m = 0.9 + sd * z[0]
            i = 0.9 + sd * (rho * z[0] + math.sqrt(1 - rho ** 2) * z[1])
            out.append(dict(volume=f'{s}__{k}.nii.gz', patient=f'{s}__{k}', source=s,
                            model={'per_class': {c: m for c in CL}, 'flagged': []},
                            inter={'per_class': {c: i for c in CL}, 'flagged': []}))
        return out
    lo = analyse(rows(0.0, 0.12), alloc, n_boot=40)
    hi = analyse(rows(0.7, 0.12), alloc, n_boot=40)
    assert hi['power_human_level'][150][0] > lo['power_human_level'][150][0], (lo, hi)
    assert hi['rho']['LAD'] > 0.5 and abs(lo['rho']['LAD']) < 0.35, (lo['rho'], hi['rho'])
    w = seal_weights({'A__1': 'A', 'A__2': 'A', 'B__1': 'B'}, alloc)
    assert w['B__1'] > w['A__1'], w
    print('[repower] self-test passed: P150 rho 0 / 0.7 =', lo['power_human_level'][150][0],
          hi['power_human_level'][150][0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rows', nargs='?')
    ap.add_argument('--out')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    seal = json.load(open(os.path.join(REPO, 'configs/segqueue14/sealed-pool-2026-10.json')))
    alloc = {s: v[0] for s, v in seal['primary']['allocation_[sealed,total]_by_source'].items()}
    rows = [json.loads(ln) for ln in open(a.rows) if ln.strip()]
    res = analyse(rows, alloc)
    s = json.dumps(res, indent=1)
    if a.out:
        open(a.out, 'w').write(s)
    print(s)


if __name__ == '__main__':
    main()
