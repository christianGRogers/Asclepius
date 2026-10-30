"""Golf R2 E6: how many paired patients does a segment-level LIE-vs-LGE validation need?

Path B's reference standard for scar is CMR late gadolinium enhancement (LGE), read per AHA segment in Kim bins
(0 | 1-25 | 26-50 | 51-75 | 76-100 %). Janus-M grades LIE CT in the same bins. Segments of one patient are not
independent, so the size is set by patients, with a patient random effect, and every CI is a patient bootstrap.

Simulated cohort (all parameters are stated assumptions, varied in a grid):
  - N patients; a share `enrich` has LGE scar (an enriched cohort: known or suspected prior infarction), the rest none.
  - A scar patient has K ~ 1 + Poisson(lam) LGE-positive segments (capped at 16), contiguous by AHA index.
  - Their true bins are drawn with weights BIN_W over bins 1-4.
  - 16 segments per patient (segment 17 is left out, as many LGE reads do).
  - Grader: detects a scar segment with per-bin probability SENS_BY_BIN (pooled ~0.86, Gatti 2025 segment level);
    calls a scar-free segment scar with 1 - spec (0.98, Gatti 2025). A patient random effect on the logit
    (SD tau) makes errors cluster within patients. A detected segment is graded in its true bin with
    probability 1 - q, one bin off otherwise (within 1-4).
Endpoints, each judged on the 95 % patient-bootstrap lower bound (one look):
  E-sens: segment sensitivity for scar presence >= 0.75
  E-spec: segment specificity >= 0.93
  E-kap : linear-weighted kappa over all 16 x N segments >= 0.60
Power = share of simulated studies that pass. Output: cohort_power.json.

Usage: python cohort_power.py [--sims 400] [--boot 400]
"""
import argparse, json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SENS_BY_BIN = {1: 0.70, 2: 0.88, 3: 0.93, 4: 0.97}
BIN_W = np.array([0.30, 0.25, 0.25, 0.20])
SPEC = 0.98
TARGET = {"sens": 0.75, "spec": 0.93, "kappa": 0.60}


def logit(p):
    return np.log(p / (1 - p))


def expit(x):
    return 1 / (1 + np.exp(-x))


def simulate(N, enrich, lam, tau, q, rng):
    T = np.zeros((N, 16), int)
    G = np.zeros((N, 16), int)
    for i in range(N):
        b = rng.normal(0, tau)
        if rng.random() < enrich:
            K = min(1 + rng.poisson(lam), 16)
            start = rng.integers(16)
            idx = (start + np.arange(K)) % 16
            T[i, idx] = rng.choice([1, 2, 3, 4], size=K, p=BIN_W)
        for j in range(16):
            t = T[i, j]
            if t == 0:
                G[i, j] = rng.choice([1, 2], p=[0.7, 0.3]) if rng.random() < expit(logit(1 - SPEC) + b) else 0
            elif rng.random() < expit(logit(SENS_BY_BIN[t]) - b):
                G[i, j] = t if rng.random() > q else int(np.clip(t + rng.choice([-1, 1]), 1, 4))
    return T, G


def wkappa_counts(O):
    k = O.shape[0]
    W = np.abs(np.subtract.outer(np.arange(k), np.arange(k))) / (k - 1)
    E = np.outer(O.sum(1), O.sum(0)) / O.sum()
    return 1 - (W * O).sum() / max((W * E).sum(), 1e-9)


def stats_from(Tp, Gp):
    """Per-patient sufficient statistics so a bootstrap is a weighted sum."""
    N = Tp.shape[0]
    tp = ((Tp > 0) & (Gp > 0)).sum(1); pos = (Tp > 0).sum(1)
    tn = ((Tp == 0) & (Gp == 0)).sum(1); neg = (Tp == 0).sum(1)
    O = np.zeros((N, 5, 5))
    for i in range(N):
        np.add.at(O[i], (Tp[i], Gp[i]), 1)
    return tp, pos, tn, neg, O


def lower_bounds(T, G, boot, rng):
    tp, pos, tn, neg, O = stats_from(T, G)
    N = len(tp)
    W = rng.multinomial(N, np.ones(N) / N, size=boot).astype(float)
    sens = (W @ tp) / np.maximum(W @ pos, 1)
    spec = (W @ tn) / np.maximum(W @ neg, 1)
    kap = np.array([wkappa_counts(np.tensordot(w, O, 1)) for w in W])
    return {"sens": float(np.percentile(sens, 2.5)), "spec": float(np.percentile(spec, 2.5)),
            "kappa": float(np.percentile(kap, 2.5)),
            "point": {"sens": float(tp.sum() / max(pos.sum(), 1)), "spec": float(tn.sum() / neg.sum()),
                      "kappa": float(wkappa_counts(O.sum(0)))}}


def power(N, enrich, lam, tau, q, sims, boot, seed):
    rng = np.random.default_rng(seed)
    ok = {k: 0 for k in TARGET}; allok = 0; pts = []
    for _ in range(sims):
        T, G = simulate(N, enrich, lam, tau, q, rng)
        lb = lower_bounds(T, G, boot, rng)
        p = {k: lb[k] >= TARGET[k] for k in TARGET}
        for k in TARGET:
            ok[k] += p[k]
        allok += all(p.values())
        pts.append(lb["point"])
    return {"N": N, "enrich": enrich, "lam": lam, "tau": tau, "q": q,
            "power": {k: ok[k] / sims for k in TARGET}, "power_all": allok / sims,
            "point_median": {k: float(np.median([p[k] for p in pts])) for k in TARGET}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=400)
    ap.add_argument("--boot", type=int, default=400)
    a = ap.parse_args()
    grid = []
    base = dict(lam=3.0, tau=0.7, q=0.25)
    for enrich in (0.3, 0.5, 0.7):
        for N in (30, 40, 60, 80, 100, 120, 160):
            grid.append(dict(N=N, enrich=enrich, **base))
    for tau in (0.0, 1.2):                          # within-patient clustering: none, strong
        for N in (60, 80, 100, 120):
            grid.append(dict(N=N, enrich=0.5, lam=3.0, tau=tau, q=0.25))
    for lam in (1.5,):                              # smaller infarcts
        for N in (60, 80, 100, 120, 160):
            grid.append(dict(N=N, enrich=0.5, lam=lam, tau=0.7, q=0.25))
    for q in (0.40,):                               # worse bin agreement
        for N in (60, 80, 100, 120, 160):
            grid.append(dict(N=N, enrich=0.5, lam=3.0, tau=0.7, q=q))
    res = []
    for n, g in enumerate(grid):
        r = power(**g, sims=a.sims, boot=a.boot, seed=1000 + n)
        res.append(r)
        print(r, flush=True)
    meta = {"assumptions": {"sens_by_bin": SENS_BY_BIN, "bin_weights_1_4": BIN_W.tolist(), "spec": SPEC,
                            "targets_lower_95": TARGET, "segments_per_patient": 16,
                            "sims": a.sims, "boot": a.boot}}
    (HERE / "cohort_power.json").write_text(json.dumps({**meta, "grid": res}, indent=1) + "\n")
