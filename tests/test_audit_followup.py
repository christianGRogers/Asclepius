"""Echo audit follow-up (Round 6, A21): defects found while re-verifying the fixes and checking
the remaining suspicions. CONFIRMED defects are ``xfail(strict=True)``; resolved suspicions are
plain regression tests. Evidence and owners:
vault/Plans/Experiments/Echo - Audit of the segtrain implementation against the master plan.md
"""

import json

import nibabel as nib
import numpy as np
import pytest

AFF = np.diag([-0.5, 0.5, 0.5, 1.0])


def _save(path, arr, affine=AFF):
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(arr, affine), str(path))


# ------------------------------------------------------------------------------- E1
def test_reads_report_keeps_sealed_cases_out(tmp_path):
    from segtrain import reads as R

    lab = np.zeros((30, 20, 12), np.uint8)
    lab[3:25, 8:11, 4:7] = R.LAD
    for folder in ("imagecas_0003", "imagecas_0003__r2", "imagecas_0004", "imagecas_0004__r2"):
        _save(tmp_path / folder / "segmentations" / "left_anterior_descending.nii.gz",
              (lab > 0).astype(np.uint8))
    try:
        cases = R.load_read_folder(str(tmp_path))
    except Exception:
        return                                          # refusing outright is an acceptable fix
    assert "c0002" not in {c.case for c in cases}, [c.case for c in cases]
    assert "c0003" in {c.case for c in cases}


# ------------------------------------------------------------------------------- E2
def test_reads_and_convert_agree_on_case_identity():
    from segtrain.proxy import canonical_case
    from segtrain.reads import case_id

    for name in ("imagecas_0003", "IMAGECAS_0003", "imagecas-0003", "c0002_rA",
                 "imagecas_0003__r2", "imagecas_1001"):
        want = canonical_case(name)
        got = case_id(name)
        if want is None:
            assert not (got.startswith("c") and got[1:].isdigit()), (name, got)
        else:
            assert got == want, (name, got, want)


# ------------------------------------------------------------------------------- E3
@pytest.mark.xfail(strict=True, reason=(
    "ECHO-E3 (suspicion confirmed): a class present in the reference whose voxels carry no "
    "centreline voxel is dropped from tree_f1's per_class and from the macro mean without any "
    "flag (synthetic even-width cross-section; skimage 0.26 skeletonize returns nothing). "
    "tf1.py is frozen (A1c); a fix can live in the `segtrain tf1` wrapper or follow A1c."))
def test_tf1_reports_a_reference_class_with_no_centreline(tmp_path, capsys):
    pytest.importorskip("skimage")
    from segtrain.cli import main

    shape = (80, 40, 30)
    ref = np.zeros(shape, np.uint8)
    g = np.indices(shape)
    ref[((g[1] - 10) ** 2 + (g[2] - 10) ** 2 <= 9) & (g[0] > 5) & (g[0] < 75)] = 4
    ref[5:75, 24:30, 14:20] = 2                     # LAD present, 2520 voxels
    _save(tmp_path / "ref.nii.gz", ref)
    _save(tmp_path / "pred.nii.gz", np.where(ref == 4, 4, 0).astype(np.uint8))   # LAD missed
    assert main(["tf1", str(tmp_path / "ref.nii.gz"), str(tmp_path / "pred.nii.gz")]) == 0
    row = json.loads(capsys.readouterr().out)
    assert "tf1_left_anterior_descending" in row or any(
        "centreline" in k and "left_anterior_descending" in json.dumps(row[k]) for k in row), row


# ------------------------------------------------------------------------------- resolved
def test_lm_in_one_read_only_triggers_a_third_read():
    """Round 6 A21 ruling: LM present in one read only is a decision disagreement."""
    from segtrain import reads as R

    a = np.zeros((60, 40, 24), np.uint8)
    a[5:19, 18:22, 10:14] = R.LM
    a[15:50, 24:28, 10:14] = R.LAD
    a[15:50, 12:16, 10:14] = R.LCX
    b = a.copy()
    b[b == R.LM] = R.LAD
    t = R.third_read_triggers(a, b, (0.5, 0.5, 0.5))
    assert t.needed and any("LM" in r for r in t.reasons)


def test_patch_pin_refuses_a_planner_mismatch(tmp_path):
    from segtrain.plans import enforce_patch

    f = tmp_path / "p.json"
    f.write_text(json.dumps({"configurations": {"3d_fullres": {
        "patch_size": [192, 192, 192], "batch_size": 2, "architecture": {}}}}))
    with pytest.raises(ValueError):
        enforce_patch(f, "3d_fullres", [256] * 3, 2, allow_pin=False)


# ------------------------------------------------------------------------------- E4
def test_wave_report_works_on_the_tree_bounding_box(monkeypatch):
    pytest.importorskip("skimage")
    from scipy import ndimage

    from segtrain import reads as R

    big = (160, 160, 120)
    lab = np.zeros(big, np.uint8)
    lab[60:70, 78:82, 60:64] = R.LM
    lab[70:100, 84:88, 60:64] = R.LAD
    lab[70:100, 72:76, 60:64] = R.LCX
    lab[70:74, 76:84, 60:64] = R.LM
    shapes = []
    real = ndimage.distance_transform_edt

    def spy(a, *args, **kw):
        shapes.append(np.asarray(a).size)
        return real(a, *args, **kw)

    monkeypatch.setattr(ndimage, "distance_transform_edt", spy)
    case = R.CaseReads("c0100", {"A": lab, "B": lab.copy()}, (0.5, 0.5, 0.5), mask=lab > 0,
                       icx4=lab, affine=AFF)
    R.first_reads_report([case], scorer=None, use_namer=False)
    # No distance transform may run on the full grid; none at all (exact point distances) is fine.
    assert not shapes or max(shapes) < lab.size / 8, (max(shapes), lab.size)
