"""Run training on a remote machine over SSH.

Uses the ``ssh`` executable rather than a Python SSH library on purpose. OpenSSH
ships with Windows 10+, macOS and every Linux, and it already understands the
user's ``~/.ssh/config``, agent, jump hosts and keys. A library would mean
reimplementing all of that, and -- more importantly -- would have to be
installed into Slicer's bundled Python, which is exactly the kind of fragile
dependency this pipeline avoids.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Sequence

from .base import Backend, BackendError, Job


class SshBackend(Backend):
    """Launch under ``nohup`` on a remote host and leave it running.

    The remote run directory is the same shape as a local one, so the monitor
    can either read it over an SFTP/rsync pull or watch a mounted copy without
    any special-casing.
    """

    name = "ssh"

    def __init__(self, host: Optional[str] = None, ssh_options: Optional[Sequence[str]] = None):
        if not host:
            raise BackendError("ssh backend requires a host, e.g. user@gpu-box")
        if shutil.which("ssh") is None:
            raise BackendError("no 'ssh' executable found on PATH")
        self.host = host
        self.ssh_options = list(ssh_options or ["-o", "BatchMode=yes"])

    def _ssh(self, remote_command: str, timeout: int = 60) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["ssh", *self.ssh_options, self.host, remote_command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def submit(
        self,
        command: Sequence[str],
        run_dir: str,
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
    ) -> Job:
        exports = ""
        if env:
            # Only forward our own variables. Shipping the whole local
            # environment would overwrite the remote machine's PATH, CUDA
            # settings and virtualenv with values from a Windows laptop.
            ours = {k: v for k, v in env.items() if k.startswith(("SEGTRAIN_", "nnUNet_"))}
            exports = "".join(f"export {k}={shlex.quote(str(v))}; " for k, v in ours.items())

        cd = f"cd {shlex.quote(cwd)}; " if cwd else ""
        quoted = " ".join(shlex.quote(str(c)) for c in command)
        log = shlex.quote(f"{run_dir}/train.log")

        # nohup + setsid so the run survives this SSH session closing; echo $! to
        # bring the remote PID back for later status checks.
        remote = (
            f"mkdir -p {shlex.quote(run_dir)}; {cd}{exports}"
            f"nohup setsid {quoted} >> {log} 2>&1 & echo $!"
        )

        result = self._ssh(remote)
        if result.returncode != 0:
            raise BackendError(f"ssh launch failed: {result.stderr.strip() or result.stdout}")

        pid = None
        for line in result.stdout.strip().splitlines():
            if line.strip().isdigit():
                pid = int(line.strip())
        return Job(
            backend=self.name,
            command=list(command),
            run_dir=run_dir,
            pid=pid,
            detail={"host": self.host},
        )

    def is_running(self, job: Job) -> bool:
        if not job.pid:
            return False
        result = self._ssh(f"kill -0 {job.pid} 2>/dev/null && echo yes || echo no")
        return "yes" in result.stdout

    def cancel(self, job: Job) -> bool:
        if not job.pid:
            return False
        # Negative PID targets the whole process group setsid created, so the
        # dataloader workers go too rather than being orphaned.
        result = self._ssh(f"kill -TERM -{job.pid} 2>/dev/null || kill -TERM {job.pid}")
        return result.returncode == 0

    def pull(self, remote_path: str, local_path: Path, exclude: Sequence[str] = ()) -> bool:
        """Copy a run directory down for offline inspection.

        Prefers rsync (incremental, so repeated pulls of a growing run are
        cheap) and falls back to scp where rsync is unavailable, as on a stock
        Windows install.
        """
        local_path = Path(local_path)
        local_path.mkdir(parents=True, exist_ok=True)
        src = f"{self.host}:{remote_path}/"

        if shutil.which("rsync"):
            cmd = ["rsync", "-az", "--partial"]
            for pattern in exclude:
                cmd += ["--exclude", pattern]
            cmd += [src, str(local_path)]
        elif shutil.which("scp"):
            cmd = ["scp", "-r", f"{self.host}:{remote_path}/.", str(local_path)]
        else:
            raise BackendError("neither rsync nor scp found on PATH")

        return subprocess.run(cmd, capture_output=True, text=True, timeout=3600).returncode == 0
