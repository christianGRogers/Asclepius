"""The four Janus-M classes (JA1) and the label-value checks every read must pass.

JA1 (Janus-M Round 1 ruling): 0 background; 1 LV myocardium (compact wall, septum
included); 2 LV blood pool (papillary muscles and trabeculae included; basal limit
at the mitral and aortic valve planes); 3 RV blood pool; 4 LA blood pool (to the
mitral annulus). No layer, segment or scar class: those are computed (JA2-JA4).

Stdlib only, Python 3.9.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Tuple

BACKGROUND = 0
LV_MYO = 1
LV_POOL = 2
RV_POOL = 3
LA_POOL = 4

#: value -> short name, as stored in a read and shown to a reader.
CLASSES: Dict[int, str] = {
    LV_MYO: "LV myocardium",
    LV_POOL: "LV blood pool",
    RV_POOL: "RV blood pool",
    LA_POOL: "LA blood pool",
}

#: value -> what the reader includes, from JA1. Shown in the protocol and the client.
CONVENTIONS: Dict[int, str] = {
    LV_MYO: "compact LV wall, septum included; papillary muscles and trabeculae are NOT "
            "myocardium",
    LV_POOL: "LV cavity with papillary muscles and trabeculae included; basal limit at the "
             "mitral and aortic valve planes",
    RV_POOL: "RV cavity",
    LA_POOL: "LA cavity, to the mitral annulus",
}

#: Display colours (0..1 RGB). Distinct from SegQueue14's coronary colours, so a
#: screenshot says which project it is.
COLORS: Dict[int, Tuple[float, float, float]] = {
    LV_MYO: (0.80, 0.45, 0.30),
    LV_POOL: (0.85, 0.15, 0.15),
    RV_POOL: (0.20, 0.35, 0.85),
    LA_POOL: (0.95, 0.75, 0.20),
}

#: Every class must be present in a submitted read.
REQUIRED = (LV_MYO, LV_POOL, RV_POOL, LA_POOL)
VALID_VALUES = frozenset({BACKGROUND, *CLASSES})


def missing_required(voxel_counts: Mapping) -> List[int]:
    """Required classes with no voxels. Keys may be ints or their string form."""
    counts = {}
    for key, value in (voxel_counts or {}).items():
        try:
            counts[int(key)] = int(value)
        except (TypeError, ValueError):
            continue
    return [v for v in REQUIRED if counts.get(v, 0) <= 0]


def invalid_values(values) -> List[int]:
    """Label values outside 0..4, sorted."""
    return sorted(int(v) for v in set(values) if int(v) not in VALID_VALUES)


def missing_message(missing) -> str:
    names = ", ".join(f"{CLASSES[v]} ({v})" for v in missing)
    return f"These Janus-M classes are empty: {names}. Every read labels all four (JA1)."
