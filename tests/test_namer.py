"""The rule-based branch namer (A4 QA, A7 renaming, A8 ramus switch) on tiny synthetic trees.

The fixture is a left tree (a thick left main from a superior ostium, splitting into an anterior LAD
and a posterior LCx) and a separate right tree (RCA), drawn as tubes in an 80^3 grid at 1 mm. The
world frame is RAS: the left tree sits at more negative x, anterior is +y, superior is +z.
The smallest-x skeleton vertex lies mid-vessel, as in real trees: the frozen ostium score's 'beyond'
feature singles out whichever endpoint is vertex 0 (the experiment's quirk, kept by the port).
"""

import numpy as np
import pytest
from scipy import ndimage

from segtrain import namer
from segtrain.namer import LAD, LCX, LM, RCA

SHAPE = (80, 80, 80)
OSTIUM, BIF = (25, 40, 65), (20, 40, 55)
RAS = np.eye(4)


def _tube(lab, a, b, r, k):
    a, b = np.array(a, float), np.array(b, float)
    g = np.indices(lab.shape).reshape(3, -1).T.astype(float)
    d = b - a
    t = np.clip((g - a) @ d / (d @ d), 0, 1)
    inside = (np.linalg.norm(g - (a + t[:, None] * d), axis=1) <= r).reshape(lab.shape)
    lab[inside & (lab == 0)] = k


def _tree(ramus=False, right=True, ostium=OSTIUM):
    lab = np.zeros(SHAPE, np.uint8)
    _tube(lab, ostium, BIF, 3.0, LM)
    _tube(lab, BIF, (23, 70, 15), 2.0, LAD)
    _tube(lab, BIF, (23, 10, 20), 2.0, LCX)
    if ramus:  # between LAD and LCx in the anterior direction, leaving at the bifurcation
        _tube(lab, BIF, (24, 43, 25), 1.8, LCX)
    if right:
        _tube(lab, (55, 40, 65), (65, 50, 10), 2.5, RCA)
    return lab


def _dice(a, b, k):
    x, y = a == k, b == k
    return 2 * (x & y).sum() / max(x.sum() + y.sum(), 1)


@pytest.fixture(scope="module")
def truth():
    return _tree()


@pytest.fixture(scope="module")
def named(truth):
    return namer.name_tree(truth > 0, RAS)


def test_names_the_four_classes(truth, named):
    for k in (LM, LAD, LCX, RCA):
        assert _dice(truth, named.labels, k) > 0.9, namer.CLASS_NAMES[k]
    assert named.labels.dtype == np.uint8 and ((named.labels > 0) == (truth > 0)).all()


def test_decisions_sit_at_the_ostium_and_the_carina(named):
    d = named.decisions
    assert d.failure is None and not d.fused_trees and d.n_ramus == 0
    # the ostium is where the LM ends on the surface: 3 mm (its radius) beyond the tube's axis end
    assert np.linalg.norm(np.subtract(d.ostium_vox, OSTIUM)) <= 4
    assert np.linalg.norm(np.subtract(d.lm_end_vox, BIF)) <= 3
    assert 10 < d.lm_length_mm < 18
    assert d.left_component != d.right_component


def test_every_class_is_one_connected_piece(named):
    for k in (LM, LAD, LCX, RCA):
        _, n = ndimage.label(named.labels == k, structure=np.ones((3, 3, 3)))
        assert n == 1, namer.CLASS_NAMES[k]


def test_left_and_right_follow_the_affine(truth, named):
    # the same patient stored LAS (as every ImageCAS mask is): voxel x flipped, affine says so
    las = np.diag([-1.0, 1, 1, 1])
    las[0, 3] = SHAPE[0] - 1
    out = namer.name_tree(truth[::-1] > 0, las).labels[::-1]
    for k in (LM, LAD, LCX, RCA):  # skeletonisation is not exactly flip-equivariant
        assert _dice(out, named.labels, k) > 0.95, namer.CLASS_NAMES[k]
    # bare spacings are read as LAS (as_affine); reading the RAS volume that way swaps the trees
    wrong = namer.name_tree(truth > 0, namer.as_affine((1.0, 1.0, 1.0)))
    assert _dice(truth, wrong.labels, RCA) < 0.1


def test_names_in_the_input_are_ignored(truth, named):
    noisy = truth.copy()
    noisy[noisy == LAD] = LCX
    assert (namer.name_tree(truth, RAS).labels == named.labels).all()
    assert (namer.rename(noisy, RAS).labels == named.labels).all()


