"""Selecting a class for editing shows it (D52, 0.25.4).

D26 and D51 start the classes of a seeded case hidden: they begin as identical
copies of the seed, and four (or 18) of them shown at once hide each other. The
annotator then picks a class in the Segment Editor's list and paints. But
Slicer's editor checks the selected segment at the first stroke, and when it is
hidden asks "The selected segment is hidden. Would you like to make it
visible?" -- and the stroke that raised the question is lost.

So the panel makes the class selected for editing visible as soon as it is
selected: by a click in the segment list, or by the editor itself picking one
when a case or submission is bound. Only that class: every other class keeps
the visibility it had. A class the annotator hides again by its eye, while it
stays selected, stays hidden: only a *change* of selection, or binding a case,
shows it.

Free of Slicer, Qt and VTK -- the editor node is passed in -- so pytest checks it
with stand-ins. Python 3.9-clean, as Slicer 5.8 bundles 3.9.
"""


def selected_segment(editor_node):
    """``(segmentation node, segment id)`` selected in ``editor_node``, or
    ``(None, None)`` when nothing is selected or the node is gone."""
    if editor_node is None:
        return None, None
    try:
        segment_id = editor_node.GetSelectedSegmentID()
        segmentation_node = editor_node.GetSegmentationNode()
    except Exception:
        return None, None
    if not segment_id or segmentation_node is None:
        return None, None
    return segmentation_node, segment_id


def show_segment(segmentation_node, segment_id):
    """Make one segment visible, leaving every other one as it is.

    Returns whether its visibility changed. Never raises: a class left hidden
    is the old behaviour (Slicer asks), not a broken case.
    """
    if segmentation_node is None or not segment_id:
        return False
    try:
        if segmentation_node.GetSegmentation().GetSegment(segment_id) is None:
            return False
        display = segmentation_node.GetDisplayNode()
        if display is None or display.GetSegmentVisibility(segment_id):
            return False
        display.SetSegmentVisibility(segment_id, True)
    except Exception:
        return False
    return True


class ShowSelected:
    """Shows the class selected in an editor node when the selection changes.

    ``update(editor_node)`` is called on every modification of the node (its
    ``ModifiedEvent`` fires for effect parameters too, so it only acts when the
    selected segment or segmentation is a different one); ``update(editor_node,
    force=True)`` when a case or submission is bound, which shows whatever is
    selected then, even if it has the same id as on the previous case.
    """

    def __init__(self):
        self.last = (None, None)

    def update(self, editor_node, force=False):
        """Returns whether a segment was made visible."""
        current = selected_segment(editor_node)
        changed = (current[0] is not self.last[0]) or (current[1] != self.last[1])
        self.last = current
        if current[1] is None or not (changed or force):
            return False
        return show_segment(*current)
