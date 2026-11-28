"""The Janus 1-F stage-1 trainer (J1F-A; master plan - Janus 1-F §2, Delta v3 §4.1 as amended by F-A27 to F-A35).

``nnUNetTrainer_segtrain_finetune`` (no mirroring, sealed refusal, wall-clock pause and chain resume, 2500-iteration
linear warm-up to 1e-2 then poly, stepped per iteration) with what 1-F adds:

1. **The parent-copy load** (F-A2). ``SEGTRAIN_FINETUNE_FROM`` is Janus 0's ``checkpoint_final.pth`` and
   ``SEGTRAIN_FINETUNE_HEADS=parent_copy:<configs/janus1/j1f_parents.json>`` names the rule: non-head tensors strict
   and bitwise; every ``seg_layers`` head grown 5 -> 13 (:mod:`segtrain.nnunet_ext.parent_copy`).
2. **The step-0 identity**, on one real training patch before the first step: territory sums of the 13-channel
   softmax equal Janus 0's within 1e-5 and the hierarchical decode's territory equals Janus 0's argmax. Refuses
   otherwise.
3. **500 epochs** (two 23:50 links; ``SEGTRAIN_EPOCHS`` / ``SEGTRAIN_ITERATIONS`` must be unset), DiceCE unweighted
   (Step T), ignore label 13 (F-A29: from dataset.json; refused otherwise).
4. **No locked-100 id ever reaches nnU-Net** (F-A20): ``on_train_start`` refuses any id of
   ``configs/janus1/split-2026-11.json``'s locked 100 in the split, and any split whose val is not the 20
   fit-check training cases.
5. **The fit check** (F-A5) after epochs 150 and 300: the 20 val cases (training cases) predicted, decoded as F,
   Dice per class to ``fitcheck.json``; at 150, D1, OM1, PDA or PLB below 0.10 writes ``STALL``.
6. **Final validation is a no-op** (``perform_actual_validation``): nothing is validated on the locked 100, and
   ``checkpoint_best`` is never read.
"""

from __future__ import annotations

import hashlib
import json
import os

import numpy as np
import torch

from segtrain.nnunet_ext.nnUNetTrainer_segtrain_finetune import nnUNetTrainer_segtrain_finetune
from segtrain.nnunet_ext.parent_copy import F_GROUPS, load_parent_copy, step0_identity

J1F_EPOCHS = 500
FITCHECK_EPOCHS = (150, 300)
STALL_LINE = 0.10
STALL_CLASSES = ("D1", "OM1", "PDA", "PLB")
FITCHECK_SALT = "asclepius-j1f-fitcheck:"
NAMES = ("background", "LM", "LAD", "LCx", "RCA", "D1", "D2", "D3", "OM1", "OM2", "Ramus", "PDA", "PLB")
IGNORE = 13
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SPLIT_PATH = os.path.join(_REPO, "configs", "janus1", "split-2026-11.json")
SPLIT_SHA256 = "19b832fee023986e1dc64b724fbf218fce71942b7f3908f5ae110388ca1b4dd3"


def heads_rule(value: str) -> str:
    """``parent_copy:<path>`` -> path; anything else refuses."""
    if not value or not value.startswith("parent_copy:"):
        raise RuntimeError("nnUNetTrainer_janus1f needs SEGTRAIN_FINETUNE_HEADS=parent_copy:<j1f_parents.json>")
    return value[len("parent_copy:"):]


def fitcheck_ids(train) -> list:
    ranked = sorted(train, key=lambda c: hashlib.sha256((FITCHECK_SALT + c).encode()).hexdigest())
    return sorted(ranked[:20])


def load_split(path: str = SPLIT_PATH) -> dict:
    with open(path, "rb") as fh:
        raw = fh.read()
    if path == SPLIT_PATH and hashlib.sha256(raw).hexdigest() != SPLIT_SHA256:
        raise RuntimeError(f"{path} is not the pinned D45 split (#306); refusing")
    return json.loads(raw)


def check_keys(tr_keys, val_keys, split: dict) -> None:
    """F-A20's val test, on what nnU-Net is about to read."""
    locked = set(split["locked100"])
    bad = sorted((set(tr_keys) | set(val_keys)) & locked)
    if bad:
        raise RuntimeError(f"refusing to train: locked-100 id(s) in the split: {bad[:3]} (F-A20)")
    if sorted(tr_keys) != sorted(split["train620"]):
        raise RuntimeError("refusing to train: the training keys are not the D45 620")
    if sorted(val_keys) != fitcheck_ids(split["train620"]):
        raise RuntimeError("refusing to train: val is not the 20 fit-check training cases (F-A5, F-A20)")


def decode_f(prob: np.ndarray) -> np.ndarray:
    """F: territory = argmax of summed group probabilities, class = argmax inside it."""
    terr = np.argmax(np.stack([prob[list(g)].sum(0) for g in F_GROUPS]), 0)
    out = np.zeros(terr.shape, np.uint8)
    for t, g in enumerate(F_GROUPS):
        g = np.asarray(g)
        m = terr == t
        if m.any():
            out[m] = g[np.argmax(prob[g][:, m], 0)]
    return out


def dice_per_class(pred: np.ndarray, ref: np.ndarray) -> dict:
    """Dice of each foreground class; ignore-13 voxels left out; None when both are empty."""
    keep = ref != IGNORE
    out = {}
    for c in range(1, len(NAMES)):
        a, b = (pred == c) & keep, (ref == c) & keep
        s = int(a.sum()) + int(b.sum())
        out[NAMES[c]] = None if s == 0 else 2.0 * int((a & b).sum()) / s
    return out


