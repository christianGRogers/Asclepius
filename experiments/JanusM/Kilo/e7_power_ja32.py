"""E7 (Kilo v3): the paired seal's size at the JA32 bars, with the reader anchor measured on development.

Round 2 ruling, section 7 item 2: re-run the power study at the JA32 bars, under weak and strong clustering, and say how
many patients the >= 270 ischaemic scarred segments need at 50 % and 70 % enrichment. No image is read; no case id.

What is new against E6 (Kilo v2) and Golf E6:
  * all three JA32 endpoints are judged **jointly**, each on its 95 % patient-bootstrap lower bound, one look:
      sensitivity >= 0.75; specificity >= 0.93; transmurality agreement (exact Kim bin among segments scar on both
      CT and the LGE reference) >= A_dev - 0.10;
  * A_dev, the LGE inter-reader agreement on the same statistic, is **itself simulated on the 40 development
    patients** (JA28), from two independent readers, so its sampling error enters the bar. If A_dev < 0.60 the
    third endpoint is reported only and the decision rests on presence (JA32);
  * the seal's reference is the **adjudicated** double read (JA32: a third reader on any presence disagreement or a
    difference of >= 2 bins; the reference is then the median of the three, else the mean of the two);
  * only ischaemic-pattern scar enters (non-ischaemic patients are a separate stratum, JA27).

Model (stated assumptions):
  * truth: a share `enrich` of patients has an ischaemic scar in one coronary territory (AHA map, Cerqueira 2002, as
    E6); k ~ 1 + Binomial(n_territory - 1, p_k) contiguous-territory segments; true transmurality T ~ Beta(1.6, 1.6);
    17 segments per patient;
  * CT detection: logistic(a + b T + u_patient) for a scarred segment, logistic(c + u_patient) for a scar-free one,
    u ~ N(0, sd_u). sd_u = 0.8 is "weak" clustering (E6; ICC of CT-positive about 0.03); 1.6 is "strong";
    a, b, c as E6 (pooled sensitivity about 0.86, specificity about 0.98; Gatti 2025);
  * CT extent: T' = T + N(0, 0.05) per patient + N(0, sd_s) per segment; sd_s in {0.08, 0.13, 0.20} (E6's grid;
    E5's two-threshold rule measured 0.12);
  * LGE readers: each reads presence with sensitivity logistic(r_a + r_b T) (small scars missed; about 0.95 pooled)
    and a 0.01 false-call rate, and extent T + N(0, sd_r). sd_r in {0.07, 0.12} gives an inter-reader
    exact-bin agreement among scar-on-both segments of about 0.75 / 0.62 (an assumption: no paired-reader Kim-bin
    agreement is quoted in this round's sources; development measures it).

Outputs (`results_e7_power_ja32.json`): per (enrich, p_k, sd_u, sd_s, sd_r, N) the power of each endpoint and of the
joint rule, the mean number of ischaemic scarred segments, P(>= 270 scarred segments), and the distribution of A_dev.

Variant P (proposed in Kilo v3): the transmurality endpoint as a paired non-inferiority test on the seal itself:
  mean over readers k of agreement(CT, reader k) - agreement(reader 1, reader 2), patient-bootstrap lower bound
  >= -0.10. Both terms use single reads on the same seal patients, so like is compared with like and the anchor's
  development sampling error disappears.
Variant S (proposed in Kilo v3): JA32's statistic and margin, but the anchor is the inter-reader agreement over every
  double-read patient (development + seal), so it is estimated on about 4x as many segments.

Usage: python e7_power_ja32.py results_e7_power_ja32.json [--sims 300] [--boot 300] [--quick]
"""
import argparse, json, time

import numpy as np

