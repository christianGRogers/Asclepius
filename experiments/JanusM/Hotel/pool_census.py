"""Hotel E3: what the project's CCTA pool can give Janus-M, with the coronary seals kept out.

Reads only repository files (no CT, no Girder):
  - the 2026-10 QC report (one row per pool volume),
  - the D27 pool seal (patients, volumes, extension order = the A34 reserve),
  - every Round 10 D35 decision-set draft (Atlas, Bridge, Crucible, Delta, Foxtrot); until the
    set is frozen, Janus-M treats the union of all drafts as off limits (the cautious reading of A33).
A patient is excluded from Janus-M if any of its volumes is sealed, reserved or in any D35 draft.
For the rest it counts what layer analysis needs: whole heart in view, good contrast, in-plane
spacing <= 0.5 mm, and patients with more than one volume (possible multi-phase).

Usage: python pool_census.py OUT_JSON   (run from the repository root)
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "src")
from segtrain.pool_seal import _stem, ingest_patient, load_pool_seal  # noqa: E402

QC = Path("vault/Research/Datasets and benchmarks/CCTA sourcing 2026-10/QC volume reports.csv")
D35_DRAFTS = [
    "experiments/Atlas/r10/decision_set_proposal.json",
    "experiments/Bridge/r10/decision_set_proposal.json",
    "experiments/Crucible/r10/d35_proposal.json",
    "experiments/Delta/r10/d35_decision_set_proposal.json",
    "experiments/Foxtrot/r10/d35_proposal.json",
]


def strings(x):
    """Every string inside a JSON value."""
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


def in_plane(res: str):
    m = re.match(r"\s*([\d.]+)\s*x\s*([\d.]+)\s*x\s*([\d.]+)", res or "")
    return (float(m.group(1)), float(m.group(3))) if m else (None, None)


def main(out: Path) -> None:
    seal = load_pool_seal()
    rows = list(csv.DictReader(QC.open()))
    pat_of = {r["name"]: ingest_patient(_stem(r["name"])) for r in rows}
    reserve = set()
    for e in seal.extension_order:
        reserve.add(e if isinstance(e, str) else json.dumps(e))
    d35 = set()
    for f in D35_DRAFTS:
        d = json.loads(Path(f).read_text())
        if "Foxtrot" in f:
            d = d.get("proposed_d35", d)
        for s in strings(d.get("patients", d) if isinstance(d, dict) else d):
            d35.add(s)
    status = {}
    by_pat = defaultdict(list)
    for r in rows:
        by_pat[pat_of[r["name"]]].append(r)
    for p, rs in by_pat.items():
        why = None
        if any(seal.is_sealed(r["name"]) for r in rs) or p in seal.patients:
            why = "coronary seal (D27/D32/D33)"
        elif p in reserve:
            why = "seal reserve (A34)"
        elif p in d35 or any(_stem(r["name"]) in d35 for r in rs):
            why = "a D35 draft (union)"
        elif p and p.startswith("ImageCHD"):
            why = "free: ImageCHD (congenital, own stratum)"
        else:
            why = "free"
        status[p] = why
    res = {"n_volumes": len(rows), "n_patients": len(by_pat),
           "patients_by_status": Counter(status.values()),
           "d35_draft_union_size": len(d35)}
    free = [p for p, s in status.items() if s == "free"]
    good = []
    multi = []
    src_count = Counter()
    for p in free:
        rs = by_pat[p]
        ok = [r for r in rs if r["heart_in_fov"].strip().lower() == "full"
              and r["contrast"].strip().lower() == "good"]
        fine = [r for r in ok if (in_plane(r["resolution"])[0] or 9) <= 0.5]
        if fine:
            good.append(p)
            src_count[p.split("__")[0]] += 1
        if len(rs) > 1:
            multi.append(p)
    res["free_patients"] = len(free)
    res["free_whole_heart_good_contrast_inplane_le_0p5mm"] = len(good)
    res["free_layer_ready_by_source"] = dict(src_count.most_common())
    relaxed = Counter()
    for p in free:
        rs = by_pat[p]
        if any(r["heart_in_fov"].strip().lower() == "full" and r["contrast"].strip().lower() in ("good", "moderate")
               and (in_plane(r["resolution"])[0] or 9) <= 0.5 for r in rs):
            relaxed[p.split("__")[0]] += 1
    res["free_whole_heart_good_or_moderate_inplane_le_0p5mm"] = sum(relaxed.values())
    res["free_relaxed_by_source"] = dict(relaxed.most_common())
    res["free_by_source"] = dict(Counter(p.split("__")[0] for p in free).most_common())
    res["free_multi_volume_patients"] = len(multi)
    res["free_multi_volume_examples"] = sorted(multi)[:15]
    res["field_values"] = {k: Counter(r[k] for r in rows).most_common(8) for k in ("heart_in_fov", "contrast")}
    res["inplane_spacing_all"] = Counter(
        ("<=0.4" if (x := in_plane(r["resolution"])[0]) is not None and x <= 0.4 else
         "0.4-0.5" if x is not None and x <= 0.5 else ">0.5" if x is not None else "unknown") for r in rows)
    # the Janus-M Round 1 volume list: every volume of a free (non-ImageCHD) patient that has the whole
    # heart, good or moderate contrast and in-plane spacing <= 0.5 mm; re-checked by the guard
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from coronary_holdout import PoolGuard
    guard = PoolGuard()
    lines = ["# Janus-M Round 1 (Hotel): pool volumes usable for myocardial-layer work. Generated by pool_census.py.",
             "# name\titem_id (CCTA-Pool)\tsource\tresolution\tcontrast"]
    for p in sorted(free):
        for r in by_pat[p]:
            if (r["heart_in_fov"].strip().lower() == "full" and r["contrast"].strip().lower() in ("good", "moderate")
                    and (in_plane(r["resolution"])[0] or 9) <= 0.5):
                assert guard.reason(r["name"]) is None, r["name"]
                lines.append("\t".join([r["name"], r["item_id"], r["source"], r["resolution"], r["contrast"]]))
    Path(out.parent / "janusm_r1_pool_volumes.tsv").write_text("\n".join(lines) + "\n")
    res["janusm_r1_volumes"] = len(lines) - 2
    out.write_text(json.dumps(res, indent=1, default=list))
    print(json.dumps(res, indent=1, default=list))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
