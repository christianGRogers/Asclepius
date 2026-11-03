"""D39 (#275): a SegQueue14 submission keeps every class whole, overlaps included.

The format is ``segqueue14.labelfile``'s class stack: one NRRD on the CT grid with one 0/1
channel per class, readable without Slicer. These tests pin what the server, the scoring worker
and ``segtrain`` rely on: that four identical copies (an untouched seeded case) stay four whole
classes, that a partly trimmed case keeps every class's own voxels, that old single-label files
are still told apart and scored as before, and that a module older than protocol 17 is refused.
That Slicer itself writes and reopens the file is ``tests/slicer_selftest14.py``.
"""

import gzip
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.append(str(REPO / "src"))

from segqueue14 import PROTOCOL_VERSION, labelfile, labels, protocol  # noqa: E402
from segqueue14 import scoring as sq  # noqa: E402

SHAPE = (12, 16, 20)            # (k, j, i), as Slicer and SimpleITK arrays are
IJK_TO_LPS = [[-0.5, 0, 0, 10.0], [0, -0.6, 0, -20.0], [0, 0, 0.7, 30.0], [0, 0, 0, 1]]


def _tree():
    """Four disjoint tubes, one per class, in project label values."""
    vol = np.zeros(SHAPE, np.uint8)
    for value, (lo, hi) in zip((1, 2, 3, 4), ((1, 3), (5, 7), (9, 11), (13, 15))):
        vol[2:10, lo:hi, 3:17] = value
    return vol


def _write(tmp_path, masks, name="sub.seg.nrrd"):
    path = tmp_path / name
    labelfile.write_class_stack(str(path), masks, labels.NAMES, IJK_TO_LPS,
                                colors=[s["color"] for s in labels.segment_dicts()])
    return path


def test_an_untouched_seeded_case_reads_back_as_four_whole_classes(tmp_path):
    seed = (_tree() > 0).astype(np.uint8)
    path = _write(tmp_path, [seed] * 4)
    data = labelfile.read_class_stack(str(path))
    assert data["names"] == labels.NAMES
    assert data["masks"].shape == (4,) + SHAPE
    for mask in data["masks"]:
        assert np.array_equal(mask, seed)
    counts = labelfile.voxel_counts(data["masks"], data["names"])
    assert counts == {name: int(seed.sum()) for name in labels.NAMES}
    assert len(labelfile.overlaps(data["masks"], data["names"])) == 6


def test_a_partly_trimmed_case_keeps_every_class_s_own_voxels(tmp_path):
    tree = _tree()
    masks = [(tree == v).astype(np.uint8) for v in (1, 2, 3, 4)]
    masks[1] = masks[1] | masks[2]                      # LAD still holds the LCx
    data = labelfile.read_class_stack(str(_write(tmp_path, masks)))
    for want, got in zip(masks, data["masks"]):
        assert np.array_equal(want, got)
    assert labelfile.overlaps(data["masks"], data["names"]) == [
        ("LAD", "LCx", int(masks[2].sum()))]


def test_the_file_is_on_the_ct_grid_and_carries_slicer_s_segment_keys(tmp_path):
    path = _write(tmp_path, [_tree() == v for v in (1, 2, 3, 4)])
    header = labelfile.read_header(str(path))
    assert header["dimension"] == "4"
    assert header["sizes"] == "4 20 16 12"                     # class, i, j, k
    assert header["kinds"] == "list domain domain domain"
    assert header["space"] == "left-posterior-superior"
    assert header[labelfile.FORMAT_KEY] == labelfile.FORMAT_CLASS_STACK
    for c, name in enumerate(labels.NAMES):
        assert header[f"Segment{c}_Name"] == name
        assert header[f"Segment{c}_Layer"] == str(c)           # one layer per class
        assert header[f"Segment{c}_LabelValue"] == "1"
        assert header[f"Segment{c}_Extent"] == "0 19 0 15 0 11"  # never cropped
    data = labelfile.read_class_stack(str(path))
    assert data["spacing"] == pytest.approx((0.5, 0.6, 0.7))
    assert data["origin"] == pytest.approx((10.0, -20.0, 30.0))
    assert data["direction"] == pytest.approx((-1, 0, 0, 0, -1, 0, 0, 0, 1))