TERR = {"LAD": [0, 1, 6, 7, 12, 13, 16], "RCA": [2, 3, 8, 9, 14], "LCX": [4, 5, 10, 11, 15]}
TERR_P = np.array([0.5, 0.3, 0.2])
TERR_L = list(TERR.values())
EDGES = np.array([0.25, 0.50, 0.75])
DET_A, DET_B, FP_C = -0.2, 5.0, -4.3          # E6 calibration (sens ~ 0.86, spec ~ 0.98 at sd_u 0.8)
R_A, R_B, R_FP = 1.0, 12.0, 0.01               # LGE reader: misses only the thinnest scars
BARS = {"sens": 0.75, "spec": 0.93, "tbin_margin": 0.10, "anchor_floor": 0.60}
SEG_TARGET = 270


def expit(x):
    return 1 / (1 + np.exp(-x))


def kbin(t, present):
    return np.where(present, np.digitize(np.clip(t, 1e-9, 1.0), EDGES) + 1, 0)


def truth(n, enrich, p_k, rng):
    T = np.zeros((n, 17))
    for i in np.flatnonzero(rng.random(n) < enrich):
        terr = TERR_L[rng.choice(3, p=TERR_P)]
        k = 1 + rng.binomial(len(terr) - 1, p_k)
        seg = rng.choice(terr, size=k, replace=False)
        T[i, seg] = rng.beta(1.6, 1.6, size=k).clip(0.02, 1.0)
    return T


def reader(T, sd_r, rng):
    pos = T > 0
    seen = np.where(pos, rng.random(T.shape) < expit(R_A + R_B * T), rng.random(T.shape) < R_FP)
    t = np.where(pos, T + rng.normal(0, sd_r, T.shape), rng.beta(1, 6, T.shape)).clip(0.01, 1.0)
    return kbin(t, seen), t, seen


def reference(T, sd_r, rng):
    """Two independent reads, a third on presence disagreement or >= 2 bins apart (JA32)."""
    b1, t1, s1 = reader(T, sd_r, rng)
    b2, t2, s2 = reader(T, sd_r, rng)
    b3, t3, s3 = reader(T, sd_r, rng)
    adjud = (s1 != s2) | (np.abs(b1 - b2) >= 2)
    pres = np.where(adjud, (s1.astype(int) + s2 + s3) >= 2, s1 & s2)
    tt = np.where(adjud, np.median(np.stack([t1, t2, t3]), 0), (t1 + t2) / 2)
    return kbin(tt, pres), b1, b2


def ct_read(T, sd_u, sd_s, rng):
    n = T.shape[0]
    pos = T > 0
    u = rng.normal(0, sd_u, (n, 1))
    det = rng.random(T.shape) < np.where(pos, expit(DET_A + DET_B * T + u), expit(FP_C + u))
    g = np.where(pos, T + rng.normal(0, 0.05, (n, 1)) + rng.normal(0, sd_s, T.shape), rng.beta(1, 6, T.shape))
    return kbin(g.clip(0.01, 1.0), det)


def _agree_counts(x, y):
    both = (x > 0) & (y > 0)
    return (both & (x == y)).sum(1), both.sum(1)


def per_patient(ref, ct, b1=None, b2=None):
    """Sufficient statistics per patient, so a bootstrap is a weighted sum. With the two first reads b1, b2, also the
    counts for the paired endpoint: CT vs each single reader, and reader 1 vs reader 2, on the same patients."""
    rp, cp = ref > 0, ct > 0
    both = rp & cp
    cols = [(rp & cp).sum(1), rp.sum(1), (~rp & ~cp).sum(1), (~rp).sum(1), (both & (ref == ct)).sum(1), both.sum(1)]
    if b1 is not None:
        for x, y in ((ct, b1), (ct, b2), (b1, b2)):
            cols += list(_agree_counts(x, y))
    return np.stack(cols, 1).astype(float)


def agreement(b1, b2):
    both = (b1 > 0) & (b2 > 0)
    return float((b1[both] == b2[both]).mean()) if both.any() else np.nan


