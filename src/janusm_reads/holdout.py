"""The Janus-M read tools' only door to the JA12 guard (``janusm.guard``, #138).

Every step here that names cases (the read queue, its populate tool, the seed job,
the anchoring report) calls :func:`refuse` or :func:`refuse_read_cases` first, and
the whole step stops on any hit. This module adds no rule of its own: what is
refused is the guard's (pool seal, reserve, D35 draws, A14 sealed 100, ImageCAS-X
test and val, PLOS-Peng2016, public copies, TotalSegmentator twins, and the Janus-M
seal and decision roles).

It **fails closed**: if the guard cannot be imported or loaded, every call refuses.

Purposes. Reading the Janus-M reference is part of scoring it, so a seal case is
checked with the guard's ``seal_scoring`` purpose and a decision case with
``decision_scoring`` (:func:`purpose_for`). Any other purpose refuses both.

Stdlib only.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional

ANY, SEAL_SCORING, DECISION_SCORING = "any", "seal_scoring", "decision_scoring"

#: Read set (``janusm_reads.readset``) -> the guard purpose its reads are checked under.
PURPOSE_FOR_SET = {"seal": SEAL_SCORING, "decision": DECISION_SCORING}


class HoldoutError(RuntimeError):
    """The guard refused (or could not run). The whole step is refused."""


def _guard():
    try:
        from janusm import guard
    except Exception as exc:  # noqa: BLE001 - fail closed on any import problem
        raise HoldoutError(
            f"the JA12 guard (janusm.guard) cannot be imported ({exc}); refusing") from exc
    return guard


def purpose_for(read_set: str) -> str:
    try:
        return PURPOSE_FOR_SET[read_set]
    except KeyError:
        raise HoldoutError(f"{read_set!r} is not a Janus-M read set") from None


def refuse(names: Iterable[str], what: str = "this Janus-M read step",
           purpose: str = ANY, source: Optional[str] = None) -> List[str]:
    """``names`` unchanged if the guard clears them all; :class:`HoldoutError` otherwise."""
    guard = _guard()
    try:
        return guard.refuse(list(names), what=what, source=source, purpose=purpose)
    except guard.HeldOutError as exc:
        raise HoldoutError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - a guard that cannot load refuses
        raise HoldoutError(f"the JA12 guard could not run ({exc}); refusing {what}") from exc


def refuse_read_cases(cases: Iterable[str], read_sets: Mapping[str, Iterable[str]],
                      what: str = "this Janus-M read step") -> Dict[str, str]:
    """Check Janus-M read cases, each under its own set's purpose.

    ``read_sets`` is the frozen ``{'seal': [...], 'decision': [...]}``. A case in
    neither is refused outright. Returns ``{case: purpose}``.
    """
    member = {}
    for name, listed in read_sets.items():
        for c in listed:
            member[c] = name
    out, strangers, by_purpose = {}, [], {}
    for c in cases:
        if c not in member:
            strangers.append(c)
            continue
        p = purpose_for(member[c])
        out[c] = p
        by_purpose.setdefault(p, []).append(c)
    if strangers:
        raise HoldoutError(f"{what} refused: {len(strangers)} case(s) are not in the frozen "
                           f"Janus-M seal or decision set: {strangers[:10]}")
    for p, names in sorted(by_purpose.items()):
        refuse(names, what=what, purpose=p)
    return out
