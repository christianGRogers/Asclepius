"""Getting the data onto a rented GPU box, and results back off it.

Assumes nothing but OpenSSH on this end, which Windows 10+, macOS and Linux all
ship. Three details drive the design:

**Convert locally, upload the result.** The 117 binary masks per case are 9.1 GB
and merge down to ~0.7 GB. Converting here and uploading nnU-Net datasets rather
than the raw Zenodo tree saves that 9.1 GB of transfer *and* moves the CPU work
off a machine billed by the GPU-hour.

**Upload the images once.** All six tasks share identical `imagesTr`; only the
label volumes differ. Images go to a shared directory on the instance and are
hardlinked into each task, so six tasks cost ~21 GB plus ~0.7 GB each rather
than six full copies.

**Stream with tar, not scp.** A dataset is ~2500 files. scp pays a round trip per
file, which over a home connection is most of the wall clock. `tar` piped through
a single ssh connection moves the same bytes in one stream, and Windows has
shipped bsdtar as `tar.exe` since Windows 10 1803. Transfers resume by diffing
against a remote listing, so a dropped connection costs only the current batch.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .config import RemoteConfig, TaskConfig

# Files per tar batch. Small enough that a dropped connection loses little,
# large enough that per-batch ssh setup stays negligible.
BATCH_SIZE = 200

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


class RemoteError(RuntimeError):
    pass


@dataclass
class CheckResult:
    """One diagnostic, with a fix the user can paste if it failed."""

    name: str
    ok: bool
    detail: str = ""
    fix: str = ""


@dataclass
class TransferPlan:
    files: list[Path] = field(default_factory=list)
    skipped: int = 0
    total_bytes: int = 0

    @property
    def n_files(self) -> int:
        return len(self.files)

    def describe(self) -> str:
        gb = self.total_bytes / 2**30
        return (f"{self.n_files} file(s), {gb:.2f} GB to send"
                + (f"; {self.skipped} already present" if self.skipped else ""))


class Remote:
    """An SSH connection to the training instance."""

    def __init__(self, cfg: RemoteConfig):
        if not cfg.configured:
            raise RemoteError(
                "no remote host configured. Set remote.host in configs/dataset.local.yaml "
                "or pass --host user@1.2.3.4"
            )
        self.cfg = cfg

    # -- primitives ---------------------------------------------------------

    def run(self, command: str, timeout: int = 120, check: bool = False):
        result = subprocess.run(
            ["ssh", *self.cfg.ssh_args(), self.cfg.host, command],
            capture_output=True, text=True, timeout=timeout, creationflags=_NO_WINDOW,
        )
        if check and result.returncode != 0:
            raise RemoteError(
                f"remote command failed ({result.returncode}): {command}\n"
                f"{(result.stderr or result.stdout).strip()}"
            )
        return result

    def capture(self, command: str, timeout: int = 120) -> str:
        return self.run(command, timeout=timeout, check=True).stdout

    def mkdir(self, *paths: str) -> None:
        quoted = " ".join(shlex.quote(p) for p in paths)
        self.run(f"mkdir -p {quoted}", check=True)

    # -- diagnostics --------------------------------------------------------

    def check(self) -> list[CheckResult]:
        """Everything that commonly goes wrong, checked before it costs money."""
        results = [check_identity_permissions(self.cfg.identity_file)]

        probe = self.run("echo ok", timeout=45)
        connected = probe.returncode == 0 and "ok" in probe.stdout
        results.append(CheckResult(
            "ssh connection", connected,
            self.cfg.host if connected else (probe.stderr or "").strip()[:300],
            fix=("Check the instance is running and its IP is current -- Lambda assigns "
                 "a new address each time an instance starts."),
        ))
        if not connected:
            return results

        gpu = self.run("nvidia-smi --query-gpu=name,memory.total,driver_version "
                       "--format=csv,noheader 2>/dev/null || echo NONE")
        has_gpu = "NONE" not in gpu.stdout and gpu.stdout.strip()
        results.append(CheckResult("gpu", bool(has_gpu), gpu.stdout.strip()[:200],
                                   fix="Instance has no visible GPU."))

        cpus = self.run("nproc").stdout.strip()
        mem = self.run("free -g | awk '/^Mem:/{print $2\" GB\"}'").stdout.strip()
        results.append(CheckResult("cpu / ram", bool(cpus), f"{cpus} vCPUs, {mem}"))
        # nnU-Net's augmentation is CPU-bound; below ~12 the GPU will idle.
        if cpus.isdigit() and int(cpus) < 12:
            results.append(CheckResult(
                "augmentation headroom", False, f"only {cpus} vCPUs",
                fix=("nnU-Net's data augmentation will bottleneck the GPU. Expect well "
                     "below the card's nominal throughput."),
            ))

        disk = self.run(f"df -BG --output=avail {shlex.quote(self.cfg.root)} 2>/dev/null "
                        f"|| df -BG --output=avail /home | tail -1")
        avail = "".join(c for c in disk.stdout.split("\n")[-1] if c.isdigit())
        enough = avail.isdigit() and int(avail) >= 60
        results.append(CheckResult(
            "free disk", enough, f"{avail} GB available",
            fix=("Stage 1 needs ~35 GB (raw + 3 mm preprocessed + checkpoints); "
                 "a 1.5 mm group needs ~110 GB."),
        ))

        py = self.run(f"{shlex.quote(self.cfg.venv)}/bin/python -c "
                      f"'import segtrain,nnunetv2,torch;print(torch.__version__)' 2>/dev/null "
                      f"|| echo MISSING")
        ready = "MISSING" not in py.stdout
        results.append(CheckResult(
            "segtrain installed", ready,
            py.stdout.strip()[:100] if ready else "not installed",
            fix="Run: segtrain remote setup",
        ))
        return results

    # -- transfer -----------------------------------------------------------

    def remote_sizes(self, remote_dir: str) -> dict[str, int]:
        """{relative path: size} for everything already on the instance."""
        out = self.run(
            f"cd {shlex.quote(remote_dir)} 2>/dev/null && "
            f"find . -type f -printf '%s %P\\n' 2>/dev/null || true",
            timeout=300,
        ).stdout
        sizes: dict[str, int] = {}
        for line in out.splitlines():
            parts = line.strip().split(" ", 1)
            if len(parts) == 2 and parts[0].isdigit():
                sizes[parts[1].replace("\\", "/")] = int(parts[0])
        return sizes

    def plan_transfer(self, local_dir: Path, remote_dir: str,
                      files: Optional[Iterable[Path]] = None) -> TransferPlan:
        """Which files still need sending.

        Compares size only, not a checksum. Hashing 21 GB on both ends to catch a
        same-name-same-size difference costs far more than it saves for a dataset
        that is written once and never edited.
        """
        local_dir = Path(local_dir)
        candidates = list(files) if files is not None else [
            p for p in local_dir.rglob("*") if p.is_file()
        ]
        present = self.remote_sizes(remote_dir)

        plan = TransferPlan()
        for path in candidates:
            rel = path.relative_to(local_dir).as_posix()
            size = path.stat().st_size
            if present.get(rel) == size:
                plan.skipped += 1
                continue
            plan.files.append(path)
            plan.total_bytes += size
        return plan

    def send(self, local_dir: Path, remote_dir: str, plan: TransferPlan,
             progress: Optional[Callable] = None) -> None:
        """Stream files to the instance in tar batches."""
        if not plan.files:
            return
        if not _have_tar():
            raise RemoteError(
                "no 'tar' on PATH. Windows 10 1803+ ships bsdtar as tar.exe; "
                "otherwise install Git for Windows or use WSL."
            )
        self.mkdir(remote_dir)
        local_dir = Path(local_dir)
        sent_bytes = 0

        for start in range(0, len(plan.files), BATCH_SIZE):
            batch = plan.files[start:start + BATCH_SIZE]
            listing = "\n".join(p.relative_to(local_dir).as_posix() for p in batch)
            # A file-list file avoids command-line length limits, which 200 long
            # NIfTI paths would blow past on Windows.
            manifest = local_dir / ".segtrain_batch"
            manifest.write_text(listing + "\n", encoding="utf-8")
            try:
                self._stream_batch(local_dir, remote_dir, manifest)
            finally:
                manifest.unlink(missing_ok=True)

            sent_bytes += sum(p.stat().st_size for p in batch)
            if progress:
                progress(min(start + BATCH_SIZE, len(plan.files)),
                         len(plan.files), sent_bytes, plan.total_bytes)

    def _stream_batch(self, local_dir: Path, remote_dir: str, manifest: Path) -> None:
        tar_cmd = ["tar", "-cf", "-", "-C", str(local_dir), "-T", str(manifest.name)]
        ssh_cmd = ["ssh", *self.cfg.ssh_args(), self.cfg.host,
                   f"tar -xf - -C {shlex.quote(remote_dir)}"]

        tar_proc = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, cwd=str(local_dir),
                                    creationflags=_NO_WINDOW)
        ssh_proc = subprocess.Popen(ssh_cmd, stdin=tar_proc.stdout,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    creationflags=_NO_WINDOW)
        # Let tar see SIGPIPE if ssh dies, instead of blocking on a full pipe.
        tar_proc.stdout.close()
        _, ssh_err = ssh_proc.communicate()
        tar_proc.wait()

        if ssh_proc.returncode != 0:
            raise RemoteError(f"transfer failed: {(ssh_err or b'').decode(errors='replace')[:300]}")
        if tar_proc.returncode not in (0, None):
            err = (tar_proc.stderr.read() or b"").decode(errors="replace")
            raise RemoteError(f"tar failed: {err[:300]}")

    def fetch(self, remote_path: str, local_path: Path) -> bool:
        """Copy one file down. Used for checkpoints and result CSVs."""
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["scp", *self.cfg.ssh_args(), f"{self.cfg.host}:{remote_path}", str(local_path)],
            capture_output=True, text=True, timeout=7200, creationflags=_NO_WINDOW,
        )
        return result.returncode == 0

    def fetch_dir(self, remote_dir: str, local_dir: Path,
                  exclude: Iterable[str] = ()) -> bool:
        """Pull a directory down as a single compressed tar stream."""
        local_dir = Path(local_dir)
        local_dir.mkdir(parents=True, exist_ok=True)
        excludes = " ".join(f"--exclude={shlex.quote(p)}" for p in exclude)
        remote_cmd = f"tar -czf - -C {shlex.quote(remote_dir)} {excludes} ."

        ssh_proc = subprocess.Popen(
            ["ssh", *self.cfg.ssh_args(), self.cfg.host, remote_cmd],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=_NO_WINDOW)
        tar_proc = subprocess.Popen(
            ["tar", "-xzf", "-", "-C", str(local_dir)],
            stdin=ssh_proc.stdout, stderr=subprocess.PIPE, creationflags=_NO_WINDOW)
        ssh_proc.stdout.close()
        tar_proc.communicate()
        ssh_proc.wait()
        return tar_proc.returncode == 0


# -- key permissions ---------------------------------------------------------


def check_identity_permissions(identity_file: Optional[str]) -> CheckResult:
    """OpenSSH refuses a private key that other accounts can read.

    On Windows a key downloaded to Downloads/ inherits ACLs granting SYSTEM and
    Administrators full control, and ssh rejects it with UNPROTECTED PRIVATE KEY
    FILE. The fix is to strip inheritance and grant only the current user.
    """
    if not identity_file:
        return CheckResult("ssh key", True, "using agent or default key")

    path = Path(identity_file)
    if not path.is_file():
        return CheckResult("ssh key", False, f"not found: {path}",
                           fix="Check remote.identity_file in your config.")

    if os.name == "nt":
        fix = (f'icacls "{path}" /inheritance:r /grant:r "%USERNAME%:R"')
        try:
            out = subprocess.run(["icacls", str(path)], capture_output=True,
                                 text=True, timeout=30, creationflags=_NO_WINDOW).stdout
        except (OSError, subprocess.SubprocessError):
            return CheckResult("ssh key permissions", True, "could not verify")

        risky = [ident for ident in ("NT AUTHORITY\\SYSTEM", "BUILTIN\\Administrators",
                                     "Everyone", "BUILTIN\\Users")
                 if ident in out]
        if risky:
            return CheckResult(
                "ssh key permissions", False,
                "readable by " + ", ".join(risky),
                fix=("OpenSSH will refuse this key with 'UNPROTECTED PRIVATE KEY FILE'.\n"
                     f"    {fix}"),
            )
        return CheckResult("ssh key permissions", True, "restricted to current user")

    # POSIX: any group or other permission bit makes ssh refuse the key.
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        return CheckResult("ssh key permissions", False, f"mode {oct(mode)}",
                           fix=f"chmod 600 {path}")
    return CheckResult("ssh key permissions", True, f"mode {oct(mode)}")


def fix_identity_permissions(identity_file: str) -> tuple[bool, str]:
    """Restrict a private key to the current user. Returns (ok, message)."""
    path = Path(identity_file)
    if not path.is_file():
        return False, f"not found: {path}"
    if os.name != "nt":
        try:
            path.chmod(0o600)
            return True, f"chmod 600 {path}"
        except OSError as exc:
            return False, str(exc)

    user = os.environ.get("USERNAME", "")
    result = subprocess.run(
        ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:R"],
        capture_output=True, text=True, timeout=60, creationflags=_NO_WINDOW,
    )
    ok = result.returncode == 0
    return ok, (result.stdout or result.stderr).strip()[:300]


def _have_tar() -> bool:
    from shutil import which

    return which("tar") is not None


# -- provisioning ------------------------------------------------------------

SETUP_SCRIPT = r"""
set -euo pipefail
ROOT={root}
VENV={venv}
REPO={repo}