def lower_bounds(S, boot, rng):
    n = S.shape[0]
    W = rng.multinomial(n, np.full(n, 1 / n), size=boot).astype(float)
    A = W @ S
    sens = A[:, 0] / np.maximum(A[:, 1], 1)
    spec = A[:, 2] / np.maximum(A[:, 3], 1)
    tb = A[:, 4] / np.maximum(A[:, 5], 1)
    cols = [sens, spec, tb]
    if S.shape[1] > 6:   # paired: mean of CT-vs-reader agreements minus reader-vs-reader agreement
        a1 = A[:, 6] / np.maximum(A[:, 7], 1)
        a2 = A[:, 8] / np.maximum(A[:, 9], 1)
        rr = A[:, 10] / np.maximum(A[:, 11], 1)
        cols.append((a1 + a2) / 2 - rr)
    lb = np.percentile(np.stack(cols, 1), 2.5, axis=0)
    t = S.sum(0)
    pt = (t[0] / max(t[1], 1), t[2] / max(t[3], 1), t[4] / max(t[5], 1))
    return lb, pt


def one_study(n, cfg, boot, rng):
    # development: 40 patients, >= 25 with MI (JA28): enrichment there is max(enrich, 25/40)
    Td = truth(40, max(cfg["enrich"], 25 / 40), cfg["p_k"], rng)
    _, b1, b2 = reference(Td, cfg["sd_r"], rng)
    a_dev = agreement(b1, b2)
    # seal
    T = truth(n, cfg["enrich"], cfg["p_k"], rng)
    ref, s1, s2 = reference(T, cfg["sd_r"], rng)
    ct = ct_read(T, cfg["sd_u"], cfg["sd_s"], rng)
    S = per_patient(ref, ct, s1, s2)
    lb, pt = lower_bounds(S, boot, rng)
    p_sens, p_spec = lb[0] >= BARS["sens"], lb[1] >= BARS["spec"]
    t_live = a_dev >= BARS["anchor_floor"]
    p_t = lb[2] >= a_dev - BARS["tbin_margin"]
    joint = p_sens and p_spec and (p_t if t_live else True)
    # variant P (Kilo v3): paired non-inferiority on the seal itself, no development anchor
    p_pair = lb[3] >= -BARS["tbin_margin"]
    joint_pair = p_sens and p_spec and p_pair
    # variant S (Kilo v3): the anchor is the inter-reader agreement over every double-read patient (development +
    # seal; JA32 puts two readers on every patient), not development alone
    a_all = agreement(np.vstack([b1, s1]), np.vstack([b2, s2]))
    s_live = a_all >= BARS["anchor_floor"]
    p_s = lb[2] >= a_all - BARS["tbin_margin"]
    joint_s = p_sens and p_spec and (p_s if s_live else True)
    return dict(p_sens=p_sens, p_spec=p_spec, p_t=p_t, t_live=t_live, joint=joint, a_dev=a_dev,
                p_pair=p_pair, joint_pair=joint_pair, lb_pair=lb[3], p_s=p_s, s_live=s_live, joint_s=joint_s,
                a_all=a_all,
                n_scar_seg=int((T > 0).sum()), n_ref_seg=int((ref > 0).sum()),
                pt_sens=pt[0], pt_spec=pt[1], pt_t=pt[2], lb_t=lb[2])


