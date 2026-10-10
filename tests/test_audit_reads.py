"""Echo audit (Round 6, Q4): `segtrain.reads` against A3, A11', A1a/A1b and the SegQueue export.

Each test records a CONFIRMED defect and is ``xfail(strict=True)``. Evidence and owners:
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


@pytest.mark.xfail(strict=True, reason=(
    "ECHO-D5: A11' (Round 5) replaced A11's voxel rule -- each read is a separate training "
    "sample with NO name-conflict ignore -- but a11_targets, the only read->target builder in "
    "src/segtrain (and the one configs/tasks/Dataset712 points at), still writes ignore=5 "
    "wherever the two reads name a voxel differently."))
def test_two_read_targets_keep_each_reads_own_names():
    a, b = _read(R.LAD), _read(R.LCX)
    ta, tb = R.a11_targets(a, b)
    assert np.array_equal(ta, a) and np.array_equal(tb, b)


@pytest.mark.xfail(strict=True, reason=(
    "ECHO-D6: A3's monitor has two triggers (union Dice < 0.9, or calibre nearer ImageCAS-X "
    "than the mask). first_reads_report loads the ImageCAS-X labels (cr.icx4) but calls "
    "convention_check without icx_lumen, so the calibre trigger never runs in the wave report."))
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


@pytest.mark.xfail(strict=True, reason=(
    "ECHO-D7: the A11 third-read rule keeps the ramus-only exemption (Round 3 A4, Round 5 A11'), "
    "but first_reads_report calls third_read_triggers without ramus_mask, so a LAD/LCx "
    "disagreement confined to a ramus candidate still sends the case to a third reader."))
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


@pytest.mark.xfail(strict=True, reason=(
    "ECHO-D4: A1a (a tF1 without an aorta mask decides nothing) and A1b (flagged trees are "
    "excluded from decisive aggregates) cannot be enforced in segtrain.reads: the Scorer "
    "contract returns only {class: tF1}, dropping TreeF1.provisional/flagged, so "
    "score_vs_reads / inter_read_tf1 / acceptance aggregate provisional and flagged trees "
    "with no marker."))
def test_score_vs_reads_carries_the_provisional_flag():
    a = _read()
    res = R.score_vs_reads(a, [a, a.copy()], SP)
    assert "provisional" in res or any("provisional" in str(k) for k in res)


def _save(path, arr, affine):
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(arr, affine), str(path))


@pytest.mark.xfail(strict=True, reason=(
    "ECHO-D10: load_read_folder never compares the reads' affine with the mask's; a read on the "
    "same physical grid stored z-reversed (how both real SegQueue submissions are stored) is "
    "compared voxel-by-voxel with the mask, so A3 flags a perfect split as thin."))
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


@pytest.mark.xfail(strict=True, reason=(
    "ECHO-D10: SegQueue's export writes <case>/ct.nii.gz + <case>/segmentations/*.nii.gz; "
    "pointed at that tree, load_read_folder takes ct.nii.gz (HU cast to uint8) as a read "
    "called 'ct' and ignores the segmentations. There is no converter from the export to the "
    "<case>/<annotator>.nii.gz layout docs/TRAINING-R1.md step 9 asks for."))
def test_read_folder_does_not_take_the_ct_for_a_read(tmp_path):
    _save(tmp_path / "c0100" / "ct.nii.gz", np.full(SHAPE, 300, np.int16), AFFINE)
    _save(tmp_path / "c0100" / "segmentations" / "left_main.nii.gz",
          (_read() == R.LM).astype(np.uint8), AFFINE)
    cases = R.load_read_folder(str(tmp_path))
    assert all("ct" not in c.reads for c in cases), [list(c.reads) for c in cases]
