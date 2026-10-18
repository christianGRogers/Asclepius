"""Bridge, Round 9: how many double-read pool cases does A10 (D6: non-inferior to inter-read tF1 within 0.05,
per class, all four) need, and what does a paired training comparison detect on the ImageCAS-X test split?

Model per-case spread: atlas2's run-1 val (80 cases, A1 ostia, frozen segtrain.tf1), the only real per-case tF1
we have. The inter-read spread is unknown (no team reads yet), so it is a scenario (k x model SD).
CPU only; reads trillium-results/round6/atlas2/results/per_case_run1.json and per_case_b.json; no sealed case.
Usage: python3 a10_pool_power.py <repo_root> > out.json"""
import json, sys, math
import numpy as np

root = sys.argv[1]
R = f'{root}/trillium-results/round6/atlas2/results'
run1 = json.load(open(f'{R}/per_case_run1.json'))
runb = json.load(open(f'{R}/per_case_b.json'))
CL = {'1': 'LM', '2': 'LAD', '3': 'LCx', '4': 'RCA'}
rng = np.random.default_rng(20261018)
out = {}


def scores(rows, flagged_out=True):
    s = {c: [] for c in CL}
    for r in rows:
        fl = {str(x) for x in r.get('flagged_classes', [])}
        for c in CL:
            v = r['per_class'].get(c)
            if v is None or (flagged_out and c in fl):
                continue
            s[c].append(v)
    return {c: np.array(v) for c, v in s.items()}


m = scores(run1)
out['model_sd_unflagged'] = {CL[c]: [round(float(v.std(ddof=1)), 4), len(v), round(float(v.mean()), 4)]
                             for c, v in m.items()}
mf = scores(run1, flagged_out=False)
out['model_sd_with_flagged'] = {CL[c]: [round(float(v.std(ddof=1)), 4), len(v)] for c, v in mf.items()}

# --- A10 on a sealed pool subset -------------------------------------------------------------------------
# per case: d = model-vs-reads tF1 (mean over the two reads) - inter-read tF1. Pass a class if the lower 95 %
# bound of mean(d) (t-based, two-sided 95 %) is above -0.05. Model draws: run-1's empirical per-case scores
# (keeps the heavy tail), averaged over two reads with read-to-read jitter; inter-read: an independent draw from
# the same empirical distribution, rescaled to k x the model SD (rho ~ 0 between the two, Crucible).
MARGIN = 0.05
NS = [50, 75, 100, 125, 150, 200, 250, 300]
SIMS = 4000
# share of cases that are scorable per class: LM short/absent (no centreline ~5 %, D13 LM optional),
# flagged ostia (A1b) -- without the A1b review the RCA keeps ~70 % (run 1: 56/80).
KEEP = {'reviewed': {'1': 0.85, '2': 0.95, '3': 0.95, '4': 0.95},
        'not_reviewed': {'1': 0.80, '2': 0.90, '3': 0.90, '4': 0.70}}


def sim_pass(n, delta, k_inter, f_model, keep):
    passes = np.ones(SIMS, bool)
    per = {}
    for c, base in m.items():
        nc = max(5, int(round(n * keep[c])))
        mu = base.mean()
        idx = rng.integers(0, len(base), (SIMS, nc))
        model = mu + f_model * (base[idx] - mu)          # model-vs-reads per case (mean of the 2 reads)
        idx2 = rng.integers(0, len(base), (SIMS, nc))
        inter = mu + k_inter * f_model * (base[idx2] - mu)  # inter-read per case, same mean
        d = model - inter + delta
        lo = d.mean(1) - 1.96 * d.std(1, ddof=1) / math.sqrt(nc)
        p = lo > -MARGIN
        per[CL[c]] = round(float(p.mean()), 3)
        passes &= p
    return round(float(passes.mean()), 3), per


grid = []
for keep_name, keep in KEEP.items():
    for f_model in (1.0, 1.5):            # 1.5: the pool is harder / more varied than ImageCAS val
        for k in (0.5, 1.0, 1.5):
            for delta in (0.0, -0.02, -0.03, -0.05, -0.07):
                for n in NS:
                    allp, per = sim_pass(n, delta, k, f_model, keep)
                    grid.append(dict(keep=keep_name, f_model=f_model, k_inter=k, delta=delta, n=n,
                                     p_all4=allp, per_class=per))
out['a10_grid'] = grid

# --- paired retrained comparison on the ImageCAS-X test split ---------------------------------------------
# paired SD per class from the real retrained contrast (B - run 1, val 80), then the MDE (80 % power,
# two-sided 0.05) with sigma_seed = 0.013 on macro (Crucible, Round 8 A22) and k seeds per arm.
b = {r['case']: r for r in runb}
pd = []
for r in run1:
    rb = b.get(r['case'])
    if rb and r.get('decisive') is not None and rb.get('decisive') is not None:
        pd.append(rb['decisive'] - r['decisive'])
pd = np.array(pd)
sd_pair = float(pd.std(ddof=1))
out['paired_sd_decisive_macro'] = [round(sd_pair, 4), len(pd)]
SIG = 0.013
mde = {}
for n in (36, 80, 160):
    for kseeds in (1, 2, 3, 4):
        se = math.sqrt(sd_pair ** 2 / n + SIG ** 2 / kseeds)
        mde[f'n{n}_seeds{kseeds}'] = round(2.8 * se, 4)
    mde[f'n{n}_case_only'] = round(2.8 * sd_pair / math.sqrt(n), 4)
out['mde_macro'] = mde
json.dump(out, sys.stdout, indent=1)
