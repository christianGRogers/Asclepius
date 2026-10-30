"""LIE-to-CCTA registration (JA29): scanner frame, QC, heart-masked Mattes MI rigid, then affine.

Ruling: ``vault/JanusM/Judgements/Round 2 - paired-scar.md`` JA29 (JA35 item 1).

- **Direction.** The first-pass CT is moving and the LIE is fixed: grading happens on the LIE grid,
  so LIE noise is never resampled (Golf). A transform here maps a fixed (LIE) world point, in mm,
  to the moving (first-pass) world point, as ITK's do.
- **Carried.** Myocardium and cavity through their signed distances (linear); AHA segments, depth u
  and the E-D column id by nearest neighbour (:class:`~janusm.scar.common.CarriedGeometry`).
- **Chain, stopping at the first stage that passes QC (Juliet's order):**

  1. ``R0``: scanner coordinates through the shared frame of reference (identity), or a reader's
     manual initial shift on a re-registration;
  2. QC (:func:`qc`): the fat-like and blood-like shares of the carried wall on the smoothed LIE
     (Juliet E6) and the share brighter than the LIE blood median (Kilo E5), each against a cut set
     on development (:class:`QCCuts`, no defaults);
  3. ``rigid``: Mattes MI, the metric masked to classes 1-4 dilated 10 mm;
  4. ``affine`` with the same mask, kept only if it lowers the QC values against rigid
     (:func:`affine_lowers_qc`).

  B-spline is not in the pipeline.
- **Reader check** (every patient, blind to LGE): :func:`status_from_checks` turns the pass/fail
  record into the JA26 status (passed, re-registered, not graded). A fail is re-registered once from
  a manual initial shift (:func:`register_lie` with ``initial_shift_mm`` and ``attempt=2``).
- **Logged per patient** (:meth:`Registration.log`): the estimated shift of the heart between the
  scans, every stage's parameters, QC values and MI.
- **Development stop:** :func:`seal_grading_allowed` (a not-graded rate above 10 %).

Mattes MI is implemented here (cubic B-spline Parzen windows on a joint histogram, Mattes 2003),
with a Powell search over two smoothing levels, so the module needs numpy and scipy only. The MI
settings (48 bins, sampled points, levels) are implementation choices taken from the advocates'
code (Kilo and Juliet: 48 bins; Juliet: two levels, Powell); none is a threshold.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Iterable, List, Optional, Sequence

import numpy as np
from scipy import ndimage as ndi
from scipy import optimize

from janusm import geometry as G
from janusm.scar import (
    AWAITING,
    NOT_GRADED,
    PASSED,
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

#: JA29: the MI metric is masked to classes 1-4 dilated by this much (mm).
MASK_DILATION_MM = 10.0
#: JA29: a development failure rate above this stops seal grading.
MAX_FAILURE_RATE = 0.10
#: E-D columns (JA30): 3 degrees about the long axis x 2 mm along it.
COLUMN_DEG = 3.0
COLUMN_MM = 2.0

STAGE_R0 = "R0"
STAGE_RIGID = "rigid"
STAGE_AFFINE = "affine"


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
    """The QC pass cuts: each share must be at most its cut. Set on development (JA29); there are
    deliberately no defaults."""

    max_fatlike: float
    max_bloodlike: float
    max_brighter_than_blood: float


#: The JA29 definitions as given (Juliet E6, Kilo E5).
DEFAULT_QC_DEFINITIONS = QCDefinitions()


@dataclass
class QC:
    """QC values of one carried wall on the smoothed LIE (NaN when undefined)."""

    fatlike: float
    bloodlike: float
    brighter_than_blood: float
    blood_median: float
    remote_median: float
    n_wall: int

    def values(self) -> np.ndarray:
        return np.array([self.fatlike, self.bloodlike, self.brighter_than_blood], float)

    def passes(self, cuts: QCCuts) -> bool:
        """All three at or under their cuts. Any NaN fails (closed)."""
        v = self.values()
        c = np.array([cuts.max_fatlike, cuts.max_bloodlike, cuts.max_brighter_than_blood], float)
        return bool(np.isfinite(v).all() and (v <= c).all())


def qc(
    lie: np.ndarray, carried: CarriedGeometry, defs: QCDefinitions = DEFAULT_QC_DEFINITIONS
) -> QC:
    """JA29 step 2 on one carried wall. The remote is JA30's; the blood median is over the carried
    cavity's core (one voxel inside, away from partial volume with the wall)."""
    sm = smooth(lie, carried.spacing, defs.smooth_fwhm_mm)
    wall = carried.myo
    n = int(wall.sum())
    nan = float("nan")
    if n == 0:
        return QC(nan, nan, nan, nan, nan, 0)
    blood_vox = sm[core_mask(carried.cavity)]
    if blood_vox.size == 0:
        blood_vox = sm[carried.cavity]
    blood = float(np.median(blood_vox)) if blood_vox.size else nan
    rem = remote(sm, carried.segments, carried.core())
    mu = rem.median if rem is not None else nan
    w = sm[wall]
    fat = float((w < defs.fat_hu).mean())
    if np.isfinite(blood) and np.isfinite(mu) and blood > mu:
        bloodlike = float((w > mu + defs.bloodlike_frac * (blood - mu)).mean())
    else:
        bloodlike = nan
    brighter = float((w > blood).mean()) if np.isfinite(blood) else nan
    return QC(fat, bloodlike, brighter, blood, mu, n)


