"""JM-0R read-out (JA23, issue #169) on synthetic phantoms only.

No real, public or held-out case is opened here. The heart is an analytic cylinder-plus-cap LV
(as in ``test_janusm_geometry.py``) with an RV over the septum and an LA on the base; its CT
gives each class a plateau HU and is blurred, so the image edges sit exactly on the label edges.
The guard tests use only the committed case lists (names, never images).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage as ndi

from janusm import geometry as G
from janusm import guard, sealed_r1

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "experiments/JanusM/fir/jm0r_readout.py"
SPLITS = REPO / guard.SPLITS_RELPATH

RC, T, CYL, RV_W = 12.0, 8.0, 30.0, 8.0
HU = {0: -100.0, G.MYO: 120.0, G.LV: 420.0, G.RV: 380.0, G.LA: 400.0}
BLUR = 0.6  # mm, Gaussian sigma: 10-90 % width 2.563 sigma = 1.54 mm


@pytest.fixture(scope="module")
def jm0r():
    spec = importlib.util.spec_from_file_location("jm0r_readout", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["jm0r_readout"] = mod
    spec.loader.exec_module(mod)
    return mod


def phantom(sp=0.5, ins=(120.0, 240.0)):
    """JA1 labels, affine and a dict of analytic coordinates. RV covers angles ``ins``."""
    sp = np.full(3, sp)
    re_ = RC + T
    lo = np.array([-(re_ + RV_W + 4), -(re_ + RV_W + 4), -(CYL + re_ + 4)])
    hi = np.array([re_ + RV_W + 4, re_ + RV_W + 4, 10.0])
    n = np.ceil((hi - lo) / sp).astype(int)
    aff = np.diag([*sp, 1.0])
    aff[:3, 3] = lo + sp / 2
    i, j, k = np.indices(n, dtype=float)
    x, y, z = (lo[a] + ((i, j, k)[a] + 0.5) * sp[a] for a in range(3))
    r = np.hypot(x, y)
    phi = np.degrees(np.arctan2(y, x)) % 360
    rr = np.where(z >= -CYL, r, np.sqrt(r**2 + (z + CYL) ** 2))
    lab = np.zeros(n, np.int16)
    lab[(z < 0) & (rr < re_)] = G.MYO
    lab[(z < 0) & (rr < RC)] = G.LV
    lab[(z >= 0) & (z < 6) & (r < re_)] = G.LA
    rv = (z < 0) & (z >= -CYL) & (r >= re_) & (r < re_ + RV_W) & (phi >= ins[0]) & (phi <= ins[1])
    lab[rv] = G.RV
    return lab, aff, dict(x=x, y=y, z=z, r=r, phi=phi, sp=sp)


def ct_from(lab, sp, blur=BLUR, extra=None):
    ct = np.zeros(lab.shape, np.float32)
    for v, hu in HU.items():
        ct[lab == v] = hu
    if extra is not None:
        mask, hu = extra
        ct[mask] = hu
    return ndi.gaussian_filter(ct, blur / np.asarray(sp, float)).astype(np.float32)


def coronary(lab, w):
    """Three vessels along the axis on the epicardium: LAD anterior (90), LCx lateral (330),
    RCA inferior (210), all at radius RC + T + 1.5 mm."""
    cor = np.zeros(lab.shape, np.int16)
    for cls, deg in ((G.LAD, 90.0), (G.LCX, 330.0), (G.RCA, 210.0)):
        a = np.radians(deg)
        cx, cy = (RC + T + 1.5) * np.cos(a), (RC + T + 1.5) * np.sin(a)
        tube = (np.hypot(w["x"] - cx, w["y"] - cy) < 1.2) & (w["z"] < 0) & (w["z"] > -CYL)
        cor[tube & (lab == 0)] = cls
    return cor


@pytest.fixture(scope="module")
def case(jm0r):
    lab, aff, w = phantom()
    ct = ct_from(lab, w["sp"])
    cor = coronary(lab, w)
    return lab, aff, w, ct, cor, jm0r.measure(lab, ct, aff, cor)


# ------------------------------------------------------------------------------- measurements
def test_halfmax_offsets_and_edge_widths_are_recovered(case):
    *_, r = case
    assert abs(r["endo_halfmax_mm"]) < 0.25
    assert abs(r["epi_halfmax_mm"]) < 0.25
    assert abs(r["endo_10_90_mm"] - 2.563 * BLUR) < 0.35
    assert abs(r["epi_10_90_mm"] - 2.563 * BLUR) < 0.35
    assert r["plateau_blood_hu"] == pytest.approx(420, abs=5)
    assert r["plateau_myocore_hu"] == pytest.approx(120, abs=10)
    assert r["plateau_fat_hu"] == pytest.approx(-100, abs=10)
    # JA17 adaptive band: max(1 mm, 10-90 / 1.09)
    assert r["guard_adaptive_mm"] == pytest.approx(max(1.0, r["endo_10_90_mm"] / 1.09))


def test_a_moved_endocardium_moves_the_offset_by_that_distance(jm0r):
    """The label's LV pool grown 1 mm into the wall, on an unchanged image: the image edge now
    lies 1 mm inside the labelled blood, so the crossing reads about -1 mm."""
    lab, aff, w = phantom()
    ct = ct_from(lab, w["sp"])
    read = lab.copy()
    read[(lab == G.MYO) & (w["r"] < RC + 1.0) & (w["z"] < -1)] = G.LV
    r = jm0r.measure(read, ct, aff)
    assert r["endo_halfmax_mm"] == pytest.approx(-1.0, abs=0.3)


def test_rest_tpr_is_flat_with_the_guard_and_inflated_without(case):
    """A uniform wall has TPR 1. Without a guard the inner third picks up the blood's blur."""
    *_, r = case
    free = lambda g: [v for k, v in r["tpr"][g].items() if k not in (2, 3, 8, 9, 14)]  # noqa: E731
    adaptive = np.median(free("adaptive"))
    assert 0.97 < adaptive < 1.06
    assert np.median(free("0")) > adaptive + 0.02
    assert len(r["tpr"]["1"]) >= 12


