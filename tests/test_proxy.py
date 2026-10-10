"""segtrain.proxy: ImageCAS-X names projected onto the ImageCAS mask (D0/D1/D1b), A4 QA hook, sealed
exclusion (A14),
and the proxy tree going through index -> convert for the 4-class task with an ignore label."""

import json
import sys
import types

import nibabel as nib
import numpy as np
import pytest

from segtrain import proxy
from segtrain.config import Config, LabelSet, TaskConfig
from segtrain.convert import convert_dataset
from segtrain.index import build_rows, scan, write_meta
from segtrain.splits import read_meta

SP = (0.5, 0.5, 0.5)


def _tree():
    """A tiny coronary-like pair of trees on a 40^3 grid.

    Our (thick) mask: an LM trunk splitting into LAD and LCx, a diagonal off the LAD, a ramus at the
    carina, a separate RCA, and one unnamed distal stub on the LAD. ImageCAS-X (thin) names only the
    centre lines, and does not name the stub, which must then inherit LAD by geodesic growth.
    """
    mask = np.zeros((40, 40, 40), bool)
    icx = np.zeros((40, 40, 40), np.uint8)
    mask[18:22, 18:22, 5:15] = True
    icx[19:21, 19:21, 5:15] = 1  # LM
    mask[18:22, 18:22, 15:35] = True
    icx[19:21, 19:21, 15:30] = 2  # LAD (unnamed stub z 30..34)
    mask[18:22, 5:18, 13:17] = True
    icx[19:21, 5:18, 14:16] = 3  # LCx
    mask[22:30, 25:29, 22:26] = True
    icx[22:30, 26:28, 23:25] = 4  # D1 off the LAD
    mask[22:28, 14:18, 14:18] = True
    icx[22:28, 15:17, 15:17] = 8  # ramus at the carina
    mask[2:6, 2:6, 5:35] = True
    icx[3:5, 3:5, 5:35] = 9  # RCA (separate tree)
    return mask, icx


def test_projection_follows_territory_and_ramus_to_lcx():
    mask, icx = _tree()
    lab, st = proxy.project_names(mask, icx, SP)
    assert not st.empty and st.unreached_frac == 0.0
    assert ((lab > 0) == mask).all(), "every mask voxel is named, nothing outside the mask"
    assert lab[20, 20, 10] == 1  # LM
    assert (
        lab[20, 20, 20] == 2 and lab[20, 20, 33] == 2
    )  # LAD, incl. the stub ImageCAS-X never named
    assert lab[20, 10, 15] == 3  # LCx
    assert lab[26, 27, 24] == 2  # D1 -> LAD (territory, D1)
    assert lab[25, 16, 16] == 3  # ramus -> LCx (D1b)
    assert lab[3, 3, 20] == 4  # RCA
    assert 0 < st.geodesic_frac < 0.5 and st.near_frac > 0.5


def test_projection_refuses_mismatched_grids():
    mask, icx = _tree()
    with pytest.raises(ValueError):
        proxy.project_names(mask, icx[:-1], SP)


def _no_namer(monkeypatch):
    """Simulate a checkout without Bridge's segtrain.namer (the module may already be imported)."""
    import segtrain

    monkeypatch.setitem(sys.modules, "segtrain.namer", None)
    monkeypatch.delattr(segtrain, "namer", raising=False)


def test_qa_without_namer_fails_loudly(monkeypatch, tmp_path):
    """A21a: a missing namer (or a dependency of it) never yields a silently un-QA'd proxy."""
    _no_namer(monkeypatch)
    mask, icx = _tree()
    lab, _ = proxy.project_names(mask, icx, SP)
    with pytest.raises(RuntimeError, match="A4 proxy QA unavailable"):
        proxy.qa_with_namer(lab, mask, SP)
    files, icx_dir = _case_files(tmp_path, "c0000", mask, icx)
    (icx_dir / "train.txt").write_text("1\n")
    with pytest.raises(RuntimeError, match="A4 proxy QA unavailable"):
        proxy.build_proxy_tree({"c0000": files}, icx_dir, tmp_path / "out", sealed=set())
    assert not (tmp_path / "out" / "c0000").exists()
    rec = proxy.make_case("c0000", files["ct"], files["mask"], icx_dir / "1.coronary.nii.gz",
                          tmp_path / "out")
    assert not rec.ok and "A4" in rec.error


