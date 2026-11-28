"""trillium/janus1f, the J1F-A launcher (#392): every `check` self-test, every refusal, the pins and
the
SBATCH headers. Synthetic data only: no CT, no label, no model output is read."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "trillium" / "janus1f" / "lib"
LAUNCHER = ROOT / "trillium" / "janus1f" / "janus1f"
sys.path.insert(0, str(LIB))

from janus1f import (  # noqa: E402
    collect,
    dataset,
    decode,
    ledger,
    pins,
    predict_inputs,
    sbatch,
    selftest,
    split,
)


# ------------------------------------------------------------------ every self-test `check` runs
@pytest.mark.parametrize("test", selftest.TESTS, ids=lambda t: t.__name__[2:])
def test_check_selftest_passes(test):
    assert test()


def test_check_runs_every_selftest():
    names = {t.__name__ for t in selftest.TESTS}
    for required in (
        "t_parent_copy",
        "t_hierarchical_decode",
        "t_fa19_T",
        "t_G_round_trip",
        "t_fa20_val",
        "t_chunk_hygiene",
        "t_plans",
        "t_scorer_and_gates",
        "t_ignore13",
        "t_no_locked_in_719",
        "t_verdict",
        "t_ledger",
        "t_pins",
        "t_sbatch",
    ):
        assert required in names


# ------------------------------------------------------------------ the pinned files
def test_copies_are_byte_identical_to_the_files_of_record():
    assert (
        pins.sha256_file(pins.SCORER)
        == pins.sha256_file(ROOT / "experiments" / "Atlas" / "j1f_r3" / "j1f_scorer.py")
        == pins.SCORER_SHA256
    )
    assert (
        pins.sha256_file(pins.GATES)
        == pins.sha256_file(ROOT / "experiments" / "Judge" / "j1f_r3" / "j1f_gates.json")
        == pins.GATES_SHA256
    )
    assert pins.sha256_file(pins.SPLIT) == pins.SPLIT_SHA256
    assert pins.sha256_file(LIB / "test_scorer.py") == pins.sha256_file(
        ROOT / "experiments" / "Atlas" / "j1f_r3" / "test_scorer.py"
    )


@pytest.mark.parametrize("name", ["scorer", "gates", "labels.py", "tf1.py"])
def test_a_pinned_file_that_differs_refuses(tmp_path, name):
    src = dict((n, p) for n, p, _, _ in pins.FOUR)[name]
    bad = tmp_path / os.path.basename(src)
    shutil.copyfile(src, bad)
    with open(bad, "a") as f:
        f.write("\n")
    with pytest.raises(pins.PinError, match=name):
        pins.check_four({name: str(bad)}, {})


def test_split_pins_and_fitcheck():
    sp = split.load()
    assert len(sp["train620"]) == 620 and len(sp["locked100"]) == 100
    assert not set(sp["train620"]) & set(sp["locked100"])
    assert not (set(sp["train620"]) | set(sp["locked100"])) & sp["sealed"]
    fc = split.fitcheck_ids(sp["train620"])
    assert set(fc) <= set(sp["train620"]) and len(fc) == 20
    ref = json.loads(
        (ROOT / "experiments" / "Delta" / "j1f_r3" / "splits_final_j1f.json").read_text()
    )
    assert split.splits_final(sp) == ref


def test_parents_file():
    from janus1f import parents

    p = parents.load()
    assert parents.source_index(p) == [0, 1, 2, 3, 4, 2, 2, 2, 3, 3, 3, 4, 4]
    assert p["ignore_label_on_disk"] == 13


# ------------------------------------------------------------------ refusals (Delta v3 §4.5 +
# F-A36)
def test_refuses_locked_or_sealed_id_in_training():
    sp = split.load()
    with pytest.raises(split.SplitError, match="locked"):
        split.refuse_training([sp["locked100"][3]], sp)
    with pytest.raises(split.SplitError, match="sealed"):
        split.refuse_training([sorted(sp["sealed"])[0]], sp)
    with pytest.raises(split.SplitError, match="outside"):
        split.refuse_training(["c9999"], sp)


def test_refuses_a_255_in_a_dataset719_label():
    with pytest.raises(dataset.PrepError, match="13"):
        dataset.check_label_values(np.array([0, 3, 255], np.uint8), "c0001")


def test_refuses_a_locked_id_in_dataset719(tmp_path):
    sp = split.load()
    img = Path(dataset.paths(str(tmp_path))["raw"]) / "imagesTr"
    img.mkdir(parents=True)
    (img / f"{sp['locked100'][0]}_0000.nii.gz").write_bytes(b"")
    with pytest.raises(split.SplitError, match="locked"):
        dataset.check_raw_dataset(str(tmp_path), sp)


def test_refuses_converter_counts_off_f0r2():
    with pytest.raises(dataset.PrepError, match="F0-r2"):
        dataset.check_converter_line(dict(pins.CONVERTER_LINE, other_ignore=9))


def test_refuses_a_used_dataset_id(tmp_path):
    (tmp_path / "nnunet_results" / "Dataset719_Someone").mkdir(parents=True)
    with pytest.raises(dataset.PrepError, match="already used"):
        dataset.refuse_used_id(str(tmp_path))


def test_refuses_an_incomplete_case_set(tmp_path):
    sp = split.load()
    layout = {"cases": {}}
    with pytest.raises(dataset.PrepError, match="fetch"):
        dataset.write_labels(str(tmp_path), sp, layout, str(tmp_path), 1)


def test_refuses_plans_that_are_not_step_t(tmp_path):
    (tmp_path / "plans.json").write_text("{}")
    (tmp_path / "dataset_fingerprint.json").write_text("{}")
    with pytest.raises(pins.PinError, match="Step T"):
        dataset.place_plans(str(tmp_path / "w"), str(tmp_path))


def test_refuses_a_missing_janus0_baseline(tmp_path):
    sp = split.load()
    maps = tmp_path / "maps_a1"
    maps.mkdir()
    with pytest.raises(decode.DecodeError, match="marker"):
        collect.check_inputs(str(tmp_path), str(tmp_path), sp, collect.env_state({}))
    j0 = tmp_path / "j0" / "pred_fir"
    j0.mkdir(parents=True)
    with pytest.raises(decode.DecodeError, match="Janus 0"):
        decode.decode_chunk(
            str(_one_case_chunk(tmp_path)), str(tmp_path / "out"), str(j0), selftest._NpyIO()
        )


def _one_case_chunk(tmp_path):
    d = tmp_path / "chunk"
    d.mkdir()
    np.savez_compressed(d / "c0001.npz", probabilities=np.full((13, 2, 2, 2), 1 / 13, np.float16))
    (d / "c0001.pkl").write_text("x")
    return d


def test_refuses_a_second_look_and_a_third(tmp_path):
    p = str(tmp_path / "looks.json")
    ledger.open_look(p, "J1F-A", ["F", "T"])
    with pytest.raises(ledger.LedgerError, match="second run"):
        ledger.open_look(p, "J1F-A", ["F", "T"])


def test_predict_inputs_hold_only_locked_ids(tmp_path):
    sp = split.load()
    ct = tmp_path / "ct.nii.gz"
    ct.write_bytes(b"")
    layout = tmp_path / "layout.json"
    layout.write_text(json.dumps({"cases": {c: {"ct": str(ct)} for c in sp["locked100"]}}))
    ch = predict_inputs.build(str(tmp_path), str(layout), sp)
    assert [len(c) for c in ch] == [10] * 10 and sum(ch, []) == sorted(sp["locked100"])
    (tmp_path / "in_l100" / "chunk3" / f"{sp['train620'][0]}_0000.nii.gz").symlink_to(ct)
    with pytest.raises(split.SplitError, match="non-locked"):
        predict_inputs.build(str(tmp_path), str(layout), sp)


# ------------------------------------------------------------------ the launcher itself (dry run)
def _env(tmp_path, **kw):
    env = dict(
        os.environ,
        SCRATCH=str(tmp_path),
        J1F_DRYRUN="1",
        HOME=str(tmp_path / "home"),
        J1F_PYTHON=sys.executable,
    )
    env.pop("JANUS0", None)
    env.pop("J1F_WORK", None)
    env.update(kw)
    return env


def _run(tmp_path, *args, launcher=LAUNCHER, **kw):
    return subprocess.run(
        ["bash", str(launcher), *args],
        env=_env(tmp_path, **kw),
        capture_output=True,
        text=True,
        timeout=600,
    )


def test_check_refuses_an_unset_janus0_compile(tmp_path):
    r = _run(tmp_path, "check")
    assert r.returncode != 0 and "JANUS0_COMPILE is unset" in r.stderr
    r = _run(tmp_path, "check", JANUS0_COMPILE="yes")
    assert r.returncode != 0 and "must be t or f" in r.stderr


def test_check_refuses_a_superseded_exported_gate_hash(tmp_path):
    r = _run(
        tmp_path,
        "check",
        JANUS0_COMPILE="f",
        J1F_GATES_SHA256="09ddb06f4fc5f8265588b3fa6ea65d4d0cc010f0839b8a245a3e224dc7f4fc5f",
    )
    assert r.returncode != 0 and "gate file of record" in r.stderr


@pytest.mark.slow
def test_check_prints_the_four_pins_and_passes(tmp_path):
    r = _run(tmp_path, "check", JANUS0_COMPILE="f")
    assert r.returncode == 0, r.stdout + r.stderr
    for name, _, sha, _ in pins.FOUR:
        assert f"pin {name:9s} {sha} OK" in r.stdout
    assert r.stdout.count("selftest ") == len(selftest.TESTS) and " FAIL " not in r.stdout
    assert "nnUNet_compile = JANUS0_COMPILE = f" in r.stdout


@pytest.mark.slow
def test_check_fails_on_a_pin_mismatch(tmp_path):
    """A copy of the repository's relevant trees with the gate file changed by one byte."""
    repo = tmp_path / "repo"
    for sub in ("trillium/janus1f", "trillium/icx4", "configs/janus1", "src"):
        shutil.copytree(ROOT / sub, repo / sub, ignore=shutil.ignore_patterns("__pycache__"))
    with open(repo / "configs" / "janus1" / "j1f_gates.json", "a") as f:
        f.write(" ")
    r = _run(
        tmp_path,
        "check",
        launcher=repo / "trillium" / "janus1f" / "janus1f",
        JANUS0_COMPILE="f",
        PYTHONPATH="",
    )
    out = r.stdout + r.stderr
    assert r.returncode != 0 and "gates:" in out and "198b3b15" in out


