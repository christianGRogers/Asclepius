"""The 17 optional extended classes (D44, #280), in the shared package.

The table, the collapse to the four vessels, the protocol (17 still accepted, 17
refused only on an extended read), the class names in a class-stack header, and
scoring: an extended read scores, collapsed, exactly like the same voxels drawn
into the parents, and a material is scored only when both reads have it. No
Girder, no Slicer, synthetic arrays only.
"""

import itertools
import math
import sys
from pathlib import Path

import numpy as np
import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.append(str(_SRC))

from segqueue14 import PROTOCOL_VERSION, labelfile, labels, protocol, quality  # noqa: E402
from segqueue14 import scoring as sq  # noqa: E402

pytest.importorskip("scipy")  # segtrain.metrics' HD95

LPS = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 2.0, 0], [0, 0, 0, 1.0]]
SPACING = (2.0, 1.0, 1.0)

# ---------------------------------------------------------------- the table

EXPECTED = {
    "Materials": ["Stent", "Calcified plaque", "Non-calcified plaque"],
    "LAD branches": ["D1", "D2", "D3", "S1", "S2", "S3"],
    "LCx branches": ["OM1", "OM2"],
    "RCA branches": ["SN", "Conus", "RMA", "PDA", "PLB"],
    "Other": ["Ramus"],
}


def test_the_four_are_unchanged():
    # The headline, the training labels and the label config stay four (D25, D44).
    assert labels.NAMES == ["LM", "LAD", "LCx", "RCA"]
    assert labels.N_CLASSES == 4
    assert labels.LABEL_VALUES == {"LM": 1, "LAD": 2, "LCx": 3, "RCA": 4}


def test_seventeen_extended_classes_in_the_issues_groups():
    assert len(labels.EXTRA_NAMES) == 17
    assert len(labels.ALL_NAMES) == 21 == len(set(labels.ALL_NAMES))
    for group, names in EXPECTED.items():
        assert [n for n in labels.EXTRA_NAMES if labels.GROUP_OF[n] == group] == names
    assert all(labels.GROUP_OF[n] == labels.GROUP_VESSELS for n in labels.NAMES)


def test_label_values_are_pinned_and_unique():
    # Never re-pinned (#270's root cause): 1-4 the vessels, 5-21 the extras, fixed.
    assert [labels.ALL_LABEL_VALUES[n] for n in labels.ALL_NAMES] == list(range(1, 22))
    assert labels.ALL_LABEL_VALUES["Stent"] == 5
    assert labels.ALL_LABEL_VALUES["Ramus"] == 21


def test_parents_follow_the_issue():
    lad = ["D1", "D2", "D3", "S1", "S2", "S3"]
    lcx = ["OM1", "OM2", "Ramus"]
    rca = ["SN", "Conus", "RMA", "PDA", "PLB"]
    assert labels.PARENT == dict([(n, "LAD") for n in lad] + [(n, "LCx") for n in lcx]
                                 + [(n, "RCA") for n in rca])
    assert labels.MATERIALS == EXPECTED["Materials"]
    assert not set(labels.MATERIALS) & set(labels.PARENT)


def test_colours_are_distinct():
    colours = {d["name"]: d["color"] for d in labels.segment_dicts()
               + labels.extra_segment_dicts()}
    assert len(colours) == 21
    closest = min(math.dist(colours[a], colours[b])
                  for a, b in itertools.combinations(colours, 2))
    assert closest > 0.15


def test_display_order_groups_branches_under_their_parent():
    order = labels.DISPLAY_ORDER
    assert sorted(order) == sorted(labels.ALL_NAMES)
    for branch, parent in labels.PARENT.items():
        assert order.index(branch) > order.index(parent)
    assert order[-3:] == labels.MATERIALS


def test_every_class_has_annotator_instructions():
    for entry in labels.extra_segment_dicts():
        assert entry["hint"] and entry["required"] is False
    assert "optional" in labels.EXTENDED_INSTRUCTIONS.lower()


def test_extended_names_are_safe_in_a_class_stack_header():
    labelfile.header_text(labels.ALL_NAMES, (2, 2, 2), LPS)  # raises on '|' or newline


