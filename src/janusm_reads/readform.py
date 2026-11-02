"""The read form between the queue and the table (JA46 (d), JA67; R5-S6 S13).

One mapping, girder-free (stdlib only, Python 3.9), used by both ends:

* :func:`read_form` is what ``girder_janusm.export.readRecord`` writes for a stored read:
  ``cadrads`` (CAD-RADS 2.0 per vessel) and ``lesionPoints`` (vessel -> world point, mm);
* :func:`reader_grades` turns that form into ``janusm.report.build``'s ``reader_grades``:
  ``{"LM": "4B", "LAD": "0", ..., "lesion_point": {vessel: [x, y, z]}}``.

So the export and ``janusm.report.grades_from_read_record`` cannot read the form differently.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


def read_form(read: Mapping[str, Any]) -> Dict[str, dict]:
    """The form fields of a stored read (or of an exported record), as the export writes them."""
    return {"cadrads": dict(read.get("cadrads") or {}),
            "lesionPoints": dict(read.get("lesionPoints") or {})}


def _grade(g: Any) -> Optional[str]:
    if g is None:
        return None
    g = str(g).strip().upper()
    return g or None


def reader_grades(form: Mapping[str, Any]) -> Dict[str, Any]:
    """:func:`read_form`'s fields as the table's ``reader_grades``. Empty grades are dropped;
    a lesion point is kept only with three coordinates."""
    form = read_form(form)
    out: Dict[str, Any] = {str(k): _grade(v) for k, v in form["cadrads"].items()
                           if _grade(v) is not None}
    pts = {str(k): [float(c) for c in v] for k, v in form["lesionPoints"].items()
           if v is not None and len(v) == 3}
    if pts:
        out["lesion_point"] = pts
    return out
