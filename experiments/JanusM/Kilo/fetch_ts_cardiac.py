"""Fetch cardiac cases (CT + heart masks) from the public TotalSegmentator v1 dataset.

Zenodo 6802614 (CC BY 4.0), 28 GB zip; members are read by HTTP range (remotezip), so only
the chosen cases are downloaded. Every TotalSegmentator id in any held-out list
(heldout.py: the pool seal, its reserve, every Round 10 D35 draw, the pool list, the ImageCAS-X seal) is
refused before download: Janus-M never reads those patients.

Usage: python fetch_ts_cardiac.py OUT_DIR [N]
"""
import csv, io, sys, pathlib
from remotezip import RemoteZip

URL = "https://zenodo.org/records/6802614/files/Totalsegmentator_dataset.zip?download=1"
STUDY = ("ct heart", "ct coronary arteries", "ct aortic valve")
MASKS = ("heart_myocardium", "heart_ventricle_left", "heart_ventricle_right",
         "heart_atrium_left", "heart_atrium_right", "aorta")
REPO = pathlib.Path(__file__).resolve().parents[3]


def excluded_ids():
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from heldout import refused_totalseg_ids
    return refused_totalseg_ids()


def main(out, n):
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    bad = excluded_ids()
    print(f"excluding {len(bad)} pool ids: {sorted(bad)}")
    with RemoteZip(URL) as z:
        meta = z.read("Totalsegmentator_dataset/meta.csv").decode("utf-8-sig")
        rows = [r for r in csv.DictReader(io.StringIO(meta), delimiter=";")
                if r["study_type"].strip() in STUDY and r["image_id"] not in bad]
        rows.sort(key=lambda r: r["image_id"])
        (out / "chosen.csv").write_text("image_id;study_type;split\n" + "".join(
            f"{r['image_id']};{r['study_type'].strip()};{r['split']}\n" for r in rows[:n]))
        for r in rows[:n]:
            sid = r["image_id"]; base = f"Totalsegmentator_dataset/{sid}/"
            for m in ["ct.nii.gz"] + [f"segmentations/{k}.nii.gz" for k in MASKS]:
                if not (out / base / m).exists():
                    z.extract(base + m, out)
            print(sid, r["study_type"].strip(), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 30)
