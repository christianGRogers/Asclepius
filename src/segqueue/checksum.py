"""SHA-256 over files, in bounded memory, on both ends of every transfer.

Requirement N3 is "no silent data loss", and silence is the operative word. A
truncated CT volume still opens in Slicer; a truncated segmentation still loads
and looks plausible; a home Wi-Fi connection that drops mid-upload produces a
file the server is perfectly happy to store. None of those announce themselves.
So every transfer is checksummed at both ends and nothing is marked done until
the two agree.

Stdlib only, and chunked -- a 300 MB volume must not be read into memory on a
laptop that is also holding the same volume open in Slicer.
"""

from __future__ import annotations

import hashlib
import os
from typing import Optional

#: 1 MiB. Large enough that the loop overhead is irrelevant, small enough to be
#: invisible in a Slicer process that is already tight on memory.
CHUNK_BYTES = 1024 * 1024


class ChecksumMismatch(RuntimeError):
    """The bytes on disk are not the bytes that were promised."""

    def __init__(self, path: str, expected: str, actual: str) -> None:
        self.path = path
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"checksum mismatch for {path}: expected {_short(expected)}, got "
            f"{_short(actual)} -- the transfer was incomplete or corrupted"
        )


def _short(digest: str) -> str:
    return digest[:12] + "..." if len(digest) > 12 else digest


def sha256_file(path, chunk_bytes: int = CHUNK_BYTES, progress=None) -> str:
    """Lowercase hex SHA-256 of a file, read in ``chunk_bytes`` pieces.

    ``progress`` is an optional ``callable(bytes_done, total_bytes)``; hashing a
    300 MB volume takes a couple of seconds, which is long enough that a frozen
    Slicer window looks like a crash.
    """
    total = os.path.getsize(path)
    digest = hashlib.sha256()
    done = 0
    with open(path, "rb") as handle:
        while True:
            block = handle.read(chunk_bytes)
            if not block:
                break
            digest.update(block)
            done += len(block)
            if progress is not None:
                progress(done, total)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Lowercase hex SHA-256 of an in-memory blob."""
    return hashlib.sha256(data).hexdigest()


def matches(expected: Optional[str], actual: Optional[str]) -> bool:
    """Case-insensitive digest comparison that tolerates a missing expectation.

    Returns True when ``expected`` is empty: a case ingested before checksums
    were recorded is not evidence of corruption, and treating it as such would
    make the queue unusable on legacy data. Anything with a stored checksum is
    checked strictly.
    """
    if not expected:
        return True
    if not actual:
        return False
    return expected.strip().lower() == actual.strip().lower()


def verify_file(path, expected: Optional[str], chunk_bytes: int = CHUNK_BYTES,
                progress=None) -> str:
    """Hash ``path`` and raise ``ChecksumMismatch`` unless it matches ``expected``.

    Returns the computed digest so a caller that had no expectation (first
    ingest) can record one from the same read.
    """
    actual = sha256_file(path, chunk_bytes=chunk_bytes, progress=progress)
    if not matches(expected, actual):
        raise ChecksumMismatch(str(path), expected or "", actual)
    return actual
