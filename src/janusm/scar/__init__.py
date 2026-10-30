"""Janus-M path B (``jm/paired-scar``): scar inside the registered wall on a late-iodine (LIE) scan.

Ruling: ``vault/JanusM/Judgements/Round 2 - paired-scar.md``, JA26-JA32 (JA35 items 1, 2, 4, 6).

- :mod:`janusm.scar.registration` (JA29): the first-pass CCTA (moving) onto the LIE scan (fixed):
  scanner frame, QC, heart-masked Mattes MI rigid, then affine; QC values, the reader-check status
  and a per-patient log.
- :mod:`janusm.scar.scar0` (JA30): every Scar-0 menu candidate inside the registered class 1,
  aggregated per AHA segment 1-17 from :mod:`janusm.geometry` (JA26).
- :mod:`janusm.scar.scoring` (JA27-JA32, JA55, JA56): the scoring harness (cluster bootstrap over
  patients, JA55 intention-to-diagnose and yield, JA27 strata, JA56's two ordered claims).
- :mod:`janusm.scar.power`: the one power script, scoring every simulated study with that harness,
  and JA57's seal size.

Scar is never a learned class (JA26). Every output here is research output, not validated, until
JA32 passes on the paired seal, and carries the patient's registration status.

These modules take arrays, never files. A ``case_id`` given for logging goes through the JA12
guard first, and fails closed.
"""

from __future__ import annotations

#: Bump on any change that can move a reported number.
SCAR_VERSION = "1.0.0"

#: JA26: every scar output carries this until JA32 passes on the paired seal.
RESEARCH_LABEL = "research output, not validated"

# JA26 registration statuses (strings). The scoring harness's per-segment code for a not-graded
# segment is the integer janusm.scar.scoring.NOT_GRADED (-1). AWAITING is the state before the
# JA29 reader check; it is never a final status and scoring must not take it.
PASSED = "passed"
REREGISTERED = "re-registered"
NOT_GRADED = "not graded"
AWAITING = "awaiting reader check"
# JA52: flagged by the phase step. Not a registration failure (left out of failure_rate), never
# re-registered; its stratum is decided downstream with the reader's phase mark. Not a final
# grading status here: scoring a phase-suspect patient is decided by the phase-unmatched stratum.
PHASE_SUSPECT = "phase suspect"
STATUSES = (PASSED, REREGISTERED, NOT_GRADED, AWAITING, PHASE_SUSPECT)
FINAL_STATUSES = (PASSED, REREGISTERED, NOT_GRADED)


def guard_case(case_id, what: str) -> None:
    """JA12 GUARD CALL SITE for this subpackage: refuse a held-out case before anything runs.

    Raises :class:`janusm.guard.HeldOutError` on a held-out case (``GuardInputError`` when a
    pinned list is missing or changed). Fails closed: if the guard cannot be imported, the call is
    refused too.
    """
    if case_id is None:
        return
    try:
        from janusm import guard
    except ImportError as e:
        raise RuntimeError(f"JA12 guard (janusm.guard) unavailable; refusing {case_id!r}") from e
    if guard is None:  # pragma: no cover - a blocked import surfaces as ImportError above
        raise RuntimeError(f"JA12 guard (janusm.guard) unavailable; refusing {case_id!r}")
    guard.refuse([str(case_id)], what=what)


__all__ = [
    "SCAR_VERSION",
    "RESEARCH_LABEL",
    "PASSED",
    "REREGISTERED",
    "NOT_GRADED",
    "AWAITING",
    "PHASE_SUSPECT",
    "STATUSES",
    "FINAL_STATUSES",
    "guard_case",
]
