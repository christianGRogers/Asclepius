"""Make obliquely-acquired volumes loadable, at ingest, once.

ITK refuses any NIfTI whose direction cosines are not orthonormal to its
tolerance::

    ITK only supports orthonormal direction cosines.
    No orthonormal definition found!

``segtrain.convert`` already documents what this costs: **136 of the 1228
TotalSegmentator volumes -- 11.1% -- are obliquely acquired** and, stored as
float32, fall just outside that tolerance. Training sidesteps it by reading with
nibabel instead of SimpleITK. An annotator cannot: 3D Slicer *is* ITK, so those
cases do not open at all, and one in nine annotators would meet a case they
simply cannot work on.

The fix is a polar decomposition of the direction matrix -- the nearest
orthonormal matrix in the least-squares sense -- leaving voxel data, spacing and
origin untouched. On a real TotalSegmentator case the correction rotates the
axes by **0.007 degrees**, which is several orders of magnitude below a voxel and
far below anything that matters clinically. ITK is not being unreasonable; it is
being strict about float32 rounding that accumulated in the acquisition.

Doing it at ingest rather than in the client matters for a reason beyond
convenience: the corrected volume becomes *the* case. The annotator draws on it,
the reviewer sees it, and the training conversion reads the same file, so the
label and the image can never disagree about where the patient is.

It lives in ``segtrain`` rather than in the SegQueue plugin because it is a
property of the dataset, not of the annotation platform -- and because here it
can be tested without Girder, Mongo or a server.
"""

import os
import shutil

#: How far the direction matrix may stray from orthonormal before we rewrite it.
#: ITK's own tolerance is around 1e-6; the observed failures are at 2e-4, three
#: orders of magnitude worse. Fixing at 1e-7 leaves a wide margin, and rewriting
#: a file ITK would have accepted costs nothing but a little import time.
TOLERANCE = 1e-7


def _requireDeps():
    """Import numpy and nibabel, with an error naming what to install."""
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:  # pragma: no cover - deployment error
        raise ImportError(
            'Fixing oblique volumes needs numpy and nibabel, which ship with '
            'the Asclepius repository root:\n'
            '    pip install /path/to/Asclepius\n'
            'Or pass --no-fix-geometry to ingest without the correction, and '
            'accept that obliquely acquired cases will not open in Slicer.'
        ) from exc
    return np, nib


def directionError(affine):
    """How far a 4x4 affine's direction cosines are from orthonormal.

    Zero for an axis-aligned volume. Returns the largest absolute deviation of
    ``DᵀD`` from the identity, which is the quantity ITK is testing.
    """
    np, _ = _requireDeps()
    rotation = np.asarray(affine)[:3, :3]
    spacing = np.linalg.norm(rotation, axis=0)
    if not spacing.all():
        return float('inf')
    direction = rotation / spacing
    return float(abs(direction.T @ direction - np.eye(3)).max())


def orthonormalise(affine):
    """The nearest affine with orthonormal direction cosines.

    Polar decomposition via SVD: for the direction matrix ``D = U S Vᵀ``, the
    closest orthonormal matrix in the Frobenius sense is ``U Vᵀ``. Spacing,
    origin and voxel data are all left exactly as they were -- only the tiny
    non-orthogonality is removed.
    """
    np, _ = _requireDeps()
    affine = np.array(affine, dtype=float, copy=True)
    rotation = affine[:3, :3]
    spacing = np.linalg.norm(rotation, axis=0)
    direction = rotation / spacing
    u, _s, vt = np.linalg.svd(direction)
    affine[:3, :3] = (u @ vt) * spacing
    return affine


def needsFix(path, tolerance=TOLERANCE):
    """Whether a volume would be rejected by ITK. False if it cannot be read."""
    _np, nib = _requireDeps()
    try:
        return directionError(nib.load(path).affine) > tolerance
    except Exception:
        # Not something nibabel understands -- a .nrrd, say. Those carry their
        # geometry differently and have not shown this failure; leave them be
        # rather than rewriting a file we do not fully understand.
        return False


def rewrite(source, destination, affine):
    """Write ``source``'s voxels to ``destination`` under a corrected affine."""
    _np, nib = _requireDeps()
    image = nib.load(source)
    fixed = nib.Nifti1Image(image.dataobj, affine, image.header)
    # Keep both geometry records in step. A file whose sform and qform disagree
    # is read differently by different tools, which is a worse problem than the
    # one being fixed.
    fixed.set_sform(affine, code=int(image.header['sform_code']) or 1)
    fixed.set_qform(affine, code=int(image.header['qform_code']) or 1)
    nib.save(fixed, destination)
    return destination


def normaliseCase(volumePath, extraPaths=(), workDir=None, tolerance=TOLERANCE):
    """Correct a case's geometry if ITK would reject it.

    ``extraPaths`` are the masks that ship with the case. They get the *same*
    corrected affine rather than their own, because they are defined on the
    volume's grid and correcting them independently would let them drift apart
    from it.

    Returns ``(volumePath, {original: corrected}, fixed)`` with the original
    paths untouched when nothing needed doing.
    """
    _np, nib = _requireDeps()
    if not needsFix(volumePath, tolerance):
        return volumePath, {path: path for path in extraPaths if path}, False

    affine = orthonormalise(nib.load(volumePath).affine)
    if workDir is None:
        raise ValueError('normaliseCase needs a workDir to write corrections into')
    os.makedirs(workDir, exist_ok=True)

    fixedVolume = rewrite(volumePath, os.path.join(
        workDir, os.path.basename(volumePath)), affine)

    fixedExtras = {}
    for path in extraPaths:
        if not path:
            continue
        target = os.path.join(workDir, os.path.basename(path))
        try:
            fixedExtras[path] = rewrite(path, target, affine)
        except Exception:
            # A mask we cannot rewrite is better shipped as-is than not at all:
            # it is an aid, and the annotator can work without it.
            shutil.copy(path, target)
            fixedExtras[path] = target
    return fixedVolume, fixedExtras, True
