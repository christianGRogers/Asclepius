"""The wire contract. These tests exist to make a breaking change loud."""

import json

import pytest

from segqueue import PROTOCOL_VERSION
from segqueue.protocol import (
    API_PREFIX,
    CASE_SUBMIT,
    ERR_AT_LIMIT,
    ERR_CLIENT_TOO_OLD,
    ERR_QUEUE_EMPTY,
    MIN_CLIENT_PROTOCOL,
    NEXT,
    REVIEW_VERDICT,
    AssignmentInfo,
    ProjectConfig,
    ProtocolError,
    SegmentSpec,
    SubmissionMeta,
    check_client_protocol,
    error_body,
    parse_error,
    path,
)


def test_paths_are_rendered_under_the_api_prefix():
    assert path(NEXT) == "segqueue/next"
    assert path(CASE_SUBMIT, assignment_id="abc123") == "segqueue/assignment/abc123/submit"
    assert path(REVIEW_VERDICT, submission_id="s1") == "segqueue/review/s1/verdict"
    assert path(NEXT).startswith(API_PREFIX)


def test_a_missing_path_parameter_fails_loudly():
    with pytest.raises(KeyError):
        path(CASE_SUBMIT)


# --------------------------------------------------------------- round trips


def test_segment_spec_round_trips():
    spec = SegmentSpec("left_main", 1, (1.0, 0.2, 0.0), required=False, hint="short vessel")
    again = SegmentSpec.from_dict(json.loads(json.dumps(spec.to_dict())))
    assert again == spec


def test_segment_spec_fills_in_sensible_defaults():
    spec = SegmentSpec.from_dict({"name": "lad", "label": "2"})
    assert spec.label == 2
    assert spec.required is True
    assert len(spec.color) == 3


def test_project_config_round_trips_with_its_segments():
    config = ProjectConfig(
        name="Coronary phase 1",
        instructions="Segment the four major branches.",
        segments=[SegmentSpec("left_main", 1), SegmentSpec("rca", 4, required=False)],
        max_concurrent=2,
        quota_remaining=50,
    )
    again = ProjectConfig.from_dict(json.loads(json.dumps(config.to_dict())))
    assert again.name == config.name
    assert [s.name for s in again.segments] == ["left_main", "rca"]
    assert again.max_concurrent == 2
    assert again.quota_remaining == 50
    assert [s.name for s in again.required_segments()] == ["left_main"]


def test_an_uncapped_quota_survives_the_round_trip_as_none():
    """None and 0 mean opposite things; JSON must not blur them."""
    config = ProjectConfig(quota_remaining=None)
    assert ProjectConfig.from_dict(config.to_dict()).quota_remaining is None
    exhausted = ProjectConfig(quota_remaining=0)
    assert ProjectConfig.from_dict(exhausted.to_dict()).quota_remaining == 0


def test_assignment_info_round_trips():
    info = AssignmentInfo(
        assignment_id="a1", case_id="c1", case_name="case-0042",
        state="downloaded", attempt=2, size_bytes=314_572_800,
        checksum="deadbeef" * 8, assigned_at=1700.0, deadline=2300.0,
        reviewer_comment="LCX stops short of the obtuse marginal.",
    )
    again = AssignmentInfo.from_dict(json.loads(json.dumps(info.to_dict())))
    assert again == info


def test_blind_means_blind():
    """An annotator's payload must not carry the gold/duplicate flavour."""
    annotator_view = AssignmentInfo(assignment_id="a1", case_id="c1").to_dict()
    assert "kind" not in annotator_view

    admin_view = AssignmentInfo(assignment_id="a1", case_id="c1", kind="gold").to_dict()
    assert admin_view["kind"] == "gold"


def test_submission_meta_round_trips():
    meta = SubmissionMeta(
        checksum="a" * 64, size_bytes=2_000_000, annotation_seconds=1834.5,
        voxel_counts={"left_main": 812}, slicer_version="5.8.1",
        extension_version="0.1.0", annotator_note="distal RCA poorly opacified",
    )
    again = SubmissionMeta.from_dict(json.loads(json.dumps(meta.to_dict())))
    assert again == meta


def test_readers_ignore_fields_they_do_not_know():
    """Adding a response field must never break a deployed extension."""
    payload = AssignmentInfo(assignment_id="a1").to_dict()
    payload["somethingAddedNextSemester"] = {"nested": True}
    assert AssignmentInfo.from_dict(payload).assignment_id == "a1"

    config = ProjectConfig().to_dict()
    config["newKnob"] = 7
    assert ProjectConfig.from_dict(config).max_concurrent == 1


# -------------------------------------------------------------------- errors


