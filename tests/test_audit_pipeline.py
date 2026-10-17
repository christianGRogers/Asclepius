"""Echo audit (Round 6, Q4): the data path from proxy / SegQueue export to splits_final.json.

Every test here records a CONFIRMED defect against the master plan and is marked
``xfail(strict=True)``: the suite stays green while the defect exists, and turns red the
moment a fix lands (remove the marker then). Evidence and owners:
vault/Plans/Experiments/Echo - Audit of the segtrain implementation against the master plan.md
"""

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from segtrain.config import Config, load_task
from segtrain.convert import convert_dataset
from segtrain.index import assign_split, build_rows, scan, write_meta
from segtrain.proxy import load_sealed
from segtrain.splits import read_meta

REPO = Path(__file__).resolve().parents[1]
SHAPE = (8, 8, 8)
# The ImageCAS grid orientation (c0001's mask affine, scaled down): voxel x -> patient left.
AFFINE = np.array([[-0.5, 0, 0, 40.0], [0, 0.5, 0, 70.0], [0, 0, 0.5, -320.0], [0, 0, 0, 1]])


def _save(path, arr, affine=AFFINE):
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(arr, affine), str(path))


def _label():
    lab = np.zeros(SHAPE, np.uint8)
    lab[1:3, 2:6, 4] = 1
    lab[3:7, 2, 4] = 2
    lab[3:7, 5, 4] = 3
    lab[1:7, 7, 1] = 4
    return lab


def _ct():
    return np.full(SHAPE, 100, np.int16)


def _cfg(tmp_path, root):
    return Config(zenodo_root=root, nnunet_raw=tmp_path / "raw",
                  nnunet_preprocessed=tmp_path / "pre", nnunet_results=tmp_path / "res",
                  runs_root=tmp_path / "runs", link_mode="copy", convert_workers=1)


def _index(root):
    """`segtrain index --root <root> --layout nested` with its defaults (runbook step 4)."""
    rows = build_rows(scan(root, layout="nested"))
    write_meta(root / "meta.csv", rows)
    return read_meta(root / "meta.csv")


def _nonsealed(n_test, n_train):
    sealed = load_sealed()
    test, train = [], []
    for i in range(100, 1000):
        c = f"c{i:04d}"
        if c in sealed:
            continue
        s = assign_split(c, 0.15, 0.15)
        if s == "test" and len(test) < n_test:
            test.append(c)
        elif s == "train" and len(train) < n_train:
            train.append(c)
        if len(test) == n_test and len(train) == n_train:
            return test, train
    raise AssertionError("not enough cases")


# ------------------------------------------------------------------------------- D1
def test_runbook_index_convert_split_keeps_every_icx_train_case(tmp_path):
    test_ids, train_ids = _nonsealed(n_test=2, n_train=3)
    root = tmp_path / "proxy"
    for c in test_ids + train_ids:
        _save(root / c / "ct.nii.gz", _ct())
        _save(root / c / "labels.nii.gz", _label())
    rows = _index(root)
    cfg, task = _cfg(tmp_path, root), load_task(712)
    report = convert_dataset(cfg, task, rows, layout="nested")
    assert report.ok
    from segtrain.plans import write_explicit_splits

    # ImageCAS-X's own lists: all of these are ImageCAS-X train cases, one of them val.
    icx_train, icx_val = test_ids + train_ids[1:], train_ids[:1]
    path = write_explicit_splits(cfg, task, icx_train, icx_val, sealed=load_sealed())
    split = json.loads(Path(path).read_text())[0]
    assert sorted(split["train"]) == sorted(icx_train), "ImageCAS-X train cases were dropped"


# ------------------------------------------------------------------------------- D2
def _export_case(root, name):
    """SegQueue's export layout: <case>/ct.nii.gz + <case>/segmentations/<structure>.nii.gz."""
    _save(root / name / "ct.nii.gz", _ct())
    lab = _label()
    for i, s in enumerate(("left_main", "left_anterior_descending", "left_circumflex",
                           "right_coronary_artery"), start=1):
        _save(root / name / "segmentations" / f"{s}.nii.gz", (lab == i).astype(np.uint8))


def test_sealed_case_under_its_segqueue_name_is_refused(tmp_path):
    assert "c0002" in load_sealed()
    root = tmp_path / "export"
    _export_case(root, "imagecas_0003")          # = c0002, sealed ImageCAS-X test
    _export_case(root, "imagecas_0004")          # = c0003, open
    rows = _index(root)
    # pin both into training so the hash split cannot hide the leak
    rows = [r.__class__(r.case_id, "train", r.study_type) for r in rows]
    cfg, task = _cfg(tmp_path, root), load_task(712)
    convert_dataset(cfg, task, rows, layout="nested")
    trained = {p.name for p in (cfg.nnunet_raw / task.nnunet_name / "imagesTr").glob("*")}
    assert not any(n.startswith("imagecas_0003") for n in trained), trained


