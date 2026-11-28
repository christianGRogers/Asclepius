"""Janus 1-F stage 1's training rules, torch-free (so CI tests them without torch): the split and
val test (F-A20), the fit-check ids, decode F and Dice (F-A5), and the STALL rule. Used by
:mod:`segtrain.nnunet_ext.nnUNetTrainer_janus1f`."""

from __future__ import annotations

import hashlib
import json
import os

import numpy as np

#: F's decode groups (F-A4): territory -> 1-F channels
F_GROUPS = ((0,), (1,), (2, 5, 6, 7), (3, 8, 9, 10), (4, 11, 12))

J1F_EPOCHS = 500
FITCHECK_EPOCHS = (150, 300)
STALL_LINE = 0.10
STALL_CLASSES = ("D1", "OM1", "PDA", "PLB")
FITCHECK_SALT = "asclepius-j1f-fitcheck:"
NAMES = (
    "background",
    "LM",
    "LAD",
    "LCx",
    "RCA",
    "D1",
    "D2",
    "D3",
    "OM1",
    "OM2",
    "Ramus",
    "PDA",
    "PLB",
)
IGNORE = 13
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SPLIT_PATH = os.path.join(_REPO, "configs", "janus1", "split-2026-11.json")
SPLIT_SHA256 = "19b832fee023986e1dc64b724fbf218fce71942b7f3908f5ae110388ca1b4dd3"


def heads_rule(value: str) -> str:
    """``parent_copy:<path>`` -> path; anything else refuses."""
    if not value or not value.startswith("parent_copy:"):
        raise RuntimeError(
            "nnUNetTrainer_janus1f needs SEGTRAIN_FINETUNE_HEADS=parent_copy:<j1f_parents.json>"
        )
    return value[len("parent_copy:") :]


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
        raise RuntimeError(
            "refusing to train: val is not the 20 fit-check training cases (F-A5, F-A20)"
        )


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
