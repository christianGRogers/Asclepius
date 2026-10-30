"""Fetch the cardiac studies of the TotalSegmentator v1 dataset (Zenodo 6802614, CC BY 4.0).

Pulls only the members needed (ct.nii.gz and the five heart masks) out of the 28 GB zip
with HTTP range requests, for the study types 'ct heart' and 'ct coronary arteries'. Studies whose s-number is a coronary
hold-out in the project pool (seal, reserve, D35 drafts) are never downloaded.
Usage: python fetch_ts_cardiac.py OUT_DIR
"""
import csv
import io
import sys
from pathlib import Path

from remotezip import RemoteZip

from coronary_holdout import held_out_totalseg_ids

URL = "https://zenodo.org/records/6802614/files/Totalsegmentator_dataset.zip?download=1"
ROOT = "Totalsegmentator_dataset"
STUDY_TYPES = {"ct heart", "ct coronary arteries"}
MASKS = ["heart_myocardium", "heart_ventricle_left", "heart_ventricle_right",
         "heart_atrium_left", "heart_atrium_right", "aorta"]


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with RemoteZip(URL) as z:
        meta = z.read(f"{ROOT}/meta.csv").decode("utf-8-sig")
        (out / "meta.csv").write_text(meta)
        rows = [r for r in csv.DictReader(io.StringIO(meta), delimiter=";")
                if r["study_type"].strip() in STUDY_TYPES]
        held = held_out_totalseg_ids()
        n0 = len(rows)
        rows = [r for r in rows if r["image_id"] not in held]
        print(n0, "cardiac studies,", n0 - len(rows), "skipped as coronary hold-outs", flush=True)
        for r in rows:
            sid = r["image_id"]
            dst = out / sid
            if (dst / "done").exists():
                continue
            (dst / "segmentations").mkdir(parents=True, exist_ok=True)
            members = [f"{sid}/ct.nii.gz"] + [f"{sid}/segmentations/{m}.nii.gz" for m in MASKS]
            for m in members:
                (dst / m.split("/", 1)[1]).write_bytes(z.read(f"{ROOT}/{m}"))
            (dst / "done").write_text(r["study_type"])
            print(sid, r["study_type"], flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
