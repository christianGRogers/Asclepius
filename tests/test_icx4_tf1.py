"""icx4's decisive score (A1, A1a, A1b, A1c; issue #54): TotalSegmentator aortas and tree-F1 with
the frozen ``segtrain.tf1``, on the open ImageCAS-X test cases only.

Pins the vendored metric to ``src/segtrain/tf1.py`` and the A1c hash, reuses the Round 7 checks
(a perfect prediction scores 1.0; an LM renamed LAD scores LM 0, also on a short-LM stub whose LM
has no centreline) through icx4's own scorer and ImageCAS-X's 14-class encoding, checks that the
aorta and tF1 case lists hold no sealed case, runs the post-prediction chain end to end (score ->
aorta -> tF1 -> report) with sealed cases present, and checks every refusal of a wrong tf1 hash.
TotalSegmentator is never imported: ``ICX4_FAKE_AORTA`` stands in.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest
from test_icx4_sealed import FIXTURE, ICX4, LIB, SEALED_JSON, VAL_FIXTURE, _dry, _mod, _root, sealed

REPO = Path(__file__).resolve().parents[1]
PIN = "24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254"
tf1_score = _mod("tf1_score")
aorta = _mod("aorta")

# the Round 7 geometry of tests/test_tf1.py
SP = (0.5, 0.5, 0.5)
SHAPE = (110, 64, 48)
X0 = 30
LM = ((X0, 30, 20), (X0 + 15, 30, 20), 3.0, 3.0)
LAD = ((X0 + 15, 30, 20), (X0 + 70, 46, 20), 2.0, 2.0)
LCX = ((X0 + 15, 30, 20), (X0 + 70, 12, 20), 2.0, 2.0)
RCA = ((X0, 54, 36), (X0 + 70, 54, 36), 3.0, 1.6)
ICX_VALUE = {1: 1, 2: 2, 3: 3, 4: 9}  # LM, LAD, LCx, RCA in ImageCAS-X's 14-class encoding


def _tube(a, b, ra, rb):
    g = np.indices(SHAPE).reshape(3, -1).T.astype(float)
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip((g - a) @ ab / (ab @ ab), 0, 1)
    d = np.linalg.norm(g - (a + t[:, None] * ab), axis=1)
    return (d <= ra + t * (rb - ra)).reshape(SHAPE), d.reshape(SHAPE)


@pytest.fixture(scope="module")
def ref():
    lab = np.zeros(SHAPE, np.uint8)
    best = np.full(SHAPE, np.inf)
    for c, seg in [(1, LM), (2, LAD), (3, LCX), (4, RCA)]:
        m, d = _tube(*seg)
        take = m & (d < best)
        lab[take] = c
        best[take] = d[take]
    return lab


@pytest.fixture(scope="module")
def stub(ref):
    """Short-LM habit of the proxy (test_tf1._stub): the LM has no centreline voxel."""
    _, d = _tube(*LM)
    out = ref.copy()
    out[(ref == 1) & (d <= 1.8)] = 2
    return out


def _aorta():
    m = np.zeros(SHAPE, bool)
    m[: X0 - 4, 4:60, 4:44] = True
    return m


def _save(path, a):
    nib.save(nib.Nifti1Image(np.asarray(a), np.diag([*SP, 1.0])), str(path))


def _icx(four):
    out = np.zeros(SHAPE, np.uint8)
    for k, v in ICX_VALUE.items():
        out[four == k] = v
    return out


def _ct(four):
    ct = np.full(SHAPE, -100, np.int16)
    ct[four > 0] = 400
    ct[_aorta()] = 600  # the fake aorta segmenter takes > 500 HU
    return ct


# ------------------------------------------------------------------------------------ the metric
def test_the_vendored_metric_is_src_segtrain_tf1_verbatim_and_pinned():
    vendored = (LIB / "segtrain_tf1.py").read_bytes()
    assert vendored == (REPO / "src" / "segtrain" / "tf1.py").read_bytes()
    assert hashlib.sha256(vendored).hexdigest() == PIN == tf1_score.TF1_SHA256
    launcher = (ICX4 / "icx4").read_text()
    assert re.search(r'^FROZEN_SHA="([0-9a-f]{64})"$', launcher, re.M).group(1) == PIN


def _score(tmp_path, ref4, pred4, with_aorta=True):
    _save(tmp_path / "icx.nii.gz", _icx(ref4))
    _save(tmp_path / "pred.nii.gz", pred4)
    _save(tmp_path / "ct.nii.gz", _ct(ref4))
    if with_aorta:
        _save(tmp_path / "aorta.nii.gz", _aorta().astype(np.uint8))
    return tf1_score.score_case(
        "c0068",
        str(tmp_path / "pred.nii.gz"),
        str(tmp_path / "icx.nii.gz"),
        aorta_path=str(tmp_path / "aorta.nii.gz"),
        ct_path=str(tmp_path / "ct.nii.gz"),
    )


def test_a_perfect_prediction_scores_one(tmp_path, ref):
    r = _score(tmp_path, ref, ref)
    assert r["has_aorta"] and not r["provisional"] and not r["flagged_classes"]
    assert r["per_class"] == pytest.approx({"LM": 1.0, "LAD": 1.0, "LCx": 1.0, "RCA": 1.0})
    assert r["tf1"] == pytest.approx(1.0) and r["tf1_tol0"] == pytest.approx(1.0)
    assert r["fp_components"] == 0 and r["classes_without_centreline"] == []
    assert {o["rule"] for o in r["ostia"]} == {"aorta"}


def test_lm_renamed_lad_scores_lm_zero(tmp_path, ref):
    r = _score(tmp_path, ref, np.where(ref == 1, 2, ref).astype(np.uint8))
    assert r["per_class"]["LM"] == 0.0 and r["per_class"]["RCA"] == pytest.approx(1.0)


def test_round7_stub_perfect_is_one_and_renamed_is_lm_zero(tmp_path, stub):
    r = _score(tmp_path, stub, stub)
    assert r["classes_without_centreline"] == ["LM"] and r["centreline_fallback"]
    assert r["per_class"] == pytest.approx({"LM": 1.0, "LAD": 1.0, "LCx": 1.0, "RCA": 1.0})
    r = _score(tmp_path, stub, np.where(stub == 1, 2, stub).astype(np.uint8))
    assert r["per_class"]["LM"] == 0.0


def test_without_an_aorta_the_case_is_provisional(tmp_path, ref):
    r = _score(tmp_path, ref, ref, with_aorta=False)
    assert not r["has_aorta"] and r["provisional"]
    report = _mod("report")
    assert report.decisive_case_score(r) is None


def test_a_wrong_hash_is_refused_by_the_scorer(tmp_path):
    lib = tmp_path / "lib"
    shutil.copytree(LIB, lib)
    (lib / "segtrain_tf1.py").write_text((lib / "segtrain_tf1.py").read_text() + "\n# edited\n")
    W = tmp_path / "w"
    W.mkdir()
    shutil.copy(SEALED_JSON, W / "sealed_test.json")
    r = subprocess.run(
        [sys.executable, str(lib / "tf1_score.py"), str(W), str(tmp_path), "1"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 3 and "refusing to score" in r.stdout


# ------------------------------------------------------------------------------------ case lists
def test_the_aorta_and_tf1_case_lists_hold_no_sealed_case(tmp_path):
    W, icx = tmp_path / "w", tmp_path / "icx"
    W.mkdir()
    icx.mkdir()
    shutil.copy(FIXTURE, icx / "test.txt")
    shutil.copy(VAL_FIXTURE, icx / "val.txt")
    shutil.copy(SEALED_JSON, W / "sealed_test.json")
    every = {"c%04d" % i: {"ct": f"/ct/{i}.nii.gz", "mask": None} for i in range(1000)}
    json.dump({"cases": every}, open(W / "layout.json", "w"))
    S = sealed.load(SEALED_JSON)
    val = {"c%04d" % (int(x) - 1) for x in VAL_FIXTURE.read_text().split()}
    cases = aorta.cases_for_aorta(str(W), str(icx))
    # A26 (#79): val 80 + open 36 + dev 44 = 160, and not one sealed case
    assert set(cases) == val | set(S["open_icx_test"]) | set(S["excluded_dev_cases_in_test"])
    assert len(val) == 80 and len(cases) == 160
    assert not set(cases) & (set(S["sealed_icx_test"]) | set(S["sealed_quality0"]))
    assert cases["c0068"] == "/ct/68.nii.gz"  # the CT path comes from layout.json
    g = aorta.aorta_groups(str(W), str(icx))
    assert {k: len(v) for k, v in g.items()} == {"val80": 80, "open36": 36, "dev44": 44}


def _aorta_dir(tmp_path, val_ids):
    W, icx = tmp_path / "w", tmp_path / "icx"
    W.mkdir()
    icx.mkdir()
    shutil.copy(FIXTURE, icx / "test.txt")
    (icx / "val.txt").write_text("\n".join(map(str, val_ids)))
    shutil.copy(SEALED_JSON, W / "sealed_test.json")
    every = {"c%04d" % i: {"ct": f"/ct/{i}.nii.gz", "mask": None} for i in range(1000)}
    json.dump({"cases": every}, open(W / "layout.json", "w"))
    return W, icx


def test_a_val_list_holding_a_sealed_case_is_refused(tmp_path):
    S = sealed.load(SEALED_JSON)
    val = [int(x) for x in VAL_FIXTURE.read_text().split()]
    val[0] = int(S["sealed_quality0"][0][1:]) + 1
    W, icx = _aorta_dir(tmp_path, val)
    with pytest.raises(aorta.sealed.SealedError, match="REFUSING"):
        aorta.cases_for_aorta(str(W), str(icx))
    r = _run(LIB / "aorta.py", "plan", W, icx)
    assert r.returncode == 3 and "sealed" in r.stderr
    r = _run(LIB / "aorta.py", W, icx, "cpu", env={"ICX4_FAKE_AORTA": "1"})
    assert r.returncode == 3 and not (W / "aorta").exists()


@pytest.mark.parametrize("bad", ["short", "test", "missing"])
def test_a_wrong_val_list_is_refused(tmp_path, bad):
    val = [int(x) for x in VAL_FIXTURE.read_text().split()]
    if bad == "short":
        val = val[:79]
    elif bad == "test":
        val[0] = int(FIXTURE.read_text().split()[0])  # a test case in val: the split is wrong
    W, icx = _aorta_dir(tmp_path, val)
    if bad == "missing":
        os.remove(icx / "val.txt")
    with pytest.raises(aorta.sealed.SealedError):
        aorta.cases_for_aorta(str(W), str(icx))


def test_aorta_plan_prints_the_set(tmp_path):
    W, icx = _aorta_dir(tmp_path, VAL_FIXTURE.read_text().split())
    r = _run(LIB / "aorta.py", "plan", W, icx)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "aorta set: 160 cases (val 80: 80, open 36: 36, dev 44: 44), sealed 0" in r.stdout


# ------------------------------------------------------------------------------------ end to end
def _run(*args, env=None):
    e = dict(os.environ, **(env or {}))
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, env=e)


def test_post_prediction_chain_end_to_end_never_touches_a_sealed_case(tmp_path, ref, stub):
    S = sealed.load(SEALED_JSON)
    W, icx = tmp_path / "w", tmp_path / "icx"
    (W / "predictions").mkdir(parents=True)
    (tmp_path / "ct").mkdir()
    icx.mkdir()
    shutil.copy(FIXTURE, icx / "test.txt")
    shutil.copy(VAL_FIXTURE, icx / "val.txt")
    shutil.copy(SEALED_JSON, W / "sealed_test.json")
    open_, dev = S["open_icx_test"][:2], S["excluded_dev_cases_in_test"][:1]
    val = ["c%04d" % (int(VAL_FIXTURE.read_text().split()[0]) - 1)]
    seal = [S["sealed_icx_test"][0], S["sealed_quality0"][0]]
    preds = {open_[0]: ref, open_[1]: np.where(ref == 1, 2, ref), dev[0]: stub}
    layout = {}
    for c in open_ + dev + val + seal + ["c0000"]:
        n = int(c[1:]) + 1
        four = stub if c == dev[0] else ref
        _save(icx / f"{n}.coronary.nii.gz", _icx(four))
        _save(tmp_path / "ct" / f"{n}.nii.gz", _ct(four))
        _save(W / "predictions" / f"{c}.nii.gz", preds.get(c, ref).astype(np.uint8))
        layout[c] = {"ct": str(tmp_path / "ct" / f"{n}.nii.gz"), "mask": ""}
    json.dump({"cases": layout}, open(W / "layout.json", "w"))
    out = W / "results"

    r = _run(LIB / "score.py", W, icx, out, 2)
    assert r.returncode == 0, r.stdout + r.stderr
    r = _run(LIB / "aorta.py", W, icx, "cpu", env={"ICX4_FAKE_AORTA": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert sorted(p.name for p in (W / "aorta").glob("*_aorta.nii.gz")) == sorted(
        f"{c}_aorta.nii.gz" for c in open_ + dev + val
    )
    r = _run(LIB / "tf1_score.py", W, icx, 2)
    assert r.returncode == 0, r.stdout + r.stderr
    r = _run(LIB / "report.py", W, out)
    assert r.returncode == 0, r.stdout + r.stderr

    tf = json.load(open(W / "tf1_per_case.json"))
    rows = {x["case"]: x for x in tf["per_case"]}
    assert set(rows) == set(open_ + dev) and not tf["errors"] and tf["tf1_sha256"] == PIN
    assert rows[open_[0]]["tf1"] == pytest.approx(1.0) and not rows[open_[0]]["provisional"]
    assert rows[open_[1]]["per_class"]["LM"] == 0.0
    assert rows[dev[0]]["group"] == "dev44" and rows[dev[0]]["classes_without_centreline"] == ["LM"]

    res = json.load(open(out / "results.json"))
    t36, t44 = res["groups"]["open36"]["tf1"], res["groups"]["dev44"]["tf1"]
    assert t36["n_decisive_cases"] == 2 and t44["n_decisive_cases"] == 1
    assert t36["decisive_per_class"]["LM"] == {"tf1": 0.5, "n_trees": 2}
    assert t44["decisive_macro_tf1"] == pytest.approx(1.0)
    assert t44["classes_without_centreline"]["LM"] == 1
    md = (out / "SUMMARY.md").read_text()
    assert "decisive tree-F1 @ 1.5 mm" in md and PIN in md and "Dice (secondary" in md
    for f in out.iterdir():
        for c in seal:
            assert c not in f.read_text(), (f.name, c)
    assert not any(c in p.name for c in seal for p in (W / "tf1.d").iterdir())


# ----------------------------------------------------------------------------------- launcher + job
@pytest.mark.parametrize("cluster", ["trillium", "fir", "nibi", "rorqual"])
def test_dry_run_shows_the_new_stages_on_every_cluster(tmp_path, cluster):
    root, icx = _root(tmp_path)
    r = _dry(root, icx, tmp_path, ICX4_CLUSTER=cluster)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"metric: segtrain.tf1 sha256 {PIN} = frozen hash (A1c)" in r.stdout
    assert "TotalSegmentator aortas (GPU; val 80 + open 36 + dev 44, never sealed)" in r.stdout
    assert "aorta set: 160 cases (val 80: 80, open 36: 36, dev 44: 44), sealed 0" in r.stdout
    assert "tree-F1 @ 1.5 mm with the frozen segtrain.tf1" in r.stdout
    assert "would build TotalSegmentator venv" in r.stdout and "total_fast" in r.stdout
    assert f'FROZEN_SHA="{PIN}"' in r.stdout and "TOTALSEG_HOME_DIR=" in r.stdout


def test_dry_run_refuses_a_wrong_tf1_hash(tmp_path):
    root, icx = _root(tmp_path)
    f = root / "experiments" / "icx4" / "lib" / "segtrain_tf1.py"
    f.write_text(f.read_text() + "\n# edited\n")
    r = _dry(root, icx, tmp_path)
    assert r.returncode != 0 and "not the frozen" in r.stderr and "would submit" not in r.stdout


def test_icx4_work_gives_an_independent_run(tmp_path):
    root, icx = _root(tmp_path)
    work = tmp_path / "scratch" / "icx4-seed2"
    r = _dry(root, icx, tmp_path, ICX4_WORK=str(work))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "#SBATCH --job-name=icx4-icx4-seed2" in r.stdout
    assert f'export W="{work}"' in r.stdout and (work / "sealed_test.json").exists()
    assert not (tmp_path / "scratch" / "icx4").exists()
    r = _dry(root, icx, tmp_path)
    assert "#SBATCH --job-name=icx4\n" in r.stdout


def test_job_refuses_a_wrong_tf1_hash(tmp_path):
    lib = tmp_path / "exp" / "lib"
    shutil.copytree(LIB, lib)
    shutil.copy(SEALED_JSON, tmp_path / "exp" / "sealed_test.json")
    W = tmp_path / "w"
    (W / "logs").mkdir(parents=True)
    shutil.copy(SEALED_JSON, W / "sealed_test.json")
    e = {k: v for k, v in os.environ.items() if not k.startswith("ICX4_")}
    e.update(
        W=str(W),
        LIB=str(lib),
        ICX=str(tmp_path),
        VENV=str(tmp_path / "none"),
        PATH=f"{Path(sys.executable).parent}:{e.get('PATH', '')}",
    )
    ok = subprocess.run(
        ["bash", str(lib / "job_body.sh")],
        capture_output=True,
        text=True,
        env=dict(e, FROZEN_SHA="0" * 64),
    )
    assert ok.returncode == 3 and "tf1 hash differs" in ok.stdout
    (lib / "segtrain_tf1.py").write_text((lib / "segtrain_tf1.py").read_text() + "\n# edited\n")
    r = subprocess.run(
        ["bash", str(lib / "job_body.sh")],
        capture_output=True,
        text=True,
        env=dict(e, FROZEN_SHA=PIN),
    )
    assert r.returncode == 3 and "tf1 hash differs" in r.stdout
    assert not (W / ".labels_done").exists()
