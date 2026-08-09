"""Mask merging: the step where 117 files become one label volume."""

import nibabel as nib
import numpy as np
import pytest

from segtrain.convert import (
    OVERLAP_LABEL_ORDER,
    OVERLAP_SMALLER_WINS,
    geometry_offset_mm,
    link_or_copy,
    merge_masks,
    resolve_overlap,
)

IDENTITY = np.diag([1.5, 1.5, 1.5, 1.0])


def _write(path, array, affine=IDENTITY):
    img = nib.Nifti1Image(array.astype(np.uint8), affine)
    nib.save(img, str(path))


def _reference(shape=(8, 8, 8), affine=IDENTITY):
    return nib.Nifti1Image(np.zeros(shape, dtype=np.int16), affine)


# -- geometry ----------------------------------------------------------------


def test_identical_affines_have_zero_offset():
    assert geometry_offset_mm(IDENTITY, IDENTITY, (10, 10, 10)) == 0.0


def test_float32_rounding_is_far_below_a_voxel():
    """The real failure mode: obliquely-acquired volumes with float32 headers.

    Element-wise tolerances flagged these as mismatches and dropped the masks.
    """
    perturbed = IDENTITY.copy()
    perturbed[0, 1] += 1.1e-4
    perturbed[1, 0] -= 1.1e-4
    offset = geometry_offset_mm(IDENTITY, perturbed, (217, 168, 217))
    assert offset < 0.15, offset  # 0.1 voxel at 1.5 mm


def test_a_real_shift_is_detected():
    shifted = IDENTITY.copy()
    shifted[0, 3] += 5.0
    assert geometry_offset_mm(IDENTITY, shifted, (10, 10, 10)) == pytest.approx(5.0)


# -- overlap resolution ------------------------------------------------------


def test_no_overlap_assigns_directly():
    out = np.zeros((4, 4, 4), dtype=np.uint8)
    mask = np.zeros((4, 4, 4), dtype=bool)
    mask[0] = True
    assert resolve_overlap(out, mask, 1, {1: int(mask.sum())}, OVERLAP_SMALLER_WINS) == 0
    assert (out[0] == 1).all()


def test_smaller_structure_wins_contested_voxels():
    """A thin structure must not be eroded by a bulky neighbour it abuts."""
    out = np.zeros((4, 4, 4), dtype=np.uint8)
    big = np.zeros((4, 4, 4), dtype=bool)
    big[:, :, :] = True          # 64 voxels
    small = np.zeros((4, 4, 4), dtype=bool)
    small[0, 0, :] = True        # 4 voxels

    sizes = {1: int(big.sum())}
    resolve_overlap(out, big, 1, sizes, OVERLAP_SMALLER_WINS)
    sizes[2] = int(small.sum())
    n = resolve_overlap(out, small, 2, sizes, OVERLAP_SMALLER_WINS)

    assert n == 4
    assert (out[0, 0, :] == 2).all(), "small structure should own the contested voxels"
    assert out[1, 1, 1] == 1, "uncontested voxels stay with the large structure"


def test_larger_structure_does_not_steal_from_smaller():
    out = np.zeros((4, 4, 4), dtype=np.uint8)
    small = np.zeros((4, 4, 4), dtype=bool)
    small[0, 0, :] = True
    big = np.ones((4, 4, 4), dtype=bool)

    sizes = {1: int(small.sum())}
    resolve_overlap(out, small, 1, sizes, OVERLAP_SMALLER_WINS)
    sizes[2] = int(big.sum())
    resolve_overlap(out, big, 2, sizes, OVERLAP_SMALLER_WINS)

    assert (out[0, 0, :] == 1).all()


def test_label_order_policy_lets_the_later_index_win():
    out = np.zeros((4, 4, 4), dtype=np.uint8)
    small = np.zeros((4, 4, 4), dtype=bool)
    small[0, 0, :] = True
    big = np.ones((4, 4, 4), dtype=bool)

    sizes = {1: int(small.sum())}
    resolve_overlap(out, small, 1, sizes, OVERLAP_LABEL_ORDER)
    sizes[2] = int(big.sum())
    resolve_overlap(out, big, 2, sizes, OVERLAP_LABEL_ORDER)

    assert (out == 2).all()


# -- merging -----------------------------------------------------------------


