"""Dice and NSD, including the absent-structure convention."""

import math

import numpy as np

from segtrain.metrics import (
    aggregate,
    dice_dict,
    dice_score,
    nanmean,
    normalized_surface_distance,
    score_case,
    summarize_case,
)

SPACING = (1.5, 1.5, 1.5)


def _cube(shape=(16, 16, 16), lo=4, hi=12):
    m = np.zeros(shape, dtype=bool)
    m[lo:hi, lo:hi, lo:hi] = True
    return m


def test_perfect_overlap_is_one():
    m = _cube()
    assert dice_score(m, m) == 1.0


def test_disjoint_is_zero():
    a, b = np.zeros((8, 8, 8), bool), np.zeros((8, 8, 8), bool)
    a[0:2] = True
    b[6:8] = True
    assert dice_score(a, b) == 0.0


def test_absent_from_both_is_nan_not_one():
    """Scoring an absent structure as 1.0 would inflate whole-body averages."""
    empty = np.zeros((4, 4, 4), bool)
    assert math.isnan(dice_score(empty, empty))


def test_predicted_but_not_present_is_zero():
    pred = np.ones((4, 4, 4), bool)
    assert dice_score(pred, np.zeros((4, 4, 4), bool)) == 0.0


def test_dice_matches_hand_computation():
    a, b = np.zeros((10,), bool), np.zeros((10,), bool)
    a[0:6] = True
    b[4:10] = True
    assert dice_score(a, b) == 2 * 2 / (6 + 6)


def test_nsd_is_one_for_identical_shapes():
    m = _cube()
    assert normalized_surface_distance(m, m, SPACING) == 1.0


def test_nsd_falls_when_the_boundary_moves_beyond_tolerance():
    a = _cube()
    b = _cube(lo=7, hi=15)
    assert normalized_surface_distance(a, b, SPACING, tolerance_mm=1.5) < 0.5


def test_nsd_tolerates_a_one_voxel_shift_at_matching_tolerance():
    a = _cube()
    b = _cube(lo=5, hi=13)
    tight = normalized_surface_distance(a, b, SPACING, tolerance_mm=0.5)
    loose = normalized_surface_distance(a, b, SPACING, tolerance_mm=2.0)
    assert loose > tight


def test_nsd_absent_from_both_is_nan():
    empty = np.zeros((8, 8, 8), bool)
    assert math.isnan(normalized_surface_distance(empty, empty, SPACING))


def test_nsd_one_sided_is_zero():
    assert normalized_surface_distance(_cube(), np.zeros((16, 16, 16), bool), SPACING) == 0.0


def test_score_case_covers_every_class():
    ref = np.zeros((8, 8, 8), np.uint8)
    ref[0:4] = 1
    ref[4:8] = 2
    scores = score_case(ref.copy(), ref, ["a", "b"], SPACING, compute_nsd=False)
    assert [s.name for s in scores] == ["a", "b"]
    assert all(s.dice == 1.0 for s in scores)


def test_score_case_reports_absent_structures_as_nan():
    ref = np.zeros((8, 8, 8), np.uint8)
    ref[0:4] = 1
    scores = score_case(ref.copy(), ref, ["a", "never_present"], SPACING, compute_nsd=False)
    assert scores[1].ref_voxels == 0
    assert math.isnan(scores[1].dice)


def test_dice_dict_omits_nan():
    """JSON has no NaN, and an absent structure is better shown by absence."""
    ref = np.zeros((8, 8, 8), np.uint8)
    ref[0:4] = 1
    scores = score_case(ref.copy(), ref, ["a", "absent"], SPACING, compute_nsd=False)
    d = dice_dict(scores)
    assert "a" in d and "absent" not in d


def test_nanmean_ignores_absent():
    assert nanmean([1.0, float("nan"), 0.0]) == 0.5
    assert math.isnan(nanmean([float("nan")]))


def test_summarize_counts_present_structures():
    ref = np.zeros((8, 8, 8), np.uint8)
    ref[0:4] = 1
    summary = summarize_case(score_case(ref.copy(), ref, ["a", "b"], SPACING,
                                        compute_nsd=False))
    assert summary["n_classes"] == 2 and summary["n_present"] == 1


def test_aggregate_tracks_how_often_a_structure_appeared():
    """A Dice over 3 cases and over 80 cases mean very different things."""
    ref = np.zeros((8, 8, 8), np.uint8)
    ref[0:4] = 1
    both = score_case(ref.copy(), ref, ["a", "b"], SPACING, compute_nsd=False)
    agg = aggregate({"c1": both, "c2": both})
    assert agg["a"]["n_cases_present"] == 2
    assert agg["b"]["n_cases_present"] == 0
    assert agg["a"]["dice"] == 1.0


def test_only_labels_restricts_work():
    ref = np.zeros((8, 8, 8), np.uint8)
    ref[0:4] = 1
    ref[4:8] = 2
    scores = score_case(ref.copy(), ref, ["a", "b"], SPACING, compute_nsd=False,
                        only_labels=[2])
    assert len(scores) == 1 and scores[0].name == "b"
