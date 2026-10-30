"""Shared synthetic-LIE benchmark (Janus-M Round 3, path jm/paired-scar, ruling section 7 item 1): fetch the hearts.

The hearts are the union of Kilo's 15 (R2 E5) and Golf's 22 (R2 ts_cases_r2.json) public TotalSegmentator v2.0.1
cardiac CTs (CC BY 4.0, Zenodo 10.5281/zenodo.10047292), from the per-case mirror Golf used. The whole list goes
through the shared JA12 guard (janusm.guard.refuse) before the first byte is downloaded, and again per case.
Images stay in <outdir> (outside the repository); nothing is committed or uploaded.

Usage: PYTHONPATH=src python experiments/JanusM/bench_lie/fetch.py <outdir>
"""
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from janusm.guard import refuse  # noqa: E402

MIRROR = "https://huggingface.co/datasets/MedOtter/totalsegmentator-cardiac/resolve/main/{id}/{f}"
FILES = ("ct.nii.gz", "cardiac_label.nii.gz")


def hearts():
    golf = json.loads((ROOT / "experiments/JanusM/Golf/ts_cases_r2.json").read_text())
    kilo = json.loads((ROOT / "experiments/JanusM/Kilo/results_e5_lie_registration.json").read_text())["cases"]
    ids = sorted(set(golf) | {c["case"] for c in kilo})
    refuse(ids, what="shared LIE benchmark heart list", source="TotalSegmentator")   # whole list, first
    return ids


if __name__ == "__main__":
    out = Path(sys.argv[1])
    ids = hearts()
    print(f"guard: {len(ids)} hearts, 0 refused", flush=True)
    for i in ids:
        refuse([i], what="shared LIE benchmark fetch", source="TotalSegmentator")
        (out / i).mkdir(parents=True, exist_ok=True)
        for f in FILES:
            p = out / i / f
            if not p.exists():
                urllib.request.urlretrieve(MIRROR.format(id=i, f=f), p)
        print(i, flush=True)
