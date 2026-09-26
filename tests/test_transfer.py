"""The transfer, tested for the things that go wrong over hours and networks.

No ssh here. Everything interesting about this stage is *which* files it decides
to move, what it does when that fails, and whether it can tell "the command
exited 0" from "the training data is correct" -- and none of that needs a network
to exercise. `RsyncTransport` gets its own tests for the command it builds, with
the subprocess boundary injected.
"""

import json

import pytest

from segqueue.manifest import FULL, MANIFEST_NAME, QUICK, Manifest, build
from segtrain.transfer import (
    PARTIAL_DIR,
    RECEIPT_NAME,
    LocalTransport,
    RsyncTransport,
    TransferError,
    Transport,
    advise_destination,
    advise_host,
    pull,
)


def _case(root, name, ct=b"ct-bytes"):
    directory = root / name
    (directory / "segmentations").mkdir(parents=True, exist_ok=True)
    (directory / "ct.nii.gz").write_bytes(ct)
    (directory / "segmentations" / "left_main.nii.gz").write_bytes(b"lm")
    return directory


def _export(root, names=("1", "2", "10")):
    """A source tree with a manifest, as `segqueue-export` leaves it."""
    root.mkdir(parents=True, exist_ok=True)
    for name in names:
        _case(root, name)
    build(root, source={"kind": "segqueue-export"}).write(root)
    return root


@pytest.fixture
def source(tmp_path):
    return _export(tmp_path / "src")


@pytest.fixture
def destination(tmp_path):
    return tmp_path / "scratch" / "coronary"


# -- the happy path -------------------------------------------------------


def test_a_clean_pull_verifies_and_reports(source, destination):
    report = pull(LocalTransport(str(source)), destination, sleep=lambda _: None)

    assert report.ok
    assert report.totals == {"cases": 3, "files": 6, "bytes": 30}
    assert len(report.transferred) == 6
    assert report.already_present == 0
    assert report.attempts == 1
    assert report.verified.mode == FULL


def test_the_manifest_arrives_before_anything_is_planned(source, destination):
    pull(LocalTransport(str(source)), destination, sleep=lambda _: None)

    assert (destination / MANIFEST_NAME).exists()
    assert Manifest.read(destination).totals["cases"] == 3


def test_re_running_transfers_nothing(source, destination):
    pull(LocalTransport(str(source)), destination, sleep=lambda _: None)

    again = pull(LocalTransport(str(source)), destination, sleep=lambda _: None)

    assert again.ok
    assert again.transferred == []
    assert again.already_present == 6
    assert again.attempts == 0, "no attempt is needed when nothing is outstanding"


def test_a_receipt_records_what_the_data_was_built_from(source, destination):
    report = pull(LocalTransport(str(source)), destination, sleep=lambda _: None)
    report.write(destination)

    receipt = json.loads((destination / RECEIPT_NAME).read_text(encoding="utf-8"))

    assert receipt["ok"] is True
    assert receipt["manifest"]["totals"]["cases"] == 3
    assert receipt["manifest"]["source"] == {"kind": "segqueue-export"}
    assert receipt["verification"]["broken_cases"] == []


def test_the_receipt_is_not_mistaken_for_training_data(source, destination):
    report = pull(LocalTransport(str(source)), destination, sleep=lambda _: None)
    report.write(destination)

    after = pull(LocalTransport(str(source)), destination, sleep=lambda _: None)

    assert after.verified.extra == [], "the receipt and manifest are ours, not extras"


# -- resuming -------------------------------------------------------------


def test_only_the_missing_files_move(source, destination):
    pull(LocalTransport(str(source)), destination, sleep=lambda _: None)
    (destination / "2" / "ct.nii.gz").unlink()

    report = pull(LocalTransport(str(source)), destination, sleep=lambda _: None)

    assert report.transferred == ["2/ct.nii.gz"]
    assert report.already_present == 5


def test_a_truncated_file_is_re_fetched_not_kept(source, destination):
    pull(LocalTransport(str(source)), destination, sleep=lambda _: None)
    (destination / "1" / "ct.nii.gz").write_bytes(b"cut")

    report = pull(LocalTransport(str(source)), destination, sleep=lambda _: None)

    assert report.transferred == ["1/ct.nii.gz"]
    assert report.ok
    assert (destination / "1" / "ct.nii.gz").read_bytes() == b"ct-bytes"


