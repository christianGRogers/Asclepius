"""Tree-F1 (A9), its ostium (A1) and gates (A2) on tiny synthetic coronary trees.

The fixture is a left tree (LM splitting into LAD and LCx) and a separate tapering RCA on a 0.5 mm
grid, with a contrast 'aortic root' box beside both ostia. The regression tests pin
``segtrain.tf1`` to the experiment copies it replaced (Atlas's, Bridge's and Delta's Trillium
copies) on fixtures where every copy agrees on the ostium."""

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("skimage")

from segtrain import tf1 as T  # noqa: E402

SP = (0.5, 0.5, 0.5)
SHAPE = (110, 64, 48)
X0 = 30                       # tree starts here; the pool box occupies x < X0 - 4
LM = ((X0, 30, 20), (X0 + 15, 30, 20), 3.0, 3.0)
LAD = ((X0 + 15, 30, 20), (X0 + 70, 46, 20), 2.0, 2.0)
LCX = ((X0 + 15, 30, 20), (X0 + 70, 12, 20), 2.0, 2.0)
RCA = ((X0, 54, 36), (X0 + 70, 54, 36), 3.0, 1.6)
REPO = Path(__file__).resolve().parents[1]


def _tube(shape, a, b, ra, rb):
    """Distance-to-segment tube with radius tapering linearly from ``ra`` to ``rb`` (voxels)."""
    g = np.indices(shape).reshape(3, -1).T.astype(float)
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip((g - a) @ ab / (ab @ ab), 0, 1)
    d = np.linalg.norm(g - (a + t[:, None] * ab), axis=1)
    return (d <= ra + t * (rb - ra)).reshape(shape), d.reshape(shape)


def _tree(segments):
    lab = np.zeros(SHAPE, np.uint8)
    best = np.full(SHAPE, np.inf)
    for c, (a, b, ra, rb) in segments:
        m, d = _tube(SHAPE, a, b, ra, rb)
        take = m & (d < best)
        lab[take] = c
        best[take] = d[take]
    return lab


@pytest.fixture(scope="module")
def ref():
    return _tree([(1, LM), (2, LAD), (3, LCX), (4, RCA)])


@pytest.fixture(scope="module")
def aorta():
    m = np.zeros(SHAPE, bool)
    m[:X0 - 4, 4:60, 4:44] = True
    return m


@pytest.fixture(scope="module")
def ct(ref, aorta):
    c = np.zeros(SHAPE, np.float32)
    c[aorta] = 400.0
    c[ref > 0] = 400.0
    return c


def _cut(lab, cls, x_from, width):
    out = lab.copy()
    sl = out[x_from:x_from + width]
    sl[sl == cls] = 0
    return out


# ------------------------------------------------------------------------------- tree-F1
def test_identity_scores_one(ref):
    r = T.tree_f1(ref, ref, SP)
    assert r.tf1 == pytest.approx(1.0)
    assert set(r.per_class) == {1, 2, 3, 4}
    assert r.rooted_fraction == pytest.approx(1.0)
    assert len(r.ostia.ostia) == 2 and r.provisional and not r.flagged


def test_ostia_found_at_the_thick_proximal_ends(ref):
    rep = T.find_ostia(ref, SP)
    for o in rep.ostia:
        assert o.rule == "thick"
        assert o.point[0] < X0 + 6, o          # proximal end, not a distal tip


def test_cut_beyond_tolerance_loses_the_distal_vessel(ref):
    pred = _cut(ref, 2, X0 + 40, 8)          # 4 mm gap in the LAD
    r = T.tree_f1(ref, pred, SP)
    assert 0.2 < r.recall[2] < 0.75
    assert r.per_class[1] == pytest.approx(1.0) and r.per_class[4] == pytest.approx(1.0)
    assert r.tf1 < 0.95


def test_gap_within_tolerance_is_forgiven_only_with_tolerance(ref):
    pred = _cut(ref, 2, X0 + 40, 2)          # 1 mm gap
    assert T.tree_f1(ref, pred, SP, tol_mm=1.5).recall[2] > 0.95
    assert T.tree_f1(ref, pred, SP, tol_mm=0.0).recall[2] < 0.75


def test_cut_at_the_left_main_loses_the_whole_left_tree(ref):
    pred = _cut(ref, 1, X0 + 4, 8)
    r = T.tree_f1(ref, pred, SP)
    assert r.recall[2] == 0.0 and r.recall[3] == 0.0
    assert r.per_class[4] == pytest.approx(1.0)