def test_thickness_halves_and_depth_agreement(case):
    *_, r = case
    assert r["median_thickness_mm"] == pytest.approx(T, abs=1.0)
    assert r["seg_halves"] == []  # 8 mm at 0.5 mm: 5.3 voxels per third
    assert r["thirds_agree_et_laplace"] > 0.8
    assert r["frame"] == "ok"


def test_arc_sectors_equal_fixed_at_120_degrees_and_move_at_160(case, jm0r):
    *_, r = case
    assert r["septal_arc_deg"] == pytest.approx(120, abs=6)
    assert r["arc_frame_agreement"] >= 0.995  # the recomputed frame is JA3's
    assert r["arc_changed_ml"] / r["seg_ml"] < 0.03
    lab, aff, w = phantom(ins=(100.0, 260.0))
    r2 = jm0r.measure(lab, ct_from(lab, w["sp"]), aff)
    assert r2["septal_arc_deg"] == pytest.approx(160, abs=6)
    assert r2["arc_frame_agreement"] >= 0.995
    assert r2["arc_changed_ml"] / r2["seg_ml"] > 0.05


def test_territories_euclid_and_geodesic(case):
    *_, r = case
    assert r["has_coronary"]
    assert r["terr_n_segments"] == 17
    assert r["terr_voxel_disagree"] < 0.15
    assert set(r["mass_share_euclid"]) == {"LAD", "LCx", "RCA"}
    assert "terr_discordant_euclid_arc" in r


