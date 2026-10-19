"""The pre-registered reading of icx4's results (#86): experiments/Atlas/r10_read_icx4.py and the
val-80 scorer it reads (experiments/Atlas/r9_score_icx4.py).

* A27's and A29's wording is quoted verbatim from vault/Plans/Judgements/Round 9.md;
* A26: the val scorer's rows equal icx4's in-job rows on identical inputs, through a JSON round
  trip, and any difference (a value, a missing case, the hash, the wrong --set) is a STOP;
* A27: each row fires exactly at its threshold, the 10 worst val cases are listed, and the exit
  code says Stop;
* A29: Delta's rule on val decides and open-36 validates (adopted / reported, not adopted /
  withdrawn / not run);
* A15: atlas2's census categories on icx4-style inputs, with and without softmax;
* the vault note template fills every placeholder and keeps only the blocks that fire;
* sealed cases are refused in every input;
* a replay on run 1's real per-case rows (trillium-results) reproduces Round 8's published numbers.
"""

import copy
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("skimage")
nib = pytest.importorskip("nibabel")

REPO = Path(__file__).resolve().parents[1]
ROUND9 = (REPO / "vault/Plans/Judgements/Round 9.md").read_text()
TEMPLATE = REPO / "vault/Plans/Experiments/icx4 - Results (pending).md"
SEALED = json.loads((REPO / "trillium/sealed_test.json").read_text())
OPEN36 = sorted(SEALED["open_icx_test"])


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


R9 = _load("atlas_r9_score_icx4", "experiments/Atlas/r9_score_icx4.py")
RD = _load("atlas_r10_read_icx4", "experiments/Atlas/r10_read_icx4.py")
tf1_score = sys.modules["tf1_score"]
report = sys.modules["report"]


# ------------------------------------------------------------------------------------------ wording
def test_a26_a27_a29_wording_is_verbatim_round9():
    for res, then in RD.A27.values():
        assert f"| {res} | {then} |" in ROUND9, res
    for s in (RD.A26_RULE, RD.A29_PASS, RD.A29_FAIL, RD.A29_RULE, RD.A26_OPEN, RD.A26_RULES):
        assert s in ROUND9, s


# ----------------------------------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def geometry():
    return R9.synthetic()


@pytest.fixture(scope="module")
def scored(tmp_path_factory, geometry):
    """Two real cases (perfect, LAD cut) scored by the in-job function and by the r9 scorer, JSON
    round-tripped."""
    ref, aorta, _ = geometry
    cut = ref.copy()
    sl = cut[60:66]
    sl[sl == 2] = 0
    W = tmp_path_factory.mktemp("w")
    out = {}
    for c, p in (("c0068", ref), ("c0102", cut)):  # two open-36 ids
        ct = R9.write_case(str(W), c, p, ref, aorta)
        args = (c, str(W / "predictions"), str(W / "icx"), str(W / "aorta"), ct)
        mine = R9.score_case(args)
        job = tf1_score.score_case(
            c,
            str(W / "predictions" / f"{c}.nii.gz"),
            str(W / "icx" / f"{int(c[1:]) + 1}.coronary.nii.gz"),
            aorta_path=str(W / "aorta" / f"{c}_aorta.nii.gz"),
            ct_path=ct,
        )
        rt = lambda x: json.loads(json.dumps(x, default=float))  # noqa: E731
        out[c] = (rt(job), rt(mine))
    return out


def _as(case, row):
    r = copy.deepcopy(row)
    r["case"] = case
    return r


def _job_and_check(scored):
    """In-job tf1_per_case.json and r9_open36_check.json covering all 36 open cases (rows recycled
    from 2 real ones)."""
    src = list(scored.values())
    job = {"tf1_sha256": RD_PIN, "per_case": [], "errors": []}
    chk = {"tf1_sha256": RD_PIN, "set": "open36", "rows": []}
    for i, c in enumerate(OPEN36):
        j, m = src[i % 2]
        job["per_case"].append(dict(_as(c, j), group="open36"))
        chk["rows"].append(_as(c, m))
    return job, chk


