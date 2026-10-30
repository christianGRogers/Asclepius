"""Every public case number Janus-M must refuse (PM, 2026-10-30): the pool seal, its reserve, every Round 10 D35
draw, the pool list itself and the ImageCAS-X seal. The pool reuses public case numbers (TotalSegmentator
s-numbers, ImageCHD, ImageALCAPA, Taiwan AI CUP), so a public copy of a held-out case is the same patient.

Kilo refuses every TotalSegmentator id that appears anywhere in these files: wider than the seal, because the
whole pool list is excluded too. The TotalSegmentator v1 and v2 datasets share subject ids (v2 extends v1), so a
v1 id equal to a pool id is taken to be the same patient.
"""
import glob, os, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
FILES = (["configs/segqueue14/sealed-pool-2026-10.json", "configs/segqueue14/pool-2026-10.txt",
          "trillium/icx4/sealed_test.json"]
         + sorted(glob.glob(os.path.join(REPO, "experiments/*/r10*/*decision_set*proposal*.json")))
         + sorted(glob.glob(os.path.join(REPO, "experiments/*/r10*/*d35*proposal*.json"))))


def refused_totalseg_ids():
    ids = set()
    for f in FILES:
        p = f if os.path.isabs(f) else os.path.join(REPO, f)
        if not os.path.exists(p):
            raise FileNotFoundError(f"held-out list missing: {p}; refusing to go on")
        ids |= set(re.findall(r"TotalSegmentator[^_\"]*__(s\d{4})", open(p).read()))
    if len(ids) < 16:
        raise RuntimeError(f"only {len(ids)} held-out TotalSegmentator ids found; expected >= 16")
    return ids


def check(case_id):
    if case_id in refused_totalseg_ids():
        raise SystemExit(f"refusing {case_id}: a held-out pool patient (seal / reserve / D35 / pool list)")
