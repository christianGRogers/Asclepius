"""Janus-M path B: LIE registration (JA29) and Scar-0 (JA30), on phantoms only.

Fixtures (no real, public or held-out case is opened anywhere here):

- **Juliet E6's static-chest phantom**, rendered by Juliet's own code
  (``experiments/JanusM/Juliet/register_lie.py``) at 1.5 mm: the heart moves between the scans,
  the spine, lungs and aorta do not.
- **Kilo E5's synthetic case**: Kilo's LIE recipe (blood 110, remote 85, scar 150 HU, soft tissue
  compressed toward 40 HU, blur 0.6 voxel, noise 18 HU), Kilo's scars (subendocardial, depth below
  0.15 / 0.40 / 0.65 / 0.90) and Kilo's own motion field and warp
  (``experiments/JanusM/Kilo/e5_lie_registration.py``: rigid N(0, 3 deg), N(0, 4 mm) plus a smooth
  non-rigid field of RMS 1.5 mm; the whole image moves). Kilo ran it on public anatomy; here the
  anatomy is Juliet's phantom.
- **A flat slab** with scars of known depth, built by hand, where every candidate has a closed form.

Every QC cut below is a test parameter, not a development value: JA29 sets those on development.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage as ndi

from janusm import geometry as G
from janusm import scar as SC
from janusm.scar import registration as R
from janusm.scar import scar0 as S
from janusm.scar.common import CarriedGeometry, smooth

REPO = Path(__file__).resolve().parents[1]
JULIET = REPO / "experiments/JanusM/Juliet/register_lie.py"
KILO = REPO / "experiments/JanusM/Kilo/e5_lie_registration.py"
V, N = 1.5, 96  # Juliet's 144 mm field at 1.5 mm
LOOSE = R.QCCuts(
    max_fatlike=0.05, max_bloodlike=0.05, max_brighter_than_blood=0.05, max_rim_dark=0.3
)
NOTHING_PASSES = R.QCCuts(0.0, 0.0, 0.0, 0.0)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _affine():
    aff = np.diag([V, V, V, 1.0])
    aff[:3, 3] = (0.5 - N / 2) * V  # Juliet's world: (index + 0.5 - N/2) * V
    return aff


# ------------------------------------------------------------------------- Juliet E6 phantom
@pytest.fixture(scope="module")
def juliet():
    jr = _load(JULIET, "juliet_register_lie_for_tests")
    jr.N, jr.V = N, V
    rng = np.random.default_rng(3)
    fp, truth = jr.render(
        jr.FP, np.zeros(18), (np.eye(3), np.zeros(3)), 0.0, jr.FP["scar"], 30.0, rng, True
    )
    lab = truth["lab"].astype(np.int16)
    lab[lab > 4] = 0  # fat and the static chest are background for JA1
    aff = _affine()
    geo = G.analyse(lab, affine=aff)
    assert geo.aha.segments is not None and not geo.aha.flagged
    first = R.prepare_first_pass(fp, lab, aff, geometry=geo)
    return types.SimpleNamespace(jr=jr, fp=fp, lab=lab, aff=aff, geo=geo, first=first, rng=rng)


def _juliet_lie(ph, d_mm, seed, scar_T=None, phase=0.0):
    jr = ph.jr
    rng = np.random.default_rng(seed)
    mot = jr.motion_for(d_mm, rng)
    T = np.zeros(18) if scar_T is None else scar_T
    lie, _ = jr.render(jr.LIE, T, mot, phase, 150.0, 15.0, rng)
    return lie, mot


def _juliet_true_lie_points(ph, mot, p_fp):
    """Juliet's true map: a first-pass heart point to its LIE position (the heart moved by (R, t)
    about C_HEART in the heart frame)."""
    rm, t = mot
    m = ph.jr.R_HEART @ rm @ ph.jr.R_HEART.T
    return (p_fp - ph.jr.C_HEART) @ m.T + ph.jr.C_HEART + t


@pytest.fixture(scope="module")
def moved(juliet):
    """An 8 mm heart-only shift against a static chest (Juliet's hard case for whole-field MI)."""
    lie, mot = _juliet_lie(juliet, 8.0, seed=11)
    reg = R.register_lie(juliet.first, lie, juliet.aff, LOOSE)
    return lie, mot, reg


def test_static_chest_masked_rigid_recovers_the_heart(juliet, moved):
    lie, mot, reg = moved
    names = [s.name for s in reg.stages]
    assert names == ["R0", "rigid"], names  # R0 fails QC, rigid passes: the chain stops there
    assert not reg.stages[0].qc_passed and reg.final.name == "rigid" and reg.qc_passed
    p = juliet.first.myo_world
    truth = _juliet_true_lie_points(juliet, mot, p)
    tre = np.linalg.norm(reg.transform.inverse(p) - truth, axis=1).mean()
    tre_r0 = np.linalg.norm(p - truth, axis=1).mean()
    assert tre_r0 > 6.0
    assert tre < 1.0, tre  # Juliet E6: heart-masked rigid 0.26-0.56 mm
    # the three wall shares fall when the borders land on the wall (rim_dark, a phase signal,
    # need not: a carried cavity offset into the wall can read darker or brighter)
    assert (reg.stages[1].qc.values()[:3] < reg.stages[0].qc.values()[:3]).all()
    # the logged shift is the heart's displacement between the scans
    true_shift = (truth - p).mean(0)
    assert np.linalg.norm(reg.shift_mm - true_shift) < 1.0


def test_no_motion_stops_at_scanner_coordinates(juliet):
    lie, _ = _juliet_lie(juliet, 0.0, seed=12)
    reg = R.register_lie(juliet.first, lie, juliet.aff, LOOSE)
    assert [s.name for s in reg.stages] == ["R0"]
    assert reg.qc_passed and np.allclose(reg.transform.matrix, np.eye(3))
    assert np.linalg.norm(reg.shift_mm) < 1e-9
    # R0 carries the first-pass wall exactly onto the same grid
    assert np.array_equal(reg.carried.myo, juliet.lab == G.MYO)
    assert np.array_equal(reg.carried.segments, juliet.geo.aha.segments)


def test_affine_is_kept_only_if_it_lowers_qc(juliet, moved):
    lie, mot, _ = moved
    reg = R.register_lie(
        juliet.first, lie, juliet.aff, NOTHING_PASSES, n_samples=10_000, maxfev=600
    )
    names = [s.name for s in reg.stages]
    assert names == ["R0", "rigid", "affine", "rigid10"]  # JA51: the 10 mm fallback runs last
    rig, aff, fb = reg.stages[1], reg.stages[2], reg.stages[3]
    assert aff.kept == R.affine_accepted(aff.transform.matrix, aff.qc, rig.qc, NOTHING_PASSES)
    before = aff if aff.kept else rig
    assert reg.final is (fb if fb.kept else before)
    assert not reg.qc_passed  # nothing passes these cuts; the reader check decides


def test_affine_rule():
    # JA51 step 4 (PS3-S3 has the full set): values over their cuts, none rises, the max falls
    def q(a, b, c):
        return R.QC(a, b, c, 0.1, 130.0, 85.0, 100)

    eye = np.eye(3)
    assert R.affine_accepted(eye, q(0.01, 0.01, 0.0), q(0.02, 0.02, 0.0), LOOSE)
    assert not R.affine_accepted(eye, q(0.01, 0.03, 0.0), q(0.02, 0.02, 0.0), LOOSE)  # one rose
    assert not R.affine_accepted(eye, q(0.02, 0.02, 0.0), q(0.02, 0.02, 0.0), LOOSE)  # none fell
    assert not R.affine_accepted(eye, q(np.nan, 0.0, 0.0), q(0.02, 0.02, 0.0), LOOSE)


def test_qc_fails_closed_and_cuts_have_no_default(juliet):
    assert not R.QC(np.nan, 0.0, 0.0, 0.0, 130.0, 85.0, 10).passes(LOOSE)
    assert R.QC(0.05, 0.05, 0.05, 0.3, 130.0, 85.0, 10).passes(LOOSE)
    with pytest.raises(TypeError):
        R.QCCuts()  # set on development; never defaulted
    with pytest.raises(TypeError, match="development"):
        R.register_lie(juliet.first, juliet.fp, juliet.aff, None)


def test_reregistration_from_a_manual_shift(juliet, moved):
    lie, mot, _ = moved
    p = juliet.first.myo_world
    shift = (_juliet_true_lie_points(juliet, mot, p) - p).mean(0).round(0)  # a reader's shift
    with pytest.raises(ValueError, match="manual shift"):
        R.register_lie(juliet.first, lie, juliet.aff, LOOSE, attempt=2)
    reg = R.register_lie(
        juliet.first,
        lie,
        juliet.aff,
        # the shift is rounded to whole mm, which the JA52 edge offset can read as phase; the
        # phase step is not under test here (PS3-S4 is)
        R.QCCuts(0.2, 0.2, 0.2, 0.3, max_edge_offset_mm=10.0),
        initial_shift_mm=shift,
        attempt=2,
        previous_checks=[False],
    )
    assert reg.stages[0].name == "R0" and np.allclose(reg.stages[0].transform.translation, -shift)
    assert reg.status == SC.AWAITING
    assert reg.record_reader_check(True) == SC.REREGISTERED
    with pytest.raises(ValueError):
        reg.record_reader_check(True)
    log = json.loads(json.dumps(reg.log()))  # JSON-ready
    assert log["attempt"] == 2 and log["status"] == SC.REREGISTERED
    assert log["initial_shift_mm"] == shift.tolist()
    assert log["estimated_shift_norm_mm"] > 5.0


def test_log_records_every_stage(moved):
    *_, reg = moved
    log = json.loads(json.dumps(reg.log()))
    assert log["final_stage"] == "rigid" and len(log["stages"]) == 2
    assert log["qc_cuts"] == {
        "max_fatlike": 0.05,
        "max_bloodlike": 0.05,
        "max_brighter_than_blood": 0.05,
        "max_rim_dark": 0.3,
        "gate": [True, True, True, True],
        "max_rim_dark_phase": None,
        "max_edge_offset_mm": 0.6,
    }
    for s in log["stages"]:
        assert set(s["qc"]) >= {"fatlike", "bloodlike", "brighter_than_blood"}
        assert len(s["matrix"]) == 3 and len(s["translation_mm"]) == 3
    assert log["status"] == SC.AWAITING
    assert log["scar_version"] == SC.SCAR_VERSION
    assert log["geometry_version"] == G.GEOMETRY_VERSION


def test_scar0_inside_the_registered_wall_of_the_static_chest_phantom(juliet):
    """Juliet's scar patch (its own 18 sectors) graded on the moved LIE, scored per AHA segment
    against the scar's volume share of that segment on the first pass."""
    jr = juliet.jr
    T = np.zeros(18)
    T[[7, 8, 13, 14]] = (0.35, 0.6, 0.9, 0.6)  # mid and apical, adjacent sectors
    lie, mot = _juliet_lie(juliet, 6.0, seed=21, scar_T=T)
    _, truth = jr.render(
        jr.FP, T, (np.eye(3), np.zeros(3)), 0.0, jr.FP["scar"], 30.0, np.random.default_rng(0), True
    )
    seg = juliet.geo.aha.segments
    ref = np.array([(truth["scar"] & (seg == s)).sum() / (seg == s).sum() for s in range(1, 18)])
    # scar here is brighter than blood, so the blood-like shares are cut loosely
    reg = R.register_lie(juliet.first, lie, juliet.aff, R.QCCuts(0.05, 0.2, 0.2, 0.3))
    assert reg.final.name == "rigid"
    reg.record_reader_check(True)
    out = S.scar0(lie, reg.carried, status=reg.status)
    tab = out.table("P-K", "E-V")
    pres = np.array([tab["segments"][s]["presence"] for s in range(1, 18)])
    assert pres[ref >= 0.25].all()
    assert not pres[ref == 0].any()
    assert tab["registration_status"] == SC.PASSED and tab["label"] == SC.RESEARCH_LABEL


# ------------------------------------------------------------------------- Kilo E5 case
@pytest.fixture(scope="module")
def kilo(monkeypatch_module, juliet):
    # Kilo's module imports SimpleITK at the top for its own registration; the functions used
    # here (motion_field, warp, grade) are numpy only.
    stub = types.ModuleType("SimpleITK")
    stub.__getattr__ = lambda name: None  # PEP 562: any sitk.<name> default argument resolves
    monkeypatch_module.setitem(sys.modules, "SimpleITK", stub)
    monkeypatch_module.syspath_prepend(str(KILO.parent))
    before = set(sys.modules)
    mod = _load(KILO, "kilo_e5_for_tests")
    for name in set(sys.modules) - before:  # Kilo's own `layers` must not shadow anyone else's
        monkeypatch_module.delitem(sys.modules, name, raising=False)
    return mod


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="module")
def kilo_case(kilo, juliet):
    """Kilo E5's synthetic LIE of one patient, built on Juliet's first-pass phantom."""
    rng = np.random.default_rng(1237 + 5)
    lab, fp = juliet.lab, juliet.fp
    seg, u = juliet.geo.aha.segments, juliet.geo.depth.u
    myo = lab == G.MYO
    segs = (7, 9, 11, 15)
    scar = np.zeros_like(myo)
    for s, tau in zip(segs, kilo.TAUS):
        scar |= myo & (seg == s) & (u < tau)
    ref = np.array([(scar & (seg == s)).sum() / (seg == s).sum() for s in range(1, 18)])
    lie = np.where(fp < -200, fp, 40 + 0.45 * (fp - 40)).astype(np.float32)
    lie[np.isin(lab, (G.LV, G.RV, G.LA))] = 110
    lie[myo] = 85
    lie[scar] = 150
    sp = np.full(3, V)
    D = kilo.motion_field(lab.shape, sp, rng)  # voxels; fixed x samples moving x + D(x)
    lie_w = kilo.warp(ndi.gaussian_filter(lie, 0.6), D, 1)
    lie_w = lie_w + rng.normal(0, 18, lab.shape).astype(np.float32)
    true_seg = kilo.warp(seg, D, 0)
    return types.SimpleNamespace(lie=lie_w, D=D, ref=ref, true_seg=true_seg, segs=segs)


