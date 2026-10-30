"""The per-wave anchoring report: do readers follow the seed? (JA7, JA21, JA47)

For every double-read case of a wave, per border (endocardial, epicardial):

* **seed-vs-read ASSD**, for each of the two reads (voxel ASSD, as JA39 keeps it);
* **inter-read ASSD**, between the two reads;
* **share of voxels changed** from the seed, per read: voxels whose class differs
  from the seed's, over voxels labelled in either;
* the **half-maximum offsets** (canonical sign, JA44) of the seed and of each read,
  when the manifest gives them or the CT to measure them on.

Blank cases (10 seal cases read with no seed) still have a seed -- it is computed for
every case and simply not served -- so the same numbers exist for them.

**Rule 1 (JA47).** Per border,

    gap = mean seed-vs-read ASSD on blank-case reads - the same on seeded-case reads

and seeded reads **cannot accept a model** if the upper 95 % bound of
``gap - mean seeded inter-read ASSD`` exceeds :data:`RULE1_MARGIN_MM` (0.2 mm) on
either border. The bound is a **two-sample** bootstrap: blank and seeded cases are
resampled independently (no case has both a blank and a seeded read), 2 000 draws,
fixed seed.

**Rule 2 (JA47).** If more than half of a wave's seeded reads change less than 5 % of
seed voxels, the wave is **flagged**. Then 5 of its seeded cases, drawn by salted hash,
get a third read from blank by a reader who has not read them, and Rule 1 is
evaluated on them: the third reads take the blank side, the same cases' seeded reads
the seeded side. Third reads never enter the reference standard.

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

from . import BORDER_PROTOCOL
from . import labels as L

BORDERS = ("endocardial", "epicardial")

#: Rule 1: the upper bound of (gap - seeded inter-read ASSD) may not exceed this (mm).
RULE1_MARGIN_MM = 0.2
#: Rule 1's bootstrap: draws, seed, and the one-sided bound.
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 20261030
BOUND_QUANTILE = 0.95
#: Rule 2: a seeded read changing less than this share of seed voxels "follows" it,
#: and a wave where more than half do is flagged.
RULE2_CHANGED_SHARE = 0.05
RULE2_READS_SHARE = 0.5
#: Rule 2: how many seeded cases get a third read from blank, and the hash salt.
THIRD_READ_CASES = 5
THIRD_READ_SALT = "asclepius-janusm-third-read-r1:"


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
    #: Half-maximum offsets (mm, canonical sign): {"seed": {border: mm}, "reads": [...]}.
    halfmax: Dict[str, object] = field(default_factory=dict)
    #: Rule 2: seed-vs-read ASSD of a third read from blank, by border (None: no third read).
    third_vs_seed: Optional[Dict[str, Optional[float]]] = None

    def to_dict(self) -> dict:
        out = {"case": self.case, "blank": self.blank, "seedVsRead": self.seed_vs_read,
               "interRead": self.inter_read, "changedShare": self.changed,
               "halfMaxOffsets": self.halfmax}
        if self.third_vs_seed is not None:
            out["thirdReadVsSeed"] = self.third_vs_seed
        return out


def case_anchoring(case: str, seed: np.ndarray, reads: Sequence[np.ndarray], spacing,
                   blank: bool, third: Optional[np.ndarray] = None,
                   halfmax: Optional[dict] = None) -> CaseAnchoring:
    if len(reads) != 2:
        raise ValueError(f"{case}: an anchoring row needs exactly two reads, got {len(reads)}")
    out = CaseAnchoring(case=case, blank=bool(blank), halfmax=dict(halfmax or {}))
    for border in BORDERS:
        s = border_region(seed, border)
        r = [border_region(x, border) for x in reads]
        out.seed_vs_read[border] = [assd(s, x, spacing) for x in r]
        out.inter_read[border] = assd(r[0], r[1], spacing)
    out.changed = [changed_share(seed, x) for x in reads]
    if third is not None:
        out.third_vs_seed = {b: assd(border_region(seed, b), border_region(third, b), spacing)
                             for b in BORDERS}
    return out


def halfmax_offsets(labels: np.ndarray, ct: np.ndarray, spacing) -> Dict[str, Optional[float]]:
    """Whole-border half-maximum offsets (mm, canonical sign) of one label volume."""
    from .checker import check_read

    return check_read(labels, ct, spacing).offsets()


def _mean(values: Iterable[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return float(np.mean(vals)) if vals else None


def _case_values(row: CaseAnchoring, border: str, third: bool = False):
    """One case's (mean seed-vs-read ASSD, inter-read ASSD) on a border; None if missing."""
    if third:
        svr = [None if row.third_vs_seed is None else row.third_vs_seed.get(border)]
    else:
        svr = row.seed_vs_read[border]
    vals = [v for v in svr if v is not None]
    return (float(np.mean(vals)) if vals else None, row.inter_read[border])


