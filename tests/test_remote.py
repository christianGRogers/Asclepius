"""Remote plumbing that can be checked without a live instance."""

import os

import pytest

from segtrain.config import RemoteConfig
from segtrain.remote import (
    Remote,
    RemoteError,
    TransferPlan,
    check_identity_permissions,
    remote_env_exports,
    render_setup_script,
    task_remote_dirs,
)

HOST = "ubuntu@203.0.113.10"


def _cfg(**kwargs):
    return RemoteConfig(host=HOST, **kwargs)


# -- ssh arguments -----------------------------------------------------------


def test_identity_is_passed_to_ssh(tmp_path):
    key = tmp_path / "k.pem"
    key.write_text("x", encoding="utf-8")
    args = _cfg(identity_file=str(key)).ssh_args()
    assert "-i" in args and str(key) in args


def test_identities_only_is_set_with_a_key(tmp_path):
    """Without it ssh offers every agent key first and can exhaust MaxAuthTries."""
    key = tmp_path / "k.pem"
    key.write_text("x", encoding="utf-8")
    assert "IdentitiesOnly=yes" in _cfg(identity_file=str(key)).ssh_args()


def test_no_identity_flag_when_none_configured():
    assert "-i" not in _cfg().ssh_args()


def test_keepalives_are_always_set():
    """A run is watched for days; NAT drops idle control channels without these."""
    args = _cfg().ssh_args()
    assert "ServerAliveInterval=30" in args
    assert "BatchMode=yes" in args


def test_extra_ssh_options_are_appended():
    assert "-J" in _cfg(ssh_options=["-J", "bastion"]).ssh_args()


# -- paths -------------------------------------------------------------------


def test_remote_paths_derive_from_root():
    cfg = _cfg(root="/data/seg")
    assert cfg.nnunet_raw == "/data/seg/data/nnUNet_raw"
    assert cfg.runs_root == "/data/seg/runs"
    assert cfg.repo == "/data/seg/segmentator-train"


def test_env_exports_cover_all_four_variables():
    exports = remote_env_exports(_cfg())
    for var in ("nnUNet_raw", "nnUNet_preprocessed", "nnUNet_results", "nnUNet_extTrainer"):
        assert f"export {var}=" in exports


def test_ext_trainer_points_into_the_uploaded_repo():
    """Without this nnU-Net cannot find nnUNetTrainer_segtrain and the run dies."""
    assert "/segmentator-train/src/segtrain/nnunet_ext" in remote_env_exports(_cfg())


def test_task_dirs_share_one_image_pool():
    from segtrain.config import load_task

    cfg = _cfg()
    a = task_remote_dirs(cfg, load_task(701))
    b = task_remote_dirs(cfg, load_task(702))
    assert a["shared_images"] == b["shared_images"], "images must be uploaded once"
    assert a["labelsTr"] != b["labelsTr"], "labels are per task"


def test_setup_script_reuses_system_site_packages():
    """The instance image ships a CUDA torch matched to its driver; rebuilding
    that in a clean venv would re-download gigabytes on the GPU clock."""
    assert "--system-site-packages" in render_setup_script(_cfg())


def test_setup_script_quotes_paths_with_spaces():
    script = render_setup_script(_cfg(root="/home/ubuntu/my seg"))
    assert "'/home/ubuntu/my seg'" in script


# -- configuration guard -----------------------------------------------------


def test_remote_without_host_is_rejected_early():
    with pytest.raises(RemoteError, match="no remote host"):
        Remote(RemoteConfig())


# -- transfer planning -------------------------------------------------------


class _FakeRemote(Remote):
    """Remote with the network stubbed out, to test the diff logic."""

    def __init__(self, present):
        Remote.__init__(self, _cfg())
        self._present = present

    def remote_sizes(self, remote_dir):
        return self._present


def _make(tmp_path, names_sizes):
    for name, size in names_sizes.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * size)


def test_plan_sends_everything_when_remote_is_empty(tmp_path):
    _make(tmp_path, {"a.nii.gz": 10, "b.nii.gz": 20})
    plan = _FakeRemote({}).plan_transfer(tmp_path, "/remote")
    assert plan.n_files == 2 and plan.total_bytes == 30 and plan.skipped == 0


def test_plan_skips_files_already_present_at_the_same_size(tmp_path):
    """This is what makes a dropped 21 GB upload resumable."""
    _make(tmp_path, {"a.nii.gz": 10, "b.nii.gz": 20})
    plan = _FakeRemote({"a.nii.gz": 10}).plan_transfer(tmp_path, "/remote")
    assert plan.n_files == 1 and plan.skipped == 1
    assert plan.files[0].name == "b.nii.gz"


def test_plan_resends_a_truncated_file(tmp_path):
    """A partially-transferred file has the right name and the wrong size."""
    _make(tmp_path, {"a.nii.gz": 10})
    plan = _FakeRemote({"a.nii.gz": 4}).plan_transfer(tmp_path, "/remote")
    assert plan.n_files == 1


def test_plan_uses_posix_relative_paths(tmp_path):
    """Remote listings are POSIX; Windows separators would never match."""
    _make(tmp_path, {"sub/a.nii.gz": 5})
    plan = _FakeRemote({"sub/a.nii.gz": 5}).plan_transfer(tmp_path, "/remote")
    assert plan.skipped == 1 and plan.n_files == 0


def test_plan_accepts_an_explicit_file_list(tmp_path):
    _make(tmp_path, {"a.nii.gz": 10, "b.nii.gz": 20})
    plan = _FakeRemote({}).plan_transfer(tmp_path, "/remote",
                                         files=[tmp_path / "a.nii.gz"])
    assert plan.n_files == 1


def test_transfer_plan_describe_mentions_skipped():
    plan = TransferPlan(files=[], skipped=3, total_bytes=0)
    assert "3 already present" in plan.describe()


# -- key permissions ---------------------------------------------------------


def test_missing_key_is_reported():
    result = check_identity_permissions("/no/such/key.pem")
    assert not result.ok and "not found" in result.detail


def test_no_key_configured_is_fine():
    assert check_identity_permissions(None).ok


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_group_readable_key_is_rejected(tmp_path):
    key = tmp_path / "k.pem"
    key.write_text("x", encoding="utf-8")
    key.chmod(0o644)
    result = check_identity_permissions(str(key))
    assert not result.ok and "chmod 600" in result.fix


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_private_key_is_accepted(tmp_path):
    key = tmp_path / "k.pem"
    key.write_text("x", encoding="utf-8")
    key.chmod(0o600)
    assert check_identity_permissions(str(key)).ok


@pytest.mark.skipif(os.name != "nt", reason="Windows ACLs")
def test_windows_reports_a_fix_command(tmp_path):
    """A key downloaded to Downloads/ inherits ACLs OpenSSH refuses."""
    key = tmp_path / "k.pem"
    key.write_text("x", encoding="utf-8")
    result = check_identity_permissions(str(key))
    if not result.ok:
        assert "icacls" in result.fix