def test_is_extended():
    assert not labels.is_extended(labels.NAMES)
    assert labels.is_extended(labels.ALL_NAMES)
    assert labels.is_extended(["LM", "Stent"])
    assert labels.stack_names(False) == labels.NAMES
    assert labels.stack_names(True) == labels.ALL_NAMES


# ------------------------------------------------------------- the collapse


def _tree(shape=(12, 16, 16)):
    """A synthetic tree: four trunks, each with branches beside it, and materials."""
    four = np.zeros((4,) + shape, np.uint8)
    four[0, 2:4, 2:4, 2:4] = 1                 # LM
    four[1, 2:10, 5:7, 2:4] = 1                # LAD trunk
    four[2, 2:10, 9:11, 2:4] = 1               # LCx trunk
    four[3, 2:10, 13:15, 2:4] = 1              # RCA trunk
    branches = {
        "D1": (slice(3, 5), slice(5, 7), slice(5, 8)),
        "S1": (slice(6, 8), slice(5, 7), slice(5, 8)),
        "OM1": (slice(3, 5), slice(9, 11), slice(5, 8)),
        "Ramus": (slice(7, 9), slice(9, 11), slice(5, 8)),
        "PDA": (slice(3, 5), slice(13, 15), slice(5, 8)),
        "SN": (slice(7, 9), slice(13, 15), slice(5, 8)),
    }
    materials = {
        "Stent": (slice(4, 6), slice(5, 7), slice(2, 4)),          # inside the LAD
        "Calcified plaque": (slice(5, 6), slice(13, 15), slice(2, 4)),
    }
    return four, branches, materials


def _extended(four, branches, materials, move=True):
    """The same voxels as a 21-class read: branches moved out of their parents."""
    stack = np.zeros((21,) + four.shape[1:], np.uint8)
    stack[:4] = four
    for name, where in list(branches.items()) + list(materials.items()):
        channel = labels.ALL_NAMES.index(name)
        stack[(channel,) + where] = 1
        parent = labels.PARENT.get(name)
        if parent and move:
            stack[(labels.NAMES.index(parent),) + where] = 0
    return stack


def _drawnIntoParents(four, branches):
    """The four-class read an annotator not using the extras would draw."""
    out = four.copy()
    for name, where in branches.items():
        out[(labels.NAMES.index(labels.PARENT[name]),) + where] = 1
    return out


def test_a_four_class_read_collapses_to_itself():
    four, _, _ = _tree()
    assert np.array_equal(labels.collapse_to_four(four, labels.NAMES), four)


def test_branches_fold_into_their_parent_and_materials_into_nothing():
    four, branches, materials = _tree()
    stack = _extended(four, branches, materials)
    got = labels.collapse_to_four(stack, labels.ALL_NAMES)
    assert np.array_equal(got, _drawnIntoParents(four, branches))
    # The stent sits inside the LAD; the calcified plaque was painted beside the
    # RCA trunk and must not have become RCA.
    plaque = materials["Calcified plaque"]
    assert got[(3,) + plaque].all()                      # the trunk was there already
    alone = np.zeros_like(stack)
    alone[(labels.ALL_NAMES.index("Calcified plaque"),) + (slice(0, 2),) * 3] = 1
    assert not labels.collapse_to_four(alone, labels.ALL_NAMES).any()


def test_collapse_checks_the_channel_count():
    with pytest.raises(ValueError):
        labels.collapse_to_four(np.zeros((3, 2, 2, 2)), labels.NAMES)


# --------------------------------------------------------------- protocol


def test_protocol_17_and_18_are_both_accepted():
    for sent in (17, "17", 18, "18", PROTOCOL_VERSION):
        protocol.check_client_protocol(sent)


def test_a_protocol_17_reviewer_is_refused_only_an_extended_read():
    protocol.check_extended_reader(17, extended=False)      # a 4-class read: fine
    protocol.check_extended_reader(18, extended=True)       # the new module: fine
    protocol.check_extended_reader(None, extended=True)     # not a module: fine
    with pytest.raises(protocol.ProtocolError) as info:
        protocol.check_extended_reader(17, extended=True)
    assert info.value.code == protocol.ERR_UPDATE_TO_REVIEW
    assert "Update SegQueue14 to review this read" in str(info.value)
    assert info.value.detail["minProtocol"] == protocol.EXTENDED_CLASSES_PROTOCOL == 18


