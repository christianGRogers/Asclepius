"""Scanning a TotalSegmentator case tree: which cases qualify, and what ships with them.

Two decisions get made here that nothing downstream can undo. The first is
eligibility: TotalSegmentator is a whole-body dataset, so most of it has no
coronary anatomy in the field of view, and a scan that silently accepts those
cases spends the project's only scarce resource -- annotator hours -- on scans of
legs. The second is the head start: a case that already carries a coronary mask
hands the annotator a tree to split instead of one to draw.

Both are decided from filenames alone, which is what makes them testable here
against a few empty files rather than against 1.5 TB of CT.
"""

import os

import pytest

from segqueue import dataset


def makeCase(root, name, structures=(), image="ct.nii.gz"):
    """Create a case directory with empty files standing in for volumes."""
    caseDir = root / name
    caseDir.mkdir(parents=True, exist_ok=True)
    if image:
        (caseDir / image).write_bytes(b"")
    if structures:
        segDir = caseDir / dataset.SEGMENTATIONS_DIR
        segDir.mkdir(exist_ok=True)
        for structure in structures:
            (segDir / (structure + ".nii.gz")).write_bytes(b"")
    return caseDir


# ------------------------------------------------------------- eligibility


def test_a_case_with_a_heart_is_eligible(tmp_path):
    makeCase(tmp_path, "s0011", ["heart", "aorta", "liver"])
    cases = list(dataset.find_cases(str(tmp_path)))

    assert [c.name for c in cases] == ["s0011"]
    assert cases[0].has_heart
    assert cases[0].volume.endswith("ct.nii.gz")


def test_a_case_with_no_heart_is_skipped(tmp_path):
    # The reason the filter exists: a whole-body dataset is mostly not chests.
    makeCase(tmp_path, "s0012", ["femur_left", "femur_right", "urinary_bladder"])
    assert list(dataset.find_cases(str(tmp_path))) == []


def test_the_v1_chamber_structures_also_count_as_a_heart(tmp_path):
    # TotalSegmentator v1 split the heart into chambers and myocardium. Both
    # releases are in circulation, and rejecting v1 data would look identical to
    # "this dataset has no cardiac cases".
    makeCase(tmp_path, "s0013", ["heart_ventricle_left", "heart_myocardium"])
    cases = list(dataset.find_cases(str(tmp_path)))
    assert [c.name for c in cases] == ["s0013"]
    # Myocardium beats a chamber: it wraps the ventricles, so its centre is
    # close to where the coronary tree actually runs, which is the whole reason
    # the region mask is sent to the client.
    assert os.path.basename(cases[0].region) == "heart_myocardium.nii.gz"


def test_the_whole_heart_wins_over_a_single_chamber(tmp_path):
    # For framing the view and confining edits, the whole heart is the useful
    # mask; a left ventricle would centre the view off the coronary tree.
    makeCase(tmp_path, "s0014", ["heart_atrium_left", "heart"])
    case = next(iter(dataset.find_cases(str(tmp_path))))
    assert os.path.basename(case.region) == "heart.nii.gz"


def test_the_filter_can_be_turned_off(tmp_path):
    makeCase(tmp_path, "s0015", ["femur_left"])
    assert [c.name for c in dataset.find_cases(str(tmp_path), requireHeart=False)] \
        == ["s0015"]


def test_a_directory_with_no_ct_is_not_a_case(tmp_path):
    # Datasets acquire stray directories: a README, an unpacked archive, a
    # half-copied case. None of them should reach an annotator.
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "README.txt").write_text("hello")
    makeCase(tmp_path, "s0016", ["heart"], image=None)
    assert list(dataset.find_cases(str(tmp_path), requireHeart=False)) == []


def test_cases_come_back_in_a_stable_order(tmp_path):
    for name in ("s0030", "s0010", "s0020"):
        makeCase(tmp_path, name, ["heart"])
    names = [c.name for c in dataset.find_cases(str(tmp_path))]
    assert names == ["s0010", "s0020", "s0030"]


