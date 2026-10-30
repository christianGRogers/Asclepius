"""R4-S23 (JA62; issue #215) and R5-S12 (JA72, JA79; issue #233): the lead-run decision scorer,
``tools/janusm/score_decision.py``.

Synthetic only: label maps are ``harness.exact_shift_phantom`` and plain arrays; no case is
opened. Case ids appear only as guard inputs, never in an output or an assertion message.
The R5-S12 tests are named as Round 5's ruling (``jm/rest-ccta``) names them, in its order.
"""

import builtins
import hashlib
import importlib.util
import io
import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
for p in (REPO / "src", REPO / "tools" / "janusm"):
    if str(p) not in sys.path:
        sys.path.append(str(p))

from janusm import features as F  # noqa: E402
from janusm import geometry as G  # noqa: E402
from janusm import guard  # noqa: E402
from janusm import harness as H  # noqa: E402
from janusm import reference as R  # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "tools/janusm" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _load("score_decision")
B = _load("build_reference")
SEALED = json.loads((REPO / "configs/janusm/sealed-r1.json").read_text())
# The list as sealed-r1.json holds it, not as the function under test returns it (R5-S12).
ORDER = list(SEALED["decision"])


# ------------------------------------------------------------------------------ harness, R4-S4/S5
# The real harness.compare(roi="ja37") (without STA, which the scorer does not keep) and
# harness.transfer_check (R4-S4/S5, on dev since #219).
def _compare(ref, test, *, affine, roi):
    assert roi == "ja37"
    return H.compare(ref, test, affine=affine, roi=roi, with_sta=False)


_transfer = H.transfer_check


def _memo(fn):
    cache = {}

    def f(ref, test, **kw):
        key = (id(ref), id(test))
        if key not in cache:
            cache[key] = fn(ref, test, **kw)
        return cache[key]

    return f


def _labels(endo=0.0, epi=0.0):
    cav, out, aff = H.exact_shift_phantom(endo_shift_mm=endo, epi_shift_mm=epi)
    lab = np.zeros(cav.shape, np.int16)
    lab[out] = G.MYO
    lab[cav] = G.LV
    return lab, aff


