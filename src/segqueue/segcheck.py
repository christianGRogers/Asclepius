"""Pre-flight checks on a segmentation, run client-side and again on the server.

The cheapest rejection is the one that never becomes a submission. Most of what
a reviewer would send back is mechanical -- a segment left empty, a stray
segment named "Segment_1", a segmentation resampled onto a different grid than
the source volume -- and all of it is detectable before the upload starts. So
the extension runs these checks at the click of Submit and refuses to send;
the server runs the identical checks on receipt, because a client can be old,
patched, or simply lying.

That double-run is why this module takes *summaries* rather than volumes. The
client has a ``vtkSegmentation`` and the server has a ``.seg.nrrd``, and neither
can hand the other its own objects -- but both can produce a dict of segment
names to voxel counts and a small geometry record. Keeping the rules over those
summaries means one implementation, tested once, with no numpy in sight.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

#: A submission cannot proceed.
ERROR = "error"
#: Worth telling the annotator, but not worth blocking on. Warnings are also
#: recorded on the submission, so a reviewer sees what the annotator saw.
WARNING = "warning"


@dataclass(frozen=True)
class Problem:
    level: str
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.level.upper()}: {self.message}"


@dataclass(frozen=True)
class Geometry:
    """Just enough of a volume's grid to tell whether two share one.

    Not a general image header -- direction cosines are deliberately absent,
    because Slicer writes the segmentation with the source volume's own
    directions and a mismatch there has never been the failure we see. Size and
    spacing are what drift, via a resample the annotator did not mean to do.
    """

    size: tuple = ()
    spacing: tuple = ()
    origin: tuple = ()

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> Optional[Geometry]:
        if not data:
            return None
        return cls(
            size=tuple(int(v) for v in data.get("size", ()) or ()),
            spacing=tuple(float(v) for v in data.get("spacing", ()) or ()),
            origin=tuple(float(v) for v in data.get("origin", ()) or ()),
        )

    def to_dict(self) -> dict:
        return {
            "size": list(self.size),
            "spacing": list(self.spacing),
            "origin": list(self.origin),
        }


#: Tolerance for spacing and origin comparison, in the volume's own units (mm).
#: NRRD stores these as decimal text, so a round-trip through Slicer can move
#: the last digit; anything at 1e-4 mm is a formatting artefact, not a resample.
GEOMETRY_TOLERANCE_MM = 1e-3

#: Voxel count at or below which a segment is treated as an accidental stray
#: mark rather than a structure. A single errant paint click leaves a handful of
#: voxels, and blocking submission on it is friendlier than a rejection later.
STRAY_VOXELS = 8


def _close(a, b, tol: float) -> bool:
    if len(a) != len(b):
        return False
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def check_submission(
    voxel_counts: dict,
    segments,
    source_geometry: Optional[Geometry] = None,
    segmentation_geometry: Optional[Geometry] = None,
    annotation_seconds: Optional[float] = None,
    min_plausible_seconds: float = 60.0,
) -> list:
    """Every problem with a proposed submission, worst first.

    ``segments`` is the project's ``SegmentSpec`` list from ``protocol.py``;
    ``voxel_counts`` maps segment name to the number of labelled voxels. An
    empty result means the submission is good to send.
    """
    problems = []
    expected = {s.name: s for s in segments}

    for spec in segments:
        count = int(voxel_counts.get(spec.name, 0) or 0)
        if count == 0:
            if spec.required:
                problems.append(Problem(
                    ERROR, "empty_required_segment",
                    f"{spec.name!r} is empty. Segment it, or ask a reviewer to "
                    "mark it not-applicable for this case.",
                ))
            else:
                problems.append(Problem(
                    WARNING, "empty_optional_segment",
                    f"{spec.name!r} is empty -- fine if the structure is genuinely "
                    "absent or outside the field of view.",
                ))
        elif 0 < count <= STRAY_VOXELS:
            problems.append(Problem(
                ERROR, "stray_voxels",
                f"{spec.name!r} has only {count} voxels, which is almost certainly "
                "a stray paint click rather than a structure.",
            ))

    for name, count in sorted(voxel_counts.items()):
        if name not in expected and int(count or 0) > 0:
            problems.append(Problem(
                ERROR, "unexpected_segment",
                f"{name!r} is not part of this project's protocol. Delete it "
                "before submitting -- renamed or extra segments break the training "
                "conversion downstream.",
            ))

    if source_geometry is not None and segmentation_geometry is not None:
        problems.extend(_check_geometry(source_geometry, segmentation_geometry))

    if annotation_seconds is not None and annotation_seconds < min_plausible_seconds:
        # A warning, not an error. The server records it and the dashboard
        # aggregates it; blocking here would only teach people to idle first.
        problems.append(Problem(
            WARNING, "implausibly_fast",
            f"This case took {annotation_seconds:.0f} seconds. That is unusually "
            "fast -- please check you have not submitted an unfinished segmentation.",
        ))

    problems.sort(key=lambda p: 0 if p.level == ERROR else 1)
    return problems


def _check_geometry(source: Geometry, seg: Geometry) -> list:
    problems = []
    if source.size and seg.size and tuple(source.size) != tuple(seg.size):
        problems.append(Problem(
            ERROR, "geometry_size",
            f"The segmentation grid is {list(seg.size)} but the source volume is "
            f"{list(source.size)}. Export the labelmap using the source volume as "
            "the reference geometry.",
        ))
    if source.spacing and seg.spacing and not _close(source.spacing, seg.spacing,
                                                     GEOMETRY_TOLERANCE_MM):
        problems.append(Problem(
            ERROR, "geometry_spacing",
            f"The segmentation was resampled to spacing {list(seg.spacing)}; the "
            f"source volume is {list(source.spacing)}. Coronary work must stay on "
            "the native grid.",
        ))
    if source.origin and seg.origin and not _close(source.origin, seg.origin,
                                                   GEOMETRY_TOLERANCE_MM):
        problems.append(Problem(
            ERROR, "geometry_origin",
            f"The segmentation origin {list(seg.origin)} does not match the "
            f"source volume {list(source.origin)}.",
        ))
    return problems


def blocking(problems) -> list:
    """Only the problems that must stop a submission."""
    return [p for p in problems if p.level == ERROR]


def summarise(problems) -> str:
    """Multi-line text for a Qt label or an HTTP error body."""
    if not problems:
        return "No problems found."
    return "\n".join(f"- {p.message}" for p in problems)
