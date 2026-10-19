"""D27: a sealed SegQueue14 pool volume is refused at every guarded entry point, and the
SegQueue14 export leaves it out by default and counts it (issue #84).

The guards: the trainer's ``sealed_guard``, ``segtrain convert``, ``reads.load_read_folder`` and
the A12 reads report, ``evaluate.score_predictions``, ``aorta.produce_aortas``, and
``segqueue14-export``. The A14 ImageCAS seal (``trillium/sealed_test.json``) is unchanged; its own
tests (test_finetune, test_audit_followup, test_plans_coronary, test_icx4_sealed) still run.
"""

import importlib.util
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
_SRC = REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.append(str(_SRC))

from segtrain.pool_seal import SealedPoolError, load_pool_seal  # noqa: E402

SEAL = json.loads((REPO / "configs/segqueue14/sealed-pool-2026-10.json").read_text())
SEALED_VOL = SEAL["primary"]["volumes"][0]                 # e.g. Figshare-23057000__PA1.nii.gz
SEALED = SEALED_VOL[: -len(".nii.gz")]
REPORT_ONLY = SEAL["report_only"]["patients"][0]
OPEN_POOL = SEAL["primary"]["extension_order"][0]          # a pool patient that is not sealed
AFF = np.diag([0.5, 0.5, 0.5, 1.0])


def _save(path, arr, affine=AFF):
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(arr, affine), str(path))


# ------------------------------------------------------------------ the trainer's guard
def test_trainer_guard_refuses_a_sealed_pool_volume_and_keeps_a14():
    from segtrain.nnunet_ext.sealed_guard import refuse_sealed

    assert refuse_sealed(["c0003", "c0003__r2", "imagecas_0004"]) == 3   # A14 as before
    # the last two are unlisted volumes of sealed patients, grouped as the ingest does (#87)
    for name in (SEALED, f"{SEALED}__r2", REPORT_ONLY, "Mendeley-SDN-spb25zt2c4__s999",
                 "Slicer-SampleData__TruncalValve_4DCT_f20"):
        with pytest.raises(SealedPoolError, match="D27"):
            refuse_sealed(["c0003", name])
    with pytest.raises(RuntimeError, match="A14"):                     # A14 still refuses
        refuse_sealed(["c0003", "imagecas_0003__r2"])


def test_trainer_guard_without_the_seal_file_refuses(tmp_path, monkeypatch):
    from segtrain.nnunet_ext.sealed_guard import refuse_sealed

    monkeypatch.setenv("SEGTRAIN_POOL_SEAL", str(tmp_path / "missing.json"))
    with pytest.raises(FileNotFoundError):
        refuse_sealed(["c0003"])


# ------------------------------------------------------------------ convert
def _convert_tree(tmp_path, names):
    from segqueue14 import labels
    from segtrain.config import Config, TaskConfig, load_label_set
    from segtrain.index import build_rows, scan, write_meta
    from segtrain.splits import read_meta

    root = tmp_path / "export"
    for name in names:
        lab = np.zeros((12, 10, 8), np.uint8)
        lab[2:8, 3:5, 3:5] = 2
        _save(root / name / "ct.nii.gz", np.zeros(lab.shape, np.int16))
        _save(root / name / "labels.nii.gz", lab)
    rows = build_rows(scan(root), val_fraction=0.0, test_fraction=0.0, seed=1)
    write_meta(root / "meta.csv", rows)
    cfg = Config(zenodo_root=root, nnunet_raw=tmp_path / "raw",
                 nnunet_preprocessed=tmp_path / "pre", nnunet_results=tmp_path / "res",
                 runs_root=tmp_path / "runs", link_mode="copy", convert_workers=1)
    task = TaskConfig(dataset_id=798, dataset_name="PoolSealConvert",
                      label_set=load_label_set(labels.LABEL_SET_NAME,
                                               labels_dir=REPO / "configs" / "labels"),
                      spacing=None, configuration="3d_fullres")
    return cfg, task, read_meta(root / "meta.csv")


