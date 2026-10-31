"""Juliet R4 E12 scorer: results_v3_juliet.jsonl.gz -> scores_v3_juliet.json (Janus-M Round 4, #251 items 1-2).

Decision rules pre-registered on #251 before any v3 result:

1. The chain as shipped (arm `shipped`). `register_lie`'s control flow is replayed on the logged stages, with the
   module's own `QC.passes`, `qc_rule_accepts` and `normalised_max` (and the logged `affine_sanity`):
     R0 if it passes QC; else rigid (4 mm); if rigid fails QC, affine is computed and kept iff the acceptance rule
     holds; if the result still fails QC, rigid10 replaces it iff rigid10 passes QC or lowers the normalised max.
   QC cuts (JA53 provisional, the Round 3 way): each value's cut is the p95 of the module's R0 values on motion
   'none' cases of the *other* half of hearts (score.half), per blood level; rim_dark's phase cut = its gate cut;
   edge-offset cut 0.6 mm. The phase step (JA52) runs on the final stage: evaluable iff contrast >= 2 SD; flags
   rim_dark > cut, |edge offset| > 0.6 mm.
2. Strike (unchanged from #179) on arm `shipped`: score.strike_on (CNR 5, motion none or rigid, every blood level;
   sens < 0.75, spec < 0.93, scar-free spec < 0.93, spill > 0.25; rule 1c). Phase-flagged cases stay in.
   P-J's tau per arm by score.fit_taus (p99 of E-D over scar-free segments, other half, none + rigid). Every other
   arm is reported and never strikes.
3. Item 2, affine acceptance (all but S and N also need the 4(a) sanity bound):
     L  literal 4(b) (as shipped);  a  no rise over the three wall shares, normalised max (all four) falls;
     b  normalised max falls and no value newly crosses its cut;  c  sanity alone if |log det A| >= 0.02, else L;
     d  affine passes QC or lowers the normalised max (the step-5 test);  S  sanity bound only;  N  never.
   Reported per motion on every case (the rigid-vs-affine decision alone) and as full chains (`chain_<rule>`).
   Choice: lowest pooled p90 TRE of the decision over motions rigid, scale, aniso3, aniso6; ties -> fewer keeps.
"""
from __future__ import annotations

import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BENCH = ROOT / "experiments/JanusM/bench_lie"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(HERE))
import score as S3  # noqa: E402  (Round 3's scorer: half, kim, arr, calls, auc, fit_taus, strike_on)
from janusm.scar import registration as REG  # noqa: E402

QCN = REG.QC_NAMES
MOTIONS = ("none", "rigid", "scale", "aniso3", "aniso6", "phase", "phase_neg", "nonrigid")
CHOICE_MOTIONS = ("rigid", "scale", "aniso3", "aniso6")
RULES = ("L", "a", "b", "c", "d", "S", "N")
LOGDET_C = 0.02
STAGES = ("R0", "rigid", "affine", "rigid10")


def load(path):
    path = Path(path)
    op = gzip.open if path.suffix == ".gz" else open
    with op(path, "rt") as fh:
        rows = [json.loads(line) for line in fh]
    return [r for r in rows if "skip" not in r], [r for r in rows if "skip" in r]


def qobj(rec):
    v = [np.nan if rec["qc"][n] is None else rec["qc"][n] for n in QCN]
    return REG.QC(*v, blood_median=np.nan, remote_median=np.nan, n_wall=0)


def fit_cuts(rows):
    acc = defaultdict(list)
    for r in rows:
        if r["motion"] == "none":
            acc[(S3.half(r["heart"]), r["blood"])].append(qobj(r["arms"]["R0"]).values())
    cuts = {}
    for (h, b), v in acc.items():
        v = np.array(v)
        p = [float(np.nanpercentile(v[:, k], 95)) for k in range(4)]
        cuts[(1 - h, b)] = REG.QCCuts(max_fatlike=p[0], max_bloodlike=p[1], max_brighter_than_blood=p[2],
                                      max_rim_dark=p[3])
    return cuts