def affine_lowers_qc(affine_qc: QC, rigid_qc: QC) -> bool:
    """JA29 step 4: affine is kept only if it lowers the QC values against rigid. Read as: no value
    rises and their sum falls. Any NaN keeps rigid."""
    a, r = affine_qc.values(), rigid_qc.values()
    if not (np.isfinite(a).all() and np.isfinite(r).all()):
        return False
    return bool((a <= r).all() and a.sum() < r.sum())


# ---------------------------------------------------------------------------------- first pass
@dataclass
class FirstPass:
    """The moving side, prepared once per patient (cropped round the heart)."""

    image: np.ndarray
    affine: np.ndarray
    spacing: np.ndarray
    mask: np.ndarray  # classes 1-4 dilated MASK_DILATION_MM
    sdf_myo: np.ndarray
    sdf_cav: np.ndarray
    seg_ext: np.ndarray  # nearest wall voxel's segment, everywhere in the crop
    u_ext: np.ndarray
    col_ext: np.ndarray
    myo_world: np.ndarray  # (n, 3) world mm of first-pass wall voxels, for the logged shift
    centre: np.ndarray  # rotation centre (world mm): the mask centroid
    geometry_flags: List[str] = field(default_factory=list)


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
    case_id=None,
) -> FirstPass:
    """Crop the first-pass CT and its JA1 labels round the heart and build what is carried.

    ``geometry`` is :func:`janusm.geometry.analyse` on the same grid (computed here when not
    given). It must have AHA segments; a failed derivation cannot be graded and raises.
    """
    guard_case(case_id, "janusm.scar.registration.prepare_first_pass")
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
    mask = ndi.distance_transform_edt(~hc, sampling=sp) <= MASK_DILATION_MM
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
    """p_moving = matrix (p_fixed - centre) + centre + translation (world mm)."""

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


def _metric(fp: FirstPass, lie, lie_aff, lie_sp, levels_mm, n_samples, bins, seed) -> _Metric:
    rng = np.random.default_rng(seed)
    idx = np.argwhere(fp.mask)
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


def _optimise(metric: _Metric, make, x0, step, maxfev) -> np.ndarray:
    x = np.asarray(x0, float)
    for level in range(len(metric.fixed_levels)):
        fr, mr = metric.ranges(level, make(x))

        def cost(q, level=level, fr=fr, mr=mr):
            return metric.cost(level, make(q), fr, mr)

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
        }


def status_from_checks(checks: Sequence[bool]) -> str:
    """JA29 reader check -> JA26 status: pass first time -> passed; fail, then pass after the one
    re-registration -> re-registered; two fails -> not graded. Before a check (or between the fail
    and the re-registration's check) the status is "awaiting reader check"."""
    checks = [bool(c) for c in checks]
    if len(checks) > 2 or (len(checks) == 2 and checks[0]):
        raise ValueError(f"JA29 allows one check, or a fail and one re-check: {checks}")
    if not checks:
        return AWAITING
    if checks[0]:
        return PASSED
    if len(checks) == 1:
        return AWAITING
    return REREGISTERED if checks[1] else NOT_GRADED


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

    @property
    def transform(self) -> Transform:
        return self.final.transform

    @property
    def qc_passed(self) -> bool:
        return self.final.qc_passed

    @property
    def status(self) -> str:
        return status_from_checks(self.reader_checks)

    def record_reader_check(self, passed: bool) -> str:
        """Record this attempt's reader check; returns the status."""
        expect = 1 if self.attempt == 1 else 2
        if len(self.reader_checks) != expect - 1:
            raise ValueError(f"attempt {self.attempt} already has its reader check")
        self.reader_checks.append(bool(passed))
        return self.status

    def log(self) -> dict:
        """The per-patient JA29 log, JSON-ready."""
        return {
            "scar_version": SCAR_VERSION,
            "geometry_version": G.GEOMETRY_VERSION,
            "case_id": self.case_id,
            "attempt": self.attempt,
            "initial_shift_mm": None
            if self.initial_shift_mm is None
            else np.round(self.initial_shift_mm, 3).tolist(),
            "stages": [s.summary() for s in self.stages],
            "final_stage": self.final.name,
            "qc_passed": self.qc_passed,
            "qc_cuts": asdict(self.cuts),
            "estimated_shift_mm": np.round(self.shift_mm, 3).tolist(),
            "estimated_shift_norm_mm": round(float(np.linalg.norm(self.shift_mm)), 3),
            "reader_checks": list(self.reader_checks),
            "status": self.status,
            "geometry_flags": list(self.geometry_flags),
        }


