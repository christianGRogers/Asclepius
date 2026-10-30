"""Kilo R4: score the CANONICAL benchmark-v3 rows (Golf's ``bench_lie/results_v3.jsonl.gz``, #251) under Kilo's
pre-registered rules, with the same code as Kilo's replication (score_shipped.py).

Golf's rows log the same shipped stages under other names: R0, rigid4, affine4, rigid10, each with ``shipped`` (the
four shipped QC values, contrast, affine sanity ``sane`` / ``log_det``, the JA52 edge offset) and ``tre_mm``. This maps
them to score_shipped's format (rigid4 -> rigid, affine4 -> affine) and scores CNR 5. Golf's ``aniso`` (3 / 3 / 6 %)
stands in for aniso3 / aniso6 in the item 2 choice, as pre-registered on #251 (Kilo, Juliet). Golf's B-spline starts
from rigid4 (Kilo's from the as-shipped final stage); it is reported only.

Usage: PYTHONPATH=src python experiments/JanusM/Kilo/r4/golf_rows.py <golf results_v3.jsonl[.gz]> [out.json]
"""
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_shipped as K  # noqa: E402

NAMES = {"R0": "R0", "rigid4": "rigid", "affine4": "affine", "rigid10": "rigid10"}


def convert(r):
    if "skip" in r:
        return r
    out = {k: v for k, v in r.items() if k != "arms"}
    out["arms"], out["stages"] = {}, {}
    for g, k in NAMES.items():
        a = r["arms"][g]
        s = a["shipped"]
        out["stages"][k] = {"qc": {q: s[q] for q in K.QN} | {"contrast": s["contrast"]}, "tre_mm": a["tre_mm"],
                            "edge_offset_mm": s["edge_offset_mm"],
                            "sanity": {"ok": s["sane"], "log_det": s["log_det"]}}
        out["arms"][k] = a
    for k in ("oracle", "bspline"):
        if k in r["arms"]:
            out["arms"][k] = r["arms"][k]
    if "bspline" in r["arms"]:
        out["bspline"] = {"from": "rigid", "tre_mm": r["arms"]["bspline"].get("tre_mm")}
    return out


def main(path, out_path=HERE / "scores_kilo_on_golf_v3.json"):
    op = gzip.open if str(path).endswith(".gz") else open
    rows = [convert(json.loads(line)) for line in op(path, "rt")]
    return K.main(rows=rows, out_path=out_path, choice_motions=K.CHOICE_MOTIONS_GOLF,
                  source=f"Golf's canonical v3 rows ({Path(path).name}), mapped by golf_rows.py")


if __name__ == "__main__":
    o = main(*sys.argv[1:3])
    print("cases", o["n_cases"], {k: v["struck"] for k, v in o["strike"].items() if isinstance(v, dict)})
    print("choice", o["item2"]["choice_prov"], o["item2"]["choice_fit"])
