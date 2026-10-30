"""Summarise E8 (e8_qc_phase.py): null QC distributions, what each QC value flags, the edge offset against truth,
and grading by condition. Heart-cluster bootstrap CIs. No image is read here.

P-K* (Kilo v3 proposal) = P-K with a floor: a segment is present only if >= 5 % of its voxels exceed
max(FWHM threshold, remote + 3 SD). The thresholds are nested, so this is exactly "P-K and E-V >= 0.05".

Usage: python e8_summarise.py E8_RAW.json OUT_SUMMARY.json
"""
import json, sys

import numpy as np

KIM = np.array([0.25, 0.50, 0.75])
QC = ("q_fat", "q_blood", "q_bright", "edge_offset_remote", "edge_iqr")


def kbin(f, present):
    return np.where(present, np.digitize(np.clip(f, 1e-9, 1), KIM) + 1, 0)


def rows_of(d):
    out = []
    for c in d["cases"]:
        for r in c.get("rows", []):
            if r.get("fail"):
                continue
            r = dict(r, case=c["case"])
            es = [x for x in r["edge_offset_seg"] if x is not None]
            r["edge_iqr"] = float(np.subtract(*np.percentile(es, [75, 25]))) if len(es) >= 8 else np.nan
            if r["edge_offset_remote"] is None:
                r["edge_offset_remote"] = np.nan
            out.append(r)
    return out


def pick(rows, **kw):
    return [r for r in rows if all(r[k] == v if not isinstance(v, (tuple, list)) else r[k] in v for k, v in kw.items())]


def pct(v, q):
    v = np.array(v, float); v = v[np.isfinite(v)]
    return [round(float(x), 3) for x in np.percentile(v, q)] if len(v) else None


def cluster_boot(rows, stat, nb=1000, seed=7):
    cases = sorted({r["case"] for r in rows})
    by = {c: [r for r in rows if r["case"] == c] for c in cases}
    rng = np.random.default_rng(seed)
    pt = stat(rows)
    bs = []
    for _ in range(nb):
        rr = [r for c in rng.choice(cases, len(cases)) for r in by[c]]
        bs.append(stat(rr))
    bs = np.array(bs, float)
    return [round(float(pt), 3)] + [round(float(x), 3) for x in np.nanpercentile(bs, [2.5, 97.5])]


def presence(r, rule):
    pk, pg, ev = np.array(r["pk"]), np.array(r["pg"]), np.nan_to_num(np.array(r["ev"], float))
    return {"P-K": pk > 0, "P-G": pg > 0, "P-K*": (pk > 0) & (ev >= 0.05)}[rule]


def counts(rows, rule):
    tp = fn = tn = fp = agree = both = 0
    for r in rows:
        tf = np.array(r["truth_frac"]); pos = tf > 0
        p = presence(r, rule)
        tp += int((p & pos).sum()); fn += int((~p & pos).sum()); tn += int((~p & ~pos).sum()); fp += int((p & ~pos).sum())
        b_ct = kbin(np.nan_to_num(np.array(r["ev"], float)), p); b_t = kbin(tf, pos)
        bb = pos & p
        agree += int((b_ct[bb] == b_t[bb]).sum()); both += int(bb.sum())
    return tp, fn, tn, fp, agree, both


def sens(rows, rule):
    tp, fn, *_ = counts(rows, rule); return tp / max(tp + fn, 1)


def spec(rows, rule):
    _, _, tn, fp, _, _ = counts(rows, rule); return tn / max(tn + fp, 1)


def tbin(rows, rule):
    *_, a, b = counts(rows, rule); return a / max(b, 1)


