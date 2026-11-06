"""The annotator benchmark (D43, #286): one fixed ImageCAS-X case, drawn once.

Every annotator (except the ones named at run time) is served the same ImageCAS-X
case, seeded like a pool case, and scored on their own against ImageCAS-X. This
module is the part that needs no Girder: the case's name, which ImageCAS-X cases
may be drawn, and the draw itself. ``girder_segqueue14.benchmark`` does the rest.

**Eligible:** an ImageCAS-X train or val case (they are the ones with a released
reference) that nothing holds out. **Excluded**, each with its reason:

* the ImageCAS-X test split, open and sealed;
* every list in ``trillium/sealed_test.json`` (A14): the sealed test and
  quality-0 cases and the excluded development cases;
* whatever the JA12 guard (``janusm.guard``) refuses for an ImageCAS-X id: the
  A14 sealed 100, the test split, val 80, the Janus-M seal and decision cases;
* TotalSegmentator twins: ImageCAS cases that may be in TotalSegmentator's
  training data. The project has no such list for ImageCAS (its twin list,
  ``configs/janusm/ts-twins-r1.json``, is TotalSegmentator subjects matching
  held-out pool patients), so this is empty unless a list is passed.

**The draw** ranks every eligible case by ``sha256(salt + case)`` and takes the
lowest. It depends only on the eligible set and the salt, both recorded with the
pick; the server stores the pick on the case and never draws again.

Standard library only, Python 3.9.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Mapping, Optional

#: Every benchmark case's name starts with this (D43): ``annotator_benchmark_0123``,
#: with the ImageCAS id (1-based) zero-padded to four digits, as ``imagecas_0123``.
NAME_PREFIX = "annotator_benchmark_"
_NAME_RE = re.compile(r"^annotator_benchmark_(\d{1,4})$")
#: A read of one, as an export or a training tree may spell it (``__r2``, ``_rA``).
_READ_SUFFIX = re.compile(r"(__r\d+|_r[A-Za-z0-9]+)$")

#: The serve tier and dataset recorded on the case. The tier sorts nothing: the
#: case is served only to the annotators it is assigned to.
TIER = "annotator-benchmark"
DATASET = "ImageCAS-X"

#: The draw's salt. Changing it is a different draw; the server never redraws a
#: case it already has, whatever this says.
SALT = "asclepius-annotator-benchmark-d43:"

#: The ImageCAS-X splits a benchmark may come from.
ELIGIBLE_SPLITS = ("train", "val")

#: ``trillium/sealed_test.json`` keys that are not lists of held-out cases.
SEALED_TEST_NOT_LISTS = ("rule", "declared_dev_cases")

NO_TWIN_LIST = ("none: the project has no list of ImageCAS cases that may be in "
                "TotalSegmentator's training data (configs/janusm/ts-twins-r1.json lists "
                "TotalSegmentator subjects, not ImageCAS cases)")


def case_name(imagecas_id: int) -> str:
    """ImageCAS id 123 -> ``annotator_benchmark_0123``."""
    n = int(imagecas_id)
    if not 1 <= n <= 1000:
        raise ValueError(f"ImageCAS id {n} is not in 1..1000")
    return f"{NAME_PREFIX}{n:04d}"


def _base(name: str) -> str:
    base = str(name or "").strip().replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    return _READ_SUFFIX.sub("", base)


def is_benchmark_name(name: str) -> bool:
    """True for a benchmark case or a read of one (``annotator_benchmark_0123__r2``)."""
    return bool(_NAME_RE.match(_base(name)))


def imagecas_id_of(name: str) -> Optional[int]:
    """``annotator_benchmark_0123`` -> 123; None for any other name."""
    m = _NAME_RE.match(_base(name))
    return int(m.group(1)) if m else None


def icx_case(imagecas_id: int) -> str:
    """ImageCAS id 123 -> ImageCAS-X ``c0122`` (the tournament's id - 1 naming)."""
    return f"c{int(imagecas_id) - 1:04d}"


def imagecas_id(icx: str) -> int:
    """ImageCAS-X ``c0122`` -> ImageCAS id 123."""
    if not re.fullmatch(r"c\d{4}", str(icx)):
        raise ValueError(f"{icx!r} is not an ImageCAS-X case id (cNNNN)")
    return int(icx[1:]) + 1


def rank(icx: str, salt: str = SALT) -> str:
    """The draw's sort key for one case: ``sha256(salt + case)`` in hex."""
    return hashlib.sha256(f"{salt}{icx}".encode()).hexdigest()


@dataclass
class Eligibility:
    """Which ImageCAS-X cases may be the benchmark, and why the rest may not."""

    eligible: List[str]                       # c-ids, in draw order
    excluded: Dict[str, str] = field(default_factory=dict)   # c-id -> first reason
    salt: str = SALT
    twins: str = NO_TWIN_LIST

    def counts(self) -> Dict[str, int]:
        """How many cases each kind of reason excluded (by its first words)."""
        out: Dict[str, int] = {}
        for why in self.excluded.values():
            key = why.split(":", 1)[0]
            out[key] = out.get(key, 0) + 1
        return dict(sorted(out.items()))


def eligibility(splits: Mapping[str, Iterable[str]],
                sealed_test: Mapping[str, object],
                guard_reason: Callable[[str], Optional[str]],
                twins: Optional[Iterable[str]] = None,
                salt: str = SALT) -> Eligibility:
    """The eligible ImageCAS-X cases, in draw order, and every exclusion.

    ``splits``: ``{"train": [c-ids], "val": [...], "test": [...]}`` (ImageCAS-X's
    own split, ``trillium-results/icx14/results/splits.json``). ``sealed_test``:
    ``trillium/sealed_test.json`` as loaded. ``guard_reason(c_id)``: the JA12
    guard's refusal for an ImageCAS-X id, or None. ``twins``: ImageCAS-X c-ids that
    may be in TotalSegmentator's training data, or None when no list exists.

    A case is excluded for the first reason that applies, in the order above. A
    case in no train/val list is not a candidate at all.
    """
    test = {str(c) for c in splits.get("test", ())}
    candidates = sorted({str(c) for s in ELIGIBLE_SPLITS for c in splits.get(s, ())})
    held: Dict[str, str] = {}
    for key, value in sealed_test.items():
        if key in SEALED_TEST_NOT_LISTS or not isinstance(value, list):
            continue
        for c in value:
            held.setdefault(str(c), f"trillium/sealed_test.json {key}")
    twin_set = None if twins is None else {str(c) for c in twins}

    excluded: Dict[str, str] = {}
    eligible: List[str] = []
    for c in candidates:
        if c in test:
            excluded[c] = "test: in ImageCAS-X's test split as well as train/val"
        elif c in held:
            excluded[c] = f"sealed or excluded: {held[c]}"
        else:
            why = guard_reason(c)
            if why:
                excluded[c] = f"JA12 guard: {why}"
            elif twin_set is not None and c in twin_set:
                excluded[c] = "TotalSegmentator twin: may be in its training data"
            else:
                eligible.append(c)
    eligible.sort(key=lambda c: (rank(c, salt), c))
    return Eligibility(eligible=eligible, excluded=excluded, salt=salt,
                       twins=NO_TWIN_LIST if twin_set is None
                       else f"{len(twin_set)} listed ImageCAS-X case(s) excluded")


@dataclass(frozen=True)
class Pick:
    """The drawn case, with everything needed to check the draw later."""

    icx: str
    imagecas_id: int
    name: str
    rank: str
    position: int          # 0 = the first in draw order; > 0 if earlier ones were unusable
    eligible: int
    salt: str
    split: str
    why: str

    def to_dict(self) -> Dict[str, object]:
        return {"icxCase": self.icx, "imagecasId": self.imagecas_id, "name": self.name,
                "rank": self.rank, "position": self.position, "eligible": self.eligible,
                "salt": self.salt, "split": self.split, "why": self.why}


def draw(elig: Eligibility, splits: Mapping[str, Iterable[str]],
         usable: Optional[Callable[[str], Optional[str]]] = None,
         skipped: Optional[List[str]] = None) -> Pick:
    """The first eligible case in draw order that ``usable`` accepts.

    ``usable(c_id)`` returns None if the case can be served (its CT and reference
    exist) or the reason it cannot; each unusable case is appended to ``skipped``
    with its reason. Raises ``ValueError`` if nothing is eligible and usable.
    """
    split_of = {str(c): s for s in ELIGIBLE_SPLITS for c in splits.get(s, ())}
    for position, c in enumerate(elig.eligible):
        problem = usable(c) if usable is not None else None
        if problem:
            if skipped is not None:
                skipped.append(f"{c}: {problem}")
            continue
        n = imagecas_id(c)
        split = split_of.get(c, "")
        why = (f"ImageCAS-X {split} case {c} (ImageCAS {n}); not test, not on any "
               f"trillium/sealed_test.json list, not refused by the JA12 guard; twins: "
               f"{elig.twins}; first of {len(elig.eligible)} eligible by "
               f"sha256({elig.salt!r} + case)"
               + (f", after {position} unusable" if position else ""))
        return Pick(icx=c, imagecas_id=n, name=case_name(n), rank=rank(c, elig.salt),
                    position=position, eligible=len(elig.eligible), salt=elig.salt,
                    split=split, why=why)
    raise ValueError(f"no usable benchmark case among {len(elig.eligible)} eligible")