def test_the_geometry_matches_simpleitk(tmp_path):
    sitk = pytest.importorskip("SimpleITK")
    ct = sitk.GetImageFromArray(np.zeros(SHAPE, np.int16))
    ct.SetSpacing((0.4, 0.45, 0.6))
    ct.SetOrigin((-5.0, 7.0, 11.0))
    ct.SetDirection((0, 1, 0, -1, 0, 0, 0, 0, 1))
    d, sp, o = ct.GetDirection(), ct.GetSpacing(), ct.GetOrigin()
    ijk = [[d[3 * r + c] * sp[c] for c in range(3)] + [o[r]] for r in range(3)]
    path = tmp_path / "g.seg.nrrd"
    labelfile.write_class_stack(str(path), [_tree() == 2] * 4, labels.NAMES, ijk)
    data = labelfile.read_class_stack(str(path))
    image = sitk.GetImageFromArray(data["masks"][0])
    image.SetSpacing(data["spacing"])
    image.SetOrigin(data["origin"])
    image.SetDirection(data["direction"])
    for idx in ((0, 0, 0), (19, 15, 11), (3, 7, 5)):
        assert image.TransformIndexToPhysicalPoint(idx) == pytest.approx(
            ct.TransformIndexToPhysicalPoint(idx))


def test_ras_to_lps_flips_the_first_two_rows():
    ras = [[0.5, 0, 0, 1], [0, 0.5, 0, 2], [0, 0, 0.7, 3], [0, 0, 0, 1]]
    lps = labelfile.ras_to_lps(ras)
    assert lps[0] == [-0.5, 0, 0, -1] and lps[1] == [0, -0.5, 0, -2]
    assert lps[2] == [0, 0, 0.7, 3]


def test_old_files_sniff_as_label_volumes(tmp_path):
    stack = _write(tmp_path, [_tree() > 0] * 4)
    assert labelfile.sniff(str(stack)) == labelfile.FORMAT_CLASS_STACK
    assert labelfile.sniff_bytes(stack.read_bytes()[:4096]) == labelfile.FORMAT_CLASS_STACK
    plain = tmp_path / "old.seg.nrrd"
    plain.write_bytes(b"NRRD0004\ntype: unsigned char\ndimension: 3\nsizes: 2 2 2\n"
                      b"encoding: raw\n\n" + bytes(8))
    nifti = tmp_path / "old.nii.gz"
    nifti.write_bytes(gzip.compress(bytes(400)))
    for path in (plain, nifti):
        assert labelfile.sniff(str(path)) == labelfile.FORMAT_LABELMAP
        assert labelfile.sniff_bytes(path.read_bytes()) == labelfile.FORMAT_LABELMAP
    with pytest.raises(labelfile.LabelFileError):
        labelfile.read_class_stack(str(plain))


def test_bad_inputs_are_refused(tmp_path):
    with pytest.raises(ValueError):
        labelfile.write_class_stack(str(tmp_path / "x"), [_tree()] * 3, labels.NAMES, IJK_TO_LPS)
    with pytest.raises(ValueError):
        labelfile.write_class_stack(str(tmp_path / "x"), [_tree(), _tree()[:, :, :4]] * 2,
                                    labels.NAMES, IJK_TO_LPS)
    with pytest.raises(ValueError):
        labelfile.header_text(["a|b"], (1, 1, 1), IJK_TO_LPS)


# -------------------------------------------------------------------------- protocol


