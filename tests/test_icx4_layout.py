"""icx4's cases/ layouts (issue #79): the CT-only layout trillium/fetch_cases.py writes is accepted,
mixed or ambiguous layouts are refused, and the launcher's dry run on it shows the aorta set as
val 80 + open 36 + dev 44 = 160 with no sealed case."""

import os
import shutil

import pytest
from test_icx4_sealed import FIXTURE, ICX4, VAL_FIXTURE, _dry, _mod

layout = _mod("layout")


def _ct_only(cases, ids):
    for i in ids:
        (cases / f"c{i:04d}").mkdir(parents=True)
        (cases / f"c{i:04d}" / "ct.nii.gz").touch()


def test_ct_only_layout_is_accepted(tmp_path):
    _ct_only(tmp_path, range(5))
    (tmp_path / "cases.json").write_text("[]")  # fetch_cases' manifest is not a case
    kind, cases = layout.scan(str(tmp_path))
    assert kind == "girder-ct" and sorted(cases) == [f"c{i:04d}" for i in range(5)]
    assert cases["c0003"] == {"ct": str(tmp_path / "c0003" / "ct.nii.gz"), "mask": None}


def test_the_two_existing_layouts_are_unchanged(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    (a / "1.img.nii.gz").touch()
    (a / "1.label.nii.gz").touch()
    assert layout.scan(str(a)) == (
        "imagecas",
        {"c0000": {"ct": str(a / "1.img.nii.gz"), "mask": str(a / "1.label.nii.gz")}},
    )
    _ct_only(b, [0])
    (b / "c0000" / "coronary_arteries.nii.gz").touch()
    kind, cases = layout.scan(str(b))
    assert kind == "girder" and cases["c0000"]["mask"] == str(
        b / "c0000" / "coronary_arteries.nii.gz"
    )


@pytest.mark.parametrize("mix", ["girder+girder-ct", "imagecas+girder-ct", "two folders, one case"])
def test_mixed_or_ambiguous_layouts_are_refused(tmp_path, mix):
    _ct_only(tmp_path, [0, 1])
    if mix == "girder+girder-ct":  # e.g. an interrupted --masks fetch over a CT-only one
        (tmp_path / "c0000" / "coronary_arteries.nii.gz").touch()
    elif mix == "imagecas+girder-ct":
        (tmp_path / "9.img.nii.gz").touch()
        (tmp_path / "9.label.nii.gz").touch()
    else:
        (tmp_path / "case1").mkdir()  # ImageCAS id 1 = c0000 again
        (tmp_path / "case1" / "ct.nii.gz").touch()
    with pytest.raises(SystemExit, match="refusing to guess"):
        layout.scan(str(tmp_path))


def test_dry_run_on_the_fetched_layout_shows_the_160_aortas(tmp_path):
    """Acceptance (#79): ICX4_DRYRUN=1 ./icx4 on fetch_cases' CT-only cases/."""
    root = tmp_path / "root"
    shutil.copytree(ICX4, root / "experiments" / "icx4")
    _ct_only(root / "cases", range(1000))
    icx = tmp_path / "icx"
    icx.mkdir()
    shutil.copy(FIXTURE, icx / "test.txt")
    shutil.copy(VAL_FIXTURE, icx / "val.txt")
    held = {int(x) for x in FIXTURE.read_text().split() + VAL_FIXTURE.read_text().split()}
    (icx / "train.txt").write_text("\n".join(str(n) for n in range(1, 1001) if n not in held))
    r = _dry(root, icx, tmp_path, ICX4_CLUSTER="fir")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "layout: girder-ct" in r.stdout and "cases found: 1000" in r.stdout
    assert "aorta set: 160 cases (val 80: 80, open 36: 36, dev 44: 44), sealed 0" in r.stdout
    assert "scored: open-36 36 cases, dev-44 44 cases (of 160 ImageCAS-X test)" in r.stdout
    assert "would submit a chain" in r.stdout and "cluster: fir" in r.stdout
    assert not os.path.exists(root / "cases" / "c0000" / "coronary_arteries.nii.gz")