def test_second_read_of_a_sealed_case_is_refused(tmp_path):
    root = tmp_path / "export"
    _export_case(root, "c0002")
    _export_case(root, "c0002__r2")
    rows = [r.__class__(r.case_id, "train", r.study_type) for r in _index(root)]
    cfg, task = _cfg(tmp_path, root), load_task(712)
    convert_dataset(cfg, task, rows, layout="nested")
    trained = {p.name for p in (cfg.nnunet_raw / task.nnunet_name / "imagesTr").glob("*")}
    assert not any(n.startswith("c0002") for n in trained), trained


# ------------------------------------------------------------------------------- D3
def test_physically_identical_z_reversed_label_is_kept(tmp_path):
    root = tmp_path / "export"
    name = "c0100"
    _save(root / name / "ct.nii.gz", _ct())
    flip = AFFINE.copy()
    flip[2, 2] = -AFFINE[2, 2]
    flip[2, 3] = AFFINE[2, 3] + AFFINE[2, 2] * (SHAPE[2] - 1)   # same voxel centres in space
    _save(root / name / "labels.nii.gz", _label()[:, :, ::-1].copy(), flip)
    rows = [r.__class__(r.case_id, "train", r.study_type) for r in _index(root)]
    cfg, task = _cfg(tmp_path, root), load_task(712)
    convert_dataset(cfg, task, rows, layout="nested")
    out = nib.load(str(cfg.nnunet_raw / task.nnunet_name / "labelsTr" / f"{name}.nii.gz"))
    got = np.asarray(out.dataobj)
    assert (got > 0).sum() == (_label() > 0).sum()


def test_case_with_dropped_labels_does_not_enter_training(tmp_path):
    root = tmp_path / "export"
    name = "c0100"
    _save(root / name / "ct.nii.gz", _ct())
    shifted = AFFINE.copy()
    shifted[0, 3] += 5.0
    _save(root / name / "labels.nii.gz", _label(), shifted)
    rows = [r.__class__(r.case_id, "train", r.study_type) for r in _index(root)]
    cfg, task = _cfg(tmp_path, root), load_task(712)
    report = convert_dataset(cfg, task, rows, layout="nested")
    images = cfg.nnunet_raw / task.nnunet_name / "imagesTr" / f"{name}_0000.nii.gz"
    assert not images.exists() or not report.ok


# ------------------------------------------------------------------------------- D8
def test_proxy_cli_fails_when_no_case_was_written(tmp_path, capsys):
    from segtrain.cli import main

    cases = tmp_path / "cases"
    _save(cases / "c0100" / "ct.nii.gz", _ct())
    _save(cases / "c0100" / "coronary_arteries.nii.gz", (_label() > 0).astype(np.float64))
    icx = tmp_path / "icx"
    (icx / "segmentations").mkdir(parents=True)
    _save(icx / "segmentations" / "101.coronary.nii.gz", _label())   # nested, not flat
    (icx / "train.txt").write_text("101\n104\n")                      # 104 = c0103: absent
    (icx / "val.txt").write_text("")
    rc = main(["proxy", "--cases", str(cases), "--icx", str(icx), "--root", str(tmp_path / "out")])
    out = capsys.readouterr().out
    assert rc != 0 or "0 proxy cases written" in out, out


# ------------------------------------------------------------------------------- D9
def test_plan_printout_shows_the_ct_window(tmp_path):
    from segtrain.plans import describe_plans, finalize_plans

    cfg, task = _cfg(tmp_path, tmp_path / "proxy"), load_task(712)
    pre = task.preprocessed_dir(cfg)
    pre.mkdir(parents=True)
    plans = {"foreground_intensity_properties_per_channel": {"0": {
        "percentile_00_5": -164.0, "percentile_99_5": 640.0, "mean": 200.0, "std": 150.0}},
        "configurations": {"3d_fullres": {"spacing": [0.5, 0.5, 0.5], "patch_size": [256] * 3,
                                          "batch_size": 2, "normalization_schemes":
                                          ["CTNormalization"], "architecture": {}}}}
    f = pre / f"{task.plans_name}.json"
    f.write_text(json.dumps(plans))
    finalize_plans(f, task)
    text = describe_plans(cfg, task)
    assert "-300" in text and "1300" in text, text


def test_runbook_convert_points_at_the_proxy_tree():
    text = (REPO / "docs" / "TRAINING-R1.md").read_text()
    step4 = text.split("## 4.")[1].split("## 5.")[0]
    convert_line = [ln for ln in step4.splitlines() if "segtrain convert" in ln][0]
    assert "--zenodo-root" in convert_line or "zenodo_root" in step4


# ------------------------------------------------------------------------------- D13
def test_prepare_job_for_712_keeps_the_icx_split(tmp_path):
    from segtrain.slurm import render_prepare_script

    cfg, task = _cfg(tmp_path, tmp_path / "proxy"), load_task(712)
    text = render_prepare_script(cfg, task, convert=True, layout="nested")
    plan_at = text.index("segtrain plan")
    assert "--explicit-icx" in text[plan_at:], text
