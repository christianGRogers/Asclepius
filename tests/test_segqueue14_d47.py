"""D47 (#322) in the shared package: PDA, PLB and SN collapse to the vessel they
leave, branch groups marked complete travel in the class-stack header, the
extended instructions, and the per-case extended-mode flag on the wire.

No Girder, no Slicer, synthetic arrays only.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.append(str(_SRC))

from segqueue14 import labelfile, labels, protocol, quality  # noqa: E402
from segqueue14 import scoring as sq  # noqa: E402

LPS = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 2.0, 0], [0, 0, 0, 1.0]]
SPACING = (2.0, 1.0, 1.0)
SHAPE = (12, 20, 20)


def _read(**classes):
    """A 21-class read: ``{name: [index tuple, ...]}`` painted with 1."""
    stack = np.zeros((21,) + SHAPE, np.uint8)
    for name, wheres in classes.items():
        for where in wheres:
            stack[(labels.ALL_NAMES.index(name),) + where] = 1
    return stack


#: Two trunks far apart: LCx along y 3:5, RCA along y 15:17, both on x 2:4.
LCX = (slice(2, 10), slice(3, 5), slice(2, 4))
RCA = (slice(2, 10), slice(15, 17), slice(2, 4))
#: Beside each trunk, sharing a face with it (x 4:7 against the trunk's x 3).
OFF_LCX = (slice(4, 6), slice(3, 5), slice(4, 7))
OFF_RCA = (slice(4, 6), slice(15, 17), slice(4, 7))
#: Touching nothing.
ALONE = (slice(4, 6), slice(9, 11), slice(12, 14))


def _vessel(four, name):
    return four[labels.NAMES.index(name)] != 0


def _collapse(stack):
    stats = {}
    four = labels.collapse_to_four(stack, labels.ALL_NAMES, stats=stats)
    return four, stats


# ------------------------------------------------------------ Q1: collapse


@pytest.mark.parametrize("branch", ["PDA", "PLB", "SN"])
def test_a_branch_off_the_lcx_collapses_to_lcx(branch):
    stack = _read(LCx=[LCX], RCA=[RCA], **{branch: [OFF_LCX]})
    four, stats = _collapse(stack)
    assert _vessel(four, "LCx")[OFF_LCX].all()
    assert not _vessel(four, "RCA")[OFF_LCX].any()
    assert stats["byParent"] == {"RCA": 0, "LCx": 1} and stats["fallback"] == 0
    assert stats["perClass"] == {branch: {"RCA": 0, "LCx": 1}}


@pytest.mark.parametrize("branch", ["PDA", "PLB", "SN"])
def test_a_branch_off_the_rca_collapses_to_rca(branch):
    stack = _read(LCx=[LCX], RCA=[RCA], **{branch: [OFF_RCA]})
    four, stats = _collapse(stack)
    assert _vessel(four, "RCA")[OFF_RCA].all()
    assert not _vessel(four, "LCx")[OFF_RCA].any()
    assert stats["byParent"] == {"RCA": 1, "LCx": 0} and stats["fallback"] == 0


def test_left_dominance_both_posterior_branches_and_each_component_on_its_own():
    """A left-dominant heart: PDA and PLB off the LCx. An SN drawn in two pieces,
    one off each vessel, splits by component."""
    stack = _read(LCx=[LCX], RCA=[RCA], PDA=[OFF_LCX],
                  PLB=[(slice(7, 9), slice(3, 5), slice(4, 7))],
                  SN=[(slice(2, 3), slice(15, 17), slice(4, 6)),
                      (slice(2, 3), slice(3, 5), slice(4, 6))])
    four, stats = _collapse(stack)
    assert stats["components"] == 4 and stats["fallback"] == 0
    assert stats["perClass"]["SN"] == {"RCA": 1, "LCx": 1}
    assert stats["perClass"]["PDA"] == {"RCA": 0, "LCx": 1}
    assert stats["perClass"]["PLB"] == {"RCA": 0, "LCx": 1}
    # Every LCx-side voxel is in LCx, none in RCA.
    lcx_side = np.zeros(SHAPE, bool)
    lcx_side[:, :10] = True
    assert not (_vessel(four, "RCA") & lcx_side).any()


def test_a_branch_reached_through_another_takes_its_vessel():
    """A PDA drawn off a PLB that leaves the LCx goes to LCx, though it does not
    touch the LCx itself."""
    plb = (slice(4, 6), slice(3, 5), slice(4, 7))
    pda = (slice(4, 6), slice(3, 5), slice(7, 10))
    four, stats = _collapse(_read(LCx=[LCX], RCA=[RCA], PLB=[plb], PDA=[pda]))
    assert _vessel(four, "LCx")[pda].all() and not _vessel(four, "RCA")[pda].any()
    assert stats["fallback"] == 0


def test_fixed_branches_count_as_their_vessel():
    """An SN off the OM1 is off the LCx; one off the conus is off the RCA."""
    om1 = (slice(4, 6), slice(3, 5), slice(4, 6))
    conus = (slice(4, 6), slice(15, 17), slice(4, 6))
    sn_lcx = (slice(4, 6), slice(3, 5), slice(6, 8))
    sn_rca = (slice(4, 6), slice(15, 17), slice(6, 8))
    four, stats = _collapse(_read(LCx=[LCX], RCA=[RCA], OM1=[om1], Conus=[conus],
                                  SN=[sn_lcx, sn_rca]))
    assert _vessel(four, "LCx")[sn_lcx].all() and _vessel(four, "RCA")[sn_rca].all()
    assert stats["perClass"]["SN"] == {"RCA": 1, "LCx": 1}


def test_an_unattached_branch_falls_back_to_rca_and_is_counted():
    four, stats = _collapse(_read(LCx=[LCX], RCA=[RCA], PDA=[ALONE]))
    assert _vessel(four, "RCA")[ALONE].all()
    assert stats["fallback"] == 1 and stats["fallbackUnattached"] == 1
    assert stats["fallbackTie"] == 0


def test_a_tie_falls_back_to_rca_and_is_counted():
    """A bridge touching both vessels equally."""
    lcx = (slice(4, 6), slice(3, 5), slice(2, 4))
    rca = (slice(4, 6), slice(7, 9), slice(2, 4))
    bridge = (slice(4, 6), slice(5, 7), slice(2, 4))
    four, stats = _collapse(_read(LCx=[lcx], RCA=[rca], PLB=[bridge]))
    assert _vessel(four, "RCA")[bridge].all() and not _vessel(four, "LCx")[bridge].any()
    assert stats["fallback"] == 1 and stats["fallbackTie"] == 1


def test_most_contact_wins():
    """Touching both, but the LCx along a longer face."""
    lcx = (slice(2, 10), slice(3, 5), slice(2, 4))
    rca = (slice(2, 3), slice(7, 9), slice(2, 4))
    branch = (slice(2, 10), slice(5, 7), slice(2, 4))
    four, stats = _collapse(_read(LCx=[lcx], RCA=[rca], PDA=[branch]))
    assert _vessel(four, "LCx")[branch].all() and stats["fallback"] == 0


def test_a_four_class_read_is_unchanged_and_says_nothing():
    stack = _read(LCx=[LCX], RCA=[RCA])[:4]
    four, stats = labels.collapse_to_four(stack, labels.NAMES), {}
    labels.collapse_to_four(stack, labels.NAMES, stats=stats)
    assert np.array_equal(four, stack)
    assert stats["components"] == 0 and labels.contact_summary(stats) is None


def test_numpy_components_match_scipy():
    pytest.importorskip("scipy")
    rng = np.random.default_rng(7)
    mask = rng.random((9, 11, 10)) > 0.8
    a, n = labels._components(mask)
    b, m = labels._components(mask, use_scipy=False)
    assert n == m
    # The same partition, whatever the numbering.
    pairs = {(int(x), int(y)) for x, y in zip(a[mask], b[mask])}
    assert len(pairs) == n


# ------------------------------------------------------------ Q1: scoring


def test_a_left_pda_scores_as_lcx_and_the_score_says_so():
    pytest.importorskip("scipy")
    stack = _read(LCx=[LCX], RCA=[RCA], PDA=[OFF_LCX], SN=[ALONE])
    drawn = np.zeros((4,) + SHAPE, np.uint8)
    drawn[(2,) + LCX] = drawn[(2,) + OFF_LCX] = 1
    drawn[(3,) + RCA] = drawn[(3,) + ALONE] = 1
    got = sq.score_reads(stack, labels.ALL_NAMES, drawn, labels.NAMES, SPACING)
    assert got["per_structure"]["LCx"]["dice"] == 1.0
    assert got["per_structure"]["RCA"]["dice"] == 1.0
    parents = got["branchParents"]
    assert parents["byParent"] == {"RCA": 1, "LCx": 1}
    assert parents["fallback"] == 1 and "masks" not in parents


def test_a_four_class_pair_still_scores_exactly_as_before():
    pytest.importorskip("scipy")
    four = _read(LCx=[LCX], RCA=[RCA])[:4]
    other = four.copy()
    other[2, 2:4] = 0
    got = sq.score_reads(four, labels.NAMES, other, labels.NAMES, SPACING)
    assert got == sq.score_masks(four, other, SPACING)
    assert "branchParents" not in got


# ------------------------------------------------------- Q3: complete groups


def test_complete_groups_travel_in_the_header(tmp_path):
    stack = _read(LCx=[LCX], RCA=[RCA])
    path = tmp_path / "read.seg.nrrd"

    labelfile.write_class_stack(str(path), list(stack), labels.ALL_NAMES, LPS,
                                complete_groups=["RCA branches", "LAD branches"])
    header = labelfile.read_header(str(path))
    assert header[labelfile.COMPLETE_KEY] == "RCA branches|LAD branches"
    # Read back in panel order.
    assert labelfile.complete_groups(header) == ["LAD branches", "RCA branches"]
    assert labelfile.read_class_stack(str(path))["completeGroups"] == \
        ["LAD branches", "RCA branches"]
    raw = path.read_bytes()[:1 << 16]
    assert labelfile.complete_groups_bytes(raw) == ["LAD branches", "RCA branches"]

    labelfile.write_class_stack(str(path), list(stack), labels.ALL_NAMES, LPS,
                                complete_groups=[])
    assert labelfile.complete_groups(labelfile.read_header(str(path))) == []

    # A module before 0.20.0 writes no key: "not said", not "none ticked".
    labelfile.write_class_stack(str(path), list(stack), labels.ALL_NAMES, LPS)
    assert labelfile.COMPLETE_KEY not in labelfile.read_header(str(path))
    assert labelfile.complete_groups(labelfile.read_header(str(path))) is None
    assert labelfile.read_class_stack(str(path))["completeGroups"] is None
    assert labelfile.complete_groups_bytes(b"not an nrrd") is None


def test_unknown_groups_are_dropped_and_a_bad_name_cannot_go_in_a_header():
    assert labels.clean_complete_groups(["LCx branches", "Materials", "x", "LCx branches"]) \
        == ["LCx branches"]
    assert labels.clean_complete_groups(None) == []
    with pytest.raises(ValueError):
        labelfile.header_text(labels.NAMES, (2, 2, 2), LPS, complete_groups=["a|b"])


def test_the_three_groups_cover_every_branch_once():
    assert labels.COMPLETE_GROUPS == ("LAD branches", "LCx branches", "RCA branches")
    assert labels.group_members("LAD branches") == ["D1", "D2", "D3", "S1", "S2", "S3"]
    assert labels.group_members("LCx branches") == ["OM1", "OM2", "Ramus"]
    assert labels.group_members("RCA branches") == ["SN", "Conus", "RMA", "PDA", "PLB"]
    covered = sum((labels.group_members(g) for g in labels.COMPLETE_GROUPS), [])
    assert sorted(covered) == sorted(labels.PARENT)


# ------------------------------------------------------- Q1/Q7: instructions


def test_the_extended_instructions_say_whichever_vessel_and_trace_beyond_the_seed():
    text = labels.EXTENDED_INSTRUCTIONS
    assert "out of whichever vessel it leaves" in text
    assert "SN, PDA and PLB out of whichever of RCA or LCx" in text
    assert "SN, conus, RMA, PDA and PLB out of RCA" not in text
    assert "Trace septals, SN, conus and RMA" in text and "even where the vessel seed" in text
    assert "complete" in text
    hints = {d["name"]: d["hint"] for d in labels.extra_segment_dicts()}
    for name in ("SN", "PDA", "PLB"):
        assert "RCA or LCx" in hints[name] and "whichever artery" not in hints[name]


# ------------------------------------------------------------ Q6: the flag


def test_extended_mode_travels_with_the_assignment_and_defaults_off():
    base = {"assignmentId": "a", "caseId": "c", "caseName": "n", "state": "assigned",
            "attempt": 1, "sizeBytes": 1, "checksum": "x"}
    old = protocol.AssignmentInfo14.from_dict(base)
    assert old.extended_mode is False
    info = protocol.AssignmentInfo14.from_dict(dict(base, extendedMode=True))
    assert info.extended_mode is True
    assert info.to_dict()["extendedMode"] is True
    assert protocol.AssignmentInfo14.from_dict(info.to_dict()).extended_mode is True
    assert labels.EXTENDED_MODE_NOTE.startswith("This case is read in extended mode")


# ------------------------------------------------------------ the report


def test_the_quality_report_has_an_rca_fallback_column():
    person = {"reads": 3, "approved": 1, "sentBack": 0, "underReview": 0,
              "revisedByReviewer": 0, "extended": 2, "branchFallback": 1,
              "medianSeconds": 60.0,
              "pairs": {"n": 0, "mean": None, "median": None, "min": None, "max": None,
                        "perClass": {n: None for n in labels.NAMES}, "below": 0},
              "flagged": 0, "flags": {r: 0 for r in quality.REASONS}, "analysed": 0,
              "seeded": 0, "keptMean": {n: None for n in labels.NAMES}, "copies2": 0,
              "untrimmed": 0, "overlapReads": 0, "overlapMedian": None, "overlapMax": None,
              "empty": {n: 0 for n in labels.NAMES}}
    totals = {"reads": 3, "analysed": 0, "limit": 0, "pairFlag": 0.6, "cases": 1,
              "reads0": 0, "reads1": 1, "reads2": 0, "pairsScored": 0}
    lines = quality.render({"annotators": {"ann": person}, "totals": totals,
                            "eye": {"lowestPairDice": [], "mostOverlap": [],
                                    "likelyUntrimmed": []}})
    head = next(line for line in lines if line.startswith("login") and "rca fallback" in line)
    row = lines[lines.index(head) + 2]
    assert row.split()[:8] == ["ann", "3", "1", "0", "0", "0", "2", "1"]
