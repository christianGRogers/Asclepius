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


def pool_subjects():
    """Every TotalSegmentator subject in the SegQueue14 pool (sealed, D35 or trainable). Janus-M never
    reads any of them: the seal and the D35 set are drawn from this list, so the whole list is excluded."""
    return set(re.findall(r"TotalSegmentator-cardiac__(s\d{4})", open(POOL).read()))

URL = "https://zenodo.org/records/6802614/files/Totalsegmentator_dataset.zip?download=1"
CARDIAC = {"ct heart", "ct heart-thorakale aorta", "ct aortic valve", "ct coronary arteries", "ct left artrium"}
MASKS = ["heart_myocardium", "heart_ventricle_left", "heart_ventricle_right", "heart_atrium_left",
         "heart_atrium_right", "aorta"]

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
                z.extract(f, out)
        print(s, flush=True)

if __name__ == "__main__":
    main(sys.argv[1])
