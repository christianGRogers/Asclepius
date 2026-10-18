"""Read an ImageCAS-X centreline VTK (legacy 5.1 binary polydata): points (LPS world mm), per-point segment label,
polylines, and the released start points (vertices flagged `start_points`: degree-1 vertices within 5 mm of a
TotalSegmentator aorta, ImageCAS-X "Postprocessing"). Shared by the Round 9 scripts."""
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n


def read(path):
    r = vtk.vtkPolyDataReader(); r.SetFileName(path); r.ReadAllScalarsOn(); r.ReadAllFieldsOn(); r.Update()
    p = r.GetOutput()
    pts = v2n(p.GetPoints().GetData()).astype(float)
    lab = v2n(p.GetPointData().GetArray('segment_label'))
    st = p.GetPointData().GetArray('start_points')
    starts = [int(k) for k in (v2n(st).nonzero()[0] if st is not None else [])]
    fields = {}
    fd = p.GetFieldData()
    for i in range(fd.GetNumberOfArrays()):
        a = fd.GetAbstractArray(i)
        if a is None:
            continue
        n = a.GetNumberOfTuples() * a.GetNumberOfComponents()
        fields[a.GetName()] = [a.GetVariantValue(j).ToString() for j in range(n)]
    lines = []
    ids = vtk.vtkIdList(); cells = p.GetLines(); cells.InitTraversal()
    while cells.GetNextCell(ids):
        lines.append([ids.GetId(k) for k in range(ids.GetNumberOfIds())])
    return pts, lab, fields, lines, starts


def endpoint_degree(lines):
    deg = {}
    for l in lines:
        for e in (l[0], l[-1]):
            deg[e] = deg.get(e, 0) + 1
    return deg
