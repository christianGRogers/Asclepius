"""The coronary hold-outs Janus-M may never read: D27 pool seal (D32/D33), its A34 reserve,
and the union of every Round 10 D35 draft. The pool already holds TotalSegmentator cardiac CTs
(source `TotalSegmentator-cardiac`, same s-numbers as the Zenodo release), so any public
TotalSegmentator study with a held-out s-number is refused too.

Run from the repository root (needs src/ on the path for segtrain.pool_seal).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from segtrain.pool_seal import load_pool_seal  # noqa: E402

D35_DRAFTS = [
    "experiments/Atlas/r10/decision_set_proposal.json",
    "experiments/Bridge/r10/decision_set_proposal.json",
    "experiments/Crucible/r10/d35_proposal.json",
    "experiments/Delta/r10/d35_decision_set_proposal.json",
    "experiments/Foxtrot/r10/d35_proposal.json",
]
_TS = re.compile(r"TotalSegmentator-cardiac__(s\d{4})")


def held_out_totalseg_ids() -> set:
    """TotalSegmentator s-numbers that are coronary-sealed, reserved or in a D35 draft."""
    load_pool_seal()  # verifies the pinned seal hash; raises if the file is wrong
    text = (ROOT / "configs/segqueue14/sealed-pool-2026-10.json").read_text()
    ids = set(_TS.findall(text))
    for f in D35_DRAFTS:
        ids |= set(_TS.findall((ROOT / f).read_text()))
    return ids


if __name__ == "__main__":
    print(sorted(held_out_totalseg_ids()))


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


class PoolGuard:
    """Refuses any pool volume of a coronary-sealed, reserved (A34) or D35-draft patient."""

    def __init__(self):
        import json
        from segtrain.pool_seal import _stem, ingest_patient
        self._stem, self._patient = _stem, ingest_patient
        self.seal = load_pool_seal()
        self.reserve = {e for e in self.seal.extension_order if isinstance(e, str)}
        self.d35 = set()
        for f in D35_DRAFTS:
            d = json.loads((ROOT / f).read_text())
            if "proposed_d35" in d:
                d = d["proposed_d35"]
            self.d35 |= set(_strings(d.get("patients", [])))
            self.d35 |= {self._stem(v) for v in _strings(d.get("volumes", []))}

    def reason(self, name):
        stem = self._stem(name)
        pat = self._patient(stem)
        if self.seal.is_sealed(name) or pat in self.seal.patients:
            return "coronary seal (D27/D32/D33)"
        if pat in self.reserve:
            return "seal reserve (A34)"
        if pat in self.d35 or stem in self.d35:
            return "a D35 draft (union)"
        return None
