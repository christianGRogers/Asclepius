"""Echo audit (Round 6, Q4): `segtrain.reads` against A3, A11', A1a/A1b and the SegQueue export.

Each test recorded a CONFIRMED defect (formerly ``xfail(strict=True)``). All are fixed in
segtrain.reads, so each must now pass. Evidence and owners:
vault/Plans/Experiments/Echo - Audit of the segtrain implementation against the master plan.md
"""

import nibabel as nib
import numpy as np
import pytest

pytest.importorskip("skimage")

from segtrain import reads as R  # noqa: E402

SHAPE = (60, 40, 24)
SP = (0.5, 0.5, 0.5)
AFFINE = np.diag([-0.5, 0.5, 0.5, 1.0])


def _box(lab, sl, v):
    lab[sl] = v


def _read(branch_class=R.LAD):
    """LM -> (LAD, LCx) plus one side branch whose name is ``branch_class``; a separate RCA."""
    lab = np.zeros(SHAPE, np.uint8)
    _box(lab, np.s_[5:15, 18:22, 10:14], R.LM)
    _box(lab, np.s_[15:50, 24:28, 10:14], R.LAD)
    _box(lab, np.s_[15:50, 12:16, 10:14], R.LCX)
    _box(lab, np.s_[15:19, 16:24, 10:14], R.LM)            # the bifurcation
    _box(lab, np.s_[16:40, 18:22, 10:14], branch_class)    # a ramus-like middle branch
    _box(lab, np.s_[5:55, 34:38, 18:22], R.RCA)
    return lab


def test_two_read_targets_keep_each_reads_own_names():
    a, b = _read(R.LAD), _read(R.LCX)
    ta, tb = R.a11_targets(a, b)
    assert np.array_equal(ta, a) and np.array_equal(tb, b)


def test_wave_report_runs_the_calibre_trigger(monkeypatch):
    seen = []
    real = R.convention_check

    def spy(read, mask, spacing, icx_lumen=None, **kw):
        seen.append(icx_lumen is not None)
        return real(read, mask, spacing, icx_lumen=icx_lumen, **kw)

    monkeypatch.setattr(R, "convention_check", spy)
    a = _read()
    case = R.CaseReads("c0100", {"A": a, "B": a.copy()}, SP, mask=a > 0, icx4=a, affine=AFFINE)
    R.first_reads_report([case], scorer=None, use_namer=False)
    assert seen and all(seen)


def test_ramus_only_disagreement_does_not_trigger_a_third_read(monkeypatch):
    from segtrain import namer

    a, b = _read(R.LAD), _read(R.LCX)
    ramus = (a != b) & (a > 0)

    def fake_name_tree(mask, affine, **kw):   # the namer says: that branch is a ramus candidate
        return namer.NamingResult(np.zeros(mask.shape, np.uint8), namer.Decisions(), ramus.copy())

    monkeypatch.setattr(namer, "name_tree", fake_name_tree)
    case = R.CaseReads("c0100", {"A": a, "B": b}, SP, affine=AFFINE)
    row = R.first_reads_report([case], scorer=None)["cases"][0]
    assert row["naming_attribution"]["ramus_only"], row["naming_attribution"]
    assert not row["third_read"]["needed"], row["third_read"]["reasons"]


def test_score_vs_reads_carries_the_provisional_flag():
    a = _read()
    res = R.score_vs_reads(a, [a, a.copy()], SP)
    assert "provisional" in res or any("provisional" in str(k) for k in res)


def _save(path, arr, affine):
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(arr, affine), str(path))


def test_read_folder_aligns_reads_with_the_mask(tmp_path):
    a = _read()
    a[:, :, :] = 0
    a[5:55, 34:38, 2:6] = R.RCA                 # off-centre in z so a flip matters
    flip = AFFINE.copy()
    flip[2, 2] = -0.5
    flip[2, 3] = 0.5 * (SHAPE[2] - 1)
    _save(tmp_path / "reads" / "c0100" / "A.nii.gz", a[:, :, ::-1].copy(), flip)
    _save(tmp_path / "masks" / "c0100.nii.gz", (a > 0).astype(np.uint8), AFFINE)
    (case,) = R.load_read_folder(str(tmp_path / "reads"), mask_dir=str(tmp_path / "masks"))
    cc = R.convention_check(case.reads["A"], case.mask, case.spacing)
    assert cc.union_dice_vs_mask > 0.99, cc


def test_read_folder_does_not_take_the_ct_for_a_read(tmp_path):
    _save(tmp_path / "c0100" / "ct.nii.gz", np.full(SHAPE, 300, np.int16), AFFINE)
    _save(tmp_path / "c0100" / "segmentations" / "left_main.nii.gz",
          (_read() == R.LM).astype(np.uint8), AFFINE)
    cases = R.load_read_folder(str(tmp_path))
    assert all("ct" not in c.reads for c in cases), [list(c.reads) for c in cases]
