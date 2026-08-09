"""Submit training to a SLURM queue.

The generated script sets ``nnUNet_*`` and ``SEGTRAIN_*`` in the job environment
and writes into the same run directory shape as the other backends, so a queued
job is monitored exactly like a local one -- the shared filesystem is the whole
integration.

Note the run may sit pending for hours before producing a single event. The
monitor shows "queued" rather than "stalled" by checking job state through
``squeue``, which is why this backend records the job id.
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Sequence

from .base import Backend, BackendError, Job

SCRIPT_TEMPLATE = """#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --output={run_dir}/slurm-%j.out
#SBATCH --error={run_dir}/slurm-%j.out
#SBATCH --time={time}
#SBATCH --gres=gpu:{gpus}
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem={mem}
{extra_directives}
set -euo pipefail

{env_exports}
{modules}

mkdir -p {run_dir}
echo "host=$(hostname) job=$SLURM_JOB_ID started=$(date -Is)" >> {run_dir}/slurm.info

{command}
"""


class SlurmBackend(Backend):
    name = "slurm"

    def __init__(
        self,
        partition: Optional[str] = None,
        time: str = "48:00:00",
        gpus: int = 1,
        cpus: int = 12,
        mem: str = "64G",
        modules: Sequence[str] = (),
        account: Optional[str] = None,
        submit_via_ssh: Optional[str] = None,
    ):
        self.partition = partition
        # nnU-Net's default schedule is 1000 epochs; a 48h wall clock is the
        # realistic ballpark for one 3d_fullres model on a single modern GPU.
        # Raise it for the larger 1.5 mm groups rather than discovering the
        # limit when a run is killed at epoch 800.
        self.time = time
        self.gpus = gpus
        self.cpus = cpus
        self.mem = mem
        self.modules = list(modules)
        self.account = account
        self.submit_via_ssh = submit_via_ssh
        if submit_via_ssh is None and shutil.which("sbatch") is None:
            raise BackendError(
                "no 'sbatch' on PATH; pass submit_via_ssh=user@login-node to submit remotely"
            )

    def render_script(
        self,
        command: Sequence[str],
        run_dir: str,
        env: Optional[dict] = None,
        job_name: str = "segtrain",
    ) -> str:
        ours = {}
        if env:
            ours = {k: v for k, v in env.items() if k.startswith(("SEGTRAIN_", "nnUNet_"))}
        exports = "\n".join(f"export {k}={shlex.quote(str(v))}" for k, v in sorted(ours.items()))

        directives = []
        if self.partition:
            directives.append(f"#SBATCH --partition={self.partition}")
        if self.account:
            directives.append(f"#SBATCH --account={self.account}")

        return SCRIPT_TEMPLATE.format(
            job_name=job_name,
            run_dir=run_dir,
            time=self.time,
            gpus=self.gpus,
            cpus=self.cpus,
            mem=self.mem,
            extra_directives="\n".join(directives),
            env_exports=exports,
            modules="\n".join(f"module load {m}" for m in self.modules),
            command=" ".join(shlex.quote(str(c)) for c in command),
        )

    def submit(
        self,
        command: Sequence[str],
        run_dir: str,
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
    ) -> Job:
        script = self.render_script(command, run_dir, env)
        script_path = Path(run_dir) / "submit.sh"

        if self.submit_via_ssh:
            raise BackendError(
                "remote SLURM submission is not wired up; write submit.sh to the shared "
                "filesystem and run sbatch on the login node, or run segtrain there"
            )

        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script, encoding="utf-8")
        script_path.chmod(0o755)

        result = subprocess.run(
            ["sbatch", str(script_path)], capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise BackendError(f"sbatch failed: {result.stderr.strip()}")

        match = re.search(r"(\d+)", result.stdout)
        return Job(
            backend=self.name,
            command=list(command),
            run_dir=run_dir,
            job_id=match.group(1) if match else None,
            detail={"script": str(script_path)},
        )

    def is_running(self, job: Job) -> bool:
        if not job.job_id:
            return False
        result = subprocess.run(
            ["squeue", "-j", job.job_id, "-h", "-o", "%T"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        # PENDING counts as running: the job exists and will start. Reporting it
        # as dead would make a queued run look like a failed one.
        return result.stdout.strip() in {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING"}

    def cancel(self, job: Job) -> bool:
        if not job.job_id:
            return False
        return subprocess.run(
            ["scancel", job.job_id], capture_output=True, timeout=60
        ).returncode == 0
