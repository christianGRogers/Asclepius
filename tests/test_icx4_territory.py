"""The icx4 training labels collapse ImageCAS-X exactly as SegQueue14 does (D25).

``trillium/icx4/lib/territory.py`` is a copy (the Trillium job venv has no
segtrain); this pins it to ``segqueue14.labels.ICX14_TO_4`` and to
``segtrain.reads.icx_to_territory``, and pins ``segqueue14.labels.icx14_to_four``
(the SegQueue14 scorer and reference overlay) to both.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

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


# ------------------------------------------------- SegQueue14's own collapse (#57, #68)
# ``labels.icx14_to_four`` is what the SegQueue14 scorer and the reviewer's reference
# overlay use. It must give exactly the icx4 training labels.


def _random_icx(seed, shape=(18, 14, 22)):
    rng = np.random.default_rng(seed)
    vol = np.zeros(shape, np.int64)
    mask = rng.random(shape) < 0.25
    vol[mask] = rng.integers(1, 15, size=int(mask.sum()))
    return vol


def test_segqueue14_collapse_is_the_icx4_training_collapse():
    for seed in range(5):
        vol = _random_icx(seed)
        assert (vol == labels.ICX_OTHER).any()
        four = _territory().to_four(vol, ANISO)
        assert np.array_equal(labels.icx14_to_four(vol, ANISO), four), seed
        assert np.array_equal(labels.icx14_to_four(vol, ANISO), icx_to_territory(vol, ANISO))


def test_segqueue14_collapse_without_scipy(monkeypatch):
    """Slicer may not ship scipy; the numpy search must give the same collapse.

    Exact on tie-free fixtures. On dense random volumes an Other voxel can have two
    LAD/LCx voxels at the same distance (its two neighbours along one axis), which
    either search may break its own way, so there each Other voxel must just take a
    class found at the minimal distance."""
    fixed = []
    for shape, lad, lcx, other in (((16, 3, 16), (slice(None), 1, 15), (15, 1, slice(None)),
                                    (slice(2, 14), 1, slice(2, 14))),
                                   ((5, 5, 20), (2, 2, slice(0, 4)), (2, 2, slice(16, 20)),
                                    (2, 2, slice(4, 16)))):
        vol = np.zeros(shape, np.int64)
        vol[lad], vol[lcx], vol[other] = 2, 6, 14
        fixed.append(vol)
    uneven = (0.3471, 0.3529, 0.5013)  # no two LAD/LCx distances tie on these
    expected = [_territory().to_four(v, uneven) for v in fixed]
    randoms = [_random_icx(seed) for seed in range(3)]
    tables = [_territory().TERRITORY[v] for v in randoms]
    monkeypatch.setitem(sys.modules, "scipy.spatial", None)  # import now fails
    with pytest.raises(ImportError):
        from scipy.spatial import cKDTree  # noqa: F401
    for vol, want in zip(fixed, expected):
        assert np.array_equal(labels.icx14_to_four(vol, uneven), want)

    for seed, (vol, base) in enumerate(zip(randoms, tables)):
        got = labels.icx14_to_four(vol, ANISO)
        src = np.argwhere(np.isin(base, (2, 3)))
        for p in np.argwhere(vol == labels.ICX_OTHER):
            d = (((src - p) * ANISO) ** 2).sum(axis=1)
            nearest = {int(base[tuple(q)]) for q in src[np.isclose(d, d.min())]}
            assert int(got[tuple(p)]) in nearest, (seed, p)

    # Small chunks: the same answer however the queries are split.
    pts = np.argwhere(_random_icx(0) > 0).astype(float) * ANISO
    assert np.array_equal(labels._nearest(pts, pts[::7], use_scipy=False, budget=50),
                          labels._nearest(pts, pts[::7], use_scipy=False))


def test_a_reference_with_nothing_above_four_is_still_imagecas_x():
    """#57: LM, LAD, LCx and D1 only -- max value 4, no RCA. The 4 is a D1, so LAD."""
    vol = np.array([[[0, 1, 2, 3, 4]]])
    assert labels.icx14_to_four(vol).tolist() == [[[0, 1, 2, 3, 2]]]


def test_other_with_no_lad_or_lcx_and_unknown_values_are_background():
    vol = np.array([[[1, 9, 14, 15, 200, -1]]])
    assert labels.icx14_to_four(vol, ANISO).tolist() == [[[1, 4, 0, 0, 0, 0]]]


def test_labels_still_imports_without_numpy():
    """segqueue14.labels loads in Slicer and the server's API process; numpy is only
    needed when a reference is actually collapsed."""
    code = ("import sys; sys.modules['numpy'] = None; "
            "from segqueue14 import labels; print(labels.N_CLASSES)")
    src = str(Path(__file__).resolve().parents[1] / "src")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env={**os.environ, "PYTHONPATH": src}, check=True)
    assert out.stdout.strip() == "4"
