"""Golf R3 data: the 22 public TotalSegmentator v2.0.1 gated-like cardiac CTs (CC BY 4.0, Zenodo 10.5281/zenodo.10047292)
that pass the shared JA12 guard (janusm.guard, v2, 711 refused).  The whole list is refused-checked before the first
byte is downloaded, and each id again before its own download.  Images stay in <outdir>; nothing is committed.
Usage: PYTHONPATH=src python fetch_ts_r3.py <outdir>"""
import json, sys, urllib.request
from pathlib import Path

from janusm.guard import GUARD_VERSION, refuse

HERE = Path(__file__).resolve().parent
MIRROR = "https://huggingface.co/datasets/MedOtter/totalsegmentator-cardiac/resolve/main/{id}/{f}"


def cases():
    ids = sorted(json.loads((HERE / "ts_cases_r2.json").read_text()))
    refuse([f"TotalSegmentator-cardiac__{i}" for i in ids], what="Golf R3 TotalSegmentator fetch")
    return ids


if __name__ == "__main__":
    out = Path(sys.argv[1])
    ids = cases()
    print(f"guard v{GUARD_VERSION}: {len(ids)} ids pass", flush=True)
    for i in ids:
        refuse([f"TotalSegmentator-cardiac__{i}"], what="Golf R3 TotalSegmentator fetch")
        (out / i).mkdir(parents=True, exist_ok=True)
        for f in ("ct.nii.gz", "cardiac_label.nii.gz"):
            p = out / i / f
            if not p.exists():
                urllib.request.urlretrieve(MIRROR.format(id=i, f=f), str(p) + ".part")
                Path(str(p) + ".part").rename(p)
        print(i, flush=True)
