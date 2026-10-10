"""A21 dry run: SegQueue export -> index -> convert -> splits -> reads-report, on the two real
SegQueue test submissions (binary, LPS, z-reversed, named imagecas_NNNN) with ImageCAS-X names
and a synthetic second read. The script is experiments/Echo/segqueue_dry_run.py; swap in the
first real approved export with ``--export <dir>``.

Needs the shared tournament cache (submissions, masks, CTs c0001/c0004, ImageCAS-X); skips
without it. The reads-report half takes ~20 min and ~4.5 GB on full volumes, so it runs only
with SEGTRAIN_DRY_RUN=1."""

import importlib.util
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "experiments" / "Echo" / "segqueue_dry_run.py"
SCR = Path("/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad")
NEEDED = [SCR / "data/submissions/imagecas_0002_attempt1.seg.nrrd",
          SCR / "data/submissions/imagecas_0005_attempt1.seg.nrrd",
          SCR / "data/ct/c0001.nii.gz", SCR / "data/ct/c0004.nii.gz",
          SCR / "data/masks/c0001.nii.gz", SCR / "data/masks/c0004.nii.gz",
          SCR / "work/Bridge/icx/segmentations/2.coronary.nii.gz",
          SCR / "work/Bridge/icx/segmentations/5.coronary.nii.gz",
          SCR / "work/Bridge/icx/train.txt"]

pytestmark = [pytest.mark.needs_data, pytest.mark.slow,
              pytest.mark.skipif(not all(p.is_file() for p in NEEDED) or not SCRIPT.is_file(),
                                 reason="tournament data cache not present")]


def _script():
    pytest.importorskip("SimpleITK")
    spec = importlib.util.spec_from_file_location("segqueue_dry_run", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_export_index_convert_splits(tmp_path):
    r = _script().run(tmp_path, report_step=False)
    assert r["ok"], r["checks"]


@pytest.mark.skipif(os.environ.get("SEGTRAIN_DRY_RUN") != "1",
                    reason="full dry run (~20 min, ~4.5 GB): set SEGTRAIN_DRY_RUN=1")
def test_full_dry_run_through_reads_report(tmp_path):
    r = _script().run(tmp_path, fast=True)
    assert r["ok"], r["checks"]