mkdir -p "$ROOT" "$ROOT/data" "$ROOT/runs"

if [ ! -d "$VENV" ]; then
  # --system-site-packages keeps the image's preinstalled CUDA torch, which is
  # already matched to the driver. Building a clean venv would re-download a
  # multi-gigabyte torch wheel on the GPU clock for no benefit.
  {python} -m venv --system-site-packages "$VENV"
fi
"$VENV/bin/python" -m pip install --quiet --upgrade pip

if [ -d "$REPO/.git" ]; then
  git -C "$REPO" pull --ff-only || true
fi

if [ -d "$REPO" ]; then
  "$VENV/bin/python" -m pip install --quiet -e "$REPO[train]"
fi

"$VENV/bin/python" - <<'PY'
import torch
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
if torch.cuda.is_available():
    p = torch.cuda.get_device_properties(0)
    print("gpu", p.name, round(p.total_memory / 2**30, 1), "GiB")
PY
"""


def render_setup_script(cfg: RemoteConfig) -> str:
    return SETUP_SCRIPT.format(
        root=shlex.quote(cfg.root),
        venv=shlex.quote(cfg.venv),
        repo=shlex.quote(cfg.repo),
        python=shlex.quote(cfg.python),
    )


def remote_env_exports(cfg: RemoteConfig) -> str:
    """nnU-Net's three roots plus our trainer path, as shell exports."""
    pairs = {
        "nnUNet_raw": cfg.nnunet_raw,
        "nnUNet_preprocessed": cfg.nnunet_preprocessed,
        "nnUNet_results": cfg.nnunet_results,
        "nnUNet_extTrainer": f"{cfg.repo}/src/segtrain/nnunet_ext",
    }
    return " ".join(f"export {k}={shlex.quote(v)};" for k, v in pairs.items())


