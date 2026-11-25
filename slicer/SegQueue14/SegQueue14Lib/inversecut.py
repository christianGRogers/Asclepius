"""The arithmetic behind *Inverse cut* and D51's seeded extended classes.

Numpy only, no Slicer, Qt or VTK, so pytest checks it with plain arrays. The
Segment Editor effect (``SegmentEditorInverseCutEffect``) and the module's logic
(``SegQueue14.py``) call these; the voxels they produce are decided here.

* ``inverse_cut``: the selected segment keeps only its voxels inside the outlined
  region; an empty segment takes the vessel seed's voxels inside it instead
  (D51 a).
* ``inside_region``: which voxels of a mask project inside a lasso drawn in a
  view, the region extruded through the whole volume along the view direction,
  as Slicer's Scissors does by default.
* ``outline_in_pane``: a slice view's lasso moved from the view's event positions
  into the XY of the pane it was drawn in (a lightbox has several), which is
  what the slice node's XYToRAS expects (0.25.1).
* ``is_untouched_copy``: whether a class is still a voxel-for-voxel copy of the
  seed (D51 c and d).
"""

import numpy as np

#: A lasso is thinned to at most this many vertices before the voxel test: the
#: test costs one pass over the voxels per edge.
MAX_POLYGON_POINTS = 256


def simplify_polygon(points, max_points=MAX_POLYGON_POINTS):
    """``points`` as an ``(n, 2)`` float array, consecutive repeats dropped and
    thinned evenly to at most ``max_points`` vertices. Fewer than three distinct
    points is not a region, and comes back as an empty ``(0, 2)`` array."""
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    if len(pts):
        keep = np.ones(len(pts), bool)
        keep[1:] = np.any(np.diff(pts, axis=0) != 0, axis=1)
        pts = pts[keep]
    if len(pts) > max_points:
        pts = pts[np.linspace(0, len(pts) - 1, max_points).round().astype(int)]
    if len(np.unique(pts, axis=0)) < 3:
        return np.zeros((0, 2), float)
    return pts


def points_in_polygon(points, polygon):
    """Boolean ``(n,)``: which of ``points`` (``(n, 2)``) lie inside ``polygon``.

    Even-odd rule, the polygon closed from its last vertex to its first, so a
    lasso that crosses itself keeps what an even-odd fill would. Points exactly on
    an edge may fall either way.
    """
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    poly = np.asarray(polygon, dtype=float).reshape(-1, 2)
    inside = np.zeros(len(pts), bool)
    if len(poly) < 3 or not len(pts):
        return inside
    x, y = pts[:, 0], pts[:, 1]
    xj, yj = poly[-1]
    for xi, yi in poly:
        if yi != yj:
            crosses = (yi > y) != (yj > y)
            xcross = (xj - xi) * (y - yi) / (yj - yi) + xi
            inside ^= crosses & (x < xcross)
        xj, yj = xi, yi
    return inside


def project(ijk, ijk_to_display):
    """``(n, 2)`` display positions of voxel indices ``ijk`` (``(n, 3)``, i j k).

    ``ijk_to_display`` is a 4x4 matrix from voxel index to display coordinates,
    homogeneous: a slice view's is affine (the last row 0 0 0 1), a 3D view's
    carries the camera's perspective, and the divide by ``w`` handles both.
    """
    m = np.asarray(ijk_to_display, dtype=float).reshape(4, 4)
    ijk = np.asarray(ijk, dtype=float).reshape(-1, 3)
    h = ijk @ m[:3, :3].T + m[:3, 3]
    w = ijk @ m[3, :3] + m[3, 3]
    w = np.where(w == 0, 1e-12, w)
    return h[:, :2] / w[:, None]


def outline_in_pane(points, device_start, pane_start):
    """``(n, 2)``: a slice view's lasso in the XY of the pane it was drawn in.

    ``points`` are the interactor's event positions. ``device_start`` is the first
    of them and ``pane_start`` the same point as Slicer converts it
    (``vtkMRMLAbstractSliceViewDisplayableManager.ConvertDeviceToXYZ``, what
    Scissors uses), whose x and y are relative to the pane under the mouse. Every
    point moves by that one offset, so a lasso that strays across a lightbox pane
    border stays one shape in the pane it started in. Outside a lightbox the
    offset is zero and the points come back as they were.
    """
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    offset = (np.asarray(pane_start, dtype=float).reshape(-1)[:2]
              - np.asarray(device_start, dtype=float).reshape(-1)[:2])
    return pts + offset


def inside_region(mask, ijk_to_display, polygon):
    """Boolean array shaped like ``mask``: its voxels whose centre projects inside
    ``polygon``. Only the voxels set in ``mask`` are tested (the rest are False),
    which is what keeps a lasso over a whole CT cheap: a coronary seed is a few
    hundred thousand voxels.

    ``mask`` is indexed ``[k, j, i]``, as ``slicer.util.arrayFromVolume`` and
    ``arrayFromSegmentBinaryLabelmap`` return it.
    """
    mask = np.asarray(mask)
    out = np.zeros(mask.shape, bool)
    poly = simplify_polygon(polygon)
    if not len(poly):
        return out
    k, j, i = np.nonzero(mask)
    if not len(k):
        return out
    xy = project(np.stack([i, j, k], axis=1), ijk_to_display)
    out[k, j, i] = points_in_polygon(xy, poly)
    return out


def inverse_cut(segment, inside, seed=None):
    """``(result, source)``: what the selected segment becomes (D51 a).

    The segment keeps only its voxels inside the region. If it is empty and a seed
    is given, it becomes the seed's voxels inside the region instead. ``source``
    says which happened: ``"segment"`` or ``"seed"``; otherwise ``result`` is None
    and the segment is to be left alone, and ``source`` says why: ``None`` when
    there was nothing to cut (an empty segment and no seed, or an empty seed), and
    ``"outside"`` when the region holds none of the voxels it would keep.

    **Fail-safe (0.25.1).** A cut never empties the segment: an outline that
    misses every voxel is a slip, or a region that did not land where it was drawn
    (0.25.0 wiped whole segments that way in a lightbox view), not a request to
    delete the class.

    All arrays share one shape (one grid); ``result`` is 0/1 ``uint8``.
    """
    segment = np.asarray(segment) != 0
    inside = np.asarray(inside, dtype=bool)
    if segment.shape != inside.shape:
        raise ValueError("segment {} and region {} are not on one grid".format(
            segment.shape, inside.shape))
    if segment.any():
        return _kept(segment, inside, "segment")
    if seed is not None:
        seed = np.asarray(seed) != 0
        if seed.shape != inside.shape:
            raise ValueError("seed {} and region {} are not on one grid".format(
                seed.shape, inside.shape))
        if seed.any():
            return _kept(seed, inside, "seed")
    return None, None


def _kept(source, inside, name):
    kept = source & inside
    if not kept.any():
        return None, "outside"
    return kept.astype(np.uint8), name


def is_untouched_copy(mask, seed):
    """Whether ``mask`` is still exactly the seed, voxel for voxel (D51 c, d).

    Both on one grid. An empty seed has no copies: an empty class is empty, not a
    copy of an empty seed. Arrays of different shapes are never copies.
    """
    if mask is None or seed is None:
        return False
    mask, seed = np.asarray(mask), np.asarray(seed)
    if mask.shape != seed.shape:
        return False
    seed = seed != 0
    if not seed.any():
        return False
    return bool(np.array_equal(mask != 0, seed))