def test_name_swap_scores_zero_for_the_swapped_classes(ref):
    pred = ref.copy()
    pred[ref == 2], pred[ref == 3] = 3, 2
    r = T.tree_f1(ref, pred, SP)
    assert r.per_class[2] == 0.0 and r.per_class[3] == 0.0
    assert r.tf1 == pytest.approx(0.5)


def test_empty_reference_is_nan_and_empty_prediction_is_zero(ref):
    assert math.isnan(T.tree_f1(np.zeros_like(ref), ref, SP).tf1)
    assert T.tree_f1(ref, np.zeros_like(ref), SP).tf1 == 0.0


def test_ostium_tip_short_of_the_prediction_still_roots(ref):
    pred = ref.copy()
    pred[:X0 + 3] = 0                          # prediction stops 1.5 mm short of the LM ostium
    assert T.tree_f1(ref, pred, SP).recall[2] > 0.95


# ------------------------------------------------------------------------------- A2 gate
def test_fp_blob_is_seen_by_the_gate_not_by_tree_f1(ref):
    pred = ref.copy()
    pred[90:96, 2:8, 2:8] = 2                 # 216-voxel blob, touches nothing
    pred[100:103, 2:5, 40:43] = 2             # 27 voxels: noise, dropped
    assert T.fp_components(ref, pred) == 1
    assert T.fp_components(ref, ref) == 0
    assert T.tree_f1(ref, pred, SP).tf1 > 0.95


def test_raw_prediction_thresholds_probabilities_and_drops_noise(ref):
    prob = np.where(ref > 0, 0.6, 0.0).astype(np.float32)
    prob[100:103, 2:5, 40:43] = 0.9           # small component
    prob[90:96, 2:8, 2:8] = 0.4               # below threshold
    raw = T.raw_prediction(prob)
    assert np.array_equal(raw > 0, ref > 0)
    assert T.fp_components(ref, prob) == 0


def test_remove_small_components_never_keeps_only_the_largest(ref):
    kept = T.remove_small_components(ref > 0)
    assert T.components(kept)[1] == 2


# ------------------------------------------------------------------------------- A1 ostium
def test_aorta_contact_is_the_rule_of_record_and_agrees(ref, aorta):
    rep = T.find_ostia(ref, SP, aorta=aorta)
    assert not rep.provisional and rep.rules[0] == "aorta"
    assert [o.rule for o in rep.ostia] == ["aorta", "aorta"]
    assert not rep.flagged
    assert T.tree_f1(ref, ref, SP, aorta=aorta).tf1 == pytest.approx(1.0)


def test_pool_thick_cross_check_agrees_on_a_clean_tree(ref, aorta, ct):
    rep = T.find_ostia(ref, SP, aorta=aorta, ct=ct)
    assert rep.rules == ("aorta", "thick", "pool_thick")
    for o in rep.ostia:
        assert set(o.candidates) == {"aorta", "thick", "pool_thick"}
        assert o.disagreement_mm <= T.DISAGREEMENT_MM and not o.flagged


def test_cheap_rules_alone_are_provisional(ref, ct):
    rep = T.find_ostia(ref, SP, ct=ct)
    assert rep.provisional and not rep.flagged
    assert T.tree_f1(ref, ref, SP, ct=ct).provisional


def test_disagreeing_rules_flag_the_tree(ref):
    far = np.zeros(SHAPE, bool)
    far[X0 + 72:, 40:52, 14:26] = True       # 'aorta' at the LAD's distal tip
    rep = T.find_ostia(ref, SP, aorta=far)
    left = [o for o in rep.ostia if ref[o.candidates["thick"]] in (1, 2, 3)][0]
    right = [o for o in rep.ostia if o is not left][0]
    assert left.flagged and left.rule == "aorta" and left.disagreement_mm > 5
    assert right.flagged and right.rule == "thick"   # no endpoint touches the aorta at all
    assert len(rep.flagged) == 2
    assert T.tree_f1(ref, ref, SP, aorta=far).flagged


