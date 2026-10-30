"""The per-wave anchoring report (JA7): do readers follow the seed?

For every double-read case of a wave, per border (endocardial, epicardial):

* **seed-vs-read ASSD**, for each of the two reads;
* **inter-read ASSD**, between the two reads;
* **share of voxels changed** from the seed, per read: voxels whose class differs
  from the seed's, over voxels labelled in either.

Blank cases (JA7: 10 seal cases read with no seed) still have a seed -- it is
computed for every case and simply not served -- so the same numbers exist for them.
That is what makes the anchoring test possible:

    gap = mean seed-vs-read ASSD on blank cases - mean seed-vs-read ASSD on seeded cases

Seeded reads that sit closer to the seed than unseeded reads do are anchored. JA7:
"if blank reads differ from seeded reads by more than the inter-read difference,
seeded reads cannot accept a model". Here that is ``gap > mean inter-read ASSD on
seeded cases``, per border. **This reading of JA7, and the threshold, are
placeholders until Round 2 sets the anchoring thresholds** (protocol §6).

Borders are surfaces of regions: endocardial = the LV pool (2); epicardial = the
LV pool and myocardium together (1 + 2).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

from segtrain.metrics import surface_distances

from . import labels as L

BORDERS = ("endocardial", "epicardial")


def border_region(read: np.ndarray, border: str) -> np.ndarray:
    if border == "endocardial":
        return read == L.LV_POOL
    if border == "epicardial":
        return np.isin(read, (L.LV_MYO, L.LV_POOL))
    raise ValueError(border)


def assd(a: np.ndarray, b: np.ndarray, spacing) -> Optional[float]:
    """Average symmetric surface distance (mm) between two masks; None if either is empty."""
    d_ab, d_ba = surface_distances(a, b, spacing)
    if d_ab.size == 0 or d_ba.size == 0:
        return None
    return float((d_ab.sum() + d_ba.sum()) / (d_ab.size + d_ba.size))


def changed_share(seed: np.ndarray, read: np.ndarray) -> Optional[float]:
    either = (seed > 0) | (read > 0)
    n = int(either.sum())
    if n == 0:
        return None
    return float(((seed != read) & either).sum() / n)


@dataclass
class CaseAnchoring:
    case: str
    blank: bool
    seed_vs_read: Dict[str, List[Optional[float]]] = field(default_factory=dict)
    inter_read: Dict[str, Optional[float]] = field(default_factory=dict)
    changed: List[Optional[float]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"case": self.case, "blank": self.blank, "seedVsRead": self.seed_vs_read,
                "interRead": self.inter_read, "changedShare": self.changed}


def case_anchoring(case: str, seed: np.ndarray, reads: Sequence[np.ndarray], spacing,
                   blank: bool) -> CaseAnchoring:
    if len(reads) != 2:
        raise ValueError(f"{case}: an anchoring row needs exactly two reads, got {len(reads)}")
    out = CaseAnchoring(case=case, blank=bool(blank))
    for border in BORDERS:
        s = border_region(seed, border)
        r = [border_region(x, border) for x in reads]
        out.seed_vs_read[border] = [assd(s, x, spacing) for x in r]
        out.inter_read[border] = assd(r[0], r[1], spacing)
    out.changed = [changed_share(seed, x) for x in reads]
    return out


def _mean(values: Iterable[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return float(np.mean(vals)) if vals else None


def wave_report(wave: str, rows: Sequence[CaseAnchoring]) -> dict:
    """Aggregate one wave. ``anchored`` is None when there are no blank (or no
    seeded) cases in the wave to compare."""
    seeded = [r for r in rows if not r.blank]
    blank = [r for r in rows if r.blank]
    borders = {}
    for border in BORDERS:
        svr_seeded = _mean(v for r in seeded for v in r.seed_vs_read[border])
        svr_blank = _mean(v for r in blank for v in r.seed_vs_read[border])
        inter_seeded = _mean(r.inter_read[border] for r in seeded)
        inter_blank = _mean(r.inter_read[border] for r in blank)
        gap = (None if svr_seeded is None or svr_blank is None
               else svr_blank - svr_seeded)
        anchored = None if gap is None or inter_seeded is None else bool(gap > inter_seeded)
        borders[border] = {
            "seedVsReadSeeded": svr_seeded, "seedVsReadBlank": svr_blank,
            "interReadSeeded": inter_seeded, "interReadBlank": inter_blank,
            "gap": gap, "anchored": anchored,
        }
    anchored = [b["anchored"] for b in borders.values()]
    return {
        "wave": wave,
        "cases": len(rows), "seededCases": len(seeded), "blankCases": len(blank),
        "changedShareSeeded": _mean(v for r in seeded for v in r.changed),
        "changedShareBlank": _mean(v for r in blank for v in r.changed),
        "borders": borders,
        # JA7: anchored seeded reads cannot accept a model.
        "seededReadsMayAcceptModel": (None if any(a is None for a in anchored)
                                      else not any(anchored)),
        "rule": "anchored if mean seed-vs-read ASSD (blank) - (seeded) > mean inter-read "
                "ASSD (seeded); placeholder until Round 2 (protocol section 6)",
        "rows": [r.to_dict() for r in rows],
    }


def _load(path):
    import nibabel as nib

    img = nib.load(str(path))
    return np.asarray(img.dataobj).astype(np.int16), img


def report_from_manifest(manifest_path) -> dict:
    """Build the report from a manifest::

        {"wave": "1", "cases": [{"case": "c0001", "blank": false,
                                  "seed": "seeds/c0001.janusm-seed.nii.gz",
                                  "reads": ["reads/c0001__a.nii.gz", "reads/c0001__b.nii.gz"]}]}

    Paths are relative to the manifest. Every case goes through the hold-out guard
    first, and the whole report is refused on any hit (JA12).
    """
    from . import holdout

    manifest_path = Path(manifest_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    holdout.refuse([c["case"] for c in data["cases"]], what="the anchoring report")
    base = manifest_path.parent
    rows = []
    for c in data["cases"]:
        seed, img = _load(base / c["seed"])
        reads = [_load(base / p)[0] for p in c["reads"]]
        for p, r in zip(c["reads"], reads):
            if r.shape != seed.shape:
                raise ValueError(f"{c['case']}: {p} is not on the seed's grid")
        spacing = img.header.get_zooms()[:3]
        rows.append(case_anchoring(c["case"], seed, reads, spacing, bool(c.get("blank"))))
    return wave_report(str(data.get("wave", "")), rows)


def main(argv=None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Janus-M per-wave anchoring report (JA7).")
    p.add_argument("manifest")
    p.add_argument("--out", help="write the JSON here as well as printing it")
    args = p.parse_args(argv)
    report = report_from_manifest(args.manifest)
    text = json.dumps(report, indent=1, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
