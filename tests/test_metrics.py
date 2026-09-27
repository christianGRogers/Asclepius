"""Dice and NSD, including the absent-structure convention."""

import json
import math

import numpy as np

from segtrain.metrics import (
    aggregate,
    agreement,
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


# ------------------------------------------------- the two live reporting bugs
#
# Both of these produced a wrong number that looked like a right one, which is
# why they are here with the reasoning attached rather than as bare assertions.


def test_agreement_mean_dice_is_json_safe_when_nothing_was_present():
    """JSON has no NaN, and this dict is stored and read back by the dashboard.

    `json.dumps` emits a bare `NaN` token that a strict parser rejects and
    `JSON.parse` throws on. The per-structure entries were sanitised; `mean_dice`
    was not, so a submission where no listed structure appeared in either volume
    wrote one.
    """
    zeros = np.zeros((4, 4, 4), np.uint8)

    result = agreement(zeros, zeros, ["left_main"], SPACING)

    assert result["mean_dice"] is None
    assert result["n_scored"] == 0
    # Round-trips through a parser that refuses the non-standard constants.
    def _reject(constant):
        raise AssertionError(f"emitted a bare {constant}")

    json.loads(json.dumps(result), parse_constant=_reject)


def test_a_single_empty_submission_cannot_poison_an_annotators_mean():
    """The consequence of the above, stated as the thing that actually went wrong.

    NaN is not None, so an `is not None` guard passes it; and NaN propagates
    through `sum()`. One such record turned a whole `meanAgreementDice` into NaN
    with nothing to say which case caused it.
    """
    zeros = np.zeros((4, 4, 4), np.uint8)
    ref = np.zeros((4, 4, 4), np.uint8)
    ref[0:2] = 1

    empty = agreement(zeros, zeros, ["left_main"], SPACING)["mean_dice"]
    real = agreement(ref.copy(), ref, ["left_main"], SPACING)["mean_dice"]

    usable = [m for m in (empty, real) if isinstance(m, (int, float)) and math.isfinite(m)]
    assert usable == [1.0]
    assert sum(usable) / len(usable) == 1.0


def test_agreement_says_how_many_structures_its_mean_is_over():
    ref = np.zeros((8, 8, 8), np.uint8)
    ref[0:4] = 1  # only structure "a" is present

    result = agreement(ref.copy(), ref, ["a", "b"], SPACING)

    assert result["mean_dice"] == 1.0
    assert result["n_scored"] == 1, "b was in neither volume"
    assert result["n_structures"] == 2


def test_aggregate_dice_and_its_denominator_describe_the_same_cases():
    """A class absent from the reference but predicted scores 0.0, not NaN.

    So it entered the mean while `n_cases_present` counted only the cases that
    had the structure -- the reported Dice was an average over more cases than the
    count printed beside it. On coronaries this is the norm, not an edge case: a
    model that invents L-PDA in the ~95 % of patients without one had that class's
    Dice dragged toward zero against a count claiming a handful of cases.
    """
    ref = np.zeros((8, 8, 8), np.uint8)
    ref[0:4] = 1
    present = score_case(ref.copy(), ref, ["a"], SPACING, compute_nsd=False)

    # Reference has no "a"; the prediction claims one anyway.
    pred = np.zeros((8, 8, 8), np.uint8)
    pred[0:4] = 1
    invented = score_case(pred, np.zeros((8, 8, 8), np.uint8), ["a"], SPACING,
                          compute_nsd=False)

    row = aggregate({"real": present, "hallucinated": invented})["a"]

    assert row["dice"] == 0.5, "mean of 1.0 and 0.0"
    assert row["n_cases_scored"] == 2, "and the denominator says so"
    assert row["n_cases_present"] == 1
    assert row["n_cases_false_positive"] == 1


def test_aggregate_skips_cases_where_there_was_nothing_to_score():
    """Absent from both is not a zero; it is not a data point at all."""
    empty = np.zeros((8, 8, 8), np.uint8)
    nothing = score_case(empty.copy(), empty, ["a"], SPACING, compute_nsd=False)
    ref = np.zeros((8, 8, 8), np.uint8)
    ref[0:4] = 1
    present = score_case(ref.copy(), ref, ["a"], SPACING, compute_nsd=False)

    row = aggregate({"blank": nothing, "real": present})["a"]

    assert row["dice"] == 1.0, "the blank case must not average in as a zero"
    assert row["n_cases_scored"] == 1
    assert row["n_cases"] == 2
    assert row["n_cases_false_positive"] == 0