def test_protocol_17_refuses_a_0_16_module():
    assert PROTOCOL_VERSION == 17 and protocol.MIN_CLIENT_PROTOCOL == 17
    protocol.check_client_protocol(17)
    with pytest.raises(protocol.ProtocolError) as err:
        protocol.check_client_protocol(16)
    assert err.value.code == protocol.ERR_CLIENT_TOO_OLD
    assert "Update the SegQueue14 module" in str(err.value)


def test_label_format_names():
    assert protocol.label_format(None) == protocol.LABEL_FORMAT_LABELMAP
    assert protocol.label_format("") == protocol.LABEL_FORMAT_LABELMAP
    assert protocol.label_format("class-stack-nrrd/1") == protocol.LABEL_FORMAT_CLASS_STACK
    with pytest.raises(protocol.ProtocolError) as err:
        protocol.label_format("png")
    assert err.value.code == protocol.ERR_BAD_LABEL_FORMAT


# --------------------------------------------------------------------------- scoring


def test_each_class_of_a_stack_is_scored_from_its_own_mask():
    pytest.importorskip("scipy")
    tree = _tree()
    reference = sq.as_masks(tree)
    whole = np.stack([(tree > 0)] * 4).astype(np.uint8)
    result = sq.score_masks(whole, reference, (0.7, 0.6, 0.5))
    per = result["per_structure"]
    for name in labels.NAMES:
        assert per[name]["voxels_read"] == int((tree > 0).sum())
        assert per[name]["dice"] == pytest.approx(0.4)    # 1 tube of 4, both ways
    assert sq.mask_counts(whole) == {n: int((tree > 0).sum()) for n in labels.NAMES}


def test_an_old_label_volume_scores_exactly_as_before():
    pytest.importorskip("scipy")
    from segtrain.metrics import agreement

    tree = _tree()
    read = tree.copy()
    read[read == 4] = 3
    spacing = (0.7, 0.6, 0.5)
    new = sq.score_labels(read, tree, spacing)
    a, b = sq.crop_to_union(read, tree)
    old = agreement(a, b, labels.NAMES, spacing)
    for name in labels.NAMES:
        assert new["per_structure"][name]["dice"] == old["per_structure"][name]["dice"]
        assert new["per_structure"][name]["hd95"] == old["per_structure"][name]["hd95"]
    assert new["mean_dice"] == old["mean_dice"]


def test_crop_to_union_cuts_a_stack_on_its_spatial_axes():
    tree = _tree()
    a = sq.as_masks(tree)
    b, c = sq.crop_to_union(a, a)
    assert b.shape[0] == 4 and b.shape[1:] == sq.crop_to_union(tree, tree)[0].shape
    empty = np.zeros_like(a)
    assert sq.crop_to_union(empty, empty)[0].shape == (4, 1, 1, 1)


# ----------------------------------------------------------------------------- reads


def _export_tree(root, folder, classes):
    nib = pytest.importorskip("nibabel")
    seg = root / folder / "segmentations"
    seg.mkdir(parents=True)
    for name, mask in classes.items():
        nib.save(nib.Nifti1Image(mask.astype(np.uint8), np.diag([0.5, 0.5, 0.5, 1.0])),
                 str(seg / f"{name}.nii.gz"))


def test_reads_load_a_segqueue14_export_and_refuse_overlaps_when_asked(tmp_path):
    pytest.importorskip("scipy")
    from segtrain import reads as R

    tree = _tree()
    disjoint = {name: tree == labels.LABEL_VALUES[name] for name in labels.NAMES}
    _export_tree(tmp_path, "imagecas_0004", disjoint)
    overlapping = dict(disjoint, LAD=disjoint["LAD"] | disjoint["LCx"])
    _export_tree(tmp_path, "imagecas_0004__r2", overlapping)
    sealed = set()

    with pytest.raises(R.OverlappingClassesError, match=r"LAD/LCx \d+ voxels"):
        R.load_read_folder(str(tmp_path), sealed=sealed, pool_seal="exclude", overlap="refuse")

    with pytest.warns(UserWarning, match="classes share voxels"):
        [case] = R.load_read_folder(str(tmp_path), sealed=sealed, pool_seal="exclude",
                                    overlap="report")
    assert sorted(case.reads) == ["r1", "r2"]
    assert np.array_equal(case.reads["r1"], tree)              # LM, LAD, LCx, RCA by name
    assert case.overlaps == {"r2": [("LAD", "LCx", int(disjoint["LCx"].sum()))]}
    assert "r1" not in case.overlaps