def rule1_bound(blank_svr: Sequence[float], seeded_svr: Sequence[float],
                seeded_inter: Sequence[float], draws: int = BOOTSTRAP_DRAWS,
                seed: int = BOOTSTRAP_SEED) -> Optional[dict]:
    """JA47 Rule 1 on one border: the statistic, and its upper 95 % bound from a
    two-sample bootstrap (blank and seeded cases resampled independently; each seeded
    case keeps its own seed-vs-read and inter-read values together). None when either
    sample is empty."""
    b = np.asarray([v for v in blank_svr if v is not None], dtype=float)
    pairs = [(s, i) for s, i in zip(seeded_svr, seeded_inter) if s is not None and i is not None]
    if not b.size or not pairs:
        return None
    s = np.asarray([p[0] for p in pairs], dtype=float)
    i = np.asarray([p[1] for p in pairs], dtype=float)
    gap = float(b.mean() - s.mean())
    stat = gap - float(i.mean())
    rng = np.random.default_rng(seed)
    bi = rng.integers(0, b.size, size=(draws, b.size))
    si = rng.integers(0, s.size, size=(draws, s.size))
    boot = b[bi].mean(axis=1) - s[si].mean(axis=1) - i[si].mean(axis=1)
    upper = float(np.quantile(boot, BOUND_QUANTILE))
    return {"gap": gap, "interReadSeeded": float(i.mean()), "statistic": stat,
            "upper95": upper, "blankCases": int(b.size), "seededCases": int(s.size),
            "exceeds": bool(upper > RULE1_MARGIN_MM)}


def third_read_cases(wave: str, seeded_cases: Iterable[str], n: int = THIRD_READ_CASES,
                     ) -> List[str]:
    """Rule 2's draw: the ``n`` seeded cases of a wave with the lowest
    ``sha256(salt + wave + ":" + case)``. Stable whatever order the cases come in."""
    import hashlib

    def key(case):
        return hashlib.sha256(f"{THIRD_READ_SALT}{wave}:{case}".encode()).hexdigest()

    return sorted(sorted(set(seeded_cases)), key=key)[:n]


def _rule1(blank_rows, seeded_rows, third=False) -> Dict[str, Optional[dict]]:
    out = {}
    for border in BORDERS:
        bvals = [_case_values(r, border, third=third)[0] for r in blank_rows]
        svals = [_case_values(r, border) for r in seeded_rows]
        out[border] = rule1_bound(bvals, [v[0] for v in svals], [v[1] for v in svals])
    return out


def _verdict(rule1: Dict[str, Optional[dict]]) -> Optional[bool]:
    """True: seeded reads may accept a model; False: they cannot; None: not evaluable."""
    if any(v is None for v in rule1.values()):
        return None
    return not any(v["exceeds"] for v in rule1.values())


def _median(values) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return float(np.median(vals)) if vals else None


def _offset_summary(rows: Sequence[CaseAnchoring]) -> dict:
    """Median half-maximum offsets (canonical) of the seeds and the reads, per border."""
    names = sorted({k for r in rows for k in (r.halfmax.get("seed") or {})}
                   | {k for r in rows for x in (r.halfmax.get("reads") or []) for k in (x or {})})
    out = {}
    for name in names:
        out[name] = {
            "seedMedian": _median((r.halfmax.get("seed") or {}).get(name) for r in rows),
            "readMedian": _median((x or {}).get(name) for r in rows
                                  for x in (r.halfmax.get("reads") or [])),
        }
    return out