def test_convert_refuses_a_sealed_pool_volume_before_writing(tmp_path):
    from segtrain.convert import convert_dataset

    cfg, task, rows = _convert_tree(tmp_path, [OPEN_POOL, SEALED, f"{SEALED}__r2"])
    with pytest.raises(SealedPoolError, match="2 of 3"):
        convert_dataset(cfg, task, rows)
    assert not task.raw_dir(cfg).exists()
    with pytest.raises(ValueError, match="acceptance"):
        convert_dataset(cfg, task, rows, pool_seal="acceptance")


def test_convert_exclude_mode_drops_and_reports(tmp_path):
    from segtrain.convert import convert_dataset

    cfg, task, rows = _convert_tree(tmp_path, [OPEN_POOL, SEALED, f"{SEALED}__r2"])
    report = convert_dataset(cfg, task, rows, pool_seal="exclude")
    assert report.ok, report.render()
    assert report.n_train == 1 and report.n_pool_sealed == 2
    assert "2 sealed pool volume(s) excluded (D27)" in report.render()
    written = sorted(p.name for p in (task.raw_dir(cfg) / "labelsTr").iterdir())
    assert written == [f"{OPEN_POOL}.nii.gz"]


def test_convert_cli_flag(tmp_path, monkeypatch):
    from segtrain import cli

    args = cli.build_parser().parse_args(["convert", "-t", "710", "--exclude-sealed-pool"])
    assert args.exclude_sealed_pool is True
    args = cli.build_parser().parse_args(["convert", "-t", "710"])
    assert args.exclude_sealed_pool is False


# ------------------------------------------------------------------ reads
def _reads_tree(root, names):
    lab = np.zeros((30, 20, 12), np.uint8)
    lab[3:25, 8:11, 4:7] = 1
    for folder in names:
        _save(root / folder / "segmentations" / "left_anterior_descending.nii.gz", lab)


def test_load_read_folder_refuses_a_sealed_pool_case(tmp_path, monkeypatch):
    from segtrain import reads as R

    _reads_tree(tmp_path, ["imagecas_0004", "imagecas_0004__r2", SEALED, f"{SEALED}__r2"])
    opened = []
    monkeypatch.setattr(R, "_read_from_segmentations",
                        lambda seg: opened.append(seg) or (None, None))
    with pytest.raises(SealedPoolError, match="D27"):
        R.load_read_folder(str(tmp_path))
    assert opened == []                                  # refused before anything was opened


def test_load_read_folder_exclude_and_acceptance(tmp_path):
    from segtrain import reads as R

    _reads_tree(tmp_path, ["imagecas_0004", "imagecas_0004__r2", SEALED, f"{SEALED}__r2"])
    refused = []
    cases = R.load_read_folder(str(tmp_path), refused=refused, pool_seal="exclude")
    assert [c.case for c in cases] == ["c0003"]
    assert sum("(D27)" in why for why in refused) == 2
    # acceptance keeps the pool folders past the D27 check (A14 still applies unless milestone)
    with pytest.warns(UserWarning, match="A14"):
        cases = R.load_read_folder(str(tmp_path), pool_seal="acceptance")
    cases = R.load_read_folder(str(tmp_path), pool_seal="acceptance", milestone=True)
    assert SEALED in {c.case for c in cases}


def test_reads_report_refuses_or_excludes_a_sealed_pool_case():
    from segtrain import reads as R

    lab = np.zeros((30, 20, 12), np.uint8)
    lab[3:25, 8:11, 4:7] = R.LAD
    open_case = R.CaseReads("c0003", {"r1": lab, "r2": lab}, (0.5, 0.5, 0.5))
    sealed_case = R.CaseReads(SEALED, {"r1": lab, "r2": lab}, (0.5, 0.5, 0.5))
    with pytest.raises(SealedPoolError):
        R.first_reads_report([open_case, sealed_case], use_namer=False)
    report = R.first_reads_report([open_case, sealed_case], use_namer=False,
                                  pool_seal="exclude")
    assert report["wave"]["n_cases"] == 1
    assert report["wave"]["n_pool_sealed_excluded"] == 1
    assert [r["case"] for r in report["cases"]] == ["c0003"]