def _fake_namer(monkeypatch, ignore=None, exclude=False, ramus_only=False):
    mod = types.ModuleType("segtrain.namer")
    mod.disagreement = lambda label, mask, spacing: dict(
        ignore=ignore, exclude=exclude, ramus_only=ramus_only
    )
    monkeypatch.setitem(sys.modules, "segtrain.namer", mod)
    import segtrain

    monkeypatch.setattr(segtrain, "namer", mod, raising=False)


def test_qa_masks_carina_disagreement_as_ignore(monkeypatch):
    mask, icx = _tree()
    lab, _ = proxy.project_names(mask, icx, SP)
    ign = np.zeros_like(mask)
    ign[18:22, 18:22, 14:16] = True
    _fake_namer(monkeypatch, ignore=ign)
    out, qa = proxy.qa_with_namer(lab, mask, SP)
    assert qa.applied and qa.ignore_voxels == int((ign & mask).sum())
    assert (out[ign & mask] == proxy.IGNORE).all() and (out[~ign] == lab[~ign]).all()


def test_ramus_only_disagreement_is_neither_ignored_nor_excluded(monkeypatch):
    mask, icx = _tree()
    lab, _ = proxy.project_names(mask, icx, SP)
    ign = np.zeros_like(mask)
    ign[22:28, 14:18, 14:18] = True
    _fake_namer(monkeypatch, ignore=ign, exclude=True, ramus_only=True)
    out, qa = proxy.qa_with_namer(lab, mask, SP)
    assert qa.ramus_only and not qa.excluded and qa.ignore_voxels == 0 and (out == lab).all()


def test_load_sealed_reads_the_orchestrator_json(tmp_path):
    p = tmp_path / "sealed.json"
    p.write_text(
        json.dumps(
            {"sealed_icx_test": ["c0001"], "sealed_quality0": ["c0005"], "open_icx_test": ["c0009"]}
        )
    )
    assert proxy.load_sealed(p) == {"c0001", "c0005"}
    with pytest.raises(FileNotFoundError):
        proxy.load_sealed(tmp_path / "missing.json")


def test_repo_sealed_list_loads():
    sealed = proxy.load_sealed()
    assert len(sealed) == 100


def _case_files(tmp_path, case, mask, icx):
    d = tmp_path / "src" / case
    d.mkdir(parents=True)
    aff = np.diag([*SP, 1.0])
    ct = d / "ct.nii.gz"
    nib.save(nib.Nifti1Image(np.full(mask.shape, 300, np.int16), aff), str(ct))
    m = d / "mask.nii.gz"
    nib.save(nib.Nifti1Image(mask.astype(np.uint8), aff), str(m))
    icx_dir = tmp_path / "icx"
    icx_dir.mkdir(exist_ok=True)
    nib.save(
        nib.Nifti1Image(icx, aff),
        str(icx_dir / f"{proxy.case_to_imagecas_id(case)}.coronary.nii.gz"),
    )
    return {"ct": ct, "mask": m}, icx_dir


def test_build_proxy_tree_writes_nested_cases_and_refuses_sealed(tmp_path, monkeypatch):
    _no_namer(monkeypatch)
    mask, icx = _tree()
    cases = {}
    for c in ("c0000", "c0001", "c0002"):
        cases[c], icx_dir = _case_files(tmp_path, c, mask, icx)
    (icx_dir / "train.txt").write_text("1\n2\n")
    (icx_dir / "val.txt").write_text("3\n")
    out = tmp_path / "proxy"
    recs = proxy.build_proxy_tree(cases, icx_dir, out, sealed={"c0999"}, apply_qa=False)
    assert sorted(r.case for r in recs if r.ok) == ["c0000", "c0001", "c0002"]
    assert (out / "c0001" / "ct.nii.gz").exists() and (out / "c0001" / "labels.nii.gz").exists()
    report = json.loads((out / "proxy_report.json").read_text())
    assert report["n_ok"] == 3 and report["qa_applied"] is False
    with pytest.raises(ValueError):
        proxy.build_proxy_tree(cases, icx_dir, tmp_path / "p2", sealed={"c0001"}, apply_qa=False)