def calibrate(cfg, rng, n=20000):
    T = truth(n, cfg["enrich"], cfg["p_k"], rng)
    ref, b1, b2 = reference(T, cfg["sd_r"], rng)
    ct = ct_read(T, cfg["sd_u"], cfg["sd_s"], rng)
    S = per_patient(ref, ct, b1, b2).sum(0)
    pos = T > 0
    return {"ct_sens_vs_ref": round(S[0] / S[1], 3), "ct_spec_vs_ref": round(S[2] / S[3], 3),
            "ct_tbin_vs_ref": round(S[4] / S[5], 3), "reader_tbin_agreement": round(agreement(b1, b2), 3),
            "ct_tbin_vs_single_reader": round((S[6] / S[7] + S[8] / S[9]) / 2, 3),
            "reader_sens_vs_truth": round(float((b1[pos] > 0).mean()), 3),
            "scar_seg_per_scar_patient": round(float(pos.sum() / max((pos.any(1)).sum(), 1)), 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--sims", type=int, default=300); ap.add_argument("--boot", type=int, default=300)
    ap.add_argument("--seed", type=int, default=20261030); ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only-s", action="store_true")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    base = dict(enrich=0.5, p_k=0.45, sd_u=0.8, sd_s=0.13, sd_r=0.07)
    grid = []
    Ns = (80, 100, 120, 140, 160, 200, 240, 300)
    for enrich in (0.5, 0.7):                                  # ruling: 50 % and 70 %
        for sd_u in (0.8, 1.6):                                # weak / strong clustering
            for sd_s in (0.08, 0.10, 0.13, 0.20):
                grid.append(base | dict(enrich=enrich, sd_u=sd_u, sd_s=sd_s))
    for sd_r in (0.12,):                                       # noisier LGE readers
        for enrich in (0.5, 0.7):
            grid.append(base | dict(enrich=enrich, sd_r=sd_r))
    for p_k in (0.25,):                                        # smaller infarcts: fewer scarred segments each
        for enrich in (0.5, 0.7):
            grid.append(base | dict(enrich=enrich, p_k=p_k))
    if a.only_s:     # the rerun for variant S: the configurations where the transmurality endpoint is not hopeless
        grid = [base | dict(enrich=e, sd_s=s) for e in (0.5, 0.7) for s in (0.08, 0.10)] + \
               [base | dict(enrich=e, sd_s=0.13, sd_r=0.12) for e in (0.5, 0.7)]
    if a.quick:
        grid, Ns = grid[:2], (80, 120)
    res = {"settings": vars(a) | {"bars": BARS, "seg_target": SEG_TARGET, "det": [DET_A, DET_B, FP_C],
                                  "reader": [R_A, R_B, R_FP]}, "grid": []}
    t0 = time.time()
    for cfg in grid:
        cal = calibrate(cfg, rng)
        rows = []
        for n in Ns:
            out = [one_study(n, cfg, a.boot, rng) for _ in range(a.sims)]
            f = lambda k: round(float(np.mean([o[k] for o in out])), 3)  # noqa: E731
            ad = np.array([o["a_dev"] for o in out])
            rows.append({"N": n, "power_sens": f("p_sens"), "power_spec": f("p_spec"), "power_tbin": f("p_t"),
                         "share_tbin_live": f("t_live"), "power_joint": f("joint"),
                         "power_tbin_paired": f("p_pair"), "power_joint_paired": f("joint_pair"),
                         "power_tbin_pooled_anchor": f("p_s"), "power_joint_pooled_anchor": f("joint_s"),
                         "share_tbin_live_pooled": f("s_live"),
                         "a_all_p5_p50_p95": [round(float(x), 3) for x in np.nanpercentile([o["a_all"] for o in out], [5, 50, 95])],
                         "median_lb_paired_diff": round(float(np.median([o["lb_pair"] for o in out])), 3),
                         "mean_scar_segments": f("n_scar_seg"), "mean_ref_scar_segments": f("n_ref_seg"),
                         "p_ge_270_ref_segments": round(float(np.mean([o["n_ref_seg"] >= SEG_TARGET for o in out])), 3),
                         "a_dev_p5_p50_p95": [round(float(x), 3) for x in np.nanpercentile(ad, [5, 50, 95])],
                         "median_point": {k: round(float(np.median([o[k] for o in out])), 3) for k in ("pt_sens", "pt_spec", "pt_t")},
                         "median_lb_tbin": round(float(np.median([o["lb_t"] for o in out])), 3)})
            print(cfg, rows[-1], f"{time.time() - t0:.0f}s", flush=True)
        res["grid"].append({"cfg": cfg, "calibration": cal, "rows": rows})
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
