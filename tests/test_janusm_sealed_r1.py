"""JA6 (issue #140): the frozen Janus-M seal and decision set.

The committed file is pinned, it is reproduced byte for byte from Juliet's committed draw
script on the committed splits.json, and no drawn case is in any coronary hold-out.
"""

import glob
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_SRC = REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.append(str(_SRC))

from janusm import sealed_r1  # noqa: E402
from segtrain.pool_seal import load_pool_seal  # noqa: E402

FILE = REPO / sealed_r1.PATH
D = json.loads(FILE.read_text())
DRAWN = set(D["seal"]) | set(D["decision"]) | set(D["jm0"]) | set(D["seal_extension"])


def test_file_is_pinned():
    assert hashlib.sha256(FILE.read_bytes()).hexdigest() == sealed_r1.SEALED_R1_SHA256
    assert sealed_r1.load().sha256 == sealed_r1.SEALED_R1_SHA256


def test_splits_hash_is_the_ja6_one():
    digest = hashlib.sha256((REPO / sealed_r1.SPLITS).read_bytes()).hexdigest()
    assert digest.startswith(sealed_r1.SPLITS_SHA256_PREFIX)
    assert D["splits_sha256"] == digest


def test_draw_script_hash_recorded():
    assert D["draw_script_sha256"] == hashlib.sha256(
        (REPO / sealed_r1.DRAW_SCRIPT).read_bytes()).hexdigest()


def test_draw_is_reproduced_from_the_committed_script():
    assert sealed_r1.dumps(sealed_r1.build()) == FILE.read_text()


def test_sizes_and_disjoint_lists():
    assert [len(D[k]) for k in ("seal", "decision", "jm0", "seal_extension")] == [60, 40, 40, 60]
    assert len(DRAWN) == 200
    train = set(json.loads((REPO / sealed_r1.SPLITS).read_text())["train"])
    assert DRAWN <= train


def test_extension_is_the_seal_salt_continuation():
    train = json.loads((REPO / sealed_r1.SPLITS).read_text())["train"]
    ranked = sealed_r1._rank(train, sealed_r1.SEAL_SALT)
    assert set(ranked[:60]) == set(D["seal"])
    taken = set(D["seal"]) | set(D["decision"]) | set(D["jm0"])
    assert D["seal_extension"] == [c for c in ranked[60:] if c not in taken][:60]


def test_load_refuses_a_changed_file(tmp_path):
    bad = tmp_path / "sealed-r1.json"
    d = dict(D, seal=D["seal"][:-1])  # a shrunk seal
    bad.write_text(sealed_r1.dumps(d))
    with pytest.raises(sealed_r1.JanusMSealError, match="sha256"):
        sealed_r1.load(bad)
    with pytest.raises(sealed_r1.JanusMSealError, match="missing"):
        sealed_r1.load(tmp_path / "nope.json")


# ------------------------------------------------------------------ zero overlap with hold-outs
def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)


def test_no_drawn_case_is_an_imagecas_holdout():
    s = json.loads((REPO / "trillium/icx4/sealed_test.json").read_text())
    splits = json.loads((REPO / sealed_r1.SPLITS).read_text())
    held = {
        "A14 sealed 100": set(s["sealed_icx_test"]) | set(s["sealed_quality0"]),
        "ImageCAS-X test split": set(splits["test"]) | set(s["open_icx_test"])
        | set(s["excluded_dev_cases_in_test"]),
        "val 80": set(splits["val"]),
        "declared dev cases": set(s["declared_dev_cases"]),
    }
    assert len(held["val 80"]) == 80
    for name, ids in held.items():
        assert not DRAWN & ids, name


_D35 = glob.glob(str(REPO / "experiments/*/r10*/*decision*proposal*.json"))
POOL_FILES = ["configs/segqueue14/sealed-pool-2026-10.json"] + sorted(
    {str(Path(p).relative_to(REPO)) for p in _D35}
    | {"experiments/Delta/r10/d35_decision_set_proposal.json"})


@pytest.mark.parametrize("rel", POOL_FILES)
def test_no_drawn_case_is_in_the_pool_seal_reserve_or_a_d35_draw(rel):
    """The pool seal (primary, report-only), its extension order (the reserve) and every D35
    draw name pool volumes; no drawn ImageCAS id appears in them, alone or as a case part."""
    names = set(_strings(json.loads((REPO / rel).read_text())))
    tokens = {t for n in names for t in re.split(r"[^A-Za-z0-9]+", n)}
    assert not DRAWN & (names | tokens)


def test_no_drawn_case_is_refused_by_the_pool_seal_guard():
    seal = load_pool_seal()
    assert not [c for c in DRAWN if seal.is_sealed(c)]


def test_skipped_ranks_are_decision_or_jm0_cases():
    assert len(D["seal_extension_skipped"]) == 7
    assert set(D["seal_extension_skipped"]) <= set(D["decision"]) | set(D["jm0"])


# ------------------------------------------------------------------ wired into the JA12 guard
def test_the_guard_pins_and_refuses_the_frozen_file():
    from janusm import guard as G

    assert G.JANUSM_SEAL_RELPATH == sealed_r1.PATH
    assert G.JANUSM_SEAL_SHA256 == sealed_r1.SEALED_R1_SHA256
    g = G.load_guard()
    src = "ImageCAS-X"
    seal, ext, dec, jm0 = (D[k][0] for k in ("seal", "seal_extension", "decision", "jm0"))
    for case in D["seal"] + D["seal_extension"]:
        assert "seal case" in g.reason(case, src)
        assert "seal case" in g.reason(case, src, purpose=G.DECISION_SCORING)
        assert g.reason(case, src, purpose=G.SEAL_SCORING) is None
    for case in D["decision"]:
        assert "decision case" in g.reason(case, src)
        assert "decision case" in g.reason(case, src, purpose=G.SEAL_SCORING)
        assert g.reason(case, src, purpose=G.DECISION_SCORING) is None
    assert not [c for c in D["jm0"] if g.reason(c, src)]     # JM-0 is not held out
    with pytest.raises(G.HeldOutError, match="1 of 2"):
        G.refuse([jm0, seal], what="a Janus-M training run", source=src)
    assert G.refuse([seal, ext], source=src, purpose=G.SEAL_SCORING) == [seal, ext]
    assert G.refuse([dec], source=src, purpose=G.DECISION_SCORING) == [dec]
