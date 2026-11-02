"""What the read queue does with a check report: return once, then accept and flag
(JA21; Hotel v3 section 5.1 item 7), and the crash path (JA68).

Stdlib only and girder-free, so it is tested in every CI job (JA79), not only where
Girder is installed. ``girder_janusm.check`` applies it to a read.
"""

from __future__ import annotations

from typing import Optional, Tuple

from . import protocol

#: What :func:`decide` says happened, for the read's counters.
ACCEPTED, RETURNED, FLAGGED, CRASHED = "accepted", "returned", "flagged", "crashed"


def decide(report: dict, returns: Optional[int], crashed: bool = False,
           ) -> Tuple[str, bool, str, str]:
    """``(state, flagged, summary, outcome)`` for a check report on a read already
    returned ``returns`` times: return once, then accept and flag. A crash, or a read
    that could not be checked (``couldNotBeChecked``), goes back unflagged and never
    spends the return, however many returns the read has had (JA68)."""
    if crashed or report.get("couldNotBeChecked"):
        return protocol.RETURNED, False, report["summary"], CRASHED
    if report["passed"]:
        return protocol.ACCEPTED, False, report["summary"], ACCEPTED
    if int(returns or 0) < protocol.MAX_RETURNS:
        return protocol.RETURNED, False, report["summary"], RETURNED
    return (protocol.ACCEPTED, True,
            "Accepted and flagged: the read failed the check again after being returned "
            "once. " + " ".join(report.get("errors") or []), FLAGGED)
