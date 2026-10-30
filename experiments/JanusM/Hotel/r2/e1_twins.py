"""Hotel R2 E1: the JA12 twin rule on the public TotalSegmentator meta.csv files (v1 Zenodo 6802614 and
v2.0.1 Zenodo 10047292), and which Round 1 Janus-M results used a refused subject.

Reads metadata only (the two meta.csv files); no image is downloaded or opened.

    python experiments/JanusM/Hotel/r2/e1_twins.py V1_META V2_META OUT.json
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import guard_r2 as g  # noqa: E402

CARDIAC = {"ct heart", "ct heart-thorakale aorta", "ct aortic valve", "ct coronary arteries", "ct left artrium"}
R1_FILES = {  # the per-case result file of each Round 1 advocate's TotalSegmentator experiment
    "Golf": ["experiments/JanusM/Golf/ts_cases.json"],
    "Hotel": ["experiments/JanusM/Hotel/e1_ts_cardiac_results.json"],
    "India": ["experiments/JanusM/India/results/summary.json"],
    "Juliet": ["experiments/JanusM/Juliet/real_labels.json"],
    "Kilo": ["experiments/JanusM/Kilo/results_e123_grid05.json"],
}


def main(v1, v2, out):
    G = g.Guard()
    held = G.ts_ids
    m1, m2 = g.read_meta(v1), g.read_meta(v2)
    t1, t2 = g.twins(v1, held), g.twins(v2, held)
    union = set(t1) | set(t2)
    exact = {}
    for h in sorted(held):
        for s, r in m1.items():
            if s != h and s not in held and all(r[k] == m1[h][k] for k in ("gender", "institute", "study_type", "age")):
                exact[s] = h
    card = {s for s, r in m1.items() if r["study_type"].strip().lower() in CARDIAC}
    res = {
        "rule": "twin = same sex and institute as a held-out TotalSegmentator subject, |age diff| <= 5 y, any study "
                "type; blank field matches anything; applied to v1 and v2.0.1 meta.csv, union refused",
        "held_out_ids": len(held),
        "held_out_category": {h: G.pool_reason("TotalSegmentator-cardiac__" + h) for h in sorted(held)},
        "held_out_institutes_v1": sorted({m1[h]["institute"] for h in held}),
        "subjects_v1": len(m1), "subjects_v2": len(m2),
        "twins_v1": len(t1), "twins_v2": len(t2), "twins_union": len(union),
        "cardiac_v1": len(card), "cardiac_held_out": len(card & held),
        "cardiac_twins_union": len(card & union), "cardiac_left": sorted(card - held - union),
        "exact_match_age_sex_institute_studytype": exact,
        "round1_use": {},
    }
    root = g.ROOT
    for a, fs in R1_FILES.items():
        ids = set()
        for f in fs:
            ids |= set(re.findall(r"s\d{4}", (root / f).read_text()))
        res["round1_use"][a] = {"ids_in_file": len(ids), "held_out": sorted(ids & held),
                                "exact_matches": {i: exact[i] for i in sorted(ids) if i in exact},
                                "twins_union": len(ids & union)}
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k not in ("cardiac_left", "held_out_category")}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