def accept(rule, aff_rec, q_aff, q_rig, cuts):
    san = aff_rec["sanity"]
    if rule == "N":
        return False
    if rule == "S":
        return bool(san["ok"])
    if not san["ok"]:
        return False
    if rule == "L":
        return REG.qc_rule_accepts(q_aff, q_rig, cuts)
    na, nr = REG.normalised(q_aff, cuts), REG.normalised(q_rig, cuts)
    if not (np.isfinite(na).all() and np.isfinite(nr).all()):
        return False
    falls = na.max() < nr.max()
    if rule == "a":
        g = np.array(cuts.gate)
        three = np.array([True, True, True, False])[g]
        return bool((na[three] <= nr[three]).all() and falls)
    if rule == "b":
        newly = (nr <= 1.0) & (na > 1.0)
        return bool(falls and not newly.any())
    if rule == "c":
        ld = san["log_det"]
        if ld is not None and np.isfinite(ld) and abs(ld) >= LOGDET_C:
            return True
        return REG.qc_rule_accepts(q_aff, q_rig, cuts)
    if rule == "d":
        return bool(q_aff.passes(cuts) or falls)
    raise ValueError(rule)


def replay(r, cuts, rule):
    """register_lie's control flow on the logged stages. Returns (final stage, stages run, phase dict)."""
    A = r["arms"]
    q = {s: qobj(A[s]) for s in STAGES}
    run = ["R0"]
    final = "R0"
    if not q["R0"].passes(cuts):
        run.append("rigid")
        final = "rigid"
        if not q["rigid"].passes(cuts):
            run.append("affine")
            if accept(rule, A["affine"], q["affine"], q["rigid"], cuts):
                final = "affine"
        if not q[final].passes(cuts):
            run.append("rigid10")
            m_new, m_old = REG.normalised_max(q["rigid10"], cuts), REG.normalised_max(q[final], cuts)
            if q["rigid10"].passes(cuts) or (np.isfinite(m_new) and np.isfinite(m_old) and m_new < m_old):
                final = "rigid10"
    rec = A[final]
    con = rec["contrast"]
    ev = con is not None and np.isfinite(con) and con >= REG.MIN_PHASE_CONTRAST_SD
    rd = rec["qc"]["rim_dark"]
    off = rec["edge_offset_mm"]
    flags = []
    if ev:
        if rd is not None and rd > cuts.rim_dark_phase:
            flags.append("rim_dark")
        if off is not None and abs(off) > cuts.max_edge_offset_mm:
            flags.append("edge_offset")
    return final, run, {"evaluable": bool(ev), "flags": flags}


def pct(v, p):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return round(float(np.percentile(v, p)), 3) if v else None


