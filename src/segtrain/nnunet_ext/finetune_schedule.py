"""The fine-tune learning-rate schedule (Round 6, A17a): a linear warm-up over a stated number of
**iterations**, then nnU-Net's poly decay over the rest. Torch-free, so it can be tested without
nnU-Net.

lr(i) = peak * (i + 1) / W                      for 0 <= i < W   (peak at i = W - 1)
lr(i) = peak * (1 - (i - W) / (T - W)) ** 0.9   for W <= i < T   (nnU-Net's poly form)

with W the warm-up length and T the total number of iterations (epochs x iterations per epoch).
Default W = 2500 iterations = 10 epochs of 250: a deviation from Wald et al. (CVPR 2025), whose
nnU-Net fine-tuning warm-up was 50 epochs (12.5k iterations); see Atlas v8 §2.7.1.
"""

from __future__ import annotations

DEFAULT_WARMUP_ITERS = 2500
POLY_EXPONENT = 0.9


def warmup_poly_lr(iteration: int, peak_lr: float, warmup_iters: int, total_iters: int,
                   exponent: float = POLY_EXPONENT) -> float:
    """The learning rate for 0-based ``iteration``."""
    if total_iters <= 0 or peak_lr <= 0:
        raise ValueError("total_iters and peak_lr must be positive")
    warmup_iters = max(0, min(int(warmup_iters), int(total_iters)))
    i = max(0, int(iteration))
    if i < warmup_iters:
        return peak_lr * (i + 1) / warmup_iters
    decay = total_iters - warmup_iters
    if decay <= 0:
        return peak_lr
    frac = min(1.0, (i - warmup_iters) / decay)
    return peak_lr * (1.0 - frac) ** exponent


class WarmupPolyScheduler:
    """Sets ``optimizer.param_groups[*]['lr']`` per iteration. Duck-typed on the optimizer, so the
    schedule itself needs no torch. ``step(i)`` sets and returns the LR of iteration ``i``."""

    def __init__(self, optimizer, peak_lr: float, warmup_iters: int, total_iters: int,
                 exponent: float = POLY_EXPONENT):
        self.optimizer = optimizer
        self.peak_lr = float(peak_lr)
        self.warmup_iters = int(warmup_iters)
        self.total_iters = int(total_iters)
        self.exponent = exponent
        self._last_lr = [self.lr_at(0)]

    def lr_at(self, iteration: int) -> float:
        return warmup_poly_lr(iteration, self.peak_lr, self.warmup_iters, self.total_iters,
                              self.exponent)

    def step(self, iteration: int) -> float:
        lr = self.lr_at(iteration)
        for group in self.optimizer.param_groups:
            group["lr"] = lr
        self._last_lr = [lr]
        return lr

    def get_last_lr(self) -> list:
        return self._last_lr

    def describe(self) -> dict:
        return {"peak_lr": self.peak_lr, "warmup_iters": self.warmup_iters,
                "total_iters": self.total_iters, "poly_exponent": self.exponent,
                "lr_first": self.lr_at(0), "lr_end_of_warmup": self.lr_at(self.warmup_iters - 1),
                "lr_last": self.lr_at(self.total_iters - 1)}
