"""The batch aorta producer (A21): resumable, loud per case, on the CT grid, sealed cases refused.
TotalSegmentator is never imported: a fake segmenter (or a fake module) stands in."""

import json
import sys
import types

import nibabel as nib
import numpy as np
import pytest

from segtrain import aorta as AO

SHAPE = (40, 36, 30)
AFF = np.diag([0.5, 0.5, 0.8, 1.0])
AFF[:3, 3] = (-10.0, 5.0, 20.0)


def _write(path, data, aff=AFF):
    nib.save(nib.Nifti1Image(np.asarray(data), aff), str(path))
    return path


def _ct(tmp_path, name="c0001"):
    ct = np.full(SHAPE, -100, np.int16)
    ct[5:15, 5:15, 5:25] = 400  # the 'aorta': bright box
    return _write(tmp_path / f"{name}_ct.nii.gz", ct)


def _fake(calls=None):
    """Segment voxels > 200 HU of whatever image it is given, on that image's grid."""

    def seg(path, device):
        img = nib.load(path)
        if calls is not None:
            calls.append((tuple(img.shape), device))
        return nib.Nifti1Image((np.asanyarray(img.dataobj) > 200).astype(np.uint8), img.affine)

    return seg


def test_mask_is_written_on_the_ct_grid(tmp_path):
    ct = _ct(tmp_path)
    rep = AO.produce_aortas({"c0001": ct}, tmp_path / "ao", segmenter=_fake(), log=lambda s: None)
    m = nib.load(str(AO.aorta_path(tmp_path / "ao", "c0001")))
    assert rep.made == ["c0001"] and rep.ok
    assert m.shape == SHAPE and np.allclose(m.affine, AFF)
    a = np.asanyarray(m.dataobj)
    assert a.dtype == np.uint8 and set(np.unique(a)) == {0, 1} and a[5:15, 5:15, 5:25].all()
    report = json.loads((tmp_path / "ao" / "aorta_report.json").read_text())
    assert report["made"] == ["c0001"] and report["failed"] == {}


def test_reference_crop_is_pasted_back_at_the_right_place(tmp_path):
    ct = _ct(tmp_path)
    ref = np.zeros(SHAPE, np.uint8)
    ref[20:24, 18:22, 10:14] = 1  # a 'tree' away from the volume centre
    refp = _write(tmp_path / "ref.nii.gz", ref)
    calls = []
    AO.segment_aorta(
        ct, tmp_path / "a.nii.gz", reference=refp, margin_mm=8.0, segmenter=_fake(calls)
    )
    ((shape, _),) = calls
    assert shape != SHAPE  # TotalSegmentator saw the crop only
    a = np.asanyarray(nib.load(str(tmp_path / "a.nii.gz")).dataobj) > 0
    # 8 mm margin = 16 voxels in x/y (0.5 mm), 10 in z (0.8 mm): crop [4:40, 2:36, 0:24]
    assert shape == (36, 34, 24)
    want = np.zeros(SHAPE, bool)
    want[5:15, 5:15, 5:24] = True  # the bright box, as far as the crop reaches
    assert np.array_equal(a, want)


def test_existing_valid_mask_is_kept_and_overwrite_recomputes(tmp_path):
    ct = _ct(tmp_path)
    calls = []
    AO.produce_aortas({"c0001": ct}, tmp_path, segmenter=_fake(calls), log=lambda s: None)
    rep = AO.produce_aortas({"c0001": ct}, tmp_path, segmenter=_fake(calls), log=lambda s: None)
    assert rep.kept == ["c0001"] and rep.made == [] and len(calls) == 1
    AO.produce_aortas(
        {"c0001": ct}, tmp_path, segmenter=_fake(calls), overwrite=True, log=lambda s: None
    )
    assert len(calls) == 2


def test_invalid_existing_mask_is_recomputed(tmp_path):
    ct = _ct(tmp_path)
    _write(
        AO.aorta_path(tmp_path, "c0001"), np.zeros(SHAPE, np.uint8)
    )  # empty: a broken earlier run
    rep = AO.produce_aortas({"c0001": ct}, tmp_path, segmenter=_fake(), log=lambda s: None)
    assert rep.made == ["c0001"]


