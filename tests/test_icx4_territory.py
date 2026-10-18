"""The icx4 training labels collapse ImageCAS-X exactly as SegQueue14 does (D25).

``trillium/icx4/lib/territory.py`` is a copy (the Trillium job venv has no
segtrain); this pins it to ``segqueue14.labels.ICX14_TO_4`` and to
``segtrain.reads.icx_to_territory``.
"""

import importlib.util
from pathlib import Path

import numpy as np

from segqueue14 import labels
from segtrain.reads import icx_to_territory

_PATH = Path(__file__).resolve().parents[1] / "trillium" / "icx4" / "lib" / "territory.py"


def _territory():
    spec = importlib.util.spec_from_file_location("icx4_territory", _PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_table_is_segqueue14s():
    table = _territory().TERRITORY
    for value in range(1, 14):
        assert table[value] == labels.ICX14_TO_4[value], value
    assert table[0] == 0


def test_other_takes_the_nearest_lad_or_lcx_and_nothing_is_lost():
    vol = np.zeros((5, 5, 20), np.int64)
    vol[2, 2, 0:4] = 2        # LAD
    vol[2, 2, 16:20] = 6      # OM1 -> LCx
    vol[2, 2, 4:6] = 14       # Other beside the LAD
    vol[2, 2, 14:16] = 14     # Other beside the marginal
    out = _territory().to_four(vol, (0.5, 0.5, 0.5))
    assert out[2, 2, 4] == out[2, 2, 5] == labels.LABEL_VALUES["LAD"]
    assert out[2, 2, 14] == out[2, 2, 15] == labels.LABEL_VALUES["LCx"]
    assert int((out > 0).sum()) == int((vol > 0).sum())
    assert np.array_equal(out, icx_to_territory(vol))


ANISO = (0.35, 0.35, 0.5)  # ImageCAS-like voxel size, array-axis order


def test_voxel_and_mm_distance_pick_different_parents():
    """Other at the origin: the LAD is 3 voxels away along the 0.5 mm axis (1.5 mm), the
    LCx 4 voxels away along a 0.35 mm axis (1.4 mm). In voxels the LAD is nearer, in mm
    the LCx is; D25 means mm (what icx4 trains on)."""
    vol = np.zeros((6, 2, 5), np.int64)
    vol[0, 0, 0] = 14
    vol[0, 0, 3] = 2   # LAD
    vol[4, 0, 0] = 3   # LCx
    lad, lcx = labels.LABEL_VALUES["LAD"], labels.LABEL_VALUES["LCx"]
    assert icx_to_territory(vol)[0, 0, 0] == lad              # voxel units
    assert icx_to_territory(vol, ANISO)[0, 0, 0] == lcx       # mm
    assert _territory().to_four(vol, ANISO)[0, 0, 0] == lcx


def test_other_between_lad_and_lcx_matches_icx4_on_an_anisotropic_grid():
    """An Other blob between an LAD (running along axis 0) and an LCx (along axis 2)."""
    vol = np.zeros((16, 3, 16), np.int64)
    vol[:, 1, 15] = 2          # LAD
    vol[15, 1, :] = 6          # OM1 -> LCx
    vol[2:14, 1, 2:14] = 14    # Other filling the corner between them
    four = _territory().to_four(vol, ANISO)
    ours = icx_to_territory(vol, ANISO)
    assert np.array_equal(ours, four)
    assert int((ours > 0).sum()) == int((vol > 0).sum())
    # The grid is anisotropic enough that voxel units give a different answer here.
    assert not np.array_equal(icx_to_territory(vol), four)


def test_segtrain_copies_of_the_table_are_segqueue14s():
    """namer and proxy keep their own 1-13 tables (Other left at 0 for later naming)."""
    from segtrain import namer, proxy

    for table in (namer.ICX_TO_4, proxy.ICX_TO_4):
        assert {k: v for k, v in table.items() if v} == labels.ICX14_TO_4
        assert table.get(14, 0) == 0