def wave_report(wave: str, rows: Sequence[CaseAnchoring]) -> dict:
    """Aggregate one wave under JA47's two rules."""
    seeded = [r for r in rows if not r.blank]
    blank = [r for r in rows if r.blank]
    borders = {}
    rule1 = _rule1(blank, seeded)
    for border in BORDERS:
        borders[border] = {
            "seedVsReadSeeded": _mean(v for r in seeded for v in r.seed_vs_read[border]),
            "seedVsReadBlank": _mean(v for r in blank for v in r.seed_vs_read[border]),
            "interReadSeeded": _mean(r.inter_read[border] for r in seeded),
            "interReadBlank": _mean(r.inter_read[border] for r in blank),
            "rule1": rule1[border],
        }

    # Rule 2: do the seeded reads follow the seed?
    seeded_changes = [v for r in seeded for v in r.changed if v is not None]
    following = sum(1 for v in seeded_changes if v < RULE2_CHANGED_SHARE)
    flagged = bool(seeded_changes) and following > RULE2_READS_SHARE * len(seeded_changes)
    rule2 = {"seededReads": len(seeded_changes), "readsChangingUnder5pct": following,
             "flagged": flagged, "thirdReadCases": [], "rule1OnThirdReads": None,
             "thirdReadsDone": 0}
    verdict = _verdict(rule1)
    if flagged:
        drawn = third_read_cases(wave, [r.case for r in seeded])
        done = [r for r in seeded if r.case in drawn and r.third_vs_seed is not None]
        rule2["thirdReadCases"] = drawn
        rule2["thirdReadsDone"] = len(done)
        if len(done) == len(drawn):
            third = _rule1(done, done, third=True)
            rule2["rule1OnThirdReads"] = third
            v3 = _verdict(third)
            verdict = None if verdict is None or v3 is None else (verdict and v3)
        else:
            verdict = None if verdict is None else (False if verdict is False else None)

    return {
        "wave": wave,
        "border_protocol": BORDER_PROTOCOL,
        "cases": len(rows), "seededCases": len(seeded), "blankCases": len(blank),
        "changedShareSeeded": _mean(v for r in seeded for v in r.changed),
        "changedShareBlank": _mean(v for r in blank for v in r.changed),
        "borders": borders,
        "rule2": rule2,
        "halfMaxOffsets": _offset_summary(rows),
        # JA47: seeded reads that fail Rule 1 (or Rule 1 on a flagged wave's third
        # reads) cannot accept a model. None: not evaluable yet.
        "seededReadsMayAcceptModel": verdict,
        "rule": ("JA47 rule 1: seeded reads cannot accept a model if the upper 95 % "
                 "two-sample bootstrap bound of (mean blank seed-vs-read ASSD - mean "
                 "seeded seed-vs-read ASSD - mean seeded inter-read ASSD) exceeds "
                 f"{RULE1_MARGIN_MM:g} mm on either border ({BOOTSTRAP_DRAWS} draws, seed "
                 f"{BOOTSTRAP_SEED}). Rule 2: a wave where more than half of the seeded "
                 f"reads change < {RULE2_CHANGED_SHARE:.0%} of seed voxels is flagged; "
                 f"{THIRD_READ_CASES} of its seeded cases get a third read from blank and "
                 "rule 1 is evaluated on them. Third reads never enter the reference "
                 "standard."),
        "rows": [r.to_dict() for r in rows],
    }


def _load(path):
    import nibabel as nib

    img = nib.load(str(path))
    return np.asarray(img.dataobj).astype(np.int16), img


def _load_ct(path):
    import nibabel as nib

    return np.asarray(nib.load(str(path)).dataobj, dtype=np.float32)


def report_from_manifest(manifest_path) -> dict:
    """Build the report from a manifest::

        {"wave": "1", "cases": [{"case": "c0001", "blank": false,
                                  "seed": "seeds/c0001.janusm-seed.nii.gz",
                                  "reads": ["reads/c0001__a.nii.gz", "reads/c0001__b.nii.gz"],
                                  "thirdRead": "reads/c0001__third.nii.gz",      # optional
                                  "halfMaxOffsets": {"seed": {...}, "reads": [{...}, {...}]},
                                  "ct": "cts/c0001.nii.gz"}]}                    # optional

    Paths are relative to the manifest. ``halfMaxOffsets`` (canonical sign) come from
    the export; without them, and with a ``ct``, they are measured here.

    Every case must be a frozen Janus-M read case and goes through the JA12 guard first,
    under its set's scoring purpose; the whole report is refused on any hit.
    """
    from . import holdout, readset

    manifest_path = Path(manifest_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    holdout.refuse_read_cases([c["case"] for c in data["cases"]], readset.load_freeze(),
                              what="the anchoring report")
    base = manifest_path.parent
    rows = []
    for c in data["cases"]:
        seed, img = _load(base / c["seed"])
        reads = [_load(base / p)[0] for p in c["reads"]]
        for p, r in zip(c["reads"], reads):
            if r.shape != seed.shape:
                raise ValueError(f"{c['case']}: {p} is not on the seed's grid")
        spacing = img.header.get_zooms()[:3]
        third = None
        if c.get("thirdRead"):
            third = _load(base / c["thirdRead"])[0]
            if third.shape != seed.shape:
                raise ValueError(f"{c['case']}: its third read is not on the seed's grid")
        offsets = c.get("halfMaxOffsets")
        if not offsets and c.get("ct"):
            ct = np.asarray(_load_ct(base / c["ct"]), dtype=np.float32)
            offsets = {"seed": halfmax_offsets(seed, ct, spacing),
                       "reads": [halfmax_offsets(r, ct, spacing) for r in reads]}
        rows.append(case_anchoring(c["case"], seed, reads, spacing, bool(c.get("blank")),
                                   third=third, halfmax=offsets))
    return wave_report(str(data.get("wave", "")), rows)


def main(argv=None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Janus-M per-wave anchoring report (JA47).")
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