def estimated_shift(fp: FirstPass, T: Transform) -> np.ndarray:
    """Mean displacement (mm) of the first-pass wall from its first-pass to its LIE position."""
    p = fp.myo_world
    return (T.inverse(p) - p).mean(0)


def register_lie(
    first_pass: FirstPass,
    lie,
    lie_affine,
    cuts: QCCuts,
    *,
    defs: QCDefinitions = DEFAULT_QC_DEFINITIONS,
    initial_shift_mm: Optional[Sequence[float]] = None,
    attempt: int = 1,
    previous_checks: Sequence[bool] = (),
    case_id=None,
    levels_mm: Sequence[float] = (2.0, 0.0),
    n_samples: int = 30_000,
    bins: int = 48,
    maxfev: int = 2000,
    seed: int = 0,
) -> Registration:
    """Run the JA29 chain on one patient.

    ``initial_shift_mm`` is the reader's manual shift for a re-registration (the heart's
    displacement from the first pass to the LIE, world mm); pass it with ``attempt=2`` and the
    first attempt's ``previous_checks`` (``[False]``).
    """
    guard_case(case_id, "janusm.scar.registration.register_lie")
    if not isinstance(cuts, QCCuts):
        raise TypeError("cuts must be a QCCuts set on development (JA29); there is no default")
    if attempt not in (1, 2):
        raise ValueError("JA29 allows one re-registration")
    if attempt == 2 and (initial_shift_mm is None or list(previous_checks) != [False]):
        raise ValueError("a re-registration starts from a manual shift after one failed check")
    lie = np.asarray(lie, np.float32)
    lie_aff = np.asarray(lie_affine, float)
    lie_sp = np.linalg.norm(lie_aff[:3, :3], axis=0)
    shift = None if initial_shift_mm is None else np.asarray(initial_shift_mm, float)
    t0 = np.zeros(3) if shift is None else -shift  # p_moving = p_fixed - shift
    start = Transform(np.eye(3), t0, first_pass.centre)
    metric = _metric(first_pass, lie, lie_aff, lie_sp, levels_mm, n_samples, bins, seed)
    fr, mr = metric.ranges(len(levels_mm) - 1, start)

    def stage(name, T, secs):
        car = carry(first_pass, T, lie.shape, lie_aff)
        q = qc(lie, car, defs)
        mi = -metric.cost(len(levels_mm) - 1, T, fr, mr)
        return Stage(name, T, q, q.passes(cuts), mi, secs), car

    stages = []
    s, car = stage(STAGE_R0, start, 0.0)
    stages.append(s)
    final, final_car = s, car
    if not s.qc_passed:
        tic = time.time()
        rig = _rigid(metric, first_pass.centre, start, maxfev)
        s_r, car_r = stage(STAGE_RIGID, rig, time.time() - tic)
        stages.append(s_r)
        final, final_car = s_r, car_r
        if not s_r.qc_passed:
            tic = time.time()
            aff = _affine_from(metric, rig, maxfev)
            s_a, car_a = stage(STAGE_AFFINE, aff, time.time() - tic)
            s_a.kept = affine_lowers_qc(s_a.qc, s_r.qc)
            stages.append(s_a)
            if s_a.kept:
                final, final_car = s_a, car_a
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
    )
    log.info(
        "JA29 %s attempt %d: final %s, QC %s, shift %.2f mm",
        case_id or "<phantom>",
        attempt,
        final.name,
        "passed" if final.qc_passed else "failed",
        float(np.linalg.norm(reg.shift_mm)),
    )
    return reg


# ---------------------------------------------------------------------------------- development
def failure_rate(statuses: Iterable[str]) -> float:
    """Share of patients not graded (two failed reader checks). Every status must be final."""
    st = list(statuses)
    bad = [s for s in st if s not in (PASSED, REREGISTERED, NOT_GRADED)]
    if bad:
        raise ValueError(f"not every patient has a final registration status: {sorted(set(bad))}")
    if not st:
        raise ValueError("no patients")
    return sum(s == NOT_GRADED for s in st) / len(st)


def seal_grading_allowed(development_statuses: Iterable[str]) -> bool:
    """JA29: a development failure rate above 10 % stops seal grading."""
    return failure_rate(development_statuses) <= MAX_FAILURE_RATE