def score_groups(rows, arms, taus, out):
    """Round 3's presence / extent scoring (score.main, sections 2-3), per arm x blood x cnr x motion."""
    PRES, EXT = S3.PRES, S3.EXT
    groups = defaultdict(list)
    for r in rows:
        for arm in arms:
            if arm in r["arms"]:
                groups[(arm, r["blood"], r["cnr"], r["motion"])].append(r)
    for (arm, b, c, m), rr in sorted(groups.items()):
        P = {p: {"tp": 0, "fn": 0, "tn": 0, "fp": 0, "spill_twin": 0, "tp_nb": 0, "free_tn": 0, "free_n": 0,
                 "bybin": np.zeros((5, 2), int)} for p in PRES}
        E = {(p, e, t): [0, 0] for p in PRES for e in EXT for t in ("vol", "depth")}
        for r in rr:
            rec = r["arms"][arm]
            tarm = "shipped" if arm == "bspline" else arm
            tau = taus.get((S3.half(r["heart"]), tarm, b, c), 0.1)
            tv, td = np.nan_to_num(S3.arr(r["truth_vol"])), np.nan_to_num(S3.arr(r["truth_depth"]))
            valid = np.isfinite(S3.arr(rec["scar"]["pk_share"]))
            truth = ((tv >= 0.01) | (td >= 0.01))[valid]
            cs, cf, cn = S3.calls(rec["scar"], tau), S3.calls(rec["free_fixed"], tau), S3.calls(rec["noblood"], tau)
            co = S3.calls(rec["free_own"], tau)
            vo = np.isfinite(S3.arr(rec["free_own"]["pk_share"]))
            tbin = S3.kim(td[valid])
            for p in PRES:
                s, f, nb = cs[p][valid], cf[p][valid], cn[p][valid]
                P[p]["tp"] += int((s & truth).sum())
                P[p]["fn"] += int((~s & truth).sum())
                P[p]["tn"] += int((~s & ~truth).sum())
                P[p]["fp"] += int((s & ~truth).sum())
                P[p]["spill_twin"] += int((s & truth & f).sum())
                P[p]["tp_nb"] += int((nb & truth).sum())
                P[p]["free_tn"] += int((~co[p][vo]).sum())
                P[p]["free_n"] += int(vo.sum())
                for kb in range(1, 5):
                    mb = truth & (tbin == kb)
                    P[p]["bybin"][kb] += [int((s & mb).sum()), int(mb.sum())]
                both = s & truth
                for e, key in (("E-V", "ev"), ("E-D", "ed")):
                    est = np.maximum(S3.kim(S3.arr(rec["scar"][key])[valid]), 1)
                    for t, tr in (("vol", tv), ("depth", td)):
                        tb = np.maximum(S3.kim(tr[valid]), 1)
                        E[(p, e, t)][0] += int((est[both] == tb[both]).sum())
                        E[(p, e, t)][1] += int(both.sum())
        for p, d in P.items():
            sens = d["tp"] / max(d["tp"] + d["fn"], 1)
            sens_nb = d["tp_nb"] / max(d["tp"] + d["fn"], 1)
            out["presence"].append({"arm": arm, "blood": b, "cnr": c, "motion": m, "rule": p, "n_cases": len(rr),
                                    "sens": round(sens, 3),
                                    "spec": round(d["tn"] / max(d["tn"] + d["fp"], 1), 3),
                                    "spec_scarfree_hearts": round(d["free_tn"] / max(d["free_n"], 1), 3),
                                    "spill_share": round((sens - sens_nb) / sens, 3) if sens > 0 else None,
                                    "spill_twin": round(d["spill_twin"] / max(d["tp"], 1), 3),
                                    "sens_by_bin": {str(k): (round(d["bybin"][k][0] / d["bybin"][k][1], 3)
                                                             if d["bybin"][k][1] else None) for k in range(1, 5)},
                                    "n_scarred": d["tp"] + d["fn"], "n_free": d["tn"] + d["fp"]})
        for (p, e, t), (k, n) in E.items():
            out["extent"].append({"arm": arm, "blood": b, "cnr": c, "motion": m, "presence": p, "extent": e,
                                  "truth": t, "exact_agreement": round(k / n, 3) if n else None, "n_both": n})