def main():
    d = json.load(open(sys.argv[1]))
    rows = rows_of(d)
    S = {"n_hearts": len({r["case"] for r in rows}), "n_rows": len(rows)}
    # A. null QC: phase-matched, (i) aligned and unmoved, (ii) E5 motion after masked rigid; scarred hearts
    nullA = pick(rows, phase=0.0, motion="none", reg="R0", scarred=True)
    nullB = pick(rows, phase=0.0, motion="e5", reg="R3", scarred=True)
    S["null_qc"] = {}
    for name, nr in (("aligned", nullA), ("e5_after_rigid", nullB)):
        S["null_qc"][name] = {}
        for bl in ("below", "equal", "above"):
            rr = pick(nr, blood=bl)
            S["null_qc"][name][bl] = {q: pct([r[q] for r in rr], [5, 50, 95, 99]) for q in QC}
    # B. what each QC flags, with cuts from the e5-after-rigid null (the development analogue), per blood level
    tests = {"unregistered_e5 (R0)": dict(phase=0.0, motion="e5", reg="R0"),
             "phase +5% (cavity smaller), aligned": dict(phase=0.05, motion="none", reg="R0"),
             "phase -5% (cavity larger), aligned": dict(phase=-0.05, motion="none", reg="R0"),
             "phase +5%, e5 after rigid": dict(phase=0.05, motion="e5", reg="R3"),
             "phase -5%, e5 after rigid": dict(phase=-0.05, motion="e5", reg="R3")}
    S["flag_rates"] = {}
    for bl in ("below", "equal", "above"):
        ref = pick(nullB, blood=bl)
        cuts = {}
        for q in ("q_fat", "q_blood", "q_bright", "edge_iqr"):
            cuts[q] = ("hi", float(np.nanpercentile([r[q] for r in ref], 95)))
        e = np.array([r["edge_offset_remote"] for r in ref], float)
        lo, hi = np.nanpercentile(e, [2.5, 97.5])
        cuts["edge_offset_remote"] = ("two", float(lo), float(hi))
        cuts["edge_abs_0.6mm"] = ("abs", 0.6)
        S["flag_rates"][bl] = {"cuts": {k: [round(x, 3) if isinstance(x, float) else x for x in v] for k, v in cuts.items()}}
        for tname, kw in tests.items():
            rr = pick(rows, blood=bl, scarred=True, **kw)
            fr = {}
            for q, c in cuts.items():
                if c[0] == "hi":
                    v = np.array([r[q] for r in rr], float); fr[q] = float(np.mean(v > c[1]))
                elif c[0] == "two":
                    v = np.array([r["edge_offset_remote"] for r in rr], float); fr[q] = float(np.mean((v < c[1]) | (v > c[2])))
                else:
                    v = np.array([r["edge_offset_remote"] for r in rr], float); fr[q] = float(np.mean(np.abs(v) > c[1]))
            fr["null_false_flag_edge_abs_0.6mm"] = float(np.mean(np.abs(e) > 0.6))
            S["flag_rates"][bl][tname] = {k: round(v, 3) for k, v in fr.items()} | {"n": len(rr)}
    # C. edge offset against the true endocardial error
    ok = [r for r in rows if r["scarred"] and np.isfinite(r["edge_offset_remote"])]
    x = np.array([r["endo_signed_mm"] for r in ok]); y = np.array([r["edge_offset_remote"] for r in ok])
    S["edge_vs_truth"] = {"n": len(ok), "pearson_r": round(float(np.corrcoef(x, y)[0, 1]), 3),
                          "slope": round(float(np.polyfit(x, y, 1)[0]), 3), "intercept": round(float(np.polyfit(x, y, 1)[1]), 3)}
    S["edge_by_phase"] = {}
    for e_ in (-0.05, 0.0, 0.05):
        for mot, reg in (("none", "R0"), ("e5", "R3")):
            rr = pick(rows, phase=e_, motion=mot, reg=reg, scarred=True)
            S["edge_by_phase"][f"{e_:+.2f} {mot} {reg}"] = {
                "true_signed_mm": pct([r["endo_signed_mm"] for r in rr], [50]),
                "edge_offset_p5_p50_p95": pct([r["edge_offset_remote"] for r in rr], [5, 50, 95]),
                "q_blood_p50": pct([r["q_blood"] for r in rr], [50]), "q_bright_p50": pct([r["q_bright"] for r in rr], [50])}
    # D. grading, CNR 5 and 3, by phase and blood level, after masked rigid (motion e5) and aligned
    S["grading"] = {}
    for cnr in (5.0, 3.0):
        for e_ in (0.0, 0.05, -0.05):
            for mot, reg in (("none", "R0"), ("e5", "R3")):
                for bl in ("below", "equal", "above"):
                    sc = pick(rows, cnr=cnr, phase=e_, motion=mot, reg=reg, blood=bl, scarred=True)
                    fr = pick(rows, cnr=cnr, phase=e_, motion=mot, reg=reg, blood=bl, scarred=False)
                    if not sc:
                        continue
                    key = f"cnr{cnr:.0f} phase{e_:+.2f} {mot}/{reg} blood-{bl}"
                    S["grading"][key] = {rule: {"sens": cluster_boot(sc, lambda rr, ru=rule: sens(rr, ru), 300),
                                                "spec_scarred_hearts": round(spec(sc, rule), 3),
                                                "spec_scar_free_hearts": cluster_boot(fr, lambda rr, ru=rule: spec(rr, ru), 300),
                                                "tbin_scar_on_both": round(tbin(sc, rule), 3)}
                                         for rule in ("P-K", "P-K*", "P-G")}
    S["thr_k_sd"] = {"scarred": pct([r["thr_k_sd"] for r in rows if r["scarred"]], [5, 50, 95]),
                     "scar_free": pct([r["thr_k_sd"] for r in rows if not r["scarred"]], [5, 50, 95])}
    json.dump(S, open(sys.argv[2], "w"), indent=1)
    print(json.dumps({k: S[k] for k in ("n_hearts", "n_rows", "edge_vs_truth", "thr_k_sd")}, indent=1))


if __name__ == "__main__":
    main()