def test_an_unreadable_root_yields_nothing_rather_than_raising(tmp_path):
    assert list(dataset.find_cases(str(tmp_path / "does-not-exist"))) == []


# ------------------------------------------------------------- head start


def test_an_existing_coronary_mask_is_picked_up(tmp_path):
    makeCase(tmp_path, "s0020", ["heart", "coronary_arteries"])
    case = next(iter(dataset.find_cases(str(tmp_path))))

    assert case.has_seed
    assert case.seed.endswith("coronary_arteries.nii.gz")


def test_a_case_without_one_simply_has_no_seed(tmp_path):
    makeCase(tmp_path, "s0021", ["heart"])
    case = next(iter(dataset.find_cases(str(tmp_path))))
    assert not case.has_seed
    assert case.seed is None


@pytest.mark.parametrize("name", dataset.CORONARY_STRUCTURES)
def test_the_known_spellings_of_the_coronary_mask_are_all_recognised(tmp_path, name):
    makeCase(tmp_path, "s0022", ["heart", name])
    assert next(iter(dataset.find_cases(str(tmp_path)))).has_seed


def test_other_mask_formats_are_accepted(tmp_path):
    # Anyone who re-exports the dataset through Slicer ends up with .nrrd.
    caseDir = makeCase(tmp_path, "s0023", [])
    (caseDir / dataset.SEGMENTATIONS_DIR).mkdir()
    (caseDir / dataset.SEGMENTATIONS_DIR / "heart.nrrd").write_bytes(b"")
    case = next(iter(dataset.find_cases(str(tmp_path))))
    assert case.region.endswith("heart.nrrd")


# ------------------------------------------------------------------ gold


def test_gold_references_come_from_a_separate_directory(tmp_path):
    pool = tmp_path / "pool"
    gold = tmp_path / "gold"
    gold.mkdir()
    makeCase(pool, "s0040", ["heart"])
    makeCase(pool, "s0041", ["heart"])
    (gold / "s0040.nii.gz").write_bytes(b"")

    found = {c.name: c.gold for c in dataset.find_cases(str(pool), goldRoot=str(gold))}
    assert found["s0040"].endswith("s0040.nii.gz")
    assert found["s0041"] is None


def test_no_gold_root_means_no_gold(tmp_path):
    # The pool must never be its own source of answers: an expert reference
    # sitting beside the volumes would be handed to the annotator as data.
    caseDir = makeCase(tmp_path, "s0042", ["heart"])
    (caseDir / "s0042.nii.gz").write_bytes(b"")
    assert next(iter(dataset.find_cases(str(tmp_path)))).gold is None


# --------------------------------------------------------------- summary


def test_the_scan_summary_reports_what_was_rejected(tmp_path):
    # A scan returning 2 of 5 cases looks exactly like a correct one until
    # somebody asks why the project finished early, so the rejected count is
    # part of the answer rather than something to infer.
    makeCase(tmp_path, "s0001", ["heart", "coronary_arteries"])
    makeCase(tmp_path, "s0002", ["heart"])
    makeCase(tmp_path, "s0003", ["femur_left"])
    makeCase(tmp_path, "s0004", ["liver", "spleen"])
    makeCase(tmp_path, "s0005", ["heart_myocardium"])

    summary = dataset.scan_summary(str(tmp_path))

    assert summary["cases"] == 5
    assert summary["with_heart"] == 3
    assert summary["without_heart"] == 2
    assert summary["with_coronary_seed"] == 1
    assert summary["with_gold"] == 0


def test_the_summary_counts_cases_the_filter_would_drop(tmp_path):
    makeCase(tmp_path, "s0001", ["femur_left"])
    summary = dataset.scan_summary(str(tmp_path))
    assert summary["cases"] == 1
    assert summary["with_heart"] == 0
    assert list(dataset.find_cases(str(tmp_path))) == []
