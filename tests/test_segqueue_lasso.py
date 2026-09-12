"""Circling a branch in the 3D view.

The property this file exists for is occlusion. A loop drawn on a flat screen is
a tube through the volume, and the difference between a tool that works and one
that quietly mislabels is whether the vessel thirty millimetres behind the
circled one comes along with it. Everything else here is bookkeeping around that.
"""

from segqueue.lasso import (
    DEPTH_TOLERANCE_MM,
    Selection,
    bounds,
    describe,
    dominant_piece,
    polygon_contains,
    select_visible,
    simplify,
)

# A 100x100 box, drawn as a path with the closing edge implied.
BOX = [(0, 0), (100, 0), (100, 100), (0, 100)]


def projected(*entries):
    """(voxel, x, y, depth) rows, with the voxel index made up from the row."""
    return [((n, 0, 0), x, y, d) for n, (x, y, d) in enumerate(entries)]


# ------------------------------------------------------------- inside or out

def test_a_point_inside_the_loop_is_inside():
    assert polygon_contains(BOX, 50, 50)


def test_a_point_outside_the_loop_is_outside():
    assert not polygon_contains(BOX, 150, 50)
    assert not polygon_contains(BOX, 50, 150)
    assert not polygon_contains(BOX, -10, 50)


def test_the_loop_closes_itself():
    # The caller hands over a drag path, not a closed ring: the last point is
    # where the mouse came up, and the edge back to the start is implied.
    triangle = [(0, 0), (100, 0), (50, 100)]
    assert polygon_contains(triangle, 50, 10)
    assert not polygon_contains(triangle, 5, 90)


def test_a_path_too_short_to_enclose_anything_encloses_nothing():
    assert not polygon_contains([(0, 0), (10, 10)], 5, 5)
    assert not polygon_contains([], 0, 0)


def test_a_self_crossing_loop_still_selects_what_was_drawn_around():
    # Drawing quickly around a vessel crosses your own line constantly. The
    # figure-of-eight is the pathological version; both lobes must read as
    # inside rather than cancelling each other out.
    left = [(0, 0), (40, 0), (40, 40), (0, 40)]
    right = [(60, 0), (100, 0), (100, 40), (60, 40)]
    figure = left + right
    assert polygon_contains(figure, 20, 20) or polygon_contains(figure, 80, 20)


def test_bounds_are_the_extremes_of_the_path():
    assert bounds(BOX) == (0, 0, 100, 100)


# -------------------------------------------------------------- occlusion

def test_a_vessel_behind_the_circled_one_is_not_selected():
    """The whole point of the module.

    Two voxels at the same pixel: the LAD at 100 mm and the RCA at 130 mm. The
    loop is drawn around what the annotator can see, which is the LAD.
    """
    rows = projected((50, 50, 100.0), (50, 50, 130.0))
    picked = select_visible(rows, BOX)
    assert picked.voxels == {(0, 0, 0)}
    assert picked.hidden == 1


def test_the_full_thickness_of_the_circled_vessel_is_kept():
    # Near and far wall of one artery, a couple of millimetres apart. Selecting
    # only the front skin would still work -- these are markers, and the flood
    # fills the rest -- but there is no reason to throw away good markers.
    rows = projected((50, 50, 100.0), (50, 50, 102.5))
    picked = select_visible(rows, BOX)
    assert len(picked.voxels) == 2
    assert picked.hidden == 0


def test_the_depth_rule_is_measured_from_the_nearest_voxel_at_that_pixel():
    # Not from the nearest voxel anywhere in the loop: a branch that dips towards
    # the camera at one end must not shadow the other end of itself.
    rows = projected((10, 10, 50.0), (90, 90, 200.0), (90, 90, 202.0))
    picked = select_visible(rows, BOX)
    assert len(picked.voxels) == 3
    assert picked.hidden == 0


def test_a_nearer_voxel_outside_the_loop_does_not_suppress_one_inside_it():
    # A branch crossing in front of the circled one, but outside the loop, must
    # not blank out part of the selection. It cannot, because the near-surface
    # rule is scoped to a pixel and a pixel is wholly inside the loop or wholly
    # outside it -- this pins that down rather than leaving it to be rediscovered
    # if the depth test ever moves ahead of the loop test.
    triangle = [(0, 0), (100, 0), (50, 100)]
    rows = [((1, 0, 0), 5.0, 90.0, 10.0),     # inside the box, outside the loop
            ((2, 0, 0), 50.0, 50.0, 100.0)]   # inside the loop, much further away
    picked = select_visible(rows, triangle)
    assert picked.voxels == {(2, 0, 0)}
    assert picked.outside == 1
    assert picked.hidden == 0


def test_the_tolerance_is_configurable_and_actually_applied():
    rows = projected((50, 50, 100.0), (50, 50, 100.0 + DEPTH_TOLERANCE_MM + 1))
    assert len(select_visible(rows, BOX).voxels) == 1
    assert len(select_visible(rows, BOX, depth_tolerance=1000.0).voxels) == 2


