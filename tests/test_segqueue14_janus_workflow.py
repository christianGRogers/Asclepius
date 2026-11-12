"""The *SegQueue14 on janus* workflow's argument checks (D43, #286; #293).

Runs the workflow's own "Which step" script with bash, as Actions would, so what
reaches the shell on janus is checked here and not only by reading the YAML.
"""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/segqueue14-janus.yml"

pytestmark = pytest.mark.skipif(not shutil.which("bash"), reason="no bash")


def _script():
    wf = yaml.safe_load(WORKFLOW.read_text())
    steps = wf["jobs"]["run"]["steps"]
    return next(s for s in steps if s.get("id") == "cmd")["run"]


def _which(tmp_path, command, args=""):
    out, summary = tmp_path / "out", tmp_path / "summary"
    out.write_text("")
    done = subprocess.run(
        ["bash", "-c", _script()], capture_output=True, text=True, timeout=30,
        env={"PATH": "/usr/bin:/bin", "INPUT": command, "ARGS": args,
             "GITHUB_OUTPUT": str(out), "GITHUB_STEP_SUMMARY": str(summary)})
    cmd = None
    for line in out.read_text().splitlines():
        if line.startswith("cmd="):
            cmd = line[4:]
    return done.returncode, cmd, done.stdout + done.stderr


@pytest.mark.parametrize("command,args,expected", [
    ("benchmark-seed", "", "benchmark-seed"),
    ("benchmark-seed --apply", "", "benchmark-seed --apply"),
    ("benchmark-seed", "--from-girder=user/christian/Public",
     "benchmark-seed --from-girder=user/christian/Public"),
    ("benchmark-seed --apply",
     "--from-girder=user/christian/Public --from-girder-file=ImageCAS__0855_seg.nii.gz",
     "benchmark-seed --from-girder=user/christian/Public "
     "--from-girder-file=ImageCAS__0855_seg.nii.gz --apply"),
    ("benchmark-create", "--imagecas-id=1", "benchmark-create --imagecas-id=1"),
    ("benchmark-create --apply", "--imagecas-id=1 --replace",
     "benchmark-create --imagecas-id=1 --replace --apply"),
    ("benchmark-assign --apply", "--exclude=a,b --retest",
     "benchmark-assign --exclude=a,b --retest --apply"),
    ("quality-report", "", "quality-report"),
    ("quality-report", "--limit=0", "quality-report --limit=0"),
    ("quality-report", "--limit=500", "quality-report --limit=500"),
    ("quality-report", "--exclude=christian", "quality-report --exclude=christian"),
    ("quality-report", "--exclude=a.b,c_d,e-1", "quality-report --exclude=a.b,c_d,e-1"),
    ("quality-report", "--limit=5 --exclude=a,b", "quality-report --limit=5 --exclude=a,b"),
    ("quality-report", "--exclude=a,b --limit=5", "quality-report --exclude=a,b --limit=5"),
    # #315: one login and one date, in either order; --apply from the step only.
    ("reopen", "--login=ryoplacv --submitted-before=2026-11-09",
     "reopen --login=ryoplacv --submitted-before=2026-11-09"),
    ("reopen --apply", "--submitted-before=2026-11-09 --login=ryoplacv",
     "reopen --submitted-before=2026-11-09 --login=ryoplacv --apply"),
])
def test_accepted(tmp_path, command, args, expected):
    code, cmd, log = _which(tmp_path, command, args)
    assert code == 0, log
    assert cmd == expected