RD_PIN = R9.PINNED


# --------------------------------------------------------------------------------------------- A26
def test_r9_rows_equal_in_job_rows_through_json(scored):
    for job, mine in scored.values():
        assert {k: v for k, v in mine.items() if k != "dice"} == job


def test_a26_pass_and_every_kind_of_difference_stops(scored):
    job, chk = _job_and_check(scored)
    assert RD.a26_identity(job, chk)["ok"]
    bad = copy.deepcopy(chk)
    bad["rows"][5]["per_class"]["LAD"] += 1e-9
    r = RD.a26_identity(job, bad)
    assert not r["ok"] and OPEN36[5] in r["problems"][0] and "per_class" in r["problems"][0]
    bad = copy.deepcopy(chk)
    bad["rows"][0]["flagged_classes"] = ["RCA"]
    assert not RD.a26_identity(job, bad)["ok"]
    bad = copy.deepcopy(chk)
    del bad["rows"][3]
    assert any("no r9_score_icx4 row" in p for p in RD.a26_identity(job, bad)["problems"])
    bad = dict(chk, tf1_sha256="0" * 64)
    assert not RD.a26_identity(job, bad)["ok"]
    bad = dict(chk, set="val")
    assert not RD.a26_identity(job, bad)["ok"]
    j2 = copy.deepcopy(job)
    j2["per_case"].pop()
    assert not RD.a26_identity(j2, chk)["ok"]


# --------------------------------------------------------------------------------------------- A27
def _row(case, lm=1.0, lad=1.0, lcx=1.0, rca=1.0, flagged=(), fp=0, prov=False):
    pc = {"LM": lm, "LAD": lad, "LCx": lcx, "RCA": rca}
    return {
        "case": case,
        "tf1": float(np.mean(list(pc.values()))),
        "per_class": pc,
        "flagged_classes": list(flagged),
        "provisional": prov,
        "fp_components": fp,
        "has_aorta": not prov,
        "tf1_tol0": 0.5,
        "classes_without_centreline": [],
        "dice": {"tree": 0.9, "LM": 0.9, "LAD": 0.9, "LCx": 0.9, "RCA": 0.9},
    }


_SEALED_ALL = set(SEALED["sealed_icx_test"]) | set(SEALED["sealed_quality0"])
VAL = [c for c in (f"c{i:04d}" for i in range(850, 1000)) if c not in _SEALED_ALL][
    :80
]  # synthetic, never sealed
assert not set(VAL) & (set(SEALED["sealed_icx_test"]) | set(SEALED["sealed_quality0"]))


def _val(rows):
    return {"set": "val", "tf1_sha256": RD_PIN, "summary": R9.summarise(rows), "rows": rows}


def _fired(val, dice=(90.0, 80)):
    f, info = RD.a27_reading(val, dice)
    return {x["row"]: x for x in f}, info


def test_a27_macro_rows_at_their_thresholds():
    for v, want in (
        (0.79, "stop"),
        (0.80, "reopen"),
        (0.849, "reopen"),
        (0.85, None),
        (0.95, None),
    ):
        f, info = _fired(_val([_row(c, v, v, v, v) for c in VAL]))
        assert info["macro"] == pytest.approx(v, abs=1e-4)
        assert (want in f) if want else not ({"stop", "reopen"} & set(f)), (v, f)


def test_a27_class_row_lists_the_10_worst_decisive_val_cases():
    rows = [_row(c, lcx=0.5 + i / 200) for i, c in enumerate(VAL)]
    rows[0]["flagged_classes"] = ["LCx"]  # flagged trees are not decisive: not among the worst
    f, info = _fired(_val(rows))
    assert "class" in f and [c["class"] for c in f["class"]["classes"]] == ["LCx"]
    worst = [w["case"] for w in f["class"]["classes"][0]["worst10"]]
    assert worst == VAL[1:11]
    f, _ = _fired(_val([_row(c, lcx=0.80) for c in VAL]))
    assert "class" not in f  # 0.80 itself does not fire (< 0.80)


