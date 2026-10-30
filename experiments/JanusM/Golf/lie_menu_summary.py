"""Golf R3 E8/E9 summary: reads the per-case JSON of lie_menu.py and writes lie_menu.json.

Two-fold by heart (salted hash), so nothing is chosen on the hearts it is scored on:
  * P-J's tau: p99 of the chord extent T over truth-negative segments of the other fold (scar-free hearts included),
    per (blood, CNR) = "protocol", pooling the chest and static motions (phase5 is a JA27 stratum, not development);
  * QC cuts: each QC value's p95 over the other fold's registrations whose endocardial ASSD <= 1.0 mm (a stand-in
    for the JA29 reader pass; truth is used only to emulate the reader, never by a rule).
The JA29 chain: R0 if it passes QC; else rigid, then affine kept only if it lowers the QC values against rigid
(JA29 step 4); the result is the chain's geometry, scored whether or not it passed (a fail stays in, as the reader
check would catch only part of it; the not-graded rule is reported separately as the QC-fail share).

Presence: P-K pk >= 0.05; P-G pg >= 0.05; P-J ed >= tau.  Extent among called scar-positive segments:
E-V (ev), E-D (ed), E-D3 (ed3), at least bin 1.  Truth presence: volume share > 0.5 %.
Spill share of a presence rule = (sens - sens with blood set to remote) / sens, at the same registration and noise.
Patient-cluster bootstrap over hearts (2000) for sensitivity and specificity.
Usage: python lie_menu_summary.py [<dir of per-case json>]
"""
import hashlib, json, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
EDGES = np.array([0.005, 0.25, 0.50, 0.75])
QC_KEYS = ("qc_fat", "qc_brighter_than_blood", "qc_bloodlike")
TYPICAL = ("chest", "static")


def kim(f):
    return np.digitize(np.asarray(f), EDGES, right=True)


def fold(case):
    return int(hashlib.sha256(("golf-r3-e8:" + case).encode()).hexdigest()[:8], 16) % 2


def load(d):
    cases = {}
    for p in sorted(Path(d).glob("s*.json")):
        o = json.loads(p.read_text())
        if "runs" in o:
            cases[p.stem] = o
    return cases


def qcv(r):
    q = r["scar_qc"]
    return np.array([q[k] if q[k] == q[k] else 0.0 for k in QC_KEYS])


def cuts_from(rows):
    good = np.array([qcv(r) for r in rows if r["geom"] in ("rigid", "affine", "R0") and r["assd_endo"] <= 1.0])
    return np.percentile(good, 95, axis=0) if len(good) else np.full(len(QC_KEYS), np.inf)


def chain(runs_by_geom, cut):
    passes = lambda r: bool(np.all(qcv(r) <= cut))
    r0 = runs_by_geom["R0"]
    if passes(r0):
        return r0, True, "R0"
    rig, aff = runs_by_geom["rigid"], runs_by_geom["affine"]
    pick = aff if np.all(qcv(aff) <= qcv(rig)) else rig
    return pick, passes(pick), "affine" if pick is aff else "rigid"


def segtable(case, r, truth, tau):
    """Per-segment rows: (case, truth vol, truth depth, calls...) for one run."""
    tv, td = np.array(truth["vol"]), np.array(truth["depth"])
    out = []
    for var, pos_ok in (("scar", True), ("noscar", False), ("scar_nb", True), ("noscar_nb", False)):
        g = {k: np.array(v) for k, v in r[var].items()}
        t_v = tv if pos_ok else np.zeros(17)
        t_d = td if pos_ok else np.zeros(17)
        out.append((var, t_v, t_d, {"P-K": g["pk"] >= 0.05, "P-G": g["pg"] >= 0.05, "P-J": g["ed"] >= tau},
                    {"E-V": g["ev"], "E-D": g["ed"], "E-D3": g["ed3"]}, g["ed"]))
    return out


def boot_ci(num, den, rng, nb=2000):
    num, den = np.asarray(num, float), np.asarray(den, float)
    n = len(num)
    W = rng.multinomial(n, np.ones(n) / n, size=nb)
    v = (W @ num) / np.maximum(W @ den, 1)
    return [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)]


