"""Lima's held-out guard for public TotalSegmentator cases (Janus-M R2, path jm/rest-ccta).

Until the shared JA12 guard (#138) lands, every Lima script calls `check(sid)` before it opens a public
TotalSegmentator case. It refuses, by patient:

1. every TotalSegmentator s-number named in any coronary held-out or pool file: the SegQueue14 pool list (which
   contains the seal, the reserve and every D35 draw), the pool seal, the A14 sealed test, and every JSON or text
   file under experiments/*/r10*/ (all Round 10 draws and proposals). Wider than the seal, as Kilo's and India's
   guards are;
2. every **twin** (Round 1 ruling, section 4, JA12): a public subject, in either release, whose sex and institute
   match a held-out subject's in that release and whose age is within +-5 years, of any study type.

The twin list is computed by `twins.py` from the two public meta.csv files (metadata only, no image) and committed
as `twins.json`. If that file is missing, the guard refuses to run.
"""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FIXED = ["configs/segqueue14/pool-2026-10.txt", "configs/segqueue14/sealed-pool-2026-10.json",
         "trillium/icx4/sealed_test.json"]
TS_ID = re.compile(r"TotalSegmentator[^_\"\s/]*__(s\d{4})")
MIN_IDS = 16  # the pool holds 16 TotalSegmentator volumes today; fewer means a source file went missing


def source_files():
    files = [os.path.join(REPO, f) for f in FIXED]
    for f in files:
        if not os.path.exists(f):
            raise FileNotFoundError(f"held-out source missing: {f}; refusing to run")
    for pat in ("experiments/*/r10*/*.json", "experiments/*/r10*/*.txt", "configs/**/*.json", "configs/**/*.txt"):
        files += sorted(glob.glob(os.path.join(REPO, pat), recursive=True))
    return sorted(set(files))


def held_out_ids():
    ids = set()
    for f in source_files():
        with open(f, encoding="utf-8", errors="ignore") as fh:
            ids |= set(TS_ID.findall(fh.read()))
    if len(ids) < MIN_IDS:
        raise RuntimeError(f"only {len(ids)} held-out TotalSegmentator ids found (expected >= {MIN_IDS}); refusing")
    return ids


def twin_ids():
    p = os.path.join(HERE, "twins.json")
    if not os.path.exists(p):
        raise FileNotFoundError("twins.json missing: run twins.py (metadata only) first; refusing")
    d = json.load(open(p))
    if set(d["held_out"]) != held_out_ids():
        raise RuntimeError("twins.json was built from a different held-out list; re-run twins.py; refusing")
    return set(d["refused_twins"])


def refused():
    return held_out_ids() | twin_ids()


_CACHE = None


def check(sid):
    """Raise before any file of `sid` is opened if it is a held-out patient or a twin of one."""
    global _CACHE
    if _CACHE is None:
        _CACHE = refused()
    if sid in _CACHE:
        raise SystemExit(f"refusing {sid}: a coronary held-out TotalSegmentator patient or a twin of one")
    return sid


if __name__ == "__main__":
    h = held_out_ids()
    print(len(h), "held-out ids;", len(refused()), "refused in total (held-out + twins)")