# --------------------------------------------------------------- the file


def test_class_names_come_from_the_header(tmp_path):
    four, branches, materials = _tree()
    stack = _extended(four, branches, materials)
    path = tmp_path / "read.seg.nrrd"
    labelfile.write_class_stack(str(path), list(stack), labels.ALL_NAMES, LPS)
    raw = path.read_bytes()[:1 << 16]
    assert labelfile.class_names_bytes(raw) == labels.ALL_NAMES
    data = labelfile.read_class_stack(str(path))
    assert data["names"] == labels.ALL_NAMES
    assert np.array_equal(data["masks"], stack)

    labelfile.write_class_stack(str(path), list(four), labels.NAMES, LPS)
    assert labelfile.class_names_bytes(path.read_bytes()[:1 << 16]) == labels.NAMES
    assert labelfile.class_names_bytes(b"\x1f\x8b not an nrrd") == []


# ---------------------------------------------------------------- scoring


def test_the_collapsed_score_equals_the_four_class_score_of_the_same_voxels():
    four, branches, materials = _tree()
    extended = _extended(four, branches, materials)
    drawn = _drawnIntoParents(four, branches)
    other = four.copy()
    other[1, 8:10] = 0                                    # a second read, a bit shorter

    want = sq.score_masks(drawn, other, SPACING)
    got = sq.score_reads(extended, labels.ALL_NAMES, other, labels.NAMES, SPACING)
    assert got["mean_dice"] == want["mean_dice"]
    assert got["per_structure"] == want["per_structure"]
    assert got["required_min_dice"] == want["required_min_dice"]
    # One side is extended, the other is not: no material is scored, but they pair.
    assert "materials" not in got
    assert got["extended"] == {"read": True, "reference": False}


def test_a_four_class_pair_scores_exactly_as_before():
    four, _, _ = _tree()
    other = four.copy()
    other[3, 2:5] = 0
    assert sq.score_reads(four, labels.NAMES, other, labels.NAMES, SPACING) == \
        sq.score_masks(four, other, SPACING)


def test_a_material_is_scored_only_when_both_reads_have_it():
    four, branches, materials = _tree()
    mine = _extended(four, branches, materials)
    theirs = _extended(four, branches, {"Stent": materials["Stent"]}, move=False)
    got = sq.score_reads(mine, labels.ALL_NAMES, theirs, labels.ALL_NAMES, SPACING)
    # Both name every material (both are 21-class): all three are scored, the
    # calcified plaque only one of them painted scores 0, the non-calcified
    # plaque neither painted has no Dice.
    assert got["materials"]["Stent"]["dice"] == 1.0
    assert got["materials"]["Calcified plaque"]["dice"] == 0.0
    assert got["materials"]["Non-calcified plaque"]["dice"] is None
    # Materials never move the headline: same as the collapsed four.
    assert got["mean_dice"] == sq.score_masks(
        labels.collapse_to_four(mine, labels.ALL_NAMES),
        labels.collapse_to_four(theirs, labels.ALL_NAMES), SPACING)["mean_dice"]

    subset = ["LM", "LAD", "LCx", "RCA", "Stent"]
    small = np.concatenate([four, mine[[labels.ALL_NAMES.index("Stent")]]])
    got = sq.score_reads(mine, labels.ALL_NAMES, small, subset, SPACING)
    assert list(got["materials"]) == ["Stent"]


# ---------------------------------------------------------------- report


def test_the_quality_report_counts_extended_reads():
    person = {"reads": 3, "approved": 1, "sentBack": 0, "underReview": 0,
              "revisedByReviewer": 0, "extended": 2, "medianSeconds": 60.0,
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
    head = next(line for line in lines if line.startswith("login") and "extended" in line)
    row = lines[lines.index(head) + 2]
    assert row.split()[:7] == ["ann", "3", "1", "0", "0", "0", "2"]
