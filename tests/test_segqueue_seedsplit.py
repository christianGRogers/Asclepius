"""Dividing the coronary seed into branches.

The behaviour worth pinning down here is the one an annotator cannot check by
eye on a 400-slice case: that the division walks *along* the mask rather than
across the gap between two vessels, that a component nobody marked is handed
back rather than absorbed, and that the same markers divide the same mask the
same way twice.

The masks below are drawn as small grids for a reason. A tree that fits in a
docstring can be reasoned about exactly, and every failure this module can have
-- leaking across a touching branch, claiming an unmarked component, breaking a
tie differently on a second run -- shows up at that size.
"""

import pytest

from segqueue.seedsplit import (
    Split,
    components,
    describe_leftovers,
    geodesic_partition,
    snap_to_mask,
)


# --------------------------------------------------------------- small shapes

def line(k, j, i0, i1):
    """A run of voxels along i, inclusive."""
    return {(k, j, i) for i in range(i0, i1 + 1)}


@pytest.fixture
def tee():
    """A left main splitting into two arms, in one plane.

    ::

        i ->   0 1 2 3 4 5 6 7 8
        j=0            L L L L L      <- "lad", up-branch
        j=1    M M M M X
        j=2            C C C C C      <- "lcx", down-branch

    The stem M is shared; X is the bifurcation voxel joining all three.
    """
    stem = line(0, 1, 0, 4)
    lad = line(0, 0, 4, 8)
    lcx = line(0, 2, 4, 8)
    return stem | lad | lcx


# ------------------------------------------------------------ walking the mask

def test_a_joined_tree_divides_at_the_midpoint_along_the_lumen(tee):
    # The point of the whole module: LAD and LCx are connected through the stem,
    # so nothing about straight-line distance separates them.
    split = geodesic_partition(tee, {"lad": [(0, 0, 8)], "lcx": [(0, 2, 8)]})

    assert (0, 0, 5) in split.assigned["lad"]
    assert (0, 2, 5) in split.assigned["lcx"]
    # Every voxel is placed, and no voxel is placed twice.
    assert split.total_assigned() == len(tee)
    assert not split.unreachable
    assert not (split.assigned["lad"] & split.assigned["lcx"])


def test_distance_is_measured_through_the_mask_not_across_the_gap():
    """Two vessels passing close without touching.

    ::

        i ->   0 1 2 3 4 5
        j=0    A A A A A A
        j=1                  (gap)
        j=2    B B B B B B

    (0,0,5) is one step from (0,2,5) in space if you are allowed to cut the
    corner, and unreachable if you are not. A straight-line rule would hand half
    of A to B's marker at the far end; walking the mask cannot.
    """
    mask = line(0, 0, 0, 5) | line(0, 2, 0, 5)
    split = geodesic_partition(mask, {"a": [(0, 0, 0)], "b": [(0, 2, 0)]})

    assert split.assigned["a"] == line(0, 0, 0, 5)
    assert split.assigned["b"] == line(0, 2, 0, 5)


def test_six_connectivity_does_not_leak_across_a_diagonal_touch():
    """Two runs meeting corner to corner only.

    The staircase edge a resampled mask is full of. Under 26-connectivity these
    are one component and one marker takes both, which is exactly the
    mislabelling the default guards against.
    """
    mask = {(0, 0, 0), (0, 0, 1), (0, 1, 2), (0, 1, 3)}
    split = geodesic_partition(mask, {"a": [(0, 0, 0)]})
    assert split.assigned["a"] == {(0, 0, 0), (0, 0, 1)}
    assert split.unreachable == {(0, 1, 2), (0, 1, 3)}

    leaked = geodesic_partition(mask, {"a": [(0, 0, 0)]}, connectivity=26)
    assert leaked.assigned["a"] == mask


# ------------------------------------------------------- separate components

def test_one_marker_claims_its_whole_component_and_nothing_else():
    # The RCA case: a separate component, so a single marker anywhere on it is
    # enough, and a marker on the left tree cannot reach it at any distance.
    left = line(0, 0, 0, 5)
    right = line(0, 4, 0, 5)
    split = geodesic_partition(left | right, {"lad": [(0, 0, 0)], "rca": [(0, 4, 3)]})

    assert split.assigned["lad"] == left
    assert split.assigned["rca"] == right


def test_an_unmarked_component_is_handed_back_not_absorbed():
    # A vein the model caught, or an aortic root fragment. Gluing it to the
    # nearest branch would be silent mislabelling; leaving it in the leftovers
    # puts it in front of the annotator.
    tree = line(0, 0, 0, 5)
    speck = {(0, 9, 9), (0, 9, 10)}
    split = geodesic_partition(tree | speck, {"lad": [(0, 0, 0)]})

    assert split.assigned["lad"] == tree
    assert split.unreachable == speck


def test_a_label_that_claims_nothing_is_reported_rather_than_dropped():
    # A marker dropped beside the vessel, snapped too far to recover. The panel
    # draws a row per vessel, so the key has to exist -- and the annotator has to
    # be told, because the branch will simply look unsegmented.
    split = geodesic_partition(line(0, 0, 0, 5),
                               {"lad": [(0, 0, 0)], "lcx": [(5, 5, 5)]})

    assert split.assigned["lcx"] == set()
    assert split.empty_labels() == ["lcx"]
    assert split.stray["lcx"] == [(5, 5, 5)]


