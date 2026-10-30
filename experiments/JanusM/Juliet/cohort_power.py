"""E5 (Juliet, Janus-M Round 2, path jm/paired-scar): how many paired patients does a segment-level validation of
CT scar transmurality against CMR LGE need?

Simulation only (no case is opened; guard_r2.gate() runs first anyway).

Truth (per patient, 17 AHA segments; Cerqueira 2002 standard artery map, verified from secondary sources only):
  - a share f_mi of the cohort has a prior MI: one scar patch of 2-7 contiguous segments inside one territory
    (LAD 1,2,7,8,13,14,17; RCA 3,4,9,10,15; LCx 5,6,11,12,16), taken in segment order from a random start;
  - the others carry an unrecognised scar with probability 0.10 (2-3 segments) -- ICELAND MI found 17 % in adults
    aged 67-93 (Schelbert 2012), so 0.10 for a younger referral cohort is an assumption;
  - each scarred segment's LGE Kim bin (1: 1-25, 2: 26-50, 3: 51-75, 4: 76-100 %) is drawn with weights
    (0.30, 0.25, 0.20, 0.25) -- an assumption, stated so the judge can change it.

CT read model (the pipeline's output per segment):
  - presence: per-segment sensitivity / specificity as pooled for LIE vs LGE (0.86 / 0.98; Gatti 2025), with a
    patient-level random effect (image quality; logit SD 0.8) so that segments within a patient are correlated;
  - given a detected scar, the bin is right with p_bin, one bin off with 0.8 (1-p_bin), two off otherwise;
    a false positive reads bin 1 (or 2 with p 0.2).
Scenarios: 'published' (0.86 / 0.98, p_bin 0.65) and 'weak' (0.72 / 0.95, p_bin 0.45) -- the second is a pipeline
that should FAIL the acceptance rule, so its pass rate is the rule's false-acceptance rate.

Endpoints, per simulated cohort, with patient-cluster bootstrap (B = 400) 95 % percentile CIs:
  quadratic-weighted kappa over 5 classes (0-4); segment sensitivity and specificity for scar presence.
Pre-registered success (proposed): lower bound kappa_w >= 0.60 AND sensitivity >= 0.70 AND specificity >= 0.90.
Power = share of 300 simulated cohorts that succeed, for N patients in the validation part of the cohort.

Usage: python cohort_power.py -> e5_cohort_power.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'e5_cohort_power.json'
TERR = {'LAD': [1, 2, 7, 8, 13, 14, 17], 'RCA': [3, 4, 9, 10, 15], 'LCx': [5, 6, 11, 12, 16]}
BIN_W = np.array([0.30, 0.25, 0.20, 0.25])
SCEN = {'published': dict(sens=0.86, spec=0.98, p_bin=0.65), 'weak': dict(sens=0.72, spec=0.95, p_bin=0.45)}
W = 1 - (np.subtract.outer(np.arange(5), np.arange(5)) ** 2) / 16.0       # quadratic agreement weights


def logit(p):
    return np.log(p / (1 - p))


def expit(x):
    return 1 / (1 + np.exp(-x))


def patient(rng, f_mi, sc):
    truth = np.zeros(17, int)
    if rng.random() < f_mi:
        k = rng.integers(2, 8)
    elif rng.random() < 0.10:
        k = rng.integers(2, 4)
    else:
        k = 0
    if k:
        segs = TERR[rng.choice(list(TERR))]
        k = min(k, len(segs))
        start = rng.integers(len(segs))
        for s in [segs[(start + i) % len(segs)] for i in range(k)]:
            truth[s - 1] = rng.choice(4, p=BIN_W) + 1
    z = rng.normal()
    se, sp = expit(logit(sc['sens']) + 0.8 * z), expit(logit(sc['spec']) + 0.8 * z)
    ct = np.zeros(17, int)
    for i, t in enumerate(truth):
        if t:
            if rng.random() < se:
                u = rng.random()
                if u < sc['p_bin']:
                    ct[i] = t
                else:
                    step = 1 if u < sc['p_bin'] + 0.8 * (1 - sc['p_bin']) else 2
                    ct[i] = int(np.clip(t + step * rng.choice([-1, 1]), 1, 4))
        elif rng.random() > sp:
            ct[i] = 1 if rng.random() < 0.8 else 2
    M = np.zeros((5, 5))
    np.add.at(M, (truth, ct), 1)
    return M


def kappa_w(M):
    n = M.sum(-1).sum(-1)[..., None, None]
    P = M / n
    r, c = P.sum(-1), P.sum(-2)
    E = r[..., :, None] * c[..., None, :]
    po, pe = (W * P).sum((-1, -2)), (W * E).sum((-1, -2))
    return (po - pe) / (1 - pe)


def endpoints(M):
    tp = M[..., 1:, 1:].sum((-1, -2))
    pos = M[..., 1:, :].sum((-1, -2))
    tn = M[..., 0, 0]
    neg = M[..., 0, :].sum(-1)
    return kappa_w(M), tp / pos, tn / neg


def cohort(rng, n, f_mi, sc, B=400):
    Ms = np.stack([patient(rng, f_mi, sc) for _ in range(n)])
    point = endpoints(Ms.sum(0))
    idx = rng.integers(0, n, (B, n))
    boot = endpoints(Ms[idx].sum(1))
    lo = [np.nanpercentile(b, 2.5) for b in boot]
    hi = [np.nanpercentile(b, 97.5) for b in boot]
    scarred = Ms[:, 1:, :].sum()
    return point, lo, hi, scarred


def main():
    sys.path.insert(0, str(HERE))
    import guard_r2
    guard_r2.gate([])
    rng = np.random.default_rng(20261030)
    rows = []
    for scen, sc in SCEN.items():
        for f_mi in (0.5, 0.8):
            for n in (30, 45, 60, 90, 120, 180):
                res = [cohort(rng, n, f_mi, sc) for _ in range(300)]
                lo = np.array([r[1] for r in res])
                hi = np.array([r[2] for r in res])
                pt = np.array([r[0] for r in res])
                ok = (lo[:, 0] >= 0.60) & (lo[:, 1] >= 0.70) & (lo[:, 2] >= 0.90)
                row = {'scenario': scen, 'f_mi': f_mi, 'n_patients': n, 'pass_rate': round(float(ok.mean()), 3),
                       'scarred_segments_median': float(np.median([r[3] for r in res])),
                       'kappa_w_mean': round(float(pt[:, 0].mean()), 3),
                       'sens_mean': round(float(pt[:, 1].mean()), 3), 'spec_mean': round(float(pt[:, 2].mean()), 3),
                       'ci_halfwidth_kappa': round(float(np.median((hi[:, 0] - lo[:, 0]) / 2)), 3),
                       'ci_halfwidth_sens': round(float(np.median((hi[:, 1] - lo[:, 1]) / 2)), 3),
                       'ci_halfwidth_spec': round(float(np.median((hi[:, 2] - lo[:, 2]) / 2)), 3),
                       'pass_kappa': round(float((lo[:, 0] >= 0.60).mean()), 3),
                       'pass_sens': round(float((lo[:, 1] >= 0.70).mean()), 3),
                       'pass_spec': round(float((lo[:, 2] >= 0.90).mean()), 3)}
                rows.append(row)
                print(row, flush=True)
    # Stress CTP vs invasive FFR (secondary, 'where present'): Hanley-McNeil 95 % CI half-width of a per-vessel AUC
    hm = []
    for auc in (0.80, 0.85):
        q1, q2 = auc / (2 - auc), 2 * auc ** 2 / (1 + auc)
        for nv in (60, 90, 120, 180, 240):
            npos = round(0.4 * nv)
            nneg = nv - npos
            se = np.sqrt((auc * (1 - auc) + (npos - 1) * (q1 - auc ** 2) + (nneg - 1) * (q2 - auc ** 2)) /
                         (npos * nneg))
            hm.append({'auc': auc, 'vessels': nv, 'positive_share': 0.4, 'ci_halfwidth': round(float(1.96 * se), 3)})
    out = {'assumptions': {'bin_weights': BIN_W.tolist(), 'scenarios': SCEN, 'unrecognised_scar_rate': 0.10,
                           'patient_logit_sd': 0.8, 'bootstrap': 400, 'cohorts_per_cell': 300,
                           'success_rule': 'lower95(kappa_w)>=0.60 & lower95(sens)>=0.70 & lower95(spec)>=0.90'},
           'rows': rows, 'ctp_ffr_auc_halfwidth': hm}
    OUT.write_text(json.dumps(out, indent=1) + '\n')
    guard_r2.scan_outputs([OUT])


if __name__ == '__main__':
    main()
