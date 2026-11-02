"""The per-wave anchoring report: do readers follow the seed? (JA7, JA21, JA47)

For every double-read case of a wave, per border (endocardial, epicardial):

* **seed-vs-read ASSD**, for each of the two reads (voxel ASSD, as JA39 keeps it);
* **inter-read ASSD**, between the two reads;
* **share of seed voxels changed**, per read: voxels (within seed or read) whose
  class differs from the seed's, over the seed's foreground voxels (JA68);
* the **half-maximum offsets** (canonical sign, JA44) of the seed and of each read,
  when the manifest gives them or the CT to measure them on.

Blank cases (10 seal cases read with no seed) still have a seed -- it is computed for
every case and simply not served -- so the same numbers exist for them.

**Rule 1 (JA47, JA68).** Per border,

    gap = mean seed-vs-read ASSD on blank-case reads - the same on seeded-case reads

with both means taken over **reads** (the report's ``seedVsReadBlank`` and
``seedVsReadSeeded``), and seeded reads **cannot accept a model** if the upper 95 %
bound of ``gap - mean seeded inter-read ASSD`` exceeds :data:`RULE1_MARGIN_MM`
(0.2 mm) on either border. The bound is a **two-sample** bootstrap **by case**: blank
and seeded cases are resampled independently (no case has both a blank and a seeded
read; two separate draws from one generator, blank first), 2 000 draws, seed
:data:`BOOTSTRAP_SEED`, the 0.95 quantile; each draw recomputes the read-level means
over the cases it drew.

**Rule 2 (JA47, JA68).** If more than half of a wave's seeded reads change less than
5 % of seed voxels, the wave is **flagged** (exactly half is not). Then 5 of its
seeded cases, drawn by salted hash, get a third read from blank by a reader who has
not read them, and Rule 1 is
evaluated on them: the third reads take the blank side, the same cases' seeded reads
the seeded side. Third reads never enter the reference standard.

Borders are surfaces of regions: endocardial = the LV pool (2); epicardial = the
LV pool and myocardium together (1 + 2).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from segtrain.metrics import surface_distances

from . import BORDER_PROTOCOL
from . import labels as L

# Rule 2's flag (a seeded read "follows" below RULE2_CHANGED_SHARE; a wave is flagged
# when more than RULE2_READS_SHARE of its seeded reads do), how many seeded cases get a
# third read from blank, the hash salt, and the draw itself. In the stdlib half, so the
# queue's server recomputes the same flag (JA78) and enforces the same draw.
from .readset import (  # noqa: F401
    RULE2_CHANGED_SHARE,
    RULE2_READS_SHARE,
    THIRD_READ_CASES,
    THIRD_READ_SALT,
    rule2,
    third_read_cases,
)

BORDERS = ("endocardial", "epicardial")

#: Rule 1: the upper bound of (gap - seeded inter-read ASSD) may not exceed this (mm).
RULE1_MARGIN_MM = 0.2
#: Rule 1's bootstrap: draws, seed, and the one-sided bound.
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 20261030
BOUND_QUANTILE = 0.95


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
    """JA68: voxels whose class differs from the seed's (within seed or read), over
    the seed's foreground voxels. None for an empty seed."""
    n = int((seed > 0).sum())
    if n == 0:
        return None
    either = (seed > 0) | (read > 0)
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
    """One case's (seed-vs-read ASSDs of its reads, inter-read ASSD) on a border."""
    if third:
        svr = [None if row.third_vs_seed is None else row.third_vs_seed.get(border)]
    else:
        svr = row.seed_vs_read[border]
    return [v for v in svr if v is not None], row.inter_read[border]


def _reads_of(value) -> List[float]:
    """A case's read values: a list (None dropped), or a bare number for one read."""
    if value is None:
        return []
    items = value if isinstance(value, (list, tuple)) else [value]
    return [float(x) for x in items if x is not None]


def _sums(rows: Sequence[List[float]]) -> Tuple[np.ndarray, np.ndarray]:
    return (np.asarray([sum(r) for r in rows], dtype=float),
            np.asarray([len(r) for r in rows], dtype=float))


def rule1_bound(blank_svr: Sequence, seeded_svr: Sequence, seeded_inter: Sequence,
                draws: int = BOOTSTRAP_DRAWS, seed: int = BOOTSTRAP_SEED) -> Optional[dict]:
    """JA47 Rule 1 on one border, as JA68 pins it.

    ``blank_svr`` and ``seeded_svr`` hold, per case, the seed-vs-read ASSDs of its reads
    (a list; a bare number is one read; None values are dropped, and a case with none
    left is not in the sample). ``seeded_inter`` is each seeded case's inter-read
    ASSD, in the same order (None: the case adds nothing to the inter-read mean).

    ``gap`` = read-level mean of the blank values - read-level mean of the seeded
    values, so it equals the report's ``seedVsReadBlank - seedVsReadSeeded``. The
    bound is a two-sample bootstrap by case: ``default_rng(seed)`` draws the blank
    cases' indices, then, independently, the seeded cases' (each seeded case keeps its
    reads and its inter-read value together); each draw recomputes the read-level
    means and the inter-read mean; ``upper95`` is the 0.95 quantile. None when either
    sample is empty or no seeded case has an inter-read value.
    """
    b_sum, b_n = _sums([r for r in map(_reads_of, blank_svr) if r])
    seeded = [(_reads_of(v), i) for v, i in zip(seeded_svr, seeded_inter)]
    seeded = [(r, i) for r, i in seeded if r]
    s_sum, s_n = _sums([r for r, _ in seeded])
    has = np.asarray([i is not None for _, i in seeded], dtype=float)
    i_val = np.asarray([0.0 if i is None else float(i) for _, i in seeded], dtype=float)
    if not b_sum.size or not s_sum.size or not has.any():
        return None
    gap = float(b_sum.sum() / b_n.sum() - s_sum.sum() / s_n.sum())
    inter_mean = float(i_val.sum() / has.sum())
    stat = gap - inter_mean
    rng = np.random.default_rng(seed)
    bi = rng.integers(0, b_sum.size, size=(draws, b_sum.size))
    si = rng.integers(0, s_sum.size, size=(draws, s_sum.size))
    with np.errstate(invalid="ignore", divide="ignore"):
        boot = (b_sum[bi].sum(axis=1) / b_n[bi].sum(axis=1)
                - s_sum[si].sum(axis=1) / s_n[si].sum(axis=1)
                - i_val[si].sum(axis=1) / has[si].sum(axis=1))
    upper = float(np.nanquantile(boot, BOUND_QUANTILE))
    return {"gap": gap, "interReadSeeded": inter_mean, "statistic": stat,
            "upper95": upper, "blankCases": int(b_sum.size), "seededCases": int(s_sum.size),
            "exceeds": bool(upper > RULE1_MARGIN_MM)}


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
    rule2_ = rule2(v for r in seeded for v in r.changed)
    flagged = rule2_["flagged"]
    rule2_.update({"thirdReadCases": [], "rule1OnThirdReads": None, "thirdReadsDone": 0})
    verdict = _verdict(rule1)
    if flagged:
        drawn = third_read_cases(wave, [r.case for r in seeded])
        done = [r for r in seeded if r.case in drawn and r.third_vs_seed is not None]
        rule2_["thirdReadCases"] = drawn
        rule2_["thirdReadsDone"] = len(done)
        if len(done) == len(drawn):
            third = _rule1(done, done, third=True)
            rule2_["rule1OnThirdReads"] = third
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
        "rule2": rule2_,
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
