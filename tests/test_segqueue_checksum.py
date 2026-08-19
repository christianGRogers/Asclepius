"""Transfer verification -- requirement N3, "no silent data loss"."""

import hashlib

import pytest

from segqueue.checksum import (
    ChecksumMismatch,
    matches,
    sha256_bytes,
    sha256_file,
    verify_file,
)


@pytest.fixture
def volume(tmp_path):
    """Several chunks' worth, so the streaming loop is actually exercised."""
    path = tmp_path / "ct.nrrd"
    payload = (b"NRRD0004\n" + bytes(range(256)) * 4096)
    path.write_bytes(payload)
    return path, hashlib.sha256(payload).hexdigest()


def test_file_digest_matches_hashlib(volume):
    path, expected = volume
    assert sha256_file(path) == expected


def test_chunking_does_not_change_the_digest(volume):
    path, expected = volume
    assert sha256_file(path, chunk_bytes=7) == expected
    assert sha256_file(path, chunk_bytes=10**9) == expected


def test_progress_is_reported_and_ends_at_the_total(volume):
    path, _ = volume
    seen = []
    sha256_file(path, chunk_bytes=1024, progress=lambda done, total: seen.append((done, total)))
    assert seen
    assert seen[-1][0] == seen[-1][1] == path.stat().st_size
    assert [d for d, _ in seen] == sorted(d for d, _ in seen)


def test_an_empty_file_still_hashes(tmp_path):
    path = tmp_path / "empty"
    path.write_bytes(b"")
    assert sha256_file(path) == hashlib.sha256(b"").hexdigest()


def test_bytes_and_file_agree(tmp_path):
    path = tmp_path / "x"
    path.write_bytes(b"abc")
    assert sha256_bytes(b"abc") == sha256_file(path)


def test_verify_returns_the_digest_it_computed(volume):
    path, expected = volume
    assert verify_file(path, expected) == expected


def test_a_truncated_transfer_is_caught(volume, tmp_path):
    _, expected = volume
    truncated = tmp_path / "partial.nrrd"
    truncated.write_bytes(b"NRRD0004\n")
    with pytest.raises(ChecksumMismatch) as excinfo:
        verify_file(truncated, expected)
    assert "incomplete or corrupted" in str(excinfo.value)
    assert excinfo.value.expected == expected


def test_comparison_is_case_insensitive_and_whitespace_tolerant():
    digest = sha256_bytes(b"x")
    assert matches(digest.upper(), digest)
    assert matches("  " + digest + "\n", digest)


def test_no_recorded_checksum_is_not_evidence_of_corruption():
    """Cases ingested before checksums existed must stay usable."""
    assert matches(None, sha256_bytes(b"x"))
    assert matches("", sha256_bytes(b"x"))


def test_a_recorded_checksum_against_nothing_fails():
    assert not matches(sha256_bytes(b"x"), "")
    assert not matches(sha256_bytes(b"x"), None)


def test_first_ingest_can_record_a_checksum_from_the_same_read(volume):
    path, expected = volume
    assert verify_file(path, None) == expected
