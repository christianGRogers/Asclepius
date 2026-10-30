"""Golf E1: which SegQueue14 pool volumes can Janus-M touch at all?

Excluded (README "Binding from the project"; D27/D32/D33, D35, A33/A34):
  - every volume of a sealed pool patient (primary + report-only), via segtrain.pool_seal;
  - every patient of the three D35 candidate draws (A33 freezes their union until Q1);
  - every patient on the seal's extension order (the A34 reserve: untrained, uninspected).
Reads only repository JSON/text; no image is opened.  Output: census.json next to this file.
Usage: python experiments/JanusM/Golf/census.py
"""
import json, collections, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from segtrain.pool_seal import load_pool_seal, ingest_patient, _stem  # noqa: E402

DRAWS = ["experiments/Delta/r10/d35_decision_set_proposal.json",
         "experiments/Atlas/r10/decision_set_proposal.json",
         "experiments/Bridge/r10/decision_set_proposal.json"]
# What each source carries that matters for the myocardium (from tools/ccta/ingest_open.py and the sourcing notes).
MYO_NOTES = {
    "ImageCHD": "label.nii.gz has myocardium (5), LV (1), RV (2): congenital, mostly children",
    "Mendeley-SDN-cy54ttk3fj": "40 normal rest-perfusion CCTA (Punzo 2020), diastolic + systolic recon",
    "Figshare-EpicardialFat-CE": "epicardial fat mask",
    "TotalSegmentator-cardiac": "TotalSegmentator myocardium/LV/RV labels exist (1.5 mm)",
}


def main():
    seal = load_pool_seal()
    pool = [l.strip() for l in (ROOT / "configs/segqueue14/pool-2026-10.txt").read_text().splitlines()
            if l.strip() and not l.startswith("#")]
    sealed_json = json.loads((ROOT / "configs/segqueue14/sealed-pool-2026-10.json").read_text())
    reserve = set(sealed_json["primary"].get("extension_order", []))
    d35 = set()
    for p in DRAWS:
        d = json.loads((ROOT / p).read_text())
        d35 |= set(d.get("patients") or d["decision_set"]["patients"])
    d35_ingest = {ingest_patient(p) or p for p in d35} | d35
    reserve_ingest = {ingest_patient(p) or p for p in reserve} | reserve

    rows = collections.defaultdict(lambda: collections.Counter())
    allowed = []
    for v in pool:
        src = v.split("__")[0]
        pat = ingest_patient(_stem(v))
        rows[src]["volumes"] += 1
        if seal.is_sealed(v):
            rows[src]["sealed"] += 1
        elif pat in d35_ingest:
            rows[src]["d35_draws"] += 1
        elif pat in reserve_ingest:
            rows[src]["reserve"] += 1
        else:
            rows[src]["janusm_allowed"] += 1
            allowed.append(v)
    pats = collections.defaultdict(set)
    for v in allowed:
        pats[v.split("__")[0]].add(ingest_patient(_stem(v)))
    out = {"seal_sha256": seal.sha256, "n_pool_volumes": len(pool), "n_allowed_volumes": len(allowed),
           "n_allowed_patients": sum(len(s) for s in pats.values()),
           "by_source": {s: dict(c, allowed_patients=len(pats[s]), myocardium_note=MYO_NOTES.get(s, ""))
                         for s, c in sorted(rows.items())},
           "allowed_volumes": allowed}
    (Path(__file__).parent / "census.json").write_text(json.dumps(out, indent=1))
    print(f"pool {len(pool)} volumes; Janus-M allowed {len(allowed)} volumes, {out['n_allowed_patients']} patients")
    print(f"{'source':40s} vol sealed d35 reserve allowed(pat)")
    for s, c in sorted(rows.items()):
        print(f"{s:40s} {c['volumes']:3d} {c['sealed']:6d} {c['d35_draws']:3d} {c['reserve']:7d} "
              f"{c['janusm_allowed']:4d} ({len(pats[s])})")


if __name__ == "__main__":
    main()
