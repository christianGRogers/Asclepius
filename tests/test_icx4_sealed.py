"""icx4 never scores a sealed case (A14, issue #55).

``trillium/icx4/lib/sealed.py`` is the one filter every icx4 scoring stage uses. These tests pin
it to the real ``trillium/sealed_test.json`` and to ImageCAS-X's real 160-case test split
(``tests/fixtures/imagecas_x_test.txt``: ImageCAS-X ``filelist/test.txt`` as released, 1-based
ImageCAS ids; Zenodo 10.5281/zenodo.21887809, CC BY 4.0, fetched 2026-10-18). They run the
scoring and report stages end to end on small synthetic volumes with sealed cases among them, the
launcher's dry run on every cluster profile, and the job's refusal to start.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
ICX4 = REPO / "trillium" / "icx4"
LIB = ICX4 / "lib"
SEALED_JSON = REPO / "trillium" / "sealed_test.json"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "imagecas_x_test.txt"
# ImageCAS-X filelist/val.txt as released (fold 0; same Zenodo record, fetched 2026-10-18)
VAL_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "imagecas_x_val.txt"


def _mod(name):
    spec = importlib.util.spec_from_file_location(f"icx4_{name}", LIB / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(LIB))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(LIB))
    return mod


sealed = _mod("sealed")


def _test_ids():
    return ["c%04d" % (int(x) - 1) for x in FIXTURE.read_text().split()]


@pytest.fixture(scope="module")
def S():
    return sealed.load(SEALED_JSON)


# ------------------------------------------------------------------------------------- the filter
def test_scored_list_is_exactly_open36_and_dev44_on_the_real_split(S):
    test = _test_ids()
    assert len(test) == len(set(test)) == 160
    g = sealed.scored_groups(S, test)
    scored = set(g["open36"]) | set(g["dev44"])
    assert (
        len(g["open36"]) == 36 and len(g["dev44"]) == 44 and not set(g["open36"]) & set(g["dev44"])
    )
    assert scored == set(S["open_icx_test"]) | set(S["excluded_dev_cases_in_test"])
    assert not scored & set(S["sealed_icx_test"]) and not scored & set(S["sealed_quality0"])
    assert scored <= set(test) and len(set(test) - scored) == 80
    assert set(test) - scored == set(S["sealed_icx_test"])


def test_the_experiment_folder_copy_is_the_official_list():
    assert (ICX4 / "sealed_test.json").read_bytes() == SEALED_JSON.read_bytes()


def test_present_restricts_each_group_and_never_adds(S):
    test = _test_ids()
    present = set(S["open_icx_test"][:5]) | set(S["sealed_icx_test"]) | {"c0001"}
    g = sealed.scored_groups(S, test, present)
    assert g == {"open36": sorted(S["open_icx_test"][:5]), "dev44": []}


def test_a_test_split_that_the_seal_does_not_describe_is_refused(S):
    test = _test_ids()
    with pytest.raises(sealed.SealedError):
        sealed.scored_groups(S, test[:-1])  # a case missing
    with pytest.raises(sealed.SealedError):
        sealed.scored_groups(S, test + ["c0001"])  # an unknown case
    with pytest.raises(sealed.SealedError):
        sealed.scored_groups(S, test + test[:1])  # a duplicate


def test_refuse_sealed_names_the_cases(S):
    assert sealed.refuse_sealed(S["open_icx_test"], S, "t") == S["open_icx_test"]
    for c in (S["sealed_icx_test"][0], S["sealed_quality0"][0]):
        with pytest.raises(sealed.SealedError, match="REFUSING"):
            sealed.refuse_sealed(["c0068", c], S, "t")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("sealed_icx_test"),
        lambda d: d.pop("sealed_quality0"),
        lambda d: d["sealed_icx_test"].pop(),
        lambda d: d["open_icx_test"].__setitem__(0, d["sealed_icx_test"][0]),  # overlap
        lambda d: d["excluded_dev_cases_in_test"].__setitem__(0, "imagecas_1"),
    ],
)
def test_a_malformed_list_is_refused(tmp_path, mutate):
    d = json.loads(SEALED_JSON.read_text())
    mutate(d)
    p = tmp_path / "sealed_test.json"
    p.write_text(json.dumps(d))
    with pytest.raises(sealed.SealedError):
        sealed.load(p)


def test_a_missing_or_unreadable_list_is_refused_never_score_everything(tmp_path):
    with pytest.raises(sealed.SealedError, match="missing or unreadable"):
        sealed.load(tmp_path / "nope.json")
    (tmp_path / "bad.json").write_text("{not json")
    with pytest.raises(sealed.SealedError, match="missing or unreadable"):
        sealed.load(tmp_path / "bad.json")
    r = subprocess.run(
        [sys.executable, str(LIB / "sealed.py"), "check", str(tmp_path / "nope.json")],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 3 and "refusing" in r.stderr


def test_cli_prints_the_filter_and_the_group_counts(tmp_path):
    icx = tmp_path / "icx"
    icx.mkdir()
    shutil.copy(FIXTURE, icx / "test.txt")
    r = subprocess.run(
        [sys.executable, str(LIB / "sealed.py"), "check", str(SEALED_JSON), str(icx)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert (
        "80 sealed ImageCAS-X test" in r.stdout and "open-36 36 cases, dev-44 44 cases" in r.stdout
    )


# --------------------------------------------------------------------- score + report, end to end
SHAPE = (12, 10, 8)


def _vol(path, data):
    nib.save(nib.Nifti1Image(np.asarray(data, np.uint8), np.diag([0.5, 0.5, 0.5, 1.0])), str(path))


def _workdir(tmp_path, S):
    """A workdir with 2 open-36, 1 dev-44, 2 sealed and 1 training case, all predicted."""
    W, icx = tmp_path / "w", tmp_path / "icx"
    (W / "predictions").mkdir(parents=True)
    icx.mkdir()
    shutil.copy(FIXTURE, icx / "test.txt")
    open_, dev, seal = (
        S["open_icx_test"][:2],
        S["excluded_dev_cases_in_test"][:1],
        [S["sealed_icx_test"][0], S["sealed_quality0"][0]],
    )
    cases = open_ + dev + seal + ["c0001"]
    lab = np.zeros(SHAPE, np.uint8)
    lab[2:10, 3, 3] = 2  # ImageCAS-X LAD
    lab[2:10, 6, 3] = 9  # ImageCAS-X RCA
    for c in cases:
        _vol(icx / f"{int(c[1:]) + 1}.coronary.nii.gz", lab)  # labels exist even for sealed cases
        pred = np.zeros(SHAPE, np.uint8)
        pred[2:10, 3, 3] = 2
        _vol(W / "predictions" / f"{c}.nii.gz", pred)
    json.dump({"cases": {c: {"ct": "", "mask": ""} for c in cases}}, open(W / "layout.json", "w"))
    shutil.copy(SEALED_JSON, W / "sealed_test.json")
    return W, icx, open_, dev, seal


def test_score_and_report_never_touch_a_sealed_case(tmp_path, S):
    W, icx, open_, dev, seal = _workdir(tmp_path, S)
    out = W / "results"
    r = subprocess.run(
        [sys.executable, str(LIB / "score.py"), str(W), str(icx), str(out), "2"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    r = subprocess.run(
        [sys.executable, str(LIB / "report.py"), str(W), str(out)], capture_output=True, text=True
    )
    assert r.returncode == 0, r.stdout + r.stderr

    rows = json.load(open(W / "dice_per_case.json"))
    assert sorted(x["case"] for x in rows) == sorted(open_ + dev)
    assert {x["case"]: x["group"] for x in rows} == {
        **{c: "open36" for c in open_},
        **{c: "dev44" for c in dev},
    }
    assert rows[0]["cls"]["LAD"]["dice"] == 1.0 and rows[0]["cls"]["RCA"]["dice"] == 0.0
    # nothing under results/ mentions a sealed case
    for f in out.iterdir():
        text = f.read_text()
        for c in seal:
            assert c not in text, (f.name, c)
    idx = json.load(open(out / "predictions_index.json"))
    assert idx["sealed_cases_omitted"] == 2 and idx["n_cases"] == 6 and not idx["missing"]
    res = json.load(open(out / "results.json"))
    assert res["groups"]["open36"]["n_scored"] == 2 and res["groups"]["dev44"]["n_scored"] == 1
    assert res["groups"]["open36"]["n_listed"] == 36 and res["groups"]["dev44"]["n_listed"] == 44
    md = (out / "SUMMARY.md").read_text()
    assert (
        "80 sealed ImageCAS-X test cases" in md
        and "2 of 36 cases scored" in md
        and "1 of 44 cases scored" in md
    )


def test_score_refuses_without_the_sealed_list(tmp_path, S):
    W, icx, *_ = _workdir(tmp_path, S)
    os.remove(W / "sealed_test.json")
    r = subprocess.run(
        [sys.executable, str(LIB / "score.py"), str(W), str(icx), str(W / "results"), "2"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 3 and "refusing" in r.stdout
    assert not (W / "dice_per_case.json").exists() and not (W / "results" / "SUMMARY.md").exists()


def test_report_refuses_a_sealed_row(tmp_path, S):
    W, icx, open_, dev, seal = _workdir(tmp_path, S)
    json.dump(
        [{"case": seal[0], "group": "open36", "tree": 1.0, "cls": {}}],
        open(W / "dice_per_case.json", "w"),
    )
    r = subprocess.run(
        [sys.executable, str(LIB / "report.py"), str(W), str(W / "results")],
        capture_output=True,
        text=True,
    )
    assert (
        r.returncode == 3 and "REFUSING" in r.stdout and not (W / "results" / "SUMMARY.md").exists()
    )


# ------------------------------------------------------------------------- the launcher (dry run)
def _root(tmp_path, with_sealed=True):
    root = tmp_path / "root"
    shutil.copytree(ICX4, root / "experiments" / "icx4")
    if not with_sealed:
        os.remove(root / "experiments" / "icx4" / "sealed_test.json")
    cases = root / "cases"
    cases.mkdir()
    for n in range(1, 1001):
        (cases / f"{n}.img.nii.gz").touch()
        (cases / f"{n}.label.nii.gz").touch()
    icx = tmp_path / "icx"
    icx.mkdir()
    shutil.copy(FIXTURE, icx / "test.txt")
    shutil.copy(VAL_FIXTURE, icx / "val.txt")
    test = {int(x) for x in FIXTURE.read_text().split()}
    val = {int(x) for x in VAL_FIXTURE.read_text().split()}
    rest = [n for n in range(1, 1001) if n not in test | val]
    (icx / "train.txt").write_text("\n".join(map(str, rest[:560])))
    return root, icx


def _dry(root, icx, tmp_path, **env):
    e = {k: v for k, v in os.environ.items() if not k.startswith(("ICX4_", "CC_CLUSTER"))}
    e.update(ICX4_DRYRUN="1", ICX4_DRY_ICX=str(icx), SCRATCH=str(tmp_path / "scratch"), **env)
    return subprocess.run(
        ["bash", str(root / "experiments" / "icx4" / "icx4")],
        capture_output=True,
        text=True,
        env=e,
        cwd=root / "experiments" / "icx4",
    )


@pytest.mark.parametrize("cluster", ["trillium", "fir", "nibi", "rorqual"])
def test_dry_run_shows_the_filter_on_every_cluster(tmp_path, cluster):
    root, icx = _root(tmp_path)
    r = _dry(root, icx, tmp_path, ICX4_CLUSTER=cluster)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (
        "80 sealed ImageCAS-X test + 20 sealed quality-0 cases are predicted but never scored"
        in r.stdout
    )
    assert "scored: open-36 36 cases, dev-44 44 cases (of 160 ImageCAS-X test)" in r.stdout
    assert f"cluster: {cluster}" in r.stdout
    assert (
        tmp_path / "scratch" / "icx4" / "sealed_test.json"
    ).read_bytes() == SEALED_JSON.read_bytes()


def test_dry_run_refuses_without_the_sealed_list(tmp_path):
    root, icx = _root(tmp_path, with_sealed=False)
    r = _dry(root, icx, tmp_path)
    assert r.returncode != 0 and "refusing to start" in r.stderr
    assert "would submit" not in r.stdout


# ----------------------------------------------------------------------- the job refuses to start
def _job(tmp_path, W, lib=LIB):
    e = {k: v for k, v in os.environ.items() if not k.startswith("ICX4_")}
    e.update(
        W=str(W),
        LIB=str(lib),
        ICX=str(tmp_path / "icx"),
        VENV=str(tmp_path / "no-venv"),
        PATH=f"{Path(sys.executable).parent}:{e.get('PATH', '')}",
    )
    return subprocess.run(["bash", str(lib / "job_body.sh")], capture_output=True, text=True, env=e)


def test_job_refuses_to_start_without_the_sealed_list(tmp_path):
    W = tmp_path / "w"
    (W / "logs").mkdir(parents=True)
    r = _job(tmp_path, W)
    assert r.returncode == 3 and "REFUSING" in r.stdout
    assert not (W / ".labels_done").exists() and not (W / "timings.json").exists()


def test_job_refuses_a_workdir_copy_that_differs_from_the_experiment_folder(tmp_path):
    W = tmp_path / "w"
    (W / "logs").mkdir(parents=True)
    d = json.loads(SEALED_JSON.read_text())
    d["open_icx_test"], d["sealed_icx_test"][:36] = (
        d["sealed_icx_test"][:36],
        d["open_icx_test"],
    )  # still valid
    (W / "sealed_test.json").write_text(json.dumps(d))
    r = _job(tmp_path, W)
    assert r.returncode == 3 and "differs" in r.stdout
