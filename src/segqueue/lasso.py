"""Picking part of a mask by circling it in a 3D view.

``seedsplit`` divides the coronary mask between branches once it knows a few
voxels of each. This module is about the fastest way to say which voxels: look
at the tree in 3D, draw a loop around the branch, and everything under the loop
is that branch.

The whole difficulty is that a 3D view is flat. A loop drawn on screen is a
*tube* through the volume, and a naive "everything inside the tube" takes the
LAD the annotator circled **and** the RCA sitting thirty millimetres behind it,
which is worse than useless -- it is a mislabelling that looks like progress.
Slicer's own Scissors has exactly this behaviour, and it is the reason this is
not simply a call into Scissors.

So a loop selects **what the annotator can see**: within the loop, each screen
pixel keeps only the voxels nearest the camera, plus everything within a vessel's
thickness behind them. A branch in front shadows whatever is behind it, the same
way it does on the screen the annotator is looking at.

The far side of the circled vessel does not need to be selected, and is not.
What comes out of here is a set of *markers* handed to ``seedsplit``, which
floods the rest of the branch through the mask -- so circling the visible surface
of the LAD claims the whole LAD, back side included, and still claims nothing of
the RCA behind it.

Stdlib only, and pure geometry: display coordinates in, voxels out. The caller
does the projection (it needs the camera, which means VTK), and everything that
decides *which voxels* is here, where it can be tested without a renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

#: A voxel index, matching ``seedsplit.Voxel``: (k, j, i).
Voxel = Tuple[int, int, int]

#: A point on screen, in pixels.
Point = Tuple[float, float]

#: How far behind the nearest visible voxel a pixel still selects, in millimetres
#: along the view direction. A coronary artery is 1-4 mm across, so this keeps
#: the whole thickness of the circled vessel and drops a second vessel more than
#: a few millimetres behind it. It does not need to be generous: what it selects
#: are markers, and ``seedsplit`` floods the rest of the branch from them.
DEPTH_TOLERANCE_MM = 6.0

#: Pixels the near-surface test bins by. 1 is the honest answer -- a pixel is a
#: pixel -- and anything larger starts letting a vessel shadow its neighbour
#: sideways rather than only behind.
DEPTH_BUCKET_PX = 1.0

#: Shortest move, in pixels, that adds a point to the loop being drawn. A mouse
#: drag reports events far faster than a hand moves, so without this a slow
#: careful loop arrives as two thousand points, nearly all of them duplicates,
#: and every one of them costs a full pass over the mask.
MIN_STEP_PX = 4.0


@dataclass
class Selection:
    """What one loop picked out.

    ``hidden`` is the count the near-surface rule rejected -- voxels inside the
    loop but behind something else. Reported rather than dropped silently
    because it is the number that explains a surprise: a loop that looks like it
    covered two branches and selected one did exactly what it should, and the
    annotator is entitled to know that rather than to wonder.
    """

    voxels: Set[Voxel]
    #: Inside the loop, but behind a nearer voxel at the same pixel.
    hidden: int = 0
    #: Inside the loop's bounding box, but outside the loop itself.
    outside: int = 0
    #: Inside the loop and visible, but belonging to a different connected piece
    #: of the mask than the one the loop mostly covered. See ``select_visible``.
    elsewhere: int = 0

    def __bool__(self) -> bool:
        return bool(self.voxels)

    def __len__(self) -> int:
        return len(self.voxels)


def simplify(points: Iterable[Point], min_step: float = MIN_STEP_PX) -> List[Point]:
    """Thin a dragged path down to the points that actually turn corners.

    Keeps the first and last points always, so the loop still closes where the
    annotator released the button.
    """
    kept: List[Point] = []
    for point in points:
        x, y = float(point[0]), float(point[1])
        if not kept:
            kept.append((x, y))
            continue
        lx, ly = kept[-1]
        if abs(x - lx) >= min_step or abs(y - ly) >= min_step:
            kept.append((x, y))
    if len(kept) > 1:
        last = tuple(float(c) for c in list(points)[-1])  # type: ignore[arg-type]
        if kept[-1] != last:
            kept.append(last)  # type: ignore[arg-type]
    return kept


def polygon_contains(polygon: Sequence[Point], x: float, y: float) -> bool:
    """Whether (x, y) is inside the closed polygon. Crossing-number rule.

    The polygon is implicitly closed -- the caller does not repeat the first
    point -- because that is how a lasso arrives: a path and a released mouse
    button.

    Self-intersecting loops are normal here (a hand drawing quickly around a
    branch crosses its own line constantly), and the crossing-number rule handles
    them the way the annotator means: the region they drew around is inside.
    """
    inside = False
    count = len(polygon)
    if count < 3:
        return False
    j = count - 1
    for i in range(count):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        # Half-open test on y, so a vertex exactly on the ray is counted once
        # rather than twice or not at all.
        if (yi > y) != (yj > y):
            crossing = xi + (y - yi) * (xj - xi) / (yj - yi)
            if crossing > x:
                inside = not inside
        j = i
    return inside


def bounds(polygon: Sequence[Point]) -> Tuple[float, float, float, float]:
    """(xmin, ymin, xmax, ymax) of the loop."""
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return min(xs), min(ys), max(xs), max(ys)


def dominant_piece(
    voxels: Set[Voxel],
    pieces: Sequence[Set[Voxel]],
) -> Tuple[Set[Voxel], int]:
    """Narrow a selection to the connected piece of the mask holding most of it.

    Returns ``(kept, dropped)``.

    This is what stops a loop around one branch taking a different one behind it,
    and the per-pixel depth rule on its own does not: depth only decides between
    two voxels landing on the *same* pixel. A loop around a 3 mm artery is mostly
    empty screen, and across all that emptiness the vessel behind is the nearest
    thing there is -- so it is visible, it is inside the loop, and it is selected.
    Measured on a synthetic tree with the RCA directly behind the LAD, the depth
    rule alone let through eight and a half thousand RCA voxels.

    A loop means one branch, and a branch is connected. So: of the pieces the
    selection touches, keep the one it covers most of and drop the rest. That
    reads the gesture the way it was meant, and a branch genuinely split into two
    pieces by the source model just takes two loops -- selections accumulate.
    """
    if not voxels or not pieces:
        return set(voxels), 0

    best: Optional[Set[Voxel]] = None
    best_count = 0
    for piece in pieces:
        count = len(voxels & piece)
        if count > best_count:
            best, best_count = piece, count
    if best is None:
        return set(voxels), 0

    kept = voxels & best
    return kept, len(voxels) - len(kept)


def select_visible(
    projected: Iterable[Tuple[Voxel, float, float, float]],
    polygon: Sequence[Point],
    depth_tolerance: float = DEPTH_TOLERANCE_MM,
    bucket: float = DEPTH_BUCKET_PX,
    pieces: Optional[Sequence[Set[Voxel]]] = None,
) -> Selection:
    """The voxels a loop picks out: inside it, and not hidden behind others.

    ``projected`` is ``(voxel, x, y, depth)`` per mask voxel -- screen pixels and
    a depth in millimetres along the view direction, increasing away from the
    camera. The caller produces it from the camera; see the module docstring for
    why the split falls there.

    Three passes, cheapest first, because this runs on a mouse-release with tens
    of thousands of voxels and the annotator is waiting:

    1. **Bounding box.** A loop around one branch covers a small part of the
       screen, so this rejects most of the mask with two comparisons each.
    2. **Inside the loop.** Only now, and only for what survived the box, because
       this is the expensive test.
    3. **Near surface.** Per pixel, the nearest voxel and everything within
       ``depth_tolerance`` behind it. Last, so the depth bookkeeping is built
       only for what was actually circled -- and so the rule stays scoped to the
       loop, which is what keeps a branch crossing in front of the circled one,
       but outside the loop, from blanking out part of the selection.

    Then, if ``pieces`` is given (the mask's connected components), the selection
    is narrowed to the single piece it mostly covers. Pass it: on its own the
    depth rule does not stop a loop taking a vessel behind the circled one, for
    the reason set out in ``dominant_piece``.
    """
    if len(polygon) < 3:
        return Selection(voxels=set())

    xmin, ymin, xmax, ymax = bounds(polygon)
    outside = 0
    # Per pixel bucket: the nearest depth seen, and the voxels at that pixel.
    nearest: Dict[Tuple[int, int], float] = {}
    at_pixel: Dict[Tuple[int, int], List[Tuple[Voxel, float]]] = {}

    for voxel, x, y, depth in projected:
        if x < xmin or x > xmax or y < ymin or y > ymax:
            continue
        if not polygon_contains(polygon, x, y):
            outside += 1
            continue
        key = (int(x // bucket), int(y // bucket))
        at_pixel.setdefault(key, []).append((_as_voxel(voxel), depth))
        if key not in nearest or depth < nearest[key]:
            nearest[key] = depth

    chosen: Set[Voxel] = set()
    hidden = 0
    for key, entries in at_pixel.items():
        limit = nearest[key] + depth_tolerance
        for voxel, depth in entries:
            if depth <= limit:
                chosen.add(voxel)
            else:
                hidden += 1

    chosen, elsewhere = dominant_piece(chosen, pieces or ())
    return Selection(voxels=chosen, hidden=hidden, outside=outside,
                     elsewhere=elsewhere)


def describe(selection: Selection, branch: str) -> str:
    """One line about what a loop picked up, for the panel."""
    if not selection.voxels:
        return ("Nothing on the mask was inside that loop. Circle a branch of "
                "the tree itself, not empty space.")
    text = "Circled {} voxels for {}.".format(len(selection.voxels), branch)
    behind = selection.hidden + selection.elsewhere
    if behind:
        text += " {} more, on another branch behind it, were left alone.".format(
            behind)
    return text


def _as_voxel(point: Sequence[int]) -> Voxel:
    k, j, i = point
    return (int(k), int(j), int(i))
