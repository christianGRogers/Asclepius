"""LIE-to-CCTA registration (JA29 as amended by JA51-JA53): scanner frame, QC, heart-masked Mattes
MI rigid, affine under a sanity bound and the normalised QC rule, a 10 mm fallback, the phase step.

Rulings: ``vault/JanusM/Judgements/Round 2 - paired-scar.md`` JA29 (direction, carried quantities,
reader check, logging), and ``vault/JanusM/Judgements/Round 3 - paired-scar.md`` JA51 (the chain,
which replaces JA29's steps 1-4), JA52 (the phase step) and JA53 (QC cuts); shipped as PS3-S1 to
PS3-S5 (§9).

- **Direction.** The first-pass CT is moving and the LIE is fixed: grading happens on the LIE grid,
  so LIE noise is never resampled (Golf). A transform here maps a fixed (LIE) world point, in mm,
  to the moving (first-pass) world point, as ITK's do.
- **Carried.** Myocardium and cavity through their signed distances (linear); AHA segments, depth u
  and the E-D column id by nearest neighbour (:class:`~janusm.scar.common.CarriedGeometry`).
- **The chain (JA51), stopping at the first stage that passes QC:**

  1. ``R0``: scanner coordinates through the shared frame of reference (identity), or a reader's
     manual initial shift on a re-registration;
  2. QC (:func:`qc`): four values on the smoothed LIE: the fat-like and blood-like shares of the
     carried wall, the share brighter than the blood median, and ``rim_dark`` (the share of the
     carried cavity's 2 mm inner rim below (remote + blood median) / 2). The blood median is taken
     >= 2 mm inside the carried cavity border, or 1 voxel inside if fewer than 50 voxels remain.
     Each value against a cut (:class:`QCCuts`, no defaults; :func:`fit_qc_cuts` sets them on
     development, :func:`load_provisional_qc_cuts` reads the benchmark's until then). Any NaN fails;
  3. ``rigid``: Mattes MI, the metric masked to classes 1-4 dilated by 4 mm (Euclidean,
     ``edt <= margin``; :data:`MASK_DILATION_MM`, a parameter of :func:`prepare_first_pass`);
  4. ``affine`` with the same mask, kept only if :func:`affine_accepted` (JA81, rule (g)): a sanity
     bound (|log det A| <= 0.15; every singular value and shear term within +/- 15 % of identity),
     the normalised QC maximum (each gated value divided by its cut) no higher than rigid's, and
     either affine passes QC or |log det A| >= 0.02 (:data:`AFFINE_SCALE_LOG_DET`). The result
     after this step is the **last 4 mm stage** (``Registration.stage_4mm``);
  5. ``rigid10``: if the result still fails QC, the phase step is run on the last 4 mm stage and
     logged (``phase_4mm``); then one rigid run from R0 with a 10 mm Euclidean mask
     (:data:`FALLBACK_MASK_MM`). It replaces the result only if it passes QC or lowers the
     normalised maximum. It is logged as its own stage either way. JA82's skip (a routing flag on
     the 4 mm stage skips step 5) is built but **off by default**
     (``phase_check_before_fallback``): its PS4-S5 acceptance replay missed (see
     ``bench_lie/scores_v3.json`` -> ``ja82_replay``), so step 5 ships as JA51 states;
  6. the phase step (JA52 as amended by JA84, :func:`phase_step`) on the final stage: the signed
     endocardial edge offset over the 6 remote segments beyond +/- 0.6 mm is the **routing** flag;
     ``rim_dark`` above its phase cut is **advisory** (logged, shown to the reader after the
     decision, routes no patient); the affine log-determinant and the edge offset's per-segment
     IQR are logged only.

  B-spline is not in the pipeline (JA53).
- **Reader check** (every patient, blind to LGE): :func:`status_from_checks` turns the pass/fail
  record, the routing flag, the phase source (JA59) and the reader's phase mark into the JA26
  status (passed, re-registered, not graded) or ``phase suspect``, with its JA85 route
  (``confirmed`` or ``flag_only``). A fail is re-registered once from a manual initial shift
  (:func:`register_lie` with ``initial_shift_mm`` and ``attempt=2``), never a phase-suspect
  patient. A phase-suspect patient is graded on its last 4 mm stage (``graded_stage``), never on
  the 10 mm fallback (JA85).
- **Logged per patient** (:meth:`Registration.log`): the estimated shift of the heart between the
  scans, every stage's parameters, QC values and MI, and the phase step.
- **Development stop:** :func:`seal_grading_allowed` (a not-graded rate above 10 %, phase-suspect
  patients excluded); :func:`phase_suspect_needs_report` (JA52: a phase-suspect share above 20 %).

Mattes MI is implemented here (cubic B-spline Parzen windows on a joint histogram, Mattes 2003),
with a Powell search over two smoothing levels, so the module needs numpy and scipy only. The MI
settings (48 bins, sampled points, levels) are implementation choices taken from the advocates'
code (Kilo and Juliet: 48 bins; Juliet: two levels, Powell); none is a threshold.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
from scipy import ndimage as ndi
from scipy import optimize

from janusm import geometry as G
from janusm.scar import (
    AWAITING,
    NOT_GRADED,
    PASSED,
    PHASE_SUSPECT,
    REREGISTERED,
    SCAR_VERSION,
    guard_case,
)
from janusm.scar.common import (
    SMOOTH_FWHM_MM,
    CarriedGeometry,
    core_mask,
    remote,
    smooth,
)

log = logging.getLogger(__name__)

#: JA51 step 3: the MI metric is masked to classes 1-4 dilated by this much (mm, Euclidean).
MASK_DILATION_MM = 4.0
#: JA51 step 5: the one rigid fallback's mask (mm, Euclidean).
FALLBACK_MASK_MM = 10.0
#: JA29: a development failure rate above this stops seal grading.
MAX_FAILURE_RATE = 0.10
#: JA52 stop rule: a development phase-suspect share above this goes to the lead.
PHASE_SUSPECT_REPORT_SHARE = 0.20
#: E-D columns (JA30): 3 degrees about the long axis x 2 mm along it.
COLUMN_DEG = 3.0
COLUMN_MM = 2.0

#: JA51 step 2: the blood median is taken at least this far inside the carried cavity border (mm)...
BLOOD_CORE_MM = 2.0
#: ...or one voxel inside when fewer than this many voxels remain.
MIN_BLOOD_CORE_VOXELS = 50
#: JA51 step 2: ``rim_dark`` reads the carried cavity's inner rim this deep (mm, Euclidean).
RIM_MM = 2.0
#: ``rim_dark`` is NaN (and fails) on a rim of fewer voxels (the benchmark's ``menu.qc``).
MIN_RIM_VOXELS = 50

#: JA51 step 4(a): |log det A| bound, and the +/- band on every singular value and shear term.
MAX_ABS_LOG_DET = 0.15
MAX_SCALE_SHEAR_DEV = 0.15

#: JA81 (c'): affine that fails QC is still kept when |log det A| reaches this (a scale is found).
AFFINE_SCALE_LOG_DET = 0.02

#: JA52 / JA84: the routing phase flag, |edge offset| above this (mm).
EDGE_OFFSET_FLAG_MM = 0.6
#: JA52: phase is not evaluable when (blood median - remote) is under this many robust SD of remote.
MIN_PHASE_CONTRAST_SD = 2.0
#: Kilo E8's edge-offset profile: distance range and bin width (mm), and the blood and remote-wall
#: windows (bin centres, mm from the carried endocardium; negative in the cavity).
EDGE_PROFILE_MM = (-6.0, 4.0)
EDGE_BIN_MM = 0.5
EDGE_BLOOD_MM = (-6.0, -3.0)
EDGE_WALL_MM = (1.5, 3.5)
#: Kilo E8: a profile needs this many voxels, and a bin more than this many.
EDGE_MIN_VOXELS = 200
EDGE_MIN_BIN_VOXELS = 5

STAGE_R0 = "R0"
STAGE_RIGID = "rigid"
STAGE_AFFINE = "affine"
STAGE_FALLBACK = "rigid10"

#: JA59 / JA85: where a patient's phase information comes from.
PHASE_DICOM_UNMATCHED = "dicom_unmatched"
PHASE_DICOM_MATCHED = "dicom_matched"
PHASE_INFERRED = "inferred"
PHASE_SOURCES = (PHASE_DICOM_UNMATCHED, PHASE_DICOM_MATCHED, PHASE_INFERRED)
#: JA85 routes into the ``phase_unmatched`` stratum: confirmed (outside yield) or on the flag alone
#: (charged to yield).
ROUTE_CONFIRMED = "confirmed"
ROUTE_FLAG_ONLY = "flag_only"
PHASE_ROUTES = (ROUTE_CONFIRMED, ROUTE_FLAG_ONLY)

#: JA83: the SCAR_VERSION at which the shipped QC definitions (:func:`qc`,
#: :class:`QCDefinitions`) last changed. Bump it, with SCAR_VERSION, on any change that moves a QC
#: value; a cut file declaring another is refused.
QC_DEFINITIONS_SINCE = "1.1.0"
#: JA83: what a cut file must declare under ``qc_definitions`` (:func:`load_provisional_qc_cuts`).
QC_DEFINITIONS = f"janusm.scar.registration {QC_DEFINITIONS_SINCE}"

#: The four QC values, in the order of :meth:`QC.values` and :meth:`QCCuts.values`.
QC_NAMES = ("fatlike", "bloodlike", "brighter_than_blood", "rim_dark")


@dataclass(frozen=True)
class QCDefinitions:
    """What counts as fat-like and blood-like (Juliet E6). Definitions, not pass cuts."""

    #: A wall voxel is fat-like below this smoothed LIE value (HU).
    fat_hu: float = 0.0
    #: Blood-like: above remote + this x (blood median - remote).
    bloodlike_frac: float = 0.8
    #: The smoothing QC reads (the JA30 common step).
    smooth_fwhm_mm: float = SMOOTH_FWHM_MM


@dataclass(frozen=True)
class QCCuts:
    """The QC pass cuts: each gated share must be at most its cut. Set on development (JA53); the
    four cuts deliberately have no defaults.

    - ``gate``: which values stop R0 (JA53's drop rule marks a weak value ``False``; it stays
      logged). At least one value must be gated.
    - ``max_rim_dark_phase``: ``rim_dark``'s phase cut (JA52; advisory under JA84); ``None`` uses
      ``max_rim_dark``.
    - ``max_edge_offset_mm``: the routing phase flag's cut (JA52, JA84).
    """

    max_fatlike: float
    max_bloodlike: float
    max_brighter_than_blood: float
    max_rim_dark: float
    gate: Tuple[bool, bool, bool, bool] = (True, True, True, True)
    max_rim_dark_phase: Optional[float] = None
    max_edge_offset_mm: float = EDGE_OFFSET_FLAG_MM

    def __post_init__(self):
        g = tuple(bool(x) for x in self.gate)
        if len(g) != 4:
            raise ValueError(f"gate has one flag per QC value {QC_NAMES}: {self.gate}")
        if not any(g):
            raise ValueError("at least one QC value must stay in the gate (fail closed)")
        object.__setattr__(self, "gate", g)

    def values(self) -> np.ndarray:
        return np.array(
            [self.max_fatlike, self.max_bloodlike, self.max_brighter_than_blood, self.max_rim_dark],
            float,
        )

    @property
    def rim_dark_phase(self) -> float:
        return self.max_rim_dark if self.max_rim_dark_phase is None else self.max_rim_dark_phase


#: The JA29 definitions as given (Juliet E6, Kilo E5).
DEFAULT_QC_DEFINITIONS = QCDefinitions()


@dataclass
class QC:
    """QC values of one carried wall on the smoothed LIE (NaN when undefined)."""

    fatlike: float
    bloodlike: float
    brighter_than_blood: float
    rim_dark: float
    blood_median: float
    remote_median: float
    n_wall: int
    remote_sd: float = float("nan")
    #: Voxels the blood median was taken over, and how deep: ">=2mm" or "1 voxel".
    n_blood: int = 0
    blood_core: str = ""

    def values(self) -> np.ndarray:
        return np.array(
            [self.fatlike, self.bloodlike, self.brighter_than_blood, self.rim_dark], float
        )

    @property
    def contrast(self) -> float:
        """The patient's blood-to-remote contrast, (blood median - remote) / robust SD of remote
        (JA53's index for the shares' cuts; JA52's evaluability)."""
        if not (np.isfinite(self.remote_sd) and self.remote_sd > 0):
            return float("nan")
        return float((self.blood_median - self.remote_median) / self.remote_sd)

    def passes(self, cuts: QCCuts) -> bool:
        """Every gated value at or under its cut. Any gated NaN fails (closed)."""
        g = np.array(cuts.gate)
        v, c = self.values()[g], cuts.values()[g]
        return bool(np.isfinite(v).all() and (v <= c).all())


def normalised(q: QC, cuts: QCCuts) -> np.ndarray:
    """JA51 step 4(b): each gated QC value divided by its cut. A cut at or below zero divides by a
    tiny positive number instead, so the order of values is kept and nothing flips sign."""
    g = np.array(cuts.gate)
    return q.values()[g] / np.maximum(cuts.values()[g], 1e-6)


def normalised_max(q: QC, cuts: QCCuts) -> float:
    """The largest normalised QC value (NaN if any is NaN)."""
    v = normalised(q, cuts)
    return float(v.max()) if np.isfinite(v).all() else float("nan")


def inner_depth_mm(cavity: np.ndarray, spacing) -> np.ndarray:
    """Distance (mm) of each cavity voxel centre inside the carried cavity border, which lies half a
    voxel beyond the last cavity voxel (the :meth:`CarriedGeometry.d_endo_mm` convention); 0
    outside the cavity."""
    if not cavity.any():
        return np.zeros(cavity.shape)
    h = 0.5 * float(np.mean(spacing))
    return np.where(cavity, ndi.distance_transform_edt(cavity, sampling=spacing) - h, 0.0)


def blood_core(cavity: np.ndarray, spacing) -> Tuple[np.ndarray, str]:
    """JA51 step 2 (#188 reading 5, corrected): the voxels the blood median is taken over: >= 2 mm
    inside the carried cavity border, or 1 voxel inside if fewer than 50 voxels remain."""
    deep = cavity & (inner_depth_mm(cavity, spacing) >= BLOOD_CORE_MM)
    if int(deep.sum()) >= MIN_BLOOD_CORE_VOXELS:
        return deep, f">={BLOOD_CORE_MM:g}mm"
    return core_mask(cavity), "1 voxel"


def inner_rim(cavity: np.ndarray, spacing) -> np.ndarray:
    """The carried cavity's inner rim: cavity voxels less than :data:`RIM_MM` inside its border."""
    return cavity & (inner_depth_mm(cavity, spacing) < RIM_MM)


def qc(
    lie: np.ndarray, carried: CarriedGeometry, defs: QCDefinitions = DEFAULT_QC_DEFINITIONS
) -> QC:
    """JA51 step 2 on one carried wall. The remote is JA30's."""
    sm = smooth(lie, carried.spacing, defs.smooth_fwhm_mm)
    return _qc_smoothed(sm, carried, defs)


def _qc_smoothed(sm: np.ndarray, carried: CarriedGeometry, defs: QCDefinitions) -> QC:
    wall = carried.myo
    n = int(wall.sum())
    nan = float("nan")
    if n == 0:
        return QC(nan, nan, nan, nan, nan, nan, 0)
    core, depth = blood_core(carried.cavity, carried.spacing)
    blood_vox = sm[core]
    blood = float(np.median(blood_vox)) if blood_vox.size else nan
    rem = remote(sm, carried.segments, carried.core())
    mu = rem.median if rem is not None else nan
    sd = rem.sd if rem is not None else nan
    w = sm[wall]
    fat = float((w < defs.fat_hu).mean())
    if np.isfinite(blood) and np.isfinite(mu) and blood > mu:
        bloodlike = float((w > mu + defs.bloodlike_frac * (blood - mu)).mean())
    else:
        bloodlike = nan
    brighter = float((w > blood).mean()) if np.isfinite(blood) else nan
    rim = inner_rim(carried.cavity, carried.spacing)
    if int(rim.sum()) >= MIN_RIM_VOXELS and np.isfinite(blood) and np.isfinite(mu):
        rim_dark = float((sm[rim] < (mu + blood) / 2.0).mean())
    else:
        rim_dark = nan
    return QC(fat, bloodlike, brighter, rim_dark, blood, mu, n, sd, int(blood_vox.size), depth)


# ---------------------------------------------------------------------------------- affine rule
def affine_sanity(matrix: np.ndarray) -> dict:
    """JA51 step 4(a) on the affine's 3 x 3 matrix: log det, singular values and shear terms (the
    off-diagonal of the upper-triangular factor of A = QR, each row divided by its diagonal), and
    whether all are within bounds."""
    a = np.asarray(matrix, float)
    det = float(np.linalg.det(a))
    log_det = float(np.log(det)) if det > 0 else float("nan")
    sv = np.linalg.svd(a, compute_uv=False)
    _, r = np.linalg.qr(a)
    r = r * np.sign(np.diag(r))[:, None]
    shear = np.array([r[0, 1] / r[0, 0], r[0, 2] / r[0, 0], r[1, 2] / r[1, 1]])
    ok = (
        np.isfinite(log_det)
        and abs(log_det) <= MAX_ABS_LOG_DET
        and bool((np.abs(sv - 1.0) <= MAX_SCALE_SHEAR_DEV).all())
        and bool((np.abs(shear) <= MAX_SCALE_SHEAR_DEV).all())
    )
    return {
        "log_det": log_det,
        "singular_values": sv.tolist(),
        "shear": shear.tolist(),
        "ok": bool(ok),
    }


def qc_rule_accepts(new: QC, old: QC, cuts: QCCuts) -> bool:
    """JA51 step 4(b) as first written: the QC values divided by their cuts show no rise, and their
    maximum falls. Any NaN rejects. **Superseded by JA81** (:func:`affine_accepted`); kept because
    the Round 4 benchmark scorers replay it as the ``literal`` rule."""
    a, r = normalised(new, cuts), normalised(old, cuts)
    if not (np.isfinite(a).all() and np.isfinite(r).all()):
        return False
    return bool((a <= r).all() and a.max() < r.max())


def affine_rule(matrix: np.ndarray, affine_qc: QC, rigid_qc: QC, cuts: QCCuts) -> dict:
    """JA81's three clauses, each logged: (a) the sanity bound; (b') the normalised QC maximum for
    affine is no higher than for rigid; (c') affine passes QC, or |log det A| >= 0.02. Any NaN
    (in the gated QC values or the log det) fails its clause. ``kept`` is all three."""
    san = affine_sanity(matrix)
    m_aff, m_rig = normalised_max(affine_qc, cuts), normalised_max(rigid_qc, cuts)
    max_ok = bool(np.isfinite(m_aff) and np.isfinite(m_rig) and m_aff <= m_rig)
    ld = san["log_det"]
    scaled = bool(np.isfinite(ld) and abs(ld) >= AFFINE_SCALE_LOG_DET)
    passes_or_scaled = bool(affine_qc.passes(cuts) or scaled)
    return {
        "sanity": bool(san["ok"]),
        "max_not_raised": max_ok,
        "passes_or_scaled": passes_or_scaled,
        "normalised_max_affine": None if not np.isfinite(m_aff) else round(m_aff, 5),
        "normalised_max_rigid": None if not np.isfinite(m_rig) else round(m_rig, 5),
        "kept": bool(san["ok"] and max_ok and passes_or_scaled),
    }


def affine_accepted(matrix: np.ndarray, affine_qc: QC, rigid_qc: QC, cuts: QCCuts) -> bool:
    """JA81 (rule (g); replaces JA51 4(b)): affine is kept iff all hold:

    - (a) ``affine_sanity(matrix)["ok"]`` (unchanged);
    - (b') ``normalised_max(affine) <= normalised_max(rigid)``;
    - (c') ``affine_qc.passes(cuts)`` or ``abs(log_det) >= AFFINE_SCALE_LOG_DET`` (0.02).

    Any NaN rejects. (c') reads |log det| and does not depend on its sign (see
    :class:`Transform` for the sign convention)."""
    return affine_rule(matrix, affine_qc, rigid_qc, cuts)["kept"]


# ---------------------------------------------------------------------------------- first pass
@dataclass
class FirstPass:
    """The moving side, prepared once per patient (cropped round the heart)."""

    image: np.ndarray
    affine: np.ndarray
    spacing: np.ndarray
    mask: np.ndarray  # classes 1-4 dilated mask_mm (Euclidean): the JA51 metric mask
    sdf_myo: np.ndarray
    sdf_cav: np.ndarray
    seg_ext: np.ndarray  # nearest wall voxel's segment, everywhere in the crop
    u_ext: np.ndarray
    col_ext: np.ndarray
    myo_world: np.ndarray  # (n, 3) world mm of first-pass wall voxels, for the logged shift
    centre: np.ndarray  # rotation centre (world mm): the mask centroid
    geometry_flags: List[str] = field(default_factory=list)
    #: classes 1-4 dilated fallback_mm: the JA51 step 5 fallback's mask (None: no fallback)
    fallback_mask: Optional[np.ndarray] = None
    mask_mm: float = MASK_DILATION_MM
    fallback_mm: Optional[float] = FALLBACK_MASK_MM


def _sdf(mask: np.ndarray, sp) -> np.ndarray:
    """Signed distance (mm), negative inside."""
    if not mask.any():
        return np.full(mask.shape, 1e6, np.float32)
    out = ndi.distance_transform_edt(~mask, sampling=sp) - ndi.distance_transform_edt(
        mask, sampling=sp
    )
    return out.astype(np.float32)


def _columns(seg: np.ndarray, aha: G.AHA, affine: np.ndarray) -> np.ndarray:
    """E-D column id per wall voxel: 3 degrees about the AHA long axis x 2 mm along it."""
    col = np.full(seg.shape, -1, np.int64)
    wall = seg > 0
    base, apex = np.asarray(aha.base_mm, float), np.asarray(aha.apex_mm, float)
    axis = (apex - base) / np.linalg.norm(apex - base)
    helper = np.eye(3)[int(np.argmin(np.abs(axis)))]
    e1 = helper - (helper @ axis) * axis
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    p = G._world(np.argwhere(wall).astype(float), affine) - base
    s = p @ axis
    ang = np.degrees(np.arctan2(p @ e2, p @ e1)) % 360.0
    ia = np.floor(ang / COLUMN_DEG).astype(np.int64)
    js = np.floor(s / COLUMN_MM).astype(np.int64) + 100_000
    col[wall] = ia * 1_000_000 + js
    return col


def prepare_first_pass(
    ct,
    labels,
    affine,
    *,
    geometry: Optional[G.Geometry] = None,
    margin_mm: float = 30.0,
    mask_mm: float = MASK_DILATION_MM,
    fallback_mm: Optional[float] = FALLBACK_MASK_MM,
    case_id=None,
) -> FirstPass:
    """Crop the first-pass CT and its JA1 labels round the heart and build what is carried.

    ``geometry`` is :func:`janusm.geometry.analyse` on the same grid (computed here when not
    given). It must have AHA segments; a failed derivation cannot be graded and raises.

    ``mask_mm`` is JA51's metric mask margin (4 mm, Euclidean: ``edt <= margin``); ``fallback_mm``
    the step 5 fallback's (10 mm; ``None`` builds no fallback mask, and the chain then has no
    fallback stage).
    """
    guard_case(case_id, "janusm.scar.registration.prepare_first_pass")
    for m_ in (mask_mm, fallback_mm):
        if m_ is not None and not (0.0 <= float(m_) <= margin_mm):
            raise ValueError(f"mask margin {m_} mm must lie in [0, crop margin {margin_mm} mm]")
    labels = G._check_labels(labels)
    ct = np.asarray(ct, np.float32)
    if ct.shape != labels.shape:
        raise ValueError(f"first-pass CT {ct.shape} and labels {labels.shape} differ")
    aff, sp = G._affine(labels.shape, None, affine)
    if geometry is None:
        geometry = G.analyse(labels, affine=aff)
    if geometry.aha.segments is None:
        raise ValueError(f"no AHA segments on the first pass: {geometry.aha.flags}")
    heart = np.isin(labels, (G.MYO, G.LV, G.RV, G.LA))
    nz = np.argwhere(heart)
    m = np.ceil(margin_mm / sp).astype(int)
    lo = np.maximum(nz.min(0) - m, 0)
    hi = np.minimum(nz.max(0) + m + 1, labels.shape)
    box = tuple(slice(a, b) for a, b in zip(lo, hi))
    caff = aff.copy()
    caff[:3, 3] = G._world(lo[None].astype(float), aff)[0]
    lab = labels[box]
    seg = geometry.aha.segments[box].astype(np.int16)
    u = geometry.depth.u[box]
    myo, cav = lab == G.MYO, lab == G.LV
    hc = heart[box]
    dist = ndi.distance_transform_edt(~hc, sampling=sp)
    mask = dist <= float(mask_mm)
    fallback = None if fallback_mm is None else dist <= float(fallback_mm)
    _, idx = ndi.distance_transform_edt(~myo, sampling=sp, return_indices=True)
    idx = tuple(idx)
    col = _columns(seg, geometry.aha, caff)
    centre = G._world(np.argwhere(mask).mean(0)[None], caff)[0]
    return FirstPass(
        image=ct[box],
        affine=caff,
        spacing=sp,
        mask=mask,
        sdf_myo=_sdf(myo, sp),
        sdf_cav=_sdf(cav, sp),
        seg_ext=seg[idx],
        u_ext=u[idx].astype(np.float32),
        col_ext=col[idx],
        myo_world=G._world(np.argwhere(myo).astype(float), caff),
        centre=centre,
        geometry_flags=list(geometry.aha.flags),
        fallback_mask=fallback,
        mask_mm=float(mask_mm),
        fallback_mm=None if fallback_mm is None else float(fallback_mm),
    )


# ---------------------------------------------------------------------------------- transforms
def _rot(deg: Sequence[float]) -> np.ndarray:
    ax, ay, az = np.radians(np.asarray(deg, float))
    cx, sx, cy, sy, cz, sz = np.cos(ax), np.sin(ax), np.cos(ay), np.sin(ay), np.cos(az), np.sin(az)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rz @ ry @ rx


@dataclass
class Transform:
    """p_moving = matrix (p_fixed - centre) + centre + translation (world mm).

    The transform maps the fixed LIE to the moving first pass. **Sign (JA81):** a LIE heart larger
    than the first pass by a factor s is mapped back by ``matrix ~ I / s``, so
    ``log det(matrix) ~ -3 log s`` (a 3 % enlargement reads about -0.089). JA81's (c') reads
    |log det| and does not depend on the sign."""

    matrix: np.ndarray
    translation: np.ndarray
    centre: np.ndarray

    def forward(self, p_fixed: np.ndarray) -> np.ndarray:
        return (p_fixed - self.centre) @ self.matrix.T + self.centre + self.translation

    def inverse(self, p_moving: np.ndarray) -> np.ndarray:
        inv = np.linalg.inv(self.matrix)
        return (p_moving - self.centre - self.translation) @ inv.T + self.centre

    def as_4x4(self) -> np.ndarray:
        out = np.eye(4)
        out[:3, :3] = self.matrix
        out[:3, 3] = self.centre + self.translation - self.matrix @ self.centre
        return out


# ---------------------------------------------------------------------------------- Mattes MI
def _bspline3(x: np.ndarray):
    """Cubic B-spline Parzen weights: the 4 bins i-1..i+2 round floor(x) and their weights."""
    i = np.floor(x).astype(np.int64)
    f = x - i
    f2, f3 = f * f, f * f * f
    w = np.stack(
        [(1 - f) ** 3 / 6, (3 * f3 - 6 * f2 + 4) / 6, (-3 * f3 + 3 * f2 + 3 * f + 1) / 6, f3 / 6]
    )
    return np.stack([i - 1, i, i + 1, i + 2]), w


def mattes_mi(fixed_vals, moving_vals, f_range, m_range, bins: int = 48) -> float:
    """Mutual information (nats) of two samples, cubic B-spline Parzen windows on both."""
    def to_bins(v, rng):
        lo, hi = rng
        x = (np.clip(v, lo, hi) - lo) / max(hi - lo, 1e-6) * (bins - 1)
        return x + 2.0  # two bins of padding on each side for the kernel

    nb = bins + 4
    fi, fw = _bspline3(to_bins(np.asarray(fixed_vals, float), f_range))
    mi_, mw = _bspline3(to_bins(np.asarray(moving_vals, float), m_range))
    joint = np.zeros(nb * nb)
    for a in range(4):
        for b in range(4):
            joint += np.bincount(fi[a] * nb + mi_[b], weights=fw[a] * mw[b], minlength=nb * nb)
    p = joint.reshape(nb, nb)
    p /= p.sum()
    pf, pm = p.sum(1), p.sum(0)
    nz = p > 0
    return float((p[nz] * np.log(p[nz] / np.outer(pf, pm)[nz])).sum())


def _sample(img: np.ndarray, affine: np.ndarray, pts: np.ndarray, order: int = 1, **kw):
    ijk = (pts - affine[:3, 3]) @ np.linalg.inv(affine[:3, :3]).T
    return ndi.map_coordinates(img, ijk.T, order=order, **kw)


@dataclass
class _Metric:
    fixed_levels: list
    fixed_affine: np.ndarray
    moving_vals: list
    pts: np.ndarray  # moving-mask sample points (world mm)
    bins: int

    def _fixed(self, level: int, T: Transform) -> np.ndarray:
        pts = T.inverse(self.pts)
        return _sample(self.fixed_levels[level], self.fixed_affine, pts, mode="nearest")

    def cost(self, level: int, T: Transform, f_range, m_range) -> float:
        fv = self._fixed(level, T)
        return -mattes_mi(fv, self.moving_vals[level], f_range, m_range, self.bins)

    def ranges(self, level: int, T: Transform):
        fv = self._fixed(level, T)
        mv = self.moving_vals[level]
        return tuple(np.percentile(fv, (0.5, 99.5))), tuple(np.percentile(mv, (0.5, 99.5)))


def _metric(
    fp: FirstPass, lie, lie_aff, lie_sp, levels_mm, n_samples, bins, seed, mask=None
) -> _Metric:
    rng = np.random.default_rng(seed)
    idx = np.argwhere(fp.mask if mask is None else mask)
    if len(idx) > n_samples:
        idx = idx[rng.choice(len(idx), n_samples, replace=False)]
    pts = G._world(idx.astype(float), fp.affine)
    fixed_levels, moving_vals = [], []
    for s in levels_mm:
        f = ndi.gaussian_filter(lie, s / lie_sp) if s > 0 else lie
        m = ndi.gaussian_filter(fp.image, s / fp.spacing) if s > 0 else fp.image
        fixed_levels.append(f)
        moving_vals.append(m[tuple(idx.T)].astype(float))
    return _Metric(fixed_levels, lie_aff, moving_vals, pts, bins)


def _optimise(metric: _Metric, make, x0, step, maxfev, penalty=None) -> np.ndarray:
    """Powell over the smoothing levels. ``penalty(q)``, when given, is added to the cost (the
    PS4-S7 variant only; the shipped stages pass none)."""
    x = np.asarray(x0, float)
    for level in range(len(metric.fixed_levels)):
        fr, mr = metric.ranges(level, make(x))

        def cost(q, level=level, fr=fr, mr=mr):
            c = metric.cost(level, make(q), fr, mr)
            return c if penalty is None else c + penalty(q)

        res = optimize.minimize(
            cost,
            x,
            method="Powell",
            options={"xtol": 1e-3, "ftol": 1e-6, "maxfev": maxfev, "direc": np.diag(step)},
        )
        x = res.x
    return x


def _rigid(metric, centre, start: Transform, maxfev) -> Transform:
    def make(q):
        return Transform(_rot(q[:3]), np.asarray(q[3:6]), centre)

    # rotation in degrees, translation in mm; starts from the R0 translation
    q = _optimise(metric, make, [0, 0, 0, *start.translation], [2, 2, 2, 4, 4, 4], maxfev)
    return make(q)


def _affine_from(metric, rig: Transform, maxfev) -> Transform:
    m0, scale = rig.matrix, 0.01

    def make(q):
        m = m0 + scale * np.asarray(q[:9]).reshape(3, 3)
        return Transform(m, np.asarray(q[9:]), rig.centre)

    q = _optimise(metric, make, [0] * 9 + list(rig.translation), [1] * 9 + [1, 1, 1], maxfev)
    return make(q)


#: PS4-S7 (report only): the affine optimiser variants :func:`register_lie` can take. ``None`` is
#: the shipped optimiser (:func:`_affine_from`), byte-identical to SCAR_VERSION 1.1.0.
AFFINE_VARIANTS = (None, "scaled")
#: PS4-S7 ``scaled``: Powell's initial step on each log-scale, and on each linear entry of the full
#: affine that follows (the shipped optimiser steps both in units of 0.01, with the translations).
VARIANT_SCALE_STEP = 0.01
VARIANT_LINEAR_STEP = 0.002
#: PS4-S7 ``scaled``: penalty (in MI nats) per unit squared Frobenius distance of the full affine's
#: linear part from the scale stage's. On the static-chest phantom (seed 22) 0 lets the full affine
#: drift on a pure 4 mm shift (TRE 0.50 mm against rigid 0.22); 10 holds it (0.26) and keeps the
#: 3 % scale fix (0.24 against rigid 1.29); 100 loses the scale fix (0.56).
VARIANT_RIGID_PENALTY = 10.0


def _affine_scaled(
    metric, rig: Transform, maxfev, *, rigid_penalty: float = VARIANT_RIGID_PENALTY
) -> Transform:
    """PS4-S7 variant (engineering, report only; not used unless asked for): a scale-only stage,
    then the full affine with its own, smaller steps for the linear part.

    1. three log-scales along the rigid frame's axes plus the translation (the rotation is held);
    2. the full affine from there, the nine linear entries stepped in units of
       :data:`VARIANT_LINEAR_STEP` (translation in mm, as before), optionally penalised toward the
       scale stage's linear part by ``rigid_penalty``.

    Adoption needs a later ruling with a v3 replay (PS4-S7)."""
    r0 = rig.matrix

    def make_s(q):
        return Transform(r0 @ np.diag(np.exp(np.asarray(q[:3]))), np.asarray(q[3:6]), rig.centre)

    qs = _optimise(
        metric,
        make_s,
        [0.0, 0.0, 0.0, *rig.translation],
        [VARIANT_SCALE_STEP] * 3 + [1.0, 1.0, 1.0],
        maxfev,
    )
    sc = make_s(qs)
    m0 = sc.matrix

    def make(q):
        m = m0 + VARIANT_LINEAR_STEP * np.asarray(q[:9]).reshape(3, 3)
        return Transform(m, np.asarray(q[9:]), rig.centre)

    pen = None
    if rigid_penalty > 0:

        def pen(q):
            return rigid_penalty * float(np.sum((VARIANT_LINEAR_STEP * np.asarray(q[:9])) ** 2))

    q = _optimise(
        metric, make, [0] * 9 + list(sc.translation), [1] * 9 + [1, 1, 1], maxfev, penalty=pen
    )
    return make(q)


# ---------------------------------------------------------------------------------- carrying
def carry(fp: FirstPass, T: Transform, lie_shape, lie_affine) -> CarriedGeometry:
    """Carry the first-pass geometry onto the LIE grid through ``T`` (fixed -> moving)."""
    lie_aff = np.asarray(lie_affine, float)
    lie_sp = np.linalg.norm(lie_aff[:3, :3], axis=0)
    shape = tuple(lie_shape)
    # only the part of the LIE grid the cropped first pass can reach
    n = np.array(fp.mask.shape) - 1
    corners = np.array([[i, j, k] for i in (0, n[0]) for j in (0, n[1]) for k in (0, n[2])], float)
    pf = T.inverse(G._world(corners, fp.affine))
    ijk = (pf - lie_aff[:3, 3]) @ np.linalg.inv(lie_aff[:3, :3]).T
    lo = np.clip(np.floor(ijk.min(0)).astype(int) - 1, 0, shape)
    hi = np.clip(np.ceil(ijk.max(0)).astype(int) + 2, 0, shape)
    out_myo = np.zeros(shape, bool)
    out_cav = np.zeros(shape, bool)
    out_seg = np.zeros(shape, np.int16)
    out_u = np.full(shape, np.nan, np.float32)
    out_col = np.full(shape, -1, np.int64)
    if (hi > lo).all():
        box = tuple(slice(a, b) for a, b in zip(lo, hi))
        grid = np.indices(hi - lo).reshape(3, -1).T + lo
        pm = T.forward(G._world(grid.astype(float), lie_aff))
        bshape = tuple(hi - lo)
        far = dict(mode="constant", cval=1e6)
        myo_sdf = _sample(fp.sdf_myo, fp.affine, pm, 1, **far).reshape(bshape)
        cav_sdf = _sample(fp.sdf_cav, fp.affine, pm, 1, **far).reshape(bshape)
        cav = cav_sdf < 0
        myo = (myo_sdf < 0) & ~cav
        nearest = dict(mode="nearest")
        seg = _sample(fp.seg_ext, fp.affine, pm, 0, **nearest).reshape(bshape).astype(np.int16)
        u = _sample(fp.u_ext, fp.affine, pm, 0, **nearest).reshape(bshape)
        col = _sample(fp.col_ext, fp.affine, pm, 0, **nearest).reshape(bshape)
        out_myo[box], out_cav[box] = myo, cav
        out_seg[box] = np.where(myo, seg, 0)
        out_u[box] = np.where(myo, u, np.nan)
        out_col[box] = np.where(myo, col, -1)
    return CarriedGeometry(
        myo=out_myo,
        cavity=out_cav,
        segments=out_seg,
        u=out_u,
        column=out_col,
        spacing=lie_sp,
        affine=lie_aff,
    )


# ---------------------------------------------------------------------------------- the phase step
def signed_endo_distance(cavity: np.ndarray, spacing) -> np.ndarray:
    """mm from the carried endocardium, half-voxel corrected (Golf's convention, JA15; Kilo E8):
    negative in the cavity, positive outside it; boundary voxels sit at -h/2 and +h/2."""
    sp = np.asarray(spacing, float)
    if not cavity.any():
        return np.full(cavity.shape, np.inf, np.float32)
    h = float(np.mean(sp))
    inside = ndi.distance_transform_edt(cavity, sampling=sp) - h / 2
    outside = ndi.distance_transform_edt(~cavity, sampling=sp) - h / 2
    return np.where(cavity, -inside, outside).astype(np.float32)


def _kilo_crossing(d: np.ndarray, v: np.ndarray) -> float:
    """Kilo E8's half-way crossing of the mean profile v(d), in Kilo's sign (+ = the LIE's edge lies
    outside the carried border, i.e. the LIE cavity is larger). NaN when undefined."""
    if d.size < EDGE_MIN_VOXELS:
        return float("nan")
    lo, hi = EDGE_PROFILE_MM
    edges = np.arange(lo, hi + 1e-6, EDGE_BIN_MM)
    k = np.digitize(d, edges) - 1
    nb = len(edges) - 1
    cnt = np.bincount(k[(k >= 0) & (k < nb)], minlength=nb)
    tot = np.bincount(k[(k >= 0) & (k < nb)], weights=v[(k >= 0) & (k < nb)], minlength=nb)
    prof = np.where(cnt > EDGE_MIN_BIN_VOXELS, tot / np.maximum(cnt, 1), np.nan)
    mid = (edges[:-1] + edges[1:]) / 2
    bsel = (mid >= EDGE_BLOOD_MM[0]) & (mid <= EDGE_BLOOD_MM[1]) & np.isfinite(prof)
    wsel = (mid >= EDGE_WALL_MM[0]) & (mid <= EDGE_WALL_MM[1]) & np.isfinite(prof)
    if not bsel.any() or not wsel.any():
        return float("nan")
    b, w = float(np.median(prof[bsel])), float(np.median(prof[wsel]))
    if abs(b - w) < 1e-3:
        return float("nan")
    half = (b + w) / 2
    ok = np.isfinite(prof)
    f, m = (prof[ok] - half) * np.sign(b - w), mid[ok]  # f > 0 on the blood side
    for i in range(len(f) - 1):
        if f[i] > 0 >= f[i + 1]:
            return float(m[i] + (m[i + 1] - m[i]) * f[i] / (f[i] - f[i + 1]))
    return float("nan")


def edge_offset(
    smoothed: np.ndarray, carried: CarriedGeometry, segments: Sequence[int]
) -> float:
    """JA52's secondary flag (Kilo E8's definition) in **JA44's canonical sign**.

    The signed distance from the carried endocardium (half-voxel corrected) at which the mean
    smoothed-LIE profile over ``segments`` (cavity and wall voxels whose nearest carried-wall
    voxel is in those segments, -6 to +4 mm, 0.5 mm bins) crosses half-way between blood (bins
    -6 to -3 mm) and remote wall (+1.5 to +3.5 mm).

    Sign conversion: Kilo E8 (and Golf E9's code) report + when the LIE's edge lies outward of the
    carried border (the LIE cavity is larger). JA44's canonical sign is + when the region bounded by
    the border (the carried cavity) extends beyond the image's half-maximum, i.e. the LIE cavity
    is smaller. So ``edge_offset = -kilo_offset``: a larger LIE cavity reads negative.
    """
    cav, wall = carried.cavity, carried.segments > 0
    if not cav.any() or not wall.any():
        return float("nan")
    sd = signed_endo_distance(cav, carried.spacing)
    _, ind = ndi.distance_transform_edt(~wall, sampling=carried.spacing, return_indices=True)
    near = carried.segments[tuple(ind)]
    lo, hi = EDGE_PROFILE_MM
    region = (sd >= lo) & (sd <= hi) & (cav | wall) & np.isin(near, list(segments))
    return -_kilo_crossing(sd[region].astype(float), smoothed[region].astype(float))


@dataclass
class PhaseCheck:
    """JA52 as amended by JA84. ``routing_flags`` holds the edge offset only and is what
    ``suspect`` reads; ``advisory_flags`` holds ``rim_dark``, which is logged and shown to the
    reader after the decision but routes no patient. ``flags`` lists both (routing first)."""

    evaluable: bool
    contrast: float
    rim_dark: float
    rim_dark_cut: float
    #: JA44 canonical sign (see :func:`edge_offset`), over the 6 remote segments
    edge_offset_mm: float
    edge_offset_cut_mm: float
    #: IQR over segments 1-16 of the per-segment edge offset (logged only)
    edge_offset_iqr_mm: float
    #: log det of the affine stage's matrix (logged only; None when affine did not run)
    log_det_affine: Optional[float]
    log_det_final: float
    routing_flags: List[str] = field(default_factory=list)
    advisory_flags: List[str] = field(default_factory=list)

    @property
    def flags(self) -> List[str]:
        return list(self.routing_flags) + list(self.advisory_flags)

    @property
    def suspect(self) -> bool:
        """JA84: the routing flag (the edge offset) fired. ``rim_dark`` alone never sets this."""
        return bool(self.routing_flags)

    def summary(self) -> dict:
        def r(x):
            return None if x is None or not np.isfinite(x) else round(float(x), 4)

        return {
            "evaluable": self.evaluable,
            "contrast_sd": r(self.contrast),
            "rim_dark": r(self.rim_dark),
            "rim_dark_cut": r(self.rim_dark_cut),
            "edge_offset_mm": r(self.edge_offset_mm),
            "edge_offset_sign": "JA44 (+ = carried cavity beyond the LIE half-maximum)",
            "edge_offset_cut_mm": r(self.edge_offset_cut_mm),
            "edge_offset_iqr_mm": r(self.edge_offset_iqr_mm),
            "log_det_affine": r(self.log_det_affine),
            "log_det_final": r(self.log_det_final),
            "flags": self.flags,
            "routing_flags": list(self.routing_flags),
            "advisory_flags": list(self.advisory_flags),
            "phase_flag": self.suspect,
        }


def phase_step(
    lie: np.ndarray,
    carried: CarriedGeometry,
    cuts: QCCuts,
    *,
    final_qc: Optional[QC] = None,
    log_det_affine: Optional[float] = None,
    log_det_final: float = 0.0,
    defs: QCDefinitions = DEFAULT_QC_DEFINITIONS,
) -> PhaseCheck:
    """JA52 as amended by JA84, on one stage's carried geometry.

    - **Not evaluable** when (blood median - remote) < 2 robust SD of remote: no flag (phase then
      rests on the DICOM fields and the reader).
    - **Routing flag** ``edge_offset``: |edge offset| above ``cuts.max_edge_offset_mm``. It sees a
      larger and a smaller LIE cavity alike.
    - **Advisory flag** ``rim_dark``: above its phase cut (``cuts.rim_dark_phase``). It marks
      misregistration in general, so on its own it routes no patient (JA84).
    - **Logged only:** the affine log-determinant and the edge offset's per-segment IQR.
    """
    sm = smooth(lie, carried.spacing, defs.smooth_fwhm_mm)
    q = final_qc if final_qc is not None else _qc_smoothed(sm, carried, defs)
    rem = remote(sm, carried.segments, carried.core())
    contrast = q.contrast
    evaluable = bool(np.isfinite(contrast) and contrast >= MIN_PHASE_CONTRAST_SD)
    off = edge_offset(sm, carried, rem.segments) if rem is not None else float("nan")
    per = np.array([edge_offset(sm, carried, [s]) for s in range(1, 17)])
    per = per[np.isfinite(per)]
    iqr = float(np.subtract(*np.percentile(per, [75, 25]))) if per.size >= 2 else float("nan")
    routing, advisory = [], []
    if evaluable:
        if np.isfinite(off) and abs(off) > cuts.max_edge_offset_mm:
            routing.append("edge_offset")
        if np.isfinite(q.rim_dark) and q.rim_dark > cuts.rim_dark_phase:
            advisory.append("rim_dark")
    return PhaseCheck(
        evaluable=evaluable,
        contrast=contrast,
        rim_dark=q.rim_dark,
        rim_dark_cut=cuts.rim_dark_phase,
        edge_offset_mm=off,
        edge_offset_cut_mm=cuts.max_edge_offset_mm,
        edge_offset_iqr_mm=iqr,
        log_det_affine=log_det_affine,
        log_det_final=float(log_det_final),
        routing_flags=routing,
        advisory_flags=advisory,
    )


# ---------------------------------------------------------------------------------- the chain
@dataclass
class Stage:
    name: str
    transform: Transform
    qc: QC
    qc_passed: bool
    mi: float
    seconds: float
    kept: bool = True
    info: dict = field(default_factory=dict)

    def summary(self) -> dict:
        return {
            "name": self.name,
            "qc": asdict(self.qc),
            "qc_passed": self.qc_passed,
            "mi": round(self.mi, 5),
            "seconds": round(self.seconds, 2),
            "kept": self.kept,
            "matrix": np.round(self.transform.matrix, 6).tolist(),
            "translation_mm": np.round(self.transform.translation, 4).tolist(),
            "centre_mm": np.round(self.transform.centre, 4).tolist(),
            **self.info,
        }


class RoutedStatus(str):
    """A JA26 status string that also carries its JA85 ``route`` (``confirmed``, ``flag_only``, or
    ``None`` for a patient not routed to the ``phase_unmatched`` stratum). It compares and prints
    as the status itself."""

    route: Optional[str]

    def __new__(cls, status: str, route: Optional[str] = None):
        if route is not None and route not in PHASE_ROUTES:
            raise ValueError(f"route must be one of {PHASE_ROUTES} or None, not {route!r}")
        out = super().__new__(cls, status)
        out.route = route
        return out

    @property
    def status(self) -> str:
        return str(self)


def status_from_checks(
    checks: Sequence[bool],
    *,
    phase_flag: bool = False,
    phase_source: Optional[str] = None,
    reader_phase_mark: bool = False,
) -> RoutedStatus:
    """JA29 reader check -> JA26 status, routed by JA85. Returns a :class:`RoutedStatus` (the status
    string, with ``.route``).

    Reader check: pass first time -> passed; fail, then pass after the one re-registration ->
    re-registered; two fails -> not graded. Before a check (or between the fail and the
    re-registration's check) the status is "awaiting reader check".

    JA85, with ``phase_flag`` the routing flag (the edge offset, JA84), ``phase_source`` one of
    :data:`PHASE_SOURCES` (JA59) and ``reader_phase_mark`` the reader's "cavity size differs
    (phase)":

    ===================  =========  ===========  ===================================================
    phase source         edge flag  reader mark  status, route
    ===================  =========  ===========  ===================================================
    ``dicom_unmatched``  any        any          ``phase suspect``, ``confirmed`` (outside yield)
    matched / inferred   any        yes          ``phase suspect``, ``confirmed`` (outside yield)
    ``inferred``         yes        no           ``phase suspect``, ``flag_only`` (charged to yield)
    ``dicom_matched``    yes        no           ordinary: the reader check decides (route None)
    any                  no         no           ordinary (route None)
    ===================  =========  ===========  ===================================================

    A flagged patient whose phase source is not recorded cannot be routed and stays "awaiting
    reader check" (fails closed: it cannot be scored)."""
    checks = [bool(c) for c in checks]
    if len(checks) > 2 or (len(checks) == 2 and checks[0]):
        raise ValueError(f"JA29 allows one check, or a fail and one re-check: {checks}")
    if phase_source is not None and phase_source not in PHASE_SOURCES:
        raise ValueError(f"phase_source must be one of {PHASE_SOURCES}, not {phase_source!r}")
    if phase_source == PHASE_DICOM_UNMATCHED or reader_phase_mark:
        return RoutedStatus(PHASE_SUSPECT, ROUTE_CONFIRMED)
    if phase_flag:
        if phase_source == PHASE_INFERRED:
            return RoutedStatus(PHASE_SUSPECT, ROUTE_FLAG_ONLY)
        if phase_source is None:
            return RoutedStatus(AWAITING)
    if not checks:
        return RoutedStatus(AWAITING)
    if checks[0]:
        return RoutedStatus(PASSED)
    if len(checks) == 1:
        return RoutedStatus(AWAITING)
    return RoutedStatus(REREGISTERED if checks[1] else NOT_GRADED)


@dataclass
class Registration:
    """One patient's registration attempt (1, or 2 after a failed reader check)."""

    stages: List[Stage]
    final: Stage
    carried: CarriedGeometry
    cuts: QCCuts
    attempt: int
    shift_mm: np.ndarray
    initial_shift_mm: Optional[np.ndarray]
    case_id: Optional[str] = None
    reader_checks: List[bool] = field(default_factory=list)
    geometry_flags: List[str] = field(default_factory=list)
    phase: Optional[PhaseCheck] = None
    mask_mm: float = MASK_DILATION_MM
    fallback_mm: Optional[float] = FALLBACK_MASK_MM
    protocol: Optional[str] = None
    #: The last 4 mm stage (the result after JA51 step 4) and its carried geometry; ``None`` means
    #: the final stage is that stage.
    stage_4mm: Optional[Stage] = None
    carried_4mm: Optional[CarriedGeometry] = None
    #: The phase step on the last 4 mm stage, when step 5 was reached (JA82); else ``None``.
    phase_4mm: Optional[PhaseCheck] = None
    #: JA82: whether the 4 mm routing flag skipped step 5 (only with
    #: ``phase_check_before_fallback``).
    step5_skipped: bool = False
    #: JA59 / JA85: the phase source (:data:`PHASE_SOURCES`) and the reader's phase mark.
    phase_source: Optional[str] = None
    reader_phase_mark: bool = False

    @property
    def transform(self) -> Transform:
        return self.final.transform

    @property
    def qc_passed(self) -> bool:
        return self.final.qc_passed

    @property
    def phase_flag(self) -> bool:
        """JA84's routing flag on the final stage (under JA82's skip, the final stage is the 4 mm
        stage that flagged)."""
        return bool(self.phase is not None and self.phase.suspect)

    @property
    def routed_status(self) -> RoutedStatus:
        return status_from_checks(
            self.reader_checks,
            phase_flag=self.phase_flag,
            phase_source=self.phase_source,
            reader_phase_mark=self.reader_phase_mark,
        )

    @property
    def status(self) -> str:
        return str(self.routed_status)

    @property
    def phase_route(self) -> Optional[str]:
        """JA85: ``confirmed``, ``flag_only``, or ``None`` (not in the phase-unmatched stratum)."""
        return self.routed_status.route

    @property
    def phase_suspect(self) -> bool:
        return self.status == PHASE_SUSPECT

    @property
    def graded_stage(self) -> Stage:
        """The stage scar is graded on: the final stage, except that a phase-suspect patient is
        graded on its last 4 mm stage, never on the 10 mm fallback (JA85)."""
        if self.phase_suspect and self.stage_4mm is not None:
            return self.stage_4mm
        return self.final

    @property
    def graded_carried(self) -> CarriedGeometry:
        """The carried geometry of :attr:`graded_stage`."""
        if self.graded_stage is self.final or self.carried_4mm is None:
            return self.carried
        return self.carried_4mm

    @property
    def reregistration_allowed(self) -> bool:
        """JA51 step 6: only a first attempt that failed its reader check and is not phase suspect
        (JA52: registration cannot fix phase). A DICOM-matched patient whose flag the reader does
        not confirm is an ordinary patient (JA85) and can be re-registered."""
        return self.attempt == 1 and self.reader_checks == [False] and not self.phase_suspect

    def record_reader_check(self, passed: bool, *, phase_mark: bool = False) -> str:
        """Record this attempt's reader check, and the reader's "cavity size differs (phase)" mark
        (JA85); returns the status."""
        expect = 1 if self.attempt == 1 else 2
        if len(self.reader_checks) != expect - 1:
            raise ValueError(f"attempt {self.attempt} already has its reader check")
        self.reader_checks.append(bool(passed))
        self.reader_phase_mark = bool(self.reader_phase_mark or phase_mark)
        return self.status

    def log(self) -> dict:
        """The per-patient JA29 / JA51 / JA52 log, JSON-ready."""
        cuts = asdict(self.cuts)
        cuts["gate"] = list(cuts["gate"])
        return {
            "scar_version": SCAR_VERSION,
            "geometry_version": G.GEOMETRY_VERSION,
            "case_id": self.case_id,
            "attempt": self.attempt,
            "initial_shift_mm": None
            if self.initial_shift_mm is None
            else np.round(self.initial_shift_mm, 3).tolist(),
            "mask_mm": self.mask_mm,
            "fallback_mm": self.fallback_mm,
            "protocol": self.protocol,
            "stages": [s.summary() for s in self.stages],
            "final_stage": self.final.name,
            "qc_passed": self.qc_passed,
            "qc_cuts": cuts,
            "phase": None if self.phase is None else self.phase.summary(),
            "phase_4mm": None if self.phase_4mm is None else self.phase_4mm.summary(),
            "step5_skipped": self.step5_skipped,
            "graded_stage": self.graded_stage.name,
            "phase_source": self.phase_source,
            "reader_phase_mark": self.reader_phase_mark,
            "estimated_shift_mm": np.round(self.shift_mm, 3).tolist(),
            "estimated_shift_norm_mm": round(float(np.linalg.norm(self.shift_mm)), 3),
            "reader_checks": list(self.reader_checks),
            "status": self.status,
            "phase_route": self.phase_route,
            "geometry_flags": list(self.geometry_flags),
        }


def estimated_shift(fp: FirstPass, T: Transform) -> np.ndarray:
    """Mean displacement (mm) of the first-pass wall from its first-pass to its LIE position."""
    p = fp.myo_world
    return (T.inverse(p) - p).mean(0)


def _log_det(matrix: np.ndarray) -> float:
    det = float(np.linalg.det(matrix))
    return float(np.log(det)) if det > 0 else float("nan")


def register_lie(
    first_pass: FirstPass,
    lie,
    lie_affine,
    cuts: QCCuts | FittedQCCuts,
    *,
    protocol: Optional[str] = None,
    defs: QCDefinitions = DEFAULT_QC_DEFINITIONS,
    initial_shift_mm: Optional[Sequence[float]] = None,
    attempt: int = 1,
    previous_checks: Sequence[bool] = (),
    previous_phase_suspect: bool = False,
    phase_source: Optional[str] = None,
    phase_check_before_fallback: bool = False,
    affine_variant: Optional[str] = None,
    case_id=None,
    levels_mm: Sequence[float] = (2.0, 0.0),
    n_samples: int = 30_000,
    bins: int = 48,
    maxfev: int = 2000,
    seed: int = 0,
) -> Registration:
    """Run the JA51 chain (affine rule JA81) and the JA52 / JA84 phase step on one patient.

    ``cuts`` is a :class:`QCCuts`, or :class:`FittedQCCuts` from :func:`fit_qc_cuts` (then
    ``protocol`` picks the key, and the shares' cuts are read at the patient's own
    blood-to-remote contrast at R0).

    ``initial_shift_mm`` is the reader's manual shift for a re-registration (the heart's
    displacement from the first pass to the LIE, world mm); pass it with ``attempt=2`` and the
    first attempt's ``previous_checks`` (``[False]``). A first attempt flagged by the phase step
    (``previous_phase_suspect``) is never re-registered.

    ``phase_source`` is the patient's JA59 phase source (:data:`PHASE_SOURCES`), used by the JA85
    routing in :attr:`Registration.status`.

    ``phase_check_before_fallback`` turns on JA82's skip: when step 5 would run and the last 4 mm
    stage's routing flag fires (evaluable, |edge offset| above its cut), step 5 is skipped and the
    4 mm stage is final. **Off by default:** its PS4-S5 acceptance replay missed, so JA51 step 5
    ships unchanged (JA82). The 4 mm phase check is computed and logged either way.

    ``affine_variant`` (PS4-S7, report only): ``None`` is the shipped optimiser; ``"scaled"`` runs
    :func:`_affine_scaled`. Not used by default; adoption needs a later ruling.
    """
    guard_case(case_id, "janusm.scar.registration.register_lie")
    if phase_source is not None and phase_source not in PHASE_SOURCES:
        raise ValueError(f"phase_source must be one of {PHASE_SOURCES}, not {phase_source!r}")
    if affine_variant not in AFFINE_VARIANTS:
        raise ValueError(f"affine_variant must be one of {AFFINE_VARIANTS}, not {affine_variant!r}")
    if not isinstance(cuts, (QCCuts, FittedQCCuts)):
        raise TypeError("cuts must be a QCCuts set on development (JA53); there is no default")
    if attempt not in (1, 2):
        raise ValueError("JA29 allows one re-registration")
    if attempt == 2 and (initial_shift_mm is None or list(previous_checks) != [False]):
        raise ValueError("a re-registration starts from a manual shift after one failed check")
    if attempt == 2 and previous_phase_suspect:
        raise ValueError("JA52: a phase-suspect patient is not re-registered")
    lie = np.asarray(lie, np.float32)
    lie_aff = np.asarray(lie_affine, float)
    lie_sp = np.linalg.norm(lie_aff[:3, :3], axis=0)
    shift = None if initial_shift_mm is None else np.asarray(initial_shift_mm, float)
    t0 = np.zeros(3) if shift is None else -shift  # p_moving = p_fixed - shift
    start = Transform(np.eye(3), t0, first_pass.centre)
    last = len(levels_mm) - 1
    metric = _metric(first_pass, lie, lie_aff, lie_sp, levels_mm, n_samples, bins, seed)
    ranges = metric.ranges(last, start)

    car0 = carry(first_pass, start, lie.shape, lie_aff)
    q0 = qc(lie, car0, defs)
    if isinstance(cuts, FittedQCCuts):
        cuts = cuts.cuts_for(protocol, q0.contrast)

    def stage(name, T, secs, met=metric, rng=ranges, car=None, q=None):
        car = carry(first_pass, T, lie.shape, lie_aff) if car is None else car
        q = qc(lie, car, defs) if q is None else q
        mi = -met.cost(last, T, *rng)
        return Stage(name, T, q, q.passes(cuts), mi, secs), car

    stages = []
    s, car = stage(STAGE_R0, start, 0.0, car=car0, q=q0)
    stages.append(s)
    final, final_car = s, car
    log_det_affine = None
    if not s.qc_passed:
        tic = time.time()
        rig = _rigid(metric, first_pass.centre, start, maxfev)
        s_r, car_r = stage(STAGE_RIGID, rig, time.time() - tic)
        stages.append(s_r)
        final, final_car = s_r, car_r
        if not s_r.qc_passed:
            tic = time.time()
            if affine_variant is None:
                aff = _affine_from(metric, rig, maxfev)
            else:
                aff = _affine_scaled(metric, rig, maxfev)
            s_a, car_a = stage(STAGE_AFFINE, aff, time.time() - tic)
            sanity = affine_sanity(aff.matrix)
            rule = affine_rule(aff.matrix, s_a.qc, s_r.qc, cuts)
            s_a.kept = rule["kept"]
            s_a.info = {
                "sanity": sanity,
                "affine_rule": "JA81 (g)",
                "normalised_qc_rule": bool(rule["max_not_raised"] and rule["passes_or_scaled"]),
                **{k: rule[k] for k in ("max_not_raised", "passes_or_scaled")},
                "normalised_max_affine": rule["normalised_max_affine"],
                "normalised_max_rigid": rule["normalised_max_rigid"],
            }
            if affine_variant is not None:
                s_a.info["optimiser_variant"] = affine_variant
            log_det_affine = sanity["log_det"]
            stages.append(s_a)
            if s_a.kept:
                final, final_car = s_a, car_a
    stage_4mm, carried_4mm = final, final_car
    phase_4mm = None
    step5_skipped = False
    if not final.qc_passed and first_pass.fallback_mask is not None:
        # JA82: the phase step on the last 4 mm stage, logged; with the switch on, a routing flag
        # here skips step 5.
        phase_4mm = phase_step(
            lie,
            final_car,
            cuts,
            final_qc=final.qc,
            log_det_affine=log_det_affine,
            log_det_final=_log_det(final.transform.matrix),
            defs=defs,
        )
        step5_skipped = bool(phase_check_before_fallback and phase_4mm.suspect)
        if not step5_skipped:
            met10 = _metric(
                first_pass, lie, lie_aff, lie_sp, levels_mm, n_samples, bins, seed,
                mask=first_pass.fallback_mask,
            )
            rng10 = met10.ranges(last, start)
            tic = time.time()
            rig10 = _rigid(met10, first_pass.centre, start, maxfev)
            s_f, car_f = stage(STAGE_FALLBACK, rig10, time.time() - tic, met10, rng10)
            m_new, m_old = normalised_max(s_f.qc, cuts), normalised_max(final.qc, cuts)
            lowers = bool(np.isfinite(m_new) and np.isfinite(m_old) and m_new < m_old)
            s_f.kept = bool(s_f.qc_passed or lowers)
            s_f.info = {
                "mask_mm": first_pass.fallback_mm,
                "normalised_max": None if not np.isfinite(m_new) else round(m_new, 5),
                "replaced_normalised_max": None if not np.isfinite(m_old) else round(m_old, 5),
            }
            stages.append(s_f)
            if s_f.kept:
                final, final_car = s_f, car_f
    if step5_skipped:
        phase = phase_4mm  # the 4 mm stage is final: the same check
    else:
        phase = phase_step(
            lie,
            final_car,
            cuts,
            final_qc=final.qc,
            log_det_affine=log_det_affine,
            log_det_final=_log_det(final.transform.matrix),
            defs=defs,
        )
    reg = Registration(
        stages=stages,
        final=final,
        carried=final_car,
        cuts=cuts,
        attempt=attempt,
        shift_mm=estimated_shift(first_pass, final.transform),
        initial_shift_mm=shift,
        case_id=None if case_id is None else str(case_id),
        reader_checks=list(previous_checks),
        geometry_flags=first_pass.geometry_flags,
        phase=phase,
        mask_mm=first_pass.mask_mm,
        fallback_mm=first_pass.fallback_mm,
        protocol=protocol,
        stage_4mm=None if stage_4mm is final else stage_4mm,
        carried_4mm=None if stage_4mm is final else carried_4mm,
        phase_4mm=phase_4mm,
        step5_skipped=step5_skipped,
        phase_source=phase_source,
    )
    log.info(
        "JA51 %s attempt %d: final %s, QC %s, phase %s, shift %.2f mm",
        case_id or "<phantom>",
        attempt,
        final.name,
        "passed" if final.qc_passed else "failed",
        ",".join(phase.flags) or ("ok" if phase.evaluable else "not evaluable"),
        float(np.linalg.norm(reg.shift_mm)),
    )
    return reg


# ---------------------------------------------------------------------------------- development
def failure_rate(statuses: Iterable[str]) -> float:
    """Share of patients not graded (two failed reader checks). Every status must be final.
    Phase-suspect patients are not registration failures and are left out entirely (JA52)."""
    st = list(statuses)
    bad = [s for s in st if s not in (PASSED, REREGISTERED, NOT_GRADED, PHASE_SUSPECT)]
    if bad:
        raise ValueError(f"not every patient has a final registration status: {sorted(set(bad))}")
    st = [s for s in st if s != PHASE_SUSPECT]
    if not st:
        raise ValueError("no patients with a registration status (phase-suspect ones excluded)")
    return sum(s == NOT_GRADED for s in st) / len(st)


def seal_grading_allowed(development_statuses: Iterable[str]) -> bool:
    """JA29: a development failure rate above 10 % stops seal grading."""
    return failure_rate(development_statuses) <= MAX_FAILURE_RATE


def phase_suspect_share(statuses: Iterable[str]) -> float:
    st = list(statuses)
    if not st:
        raise ValueError("no patients")
    return sum(s == PHASE_SUSPECT for s in st) / len(st)


def phase_suspect_needs_report(development_statuses: Iterable[str]) -> bool:
    """JA52 stop rule: a development phase-suspect share above 20 % is reported to the lead before
    any seal patient is read."""
    return phase_suspect_share(development_statuses) > PHASE_SUSPECT_REPORT_SHARE


# ---------------------------------------------------------------------------------- QC cuts (JA53)
#: JA53: a protocol key gets its own cuts with at least this many reader-passed records.
MIN_PROTOCOL_RECORDS = 15
#: JA53: the p95 over reader-passed development records.
CUT_PERCENTILE = 95.0
#: JA53 drop rule: a value catching fewer than this share of reader fails leaves the gate.
MIN_CATCH_RATE = 0.5
#: Records per contrast bin of the monotone p95 band (an implementation choice), and at most
#: this many bins.
BAND_BIN_RECORDS = 30
BAND_MAX_BINS = 10
POOLED = "pooled"
#: The three shares fitted against contrast (JA53); rim_dark is a plain p95.
BANDED = QC_NAMES[:3]
#: JA83: the provisional cuts' source, the v3 benchmark's registered-case cuts.
BENCH_SCORES = Path(__file__).resolve().parents[3] / "experiments/JanusM/bench_lie/scores_v3.json"
#: ... the key they sit under (shipped QC names, keyed ``half|blood|cnr``); rim_dark phase cuts:
BENCH_CUTS_KEY = "qc_cuts_registered"
BENCH_PHASE_KEY = "rim_dark_phase_cuts_ja53"


def _pav(y: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Weighted pool-adjacent-violators: the non-decreasing least-squares fit."""
    blocks = []  # [value, weight, count]
    for yi, wi in zip(y, w):
        blocks.append([float(yi), float(wi), 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            v2, w2, n2 = blocks.pop()
            v1, w1, n1 = blocks.pop()
            blocks.append([(v1 * w1 + v2 * w2) / (w1 + w2), w1 + w2, n1 + n2])
    return np.concatenate([[v] * n for v, _, n in blocks])


@dataclass(frozen=True)
class ContrastBand:
    """A monotone p95 band of one QC share against blood-to-remote contrast: the cut at each knot,
    linear in between, flat outside. A NaN contrast gives a NaN cut (the value then fails)."""

    contrast: Tuple[float, ...]
    cut: Tuple[float, ...]

    def at(self, contrast: float) -> float:
        if not np.isfinite(contrast):
            return float("nan")
        return float(np.interp(contrast, self.contrast, self.cut))

    @classmethod
    def fit(cls, contrast: np.ndarray, values: np.ndarray) -> ContrastBand:
        ok = np.isfinite(contrast) & np.isfinite(values)
        x, y = np.asarray(contrast, float)[ok], np.asarray(values, float)[ok]
        if y.size == 0:
            raise ValueError("no finite (contrast, value) pair to fit a QC cut on")
        nb = int(np.clip(y.size // BAND_BIN_RECORDS, 1, BAND_MAX_BINS))
        order = np.argsort(x, kind="stable")
        parts = np.array_split(order, nb)
        xc = np.array([np.median(x[p]) for p in parts])
        yc = np.array([np.percentile(y[p], CUT_PERCENTILE) for p in parts])
        w = np.array([len(p) for p in parts], float)
        up = _pav(yc, w)
        down = -_pav(-yc, w)
        fit = up if ((up - yc) ** 2 * w).sum() <= ((down - yc) ** 2 * w).sum() else down
        return cls(tuple(float(v) for v in xc), tuple(float(v) for v in fit))


@dataclass(frozen=True)
class ProtocolCuts:
    """One protocol key's (or the pooled) JA53 cuts."""

    fatlike: ContrastBand
    bloodlike: ContrastBand
    brighter_than_blood: ContrastBand
    rim_dark: float
    rim_dark_phase: float
    n_reader_passed: int
    n_phase_matched: int


@dataclass(frozen=True)
class FittedQCCuts:
    """JA53's development cuts: per protocol key (``pooled`` for the rest), the drop rule's gate,
    and how often each value caught a reader fail. Frozen with the JA28 freeze."""

    protocols: Mapping[str, ProtocolCuts]
    gate: Tuple[bool, bool, bool, bool]
    catch_rate: Tuple[float, float, float, float]
    n_records: int
    n_reader_failed: int
    max_edge_offset_mm: float = EDGE_OFFSET_FLAG_MM

    def protocol_cuts(self, protocol: Optional[str]) -> ProtocolCuts:
        if protocol is not None and str(protocol) in self.protocols:
            return self.protocols[str(protocol)]
        return self.protocols[POOLED]

    def cuts_for(self, protocol: Optional[str], contrast: float) -> QCCuts:
        """The :class:`QCCuts` for one patient: its protocol key (pooled if the key had fewer than
        15 reader-passed records) at its own blood-to-remote contrast."""
        p = self.protocol_cuts(protocol)
        return QCCuts(
            max_fatlike=p.fatlike.at(contrast),
            max_bloodlike=p.bloodlike.at(contrast),
            max_brighter_than_blood=p.brighter_than_blood.at(contrast),
            max_rim_dark=p.rim_dark,
            gate=self.gate,
            max_rim_dark_phase=p.rim_dark_phase,
            max_edge_offset_mm=self.max_edge_offset_mm,
        )

    def to_json(self) -> dict:
        """The frozen JSON for ``configs/janusm/paired-r2.json`` (counts only; no case id)."""

        def band(b: ContrastBand):
            return {"contrast": list(b.contrast), "cut": list(b.cut)}

        return {
            "ruling": "JA53 (Round 3 - paired-scar), PS3-S5",
            "frozen": True,
            "scar_version": SCAR_VERSION,
            "percentile": CUT_PERCENTILE,
            "contrast": "(blood median - remote) / robust SD of remote",
            "n_records": self.n_records,
            "n_reader_failed": self.n_reader_failed,
            "gate": dict(zip(QC_NAMES, self.gate)),
            "catch_rate": {
                k: (None if not np.isfinite(v) else round(float(v), 4))
                for k, v in zip(QC_NAMES, self.catch_rate)
            },
            "max_edge_offset_mm": self.max_edge_offset_mm,
            "protocols": {
                key: {
                    **{n: band(getattr(p, n)) for n in BANDED},
                    "rim_dark": p.rim_dark,
                    "rim_dark_phase": p.rim_dark_phase,
                    "n_reader_passed": p.n_reader_passed,
                    "n_phase_matched": p.n_phase_matched,
                }
                for key, p in self.protocols.items()
            },
        }

    @classmethod
    def from_json(cls, d: Mapping) -> FittedQCCuts:
        if not d.get("frozen"):
            raise ValueError("QC cuts must be the frozen JA53 output")

        def band(x):
            return ContrastBand(tuple(map(float, x["contrast"])), tuple(map(float, x["cut"])))

        protos = {
            k: ProtocolCuts(
                **{n: band(v[n]) for n in BANDED},
                rim_dark=float(v["rim_dark"]),
                rim_dark_phase=float(v["rim_dark_phase"]),
                n_reader_passed=int(v["n_reader_passed"]),
                n_phase_matched=int(v["n_phase_matched"]),
            )
            for k, v in d["protocols"].items()
        }
        if POOLED not in protos:
            raise ValueError("frozen QC cuts have no pooled key")
        cr = d.get("catch_rate", {})
        return cls(
            protocols=protos,
            gate=tuple(bool(d["gate"][n]) for n in QC_NAMES),
            catch_rate=tuple(
                float("nan") if cr.get(n) is None else float(cr[n]) for n in QC_NAMES
            ),
            n_records=int(d["n_records"]),
            n_reader_failed=int(d["n_reader_failed"]),
            max_edge_offset_mm=float(d.get("max_edge_offset_mm", EDGE_OFFSET_FLAG_MM)),
        )


def _record_values(rec: Mapping) -> np.ndarray:
    q = rec["qc"]
    if isinstance(q, QC):
        return q.values()
    return np.array([float(q[n]) if q.get(n) is not None else np.nan for n in QC_NAMES], float)


def _p95(v: np.ndarray) -> float:
    v = v[np.isfinite(v)]
    if v.size == 0:
        raise ValueError("no finite value to fit a QC cut on")
    return float(np.percentile(v, CUT_PERCENTILE))


def _fit_protocol(recs: Sequence[Mapping]) -> ProtocolCuts:
    vals = np.array([_record_values(r) for r in recs], float).reshape(-1, 4)
    con = np.array([float(r["contrast"]) for r in recs], float)
    matched = np.array([bool(r["phase_matched"]) for r in recs], bool)
    if not matched.any():
        raise ValueError("JA53: rim_dark's phase cut needs phase-matched reader-passed records")
    return ProtocolCuts(
        fatlike=ContrastBand.fit(con, vals[:, 0]),
        bloodlike=ContrastBand.fit(con, vals[:, 1]),
        brighter_than_blood=ContrastBand.fit(con, vals[:, 2]),
        rim_dark=_p95(vals[:, 3]),
        rim_dark_phase=_p95(vals[matched, 3]),
        n_reader_passed=len(recs),
        n_phase_matched=int(matched.sum()),
    )


def fit_qc_cuts(records: Iterable[Mapping]) -> FittedQCCuts:
    """JA53: set the QC cuts once on development.

    Each record is one development patient: ``case_id`` (required: the JA12 guard runs on every id
    first and fails closed), ``qc`` (the four values, a mapping or a :class:`QC`), ``reader_pass``
    (the reader's first check, blind to every QC value), ``protocol`` (the key), ``contrast``
    ((blood median - remote) / robust SD of remote) and ``phase_matched``.

    - Each cut is the p95 over reader-passed records, per protocol key with >= 15 of them, pooled
      otherwise.
    - The fat-like, blood-like and brighter-than-blood cuts are monotone p95 bands against
      contrast (:class:`ContrastBand`); ``rim_dark`` is a plain p95, and its phase cut the p95 over
      phase-matched reader-passed records.
    - Drop rule: a value that is above its cut in fewer than 50 % of reader fails is marked
      ``gate=False`` (it stays logged). With no reader fail the rule cannot run and every value
      stays gated. If every value would leave the gate, this raises: the lead decides.
    """
    recs = list(records)
    if not recs:
        raise ValueError("no development records")
    ids = [r.get("case_id") for r in recs]
    if any(i is None or str(i) == "" for i in ids):
        raise ValueError("every development record needs a case_id for the JA12 guard")
    for i in ids:
        guard_case(i, "janusm.scar.registration.fit_qc_cuts")
    passed = [r for r in recs if bool(r["reader_pass"])]
    failed = [r for r in recs if not bool(r["reader_pass"])]
    if not passed:
        raise ValueError("no reader-passed development record")
    by_key: dict = {}
    for r in passed:
        by_key.setdefault(str(r["protocol"]), []).append(r)
    protos = {POOLED: _fit_protocol(passed)}
    for key, rs in sorted(by_key.items()):
        if len(rs) >= MIN_PROTOCOL_RECORDS:
            if key == POOLED:
                raise ValueError(f"{POOLED!r} is reserved and cannot be a protocol key")
            protos[key] = _fit_protocol(rs)
    provisional = FittedQCCuts(protos, (True,) * 4, (np.nan,) * 4, len(recs), len(failed))
    if failed:
        caught = np.zeros(4)
        for r in failed:
            c = provisional.cuts_for(str(r["protocol"]), float(r["contrast"])).values()
            v = _record_values(r)
            caught += ~(np.isfinite(v) & np.isfinite(c) & (v <= c))  # NaN counts as caught
        rate = caught / len(failed)
        gate = tuple(bool(x >= MIN_CATCH_RATE) for x in rate)
        if not any(gate):
            raise ValueError(
                f"JA53 drop rule would drop every QC value (catch rates {np.round(rate, 3)}); "
                "report to the lead"
            )
    else:
        rate, gate = np.full(4, np.nan), (True,) * 4
    return FittedQCCuts(protos, gate, tuple(float(x) for x in rate), len(recs), len(failed))


def save_qc_cuts(fitted: FittedQCCuts, path) -> Path:
    """Write the frozen JSON (for ``configs/janusm/paired-r2.json``). Cuts are never moved after
    the JA28 freeze, so an existing file is refused."""
    p = Path(path)
    if p.exists():
        raise FileExistsError(f"{p} exists: frozen QC cuts are never moved (JA28, JA53)")
    p.write_text(json.dumps(fitted.to_json(), indent=1, sort_keys=True) + "\n")
    return p


def load_qc_cuts(path) -> FittedQCCuts:
    return FittedQCCuts.from_json(json.loads(Path(path).read_text()))


def load_provisional_qc_cuts(
    path=BENCH_SCORES, *, blood: str, cnr: int, half: Optional[int] = None
) -> QCCuts:
    """JA83's provisional cuts until development: p95 of the **shipped** QC over **registered**
    benchmark cases (``bench_lie/scores_v3.json`` -> ``qc_cuts_registered``: rigid4 with TRE < 1 mm
    on motions none and rigid, other half, keyed ``half|blood|cnr``) at the matching blood level and
    CNR. ``max_rim_dark_phase`` is ``rim_dark_phase_cuts_ja53`` (advisory only, JA84).

    The file must declare ``qc_definitions`` equal to :data:`QC_DEFINITIONS`; any other file
    (v2's ``scores.json``, measured with v2's QC on aligned images, has none) is refused.

    ``half`` picks one of the benchmark's two cross-fitted halves; ``None`` takes each value's
    larger cut over the halves."""
    d = json.loads(Path(path).read_text())
    declared = d.get("qc_definitions")
    if declared != QC_DEFINITIONS:
        raise ValueError(
            f"{path}: QC cuts declare qc_definitions {declared!r}, not {QC_DEFINITIONS!r} "
            "(JA83: a cut file must be measured with the shipped QC definitions)"
        )
    if BENCH_CUTS_KEY not in d or BENCH_PHASE_KEY not in d:
        raise ValueError(f"{path}: no {BENCH_CUTS_KEY!r} / {BENCH_PHASE_KEY!r} (JA83)")

    def pick(table):
        return [
            v for k, v in table.items()
            if k.split("|")[1:] == [str(blood), str(cnr)]
            and (half is None or k.split("|")[0] == str(half))
        ]

    rows, phase = pick(d[BENCH_CUTS_KEY]), pick(d[BENCH_PHASE_KEY])
    if not rows or not phase:
        raise KeyError(f"no benchmark QC cuts for blood {blood!r}, CNR {cnr}, half {half}")
    cut = {n: max(float(r[n]) for r in rows) for n in QC_NAMES}
    return QCCuts(
        max_fatlike=cut["fatlike"],
        max_bloodlike=cut["bloodlike"],
        max_brighter_than_blood=cut["brighter_than_blood"],
        max_rim_dark=cut["rim_dark"],
        max_rim_dark_phase=max(float(v) for v in phase),
    )