def test_fat_grid_finds_a_core_blob_and_nothing_without_it(case, jm0r):
    *_, r = case
    assert not any(r["fat_grid"].values())
    assert r["fat_hotel_any"] is False
    lab, aff, w, *_ = case
    a = np.radians(330.0)
    cx, cy, cz = (RC + T / 2) * np.cos(a), (RC + T / 2) * np.sin(a), -15.0
    blob = np.sqrt((w["x"] - cx) ** 2 + (w["y"] - cy) ** 2 + (w["z"] - cz) ** 2) < 2.5
    r2 = jm0r.measure(lab, ct_from(lab, w["sp"], extra=(blob, -100.0)), aff)
    assert r2["fat_grid"]["0_5"] and r2["fat_grid"]["-50_5"]
    assert not r2["fat_grid"]["-100_5"]  # the blob is -100 HU: nothing lies below it
    assert r2["fat_hotel_any"] is True


# ------------------------------------------------------------------------------- aggregate
def test_aggregate_holds_no_case_id_and_no_per_case_value(case, jm0r):
    *_, r = case
    rows = [dict(r), dict(r), {"error": "FileNotFoundError", "seconds": 0.1}]
    s = jm0r.aggregate(rows)
    text = json.dumps(s)
    assert s["n_cases"] == 3 and s["n_measured"] == 2 and s["n_frame_ok"] == 2
    assert s["failures_by_type"] == {"FileNotFoundError": 1}
    assert not re.search(r"c\d{4}|s\d{4}|nii|/", text)
    assert "_core_sample" not in text and "id" not in s
    gate = s["ja17_rest_tpr_gate"]
    assert gate["passes"] is not None
    assert s["lima"]["ja20_septal_arc_column_kept"] is False
    assert len(s["hotel"]["core1_hist_pooled"]) == len(jm0r.HIST_EDGES) - 1
    assert s["lima"]["fat_grid_le_5pct_hearts"]  # no fat in the phantom


# ------------------------------------------------------------------------------- guard
def _cases_file(tmp_path, names):
    p = tmp_path / "m0_cases.txt"
    p.write_text("\n".join(names) + "\n")
    return p


def test_the_frozen_jm0_list_passes_the_guard(tmp_path, jm0r):
    jm0 = sorted(sealed_r1.load().jm0)
    assert jm0r.guard_cases(_cases_file(tmp_path, jm0), SPLITS) == jm0


@pytest.mark.parametrize("change", ["missing", "decision", "duplicate", "seal"])
def test_any_other_list_is_refused(tmp_path, jm0r, change):
    s = sealed_r1.load()
    jm0 = sorted(s.jm0)
    names = {"missing": jm0[1:], "decision": jm0[1:] + [sorted(s.decision)[0]],
             "duplicate": jm0 + jm0[:1], "seal": jm0 + [sorted(s.seal)[0]]}[change]
    with pytest.raises(jm0r.Refused):
        jm0r.guard_cases(_cases_file(tmp_path, names), SPLITS)


def test_a_changed_splits_file_is_refused(tmp_path, jm0r):
    bad = tmp_path / "splits.json"
    bad.write_bytes(SPLITS.read_bytes() + b"\n")
    with pytest.raises(jm0r.Refused, match="JA6"):
        jm0r.guard_cases(_cases_file(tmp_path, sorted(sealed_r1.load().jm0)), bad)


def test_the_guard_is_called_with_purpose_any_and_its_refusal_stops(tmp_path, jm0r,
                                                                    monkeypatch):
    seen = {}

    def refuse(names, what, source, purpose):
        seen.update(source=source, purpose=purpose, n=len(names))
        raise guard.HeldOutError("REFUSING x: 1 of 40 name(s) are held out:\n  c0000: ...")

    monkeypatch.setattr(guard, "refuse", refuse)
    with pytest.raises(jm0r.Refused, match="HeldOutError") as e:
        jm0r.guard_cases(_cases_file(tmp_path, sorted(sealed_r1.load().jm0)), SPLITS)
    assert seen == {"source": "ImageCAS-X", "purpose": guard.ANY, "n": 40}
    assert "c0000" not in str(e.value)  # only the guard's first line is passed on