def _sbatch_lines(text):
    return [line for line in text.splitlines() if line.startswith("#SBATCH")]


def test_every_job_writes_the_exact_fir_headers(tmp_path):
    w = tmp_path / "janus1f"
    w.mkdir()
    (w / ".check_ok").write_text("JANUS0_COMPILE=f now\n")
    gpu = ["--account=def-aso22_gpu", "--gpus-per-node=h100:1", "--cpus-per-task=12", "--mem=280G"]
    cpu = ["--account=def-aso22", "--cpus-per-task=16", "--mem=64G"]
    assert _run(tmp_path, "prep", JANUS0_COMPILE="f").returncode == 0
    assert _run(tmp_path, "train", JANUS0_COMPILE="f", J1F_RUN="a1").returncode == 0
    assert _run(tmp_path, "predict", JANUS0_COMPILE="f", J1F_RUN="a1").returncode == 0
    want = {
        "prep.sh": cpu + ["--time=3:00:00"],
        "train_a1_link1.sh": gpu + ["--time=23:50:00"],
        "train_a1_link2.sh": gpu + ["--time=23:50:00"],
        "predict_a1.sh": gpu + ["--time=6:00:00"],
    }
    for f, lines in want.items():
        got = [s.split(None, 1)[1] for s in _sbatch_lines((w / f).read_text())]
        assert [
            g for g in got if not g.startswith(("--job-name", "--nodes", "--output"))
        ] == lines, f
    link1, link2 = (w / "train_a1_link1.sh").read_text(), (w / "train_a1_link2.sh").read_text()
    assert "nnUNetv2_train 719 3d_fullres 0 -tr nnUNetTrainer_janus1f" in link1
    assert link1.rstrip().endswith("nnUNetResEncUNetPlans_60G_iso05") and link2.rstrip().endswith(
        "--c"
    )
    for s in (
        "nnUNet_compile=f",
        "SEGTRAIN_CT_WINDOW=off",
        "SEGTRAIN_SAVE_EVERY=10",
        "SEGTRAIN_MAX_SECONDS=84000",
        "parent_copy:",
        "unset SEGTRAIN_ITERATIONS SEGTRAIN_EPOCHS",
    ):
        assert s in link1
    pr = (w / "predict_a1.sh").read_text()
    for s in (
        "--save_probabilities --disable_tta",
        '-ge 40 ] || { echo "[janus1f] REFUSE: < 40 GB free"; exit 3; }',
        "du -sh",
        "python -m janus1f.decode",
    ):
        assert s in pr
    assert _run(tmp_path, "train", JANUS0_COMPILE="f", J1F_RUN="a2").returncode == 0
    assert "nnUNetv2_train 719 3d_fullres 1 " in (w / "train_a2_link1.sh").read_text()
    assert sbatch.header("collect", "x", "y").count("def-aso22\n") == 1


