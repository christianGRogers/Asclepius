"""Just enough NIfTI-1 to check a prelabel before it is attached. Stdlib only.

The prelabel tool runs on the server, where the CT for each case is already in
Girder's assetstore. Comparing grid sizes needs only the 348-byte header of each
file, which for a gzipped NIfTI is the first few kilobytes of the stream -- so the
check costs a few kilobytes per case rather than a 110 GB read, and it needs no
numpy, nibabel or SimpleITK on the web server.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

HEADER_BYTES = 348

#: NIfTI datatype codes we care to name.
DT_UINT8 = 2
DT_INT16 = 4
DT_INT32 = 8
DT_FLOAT32 = 16
DT_INT8 = 256
DT_UINT16 = 512
_DT_NAMES = {DT_UINT8: "uint8", DT_INT16: "int16", DT_INT32: "int32",
             DT_FLOAT32: "float32", 64: "float64", DT_INT8: "int8",
             DT_UINT16: "uint16", 768: "uint32"}


class NiftiError(ValueError):
    """Not a NIfTI-1 file we can read."""


@dataclass(frozen=True)
class NiftiHeader:
    """The fields of a NIfTI-1 header the prelabel checks read; nothing else."""

    dims: Tuple[int, ...]
    datatype: int
    bitpix: int
    pixdim: Tuple[float, ...]
    vox_offset: float
    little_endian: bool

    @property
    def dtype_name(self) -> str:
        return _DT_NAMES.get(self.datatype, f"code {self.datatype}")

    @property
    def shape3(self) -> Tuple[int, ...]:
        return tuple(self.dims[:3])

    @property
    def spacing3(self) -> Tuple[float, ...]:
        return tuple(self.pixdim[:3])


def parse_header(raw: bytes) -> NiftiHeader:
    """Parse an uncompressed NIfTI-1 header (the first 348 bytes)."""
    if len(raw) < HEADER_BYTES:
        raise NiftiError(f"only {len(raw)} bytes; a NIfTI-1 header is {HEADER_BYTES}")
    if struct.unpack("<i", raw[0:4])[0] == HEADER_BYTES:
        order, little = "<", True
    elif struct.unpack(">i", raw[0:4])[0] == HEADER_BYTES:
        order, little = ">", False
    else:
        raise NiftiError("not a NIfTI-1 header (sizeof_hdr is not 348)")
    magic = raw[344:348]
    if magic not in (b"n+1\x00", b"ni1\x00"):
        raise NiftiError(f"bad NIfTI magic {magic!r}")
    dim = struct.unpack(order + "8h", raw[40:56])
    ndim = dim[0]
    if not 1 <= ndim <= 7:
        raise NiftiError(f"bad dimension count {ndim}")
    datatype, bitpix = struct.unpack(order + "hh", raw[70:74])
    pixdim = struct.unpack(order + "8f", raw[76:108])
    (vox_offset,) = struct.unpack(order + "f", raw[108:112])
    return NiftiHeader(
        dims=tuple(int(d) for d in dim[1:1 + ndim]),
        datatype=int(datatype), bitpix=int(bitpix),
        pixdim=tuple(round(float(p), 6) for p in pixdim[1:1 + ndim]),
        vox_offset=float(vox_offset), little_endian=little)


def header_from_chunks(chunks: Iterable[bytes], limit: int = 1 << 20) -> NiftiHeader:
    """Read the header from a (possibly gzipped) byte stream, stopping early.

    ``chunks`` is any iterable of ``bytes`` -- a Girder download generator, a file
    read in blocks. At most ``limit`` compressed bytes are consumed.
    """
    out = b""
    decomp = None
    started = False
    consumed = 0
    for chunk in chunks:
        if not chunk:
            continue
        consumed += len(chunk)
        if not started:
            started = True
            if chunk[:2] == b"\x1f\x8b":
                decomp = zlib.decompressobj(16 + zlib.MAX_WBITS)
        if decomp is not None:
            # Bounded output: a label volume is mostly zeros and a megabyte of
            # it can inflate to a hundred, of which we want 348 bytes.
            pending = decomp.unconsumed_tail + chunk
            while pending and len(out) < HEADER_BYTES:
                out += decomp.decompress(pending, HEADER_BYTES)
                pending = decomp.unconsumed_tail
                if decomp.eof:
                    break
        else:
            out += chunk
        if len(out) >= HEADER_BYTES or consumed >= limit:
            break
    return parse_header(out[:HEADER_BYTES])


def header_from_path(path: str) -> NiftiHeader:
    """``header_from_chunks`` over a file on disk, gzipped or not."""
    def blocks():
        with open(path, "rb") as handle:
            while True:
                block = handle.read(65536)
                if not block:
                    return
                yield block
    return header_from_chunks(blocks())


def same_grid(a: NiftiHeader, b: NiftiHeader, spacing_tol: float = 1e-3) -> Optional[str]:
    """None when ``a`` and ``b`` share a voxel grid, else what differs."""
    if a.shape3 != b.shape3:
        return f"shape {a.shape3} != {b.shape3}"
    for x, y in zip(a.spacing3, b.spacing3):
        if abs(abs(x) - abs(y)) > spacing_tol * max(1.0, abs(y)):
            return f"spacing {a.spacing3} != {b.spacing3}"
    return None


def check_prelabel_header(header: NiftiHeader) -> Optional[str]:
    """None for a header a prelabel (uint8 labels, one 3D volume) can have, else the problem."""
    if len(header.dims) != 3 and not (len(header.dims) == 4 and header.dims[3] == 1):
        return f"expected a 3D volume, got dims {header.dims}"
    if header.datatype != DT_UINT8:
        return f"expected uint8 labels, got {header.dtype_name}"
    return None