def test_reads_mark_shared_voxels_ignore_by_default(tmp_path):
    """D40 (#278): the default load writes a voxel two classes share as IGNORE and records it."""
    pytest.importorskip("scipy")
    from segtrain import reads as R

    tree = _tree()
    disjoint = {name: tree == labels.LABEL_VALUES[name] for name in labels.NAMES}
    _export_tree(tmp_path, "imagecas_0004", disjoint)
    overlapping = dict(disjoint, LAD=disjoint["LAD"] | disjoint["LCx"])
    _export_tree(tmp_path, "imagecas_0004__r2", overlapping)

    with pytest.warns(UserWarning, match=r"written as ignore \(D40\)"):
        [case] = R.load_read_folder(str(tmp_path), sealed=set(), pool_seal="exclude")
    assert np.array_equal(case.reads["r1"], tree)
    want = tree.copy()
    want[disjoint["LCx"]] = R.IGNORE
    assert np.array_equal(case.reads["r2"], want)
    assert case.overlaps == {"r2": [("LAD", "LCx", int(disjoint["LCx"].sum()))]}


def test_an_untouched_seeded_read_is_all_ignore_on_the_tree(tmp_path):
    pytest.importorskip("scipy")
    from segtrain import reads as R

    tree = _tree() > 0
    _export_tree(tmp_path, "imagecas_0004", {name: tree for name in labels.NAMES})
    with pytest.warns(UserWarning, match="classes share voxels"):
        [case] = R.load_read_folder(str(tmp_path), sealed=set(), pool_seal="exclude")
    assert np.array_equal(case.reads["r1"], np.where(tree, R.IGNORE, 0))


def test_the_reads_report_leaves_ignored_voxels_out_of_the_agreement(tmp_path):
    """A voxel one read leaves to ignore counts for no class in the inter-read metrics."""
    pytest.importorskip("scipy")
    from segtrain import reads as R

    tree = _tree()
    disjoint = {name: tree == labels.LABEL_VALUES[name] for name in labels.NAMES}
    _export_tree(tmp_path, "imagecas_0004", disjoint)
    _export_tree(tmp_path, "imagecas_0004__r2",
                 dict(disjoint, LAD=disjoint["LAD"] | disjoint["LCx"]))
    with pytest.warns(UserWarning):
        cases = R.load_read_folder(str(tmp_path), sealed=set(), pool_seal="exclude")

    seen = []

    def scorer(ref, pred, spacing):
        seen.append((np.asarray(ref).copy(), np.asarray(pred).copy()))
        return {c: 1.0 for c in R.CLASSES if (np.asarray(ref) == c).any()}

    report = R.first_reads_report(cases, scorer=scorer, use_namer=False, pool_seal="exclude")
    [row] = report["cases"]
    n_lcx = int(disjoint["LCx"].sum())
    assert row["ignored_voxels"] == n_lcx
    assert row["shared_class_voxels"] == {"r2": [["LAD", "LCx", n_lcx]]}
    assert row["name_conflict_fraction"] == 0.0           # LAD-over-LCx is not a naming conflict
    for ref, pred in seen:
        assert R.IGNORE not in np.unique(ref) and R.IGNORE not in np.unique(pred)
        assert not (ref == R.LCX).any() and not (pred == R.LCX).any()   # left out of both
    assert report["wave"]["ignored_voxels_left_out"] == n_lcx
    assert report["wave"]["n_reads_with_shared_voxels"] == 1
    assert "left out of the inter-read metrics as ignore (D40): " + str(n_lcx) \
        in R.report_markdown(report)
