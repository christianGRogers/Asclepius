"""Kilo v1: the SegQueue/cases volumes Janus-M may read, prelabel, train or score on.

Janus-M never reads, scores or trains on a coronary sealed case or a D35 decision-set patient (D37,
README). Kilo is stricter than that minimum, by patient (`segtrain.pool_seal`, D32/D33 grouping):

  refused  1. the D27/D32 pool seal, primary and report-only (the project's guard, hash-pinned);
           2. the seal's whole extension order (the A34 reserve: "untrained, unprelabelled and
              uninspected" until the seal is sized);
           4. PLOS-Peng2016 (burned-in patient text; QC report).
           3. every patient of every Round 10 D35 draw (Delta's adopted draw, and Atlas's, Bridge's
              and Crucible's), since A33 freezes all candidate draws until the lead answers Q1.
  kept     every other volume of the 904 in the QC report (`QC volume reports.csv`) with the
           whole heart in the field of view and contrast not 'none'. Coronary annotatability does
           not matter for the myocardium, so volumes left out of the coronary pool list are kept.
  flagged  spacing-suspect sets (ImageALCAPA, HOCMvalvesSeg, CCA200-HF; QC report) and the
           paediatric congenital sets: usable for training, never for a mm metric or the seal.

Output: JSON with the kept volumes (name, Girder item id, patient, source, flags) and counts.
Standard library only.  Usage: python3 allowed_volumes.py OUT.json
"""
from __future__ import annotations

import collections, csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "src"))
from segtrain.pool_seal import ingest_patient, load_pool_seal  # noqa: E402

QC = os.path.join(REPO, "vault/Research/Datasets and benchmarks/CCTA sourcing 2026-10/QC volume reports.csv")
SEAL = os.path.join(REPO, "configs/segqueue14/sealed-pool-2026-10.json")
DRAWS = {
    "Delta": ("experiments/Delta/r10/d35_decision_set_proposal.json", lambda d: d["patients"]),
    "Atlas": ("experiments/Atlas/r10/decision_set_proposal.json", lambda d: d["decision_set"]["patients"]),
    "Bridge": ("experiments/Bridge/r10/decision_set_proposal.json", lambda d: d["patients"]),
    "Crucible": ("experiments/Crucible/r10/d35_proposal.json", lambda d: d["patients"]),
}
SPACING_SUSPECT = {"ImageALCAPA", "HOCMvalvesSeg", "CCA200-HF"}
PRIVACY = {"PLOS-Peng2016-CCTA-JPEG"}  # burned-in patient text (QC report); never used
PAEDIATRIC = {"ImageCHD", "ImageALCAPA", "Slicer-SampleData"}


def main(out):
    guard = load_pool_seal(SEAL)
    seal = json.load(open(SEAL))
    reserve = {ingest_patient(p) or p for p in seal["primary"]["extension_order"]}
    d35 = set()
    for name, (path, get) in DRAWS.items():
        d35 |= {ingest_patient(p) or p for p in get(json.load(open(os.path.join(REPO, path))))}
    rows = list(csv.DictReader(open(QC)))
    kept, refused = [], collections.Counter()
    for r in rows:
        stem = r["name"][: -len(".nii.gz")]
        pat = ingest_patient(stem)
        if guard.is_sealed(stem) or guard.is_sealed(r["name"]):
            refused["sealed"] += 1
        elif pat in reserve:
            refused["reserve"] += 1
        elif pat in d35:
            refused["d35_any_draw"] += 1
        elif r["source"] in PRIVACY:
            refused["privacy_burned_in_text"] += 1
        elif r["heart_in_fov"] != "full":
            refused["heart_not_full"] += 1
        elif r["contrast"] == "none":
            refused["no_contrast"] += 1
        else:
            flags = [f for f, s in (("spacing_suspect", SPACING_SUSPECT), ("paediatric", PAEDIATRIC)) if r["source"] in s]
            kept.append({"name": r["name"], "item_id": r["item_id"], "patient": pat, "source": r["source"],
                         "contrast": r["contrast"], "quality": r["quality"], "flags": flags})
    for k in kept:  # defence in depth
        s = k["name"][: -len(".nii.gz")]
        assert not guard.is_sealed(s) and k["patient"] not in reserve and k["patient"] not in d35, s
    by_src = collections.defaultdict(lambda: [0, set()])
    for k in kept:
        by_src[k["source"]][0] += 1; by_src[k["source"]][1].add(k["patient"])
    clean = [k for k in kept if not k["flags"]]
    summary = {
        "rule": __doc__.split("Output:")[0].strip(),
        "seal_sha256": guard.sha256,
        "n_qc_volumes": len(rows), "refused_volumes": dict(refused),
        "kept_volumes": len(kept), "kept_patients": len({k["patient"] for k in kept}),
        "kept_adult_good_spacing_volumes": len(clean),
        "kept_adult_good_spacing_patients": len({k["patient"] for k in clean}),
        "by_source_[volumes,patients]": {s: [v[0], len(v[1])] for s, v in sorted(by_src.items())},
        "volumes": kept,
    }
    json.dump(summary, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("volumes", "rule")}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
