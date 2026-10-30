"""Golf R4 E12 summary: JA57's planning table from power_r4.json.

N80 is read three ways, all from the committed curves (no new simulation):
  grid    `seal_size`'s rule: the smallest grid N from which power stays >= 0.80 (step 20);
  interp  the first upward crossing of 0.80, linear between the two grid points that bracket it;
  band    the interp N80 recomputed with every grid power moved by -2 / +2 Monte-Carlo SE (sqrt(p(1-p)/sims)),
          i.e. how far N80 can move from simulation noise alone.
The seal is JA57's: max(120; N for >= 270 scarred segments; N80 of claim 1), capped at 240; reported for the grid
and the interpolated N80.

Usage: python experiments/JanusM/Golf/r4/power_r4_table.py  (writes power_r4_table.json, prints a table)
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOOR, CAP, TARGET = 120, 240, 0.80


def interp_n80(curve, shift=0.0, sims=None):
    ns = sorted(int(k) for k in curve)
    p = []
    for n in ns:
        v = curve[str(n)]
        se = math.sqrt(max(v * (1 - v), 1e-9) / sims) if sims else 0.0
        p.append(v + shift * se)
    if p[0] >= TARGET:
        return float(ns[0])  # at or below the grid's first point
    for i in range(1, len(ns)):
        if p[i] >= TARGET and p[i - 1] < TARGET:
            return ns[i - 1] + (TARGET - p[i - 1]) / (p[i] - p[i - 1]) * (ns[i] - ns[i - 1])
    return None


def seal(n80, n_seg):
    if n80 is None:
        return CAP
    return int(min(max(FLOOR, n_seg, math.ceil(n80)), CAP))


def main():
    d = json.loads((HERE / "power_r4.json").read_text())
    sims = d["settings"]["sims"]
    rows = []
    for c in d["cells"]:
        cur = c["power_claim1"]
        n80 = interp_n80(cur)
        lo, hi = interp_n80(cur, +2, sims), interp_n80(cur, -2, sims)
        rows.append({k: c[k] for k in ("clustering", "enrich", "p_fail", "infarct_size", "n_segments_270")} | {
            "power_at_160": cur.get("160"), "power_at_200": cur.get("200"), "power_at_240": cur.get("240"),
            "max_power_grid": max(cur.values()),
            "n80_grid": c["claim1"]["grid_n80"], "n80_interp": None if n80 is None else round(n80, 1),
            "n80_mc_band": [None if lo is None else round(lo, 1), None if hi is None else round(hi, 1)],
            "seal_grid": seal(c["claim1"]["grid_n80"], c["n_segments_270"]),
            "seal_interp": seal(n80, c["n_segments_270"]),
            "claim2_joint_n80_interp": (lambda x: None if x is None else round(x, 1))(
                interp_n80(c["power_claim2_joint"])),
            "binding": ("cap" if (n80 is None or max(n80, c["n_segments_270"]) > CAP) else
                        "power" if n80 >= max(FLOOR, c["n_segments_270"]) else
                        "segments" if c["n_segments_270"] >= FLOOR else "floor")})
    out = {"source": "power_r4.json", "sims": sims, "rows": rows,
           "reproductions": d["reproductions"]}
    (HERE / "power_r4_table.json").write_text(json.dumps(out, indent=1) + "\n")
    for r in rows:
        print(r["clustering"], r["enrich"], r["p_fail"], r["infarct_size"], "P160", r["power_at_160"], "P200",
              r["power_at_200"], "P240", r["power_at_240"], "N80 grid", r["n80_grid"], "interp", r["n80_interp"],
              r["n80_mc_band"], "seg", r["n_segments_270"], "seal", r["seal_grid"], r["seal_interp"], r["binding"],
              "joint", r["claim2_joint_n80_interp"])
    print(json.dumps(d["reproductions"], indent=1))


if __name__ == "__main__":
    main()
