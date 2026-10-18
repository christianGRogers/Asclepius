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
    assert not any(seal.is_sealed(p) for p in seal.extension_order)


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
