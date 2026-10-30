"""PS3-S6 and PS3-S7 (JA54): the final Scar-0 menu, and the benchmark as a regression fixture.

Ruling: ``vault/JanusM/Judgements/Round 3 - paired-scar.md`` section 9, ``scar0.py``. Synthetic
phantoms only; the parity test uses the bench_lie phantom heart (no download, no real heart)."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import numpy as np
import pytest

from janusm import scar as SC
from janusm.scar import scar0 as S
from janusm.scar.common import CarriedGeometry

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "experiments" / "JanusM" / "bench_lie"


def strip_phantom(
    scar_layers, *, spacing=1.0, layers=10, scar_hu=150.0, bright_17=None, noise=5.0, seed=0, ny=24
):
    """A flat wall ``layers`` voxels thick along x (voxel ``spacing`` mm), the cavity below it.
    Segment s is a strip along z; its scar fills the first ``scar_layers[s - 1]`` layers from the
    endocardium at ``scar_hu``. Segment 17 is filled at ``bright_17`` when given (sets P-K's half-
    way cut). Columns are 2 x 2 lines; u is exact."""
    nx, per = layers + 6, 4
    nz = 17 * per
    x0 = 3
    i = np.arange(nx)[:, None, None] + np.zeros((nx, ny, nz), int)
    j = np.arange(ny)[None, :, None] + np.zeros((nx, ny, nz), int)
    k = np.arange(nz)[None, None, :] + np.zeros((nx, ny, nz), int)
    myo = (i >= x0) & (i < x0 + layers)
    cav = i < x0
    seg = np.where(myo, k // per + 1, 0).astype(np.int16)
    u = np.where(myo, (i - x0 + 0.5) / layers, np.nan).astype(np.float32)
    col = np.where(myo, (j // 2) * 1000 + k // 2, -1)
    depth = np.array([0] + list(scar_layers))[seg]
    scar = myo & (i - x0 < depth)
    lie = np.full(myo.shape, 85.0, np.float32)
    lie[scar] = scar_hu
    if bright_17 is not None:
        lie[myo & (seg == 17)] = bright_17
    lie += np.random.default_rng(seed).normal(0, noise, myo.shape).astype(np.float32)
    car = CarriedGeometry(
        myo, cav, seg, u, col, np.full(3, float(spacing)), np.diag([spacing] * 3 + [1.0])
    )
    return lie, car


# ------------------------------------------------------------------------------------------ PS3-S6
def test_ps3_s6_where_half_way_and_3sd_cuts_differ_e_d_follows_3sd():
    """A dim scar (120 HU) sits between the cuts: above remote + 3 SD, below P-K's half-way cut (set
    by a 250 HU segment 17). E-D follows 3 SD: it reads the scar, as E-V does, and P-K's half-way
    share reads nothing."""
    k = [0] * 11 + [5, 0, 0, 0, 0, 0]
    lie, car = strip_phantom(k, scar_hu=120.0, bright_17=250.0)
    out = S.scar0(lie, car, status=SC.PASSED)
    assert out.thresholds["sd"] < 120.0 < out.thresholds["half_way"]
    row = out.segments[12]
    assert row["share_pk"] == 0.0  # the half-way cut sees no scar
    assert row["share_ev"] == pytest.approx(0.55, abs=0.06)
    assert row["extent_ed"] == pytest.approx(0.6, abs=0.05)  # 5 layers + one blur layer, at 3 SD
    for s in range(1, 12):
        assert out.segments[s]["extent_ed"] == 0.0
    # E-D and E-V share one voxel cut (JA54): their deepest u is the same call
    assert row["deepest_ed"] == row["deepest_ev"] == pytest.approx(0.6)
    assert row["deepest_ed_median"] == row["deepest_ev_median"] == pytest.approx(0.6)


def test_ps3_s6_a_1mm_endocardial_rim_of_scar_only_gives_share_pg_0():
    """On a 1/3 mm grid the 1 mm rim is three voxel layers (d_endo 1/6, 1/2, 5/6 mm). A scar filling
    that rim only gives share_pg = 0; a 2 mm scar (segment 11, between equally deep neighbours so
    the opening keeps its edges) gives the share of the wall >= 1 mm from the endocardium (JA54's
    denominator): 3 called layers of 27, not of 30. Smoothing is off here so the test reads the
    rule, not the blur."""
    sharp = dataclasses.replace(S.JA30, smooth_fwhm_mm=1e-3)
    k = [0] * 8 + [3, 6, 6, 6] + [0] * 5
    lie, car = strip_phantom(k, spacing=1 / 3, layers=30, scar_hu=150.0, noise=5.0, ny=60)
    d = car.d_endo_mm()
    first = [float(d[3 + n, 0, 0]) for n in range(4)]
    assert first == pytest.approx([1 / 6, 1 / 2, 5 / 6, 7 / 6])
    out = S.scar0(lie, car, status=SC.PASSED, constants=sharp)
    rim, deeper = out.segments[9], out.segments[11]
    assert rim["share_ev"] == pytest.approx(0.1, abs=0.01)  # the rim is called...
    assert rim["share_pg"] == 0  # ...and P-G ignores it
    assert rim["n_voxels_pg"] == rim["n_voxels"] * 27 // 30
    assert deeper["share_pg"] == pytest.approx(
        3 / 27, abs=0.003
    )  # the whole-segment share would be 0.100
    assert out.presence("P-G")[9] is False and out.presence("P-G")[11] is True


def test_ps3_s6_choose_presence_p_k_raises():
    with pytest.raises(ValueError, match="struck"):
        S.choose_presence({"P-K": (0.99, 0.99)})
    with pytest.raises(ValueError, match="struck"):
        S.choose_presence({"P-J": (0.8, 0.96), "P-K": (0.9, 0.99)})
    assert S.PRESENCE == ("P-J", "P-G") and S.DIAGNOSTIC == ("P-K",)


def test_ps3_s6_p_k_is_computed_under_a_diagnostic_key_only():
    lie, car = strip_phantom([0] * 8 + [1, 2, 3, 4, 5, 6, 7, 9, 10])
    out = S.scar0(lie, car, status=SC.PASSED, tau=0.05)
    with pytest.raises(ValueError, match="struck"):
        out.presence("P-K")
    with pytest.raises(ValueError, match="struck"):
        out.for_scoring("P-K", "E-V")
    pk = out.diagnostic_presence("P-K")
    assert all(pk[s] is False for s in range(1, 9)) and all(pk[s] for s in range(9, 18))
    tab = out.table("P-J", "E-D")
    assert tab["presence_menu"] == ["P-J", "P-G"] and tab["diagnostic_candidates"] == ["P-K"]
    assert all(tab["segments"][s]["diagnostic_pk"] == pk[s] for s in range(1, 18))


def test_ps3_s6_deepest_median_over_columns():
    """One noisy column sets the "any column" deepest u; the median over columns does not move
    (Golf, #188 reading 4 kept beside it)."""
    k = [0] * 11 + [3, 0, 0, 0, 0, 0]
    lie, car = strip_phantom(k, noise=0.5)
    sel = (
        car.myo
        & (car.segments == 12)
        & (car.column == car.column[car.myo & (car.segments == 12)][0])
    )
    lie[sel] = 150.0  # one column scarred through the whole wall
    out = S.scar0(lie, car, status=SC.PASSED)
    row = out.segments[12]
    assert row["deepest_ed"] == pytest.approx(1.0)
    assert row["deepest_ed_median"] == pytest.approx(0.4)  # 3 layers + one blur layer
    tab = out.table("P-G", "E-D")["segments"][12]
    assert tab["deepest_u"] == pytest.approx(1.0) and tab["deepest_u_median"] == pytest.approx(0.4)
    assert (
        out.segments[1]["deepest_ed_median"] != out.segments[1]["deepest_ed_median"]
    )  # NaN without scar


def test_ps3_s6_for_scoring_returns_the_per_segment_kim_bin():
    from janusm.scar import scoring

    k = [0] * 8 + [1, 2, 3, 4, 5, 6, 7, 9, 10]
    lie, car = strip_phantom(k)
    got = S.scar0(lie, car, status=SC.PASSED, tau=0.05).for_scoring("P-J", "E-D")
    ref = np.array(
        [S.kim_bin(min(n / 10 + 0.1, 1.0), n > 0) for n in k]
    )  # E-D at 3 SD: one blur layer more
    assert np.array_equal(got.kim_bin, ref)
    assert got.kim_bin.shape == (17,) and set(got.kim_bin) <= {0, 1, 2, 3, 4}
    bins, shares = got
    scoring.Patient(ref=ref, ct=bins, ct_share=shares)
    ng = S.scar0(lie, car, status=SC.NOT_GRADED).for_scoring("P-G", "E-V")
    assert (ng.kim_bin == scoring.NOT_GRADED).all() and np.isnan(ng.share).all()


# ------------------------------------------------------------------------------------------ PS3-S7
@pytest.fixture(scope="module")
def parity_module():
    pytest.importorskip("scipy")
    sys.path.insert(0, str(BENCH))
    try:
        import module_parity
    finally:
        sys.path.remove(str(BENCH))
    return module_parity


def test_ps3_s7_ci_parity_test_on_the_bench_lie_phantom_heart(parity_module):
    """menu.grade and scar0 on the oracle geometry, every striking condition (CNR 5; motion none,
    rigid; blood below, equal, above): per-segment ev, ed and pg_share agree within 0.02. The
    phantom only; nothing is downloaded."""
    M = parity_module
    assert M.TOL == 0.02
    assert sorted(M.STRIKING) == sorted(
        (b, 5, m) for b in ("below", "equal", "above") for m in ("none", "rigid")
    )
    heart = M.bench.load_heart("phantom", None)
    rows = M.parity(heart)
    assert len(rows) == 6 and not any("skip" in r for r in rows)
    for r in rows:
        for key, res in r["parity"].items():
            assert res["n"] >= 15 and res["n_one_sided"] == 0, (r["blood"], r["motion"], key, res)
            assert res["max_abs_diff"] <= M.TOL, (r["blood"], r["motion"], key, res)
        assert r["pass"]
    s = M.summary(rows)
    assert s["n_pass"] == s["n_cases"] == 6


def test_ps3_s7_offline_script_guards_first(parity_module, monkeypatch, tmp_path):
    """The offline script calls the JA12 guard on the whole heart list before any heart is read."""
    M = parity_module
    calls = []

    class Refused(Exception):
        pass

    def guarded():
        calls.append("guard")
        raise Refused("guard refused")

    def load(*a, **k):  # pragma: no cover - must never be reached
        calls.append("load")
        raise AssertionError("a heart was read before the guard")

    fake_fetch = type(sys)("fetch")
    fake_fetch.hearts = guarded
    monkeypatch.setitem(sys.modules, "fetch", fake_fetch)
    monkeypatch.setattr(M.bench, "load_heart", load)
    monkeypatch.setattr(sys, "argv", ["module_parity.py", str(tmp_path)])
    with pytest.raises(Refused):
        M.main()
    assert calls == ["guard"]
    assert not (tmp_path / "module_parity.json").exists()
