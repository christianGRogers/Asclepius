"""The geometry a submission declares. Nothing here judges a submission.

This module used to validate before sending: empty required segments, stray
paint clicks, segment names outside the protocol, a segmentation exported on a
resampled or shifted grid. All of it is gone, including the advisory version that
replaced it for one commit.

**Why.** Every submission is seen by a human reviewer, and a check that refuses
the work cannot be overruled by them. The checks were also wrong often enough to
be worse than nothing -- a segment plainly on screen reported as empty after a
draft was reopened, which cost an annotator a finished case and taught the room
to distrust the panel. Demoting them to warnings did not fix that: a warning
nobody can act on and nobody believes is noise on the one screen that has to be
unambiguous.

What survives lives where it belongs and is not a matter of judgement -- the
server still checks the uploaded bytes against their declared checksum and size,
because a truncated transfer is corruption, not an opinion about anatomy.

``Geometry`` stays because a submission still *declares* the grid it was exported
on. It is recorded, and read later by whoever is converting the data; it is not
checked here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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