def test_error_bodies_round_trip_into_protocol_errors():
    body = error_body(ERR_QUEUE_EMPTY, "Nothing left to hand out.", retryAfter=300)
    err = parse_error(json.loads(json.dumps(body)))
    assert isinstance(err, ProtocolError)
    assert err.code == ERR_QUEUE_EMPTY
    assert str(err) == "Nothing left to hand out."
    assert err.detail["retryAfter"] == 300


def test_a_refusal_wrapped_by_girder_is_still_recognised():
    """Girder nests a RestException's payload under "extra"; that is the shape
    the client actually receives on the wire."""
    err = parse_error({
        "message": "You already hold a case.",
        "type": "rest",
        "extra": error_body(ERR_AT_LIMIT, "You already hold a case.", maxConcurrent=1),
    })
    assert err is not None
    assert err.code == ERR_AT_LIMIT
    assert err.detail["maxConcurrent"] == 1
    assert str(err) == "You already hold a case."


def test_an_ordinary_girder_error_is_not_mistaken_for_ours():
    assert parse_error({"message": "Access denied.", "type": "access"}) is None
    assert parse_error("not even a dict") is None
    assert parse_error(None) is None


# ----------------------------------------------------- version negotiation


def test_a_current_client_is_accepted():
    check_client_protocol(PROTOCOL_VERSION)


def test_a_client_that_sends_no_version_is_accepted():
    """The first release sent no header; refusing it would strand real users."""
    check_client_protocol(None)


def test_a_client_below_the_minimum_is_told_how_to_fix_it():
    with pytest.raises(ProtocolError) as excinfo:
        check_client_protocol(MIN_CLIENT_PROTOCOL - 1)
    err = excinfo.value
    assert err.code == ERR_CLIENT_TOO_OLD
    assert err.detail["minProtocol"] == MIN_CLIENT_PROTOCOL
    assert "Reinstall" in str(err)


# --------------------------------------------------------- case assets


def test_an_assignment_reports_what_ships_with_the_case():
    info = AssignmentInfo(assignment_id="a1", has_seed=True, has_region=True)
    back = AssignmentInfo.from_dict(info.to_dict())

    assert back.has_seed and back.has_region
    # Safe to expose, unlike `kind`: these are properties of the source data,
    # not of the assignment, so they leak nothing about gold or duplicate status.
    assert back.kind is None


def test_a_case_with_no_extras_says_so_rather_than_omitting_the_field():
    # An older server that omits the keys must read as "no extras", not as a
    # crash and not as "yes" -- the client branches on these to decide whether
    # to spend a round trip fetching a mask that does not exist.
    back = AssignmentInfo.from_dict({"assignmentId": "a1"})
    assert back.has_seed is False
    assert back.has_region is False


def test_the_asset_route_is_built_from_the_kind():
    from segqueue.protocol import ASSET_KINDS, ASSET_REGION, ASSET_SEED, CASE_ASSET

    assert path(CASE_ASSET, case_id="c1", kind=ASSET_SEED) == "segqueue/case/c1/asset/seed"
    assert path(CASE_ASSET, case_id="c1", kind=ASSET_REGION) \
        == "segqueue/case/c1/asset/region"
    assert set(ASSET_KINDS) == {ASSET_SEED, ASSET_REGION}


def test_the_helper_segment_names_cannot_collide_with_a_project_segment():
    """The scene's scaffolding must never be mistaken for a vessel.

    Checked against the coronary label set itself rather than a copy, because
    that file is what `segtrain convert` reads: if a helper name ever became a
    structure name, the dataset's own coronary mask could be submitted as
    though a student had drawn it, and every dashboard number would look fine.
    """
    from pathlib import Path

    import yaml

    from segqueue.protocol import REGION_SEGMENT_NAME, SEED_SEGMENT_NAME

    labels = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "configs" / "labels" / "coronary.yaml")
        .read_text(encoding="utf-8-sig"))
    structures = set(labels["labels"])
    assert "left_main" in structures  # the file is the one we think it is

    for name in (SEED_SEGMENT_NAME, REGION_SEGMENT_NAME):
        assert name not in structures
        # Prefixed so they sort together and read as scaffolding. The export
        # excludes them structurally, but a name that looked like anatomy would
        # still invite somebody to "fix" it.
        assert name.startswith("~")


def test_an_assignment_carries_the_volumes_real_filename():
    # The client names its local copy from this before downloading, so it can
    # tell whether the case is already cached -- and Slicer chooses its reader
    # from the extension, so getting it wrong makes a perfectly transferred file
    # unopenable.
    info = AssignmentInfo(assignment_id="a1", volume_name="s0004.nii.gz")
    assert AssignmentInfo.from_dict(info.to_dict()).volume_name == "s0004.nii.gz"


def test_a_server_that_omits_the_filename_reads_as_blank():
    assert AssignmentInfo.from_dict({"assignmentId": "a1"}).volume_name == ""
