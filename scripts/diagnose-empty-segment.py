"""Why does a segment that is plainly there report as empty?

Run it inside Slicer, with the case open and the segment visible, from the Python
console (View -> Python Console):

    exec(open(r'C:\\path\\to\\Asclepius\\scripts\\diagnose-empty-segment.py').read())

It changes nothing. It reports what the submission check actually sees, which is
not what the Segment Editor shows:

* The editor draws a segment's own labelmap. The check counts the *exported*
  label volume, which is a different array built by flattening every segment
  into one label per voxel.
* A segmentation keeps its labelmaps in layers, and each segment carries a label
  value that is only required to be unique within its own layer. The export
  resolves both. So a segment can hold thousands of voxels and still contribute
  none to the export -- if its label value collides, if it is on an unexpected
  layer, or if there are two segments with the same name and the wrong one is
  being exported.

Each of those leaves a different fingerprint below, which is the point: the
answer is in the table rather than in a guess.
"""

import os
import tempfile
import traceback

import slicer

print("=" * 72)

try:
    widget = slicer.modules.SegQueueWidget
    logic = widget.logic
except Exception as exc:  # pragma: no cover - module not loaded
    print("Open the SegQueue module first (%s)" % exc)
    raise SystemExit from None

module = __import__(logic.__module__) if logic else None
print("SegQueue %s" % getattr(module, "__version__", "?"))

seg = logic.segmentationNode
volume = logic.volumeNode
if seg is None:
    print("No segmentation is open. Open the case first.")
    raise SystemExit

project = logic.project
specs = list(project.segments) if project else []
wanted = {s.name: int(s.label) for s in specs}
print("assignment: %s" % (logic.assignment.case_name if logic.assignment else "none"))
print("resumed from an autosaved draft: %s" % getattr(logic, "resumedDraft", "?"))
print("protocol: %s" % wanted)
print()

segmentation = seg.GetSegmentation()
try:
    layers = segmentation.GetNumberOfLayers()
except AttributeError:
    layers = "?"
print("%d segment(s) in %s layer(s)" % (segmentation.GetNumberOfSegments(), layers))
print()
print("%-34s %-6s %-6s %-10s %-10s" % ("name", "label", "layer", "own vox", "grid vox"))
print("-" * 72)

byName = {}
rows = []
for i in range(segmentation.GetNumberOfSegments()):
    sid = segmentation.GetNthSegmentID(i)
    segment = segmentation.GetSegment(sid)
    name = segment.GetName()
    byName.setdefault(name, []).append(sid)

    try:
        label = segment.GetLabelValue()
    except AttributeError:
        label = "?"
    try:
        layer = segmentation.GetLayerIndex(sid)
    except AttributeError:
        layer = "?"

    def count(ref, _sid=sid):
        try:
            a = slicer.util.arrayFromSegmentBinaryLabelmap(seg, _sid, ref)
            return int((a > 0).sum()) if a is not None and a.size else 0
        except Exception as exc:
            return "err:%s" % str(exc)[:18]

    own, grid = count(None), count(volume)
    rows.append((name, label, layer, own, grid, sid))
    print("%-34s %-6s %-6s %-10s %-10s" % (name[:34], label, layer, own, grid))

print()
problems = []

# Two segments with one name: segmentIdFor returns the first, and the export is
# given that one -- which may be the empty one.
for name, ids in byName.items():
    if len(ids) > 1:
        problems.append("%r exists %d times (ids %s). The export uses the first."
                        % (name, len(ids), ", ".join(ids)))

# A label value is unique per layer, not per segmentation. Two segments sharing
# both is the case where one of them silently contributes nothing.
seen = {}
for name, label, layer, _own, _grid, _sid in rows:
    key = (layer, label)
    if key in seen:
        problems.append("%r and %r share label %s on layer %s"
                        % (seen[key], name, label, layer))
    seen[key] = name

for name in wanted:
    if name not in byName:
        problems.append("%r is in the protocol but not in the scene at all" % name)

for name, label, _layer, own, grid, _sid in rows:
    if name in wanted and label != "?" and int(label) != wanted[name]:
        problems.append("%r carries label %s, the protocol says %s"
                        % (name, label, wanted[name]))
    if name in wanted and own and not grid:
        problems.append("%r has %s voxels of its own but none on the source grid "
                        "-- its geometry does not line up with the volume"
                        % (name, own))

print("=== what the submission check sees ===")
path = os.path.join(tempfile.gettempdir(), "segqueue_diagnose.seg.nrrd")
try:
    counts, source, segGeom = logic.exportLabelmap(path)
    print("exported counts: %s" % counts)
    for name in wanted:
        if counts.get(name, 0) == 0:
            problems.append("%r exports as EMPTY -- this is the error you see" % name)
    print("source geometry      : %s" % (source.to_dict() if source else None))
    print("segmentation geometry: %s" % (segGeom.to_dict() if segGeom else None))
    print()
    for problem in logic.validate(counts, source, segGeom):
        print("  [%s] %s" % (problem.level, problem.message))
except Exception as exc:
    print("the export itself failed: %r" % exc)
    traceback.print_exc()
finally:
    if os.path.exists(path):
        os.unlink(path)

print()
print("=== findings ===")
if problems:
    for problem in problems:
        print("  * %s" % problem)
else:
    print("  nothing obviously wrong -- send this whole output and the draft path")
print()
print("draft on disk: %s" % (
    logic.cache.workPath(logic.assignment.assignment_id)
    if logic.assignment else "no case open"))
print("=" * 72)
