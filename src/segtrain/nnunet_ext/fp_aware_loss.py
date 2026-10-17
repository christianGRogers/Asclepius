"""The FP-aware loss of run 3 (Round 8, A24; Atlas v9 §2.4).

    L = L_nnU-Net + lambda * mean over B of [ -p_fg(v)**gamma * log p_bg(v) ]

B is the set of voxels farther than ``band_mm`` from any labelled voxel (any class, ``ignore``
included), on the full-resolution output only. p_fg = 1 - p_bg, and the focal weight
p_fg**gamma is detached.

* **What it is for.** Run 2's census: 79 % of the raw FP components are confident (p90 >= 0.94),
  vessel-calibre tubes beside the tree, mostly cardiac veins. At ~0.8 % of the predicted foreground
  they are nearly free under DiceCE, while the gate counts each one.
* **What it leaves alone.** The band keeps the term away from the tree's boundary, where reads
  disagree about calibre (DiceCE handles that), and away from ``ignore`` voxels.
* **Sources.** Focal hard-negative weighting (Lin et al., ICCV 2017), restricted to voxels away
  from the annotated tree; instance-level FP penalties (Kofler et al., blob loss,
  arXiv 2205.08209) are the heavier relative this approximates without per-iteration
  connected components.

The band is a cubic max-pool dilation of the label by ``ceil(band_mm / spacing)`` voxels per axis
(Chebyshev distance), computed on the GPU. Torch only, so it is tested on CPU.
"""

from __future__ import annotations

import math
from typing import Sequence

import torch
import torch.nn.functional as F


def band_voxels(band_mm: float, spacing: Sequence[float]) -> list:
    return [max(0, int(math.ceil(band_mm / float(s)))) for s in spacing]


def far_background(target: torch.Tensor, radius: Sequence[int]) -> torch.Tensor:
    """Boolean (B, X, Y, Z): voxels farther than ``radius`` voxels (per axis) from any labelled
    voxel. ``target`` is nnU-Net's (B, 1, X, Y, Z) label tensor (0 = background)."""
    labelled = (target[:, :1] > 0).float()
    k = [2 * r + 1 for r in radius]
    near = F.max_pool3d(labelled, kernel_size=k, stride=1, padding=list(radius)) > 0
    return ~near[:, 0]


def fp_term(logits: torch.Tensor, target: torch.Tensor, radius: Sequence[int],
            gamma: float = 2.0) -> torch.Tensor:
    """Mean over far-background voxels of -p_fg**gamma * log p_bg (p_fg detached)."""
    logp = torch.log_softmax(logits.float(), dim=1)
    log_bg = logp[:, 0]
    p_fg = (1.0 - log_bg.exp()).clamp(min=0.0).detach()
    far = far_background(target, radius)
    if not bool(far.any()):
        return logits.sum() * 0.0
    per = -(p_fg ** gamma) * log_bg
    return per[far].mean()


class FPAwareLoss(torch.nn.Module):
    """Wraps nnU-Net's loss (DiceCE, deep-supervision wrapper included); adds the FP term on the
    full-resolution output. Keeps the last term value for logging."""

    def __init__(self, base, spacing: Sequence[float], lam: float = 1.0, gamma: float = 2.0,
                 band_mm: float = 1.5):
        super().__init__()
        self.base = base
        self.lam = float(lam)
        self.gamma = float(gamma)
        self.band_mm = float(band_mm)
        self.radius = band_voxels(band_mm, spacing)
        self.last_term = 0.0
        self.terms: list = []

    def forward(self, output, target):
        base = self.base(output, target)
        out0 = output[0] if isinstance(output, (list, tuple)) else output
        tgt0 = target[0] if isinstance(target, (list, tuple)) else target
        term = fp_term(out0, tgt0, self.radius, self.gamma)
        self.last_term = float(term.detach())
        if torch.is_grad_enabled():           # training steps only; validation runs under no_grad
            self.terms.append(self.last_term)
        return base + self.lam * term

    def describe(self) -> dict:
        return {"lambda": self.lam, "gamma": self.gamma, "band_mm": self.band_mm,
                "band_voxels": self.radius}
