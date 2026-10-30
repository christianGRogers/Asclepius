"""Janus-M geometry (JA2-JA4) on analytic phantoms.

The LV phantom is a cylinder with a hemispherical apex, its long axis along -S (base superior),
anterior +A. The cavity has radius RC and length CYL + RC; the wall is T thick. The LA sits on top
of the cavity, and the RV wraps the septum from the anterior insertion (120 degrees, atan2(A, R))
to the inferior one (240 degrees). Everything analytic is known in closed form:

- depth on the cylinder: (r - RC) / T;
- rings: thirds of the cavity length CYL + RC from the base plane, 17 beyond;
- sectors: 60 degrees from the anterior insertion into the septum (basal, mid), 90 apical;
- territories: three vessels parallel to the axis; on the cylinder the boundaries are the bisectors.

"Within one voxel" means a disagreeing voxel lies within one voxel (largest spacing) of an analytic
boundary, measured in mm.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from janusm import geometry as G

RC, T, CYL = 12.0, 8.0, 30.0  # mm
RV_W = 8.0  # RV blood pool thickness
INS_ANT, INS_INF = 120.0, 240.0  # degrees, atan2(A, R)


def phantom(sp=(0.5, 0.5, 0.5), wall=T, rc=RC):
    """Label map, affine and the world coordinates (mm) of every voxel centre."""
    sp = np.asarray(sp, float)
    re = rc + wall
    lo = np.array([-(re + RV_W + 4), -(re + RV_W + 4), -(CYL + re + 4)])
    hi = np.array([re + RV_W + 4, re + RV_W + 4, 10.0])
    n = np.ceil((hi - lo) / sp).astype(int)
    aff = np.diag([*sp, 1.0])
    aff[:3, 3] = lo + sp / 2
    i, j, k = np.indices(n, dtype=float)
    x, y, z = (lo[0] + (i + 0.5) * sp[0], lo[1] + (j + 0.5) * sp[1], lo[2] + (k + 0.5) * sp[2])
    r = np.hypot(x, y)
    phi = np.degrees(np.arctan2(y, x)) % 360
    # distance from the axis-and-cap skeleton: cylinder above z=-CYL, sphere below
    rr = np.where(z >= -CYL, r, np.sqrt(r**2 + (z + CYL) ** 2))
    below_top = z < 0
    lab = np.zeros(n, np.int16)
    lab[below_top & (rr < re)] = G.MYO
    lab[below_top & (rr < rc)] = G.LV
    lab[(z >= 0) & (z < 6) & (r < re)] = G.LA
    rv = below_top & (z >= -CYL) & (r >= re) & (r < re + RV_W) & (phi >= INS_ANT) & (phi <= INS_INF)
    lab[rv] = G.RV
    return lab, aff, dict(x=x, y=y, z=z, r=r, rr=rr, phi=phi, sp=sp, re=re, rc=rc, wall=wall)


@pytest.fixture(scope="module")
def ph():
    return phantom()


@pytest.fixture(scope="module")
def ph_aha(ph):
    lab, aff, _ = ph
    return G.aha17(lab, affine=aff)


def _ang_diff(a, b):
    return np.abs((a - b + 180) % 360 - 180)


# ------------------------------------------------------------------------------------------- JA2
def test_equal_thickness_depth_and_thirds_match_analytic(ph):
    lab, aff, w = ph
    d = G.depth(lab, affine=aff)
    myo = lab == G.MYO
    cyl = myo & (w["z"] < -T - 1) & (w["z"] > -CYL)  # away from the basal cut
    true_u = (w["r"] - RC) / T
    # thickness on the cylinder is T to within a voxel
    assert abs(np.median(d.thickness[cyl]) - T) < w["sp"].max()
    lay = G.layers(d, w["sp"])
    assert lay.regions[0]["scheme"] == "thirds"
    truth = 1 + np.minimum((true_u * 3).astype(int), 2)
    wrong = cyl & (lay.label != truth)
    # every disagreeing voxel is within one voxel of a cut at RC + T/3 or RC + 2T/3
    dcut = np.minimum(np.abs(w["r"] - (RC + T / 3)), np.abs(w["r"] - (RC + 2 * T / 3)))
    assert (dcut[wrong] <= w["sp"].max()).all()
    assert wrong.sum() / cyl.sum() < 0.1


@pytest.mark.parametrize("method", ["laplace", "yezzi_prince"])
def test_alternative_depths_match_their_closed_forms(ph, method):
    """On a cylinder the harmonic depth is ln(r/RC) / ln(RE/RC), not linear: its 1/3 cut sits ~0.4
    mm inside the equal-thickness one (Juliet's 0.36 mm in a 10 mm wall). Yezzi-Prince follows the
    radial streamlines, so it is linear again. Both agree with equal thickness on most of the wall
    (India and Golf: 88 % on real hearts at 1.5 mm)."""
    lab, aff, w = ph
    myo = lab == G.MYO
    cyl = myo & (w["z"] < -T - 1) & (w["z"] > -CYL)
    alt_d = G.depth(lab, affine=aff, method=method)
    alt = G.layers(alt_d, w["sp"]).label
    eq = G.layers(G.depth(lab, affine=aff), w["sp"]).label
    assert np.mean(eq[myo] == alt[myo]) > 0.8
    re = RC + T
    if method == "laplace":
        u = np.log(w["r"] / RC) / np.log(re / RC)
        cuts = [RC * (re / RC) ** f for f in (1 / 3, 2 / 3)]
    else:
        u = (w["r"] - RC) / T
        cuts = [RC + T / 3, RC + 2 * T / 3]
        assert abs(np.median(alt_d.thickness[cyl]) - T) < w["sp"].max()
    truth = 1 + np.minimum((u * 3).astype(int), 2)
    wrong = cyl & (alt != truth)
    dcut = np.min([np.abs(w["r"] - c) for c in cuts], axis=0)
    assert (dcut[wrong] <= w["sp"].max()).all()


def test_flat_wall_depth_is_exact_for_all_methods():
    """A wide slab N voxels thick: voxel k sits at depth (k - 0.5) / N by every method, and its
    thickness is N voxels."""
    lab = np.zeros((30, 41, 41), np.int16)
    lab[:20] = G.LV  # deep: no short cut to the outside through the cavity
    lab[20:26] = G.MYO  # 6 voxels
    want = (np.arange(1, 7) - 0.5) / 6
    for m in G.DEPTH_METHODS:
        d = G.depth(lab, spacing=(0.7, 0.7, 0.7), method=m)
        got = d.u[20:26, 20, 20]
        assert np.allclose(got, want, atol=0.02), (m, got)
        assert np.allclose(d.thickness[20:26, 20, 20], 6 * 0.7, atol=0.05), m


def test_halves_where_the_wall_is_thin_or_coarse():
    """Juliet's phantom sizes: a 5 mm wall at 0.5 mm has 3.3 voxels per third (< 4): halves. A
    4.5 mm wall is under 5 mm: halves at any grid. A 10 mm wall at 0.5 mm: thirds."""
    for wall, sp, scheme in ((5.0, 0.5, "halves"), (4.5, 0.25, "halves"), (10.0, 0.5, "thirds")):
        lab, aff, w = phantom(sp=(sp,) * 3, wall=wall, rc=10.0)
        lay = G.layers(G.depth(lab, affine=aff), w["sp"])
        assert lay.regions[0]["scheme"] == scheme, (wall, sp, lay.regions[0])
        codes = set(np.unique(lay.label[lab == G.MYO]).tolist())
        assert codes == (
            {G.INNER_HALF, G.OUTER_HALF} if scheme == "halves" else {G.SUBENDO, G.MIDWALL, G.SUBEPI}
        )


def test_halves_are_decided_per_segment():
    """Thin the anterior free wall only: its segments get halves, the rest keep thirds."""
    lab, aff, w = phantom(sp=(0.5,) * 3, wall=9.0, rc=10.0)
    thin = (lab == G.MYO) & (w["phi"] > 50) & (w["phi"] < 110) & (w["rr"] > 10.0 + 4.5)
    lab = lab.copy()
    lab[thin] = G.BACKGROUND
    a = G.aha17(lab, affine=aff)
    lay = G.layers(G.depth(lab, affine=aff), w["sp"], a.segments)
    assert lay.regions[7]["scheme"] == "halves"  # mid anterior
    assert lay.regions[10]["scheme"] == "thirds"  # mid inferior
    assert set(np.unique(lay.label[a.segments == 10]).tolist()) == {1, 2, 3}


# ------------------------------------------------------------------------------------------- JA3
def analytic_segments(w, cav_len):
    s = -w["z"]  # base plane at z = 0, axis along -S
    theta = (w["phi"] - INS_ANT) % 360  # into the septum = increasing phi here
    ring = np.where(s > cav_len, 3, np.clip((s / cav_len * 3).astype(int), 0, 2))
    six = G._SIX[(theta // 60).astype(int) % 6]
    four = G._FOUR[(((theta - 15) % 360) // 90).astype(int) % 4]
    seg = np.where(ring == 0, six, np.where(ring == 1, six + 6, np.where(ring == 2, four, 17)))
    # distance (mm) to the nearest analytic boundary
    ring_d = np.min([np.abs(s - f * cav_len) for f in (1 / 3, 2 / 3, 1.0)], axis=0)
    cuts6 = INS_ANT + np.arange(6) * 60.0
    cuts4 = INS_ANT + 15 + np.arange(4) * 90.0
    rad = np.maximum(w["r"], 1e-6)
    d6 = np.min([_ang_diff(w["phi"], c) for c in cuts6], axis=0) * np.pi / 180 * rad
    d4 = np.min([_ang_diff(w["phi"], c) for c in cuts4], axis=0) * np.pi / 180 * rad
    sect_d = np.where(ring <= 1, d6, np.where(ring == 2, d4, np.inf))
    return seg, np.minimum(ring_d, sect_d)


def test_aha_segments_match_analytic_within_one_voxel(ph, ph_aha):
    lab, aff, w = ph
    a = ph_aha
    assert not a.flagged, a.flags
    assert a.cavity_length_mm == pytest.approx(CYL + RC, abs=w["sp"].max())
    assert a.septal_arc_deg == pytest.approx(INS_INF - INS_ANT, abs=6)
    seg, bd = analytic_segments(w, CYL + RC)
    myo = lab == G.MYO
    wrong = myo & (a.segments != seg)
    assert wrong.sum() / myo.sum() < 0.05
    # the measured insertion and base move the cuts by under a voxel at the epicardium
    assert (bd[wrong] <= w["sp"].max() * 1.5).all(), np.sort(bd[wrong])[-5:]
    assert set(np.unique(a.segments[myo]).tolist()) == set(range(1, 18))


def test_aha_frame_is_world_mm_not_voxel_order(ph):
    """Flip the array and the affine together: same anatomy, same segments."""
    lab, aff, w = ph
    flip = lab[::-1, :, ::-1]
    faff = aff.copy()
    faff[:3, 0] *= -1
    faff[:3, 2] *= -1
    faff[:3, 3] = aff[:3, :3] @ (np.array(lab.shape) - 1) * np.array([1, 0, 1]) + aff[:3, 3]
    a0 = G.aha17(lab, affine=aff).segments
    a1 = G.aha17(flip, affine=faff).segments[::-1, :, ::-1]
    myo = lab == G.MYO
    assert np.mean(a0[myo] == a1[myo]) > 0.99


def test_anisotropic_grid():
    lab, aff, w = phantom(sp=(0.5, 0.5, 0.8))
    a = G.aha17(lab, affine=aff)
    assert not a.flagged
    seg, bd = analytic_segments(w, CYL + RC)
    myo = lab == G.MYO
    wrong = myo & (a.segments != seg)
    assert (bd[wrong] <= 0.8 * 1.5).all()


def test_orientation_checks_flag_a_mirrored_case(ph, ph_aha):
    """Golf's check: segment 1 anterior of 4, septum toward the RV, lateral away. A label map whose
    segments are mirrored (anterior <-> inferior) must be flagged."""
    lab, aff, _ = ph
    seg = ph_aha.segments
    ok = G.orientation_checks(seg, lab, aff)
    assert ok["ok"] and ok["septum_towards_rv"] and ok["lateral_away_from_rv"]
    swap = {1: 4, 4: 1, 2: 3, 3: 2, 5: 6, 6: 5, 7: 10, 10: 7, 8: 9, 9: 8, 11: 12, 12: 11}
    mirrored = seg.copy()
    for a, b in swap.items():
        mirrored[seg == a] = b
    bad = G.orientation_checks(mirrored, lab, aff)
    assert not bad["ok"] and "segment 1 not anterior of segment 4" in bad["failed"]
    lateral = seg.copy()
    for a, b in {2: 5, 5: 2, 3: 6, 6: 3, 8: 11, 11: 8, 9: 12, 12: 9}.items():
        lateral[seg == a] = b
    assert "septum not toward the RV" in G.orientation_checks(lateral, lab, aff)["failed"]


def test_derivation_failures_are_flagged_not_tabled(ph):
    lab, aff, _ = ph
    no_la = np.where(lab == G.LA, 0, lab)
    a = G.aha17(no_la, affine=aff)
    assert a.flagged and a.segments is None and "mitral" in a.flags[0]
    no_rv = np.where(lab == G.RV, 0, lab)
    a = G.aha17(no_rv, affine=aff)
    assert a.flagged and a.segments is None and "RV" in a.flags[0]
    r = G.analyse(no_rv, affine=aff).report()
    assert r["flagged"] and r["segments"] == {}


def test_bad_labels_are_refused():
    with pytest.raises(ValueError, match="0-4"):
        G.depth(np.full((4, 4, 4), 7, np.int16), spacing=(1, 1, 1))


# ------------------------------------------------------------------------------------------- JA4
VESSELS = {G.LAD: 90.0, G.LCX: 330.0, G.RCA: 210.0}  # degrees, just outside the epicardium


def coronary(lab, w, extra_lm=True):
    c = np.zeros(lab.shape, np.int16)
    rad = w["re"] + 1.5
    for cls, ang in VESSELS.items():
        cx, cy = rad * np.cos(np.radians(ang)), rad * np.sin(np.radians(ang))
        tube = (np.hypot(w["x"] - cx, w["y"] - cy) < 1.0) & (w["z"] < 0) & (w["z"] > -CYL)
        c[tube & (lab == 0) | tube & (lab == G.RV)] = cls
    if extra_lm:  # an LM blob hugging the lateral wall: must not be a seed
        lm = (np.hypot(w["x"] - (w["re"] + 1.5), w["y"]) < 1.2) & (np.abs(w["z"] + 10) < 3)
        c[lm & (lab != G.MYO)] = G.LM
    return c


def analytic_territory(w):
    """Nearest vessel on the cylinder: the smallest angular difference to the vessel angles."""
    cls = np.array(list(VESSELS))
    d = np.stack([_ang_diff(w["phi"], a) for a in VESSELS.values()])
    t = cls[np.argmin(d, axis=0)]
    two = np.sort(d, axis=0)
    margin = (two[1] - two[0]) / 2 * np.pi / 180 * w["r"]  # arc distance to the bisector
    return t, margin


def test_euclidean_territories_match_analytic_and_ignore_lm(ph, ph_aha):
    lab, aff, w = ph
    cor = coronary(lab, w)
    t = G.territories(lab, cor, affine=aff, segments=ph_aha.segments)
    myo = lab == G.MYO
    assert set(np.unique(t.label[myo]).tolist()) <= {G.LAD, G.LCX, G.RCA}
    cyl = myo & (w["z"] < -3) & (w["z"] > -CYL + 3)
    want, margin = analytic_territory(w)
    wrong = cyl & (t.label != want)
    assert (margin[wrong] <= w["sp"].max()).all()
    # the standard map is always beside the majority
    assert all(v["standard"] == G.AHA_STANDARD[k] for k, v in t.segments.items())
    assert len(t.segments) == 17


def test_segment_majority_follows_the_voxels(ph, ph_aha):
    lab, aff, w = ph
    t = G.territories(lab, coronary(lab, w), affine=aff, segments=ph_aha.segments)
    for k, v in t.segments.items():
        vals, cnt = np.unique(t.label[ph_aha.segments == k], return_counts=True)
        assert v["territory"] == G.TERRITORY_NAMES[int(vals[np.argmax(cnt)])]


def test_standard_vessels_reproduce_the_standard_map(ph, ph_aha):
    """Golf's territory self-test: arteries on the epicardial shell, each labelled by the standard
    territory of the nearest segment, give no reassigned segment."""
    from scipy import ndimage as ndi

    lab, aff, _ = ph
    seg = ph_aha.segments
    heart = (lab == G.MYO) | (lab == G.LV)
    shell = ndi.binary_dilation(heart, iterations=2) & ~ndi.binary_dilation(heart, iterations=1)
    _, idx = ndi.distance_transform_edt(seg == 0, return_indices=True)
    near = seg[tuple(idx)]
    code = {"LAD": G.LAD, "LCx": G.LCX, "RCA": G.RCA}
    art = np.zeros(lab.shape, np.int16)
    for s, name in G.AHA_STANDARD.items():
        art[shell & (near == s)] = code[name]
    t = G.territories(lab, art, affine=aff, segments=seg)
    assert [k for k, v in t.segments.items() if not v["concordant"]] == []


def test_geodesic_territories_agree_on_the_cylinder(ph, ph_aha):
    lab, aff, w = ph
    cor = coronary(lab, w)
    e = G.territories(lab, cor, affine=aff, segments=ph_aha.segments)
    g = G.territories(lab, cor, affine=aff, segments=ph_aha.segments, method="geodesic")
    myo = lab == G.MYO
    cyl = myo & (w["z"] < -3) & (w["z"] > -CYL + 3)
    assert np.mean(e.label[cyl] == g.label[cyl]) > 0.95
    assert not g.flags


def test_coronary_map_must_use_d25_classes(ph):
    lab, aff, _ = ph
    bad = np.zeros(lab.shape, np.int16)
    bad[0, 0, 0] = 9
    with pytest.raises(ValueError, match="D25"):
        G.territories(lab, bad, affine=aff)
    only_lm = np.zeros(lab.shape, np.int16)
    only_lm[0, 0, 0] = G.LM
    with pytest.raises(ValueError, match="no LAD"):
        G.territories(lab, only_lm, affine=aff)


# ------------------------------------------------------------------------------------------- all
def test_analyse_report_is_versioned_and_complete(ph):
    import json

    lab, aff, w = ph
    big = np.zeros(tuple(s + 20 for s in lab.shape), np.int16)
    big[10:-10, 10:-10, 10:-10] = lab
    cor = np.zeros(big.shape, np.int16)
    cor[10:-10, 10:-10, 10:-10] = coronary(lab, w)
    baff = aff.copy()
    baff[:3, 3] -= 10 * w["sp"]
    g = G.analyse(big, affine=baff, coronary=cor, margin_mm=3.0)
    r = g.report()
    json.dumps(r)
    assert r["geometry_version"] == G.GEOMETRY_VERSION
    assert r["depth_method"] == "equal_thickness" and r["territory_method"] == "euclidean"
    assert not r["flagged"], r["flags"]
    assert sorted(r["segments"]) == list(range(1, 18))
    row = r["segments"][7]
    assert row["layer_scheme"] == "thirds" and row["standard_territory"] == "LAD"
    assert row["territory"] == "LAD"
    assert g.aha.segments.shape == big.shape and g.layers.label.shape == big.shape
    # the crop is invisible: the same segments as on the tight array
    a = G.aha17(lab, affine=aff).segments
    assert np.array_equal(g.aha.segments[10:-10, 10:-10, 10:-10], a)


def test_load_case_fails_closed_without_the_guard(tmp_path, monkeypatch):
    """JA12: loading by name goes through the guard; no importable guard means no load."""
    import sys

    import janusm

    monkeypatch.delattr(janusm, "guard", raising=False)
    monkeypatch.setitem(sys.modules, "janusm.guard", None)
    with pytest.raises(RuntimeError, match="JA12"):
        G.load_case("ImageCAS-X__c0001", tmp_path / "x.nii.gz")


def test_load_case_refuses_held_out_cases_before_reading(tmp_path):
    """The real guard (#138): its positive controls never reach the file system."""
    from janusm.guard import HeldOutError

    missing = tmp_path / "never-read.nii.gz"
    with pytest.raises(HeldOutError):
        G.load_case("TotalSegmentator-cardiac__s0655", missing)
    with pytest.raises(HeldOutError):
        G.load_case("s0655", missing, source="TotalSegmentator")


def test_load_case_calls_the_guard_first(tmp_path, monkeypatch):
    import sys
    import types

    import janusm

    nib = pytest.importorskip("nibabel")
    seen = []
    fake = types.ModuleType("janusm.guard")

    def refuse(names, what="", source=None, purpose="any"):
        seen.append((list(names), source))
        if "TotalSegmentator-cardiac__s0655" in names:
            raise PermissionError("held out")
        return list(names)

    fake.refuse = refuse
    monkeypatch.setitem(sys.modules, "janusm.guard", fake)
    monkeypatch.setattr(janusm, "guard", fake, raising=False)
    lab, aff, _ = phantom(sp=(1.0, 1.0, 1.0))
    p = tmp_path / "c.nii.gz"
    nib.save(nib.Nifti1Image(lab, aff), str(p))
    with pytest.raises(PermissionError):
        G.load_case("TotalSegmentator-cardiac__s0655", p)
    got, gaff, cor = G.load_case("ImageCAS-X__c0001", p)
    G.load_case("c0001", p, source="ImageCAS-X")
    assert seen == [
        (["TotalSegmentator-cardiac__s0655"], None),
        (["ImageCAS-X__c0001"], None),
        (["c0001"], "ImageCAS-X"),
    ]
    assert np.array_equal(got, lab) and np.allclose(gaff, aff) and cor is None


# ------------------------------------------------------------------------------------ prototypes
PROTO = Path(__file__).resolve().parents[1] / "experiments" / "JanusM"


def _proto(name, rel):
    import importlib.util
    import sys

    path = PROTO / rel
    if not path.is_file():
        pytest.skip(f"Round 1 prototype {rel} is gone")
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location(f"janusm_r1_{name}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(path.parent))
    return mod


def _ring(seg):
    return np.select([seg == 0, seg <= 6, seg <= 12, seg <= 16], [-1, 0, 1, 2], 3)


@pytest.fixture(scope="module")
def r1(ph):
    """The three Round 1 AHA implementations on the same phantom (no data: arrays only)."""
    pytest.importorskip("nibabel")
    lab, aff, w = ph
    sp = w["sp"]
    myo, lv, rv, la = (lab == c for c in (G.MYO, G.LV, G.RV, G.LA))
    juliet = _proto("juliet", "Juliet/real_labels.py")
    _, det = juliet.geometry("phantom", myo, lv, rv, la, np.zeros_like(myo), sp)
    js = np.zeros(lab.shape, np.int16)
    sub = np.zeros(myo[det["box"]].shape, np.int16)
    sub[tuple(det["myo_vox"].T)] = det["seg"]
    js[det["box"]] = sub
    india = _proto("india", "India/lvgeom.py")
    g = dict(myo=myo, lv=lv, rv=rv, la=la, affine=aff)
    ins = india.aha17(g, india.lv_frame(g))
    golf = _proto("golf", "Golf/layers_ts.py")
    geom, _ = golf.aha(myo, lv, rv, la, sp)
    gs = golf.aha_labels(myo, geom, np.array([0.0, 1.0, 1.0]) / np.sqrt(2))
    return {"juliet": js, "india": ins, "golf": gs}


def test_round1_prototypes_side_by_side(ph, ph_aha, r1):
    """JA3 against the prototypes it replaces, on one phantom. Measured at 0.5 mm (voxel agreement
    with the analytic segments): this module 0.996, Golf 0.909, India 0.859, Juliet 0.715. Each gap
    is a method JA3 ruled on, which these asserts pin:

    - Juliet: rings are thirds of base -> epicardial apex with the cap past 0.9, not of the cavity,
      so rings agree on only ~75 %; its zero (RV centroid +/- 60 degrees) matches ours on this
      symmetric RV, so sectors agree where rings do.
    - India: same fixed sectors, but a 2-voxel RV dilation widens the arc (132 vs 120 degrees) and
      moves the insertion; myocardium above the base plane is left unsegmented.
    - Golf: PCA axis and an arc-proportional septum (its arc 136 degrees), not fixed 60-degree
      sectors.
    """
    lab, _, w = ph
    myo = lab == G.MYO
    truth, _ = analytic_segments(w, CYL + RC)
    ours = ph_aha.segments
    acc = {k: float(np.mean(v[myo] == truth[myo])) for k, v in r1.items()}
    assert np.mean(ours[myo] == truth[myo]) > max(acc.values())
    assert min(acc.values()) > 0.65
    ring_ok = {k: _ring(v[myo]) == _ring(ours[myo]) for k, v in r1.items()}
    assert ring_ok["juliet"].mean() < 0.8  # different ring rule
    assert np.mean((r1["juliet"][myo] == ours[myo])[ring_ok["juliet"]]) > 0.9  # same sectors
    assert ring_ok["india"].mean() > 0.9 and ring_ok["golf"].mean() > 0.9
    assert np.mean(r1["india"][myo] == 0) > 0  # unsegmented base


def test_round1_thirds_match_golf_and_india(ph):
    """Equal-thickness thirds as Golf and India computed them, to within the half-voxel offset."""
    lab, aff, w = ph
    myo, lv = lab == G.MYO, lab == G.LV
    ours = G.layers(G.depth(lab, affine=aff), w["sp"]).label
    india = _proto("india", "India/lvgeom.py")
    t, _ = india.depth_distance(myo, lv, w["sp"])
    golf = _proto("golf", "Golf/layers_ts.py")
    for theirs in (india.layers(t, myo), golf.thirds(golf.depth(myo, lv, w["sp"]), myo)):
        assert np.mean(theirs[myo] == ours[myo]) > 0.97


# ------------------------------------------------------------------- JA15 harness as the fixture
@pytest.mark.parametrize(
    "border,shift", [("epi", 0.5), ("epi", -0.5), ("endo", 0.5), ("endo", -0.5)]
)
def test_segment_thickness_tracks_a_known_border_shift(border, shift):
    """Geometry's per-segment wall, read through the JA15 harness, moves with an exact offset of
    either border: + for the epicardium outward, - for the endocardium outward."""
    from janusm import harness as H

    ref, aff = H.phantom()
    kw = {"epi_shift_mm": shift} if border == "epi" else {"endo_shift_mm": shift}
    test, _ = H.phantom(**kw)
    walls_r, seg_r = H.segment_thickness(ref, affine=aff)
    assert seg_r is not None and len(walls_r) == 16
    mid = [walls_r[k] for k in range(7, 13)]
    assert np.median(mid) == pytest.approx(H.PHANTOM_WALL, abs=0.5)
    walls_t, _ = H.segment_thickness(test, affine=aff)
    th = H.thickness_error(walls_r, walls_t)
    expect = shift if border == "epi" else -shift
    assert th["n_segments"] == 16
    assert th["median_signed_mm"] == pytest.approx(expect, abs=0.1)
    assert th["median_abs_mm"] == pytest.approx(abs(expect), abs=0.1)
