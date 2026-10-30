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


# --- Round 2 (Kilo v2): the JA12 twin rule ---------------------------------------------------------------------
# TotalSegmentator publishes no patient id, so one held-out patient could appear under a second s-number (another
# study). JA12 (Round 1 ruling, section 4) refuses as a "twin" every public subject that matches a held-out subject
# on sex and institute, with age within +-5 years, of any study type. It over-refuses on purpose.
TWIN_AGE_YEARS = 5


def _meta_rows(meta_text):
    import csv, io
    return list(csv.DictReader(io.StringIO(meta_text.lstrip("﻿")), delimiter=";"))


def refused_with_twins(meta_text):
    """Return (direct, twins): held-out s-numbers, and every other s-number refused under the JA12 twin rule.
    meta_text is the public TotalSegmentator meta.csv (image_id;age;gender;institute;study_type;split)."""
    direct = refused_totalseg_ids()
    rows = {r["image_id"]: r for r in _meta_rows(meta_text)}
    missing = sorted(direct - set(rows))
    if missing:
        raise RuntimeError(f"held-out ids missing from meta.csv: {missing}; refusing to go on")
    keys = [(rows[s]["gender"].strip(), rows[s]["institute"].strip(), int(float(rows[s]["age"])))
            for s in sorted(direct)]
    twins = set()
    for sid, r in rows.items():
        if sid in direct:
            continue
        try:
            age = int(float(r["age"]))
        except ValueError:          # no age stated: cannot rule a twin out, so refuse on sex + institute alone
            age = None
        for g, inst, a in keys:
            if r["gender"].strip() == g and r["institute"].strip() == inst and \
                    (age is None or abs(age - a) <= TWIN_AGE_YEARS):
                twins.add(sid)
                break
    return direct, twins


def check_public(case_id, meta_text):
    """Refuse a public TotalSegmentator case if it is held out or a JA12 twin of a held-out subject."""
    direct, twins = refused_with_twins(meta_text)
    if case_id in direct:
        raise SystemExit(f"refusing {case_id}: a held-out pool patient (seal / reserve / D35 / pool list)")
    if case_id in twins:
        raise SystemExit(f"refusing {case_id}: a JA12 twin of a held-out pool patient")