class _FlakyTransport(Transport):
    """Fails the first ``failures`` fetches, moving some of the list each time."""

    def __init__(self, source, failures, per_attempt=2):
        self.inner = LocalTransport(str(source))
        self.failures = failures
        self.per_attempt = per_attempt
        self.calls = []

    def fetch_manifest(self, destination):
        return self.inner.fetch_manifest(destination)

    def fetch(self, destination, paths):
        self.calls.append(list(paths))
        if self.failures > 0:
            self.failures -= 1
            self.inner.fetch(destination, list(paths)[: self.per_attempt])
            raise TransferError("connection reset by peer")
        self.inner.fetch(destination, paths)


def test_a_dropped_connection_is_retried_and_the_retry_is_smaller(source, destination):
    transport = _FlakyTransport(source, failures=2)
    slept = []

    report = pull(transport, destination, sleep=slept.append)

    assert report.ok
    assert report.attempts == 3
    sizes = [len(call) for call in transport.calls]
    assert sizes == sorted(sizes, reverse=True), "each retry must be strictly less work"
    assert sizes[0] > sizes[-1]


def test_retries_back_off(source, destination):
    slept = []

    pull(_FlakyTransport(source, failures=2), destination, backoff=5.0, sleep=slept.append)

    assert slept == [5.0, 10.0]


def test_giving_up_says_how_much_is_left_and_why(source, destination):
    # One file per attempt, three attempts, six files: it cannot finish.
    with pytest.raises(TransferError, match=r"3 file\(s\) still missing after 3 attempt"):
        pull(_FlakyTransport(source, failures=99, per_attempt=1), destination,
             attempts=3, sleep=lambda _: None)


def test_a_transport_that_errors_after_delivering_everything_is_a_success(source, destination):
    """What matters is whether the data is there, not how the command felt.

    rsync exits non-zero for a vanished source file or a partial attribute set
    even when every byte arrived. Failing the run then would mean re-transferring
    a complete dataset to satisfy an exit code.
    """
    report = pull(_FlakyTransport(source, failures=99, per_attempt=6), destination,
                  attempts=3, sleep=lambda _: None)

    assert report.ok
    assert report.attempts == 1


def test_a_transport_that_succeeds_without_moving_anything_fails_fast(destination, tmp_path):
    """rsync exits 0 happily when asked for paths the source does not have."""
    source = _export(tmp_path / "src")

    class _Liar(LocalTransport):
        def fetch(self, destination, paths):
            return None  # "success"

    with pytest.raises(TransferError, match="moved none of the"):
        pull(_Liar(str(source)), destination, sleep=lambda _: None)


# -- verification is separate from transport success ----------------------


def test_corruption_survives_the_transport_and_is_caught_by_verification(destination, tmp_path):
    source = _export(tmp_path / "src")

    class _Corrupting(LocalTransport):
        def fetch(self, destination, paths):
            super().fetch(destination, paths)
            import os
            target = os.path.join(destination, "1", "ct.nii.gz")
            if os.path.exists(target):
                with open(target, "wb") as handle:
                    handle.write(b"CT-BYTES")  # same length, wrong bytes

    report = pull(_Corrupting(str(source)), destination, sleep=lambda _: None)

    assert not report.ok, "the transport succeeded; the data is still wrong"
    assert report.verified.corrupt == ["1/ct.nii.gz"]
    assert report.verified.broken_cases == ["1"]


def test_quick_mode_is_available_but_says_what_it_did_not_check(source, destination):
    report = pull(LocalTransport(str(source)), destination, mode=QUICK,
                  sleep=lambda _: None)

    assert report.ok
    assert "sizes only" in report.verified.summary()


def test_a_source_with_no_manifest_is_refused(destination, tmp_path):
    bare = tmp_path / "bare"
    _case(bare, "1")

    with pytest.raises(TransferError, match="not at the source: manifest.json"):
        pull(LocalTransport(str(bare)), destination, sleep=lambda _: None)


def test_an_unparseable_manifest_is_a_transfer_error_not_a_crash(destination, tmp_path):
    source = _export(tmp_path / "src")
    (source / MANIFEST_NAME).write_text("{not json", encoding="utf-8")

    with pytest.raises(TransferError, match="not valid JSON"):
        pull(LocalTransport(str(source)), destination, sleep=lambda _: None)


