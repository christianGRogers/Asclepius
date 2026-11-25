"""Keeping the 3D view's surfaces through a direct voxel write (0.25.2).

``slicer.util.updateSegmentBinaryLabelmapFromArray`` re-imports a segment from a
label volume. Slicer 5.8 then drops the closed-surface representation of *every*
segment in the segmentation, so whatever the 3D view showed disappears until it is
rebuilt (the module's Show in 3D). The Segment Editor's own effects modify the
labelmap in place and keep it; code outside an effect that writes voxels directly
wraps the write in ``keeping_closed_surface``.

Free of Slicer, Qt and VTK -- the segmentation node is only called -- so pytest
checks it with a stand-in. Python 3.9-clean, as Slicer 5.8 bundles 3.9.
"""

from contextlib import contextmanager

#: ``vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName()``.
CLOSED_SURFACE = "Closed surface"


def has_closed_surface(segmentation_node):
    """Whether the segmentation shows its segments as surfaces (in the 3D view)."""
    if segmentation_node is None:
        return False
    segmentation = segmentation_node.GetSegmentation()
    if segmentation is None or not segmentation.GetNumberOfSegments():
        return False
    return bool(segmentation.ContainsRepresentation(CLOSED_SURFACE))


@contextmanager
def keeping_closed_surface(segmentation_node):
    """Around direct voxel writes: if the segmentation had closed surfaces before,
    it has them after, rebuilt from the new voxels. Yields whether it had them.

    Rebuilt even when the writes raise, so a half-done write never leaves the 3D
    view blank. A segmentation that showed no surfaces is left without them:
    building surfaces nobody asked for costs time on a full-size CT.
    """
    had = has_closed_surface(segmentation_node)
    try:
        yield had
    finally:
        if had:
            segmentation_node.CreateClosedSurfaceRepresentation()
