"""PS4-S3 offline report (Round 4 - paired-scar §9; report only): JA81's rule (g) on Kilo's K1 phantom seeds.

Reads the committed ``experiments/JanusM/Kilo/r4/k1_phantom_rules.json`` (Kilo's run of the shipped optimiser on the
PS3-S3 static-chest phantom, every stage forced, with the test's tight cuts; the default optimiser is unchanged by
PS4, so the rows still stand) and applies rule (g) as ``registration.affine_accepted`` states it, on the logged values:
sane, and max(affine normalised QC) <= max(rigid normalised QC), and (affine passes QC, i.e. every normalised value
<= 1, or |log det| >= ``AFFINE_SCALE_LOG_DET``). Counts how many of the 9 correct scale fixes (3 % up, 3 % down,
6 % uniaxial; 3 seeds each; affine TRE below rigid's) are kept, and how many worse affines on the 4 mm shift are.

Phantom rows only: nothing is downloaded, no case is opened. Usage: python experiments/JanusM/bench_lie/ps4_s3_k1_rule_g.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from janusm.scar import registration as R  # noqa: E402

K1 = ROOT / "experiments/JanusM/Kilo/r4/k1_phantom_rules.json"


def rule_g(row):
    an, rn = row["affine_norm"], row["rigid_norm"]
    passes = all(v <= 1.0 for v in an)
    return bool(row["sanity_ok"] and max(an) <= max(rn)
                and (passes or abs(row["log_det"]) >= R.AFFINE_SCALE_LOG_DET))


def main():
    d = json.loads(K1.read_text())
    rows = []
    for r in d["rows"]:
        rows.append({k: r[k] for k in ("motion", "seed", "tre_rigid", "tre_affine", "log_det", "sanity_ok")}
                    | {"g": rule_g(r), "ja51": r["ja51"], "b": r["b"]})
    fixes = [r for r in rows if r["motion"] != "shift_4mm" and r["tre_affine"] < r["tre_rigid"]]
    worse = [r for r in rows if r["motion"] == "shift_4mm" and r["tre_affine"] > r["tre_rigid"]]
    out = {"ruling": "Round 4 - paired-scar, PS4-S3 (offline, report only)", "source": str(K1.relative_to(ROOT)),
           "rule": "JA81 (g)", "affine_scale_log_det": R.AFFINE_SCALE_LOG_DET, "rows": rows,
           "summary": {"correct_scale_fixes": len(fixes),
                       "kept_g": sum(r["g"] for r in fixes), "kept_b": sum(r["b"] for r in fixes),
                       "kept_ja51": sum(r["ja51"] for r in fixes),
                       "shift_worse_affines": len(worse), "shift_worse_kept_g": sum(r["g"] for r in worse),
                       "by_motion": {m: f"{sum(r['g'] for r in fixes if r['motion'] == m)}/"
                                        f"{sum(1 for r in fixes if r['motion'] == m)}"
                                     for m in ("scale_+3", "scale_-3", "uniaxial_+6")}}}
    (HERE / "ps4_s3_k1_rule_g.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    print(json.dumps(main()["summary"], indent=1))
