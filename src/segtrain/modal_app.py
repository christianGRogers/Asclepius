"""Modal app: the GPU half of the pipeline.

Modal is serverless, so there is no instance to provision, no IP to chase and no
SSH key to manage. Three things follow from that, and they shape this file:

**Preprocessing runs without a GPU.** Planning and preprocessing are pure CPU
work. On a rented instance you pay GPU rates for the hour or two they take; here
they get their own CPU-only function and cost a couple of dollars.

**Uploading is free.** Data goes from the laptop straight into a Volume with no
container running, so the hours spent pushing 21 GB cost nothing.

**Functions are capped at 24 hours, and Stage 1 needs ~36.** Training must
therefore stop cleanly before the ceiling, checkpoint, and be relaunched. That is
what ``SEGTRAIN_MAX_SECONDS`` in ``nnUNetTrainer_segtrain`` does, and what the
driver loop in ``segtrain modal train`` relies on. The subtle part is that
nnU-Net's ``on_train_end`` *deletes* ``checkpoint_latest.pth``; a paused run skips
it so ``--c`` has something to resume from.

The container runs the same ``segtrain`` commands as a local machine -- only the
nnU-Net roots differ, pointing into the mounted Volume. Nothing about the event
stream, the preview daemon or the Slicer monitor changes.

Run through ``segtrain modal ...``, or directly::

    modal run src/segtrain/modal_app.py::prepare --task 701
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import modal

APP_NAME = "segtrain"
VOLUME_NAME = "segtrain-data"
MOUNT = "/data"

# Where `fetch` puts the Zenodo tree. Named after the archive so a human poking
# at the volume with `segtrain modal inspect` sees what it is.
DATASET = f"{MOUNT}/Totalsegmentator_dataset_v201"

# Repo root: src/segtrain/modal_app.py -> repo/
REPO = Path(__file__).resolve().parents[2]

GPU = os.environ.get("SEGTRAIN_MODAL_GPU", "A100-40GB")
CPU = float(os.environ.get("SEGTRAIN_MODAL_CPU", "24"))
MEMORY_MB = int(os.environ.get("SEGTRAIN_MODAL_MEMORY", str(64 * 1024)))

HOURS = 3600

app = modal.App(APP_NAME)
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

# torch comes from PyPI with bundled CUDA; Modal supplies the driver. Pinning
# nnU-Net's major version matters -- the trainer subclass touches internals that
# are stable within v2 but not across a major bump.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch",
        "nnunetv2>=2.5,<3",
        "nibabel>=4.0",
        "PyYAML>=6.0",
        "scipy>=1.7",
        "SimpleITK>=2.2",
    )
    # Mounted at runtime rather than baked into a layer, so editing pipeline code
    # does not trigger an image rebuild. Worth a lot while iterating.
    .add_local_dir(REPO / "src", "/root/src")
    .add_local_dir(REPO / "configs", "/root/configs")
    .add_local_dir(REPO / "scripts", "/root/scripts")
)

CONTAINER_ENV = {
    "PYTHONPATH": "/root/src",
    "nnUNet_raw": f"{MOUNT}/nnUNet_raw",
    "nnUNet_preprocessed": f"{MOUNT}/nnUNet_preprocessed",
    "nnUNet_results": f"{MOUNT}/nnUNet_results",
    # Without this nnU-Net cannot find nnUNetTrainer_segtrain and the run dies
    # immediately with "Could not find requested nnunet trainer".
    "nnUNet_extTrainer": "/root/src/segtrain/nnunet_ext",
}


# -- helpers running inside the container ------------------------------------


def _segtrain(*args: str, env: dict | None = None) -> int:
    """Invoke the pipeline's own CLI, streaming output into Modal's logs."""
    cmd = [sys.executable, "-m", "segtrain.cli", *args]
    print("+ " + " ".join(cmd), flush=True)
    full = {**os.environ, **CONTAINER_ENV, **(env or {})}
    return subprocess.run(cmd, env=full).returncode


def _roots() -> list[str]:
    """CLI overrides pointing every root into the mounted Volume."""
    return [
        "--zenodo-root", DATASET,
        "--nnunet-raw", f"{MOUNT}/nnUNet_raw",
        "--nnunet-preprocessed", f"{MOUNT}/nnUNet_preprocessed",
        "--nnunet-results", f"{MOUNT}/nnUNet_results",
        "--runs-root", f"{MOUNT}/runs",
    ]


def _task_name(task: str) -> str:
    sys.path.insert(0, "/root/src")
    from segtrain.config import load_task

    return load_task(task).nnunet_name


def _has_checkpoint(task: str, fold: int) -> bool:
    sys.path.insert(0, "/root/src")
    from segtrain.config import load_task

    cfg = load_task(task)
    model = (Path(MOUNT) / "nnUNet_results" / cfg.nnunet_name /
             f"{cfg.trainer}__{cfg.plans_name}__{cfg.configuration}" / f"fold_{fold}")
    return (model / "checkpoint_latest.pth").is_file()


# -- functions ---------------------------------------------------------------


@app.function(
    image=image,
    volumes={MOUNT: volume},
    cpu=8.0,
    memory=MEMORY_MB,
    # Zenodo -> Modal is minutes, not the hours it takes from a laptop. Unpacking
    # 145k small files onto the Volume is the slow half, hence the wide timeout.
    timeout=12 * HOURS,
)
def fetch(task: str = "701", convert: bool = True,
          keep_raw: bool = True, keep_zip: bool = False) -> str:
    """Download the dataset from Zenodo straight onto the Volume, then convert.

    This is the alternative to ``segtrain modal upload``, and on any connection
    slower than a datacenter's it is the better one: the 21 GB never touches your
    laptop. Conversion runs here too -- the argument for converting locally was
    that a rented GPU box bills by the hour whether or not the GPU is busy, and
    that does not apply to a CPU-only serverless function.

    The archive is downloaded *to the Volume* rather than to container-local
    disk, so a container that dies at 19 GB resumes instead of starting over.
    """
    args = ["--dest", DATASET, "--zip", f"{MOUNT}/Totalsegmentator_dataset_v201.zip"]
    if keep_zip:
        args.append("--keep-zip")

    cmd = [sys.executable, "/root/scripts/init_dataset.py", *args]
    print("+ " + " ".join(cmd), flush=True)
    code = subprocess.run(cmd, env={**os.environ, **CONTAINER_ENV}).returncode
    volume.commit()
    if code != 0:
        raise RuntimeError(f"dataset download failed with exit code {code}")

    if convert:
        code = _segtrain("convert", "--task", task, *_roots())
        volume.commit()
        if code != 0:
            raise RuntimeError(f"`segtrain convert` failed with exit code {code}")

    # Kept by default: every task converts from this tree, so the five Stage 2
    # datasets would each have to re-download it. Drop it only once all six
    # conversions are done and you want the ~30 GB back.
    if not keep_raw:
        shutil.rmtree(DATASET, ignore_errors=True)
        volume.commit()
        print(f"removed {DATASET}", flush=True)

    return f"fetched dataset; {'converted ' + task if convert else 'not converted'}"


@app.function(
    image=image,
    volumes={MOUNT: volume},
    # No GPU on purpose. Fingerprinting, planning and preprocessing are CPU and
    # disk bound; attaching a GPU here would burn ~$2/hour to leave it idle.
    cpu=CPU,
    memory=MEMORY_MB,
    timeout=6 * HOURS,
)
def prepare(task: str = "701", scheme: str = "official") -> str:
    """Link images into the task, then plan and preprocess."""
    # sys.path first: CONTAINER_ENV's PYTHONPATH reaches subprocesses, not this
    # process, so segtrain is not importable until /root/src is on the path.
    sys.path.insert(0, "/root/src")

    from segtrain.config import load_config, load_task
    from segtrain.convert import link_or_copy

    cfg = load_config(Path("/root/configs/dataset.yaml"), {
        "zenodo_root": DATASET,
        "nnunet_raw": f"{MOUNT}/nnUNet_raw",
        "nnunet_preprocessed": f"{MOUNT}/nnUNet_preprocessed",
        "nnunet_results": f"{MOUNT}/nnUNet_results",
        "runs_root": f"{MOUNT}/runs",
    })
    task_cfg = load_task(task)
    raw = task_cfg.raw_dir(cfg)

    # Images are uploaded once into shared_images and materialised per task.
    # link_or_copy already degrades hardlink -> symlink -> copy, which covers
    # whatever Modal's volume filesystem does or does not support.
    shared = Path(MOUNT) / "shared_images"
    linked = {}
    for split in ("imagesTr", "imagesTs"):
        src_dir = shared / split
        if not src_dir.is_dir():
            continue
        dst_dir = raw / split
        dst_dir.mkdir(parents=True, exist_ok=True)
        modes = set()
        for src in sorted(src_dir.glob("*.nii.gz")):
            modes.add(link_or_copy(src, dst_dir / src.name, "hardlink"))
        linked[split] = (len(list(dst_dir.glob("*.nii.gz"))), sorted(modes))
    print("images materialised:", linked, flush=True)

    volume.commit()

    for step in (["plan", "--task", task, "--scheme", scheme],
                 ["preprocess", "--task", task]):
        code = _segtrain(*step, *_roots())
        if code != 0:
            volume.commit()
            raise RuntimeError(f"`segtrain {step[0]}` failed with exit code {code}")
        volume.commit()

    return f"prepared {task_cfg.nnunet_name}"


@app.function(
    image=image,
    gpu=GPU,
    volumes={MOUNT: volume},
    cpu=CPU,
    memory=MEMORY_MB,
    # Modal's ceiling is 24 h. The trainer stops itself before this via
    # SEGTRAIN_MAX_SECONDS so the timeout is a backstop, not the mechanism.
    timeout=23 * HOURS,
    # For genuine crashes and preemption. A clean pause returns normally and is
    # handled by the driver loop instead.
    retries=modal.Retries(max_retries=3, initial_delay=0.0),
)
def train(
    task: str = "701",
    fold: int = 0,
    epochs: int | None = None,
    iterations: int | None = None,
    max_seconds: int = 22 * HOURS,
    save_every: int = 25,
    preview: bool = True,
) -> dict:
    """One training chunk. Resumes automatically if a checkpoint exists."""
    sys.path.insert(0, "/root/src")
    name = _task_name(task)
    run_dir = f"{MOUNT}/runs/{name}__fold{fold}"
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    resuming = _has_checkpoint(task, fold)
    print(f"task={name} fold={fold} resuming={resuming} budget={max_seconds}s", flush=True)

    env = {
        "SEGTRAIN_RUN_DIR": run_dir,
        "SEGTRAIN_TASK": name,
        "SEGTRAIN_MAX_SECONDS": str(max_seconds),
        "SEGTRAIN_SAVE_EVERY": str(save_every),
    }
    if epochs:
        env["SEGTRAIN_EPOCHS"] = str(epochs)
    if iterations:
        env["SEGTRAIN_ITERATIONS"] = str(iterations)

    # The preview daemon shares this container and its GPU. A separate Modal
    # function would mean a second billed GPU for what is a few seconds of
    # inference every N epochs. It is still its own process, so a preview crash
    # cannot take training down.
    preview_proc = None
    if preview:
        preview_proc = subprocess.Popen(
            [sys.executable, "-m", "segtrain.cli", "preview",
             "--task", task, "--fold", str(fold), "--watch",
             "--device", "cuda", "--poll", "60", *_roots()],
            env={**os.environ, **CONTAINER_ENV, **env},
        )

    try:
        args = ["train", "--task", task, "--fold", str(fold),
                "--device", "cuda", "--backend", "local", "--foreground", *_roots()]
        if resuming:
            args.append("--continue-training")
        if epochs:
            args += ["--epochs", str(epochs)]
        if iterations:
            args += ["--iterations", str(iterations)]
        code = _segtrain(*args, env=env)
    finally:
        if preview_proc is not None:
            preview_proc.terminate()
            try:
                preview_proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                preview_proc.kill()
        volume.commit()

    if code != 0:
        raise RuntimeError(f"training exited with code {code}")

    from segtrain.events import read_run

    state = read_run(Path(run_dir))
    return {
        "status": state.status,
        "epoch": state.current_epoch,
        "total_epochs": state.total_epochs,
        "finished": bool(state.status == "completed"),
    }


@app.function(
    image=image,
    gpu=GPU,
    volumes={MOUNT: volume},
    cpu=16.0,
    memory=MEMORY_MB,
    timeout=6 * HOURS,
)
def evaluate(task: str = "701", fold: int = 0,
             checkpoint: str = "checkpoint_best.pth") -> str:
    """Score the held-out test set on the volume."""
    code = _segtrain("evaluate", "--task", task, "--fold", str(fold),
                     "--device", "cuda", "--checkpoint", checkpoint, *_roots())
    volume.commit()
    if code != 0:
        raise RuntimeError(f"evaluation failed with exit code {code}")
    return f"evaluated {task} fold {fold}"


@app.function(image=image, volumes={MOUNT: volume}, timeout=600)
def inspect(path: str = "") -> str:
    """List part of the volume. Cheap sanity check after an upload."""
    target = Path(MOUNT) / path.lstrip("/")
    if not target.exists():
        return f"{target} does not exist"
    if target.is_file():
        return f"{target}  {target.stat().st_size} bytes"

    lines = []
    for child in sorted(target.iterdir())[:40]:
        if child.is_dir():
            lines.append(f"{child.name}/  ({sum(1 for _ in child.rglob('*'))} entries)")
        else:
            lines.append(f"{child.name}  {child.stat().st_size}")
    return "\n".join(lines) or "(empty)"


@app.local_entrypoint()
def main(task: str = "701", fold: int = 0, action: str = "prepare"):
    """Entry point for `modal run src/segtrain/modal_app.py`."""
    if action == "fetch":
        print(fetch.remote(task=task))
    elif action == "prepare":
        print(prepare.remote(task=task))
    elif action == "train":
        print(train.remote(task=task, fold=fold))
    elif action == "evaluate":
        print(evaluate.remote(task=task, fold=fold))
    elif action == "inspect":
        print(inspect.remote(""))
    else:
        raise SystemExit(f"unknown action {action!r}")
