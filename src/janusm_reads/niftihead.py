"""A CT's world bounding box from its NIfTI header alone (JA67: a lesion point outside
the CT is refused). Stdlib only, so the web server needs neither numpy nor nibabel,
and only the header's first bytes are read, never the volume.

The affine is the one nibabel's ``get_best_affine`` gives: the sform when its code is
set, else the qform, else the voxel sizes (centred, x flipped, as nibabel's base affine).
World coordinates are NIfTI's RAS millimetres, which Slicer also shows.
"""

from __future__ import annotations

import math
import struct
import zlib
from typing import Dict, List, Optional, Sequence, Tuple

#: Enough leading bytes of a stored file to hold either header, compressed or not.
HEADER_READ_BYTES = 1 << 16

Bounds = Tuple[List[float], List[float]]


def header_bytes(raw: bytes) -> bytes:
    """The leading bytes of a NIfTI file, gunzipped if they are gzip."""
    if raw[:2] == b"\x1f\x8b":
        try:
            return zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(raw, 4096)
        except zlib.error:
            return b""
    return raw


def _layout(raw: bytes):
    """``(version, byte order)`` of a NIfTI header, or None."""
    for order in "<>":
        if len(raw) >= 4:
            size = struct.unpack(order + "i", raw[:4])[0]
            if size == 348 and len(raw) >= 348:
                return 1, order
            if size == 540 and len(raw) >= 540:
                return 2, order
    return None


def _quaternion_affine(b, c, d, qx, qy, qz, pix, qfac):
    a = math.sqrt(max(0.0, 1.0 - (b * b + c * c + d * d)))
    rot = [[a * a + b * b - c * c - d * d, 2 * (b * c - a * d), 2 * (b * d + a * c)],
           [2 * (b * c + a * d), a * a + c * c - b * b - d * d, 2 * (c * d - a * b)],
           [2 * (b * d - a * c), 2 * (c * d + a * b), a * a + d * d - c * c - b * b]]
    scale = [pix[0], pix[1], pix[2] * (-1.0 if qfac < 0 else 1.0)]
    return [[rot[r][k] * scale[k] for k in range(3)] + [(qx, qy, qz)[r]] for r in range(3)]


def affine_and_shape(raw: bytes):
    """``(3x4 affine rows, (nx, ny, nz))`` from a NIfTI-1 or NIfTI-2 header, or None."""
    raw = header_bytes(raw)
    found = _layout(raw)
    if found is None:
        return None
    version, o = found
    if version == 1:
        dim = struct.unpack(o + "8h", raw[40:56])
        pix = struct.unpack(o + "8f", raw[76:108])
        qcode, scode = struct.unpack(o + "2h", raw[252:256])
        quat = struct.unpack(o + "6f", raw[256:280])
        srow = [struct.unpack(o + "4f", raw[280 + 16 * r:296 + 16 * r]) for r in range(3)]
    else:
        dim = struct.unpack(o + "8q", raw[16:80])
        pix = struct.unpack(o + "8d", raw[104:168])
        qcode, scode = struct.unpack(o + "2i", raw[344:352])
        quat = struct.unpack(o + "6d", raw[352:400])
        srow = [struct.unpack(o + "4d", raw[400 + 32 * r:432 + 32 * r]) for r in range(3)]
    shape = tuple(int(n) for n in dim[1:4])
    if dim[0] < 3 or min(shape) < 1:
        return None
    if scode > 0:
        rows = [list(map(float, r)) for r in srow]
    elif qcode > 0:
        rows = _quaternion_affine(*quat, pix=pix[1:4], qfac=pix[0])
    else:
        # nibabel's base affine: x flipped (LAS), centred on the volume.
        size = [abs(float(p)) or 1.0 for p in pix[1:4]]
        size[0] = -size[0]
        rows = [[size[r] if k == r else 0.0 for k in range(3)]
                + [-size[r] * (shape[r] - 1) / 2.0] for r in range(3)]
    return rows, shape


def world_bounds(raw: bytes) -> Optional[Bounds]:
    """``(lo, hi)``: the CT's world box (RAS mm), voxel edges included; None when
    ``raw`` does not start with a NIfTI header."""
    found = affine_and_shape(raw)
    if found is None:
        return None
    rows, shape = found
    corners = [(i, j, k) for i in (-0.5, shape[0] - 0.5) for j in (-0.5, shape[1] - 0.5)
               for k in (-0.5, shape[2] - 0.5)]
    world = [[sum(rows[r][a] * p[a] for a in range(3)) + rows[r][3] for r in range(3)]
             for p in corners]
    return ([min(w[r] for w in world) for r in range(3)],
            [max(w[r] for w in world) for r in range(3)])


def contains(bounds: Optional[Sequence[Sequence[float]]], point: Sequence[float],
             tolerance_mm: float = 1.0) -> bool:
    """Whether ``point`` (RAS mm) is inside ``bounds`` widened by ``tolerance_mm``."""
    lo, hi = bounds
    return all(float(lo[k]) - tolerance_mm <= float(point[k]) <= float(hi[k]) + tolerance_mm
               for k in range(3))


def points_outside(lesion_points: Optional[Dict[str, Sequence[float]]],
                   bounds: Optional[Sequence[Sequence[float]]],
                   tolerance_mm: float = 1.0) -> List[str]:
    """JA67: one message per lesion point (world mm, RAS) outside the CT's world box
    ``bounds`` widened by ``tolerance_mm``; empty when every point is inside, or when
    there is no box to check against."""
    if not bounds:
        return []
    out = []
    for vessel, point in sorted((lesion_points or {}).items()):
        try:
            inside = len(point) == 3 and contains(bounds, point, tolerance_mm)
        except (TypeError, ValueError):
            inside = False
        if not inside:
            out.append(f"{vessel}: the lesion point is outside the CT.")
    return out