def test_fails_closed_without_the_guard(tmp_path, jm0r, monkeypatch):
    monkeypatch.setitem(sys.modules, "janusm.guard", None)
    with pytest.raises(jm0r.Refused, match="unavailable"):
        jm0r.guard_cases(_cases_file(tmp_path, sorted(sealed_r1.load().jm0)), SPLITS)


def test_main_opens_nothing_when_refused(tmp_path, jm0r, monkeypatch, capsys):
    opened = []
    monkeypatch.setattr(jm0r, "load_case", lambda *a: opened.append(a))
    names = sorted(sealed_r1.load().jm0)[1:] + [sorted(sealed_r1.load().decision)[0]]
    rc = jm0r.main(["--cases", str(_cases_file(tmp_path, names)), "--hc", "nowhere",
                    "--layout", str(tmp_path / "no-layout.json"), "--icx", "nowhere",
                    "--splits", str(SPLITS), "--out", str(tmp_path / "out"), "--np", "1"])
    assert rc == 3 and not opened
    assert "REFUSED" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


# ------------------------------------------------------------------------------- end to end
def test_end_to_end_on_synthetic_nifti(tmp_path, jm0r, monkeypatch, capsys):
    """Synthetic files under made-up ids c9001/c9002 (ImageCAS-X has c0000-c0999), with the guard
    stubbed to accept them: checks the plumbing and that only aggregates leave the job."""
    nib = pytest.importorskip("nibabel")
    lab, aff, w = phantom(sp=0.6)
    ct = ct_from(lab, w["sp"])
    cor = coronary(lab, w)
    ids = {v: k for k, v in jm0r.HC_FALLBACK.items()}
    hc = np.zeros(lab.shape, np.int16)
    for ja1, name in ((G.MYO, "heart_myocardium"), (G.LV, "heart_ventricle_left"),
                      (G.RV, "heart_ventricle_right"), (G.LA, "heart_atrium_left")):
        hc[lab == ja1] = ids[name]
    icx = np.zeros(lab.shape, np.int16)
    icx[cor == G.LAD], icx[cor == G.LCX], icx[cor == G.RCA] = 2, 3, 9  # ImageCAS-X 14 classes
    names = ["c9001", "c9002"]
    (tmp_path / "hc").mkdir()
    (tmp_path / "icx").mkdir()
    layout = {"cases": {}}
    for c in names:
        nib.save(nib.Nifti1Image(hc, aff), tmp_path / "hc" / f"{c}.nii.gz")
        nib.save(nib.Nifti1Image(ct, aff), tmp_path / f"{c}_ct.nii.gz")
        nib.save(nib.Nifti1Image(icx, aff), tmp_path / "icx" / jm0r.icx_label_name(c))
        layout["cases"][c] = {"ct": str(tmp_path / f"{c}_ct.nii.gz")}
    (tmp_path / "layout.json").write_text(json.dumps(layout))
    monkeypatch.setattr(jm0r, "guard_cases", lambda cases, splits: names)
    monkeypatch.setattr(jm0r, "hc_ids", lambda: ids)
    out = tmp_path / "out"
    rc = jm0r.main(["--cases", "x", "--hc", str(tmp_path / "hc"), "--layout",
                    str(tmp_path / "layout.json"), "--icx", str(tmp_path / "icx"),
                    "--splits", "x", "--out", str(out), "--np", "1"])
    assert rc == 0
    cap = capsys.readouterr()
    s = json.loads(cap.out)
    assert s == json.loads((out / "summary.json").read_text())
    assert s["n_frame_ok"] == 2 and s["lima"]["territories"]["n_cases"] == 2
    for c in names:
        assert c not in cap.out and c not in cap.err
    assert str(tmp_path) not in cap.out
    rows = [json.loads(x) for x in (out / "cases.jsonl").read_text().splitlines()]
    assert [r["id"] for r in rows] == names  # the per-case file (stays on Fir) has them
    assert s["provenance"]["script_sha256"] == hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