def test_ramus_switch():
    lab = _tree(ramus=True)
    ram = (lab > 0) & (_tree() == 0)  # the ramus voxels
    out = {r: namer.name_tree(lab > 0, RAS, ramus=r) for r in ("LCx", "LAD")}
    assert out["LCx"].decisions.n_ramus >= 1
    assert (out["LCx"].labels[ram] == LCX).mean() > 0.9
    assert (out["LAD"].labels[ram] == LAD).mean() > 0.9
    assert out["LCx"].ramus_candidates[ram].mean() > 0.9
    assert not out["LCx"].ramus_candidates[lab == RCA].any()
    with pytest.raises(ValueError):
        namer.name_tree(lab > 0, RAS, ramus="ramus")


def test_a_short_thick_left_main_is_not_pruned_as_a_spur():
    # a skimage skeleton ends ~ one radius inside the ostium: a 4.5 mm LM leaves a stub shorter
    # than the spur threshold at the bifurcation; pruning it would leave no bifurcation at all
    lab = _tree(ostium=(21, 40, 59))
    out = namer.name_tree(lab > 0, RAS)
    assert out.decisions.failure is None
    assert np.linalg.norm(np.subtract(out.decisions.lm_end_vox, BIF)) <= 3
    for k in (LM, LAD, LCX):
        assert _dice(lab, out.labels, k) > 0.85, namer.CLASS_NAMES[k]


@pytest.mark.parametrize("ramus", [False, True])
def test_skeleton_matches_kimimaro_teasar(ramus):
    # the frozen experiment skeletonised with kimimaro (TEASAR); the port re-implements it in scipy
    kimimaro = pytest.importorskip("kimimaro")
    from scipy.spatial import cKDTree

    mask = _tree(ramus=ramus) > 0
    sp = np.array([0.4, 0.4, 0.5])
    ours = namer._Skel(mask, sp)
    comp, _ = ndimage.label(mask, structure=np.ones((3, 3, 3)))
    ref = kimimaro.skeletonize(
        comp.astype(np.uint32),
        teasar_params={"scale": 1.5, "const": 2, "pdrf_scale": 100000, "pdrf_exponent": 4},
        anisotropy=tuple(sp),
        dust_threshold=100,
        fix_branching=True,
        progress=False,
        parallel=1,
    )
    kv = np.concatenate([s.vertices for s in ref.values()])
    kdeg = np.concatenate(
        [np.bincount(s.edges.ravel(), minlength=len(s.vertices)) for s in ref.values()]
    )
    deg = np.array([len(ours.adj[i]) for i in range(len(ours.V))])
    assert abs(len(ours.V) - len(kv)) <= 0.02 * len(kv)
    assert (deg == 1).sum() == (kdeg == 1).sum() and (deg >= 3).sum() == (kdeg >= 3).sum()
    assert np.percentile(cKDTree(kv).query(ours.P)[0], 95) <= 0.5


def test_naming_bridge_carries_the_name_across_a_gap(truth, named):
    cut = truth > 0
    cut[:, 58, :] = False  # a ~2 mm gap along the LAD (only the LAD crosses y = 58)
    out = namer.name_tree(cut, RAS)
    assert len(out.info["bridges"]) == 1 and out.info["bridges"][0]["gap_mm"] <= 4
    distal = cut & (np.indices(SHAPE)[1] > 58)
    assert (out.labels[distal] == LAD).all()
    assert namer.name_tree(cut, RAS, bridge_mm=0).info["bridges"] == []
    wide = truth > 0
    wide[:, 56:61, :] = False  # ~8 mm: too far to bridge
    assert namer.name_tree(wide, RAS).info["bridges"] == []


def test_empty_and_degenerate_inputs():
    out = namer.name_tree(np.zeros(SHAPE, bool), RAS)
    assert out.decisions.failure == "empty" and not out.labels.any()
    blob = np.zeros(SHAPE, bool)
    blob[10:14, 10:14, 10:14] = True
    assert namer.name_tree(blob, RAS).decisions.failure == "no_tree"
    single = namer.name_tree(_tree(right=False) > 0, RAS)
    assert single.decisions.failure == "single_tree" and not (single.labels == RCA).any()
    assert namer.extract_decisions(np.zeros(SHAPE, np.uint8), RAS).failure == "empty"


