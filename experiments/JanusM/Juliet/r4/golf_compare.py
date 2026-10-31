"""Juliet R4 E12 against the canonical v3 (Golf's `bench_lie/results_v3.jsonl.gz`, #251).

1. Determinism: on the motions both runs share with the same seed string (none, rigid, scale, phase, nonrigid; CNR
   5), match cases by (heart, blood, motion) and compare per stage (R0, rigid 4 mm, affine 4 mm, rigid10): the seed,
   TRE, the four shipped QC values, the edge offset, and menu.grade's per-segment ev / ed / pg_share (scarred image).
2. My pre-registered scorer (score_v3_juliet.py, rules as posted on #251) applied to Golf's rows, with the mapping
   pre-registered there: his `aniso` replaces my `aniso3` / `aniso6` in the item-2 choice. Only CNR 5 rows are used.
   His rows lack the `free_fixed` twin (used only for the reported spill_twin), so spill_twin is not reported here;
   the striking spill (blood set to remote) is present.

No image is read: both inputs are committed JSON. Usage:
  git show origin/exp/jm-r4-paired-scar-golf:experiments/JanusM/bench_lie/results_v3.jsonl.gz > /tmp/golf.jsonl.gz
  PYTHONPATH=src python experiments/JanusM/Juliet/r4/golf_compare.py /tmp/golf.jsonl.gz
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments/JanusM/bench_lie"))
sys.path.insert(0, str(HERE))
import score as S3  # noqa: E402
import score_v3_juliet as V  # noqa: E402

STAGE = {"R0": "R0", "rigid4": "rigid", "affine4": "affine", "rigid10": "rigid10", "oracle": "oracle"}
SHARED = ("none", "rigid", "scale", "phase", "nonrigid")


def adapt(r):
    """Golf's row -> the fields score_v3_juliet reads."""
    out = {k: r[k] for k in ("heart", "blood", "cnr", "motion", "seed", "truth_vol", "truth_depth", "T_nominal")}
    out["arms"] = {}
    for g, mine in STAGE.items():
        if g not in r["arms"]:
            continue
        a = r["arms"][g]
        sh = a.get("shipped") or {}
        rec = {"scar": a["scar"], "free_own": a["free_own"], "noblood": a["noblood"],
               "free_fixed": a.get("free_fixed", a["free_own"]),
               "qc": {n: sh.get(n) for n in V.QCN}, "contrast": sh.get("contrast"),
               "edge_offset_mm": sh.get("edge_offset_mm"), "tre_mm": a.get("tre_mm")}
        if mine == "affine":
            rec["sanity"] = {"ok": bool(sh.get("sane")), "log_det": sh.get("log_det")}
        if mine == "oracle":
            sm = a["scar"].get("qc", {})
            rec["qc"] = {"fatlike": sm.get("fat_like"), "bloodlike": sm.get("blood_like"),
                         "brighter_than_blood": sm.get("above_blood"), "rim_dark": sm.get("rim_dark")}
        out["arms"][mine] = rec
    return out


def diff(a, b):
    a, b = np.array([np.nan if x is None else x for x in a], float), np.array([np.nan if x is None else x for x in b], float)
    m = np.isfinite(a) & np.isfinite(b)
    return float(np.abs(a[m] - b[m]).max()) if m.any() else 0.0


def main():
    golf = [json.loads(line) for line in gzip.open(sys.argv[1], "rt")]
    golf = [r for r in golf if "arms" in r and r.get("cnr") == 5]
    mine, _ = V.load(HERE / "results_v3_juliet.jsonl.gz")
    by = {(r["heart"], r["blood"], r["motion"]): r for r in mine}
    cmp = {"n_matched": 0, "seed_equal": 0, "per_stage": {}}
    worst = []
    for g in golf:
        if g["motion"] not in SHARED:
            continue
        m = by.get((g["heart"], g["blood"], g["motion"]))
        if m is None:
            continue
        cmp["n_matched"] += 1
        cmp["seed_equal"] += int(g["seed"] == m["seed"])
        ga = adapt(g)
        for st in ("R0", "rigid", "affine", "rigid10"):
            d = cmp["per_stage"].setdefault(st, {"tre": [], "qc": [], "edge": [], "menu": []})
            x, y = ga["arms"][st], m["arms"][st]
            d["tre"].append(abs((x["tre_mm"] or 0) - (y["tre_mm"] or 0)))
            d["qc"].append(max(abs((x["qc"][n] or 0) - (y["qc"][n] or 0)) for n in V.QCN))
            if x["edge_offset_mm"] is not None and y["edge_offset_mm"] is not None:
                d["edge"].append(abs(x["edge_offset_mm"] - y["edge_offset_mm"]))
            d["menu"].append(max(diff(x["scar"][k], y["scar"][k]) for k in ("ev", "ed", "pg_share")))
            if d["tre"][-1] > 0.05:
                worst.append((g["heart"], g["blood"], g["motion"], st, x["tre_mm"], y["tre_mm"]))
    for st, d in cmp["per_stage"].items():
        cmp["per_stage"][st] = {k: {"identical_share": round(float(np.mean(np.array(v) < 1e-3)), 3),
                                    "max_abs": round(float(np.max(v)), 4), "p95_abs": round(float(np.percentile(v, 95)), 4)}
                                for k, v in d.items() if v}
    cmp["tre_differs_by_more_than_0.05mm"] = len(worst)
    cmp["examples"] = worst[:10]
    # my pre-registered scorer on Golf's rows
    rows = [adapt(g) for g in golf]
    V.CHOICE_MOTIONS = ("rigid", "scale", "aniso")          # the mapping pre-registered on #251
    V.MOTIONS = ("none", "rigid", "scale", "aniso", "phase", "phase_neg", "nonrigid")
    tmp = HERE / "_golf_rows.jsonl.gz"
    with gzip.open(tmp, "wt") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    try:
        s = V.main(tmp, HERE / "scores_on_golf_rows.json")
    finally:
        tmp.unlink()
    out = {"note": "Juliet's replication vs the canonical v3 (Golf); Juliet's pre-registered scorer on Golf's rows",
           "determinism": cmp,
           "on_golf_rows": {"strike": {p: {k: s["strike"][p][k] for k in ("struck", "min_sens", "why")}
                                       for p in ("P-K", "P-J", "P-G")},
                            "affine_rule_choice": s["affine_rule_choice"],
                            "registration": s["registration"], "phase_auc": s["phase_auc"],
                            "n_cases": s["n_cases"]}}
    (HERE / "golf_compare.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["determinism"], indent=1))
    print(json.dumps(out["on_golf_rows"]["strike"], indent=1))
    print(json.dumps(out["on_golf_rows"]["affine_rule_choice"], indent=1))
    for r in s["registration"]:
        print(r["motion"], {a: (r.get(f"{a}_tre_median"), r.get(f"{a}_tre_p90")) for a in
                            ("rigid", "affine", "rigid10", "shipped")}, r["shipped_final"])


if __name__ == "__main__":
    main()
