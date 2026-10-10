"""Echo D1/D2/D13 fixes in Atlas's modules: every name a case travels under maps to its case id
before any sealed check (A14); both reads of a case share a split; the explicit ImageCAS-X split
is kept, never replaced by the hash split; listed cases in imagesTs are refused."""

import json

import nibabel as nib
import numpy as np
import pytest

from segtrain import plans
from segtrain.config import Config, LabelSet, TaskConfig
from segtrain.index import assign_split
from segtrain.proxy import canonical_case, icx_label_path, sealed_reason, split_read_suffix


@pytest.mark.parametrize("name,case", [
    ("c0002", "c0002"), ("c0002__r2", "c0002"), ("c0002_rA", "c0002"),
    ("imagecas_0003", "c0002"), ("imagecas_0003__r3", "c0002"), ("ImageCAS-3", "c0002"),
    ("3", "c0002"), ("3.img", "c0002"), ("s0001", None), ("imagecas_1001", None), ("", None),
])
def test_canonical_case(name, case):
    assert canonical_case(name) == case


def test_sealed_reason_maps_names_and_refuses_unmappable():
    sealed = {"c0002"}
    assert "sealed" in sealed_reason("imagecas_0003__r2", sealed)
    assert "does not map" in sealed_reason("patient_x", sealed)
    assert sealed_reason("c0003__r2", sealed) is None
    assert split_read_suffix("c0003__r2") == ("c0003", "__r2")


def test_reads_of_one_case_share_its_split():
    for i in range(200):
        c = f"c{i:04d}"
        s = assign_split(c, 0.15, 0.15)
        assert assign_split(f"{c}__r2", 0.15, 0.15) == s
        assert assign_split(f"imagecas_{i + 1:04d}", 0.15, 0.15) == s


def _setup(tmp_path, idents, folder="imagesTr", task_file_text="explicit_split: icx\n"):
    tf = tmp_path / "task.yaml"
    tf.write_text(task_file_text)
    task = TaskConfig(712, "CoronaryBranches", LabelSet("b", {"x": 1}), (0.5, 0.5, 0.5),
                      source_path=tf)
    cfg = Config(zenodo_root=tmp_path, nnunet_raw=tmp_path / "raw",
                 nnunet_preprocessed=tmp_path / "pre", nnunet_results=tmp_path / "res",
                 runs_root=tmp_path / "runs")
    d = task.raw_dir(cfg) / folder
    d.mkdir(parents=True, exist_ok=True)
    for i in idents:
        (d / f"{i}_0000.nii.gz").write_bytes(b"")
    return cfg, task


def test_explicit_split_keeps_both_reads_together_and_reports_absent(tmp_path, capsys):
    cfg, task = _setup(tmp_path, ["c0001", "c0001__r2", "imagecas_0004", "c0005"])
    out = plans.write_explicit_splits(cfg, task, ["c0001", "c0003", "c0009"], ["c0005"],
                                      sealed={"c0002"})
    split = json.loads(out.read_text())[0]
    assert split == {"train": ["c0001", "c0001__r2", "imagecas_0004"], "val": ["c0005"]}
    assert "c0009" in capsys.readouterr().out          # absent: reported, not silently dropped


def test_explicit_split_refuses_cases_converted_as_test(tmp_path):
    cfg, task = _setup(tmp_path, ["c0001", "c0005"])
    _setup(tmp_path, ["c0003"], folder="imagesTs")
    with pytest.raises(RuntimeError, match="imagesTs"):
        plans.write_explicit_splits(cfg, task, ["c0001", "c0003"], ["c0005"])


def test_explicit_split_refuses_a_converted_sealed_read(tmp_path):
    cfg, task = _setup(tmp_path, ["c0001", "c0005", "imagecas_0003__r2"])
    with pytest.raises(ValueError, match="A14"):
        plans.write_explicit_splits(cfg, task, ["c0001"], ["c0005"], sealed={"c0002"})


def test_plan_keeps_an_explicit_split(tmp_path, monkeypatch):
    cfg, task = _setup(tmp_path, ["c0001", "c0005"])
    plans.write_explicit_splits(cfg, task, ["c0001"], ["c0005"])
    path = plans.write_splits(cfg, task)                # what `segtrain plan` calls
    assert json.loads(path.read_text()) == [{"train": ["c0001"], "val": ["c0005"]}]


def test_plan_without_an_explicit_split_refuses_the_hash_split(tmp_path, monkeypatch):
    cfg, task = _setup(tmp_path, ["c0001", "c0005"])
    monkeypatch.delenv(plans.ICX_DIR_ENV, raising=False)
    with pytest.raises(RuntimeError, match="explicit"):
        plans.write_splits(cfg, task)
    icx = tmp_path / "icx"
    icx.mkdir()
    (icx / "train.txt").write_text("2\n")               # c0001
    (icx / "val.txt").write_text("6\n")                 # c0005
    monkeypatch.setenv(plans.ICX_DIR_ENV, str(icx))
    path = plans.write_splits(cfg, task)
    assert json.loads(path.read_text()) == [{"train": ["c0001"], "val": ["c0005"]}]


def test_icx_label_path_accepts_the_unzipped_zenodo_tree(tmp_path):
    (tmp_path / "segmentations").mkdir()
    nib.save(nib.Nifti1Image(np.zeros((2, 2, 2), np.uint8), np.eye(4)),
             str(tmp_path / "segmentations" / "1.coronary.nii.gz"))
    assert icx_label_path(tmp_path, "c0000").parent.name == "segmentations"
    assert icx_label_path(tmp_path, "c0001").name == "2.coronary.nii.gz"
