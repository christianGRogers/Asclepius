"""Golf E2 data: fetch TotalSegmentator v2.0.1 contrast cardiac cases (CC BY 4.0, Zenodo 10.5281/zenodo.10047292)
that are NOT in the SegQueue14 pool list, so they cannot be a sealed, reserve or D35 volume.
Picks the first N 'gated_like' ids by sha256('janusm-golf-r1:' + id) and downloads ct + cardiac_label from the
Hugging Face mirror tools/ccta/ingest_totalseg.py already uses.  Nothing is uploaded anywhere.
Usage: python fetch_ts.py <outdir> [N=24]"""
import hashlib, json, os, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MIRROR = "https://huggingface.co/datasets/MedOtter/totalsegmentator-cardiac/resolve/main/{id}/{f}"


def chosen(n):
    ids = json.loads((ROOT / "tools/ccta/totalseg_cardiac_ids.json").read_text())
    pool = (ROOT / "configs/segqueue14/pool-2026-10.txt").read_text()
    cand = [i for i in ids["gated_like"] if f"TotalSegmentator-cardiac__{i}" not in pool]
    return sorted(cand, key=lambda i: hashlib.sha256(f"janusm-golf-r1:{i}".encode()).hexdigest())[:n], ids["meta"]


if __name__ == "__main__":
    out, n = Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 24
    sel, meta = chosen(n)
    (Path(__file__).parent / "ts_cases.json").write_text(json.dumps({i: meta[i] for i in sel}, indent=1))
    for i in sel:
        (out / i).mkdir(parents=True, exist_ok=True)
        for f in ("ct.nii.gz", "cardiac_label.nii.gz"):
            p = out / i / f
            if not p.exists():
                urllib.request.urlretrieve(MIRROR.format(id=i, f=f), p)
        print(i, flush=True)
