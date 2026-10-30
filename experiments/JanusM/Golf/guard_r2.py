"""Golf's Round 2 held-out guard: JA12's full refusal list, until the shared guard (#138) lands.

It refuses, by patient, before any case is opened:
  1. everything Golf's Round 1 guard refuses (`heldout.py`): the pool seal (primary, report-only, extension
     order / reserve), every Round 10 D35 draw, the A14 sealed 100;
  2. the ImageCAS-X val 80 and the whole ImageCAS-X test split (160 = A14 sealed 80 + open 36 + dev 44), from the
     committed splits.json (sha256 prefix a53bd426cddc; refuses to run on any other file);
  3. PLOS-Peng2016, as a whole source;
  4. every TotalSegmentator subject named anywhere in the coronary pool list (all 16, sealed or not);
  5. every TotalSegmentator "twin" (ruling §4, JA12): a public subject matching a held-out TotalSegmentator subject on
     sex and institute, with age within +-5 years and any study type. It is checked separately in v1 (Zenodo 6802614)
     and v2.0.1 (Zenodo 10047292) metadata, because institute letters are relabelled between versions. A blank sex
     matches either sex (over-refusal is the safe side).

Superseded by the shared guard `src/janusm/guard.py` (#138), which `refuse` also calls when it is present. The
shared twin list `configs/janusm/ts-twins-r1.json` holds the same 707 s-numbers as `guard_r2_twins.json`.

The twin list is computed once by `python guard_r2.py --twins <meta_v1.csv> <meta_v2.csv>` and committed as
`guard_r2_twins.json` (s-numbers only). The guard refuses to load without it.

    from guard_r2 import refuse
    refuse("TotalSegmentator-cardiac", "s0655")   # raises HeldOutError
"""
import csv, hashlib, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from heldout import HeldOutError, reason as r1_reason  # noqa: E402

SPLITS = ROOT / "trillium-results/icx14/results/splits.json"
SPLITS_SHA = "a53bd426cddc"
POOL = ROOT / "configs/segqueue14/pool-2026-10.txt"
TWINS = HERE / "guard_r2_twins.json"
TS_SOURCES = ("TotalSegmentator-cardiac", "TotalSegmentator", "TotalSegmentator-v1", "TotalSegmentator-v2")
REFUSED_SOURCES = {"PLOS-Peng2016"}


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pool_ts_subjects():
    ids = set(re.findall(r"TotalSegmentator[A-Za-z_-]*__(s\d{4})", POOL.read_text()))
    if len(ids) < 16:
        raise HeldOutError(f"pool lists {len(ids)} TotalSegmentator subjects, expected >= 16; refusing to run")
    return ids


def _load():
    if not _sha(SPLITS).startswith(SPLITS_SHA):
        raise HeldOutError("splits.json is not the committed icx14 copy; refusing to run")
    sp = json.loads(SPLITS.read_text())
    icx_bad = set(sp["val"]) | set(sp["test"])
    if len(sp["val"]) != 80 or len(sp["test"]) != 160:
        raise HeldOutError("splits.json does not hold val 80 / test 160")
    if not TWINS.exists():
        raise HeldOutError("guard_r2_twins.json missing: run --twins first; refusing to run")
    tw = json.loads(TWINS.read_text())
    held = pool_ts_subjects()
    if set(tw["held_out"]) != held:
        raise HeldOutError("twin list was built for a different held-out set; rebuild it")
    return icx_bad, held | set(tw["refused"])


_ICX_BAD, _TS_BAD = _load()


def reason(source, case):
    if source in REFUSED_SOURCES:
        return f"{source}: refused source (burned-in text; JA5)"
    r = r1_reason(source, case)
    if r:
        return r
    if source == "ImageCAS" and case in _ICX_BAD:
        return f"ImageCAS {case}: ImageCAS-X val 80 or test split (JA5)"
    if source in TS_SOURCES and case in _TS_BAD:
        return f"{source}__{case}: held-out TotalSegmentator subject or twin (JA12)"
    return None


def refuse(source, case):
    r = reason(source, case)
    if r:
        raise HeldOutError(f"REFUSING {r}")
    try:                                    # the shared JA12 guard (#138), when present, is checked as well
        sys.path.insert(0, str(ROOT / "src"))
        from janusm.guard import refuse as shared_refuse
    except ImportError:
        return case
    shared_refuse([f"{source}__{case}"], what="Golf R2")
    return case


def _rows(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig"), delimiter=";"))


def _twins(rows, held):
    by = {r["image_id"]: r for r in rows}
    out = {}
    for h in sorted(held):
        if h not in by:
            continue
        a = by[h]
        for r in rows:
            if r["image_id"] == h:
                continue
            sex_ok = not a["gender"] or not r["gender"] or a["gender"] == r["gender"]
            try:
                age_ok = abs(float(a["age"]) - float(r["age"])) <= 5
            except ValueError:
                age_ok = True                       # unknown age: refuse (safe side)
            if sex_ok and age_ok and a["institute"] == r["institute"]:
                out.setdefault(r["image_id"], []).append(h)
    return out


def build_twins(meta_v1, meta_v2):
    held = pool_ts_subjects()
    v1, v2 = _rows(meta_v1), _rows(meta_v2)
    t1, t2 = _twins(v1, held), _twins(v2, held)
    refused = sorted(set(t1) | set(t2))
    card = {"ct heart", "ct heart-thorakale aorta", "ct aortic valve", "ct coronary arteries", "ct left artrium"}
    st = {r["image_id"]: r["study_type"].strip() for r in v2 + v1}
    res = {
        "rule": "same sex (blank matches any) and institute, |age difference| <= 5 y, any study type; v1 and v2 "
                "metadata checked separately; JA12 / Round 1 ruling section 4",
        "meta_v1_sha256": _sha(meta_v1), "meta_v2_sha256": _sha(meta_v2),
        "held_out": sorted(held),
        "held_out_found": {"v1": sum(h in {r['image_id'] for r in v1} for h in held),
                           "v2": sum(h in {r['image_id'] for r in v2} for h in held)},
        "subjects": {"v1": len(v1), "v2": len(v2)},
        "twins_v1": len(t1), "twins_v2": len(t2),
        "refused_count": len(refused),
        "refused_cardiac_study_types": sum(st.get(s) in card for s in refused),
        "per_held_out": {h: sum(h in v for v in t1.values()) + sum(h in v for v in t2.values()) for h in sorted(held)},
        "refused": refused,
    }
    TWINS.write_text(json.dumps(res, indent=1) + "\n")
    return res


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--twins":
        r = build_twins(a[1], a[2])
        print({k: v for k, v in r.items() if k != "refused"})
        sys.exit(0)
    bad = [reason(a[0], c) for c in a[1:]]
    for c, r in zip(a[1:], bad):
        print(c, r or "allowed")
    sys.exit(3 if any(bad) else 0)