def test_absent_left_main_gives_each_left_tree_its_own_ostium():
    lad = ((X0, 36, 20), (X0 + 70, 50, 20), 2.6, 2.0)
    lcx = ((X0, 24, 20), (X0 + 70, 8, 20), 2.6, 2.0)
    lab = _tree([(2, lad), (3, lcx), (4, RCA)])
    rep = T.find_ostia(lab, SP)
    assert len(rep.ostia) == 3
    assert all(o.point[0] < X0 + 6 for o in rep.ostia)
    pred = _cut(lab, 3, X0 + 2, 8)            # LCx cut at its own ostium
    r = T.tree_f1(lab, pred, SP)
    assert r.recall[2] > 0.95 and r.recall[3] == 0.0


# ------------------------------------------------------------------------------- bridge audit
def test_bridge_audit_tells_true_fp_and_cross_tree_joins(ref):
    before = _cut(ref, 2, X0 + 40, 8)
    before[90:96, 2:8, 2:8] = 2               # FP blob
    lad_d = tuple(np.argwhere(before[X0 + 48:X0 + 52] == 2)[0] + [X0 + 48, 0, 0])
    lad_p = tuple(np.argwhere(before[X0 + 36:X0 + 40] == 2)[0] + [X0 + 36, 0, 0])
    rca = tuple(np.argwhere(before == 4)[0])
    bridges = [dict(p=lad_d, q=lad_p, gap_mm=4.0),
               dict(p=(92, 4, 4), q=lad_d, gap_mm=9.0),
               dict(p=rca, q=(X0 + 2, 30, 20), gap_mm=3.0)]
    after = before.copy()
    for b in bridges:
        p, q = np.array(b["p"], float), np.array(b["q"], float)
        for t in np.linspace(0, 1, 200):
            after[tuple(np.round(p + t * (q - p)).astype(int))] = 2
    audit = T.audit_bridges(ref, before, after, bridges, SP)
    assert [r["touches_reference"] for r in audit.rows] == [True, False, True]
    assert [r["cross_tree"] for r in audit.rows] == [False, False, True]
    assert audit.n_fp_joins == 1 and audit.n_cross_tree == 1
    assert audit.fp_components_before == 1 and audit.fp_components_after == 0
    assert audit.rows[-1]["added_voxels_off_reference"] > 0
    assert audit.as_row()["n_bridges"] == 3


# ------------------------------------------------------------------------------- regression
def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, REPO / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cases(ref):
    swap = ref.copy()
    swap[ref == 2], swap[ref == 3] = 3, 2
    return {"identity": ref, "cut": _cut(ref, 2, X0 + 40, 8), "small_gap": _cut(ref, 2, X0 + 40, 2),
            "lm_cut": _cut(ref, 1, X0 + 4, 8), "swap": swap, "lcx_lost": np.where(ref == 3, 0, ref)}


@pytest.mark.parametrize("tol", [0.0, 1.5])
def test_matches_atlas_copy(ref, tol):
    atlas = _load("atlas_tf1", "trillium/atlas/lib/tf1.py")
    for name, pred in _cases(ref).items():
        theirs = atlas.score(ref, pred.astype(np.uint8), SP, tol=tol)
        ours = T.tree_f1(ref, pred, SP, tol_mm=tol)
        assert ours.tf1 == pytest.approx(theirs["tf1"], abs=1e-9), name
        assert ours.per_class == pytest.approx(theirs["tf1_per_class"], abs=1e-9), name
        assert T.fp_components(ref, pred) == theirs["fp_components"], name


@pytest.mark.parametrize("tol", [0.0, 1.5])
def test_matches_delta_and_bridge_copies(ref, tol):
    pytest.importorskip("cc3d")
    pytest.importorskip("networkx")
    delta = _load("delta_lib", "trillium/delta/deltalib.py")
    bridge = _load("bridge_tf1", "trillium/bridge/py/tf1.py")
    dref, bref = delta.RefTree(ref, SP), bridge.Ref(ref, SP)
    ours_ostia = sorted(T.find_ostia(ref, SP).points)
    assert sorted(dref.roots) == ours_ostia
    for name, pred in _cases(ref).items():
        ours = T.tree_f1(ref, pred, SP, tol_mm=tol)
        d = delta.tree_f1(dref, pred, tol_mm=tol)
        b = bridge.score(bref, pred, tol=tol)
        assert ours.tf1 == pytest.approx(d["tf1"], abs=1e-9), name
        assert ours.tf1 == pytest.approx(b["tf1"], abs=1e-9), name
        assert T.fp_components(ref, pred) == delta.fp_components(dref, pred > 0), name
