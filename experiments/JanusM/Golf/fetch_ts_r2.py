"""Golf R2 data: the public TotalSegmentator v2.0.1 gated-like cardiac CTs (CC BY 4.0, Zenodo 10.5281/zenodo.10047292)
that pass the Round 2 guard (guard_r2.py: pool, seal, reserve, D35, A14, and the JA12 twin rule).
Every id is refused-checked before its first byte is downloaded.  Images stay in <outdir>; nothing is committed or
uploaded.   Usage: python fetch_ts_r2.py <outdir>"""
import json, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from guard_r2 import reason, refuse  # noqa: E402

MIRROR = "https://huggingface.co/datasets/MedOtter/totalsegmentator-cardiac/resolve/main/{id}/{f}"


def chosen():
    ids = json.loads((HERE.parents[2] / "tools/ccta/totalseg_cardiac_ids.json").read_text())
    return [i for i in ids["gated_like"] if not reason("TotalSegmentator-cardiac", i)], ids["meta"]


if __name__ == "__main__":
    out = Path(sys.argv[1])
    sel, meta = chosen()
    (HERE / "ts_cases_r2.json").write_text(json.dumps({i: meta[i] for i in sel}, indent=1) + "\n")
    for i in sel:
        refuse("TotalSegmentator-cardiac", i)
        (out / i).mkdir(parents=True, exist_ok=True)
        for f in ("ct.nii.gz", "cardiac_label.nii.gz"):
            p = out / i / f
            if not p.exists():
                urllib.request.urlretrieve(MIRROR.format(id=i, f=f), p)
        print(i, flush=True)
