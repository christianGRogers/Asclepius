"""Orthonormalising oblique volumes so ITK -- and therefore Slicer -- will read them.

``segtrain.convert`` records the scale of this: 136 of the 1228 TotalSegmentator
volumes are obliquely acquired and, as float32, fall just outside ITK's
orthonormality tolerance. Training reads them with nibabel and is unaffected.
An annotator cannot do that: Slicer *is* ITK, so those cases do not open at all,
and one annotator in nine would be handed a case they cannot work on.

The correction has to be conservative to be defensible. These tests pin down
exactly what it is allowed to change: the direction cosines, and nothing else.
"""

import numpy as np
import pytest

nib = pytest.importorskip("nibabel")

from segtrain import geometry  # noqa: E402

#: The real deviation measured on TotalSegmentator case s0004, which is what
#: sent an annotator a case Slicer refused to open.
OBSERVED_ERROR = 2.1e-4


def obliqueAffine(errorScale=1.0, spacing=(1.5, 1.5, 1.5)):
    """An affine with direction cosines slightly off orthonormal, as acquired."""
    tilt = np.array([
        [0.998323, -0.034807, 0.046407],
        [0.034373, 0.999386, 0.005721],
        [-0.046577, -0.004001, 0.998906],
    ])
    direction = np.eye(3) + (tilt - np.eye(3)) * errorScale
    affine = np.eye(4)
    affine[:3, :3] = direction * np.asarray(spacing)
    affine[:3, 3] = (12.5, -30.25, 7.0)
    return affine


def writeVolume(path, affine, shape=(6, 5, 4)):
    data = np.arange(np.prod(shape), dtype=np.int16).reshape(shape)
    nib.save(nib.Nifti1Image(data, affine), str(path))
    return data


# ----------------------------------------------------------------- measuring


def test_an_axis_aligned_volume_needs_nothing():
    assert geometry.directionError(np.diag([1.5, 1.5, 1.5, 1.0])) < 1e-12


def test_an_oblique_affine_is_measured_as_off():
    error = geometry.directionError(obliqueAffine())
    assert error > geometry.TOLERANCE
    # Same order of magnitude as the case that actually failed.
    assert 1e-5 < error < 1e-2


def test_a_degenerate_affine_does_not_divide_by_zero():
    affine = np.eye(4)
    affine[:3, :3] = 0.0
    assert geometry.directionError(affine) == float("inf")


# ---------------------------------------------------------------- correcting


def test_the_correction_reaches_machine_precision():
    fixed = geometry.orthonormalise(obliqueAffine())
    assert geometry.directionError(fixed) < 1e-12


def test_spacing_and_origin_are_left_exactly_alone():
    original = obliqueAffine(spacing=(0.4, 0.4, 0.5))
    fixed = geometry.orthonormalise(original)

    assert np.allclose(np.linalg.norm(fixed[:3, :3], axis=0), (0.4, 0.4, 0.5))
    assert np.array_equal(fixed[:3, 3], original[:3, 3])
    assert np.array_equal(fixed[3], original[3])


def test_the_axes_barely_move():
    """The correction must be far below a voxel, or it is not a correction.

    On the real case this was 0.007 degrees. Anything approaching a degree would
    mean the volume was genuinely oblique rather than suffering float32 rounding,
    and quietly straightening it would be falsifying the acquisition.
    """
    original = obliqueAffine()
    fixed = geometry.orthonormalise(original)

    def unit(a):
        return a[:3, :3] / np.linalg.norm(a[:3, :3], axis=0)

    cosines = (unit(original) * unit(fixed)).sum(axis=0)
    assert np.degrees(np.arccos(np.clip(cosines, -1, 1))).max() < 0.1


def test_an_already_orthonormal_affine_is_returned_unchanged():
    original = np.diag([1.5, 1.5, 1.5, 1.0])
    assert np.allclose(geometry.orthonormalise(original), original)


def test_the_input_affine_is_not_mutated():
    original = obliqueAffine()
    before = original.copy()
    geometry.orthonormalise(original)
    assert np.array_equal(original, before)


# -------------------------------------------------------------------- files


def test_an_oblique_file_is_detected_and_an_aligned_one_is_not(tmp_path):
    oblique, aligned = tmp_path / "o.nii.gz", tmp_path / "a.nii.gz"
    writeVolume(oblique, obliqueAffine())
    writeVolume(aligned, np.diag([1.5, 1.5, 1.5, 1.0]))

    assert geometry.needsFix(str(oblique))
    assert not geometry.needsFix(str(aligned))


def test_a_file_nibabel_cannot_read_is_left_alone(tmp_path):
    # A .nrrd, say. Those carry geometry differently and have not shown this
    # failure; rewriting a file we do not understand would be worse.
    path = tmp_path / "volume.nrrd"
    path.write_bytes(b"NRRD0004\n# not a NIfTI\n")
    assert not geometry.needsFix(str(path))


def test_correcting_a_case_keeps_every_voxel(tmp_path):
    source = tmp_path / "ct.nii.gz"
    original = writeVolume(source, obliqueAffine())

    fixed, extras, changed = geometry.normaliseCase(
        str(source), workDir=str(tmp_path / "work"))

    assert changed and extras == {}
    after = nib.load(fixed)
    assert np.array_equal(np.asarray(after.dataobj), original)
    assert after.get_data_dtype() == np.dtype(np.int16)
    assert geometry.directionError(after.affine) < 1e-8


def test_masks_get_the_volumes_corrected_affine_not_their_own(tmp_path):
    """Masks are defined on the volume's grid and must stay on it.

    Correcting each independently would let them drift apart from the CT by
    fractions of a degree -- invisible in a slice view, and exactly the sort of
    thing that turns up as an unexplained Dice ceiling months later.
    """
    source = tmp_path / "ct.nii.gz"
    heart = tmp_path / "heart.nii.gz"
    writeVolume(source, obliqueAffine())
    writeVolume(heart, obliqueAffine(errorScale=0.5))  # subtly different

    fixed, extras, changed = geometry.normaliseCase(
        str(source), [str(heart)], workDir=str(tmp_path / "work"))

    assert changed
    assert np.allclose(nib.load(fixed).affine, nib.load(extras[str(heart)]).affine)


def test_an_aligned_case_is_passed_through_untouched(tmp_path):
    source = tmp_path / "ct.nii.gz"
    heart = tmp_path / "heart.nii.gz"
    writeVolume(source, np.diag([1.5, 1.5, 1.5, 1.0]))
    writeVolume(heart, np.diag([1.5, 1.5, 1.5, 1.0]))

    fixed, extras, changed = geometry.normaliseCase(
        str(source), [str(heart)], workDir=str(tmp_path / "work"))

    assert not changed
    assert fixed == str(source)
    assert extras == {str(heart): str(heart)}
    assert not (tmp_path / "work").exists()


def test_the_sform_and_qform_agree_after_correction(tmp_path):
    # A file whose two geometry records disagree is read differently by
    # different tools, which is a worse problem than the one being fixed.
    source = tmp_path / "ct.nii.gz"
    writeVolume(source, obliqueAffine())

    fixed, _extras, _changed = geometry.normaliseCase(
        str(source), workDir=str(tmp_path / "work"))

    image = nib.load(fixed)
    assert np.allclose(image.get_sform(), image.get_qform(), atol=1e-5)
    assert geometry.directionError(image.get_sform()) < 1e-8
