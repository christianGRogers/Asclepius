"""The reviewer's "Compare reads" view (#335), in the shared package.

Which reads of a case are offered (annotator reads only; reopened and superseded
reads only when asked for), the both / A-only / B-only voxel counts per class
against a hand-computed overlap, the Dice against the server's own pair scoring
(``segqueue14.scoring.score_reads``) on the same voxels, an extended read against a
four-class read compared after the collapse (PDA by contact, D47), two extended
reads class by class, and three reads of which two are picked. Synthetic arrays only.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.append(str(_SRC))

from segqueue14 import compare, labels  # noqa: E402

SHAPE = (12, 16, 16)
SPACING = (0.6, 0.5, 0.5)


def _four(**boxes):
    """``(4, *SHAPE)`` masks: each named class filled in its ``(z0, z1, y0, y1, x0, x1)``."""
    out = np.zeros((4,) + SHAPE, np.uint8)
    for name, (z0, z1, y0, y1, x0, x1) in boxes.items():
        out[labels.NAMES.index(name), z0:z1, y0:y1, x0:x1] = 1
    return out


def _extended(four, **extra):
    """``four`` with the 17 extended channels added, ``extra`` boxes filled."""
    out = np.zeros((len(labels.ALL_NAMES),) + SHAPE, np.uint8)
    out[:4] = four
    for name, (z0, z1, y0, y1, x0, x1) in extra.items():
        out[labels.ALL_NAMES.index(name), z0:z1, y0:y1, x0:x1] = 1
    return out


# ------------------------------------------------------------------- the reads


def _row(sid, login, assignment, state="submitted", role="annotator", **more):
    row = {"submissionId": sid, "assignmentId": assignment, "state": state,
           "authorRole": role, "annotator": {"login": login}, "attempt": 1}
    row.update(more)
    return row


def test_two_pool_reads_are_a_and_b_and_a_revision_is_not_a_read():
    rows = [_row("s1", "ann1", "x1"), _row("s2", "ann2", "x2"),
            _row("s3", "rev", "x1", role="reviewer")]
    reads = compare.comparable_reads(rows)
    assert [(r["key"], r["submissionId"]) for r in reads] == [("A", "s1"), ("B", "s2")]
    assert compare.read_label(reads[0]) == "A: ann1"


def test_a_reopened_read_is_left_out_unless_asked_for():
    # #315: the server's flag when it sends one.
    rows = [_row("s1", "ann1", "x1", reopened=True), _row("s2", "ann2", "x2", reopened=False),
            _row("s3", "ann1", "x1", reopened=False, attempt=2)]
    assert [r["submissionId"] for r in compare.comparable_reads(rows)] == ["s2", "s3"]
    every = compare.comparable_reads(rows, include_reopened=True)
    assert [(r["key"], r["submissionId"], r["reopened"]) for r in every] == [
        ("A", "s1", True), ("B", "s2", False), ("C", "s3", False)]
    assert compare.read_label(every[0]).endswith("[reopened]")
    assert compare.read_label(every[2]) == "C: ann1, attempt 2"


def test_without_the_flag_a_reopened_read_is_known_by_its_assignment():
    # Reopened and not yet resubmitted: the assignment is back with the annotator.
    waiting = [_row("s1", "ann1", "x1", state="downloaded"), _row("s2", "ann2", "x2")]
    assert [r["submissionId"] for r in compare.comparable_reads(waiting)] == ["s2"]
    # Resubmitted: the later submission on the same assignment replaces it.
    back = [_row("s1", "ann1", "x1"), _row("s2", "ann2", "x2"),
            _row("s3", "ann1", "x1", attempt=2)]
    assert [r["submissionId"] for r in compare.comparable_reads(back)] == ["s2", "s3"]


def test_a_third_read_after_a_return_to_pool_is_offered():
    rows = [_row("s1", "ann1", "x1", state="released"), _row("s2", "ann2", "x2"),
            _row("s3", "ann3", "x3")]
    assert [r["key"] for r in compare.comparable_reads(rows)] == ["A", "B", "C"]
    assert len({compare.read_colour(k) for k in "ABC"}) == 3


# ----------------------------------------------------------------- the numbers


def test_the_counts_match_a_hand_computed_overlap_per_class():
    # LAD: A 2x4x4 at z 2-4, B 2x4x4 at z 3-5 -> both 1x4x4 = 16, A only 16, B only 16.
    # RCA: A 4x2x2 = 16, B none -> A only 16. LCx in neither.
    a = _four(LAD=(2, 4, 2, 6, 2, 6), RCA=(1, 5, 10, 12, 10, 12), LM=(0, 2, 0, 2, 0, 2))
    b = _four(LAD=(3, 5, 2, 6, 2, 6), LM=(0, 2, 0, 2, 0, 2))
    result = compare.compare_reads(a, labels.NAMES, b, labels.NAMES)
    pc = result["per_class"]
    assert result["mode"] == compare.MODE_FOUR
    assert (pc["LAD"]["both"], pc["LAD"]["a_only"], pc["LAD"]["b_only"]) == (16, 16, 16)
    assert pc["LAD"]["dice"] == 0.5
    assert (pc["RCA"]["both"], pc["RCA"]["a_only"], pc["RCA"]["b_only"]) == (0, 16, 0)
    assert pc["RCA"]["dice"] == 0.0
    assert (pc["LM"]["both"], pc["LM"]["dice"]) == (8, 1.0)
    assert pc["LCx"]["dice"] is None and pc["LCx"]["voxels_a"] == pc["LCx"]["voxels_b"] == 0
    assert result["mean_dice"] == 0.5 and result["n_scored"] == 3
    maps = compare.category_masks(*(m[labels.NAMES.index("LAD")]
                                    for m in result["masks"][1:]))
    assert [int(maps[k].sum()) for k in (compare.BOTH, compare.A_ONLY, compare.B_ONLY)] \
        == [16, 16, 16]
    lines = compare.summary_lines(result)
    assert lines[1] == "LAD: Dice 0.500  |  both 16  A only 16  B only 16"
    assert lines[2] == "LCx: in neither read"
    assert lines[-1] == "Mean Dice (the pair score): 0.500"
    assert compare.summary_lines(result, "RCA")[0].startswith("RCA: Dice 0.000")


def _server_dice(a, a_names, b, b_names):
    pytest.importorskip("scipy")  # segtrain.metrics' HD95
    from segqueue14 import scoring as sq

    return sq.score_reads(a, a_names, b, b_names, SPACING)


def test_the_dice_matches_the_servers_pair_scoring():
    a = _four(LAD=(2, 8, 2, 6, 2, 6), LCx=(2, 8, 8, 11, 2, 5), RCA=(1, 9, 10, 13, 10, 13))
    b = _four(LAD=(3, 9, 3, 6, 2, 7), LCx=(4, 8, 8, 12, 2, 5), RCA=(1, 6, 10, 13, 11, 14),
              LM=(0, 1, 0, 1, 0, 1))
    mine = compare.compare_reads(a, labels.NAMES, b, labels.NAMES)
    server = _server_dice(a, labels.NAMES, b, labels.NAMES)
    for name in labels.NAMES:
        assert mine["per_class"][name]["dice"] == server["per_structure"][name]["dice"], name
        assert mine["per_class"][name]["voxels_a"] == server["per_structure"][name]["voxels_read"]
    assert mine["mean_dice"] == server["mean_dice"]
    assert mine["headline"]["mean_dice"] == server["mean_dice"]


def test_an_extended_read_against_a_four_class_read_compares_after_the_collapse():
    # The extended read draws its LCx short and the rest as a PDA leaving the LCx
    # (left-dominant, D47 Q1): collapsed, the PDA is LCx, so the LCx agrees fully.
    lcx = (2, 10, 8, 11, 2, 5)
    four = _four(LAD=(2, 8, 2, 6, 2, 6), LCx=lcx, RCA=(1, 9, 10, 13, 10, 13))
    short = _four(LAD=(2, 8, 2, 6, 2, 6), LCx=(2, 6, 8, 11, 2, 5), RCA=(1, 9, 10, 13, 10, 13))
    ext = _extended(short, PDA=(6, 10, 8, 11, 2, 5), D1=(2, 4, 6, 8, 2, 6))
    result = compare.compare_reads(ext, labels.ALL_NAMES, four, labels.NAMES)
    assert result["mode"] == compare.MODE_FOUR
    assert result["names"] == labels.NAMES
    assert result["per_class"]["LCx"]["dice"] == 1.0
    assert result["per_class"]["RCA"]["dice"] == 1.0
    # D1 went into the LAD: 16 voxels the four-class read does not have.
    assert result["per_class"]["LAD"]["a_only"] == 2 * 2 * 4
    server = _server_dice(ext, labels.ALL_NAMES, four, labels.NAMES)
    for name in labels.NAMES:
        assert result["per_class"][name]["dice"] == server["per_structure"][name]["dice"]
    # The same, the other way round.
    flipped = compare.compare_reads(four, labels.NAMES, ext, labels.ALL_NAMES)
    assert flipped["per_class"]["LAD"]["b_only"] == 16
    assert flipped["mean_dice"] == result["mean_dice"]


def test_two_extended_reads_compare_class_by_class_with_the_pair_score_beside():
    base = _four(LAD=(2, 8, 2, 6, 2, 6), RCA=(1, 9, 10, 13, 10, 13))
    a = _extended(base, D1=(2, 4, 6, 8, 2, 6), Stent=(3, 5, 3, 5, 3, 5))
    b = _extended(base, D2=(2, 4, 6, 8, 2, 6), Stent=(4, 6, 3, 5, 3, 5))
    result = compare.compare_reads(a, labels.ALL_NAMES, b, labels.ALL_NAMES)
    assert result["mode"] == compare.MODE_CLASSES
    assert result["names"] == labels.ALL_NAMES
    pc = result["per_class"]
    # Class by class the D1 and the D2 disagree completely...
    assert (pc["D1"]["a_only"], pc["D1"]["dice"]) == (16, 0.0)
    assert (pc["D2"]["b_only"], pc["D2"]["dice"]) == (16, 0.0)
    assert (pc["Stent"]["both"], pc["Stent"]["dice"]) == (4, 0.5)
    # ...but both go into the LAD in the collapse, which is the pair score.
    head = result["headline"]["per_class"]
    assert head["LAD"]["dice"] == 1.0
    server = _server_dice(a, labels.ALL_NAMES, b, labels.ALL_NAMES)
    assert result["headline"]["mean_dice"] == server["mean_dice"]
    assert pc["Stent"]["dice"] == server["materials"]["Stent"]["dice"]
    assert compare.summary_lines(result)[-1].startswith(
        "Mean Dice after the four-class collapse (the pair score): 1.000")


def test_three_reads_any_two_can_be_the_pair():
    reads = {"A": _four(LAD=(2, 8, 2, 6, 2, 6)),
             "B": _four(LAD=(2, 8, 2, 6, 2, 6)),
             "C": _four(LAD=(5, 8, 2, 6, 2, 6))}
    dice = {pair: compare.compare_reads(reads[pair[0]], labels.NAMES,
                                        reads[pair[1]], labels.NAMES)["mean_dice"]
            for pair in ("AB", "AC", "BC", "CA")}
    assert dice == {"AB": 1.0, "AC": round(2 * 48 / (96 + 48), 4),
                    "BC": round(2 * 48 / (96 + 48), 4), "CA": round(2 * 48 / (96 + 48), 4)}


def test_reads_on_different_grids_are_refused():
    with pytest.raises(ValueError):
        compare.align(np.zeros((4, 2, 2, 2)), labels.NAMES, np.zeros((4, 2, 2, 3)),
                      labels.NAMES)


def test_the_box_helpers():
    mask = np.zeros(SHAPE, bool)
    assert compare.bounding_box(mask) is None
    mask[3:5, 4:6, 7:9] = True
    box = compare.bounding_box(mask, margin=1)
    assert box == (slice(2, 6), slice(3, 7), slice(6, 10))
    assert compare.union_box([box, None, (slice(0, 3), slice(5, 9), slice(6, 7))], SHAPE) \
        == (slice(0, 6), slice(3, 9), slice(6, 10))
    assert compare.union_box([None], SHAPE) == (slice(0, 1),) * 3


def test_the_module_imports_without_numpy_on_the_path():
    # Like scoring: the Slicer side imports it, and numpy is only needed on use.
    import ast

    tree = ast.parse((_SRC / "segqueue14" / "compare.py").read_text())
    top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert all("numpy" not in ast.dump(n) for n in top)
