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