def main(d):
    cases = load(d)
    rng = np.random.default_rng(7)
    folds = {c: fold(c) for c in cases}
    allruns = [(c, r) for c, o in cases.items() for r in o["runs"]]
    # QC cuts per fold (from the other fold), per (blood, cnr)
    cut = {}
    for f in (0, 1):
        for blood in ("below", "equal", "above"):
            for cnr in (3.0, 5.0):
                rows = [r for c, r in allruns if folds[c] != f and r["blood"] == blood and r["cnr"] == cnr
                        and r["motion"] in TYPICAL]
                cut[(f, blood, cnr)] = cuts_from(rows)
    # P-J tau per fold, per (blood, cnr, geom)
    tau = {}
    for f in (0, 1):
        for c, r in allruns:
            if folds[c] == f or r["motion"] not in TYPICAL:
                continue
            tv = np.array(cases[c]["truth"][r["motion"]]["vol"])
            key = (f, r["blood"], r["cnr"], r["geom"])
            vals = list(np.array(r["scar"]["ed"])[tv <= 0.005]) + list(r["noscar"]["ed"])
            tau.setdefault(key, []).extend(vals)
    tau = {k: float(np.percentile(v, 99)) for k, v in tau.items()}
    # tau for the chain geometry: the stage the chain chose
    results, qc_rows, e9_rows = [], [], []
    for motion in ("chest", "static", "phase5"):
        for blood in ("below", "equal", "above"):
            for cnr in (3.0, 5.0):
                geoms = ["exact", "R0", "rigid", "affine", "chain"] + (["rigid_nomask"] if motion == "static" else [])
                for gname in geoms:
                    per_case = {}
                    for c, o in cases.items():
                        rr = {r["geom"]: r for r in o["runs"] if r["motion"] == motion and r["blood"] == blood
                              and r["cnr"] == cnr}
                        if not rr:
                            continue
                        f = folds[c]
                        if gname == "chain":
                            r, ok, stage = chain(rr, cut[(f, blood, cnr)])
                            t = tau.get((f, blood, cnr, stage), np.inf)
                            qc_rows.append({"case": c, "motion": motion, "blood": blood, "cnr": cnr, "stage": stage,
                                            "qc_pass": ok, "assd_endo": r["assd_endo"]})
                        else:
                            r = rr[gname]
                            t = tau.get((f, blood, cnr, gname), tau.get((f, blood, cnr, "affine"), np.inf))
                        per_case[c] = (r, segtable(c, r, o["truth"][motion], t))
                    if not per_case:
                        continue
                    row = {"motion": motion, "blood": blood, "cnr": cnr, "geom": gname, "n_hearts": len(per_case),
                           "assd_endo_median": round(float(np.median([v[0]["assd_endo"] for v in per_case.values()])), 3)}
                    for rule in ("P-K", "P-G", "P-J"):
                        tp, P, tn, N, tp_nb, fp, fp_nb = [], [], [], [], [], [], []
                        for c, (r, tabs) in per_case.items():
                            T = {v[0]: v for v in tabs}
                            pos = T["scar"][1] > 0.005
                            tp.append((T["scar"][3][rule] & pos).sum()); P.append(pos.sum())
                            tp_nb.append((T["scar_nb"][3][rule] & pos).sum())
                            neg_calls = np.concatenate([T["scar"][3][rule][~pos], T["noscar"][3][rule]])
                            neg_nb = np.concatenate([T["scar_nb"][3][rule][~pos], T["noscar_nb"][3][rule]])
                            tn.append((~neg_calls).sum()); N.append(len(neg_calls))
                            fp.append(neg_calls.sum()); fp_nb.append(neg_nb.sum())
                        sens = sum(tp) / max(sum(P), 1); sens_nb = sum(tp_nb) / max(sum(P), 1)
                        spec = sum(tn) / max(sum(N), 1)
                        row[rule] = {"sens": round(sens, 3), "sens_ci": boot_ci(tp, P, rng),
                                     "spec": round(spec, 3), "spec_ci": boot_ci(tn, N, rng),
                                     "sens_blood_remote": round(sens_nb, 3),
                                     "spill_share_sens": round((sens - sens_nb) / sens, 3) if sens > 0 else None,
                                     "fp_rate": round(sum(fp) / max(sum(N), 1), 4),
                                     "fp_rate_blood_remote": round(sum(fp_nb) / max(sum(N), 1), 4)}
                    # extent: among truth-positive segments called present by P-G, and by an oracle presence
                    for pres in ("P-G", "oracle"):
                        for ext in ("E-V", "E-D", "E-D3"):
                            agree_v, agree_d, n_both, err_v, err_d = 0, 0, 0, [], []
                            for c, (r, tabs) in per_case.items():
                                T = {v[0]: v for v in tabs}["scar"]
                                pos = T[1] > 0.005
                                called = pos & (T[3]["P-G"] if pres == "P-G" else True)
                                e = T[4][ext][called]
                                b = np.maximum(kim(e), 1)
                                agree_v += (b == kim(T[1][called])).sum(); agree_d += (b == kim(T[2][called])).sum()
                                n_both += called.sum()
                                err_v += list(e - T[1][called]); err_d += list(e - T[2][called])
                            row[f"{ext}|{pres}"] = {
                                "n": int(n_both), "agree_vs_vol": round(agree_v / max(n_both, 1), 3),
                                "agree_vs_depth": round(agree_d / max(n_both, 1), 3),
                                "bias_vs_vol": round(float(np.mean(err_v)), 3) if err_v else None,
                                "sd_vs_vol": round(float(np.std(err_v)), 3) if err_v else None,
                                "bias_vs_depth": round(float(np.mean(err_d)), 3) if err_d else None,
                                "sd_vs_depth": round(float(np.std(err_d)), 3) if err_d else None}
                    results.append(row)
                # E9 rows: truth-free numbers per registration stage
                for c, o in cases.items():
                    for r in o["runs"]:
                        if r["motion"] == motion and r["blood"] == blood and r["cnr"] == cnr:
                            q = r["scar_qc"]
                            e9_rows.append({"case": c, "motion": motion, "blood": blood, "cnr": cnr, "geom": r["geom"],
                                            "off_endo": q["off_endo"], "off_epi": q["off_epi"], "dthick": q["dthick"],
                                            "logdet": r.get("logdet"), "assd_endo": r["assd_endo"],
                                            "noscar_dthick": r["noscar_qc"]["dthick"],
                                            "noscar_off_endo": r["noscar_qc"]["off_endo"]})
    e9 = phase_check(e9_rows)
    qc = qc_summary(qc_rows)
    out = {"n_hearts": len(cases), "folds": folds, "qc_cuts": {f"{k[0]}|{k[1]}|{k[2]}": np.round(v, 4).tolist()
                                                               for k, v in cut.items()},
           "qc_keys": QC_KEYS, "tau_pj": {"|".join(map(str, k)): round(v, 4) for k, v in tau.items()},
           "rows": results, "chain_qc": qc, "e9_phase_check": e9}
    (HERE / "lie_menu.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


def auc(pos, neg):
    pos, neg = np.asarray(pos), np.asarray(neg)
    pos, neg = pos[np.isfinite(pos)], neg[np.isfinite(neg)]
    if not len(pos) or not len(neg):
        return None
    return round(float(((pos[:, None] > neg[None]).mean() + 0.5 * (pos[:, None] == neg[None]).mean())), 3)


def phase_check(rows):
    """E9: can a truth-free number tell a 5 % phase change (phase5) from breath-hold motion (chest, static), after
    each registration stage?  AUC of each statistic (signed so that larger = more phase-like)."""
    out = []
    for geom in ("R0", "rigid", "affine"):
        for blood in ("below", "equal", "above", "all"):
            for cnr in (3.0, 5.0):
                sel = [r for r in rows if r["geom"] == geom and r["cnr"] == cnr and (blood == "all" or r["blood"] == blood)]
                ph = [r for r in sel if r["motion"] == "phase5"]
                no = [r for r in sel if r["motion"] != "phase5"]
                row = {"geom": geom, "blood": blood, "cnr": cnr, "n_phase": len(ph), "n_other": len(no)}
                for k, sgn in (("dthick", 1), ("off_endo", -1), ("noscar_dthick", 1), ("noscar_off_endo", -1)):
                    row["auc_" + k] = auc([sgn * r[k] for r in ph], [sgn * r[k] for r in no])
                    row["median_phase_" + k] = round(float(np.nanmedian([r[k] for r in ph])), 3) if ph else None
                    row["median_other_" + k] = round(float(np.nanmedian([r[k] for r in no])), 3) if no else None
                row["auc_abs_logdet"] = auc([abs(r["logdet"] or 0) for r in ph], [abs(r["logdet"] or 0) for r in no])
                # the transform maps LIE points to first-pass points: a smaller heart on the LIE (the simulated phase
                # change) gives det > 1, so log det > 0 is phase-like
                row["auc_pos_logdet"] = auc([(r["logdet"] or 0) for r in ph], [(r["logdet"] or 0) for r in no])
                if geom == "affine":
                    row["median_phase_logdet"] = round(float(np.median([r["logdet"] for r in ph])), 4) if ph else None
                    row["median_other_logdet"] = round(float(np.median([r["logdet"] for r in no])), 4) if no else None
                out.append(row)
    return out


def qc_summary(rows):
    out = []
    for motion in ("chest", "static", "phase5"):
        for cnr in (3.0, 5.0):
            sel = [r for r in rows if r["motion"] == motion and r["cnr"] == cnr]
            if not sel:
                continue
            good = np.array([r["assd_endo"] <= 1.0 for r in sel]); ok = np.array([r["qc_pass"] for r in sel])
            out.append({"motion": motion, "cnr": cnr, "n": len(sel),
                        "stage_share": {s: round(float(np.mean([r["stage"] == s for r in sel])), 3)
                                        for s in ("R0", "rigid", "affine")},
                        "qc_fail_share": round(float((~ok).mean()), 3),
                        "truly_bad_share": round(float((~good).mean()), 3),
                        "qc_pass_but_bad": int((ok & ~good).sum()), "qc_fail_but_good": int((~ok & good).sum()),
                        "assd_endo_median": round(float(np.median([r["assd_endo"] for r in sel])), 3)})
    return out


if __name__ == "__main__":
    o = main(sys.argv[1] if len(sys.argv) > 1 else "/home/user/golf_e8")
    print("hearts", o["n_hearts"])
    for r in o["rows"]:
        if r["geom"] in ("chain", "exact") and r["cnr"] == 5.0:
            print(r["motion"], r["blood"], r["geom"], {k: (r[k]["sens"], r[k]["spec"], r[k]["spill_share_sens"])
                                                     for k in ("P-K", "P-G", "P-J")})
