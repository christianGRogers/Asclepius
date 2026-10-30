"""India's Round 2 held-out guard (JA12 stand-in until the shared guard, #138, lands).

Janus-M India opens only public TotalSegmentator cases. Before any image is fetched or read, this module refuses:

1. every TotalSegmentator s-number named by the coronary pool list, the pool seal or any Round 10 D35 draw
   (`fetch_ts_cardiac.pool_subjects()`, India v1; all 16 pool s-numbers are refused, whatever their coronary role);
2. every **twin** of those subjects (ruling §4, JA12): any public subject, in TotalSegmentator v1 (Zenodo 6802614)
   or v2.0.1 (Zenodo 10047292), with the same sex and the same institute as a held-out subject in that release,
   age within +-5 years, any study type. A missing sex or age counts as a match (over-refusal);
3. any source other than TotalSegmentator (India's Round 2 opens no ImageCAS, pool or other case at all).

The two `meta.csv` files are tables (no images). `build()` writes `results/guard_r2.json` with the refused ids and
counts; `refuse()` reads that file and raises before a case is touched.

    python guard_r2.py V1_META V2_META        # builds results/guard_r2.json
"""
from __future__ import annotations

import csv, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results", "guard_r2.json")
AGE_TOL = 5.0


class HeldOutError(RuntimeError):
    pass


def _rows(path):
    with open(path, encoding="utf-8-sig") as f:
        return {r["image_id"]: r for r in csv.DictReader(f, delimiter=";")}


def _age(r):
    try:
        return float(r["age"])
    except (ValueError, KeyError, TypeError):
        return None


def _twins(meta, held):
    """Subjects of one release matching a held-out subject of the same release on sex + institute, age +-5."""
    out = {}
    for h in sorted(held):
        if h not in meta:
            continue
        hr = meta[h]
        ha, hs, hi = _age(hr), hr["gender"].strip().lower(), hr["institute"].strip()
        for sid, r in meta.items():
            if sid in held:
                continue
            a, s = _age(r), r["gender"].strip().lower()
            if r["institute"].strip() != hi:
                continue
            if s and hs and s != hs:
                continue
            if a is not None and ha is not None and abs(a - ha) > AGE_TOL:
                continue
            out.setdefault(sid, []).append(h)
    return out


def build(v1_meta, v2_meta):
    sys.path.insert(0, HERE)
    from fetch_ts_cardiac import pool_subjects, CARDIAC
    held = pool_subjects()
    m1, m2 = _rows(v1_meta), _rows(v2_meta)
    t1, t2 = _twins(m1, held), _twins(m2, held)
    twins = sorted(set(t1) | set(t2))
    cardiac_v1 = {s for s, r in m1.items() if r["study_type"].strip() in CARDIAC}
    res = {
        "rule": "same sex (missing = match), same institute within a release, |age diff| <= 5 y (missing = match), "
                "any study type; in v1 or v2.0.1",
        "meta_sha256": {"v1": hashlib.sha256(open(v1_meta, "rb").read()).hexdigest(),
                        "v2.0.1": hashlib.sha256(open(v2_meta, "rb").read()).hexdigest()},
        "held_out": sorted(held),
        "held_out_in_v1": sorted(h for h in held if h in m1),
        "held_out_in_v2": sorted(h for h in held if h in m2),
        "n_subjects_v1": len(m1), "n_subjects_v2": len(m2),
        "twins_v1": len(t1), "twins_v2": len(t2), "twins_union": len(twins),
        "twins_per_held_out": {h: sum(h in v for v in {**t1, **t2}.values()) for h in sorted(held)},
        "cardiac_v1_total": len(cardiac_v1),
        "cardiac_v1_held_out": len(cardiac_v1 & held),
        "cardiac_v1_twins": len(cardiac_v1 & set(twins)),
        "cardiac_v1_allowed": len(cardiac_v1 - held - set(twins)),
        "refused": sorted(held | set(twins)),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=1)
    return res


_REFUSED = None


def refuse(source, case):
    """Raise HeldOutError unless `case` is a public TotalSegmentator subject that is neither held out nor a twin."""
    global _REFUSED
    if source != "TotalSegmentator":
        raise HeldOutError(f"India R2 opens TotalSegmentator only; {source}:{case} refused")
    if _REFUSED is None:
        if not os.path.exists(OUT):
            raise HeldOutError("results/guard_r2.json missing: run guard_r2.py first")
        g = json.load(open(OUT))
        sys.path.insert(0, HERE)
        from fetch_ts_cardiac import pool_subjects
        held = pool_subjects()
        if not held <= set(g["refused"]):
            raise HeldOutError("guard_r2.json is stale: a held-out id is missing from it")
        _REFUSED = set(g["refused"])
    if case in _REFUSED:
        raise HeldOutError(f"TotalSegmentator {case}: held out or a twin of a held-out subject; refused")
    return case


if __name__ == "__main__":
    r = build(sys.argv[1], sys.argv[2])
    print(json.dumps({k: v for k, v in r.items() if k not in ("refused",)}, indent=1))