# -- the rsync command ----------------------------------------------------


def _capture():
    seen = []

    def runner(command):
        seen.append(list(command))
        return 0

    return seen, runner


def test_rsync_quarantines_partial_files_rather_than_leaving_them_in_the_tree(tmp_path):
    seen, runner = _capture()
    transport = RsyncTransport(remote="host:/srv/export", runner=runner)

    with pytest.raises(TransferError):  # no manifest actually lands
        transport.fetch_manifest(str(tmp_path))

    assert "--partial-dir=" + PARTIAL_DIR in seen[0]


def test_rsync_resumes_with_verification_not_assumption(tmp_path):
    seen, runner = _capture()
    RsyncTransport(remote="host:/srv/export", runner=runner).fetch(
        str(tmp_path), ["1/ct.nii.gz"])

    assert "--append-verify" in seen[0], "a resumed file must be checksummed"


def test_rsync_never_deletes_at_the_destination(tmp_path):
    seen, runner = _capture()
    RsyncTransport(remote="host:/srv/export", runner=runner).fetch(
        str(tmp_path), ["1/ct.nii.gz"])

    assert not any(arg.startswith("--delete") for arg in seen[0]), \
        "$SCRATCH holds other work; a transfer may not remove what it did not bring"


def test_rsync_is_given_the_work_list_not_a_wildcard(tmp_path):
    captured = {}

    def runner(command):
        listing = [a for a in command if a.startswith("--files-from=")][0]
        captured["paths"] = open(listing.split("=", 1)[1], encoding="utf-8").read().split()
        return 0

    RsyncTransport(remote="host:/srv/export", runner=runner).fetch(
        str(tmp_path), ["1/ct.nii.gz", "2/segmentations/left_main.nii.gz"])

    assert captured["paths"] == ["1/ct.nii.gz", "2/segmentations/left_main.nii.gz"]


def test_the_trailing_slash_is_not_the_operators_problem(tmp_path):
    seen, runner = _capture()
    RsyncTransport(remote="host:/srv/export", runner=runner).fetch(
        str(tmp_path), ["1/ct.nii.gz"])

    assert "host:/srv/export/" in seen[0], "rsync lands a directory deeper without it"


def test_a_nonzero_rsync_exit_becomes_a_transfer_error(tmp_path):
    transport = RsyncTransport(remote="host:/srv/export", runner=lambda command: 23)

    with pytest.raises(TransferError, match="rsync exited 23"):
        transport.fetch(str(tmp_path), ["1/ct.nii.gz"])


def test_fetching_an_empty_list_runs_nothing(tmp_path):
    seen, runner = _capture()
    RsyncTransport(remote="host:/srv/export", runner=runner).fetch(str(tmp_path), [])

    assert seen == []


def test_bandwidth_limit_and_ssh_options_are_passed_through(tmp_path):
    seen, runner = _capture()
    RsyncTransport(remote="host:/srv/export", runner=runner, bandwidth_limit="50m",
                   ssh_options=["-i", "/home/me/.ssh/id_ed25519"]).fetch(
        str(tmp_path), ["1/ct.nii.gz"])

    assert "--bwlimit=50m" in seen[0]
    assert "ssh -i /home/me/.ssh/id_ed25519" in seen[0]


# -- advice ---------------------------------------------------------------


def test_running_inside_a_slurm_job_is_called_out(monkeypatch):
    monkeypatch.setenv("SLURM_JOB_ID", "12345")

    notes = advise_host("tri-login01")

    assert any("no outbound network" in note for note in notes)


def test_a_login_node_draws_no_slurm_warning(monkeypatch):
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)

    assert advise_host("tri-dm1") == []


def test_a_destination_outside_scratch_is_called_out(monkeypatch, tmp_path):
    monkeypatch.setenv("SCRATCH", str(tmp_path / "scratch"))

    notes = advise_destination(tmp_path / "home" / "coronary")

    assert any("read-only" in note for note in notes)


def test_a_destination_under_scratch_is_fine(monkeypatch, tmp_path):
    monkeypatch.setenv("SCRATCH", str(tmp_path / "scratch"))

    assert advise_destination(tmp_path / "scratch" / "coronary") == []
