"""R4-S23 (JA62; issue #215): the lead-run decision scorer, ``tools/janusm/score_decision.py``.

Synthetic only: label maps are ``harness.exact_shift_phantom`` and plain arrays; no case is
opened. Case ids appear only as guard inputs, never in an output.
"""

import importlib.util
import json
import sys
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
ORDER = S.decision_order()


# ------------------------------------------------------------------------------ harness, R4-S4/S5
# The scorer calls harness.compare(roi="ja37") and harness.transfer_check (Group B, #212). Until
# those are on dev, these stand-ins follow R4-S4/S5's text; on the closed phantoms here JA37's band
# holds the whole of both borders, so the band changes nothing.
def _compare(ref, test, *, affine, roi):
    assert roi == "ja37"
    if hasattr(H, "ja37_band"):
        return H.compare(ref, test, affine=affine, roi=roi, with_sta=False)
    return H.compare(ref, test, affine=affine, with_sta=False)


def _transfer(rows, *, n_first=20, limit_mm=0.05):
    if hasattr(H, "transfer_check"):
        return H.transfer_check(rows, n_first=n_first, limit_mm=limit_mm)
    if len(rows) < n_first:
        raise ValueError("fewer rows than n_first")
    rows = rows[:n_first]
    med = {b: float(np.median([abs(r[f"bias_{b}"] - r[f"bias_pp_{b}"]) for r in rows]))
           for b in S.BORDERS}
    ok = all(v <= limit_mm for v in med.values())
    over = sum(any(abs(r[f"bias_{b}"] - r[f"bias_pp_{b}"]) > limit_mm for b in S.BORDERS)
               for r in rows)
    return {"median_abs_diff_mm": med, "passed": ok, "n_over_limit": over,
            "bias_guard_mm": H.BIAS_GUARD_VALIDATED_MM if ok else H.BIAS_GUARD_FALLBACK_MM}


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


def _fake_features(labels, ct, affine, coronary, *, guard_mm=F.DEFAULT_GUARD_MM):
    return {"features_version": F.FEATURES_VERSION, "guard_mm": float(guard_mm),
            "marker": int(np.asarray(labels).ravel()[0])}


def _fake_compare(ref, test, *, affine, roi):
    row = {f"{k}_{b}": 0.1 for k in ("assd_pp", "assd_voxel", "bias", "bias_pp", "mean_abs_d")
           for b in S.BORDERS}
    return row


@pytest.fixture(scope="module")
def phantom_out():
    read, aff = _labels()
    model, _ = _labels(endo=0.5)
    items = [lambda: (model, read, read, None, aff, None)] * 20
    return S.score(items, compare=_memo(_compare), transfer_fn=_transfer,
                   features_fn=_fake_features)


# ------------------------------------------------------------------------------ the named tests
def test_known_d_and_transfer_verdict_on_exact_shift_phantom(phantom_out):
    """Reads identical, model's endocardium exactly +0.5 mm: d_endo = 0.5 within JA65's 0.035 mm;
    d_epi ~ 0; vol and pp agree on exact phantoms, so the guard stays 0.3 mm."""
    out = phantom_out
    assert out["n_cases"] == 20 and len(out["reads"]) == 20 and len(out["assd_pp"]) == 20
    row = out["assd_pp"][0]
    assert abs(row["d_endo"] - 0.5) <= 0.035
    assert abs(row["d_epi"]) <= 0.035
    assert row["read_vs_read"]["assd_pp_endo"] == pytest.approx(0.0, abs=1e-9)
    assert row["assd_guard_pass_endo"] and row["assd_guard_pass_epi"]
    tc = out["transfer_check"]
    assert tc["passed"] is True and tc["transfer_bias_guard_mm"] == H.BIAS_GUARD_TIGHT_MM
    # JA71 passed (R5-S3), so the open-base check's guard is 0.3 mm and the transfer check decides
    assert tc["bias_guard_mm"] == max(H.BIAS_GUARD_TIGHT_MM, H.BIAS_GUARD_VALIDATED_MM) == 0.3
    assert set(S.COMPARISONS) <= set(tc)
    json.loads(S.dumps(out))


def test_transfer_fails_to_half_mm_when_vol_and_pp_disagree():
    def cmp(ref, test, *, affine, roi):
        row = _fake_compare(ref, test, affine=affine, roi=roi)
        row["bias_endo"] = 0.1 + 0.06  # |vol - pp| = 0.06 > 0.05
        return row

    items = [lambda: (0, 0, 0, None, None, None)] * 20
    out = S.score(items, compare=cmp, transfer_fn=_transfer, features_fn=_fake_features)
    tc = out["transfer_check"]
    assert tc["passed"] is False and tc["bias_guard_mm"] == H.BIAS_GUARD_FALLBACK_MM
    assert tc["model_vs_read_1"]["n_over_limit"] == 20


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
