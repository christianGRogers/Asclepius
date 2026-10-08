"""Fixed-CT-window check used by ``nnUNetTrainer_segtrain_coronary``; torch-free so it is testable without nnU-Net.

The master plan fixes the CT window at [-300, 1300] HU instead of nnU-Net's labelled-voxel percentiles (vault:
"Atlas - nnU-Net's automatic CT window on lumen labels flattens 38 percent of the heart box").
"""

from __future__ import annotations

import os

CT_WINDOW = (-300.0, 1300.0)


def expected_window() -> tuple[float, float] | None:
    """The CT window the trainer requires in the plans, or None if the check is disabled."""
    raw = os.environ.get("SEGTRAIN_CT_WINDOW", "").strip()
    if raw.lower() == "off":
        return None
    if raw:
        lo, hi = (float(x) for x in raw.split(","))
        return (lo, hi)
    return CT_WINDOW


def plans_window(plans: dict) -> tuple[float, float] | None:
    """(low, high) HU clip range of channel 0 in a plans dict, or None if absent."""
    props = (plans.get("foreground_intensity_properties_per_channel") or {}).get("0") or {}
    if "percentile_00_5" not in props or "percentile_99_5" not in props:
        return None
    return (float(props["percentile_00_5"]), float(props["percentile_99_5"]))


def check_window(plans: dict, expected: tuple[float, float] | None) -> None:
    """Raise if the plans' CT window is not the expected fixed one (no-op when expected is None)."""
    if expected is None:
        return
    got = plans_window(plans)
    if got is None or abs(got[0] - expected[0]) > 1e-3 or abs(got[1] - expected[1]) > 1e-3:
        raise RuntimeError(
            f"plans CT window is {got}, expected the fixed window {expected}. Run segtrain.plans.finalize_plans "
            "(or plan with the task's ct_window) and re-preprocess; or set SEGTRAIN_CT_WINDOW=off for the window "
            "ablation."
        )
