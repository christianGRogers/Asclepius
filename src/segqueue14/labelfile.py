"""The SegQueue14 submission file: every class whole, overlaps included (D39).

A submission used to be one integer label volume. A voxel of that holds one
value, so where two classes shared voxels the export kept one of them -- in
practice the last, RCA -- and an untouched seeded case (D26: every class a full
copy of the seed) came out as an all-RCA tree (#275). D39: every class is saved
in its entirety, overlaps included.

**The format (``FORMAT_CLASS_STACK``).** One gzip-compressed NRRD on the CT grid,
voxel for voxel, with a class axis: ``dimension: 4``, ``sizes: C I J K``,
``kinds: list domain domain domain``, one uint8 0/1 channel per class in label
order: the four (LM, LAD, LCx, RCA), or all 21 for a read with the extended
classes (D44, ``labels.ALL_NAMES``). ``SegQueue14_Classes`` names the channels, so
which classes a read has is in its header. The header also carries Slicer's
segmentation keys, one layer per class, so the same file is a valid Slicer
``.seg.nrrd``: Slicer opens it as named, coloured, overlapping segments. Unlike a ``.seg.nrrd`` that
Slicer writes itself, it is never cropped to the segments' extent: the grid is
the CT's. ``SegQueue14_Format`` in the header names the format, so a reader
tells it from an old single-label file by the header alone.

**Old files (``FORMAT_LABELMAP``).** Submissions from before protocol 17 are one
integer volume in the project's label values, and stay readable everywhere.

Writing and the header are stdlib only (Python 3.9, inside Slicer); the array
functions import numpy on use.
"""

from __future__ import annotations

import gzip
import io
import re
from typing import Dict, List, Optional, Sequence, Tuple

#: One uint8 0/1 channel per class, in project order (D39, protocol 17).
FORMAT_CLASS_STACK = "class-stack-nrrd/1"
#: One integer label volume in the project's values (before protocol 17).
FORMAT_LABELMAP = "labelmap"
FORMATS = (FORMAT_CLASS_STACK, FORMAT_LABELMAP)

#: The header key that names the format.
FORMAT_KEY = "SegQueue14_Format"
#: The header key that lists the classes, ``|``-separated, in channel order.
CLASSES_KEY = "SegQueue14_Classes"

_MAGIC = b"NRRD"
_HEADER_LIMIT = 1 << 16


class LabelFileError(ValueError):
    """Not a SegQueue14 label file this module can read."""


# ------------------------------------------------------------------ geometry


def ras_to_lps(ijk_to_ras) -> List[List[float]]:
    """A 4x4 IJK-to-RAS matrix (Slicer's) as IJK-to-LPS (NRRD's and ITK's)."""
    rows = [[float(ijk_to_ras[r][c]) for c in range(4)] for r in range(4)]
    for r in (0, 1):
        rows[r] = [-v for v in rows[r]]
    return rows


def _fmt(value: float) -> str:
    return repr(float(value))


def _vector(values) -> str:
    return "(" + ",".join(_fmt(v) for v in values) + ")"


# -------------------------------------------------------------------- header


def header_text(names: Sequence[str], size_ijk: Sequence[int], ijk_to_lps,
                colors: Optional[Sequence[Sequence[float]]] = None,
                encoding: str = "gzip") -> str:
    """The NRRD header for a class stack of ``names`` on the given grid.

    ``ijk_to_lps`` is a 4x4 (or 3x4) matrix whose columns 0-2 are the i, j, k
    steps in LPS millimetres and whose column 3 is the origin.
    """
    names = [str(n) for n in names]
    for name in names:
        if "|" in name or "\n" in name:
            raise ValueError(f"class name {name!r} cannot go in a header")
    size_ijk = [int(n) for n in size_ijk]
    if len(size_ijk) != 3:
        raise ValueError("size_ijk must have three entries")
    steps = [[float(ijk_to_lps[r][c]) for r in range(3)] for c in range(3)]
    origin = [float(ijk_to_lps[r][3]) for r in range(3)]
    full = f"0 {size_ijk[0] - 1} 0 {size_ijk[1] - 1} 0 {size_ijk[2] - 1}"
    lines = [
        "NRRD0004",
        "# SegQueue14 submission: one 0/1 channel per class, on the CT grid (D39)",
        "type: unsigned char",
        "dimension: 4",
        "space: left-posterior-superior",
        "sizes: {} {} {} {}".format(len(names), *size_ijk),
        "space directions: none " + " ".join(_vector(s) for s in steps),
        "kinds: list domain domain domain",
        "encoding: " + encoding,
        "space origin: " + _vector(origin),
        f"{FORMAT_KEY}:={FORMAT_CLASS_STACK}",
        f"{CLASSES_KEY}:=" + "|".join(names),
        # Slicer's segmentation keys: each class its own layer, value 1 in it.
        "Segmentation_ContainedRepresentationNames:=Binary labelmap|",
        "Segmentation_MasterRepresentation:=Binary labelmap",
        "Segmentation_SourceRepresentation:=Binary labelmap",
        "Segmentation_ReferenceImageExtentOffset:=0 0 0",
    ]
    for index, name in enumerate(names):
        colour = (colors[index] if colors is not None and index < len(colors)
                  else (0.5, 0.5, 0.5))
        lines += [
            f"Segment{index}_Color:=" + " ".join(_fmt(c) for c in list(colour)[:3]),
            f"Segment{index}_ColorAutoGenerated:=0",
            f"Segment{index}_Extent:={full}",
            f"Segment{index}_ID:={name}",
            f"Segment{index}_LabelValue:=1",
            f"Segment{index}_Layer:={index}",
            f"Segment{index}_Name:={name}",
            f"Segment{index}_NameAutoGenerated:=0",
            f"Segment{index}_Tags:=SegQueue14:class|",
        ]
    return "\n".join(lines) + "\n\n"