def test_merge_round_trips_every_structure(tmp_path):
    """Splitting the merged volume must reproduce each input mask exactly."""
    names = ["alpha", "beta", "gamma"]
    masks = {}
    for i, name in enumerate(names):
        m = np.zeros((8, 8, 8), dtype=bool)
        m[i * 2:i * 2 + 2] = True
        masks[name] = m
        _write(tmp_path / (name + ".nii.gz"), m)

    labels, missing, overlaps, mismatch = merge_masks(tmp_path, names, _reference())

    assert missing == [] and overlaps == 0 and mismatch == []
    for i, name in enumerate(names, start=1):
        assert np.array_equal(labels == i, masks[name]), name


def test_absent_structure_is_reported_not_fatal(tmp_path):
    _write(tmp_path / "alpha.nii.gz", np.ones((8, 8, 8), dtype=bool))
    labels, missing, _, _ = merge_masks(tmp_path, ["alpha", "absent"], _reference())
    assert missing == ["absent"]
    assert labels.max() == 1


def test_empty_mask_contributes_nothing(tmp_path):
    _write(tmp_path / "alpha.nii.gz", np.zeros((8, 8, 8), dtype=bool))
    labels, missing, _, _ = merge_masks(tmp_path, ["alpha"], _reference())
    assert missing == [] and labels.max() == 0


def test_wrong_shape_is_dropped_and_reported(tmp_path):
    _write(tmp_path / "alpha.nii.gz", np.ones((4, 4, 4), dtype=bool))
    labels, _, _, mismatch = merge_masks(tmp_path, ["alpha"], _reference((8, 8, 8)))
    assert len(mismatch) == 1 and "shape" in mismatch[0]
    assert labels.max() == 0


def test_tiny_affine_noise_does_not_drop_a_mask(tmp_path):
    noisy = IDENTITY.copy()
    noisy[0, 1] += 1.1e-4
    _write(tmp_path / "alpha.nii.gz", np.ones((8, 8, 8), dtype=bool), affine=noisy)
    labels, _, _, mismatch = merge_masks(tmp_path, ["alpha"], _reference())
    assert mismatch == [], mismatch
    assert labels.max() == 1


def test_output_dtype_is_uint8(tmp_path):
    _write(tmp_path / "alpha.nii.gz", np.ones((8, 8, 8), dtype=bool))
    labels, _, _, _ = merge_masks(tmp_path, ["alpha"], _reference())
    assert labels.dtype == np.uint8


# -- linking -----------------------------------------------------------------


def test_link_or_copy_creates_a_readable_file(tmp_path):
    src = tmp_path / "src.bin"
    src.write_bytes(b"payload")
    mode = link_or_copy(src, tmp_path / "out" / "dst.bin", "hardlink")
    assert mode in ("hardlink", "symlink", "copy")
    assert (tmp_path / "out" / "dst.bin").read_bytes() == b"payload"


def test_link_or_copy_is_idempotent(tmp_path):
    src = tmp_path / "src.bin"
    src.write_bytes(b"x")
    dst = tmp_path / "dst.bin"
    link_or_copy(src, dst, "copy")
    assert link_or_copy(src, dst, "copy") == "exists"


def test_copy_mode_always_works(tmp_path):
    src = tmp_path / "src.bin"
    src.write_bytes(b"x")
    assert link_or_copy(src, tmp_path / "d.bin", "copy") == "copy"


# -- against the real dataset ------------------------------------------------


@pytest.mark.needs_data
@pytest.mark.slow
def test_real_case_merges_and_splits_back(cfg, sample_case):
    """End-to-end on real data: no structure is lost by the merge.

    Overlapping voxels legitimately change owner, so agreement is asserted away
    from the contested set rather than everywhere.
    """
    from segtrain.config import load_label_set

    labels_cfg = load_label_set("all117")
    seg_dir = cfg.zenodo_root / sample_case / "segmentations"
    ct = nib.load(str(cfg.zenodo_root / sample_case / "ct.nii.gz"))

    merged, missing, overlaps, mismatch = merge_masks(seg_dir, labels_cfg.names, ct)

    assert missing == [] and mismatch == []
    assert merged.shape == ct.shape

    contested = np.zeros(ct.shape, dtype=np.uint8)
    seen = np.zeros(ct.shape, dtype=bool)
    for name in labels_cfg.names:
        m = np.asanyarray(nib.load(str(seg_dir / (name + ".nii.gz"))).dataobj) > 0
        contested |= (m & seen)
        seen |= m

    for name in labels_cfg.names:
        index = labels_cfg.index_of(name)
        original = np.asanyarray(nib.load(str(seg_dir / (name + ".nii.gz"))).dataobj) > 0
        if not original.any():
            continue
        uncontested = original & ~contested.astype(bool)
        assert (merged[uncontested] == index).all(), name
