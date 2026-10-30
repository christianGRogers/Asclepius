"""E4 (Kilo v2): the JA12 twin rule applied to the public TotalSegmentator v1 meta.csv (Round 1 ruling, section 6.7).

Reads only meta.csv (image_id; age; gender; institute; study_type; split), no image. Writes the refused counts and
the open cardiac-protocol ids. It never writes a held-out subject's demographics.
Usage: python e4_twins.py META_CSV OUT_JSON
"""
import collections, json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from heldout import refused_with_twins, _meta_rows, TWIN_AGE_YEARS

CARDIAC = ("ct heart", "ct coronary arteries", "ct aortic valve")
meta = open(sys.argv[1], encoding="utf-8").read()
direct, twins = refused_with_twins(meta)
rows = _meta_rows(meta)
card = [r for r in rows if r["study_type"].strip() in CARDIAC]
open_card = sorted(r["image_id"] for r in card if r["image_id"] not in direct | twins)
out = {"rule": f"same sex and institute as a held-out subject, age within +-{TWIN_AGE_YEARS} y, any study type",
       "subjects": len(rows), "held_out_direct": len(direct), "twins": len(twins),
       "open_after_rule": len(rows) - len(direct) - len(twins),
       "cardiac_protocol": {"total": len(card), "held_out_direct": sum(r["image_id"] in direct for r in card),
                            "twins": sum(r["image_id"] in twins for r in card), "open": len(open_card)},
       "twins_by_study_type": dict(collections.Counter(r["study_type"].strip() for r in rows
                                                       if r["image_id"] in twins).most_common()),
       "open_cardiac_ids": open_card}
json.dump(out, open(sys.argv[2], "w"), indent=1)
print({k: v for k, v in out.items() if k not in ("open_cardiac_ids", "twins_by_study_type")})