def _read_header_bytes(handle) -> Tuple[bytes, int]:
    """The header bytes (up to the blank line) and the offset of the data."""
    raw = handle.read(_HEADER_LIMIT)
    if not raw.startswith(_MAGIC):
        raise LabelFileError("not an NRRD file")
    end = raw.find(b"\n\n")
    if end < 0:
        raise LabelFileError("NRRD header has no end (or is too long)")
    return raw[:end], end + 2


def parse_header(raw: bytes) -> Dict[str, str]:
    """``{field: value}`` for fields and ``{key: value}`` for ``key:=value`` pairs."""
    out: Dict[str, str] = {}
    for line in raw.decode("latin-1").splitlines()[1:]:
        if not line or line.startswith("#"):
            continue
        if ":=" in line:
            key, value = line.split(":=", 1)
        elif ": " in line:
            key, value = line.split(": ", 1)
        else:
            continue
        out[key.strip()] = value.strip()
    return out


def read_header(path: str) -> Dict[str, str]:
    """The header of an NRRD file, or ``{}`` for anything that is not one."""
    try:
        with open(path, "rb") as handle:
            raw, _ = _read_header_bytes(handle)
    except (OSError, LabelFileError):
        return {}
    return parse_header(raw)


def sniff(path: str) -> str:
    """``FORMAT_CLASS_STACK`` or ``FORMAT_LABELMAP``, from the file's header.

    Decided by the bytes, not by what a client declared: anything without the
    class-stack header key -- a NIfTI, an ordinary NRRD -- is an old label volume.
    """
    header = read_header(path)
    if header.get(FORMAT_KEY) == FORMAT_CLASS_STACK:
        return FORMAT_CLASS_STACK
    return FORMAT_LABELMAP


def class_names(header: Dict[str, str]) -> List[str]:
    """The channel names of a class-stack header (``parse_header``'s dict), or []."""
    if header.get(FORMAT_KEY) != FORMAT_CLASS_STACK:
        return []
    names = [n for n in header.get(CLASSES_KEY, "").split("|") if n]
    try:
        channels = int(header.get("sizes", "").split()[0])
    except (IndexError, ValueError):
        channels = len(names)
    if len(names) != channels:
        names = [header.get(f"Segment{c}_Name", f"class{c + 1}") for c in range(channels)]
    return names


def class_names_bytes(raw: bytes) -> List[str]:
    """``class_names`` over the first bytes of a file; [] for an old label volume."""
    try:
        header, _ = _read_header_bytes(io.BytesIO(raw))
    except LabelFileError:
        return []
    return class_names(parse_header(header))


def sniff_bytes(raw: bytes) -> str:
    """``sniff`` over the first bytes of a file (its header is in the first 64 KB)."""
    try:
        header, _ = _read_header_bytes(io.BytesIO(raw))
    except LabelFileError:
        return FORMAT_LABELMAP
    if parse_header(header).get(FORMAT_KEY) == FORMAT_CLASS_STACK:
        return FORMAT_CLASS_STACK
    return FORMAT_LABELMAP


# --------------------------------------------------------------------- write


def write_class_stack(path: str, masks: Sequence, names: Sequence[str], ijk_to_lps,
                      colors: Optional[Sequence[Sequence[float]]] = None,
                      compresslevel: int = 6) -> None:
    """Write ``masks`` (one array per class, each indexed ``[k, j, i]``) to ``path``.

    Every mask must have the same shape: the CT's, so the file overlays it voxel
    for voxel. Any non-zero voxel is written as 1. The data is streamed one
    k-slice at a time, so memory stays at the masks themselves.
    """
    import numpy as np

    masks = [np.asarray(m) for m in masks]
    if len(masks) != len(names):
        raise ValueError(f"{len(masks)} masks for {len(names)} class names")
    if not masks:
        raise ValueError("a class stack needs at least one class")
    shape = masks[0].shape
    if len(shape) != 3 or any(m.shape != shape for m in masks):
        raise ValueError(f"every mask must be 3D with one shape; got "
                         f"{[m.shape for m in masks]}")
    nk, nj, ni = shape
    header = header_text(names, (ni, nj, nk), ijk_to_lps, colors)
    with open(path, "wb") as out:
        out.write(header.encode("latin-1"))
        with gzip.GzipFile(fileobj=out, mode="wb", compresslevel=compresslevel,
                           mtime=0) as gz:
            for k in range(nk):
                # (j, i, class): the class axis is the fastest in the file.
                plane = np.stack([m[k] != 0 for m in masks], axis=-1)
                gz.write(np.ascontiguousarray(plane, dtype=np.uint8).tobytes())


