"""The D27 pool seal: the canonical file is pinned; the loader seals by volume and by patient."""

import hashlib
import json
import logging
from pathlib import Path

import pytest

from segtrain import pool_seal
from segtrain.pool_seal import SealedPoolError, apply, load_pool_seal

REPO = Path(__file__).resolve().parents[1]
SEAL = REPO / "configs" / "segqueue14" / "sealed-pool-2026-10.json"
BRIDGE = REPO / "experiments" / "Bridge" / "r9" / "sealed_pool_proposal.json"
#: Pinned here as well as in the module: changing the seal takes an edit in both.
PINNED = "8f529842934bfb72883a7da593b128ad6c091aecb8228005e9792cd8d92c1183"


@pytest.fixture(scope="module")
def seal():
    return load_pool_seal(SEAL)


@pytest.fixture(scope="module")
def data():
    return json.loads(SEAL.read_text(encoding="utf-8"))


def test_seal_file_is_pinned_and_is_bridges_proposal():
    assert hashlib.sha256(SEAL.read_bytes()).hexdigest() == PINNED
    assert pool_seal.SEAL_SHA256 == PINNED
    assert SEAL.read_bytes() == BRIDGE.read_bytes()


def test_seal_contents_match_d27(seal, data):
    assert data["primary"]["n_patients"] == 150 and data["primary"]["n_volumes"] == 216
    assert data["report_only"]["n_patients"] == 20
    assert len(seal.patients) == 170
    assert len(seal.volumes) == 216 + len(data["report_only"]["volumes"])
    assert len(seal.report_only_patients) == 20
    # The extension order is carried, not sealed: extending is a later, explicit change.
    assert len(seal.extension_order) == 150
    # ... except the extension candidates the ingest groups with a sealed patient (#87)
    grouped = [p for p in seal.extension_order if pool_seal.ingest_patient(p)
               in seal.ingest_patients]
    assert {p for p in seal.extension_order if seal.is_sealed(p)} == set(grouped)
    assert len(grouped) == 31          # reported to the PM on #84


def test_default_path_finds_the_checkout_file(monkeypatch):
    monkeypatch.delenv(pool_seal.SEAL_ENV, raising=False)
    assert pool_seal.default_path() == SEAL
    assert load_pool_seal().sha256 == PINNED


def test_missing_or_altered_seal_is_an_error(tmp_path, monkeypatch):
    with pytest.raises(FileNotFoundError):
        load_pool_seal(tmp_path / "nope.json")
    monkeypatch.setenv(pool_seal.SEAL_ENV, str(tmp_path / "nope.json"))
    with pytest.raises(FileNotFoundError):
        load_pool_seal()
    altered = tmp_path / "seal.json"
    altered.write_bytes(SEAL.read_bytes() + b"\n")
    with pytest.raises(SealedPoolError, match="sha256"):
        load_pool_seal(altered)


def test_every_name_a_sealed_volume_travels_under(seal, data):
    vol = data["primary"]["volumes"][0]
    stem = vol[: -len(".nii.gz")]
    for name in (vol, stem, f"{stem}__r2", f"{stem}_0000.nii.gz", f"/x/cases/{vol}",
                 f"imagesTr/{stem}_0000.nii.gz", f"{stem}.seg.nrrd"):
        assert seal.is_sealed(name), name


def test_every_volume_of_a_sealed_patient_is_sealed(seal, data):
    multi = data["multi_volume_patients"]
    sealed_multi = [p for p in multi if p in seal.patients]
    assert sealed_multi
    for p in sealed_multi:
        assert all(seal.is_sealed(v) for v in multi[p])
    # A volume of a sealed patient that is not in the pool list is still sealed.
    pat = next(p for p in data["primary"]["patients"] if "CardiacCT15" in p)
    assert seal.is_sealed(f"{pat}_tp9.nii.gz")
    for p in data["report_only"]["patients"]:
        assert seal.is_sealed(p)