def test_a27_flagged_dice_and_fp_rows():
    rows = [
        _row(c, flagged=("RCA",) if i < 25 else ()) for i, c in enumerate(VAL)
    ]  # 25/80 = 31 % > 30 %
    f, info = _fired(_val(rows))
    assert f["flagged"]["classes"] == ["RCA"] and info["per_class"]["RCA"]["n_flagged"] == 25
    rows = [
        _row(c, flagged=("RCA",) if i < 24 else ()) for i, c in enumerate(VAL)
    ]  # 24/80 = 30 %: not > 30 %
    assert "flagged" not in _fired(_val(rows))[0]
    assert "dice" in _fired(_val([_row(c) for c in VAL]), (88.2, 80))[0]
    assert "dice" not in _fired(_val([_row(c) for c in VAL]), (88.3, 80))[0]
    assert "fp_ok" in _fired(_val([_row(c, fp=1) for c in VAL]))[0]
    f = _fired(_val([_row(c, fp=2 if i % 2 else 1) for i, c in enumerate(VAL)]))[0]
    assert "fp_high" in f and "fp_ok" not in f


def test_a27_provisional_cases_are_left_out():
    rows = [_row(c) for c in VAL[:70]] + [_row(c, 0.1, 0.1, 0.1, 0.1, prov=True) for c in VAL[70:]]
    f, info = _fired(_val(rows))
    assert info["macro"] == 1.0 and info["n_decisive_cases"] == 70 and "stop" not in f


def test_replay_on_run1_real_rows_reproduces_round8_decisive_macro():
    """atlas2's per-case rows of run 1 (Trillium, thick reference, old hash): same decisive
    definition -> 0.896."""
    per = json.loads(
        (REPO / "trillium-results/round6/atlas2/results/per_case_run1.json").read_text()
    )
    names = {"1": "LM", "2": "LAD", "3": "LCx", "4": "RCA"}
    rows = []
    for a in per:
        rows.append(
            {
                "case": a["case"],
                "tf1": a["tf1"],
                "tf1_tol0": a["tf1_tol0"],
                "provisional": a["provisional"],
                "per_class": {names[str(k)]: v for k, v in a["per_class"].items()},
                "flagged_classes": [names[str(k)] for k in a["flagged_classes"]],
                "fp_components": a["fp_components"],
                "has_aorta": not a["provisional"],
                "classes_without_centreline": [],
                "dice": {k: None for k in ["tree", *names.values()]},
            }
        )
    f, info = _fired(_val(rows))
    assert info["macro"] == pytest.approx(0.896, abs=5e-4)  # Round 8: "decisive macro tF1 0.896"
    # Round 8 / atlas2 SUMMARY.md: LM 0.966, LAD 0.901, LCx 0.846, RCA 0.883; 44 of 316 trees
    # flagged; FP 1.49
    for n, v in (("LM", 0.966), ("LAD", 0.901), ("LCx", 0.846), ("RCA", 0.883)):
        assert info["per_class"][n]["tf1"] == pytest.approx(v, abs=6e-4), (
            n
        )  # published at 3 dp, ours at 4 dp
    assert sum(info["per_class"][n]["n_flagged"] for n in info["per_class"]) == 44
    assert sum(info["per_class"][n]["n_trees_all"] for n in info["per_class"]) == 316
    assert info["fp_val"] == pytest.approx(1.49, abs=5e-3) and "fp_high" in f
    assert not {"stop", "reopen"} & set(f)


