"""Turning the extended classes off hides them; turning them on shows them as they were (D53).

Before 0.25.6 turning "Extended classes" off *removed* every extended class the
module judged empty or an untouched copy of the seed, and raised a "Kept D1, D2,
OM2 because you have changed them ..." box for the rest. A removed branch came back
empty when the box was turned on again, and was never given its seed copy again
(D52 records it as already selected), and the box confused annotators. D53: the
toggle only hides. No segment is removed, emptied, refilled or re-seeded by it.

``ExtendedView`` remembers, when the classes are hidden, which of them were shown,
so turning the toggle back on restores exactly that -- a group hidden with its
"Show" tick, or a class hidden by its eye, stays hidden. Hiding twice in a row
keeps the first record, so toggling off, off and on loses nothing either.

Free of Slicer, Qt and VTK -- the display node is passed in -- so pytest checks it
with stand-ins. Python 3.9-clean, as Slicer 5.8 bundles 3.9.
"""


class ExtendedView:
    """Hide or show a set of segments on a display node, remembering their eyes."""

    def __init__(self):
        #: ``{segment id: visible}`` from the last hide, or None while shown.
        self.remembered = None

    @property
    def hidden(self):
        return self.remembered is not None

    def reset(self):
        """Forget the record: a new case or submission is in the scene."""
        self.remembered = None

    def hide(self, display, segment_ids):
        """Hide every segment of ``segment_ids``; returns how many were hidden.

        The first hide records each segment's visibility; a hide while already
        hidden adds only segments not recorded yet, so nothing is forgotten.
        """
        if display is None:
            return 0
        if self.remembered is None:
            self.remembered = {}
        hidden = 0
        for segment_id in segment_ids:
            if not segment_id:
                continue
            if segment_id not in self.remembered:
                self.remembered[segment_id] = bool(display.GetSegmentVisibility(segment_id))
            display.SetSegmentVisibility(segment_id, False)
            hidden += 1
        return hidden

    def show(self, display, segment_ids):
        """Give every segment of ``segment_ids`` back the visibility it had when
        hidden; returns how many were restored. A segment never hidden by this
        (one added while the classes were hidden) is left as it is."""
        remembered, self.remembered = self.remembered or {}, None
        if display is None:
            return 0
        restored = 0
        for segment_id in segment_ids:
            if segment_id in remembered:
                display.SetSegmentVisibility(segment_id, remembered[segment_id])
                restored += 1
        return restored