def task_remote_dirs(cfg: RemoteConfig, task: TaskConfig) -> dict[str, str]:
    base = f"{cfg.nnunet_raw}/{task.nnunet_name}"
    return {
        "base": base,
        "imagesTr": f"{base}/imagesTr",
        "labelsTr": f"{base}/labelsTr",
        "imagesTs": f"{base}/imagesTs",
        "labelsTs": f"{base}/labelsTs",
        "shared_images": f"{cfg.data_root}/shared_images",
    }


def link_shared_images(remote: Remote, cfg: RemoteConfig, task: TaskConfig) -> str:
    """Hardlink the shared image pool into this task's imagesTr/imagesTs.

    Every task uses byte-identical images and differs only in labels. Uploading
    them once and linking keeps six tasks at ~21 GB total instead of ~126 GB.
    """
    dirs = task_remote_dirs(cfg, task)
    shared = dirs["shared_images"]
    script = (
        f"set -e; mkdir -p {shlex.quote(dirs['imagesTr'])} {shlex.quote(dirs['imagesTs'])}; "
        f"for split in imagesTr imagesTs; do "
        f"  src={shlex.quote(shared)}/$split; dst={shlex.quote(dirs['base'])}/$split; "
        f"  [ -d \"$src\" ] || continue; "
        # ln -f is idempotent, so re-running after a partial upload is safe.
        f"  find \"$src\" -name '*.nii.gz' -exec ln -f {{}} \"$dst\"/ \\; ; "
        f"done; "
        f"echo linked $(find {shlex.quote(dirs['base'])}/imagesTr -name '*.nii.gz' | wc -l) images"
    )
    return remote.capture(script, timeout=600).strip()


def wait_for(remote: Remote, predicate: Callable[[Remote], bool],
             timeout: float = 600, interval: float = 10) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate(remote):
            return True
        time.sleep(interval)
    return False


def render_check_report(results: list[CheckResult], stream=sys.stdout) -> bool:
    ok = True
    for r in results:
        mark = "OK  " if r.ok else "FAIL"
        print(f"  [{mark}] {r.name}" + (f" -- {r.detail}" if r.detail else ""), file=stream)
        if not r.ok:
            ok = False
            if r.fix:
                for line in r.fix.splitlines():
                    print(f"         {line}", file=stream)
    return ok