def test_reads_report_cli_option():
    from segtrain import cli

    args = cli.build_parser().parse_args(["reads-report", "x", "--out", "y"])
    assert args.sealed_pool == "refuse"


# ------------------------------------------------------------------ evaluate, aorta
def test_score_predictions_refuses_a_sealed_pool_prediction(tmp_path):
    from segtrain.evaluate import score_predictions

    class _Task:
        class label_set:  # noqa: N801
            names = ["a"]

        @staticmethod
        def raw_dir(cfg):
            return tmp_path / "raw"

    preds = tmp_path / "preds"
    for name in ("c0003", SEALED):
        _save(preds / f"{name}.nii.gz", np.zeros((4, 4, 4), np.uint8))
    with pytest.raises(SealedPoolError):
        score_predictions(None, _Task, preds)
    assert score_predictions(None, _Task, preds, pool_seal="exclude") == {}   # no labelsTs


def test_produce_aortas_refuses_a_sealed_pool_volume(tmp_path):
    from segtrain.aorta import produce_aortas

    with pytest.raises(SealedPoolError):
        produce_aortas({SEALED: tmp_path / "ct.nii.gz"}, tmp_path / "out",
                       segmenter=lambda *a, **k: None)


# ------------------------------------------------------------------ segqueue14-export
def _exporter():
    spec = importlib.util.spec_from_file_location(
        "sq14_export_seal", REPO / "server" / "girder_segqueue14" / "export.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fake_models(cases, submissions_opened):
    """Assignments and cases as ``collect`` sees them; records every submission lookup."""
    assignments = [{"_id": f"a{i}", "caseId": c["_id"]} for i, c in enumerate(cases)]
    byId = {c["_id"]: c for c in cases}

    class Assignment:
        def find(self, query, sort=None):
            return list(assignments)

    class Case:
        def load(self, caseId, force=False):
            return byId.get(caseId)

    class Submission:
        def findOne(self, query):
            submissions_opened.append(query["assignmentId"])
            return {"_id": "s" + query["assignmentId"], "fileId": "f"}

    return lambda: (None, Assignment, Case, Submission)


def test_export_leaves_sealed_cases_out_by_default_and_counts_them(monkeypatch):
    ex = _exporter()
    cases = [{"_id": 1, "name": OPEN_POOL}, {"_id": 2, "name": SEALED},
             {"_id": 3, "name": REPORT_ONLY}, {"_id": 4, "name": "imagecas_0002"}]
    opened = []
    monkeypatch.setattr(ex, "_models", _fake_models(cases, opened))
    seal = load_pool_seal()

    got = list(ex.collect(seal=seal))
    exported = [name for _, sub, name in got if name is not ex.SEALED]
    sealed = [case["name"] for case, _, name in got if name is ex.SEALED]
    assert exported == [OPEN_POOL, "imagecas_0002"]
    assert sealed == [SEALED, REPORT_ONLY]
    assert opened == ["a0", "a3"]               # no submission of a sealed case was loaded
    # --limit counts exported cases only
    assert [n for _, _, n in ex.collect(seal=seal, limit=2) if n is not ex.SEALED] == exported
    # acceptance scoring (no seal passed) includes them
    assert [n for _, _, n in ex.collect()] == [c["name"] for c in cases]


def test_export_cli_options():
    ex = _exporter()
    args = ex.buildParser().parse_args(["--out", "x"])
    assert args.acceptance_scoring is False and args.seal_file is None
    args = ex.buildParser().parse_args(["--out", "x", "--acceptance-scoring",
                                        "--seal-file", "s.json"])
    assert args.acceptance_scoring is True and args.seal_file == "s.json"
