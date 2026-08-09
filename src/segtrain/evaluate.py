"""Held-out evaluation: Dice and NSD per structure over the 89 test cases.

These 89 cases never enter ``imagesTr``, so nothing about them has influenced
training, plans, checkpoint selection or postprocessing. That is the only way
the numbers mean anything.

Output is two CSVs -- one row per (case, structure) and one row per structure --
plus a printable summary. Per-case rows are kept because the aggregate hides the
thing you usually need: whether a mediocre mean comes from uniform mediocrity or
from a handful of catastrophic cases.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional, Sequence

import nibabel as nib
import numpy as np

from .config import Config, TaskConfig
from .metrics import DEFAULT_NSD_TOLERANCE_MM, ClassScore, aggregate, nanmean, score_case


def predict_test_set(
    cfg: Config,
    task: TaskConfig,
    fold: int = 0,
    checkpoint_name: str = "checkpoint_best.pth",
    device: str = "cuda",
    output_dir: Optional[Path] = None,
    limit: Optional[int] = None,
) -> Path:
    """Run inference over imagesTs. Returns the folder of predictions."""
    import torch
    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

    raw = task.raw_dir(cfg)
    images_ts = raw / "imagesTs"
    if not images_ts.is_dir():
        raise FileNotFoundError(f"no test images at {images_ts}; run `segtrain convert` first")

    out = Path(output_dir) if output_dir else (task.run_dir(cfg, fold) / "test_predictions")
    out.mkdir(parents=True, exist_ok=True)

    model_folder = (
        task.results_dir(cfg) / f"{task.trainer}__{task.plans_name}__{task.configuration}"
    )
    predictor = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        # Mirroring IS enabled here, unlike in previews: this is the final number
        # and nnU-Net's default inference includes test-time augmentation.
        use_mirroring=True,
        perform_everything_on_device=(device != "cpu"),
        device=torch.device(device),
        verbose=False,
        allow_tqdm=False,
    )
    predictor.initialize_from_trained_model_folder(
        str(model_folder), use_folds=(fold,), checkpoint_name=checkpoint_name
    )

    files = sorted(images_ts.glob("*_0000.nii.gz"))
    if limit:
        files = files[:limit]
    if not files:
        raise FileNotFoundError(f"no *_0000.nii.gz under {images_ts}")

    predictor.predict_from_files(
        [[str(f)] for f in files],
        [str(out / f.name.replace("_0000.nii.gz", "")) for f in files],
        # Probability maps are float16 per class per voxel -- hundreds of GB
        # across a group model's test set, and only needed for cross-fold
        # ensembling, which single-fold evaluation does not do.
        save_probabilities=False,
        overwrite=True,
        num_processes_preprocessing=2,
        num_processes_segmentation_export=2,
    )
    return out


def score_predictions(
    cfg: Config,
    task: TaskConfig,
    predictions_dir: Path,
    tolerance_mm: float = DEFAULT_NSD_TOLERANCE_MM,
    compute_nsd: bool = True,
    limit: Optional[int] = None,
    progress: Optional[callable] = None,
) -> dict[str, list[ClassScore]]:
    """Score every prediction against its ground truth in labelsTs."""
    labels_ts = task.raw_dir(cfg) / "labelsTs"
    names = task.label_set.names
    preds = sorted(Path(predictions_dir).glob("*.nii.gz"))
    if limit:
        preds = preds[:limit]

    per_case: dict[str, list[ClassScore]] = {}
    for i, pred_path in enumerate(preds, start=1):
        case_id = pred_path.name[: -len(".nii.gz")]
        ref_path = labels_ts / f"{case_id}.nii.gz"
        if not ref_path.is_file():
            continue

        pred_img = nib.load(str(pred_path))
        ref_img = nib.load(str(ref_path))
        spacing = [float(z) for z in ref_img.header.get_zooms()[:3]]
        per_case[case_id] = score_case(
            np.asanyarray(pred_img.dataobj).astype(np.uint8),
            np.asanyarray(ref_img.dataobj).astype(np.uint8),
            names,
            spacing,
            tolerance_mm=tolerance_mm,
            compute_nsd=compute_nsd,
        )
        if progress:
            progress(i, len(preds))
    return per_case


def write_reports(
    per_case: dict[str, list[ClassScore]],
    out_dir: Path,
    prefix: str = "test",
) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_case_csv = out_dir / f"{prefix}_per_case.csv"
    with open(per_case_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["case", "structure", "label", "dice", "nsd",
                            "ref_voxels", "pred_voxels"]
        )
        writer.writeheader()
        for case_id, scores in sorted(per_case.items()):
            for s in scores:
                writer.writerow({"case": case_id, **s.as_row()})

    agg = aggregate(per_case)
    per_structure_csv = out_dir / f"{prefix}_per_structure.csv"
    with open(per_structure_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["structure", "dice", "nsd", "n_cases_present", "n_cases"]
        )
        writer.writeheader()
        for name, row in sorted(agg.items(), key=lambda kv: kv[1]["dice"]):
            writer.writerow({"structure": name, **row})

    return per_case_csv, per_structure_csv


def summarize(per_case: dict[str, list[ClassScore]], n_worst: int = 10) -> str:
    if not per_case:
        return "no cases scored"

    agg = aggregate(per_case)
    all_dice = [s.dice for scores in per_case.values() for s in scores]
    all_nsd = [s.nsd for scores in per_case.values() for s in scores]

    lines = [
        f"cases scored:      {len(per_case)}",
        f"structures:        {len(agg)}",
        f"mean Dice:         {nanmean(all_dice):.4f}",
        f"mean NSD:          {nanmean(all_nsd):.4f}",
        "",
        f"weakest {n_worst} structures by Dice:",
        f"  {'structure':<32} {'dice':>7} {'nsd':>7} {'cases':>6}",
    ]
    ranked = sorted(agg.items(), key=lambda kv: (kv[1]["dice"] != kv[1]["dice"], kv[1]["dice"]))
    for name, row in ranked[:n_worst]:
        lines.append(
            f"  {name:<32} {row['dice']:>7.4f} {row['nsd']:>7.4f} "
            f"{int(row['n_cases_present']):>6}"
        )

    # A structure present in very few test cases has a statistically meaningless
    # score; flagging it prevents over-reading a single bad case.
    rare = [(n, r) for n, r in agg.items() if r["n_cases_present"] < 5]
    if rare:
        lines.append("")
        lines.append(f"present in fewer than 5 test cases ({len(rare)}), scores are noisy:")
        lines.append("  " + ", ".join(sorted(n for n, _ in rare)))
    return "\n".join(lines)


def wilcoxon(a: Sequence[float], b: Sequence[float]) -> Optional[tuple[float, float]]:
    """Paired Wilcoxon signed-rank test, as used in the reference paper.

    Pairs where either value is NaN are dropped rather than imputed. Returns
    None when too few pairs remain for the test to mean anything.
    """
    from scipy.stats import wilcoxon as _w

    pairs = [(x, y) for x, y in zip(a, b) if x == x and y == y]
    if len(pairs) < 6:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    if all(x == y for x, y in pairs):
        return None
    stat, p = _w(xs, ys)
    return float(stat), float(p)