# ---------------------------------------------------------------------- read


def _numbers(text: str) -> List[float]:
    return [float(v) for v in text.strip().strip("()").split(",")]


def read_class_stack(path: str) -> dict:
    """Read a class-stack file without Slicer.

    Returns ``{"masks", "names", "ijk_to_lps", "spacing", "origin", "direction",
    "format"}``: ``masks`` is uint8 0/1, shaped ``(classes, k, j, i)`` -- each
    ``masks[c]`` in the same index order as a SimpleITK or Slicer array of the CT;
    ``spacing``/``origin``/``direction`` are ITK's (LPS; ``direction`` row-major
    3x3), so ``SimpleITK.GetImageFromArray(masks[c])`` plus those is the class
    on the CT's grid.
    """
    import numpy as np

    with open(path, "rb") as handle:
        raw, offset = _read_header_bytes(handle)
        header = parse_header(raw)
        handle.seek(offset)
        payload = handle.read()
    if header.get(FORMAT_KEY) != FORMAT_CLASS_STACK:
        raise LabelFileError(f"{path}: not a SegQueue14 class-stack file")
    if header.get("type") not in ("unsigned char", "uchar", "uint8", "uint8_t"):
        raise LabelFileError(f"{path}: expected unsigned char, got {header.get('type')}")
    sizes = [int(v) for v in header.get("sizes", "").split()]
    if len(sizes) != 4:
        raise LabelFileError(f"{path}: expected four sizes, got {sizes}")
    encoding = header.get("encoding", "raw")
    if encoding in ("gzip", "gz"):
        payload = gzip.GzipFile(fileobj=io.BytesIO(payload)).read()
    elif encoding != "raw":
        raise LabelFileError(f"{path}: unsupported NRRD encoding {encoding!r}")
    nc, ni, nj, nk = sizes
    expected = nc * ni * nj * nk
    if len(payload) < expected:
        raise LabelFileError(f"{path}: {len(payload)} data bytes, expected {expected}")
    data = np.frombuffer(payload[:expected], dtype=np.uint8).reshape(nk, nj, ni, nc)
    masks = np.ascontiguousarray(np.moveaxis(data, -1, 0)) != 0

    names = class_names(header)
    vectors = [_numbers(v) for v in re.findall(r"\(([^)]*)\)",
                                               header.get("space directions", ""))]
    if len(vectors) != 3:
        raise LabelFileError(f"{path}: bad space directions {header.get('space directions')!r}")
    origin = _numbers(header.get("space origin", "(0,0,0)"))
    ijk_to_lps = [[vectors[c][r] for c in range(3)] + [origin[r]] for r in range(3)]
    ijk_to_lps.append([0.0, 0.0, 0.0, 1.0])
    spacing = [float(np.linalg.norm(v)) for v in vectors]
    direction = [vectors[c][r] / spacing[c] if spacing[c] else 0.0
                 for r in range(3) for c in range(3)]
    return {
        "masks": masks.astype(np.uint8),
        "names": names,
        "ijk_to_lps": ijk_to_lps,
        "spacing": tuple(spacing),
        "origin": tuple(origin),
        "direction": tuple(direction),
        "format": FORMAT_CLASS_STACK,
    }


# ------------------------------------------------------------ class handling


def masks_from_labels(volume, n_classes: int):
    """An old single-label volume as ``(classes, ...)`` 0/1 masks (label ``c + 1``)."""
    import numpy as np

    volume = np.asarray(volume)
    return np.stack([(volume == c + 1) for c in range(n_classes)]).astype(np.uint8)


def voxel_counts(masks, names: Sequence[str]) -> Dict[str, int]:
    """``{class: voxels}``, each class counted whole, overlaps included."""
    import numpy as np

    return {name: int(np.count_nonzero(masks[c])) for c, name in enumerate(names)}


def overlaps(masks, names: Sequence[str]) -> List[Tuple[str, str, int]]:
    """``[(name, name, voxels), ...]``: every pair of classes that shares voxels."""
    import numpy as np

    out = []
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            shared = int(np.count_nonzero((masks[a] != 0) & (masks[b] != 0)))
            if shared:
                out.append((names[a], names[b], shared))
    return out