def stall(mean_dice: dict, epoch: int) -> list:
    """F-A5: at epoch 150, the stall classes below 0.10."""
    if epoch != FITCHECK_EPOCHS[0]:
        return []
    return [c for c in STALL_CLASSES if mean_dice.get(c) is not None and mean_dice[c] < STALL_LINE]


class nnUNetTrainer_janus1f(nnUNetTrainer_segtrain_finetune):
    """J1F-A: 13 outputs, warm from Janus 0 by parent copy, 500 epochs, fit check at 150 and 300."""

    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device("cuda")):  # noqa: B008
        for var in ("SEGTRAIN_EPOCHS", "SEGTRAIN_ITERATIONS"):
            if os.environ.get(var):
                raise RuntimeError(f"nnUNetTrainer_janus1f: {var} must be unset (500 x 250 is the recipe)")
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = J1F_EPOCHS
        self.parents_path = heads_rule(os.environ.get("SEGTRAIN_FINETUNE_HEADS", ""))
        self._source_heads = None
        self._identity = None
        if (dataset_json.get("labels") or {}).get("ignore") != IGNORE:
            raise RuntimeError("nnUNetTrainer_janus1f: dataset.json must carry ignore 13 (F-A29)")

    # -- the load ------------------------------------------------------------------
    def initialize(self):
        # skip the finetune parent's strict same-classes load; do the parent copy instead
        src, self.finetune_source = self.finetune_source, None
        try:
            super().initialize()
        finally:
            self.finetune_source = src
        if self.finetune_source and self._finetune_summary is None:
            summary = load_parent_copy(self.network, self.finetune_source, self.parents_path,
                                       self.plans_manager.plans, self.configuration_name, self.dataset_json,
                                       map_location=str(self.device))
            self._source_heads = summary.pop("_source_heads")
            self._finetune_summary = summary
            self.print_to_log_file(f"[janus1f] Janus 0 loaded by parent copy: {summary}")

    def do_split(self):
        tr, val = super().do_split()
        check_keys(tr, val, load_split())
        return tr, val

    def on_train_start(self) -> None:
        resumed = int(self.current_epoch) > 0
        super().on_train_start()
        if not resumed:
            if self._source_heads is None:
                raise RuntimeError("nnUNetTrainer_janus1f: no parent-copy load happened; refusing")
            batch = next(self.dataloader_train)
            x = batch["data"].to(self.device, non_blocking=True)
            self._identity = step0_identity(self.network, x, self._source_heads)
            self.print_to_log_file(f"[janus1f] step-0 identity: {self._identity}")
            self._write_json("step0_identity.json", self._identity)

    # -- the fit check (F-A5) ------------------------------------------------------
    def on_epoch_end(self) -> None:
        done = int(self.current_epoch) + 1          # epochs completed after this one
        super().on_epoch_end()
        if done in FITCHECK_EPOCHS:
            try:
                self.fit_check(done)
            except Exception as exc:                # a failed fit check never stops training
                self.print_to_log_file(f"[janus1f] fit check at epoch {done} failed: {exc!r}")

    def fit_check(self, epoch: int) -> dict:
        from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

        self.set_deep_supervision_enabled(False)
        self.network.eval()
        try:
            predictor = nnUNetPredictor(tile_step_size=0.5, use_gaussian=True, use_mirroring=False,
                                        perform_everything_on_device=True, device=self.device, verbose=False,
                                        verbose_preprocessing=False, allow_tqdm=False)
            predictor.manual_initialization(self.network, self.plans_manager, self.configuration_manager, None,
                                            self.dataset_json, self.__class__.__name__, None)
            _, val_keys = self.do_split()
            ds = self.dataset_class(self.preprocessed_dataset_folder, val_keys,
                                    folder_with_segs_from_previous_stage=self.folder_with_segs_from_previous_stage)
            per_case = {}
            for k in ds.identifiers:
                data, seg, _, _ = ds.load_case(k)
                with torch.no_grad():
                    logits = predictor.predict_sliding_window_return_logits(torch.from_numpy(np.asarray(data[:])))
                prob = torch.softmax(logits.float(), 0).cpu().numpy()
                per_case[k] = dice_per_class(decode_f(prob), np.asarray(seg[:])[0])
        finally:
            self.set_deep_supervision_enabled(self.enable_deep_supervision)
            self.network.train()
        mean = {}
        for c in NAMES[1:]:
            v = [d[c] for d in per_case.values() if d[c] is not None]
            mean[c] = float(np.mean(v)) if v else None
        st = stall(mean, epoch)
        out = {"epoch": epoch, "cases": sorted(per_case), "mean_dice": mean, "per_case": per_case,
               "stall_line": STALL_LINE, "stall_classes": st}
        path = os.path.join(self.output_folder, "fitcheck.json")
        prev = {}
        if os.path.exists(path):
            with open(path) as fh:
                prev = json.load(fh)
        prev[str(epoch)] = out
        self._write_json("fitcheck.json", prev)
        if st:
            with open(os.path.join(self.output_folder, "STALL"), "w") as fh:
                fh.write(f"epoch {epoch}: {', '.join(st)} below {STALL_LINE} (F-A5); the PM may cancel\n")
        self.print_to_log_file(f"[janus1f] fit check at epoch {epoch}: mean Dice {mean}; stall {st or 'none'}")
        return out

    def _write_json(self, name: str, obj) -> None:
        p = os.path.join(self.output_folder, name)
        with open(p + ".part", "w") as fh:
            json.dump(obj, fh, indent=1)
        os.replace(p + ".part", p)

    # -- never validate ------------------------------------------------------------
    def perform_actual_validation(self, save_probabilities: bool = False):
        self.print_to_log_file("[janus1f] final validation skipped (F-A20): the locked 100 is scored only by "
                               "`collect`")
