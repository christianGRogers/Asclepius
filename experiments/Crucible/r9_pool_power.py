"""Round 9: how many sealed pool volumes (two team reads each, D23) does A10 need at D6's 0.05 per class?
Simulates per-case A10 contrasts d = tF1(model vs reads) - tF1(read A vs read B), per class, as correlated
Gaussians with Bridge's measured per-class SDs (Round 6 note, sec. 3), and runs the implemented rule
(segtrain.reads.acceptance: paired bootstrap 95 % CI, pass iff lower bound > -0.05 in every class).
Scenarios: delta = true mean contrast (0 = exactly human-level); SD x1.0 (ImageCAS-like) or x1.3 (pooled sources,
assumed harder); a share of cases dropped by A1b (flagged ostia) before the test. CPU only; no case data read."""
import sys, json
import numpy as np
sys.path.insert(0, 'src')
from segtrain.reads import acceptance  # noqa: E402

SD = {1: 0.17, 2: 0.15, 3: 0.19, 4: 0.19}   # Bridge Round 6 sec. 3: 0.14 (macro) to 0.19 (LCx, RCA); LM/LAD between
RHO = 0.3                                     # between-class correlation of the contrast (assumed; Bridge: LM 0.57)
REPS, NBOOT = 400, 1000


def sim(n, delta, scale, drop, rng):
    k = len(SD)
    sd = np.array([SD[c] for c in sorted(SD)]) * scale
    cov = RHO * np.outer(sd, sd); np.fill_diagonal(cov, sd ** 2)
    acc = 0; per = np.zeros(k)
    for r in range(REPS):
        d = rng.multivariate_normal(np.full(k, delta), cov, size=n)
        flagged = list(rng.random(n) < drop)
        model = [{c: 0.9 + d[i, j] for j, c in enumerate(sorted(SD))} for i in range(n)]
        inter = [{c: 0.9 for c in SD} for _ in range(n)]
        out = acceptance(model, inter, n_boot=NBOOT, seed=r, flagged=flagged, provisional=[False] * n)
        acc += bool(out['accepted'])
        per += [bool(out['per_class'][c]['pass']) for c in sorted(SD)]
    return acc / REPS, (per / REPS).round(2).tolist()


rng = np.random.default_rng(9)
rows = []
for scale in (1.0, 1.3):
    for drop in (0.0, 0.2):
        for delta in (-0.05, 0.0, 0.02):
            for n in (50, 75, 100, 150, 200):
                p, per = sim(n, delta, scale, drop, rng)
                rows.append(dict(scale=scale, drop=drop, delta=delta, n=n, p_all=p, p_class=per))
                print(json.dumps(rows[-1]), flush=True)
json.dump(rows, open(sys.argv[1] if len(sys.argv) > 1 else 'r9_pool_power.json', 'w'), indent=1)
