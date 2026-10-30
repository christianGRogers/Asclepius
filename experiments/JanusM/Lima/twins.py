"""JA12 twin rule on the public TotalSegmentator meta.csv files (metadata only; no image is opened).

A **twin** is a public subject, in either release (v1, Zenodo 6802614; v2.0.1, Zenodo 10047292), who matches a
coronary held-out subject in that release on sex and institute, with age within +-5 years, of any study type
(Round 1 ruling, section 4). A missing sex or age on either side counts as a match (conservative). Institute
letters are relabelled between releases (India R1), so the match is made within each release; a held-out id with
no v1 row is carried into v1 through the institute map learned on the shared ids.

    python twins.py V1_META_CSV V2_META_CSV      # writes twins.json beside this file

The meta.csv files are fetched to a scratch folder with remotezip (two small range reads) and never committed.
"""
import collections
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from heldout import held_out_ids  # noqa: E402

AGE_TOL = 5.0


def read(p):
    rows = {}
    with open(p, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            age = r["age"].strip()
            rows[r["image_id"].strip()] = dict(age=float(age) if age else None,
                                               sex=(r["gender"].strip().lower() or None),
                                               inst=r["institute"].strip(), study=r["study_type"].strip())
    return rows


def match(a, b):
    if a["inst"] != b["inst"]:
        return False
    if a["sex"] and b["sex"] and a["sex"] != b["sex"]:
        return False
    if a["age"] is not None and b["age"] is not None and abs(a["age"] - b["age"]) > AGE_TOL:
        return False
    return True


def main(v1p, v2p):
    v1, v2 = read(v1p), read(v2p)
    held = sorted(held_out_ids())
    # institute map v2 -> v1 from the shared ids (India R1: consistent relabelling)
    pairs = collections.Counter((v2[s]["inst"], v1[s]["inst"]) for s in v1 if s in v2)
    imap = {}
    for (a, b), n in pairs.most_common():
        imap.setdefault(a, b)
    out = {"held_out": held, "age_tol_years": AGE_TOL, "per_release": {}, "refused_twins": []}
    twins = set()
    for name, rel in (("v1", v1), ("v2.0.1", v2)):
        tw, missing = {}, []
        for h in held:
            if h in rel:
                hr = rel[h]
            elif h in v2 and name == "v1":
                hr = dict(v2[h], inst=imap.get(v2[h]["inst"], "?"))
            else:
                missing.append(h)
                continue
            t = sorted(s for s, r in rel.items() if s not in held and match(hr, r))
            tw[h] = t
            twins |= set(t)
        out["per_release"][name] = {
            "n_subjects": len(rel), "held_out_without_row": missing,
            "twins_per_held_out": {h: len(v) for h, v in tw.items()},
            "n_twins": len(set().union(*tw.values())) if tw else 0,
            "n_twins_cardiac_study": len({s for v in tw.values() for s in v
                                          if any(k in rel[s]["study"] for k in ("heart", "coronar", "aortic valve",
                                                                                "atrium", "artrium"))}),
        }
    out["refused_twins"] = sorted(twins)
    out["n_refused_twins"] = len(twins)
    out["n_refused_total"] = len(twins | set(held))
    json.dump(out, open(os.path.join(HERE, "twins.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ("refused_twins", "held_out")}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
