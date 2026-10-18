"""icx4 refuses a partial cases/ (issue #82).

On 2026-10-18 an interrupted fetch_cases.py left CTs for 669 of the 1000 case folders, and the
launcher submitted the chain anyway. Now the launcher (dry run here) and job_body.sh both refuse
unless all 1000 CTs and every ImageCAS-X train/val/test case are present; ICX4_ALLOW_PARTIAL=1 is
the only way through. layout.py reports a case folder without a finished ct.nii.gz as incomplete.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from test_icx4_sealed import FIXTURE, ICX4, LIB, SEALED_JSON, VAL_FIXTURE, _dry, _mod
from test_icx4_tf1 import PIN

layout = _mod("layout")

# 331 of the 1000 case folders lack a finished CT, as in the incident; some still hold a .part
MISSING = [i for i in range(1000) if i % 3 == 0][:331]


def _icx(tmp_path):
    icx = tmp_path / "icx"
    icx.mkdir()
    shutil.copy(FIXTURE, icx / "test.txt")
    shutil.copy(VAL_FIXTURE, icx / "val.txt")
    held = {int(x) for x in FIXTURE.read_text().split() + VAL_FIXTURE.read_text().split()}
    rest = [n for n in range(1, 1001) if n not in held]
    (icx / "train.txt").write_text("\n".join(map(str, rest[:560])))
    return icx


def _cases(cases, missing=()):
    for i in range(1000):
        d = cases / f"c{i:04d}"
        d.mkdir(parents=True)
        if i not in missing:
            (d / "ct.nii.gz").touch()
        elif i % 2:
            (d / "ct.nii.gz.part").write_bytes(b"half")


def _launch(tmp_path, missing, **env):
    root = tmp_path / "root"
    shutil.copytree(ICX4, root / "experiments" / "icx4")
    _cases(root / "cases", missing)
    return _dry(root, _icx(tmp_path), tmp_path, ICX4_CLUSTER="fir", **env)


def test_layout_reports_folders_without_a_finished_ct(tmp_path):
    _cases(tmp_path, MISSING)
    kind, cases = layout.scan(str(tmp_path))
    assert kind == "girder-ct" and len(cases) == 669
    inc = layout.incomplete(str(tmp_path))
    assert sorted(inc) == [f"c{i:04d}" for i in MISSING]
    assert inc["c0003"] == "partial" and inc["c0000"] == "missing"
    r = subprocess.run(
        [sys.executable, str(LIB / "layout.py"), str(tmp_path), str(tmp_path / "layout.json")],
        capture_output=True,
        text=True,
        env=dict(os.environ, CASES=str(tmp_path)),
        cwd=tmp_path,
    )
    assert r.returncode == 0, r.stderr
    assert "incomplete: 331 case folder(s) without a finished ct.nii.gz" in r.stdout
    assert json.loads((tmp_path / "layout.json").read_text())["incomplete"] == inc


def test_launcher_refuses_669_of_1000(tmp_path):
    r = _launch(tmp_path, MISSING)
    assert r.returncode != 0, r.stdout
    assert "cases with a CT: 669 of 1000" in r.stdout
    assert "MISSING: 331 of 1000 cases have no CT, e.g. ['c0000', 'c0003'" in r.stdout
    assert "MISSING: ImageCAS-X train:" in r.stdout and "MISSING: ImageCAS-X val:" in r.stdout
    assert "resume the fetch: python3 <repo>/trillium/fetch_cases.py" in r.stdout
    assert "REFUSING: cases/ is incomplete" in r.stdout
    assert "not submitting" in r.stderr and "would submit" not in r.stdout


def test_launcher_refuses_even_one_missing_test_case(tmp_path):
    one = int(FIXTURE.read_text().split()[0]) - 1  # an ImageCAS-X test case
    r = _launch(tmp_path, [one])
    assert r.returncode != 0 and "would submit" not in r.stdout
    assert f"ImageCAS-X test: 1 of 160 cases missing, e.g. ['c{one:04d}']" in r.stdout


def test_override_lets_a_deliberate_partial_run_through(tmp_path):
    r = _launch(tmp_path, MISSING, ICX4_ALLOW_PARTIAL="1")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "WARNING: ICX4_ALLOW_PARTIAL=1" in r.stdout and "would submit a chain" in r.stdout
    # the job's second guard sees the same choice
    assert 'export ICX4_ALLOW_PARTIAL="1"' in r.stdout


def test_complete_cases_still_submit(tmp_path):
    r = _launch(tmp_path, ())
    assert r.returncode == 0, r.stdout + r.stderr
    assert "cases complete: all 1000 CTs" in r.stdout and "would submit a chain" in r.stdout
    assert 'export ICX4_ALLOW_PARTIAL="0"' in r.stdout


def test_job_refuses_a_partial_cases_dir_before_preprocessing(tmp_path):
    lib = tmp_path / "exp" / "lib"
    shutil.copytree(LIB, lib)
    shutil.copy(SEALED_JSON, tmp_path / "exp" / "sealed_test.json")
    W = tmp_path / "w"
    (W / "logs").mkdir(parents=True)
    shutil.copy(SEALED_JSON, W / "sealed_test.json")
    cases = tmp_path / "cases"
    _cases(cases, MISSING)
    kind, found = layout.scan(str(cases))
    json.dump(
        {"cases_dir": str(cases), "layout": kind, "cases": found, "incomplete": {}},
        open(W / "layout.json", "w"),
    )
    e = {k: v for k, v in os.environ.items() if not k.startswith("ICX4_")}
    e.update(
        W=str(W),
        LIB=str(lib),
        ICX=str(_icx(tmp_path)),
        VENV=str(tmp_path / "none"),
        FROZEN_SHA=PIN,
        PATH=f"{Path(sys.executable).parent}:{e.get('PATH', '')}",
    )
    r = subprocess.run(["bash", str(lib / "job_body.sh")], capture_output=True, text=True, env=e)
    assert r.returncode == 3 and "REFUSING: cases/ is incomplete" in r.stdout, r.stdout + r.stderr
    assert "resume the fetch" in r.stdout
    assert not (W / "timings.json").exists() and not (W / "nnunet_raw").exists()
