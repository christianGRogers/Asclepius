"""Kilo R4: score benchmark-v3 rows under Kilo's pre-registered rules (Janus-M Round 4, #251 items 1, 2).

Input: Kilo's replication rows (results_kilo_r4.jsonl[.gz], default) -> scores_kilo_r4.json. The canonical v3 rows are
Golf's (bench_lie/results_v3.jsonl.gz); golf_rows.py maps them to this format and scores them with the same code.

Pre-registered on #251 (Kilo, 18:56 and 19:25 UTC 2026-10-30) before any v3 result existed. Definitions follow
score.py (truth presence, sensitivity, specificity, scar-free specificity, spill, Kim-bin extent agreement, P-J's
tau = p99 of E-D on scar-free segments of the other half of the hearts), so v2 and v3 numbers are comparable.

Chains replayed from the forced stages (run_shipped.py), at two cut sets:
  prov  JA53's provisional cuts: ``registration.load_provisional_qc_cuts`` (bench_lie/scores.json), matching blood, CNR 5;
  fit   the same chain at cuts re-fitted on the SHIPPED QC values as development will: p95 of R0 on motion 'none'
        cases, the other half of the hearts, per blood (rim_dark's phase cut = the same p95; edge offset 0.6 mm).
Affine acceptance rules (JA51 step 4; #243; #251 item 2): 'ja51' (as shipped), 'a', 'b', 'c', 'k' (see RULES).
Arms: chain_<rule>_<cuts>; the deciding arm is chain_ja51_prov (= ``chain_shipped``); stages R0, rigid, affine,
rigid10; oracle; bspline (nonrigid and rigid only).

Strike (#179's rules, unchanged): CNR 5, motion none or rigid, any blood; struck if sens < 0.75, spec < 0.93,
scar-free spec < 0.93 or spill > 0.25, on chain_ja51_prov. The same rules on other arms are reported, never striking.
Phase-suspect patients stay in the striking scoring (no phase change there; their rate is reported).

Item 2 measure: per rule and cut set, final-stage TRE (median / p90) per motion and wrong decisions (affine kept when
its TRE exceeds rigid's by > 0.25 mm, or rejected when it beats rigid's by > 0.25 mm). Choice (on 'fit'): the lowest
pooled p90 final TRE over rigid, scale, aniso3, aniso6, among rules keeping affine on <= 10 % of the rigid cases where
affine is worse by > 0.25 mm.

Usage: PYTHONPATH=src python experiments/JanusM/Kilo/r4/score_shipped.py [rows.jsonl[.gz] [out.json]]
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "experiments/JanusM/bench_lie"))
sys.path.insert(0, str(ROOT / "src"))
from score import EXT, PRES, arr, auc, calls, half, kim, load, strike_on  # noqa: E402

QN = ("fatlike", "bloodlike", "brighter_than_blood", "rim_dark")
MOTIONS = ("none", "rigid", "scale", "aniso3", "aniso6", "aniso", "phase", "phase_m5", "phase_neg", "nonrigid")
STAGES = ("R0", "rigid", "affine", "rigid10")
RULES = ("ja51", "a", "b", "c", "k")
CUTSETS = ("prov", "fit")
WRONG_MM = 0.25
SCALE_LOGDET = 0.03
EDGE_MM = 0.6
CHOICE_MOTIONS = ("rigid", "scale", "aniso3", "aniso6")
#: on Golf's canonical rows his `aniso` (3 / 3 / 6 %) stands in for aniso3 / aniso6 (pre-registered on #251)
CHOICE_MOTIONS_GOLF = ("rigid", "scale", "aniso")


def prov_cuts():
    from janusm.scar.registration import load_provisional_qc_cuts
    out = {}
    for b in ("below", "equal", "above"):
        c = load_provisional_qc_cuts(blood=b, cnr=5)
        out[b] = np.array(c.values(), float)
    return out


def fit_cuts(rows):
    acc = defaultdict(list)
    for r in rows:
        if r["motion"] == "none":
            acc[(half(r["heart"]), r["blood"])].append(qv(r["stages"]["R0"]["qc"]))
    out = {}
    for (hh, b), v in acc.items():
        out[(1 - hh, b)] = np.nanpercentile(np.array(v), 95, axis=0)
    return out


def qv(q):
    return np.array([np.nan if q[k] is None else q[k] for k in QN], float)


def norm(q, cut):
    return q / np.maximum(cut, 1e-6)


def passes(q, cut):
    return bool(np.isfinite(q).all() and (q <= cut).all())


def accept(rule, a, r, cut, sanity, log_det):
    """Affine acceptance (step 4) under one rule. a, r: affine and rigid QC vectors."""
    if not sanity:
        return False
    na, nr = norm(a, cut), norm(r, cut)
    if not (np.isfinite(na).all() and np.isfinite(nr).all()):
        return False
    falls = na.max() < nr.max()
    if rule == "ja51":
        return bool((na <= nr).all() and falls)
    if rule == "a":
        return bool((na[:3] <= nr[:3]).all() and falls)
    if rule == "b":
        return bool(falls and not ((nr <= 1) & (na > 1)).any())
    if rule == "c":
        if np.isfinite(log_det) and abs(log_det) >= SCALE_LOGDET:
            return True
        return bool((na <= nr).all() and falls)
    if rule == "k":
        return bool(falls and ((na <= nr) | (na <= 1)).all())
    raise ValueError(rule)


def replay(r, cut, rule):
    """JA51 as shipped (stop at the first stage passing QC; affine only after a failed rigid; one 10 mm fallback
    replacing the result if it passes or lowers the normalised maximum), with step 4 under ``rule``."""
    st = r["stages"]
    q = {s: qv(st[s]["qc"]) for s in STAGES}
    p = {s: passes(q[s], cut) for s in STAGES}
    if p["R0"]:
        return "R0"
    final = "rigid"
    if not p["rigid"]:
        a = st["affine"]
        if accept(rule, q["affine"], q["rigid"], cut, a["sanity"]["ok"], a["sanity"]["log_det"] or np.nan):
            final = "affine"
    if not p[final]:
        mn, mo = norm(q["rigid10"], cut).max(), norm(q[final], cut).max()
        if p["rigid10"] or (np.isfinite(mn) and np.isfinite(mo) and mn < mo):
            final = "rigid10"
    return final


def phase_flags(r, stage, cut):
    """JA52 on the final stage: evaluable if contrast >= 2 SD; rim_dark above its (phase) cut; |edge| > 0.6 mm."""
    s = r["stages"][stage]
    q = s["qc"]
    con = q.get("contrast")
    if con is None or not np.isfinite(con) or con < 2.0:
        return {"evaluable": False, "flags": []}
    f = []
    if q["rim_dark"] is not None and q["rim_dark"] > cut[3]:
        f.append("rim_dark")
    eo = s.get("edge_offset_mm")
    if eo is not None and np.isfinite(eo) and abs(eo) > EDGE_MM:
        f.append("edge_offset")
    return {"evaluable": True, "flags": f}


def q_med(v):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return (round(float(np.median(v)), 3), round(float(np.percentile(v, 90)), 3), len(v)) if v else (None, None, 0)


def score_groups(rows, arms, taus):
    out = {"presence": [], "extent": []}
    groups = defaultdict(list)
    for r in rows:
        for arm in arms:
            if arm in r["arms"]:
                groups[(arm, r["blood"], r["cnr"], r["motion"])].append(r)
    for (arm, b, c, m), rr in sorted(groups.items()):
        P = {p: {"tp": 0, "fn": 0, "tn": 0, "fp": 0, "tp_nb": 0, "free_tn": 0, "free_n": 0,
                 "bybin": np.zeros((5, 2), int)} for p in PRES}
        E = {(p, e, t): [0, 0] for p in PRES for e in EXT for t in ("vol", "depth")}
        for r in rr:
            rec = r["arms"][arm]
            tau = taus.get((half(r["heart"]), arm, b), 0.1)
            tv, td = np.nan_to_num(arr(r["truth_vol"])), np.nan_to_num(arr(r["truth_depth"]))
            valid = np.isfinite(arr(rec["scar"]["pk_share"]))
            truth = ((tv >= 0.01) | (td >= 0.01))[valid]
            cs, cn, co = calls(rec["scar"], tau), calls(rec["noblood"], tau), calls(rec["free_own"], tau)
            vo = np.isfinite(arr(rec["free_own"]["pk_share"]))
            tbin = kim(td[valid])
            for p in PRES:
                s, nb = cs[p][valid], cn[p][valid]
                P[p]["tp"] += int((s & truth).sum())
                P[p]["fn"] += int((~s & truth).sum())
                P[p]["tn"] += int((~s & ~truth).sum())
                P[p]["fp"] += int((s & ~truth).sum())
                P[p]["tp_nb"] += int((nb & truth).sum())
                P[p]["free_tn"] += int((~co[p][vo]).sum())
                P[p]["free_n"] += int(vo.sum())
                for kb in range(1, 5):
                    mb = truth & (tbin == kb)
                    P[p]["bybin"][kb] += [int((s & mb).sum()), int(mb.sum())]
                both = s & truth
                for e, key in (("E-V", "ev"), ("E-D", "ed")):
                    est = np.maximum(kim(arr(rec["scar"][key])[valid]), 1)
                    for t, tr in (("vol", tv), ("depth", td)):
                        tb = np.maximum(kim(tr[valid]), 1)
                        E[(p, e, t)][0] += int((est[both] == tb[both]).sum())
                        E[(p, e, t)][1] += int(both.sum())
        for p, d in P.items():
            sens = d["tp"] / max(d["tp"] + d["fn"], 1)
            sens_nb = d["tp_nb"] / max(d["tp"] + d["fn"], 1)
            out["presence"].append({"arm": arm, "blood": b, "cnr": c, "motion": m, "rule": p, "n_cases": len(rr),
                                    "sens": round(sens, 3), "spec": round(d["tn"] / max(d["tn"] + d["fp"], 1), 3),
                                    "spec_scarfree_hearts": round(d["free_tn"] / max(d["free_n"], 1), 3),
                                    "spill_share": round((sens - sens_nb) / sens, 3) if sens > 0 else None,
                                    "sens_by_bin": {str(k): (round(d["bybin"][k][0] / d["bybin"][k][1], 3)
                                                             if d["bybin"][k][1] else None) for k in range(1, 5)},
                                    "n_scarred": d["tp"] + d["fn"], "n_free": d["tn"] + d["fp"]})
        for (p, e, t), (k, n) in E.items():
            out["extent"].append({"arm": arm, "blood": b, "cnr": c, "motion": m, "presence": p, "extent": e,
                                  "truth": t, "exact_agreement": round(k / n, 3) if n else None, "n_both": n})
    return out


def fit_taus(rows, arms):
    """score.py's tau: p99 of E-D over scar-free segments (scarred hearts' and twins'), motions none and rigid,
    per arm and blood, fitted on the other half of the hearts."""
    acc = defaultdict(list)
    for r in rows:
        if r["motion"] not in ("none", "rigid"):
            continue
        free = (np.nan_to_num(arr(r["truth_depth"])) < 0.01) & (np.nan_to_num(arr(r["truth_vol"])) < 0.01)
        for arm in arms:
            if arm not in r["arms"]:
                continue
            ed, tw = arr(r["arms"][arm]["scar"]["ed"]), arr(r["arms"][arm]["free_own"]["ed"])
            acc[(half(r["heart"]), arm, r["blood"])] += list(ed[free & np.isfinite(ed)]) + list(tw[np.isfinite(tw)])
    return {(1 - hh, arm, b): (float(np.percentile(v, 99)) if v else 0.1) for (hh, arm, b), v in acc.items()}


def main(path=HERE / "results_kilo_r4.jsonl", out_path=HERE / "scores_kilo_r4.json", rows=None,
         choice_motions=CHOICE_MOTIONS, source="Kilo's replication rows (run_shipped.py)"):
    if rows is None:
        rows, skips = load(path)
    else:
        skips = [r for r in rows if "skip" in r]
        rows = [r for r in rows if "skip" not in r]
    rows = [r for r in rows if r.get("cnr") == 5 and "stages" in r and all(s in r["stages"] for s in STAGES)]
    pc, fc = prov_cuts(), fit_cuts(rows)
    cutfor = {"prov": lambda r: pc[r["blood"]], "fit": lambda r: fc[(half(r["heart"]), r["blood"])]}
    out = {"source": source, "choice_motions": list(choice_motions), "n_cases": len(rows), "hearts": sorted({r["heart"] for r in rows}), "skipped": skips,
           "cuts": {"prov": {b: dict(zip(QN, np.round(v, 4).tolist())) for b, v in pc.items()},
                    "fit": {f"{k[0]}|{k[1]}": dict(zip(QN, np.round(v, 4).tolist())) for k, v in sorted(fc.items())}}}
    # replay every chain
    for r in rows:
        r["final"], r["phase"] = {}, {}
        for cs in CUTSETS:
            cut = cutfor[cs](r)
            for rule in RULES:
                f = replay(r, cut, rule)
                r["final"][(rule, cs)] = f
                r["arms"][f"chain_{rule}_{cs}"] = r["arms"][f]
                r["phase"][(rule, cs)] = phase_flags(r, f, cut)
    # replay check against the live (un-forced) call
    live = [r for r in rows if "live_check" in r]
    out["replay_check"] = {"n": len(live),
                           "agree": sum(r["live_check"]["final"] == r["final"][("ja51", "prov")] for r in live),
                           "disagree": [(r["heart"], r["live_check"]["final"], r["final"][("ja51", "prov")])
                                        for r in live if r["live_check"]["final"] != r["final"][("ja51", "prov")]]}
    # 1. registration: per motion, TRE per stage and per chain, stage counts, phase-flag rates
    reg = []
    for m in MOTIONS:
        rr = [r for r in rows if r["motion"] == m]
        if not rr:
            continue
        row = {"motion": m, "n": len(rr)}
        for s in STAGES:
            row[f"{s}_tre"] = q_med([r["stages"][s]["tre_mm"] for r in rr])
        bs = [r["bspline"]["tre_mm"] for r in rr if "bspline" in r and "tre_mm" in r.get("bspline", {})]
        if bs:
            row["bspline_tre"] = q_med(bs)
        if all("oracle_qc" in r for r in rr):
            row["oracle_qc_median"] = {k: q_med([r["oracle_qc"][k] for r in rr])[0] for k in QN + ("edge_offset_mm",)}
        row["edge_offset_by_stage_median"] = {s: q_med([r["stages"][s]["edge_offset_mm"] for r in rr])[0]
                                              for s in STAGES}
        row["affine_sanity_ok"] = round(float(np.mean([r["stages"]["affine"]["sanity"]["ok"] for r in rr])), 3)
        row["affine_log_det_median"] = q_med([r["stages"]["affine"]["sanity"]["log_det"] for r in rr])[0]
        for cs in CUTSETS:
            for rule in RULES:
                fin = [r["final"][(rule, cs)] for r in rr]
                t = [r["stages"][f]["tre_mm"] for r, f in zip(rr, fin)]
                ph = [r["phase"][(rule, cs)] for r in rr]
                row[f"chain_{rule}_{cs}"] = {
                    "tre": q_med(t), "stages": {s: fin.count(s) for s in STAGES},
                    "phase_suspect": round(float(np.mean([bool(p["flags"]) for p in ph])), 3),
                    "phase_by_flag": {k: round(float(np.mean([k in p["flags"] for p in ph])), 3)
                                      for k in ("rim_dark", "edge_offset")},
                    "not_evaluable": round(float(np.mean([not p["evaluable"] for p in ph])), 3)}
        reg.append(row)
    out["registration"] = reg
    # 2. item 2: affine acceptance rules
    item2 = {}
    for cs in CUTSETS:
        for rule in RULES:
            d = {"per_motion": {}}
            pooled = []
            for m in MOTIONS:
                rr = [r for r in rows if r["motion"] == m]
                if not rr:
                    continue
                kept_bad = kept = rej_good = cmp = worse_n = better_n = 0
                for r in rr:
                    cut = cutfor[cs](r)
                    q = {s: qv(r["stages"][s]["qc"]) for s in STAGES}
                    if passes(q["R0"], cut) or passes(q["rigid"], cut):
                        continue                                # affine never compared on this case
                    cmp += 1
                    a = r["stages"]["affine"]
                    k = accept(rule, q["affine"], q["rigid"], cut, a["sanity"]["ok"],
                               a["sanity"]["log_det"] if a["sanity"]["log_det"] is not None else np.nan)
                    dt = a["tre_mm"] - r["stages"]["rigid"]["tre_mm"]
                    worse, better = dt > WRONG_MM, dt < -WRONG_MM
                    worse_n += worse
                    better_n += better
                    kept += k
                    kept_bad += k and worse
                    rej_good += (not k) and better
                t = [r["stages"][r["final"][(rule, cs)]]["tre_mm"] for r in rr]
                if m in choice_motions:
                    pooled += t
                d["per_motion"][m] = {"final_tre": q_med(t), "affine_compared": cmp, "affine_kept": kept,
                                      "affine_worse_cases": worse_n, "kept_when_worse": kept_bad,
                                      "affine_better_cases": better_n, "rejected_when_better": rej_good}
            rg = d["per_motion"].get("rigid", {})
            d["kept_when_worse_share_rigid"] = (round(rg["kept_when_worse"] / rg["affine_worse_cases"], 3)
                                                if rg.get("affine_worse_cases") else 0.0)
            d["eligible"] = d["kept_when_worse_share_rigid"] <= 0.10
            d["pooled_p90_choice_motions"] = q_med(pooled)[1]
            d["wrong_decisions_total"] = sum(v["kept_when_worse"] + v["rejected_when_better"]
                                             for v in d["per_motion"].values())
            item2[f"{rule}_{cs}"] = d
    for cs in CUTSETS:
        el = [r for r in RULES if item2[f"{r}_{cs}"]["eligible"]]
        item2[f"choice_{cs}"] = min(el, key=lambda r: (item2[f"{r}_{cs}"]["pooled_p90_choice_motions"]
                                                    if item2[f"{r}_{cs}"]["pooled_p90_choice_motions"] is not None
                                                    else np.inf)) if el else None
    out["item2"] = item2
    # 3. presence and extent
    arms = ["oracle", *STAGES, "bspline"] + [f"chain_{rl}_{cs}" for cs in CUTSETS for rl in RULES]
    taus = fit_taus(rows, arms)
    sc = score_groups(rows, arms, taus)
    out["presence"], out["extent"] = sc["presence"], sc["extent"]
    out["taus"] = {f"{k[0]}|{k[1]}|{k[2]}": round(v, 4) for k, v in sorted(taus.items())}
    # 4. strike (deciding: chain_ja51_prov = chain_shipped); reported on the others
    out["strike"] = strike_on(out, "chain_ja51_prov")
    out["strike_reported"] = {a: strike_on(out, a) for a in
                              ["chain_ja51_fit"] + [f"chain_{rl}_{cs}" for cs in CUTSETS for rl in RULES[1:]] +
                              ["oracle", "rigid"]}
    out["phase_flag_rate_striking"] = {
        cs: round(float(np.mean([bool(r["phase"][("ja51", cs)]["flags"]) for r in rows
                                 if r["motion"] in ("none", "rigid")])), 3) for cs in CUTSETS}
    # 5. phase detection (JA52) on the deciding-chain final stage: flag rates by motion, and AUCs
    ph = {}
    for cs in CUTSETS:
        for b in ("below", "equal", "above"):
            def vals(m, key):
                return [r["stages"][r["final"][("ja51", cs)]][key] if key == "edge_offset_mm"
                        else r["stages"][r["final"][("ja51", cs)]]["qc"][key]
                        for r in rows if r["motion"] == m and r["blood"] == b]
            ph[f"{cs}|{b}"] = {
                "rim_dark_auc_phase_vs_rigid": auc(vals("phase", "rim_dark"), vals("rigid", "rim_dark")),
                    "neg_edge_auc_larger_cavity_vs_rigid": auc(
                    [-x for m in ("phase_m5", "phase_neg") for x in vals(m, "edge_offset_mm") if x is not None],
                    [-x for x in vals("rigid", "edge_offset_mm") if x is not None]),
                "edge_offset_median": {m: q_med(vals(m, "edge_offset_mm"))[0]
                                       for m in ("rigid", "phase", "phase_m5", "phase_neg")}}
    out["phase"] = ph
    Path(out_path).write_text(json.dumps(out, indent=1, default=str) + "\n")
    return out


if __name__ == "__main__":
    o = main(*sys.argv[1:3])
    print("cases", o["n_cases"], "hearts", len(o["hearts"]), "replay", o["replay_check"])
    for r in o["registration"]:
        print(r["motion"], {s: r[f"{s}_tre"][:2] for s in STAGES}, r.get("bspline_tre"),
              "ja51_prov", r["chain_ja51_prov"]["tre"][:2], r["chain_ja51_prov"]["stages"],
              "ph", r["chain_ja51_prov"]["phase_suspect"], "ja51_fit", r["chain_ja51_fit"]["tre"][:2],
              r["chain_ja51_fit"]["stages"], "ph", r["chain_ja51_fit"]["phase_suspect"])
    print(json.dumps({k: v["struck"] for k, v in o["strike"].items() if isinstance(v, dict) and "struck" in v}))
    for k in ("choice_prov", "choice_fit"):
        print(k, o["item2"][k])