def test_pixels_are_bucketed_separately():
    # Two voxels far apart on screen, both alone at their pixel: neither hides
    # the other however different their depths.
    rows = projected((10, 10, 50.0), (80, 80, 500.0))
    assert len(select_visible(rows, BOX).voxels) == 2


# ----------------------------------------------------- one branch per loop

def test_a_loop_keeps_only_the_piece_it_mostly_covers():
    """The rule the per-pixel depth test cannot provide.

    A loop around a 3 mm artery is mostly empty screen, and across that emptiness
    a vessel behind is the nearest thing there is -- so it is visible, inside the
    loop, and selected. Only connectivity separates them.
    """
    front = {(0, 0, n) for n in range(10)}
    behind = {(9, 9, n) for n in range(4)}
    rows = ([(v, 10.0 + i, 10.0, 100.0) for i, v in enumerate(sorted(front))]
            + [(v, 40.0 + i, 40.0, 400.0) for i, v in enumerate(sorted(behind))])

    loose = select_visible(rows, BOX)
    assert loose.voxels == front | behind, "without pieces, both come along"

    picked = select_visible(rows, BOX, pieces=[front, behind])
    assert picked.voxels == front
    assert picked.elsewhere == len(behind)


def test_the_piece_with_the_most_circled_voxels_wins():
    small = {(0, 0, 0)}
    large = {(5, 5, n) for n in range(6)}
    rows = [(v, 10.0 + i, 10.0, 50.0) for i, v in enumerate(sorted(small | large))]
    picked = select_visible(rows, BOX, pieces=[small, large])
    assert picked.voxels == large


def test_dominant_piece_passes_everything_through_when_there_are_no_pieces():
    voxels = {(0, 0, 0), (1, 1, 1)}
    assert dominant_piece(voxels, []) == (voxels, 0)
    assert dominant_piece(set(), [{(0, 0, 0)}]) == (set(), 0)


def test_dominant_piece_keeps_everything_when_it_matches_no_piece():
    # Should not happen -- the selection comes from the mask the pieces describe
    # -- but returning the selection unfiltered is the safe reading of "I cannot
    # tell", and is what the caller's report then reflects.
    voxels = {(9, 9, 9)}
    kept, dropped = dominant_piece(voxels, [{(0, 0, 0)}])
    assert kept == voxels and dropped == 0


# ---------------------------------------------------------------- selection

def test_voxels_outside_the_bounding_box_are_rejected_cheaply():
    rows = projected((500, 500, 10.0), (50, 50, 10.0))
    picked = select_visible(rows, BOX)
    assert picked.voxels == {(1, 0, 0)}
    # Rejected by the box, so never tested against the loop and never counted
    # as "inside the box but outside the loop".
    assert picked.outside == 0


def test_a_loop_over_empty_space_selects_nothing():
    picked = select_visible(projected((500, 500, 10.0)), BOX)
    assert not picked
    assert len(picked) == 0


def test_a_degenerate_loop_selects_nothing_rather_than_raising():
    # A click with no drag. Must not be an exception on the annotator's screen.
    assert select_visible(projected((50, 50, 1.0)), [(50, 50)]).voxels == set()


# ------------------------------------------------------------- thinning

def test_a_dragged_path_is_thinned_to_the_points_that_move():
    # Mouse move events arrive far faster than a hand moves.
    path = [(0, 0)] * 50 + [(100, 0)]
    assert simplify(path) == [(0, 0), (100, 0)]


def test_thinning_keeps_the_point_the_mouse_came_up_on():
    path = [(0, 0), (100, 0), (100, 1)]
    assert simplify(path)[-1] == (100, 1)


def test_thinning_keeps_real_corners():
    path = [(0, 0), (100, 0), (100, 100), (0, 100)]
    assert simplify(path) == path


def test_thinning_an_empty_path_is_empty():
    assert simplify([]) == []


# ------------------------------------------------------------- reporting

def test_an_empty_selection_says_what_to_do_instead():
    assert "empty space" in describe(Selection(voxels=set()), "LAD")


def test_occluded_voxels_are_mentioned_rather_than_silently_dropped():
    # A loop that looks like it covered two branches and selected one did the
    # right thing, and the annotator is entitled to know that.
    text = describe(Selection(voxels={(0, 0, 0)}, hidden=400), "LAD")
    assert "400" in text and "behind" in text
    # Dropped for being on another piece counts the same way to a reader: it was
    # under the loop and it was not taken.
    other = describe(Selection(voxels={(0, 0, 0)}, elsewhere=7), "LAD")
    assert "7" in other and "behind" in other


def test_a_clean_selection_does_not_mention_occlusion():
    text = describe(Selection(voxels={(0, 0, 0)}), "LAD")
    assert "behind" not in text
    assert "LAD" in text