def test_kilo_case_rigid_reaches_the_non_rigid_floor(juliet, kilo_case):
    # Kilo's scar (150 HU) is brighter than its blood (110 HU): the blood-like cuts are loose
    reg = R.register_lie(juliet.first, kilo_case.lie, juliet.aff, R.QCCuts(0.05, 0.2, 0.2, 0.3))
    assert reg.final.name in ("rigid", "affine")
    wall = kilo_case.true_seg > 0
    ijk = np.argwhere(wall).astype(float)
    x = G._world(ijk, juliet.aff)
    truth = x + kilo_case.D[wall] * V
    tre = np.linalg.norm(reg.transform.forward(x) - truth, axis=1).mean()
    tre_r0 = np.linalg.norm(x - truth, axis=1).mean()
    assert tre < 1.5, tre  # Kilo E5: 0.78-0.82 mm, the floor set by the 1.5 mm non-rigid field
    assert tre < tre_r0
    out = S.scar0(kilo_case.lie, reg.carried, status=SC.AWAITING)
    pk = out.presence("P-K")
    thick = [s for s in range(1, 18) if kilo_case.ref[s - 1] >= 0.3]
    assert thick and all(pk[s] for s in thick)


def test_p_k_and_e_v_reproduce_kilo_e5_grade(kilo, juliet, kilo_case):
    """On the same smoothed image and wall, JA30's P-K share and E-V share are Kilo's own GF and
    G3 fractions (Kilo grades segments 1-16, so segment 17 is left off the wall here)."""
    seg = juliet.geo.aha.segments.copy()
    seg[seg == 17] = 0
    myo = seg > 0
    car = CarriedGeometry(
        myo=myo,
        cavity=juliet.lab == G.LV,
        segments=seg.astype(np.int16),
        u=np.where(myo, juliet.geo.depth.u, np.nan),
        column=np.where(myo, 0, -1),
        spacing=np.full(3, V),
        affine=juliet.aff,
    )
    lie = kilo_case.lie
    out = S.scar0(lie, car, status=SC.PASSED)
    sm = smooth(lie, car.spacing)
    gf, _ = kilo.grade(sm, seg, None)
    g3, _ = kilo.grade(sm, seg, 3.0)
    ours_pk = np.array([out.segments[s]["share_pk"] for s in range(1, 17)])
    ours_ev = np.array([out.segments[s]["share_ev"] for s in range(1, 17)])
    assert np.allclose(ours_pk, gf, atol=1e-12)
    assert np.allclose(ours_ev, g3, atol=1e-12)