# --------------------------------------------------------------------------------------------- A29
def _delta(val_share, val_d, open_share=0.99, open_d=0.0, aorta=True):
    def s(sh, d):
        x = {"n": 80}
        if aorta:
            x["tf1_expert_minus_aorta"] = [d, [d - 0.002, d + 0.002], 80]
            x["ostium_expert_vs_aorta_mm"] = {
                "n": 160,
                "median": 0.5,
                "share_le_2mm": sh,
                "share_le_5mm": 1.0,
            }
        return x

    return {
        "splits": {"val": s(val_share, val_d), "open_clean": s(open_share, open_d)},
        "errors": [],
    }


def test_a29_rule_on_val_validated_on_open36():
    assert RD.a29_reading(_delta(0.95, 0.005))["verdict"] == "adopted"
    assert (
        RD.a29_reading(_delta(0.96, -0.004, open_share=0.90))["verdict"] == "reported, not adopted"
    )
    assert RD.a29_reading(_delta(0.94, 0.0))["verdict"] == "withdrawn"
    assert RD.a29_reading(_delta(0.99, 0.006))["verdict"] == "withdrawn"
    assert RD.a29_reading(_delta(0.99, 0.0, aorta=False))["verdict"] == "not run"
    assert RD.a29_reading(_delta(0.99, 0.0))["text"] == RD.A29_PASS


# ---------------------------------------------------------------------------------- read end to end
def _write_inputs(tmp, scored, val_rows, per_case_dice=None, sealed_in=None):
    res = tmp / "results"
    res.mkdir()
    job, chk = _job_and_check(scored)
    (res / "tf1_per_case.json").write_text(json.dumps(job))
    dice = per_case_dice or [{"case": c, "group": "open36", "tree": 0.9} for c in OPEN36]
    if sealed_in:
        dice.append({"case": sealed_in, "group": "open36", "tree": 0.9})
    (res / "per_case_test.json").write_text(json.dumps(dice))
    (tmp / "o.json").write_text(json.dumps(chk))
    (tmp / "v.json").write_text(json.dumps(_val(val_rows)))
    (tmp / "d.json").write_text(json.dumps(_delta(0.97, 0.001)))
    return [
        "read",
        "--results",
        str(res),
        "--open36",
        str(tmp / "o.json"),
        "--val",
        str(tmp / "v.json"),
        "--delta",
        str(tmp / "d.json"),
        "--out",
        str(tmp / "verdict.json"),
        "--note-template",
        str(TEMPLATE),
        "--note-out",
        str(tmp / "note.md"),
    ]


def test_read_stands_fills_the_note(tmp_path, scored, capsys):
    rc = RD.main(_write_inputs(tmp_path, scored, [_row(c, lcx=0.9) for c in VAL]))
    assert rc == 0
    out = capsys.readouterr().out
    assert "**PASS**" in out and RD.A27["fp_ok"][1] in out and "P2 adopted" in out
    note = (tmp_path / "note.md").read_text()
    assert "{{" not in note and "The recipe stands" in note and "A29: P2 adopted" in note
    assert "A27: Stop" not in note and "recipe reopens" not in note and "A26 failed" not in note
    v = json.loads((tmp_path / "verdict.json").read_text())
    assert v["a26"]["ok"] and {f["row"] for f in v["a27"]["fired"]} == {"fp_ok"}


def test_read_stop_exit_code_and_note(tmp_path, scored, capsys):
    rc = RD.main(_write_inputs(tmp_path, scored, [_row(c, 0.7, 0.7, 0.7, 0.7, fp=3) for c in VAL]))
    assert rc == 3
    out = capsys.readouterr().out
    assert RD.A27["stop"][1] in out and RD.A27["class"][1] in out and RD.A27["fp_high"][1] in out
    note = (tmp_path / "note.md").read_text()
    assert "A27: Stop" in note and "The recipe stands" not in note and "FP per case > 1" in note


