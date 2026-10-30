"""Scar-0 (JA30): a rule, no training, every candidate of the pre-registered menu.

Ruling: ``vault/JanusM/Judgements/Round 2 - paired-scar.md`` JA26 and JA30 (JA35 item 2).

Scar is a per-voxel call inside the **registered** class 1 on the LIE grid, aggregated per AHA
segment 1-17 of :mod:`janusm.geometry` (JA26). The wall, segments, depth u and E-D columns come
from :mod:`janusm.scar.registration` (:class:`~janusm.scar.common.CarriedGeometry`).

**Common steps** (:mod:`janusm.scar.common`): smooth the registered LIE (Gaussian FWHM 1.5 mm);
remote = the core voxels (one voxel inside both carried borders) of the 6 lowest-median segments,
median and robust SD (1.4826 x MAD).

**Presence candidates**

- ``P-K`` (Kilo): >= 5 % of the segment's voxels above remote + 1/2 (p99 of the brightest
  segment's core - remote);
- ``P-J`` (Juliet): extent T (E-D) >= tau, tau the p99 of T over LGE-negative development segments
  (:func:`tau_from_development`);
- ``P-G`` (Golf): >= 5 % of the segment's voxels above remote + 3 SD after a 1-voxel opening,
  ignoring 1 mm at the carried endocardium.

**Extent candidates**

- ``E-V`` (Kilo, Golf): the share of the segment's voxels above remote + 3 SD;
- ``E-D`` (Juliet): depth-binned transmural extent: per 3-degree x 2 mm column, 10 bins of u, a
  bin scar when most of its voxels pass, the column's extent the share of its bins that are scar
  (columns with at least 6 bins), averaged over the segment. The voxel cut is the half-way cut of
  P-K (Juliet E6's rule, which JA30 adopts for P-K).

**Choice** (:func:`choose_presence`, :func:`choose_extent`) is made once on development against
the double LGE read; a present segment reads at least Kim bin 1. Development may change only the
choice and tau: every other constant is fixed now (:class:`JA30Constants`) and recorded in the
output.

**Outputs per segment** (:meth:`Scar0.table`): presence; Kim bin (0 / 1-25 / 26-50 / 51-75 /
76-100 %); scar share; deepest depth u reached (the far edge of the deepest depth bin called scar
in any E-D column, with the chosen extent's voxel cut); territory. Per territory: the share of
its segments scar-present. Every output is labelled "research output, not validated" and carries
the patient's registration status; a "not graded" patient gets no grade at all.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, Mapping, Optional, Tuple

import numpy as np
from scipy import ndimage as ndi

from janusm import geometry as G
from janusm.scar import (
    NOT_GRADED,
    RESEARCH_LABEL,
    SCAR_VERSION,
    STATUSES,
    guard_case,
)
from janusm.scar.common import (
    MAD_TO_SD,
    MIN_CORE_VOXELS,
    REMOTE_N_SEGMENTS,
    SMOOTH_FWHM_MM,
    CarriedGeometry,
    remote,
    smooth,
)

PRESENCE = ("P-K", "P-J", "P-G")
EXTENT = ("E-V", "E-D")
#: Kim bin edges in percent: 0 | 1-25 | 26-50 | 51-75 | 76-100.
KIM_EDGES_PCT = (25.0, 50.0, 75.0)
#: JA30: tau is per scanner protocol when the protocol has at least this many development patients.
TAU_MIN_PATIENTS = 15
#: JA30: the presence choice needs a specificity lower bound of at least this.
MIN_SPEC_LOWER_BOUND = 0.95

_FACE = ndi.generate_binary_structure(3, 1)


@dataclass(frozen=True)
class JA30Constants:
    """Every Scar-0 constant, fixed by JA30 (development changes only the choice and tau)."""

    smooth_fwhm_mm: float = SMOOTH_FWHM_MM
    remote_n_segments: int = REMOTE_N_SEGMENTS
    mad_to_sd: float = MAD_TO_SD
    min_core_voxels: int = MIN_CORE_VOXELS
    #: A segment is graded only with more than this many carried voxels (Kilo E5).
    min_segment_voxels: int = 20
    presence_share: float = 0.05
    half_way: float = 0.5
    brightest_percentile: float = 99.0
    sd_k: float = 3.0
    endo_ignore_mm: float = 1.0
    depth_bins: int = 10
    depth_bin_majority: float = 0.5
    column_min_bins: int = 6


JA30 = JA30Constants()


def kim_bin(share, present) -> int:
    """Kim bin from a share in [0, 1]: 0 when absent; a present segment reads at least bin 1."""
    if not present:
        return 0
    pct = 0.0 if share is None or not np.isfinite(share) else 100.0 * float(share)
    return 1 + int(np.searchsorted(KIM_EDGES_PCT, pct, side="left"))


def _opened(mask):
    return ndi.binary_opening(mask, _FACE)



def _columns(cut, u, column, sel, c: JA30Constants) -> Tuple[float, float]:
    """Juliet's depth-binned columns on the voxels ``sel`` of one segment.

    Per 3-degree x 2 mm column, u is cut into ``depth_bins`` bins; a bin is scar when more than
    half its voxels pass ``cut``. Only columns spanning at least ``column_min_bins`` bins count.
    Returns (E-D extent: the mean over columns of the share of their bins that are scar; deepest
    depth u reached: the far edge of the deepest scar bin in any column), NaN when undefined.
    """
    nan = float("nan")
    col = column[sel]
    b = np.clip(np.floor(u[sel] * c.depth_bins), 0, c.depth_bins - 1).astype(np.int64)
    ok = col >= 0
    if not ok.any():
        return nan, nan
    key = col[ok] * c.depth_bins + b[ok]
    uk, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
    scar_bin = (np.bincount(inv, weights=cut[sel][ok]) / cnt) > c.depth_bin_majority
    cid, kbin = uk // c.depth_bins, uk % c.depth_bins
    _, cinv, ccnt = np.unique(cid, return_inverse=True, return_counts=True)
    good = ccnt >= c.column_min_bins
    if not good.any():
        return nan, nan
    ext = np.bincount(cinv, weights=scar_bin) / ccnt
    deep = scar_bin & good[cinv]
    deepest = float((kbin[deep].max() + 1) / c.depth_bins) if deep.any() else nan
    return float(ext[good].mean()), deepest


@dataclass
class Scar0:
    """Every menu candidate for one patient (:func:`scar0`); :meth:`table` picks one pair."""

    status: str
    segments: Dict[int, dict]
    remote: Optional[dict]
    thresholds: Dict[str, float]
    tau: Optional[float]
    constants: JA30Constants
    territory: Dict[int, str]
    territory_source: str
    case_id: Optional[str] = None
    ungradable: Optional[str] = None

    @property
    def graded(self) -> bool:
        return self.status != NOT_GRADED and self.ungradable is None

    def presence(self, candidate: str) -> Dict[int, Optional[bool]]:
        if candidate not in PRESENCE:
            raise ValueError(f"presence candidate must be one of {PRESENCE}, not {candidate!r}")
        if candidate == "P-J" and self.tau is None:
            raise ValueError("P-J needs tau, set on development (tau_from_development)")
        out = {}
        for s, row in self.segments.items():
            if not self.graded or not row["graded"]:
                out[s] = None
            elif candidate == "P-K":
                out[s] = row["share_pk"] >= self.constants.presence_share
            elif candidate == "P-G":
                out[s] = row["share_pg"] >= self.constants.presence_share
            else:
                out[s] = bool(np.isfinite(row["extent_ed"]) and row["extent_ed"] >= self.tau)
        return out

    def table(self, presence: str, extent: str) -> dict:
        """The JA26 per-segment and per-territory outputs for one (presence, extent) pair."""
        if extent not in EXTENT:
            raise ValueError(f"extent candidate must be one of {EXTENT}, not {extent!r}")
        pres = self.presence(presence)
        key, deep = ("share_ev", "deepest_ev") if extent == "E-V" else ("extent_ed", "deepest_ed")
        segs = {}
        for s in range(1, 18):
            row = self.segments.get(s)
            out = {
                "name": G.SEGMENT_NAMES[s],
                "territory": self.territory.get(s),
                "standard_territory": G.AHA_STANDARD[s],
            }
            p = pres.get(s)
            if row is None or p is None:
                out.update(graded=False, presence=None, kim_bin=None, share=None, deepest_u=None)
            else:
                share = row[key]
                out.update(
                    graded=True,
                    presence=bool(p),
                    kim_bin=kim_bin(share, p),
                    share=None if not np.isfinite(share) else round(float(share), 4),
                    deepest_u=round(float(row[deep]), 4)
                    if p and np.isfinite(row[deep])
                    else None,
                )
            segs[s] = out
        terr = {}
        for name in sorted(set(self.territory.values())):
            mine = [s for s in range(1, 18) if self.territory.get(s) == name]
            calls = [segs[s]["presence"] for s in mine if segs[s]["graded"]]
            terr[name] = {
                "n_segments": len(mine),
                "n_graded": len(calls),
                "share_scar_present": round(sum(calls) / len(calls), 4) if calls else None,
            }
        return {
            "label": RESEARCH_LABEL,
            "registration_status": self.status,
            "graded": self.graded,
            "ungradable": self.ungradable,
            "presence_candidate": presence,
            "extent_candidate": extent,
            "tau": self.tau,
            "segments": segs,
            "territories": terr,
            "territory_source": self.territory_source,
            "remote": self.remote,
            "thresholds": self.thresholds,
            "constants": asdict(self.constants),
            "constants_are_ja30": self.constants == JA30,
            "scar_version": SCAR_VERSION,
            "geometry_version": G.GEOMETRY_VERSION,
            "case_id": self.case_id,
        }


def scar0(
    lie,
    carried: CarriedGeometry,
    *,
    status: str,
    tau: Optional[float] = None,
    territory: Optional[Mapping[int, str]] = None,
    constants: JA30Constants = JA30,
    case_id=None,
) -> Scar0:
    """Compute every Scar-0 candidate inside the carried wall of one patient.

    ``status`` is the JA26 registration status
    (:func:`~janusm.scar.registration.status_from_checks`).
    ``tau`` is P-J's development cut (per protocol); without it P-J is not available.
    ``territory`` maps segment -> artery (from :func:`janusm.geometry.territories`); without it the
    standard AHA map is used, and the output says so.
    """
    guard_case(case_id, "janusm.scar.scar0")
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}, not {status!r}")
    c = constants
    if territory is None:
        terr, source = dict(G.AHA_STANDARD), "standard AHA map"
    else:
        terr, source = {int(k): str(v) for k, v in territory.items()}, "patient territories"
    lie = np.asarray(lie, np.float32)
    if lie.shape != carried.myo.shape:
        raise ValueError(f"LIE {lie.shape} and carried geometry {carried.myo.shape} differ")
    base = dict(
        tau=None if tau is None else float(tau),
        constants=c,
        territory=terr,
        territory_source=source,
        case_id=None if case_id is None else str(case_id),
    )
    if status == NOT_GRADED:
        return Scar0(status=status, segments={}, remote=None, thresholds={}, **base)
    sm = smooth(lie, carried.spacing, c.smooth_fwhm_mm)
    myo, seg = carried.myo, carried.segments
    rem = remote(
        sm,
        seg,
        carried.core(),
        n_segments=c.remote_n_segments,
        min_core_voxels=c.min_core_voxels,
    )
    if rem is None:
        return Scar0(
            status=status,
            segments={},
            remote=None,
            thresholds={},
            ungradable=f"fewer than {c.remote_n_segments} segments with a usable core",
            **base,
        )
    mu, sd = rem.median, rem.sd * (c.mad_to_sd / MAD_TO_SD)
    top = sm[carried.core() & (seg == rem.brightest)]
    thr_half = mu + c.half_way * (float(np.percentile(top, c.brightest_percentile)) - mu)
    thr_sd = mu + c.sd_k * sd
    above_half = myo & (sm > thr_half)
    above_sd = myo & (sm > thr_sd)
    pg = _opened(above_sd) & (carried.d_endo_mm() >= c.endo_ignore_mm)
    rows = {}
    for s in range(1, 18):
        sel = myo & (seg == s)
        n = int(sel.sum())
        if n == 0:
            continue
        ok = n > c.min_segment_voxels
        ext_ed, deep_ed = _columns(above_half, carried.u, carried.column, sel, c)
        _, deep_ev = _columns(above_sd, carried.u, carried.column, sel, c)
        rows[s] = {
            "n_voxels": n,
            "graded": ok,
            "share_pk": float(above_half[sel].mean()),
            "share_pg": float(pg[sel].sum() / n),
            "share_ev": float(above_sd[sel].mean()),
            "extent_ed": ext_ed,
            "deepest_ev": deep_ev,
            "deepest_ed": deep_ed,
        }
    return Scar0(
        status=status,
        segments=rows,
        remote={
            "median": round(mu, 4),
            "sd": round(sd, 4),
            "segments": rem.segments,
            "n_voxels": rem.n_voxels,
            "brightest_segment": rem.brightest,
        },
        thresholds={"half_way": round(thr_half, 4), "sd": round(thr_sd, 4)},
        **base,
    )


# ---------------------------------------------------------------------------------- development
def tau_from_development(
    records: Iterable[Tuple[str, str, float]],
    *,
    min_patients: int = TAU_MIN_PATIENTS,
) -> Dict[str, float]:
    """P-J's tau per scanner protocol, from LGE-negative development segments.

    ``records`` are ``(protocol, patient_key, T)``, one per LGE-negative development segment, with
    T the E-D extent. tau is the 99th percentile of T: per protocol when the protocol has at least
    ``min_patients`` development patients, else the pooled value. Every patient key goes through the
    JA12 guard first (fails closed). Returns ``{protocol: tau}``; ``"pooled"`` is always present.
    """
    rec = [(str(p), str(k), float(t)) for p, k, t in records]
    if not rec:
        raise ValueError("no development records")
    keys = sorted({k for _, k, _ in rec})
    for k in keys:
        guard_case(k, "janusm.scar.scar0.tau_from_development")
    t_all = np.array([t for _, _, t in rec])
    if not np.isfinite(t_all).all():
        raise ValueError("every development T must be finite")
    pooled = float(np.percentile(t_all, 99))
    out = {"pooled": pooled}
    for prot in sorted({p for p, _, _ in rec}):
        mine = [(k, t) for p, k, t in rec if p == prot]
        if len({k for k, _ in mine}) >= min_patients:
            out[prot] = float(np.percentile([t for _, t in mine], 99))
        else:
            out[prot] = pooled
    return out


def choose_presence(dev: Mapping[str, Tuple[float, float]]) -> Optional[str]:
    """JA30: the presence candidate with the highest development segment sensitivity among those
    whose specificity lower bound (cluster bootstrap) is >= 0.95; ties go to the earlier in the
    list. ``dev`` maps candidate -> (sensitivity, specificity lower bound); None if none
    qualifies."""
    bad = set(dev) - set(PRESENCE)
    if bad:
        raise ValueError(f"unknown presence candidates {sorted(bad)}")
    ok = [p for p in PRESENCE if p in dev and dev[p][1] >= MIN_SPEC_LOWER_BOUND]
    if not ok:
        return None
    best = max(dev[p][0] for p in ok)
    return next(p for p in ok if dev[p][0] == best)


def choose_extent(dev: Mapping[str, float]) -> str:
    """JA30: the extent candidate with the higher transmurality agreement among scar-on-both
    development segments; a tie goes to the earlier in the list (E-V)."""
    bad = set(dev) - set(EXTENT)
    if bad or not dev:
        raise ValueError(f"extent agreement must be given for {EXTENT}")
    have = [e for e in EXTENT if e in dev]
    best = max(dev[e] for e in have)
    return next(e for e in have if dev[e] == best)
