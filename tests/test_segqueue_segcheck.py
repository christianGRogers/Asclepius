"""Pre-flight submission checks -- the rejections that never need a reviewer."""

from segqueue.protocol import SegmentSpec
from segqueue.segcheck import (
    ERROR,
    WARNING,
    Geometry,
    blocking,
    check_submission,
    summarise,
)

CORONARY = [
    SegmentSpec("left_main", 1, (1.0, 0.0, 0.0)),
    SegmentSpec("left_anterior_descending", 2, (0.0, 1.0, 0.0)),
    SegmentSpec("left_circumflex", 3, (0.0, 0.0, 1.0)),
    SegmentSpec("right_coronary_artery", 4, (1.0, 1.0, 0.0), required=False,
                hint="May be absent in a left-dominant system."),
]

GOOD_COUNTS = {
    "left_main": 800,
    "left_anterior_descending": 4200,
    "left_circumflex": 3100,
    "right_coronary_artery": 3600,
}

GRID = Geometry(size=(512, 512, 300), spacing=(0.35, 0.35, 0.4), origin=(-200.0, -200.0, 0.0))


def codes(problems):
    return {p.code for p in problems}


def test_a_complete_segmentation_passes_clean():
    problems = check_submission(GOOD_COUNTS, CORONARY, GRID, GRID, annotation_seconds=1800)
    assert problems == []
    assert summarise(problems) == "No problems found."


def test_an_empty_required_segment_blocks_submission():
    counts = dict(GOOD_COUNTS, left_main=0)
    problems = check_submission(counts, CORONARY, GRID, GRID, annotation_seconds=1800)
    assert codes(problems) == {"empty_required_segment"}
    assert blocking(problems)


def test_an_empty_optional_segment_only_warns():
    """A right coronary artery can be genuinely absent in a left-dominant system."""
    counts = dict(GOOD_COUNTS, right_coronary_artery=0)
    problems = check_submission(counts, CORONARY, GRID, GRID, annotation_seconds=1800)
    assert codes(problems) == {"empty_optional_segment"}
    assert problems[0].level == WARNING
    assert not blocking(problems)


def test_a_missing_key_counts_the_same_as_zero():
    counts = {k: v for k, v in GOOD_COUNTS.items() if k != "left_main"}
    problems = check_submission(counts, CORONARY, GRID, GRID, annotation_seconds=1800)
    assert codes(problems) == {"empty_required_segment"}


def test_a_stray_paint_click_is_caught_rather_than_counted_as_work():
    counts = dict(GOOD_COUNTS, left_main=3)
    problems = check_submission(counts, CORONARY, GRID, GRID, annotation_seconds=1800)
    assert codes(problems) == {"stray_voxels"}
    assert blocking(problems)


def test_an_extra_segment_blocks_because_it_breaks_the_training_conversion():
    counts = dict(GOOD_COUNTS, Segment_1=500)
    problems = check_submission(counts, CORONARY, GRID, GRID, annotation_seconds=1800)
    assert codes(problems) == {"unexpected_segment"}
    assert blocking(problems)


def test_an_empty_extra_segment_is_ignored():
    """Slicer leaves empty scratch segments around; they harm nothing."""
    counts = dict(GOOD_COUNTS, Segment_1=0)
    assert check_submission(counts, CORONARY, GRID, GRID, annotation_seconds=1800) == []


def test_a_resampled_segmentation_is_refused():
    resampled = Geometry(size=(256, 256, 150), spacing=(0.7, 0.7, 0.8),
                         origin=(-200.0, -200.0, 0.0))
    problems = check_submission(GOOD_COUNTS, CORONARY, GRID, resampled,
                                annotation_seconds=1800)
    assert "geometry_size" in codes(problems)
    assert "geometry_spacing" in codes(problems)


def test_a_shifted_origin_is_refused():
    shifted = Geometry(size=GRID.size, spacing=GRID.spacing, origin=(-199.0, -200.0, 0.0))
    problems = check_submission(GOOD_COUNTS, CORONARY, GRID, shifted, annotation_seconds=1800)
    assert codes(problems) == {"geometry_origin"}


def test_decimal_round_tripping_is_not_mistaken_for_a_resample():
    """NRRD writes these as text; the last digit moves and means nothing."""
    jittered = Geometry(size=GRID.size, spacing=(0.3500001, 0.35, 0.4000002),
                        origin=(-200.0000004, -200.0, 0.0))
    assert check_submission(GOOD_COUNTS, CORONARY, GRID, jittered,
                            annotation_seconds=1800) == []


def test_missing_geometry_is_not_an_error():
    """An older client sends no geometry; that must not block its work."""
    assert check_submission(GOOD_COUNTS, CORONARY, None, None, annotation_seconds=1800) == []


def test_an_implausibly_fast_case_warns_but_does_not_block():
    problems = check_submission(GOOD_COUNTS, CORONARY, GRID, GRID, annotation_seconds=12)
    assert codes(problems) == {"implausibly_fast"}
    assert not blocking(problems)


def test_errors_sort_ahead_of_warnings():
    counts = dict(GOOD_COUNTS, left_main=0, right_coronary_artery=0)
    problems = check_submission(counts, CORONARY, GRID, GRID, annotation_seconds=5)
    levels = [p.level for p in problems]
    assert levels == sorted(levels, key=lambda lvl: 0 if lvl == ERROR else 1)
    assert levels[0] == ERROR


def test_summarise_lists_every_problem():
    counts = dict(GOOD_COUNTS, left_main=0, Segment_1=99)
    text = summarise(check_submission(counts, CORONARY, GRID, GRID, annotation_seconds=1800))
    assert "left_main" in text
    assert "Segment_1" in text
    assert text.count("\n") == 1