def main(path=HERE / "results_v3_juliet.jsonl.gz", out_path=HERE / "scores_v3_juliet.json"):
    rows, skips = load(path)
    cuts = fit_cuts(rows)
    for r in rows:
        cut = cuts[(S3.half(r["heart"]), r["blood"])]
        r["chain"] = {}
        for rule in RULES:
            final, run, ph = replay(r, cut, rule)
            r["chain"][rule] = {"final": final, "run": run, "phase": ph}
            r["arms"]["shipped" if rule == "L" else f"chain_{rule}"] = r["arms"][final]
    chain_arms = ["shipped"] + [f"chain_{x}" for x in RULES if x != "L"]
    taus = S3.fit_taus(rows)
    out = {"n_cases": len(rows), "hearts": sorted({r["heart"] for r in rows}), "skipped": skips,
           "scar_version": REG.SCAR_VERSION, "registration": [], "affine_rules": [], "phase": [],
           "presence": [], "extent": [], "strike": {}, "strike_reported": {}}
    # 1. registration: TRE per stage and chain, chain paths, QC behaviour when affine helps
    for m in MOTIONS:
        rr = [r for r in rows if r["motion"] == m]
        if not rr:
            continue
        row = {"motion": m, "n": len(rr)}
        for arm in list(STAGES) + ["bspline"] + chain_arms:
            t = [r["arms"][arm]["tre_mm"] for r in rr if arm in r["arms"]]
            if t:
                row[f"{arm}_tre_median"], row[f"{arm}_tre_p90"] = pct(t, 50), pct(t, 90)
        sh = [r["chain"]["L"] for r in rr]
        row["shipped_final"] = {s: sum(x["final"] == s for x in sh) for s in STAGES}
        row["shipped_reached_affine"] = sum("affine" in x["run"] for x in sh)
        row["shipped_ran_fallback"] = sum("rigid10" in x["run"] for x in sh)
        helps = [r for r in rr if r["arms"]["affine"]["tre_mm"] < r["arms"]["rigid"]["tre_mm"] - 0.1]
        rises = 0
        for r in helps:
            cut = cuts[(S3.half(r["heart"]), r["blood"])]
            na, nr = REG.normalised(qobj(r["arms"]["affine"]), cut), REG.normalised(qobj(r["arms"]["rigid"]), cut)
            rises += bool((na > nr).any())
        row["affine_helps_by_0.1mm"] = len(helps)
        row["affine_helps_but_a_qc_value_rises"] = rises
        row["affine_sanity_ok"] = sum(bool(r["arms"]["affine"]["sanity"]["ok"]) for r in rr)
        row["affine_log_det_median"] = pct([r["arms"]["affine"]["sanity"]["log_det"] for r in rr], 50)
        out["registration"].append(row)
    # 2. item 2: the rigid-vs-affine decision under each rule, on every case
    for rule in RULES:
        for m in MOTIONS:
            rr = [r for r in rows if r["motion"] == m]
            keep, tre, reg, sub = [], [], [], []
            for r in rr:
                cut = cuts[(S3.half(r["heart"]), r["blood"])]
                A = r["arms"]
                k = accept(rule, A["affine"], qobj(A["affine"]), qobj(A["rigid"]), cut)
                ta, tr = A["affine"]["tre_mm"], A["rigid"]["tre_mm"]
                keep.append(k)
                tre.append(ta if k else tr)
                reg.append((ta if k else tr) - min(ta, tr))
                if "affine" in r["chain"]["L"]["run"]:
                    sub.append(ta if k else tr)
            fin = [r["arms"][r["chain"][rule]["final"]]["tre_mm"] for r in rr]
            out["affine_rules"].append({"rule": rule, "motion": m, "n": len(rr), "keep_rate": round(np.mean(keep), 3),
                                        "decision_tre_median": pct(tre, 50), "decision_tre_p90": pct(tre, 90),
                                        "regret_mean": round(float(np.mean(reg)), 3), "regret_p90": pct(reg, 90),
                                        "n_shipped_reaches_affine": len(sub),
                                        "decision_tre_p90_where_shipped_reaches_affine": pct(sub, 90),
                                        "chain_final_tre_median": pct(fin, 50), "chain_final_tre_p90": pct(fin, 90)})
    pooled = {}
    for rule in RULES:
        t, k = [], []
        for r in rows:
            if r["motion"] in CHOICE_MOTIONS:
                cut = cuts[(S3.half(r["heart"]), r["blood"])]
                A = r["arms"]
                kk = accept(rule, A["affine"], qobj(A["affine"]), qobj(A["rigid"]), cut)
                t.append(A["affine"]["tre_mm"] if kk else A["rigid"]["tre_mm"])
                k.append(kk)
        pooled[rule] = {"pooled_p90": pct(t, 90), "keeps": int(sum(k)), "n": len(t)}
    best = min(RULES, key=lambda x: (pooled[x]["pooled_p90"], pooled[x]["keeps"]))
    out["affine_rule_choice"] = {"criterion": "lowest pooled p90 decision TRE over " + ", ".join(CHOICE_MOTIONS)
                                 + "; ties -> fewer keeps (pre-registered on #251)", "pooled": pooled, "chosen": best}
    # 3. phase step on the shipped final stage
    for m in MOTIONS:
        for b in ("below", "equal", "above", "all"):
            rr = [r for r in rows if r["motion"] == m and (b == "all" or r["blood"] == b)]
            ph = [r["chain"]["L"]["phase"] for r in rr]
            out["phase"].append({"motion": m, "blood": b, "n": len(rr),
                                 "not_evaluable": sum(not p["evaluable"] for p in ph),
                                 "flag_rim_dark": sum("rim_dark" in p["flags"] for p in ph),
                                 "flag_edge_offset": sum("edge_offset" in p["flags"] for p in ph),
                                 "flag_any": sum(bool(p["flags"]) for p in ph),
                                 "edge_offset_median": pct([r["arms"][r["chain"]["L"]["final"]]["edge_offset_mm"]
                                                            for r in rr], 50)})
    fin = lambda r, k: r["arms"][r["chain"]["L"]["final"]][k]  # noqa: E731
    out["phase_auc"] = {
        "edge_offset_neg_phase_neg_vs_rigid": S3.auc([-fin(r, "edge_offset_mm") for r in rows if r["motion"] == "phase_neg"],
                                                     [-fin(r, "edge_offset_mm") for r in rows if r["motion"] == "rigid"]),
        "abs_edge_offset_phase_neg_vs_rigid": S3.auc([abs(fin(r, "edge_offset_mm")) for r in rows if r["motion"] == "phase_neg"],
                                                     [abs(fin(r, "edge_offset_mm")) for r in rows if r["motion"] == "rigid"]),
        "rim_dark_phase_vs_rigid": S3.auc([fin(r, "qc")["rim_dark"] for r in rows if r["motion"] == "phase"],
                                          [fin(r, "qc")["rim_dark"] for r in rows if r["motion"] == "rigid"]),
        "rim_dark_phase_neg_vs_rigid": S3.auc([fin(r, "qc")["rim_dark"] for r in rows if r["motion"] == "phase_neg"],
                                              [fin(r, "qc")["rim_dark"] for r in rows if r["motion"] == "rigid"])}
    # 4. presence and extent; strike
    arms = ["oracle", "R0", "rigid", "affine", "rigid10", "bspline"] + chain_arms
    score_groups(rows, arms, taus, out)
    out["strike"] = S3.strike_on(out, "shipped")
    out["strike_reported"] = {a: S3.strike_on(out, a) for a in ["oracle", "rigid", "rigid10"] + chain_arms[1:]}
    out["phase_flagged_in_strike_conditions"] = sum(bool(r["chain"]["L"]["phase"]["flags"]) for r in rows
                                                    if r["motion"] in S3.STRIKE_MOTIONS)
    out["taus"] = {f"{k[0]}|{k[1]}|{k[2]}|{k[3]}": round(v, 3) for k, v in sorted(taus.items())
                   if k[1] in ("shipped", "oracle", "rigid")}
    out["qc_cuts"] = {f"{h}|{b}": dict(zip(QCN, np.round(c.values(), 5).tolist())) for (h, b), c in sorted(cuts.items())}
    Path(out_path).write_text(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    o = main(*(sys.argv[1:3] or []))
    print("cases", o["n_cases"], "hearts", len(o["hearts"]))
    for r in o["registration"]:
        print(r["motion"], {a: (r.get(f"{a}_tre_median"), r.get(f"{a}_tre_p90")) for a in
                            ("R0", "rigid", "affine", "rigid10", "bspline", "shipped")}, r["shipped_final"])
    print(json.dumps(o["affine_rule_choice"], indent=1))
    print(json.dumps(o["strike"], indent=1))
