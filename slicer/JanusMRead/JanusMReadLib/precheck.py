"""The checks the reader module runs before anything is uploaded, free of Slicer.

Two only, from the issue (#156): every value is 0-4 and all four JA1 classes are
present -- plus refusing classes that overlap, because a voxel can carry only one
value in the submitted file. The server's automatic check (half-maximum offsets,
label conventions) is the authority; these exist so a reader is told at once, not
after an upload.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping

from janusm_reads import labels as L


def voxel_counts(values) -> Dict[int, int]:
    """``{label value: voxels}`` for every non-zero value in an array of labels."""
    import numpy as np

    found, counts = np.unique(np.asarray(values), return_counts=True)
    return {int(v): int(n) for v, n in zip(found, counts) if int(v) != L.BACKGROUND}


def problems(present_values: Iterable[int], counts: Mapping[int, int],
             overlapping_voxels: int = 0) -> List[str]:
    """What stops this read being uploaded, in words; empty when it may be."""
    out = []
    bad = L.invalid_values(present_values)
    if bad:
        out.append("The read holds label values outside 0-4 ({}). Only the four "
                   "Janus-M classes may be submitted.".format(", ".join(map(str, bad))))
    if overlapping_voxels:
        out.append("{} voxels are in more than one class. Each voxel is one class: "
                   "remove the overlap, then submit.".format(int(overlapping_voxels)))
    missing = L.missing_required(counts)
    if missing:
        out.append(L.missing_message(missing))
    return out


def sniff_suffix(path: str) -> str:
    """The file suffix Slicer needs to read a downloaded volume, from its bytes.

    The read queue serves the CT under the read's route, not under a filename, and
    ImageCAS-X CTs are NIfTI (gzipped or not), NRRD or MetaImage.
    """
    with open(path, "rb") as handle:
        head = handle.read(352)
    if head[:2] == b"\x1f\x8b":
        return ".nii.gz"
    if head[:4] == b"NRRD":
        return ".nrrd"
    if head[:10] in (b"ObjectType", b"NDims = 3\n") or b"ElementDataFile" in head:
        return ".mha"
    if len(head) >= 348 and head[344:347] in (b"n+1", b"ni1"):
        return ".nii"
    return ".nii.gz"
