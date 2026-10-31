"""Shared synthetic-LIE benchmark v3 (Round 4, #251): score results_v3.jsonl -> scores_v3.json.

Pre-registered on #251 before any v3 result (Golf's posts of 2026-10-30).

1. **The shipped JA51 chain**, assembled from the logged stages with the shipped decision functions
   (`QC.passes`, `affine_sanity`, `qc_rule_accepts`, `normalised_max`):
     R0 if it passes QC; else rigid4; if rigid4 fails QC, affine4 replaces it only if the affine rule accepts; if the
     result still fails QC, rigid10 replaces it if it passes QC or lowers the normalised maximum.
   QC cuts: p95 of the shipped QC at R0 on motion 'none', per blood level and CNR, from the *other* half of the
   hearts (v2's half split and method, on the shipped QC definitions). `rim_dark`'s phase cut = its QC cut
   (`QCCuts.max_rim_dark_phase` None, as shipped); the edge-offset flag is the shipped 0.6 mm.
2. **Affine-rule candidates (#251 item 2)**, each a whole alternative chain (same cuts, same stages):
     literal  JA51 4(a) sanity and 4(b) as shipped (`affine_accepted`);
     a        sanity; no normalised rise over the three wall shares only; the normalised maximum falls;
     b        sanity; the normalised maximum falls; no value newly crosses its cut;
     c        sanity; if |log det| >= 0.02 the sanity bound decides alone, else 4(b);
     g        (Golf) sanity; the normalised maximum does not rise; and (affine passes QC or |log det| >= 0.02);
     never    affine never kept;   always   affine kept whenever sane.
   The pick (pre-registered): lowest pooled chain TRE p90 over scale, aniso, phase and phase_neg, subject to (i) on
   none and rigid, at every blood x CNR, chain TRE median and p90 <= never-affine's + 0.05 mm, and (ii) no presence
   strike that never-affine does not have. Ties within 0.02 mm go to fewer clauses; nothing qualifying -> never.
3. **Presence and extent** as v2 (`score.py`), on every arm and chain: sensitivity (pooled and by true Kim bin),
   specificity, specificity on the scar-free twin (own constants), spill share (blood set to remote). P-J's tau is
   re-fitted per arm (p99 of E-D on scar-free segments of the other half, motions none and rigid).
4. **Strike** (#179's rules, unchanged): on `chain` (JA51 literal), CNR 5, motion none or rigid, any blood level:
   sens < 0.75, spec < 0.93, scar-free spec < 0.93 or spill > 0.25. Same rules reported on the other chains/arms.
5. **Phase step (JA52)** on each chain's final stage: flag rates by motion (rim_dark above its cut; |edge offset|
   > 0.6 mm), only when evaluable (contrast >= 2 SD). And presence with the flagged cases in / out.
6. **B-spline (JA53, report only)**: TRE and presence on nonrigid, and on rigid at CNR 5 (harm check).

Usage: python experiments/JanusM/bench_lie/score_v3.py [results_v3.jsonl[.gz]]
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
from janusm.scar import registration as R  # noqa: E402
from score import EXT, PRES, arr, auc, half, kim, load  # noqa: E402

STRIKE_MOTIONS = ("none", "rigid")
MOTIONS = ("none", "rigid", "scale", "aniso", "phase", "phase_neg", "nonrigid")
SHIP_QC = ("fatlike", "bloodlike", "brighter_than_blood", "rim_dark")
RULES = ("literal", "a", "b", "c", "g", "never", "always")
RULE_CLAUSES = {"literal": 3, "a": 3, "b": 3, "c": 4, "g": 4, "never": 0, "always": 1}
SCALE_MOTIONS = ("scale", "aniso", "phase", "phase_neg")
LOGDET_SCALE = 0.02
TOL_MM = 0.05
TIE_MM = 0.02


def qc_of(log):
    nan = float("nan")
    g = lambda k: nan if log.get(k) is None else float(log[k])  # noqa: E731
    return R.QC(g("fatlike"), g("bloodlike"), g("brighter_than_blood"), g("rim_dark"), g("blood_median"),
                g("remote_median"), 1, g("remote_sd"))


def fit_cuts(rows):
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["motion"] == "none":
            s = r["arms"]["R0"]["shipped"]
            for k in SHIP_QC:
                if s.get(k) is not None:
                    acc[(half(r["heart"]), r["blood"], r["cnr"])][k].append(s[k])
    cuts = {}
    for (hh, b, c), d in acc.items():
        v = [float(np.percentile(d[k], 95)) for k in SHIP_QC]
        cuts[(1 - hh, b, c)] = R.QCCuts(*v)
    return cuts


def fit_cuts_registered(rows, tre_pass=1.0):
    """JA53's development definition, emulated (post-hoc, reported only): p95 of each shipped QC value over
    *registered, phase-matched, reader-passed* cases -- rigid4 on motions none and rigid with TRE < 1 mm standing in
    for the reader's pass -- from the other half of the hearts, per blood x CNR. rim_dark's phase cut is the same p95.
    """
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        a = r["arms"]["rigid4"]
        if r["motion"] in STRIKE_MOTIONS and a.get("tre_mm") is not None and a["tre_mm"] < tre_pass:
            for k in SHIP_QC:
                if a["shipped"].get(k) is not None:
                    acc[(half(r["heart"]), r["blood"], r["cnr"])][k].append(a["shipped"][k])
    cuts = {}
    for (hh, b, c), d in acc.items():
        cuts[(1 - hh, b, c)] = R.QCCuts(*[float(np.percentile(d[k], 95)) for k in SHIP_QC])
    return cuts


def accept(rule, rig, aff, cuts):
    """Whether affine4 replaces rigid4 under one candidate rule (rigid4 has already failed QC)."""
    # the sanity numbers are R.affine_sanity's, logged by run_v3 on the shipped affine matrix
    san = {"ok": bool(aff["shipped"]["sane"]), "log_det": aff["shipped"]["log_det"]}
    if rule == "never":
        return False
    if not san["ok"]:
        return False
    if rule == "always":
        return True
    qa, qr = qc_of(aff["shipped"]), qc_of(rig["shipped"])
    na, nr = R.normalised(qa, cuts), R.normalised(qr, cuts)
    if not (np.isfinite(na).all() and np.isfinite(nr).all()):
        return False
    ld = abs(san["log_det"])
    if rule == "literal":                       # = R.affine_accepted: sanity (above) and R.qc_rule_accepts
        return R.qc_rule_accepts(qa, qr, cuts)
    if rule == "a":
        return bool((na[:3] <= nr[:3]).all() and na.max() < nr.max())
    if rule == "b":
        cut1 = np.ones_like(na)
        newly = (na > cut1) & (nr <= cut1)
        return bool(na.max() < nr.max() and not newly.any())
    if rule == "c":
        return True if ld >= LOGDET_SCALE else R.qc_rule_accepts(qa, qr, cuts)
    if rule == "g":
        return bool(na.max() <= nr.max() and (qa.passes(cuts) or ld >= LOGDET_SCALE))
    raise ValueError(rule)


def chain(r, cuts, rule, fallback="lowers"):
    """The JA51 chain under one affine rule. Returns the final stage name.

    ``fallback`` (JA51 step 5): "lowers" as shipped (rigid10 kept if it passes QC or lowers the normalised maximum);
    "pass" (kept only if it passes QC); "none" (no fallback). The last two are post-hoc, reported only."""
    a = r["arms"]
    passes = lambda arm: qc_of(a[arm]["shipped"]).passes(cuts)  # noqa: E731
    if passes("R0"):
        return "R0"
    final = "rigid4"
    if not passes("rigid4") and accept(rule, a["rigid4"], a["affine4"], cuts):
        final = "affine4"
    if not passes(final) and fallback != "none":
        if fallback == "pass":
            return "rigid10" if passes("rigid10") else final
        m_new = R.normalised_max(qc_of(a["rigid10"]["shipped"]), cuts)
        m_old = R.normalised_max(qc_of(a[final]["shipped"]), cuts)
        if passes("rigid10") or (np.isfinite(m_new) and np.isfinite(m_old) and m_new < m_old):
            final = "rigid10"
    return final


def fit_phase_cuts(rows, rule="literal"):
    """JA53's phase cut for rim_dark: p95 of the *final-stage* rim_dark over phase-matched cases (motions none and
    rigid), from the other half of the hearts, per blood x CNR. Post-hoc, reported beside the shipped default
    (QCCuts.max_rim_dark_phase None = the R0 QC cut), which is what `load_provisional_qc_cuts` gives."""
    acc = defaultdict(list)
    for r in rows:
        if r["motion"] in STRIKE_MOTIONS:
            v = r["arms"][f"chain_{rule}"]["shipped"].get("rim_dark")
            if v is not None:
                acc[(half(r["heart"]), r["blood"], r["cnr"])].append(v)
    return {(1 - hh, b, c): float(np.percentile(v, 95)) for (hh, b, c), v in acc.items()}


def phase_flags(rec, cuts, rim_cut=None):
    s = rec["shipped"]
    rim_cut = cuts.rim_dark_phase if rim_cut is None else rim_cut
    ev = s.get("contrast") is not None and s["contrast"] >= R.MIN_PHASE_CONTRAST_SD
    f = []
    if ev:
        if s.get("rim_dark") is not None and s["rim_dark"] > rim_cut:
            f.append("rim_dark")
        if s.get("edge_offset_mm") is not None and abs(s["edge_offset_mm"]) > cuts.max_edge_offset_mm:
            f.append("edge_offset")
    return ev, f


def fit_taus(rows, arms):
    acc = defaultdict(list)
    for r in rows:
        if r["motion"] not in STRIKE_MOTIONS:
            continue
        free = (np.nan_to_num(arr(r["truth_depth"])) < 0.01) & (np.nan_to_num(arr(r["truth_vol"])) < 0.01)
        for arm in arms:
            rec = r["arms"].get(arm)
            if rec is None or "ungradable" in rec:
                continue
            ed, tw = arr(rec["scar"]["ed"]), arr(rec["free_own"]["ed"])
            acc[(half(r["heart"]), arm, r["blood"], r["cnr"])] += list(ed[free & np.isfinite(ed)]) + \
                list(tw[np.isfinite(tw)])
    return {(1 - hh, arm, b, c): (float(np.percentile(v, 99)) if v else 0.1) for (hh, arm, b, c), v in acc.items()}


def calls(rec, tau):
    return {"P-K": np.nan_to_num(arr(rec["pk_share"])) >= 0.05, "P-J": np.nan_to_num(arr(rec["ed"])) >= tau,
            "P-G": np.nan_to_num(arr(rec["pg_share"])) >= 0.05}


def presence_table(rows, arm, taus, key=lambda r: (r["blood"], r["cnr"], r["motion"]), select=None):
    groups = defaultdict(list)
    for r in rows:
        if arm in r["arms"] and (select is None or select(r)):
            groups[key(r)].append(r)
    out_p, out_e = [], []
    for k, rr in sorted(groups.items()):
        P = {p: {"tp": 0, "fn": 0, "tn": 0, "fp": 0, "tp_nb": 0, "free_tn": 0, "free_n": 0, "ungradable": 0,
                 "bybin": np.zeros((5, 2), int)} for p in PRES}
        E = {(p, e, t): [0, 0] for p in PRES for e in EXT for t in ("vol", "depth")}
        for r in rr:
            rec = r["arms"][arm]
            tau = taus.get((half(r["heart"]), arm, r["blood"], r["cnr"]), 0.1)
            tv, td = np.nan_to_num(arr(r["truth_vol"])), np.nan_to_num(arr(r["truth_depth"]))
            if "ungradable" in rec:          # no carried wall to grade: every scarred segment is a miss (JA55-like)
                truth = (tv >= 0.01) | (td >= 0.01)
                tbin = kim(td)
                for p in PRES:
                    P[p]["fn"] += int(truth.sum())
                    P[p]["ungradable"] += 1
                    for kb in range(1, 5):
                        P[p]["bybin"][kb] += [0, int((truth & (tbin == kb)).sum())]
                continue
            valid = np.isfinite(arr(rec["scar"]["pk_share"]))
            truth = ((tv >= 0.01) | (td >= 0.01))[valid]
            cs, cn, co = calls(rec["scar"], tau), calls(rec["noblood"], tau), calls(rec["free_own"], tau)
            vo = np.isfinite(arr(rec["free_own"]["pk_share"]))
            tbin = kim(td[valid])
            for p in PRES:
                s, nb = cs[p][valid], cn[p][valid]
                d = P[p]
                d["tp"] += int((s & truth).sum())
                d["fn"] += int((~s & truth).sum())
                d["tn"] += int((~s & ~truth).sum())
                d["fp"] += int((s & ~truth).sum())
                d["tp_nb"] += int((nb & truth).sum())
                d["free_tn"] += int((~co[p][vo]).sum())
                d["free_n"] += int(vo.sum())
                for kb in range(1, 5):
                    mb = truth & (tbin == kb)
                    d["bybin"][kb] += [int((s & mb).sum()), int(mb.sum())]
                both = s & truth
                for e, kk in (("E-V", "ev"), ("E-D", "ed")):
                    est = np.maximum(kim(arr(rec["scar"][kk])[valid]), 1)
                    for t, tr in (("vol", tv), ("depth", td)):
                        tb = np.maximum(kim(tr[valid]), 1)
                        E[(p, e, t)][0] += int((est[both] == tb[both]).sum())
                        E[(p, e, t)][1] += int(both.sum())
        base = dict(zip(("blood", "cnr", "motion"), k)) if isinstance(k, tuple) and len(k) == 3 else {"key": k}
        for p, d in P.items():
            sens = d["tp"] / max(d["tp"] + d["fn"], 1)
            sens_nb = d["tp_nb"] / max(d["tp"] + d["fn"], 1)
            out_p.append({"arm": arm, **base, "rule": p, "n_cases": len(rr), "sens": round(sens, 3),
                          "spec": round(d["tn"] / max(d["tn"] + d["fp"], 1), 3),
                          "spec_scarfree_hearts": round(d["free_tn"] / max(d["free_n"], 1), 3),
                          "spill_share": round((sens - sens_nb) / sens, 3) if sens > 0 else None,
                          "sens_by_bin": {str(b): (round(d["bybin"][b][0] / d["bybin"][b][1], 3)
                                                   if d["bybin"][b][1] else None) for b in range(1, 5)},
                          "n_scarred": d["tp"] + d["fn"], "n_free": d["tn"] + d["fp"],
                          "n_ungradable": d["ungradable"]})
        for (p, e, t), (kk, n) in E.items():
            out_e.append({"arm": arm, **base, "presence": p, "extent": e, "truth": t,
                          "exact_agreement": round(kk / n, 3) if n else None, "n_both": n})
    return out_p, out_e


def strike(pres, ext):
    res = {}
    xs0 = [x for x in pres if x["cnr"] == 5 and x["motion"] in STRIKE_MOTIONS]
    for p in PRES:
        xs = [x for x in xs0 if x["rule"] == p]
        why = [f"{x['blood']}/{x['motion']}: sens {x['sens']}" for x in xs if x["sens"] < 0.75] + \
              [f"{x['blood']}/{x['motion']}: spec {x['spec']}" for x in xs if x["spec"] < 0.93] + \
              [f"{x['blood']}/{x['motion']}: spill {x['spill_share']}" for x in xs
               if x["spill_share"] is not None and x["spill_share"] > 0.25] + \
              [f"{x['blood']}/{x['motion']}: spec on scar-free hearts {x['spec_scarfree_hearts']}" for x in xs
               if x["spec_scarfree_hearts"] < 0.93]
        res[p] = {"struck": bool(why), "why": why,
                  "min_sens": min(x["sens"] for x in xs) if xs else None,
                  "min_spec": min(x["spec"] for x in xs) if xs else None,
                  "min_spec_scarfree": min(x["spec_scarfree_hearts"] for x in xs) if xs else None,
                  "max_spill": max((x["spill_share"] or 0) for x in xs) if xs else None}
    e0 = [x for x in ext if x["cnr"] == 5 and x["motion"] in STRIKE_MOTIONS]
    surviving = [p for p in ("P-J", "P-G") if not res[p]["struck"]] or ["P-J", "P-G"]
    for e in EXT:
        pooled = {}
        for p in surviving:
            for t in ("vol", "depth"):
                xs = [x for x in e0 if x["extent"] == e and x["presence"] == p and x["truth"] == t and x["n_both"]]
                n = sum(x["n_both"] for x in xs)
                pooled[f"{p}|{t}"] = round(sum(x["exact_agreement"] * x["n_both"] for x in xs) / n, 3) if n else None
        fail = all(all(pooled[f"{p}|{t}"] is not None and pooled[f"{p}|{t}"] < 0.60 for t in ("vol", "depth"))
                   for p in surviving)
        res[e] = {"struck": fail, "pooled_cnr5_none_rigid": pooled}
    return res


def tre_stats(rows, arm, sel):
    t = [r["arms"][arm]["tre_mm"] for r in rows if sel(r) and arm in r["arms"] and
         r["arms"][arm].get("tre_mm") is not None]
    if not t:
        return None
    return {"n": len(t), "median": round(float(np.median(t)), 3), "p90": round(float(np.percentile(t, 90)), 3),
            "max": round(float(np.max(t)), 3)}


def main(path=None):
    path = Path(path) if path else HERE / "results_v3.jsonl"
    rows, skips = load(path)
    errors = [{k: r.get(k) for k in ("heart", "blood", "cnr", "motion", "case_error")} for r in rows if "arms" not in r]
    rows = [r for r in rows if "arms" in r]
    cuts = fit_cuts(rows)
    cuts_reg = fit_cuts_registered(rows)
    stage_counts = {}
    for r in rows:
        c = cuts[(half(r["heart"]), r["blood"], r["cnr"])]
        r["stage"] = {}
        for rule in RULES:
            st = chain(r, c, rule)
            r["stage"][rule] = st
            r["arms"][f"chain_{rule}"] = r["arms"][st]
        r["arms"]["chain"] = r["arms"]["chain_literal"]
        c2 = cuts_reg.get((half(r["heart"]), r["blood"], r["cnr"]))
        if c2 is not None:                           # post-hoc: JA53-style registered cuts, report only
            for rule in ("literal", "b", "never"):
                st = chain(r, c2, rule)
                r["stage"][f"{rule}_regcuts"] = st
                r["arms"][f"chain_{rule}_regcuts"] = r["arms"][st]
        for fb in ("pass", "none"):                   # post-hoc (after the first partial results), report only
            st = chain(r, c, "literal", fb)
            r["stage"][f"literal_fb_{fb}"] = st
            r["arms"][f"chain_literal_fb_{fb}"] = r["arms"][st]
    chain_arms = [f"chain_{x}" for x in RULES] + ["chain_literal_fb_pass", "chain_literal_fb_none",
                                                  "chain_literal_regcuts", "chain_b_regcuts", "chain_never_regcuts"]
    arms = ["oracle", "R0", "rigid4", "affine4", "rigid10", "bspline"] + chain_arms
    taus = fit_taus(rows, arms)
    out = {"version": 3, "scar_version": R.SCAR_VERSION, "n_cases": len(rows),
           "hearts": sorted({r["heart"] for r in rows}), "skipped": skips, "case_errors": errors,
           "ungradable_arms": sorted({f"{r['heart']}|{r['blood']}|{r['cnr']}|{r['motion']}|{a}"
                                      for r in rows for a, v in r["arms"].items()
                                      if "ungradable" in v and not a.startswith("chain")}),
           "qc_cuts": {f"{k[0]}|{k[1]}|{k[2]}": dict(zip(SHIP_QC, np.round(v.values(), 4).tolist()))
                       for k, v in sorted(cuts.items())},
           "qc_cuts_registered": {f"{k[0]}|{k[1]}|{k[2]}": dict(zip(SHIP_QC, np.round(v.values(), 4).tolist()))
                                  for k, v in sorted(cuts_reg.items())},
           "taus": {f"{k[0]}|{k[1]}|{k[2]}|{k[3]}": round(v, 4) for k, v in sorted(taus.items())}}
    # 1-2. registration: TRE per arm / chain and motion; stage counts
    reg = []
    for m in MOTIONS:
        rr = [r for r in rows if r["motion"] == m]
        row = {"motion": m, "n": len(rr)}
        for arm in arms:
            row[arm] = tre_stats(rows, arm, lambda r, m=m: r["motion"] == m)
        row["stages"] = {rule: {s: sum(r["stage"][rule] == s for r in rr) for s in ("R0", "rigid4", "affine4", "rigid10")}
                         for rule in list(RULES) + ["literal_fb_pass", "literal_fb_none", "literal_regcuts",
                                                    "b_regcuts", "never_regcuts"] if rule in rr[0]["stage"]}
        row["affine_sane"] = sum(bool(r["arms"]["affine4"]["shipped"]["sane"]) for r in rr)
        row["affine_better_tre"] = sum(r["arms"]["affine4"]["tre_mm"] < r["arms"]["rigid4"]["tre_mm"] for r in rr)
        row["R0_passes"] = sum(r["stage"]["literal"] == "R0" for r in rr)
        reg.append(row)
    out["registration"] = reg
    # per blood x cnr for the rule-choice constraint
    reg_bc = {}
    for rule in RULES:
        for m in MOTIONS:
            for b in ("below", "equal", "above"):
                for c in (3, 5):
                    reg_bc[f"{rule}|{m}|{b}|{c}"] = tre_stats(
                        rows, f"chain_{rule}", lambda r, m=m, b=b, c=c: r["motion"] == m and r["blood"] == b and r["cnr"] == c)
    out["registration_by_blood_cnr"] = reg_bc
    # 3-4. presence, extent, strike
    pres, ext = [], []
    for arm in arms:
        p, e = presence_table(rows, arm, taus)
        pres += p
        ext += e
    out["presence"], out["extent"] = pres, ext
    out["strike"] = strike([x for x in pres if x["arm"] == "chain_literal"],
                           [x for x in ext if x["arm"] == "chain_literal"])
    out["strike_reported"] = {a: strike([x for x in pres if x["arm"] == a], [x for x in ext if x["arm"] == a])
                              for a in arms if a not in ("chain_literal", "bspline")}
    # 2. the pre-registered affine-rule pick
    pick = {}
    never = out["strike_reported"]["chain_never"]
    for rule in RULES:
        t = [r["arms"][f"chain_{rule}"]["tre_mm"] for r in rows if r["motion"] in SCALE_MOTIONS]
        p90 = float(np.percentile(t, 90))
        worse = []
        for m in STRIKE_MOTIONS:
            for b in ("below", "equal", "above"):
                for c in (3, 5):
                    x, y = reg_bc[f"{rule}|{m}|{b}|{c}"], reg_bc[f"never|{m}|{b}|{c}"]
                    if x is None or y is None:
                        continue
                    if x["median"] > y["median"] + TOL_MM or x["p90"] > y["p90"] + TOL_MM:
                        worse.append(f"{m}/{b}/{c}: {x['median']}/{x['p90']} vs never {y['median']}/{y['p90']}")
        sr = out["strike"] if rule == "literal" else out["strike_reported"][f"chain_{rule}"]
        new_strike = [p for p in ("P-J", "P-G") if sr[p]["struck"] and not never[p]["struck"]]
        pick[rule] = {"scale_motions_p90": round(p90, 3),
                      "scale_motions_median": round(float(np.median(t)), 3),
                      "none_rigid_worse_than_never": worse, "new_strikes": new_strike,
                      "qualifies": (not worse and not new_strike), "clauses": RULE_CLAUSES[rule]}
    q = {k: v for k, v in pick.items() if v["qualifies"] and k not in ("never",)}
    if q:
        best = min(v["scale_motions_p90"] for v in q.values())
        tied = [k for k, v in q.items() if v["scale_motions_p90"] <= best + TIE_MM]
        chosen = min(tied, key=lambda k: (RULE_CLAUSES[k], q[k]["scale_motions_p90"]))
    else:
        chosen = "never"
    out["affine_rule"] = {"candidates": pick, "pick": chosen}
    # 5. phase step on each chain's final stage
    ph = {}
    pcut = fit_phase_cuts(rows)
    out["rim_dark_phase_cuts_ja53"] = {f"{k[0]}|{k[1]}|{k[2]}": round(v, 4) for k, v in sorted(pcut.items())}
    for rule in ("literal", chosen, "literal_ja53cut", "literal_regcuts"):
        for m in MOTIONS:
            rr = [r for r in rows if r["motion"] == m]
            n_ev = n_any = n_rim = n_edge = 0
            offs = []
            for r in rr:
                key = (half(r["heart"]), r["blood"], r["cnr"])
                c = cuts[key]
                if rule == "literal_regcuts":
                    c = cuts_reg[key]
                    rec = r["arms"]["chain_literal_regcuts"]
                    ev, f = phase_flags(rec, c)
                elif rule == "literal_ja53cut":
                    rec = r["arms"]["chain_literal"]
                    ev, f = phase_flags(rec, c, pcut.get(key))
                else:
                    rec = r["arms"][f"chain_{rule}"]
                    ev, f = phase_flags(rec, c)
                n_ev += ev
                n_any += bool(f)
                n_rim += "rim_dark" in f
                n_edge += "edge_offset" in f
                if rec["shipped"].get("edge_offset_mm") is not None:
                    offs.append(rec["shipped"]["edge_offset_mm"])
                r.setdefault("phase_suspect", {})[rule] = bool(f)
            ph[f"{rule}|{m}"] = {"n": len(rr), "evaluable": n_ev, "flagged": n_any, "rim_dark": n_rim,
                                 "edge_offset": n_edge,
                                 "edge_offset_median": round(float(np.median(offs)), 3) if offs else None,
                                 "edge_offset_p10_p90": (np.round(np.percentile(offs, [10, 90]), 3).tolist()
                                                         if offs else None)}
    out["phase"] = ph
    # edge-offset AUC: phase_neg vs rigid, phase vs rigid (chain literal), |offset| and signed
    eo = lambda m: [r["arms"]["chain_literal"]["shipped"].get("edge_offset_mm") for r in rows if r["motion"] == m]  # noqa: E731
    clean = lambda v: [x for x in v if x is not None]  # noqa: E731
    out["phase_auc"] = {
        "edge_offset_neg_phase_neg_vs_rigid": auc([-x for x in clean(eo("phase_neg"))], [-x for x in clean(eo("rigid"))]),
        "edge_offset_pos_phase_vs_rigid": auc(clean(eo("phase")), clean(eo("rigid"))),
        "abs_edge_offset_phase_neg_vs_rigid": auc([abs(x) for x in clean(eo("phase_neg"))], [abs(x) for x in clean(eo("rigid"))]),
        "rim_dark_phase_vs_rigid": auc(
            clean([r["arms"]["chain_literal"]["shipped"].get("rim_dark") for r in rows if r["motion"] == "phase"]),
            clean([r["arms"]["chain_literal"]["shipped"].get("rim_dark") for r in rows if r["motion"] == "rigid"])),
        "rim_dark_phase_neg_vs_rigid": auc(
            clean([r["arms"]["chain_literal"]["shipped"].get("rim_dark") for r in rows if r["motion"] == "phase_neg"]),
            clean([r["arms"]["chain_literal"]["shipped"].get("rim_dark") for r in rows if r["motion"] == "rigid"]))}
    # item 4: presence in the phase motions, flagged cases in / out (CNR 5, chain literal)
    st = {}
    for m in ("phase", "phase_neg", "rigid", "none", "scale", "aniso"):
        for label, sel in (("all", lambda r: True), ("unflagged", lambda r: not r["phase_suspect"]["literal"]),
                           ("flagged", lambda r: r["phase_suspect"]["literal"]),
                           ("unflagged_ja53cut", lambda r: not r["phase_suspect"]["literal_ja53cut"]),
                           ("flagged_ja53cut", lambda r: r["phase_suspect"]["literal_ja53cut"]),
                           ("unflagged_regcuts", lambda r: not r["phase_suspect"]["literal_regcuts"]),
                           ("flagged_regcuts", lambda r: r["phase_suspect"]["literal_regcuts"])):
            p, _ = presence_table(rows, "chain_literal", taus, key=lambda r: r["blood"],
                                  select=lambda r, m=m, sel=sel: r["motion"] == m and r["cnr"] == 5 and sel(r))
            st[f"{m}|{label}"] = [{k: x[k] for k in ("key", "rule", "n_cases", "sens", "spec", "spec_scarfree_hearts",
                                                    "n_scarred", "n_free")} for x in p if x["rule"] != "P-K"]
    out["phase_stratum_presence"] = st
    (HERE / "scores_v3.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    o = main(*(sys.argv[1:2] or []))
    print("cases", o["n_cases"], "hearts", len(o["hearts"]), "skipped", [(s["heart"], s.get("skip")) for s in o["skipped"]])
    for r in o["registration"]:
        print(r["motion"], r["n"], {a: (r[a]["median"], r[a]["p90"]) for a in ("R0", "rigid4", "affine4", "rigid10",
              "chain_literal", "chain_never") if r.get(a)}, r["stages"]["literal"], "sane", r["affine_sane"],
              "aff<rig", r["affine_better_tre"])
    print(json.dumps(o["strike"], indent=1))
    print(json.dumps(o["affine_rule"], indent=1))