def test_unsealed_names_pass(seal, data):
    pool = [ln.strip() for ln in (REPO / data["pool_list"]).read_text().splitlines()
            if ln.strip() and not ln.startswith("#")]
    open_ = [v for v in pool if not seal.is_sealed(v)]
    assert len(pool) - len(open_) == len(seal.volumes) + 60      # + the A30 grouping QC
    for name in ("c0002", "imagecas_0003", "c0002__r2", data["primary"]["extension_order"][0]):
        assert not seal.is_sealed(name)


def test_apply_modes(seal, data, caplog):
    sealed = data["primary"]["volumes"][0]
    names = ["c0001", sealed, "imagecas_0002"]
    assert apply(["c0001"], seal=seal) == ["c0001"]
    with pytest.raises(SealedPoolError, match="1 of 3"):
        apply(names, seal=seal, what="convert")
    with caplog.at_level(logging.WARNING, logger="segtrain.pool_seal"):
        assert apply(names, mode="exclude", seal=seal) == ["c0001", "imagecas_0002"]
        assert apply(names, mode="acceptance", seal=seal) == names
    assert "excluded 1 sealed" in caplog.text and "ACCEPTANCE" in caplog.text
    with pytest.raises(ValueError):
        apply(names, mode="drop", seal=seal)


# ---------------------------------------------------- A30 grouping QC (#87): refuse by patient
def _pool(data):
    return [ln.strip() for ln in (REPO / data["pool_list"]).read_text().splitlines()
            if ln.strip() and not ln.startswith("#")]


def test_unlisted_volumes_of_sealed_sdn_and_slicer_patients_are_refused(seal, data):
    listed = set(data["primary"]["volumes"]) | set(data["report_only"]["volumes"])
    # an SDN record is one patient: any other series of a sealed record is sealed
    sdn = next(v for v in _pool(data) if v.startswith("Mendeley-SDN-spb25zt2c4__")
               and v not in listed)
    assert seal.is_sealed(sdn)
    assert seal.is_sealed("Mendeley-SDN-spb25zt2c4__s999_f03.nii.gz")
    # a Slicer sequence is one patient: any frame of a sealed sequence is sealed
    frame = next(v for v in _pool(data) if v.startswith("Slicer-SampleData__TruncalValve_4DCT_f")
                 and v not in listed)
    assert seal.is_sealed(frame)
    assert seal.is_sealed("Slicer-SampleData__TruncalValve_4DCT_f20__r2")
    assert "ingest patient id" in seal.reason(frame)
    # cy54ttk3fj holds 40 patients: an unsealed one stays open
    open_ = [v for v in _pool(data) if v.startswith("Mendeley-SDN-cy54ttk3fj__")
             and v not in listed]
    assert open_ and not any(seal.is_sealed(v) for v in open_)


def test_patient_grouping_seals_exactly_the_sixty_unlisted_pool_volumes(seal, data):
    listed = set(data["primary"]["volumes"]) | set(data["report_only"]["volumes"])
    extra = [v for v in _pool(data) if v not in listed and seal.is_sealed(v)]
    assert len(extra) == 60
    groups = {pool_seal.ingest_patient(v[: -len(".nii.gz")]) for v in extra}
    assert groups == {"Mendeley-SDN-37nnfyh3x9", "Mendeley-SDN-4643nn2z44",
                      "Mendeley-SDN-spb25zt2c4", "Mendeley-SDN-7x9kb53262",
                      "Slicer-SampleData__CTCardioSeq", "Slicer-SampleData__TruncalValve_4DCT"}


def test_ingest_rules_match_the_ingest_code():
    """The SDN single-patient records and the Slicer source name are the ingest's own."""
    import ast

    tree = ast.parse((REPO / "tools" / "ccta" / "ingest_open.py").read_text(encoding="utf-8"))
    sdn = slicer_source = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "SDN_CASES"
                                                for t in node.targets):
            sdn = {k.value for k in node.value.keys}
        if (isinstance(node, ast.FunctionDef) and node.name == "run_slicer"):
            call = next(n for n in ast.walk(node) if isinstance(n, ast.Call)
                        and getattr(n.func, "id", "") == "Sink")
            slicer_source = call.args[1].value
    assert sdn == set(pool_seal.SDN_SINGLE_PATIENT_RECORDS)
    assert slicer_source == pool_seal.SLICER_SOURCE