@pytest.mark.parametrize("command,args,why", [
    ("benchmark-seed", "--from-girder=user/x;rm -rf ~", "only Girder paths"),
    ("benchmark-seed", "--from-girder='user/x'", "only Girder paths"),
    ("benchmark-seed", "--from-girder=user/$(id)", "only Girder paths"),
    ("benchmark-seed", "--from-girder=user/x/*", "only Girder paths"),
    ("benchmark-seed", "--from-girder=user/x --apply", "is not --from-girder"),
    ("benchmark-seed", "--seed-file=/etc/passwd", "is not --from-girder"),
    ("benchmark-seed", "--from-girder=", "is not --from-girder"),
    ("benchmark-seed", "--from-girder=user/../x", "'..'"),
    ("benchmark-seed", "--from-girder-file=x.nii.gz", "need --from-girder"),
    ("benchmark-create", "--from-girder=x", "is not --imagecas-id"),
    ("benchmark-create", "--imagecas-id=1;id", "may hold only --imagecas-id"),
    ("benchmark-create", "--imagecas-id=*", "may hold only --imagecas-id"),
    ("benchmark-create", "--imagecas-id=1x", "takes 1 to 4 digits"),
    ("benchmark-create", "--imagecas-id=00001", "takes 1 to 4 digits"),
    ("benchmark-create", "--imagecas-id=", "takes 1 to 4 digits"),
    ("benchmark-create", "--imagecas-id=$(id)", "may hold only --imagecas-id"),
    ("benchmark-create", "--replace", "need --imagecas-id"),
    ("benchmark-status", "--imagecas-id=1", "only benchmark-assign, benchmark-seed,"),
    ("quality-report --apply", "", "unknown step"),
    ("quality-report", "--limit=5 --json", "only --limit="),
    ("quality-report", "--limit=1;id", "only --limit="),
    ("quality-report", "--limit=$(id)", "only --limit="),
    ("quality-report", "--limit=", "only --limit="),
    ("quality-report", "--limit=123456", "only --limit="),
    ("quality-report", "--apply", "only --limit="),
    ("quality-report", "--exclude=", "only --limit="),
    ("quality-report", "--exclude=a,", "only --limit="),
    ("quality-report", "--exclude=,a", "only --limit="),
    ("quality-report", "--exclude=a,,b", "only --limit="),
    ("quality-report", "--exclude=Anna", "only --limit="),
    ("quality-report", "--exclude=a;id", "only --limit="),
    ("quality-report", "--exclude=$(id)", "only --limit="),
    ("quality-report", "--exclude=a b", "only --limit="),
    ("quality-report", "--exclude=a --exclude=b", "only --limit="),
    ("quality-report", "--limit=1 --limit=2", "only --limit="),
    ("quality-report", "--limit=1 --exclude=a --json", "only --limit="),
    ("quality-report", "--exclude=a --apply", "only --limit="),
    ("benchmark-assign", "--exclude=a/b", "only logins"),
    ("benchmark-assign", "--from-girder=x", "is not --exclude"),
    ("benchmark-assign", "", "needs args"),
    ("reopen", "", "reopen needs args"),
    ("reopen --apply", "", "reopen needs args"),
    ("reopen", "--login=ryoplacv", "exactly --login="),
    ("reopen", "--submitted-before=2026-11-09", "exactly --login="),
    ("reopen", "--login=a,b --submitted-before=2026-11-09", "exactly --login="),
    ("reopen", "--login=a --login=b --submitted-before=2026-11-09", "exactly --login="),
    ("reopen", "--login=Anna --submitted-before=2026-11-09", "exactly --login="),
    ("reopen", "--login=$(id) --submitted-before=2026-11-09", "exactly --login="),
    ("reopen", "--login=a;id --submitted-before=2026-11-09", "exactly --login="),
    ("reopen", "--login=a --submitted-before=2026-11-9", "exactly --login="),
    ("reopen", "--login=a --submitted-before=11/09/2026", "exactly --login="),
    ("reopen", "--login=a --submitted-before=2026-11-09 --apply", "exactly --login="),
    ("reopen", "--login=a  --submitted-before=2026-11-09", "exactly --login="),
    ("reopen --dry-run", "--login=a --submitted-before=2026-11-09", "unknown step"),
])
def test_refused(tmp_path, command, args, why):
    code, cmd, log = _which(tmp_path, command, args)
    assert code != 0 and cmd is None
    assert why in log, log