def test_excluded_case_is_not_written(tmp_path, monkeypatch):
    _fake_namer(monkeypatch, ignore=None, exclude=True, ramus_only=False)
    mask, icx = _tree()
    files, icx_dir = _case_files(tmp_path, "c0000", mask, icx)
    rec = proxy.make_case(
        "c0000", files["ct"], files["mask"], icx_dir / "1.coronary.nii.gz", tmp_path / "proxy"
    )
    assert rec.ok and rec.excluded and not (tmp_path / "proxy" / "c0000").exists()


BRANCHES = LabelSet(
    "coronary_branches",
    {
        "left_main": 1,
        "left_anterior_descending": 2,
        "left_circumflex": 3,
        "right_coronary_artery": 4,
    },
)


def test_proxy_tree_converts_with_ignore_label_and_sealed_exclusion(tmp_path, monkeypatch):
    """index -> convert on the proxy tree: ignore (5) survives as nnU-Net's ignore, and sealed
    cases never convert."""
    mask, icx = _tree()
    ign = np.zeros_like(mask)
    ign[18:22, 18:22, 14:16] = True
    _fake_namer(monkeypatch, ignore=ign)
    cases = {}
    for c in ("c0000", "c0001", "c0002"):
        cases[c], icx_dir = _case_files(tmp_path, c, mask, icx)
    (icx_dir / "train.txt").write_text("1 2 3\n")
    root = tmp_path / "proxy"
    proxy.build_proxy_tree(cases, icx_dir, root, sealed=set(), subsets=("train",))

    rows = build_rows(scan(root, layout="nested"), val_fraction=0.0, test_fraction=0.0, seed=1)
    write_meta(root / "meta.csv", rows)
    task_file = tmp_path / "Dataset712_CoronaryBranches.yaml"
    sealed_file = tmp_path / "sealed.json"
    sealed_file.write_text(json.dumps({"sealed_icx_test": ["c0002"], "sealed_quality0": []}))
    task_file.write_text(f"ignore_label: true\nsealed_list: {sealed_file}\n")
    task = TaskConfig(
        dataset_id=712,
        dataset_name="CoronaryBranches",
        label_set=BRANCHES,
        spacing=(0.5, 0.5, 0.5),
        source_path=task_file,
    )
    cfg = Config(
        zenodo_root=root,
        nnunet_raw=tmp_path / "raw",
        nnunet_preprocessed=tmp_path / "pre",
        nnunet_results=tmp_path / "res",
        runs_root=tmp_path / "runs",
        link_mode="copy",
        convert_workers=1,
    )
    report = convert_dataset(cfg, task, read_meta(root / "meta.csv"), layout="nested")
    assert report.ok, report.render()
    assert report.n_train == 2 and report.n_excluded == 1
    raw = task.raw_dir(cfg)
    assert not (raw / "labelsTr" / "c0002.nii.gz").exists()
    lab = np.asarray(nib.load(str(raw / "labelsTr" / "c0000.nii.gz")).dataobj)
    assert set(np.unique(lab)) == {0, 1, 2, 3, 4, 5}
    ds = json.loads((raw / "dataset.json").read_text())
    assert ds["labels"]["ignore"] == 5 and ds["labels"]["right_coronary_artery"] == 4


def test_qa_runs_with_bridges_real_namer():
    """The A4 contract with segtrain.namer.disagreement (Bridge's module) holds end to end."""
    pytest.importorskip("segtrain.namer")
    mask, icx = _tree()
    lab, _ = proxy.project_names(mask, icx, SP)
    out, qa = proxy.qa_with_namer(lab, mask, np.diag([-0.5, 0.5, 0.5, 1.0]))
    assert qa.applied and out.shape == lab.shape
    assert set(np.unique(out)) <= {0, 1, 2, 3, 4, proxy.IGNORE}
    assert qa.excluded or qa.ignore_voxels >= 0
