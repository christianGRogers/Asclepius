"""The frozen Janus-M seal and decision set, Round 1 (JA6, issue #140).

``configs/janusm/sealed-r1.json`` holds Juliet's committed draw
(``experiments/JanusM/Juliet/fir/draw_m0.py``), run on the committed
``trillium-results/icx14/results/splits.json`` train list, in its order:

1. ``seal``: 60 cases, salt ``asclepius-janusm-seal-r1:``;
2. ``decision``: 40 cases, salt ``asclepius-janusm-decision-r1:``;
3. ``jm0``: 40 cases, salt ``asclepius-janusm-juliet-r1:``.

``seal_extension`` is the pre-registered growth of the seal: the next 60 training cases by
the seal salt, in rank order, skipping any case already in one of the three lists (a decision
or JM-0 case can never become a seal case). The seal grows only from the front of this list,
by an explicit PR that changes the file and :data:`SEALED_R1_SHA256`; it never shrinks after a
read.

Every load checks the pinned hash, so a changed file fails loudly. The JA12 guard
(``janusm.guard``, issue #138) refuses seal cases outside the one scoring path and decision
cases outside decision scoring.

``python -m janusm.sealed_r1 build`` re-runs the draw and prints the file; it must match the
committed one byte for byte (``tests/test_janusm_sealed_r1.py`` checks this).

Standard library only.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PATH = "configs/janusm/sealed-r1.json"
SPLITS = "trillium-results/icx14/results/splits.json"
DRAW_SCRIPT = "experiments/JanusM/Juliet/fir/draw_m0.py"
#: JA6: the committed splits.json must hash to this prefix, else stop.
SPLITS_SHA256_PREFIX = "a53bd426cddc"
SEAL_SALT = "asclepius-janusm-seal-r1:"
N_EXTENSION = 60

#: sha256 of ``configs/janusm/sealed-r1.json``. Changing the file means changing this, by PR.
SEALED_R1_SHA256 = "fda078976d2411de0f3cfabd7a37d4f2c97f4c27a9bca0f15cabb5daa8fda216"


class JanusMSealError(RuntimeError):
    """The frozen Janus-M seal file is missing, changed, or inconsistent."""


@dataclass(frozen=True)
class SealedR1:
    seal: frozenset
    decision: frozenset
    jm0: frozenset
    seal_extension: tuple
    sha256: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path=None) -> SealedR1:
    """Load and verify the frozen file. A missing file or a wrong hash is an error, never a pass."""
    p = Path(path) if path else REPO / PATH
    if not p.is_file():
        raise JanusMSealError(f"{p}: the frozen Janus-M seal is missing; refusing to run")
    digest = _sha256(p)
    if digest != SEALED_R1_SHA256:
        raise JanusMSealError(
            f"{p}: sha256 {digest} is not the pinned Janus-M seal {SEALED_R1_SHA256}; a seal "
            "change is an explicit PR to the file and janusm.sealed_r1.SEALED_R1_SHA256")
    d = json.loads(p.read_text())
    lists = [d["seal"], d["decision"], d["jm0"], d["seal_extension"]]
    flat = [c for lst in lists for c in lst]
    if len(flat) != len(set(flat)):
        raise JanusMSealError(f"{p}: the seal, decision, JM-0 and extension lists overlap")
    return SealedR1(frozenset(d["seal"]), frozenset(d["decision"]), frozenset(d["jm0"]),
                    tuple(d["seal_extension"]), digest)


def _rank(cases, salt):
    return sorted(cases, key=lambda c: hashlib.sha256((salt + c).encode()).hexdigest())


def build(repo: Path = REPO) -> dict:
    """Re-run the committed draw script on the committed splits.json; return the file content."""
    splits = repo / SPLITS
    splits_sha = _sha256(splits)
    if not splits_sha.startswith(SPLITS_SHA256_PREFIX):
        raise JanusMSealError(
            f"{splits}: sha256 {splits_sha} does not start {SPLITS_SHA256_PREFIX} (JA6); stop")
    script = repo / DRAW_SCRIPT
    spec = importlib.util.spec_from_file_location("janusm_draw_m0", script)
    draw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(draw)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "m0_cases.txt"
        stdout, sys.stdout = sys.stdout, sys.stderr  # the script prints counts; keep stdout clean
        try:
            draw.main(str(splits), str(out))
        finally:
            sys.stdout = stdout
        read = lambda name: out.with_name(name).read_text().split()  # noqa: E731
        seal = read("janusm_seal_proposal.txt")
        decision = read("janusm_decision_proposal.txt")
        jm0 = read("m0_cases.txt")
    train = json.loads(splits.read_text())["train"]
    taken = set(seal) | set(decision) | set(jm0)
    ranked = _rank(train, SEAL_SALT)
    if set(ranked[:len(seal)]) != set(seal):
        raise JanusMSealError("the draw script's seal is not the first cases by the seal salt")
    extension = [c for c in ranked[len(seal):] if c not in taken][:N_EXTENSION]
    last = ranked.index(extension[-1])
    skipped = [c for c in ranked[len(seal):last + 1] if c in taken]
    return {
        "what": "Janus-M Round 1 seal and decision set, frozen (JA6, issue #140). Never shrinks "
                "after a read; the seal grows only from the front of seal_extension, by PR. A case "
                "is in exactly one Janus-M set, so seal-salt ranks already drawn as decision or "
                "JM-0 cases are skipped by the extension (listed in seal_extension_skipped).",
        "draw_script": DRAW_SCRIPT,
        "draw_script_sha256": _sha256(script),
        "splits": SPLITS,
        "splits_sha256": splits_sha,
        "drawn_from": "splits.json train",
        "n_train": len(train),
        "salts": {"seal": SEAL_SALT, "decision": "asclepius-janusm-decision-r1:",
                  "jm0": "asclepius-janusm-juliet-r1:"},
        "seal": seal,
        "decision": decision,
        "jm0": jm0,
        "seal_extension_rule": "the next training cases by sha256(seal salt + case), in rank "
                               "order, after the seal's 60, skipping any decision or JM-0 case",
        "seal_extension": extension,
        "seal_extension_skipped": skipped,
    }


def dumps(d: dict) -> str:
    return json.dumps(d, indent=1) + "\n"


if __name__ == "__main__":
    if sys.argv[1:] != ["build"]:
        sys.exit("usage: python -m janusm.sealed_r1 build > configs/janusm/sealed-r1.json")
    sys.stdout.write(dumps(build()))
