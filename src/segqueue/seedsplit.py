"""Dividing a pre-existing mask into the project's segments.

Most cases arrive with the coronary tree already drawn, as one unlabelled blob
(``protocol.ASSET_SEED``). The annotator's real job on those cases is not to
trace the vessels -- something already did -- it is to say which part of that
blob is the LAD, which is the LCx, and which is the RCA. Done by hand that is an
hour of painting inside a mask which is already the right shape.

So the annotator marks each branch with a few points and this module does the
division: **every voxel of the mask goes to the branch whose markers are nearest
measured through the mask**, never through the air between two vessels that pass
close without joining.

That "through the mask" is the whole design, and it is why this is a
breadth-first search rather than a comparison of straight-line distances:

* The LAD and the LCx are *joined* at the left main, so no straight-line rule
  separates them -- but walking along the lumen, a voxel in the mid-LAD is a long
  way from an LCx marker even where the two vessels sit millimetres apart.
* The RCA is usually a *separate* component, unreachable from any left-sided
  marker at any distance. Geodesic distance is infinite between components, so
  one marker anywhere on the RCA claims all of it and nothing else, and a marker
  on the left claims none of it.
* A component with no marker on it at all -- an aortic root fragment, a vein the
  model caught -- comes back as ``unreachable`` rather than being glued to
  whichever branch is nearest in space. Leftovers an annotator can see and deal
  with beat silent mislabelling every time.

Stdlib only, and voxels in and voxels out: no numpy, no VTK, no Slicer. The
caller pulls the mask off a labelmap and hands over a set of ``(k, j, i)``
tuples, which is what makes the interesting behaviour testable on a laptop with
neither Slicer nor a CT.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

#: A voxel index, in the array order Slicer hands labelmaps out in: (k, j, i).
Voxel = Tuple[int, int, int]

#: Default step rule. See ``_neighbourhood``.
DEFAULT_CONNECTIVITY = 6

#: How far ``snap_to_mask`` will drag a marker that missed, in voxels.
SNAP_RADIUS = 3


def _neighbourhood(connectivity: int = DEFAULT_CONNECTIVITY) -> Tuple[Voxel, ...]:
    """The offsets that count as adjacent.

    6 is the default everywhere here and should stay that way for vessels. Under
    26-connectivity two branches that merely pass corner-to-corner -- which
    happens wherever the LAD crosses a diagonal, and at every staircase edge in a
    mask resampled from a coarser grid -- become one connected run, and the walk
    leaks out of one vessel into the other. 6 is the conservative reading of
    "joined": faces have to actually touch.
    """
    if connectivity == 6:
        return ((-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1))
    if connectivity == 18:
        return tuple(
            (dk, dj, di)
            for dk in (-1, 0, 1) for dj in (-1, 0, 1) for di in (-1, 0, 1)
            if (dk, dj, di) != (0, 0, 0) and abs(dk) + abs(dj) + abs(di) <= 2
        )
    if connectivity == 26:
        return tuple(
            (dk, dj, di)
            for dk in (-1, 0, 1) for dj in (-1, 0, 1) for di in (-1, 0, 1)
            if (dk, dj, di) != (0, 0, 0)
        )
    raise ValueError(
        "connectivity must be 6, 18 or 26, not {!r}".format(connectivity))


@dataclass
class Split:
    """What one division came to.

    ``assigned`` carries a set per label *in the order the labels were offered*,
    including labels that won nothing -- the caller is a panel drawing one row per
    vessel, and a missing key there would read as "no opinion" rather than as
    "you marked this branch and it claimed nothing", which is a real and
    reportable mistake: a marker dropped beside the vessel instead of on it.
    """

    assigned: Dict[str, Set[Voxel]] = field(default_factory=dict)
    #: Mask voxels no marker could walk to. Whole components with nothing marked
    #: on them, nearly always.
    unreachable: Set[Voxel] = field(default_factory=set)
    #: Markers that landed outside the mask, per label. The caller snaps first
    #: (see ``snap_to_mask``), so anything here was too far out to be a near
    #: miss, and saying so is more use than ignoring it.
    stray: Dict[str, List[Voxel]] = field(default_factory=dict)

    @property
    def labels(self) -> List[str]:
        return list(self.assigned)

    def counts(self) -> Dict[str, int]:
        return {label: len(voxels) for label, voxels in self.assigned.items()}

    def empty_labels(self) -> List[str]:
        """Labels that were marked and still claimed nothing. Worth a complaint."""
        return [label for label, voxels in self.assigned.items() if not voxels]

    def total_assigned(self) -> int:
        return sum(len(voxels) for voxels in self.assigned.values())


def geodesic_partition(
    voxels: Iterable[Voxel],
    sources: Dict[str, Sequence[Voxel]],
    connectivity: int = DEFAULT_CONNECTIVITY,
) -> Split:
    """Give every voxel of ``voxels`` to its nearest label, walking the mask.

    ``sources`` maps a label to the marker voxels dropped on that branch. One
    marker is enough for a branch that is its own component; a joined tree wants
    a few down each arm, because the boundary this produces between two labels
    falls halfway *along the lumen* between their nearest markers, and "halfway
    along the left main" is not where the LAD starts.

    Distance is counted in steps, not millimetres. On a grid isotropic enough to
    resolve a 3 mm vessel those agree closely enough for a boundary the annotator
    is going to eyeball anyway, and counting steps keeps this free of spacing,
    direction cosines and every other way a grid can be described wrongly.

    Ties go to whichever label was offered first. Deterministic on purpose: the
    same markers must divide the same mask the same way twice, or an annotator
    who adds one point and re-runs cannot tell what their edit did.
    """
    mask = _mask_set(voxels)
    offsets = _neighbourhood(connectivity)

    result = Split(assigned={label: set() for label in sources},
                   stray={label: [] for label in sources})

    # Seed the frontier with every marker at once, all at distance zero, so a
    # single breadth-first sweep resolves every label together: the first label
    # to reach a voxel is by construction one at minimum distance from it.
    # Running one search per label and comparing distances afterwards costs a
    # full pass per vessel and arrives at the same answer.
    frontier: deque = deque()
    owner: Dict[Voxel, str] = {}
    for label, points in sources.items():
        for point in points:
            voxel = _as_voxel(point)
            if voxel not in mask:
                result.stray[label].append(voxel)
                continue
            if voxel in owner:
                # Two labels marked on one voxel. First wins; this is not a stray
                # -- it is on the mask -- it is merely already spoken for, and the
                # label's other markers still count.
                continue
            owner[voxel] = label
            result.assigned[label].add(voxel)
            frontier.append(voxel)

    while frontier:
        k, j, i = frontier.popleft()
        label = owner[(k, j, i)]
        for dk, dj, di in offsets:
            neighbour = (k + dk, j + dj, i + di)
            if neighbour in owner or neighbour not in mask:
                continue
            owner[neighbour] = label
            result.assigned[label].add(neighbour)
            frontier.append(neighbour)

    result.unreachable = mask - set(owner)
    return result


def snap_to_mask(
    point: Voxel,
    voxels: Iterable[Voxel],
    radius: int = SNAP_RADIUS,
) -> Optional[Voxel]:
    """The mask voxel nearest ``point``, or None if there is none within ``radius``.

    A marker is placed by clicking a vessel a couple of millimetres across with a
    mouse. Landing one voxel outside the lumen is the normal case, not the
    careless one -- and a marker that silently claims nothing produces a branch
    that comes out empty with no explanation.

    So snap, but only a little. Beyond a few voxels the click was meant for
    something else, and quietly dragging it onto the nearest vessel would hand a
    whole branch to a label the annotator never pointed at -- which is worse than
    the empty branch, because it looks like work.
    """
    mask = _mask_set(voxels)
    point = _as_voxel(point)
    if point in mask:
        return point
    if radius < 1:
        return None

    k0, j0, i0 = point
    best: Optional[Voxel] = None
    best_distance: Optional[int] = None
    for dk in range(-radius, radius + 1):
        for dj in range(-radius, radius + 1):
            for di in range(-radius, radius + 1):
                candidate = (k0 + dk, j0 + dj, i0 + di)
                if candidate not in mask:
                    continue
                distance = dk * dk + dj * dj + di * di
                # Ties break towards the lower index, so a marker equidistant
                # from two voxels snaps to the same one every run.
                if (best_distance is None or distance < best_distance
                        or (distance == best_distance and best is not None
                            and candidate < best)):
                    best, best_distance = candidate, distance
    return best


def components(
    voxels: Iterable[Voxel],
    connectivity: int = DEFAULT_CONNECTIVITY,
) -> List[Set[Voxel]]:
    """The mask's connected pieces, largest first.

    Used to say something useful about what was left over: "412 voxels in 3
    pieces" tells an annotator whether they missed a branch or whether the model
    left specks, and those want opposite responses.
    """
    mask = _mask_set(voxels)
    offsets = _neighbourhood(connectivity)
    seen: Set[Voxel] = set()
    found: List[Set[Voxel]] = []

    for start in sorted(mask):
        if start in seen:
            continue
        piece: Set[Voxel] = {start}
        seen.add(start)
        frontier = deque([start])
        while frontier:
            k, j, i = frontier.popleft()
            for dk, dj, di in offsets:
                neighbour = (k + dk, j + dj, i + di)
                if neighbour in seen or neighbour not in mask:
                    continue
                seen.add(neighbour)
                piece.add(neighbour)
                frontier.append(neighbour)
        found.append(piece)

    found.sort(key=len, reverse=True)
    return found


def describe_leftovers(
    unreachable: Iterable[Voxel],
    connectivity: int = DEFAULT_CONNECTIVITY,
) -> str:
    """One sentence on what the division did not place; ``''`` if it placed everything."""
    leftover = _mask_set(unreachable)
    if not leftover:
        return ""
    pieces = components(leftover, connectivity)
    if len(pieces) == 1:
        return ("{} voxels, in one piece, are not connected to any marker."
                .format(len(leftover)))
    return ("{} voxels, in {} pieces, are not connected to any marker."
            .format(len(leftover), len(pieces)))


def _as_voxel(point: Sequence[int]) -> Voxel:
    k, j, i = point
    return (int(k), int(j), int(i))


def _as_voxels(points: Iterable[Sequence[int]]) -> Set[Voxel]:
    """Normalise to a set of int tuples.

    Callers hand this numpy rows as often as tuples, and a ``numpy.int64`` in a
    key hashes equal to its ``int`` but prints unrecognisably in an error
    message. Converting once at the door is cheaper than everywhere after it.
    """
    return {_as_voxel(point) for point in points}


def _mask_set(voxels: Iterable[Sequence[int]]) -> Set[Voxel]:
    """``_as_voxels``, but free when the caller already built the set.

    Worth the branch. The real mask is a coronary tree pulled off a labelmap --
    tens of thousands of voxels -- and the caller snaps a dozen markers against
    it before dividing. Rebuilding the set per call turned a dozen cheap lookups
    into a dozen full passes over the tree, which is the difference between a
    button that responds and one an annotator presses twice.

    A ``set`` can only hold hashables, so it is already tuples; the int
    conversion in ``_as_voxels`` matters for printing a stray marker back at
    someone, not for the mask, which is never printed.
    """
    if isinstance(voxels, (set, frozenset)):
        return voxels  # type: ignore[return-value]
    return _as_voxels(voxels)
