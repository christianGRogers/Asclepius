"""Fetch the cardiac-protocol subjects of the TotalSegmentator v1 dataset (Zenodo 6802614, CC BY 4.0).

Only the CT and the five heart masks of each cardiac study are pulled, by HTTP range requests, so the
28 GB archive is never downloaded. Images stay in the local work folder and are never committed.

    python fetch_ts_cardiac.py OUT_DIR
"""
import csv, sys, os, re, shutil
from remotezip import RemoteZip

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
POOL = os.path.join(REPO, "configs", "segqueue14", "pool-2026-10.txt")


HELD_OUT_SOURCES = ["configs/segqueue14/pool-2026-10.txt",            # every pool volume (seal, D35, reserve, train)
                    "configs/segqueue14/sealed-pool-2026-10.json",     # the D27/D32/D33 seal
                    "experiments/*/r10*/*decision_set*proposal*.json",  # every Round 10 D35 draw and reserve order
                    "experiments/Delta/r10/d35_decision_set_proposal.json"]


def pool_subjects():
    """Every TotalSegmentator subject named by the SegQueue14 pool, the pool seal or any Round 10 D35 draw.

    Janus-M never reads any of them. TotalSegmentator s-numbers name the same patient in v1 (Zenodo 6802614,
    used here) and v2.0.1 (the pool's source): over the 1204 shared ids, sex and study type agree for 1203,
    ages differ by at most 4 years and institute letters are relabelled consistently (India E1-E4 note). So an
    s-number match is a patient match. The pool list is a superset of the others; all are read anyway so that
    a later change to any one of them is still refused."""
    import glob
    ids = set()
    for pat in HELD_OUT_SOURCES:
        for f in glob.glob(os.path.join(REPO, pat)):
            ids |= set(re.findall(r"TotalSegmentator[A-Za-z_-]*__(s\d{4})", open(f).read()))
    if len(ids) < 16:
        raise RuntimeError(f"held-out TotalSegmentator list too short ({len(ids)}); refusing to run")
    return ids


def refuse_held_out(sid):
    if sid in pool_subjects():
        raise RuntimeError(f"{sid} is a held-out (pool, sealed or D35) TotalSegmentator subject: refused")


def main(out):
    z = RemoteZip(URL)
    names = set(z.namelist())
    meta = os.path.join(out, "Totalsegmentator_dataset/meta.csv")
    if not os.path.exists(meta):
        z.extract("Totalsegmentator_dataset/meta.csv", out)
    rows = list(csv.DictReader(open(meta, encoding="utf-8-sig"), delimiter=";"))
    excl = pool_subjects()
    subj = [r["image_id"] for r in rows if r["study_type"].strip() in CARDIAC and r["image_id"] not in excl]
    for s in excl:  # never keep a pool subject locally, even by accident
        shutil.rmtree(os.path.join(out, "Totalsegmentator_dataset", s), ignore_errors=True)
    print(len(subj), "cardiac subjects after excluding", len(excl), "pool subjects", flush=True)
    for s in subj:
        base = f"Totalsegmentator_dataset/{s}/"
        files = [base + "ct.nii.gz"] + [base + f"segmentations/{m}.nii.gz" for m in MASKS]
        for f in files:
            if f in names and not os.path.exists(os.path.join(out, f)):
                for attempt in range(4):  # a dropped connection leaves a partial file: remove it and retry
                    try:
                        z.extract(f, out)
                        break
                    except Exception as e:
                        print("retry", f, type(e).__name__, flush=True)
                        try:
                            os.remove(os.path.join(out, f))
                        except OSError:
                            pass
                        z = RemoteZip(URL)
                else:
                    raise RuntimeError(f"could not fetch {f}")
        print(s, flush=True)

if __name__ == "__main__":
    main(sys.argv[1])
