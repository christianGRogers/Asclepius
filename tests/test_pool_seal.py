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
PINNED = "e71141b407acb79eeff912eee21029d34edb677d984172d871eb5f02cb1d0690"


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
    # D32: 150 real patients (ingest ids, D33 merged); every volume of each is listed
    assert data["primary"]["n_patients"] == 150 and data["primary"]["n_volumes"] == 305
    assert data["report_only"]["n_patients"] == 20
    assert len(seal.patients) == 170
    assert len(seal.volumes) == 305 + len(data["report_only"]["volumes"])
    assert len(seal.report_only_patients) == 20
    assert len(data["d32"]["added_from_extension_order"]) == 17
    # The extension order is carried, not sealed: extending is a later, explicit change.
    # Since D32 it holds real patients only, none of them sealed.
    assert len(seal.extension_order) == 101
    assert not any(seal.is_sealed(p) for p in seal.extension_order)
    assert len(set(seal.extension_order)) == 101


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
    # D32: no sealed patient has a volume outside the file
    assert len(pool) - len(open_) == len(seal.volumes)
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
    # an SDN record is one patient: a series not in the file is still sealed (by ingest patient)
    assert "Mendeley-SDN-spb25zt2c4__s999_f03.nii.gz" not in listed
    assert seal.is_sealed("Mendeley-SDN-spb25zt2c4__s999_f03.nii.gz")
    # a Slicer sequence is one patient: any frame of a sealed sequence is sealed
    frame = "Slicer-SampleData__TruncalValve_4DCT_f20__r2"
    assert seal.is_sealed(frame)
    assert "ingest patient id" in seal.reason(frame)
    # cy54ttk3fj holds 40 patients: an unsealed one stays open
    open_ = [v for v in _pool(data) if v.startswith("Mendeley-SDN-cy54ttk3fj__")
             and v not in listed]
    assert open_ and not any(seal.is_sealed(v) for v in open_)


def test_d32_every_pool_volume_of_a_sealed_patient_is_listed(seal, data):
    """D32: the A30 QC's 60 unlisted volumes (and D33's RIDER twin) are now in the file."""
    listed = set(data["primary"]["volumes"]) | set(data["report_only"]["volumes"])
    assert [v for v in _pool(data) if v not in listed and seal.is_sealed(v)] == []
    six = {"Mendeley-SDN-37nnfyh3x9", "Mendeley-SDN-4643nn2z44", "Mendeley-SDN-spb25zt2c4",
           "Mendeley-SDN-7x9kb53262", "Slicer-SampleData__CTCardioSeq",
           "Slicer-SampleData__TruncalValve_4DCT"}
    assert six <= set(data["primary"]["patients"])
    for v in _pool(data):
        if pool_seal.ingest_patient(v[: -len(".nii.gz")]) in six:
            assert v in listed, v


def test_d33_rider_pair_is_one_sealed_patient(seal, data):
    twin = "IDC-rider_lung_pet_ct__RIDER-2551730224"
    assert pool_seal.ingest_patient(twin + "__x") == "IDC-rider_lung_pet_ct__RIDER-2522924559"
    assert twin not in data["primary"]["extension_order"]
    assert any(v.startswith(twin + "__") for v in data["primary"]["volumes"])
    assert seal.is_sealed(twin + "__new-series.nii.gz")


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
