"""Submit a command to SLURM as a single batch job.

This is the general backend: it wraps whatever command it is handed in a job
script and submits it. It deliberately does **not** chain jobs across the
walltime cap -- that needs the trainer's pause protocol, knowledge of the task's
checkpoint path and a bounded resubmission loop, which is ``segtrain.slurm`` and
is driven by ``segtrain scinet submit``.

So the division is:

``segtrain scinet submit``
    The real path for a multi-day run. Self-chaining, resumes from checkpoints,
    stages data to node-local disk, runs the preview daemon.

``segtrain train --backend slurm``
    One job, one walltime block, no successor. Right for a short smoke test on a
    real GPU, or for anything that genuinely fits inside the cap.

Choosing the second for a 1000-epoch run gets you 24 hours of training and then
silence, which is why ``scinet submit`` prints a warning if you appear to be
doing that.
"""

from __future__ import annotations

import json
import shlex
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from .base import Backend, BackendError, Job
from .local import JOB_FILE


class SlurmBackend(Backend):
    """One command, one ``sbatch``."""

    name = "slurm"

    def __init__(self, scinet=None, directives: Optional[Sequence[str]] = None):
        # Accepting the config rather than reading it keeps the backend free of
        # config-loading order concerns, and lets a test pass a bare object.
        self.scinet = scinet
        self.directives = list(directives or [])

    def submit(
        self,
        command: Sequence[str],
        run_dir: str,
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
    ) -> Job:
        from .. import slurm as slurm_mod

        run_path = Path(run_dir)
        run_path.mkdir(parents=True, exist_ok=True)
        script_path = run_path / "job.sh"

        script = self._render(command, run_path, env=env, cwd=cwd)
        slurm_mod.write_script(script_path, script)

        try:
            job_id = slurm_mod.submit(script_path)
        except slurm_mod.SlurmError as exc:
            raise BackendError(str(exc)) from exc

        job = Job(backend=self.name, command=list(command), run_dir=str(run_path),
                  job_id=job_id, detail={"script": str(script_path)})
        _write_job(run_path, job)
        return job

    def _render(
        self,
        command: Sequence[str],
        run_path: Path,
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
    ) -> str:
        from .. import slurm as slurm_mod

        if self.scinet is None:
            raise BackendError(
                "the slurm backend needs the scinet: section of the config; "
                "run through the segtrain CLI rather than constructing it bare"
            )

        lines = [
            "#!/bin/bash",
            *slurm_mod.sbatch_directives(
                self.scinet,
                job_name=f"segtrain-{run_path.name}"[:64],
                log_path=f"{run_path}/slurm-%j.out",
                gpu=True,
            ),
            *self.directives,
            "",
            "set -uo pipefail",
            "",
            'echo "=== segtrain job $SLURM_JOB_ID on $(hostname) $(date -Is) ==="',
            "",
        ]
        if self.scinet.modules:
            lines.append("module --force purge")
            lines.append(f"module load {' '.join(self.scinet.modules)}")
        if self.scinet.venv:
            lines.append(f"source {shlex.quote(self.scinet.venv)}/bin/activate")
        lines.extend(self.scinet.setup_commands)
        lines.append("")

        # Only the pipeline's own variables are exported. Replaying the caller's
        # entire environment into the script would drag a login node's stale
        # module paths onto the compute node -- the exact thing `module purge`
        # above is there to prevent.
        for key, value in sorted((env or {}).items()):
            if key.startswith(("SEGTRAIN_", "nnUNet_")):
                lines.append(f"export {key}={shlex.quote(str(value))}")
        lines.append("")

        if cwd:
            lines.append(f"cd {shlex.quote(cwd)}")
        lines.append("srun " + " ".join(shlex.quote(str(c)) for c in command))
        return "\n".join(lines) + "\n"

    def is_running(self, job: Job) -> bool:
        from .. import slurm as slurm_mod

        if not job.job_id:
            return False
        state = slurm_mod.job_state(job.job_id)
        # None means neither squeue nor sacct could say. Reporting "not running"
        # there would be a guess; a job that is merely PENDING is also not
        # finished, so both collapse to "still ours".
        if state is None:
            return False
        return state.upper() in ("PENDING", "RUNNING", "CONFIGURING", "COMPLETING",
                                 "RESIZING", "SUSPENDED", "REQUEUED")

    def cancel(self, job: Job) -> bool:
        from .. import slurm as slurm_mod

        if not job.job_id:
            return False
        # Cancel the queued successor first: cancelling this job would otherwise
        # satisfy its `afterany` dependency and immediately start the very block
        # the user asked to stop.
        chain = Path(job.run_dir) / "chain_next.jobid"
        if chain.is_file():
            try:
                successor = chain.read_text(encoding="utf-8").strip()
            except OSError:
                successor = ""
            if successor:
                slurm_mod.cancel(successor)
            chain.unlink(missing_ok=True)
        return slurm_mod.cancel(job.job_id)


def _write_job(run_dir: Path, job: Job) -> None:
    payload = {
        "backend": job.backend,
        "pid": job.pid,
        "job_id": job.job_id,
        "command": list(job.command),
        "run_dir": job.run_dir,
        "python": sys.executable,
        **job.detail,
    }
    with open(run_dir / JOB_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
