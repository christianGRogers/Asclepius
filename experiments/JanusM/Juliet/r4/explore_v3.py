"""Juliet R4 E12, exploratory (NOT pre-registered; written after reading scores_v3_juliet.json): three questions that
the pre-registered scoring raised, on the same rows (results_v3_juliet.jsonl.gz).

1. Cut source. The pre-registered cuts are the p95 of R0 QC on perfectly aligned cases ('none'). With them, the rigid
   stage fails QC on every moved case and rim_dark's phase flag fires on 63/63 'rigid' cases. JA53's development cuts
   are the p95 over *reader-passed* (registered) patients. Surrogate: p95 of the final shipped-stage QC on 'rigid'
   motion cases whose rigid TRE < 1 mm (no phase change, registration good), other half of hearts, per blood.
   rim_dark's phase cut: the same p95 (phase-matched by construction).
2. The step-5 fallback. As shipped, rigid10 replaces the result if it passes QC *or lowers the normalised maximum*.
   Variants: 'pass' (replace only if it passes QC); 'off' (no fallback).
3. Rule (c)'s |log det| threshold: 0.02 (pre-registered), 0.03 (Kilo's reading), 0.05.

Output: explore_v3.json: chain-final TRE (median / p90) per motion, final-stage counts, phase-flag rates, and
P-G / P-J strike verdicts (score.strike_on) for each cut source x fallback x rule.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments/JanusM/bench_lie"))
sys.path.insert(0, str(HERE))
import score as S3  # noqa: E402
import score_v3_juliet as V  # noqa: E402
from janusm.scar import registration as REG  # noqa: E402


def registered_cuts(rows):
    acc = defaultdict(list)
    for r in rows:
        if r["motion"] == "rigid" and r["arms"]["rigid"]["tre_mm"] < 1.0:
            acc[(S3.half(r["heart"]), r["blood"])].append(V.qobj(r["arms"]["rigid"]).values())
    out = {}
    for (h, b), v in acc.items():
        p = [float(np.nanpercentile(np.array(v)[:, k], 95)) for k in range(4)]
        out[(1 - h, b)] = REG.QCCuts(max_fatlike=p[0], max_bloodlike=p[1], max_brighter_than_blood=p[2],
                                     max_rim_dark=p[3])
    return out


def accept(rule, A, cut):
    if rule.startswith("c"):
        thr = {"c": 0.02, "c03": 0.03, "c05": 0.05}[rule]
        san = A["affine"]["sanity"]
        if not san["ok"]:
            return False
        ld = san["log_det"]
        if ld is not None and np.isfinite(ld) and abs(ld) >= thr:
            return True
        return REG.qc_rule_accepts(V.qobj(A["affine"]), V.qobj(A["rigid"]), cut)
    return V.accept(rule, A["affine"], V.qobj(A["affine"]), V.qobj(A["rigid"]), cut)


def replay(r, cut, rule, fallback):
    A = r["arms"]
    q = {s: V.qobj(A[s]) for s in V.STAGES}
    final = "R0"
    if not q["R0"].passes(cut):
        final = "rigid"
        if not q["rigid"].passes(cut) and accept(rule, A, cut):
            final = "affine"
        if not q[final].passes(cut) and fallback != "off":
            m_new, m_old = REG.normalised_max(q["rigid10"], cut), REG.normalised_max(q[final], cut)
            lowers = np.isfinite(m_new) and np.isfinite(m_old) and m_new < m_old
            if q["rigid10"].passes(cut) or (fallback == "shipped" and lowers):
                final = "rigid10"
    rec = A[final]
    con = rec["contrast"]
    ev = con is not None and np.isfinite(con) and con >= REG.MIN_PHASE_CONTRAST_SD
    rd, off = rec["qc"]["rim_dark"], rec["edge_offset_mm"]
    flags = []
    if ev and rd is not None and rd > cut.rim_dark_phase:
        flags.append("rim_dark")
    if ev and off is not None and abs(off) > cut.max_edge_offset_mm:
        flags.append("edge_offset")
    return final, flags


def main():
    rows, _ = V.load(HERE / "results_v3_juliet.jsonl.gz")
    cutsets = {"aligned_R0 (pre-registered)": V.fit_cuts(rows), "registered (JA53 surrogate)": registered_cuts(rows)}
    taus = None
    res = []
    for cname, cuts in cutsets.items():
        for fb in ("shipped", "pass", "off"):
            for rule in ("L", "b", "c", "c03", "c05", "S", "N"):
                arm = f"x|{cname}|{fb}|{rule}"
                summ = {"cuts": cname, "fallback": fb, "rule": rule, "motions": {}}
                for r in rows:
                    final, flags = replay(r, cuts[(S3.half(r["heart"]), r["blood"])], rule, fb)
                    r["arms"][arm] = r["arms"][final]
                    r.setdefault("_x", {})[arm] = (final, flags)
                for m in V.MOTIONS:
                    rr = [r for r in rows if r["motion"] == m]
                    t = [r["arms"][arm]["tre_mm"] for r in rr]
                    fl = [r["_x"][arm][1] for r in rr]
                    summ["motions"][m] = {"tre_median": V.pct(t, 50), "tre_p90": V.pct(t, 90),
                                          "final": {s: sum(r["_x"][arm][0] == s for r in rr) for s in V.STAGES},
                                          "flag_rim_dark": sum("rim_dark" in f for f in fl),
                                          "flag_edge": sum("edge_offset" in f for f in fl),
                                          "flag_any": sum(bool(f) for f in fl), "n": len(rr)}
                res.append(summ)
    # strike verdicts for every variant (taus refitted per arm, as pre-registered for the shipped arm)
    arms = sorted({a for r in rows for a in r["arms"] if a.startswith("x|")})
    taus = S3.fit_taus(rows)
    out = {"presence": [], "extent": []}
    V.score_groups(rows, arms, taus, out)
    for s in res:
        arm = f"x|{s['cuts']}|{s['fallback']}|{s['rule']}"
        st = S3.strike_on(out, arm)
        s["strike"] = {p: st[p]["struck"] for p in ("P-J", "P-G")}
        s["min_sens"] = {p: st[p]["min_sens"] for p in ("P-J", "P-G")}
        s["nonrigid_spec"] = {x["rule"] + "|" + x["blood"]: x["spec"] for x in out["presence"]
                              if x["arm"] == arm and x["motion"] == "nonrigid" and x["rule"] in ("P-J", "P-G")}
    cuts_json = {c: {f"{h}|{b}": dict(zip(V.QCN, np.round(k.values(), 4).tolist())) for (h, b), k in cs.items()}
                 for c, cs in cutsets.items()}
    (HERE / "explore_v3.json").write_text(json.dumps({"note": "exploratory, not pre-registered", "cuts": cuts_json,
                                                      "variants": res}, indent=1) + "\n")
    for s in res:
        mm = s["motions"]
        print(s["cuts"][:10], s["fallback"], s["rule"], {m: (mm[m]["tre_median"], mm[m]["tre_p90"]) for m in
              ("none", "rigid", "scale", "aniso6", "phase", "phase_neg", "nonrigid")},
              "flags rigid/none/phase/phase_neg", mm["rigid"]["flag_any"], mm["none"]["flag_any"],
              mm["phase"]["flag_any"], mm["phase_neg"]["flag_any"], s["strike"], s["min_sens"])


if __name__ == "__main__" and (len(sys.argv) == 1 or sys.argv[1] != "phase-first"):
    main()


def phase_first(rows, cuts):
    """Variant 4 (exploratory): JA52's phase step is read on the 4 mm result *before* step 5. A patient flagged there
    is phase suspect and is not re-registered, so the 10 mm fallback does not run (JA52: registration cannot fix
    phase). Rule L, fallback as shipped otherwise."""
    out = {}
    for m in V.MOTIONS:
        t, fl = [], 0
        for r in [r for r in rows if r["motion"] == m]:
            cut = cuts[(S3.half(r["heart"]), r["blood"])]
            A = r["arms"]
            q = {s: V.qobj(A[s]) for s in V.STAGES}
            final = "R0"
            if not q["R0"].passes(cut):
                final = "rigid"
                if not q["rigid"].passes(cut) and accept("L", A, cut):
                    final = "affine"
                rec = A[final]
                con, rd, off = rec["contrast"], rec["qc"]["rim_dark"], rec["edge_offset_mm"]
                ev = con is not None and con >= REG.MIN_PHASE_CONTRAST_SD
                flagged = ev and ((rd is not None and rd > cut.rim_dark_phase) or
                                  (off is not None and abs(off) > cut.max_edge_offset_mm))
                if not flagged and not q[final].passes(cut):
                    m_new, m_old = REG.normalised_max(q["rigid10"], cut), REG.normalised_max(q[final], cut)
                    if q["rigid10"].passes(cut) or (np.isfinite(m_new) and np.isfinite(m_old) and m_new < m_old):
                        final = "rigid10"
                fl += bool(flagged)
            t.append(A[final]["tre_mm"])
        out[m] = {"tre_median": V.pct(t, 50), "tre_p90": V.pct(t, 90), "flagged_before_fallback": fl}
    return out


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "phase-first":
    rows, _ = V.load(HERE / "results_v3_juliet.jsonl.gz")
    res = {c: phase_first(rows, cs) for c, cs in (("aligned_R0", V.fit_cuts(rows)), ("registered", registered_cuts(rows)))}
    d = json.loads((HERE / "explore_v3.json").read_text())
    d["phase_first_then_fallback"] = res
    (HERE / "explore_v3.json").write_text(json.dumps(d, indent=1) + "\n")
    print(json.dumps(res, indent=0))
