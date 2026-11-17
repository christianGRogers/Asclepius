"""The Slicer self-test workflow runs on Apple silicon (macos-14 retirement).

GitHub retired the macos-14 image on 2026-11-02. Jobs that named it were
cancelled with no runner assigned, so SegQueue14 0.20.0-0.22.0 shipped without
an Apple-silicon Slicer test and nothing went red. These checks keep every macOS
matrix in slicer-selftest.yml on a supported arm64 label next to the Intel one,
and keep the ARM64-only steps (Rosetta) and per-runner artifact names intact.
"""

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
SELFTEST = WORKFLOWS / "slicer-selftest.yml"

#: Apple-silicon (arm64) labels GitHub still serves. macos-14 is gone.
APPLE_SILICON = {"macos-15", "macos-26"}
INTEL = "macos-15-intel"
RETIRED = {"macos-14", "macos-13", "macos-12", "macos-14-large", "macos-14-xlarge"}

MAC_JOBS = ["selftest-macos", "install", "install-anywhere"]


def _jobs():
    return yaml.safe_load(SELFTEST.read_text())["jobs"]


@pytest.mark.parametrize("job", MAC_JOBS)
def test_every_mac_matrix_has_apple_silicon_and_intel(job):
    runners = _jobs()[job]["strategy"]["matrix"]["runner"]
    assert APPLE_SILICON & set(runners), f"{job}: no Apple-silicon runner in {runners}"
    assert INTEL in runners, f"{job}: no Intel Mac runner in {runners}"


@pytest.mark.parametrize("workflow", sorted(WORKFLOWS.glob("*.yml")), ids=lambda p: p.name)
def test_no_workflow_names_a_retired_mac_image(workflow):
    text = workflow.read_text()
    for label in RETIRED:
        # A retired label is cancelled with no runner and no red tick.
        assert f"{label}," not in text and f"{label}]" not in text \
            and f"runs-on: {label}" not in text, f"{workflow.name} names {label}"


@pytest.mark.parametrize("job", MAC_JOBS)
def test_rosetta_still_runs_on_arm64(job):
    steps = _jobs()[job]["steps"]
    rosetta = next(s for s in steps if s.get("name") == "Rosetta")
    assert "runner.arch == 'ARM64'" in rosetta["if"]
    assert "--install-rosetta" in rosetta["run"]


@pytest.mark.parametrize("job", MAC_JOBS)
def test_artifacts_are_named_per_runner(job):
    uploads = [s for s in _jobs()[job]["steps"]
               if str(s.get("uses", "")).startswith("actions/upload-artifact")]
    assert uploads
    for step in uploads:
        assert "${{ matrix.runner }}" in step["with"]["name"]