def test_one_failure_is_loud_and_does_not_stop_the_others(tmp_path):
    good, bad = _ct(tmp_path, "c0001"), _ct(tmp_path, "c0002")

    def seg(path, device):
        if "c0002" in path:
            raise RuntimeError("CUDA out of memory")
        return _fake()(path, device)

    with pytest.raises(AO.AortaBatchError) as e:
        AO.produce_aortas(
            {"c0001": good, "c0002": bad, "c0003": tmp_path / "missing.nii.gz"},
            tmp_path / "ao",
            segmenter=seg,
            log=lambda s: None,
        )
    rep = e.value.report
    assert rep.made == ["c0001"] and set(rep.failed) == {"c0002", "c0003"}
    assert "out of memory" in rep.failed["c0002"] and "not found" in rep.failed["c0003"]
    assert not AO.aorta_path(tmp_path / "ao", "c0002").exists()  # no partial file
    assert not list((tmp_path / "ao").glob(".aorta_*"))  # temp dirs cleaned up
    assert json.loads((tmp_path / "ao" / "aorta_report.json").read_text())["failed"].keys() == {
        "c0002",
        "c0003",
    }


def test_empty_aorta_and_wrong_grid_are_failures(tmp_path):
    ct = _ct(tmp_path)
    empty = lambda p, d: nib.Nifti1Image(np.zeros(nib.load(p).shape, np.uint8), AFF)  # noqa: E731
    with pytest.raises(AO.AortaError, match="no aorta"):
        AO.segment_aorta(ct, tmp_path / "a.nii.gz", segmenter=empty)
    small = lambda p, d: nib.Nifti1Image(np.ones((4, 4, 4), np.uint8), AFF)  # noqa: E731
    with pytest.raises(AO.AortaError, match="grid"):
        AO.segment_aorta(ct, tmp_path / "a.nii.gz", segmenter=small)
    assert not (tmp_path / "a.nii.gz").exists()


def test_sealed_cases_are_refused_before_any_work(tmp_path):
    calls = []
    with pytest.raises(ValueError, match="sealed"):
        AO.produce_aortas(
            {"c0001": _ct(tmp_path)},
            tmp_path,
            sealed={"c0001"},
            segmenter=_fake(calls),
            log=lambda s: None,
        )
    assert calls == []


def test_device_is_validated_and_passed_through(tmp_path):
    ct = _ct(tmp_path)
    with pytest.raises(ValueError, match="device"):
        AO.produce_aortas(
            {"c0001": ct}, tmp_path, device="cuda", segmenter=_fake(), log=lambda s: None
        )
    calls = []
    AO.produce_aortas(
        {"c0001": ct}, tmp_path, device="gpu", segmenter=_fake(calls), log=lambda s: None
    )
    assert calls[0][1] == "gpu"


def test_totalsegmentator_is_imported_lazily_with_the_right_call(tmp_path, monkeypatch):
    seen = {}

    def totalsegmentator(inp, out, **kw):
        seen.update(kw, inp=inp, out=out)
        img = nib.load(inp)
        return nib.Nifti1Image((np.asanyarray(img.dataobj) > 200).astype(np.uint8), img.affine)

    api = types.ModuleType("totalsegmentator.python_api")
    api.totalsegmentator = totalsegmentator
    monkeypatch.setitem(sys.modules, "totalsegmentator", types.ModuleType("totalsegmentator"))
    monkeypatch.setitem(sys.modules, "totalsegmentator.python_api", api)
    AO.segment_aorta(_ct(tmp_path), tmp_path / "a.nii.gz", device="cpu")
    assert seen["fast"] is True and seen["roi_subset"] == ["aorta"] and seen["device"] == "cpu"
    assert seen["out"] is None


def test_missing_totalsegmentator_explains_the_install(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "totalsegmentator", None)
    monkeypatch.setitem(sys.modules, "totalsegmentator.python_api", None)
    with pytest.raises(ImportError, match="no-deps"):
        AO.segment_aorta(_ct(tmp_path), tmp_path / "a.nii.gz")
