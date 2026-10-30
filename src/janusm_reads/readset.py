"""Which cases the Janus-M read queue serves, which are read from blank, and in what order.

The queue serves the frozen Janus-M **seal (60)** and **decision set (40)** and
nothing else (JA6, JA7). Both lists come from the JA6 freeze file
(``configs/janusm/sealed-r1.json``, issue #140); this module only reads it.

**Blank reads.** JA7: 10 of the 60 seal cases are read with no seed. Which 10 is
fixed here, before any read, by the same kind of salted-hash rank JA6 uses for
the draw: the 10 seal cases whose ``sha256(BLANK_SALT + case)`` sort first. Both
reads of a blank case are blank, so the blank cases' inter-read difference is
unanchored by construction.

**Order.** Decision cases are served first, and seal cases only once an admin
opens them: JA6 re-powers the seal on the first 20 double-read decision cases
"before any seal case is read".

Stdlib only, Python 3.9.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

SEAL = "seal"
DECISION = "decision"
SETS = (SEAL, DECISION)

#: Salt for the blank-read pick. Never change it after the first read.
BLANK_SALT = "asclepius-janusm-blank-r1:"
#: JA6: the seal as first drawn. It may grow (by an explicit PR, from the
#: pre-registered extension) but never shrinks; the blank pick stays within these 60.
N_SEAL = 60
N_DECISION = 40
#: JA7: 10 of the 60 seal cases are read from blank.
N_BLANK = 10
#: JA7: every case is read twice, independently.
READS_PER_CASE = 2

#: Serve priority (higher first). Decision before seal (JA6 re-powering).
PRIORITY = {DECISION: 200, SEAL: 100}

#: ImageCAS-X / tournament case ids: ``c0000`` .. ``c0999`` (ImageCAS id - 1).
_CASE_ID = re.compile(r"^c\d{4}$")

#: Repository-relative path of the JA6 freeze file (#140); pinned in ``janusm.sealed_r1``.
FREEZE_RELPATH = "configs/janusm/sealed-r1.json"


class ReadSetError(ValueError):
    """The freeze file is missing, malformed, or names something that is not a case."""


@dataclass(frozen=True)
class CasePlan:
    """One case as the queue holds it."""

    name: str          # cNNNN
    read_set: str      # seal | decision
    blank: bool        # both reads start from no seed
    priority: int
    serve_order: int
    reads: int = READS_PER_CASE

    def to_dict(self) -> dict:
        return {"name": self.name, "readSet": self.read_set, "blank": self.blank,
                "priority": self.priority, "serveOrder": self.serve_order,
                "reads": self.reads}


def check_case_id(case: str) -> str:
    case = str(case).strip()
    if not _CASE_ID.match(case):
        raise ReadSetError(f"{case!r} is not an ImageCAS-X case id (cNNNN)")
    return case


def _cases(value) -> List[str]:
    """A list of ids, or a mapping that holds one under ``cases``."""
    if isinstance(value, Mapping):
        value = value.get("cases")
    if not isinstance(value, (list, tuple)):
        raise ReadSetError("each read set must be a list of case ids, or an object "
                           "with a 'cases' list")
    return [check_case_id(c) for c in value]


def parse_freeze(data: Mapping) -> Dict[str, List[str]]:
    """``{'seal': [...], 'decision': [...]}`` from the freeze file's JSON.

    Accepts each set either as a list or as ``{"cases": [...]}``. Refuses a case in
    both sets, a duplicate, or a list of the wrong size (60 seal, 40 decision).
    Extension cases (JA6's pre-registered next 60) are never served from here: a
    growth of the seal comes through the freeze file itself, by an explicit PR.
    """
    out = {}
    for name in SETS:
        if name not in data:
            raise ReadSetError(f"the freeze file has no {name!r} list")
        out[name] = _cases(data[name])
        if len(set(out[name])) != len(out[name]):
            raise ReadSetError(f"the {name} list repeats a case")
    both = set(out[SEAL]) & set(out[DECISION])
    if both:
        raise ReadSetError(f"cases in both seal and decision: {sorted(both)[:5]}")
    if len(out[SEAL]) < N_SEAL or len(out[DECISION]) != N_DECISION:
        raise ReadSetError(
            f"expected at least {N_SEAL} seal and exactly {N_DECISION} decision cases, found "
            f"{len(out[SEAL])} and {len(out[DECISION])}")
    return out


def load_freeze(path=None) -> Dict[str, List[str]]:
    """The frozen seal and decision lists, in freeze order, after the JA6 pin check
    (``janusm.sealed_r1.load``: a missing or changed file is an error, never a pass)."""
    from janusm import sealed_r1

    path = Path(path) if path else sealed_r1.REPO / sealed_r1.PATH
    try:
        sealed_r1.load(path)
    except sealed_r1.JanusMSealError as exc:
        raise ReadSetError(f"{exc}. The read queue serves nothing without the JA6 freeze "
                           "(#140).") from exc
    data = json.loads(path.read_text(encoding="utf-8"))
    return parse_freeze(data)


def blank_rank(case: str) -> str:
    return hashlib.sha256((BLANK_SALT + case).encode("utf-8")).hexdigest()


def blank_cases(seal: Sequence[str], n: int = N_BLANK) -> List[str]:
    """The ``n`` seal cases read from blank, in rank order, picked from the first
    :data:`N_SEAL` (the seal as drawn), so a later growth never changes them."""
    seal = [check_case_id(c) for c in seal][:N_SEAL]
    if n > len(seal):
        raise ReadSetError(f"cannot pick {n} blank cases from {len(seal)} seal cases")
    return sorted(seal, key=blank_rank)[:n]


def plan(read_sets: Mapping[str, Iterable[str]]) -> List[CasePlan]:
    """The queue's cases: decision first, then seal; each in its freeze order."""
    seal = list(read_sets[SEAL])
    decision = list(read_sets[DECISION])
    blank = set(blank_cases(seal))
    out = []
    order = 0
    for name, cases in ((DECISION, decision), (SEAL, seal)):
        for case in cases:
            out.append(CasePlan(name=check_case_id(case), read_set=name,
                                blank=case in blank, priority=PRIORITY[name],
                                serve_order=order))
            order += 1
    return out


def imagecas_number(case: str) -> int:
    """``c0001`` -> 2: the ImageCAS id, which is the tournament id plus one."""
    return int(check_case_id(case)[1:]) + 1


# ------------------------------------------------- JA47 rule 2's third-read draw

#: How many seeded cases of a flagged wave get a third read from blank, and the salt.
THIRD_READ_CASES = 5
THIRD_READ_SALT = "asclepius-janusm-third-read-r1:"


def third_read_cases(wave: str, seeded_cases: Iterable[str], n: int = THIRD_READ_CASES,
                     ) -> List[str]:
    """Rule 2's draw (JA47, JA68): the ``n`` seeded cases of a wave with the lowest
    ``sha256(salt + wave + ":" + case)``. Stable whatever order the cases come in.
    Here, in the stdlib half, so the queue's web server enforces the same draw the
    anchoring report prints."""

    def key(case):
        return hashlib.sha256(f"{THIRD_READ_SALT}{wave}:{case}".encode()).hexdigest()

    return sorted(sorted(set(seeded_cases)), key=key)[:n]