def test_read_a26_stop_reads_nothing_else(tmp_path, scored, capsys):
    args = _write_inputs(tmp_path, scored, [_row(c) for c in VAL])
    chk = json.loads((tmp_path / "o.json").read_text())
    chk["rows"][0]["tf1"] = 0.0
    (tmp_path / "o.json").write_text(json.dumps(chk))
    assert RD.main(args) == 2
    out = capsys.readouterr().out
    assert "**STOP**" in out and "A27" not in out.split("## A26")[1]
    note = (tmp_path / "note.md").read_text()
    assert "A26 failed" in note and "{{" not in note


def test_read_refuses_sealed_cases_anywhere(tmp_path, scored):
    args = _write_inputs(
        tmp_path, scored, [_row(c) for c in VAL], sealed_in=SEALED["sealed_icx_test"][0]
    )
    assert RD.main(args) == 4
    t2 = tmp_path / "b"
    t2.mkdir()
    rows = [_row(c) for c in VAL[:-1]] + [_row(SEALED["sealed_icx_test"][1])]
    assert RD.main(_write_inputs(t2, scored, rows)) == 4


# --------------------------------------------------------------------------------------- A15 census
def test_census_categories_without_and_with_softmax(tmp_path, geometry):
    ref, aorta, _ = geometry
    pred = ref.copy()
    pred[95:105, 2:10, 2:10] = 4  # one FP component, far from the tree
    W = tmp_path / "w"
    ct = R9.write_case(str(W), VAL[0], pred, ref, aorta)
    (W / "splits.json").write_text(json.dumps({"val": [VAL[0]], "train": [], "test": []}))
    (W / "layout.json").write_text(json.dumps({"cases": {VAL[0]: {"ct": ct}}}))
    out = tmp_path / "c.json"
    assert RD.main(["census", "--W", str(W), "--out", str(out), "--np", "1"]) == 0
    c = json.loads(out.read_text())
    assert (
        c["n_components"] == 1
        and c["by_category"]["unknown_no_softmax"]["n"] == 1
        and c["n_with_softmax"] == 0
    )
    prob = np.zeros((5,) + ref.shape, np.float32)
    prob[0] = 1.0
    blob = np.zeros(ref.shape, bool)
    blob[95:105, 2:10, 2:10] = True
    prob[0][blob], prob[4][blob] = 0.02, 0.98  # a confident FP
    npz = tmp_path / "npz"
    npz.mkdir()
    np.savez_compressed(
        npz / f"{VAL[0]}.npz", probabilities=np.transpose(prob, (0, 3, 2, 1))
    )  # nnU-Net's (C, z, y, x)
    assert (
        RD.main(["census", "--W", str(W), "--out", str(out), "--np", "1", "--npz-dir", str(npz)])
        == 0
    )
    c = json.loads(out.read_text())
    assert (
        c["by_category"]["confident_other"]["n"] == 1
        and c["majority_by_count"] == "confident_other"
    )
    r = RD.census_reading(c)
    assert r["confident_majority"] and r["has_softmax"]


def test_census_refuses_a_sealed_val_list(tmp_path):
    W = tmp_path / "w"
    W.mkdir()
    (W / "splits.json").write_text(json.dumps({"val": [SEALED["sealed_icx_test"][0]]}))
    assert RD.main(["census", "--W", str(W), "--out", str(tmp_path / "c.json")]) == 4


# ----------------------------------------------------------------------------------------- template
def test_template_has_a_block_for_every_branch():
    tpl = TEMPLATE.read_text()
    for k in [
        "a26_stop",
        "stands",
        "p2_adopted",
        "p2_withdrawn",
        "p2_reported",
        "p2_missing",
        "fp_confident",
        *RD.A27,
    ]:
        assert f"<!-- if:{k} -->" in tpl and f"<!-- endif:{k} -->" in tpl, k
    with pytest.raises(RD.InputError):
        RD.fill_template("{{nope}}", {}, set())
