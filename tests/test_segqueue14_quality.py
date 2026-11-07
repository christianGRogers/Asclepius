"""The figures of the annotation quality report (#296): ``segqueue14.quality``.

Arrays alone, no database: seed comparison (untrimmed, near copies), overlap, the
flag groups and the plain-text tables. The report against a real database is
``test_segqueue_server14_report.py``.
"""

import pytest

from segqueue14 import quality as report

np = pytest.importorskip("numpy")

NAMES = ["LM", "LAD", "LCx", "RCA"]


def _blocks(shape=(10, 10, 10)):
    """Four disjoint vessel blocks (z, y, x) and their union, the seed."""
    out = {}
    for i, name in enumerate(NAMES):
        m = np.zeros(shape, np.uint8)
        m[1:9, 1 + 2 * i:3 + 2 * i, 2:8] = 1
        out[name] = m
    seed = np.any(np.stack(list(out.values())), axis=0).astype(np.uint8)
    return out, seed


def test_a_trimmed_read_keeps_a_quarter_of_the_seed_per_class_and_does_not_overlap():
    classes, seed = _blocks()
    f = report.seedComparison(np.stack([classes[n] for n in NAMES]), seed)
    assert f["kept"] == {n: 0.25 for n in NAMES}
    assert f["overlapFraction"] == 0.0 and not f["untrimmed"] and f["copies"] == []
    assert f["counts"] == {n: 96 for n in NAMES} and f["seedVoxels"] == 384


def test_an_untouched_seed_is_untrimmed_and_every_class_a_copy():
    _, seed = _blocks()
    f = report.seedComparison(np.stack([seed] * 4), seed)
    assert f["kept"] == {n: 1.0 for n in NAMES} and f["seedDice"] == {n: 1.0 for n in NAMES}
    assert f["untrimmed"] and f["copies"] == NAMES and f["keptAbove"] == NAMES
    assert f["overlapFraction"] == 1.0


def test_two_classes_keeping_most_of_the_seed_are_enough_to_call_it_untrimmed():
    classes, seed = _blocks()
    masks = np.stack([np.zeros_like(seed), seed, seed, classes["RCA"]])
    masks[1, 1, 1:3, 2:8] = 0                    # LAD trimmed a little: still > 90 %
    f = report.seedComparison(masks, seed)
    assert f["keptAbove"] == ["LAD", "LCx"] and f["untrimmed"]
    assert f["counts"]["LM"] == 0
    # LAD, LCx share the seed; RCA's block is inside it too: 3 layers there.
    labelled = int(np.count_nonzero(masks.any(axis=0)))
    shared = int(np.count_nonzero(masks.sum(axis=0) >= 2))
    assert f["overlapFraction"] == round(shared / labelled, 4)

    one = report.seedComparison(np.stack([np.zeros_like(seed), seed, classes["LCx"],
                                          classes["RCA"]]), seed)
    assert one["keptAbove"] == ["LAD"] and not one["untrimmed"]


def test_without_a_seed_only_counts_and_overlap_are_given():
    classes, _ = _blocks()
    masks = np.stack([classes[n] for n in NAMES])
    masks[2] |= masks[1]                          # LCx also covers LAD's block
    f = report.seedComparison(masks)
    assert f["kept"] is None and f["seedDice"] is None and not f["untrimmed"]
    assert f["overlapFraction"] == 0.25           # 96 shared of 384 labelled


def test_flags_are_grouped_by_the_reason_the_worker_wrote():
    assert report.flagReason("mean Dice 0.41 against the other read (< 0.60)") == "low pair Dice"
    assert report.flagReason("could not be compared with the other read: geometry_mismatch") \
        == "pair not comparable"
    assert report.flagReason("required class empty in the uploaded file: RCA") \
        == "empty required class"
    assert report.flagReason("LAD Dice 0.20 against ImageCAS-X (< 0.50)") == "low reference Dice"
    assert report.flagReason("could not be scored against ImageCAS-X: reference_missing") \
        == "reference not scorable"
    assert report.flagReason("something new") == "other"


def test_tables_align_and_the_output_is_capped():
    lines = report.table(["login", "n"], [["anna", 3], ["bo", 0.5], ["c", None]])
    assert lines == ["login     n", "-----  ----", "anna      3", "bo     0.50", "c         -"]
    many = {f"user{i:03d}": {
        "reads": 1, "approved": 0, "sentBack": 0, "underReview": 0, "revisedByReviewer": 0,
        "medianSeconds": None,
        "pairs": {"n": 0, "mean": None, "median": None, "min": None, "max": None,
                  "below": 0, "perClass": {n: None for n in NAMES}},
        "flagged": 0, "flags": {r: 0 for r in report.REASONS}, "analysed": 0, "seeded": 0,
        "keptMean": {n: None for n in NAMES}, "copies2": 0, "untrimmed": 0,
        "overlapReads": 0, "overlapMedian": None, "overlapMax": None,
        "empty": {n: 0 for n in NAMES}} for i in range(60)}
    totals = {"reads": 60, "analysed": 0, "limit": 0, "pairFlag": 0.6, "cases": 1,
              "reads0": 0, "reads1": 1, "reads2": 0, "pairsScored": 0}
    out = report.render({"annotators": many, "totals": totals,
                         "eye": {"lowestPairDice": [], "mostOverlap": [],
                                 "likelyUntrimmed": []}})
    assert len(out) == report.MAX_LINES and out[-1].endswith("run with --json for all.")