def test_predict_refuses_with_less_than_40_gb_free(tmp_path):
    """The predict job's free-space guard, run with a `df` that reports 39 GB."""
    w = tmp_path / "janus1f"
    w.mkdir()
    (w / ".check_ok").write_text("JANUS0_COMPILE=f now\n")
    assert _run(tmp_path, "predict", JANUS0_COMPILE="f", J1F_RUN="a1").returncode == 0
    guard = next(
        line for line in (w / "predict_a1.sh").read_text().splitlines() if "40 GB free" in line
    ).strip()
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "df").write_text("#!/bin/sh\necho Avail\necho 39\n")
    (fake / "df").chmod(0o755)
    r = subprocess.run(
        ["bash", "-c", guard],
        env=dict(os.environ, PATH=f"{fake}:{os.environ['PATH']}"),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 3 and "REFUSE: < 40 GB free" in r.stdout
    (fake / "df").write_text("#!/bin/sh\necho Avail\necho 41\n")
    r = subprocess.run(
        ["bash", "-c", guard + " && echo ok"],
        env=dict(os.environ, PATH=f"{fake}:{os.environ['PATH']}"),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0 and "ok" in r.stdout


def test_modes_before_check_refuse(tmp_path):
    r = _run(tmp_path, "prep", JANUS0_COMPILE="f")
    assert r.returncode != 0 and "check" in r.stderr
    r = _run(tmp_path, "bogus")
    assert r.returncode != 0


# ------------------------------------------------------------------ decode through nnU-Net's own IO
def test_decode_with_nnunet_io_keeps_the_export_grid(tmp_path):
    """F, T and G written by nnU-Net's writer read back (by nibabel, as collect reads them) on Janus
    0's grid, and T rebuilt from G and Janus 0's map equals the stored T."""
    pytest.importorskip("nnunetv2")
    pytest.importorskip("SimpleITK")
    import pickle

    import nibabel as nib
    from nnunetv2.imageio.simpleitk_reader_writer import SimpleITKIO

    rng = np.random.default_rng(0)
    shape_xyz = (7, 6, 5)
    aff = np.diag([0.4, 0.4, 0.5, 1.0])
    ct = tmp_path / "ct.nii.gz"
    nib.save(nib.Nifti1Image(rng.normal(size=shape_xyz).astype(np.float32), aff), str(ct))
    rw = SimpleITKIO()
    img, props = rw.read_images([str(ct)])
    grid = img.shape[1:]
    j0dir, probs, out = tmp_path / "pred_fir", tmp_path / "chunk0", tmp_path / "maps"
    j0dir.mkdir()
    probs.mkdir()
    j0 = rng.integers(0, 5, grid).astype(np.uint8)
    rw.write_seg(j0, str(j0dir / "c0001.nii.gz"), props)
    z = rng.normal(size=(13,) + grid) * 2
    prob = np.exp(z - z.max(0)) / np.exp(z - z.max(0)).sum(0)
    np.savez_compressed(probs / "c0001.npz", probabilities=prob.astype(np.float16))
    with open(probs / "c0001.pkl", "wb") as f:
        pickle.dump(props, f)
    (probs / "c0001.nii.gz").write_bytes(b"argmax")
    plans = tmp_path / "plans.json"
    plans.write_text(
        json.dumps(
            {
                "image_reader_writer": "SimpleITKIO",
                "configurations": {},
                "dataset_name": "Dataset719_J1F",
                "plans_name": "p",
                "original_median_spacing_after_transp": [1, 1, 1],
                "original_median_shape_after_transp": [1, 1, 1],
                "transpose_forward": [0, 1, 2],
                "transpose_backward": [0, 1, 2],
                "experiment_planner_used": "x",
                "label_manager": "LabelManager",
                "foreground_intensity_properties_per_channel": {},
            }
        )
    )
    assert (
        decode.main(
            [
                "--run",
                "a1",
                "--chunk",
                "0",
                "--probs",
                str(probs),
                "--janus0",
                str(j0dir),
                "--out",
                str(out),
                "--plans",
                str(plans),
            ]
        )
        == 0
    )
    assert os.listdir(probs) == []
    paths = decode.collect_inputs(str(out), ["c0001"])["c0001"]
    rd = {k: np.asarray(nib.load(p).dataobj).astype(np.uint8) for k, p in paths.items()}
    j0n = np.asarray(nib.load(str(j0dir / "c0001.nii.gz")).dataobj).astype(np.uint8)
    assert rd["F"].shape == j0n.shape == shape_xyz
    assert np.allclose(nib.load(paths["F"]).affine, aff, atol=1e-5)
    assert decode.check_t(rd["T"], j0n, {2: rd["G2"], 3: rd["G3"], 4: rd["G4"]})


# ------------------------------------------------------------------ the collect wait (D55 Q-F3-1)
def test_collect_waits_up_to_14_days_only_when_allowed(tmp_path):
    assert selftest.t_collect_wait()
    with pytest.raises(collect.CollectError):
        collect.env_state({"J1F_Q_F2_3": "maybe"})


# ------------------------------------------------------------------ collect end to end (synthetic)
def _toy_icx():
    """A synthetic ImageCAS-X-valued tree (the scorer self-test's), no patient data."""
    icx = np.zeros((40, 70, 70), np.uint8)
    icx[12, 4:8, 4] = 1  # LM
    icx[12, 8:66, 4] = 2  # LAD
    icx[12, 18, 5:40] = 4  # D1
    icx[12, 40, 5:40] = 5  # D2
    icx[13:38, 7, 4] = 3  # LCx
    icx[20, 7, 5:40] = 6  # OM1
    icx[30, 7, 5:40] = 7  # OM2
    icx[2:30, 60, 60] = 9  # RCA
    icx[30, 30:60, 60] = 10  # R-PDA
    icx[29, 60, 25:60] = 11  # R-PLA
    return icx


class _NibIO:
    def __init__(self, aff):
        self.aff = aff

    @staticmethod
    def load_case(npz, pkl):
        return np.load(npz)["probabilities"].astype(np.float32), {}

    def read_seg(self, path):
        import nibabel as nib

        return np.asarray(nib.load(path).dataobj), {}

    def write_seg(self, arr, path, props):
        import nibabel as nib

        nib.save(nib.Nifti1Image(np.asarray(arr, np.uint8), self.aff), path)


@pytest.mark.slow
def test_collect_opens_the_ledger_first_and_ships_f_on_a_perfect_prediction(tmp_path, monkeypatch):
    import nibabel as nib

    sys.path.insert(0, str(LIB))
    import j1f_scorer as S

    sp = split.load()
    aff = np.diag([0.5, 0.5, 0.5, 1.0])
    icx = _toy_icx()
    ref, _ = S.stage1_labels(icx, (0.5, 0.5, 0.5))
    ref = np.where(ref == 255, 0, ref)
    prob = np.full((13,) + ref.shape, 1e-3, np.float32)
    np.put_along_axis(prob, ref[None].astype(np.int64), 1.0, 0)
    prob /= prob.sum(0, keepdims=True)
    work, j0, icxd = tmp_path / "w", tmp_path / "j0", tmp_path / "icx"
    for d in (work / "maps_a1", j0 / "pred_fir", icxd):
        d.mkdir(parents=True)
    four = decode.collapse_by_group(ref)
    io = _NibIO(aff)
    for c in sp["locked100"]:
        nib.save(nib.Nifti1Image(icx, aff), str(icxd / f"{int(c[1:]) + 1}.coronary.nii.gz"))
        io.write_seg(four, str(j0 / "pred_fir" / f"{c}.nii.gz"), {})
        decode.decode_case(c, prob, {}, four, str(work / "maps_a1"), io)
    (work / ".predict_done_a1").write_text("")
    seen = []

    def fake_r9(pred, *a):
        assert (work / "results" / "looks.json").exists(), "scored before the look was opened"
        seen.append(pred)
        return [
            dict(
                case=c,
                provisional=False,
                flagged_classes=[],
                fp_components=0,
                per_class={k: 0.9 for k in ("LM", "LAD", "LCx", "RCA")},
                recall={k: 0.95 for k in ("LM", "LAD", "LCx", "RCA")},
            )
            for c in sp["locked100"]
        ]

    monkeypatch.setattr(collect, "r9", fake_r9)
    res = collect.run(
        str(work),
        str(j0),
        str(icxd),
        str(tmp_path),
        str(tmp_path / "layout.json"),
        4,
        env={"J1F_Q_F2_3": "yes"},
    )
    assert res["ships"] == "F" and res["V_F"]["passed"] and res["B"]["B_F"]["n_pass"] == 6
    assert res["look"]["readings"] == ["F", "T"] and not res["fa32_applies"]
    assert len(seen) == 2
    out = work / "results"
    assert (out / "DECISION.md").read_text().startswith("# J1F-A")
    assert "F-A35" in (out / "DECISION.md").read_text()
    assert json.loads((out / "verdict.json").read_text())["ships"] == "F"
    with pytest.raises(ledger.LedgerError, match="second run"):
        collect.run(
            str(work), str(j0), str(icxd), str(tmp_path), str(tmp_path / "layout.json"), 4, env={}
        )
