"""JA12: the one Janus-M held-out guard (issue #138).

Positive controls from the issue, the pins (a changed, missing or unpinned list fails), the JA6
purpose rule (#140 hook), and the comparison with the five Round 1 prototypes it replaces.
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
for p in (REPO / "src", REPO / "tools" / "janusm"):
    if str(p) not in sys.path:
        sys.path.append(str(p))

from janusm import guard as G  # noqa: E402
from janusm.guard import (  # noqa: E402
    DECISION_SCORING,
    SEAL_SCORING,
    GuardInputError,
    HeldOutError,
    load_guard,
    refuse,
)

SEAL = json.loads((REPO / G.SEAL_RELPATH).read_text())
A14 = json.loads((REPO / G.A14_RELPATH).read_text())
DELTA = json.loads((REPO / "experiments/Delta/r10/d35_decision_set_proposal.json").read_text())


@pytest.fixture(scope="module")
def g():
    return load_guard()


# ------------------------------------------------------------------ positive controls (#138)
@pytest.mark.parametrize("name,source,why", [
    ("TotalSegmentator-cardiac__s0655", None, "pool seal"),
    ("TotalSegmentator-cardiac__s0655.nii.gz", None, "pool seal"),
    ("s0655", "TotalSegmentator", "pool seal"),                     # public copy, bare id
    ("Totalsegmentator_dataset/s0655/ct.nii.gz", None, "pool seal"),  # public copy, path
    ("TotalSegmentator-v1__s0655", None, "pool seal"),
    ("s0356", "TotalSegmentator", "reserve"),
    ("c0002", "ImageCAS-X", "A14 sealed 100"),
    ("c0002", None, "A14 sealed 100"),
    ("3", "ImageCAS", "A14 sealed 100"),                            # ImageCAS id 3 = c0002
    ("ImageCAS__3.img.nii.gz", None, "A14 sealed 100"),
    ("c0001", "ImageCAS-X", "val 80"),
    (A14["open_icx_test"][0], "ImageCAS-X", "test split"),
    ("PLOS-Peng2016-CCTA-JPEG__P01.nii.gz", None, "PLOS-Peng2016"),
    ("s0019", "TotalSegmentator", "twin"),
])
def test_positive_controls_are_refused(g, name, source, why):
    r = g.reason(name, source=source)
    assert r and why in r, (name, r)


def test_a_reserve_patient_is_refused(g):
    p = SEAL["primary"]["extension_order"][0]
    assert not g.seal.is_sealed(p)           # the reserve is not the seal itself
    assert "reserve" in g.reason(p)
    assert "reserve" in g.reason(p + "_0000.nii.gz")


def test_a_d35_patient_and_its_volumes_are_refused(g):
    p = next(x for x in DELTA["patients"] if not g.seal.is_sealed(x))
    assert g.reason(p)
    for v in DELTA["volumes"]:
        assert g.reason(v), v


def test_a_second_volume_of_a_sealed_patient_is_refused(g):
    # D33: RIDER-2551730224 is the same person as sealed RIDER-2522924559; any new series of
    # either is that patient.
    assert "IDC-rider_lung_pet_ct__RIDER-2522924559" in g.seal.patients
    for v in ("IDC-rider_lung_pet_ct__RIDER-2522924559_s7",
              "IDC-rider_lung_pet_ct__RIDER-2551730224_s9.nii.gz"):
        assert "pool seal" in g.reason(v), v
    # every listed volume of every multi-volume sealed patient
    for v in SEAL["primary"]["volumes"] + SEAL["report_only"]["volumes"]:
        assert g.reason(v), v


def test_every_pool_totalsegmentator_subject_is_held_out(g):
    pool = (REPO / "configs/segqueue14/pool-2026-10.txt").read_text()
    ids = {ln.split("__")[1][:5] for ln in pool.splitlines() if ln.startswith("TotalSegmentator")}
    assert len(ids) == 16 and ids == set(g.ts_held_out)


# ------------------------------------------------------------------ negatives
def test_allowed_cases_pass(g):
    assert g.reason("c0000", source="ImageCAS-X") is None            # ImageCAS-X train
    assert g.reason("1", source="ImageCAS") is None                  # = c0000
    assert g.reason("s0000", source="TotalSegmentator") is None      # not a twin
    # Trainable in Foxtrot's and Atlas's draws and drawn by no other: Golf refused it, JA12 not.
    assert g.reason("Taiwan-AICUP-CardiacCT__patient0013") is None
    # A trainable list in one draw does not release a patient another draw holds out.
    assert "D35" in g.reason("Taiwan-AICUP-CardiacCT__patient0001")
    assert g.reason("some-unrelated-file.nii.gz") is None


def test_refuse_stops_the_whole_run_and_names_every_hit():
    ok = ["c0000", "c0005"]                              # train, in no Janus-M held-out list
    assert refuse(ok, source="ImageCAS-X") == ok
    with pytest.raises(HeldOutError) as e:
        refuse(["c0000", "c0002", "c0001"], what="a test run", source="ImageCAS-X")
    msg = str(e.value)
    assert "2 of 3" in msg and "c0002" in msg and "c0001" in msg and "a test run" in msg


def test_cli_exit_code(capsys):
    assert G.main(["--source", "TotalSegmentator", "s0655"]) == 3
    assert G.main(["c0000"]) == 0
    assert "allowed" in capsys.readouterr().out


# ------------------------------------------------------------------ pins
def _copy_root(tmp_path):
    for rel in list(G.PINNED) + ["configs/segqueue14/pool-2026-10.txt", G.JANUSM_SEAL_RELPATH]:
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, dst)
    return tmp_path


@pytest.mark.parametrize("rel", sorted(G.PINNED) + [G.JANUSM_SEAL_RELPATH])
def test_a_changed_input_list_fails_loudly(tmp_path, rel):
    root = _copy_root(tmp_path)
    load_guard(root)                                     # the copy loads
    root2 = _copy_root(tmp_path / "changed")
    p = root2 / rel
    p.write_bytes(p.read_bytes() + b" ")
    with pytest.raises(HeldOutError):                    # GuardInputError or SealedPoolError
        load_guard(root2)


def test_a_missing_input_or_a_new_draw_file_fails(tmp_path):
    root = _copy_root(tmp_path / "missing")
    (root / G.TWINS_RELPATH).unlink()
    with pytest.raises(GuardInputError, match="not found"):
        load_guard(root)
    root = _copy_root(tmp_path / "newdraw")
    (root / "experiments/Echo/r10").mkdir(parents=True)
    (root / "experiments/Echo/r10/d35_proposal.json").write_text("{}")
    with pytest.raises(GuardInputError, match="unpinned Round 10 draw"):
        load_guard(root)


def test_an_unpinned_janusm_seal_file_fails(tmp_path, monkeypatch):
    root = _copy_root(tmp_path)
    monkeypatch.setattr(G, "JANUSM_SEAL_SHA256", None)
    (root / G.JANUSM_SEAL_RELPATH).write_text("{}")
    with pytest.raises(GuardInputError, match="does not pin it"):
        load_guard(root)


def test_janusm_seal_cases_are_refused_outside_their_scoring_path(tmp_path, monkeypatch):
    """The JA6 hook (#140): seal (and extension) only for seal scoring, decision only for
    decision scoring; a coronary hold-out stays refused for every purpose."""
    import hashlib

    root = _copy_root(tmp_path)
    raw = json.dumps({"seal": ["c0000"], "seal_extension": ["c0003"], "decision": ["c0004"],
                      "jm0": ["c0005"]}).encode()
    (root / G.JANUSM_SEAL_RELPATH).write_bytes(raw)
    monkeypatch.setattr(G, "JANUSM_SEAL_SHA256", hashlib.sha256(raw).hexdigest())
    g = load_guard(root)
    src = "ImageCAS-X"
    assert "seal case" in g.reason("c0000", src)
    assert "seal case" in g.reason("c0003", src)
    assert "decision case" in g.reason("c0004", src)
    assert g.reason("c0000", src, purpose=SEAL_SCORING) is None
    assert "decision case" in g.reason("c0004", src, purpose=SEAL_SCORING)
    assert g.reason("c0004", src, purpose=DECISION_SCORING) is None
    assert "seal case" in g.reason("c0000", src, purpose=DECISION_SCORING)
    assert g.reason("c0005", src) is None
    assert "A14" in g.reason("c0002", src, purpose=SEAL_SCORING)
    with pytest.raises(ValueError):
        g.reason("c0000", src, purpose="training")


def test_the_twin_list_matches_the_held_out_ids(g):
    tw = json.loads((REPO / G.TWINS_RELPATH).read_text())
    assert tw["held_out"] == sorted(g.ts_held_out)
    assert not set(g.ts_twins) & set(g.ts_held_out)


# ------------------------------------------------------------------ Round 1 prototypes
def test_prototypes_refuse_nothing_the_guard_allows_except_trainable_lists():
    """Every Round 1 prototype, run as committed on its own inputs, against the guard. The guard
    is stricter (twins, the ImageCAS splits, PLOS, all five draws). The only names a prototype
    refuses and the guard allows are those the draw files themselves mark trainable (Golf reads
    every name in a draw file)."""
    import compare_prototypes as C

    rep = C.compare()
    trainable = set()
    for rel in G.D35_DRAWS:
        d = json.loads((REPO / rel).read_text())
        for k, v in d.items():
            if k.startswith(G.NOT_HELD_OUT_KEYS):
                trainable |= {n.removesuffix(".nii.gz") for n in G._names_outside(v, skip=())}
    for adv, doms in rep["prototypes"].items():
        for dom, d in doms.items():
            extra = set(d["prototype_stricter"]) - trainable
            assert not extra, (adv, dom, sorted(extra)[:5])
            assert set(d["guard_stricter"]) <= set(C.EXPLAINED), (adv, dom, d["guard_stricter"])
    assert {adv for adv, doms in rep["prototypes"].items()
            if any(d["prototype_stricter"] for d in doms.values())} <= {"Golf"}