def _corrugated_epi(height_mm=1.0, stripe_vox=2):
    """The exact phantom whose epicardium carries 1 mm stripes of ``height_mm``: real geometry on
    which the volume and point-to-plane biases disagree (|vol - pp| ~ 0.085 mm > 0.05 mm)."""
    cav, out, aff = H.exact_shift_phantom()
    _, up, _ = H.exact_shift_phantom(epi_shift_mm=height_mm)
    stripe = (np.indices(cav.shape)[0] // stripe_vox) % 2 == 0
    lab = np.zeros(cav.shape, np.int16)
    lab[out | (up & stripe)] = G.MYO
    lab[cav] = G.LV
    return lab, aff


def _fake_features(labels, ct, affine, coronary, *, guard_mm=F.DEFAULT_GUARD_MM):
    return {"features_version": F.FEATURES_VERSION, "guard_mm": float(guard_mm),
            "marker": int(np.asarray(labels).ravel()[0])}


def _fake_compare(ref, test, *, affine, roi):
    row = {f"{k}_{b}": 0.1 for k in ("assd_pp", "assd_voxel", "bias", "bias_pp", "mean_abs_d")
           for b in S.BORDERS}
    return row


# Known truth (JA65's 0.035 mm): read 2 is read 1 with the epicardium exactly +0.3 mm; the model is
# read 1 with the endocardium exactly +0.5 mm. So model-vs-read 1 is (0.5, 0), model-vs-read 2 is
# (0.5, 0.3), read-vs-read is (0, 0.3), and d = mean model-vs-read - read-vs-read is (0.5, -0.15).
TRUE_PP = {"model_vs_read_1": {"endo": 0.5, "epi": 0.0},
           "model_vs_read_2": {"endo": 0.5, "epi": 0.3},
           "read_vs_read": {"endo": 0.0, "epi": 0.3}}
TRUE_D = {"endo": 0.5, "epi": -0.15}


@pytest.fixture(scope="module")
def phantom_out():
    read_1, aff = _labels()
    read_2, _ = _labels(epi=0.3)
    model, _ = _labels(endo=0.5)
    items = [lambda: (model, read_1, read_2, None, aff, None)] * 20
    return S.score(items, compare=_memo(_compare), transfer_fn=_transfer,
                   features_fn=_fake_features)


# ------------------------------------------------------------------------------ the named tests
def test_read_2_is_read_1_with_epi_plus_0_3_mm_d_on_every_row(phantom_out):
    """R5-S12: read 2 = read 1 with the epicardium +0.3 mm exactly. d on every row equals the mean
    model-vs-read pp minus read-vs-read pp, and the known truth, within 0.035 mm."""
    out = phantom_out
    assert out["n_cases"] == 20 and len(out["reads"]) == 20 and len(out["assd_pp"]) == 20
    for row in out["assd_pp"]:
        for b in S.BORDERS:
            for k, truth in TRUE_PP.items():
                assert abs(row[k][f"assd_pp_{b}"] - truth[b]) <= 0.035, (k, b)
            mv = (row["model_vs_read_1"][f"assd_pp_{b}"]
                  + row["model_vs_read_2"][f"assd_pp_{b}"]) / 2.0
            assert row[f"d_{b}"] == pytest.approx(mv - row["read_vs_read"][f"assd_pp_{b}"],
                                                  abs=1e-12)
            assert abs(row[f"d_{b}"] - TRUE_D[b]) <= 0.035, b
        # read-vs-read is not zero, so the subtraction is exercised
        assert row["read_vs_read"]["assd_pp_epi"] > 0.25
        assert row["assd_guard_pass_endo"] and row["assd_guard_pass_epi"]
    tc = out["transfer_check"]
    # vol and pp agree on exact shifts: this check supports 0.3 mm, every comparison passes
    assert tc["passed"] is True and tc["transfer_bias_guard_mm"] == H.BIAS_GUARD_TIGHT_MM
    assert tc["n_cases_over_limit"] == 0
    # the guard in force is never below the open-base check's (JA61, JA71)
    assert tc["bias_guard_mm"] == max(H.BIAS_GUARD_TIGHT_MM, H.BIAS_GUARD_VALIDATED_MM)
    assert set(S.COMPARISONS) <= set(tc)
    json.loads(S.dumps(out))


def test_phantom_vol_and_pp_disagree_gives_passed_false_and_half_mm_guard():
    """R5-S12: on real phantom geometry (a striped epicardium) the volume and point-to-plane
    biases disagree by more than 0.05 mm, so the transfer check fails and the guard is 0.5 mm."""
    read, aff = _labels()
    model, _ = _corrugated_epi()
    items = [lambda: (model, read, read, None, aff, None)] * 20
    out = S.score(items, compare=_memo(_compare), transfer_fn=_transfer,
                  features_fn=_fake_features)
    tc = out["transfer_check"]
    gap = abs(tc["model_vs_read_1"]["median_abs_diff_mm"]["epi"])
    assert gap > H.TRANSFER_LIMIT_MM  # the phantom does what it claims
    assert tc["passed"] is False
    assert tc["model_vs_read_1"]["passed"] is False and tc["model_vs_read_2"]["passed"] is False
    assert tc["read_vs_read"]["passed"] is True
    assert tc["transfer_bias_guard_mm"] == H.BIAS_GUARD_FALLBACK_MM == 0.5
    assert tc["bias_guard_mm"] == 0.5
    assert tc["n_cases_over_limit"] == 20


def _pair_compare(over):
    """A compare whose rows are over the limit (endo) only for the comparisons in ``over``,
    identified by which loader objects it is handed (model 0, read 1, read 2)."""
    names = {(1, 0): "model_vs_read_1", (2, 0): "model_vs_read_2", (1, 2): "read_vs_read"}

    def cmp(ref, test, *, affine, roi):
        row = _fake_compare(ref, test, affine=affine, roi=roi)
        if names[(int(ref[0]), int(test[0]))] in over:
            row["bias_endo"] = 0.1 + 0.06  # |vol - pp| = 0.06 > 0.05
        return row

    return cmp


def _three():
    return (np.zeros(1, np.int16), np.ones(1, np.int16), np.full(1, 2, np.int16), None, None, None)


def test_read_vs_read_failing_alone_flips_passed():
    """R5-S12: model-vs-read 1 and 2 pass; read-vs-read alone fails; ``passed`` is False."""
    ok = S.score([_three] * 20, compare=_pair_compare(()), transfer_fn=_transfer,
                 features_fn=_fake_features)["transfer_check"]
    assert ok["passed"] is True
    tc = S.score([_three] * 20, compare=_pair_compare({"read_vs_read"}), transfer_fn=_transfer,
                 features_fn=_fake_features)["transfer_check"]
    assert tc["model_vs_read_1"]["passed"] is True and tc["model_vs_read_2"]["passed"] is True
    assert tc["read_vs_read"]["passed"] is False
    assert tc["passed"] is False and tc["transfer_bias_guard_mm"] == H.BIAS_GUARD_FALLBACK_MM


def test_union_count_over_comparisons_and_borders():
    """JA72: ``n_cases_over_limit`` counts distinct cases (of the first 20) with any comparison
    and border over the limit, not the sum of the per-comparison counts; cases after 20 are out."""
    def item(k):
        def load():
            return (np.zeros(1, np.int16), np.ones(1, np.int16), np.full(1, 2, np.int16),
                    None, None, k)
        return load

    def cmp(ref, test, *, affine, roi):
        return _fake_compare(ref, test, affine=affine, roi=roi)

    # cases 0-4 over on model-vs-read 1 (endo), cases 3-7 over on read-vs-read (epi), case 22
    # over on both; the union of the first 20 is 8, the per-comparison sum 10.
    over = {"model_vs_read_1": ("endo", set(range(0, 5)) | {22}),
            "read_vs_read": ("epi", set(range(3, 8)) | {22})}
    names = {(1, 0): "model_vs_read_1", (2, 0): "model_vs_read_2", (1, 2): "read_vs_read"}
    current = {}

    def feats(labels, ct, affine, coronary, *, guard_mm):
        current["k"] = coronary
        return _fake_features(labels, ct, affine, coronary, guard_mm=guard_mm)

    def cmp_k(ref, test, *, affine, roi):
        row = cmp(ref, test, affine=affine, roi=roi)
        name = names[(int(ref[0]), int(test[0]))]
        if name in over and current["k"] in over[name][1]:
            row[f"bias_{over[name][0]}"] = 0.1 + 0.06
        return row

    out = S.score([item(k) for k in range(23)], compare=cmp_k, transfer_fn=_transfer,
                  features_fn=feats)
    tc = out["transfer_check"]
    assert tc["model_vs_read_1"]["n_over_limit"] == 5 and tc["read_vs_read"]["n_over_limit"] == 5
    assert tc["n_cases_over_limit"] == 8
    assert S.n_cases_over_limit(out["assd_pp"]) == 8


def test_decision_order_equals_sealed_r1_decision_list():
    """R5-S12: ``decision_order()`` is ``sealed-r1.json["decision"]`` as a list, in its order.
    Compared without printing an id."""
    got = S.decision_order()
    same = isinstance(got, list) and got == SEALED["decision"]
    assert same, f"decision_order() differs from sealed-r1.json's list (n={len(got)}; no ids)"
    # a reordering is not the same list (the comparison is on order, not membership)
    assert list(reversed(got)) != SEALED["decision"]


def test_fewer_than_20_cases_is_an_error():
    items = [lambda: (0, 0, 0, None, None, None)] * 19
    with pytest.raises(S.ScoreError):
        S.score(items, compare=_fake_compare, transfer_fn=_transfer, features_fn=_fake_features)


def _manifest(cases, *, one_read=(), third=(), protocol=1):
    rows = []
    for c in cases:
        recs = [{"reader": "ra", "third": False, "border_protocol": protocol},
                {"reader": "rb", "third": False, "border_protocol": protocol}]
        reads = [f"reads/{c}__r1.nii.gz", f"reads/{c}__r2.nii.gz"]
        if c in one_read:
            recs, reads = recs[:1], reads[:1]
        row = {"case": c, "reads": reads, "readRecords": recs}
        if c in third:
            row["thirdRead"] = f"reads/{c}__third.nii.gz"
            row["thirdReadRecord"] = {"reader": "rc", "third": True, "border_protocol": 1}
        rows.append(row)
    return {"border_protocol": 1, "cases": rows}


def test_order_kept_and_one_read_case_skipped():
    """List order of sealed-r1.json's decision, not the manifest's; a one-read case is skipped,
    so reads[:20] are the first 20 complete cases."""
    skip = ORDER[3]
    m = _manifest(list(reversed(ORDER)), one_read={skip})
    pairs = S.select_pairs(ORDER, S.manifest_rows([(Path("/x"), m)]))
    got = [c for c, _ in pairs]
    assert got == [c for c in ORDER if c != skip]
    assert len(got[:20]) == 20 and skip not in got[:20] and got[19] == ORDER[20]

    # the case order reaches the output: a marker per case, in that order
    items = [(lambda k=k: (0, np.full(2, k, np.int16), np.full(2, k, np.int16), None, None, None))
             for k in range(len(pairs))]
    out = S.score(items, compare=_fake_compare, transfer_fn=_transfer,
                  features_fn=_fake_features)
    assert [r["read_1"]["marker"] for r in out["reads"]] == list(range(len(pairs)))


def test_in_list_third_read_is_dropped_and_case_counts_on_two_reads():
    """R5-S12: a ``third: True`` record inside ``readRecords`` (the in-list filter) is dropped,
    and the case still counts on its two reads."""
    c = ORDER[0]
    m = _manifest([c])
    row = m["cases"][0]
    row["reads"].insert(1, "reads/in_list_third.nii.gz")
    row["readRecords"].insert(1, {"reader": "rc", "third": True, "border_protocol": 1})
    pairs = dict(S.select_pairs(ORDER, S.manifest_rows([(Path("/x"), m)])))
    assert c in pairs and len(pairs[c]) == 2
    assert {r["reader"] for r in pairs[c]} == {"ra", "rb"}
    assert all("in_list_third" not in r["path"] for r in pairs[c])
    # without the filter the case would have three reads and be skipped: the filter is what counts
    row["readRecords"][1]["third"] = False
    assert c not in dict(S.select_pairs(ORDER, S.manifest_rows([(Path("/x"), m)])))


def test_third_reads_and_other_protocols_are_dropped():
    c0, c1 = ORDER[0], ORDER[1]
    m = _manifest([c0], third={c0})
    m2 = _manifest([c1], protocol=None)
    rows = S.manifest_rows([(Path("/a"), m), (Path("/b"), {"cases": m2["cases"]})])
    pairs = dict(S.select_pairs(ORDER, rows))
    assert c1 not in pairs  # pre-v1 reads do not count
    assert all("third" not in r["path"] for r in pairs[c0])
    assert len(pairs[c0]) == 2


def test_reader_key_fixes_read_1_and_is_never_written():
    c = ORDER[0]
    m = _manifest([c])
    rows = S.manifest_rows([(Path("/x"), m)])
    a = S.select_pairs(ORDER, rows)[0][1]
    m["cases"][0]["readRecords"].reverse()
    m["cases"][0]["reads"].reverse()
    b = S.select_pairs(ORDER, S.manifest_rows([(Path("/x"), m)]))[0][1]
    assert [r["reader"] for r in a] == [r["reader"] for r in b]
    assert S.reader_key(a[0]["reader"]) < S.reader_key(a[1]["reader"])


@pytest.mark.parametrize("which", ["seal", "seal_extension", "jm0"])
def test_seal_extension_or_jm0_id_refused_before_anything_is_opened(which, monkeypatch, tmp_path):
    opened = []
    monkeypatch.setattr(S, "_loader", lambda *a, **k: opened.append(a) or (lambda: None))
    bad = SEALED[which][0]
    with pytest.raises(guard.HeldOutError):
        S.guard_cases([ORDER[0], bad], ORDER)
    # and through main: refused, nothing opened, nothing written
    man = tmp_path / "manifest.json"
    man.write_text(json.dumps(_manifest(ORDER[:25] + [bad])))
    monkeypatch.setenv("SLURM_JOB_ID", "1")
    monkeypatch.setattr(S, "harness_api", lambda: (_fake_compare, _transfer))
    out = tmp_path / "o.json"
    rc = S.main(["--run", "--manifest", str(man), "--hc", str(tmp_path), "--layout",
                 str(tmp_path / "missing.json"), "--icx", str(tmp_path), "--out", str(out)])
    assert rc == 3 and not opened and not out.exists()


def test_a_non_decision_case_is_refused():
    other = next(c for c in json.loads((REPO / "trillium-results/icx14/results/splits.json")
                                       .read_text())["train"]
                 if c not in {x for k in ("seal", "seal_extension", "decision", "jm0")
                              for x in SEALED[k]})
    with pytest.raises(guard.HeldOutError, match="not decision cases"):
        S.guard_cases([other], ORDER)


def test_decision_cases_pass_the_guard():
    assert S.guard_cases(ORDER, ORDER) == ORDER


def test_same_coronary_array_for_both_reads():
    seen = []

    def feats(labels, ct, affine, coronary, *, guard_mm):
        seen.append(coronary)
        return _fake_features(labels, ct, affine, coronary, guard_mm=guard_mm)

    cor = np.zeros((3, 3, 3), np.int16)
    S.score_case(0, 1, 2, None, None, cor, compare=_fake_compare, features_fn=feats)
    assert len(seen) == 2 and seen[0] is cor and seen[1] is cor


def test_an_id_in_the_output_is_refused():
    def feats(labels, ct, affine, coronary, *, guard_mm):
        return {**_fake_features(labels, ct, affine, coronary, guard_mm=guard_mm),
                "note": ORDER[0]}

    items = [lambda: (0, 0, 0, None, None, None)] * 20
    with pytest.raises(R.ReferenceError):
        S.score(items, compare=_fake_compare, transfer_fn=_transfer, features_fn=feats)
    with pytest.raises(R.ReferenceError):
        S.dumps({"x": "ImageCAS-X__" + ORDER[0]})


def test_build_reference_accepts_the_output_and_refuses_mismatches(phantom_out):
    reads = B.load_decision_reads(json.loads(S.dumps(phantom_out)))
    assert len(reads) == 20 and reads[0]["read_1"]["features_version"] == F.FEATURES_VERSION

    bad = json.loads(S.dumps(phantom_out))
    bad["reads"][3]["read_2"]["features_version"] = "0.9.0"
    with pytest.raises(R.ReferenceError, match="features_version"):
        B.load_decision_reads(bad)
    bad = json.loads(S.dumps(phantom_out))
    bad["features_version"] = "0.9.0"
    with pytest.raises(R.ReferenceError, match="features_version"):
        B.load_decision_reads(bad)
    with pytest.raises(R.ReferenceError, match="guard_mm"):
        B.load_decision_reads(json.loads(S.dumps(phantom_out)), guard_mm=1.5)


# ------------------------------------------------------------------------------ running
def test_without_run_prints_the_fir_command(capsys):
    assert S.main([]) == 0
    out = capsys.readouterr().out
    assert "sbatch" in out and "--run" in out and "def-aso22" in out


def test_run_outside_slurm_refuses(monkeypatch, capsys):
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    assert S.main(["--run"]) == 3
    assert "REFUSED" in capsys.readouterr().err


def test_harness_without_r4_s4_s5_refuses(monkeypatch):
    monkeypatch.delattr(H, "transfer_check", raising=False)
    with pytest.raises(S.ScoreError, match="R4-S4/R4-S5"):
        S.harness_api()


# ------------------------------------------------------------------------------ main --run (R5-S12)
READERS = ("reader-alpha-5f3c", "reader-beta-9d21")  # synthetic reader ids


def _run_env(tmp_path, monkeypatch, cases, *, held_out=None):
    """A stubbed Fir Slurm environment: a manifest on disk with read files, a layout, no image
    opened (the loader is stubbed with plain arrays and the fake compare / features)."""
    wave = tmp_path / "wave1"
    (wave / "reads").mkdir(parents=True)
    rows = []
    names = list(cases) + ([held_out] if held_out else [])
    for i, c in enumerate(names):
        reads = [f"reads/r{i}_a.nii.gz", f"reads/r{i}_b.nii.gz"]
        for r in reads:
            (wave / r).write_bytes(b"not an image")
        rows.append({"case": c, "reads": reads, "readRecords": [
            {"reader": READERS[0], "third": False, "border_protocol": 1},
            {"reader": READERS[1], "third": False, "border_protocol": 1}]})
    man = wave / "manifest.json"
    man.write_text(json.dumps({"border_protocol": 1, "cases": rows}))
    (tmp_path / "hc").mkdir()
    (tmp_path / "icx").mkdir()
    layout = tmp_path / "layout.json"
    layout.write_text(json.dumps({"cases": {c: {"ct": str(tmp_path / "ct.nii.gz")}
                                            for c in names}}))
    monkeypatch.setenv("SLURM_JOB_ID", "1")
    monkeypatch.setattr(S, "harness_api", lambda: (_fake_compare, _transfer))
    monkeypatch.setattr(S, "_jm0r", lambda: types.SimpleNamespace(hc_ids=lambda: {}))

    def loader(case, reads, hc, ct, icx, m, ids):
        assert [Path(r["path"]).parent.name for r in reads] == ["reads", "reads"]
        return lambda: (0, 0, 0, None, None, None)

    monkeypatch.setattr(S, "_loader", loader)
    monkeypatch.setattr(S, "score", _with_fake_features(S.score))
    out = tmp_path / "decision_read_features.json"
    argv = ["--run", "--manifest", str(man), "--hc", str(tmp_path / "hc"), "--layout",
            str(layout), "--icx", str(tmp_path / "icx"), "--out", str(out)]
    return argv, out


def _with_fake_features(score):
    def f(items, **kw):
        kw["features_fn"] = _fake_features
        return score(items, **kw)
    return f


def test_main_run_success_writes_json_and_matching_sha256(tmp_path, monkeypatch, capsys):
    """R5-S12: ``main --run`` under a stubbed Slurm environment writes the JSON and a matching
    ``.sha256``."""
    argv, out = _run_env(tmp_path, monkeypatch, ORDER[:22])
    assert S.main(argv) == 0
    text = out.read_bytes()
    sha = hashlib.sha256(text).hexdigest()
    side = Path(str(out) + ".sha256").read_text()
    assert side == f"{sha}  {out.name}\n"
    d = json.loads(text)
    assert d["n_cases"] == 22 and len(d["reads"]) == 22
    assert d["score_decision_version"] == S.SCORE_VERSION
    assert d["transfer_check"]["n_cases_over_limit"] == 0
    err = capsys.readouterr().err
    assert "guard:" in err and f"sha256 {sha}" in err


def test_no_reader_id_or_key_digest_in_output_bytes(tmp_path, monkeypatch):
    """R5-S12: neither a reader id nor its key digest (whole, or a 12-hex prefix) appears in the
    bytes ``main --run`` writes."""
    argv, out = _run_env(tmp_path, monkeypatch, ORDER[:20])
    assert S.main(argv) == 0
    blobs = [out.read_bytes(), Path(str(out) + ".sha256").read_bytes()]
    for reader in READERS:
        key = S.reader_key(reader)
        for needle in (reader, key, key[:12]):
            assert all(needle.encode() not in b for b in blobs), "a reader id or key was written"
    # and no case id either
    for c in ORDER[:20]:
        assert all(c.encode() not in b for b in blobs), "a case id was written"


def test_spy_no_image_mask_label_or_read_opened_before_guard_refuse(tmp_path, monkeypatch,
                                                                     capsys):
    """R5-S12 / JA72: an ``open`` / ``nib.load`` spy shows no image, mask, label or read file
    opened before ``guard.refuse``; stderr names ``HeldOutError`` for a held-out id. The manifest
    may be read first (JA72), and the spy is shown to see it."""
    import nibabel as nib

    held = SEALED["seal"][0]
    argv, out = _run_env(tmp_path, monkeypatch, ORDER[:22], held_out=held)
    events = []
    real_open, real_io_open, real_load = builtins.open, io.open, nib.load
    real_refuse = guard.refuse

    def spy_open(file, *a, **k):
        events.append(("open", str(file)))
        return real_open(file, *a, **k)

    def spy_load(file, *a, **k):
        events.append(("nib.load", str(file)))
        return real_load(file, *a, **k)

    def spy_refuse(*a, **k):
        events.append(("refuse", ""))
        return real_refuse(*a, **k)

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(io, "open", spy_open)
    monkeypatch.setattr(nib, "load", spy_load)
    monkeypatch.setattr(guard, "refuse", spy_refuse)
    try:
        rc = S.main(argv)
    finally:
        monkeypatch.setattr(builtins, "open", real_open)
        monkeypatch.setattr(io, "open", real_io_open)
    assert rc == 3 and not out.exists()
    assert "HeldOutError" in capsys.readouterr().err

    def is_data(kind, path):
        p = Path(path)
        return (kind == "nib.load" or p.name.endswith((".nii", ".nii.gz", ".nrrd", ".mha"))
                or any(d in p.parents for d in (tmp_path / "hc", tmp_path / "icx",
                                                tmp_path / "wave1" / "reads")))

    kinds = [k for k, _ in events]
    assert "refuse" in kinds  # the guard ran
    first = kinds.index("refuse")
    assert not [e for e in events[:first] if is_data(*e)], "a data file was opened before the guard"
    assert not [e for e in events if is_data(*e)], "a data file was opened at all"
    # the spy sees opens: the manifest was read (allowed before the guard, JA72)
    assert ("open", str(tmp_path / "wave1" / "manifest.json")) in events
