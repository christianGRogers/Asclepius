"""Merge run_v3's per-heart part files into results_v3.jsonl.gz (the committed record).

Usage: python experiments/JanusM/bench_lie/merge_v3.py <parts_dir>
"""
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = []
for f in sorted(Path(sys.argv[1]).glob("*.jsonl")):
    rows += [json.loads(line) for line in open(f)]
rows.sort(key=lambda r: (r["heart"], r.get("blood", ""), r.get("cnr", 0), r.get("motion", "")))
with gzip.open(HERE / "results_v3.jsonl.gz", "wt") as fh:
    for r in rows:
        fh.write(json.dumps(r) + "\n")
print(len(rows), "rows")
