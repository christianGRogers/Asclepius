"""Janus-M geometry (JA2-JA4): transmural depth and layers, AHA 17 segments, coronary territories.

Janus-M learns four borders (JA1). Everything Janus-M reports is computed from them here, by one
versioned module that replaces the Round 1 prototypes (``experiments/JanusM/{Golf,India,Juliet}``).

Input label map (JA1): 0 background, 1 LV myocardium, 2 LV blood pool, 3 RV blood pool, 4 LA blood
pool. Coronary map (D25): 0 background, 1 LM, 2 LAD, 3 LCx, 4 RCA. The caller chooses the tree
(JA4); this module never does.

Geometry is in world millimetres. Pass the NIfTI ``affine`` (RAS world, as nibabel gives it) or only
``spacing``; with spacing alone the voxel axes are taken as R, A, S. Distance transforms use the
voxel spacing (the column norms of the affine), so a sheared affine is not supported.

Rulings implemented (``vault/JanusM/Judgements/Round 1.md``):

- **JA2.** Depth u = d_endo / (d_endo + d_epi); thirds cut at 1/3 and 2/3. A segment whose wall is
  under 5 mm, or under 4 native voxels per third, gets halves instead. Laplace and Yezzi-Prince
  depths are alternatives behind ``method=``.
- **JA3.** The long axis runs from the mitral-plane centre (LV blood pool next to the LA) to the
  apex (the farthest myocardial cap). Basal, mid and apical are thirds of the cavity
  length; 17 is the cap beyond the cavity. Angle zero is the anterior RV insertion point (an end of
  the arc where classes 1 and 3 meet). Sectors are fixed: 60 degrees basal and mid, 90 apical. The
  septal arc and the orientation checks are reported, and a failed check sets ``flagged``.
- **JA4.** Each myocardial voxel takes the nearest LAD, LCx or RCA voxel (3-D Euclidean); LM is not
  a seed. A segment carries its majority territory. Geodesic assignment is behind ``method=``. The
  standard AHA map is always reported beside it.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.sparse.linalg import LinearOperator, cg
from scipy.spatial import cKDTree

#: Bump on any change that can move a reported number.
GEOMETRY_VERSION = "1.0.0"

# JA1 classes
BACKGROUND, MYO, LV, RV, LA = 0, 1, 2, 3, 4
# D25 coronary classes
LM, LAD, LCX, RCA = 1, 2, 3, 4
TERRITORY_NAMES = {LAD: "LAD", LCX: "LCx", RCA: "RCA"}

# Layer codes. Thirds 1-3; a segment that falls back to halves uses 11 and 12, so a third is never
# confused with a half.
SUBENDO, MIDWALL, SUBEPI = 1, 2, 3
INNER_HALF, OUTER_HALF = 11, 12

DEPTH_METHODS = ("equal_thickness", "laplace", "yezzi_prince")
TERRITORY_METHODS = ("euclidean", "geodesic")

SEGMENT_NAMES = {
    1: "basal anterior",
    2: "basal anteroseptal",
    3: "basal inferoseptal",
    4: "basal inferior",
    5: "basal inferolateral",
    6: "basal anterolateral",
    7: "mid anterior",
    8: "mid anteroseptal",
    9: "mid inferoseptal",
    10: "mid inferior",
    11: "mid inferolateral",
    12: "mid anterolateral",
    13: "apical anterior",
    14: "apical septal",
    15: "apical inferior",
    16: "apical lateral",
    17: "apex",
}
#: The standard AHA segment -> artery map, as commonly quoted from Cerqueira 2002.
AHA_STANDARD = {
    **{s: "LAD" for s in (1, 2, 7, 8, 13, 14, 17)},
    **{s: "RCA" for s in (3, 4, 9, 10, 15)},
    **{s: "LCx" for s in (5, 6, 11, 12, 16)},
}
AHA_STANDARD_NOTE = "Cerqueira 2002 map, verified from secondary sources only (JA4, JA14)"

_SIX = np.array([2, 3, 4, 5, 6, 1])  # basal 60-degree sectors from the anterior insertion
_FOUR = np.array([14, 15, 16, 13])  # apical 90-degree sectors, septal centred on mid-septum
_FACE = ndi.generate_binary_structure(3, 1)


# ------------------------------------------------------------------------------------------- frame
def _affine(shape: Sequence[int], spacing=None, affine=None) -> Tuple[np.ndarray, np.ndarray]:
    """(affine 4x4, spacing mm) from whichever the caller gave."""
    if len(shape) != 3:
        raise ValueError(f"expected a 3-D label map, got shape {tuple(shape)}")
    if affine is not None:
        a = np.asarray(affine, float)
        sp = np.linalg.norm(a[:3, :3], axis=0)
        if spacing is not None and not np.allclose(sp, spacing, rtol=1e-3):
            raise ValueError(f"spacing {tuple(spacing)} disagrees with the affine's {tuple(sp)}")
        return a, sp
    if spacing is None:
        raise ValueError("give spacing (mm) or an affine")
    sp = np.asarray(spacing, float)
    if sp.shape != (3,) or (sp <= 0).any():
        raise ValueError(f"bad spacing {spacing}")
    return np.diag([*sp, 1.0]), sp


def _world(ijk: np.ndarray, affine: np.ndarray) -> np.ndarray:
    return ijk @ affine[:3, :3].T + affine[:3, 3]


def _check_labels(labels: np.ndarray) -> np.ndarray:
    labels = np.asarray(labels)
    if labels.ndim != 3:
        raise ValueError(f"expected a 3-D label map, got shape {labels.shape}")
    bad = np.setdiff1d(np.unique(labels), [BACKGROUND, MYO, LV, RV, LA])
    if bad.size:
        raise ValueError(f"label map has values outside JA1's 0-4: {bad.tolist()}")
    return labels


# --------------------------------------------------------------------------------------------- JA2
@dataclass
class Depth:
    """Transmural depth (0 endocardium, 1 epicardium) and wall thickness (mm); NaN off the wall."""

    method: str
    u: np.ndarray
    thickness: np.ndarray
    d_endo: np.ndarray
    d_epi: np.ndarray


def depth(labels, spacing=None, affine=None, method: str = "equal_thickness") -> Depth:
    """Transmural depth of every LV myocardial voxel (JA2).

    ``equal_thickness`` (primary): u = d_endo / (d_endo + d_epi), with Euclidean distances (mm)
    from the voxel centre to the endocardial and epicardial surfaces. A surface lies half a voxel
    beyond the last wall voxel, so a wall N voxels across has thickness N voxels and its voxels sit
    at (k - 0.5) / N. Everything that is neither myocardium nor LV blood pool (RV, LA, background)
    is epicardial side.

    ``laplace``: the harmonic potential, 0 on the endocardium and 1 on the epicardium, with the
    boundary on the face between voxels (so a flat wall reproduces equal thickness).

    ``yezzi_prince``: lengths L0, L1 along the Laplace streamlines to each surface (Yezzi & Prince
    2003); u = L0 / (L0 + L1), thickness L0 + L1.

    ``thickness`` is d_endo + d_epi for the first two, L0 + L1 for Yezzi-Prince.
    """
    if method not in DEPTH_METHODS:
        raise ValueError(f"method must be one of {DEPTH_METHODS}, not {method!r}")
    labels = _check_labels(labels)
    _, sp = _affine(labels.shape, spacing, affine)
    myo, lv = labels == MYO, labels == LV
    if not myo.any() or not lv.any():
        raise ValueError("depth needs both LV myocardium (1) and LV blood pool (2)")
    h = 0.5 * float(sp.mean())
    d_endo = ndi.distance_transform_edt(~lv, sampling=sp) - h
    inside = np.pad(myo | lv, 1)  # the array edge counts as outside the heart
    d_epi = ndi.distance_transform_edt(inside, sampling=sp)[1:-1, 1:-1, 1:-1] - h
    d_endo, d_epi = np.maximum(d_endo, 0.0), np.maximum(d_epi, 0.0)
    nan = np.full(labels.shape, np.nan, np.float32)
    de, dp, th, u = nan.copy(), nan.copy(), nan.copy(), nan.copy()
    de[myo], dp[myo] = d_endo[myo], d_epi[myo]
    th[myo] = de[myo] + dp[myo]
    if method == "equal_thickness":
        u[myo] = de[myo] / np.maximum(th[myo], 1e-6)
    else:
        phi = _laplace(myo, lv, sp)
        if method == "laplace":
            u[myo] = phi[myo]
        else:
            l0, l1 = _yezzi_prince(phi, myo, lv, sp)
            th[myo] = l0 + l1
            u[myo] = l0 / np.maximum(l0 + l1, 1e-6)
    return Depth(method=method, u=u, thickness=th, d_endo=de, d_epi=dp)


def _neighbours(myo: np.ndarray):
    """For each of the 6 face directions: (myocardial voxels, flat index of their neighbour or -1
    off the array, axis, direction)."""
    pts = np.argwhere(myo)
    shape = np.array(myo.shape)
    for ax in range(3):
        for d in (-1, 1):
            nb = pts.copy()
            nb[:, ax] += d
            ok = (nb[:, ax] >= 0) & (nb[:, ax] < shape[ax])
            flat = np.full(len(pts), -1, np.int64)
            flat[ok] = np.ravel_multi_index(tuple(nb[ok].T), myo.shape)
            yield pts, flat, ax, d


def _laplace(myo, lv, sp, rtol=1e-8, maxiter=10000) -> np.ndarray:
    """Harmonic potential on the myocardium: 0 at the LV-pool face, 1 at every other face."""
    pts = np.argwhere(myo)
    n = len(pts)
    idx = np.full(myo.size, -1, np.int64)
    idx[np.ravel_multi_index(tuple(pts.T), myo.shape)] = np.arange(n)
    lvf = lv.ravel()
    rows, cols, vals = [], [], []
    diag = np.zeros(n)
    b = np.zeros(n)
    ar = np.arange(n)
    for _, flat, ax, _ in _neighbours(myo):
        w = 1.0 / sp[ax] ** 2
        j = np.where(flat >= 0, idx[np.maximum(flat, 0)], -1)
        inner = j >= 0
        rows.append(ar[inner])
        cols.append(j[inner])
        vals.append(np.full(inner.sum(), -w))
        diag[inner] += w
        # Dirichlet face half a voxel away: twice the coupling
        endo = ~inner & (flat >= 0) & lvf[np.maximum(flat, 0)]
        epi = ~inner & ~endo
        diag[endo | epi] += 2 * w
        b[epi] += 2 * w
    rows.append(ar)
    cols.append(ar)
    vals.append(diag)
    a = coo_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)
    ).tocsr()
    pre = LinearOperator((n, n), matvec=lambda x: x / diag)
    tol = {"rtol" if "rtol" in inspect.signature(cg).parameters else "tol": rtol}  # scipy < 1.12
    x, info = cg(a, b, x0=np.full(n, 0.5), maxiter=maxiter, M=pre, **tol)
    if info != 0:
        raise RuntimeError(f"Laplace solve did not converge (info={info})")
    phi = np.full(myo.shape, np.nan, np.float32)
    phi[tuple(pts.T)] = np.clip(x, 0.0, 1.0)
    return phi


def _yezzi_prince(phi, myo, lv, sp, tol=1e-4, maxiter=2000):
    """Streamline lengths (mm) to the endocardium (L0) and epicardium (L1): upwind Jacobi sweeps of
    grad(L) . T = 1, with T the unit gradient of the Laplace potential."""
    full = np.where(myo, phi, np.where(lv, 0.0, 1.0)).astype(float)
    g = np.stack(np.gradient(full, *sp), axis=-1)[myo]
    t = g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)
    pts = np.argwhere(myo)
    n = len(pts)
    idx = np.full(myo.size, -1, np.int64)
    idx[np.ravel_multi_index(tuple(pts.T), myo.shape)] = np.arange(n)
    lvf = lv.ravel()
    nbr = {}
    for _, flat, ax, d in _neighbours(myo):
        j = np.where(flat >= 0, idx[np.maximum(flat, 0)], -1)
        is_lv = (j < 0) & (flat >= 0) & lvf[np.maximum(flat, 0)]
        nbr[ax, d] = (j, is_lv)

    def solve(sign: float, start_is_lv: bool) -> np.ndarray:
        # upwind along -sign*T: the neighbour the streamline arrives from
        coef, src, wall = [], [], []
        for ax in range(3):
            ta = sign * t[:, ax]
            for d in (-1, 1):
                use = (ta > 0) if d == -1 else (ta < 0)
                j, is_lv = nbr[ax, d]
                start = is_lv if start_is_lv else (j < 0) & ~is_lv
                c = np.abs(ta) / sp[ax] * use
                c = np.where(j >= 0, c, np.where(start, 2 * c, 0.0))  # far wall: no inflow
                coef.append(c)
                src.append(np.where(j >= 0, j, 0))
                wall.append(j < 0)
        coef, src, wall = np.array(coef), np.array(src), np.array(wall)
        csum = coef.sum(0)
        lone = csum <= 0
        csum[lone] = 2.0 / float(sp.mean())  # no upwind neighbour: half a voxel
        length = np.full(n, 0.5 * float(sp.mean()))
        for _ in range(maxiter):
            up = np.where(wall, 0.0, length[src])
            new = (1.0 + (coef * up).sum(0)) / csum
            new[lone] = 0.5 * float(sp.mean())
            if np.max(np.abs(new - length)) < tol:
                return new
            length = new
        raise RuntimeError("Yezzi-Prince sweep did not converge")

    return solve(1.0, True), solve(-1.0, False)


@dataclass
class Layers:
    """Layer label per voxel (thirds 1-3, or halves 11-12 where JA2 says so) and region detail."""

    label: np.ndarray
    regions: Dict[int, dict]


def layers(
    dep: Depth,
    spacing,
    segments: Optional[np.ndarray] = None,
    *,
    min_vox_per_third: float = 4.0,
    min_wall_mm: float = 5.0,
) -> Layers:
    """Cut the depth into thirds at 1/3 and 2/3, or into halves where the region is too thin (JA2).

    A region is an AHA segment when ``segments`` is given, else the whole myocardium (key 0; voxels
    with segment 0 also use the whole-myocardium decision). Its wall is the median thickness of its
    mid-wall voxels (|u - 1/2| < 1/6). Halves replace thirds when the wall is under ``min_wall_mm``
    or gives fewer than ``min_vox_per_third`` native voxels per third (voxel size = mean spacing).
    """
    sp = np.asarray(spacing, float)
    vox = float(sp.mean())
    myo = ~np.isnan(dep.u)
    seg = segments if segments is not None else np.zeros(dep.u.shape, np.int16)
    out = np.zeros(dep.u.shape, np.uint8)
    regions: Dict[int, dict] = {}

    def decide(sel):
        mid = sel & (np.abs(dep.u - 0.5) < 1 / 6)
        pool = dep.thickness[mid] if mid.any() else dep.thickness[sel]
        wall = float(np.median(pool))
        vpt = wall / 3 / vox
        halves = wall < min_wall_mm or vpt < min_vox_per_third
        return {
            "wall_mm": round(wall, 3),
            "vox_per_third": round(vpt, 2),
            "scheme": "halves" if halves else "thirds",
            "n_voxels": int(sel.sum()),
        }

    whole = decide(myo)
    regions[0] = whole
    keys = [int(k) for k in np.unique(seg[myo]) if k != 0]
    for k in [0, *keys]:
        sel = myo & (seg == k)
        if not sel.any():
            continue
        info = whole if k == 0 else decide(sel)
        regions[k] = info
        u = dep.u[sel]
        if info["scheme"] == "thirds":
            out[sel] = SUBENDO + np.minimum((u * 3).astype(int), 2)
        else:
            out[sel] = np.where(u < 0.5, INNER_HALF, OUTER_HALF)
    return Layers(label=out, regions=regions)


# --------------------------------------------------------------------------------------------- JA3
@dataclass
class AHA:
    """AHA 17 segments (0 = no segment) and the frame they were cut in (world mm)."""

    segments: Optional[np.ndarray]
    flagged: bool
    flags: List[str] = field(default_factory=list)
    septal_arc_deg: Optional[float] = None
    base_mm: Optional[List[float]] = None
    apex_mm: Optional[List[float]] = None
    cavity_length_mm: Optional[float] = None
    orientation: Dict[str, object] = field(default_factory=dict)
    frac_myo_above_base: Optional[float] = None


def aha17(
    labels,
    spacing=None,
    affine=None,
    *,
    mitral_mm: Optional[float] = None,
    insertion_mm: Optional[float] = None,
    apex_mm: float = 3.0,
    anterior: Sequence[float] = (0.0, 1.0, 1.0),
    arc_rings: Tuple[float, float] = (0.0, 2 / 3),
    above_base: str = "basal",
) -> AHA:
    """AHA 17 segments on the LV myocardium (JA3).

    - Base: centroid of the LV blood pool voxels next to the LA (face-adjacent, or within
      ``mitral_mm``). Apex: the centroid of the myocardium within ``apex_mm`` of the farthest
      distance from the base (one farthest voxel tilts the axis by the grid). The long axis joins
      them.
    - Rings: s along the axis, as a fraction of the cavity length (the LV pool's farthest extent):
      basal [0, 1/3), mid [1/3, 2/3), apical [2/3, 1]; segment 17 beyond the cavity. Myocardium
      above the base plane (s < 0) is basal (``above_base="basal"``) or left without a segment
      (``"drop"``).
    - Angle zero: the anterior RV insertion point. The RV-contact arc is the myocardium next to
      class 3 (face-adjacent, or within ``insertion_mm``) in the rings spanned by ``arc_rings``
      (cavity-length fractions; basal and mid by default). Of the arc's two ends, the anterior one
      points more along ``anterior`` (world RAS; default anterior-superior, Golf's rule B). The
      angle increases into the septum.
    - Sectors are fixed: basal and mid 60 degrees (anteroseptal, inferoseptal, inferior,
      inferolateral, anterolateral, anterior); apical 90 degrees with the septal sector centred on
      mid-septum.

    The septal arc and the orientation checks are returned. Any failure sets ``flagged``; a
    derivation failure also leaves ``segments`` as None.
    """
    labels = _check_labels(labels)
    aff, sp = _affine(labels.shape, spacing, affine)
    myo, lv, rv, la = (labels == c for c in (MYO, LV, RV, LA))
    if above_base not in ("basal", "drop"):
        raise ValueError("above_base must be 'basal' or 'drop'")

    def fail(why):
        return AHA(segments=None, flagged=True, flags=[why])

    if myo.sum() < 50 or lv.sum() < 50:
        return fail("LV myocardium or blood pool missing")
    if mitral_mm is None:
        mitral = lv & ndi.binary_dilation(la, _FACE)
    else:
        mitral = lv & (ndi.distance_transform_edt(~la, sampling=sp) <= mitral_mm)
    if mitral.sum() < 10:
        return fail("no mitral plane: LV blood pool does not touch the LA")
    base = _world(np.argwhere(mitral), aff).mean(0)
    pidx = np.argwhere(myo)
    p = _world(pidx, aff)
    dist = np.linalg.norm(p - base, axis=1)
    apex = p[dist >= dist.max() - apex_mm].mean(0)  # the farthest cap, not one voxel of it
    axis = (apex - base) / np.linalg.norm(apex - base)
    s = (p - base) @ axis
    cav_len = float(((_world(np.argwhere(lv), aff) - base) @ axis).max())
    if cav_len <= 0:
        return fail("LV cavity does not extend from the mitral plane toward the apex")

    # short-axis basis (any; the angle's sense is fixed by the RV arc below)
    helper = np.eye(3)[int(np.argmin(np.abs(axis)))]
    e1 = helper - (helper @ axis) * axis
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    rel = p - base
    ang = np.degrees(np.arctan2(rel @ e2, rel @ e1)) % 360.0

    if insertion_mm is None:
        contact = ndi.binary_dilation(rv, _FACE)[myo]
    else:
        contact = (ndi.distance_transform_edt(~rv, sampling=sp) <= insertion_mm)[myo]
    lo, hi = arc_rings
    contact &= (s >= lo * cav_len) & (s <= hi * cav_len)
    if contact.sum() < 10:
        return fail("no RV insertion: myocardium does not touch the RV blood pool")
    h = np.sort(ang[contact])
    gaps = np.diff(np.concatenate([h, h[:1] + 360.0]))
    g = int(np.argmax(gaps))
    start, end = float(h[(g + 1) % len(h)]), float(h[g])  # arc runs counter-clockwise start -> end
    arc = (end - start) % 360.0

    def direction(deg):
        r = np.radians(deg)
        return np.cos(r) * e1 + np.sin(r) * e2

    ant = np.asarray(anterior, float)
    ant = ant / np.linalg.norm(ant)
    if direction(start) @ ant >= direction(end) @ ant:
        ref, sign = start, 1.0
    else:
        ref, sign = end, -1.0
    theta = (sign * (ang - ref)) % 360.0  # 0 anterior insertion, + into the septum

    ring = np.where(s > cav_len, 3, np.clip((s / cav_len * 3).astype(int), 0, 2))
    seg = np.where(
        ring == 0,
        _SIX[(theta // 60).astype(int) % 6],
        np.where(
            ring == 1,
            _SIX[(theta // 60).astype(int) % 6] + 6,
            np.where(ring == 2, _FOUR[(((theta - 15) % 360) // 90).astype(int) % 4], 17),
        ),
    )
    above = s < 0
    if above_base == "drop":
        seg = np.where(above, 0, seg)
    out = np.zeros(labels.shape, np.int16)
    out[tuple(pidx.T)] = seg

    res = AHA(
        segments=out,
        flagged=False,
        septal_arc_deg=round(arc, 1),
        base_mm=[round(float(x), 2) for x in base],
        apex_mm=[round(float(x), 2) for x in apex],
        cavity_length_mm=round(cav_len, 2),
        frac_myo_above_base=round(float(above.mean()), 4),
    )
    res.orientation = orientation_checks(out, labels, aff)
    if not res.orientation["ok"]:
        res.flags.append("orientation check failed: " + ", ".join(res.orientation["failed"]))
    missing = [k for k in range(1, 18) if not (out == k).any()]
    if missing:
        res.flags.append(f"empty segments: {missing}")
    res.flagged = bool(res.flags)
    return res


def orientation_checks(segments: np.ndarray, labels: np.ndarray, affine) -> dict:
    """JA3's per-case checks (ported from Golf's ``aha_check.py``), in world RAS mm.

    - segment 1 lies anterior of segment 4 (``seg1_minus_seg4_anterior_mm`` > 0);
    - the septum (2, 3, 8, 9) faces the RV; the lateral wall (5, 6, 11, 12) faces away.
    ``seg1_minus_seg4_superior_mm`` is reported but not required.
    """
    aff = np.asarray(affine, float)
    if aff.shape == (3,):
        aff = np.diag([*aff, 1.0])
    labels = np.asarray(labels)

    def cen(mask):
        return _world(np.argwhere(mask), aff).mean(0) if mask.any() else None

    c_myo, c_rv = cen(labels == MYO), cen(labels == RV)
    c1, c4 = cen(segments == 1), cen(segments == 4)
    c_sep, c_lat = cen(np.isin(segments, (2, 3, 8, 9))), cen(np.isin(segments, (5, 6, 11, 12)))
    out: Dict[str, object] = {}
    failed = []
    if c1 is None or c4 is None:
        failed.append("segment 1 or 4 empty")
    else:
        d = c1 - c4
        out["seg1_minus_seg4_anterior_mm"] = round(float(d[1]), 2)
        out["seg1_minus_seg4_superior_mm"] = round(float(d[2]), 2)
        if d[1] <= 0:
            failed.append("segment 1 not anterior of segment 4")
    if c_rv is None or c_sep is None or c_lat is None:
        failed.append("RV, septum or lateral wall empty")
    else:
        rvdir = c_rv - c_myo
        out["septum_towards_rv"] = bool((c_sep - c_myo) @ rvdir > 0)
        out["lateral_away_from_rv"] = bool((c_lat - c_myo) @ rvdir < 0)
        if not out["septum_towards_rv"]:
            failed.append("septum not toward the RV")
        if not out["lateral_away_from_rv"]:
            failed.append("lateral wall not away from the RV")
    out["failed"] = failed
    out["ok"] = not failed
    return out


# ------------------------------------------------------------------------------- JA20 / JA69 (a)
ARC_AGREEMENT_MIN = 0.995  # JM-0R's guard: below it the recomputed frame is not JA3's
ARC_SEPTAL = (2, 3, 8, 9)  # the two septal segments of the basal and mid rings


def _aha_theta(labels, aff, aha):
    """The JA3 angle of every myocardial voxel (0 at the anterior insertion, + into the septum),
    recomputed exactly as :func:`aha17` does with its defaults. Returns (voxel indices, angle)."""
    myo, lv, rv, la = (labels == c for c in (MYO, LV, RV, LA))
    base = _world(np.argwhere(lv & ndi.binary_dilation(la, _FACE)), aff).mean(0)
    pidx = np.argwhere(myo)
    p = _world(pidx, aff)
    dist = np.linalg.norm(p - base, axis=1)
    apex = p[dist >= dist.max() - 3.0].mean(0)
    axis = (apex - base) / np.linalg.norm(apex - base)
    s = (p - base) @ axis
    cav = float(((_world(np.argwhere(lv), aff) - base) @ axis).max())
    helper = np.eye(3)[int(np.argmin(np.abs(axis)))]
    e1 = helper - (helper @ axis) * axis
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    rel = p - base
    ang = np.degrees(np.arctan2(rel @ e2, rel @ e1)) % 360.0
    contact = ndi.binary_dilation(rv, _FACE)[myo] & (s >= 0) & (s <= 2 / 3 * cav)
    h = np.sort(ang[contact])
    gaps = np.diff(np.concatenate([h, h[:1] + 360.0]))
    g = int(np.argmax(gaps))
    start, end = float(h[(g + 1) % len(h)]), float(h[g])

    def direction(deg):
        r = np.radians(deg)
        return np.cos(r) * e1 + np.sin(r) * e2

    ant = np.array([0.0, 1.0, 1.0]) / np.sqrt(2)
    ref, sign = (start, 1.0) if direction(start) @ ant >= direction(end) @ ant else (end, -1.0)
    return pidx, (sign * (ang - ref)) % 360.0


def arc_segments(labels, aff, aha: AHA, *, arc_deg: Optional[float] = None):
    """Septal sectors proportional to the measured septal arc in the basal and mid rings (JA20:
    the two septal segments of each ring; JA69 (a): the one implementation, which JM-0R imports).
    The apical ring and 17 stay as JA3 cuts them. ``labels``, ``aff`` and ``aha`` are the same
    full-size grid :func:`analyse` returns. ``arc_deg`` overrides the measured arc (tests; 120
    degrees reproduces the fixed sectors). Returns (segments, agreement of the recomputed fixed
    sectors with JA3's), or (None, None)."""
    if aha.segments is None or aha.septal_arc_deg is None and arc_deg is None:
        return None, None
    labels = np.asarray(labels)
    aff = np.asarray(aff, float)
    pidx, theta = _aha_theta(labels, aff, aha)
    fixed = aha.segments[tuple(pidx.T)]
    ring = np.isin(fixed, (1, 2, 3, 4, 5, 6)) | np.isin(fixed, (7, 8, 9, 10, 11, 12))
    if not ring.any():
        return None, None
    recomputed = _SIX[(theta // 60).astype(int) % 6] + np.where(fixed > 6, 6, 0)
    agree = float(np.mean(recomputed[ring] == fixed[ring]))
    arc = float(np.clip(aha.septal_arc_deg if arc_deg is None else arc_deg, 60.0, 240.0))
    rest = (360.0 - arc) / 4
    edges = [arc / 2, arc, arc + rest, arc + 2 * rest, arc + 3 * rest]
    k = np.searchsorted(edges, theta, side="right")
    new = _SIX[np.clip(k, 0, 5)] + np.where(fixed > 6, 6, 0)
    seg = aha.segments.copy()
    seg[tuple(pidx[ring].T)] = new[ring]
    return seg, agree


# --------------------------------------------------------------------------------------------- JA4
@dataclass
class Territories:
    """Territory per myocardial voxel (D25 codes 2-4, 0 elsewhere) and per-segment majorities."""

    method: str
    label: np.ndarray
    share: Dict[str, float]
    segments: Dict[int, dict]
    flags: List[str] = field(default_factory=list)
    standard_note: str = AHA_STANDARD_NOTE


def territories(
    labels,
    coronary,
    spacing=None,
    affine=None,
    *,
    segments: Optional[np.ndarray] = None,
    method: str = "euclidean",
    seed_mm: float = 5.0,
) -> Territories:
    """Coronary territories on the LV myocardium (JA4).

    ``euclidean`` (primary): each myocardial voxel takes the class of the nearest LAD, LCx or RCA
    voxel (3-D, world mm). LM is never a seed.

    ``geodesic``: the epicardial myocardium within ``seed_mm`` of a vessel is seeded with that
    vessel's class, and the classes spread through the myocardium by shortest path (26-neighbour,
    mm). Voxels no path reaches fall back to Euclidean, and are counted in ``flags``.

    With ``segments``, each segment gets its majority territory beside the standard AHA map.
    """
    labels = _check_labels(labels)
    coronary = np.asarray(coronary)
    if coronary.shape != labels.shape:
        raise ValueError(f"coronary map {coronary.shape} and label map {labels.shape} differ")
    aff, _ = _affine(labels.shape, spacing, affine)
    pts, cls = _seeds(coronary, aff)
    return _territories(labels, aff, pts, cls, segments, method, seed_mm)


def _seeds(coronary: np.ndarray, aff: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """World positions (mm) and classes of the LAD, LCx and RCA voxels; LM is not a seed."""
    bad = np.setdiff1d(np.unique(coronary), [0, LM, LAD, LCX, RCA])
    if bad.size:
        raise ValueError(f"coronary map must use D25's four classes (1-4); found {bad.tolist()}")
    idx = np.argwhere(np.isin(coronary, (LAD, LCX, RCA)))
    if len(idx) == 0:
        raise ValueError("coronary map has no LAD, LCx or RCA voxel")
    return _world(idx, aff), coronary[tuple(idx.T)].astype(np.uint8)


def _territories(labels, aff, seed_pts, seed_cls, segments, method, seed_mm) -> Territories:
    if method not in TERRITORY_METHODS:
        raise ValueError(f"method must be one of {TERRITORY_METHODS}, not {method!r}")
    myo = labels == MYO
    midx = np.argwhere(myo)
    mw = _world(midx, aff)
    _, nn = cKDTree(seed_pts).query(mw)
    cls = seed_cls[nn]
    flags: List[str] = []
    if method == "geodesic":
        cls, unreached = _geodesic(
            myo, labels == LV, midx, mw, seed_pts, seed_cls, aff, seed_mm, cls
        )
        if unreached:
            flags.append(f"{unreached} myocardial voxels unreached geodesically; Euclidean used")
    out = np.zeros(labels.shape, np.uint8)
    out[tuple(midx.T)] = cls
    share = {TERRITORY_NAMES[k]: round(float(np.mean(cls == k)), 4) for k in (LAD, LCX, RCA)}
    per: Dict[int, dict] = {}
    if segments is not None:
        for k in range(1, 18):
            sel = (segments == k) & myo
            if not sel.any():
                continue
            vals, cnt = np.unique(out[sel], return_counts=True)
            maj = TERRITORY_NAMES[int(vals[np.argmax(cnt)])]
            per[k] = {
                "territory": maj,
                "majority_share": round(float(cnt.max() / cnt.sum()), 3),
                "standard": AHA_STANDARD[k],
                "concordant": maj == AHA_STANDARD[k],
            }
    return Territories(method=method, label=out, share=share, segments=per, flags=flags)


def _geodesic(myo, lv, midx, mw, seed_pts, seed_cls, aff, seed_mm, fallback):
    n = len(midx)
    idx = np.full(myo.shape, -1, np.int64)
    idx[tuple(midx.T)] = np.arange(n)
    rows, cols, wts = [], [], []
    offs = [np.array(o) - 1 for o in np.ndindex(3, 3, 3)]
    offs = [o for o in offs if tuple(o) > (0, 0, 0)]  # the 13 forward neighbours
    shape = np.array(myo.shape)
    for o in offs:
        nb = midx + o
        ok = np.all((nb >= 0) & (nb < shape), axis=1)
        j = np.full(n, -1, np.int64)
        j[ok] = idx[tuple(nb[ok].T)]
        both = np.flatnonzero(j >= 0)
        w = float(np.linalg.norm(aff[:3, :3] @ o))
        rows += [both, j[both]]
        cols += [j[both], both]
        wts += [np.full(len(both), w)] * 2
    # epicardial myocardium: a face neighbour that is neither myocardium nor LV pool
    outside = ~np.pad(myo | lv, 1)
    epi = ndi.binary_dilation(outside, _FACE)[1:-1, 1:-1, 1:-1][tuple(midx.T)]
    epi_i = np.flatnonzero(epi)
    classes = (LAD, LCX, RCA)
    for c_i, c in enumerate(classes):
        pts = seed_pts[seed_cls == c]
        if len(pts) == 0:
            continue
        d, _ = cKDTree(pts).query(mw[epi_i], distance_upper_bound=seed_mm)
        hit = np.isfinite(d)
        rows.append(np.full(hit.sum(), n + c_i))
        cols.append(epi_i[hit])
        wts.append(np.maximum(d[hit], 1e-6))
    g = csr_matrix(
        (np.concatenate(wts), (np.concatenate(rows), np.concatenate(cols))), shape=(n + 3, n + 3)
    )
    dist, _, src = dijkstra(
        g, directed=True, indices=[n, n + 1, n + 2], min_only=True, return_predecessors=True
    )
    dist, src = dist[:n], src[:n]
    reached = np.isfinite(dist) & (src >= n)
    cls = fallback.copy()
    cls[reached] = np.array(classes, np.uint8)[src[reached] - n]
    return cls, int((~reached).sum())


# --------------------------------------------------------------------------------------------- all
@dataclass
class Geometry:
    """Everything JA2-JA4 computes for one case; ``report()`` is the JSON-ready segment table."""

    depth: Depth
    layers: Layers
    aha: AHA
    territories: Optional[Territories]
    spacing: Tuple[float, float, float]

    def report(self) -> dict:
        vox_ml = float(np.prod(self.spacing)) / 1000.0
        segs = {}
        for k in range(1, 18):
            reg = self.layers.regions.get(k)
            if reg is None:
                continue
            row = {
                "name": SEGMENT_NAMES[k],
                "n_voxels": reg["n_voxels"],
                "volume_ml": round(reg["n_voxels"] * vox_ml, 3),
                "wall_mm": reg["wall_mm"],
                "vox_per_third": reg["vox_per_third"],
                "layer_scheme": reg["scheme"],
                "standard_territory": AHA_STANDARD[k],
            }
            if self.territories is not None and k in self.territories.segments:
                t = self.territories.segments[k]
                row.update(
                    territory=t["territory"],
                    territory_share=t["majority_share"],
                    concordant=t["concordant"],
                )
            segs[k] = row
        a = self.aha
        out = {
            "geometry_version": GEOMETRY_VERSION,
            "depth_method": self.depth.method,
            "territory_method": self.territories.method if self.territories else None,
            "flagged": a.flagged or bool(self.territories and self.territories.flags),
            "flags": a.flags + (self.territories.flags if self.territories else []),
            "septal_arc_deg": a.septal_arc_deg,
            "orientation": a.orientation,
            "cavity_length_mm": a.cavity_length_mm,
            "frac_myo_above_base": a.frac_myo_above_base,
            "whole_myocardium": self.layers.regions[0],
            "segments": segs,
            "standard_territory_note": AHA_STANDARD_NOTE,
        }
        if self.territories is not None:
            out["territory_share"] = self.territories.share
        return out


def analyse(
    labels,
    spacing=None,
    affine=None,
    coronary=None,
    *,
    depth_method: str = "equal_thickness",
    territory_method: str = "euclidean",
    seed_mm: float = 5.0,
    margin_mm: float = 15.0,
    **aha_kw,
) -> Geometry:
    """Depth, layers, AHA 17 segments and (with ``coronary``) territories for one case.

    The work is done on a crop around the heart (``margin_mm``); every returned array is full size.
    Territory seeds come from the whole coronary map, not the crop. If the AHA derivation fails,
    layers are decided over the whole myocardium and no territory table is made;
    ``report()['flagged']`` says so.
    """
    labels = _check_labels(labels)
    aff, sp = _affine(labels.shape, spacing, affine)
    heart = np.isin(labels, (MYO, LV, RV, LA))
    if not heart.any():
        raise ValueError("label map is empty")
    nz = np.argwhere(heart)
    m = np.ceil(margin_mm / sp).astype(int)
    lo = np.maximum(nz.min(0) - m, 0)
    hi = np.minimum(nz.max(0) + m + 1, labels.shape)
    box = tuple(slice(a, b) for a, b in zip(lo, hi))
    caff = aff.copy()
    caff[:3, 3] = _world(lo[None].astype(float), aff)[0]
    lab = labels[box]

    dep = depth(lab, affine=caff, method=depth_method)
    a = aha17(lab, affine=caff, **aha_kw)
    lay = layers(dep, sp, a.segments)
    terr = None
    if coronary is not None and a.segments is not None:
        coronary = np.asarray(coronary)
        if coronary.shape != labels.shape:
            raise ValueError(f"coronary map {coronary.shape} and label map {labels.shape} differ")
        pts, cls = _seeds(coronary, aff)  # seeds from the whole volume, not only the crop
        terr = _territories(lab, caff, pts, cls, a.segments, territory_method, seed_mm)

    def full(x, fill):
        f = np.full(labels.shape, fill, x.dtype)
        f[box] = x
        return f

    dep = Depth(
        dep.method,
        full(dep.u, np.nan),
        full(dep.thickness, np.nan),
        full(dep.d_endo, np.nan),
        full(dep.d_epi, np.nan),
    )
    lay = Layers(full(lay.label, 0), lay.regions)
    if a.segments is not None:
        a.segments = full(a.segments, 0)
    if terr is not None:
        terr.label = full(terr.label, 0)
    return Geometry(
        depth=dep, layers=lay, aha=a, territories=terr, spacing=tuple(float(x) for x in sp)
    )


# --------------------------------------------------------------------------------------------- I/O
def _refuse_if_held_out(case_id: str, source=None, purpose=None) -> None:
    """JA12 GUARD CALL SITE: the one place this module checks a case by name.

    Calls :func:`janusm.guard.refuse`, which raises ``HeldOutError`` on a held-out case and
    ``GuardInputError`` when a pinned list is missing or changed. Fails closed: if the guard cannot
    be imported, loading is refused too.
    """
    try:
        from janusm import guard
    except ImportError as e:
        raise RuntimeError(
            f"JA12 guard (janusm.guard) unavailable; refusing to load {case_id!r}"
        ) from e
    kw = {} if purpose is None else {"purpose": purpose}
    guard.refuse([case_id], what="janusm.geometry.load_case", source=source, **kw)


def load_case(case_id: str, labels_path, coronary_path=None, *, source=None, purpose=None):
    """Load a JA1 label map (and optionally a D25 coronary map) from NIfTI, after the JA12 guard.

    ``case_id`` is the pool name (``<Source>__<case>``), or a bare public id with ``source``
    (for example ``"s0655"``, ``source="TotalSegmentator"``). ``purpose`` is passed to the guard
    (its default allows no Janus-M seal or decision case). Returns (labels, affine, coronary or
    None). The affine is kept as stored (no reorientation): every function here works in world mm
    from it.
    """
    _refuse_if_held_out(case_id, source=source, purpose=purpose)
    import nibabel as nib

    im = nib.load(str(labels_path))
    labels = np.asarray(im.dataobj).astype(np.int16)
    cor = None
    if coronary_path is not None:
        ci = nib.load(str(coronary_path))
        if ci.shape != im.shape or not np.allclose(ci.affine, im.affine, atol=1e-3):
            raise ValueError(f"{case_id}: coronary and label grids differ")
        cor = np.asarray(ci.dataobj).astype(np.int16)
    return labels, im.affine, cor
