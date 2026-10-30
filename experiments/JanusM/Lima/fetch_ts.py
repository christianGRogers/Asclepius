"""Fetch the cardiac-protocol TotalSegmentator v1 subjects that Lima's guard allows (CC BY 4.0, Zenodo 6802614).

Every subject passes `heldout.check` (held-out ids and JA12 twins) *before* any of its files is requested. Only the
CT and five heart masks are read, by HTTP range requests. Images stay in a scratch folder and are never committed.

    python fetch_ts.py V1_META_CSV OUT_DIR [--masks-only]
"""
import argparse
import os
import sys

from remotezip import RemoteZip

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from heldout import check, refused  # noqa: E402
from twins import read  # noqa: E402

URL = "https://zenodo.org/records/6802614/files/Totalsegmentator_dataset.zip?download=1"
CARDIAC = {"ct heart", "ct heart-thorakale aorta", "ct aortic valve", "ct coronary arteries", "ct left artrium"}
MASKS = ["heart_myocardium", "heart_ventricle_left", "heart_ventricle_right", "heart_atrium_left", "aorta"]


def allowed_cardiac(meta):
    rows = read(meta)
    bad = refused()
    card = sorted(s for s, r in rows.items() if r["study"] in CARDIAC)
    return [s for s in card if s not in bad], len(card)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("meta"); ap.add_argument("out"); ap.add_argument("--masks-only", action="store_true")
    a = ap.parse_args()
    subj, n = allowed_cardiac(a.meta)
    print(f"{n} cardiac subjects; {len(subj)} allowed after held-out ids and twins", flush=True)
    z = RemoteZip(URL)
    names = set(z.namelist())
    for s in subj:
        check(s)  # refuses before any byte of the subject is requested
        base = f"Totalsegmentator_dataset/{s}/"
        files = ([] if a.masks_only else [base + "ct.nii.gz"]) + [base + f"segmentations/{m}.nii.gz" for m in MASKS]
        for f in files:
            if f in names and not os.path.exists(os.path.join(a.out, f)):
                for _ in range(4):
                    try:
                        z.extract(f, a.out)
                        break
                    except Exception as e:  # partial file on a dropped connection: remove and retry
                        print("retry", f, type(e).__name__, flush=True)
                        try:
                            os.remove(os.path.join(a.out, f))
                        except OSError:
                            pass
                        z = RemoteZip(URL)
                else:
                    raise RuntimeError(f"could not fetch {f}")
        print(s, flush=True)


if __name__ == "__main__":
    main()
