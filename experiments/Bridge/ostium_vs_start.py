"""Namer's left ostium (chosen on our THICK masks, no image) vs ImageCAS-X's left centreline start point
(degree-1 centreline vertex within 5 mm of a TotalSegmentator aorta, reviewed by ImageCAS-X analysts):
an aorta-contact truth that does not come from ImageCAS-X's labels-projection used elsewhere.
usage: ostium_vs_start.py EV.jsonl CL_DIR DEVSET"""
import sys, os, json, glob, numpy as np, nibabel as nib
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools'); from girder import mask_path
ev, cl, devf = sys.argv[1:4]
dev = set(open(devf).read().replace('\n', '').split(','))
out = []
for l in open(ev):
    r = json.loads(l)
    if 'ostium_vox' not in r:
        continue
    f = f"{cl}/{int(r['case'][1:]) + 1}.coronary_left_centerline.vtk"
    if not os.path.exists(f):
        continue
    rd = vtk.vtkPolyDataReader(); rd.SetFileName(f); rd.Update(); p = rd.GetOutput()
    P = v2n(p.GetPoints().GetData()).astype(float); s = v2n(p.GetPointData().GetArray('start_points'))
    S = P[s > 0] * np.array([-1, -1, 1])  # LPS -> RAS
    A = nib.load(mask_path(r['case'])).affine
    o = A[:3, :3] @ np.array(r['ostium_vox']) + A[:3, 3]
    d = float(np.min(np.linalg.norm(S - o, axis=1)))
    out.append((r['case'], d, r['case'] in dev))
d = np.array([x[1] for x in out]); h = np.array([not x[2] for x in out])
print('cases', len(d), 'median %.1f mm; <=5 mm %.3f; <=10 mm %.3f' % (np.median(d), (d <= 5).mean(), (d <= 10).mean()))
print('held-out', h.sum(), '<=5 mm %.3f <=10 mm %.3f' % ((d[h] <= 5).mean(), (d[h] <= 10).mean()))
print('worst', sorted(out, key=lambda x: -x[1])[:8])