def test_no_markers_at_all_leaves_the_mask_untouched():
    mask = line(0, 0, 0, 5)
    split = geodesic_partition(mask, {})
    assert split.unreachable == mask
    assert split.assigned == {}


# ------------------------------------------------------------- determinism

def test_the_same_markers_divide_the_same_mask_the_same_way_twice(tee):
    # An annotator who adds one point and re-runs has to be able to attribute the
    # difference to their edit. Iteration order wobbling between runs makes that
    # impossible to reason about, and the boundary visibly moves.
    sources = {"lad": [(0, 0, 8)], "lcx": [(0, 2, 8)]}
    first = geodesic_partition(tee, sources)
    second = geodesic_partition(tee, sources)
    assert first.assigned == second.assigned


def test_a_tie_goes_to_the_label_offered_first():
    # Both markers are two steps from the middle voxel of a five-long run.
    mask = line(0, 0, 0, 4)
    split = geodesic_partition(mask, {"a": [(0, 0, 0)], "b": [(0, 0, 4)]})
    assert (0, 0, 2) in split.assigned["a"]

    flipped = geodesic_partition(mask, {"b": [(0, 0, 4)], "a": [(0, 0, 0)]})
    assert (0, 0, 2) in flipped.assigned["b"]


def test_two_labels_marked_on_one_voxel_do_not_both_claim_it():
    mask = line(0, 0, 0, 4)
    split = geodesic_partition(mask, {"a": [(0, 0, 2)], "b": [(0, 0, 2)]})
    assert (0, 0, 2) in split.assigned["a"]
    assert (0, 0, 2) not in split.assigned["b"]
    # The duplicate is on the mask, so it is not a stray -- just already taken.
    assert split.stray["b"] == []


def test_extra_markers_down_an_arm_move_the_boundary():
    """Why one marker per branch is not the advice.

    With a marker at each far end the boundary lands mid-stem. Marking further
    down one arm pulls it that way, which is how an annotator says "the left main
    belongs to the LAD" without painting a voxel.
    """
    mask = line(0, 0, 0, 10)
    far = geodesic_partition(mask, {"a": [(0, 0, 0)], "b": [(0, 0, 10)]})
    near = geodesic_partition(mask, {"a": [(0, 0, 0)], "b": [(0, 0, 10), (0, 0, 2)]})
    assert len(near.assigned["b"]) > len(far.assigned["a"])
    assert (0, 0, 4) in far.assigned["a"]
    assert (0, 0, 4) in near.assigned["b"]


# ------------------------------------------------------------------ snapping

def test_a_marker_one_voxel_off_the_vessel_snaps_onto_it():
    mask = line(0, 0, 0, 5)
    assert snap_to_mask((0, 1, 3), mask) == (0, 0, 3)


def test_a_marker_already_on_the_mask_does_not_move():
    mask = line(0, 0, 0, 5)
    assert snap_to_mask((0, 0, 3), mask) == (0, 0, 3)


def test_a_marker_nowhere_near_the_mask_is_not_dragged_onto_it():
    # The guard that matters: silently snapping a far click would hand a whole
    # branch to a label the annotator never pointed at, which looks like work
    # rather than like a mistake.
    mask = line(0, 0, 0, 5)
    assert snap_to_mask((0, 40, 40), mask) is None


def test_snapping_is_deterministic_between_equidistant_voxels():
    mask = {(0, 1, 0), (0, -1, 0)}
    assert snap_to_mask((0, 0, 0), mask) == snap_to_mask((0, 0, 0), mask)
    assert snap_to_mask((0, 0, 0), mask) == (0, -1, 0)


# ------------------------------------------------------------------ leftovers

def test_components_come_back_largest_first():
    big = line(0, 0, 0, 5)
    small = {(0, 4, 4)}
    found = components(big | small)
    assert [len(piece) for piece in found] == [6, 1]


def test_leftovers_are_described_in_pieces_not_just_voxels():
    # "412 voxels in 3 pieces" and "412 voxels in one piece" want opposite
    # responses -- specks to ignore, or a branch nobody marked.
    assert describe_leftovers([]) == ""
    assert "one piece" in describe_leftovers(line(0, 0, 0, 3))
    assert "2 pieces" in describe_leftovers(line(0, 0, 0, 3) | {(0, 5, 5)})


def test_numpy_style_rows_are_accepted_as_voxels():
    # The caller pulls these off a labelmap, so they arrive as whatever the array
    # library hands out rather than as tuples.
    mask = [[0, 0, 0], [0, 0, 1], [0, 0, 2]]
    split = geodesic_partition(mask, {"a": [[0, 0, 0]]})
    assert split.assigned["a"] == {(0, 0, 0), (0, 0, 1), (0, 0, 2)}


def test_an_unknown_connectivity_is_refused_rather_than_guessed():
    with pytest.raises(ValueError):
        geodesic_partition(line(0, 0, 0, 3), {"a": [(0, 0, 0)]}, connectivity=7)


# -------------------------------------------------------------------- shape

def test_counts_are_reported_per_label_in_the_order_offered(tee):
    split = geodesic_partition(tee, {"lad": [(0, 0, 8)], "lcx": [(0, 2, 8)]})
    assert list(split.counts()) == ["lad", "lcx"]
    assert sum(split.counts().values()) == len(tee)


def test_an_empty_split_reports_nothing_rather_than_raising():
    assert Split().counts() == {}
    assert Split().empty_labels() == []
    assert Split().total_assigned() == 0