# ------------------------------------------------------------------------- flat slab
SLAB_K = [0] * 8 + [1, 2, 3, 4, 5, 6, 7, 9, 10]  # scar depth in voxels (of 10), segments 1-17


def slab(cavity_hu=85.0, noise=5.0, seed=0):
    """A flat wall 10 voxels thick (1 mm) along x, cavity below it; segment s is the strip
    z in [4(s-1), 4s); its scar fills the first SLAB_K[s-1] layers from the endocardium. Columns
    are 2 x 2 lines of the wall. Depth u = (i + 0.5) / 10 exactly."""
    nx, ny, nz = 16, 40, 68
    shape = (nx, ny, nz)
    x0 = 3  # cavity x < 3, wall 3..12, outside 13..15
    i = np.arange(nx)[:, None, None] + np.zeros(shape, int)
    k = np.arange(nz)[None, None, :] + np.zeros(shape, int)
    j = np.arange(ny)[None, :, None] + np.zeros(shape, int)
    myo = (i >= x0) & (i < x0 + 10)
    cav = i < x0
    seg = np.where(myo, k // 4 + 1, 0).astype(np.int16)
    u = np.where(myo, (i - x0 + 0.5) / 10, np.nan).astype(np.float32)
    col = np.where(myo, (j // 2) * 1000 + k // 2, -1)
    depth_vox = np.array([0] + SLAB_K)[seg]
    scar = myo & (i - x0 < depth_vox)
    lie = np.full(shape, 85.0, np.float32)
    lie[cav] = cavity_hu
    lie[scar] = 150.0
    lie += np.random.default_rng(seed).normal(0, noise, shape).astype(np.float32)
    aff = np.eye(4)
    car = CarriedGeometry(myo, cav, seg, u, col, np.ones(3), aff)
    return lie, car


def test_slab_candidates_have_their_closed_forms():
    lie, car = slab()
    out = S.scar0(lie, car, status=SC.PASSED, tau=0.05)
    # the 6 lowest of the 8 identical scar-free segments (which 6 is up to the noise)
    assert set(out.remote["segments"]) <= set(range(1, 9)) and len(out.remote["segments"]) == 6
    assert out.remote["brightest_segment"] == 17
    assert abs(out.thresholds["half_way"] - 117.5) < 3.0  # half way from 85 to p99 (150 + noise)
    for s in range(1, 18):
        k = SLAB_K[s - 1] / 10
        row = out.segments[s]
        # a flat step cut half way is exact; a one-voxel scar sits just above the cut once blurred
        tol = 1e-9 if SLAB_K[s - 1] != 1 else 0.05
        assert abs(row["share_pk"] - k) < tol, (s, row)
        assert abs(row["extent_ed"] - k) < tol, (s, row)
        assert k - 0.01 <= row["share_ev"] <= k + 0.15  # remote + 3 SD keeps about one blur layer
        if k > 0:
            assert row["deepest_ed"] == pytest.approx(SLAB_K[s - 1] / 10)  # far edge of its bin
    tab = out.table("P-K", "E-D")
    for s in range(1, 18):
        k = SLAB_K[s - 1] / 10
        r = tab["segments"][s]
        assert r["presence"] == (k >= 0.05)
        assert r["kim_bin"] == S.kim_bin(k, k > 0)
        assert r["share"] == pytest.approx(k, abs=0.05)
    pj = out.presence("P-J")
    assert all(pj[s] == (SLAB_K[s - 1] > 0) for s in range(1, 18))


def test_p_g_ignores_the_endocardial_millimetre_and_blood_spill():
    # blood as bright as scar (Golf's hard case)
    lie, car = slab(cavity_hu=150.0)
    out = S.scar0(lie, car, status=SC.PASSED)
    pg, pk = out.presence("P-G"), out.presence("P-K")
    for s in range(1, 9):  # scar-free
        assert out.segments[s]["share_ev"] >= 0.09  # the wall's first layer reads blood
        assert not pg[s] and not pk[s]
    assert not pg[9] and pk[9]  # a 1 mm subendocardial scar is removed by construction
    assert all(pg[s] for s in range(10, 18))


def test_kim_bins():
    assert S.kim_bin(0.0, False) == 0 and S.kim_bin(0.9, False) == 0
    assert S.kim_bin(0.0, True) == 1  # a present segment reads at least bin 1
    assert S.kim_bin(float("nan"), True) == 1
    assert [S.kim_bin(x, True) for x in (0.01, 0.25, 0.2501, 0.5, 0.51, 0.75, 0.76, 1.0)] == [
        1,
        1,
        2,
        2,
        3,
        3,
        4,
        4,
    ]


def test_table_carries_status_label_and_territories():
    lie, car = slab()
    terr = {s: ("LAD" if s <= 8 else "RCA") for s in range(1, 18)}
    tab = S.scar0(lie, car, status=SC.REREGISTERED, territory=terr).table("P-K", "E-V")
    assert tab["label"] == "research output, not validated"
    assert tab["registration_status"] == SC.REREGISTERED
    assert tab["territories"]["LAD"]["share_scar_present"] == 0.0
    assert tab["territories"]["RCA"]["share_scar_present"] == 1.0
    assert tab["territory_source"] == "patient territories"
    assert tab["constants_are_ja30"] and tab["constants"]["presence_share"] == 0.05
    std = S.scar0(lie, car, status=SC.PASSED).table("P-G", "E-D")
    assert std["territory_source"] == "standard AHA map"
    assert set(std["territories"]) == {"LAD", "LCx", "RCA"}
    json.dumps(tab)


def test_not_graded_patients_get_no_grade():
    lie, car = slab()
    tab = S.scar0(lie, car, status=SC.NOT_GRADED).table("P-K", "E-V")
    assert not tab["graded"] and tab["registration_status"] == SC.NOT_GRADED
    assert all(r["presence"] is None and r["kim_bin"] is None for r in tab["segments"].values())


def test_outputs_feed_the_scoring_harness():
    from janusm.scar import scoring

    lie, car = slab()
    bins, shares = S.scar0(lie, car, status=SC.PASSED).for_scoring("P-K", "E-D")
    ref = np.array([S.kim_bin(k / 10, k > 0) for k in SLAB_K])
    assert np.array_equal(bins, ref)
    scoring.Patient(ref=ref, ct=bins, ct_share=shares)
    ng, ng_share = S.scar0(lie, car, status=SC.NOT_GRADED).for_scoring("P-K", "E-V")
    assert (ng == scoring.NOT_GRADED).all() and np.isnan(ng_share).all()
    scoring.Patient(ref=ref, ct=ng)
    with pytest.raises(ValueError, match="final"):
        S.scar0(lie, car, status=SC.AWAITING).for_scoring("P-K", "E-V")


def test_menu_arguments_are_checked():
    lie, car = slab()
    out = S.scar0(lie, car, status=SC.PASSED)
    with pytest.raises(ValueError, match="tau"):
        out.table("P-J", "E-V")
    with pytest.raises(ValueError):
        out.table("P-X", "E-V")
    with pytest.raises(ValueError):
        out.table("P-K", "E-X")
    with pytest.raises(ValueError):
        S.scar0(lie, car, status="fine")


def test_too_few_remote_segments_is_ungradable():
    lie, car = slab()
    seg = car.segments.copy()
    seg[seg > 5] = 0
    car.myo = seg > 0
    car.segments = seg
    tab = S.scar0(lie, car, status=SC.PASSED).table("P-K", "E-V")
    assert not tab["graded"] and "fewer than 6" in tab["ungradable"]


# ------------------------------------------------------------------------- development rules
def test_tau_per_protocol_or_pooled():
    rng = np.random.default_rng(0)
    rec = [("A", f"dev{p:02d}", float(t)) for p in range(15) for t in rng.uniform(0, 0.1, 10)]
    rec += [("B", f"devB{p}", float(t)) for p in range(5) for t in rng.uniform(0, 0.3, 10)]
    tau = S.tau_from_development(rec)
    ta = np.percentile([t for p, _, t in rec if p == "A"], 99)
    pooled = np.percentile([t for *_, t in rec], 99)
    assert tau["A"] == pytest.approx(ta)  # 15 patients: its own
    assert tau["B"] == pytest.approx(pooled) == tau["pooled"]  # 5 patients: pooled


def test_presence_and_extent_choice():
    dev = {"P-K": (0.80, 0.96), "P-J": (0.85, 0.94), "P-G": (0.80, 0.97)}
    assert S.choose_presence(dev) == "P-K"  # P-J fails the bound; P-K beats P-G on the tie
    assert S.choose_presence({"P-K": (0.9, 0.90)}) is None
    assert S.choose_extent({"E-V": 0.6, "E-D": 0.7}) == "E-D"
    assert S.choose_extent({"E-V": 0.6, "E-D": 0.6}) == "E-V"
    with pytest.raises(ValueError):
        S.choose_presence({"P-Z": (1.0, 1.0)})


def test_reader_check_statuses_and_failure_rate():
    assert R.status_from_checks([]) == SC.AWAITING
    assert R.status_from_checks([True]) == SC.PASSED
    assert R.status_from_checks([False]) == SC.AWAITING
    assert R.status_from_checks([False, True]) == SC.REREGISTERED
    assert R.status_from_checks([False, False]) == SC.NOT_GRADED
    with pytest.raises(ValueError):
        R.status_from_checks([True, True])
    with pytest.raises(ValueError):
        R.status_from_checks([False, False, True])
    ok = [SC.PASSED] * 9 + [SC.NOT_GRADED]
    assert R.failure_rate(ok) == pytest.approx(0.1) and R.seal_grading_allowed(ok)
    assert not R.seal_grading_allowed([SC.PASSED] * 8 + [SC.NOT_GRADED])
    assert R.seal_grading_allowed([SC.REREGISTERED] * 10)
    with pytest.raises(ValueError, match="final"):
        R.failure_rate([SC.PASSED, SC.AWAITING])


# ------------------------------------------------------------------------- JA12 guard
HELD_OUT = "TotalSegmentator-cardiac__s0655"  # the guard's own positive control


def test_case_ids_are_refused_by_the_guard(juliet):
    from janusm.guard import HeldOutError

    lie, car = slab()
    with pytest.raises(HeldOutError):
        R.prepare_first_pass(juliet.fp, juliet.lab, juliet.aff, case_id=HELD_OUT)
    with pytest.raises(HeldOutError):
        R.register_lie(juliet.first, juliet.fp, juliet.aff, LOOSE, case_id=HELD_OUT)
    with pytest.raises(HeldOutError):
        S.scar0(lie, car, status=SC.PASSED, case_id=HELD_OUT)
    with pytest.raises(HeldOutError):
        S.tau_from_development([("A", HELD_OUT, 0.1)])


def test_guard_fails_closed(monkeypatch):
    import janusm

    monkeypatch.delattr(janusm, "guard", raising=False)
    monkeypatch.setitem(sys.modules, "janusm.guard", None)
    lie, car = slab()
    with pytest.raises(RuntimeError, match="JA12"):
        S.scar0(lie, car, status=SC.PASSED, case_id="phantom-1")
