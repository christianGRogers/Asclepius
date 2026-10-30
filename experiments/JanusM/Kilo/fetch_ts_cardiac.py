"""Fetch cardiac cases (CT + heart masks) from the public TotalSegmentator v1 dataset.

Zenodo 6802614 (CC BY 4.0), 28 GB zip; members are read by HTTP range (remotezip), so only
the chosen cases are downloaded. Every TotalSegmentator id in any held-out list
(heldout.py: the pool seal, its reserve, every Round 10 D35 draw, the pool list, the ImageCAS-X seal) is
refused before download: Janus-M never reads those patients. Round 2: every JA12 twin (same sex and
institute, age within 5 years, any study type) is refused too.

Usage: python fetch_ts_cardiac.py OUT_DIR [N]
"""
import csv, io, sys, pathlib
from remotezip import RemoteZip

URL = "https://zenodo.org/records/6802614/files/Totalsegmentator_dataset.zip?download=1"
STUDY = ("ct heart", "ct coronary arteries", "ct aortic valve")
MASKS = ("heart_myocardium", "heart_ventricle_left", "heart_ventricle_right",
         "heart_atrium_left", "heart_atrium_right", "aorta")
REPO = pathlib.Path(__file__).resolve().parents[3]


def excluded_ids(meta_text):
    """Held-out ids plus every JA12 twin (Round 2): refused before any CT is downloaded."""
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from heldout import refused_with_twins
    direct, twins = refused_with_twins(meta_text)
    return direct, twins


def main(out, n):
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    with RemoteZip(URL) as z:
        meta = z.read("Totalsegmentator_dataset/meta.csv").decode("utf-8-sig")
        direct, twins = excluded_ids(meta)
        from janusm.guard import load_guard                  # the shared JA12 guard (#145): twins over v1 and v2
        g = load_guard()
        shared = {r["image_id"] for r in csv.DictReader(io.StringIO(meta), delimiter=";")
                  if g.reason(r["image_id"], source="TotalSegmentator")}
        bad = direct | twins | shared
        print(f"excluding {len(direct)} held-out pool ids, {len(twins)} v1 twins, {len(bad)} in all with the shared guard")
        rows = [r for r in csv.DictReader(io.StringIO(meta), delimiter=";")
                if r["study_type"].strip() in STUDY and r["image_id"] not in bad]
        rows.sort(key=lambda r: r["image_id"])
        (out / "chosen.csv").write_text("image_id;study_type;split\n" + "".join(
            f"{r['image_id']};{r['study_type'].strip()};{r['split']}\n" for r in rows[:n]))
        for r in rows[:n]:
            sid = r["image_id"]
            assert sid not in bad, sid      # second check, per case, before the first byte of its image
            base = f"Totalsegmentator_dataset/{sid}/"
            for m in ["ct.nii.gz"] + [f"segmentations/{k}.nii.gz" for k in MASKS]:
                if not (out / base / m).exists():
                    z.extract(base + m, out)
            print(sid, r["study_type"].strip(), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 30)
