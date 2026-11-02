"""Janus-M per-case features (S6 / S7) for Round 4 Group C, on synthetic phantoms only.

R4-S14 (JA69 (a)): the arc-proportional septal values and the one ``arc_segments``, now in
``janusm.geometry``; R4-S9 and R4-S12's feature keys.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage as ndi

from janusm import features as F
from janusm import geometry as G

sys.path.insert(0, str(Path(__file__).parent))
import janusm_synth as Y  # noqa: E402

JM0R = Path(__file__).resolve().parents[1] / "experiments/JanusM/fir/jm0r_readout.py"


# JM-0R's implementation before the move (dev, 2026-10-30), frozen here so the move is checked
# against it.
def _old_theta(labels, aff, aha):
    """The JA3 angle of every myocardial voxel (0 at the anterior insertion, + into the septum),
    recomputed exactly as ``janusm.geometry.aha17`` does with its defaults."""
    myo, lv, rv, la = (labels == c for c in (G.MYO, G.LV, G.RV, G.LA))
    face = ndi.generate_binary_structure(3, 1)
    world = lambda ijk: ijk @ aff[:3, :3].T + aff[:3, 3]  # noqa: E731
    base = world(np.argwhere(lv & ndi.binary_dilation(la, face))).mean(0)
    pidx = np.argwhere(myo)
    p = world(pidx)
    dist = np.linalg.norm(p - base, axis=1)
    apex = p[dist >= dist.max() - 3.0].mean(0)
    axis = (apex - base) / np.linalg.norm(apex - base)
    s = (p - base) @ axis
    cav = float(((world(np.argwhere(lv)) - base) @ axis).max())
    helper = np.eye(3)[int(np.argmin(np.abs(axis)))]
    e1 = helper - (helper @ axis) * axis
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    rel = p - base
    ang = np.degrees(np.arctan2(rel @ e2, rel @ e1)) % 360.0
    contact = ndi.binary_dilation(rv, face)[myo] & (s >= 0) & (s <= 2 / 3 * cav)
    h = np.sort(ang[contact])
    gaps = np.diff(np.concatenate([h, h[:1] + 360.0]))
    g = int(np.argmax(gaps))
    start, end = float(h[(g + 1) % len(h)]), float(h[g])

    def direction(deg):
        r = np.radians(deg)
        return np.cos(r) * e1 + np.sin(r) * e2

    ant = np.array([0.0, 1.0, 1.0]) / np.sqrt(2)
    ref, sign = (start, 1.0) if direction(start) @ ant >= direction(end) @ ant else (end, -1.0)
    return pidx, (sign * (ang - ref)) % 360.0


def _old_arc_segments(labels, aff, aha):
    """Septal sectors proportional to the measured septal arc in the basal and mid rings (JA20:
    the two septal segments of each ring); the apical ring and 17 stay as JA3 cuts them. Returns
    (segments, agreement of the recomputed fixed sectors with JA3's), or (None, None)."""
    pidx, theta = _old_theta(labels, aff, aha)
    fixed = aha.segments[tuple(pidx.T)]
    six = np.array([2, 3, 4, 5, 6, 1])
    ring = np.isin(fixed, (1, 2, 3, 4, 5, 6)) | np.isin(fixed, (7, 8, 9, 10, 11, 12))
    if not ring.any():
        return None, None
    recomputed = six[(theta // 60).astype(int) % 6] + np.where(fixed > 6, 6, 0)
    agree = float(np.mean(recomputed[ring] == fixed[ring]))
    arc = float(np.clip(aha.septal_arc_deg, 60.0, 240.0))
    rest = (360.0 - arc) / 4
    edges = [arc / 2, arc, arc + rest, arc + 2 * rest, arc + 3 * rest]
    k = np.searchsorted(edges, theta, side="right")
    new = six[np.clip(k, 0, 5)] + np.where(fixed > 6, 6, 0)
    seg = aha.segments.copy()
    seg[tuple(pidx[ring].T)] = new[ring]
    return seg, agree




@pytest.fixture(scope="module")
def phantom():
    lab, ct, aff, cor = Y.heart()
    geo = G.analyse(lab, affine=aff, coronary=cor)
    f = F.case_features(lab, ct, aff, cor)
    return lab, ct, aff, cor, geo, f


def _sub_median(lab, ct, geo):
    myo = lab == G.MYO
    return float(np.median([ct[myo & (geo.aha.segments == k) & (geo.depth.u < 1 / 3)
                               & (geo.depth.d_endo >= 1.0)].mean() for k in range(1, 17)]))


def test_arc_values_at_120_degrees_equal_the_fixed_values(phantom):
    lab, ct, aff, _, geo, f = phantom
    a = F.septal_arc_values(lab, ct, aff, geo, _sub_median(lab, ct, geo), arc_deg=120.0)
    assert a["agreement"] >= G.ARC_AGREEMENT_MIN
    for k in F.ARC_SEPTAL:
        assert a["wall_mm"][k] == pytest.approx(f["wall_mm"][k], abs=0.01)
        assert a["rel_subendo_hu"][k] == pytest.approx(f["rel_subendo_hu"][k], abs=0.01)


def test_arc_at_180_degrees_moves_the_septal_share(phantom):
    lab, _, aff, _, geo, _ = phantom
    myo = lab == G.MYO
    ring = myo & np.isin(geo.aha.segments, range(1, 13))

    def share(seg):
        return float(np.isin(seg[ring], F.ARC_SEPTAL).mean())

    s120, _ = G.arc_segments(lab, aff, geo.aha, arc_deg=120.0)
    s180, _ = G.arc_segments(lab, aff, geo.aha, arc_deg=180.0)
    assert share(s120) == pytest.approx(share(geo.aha.segments), abs=0.005)
    assert share(s120) == pytest.approx(1 / 3, abs=0.03)
    assert share(s180) == pytest.approx(1 / 2, abs=0.03)
    assert (s180 != geo.aha.segments).any()
    assert np.array_equal(s180[myo & np.isin(geo.aha.segments, range(13, 18))],
                          geo.aha.segments[myo & np.isin(geo.aha.segments, range(13, 18))])


def test_jm0r_and_geometry_agree_on_the_phantom(phantom):
    lab, _, aff, _, geo, _ = phantom
    spec = importlib.util.spec_from_file_location("jm0r_readout_s14", JM0R)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.arc_segments is G.arc_segments  # one implementation (JA69 (a))
    new, agree = G.arc_segments(lab, aff, geo.aha)
    old, agree_old = _old_arc_segments(lab, aff, geo.aha)
    assert agree == agree_old and np.array_equal(new, old)


def test_case_features_carries_the_arc_values(phantom):
    *_, f = phantom
    a = f["septal_arc"]
    assert a["agreement"] >= G.ARC_AGREEMENT_MIN
    assert set(a["wall_mm"]) == set(a["rel_subendo_hu"]) == set(F.ARC_SEPTAL)
    assert all(v is not None for v in a["wall_mm"].values())
    assert F.FEATURES_VERSION == "1.1.0"


def test_arc_values_are_none_below_the_agreement_guard(phantom, monkeypatch):
    lab, ct, aff, _, geo, _ = phantom
    real = G.arc_segments
    monkeypatch.setattr(G, "arc_segments", lambda *a, **k: (real(*a, **k)[0], 0.99))
    a = F.septal_arc_values(lab, ct, aff, geo, 100.0)
    assert a["agreement"] == 0.99 and "0.995" in a["note"]
    assert all(v is None for v in a["wall_mm"].values())
    assert all(v is None for v in a["rel_subendo_hu"].values())


def test_patient_fat_clusters_and_geodesic_majority_are_recorded(phantom):
    *_, f = phantom
    assert set(f["fat_clusters_mm3_patient"]) == {str(c) for c in F.FAT_CUTS}
    assert set(f["segment_territory_geodesic"]) == set(f["segment_territory"])
