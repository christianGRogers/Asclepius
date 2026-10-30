"""Fetch public TotalSegmentator v1 cases for India's Round 2, after guard_r2 (held-out ids and their twins).

Masks for every allowed subject whose study covers the heart (cardiac, thorax, polytrauma, whole-body);
the CT too for the cardiac-protocol subjects. guard_r2.refuse() runs on every id before its first byte is
requested. Images stay in OUT_DIR (scratch) and are never committed.

    python fetch_r2.py V1_META OUT_DIR
"""
import csv, os, sys
from remotezip import RemoteZip
from guard_r2 import refuse, HeldOutError
from fetch_ts_cardiac import URL, CARDIAC, MASKS

HEART = ("thorax", "heart", "aortic valve", "coronary", "polytrauma", "whole body", "thx", "left artrium")


def main(meta, out):
    rows = list(csv.DictReader(open(meta, encoding="utf-8-sig"), delimiter=";"))
    todo = []
    for r in rows:
        st = r["study_type"].strip()
        if not any(h in st for h in HEART) or "head" in st:
            continue
        try:
            refuse("TotalSegmentator", r["image_id"])
        except HeldOutError:
            continue
        todo.append((r["image_id"], st in CARDIAC))
    print(len(todo), "allowed heart-covering subjects;", sum(c for _, c in todo), "cardiac", flush=True)
    z = RemoteZip(URL)
    for sid, cardiac in todo:
        refuse("TotalSegmentator", sid)
        base = f"Totalsegmentator_dataset/{sid}/"
        files = [base + f"segmentations/{m}.nii.gz" for m in MASKS] + ([base + "ct.nii.gz"] if cardiac else [])
        for f in files:
            if os.path.exists(os.path.join(out, f)):
                continue
            for _ in range(4):
                try:
                    z.extract(f, out); break
                except Exception as e:
                    print("retry", f, type(e).__name__, flush=True)
                    try: os.remove(os.path.join(out, f))
                    except OSError: pass
                    z = RemoteZip(URL)
            else:
                raise RuntimeError(f"could not fetch {f}")
        print(sid, "cardiac" if cardiac else "", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
