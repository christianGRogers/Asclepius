"""Shared fixtures.

Tests that need the real TotalSegmentator dataset are marked ``needs_data`` and
skip cleanly when it is absent, so the suite still runs on a machine that only
has the code.
"""

import os
from pathlib import Path

import pytest

from segtrain.config import ConfigError, load_config

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def cfg():
    try:
        config = load_config()
    except ConfigError as exc:
        pytest.skip("no usable dataset config: {}".format(exc))
    if not config.meta_csv.is_file():
        pytest.skip("dataset not present at {}".format(config.zenodo_root))
    return config


@pytest.fixture(scope="session")
def meta_rows(cfg):
    from segtrain.splits import read_meta

    return read_meta(cfg.meta_csv)


@pytest.fixture(scope="session")
def sample_case(cfg):
    """A subject that has all 117 structures on disk."""
    for case_id in ("s0010", "s0011", "s0012"):
        seg = cfg.zenodo_root / case_id / "segmentations"
        if seg.is_dir() and len(list(seg.glob("*.nii.gz"))) == 117:
            return case_id
    pytest.skip("no complete subject found")


@pytest.fixture(scope="session")
def env_has_nnunet():
    return bool(os.environ.get("SEGTRAIN_TEST_NNUNET"))