def test_extract_decisions_reads_any_labelling(truth):
    d = namer.extract_decisions(truth, RAS)
    assert np.linalg.norm(np.subtract(d.ostium_vox, OSTIUM)) <= 3
    assert np.linalg.norm(np.subtract(d.lm_end_vox, BIF)) <= 4
    assert d.left_component != d.right_component and not d.fused_trees


def test_compare_agreeing_labels_has_no_flags(named):
    rep = namer.compare(named.labels, named.labels, RAS)
    assert rep.flags == [] and not rep.wholesale and not rep.ignore.any()
    assert rep.ostium_distance_mm == 0 and rep.lm_dice == 1 and rep.lad_lcx_swap == 0


def test_compare_ignore_is_naming_only_and_sits_at_the_carina(truth, named):
    rep = namer.compare(truth, named.labels, RAS)
    assert rep.ignore.any() and not rep.wholesale
    assert (rep.ignore == ((truth > 0) & (named.labels > 0) & (truth != named.labels))).all()
    assert rep.ignore_within_10mm_of_carina > 0.8
    # an extent difference (a voxel only one side calls vessel) is never ignored
    thin = truth.copy()
    thin[:, :, 30:32] = 0
    assert not namer.compare(thin, named.labels, RAS).ignore[:, :, 30:32].any()


def test_compare_wholesale_triggers(named):
    swapped = named.labels.copy()
    swapped[named.labels == LAD], swapped[named.labels == LCX] = LCX, LAD
    rep = namer.compare(swapped, named.labels, RAS)
    assert "swap" in rep.flags and rep.wholesale and rep.lad_lcx_swap > 0.9
    trees = named.labels.copy()
    trees[(named.labels > 0) & (named.labels < RCA)], trees[named.labels == RCA] = RCA, LAD
    assert "tree" in namer.compare(trees, named.labels, RAS).flags
    short = named.labels.copy()  # reference LM ends 7 mm lower: ostium moves, LM overlap drops
    short[(named.labels == LM) & (np.indices(SHAPE)[2] > 58)] = LAD
    rep = namer.compare(short, named.labels, RAS)
    assert "ostium" in rep.flags and rep.ostium_distance_mm > 5 and rep.wholesale


def test_absent_left_main_reference_is_not_excluded(named):
    # separate LAD/LCx ostia: the rules always find an LM, so LM/ostium disagreement is no evidence
    ref = named.labels.copy()
    ref[ref == LM] = LAD
    rep = namer.compare(ref, named.labels, RAS)
    assert rep.no_lm_reference and "lm" not in rep.flags and "ostium" not in rep.flags
    assert not rep.wholesale and rep.ignore.any()
    assert not namer.compare(named.labels, named.labels, RAS).no_lm_reference


def test_ramus_only_swap_is_exempt():
    lab = _tree(ramus=True) > 0
    d1b = namer.name_tree(lab, RAS, ramus="LCx")
    other = namer.name_tree(lab, RAS, ramus="LAD")  # a reader who calls the ramus LAD
    rep = namer.compare(other.labels, d1b.labels, RAS, ramus_candidates=d1b.ramus_candidates)
    assert rep.flags == ["swap"] and rep.ramus_only and not rep.wholesale
    assert namer.compare(other.labels, d1b.labels, RAS).wholesale  # no candidates, no exemption


def test_disagreement_is_the_proxy_contract(truth):
    las = truth[::-1].copy()  # the project's grid: bare spacings are read as LAS
    rep = namer.disagreement(las, las > 0, (1.0, 1.0, 1.0))
    assert set(rep) >= {"ignore", "exclude", "ramus_only", "reason"}
    assert rep["ignore"].shape == SHAPE and rep["ignore"].dtype == bool
    assert not rep["exclude"] and not rep["ramus_only"]
    assert rep["ignore"].sum() < 0.05 * (las > 0).sum()
    bad = las.copy()
    bad[las == LAD], bad[las == LCX] = LCX, LAD
    assert namer.disagreement(bad, las > 0, (1.0, 1.0, 1.0))["exclude"]
    with pytest.raises(ValueError):
        namer.as_affine((1.0, 1.0))


def test_icx_to_four_territory_and_ramus():
    icx = np.arange(15, dtype=np.uint8)
    four = namer.icx_to_four(icx)
    assert four.tolist() == [0, LM, LAD, LCX, LAD, LAD, LCX, LCX, LCX, RCA, RCA, RCA, LCX, LCX, 0]
