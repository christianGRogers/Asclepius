"""Shared synthetic-LIE benchmark: score results.jsonl -> scores.json, and print the tables.

Truth presence: a segment is scarred if its truth depth extent or volume share is >= 0.01.

1. Registration: TRE per arm and motion; QC values; whether affine lowers the QC sum against rigid.
   The JA29 chain is emulated with development-style cuts fitted on the other half of the hearts (half-split by
   salted hash): stop at R0 if every QC value is <= its cut (the 95th percentile of R0's values on aligned cases,
   motion 'none', same blood level and CNR); else rigid; affine replaces rigid only if it lowers fat_like +
   above_blood.
2. Presence (P-K, P-J, P-G): sensitivity (pooled and by true Kim bin), specificity in scarred hearts, specificity
   on scar-free hearts (the twin graded with its own constants, Kilo 1b), and two spill shares:
     spill (striking, Golf/Kilo 1a) = (sens_full - sens_noblood) / sens_full, with blood set to remote and the full
       image's constants kept;
     spill_twin (reported) = the share of true-positive calls that also fire on the scar-free twin with the full
       image's constants.
   P-J's tau is the p99 of E-D over scar-free segments (scarred hearts' and twins') of the other half of the hearts,
   per arm, blood level and CNR, from motions 'none' and 'rigid'.
3. Extent (E-V, E-D) under each presence rule: exact Kim-bin agreement on scar-on-both segments, against truth as
   volume share and as depth extent.
4. Strike rules, as pre-registered on #179 before any result, with Kilo's 1a-1c accepted there by Golf and Juliet:
   - presence: struck if, at CNR 5, motion 'none' or 'rigid', any blood level, on the chain: sens < 0.75, or
     spec < 0.93, or spill share > 0.25, or specificity on scar-free hearts < 0.93; if every presence candidate is
     struck, none is (1c) and the one with the highest minimum sensitivity among those passing both specificity
     bars goes to development;
   - extent: struck if, at CNR 5, motion 'none' or 'rigid', exact agreement on scar-on-both < 0.60 under both truth
     definitions (each presence rule's scar-on-both set, so a struck extent fails under every presence rule).
5. QC and phase (ruling section 7 item 5): AUC of each truth-free QC value for (a) misregistration
   (R0 on moved hearts vs R0 on unmoved) and (b) phase mismatch (chain on 'phase' vs chain on 'rigid').
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PRES = ("P-K", "P-J", "P-G")
EXT = ("E-V", "E-D")
QCS = ("fat_like", "blood_like", "above_blood", "rim_dark")
STRIKE_MOTIONS = ("none", "rigid")
MOTIONS = ("none", "rigid", "scale", "phase", "nonrigid")


def half(h):
    return int(hashlib.sha256(f"bench-lie-r3-half:{h}".encode()).hexdigest()[:8], 16) % 2


def kim(x):
    x = np.nan_to_num(np.asarray(x, float))
    return np.select([x <= 0.005, x <= 0.25, x <= 0.50, x <= 0.75], [0, 1, 2, 3], 4)


def arr(x):
    return np.array([np.nan if v is None else v for v in x], float)


def auc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    pos, neg = pos[np.isfinite(pos)], neg[np.isfinite(neg)]
    if not len(pos) or not len(neg):
        return None
    r = np.concatenate([pos, neg]).argsort().argsort() + 1.0
    return round(float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))), 3)


def load(path):
    rows = [json.loads(l) for l in open(path)]
    return [r for r in rows if "skip" not in r], [r for r in rows if "skip" in r]


def fit_taus(rows):
    """tau[(half, arm, blood, cnr)] fitted on the *other* half."""
    acc = defaultdict(list)
    for r in rows:
        if r["motion"] not in STRIKE_MOTIONS:
            continue
        free = (np.nan_to_num(arr(r["truth_depth"])) < 0.01) & (np.nan_to_num(arr(r["truth_vol"])) < 0.01)
        for arm, rec in r["arms"].items():
            ed = arr(rec["scar"]["ed"])
            tw = arr(rec["free_own"]["ed"])
            acc[(half(r["heart"]), arm, r["blood"], r["cnr"])] += list(ed[free & np.isfinite(ed)]) + \
                list(tw[np.isfinite(tw)])
    taus = {}
    for (hh, arm, b, c), v in acc.items():
        taus[(1 - hh, arm, b, c)] = float(np.percentile(v, 99)) if v else 0.1
    return taus


def fit_qc_cuts(rows):
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["motion"] == "none":
            q = r["arms"]["R0"]["scar"]["qc"]
            for k in QCS:
                if q.get(k) is not None and np.isfinite(q[k]):
                    acc[(half(r["heart"]), r["blood"], r["cnr"])][k].append(q[k])
    return {(1 - hh, b, c): {k: float(np.percentile(v, 95)) for k, v in d.items()} for (hh, b, c), d in acc.items()}


def chain(r, cuts):
    cut = cuts.get((half(r["heart"]), r["blood"], r["cnr"]), {})
    q0 = r["arms"]["R0"]["scar"]["qc"]
    if all(q0.get(k) is None or not np.isfinite(q0[k]) or q0[k] <= cut.get(k, np.inf) for k in ("fat_like", "above_blood", "blood_like")):
        return "R0"
    s = lambda a: r["arms"][a]["scar"]["qc"]["fat_like"] + r["arms"][a]["scar"]["qc"]["above_blood"]  # noqa: E731
    return "affine" if s("affine") < s("rigid") else "rigid"


def calls(rec, tau):
    return {"P-K": np.nan_to_num(arr(rec["pk_share"])) >= 0.05, "P-J": np.nan_to_num(arr(rec["ed"])) >= tau,
            "P-G": np.nan_to_num(arr(rec["pg_share"])) >= 0.05}


def main(path=HERE / "results.jsonl"):
    rows, skips = load(path)
    taus, cuts = fit_taus(rows), fit_qc_cuts(rows)
    for r in rows:
        r["chain_stage"] = chain(r, cuts)
        r["arms"]["chain"] = r["arms"][r["chain_stage"]]
        # variant (proposed): R0 if QC passes, else rigid with the 4 mm mask
        r["arms"]["chain_m4"] = r["arms"]["R0" if r["chain_stage"] == "R0" else "rigid_m4"]
    out = {"n_cases": len(rows), "hearts": sorted({r["heart"] for r in rows}), "skipped": skips,
           "registration": [], "presence": [], "extent": [], "qc_auc": {}, "strike": {}}
    # 1. registration
    for m in MOTIONS:
        rr = [r for r in rows if r["motion"] == m]
        row = {"motion": m, "n": len(rr)}
        for arm in ("R0", "rigid", "affine", "rigid_m4", "chain", "chain_m4"):
            t = [r["arms"][arm].get("tre_mm") for r in rr if r["arms"][arm].get("tre_mm") is not None]
            row[f"{arm}_tre_median"] = round(float(np.median(t)), 3) if t else None
            row[f"{arm}_tre_p90"] = round(float(np.percentile(t, 90)), 3) if t else None
            for k in QCS:
                v = [r["arms"][arm]["scar"]["qc"].get(k) for r in rr]
                v = [x for x in v if x is not None and np.isfinite(x)]
                row[f"{arm}_{k}_median"] = round(float(np.median(v)), 4) if v else None
        row["chain_stages"] = {s: sum(r["chain_stage"] == s for r in rr) for s in ("R0", "rigid", "affine")}
        row["affine_lowers_qc_share"] = round(float(np.mean([
            (r["arms"]["affine"]["scar"]["qc"]["fat_like"] + r["arms"]["affine"]["scar"]["qc"]["above_blood"]) <
            (r["arms"]["rigid"]["scar"]["qc"]["fat_like"] + r["arms"]["rigid"]["scar"]["qc"]["above_blood"])
            for r in rr])), 3) if rr else None
        out["registration"].append(row)
    # 2-3. presence and extent, per arm x blood x cnr x motion
    groups = defaultdict(list)
    for r in rows:
        for arm in ("oracle", "chain", "chain_m4", "rigid", "affine", "rigid_m4", "R0"):
            groups[(arm, r["blood"], r["cnr"], r["motion"])].append(r)
    for (arm, b, c, m), rr in sorted(groups.items()):
        P = {p: {"tp": 0, "fn": 0, "tn": 0, "fp": 0, "spill_twin": 0, "tp_nb": 0, "free_tn": 0, "free_n": 0,
                 "bybin": np.zeros((5, 2), int)} for p in PRES}
        E = {(p, e, t): [0, 0] for p in PRES for e in EXT for t in ("vol", "depth")}
        for r in rr:
            rec = r["arms"][arm]
            tau = taus.get((half(r["heart"]), arm, b, c), 0.1)
            tv, td = np.nan_to_num(arr(r["truth_vol"])), np.nan_to_num(arr(r["truth_depth"]))
            valid = np.isfinite(arr(rec["scar"]["pk_share"]))
            truth = ((tv >= 0.01) | (td >= 0.01))[valid]
            cs, cf, cn = calls(rec["scar"], tau), calls(rec["free_fixed"], tau), calls(rec["noblood"], tau)
            co = calls(rec["free_own"], tau)
            vo = np.isfinite(arr(rec["free_own"]["pk_share"]))
            tbin = kim(td[valid])
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
                for b in range(1, 5):
                    m = truth & (tbin == b)
                    P[p]["bybin"][b] += [int((s & m).sum()), int(m.sum())]
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
            out["presence"].append({"arm": arm, "blood": b, "cnr": c, "motion": m, "rule": p,
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
    # 4. strike
    pres = [x for x in out["presence"] if x["arm"] == "chain" and x["cnr"] == 5 and x["motion"] in STRIKE_MOTIONS]
    for p in PRES:
        xs = [x for x in pres if x["rule"] == p]
        why = [f"{x['blood']}/{x['motion']}: sens {x['sens']}" for x in xs if x["sens"] < 0.75] + \
              [f"{x['blood']}/{x['motion']}: spec {x['spec']}" for x in xs if x["spec"] < 0.93] + \
              [f"{x['blood']}/{x['motion']}: spill {x['spill_share']}" for x in xs
               if x["spill_share"] is not None and x["spill_share"] > 0.25] + \
              [f"{x['blood']}/{x['motion']}: spec on scar-free hearts {x['spec_scarfree_hearts']}" for x in xs
               if x["spec_scarfree_hearts"] < 0.93]
        out["strike"][p] = {"struck": bool(why), "why": why,
                            "min_sens": min(x["sens"] for x in xs) if xs else None,
                            "passes_both_spec": all(x["spec"] >= 0.93 and x["spec_scarfree_hearts"] >= 0.93
                                                    for x in xs)}
    if all(out["strike"][p]["struck"] for p in PRES):          # Kilo 1c: the menu never goes empty
        ok = [p for p in PRES if out["strike"][p]["passes_both_spec"]] or list(PRES)
        best = max(ok, key=lambda p: out["strike"][p]["min_sens"])
        out["strike"]["all_struck_rule_1c"] = {"to_development": best, "scar1": "expected, not conditional"}
        for p in PRES:
            out["strike"][p]["struck"] = False
    ext = [x for x in out["extent"] if x["arm"] == "chain" and x["cnr"] == 5 and x["motion"] in STRIKE_MOTIONS]
    surviving = [p for p in PRES if not out["strike"][p]["struck"]] or list(PRES)
    for e in EXT:
        pooled = {}
        for p in surviving:
            for t in ("vol", "depth"):
                xs = [x for x in ext if x["extent"] == e and x["presence"] == p and x["truth"] == t and x["n_both"]]
                n = sum(x["n_both"] for x in xs)
                pooled[f"{p}|{t}"] = round(sum(x["exact_agreement"] * x["n_both"] for x in xs) / n, 3) if n else None
        fail_all = all(all(pooled[f"{p}|{t}"] is not None and pooled[f"{p}|{t}"] < 0.60 for t in ("vol", "depth"))
                       for p in surviving)
        out["strike"][e] = {"struck": fail_all, "pooled_cnr5_none_rigid": pooled, "presence_rules": surviving}
    # 5. QC AUCs
    for k in QCS:
        mis = [r["arms"]["R0"]["scar"]["qc"].get(k) for r in rows if r["motion"] != "none"]
        ali = [r["arms"]["R0"]["scar"]["qc"].get(k) for r in rows if r["motion"] == "none"]
        res = {"misregistration_R0": auc([x for x in mis if x is not None], [x for x in ali if x is not None])}
        for b in ("below", "equal", "above"):
            ph = [r["arms"]["chain"]["scar"]["qc"].get(k) for r in rows if r["motion"] == "phase" and r["blood"] == b]
            rg = [r["arms"]["chain"]["scar"]["qc"].get(k) for r in rows if r["motion"] == "rigid" and r["blood"] == b]
            res[f"phase_vs_rigid_{b}"] = auc([x for x in ph if x is not None], [x for x in rg if x is not None])
            nr = [r["arms"]["chain"]["scar"]["qc"].get(k) for r in rows if r["motion"] == "nonrigid" and r["blood"] == b]
            res[f"phase_vs_nonrigid_{b}"] = auc([x for x in ph if x is not None], [x for x in nr if x is not None])
        out["qc_auc"][k] = res
    out["taus"] = {f"{k[0]}|{k[1]}|{k[2]}|{k[3]}": round(v, 3) for k, v in sorted(taus.items())}
    out["qc_cuts"] = {f"{k[0]}|{k[1]}|{k[2]}": {q: round(x, 4) for q, x in v.items()} for k, v in sorted(cuts.items())}
    (HERE / "scores.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    o = main(*(sys.argv[1:2] or []))
    print("cases", o["n_cases"], "hearts", len(o["hearts"]), "skipped", [(s["heart"], s["skip"]) for s in o["skipped"]])
    for r in o["registration"]:
        print(r["motion"], {a: (r[f"{a}_tre_median"], r[f"{a}_tre_p90"]) for a in ("R0", "rigid", "affine", "rigid_m4", "chain", "chain_m4")},
              r["chain_stages"], "affine<rigid QC", r["affine_lowers_qc_share"])
    for x in o["presence"]:
        if x["arm"] in ("chain", "oracle") and x["motion"] in ("none", "rigid", "phase"):
            print("P", x["arm"], x["blood"], x["cnr"], x["motion"], x["rule"], x["sens"], x["spec"],
                  x["spec_scarfree_hearts"], x["spill_share"], x["spill_twin"], x["n_scarred"])
    print(json.dumps(o["strike"], indent=1))
    print(json.dumps(o["qc_auc"], indent=1))
