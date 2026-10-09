"""Round 5 CPU diagnosis of the short-R1 val results, reference side only (predictions stay on $SCRATCH).
Per val case: projected proxy reference (src/segtrain/proxy), ostia chosen by the three provisional rules
(Atlas trillium tf1 'thick', Bridge trillium tf1, Delta src find_ostia 'thick'), the ImageCAS-X start points as
truth, and ImageCAS-X vessel pieces outside the ImageCAS mask (candidate unannotated vessels -> 'FP')."""
import json, os, sys
import numpy as np, nibabel as nib
from scipy import ndimage as ndi
sys.path.insert(0, '/home/user/Asclepius/src'); sys.path.insert(0, '/home/user/Asclepius/trillium/atlas/lib')
from segtrain.proxy import project_names
from segtrain.tf1 import find_ostia
import tf1 as atf
sys.path.insert(0, '/home/user/Asclepius/trillium/bridge/py')
import importlib.util
spec = importlib.util.spec_from_file_location('btf', '/home/user/Asclepius/trillium/bridge/py/tf1.py'); btf = importlib.util.module_from_spec(spec); spec.loader.exec_module(btf)
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
CL = f'{SCR}/work/Bridge/icx/centerlines'

def starts(path):
    if not os.path.exists(path): return None
    r = vtk.vtkPolyDataReader(); r.SetFileName(path); r.Update(); p = r.GetOutput()
    P = v2n(p.GetPoints().GetData()).astype(float); s = v2n(p.GetPointData().GetArray('start_points'))
    return P[s > 0] * np.array([-1, -1, 1])

def run(case):
    n = int(case[1:]) + 1
    mi = nib.load(f'{SCR}/data/masks/{case}.nii.gz'); ii = nib.load(f'{SCR}/work/Atlas/icx/{n}.coronary.nii.gz')
    A = mi.affine; sp = np.array(mi.header.get_zooms()[:3], float)
    mask = np.asarray(mi.dataobj) > 0; icx = np.asarray(ii.dataobj).astype(np.uint8)
    u = mask | (icx > 0); idx = np.nonzero(u); m = np.ceil(8 / sp).astype(int)
    lo = np.maximum([i.min() for i in idx] - m, 0); hi = np.minimum([i.max() + 1 for i in idx] + m, mask.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi)); mask, icx = mask[sl], icx[sl]
    ref, st = project_names(mask, icx, sp)
    out = dict(case=case, affine_equal=bool(np.allclose(A, ii.affine, atol=1e-3)))
    # truth
    Ai = np.linalg.inv(A); truth = {}
    for side in ('left', 'right'):
        s = starts(f'{CL}/{n}.coronary_{side}_centerline.vtk')
        if s is not None and len(s):
            v = (Ai @ np.c_[s, np.ones(len(s))].T).T[:, :3] - lo
            truth[side] = v[0]
    # rules
    rsk = atf.skeletonize(ref > 0); rad = ndi.distance_transform_edt(ref > 0, sampling=sp)
    a_roots = atf._ostia(ref, rsk, rad, sp)
    b = btf.Ref(ref, sp); b_roots = b.roots
    d = find_ostia(ref, sp); d_roots = [o.point for o in d.ostia]
    def side_of(pt):
        return 'right' if ref[tuple(int(x) for x in pt)] == 4 else 'left'
    def dist(p, q): return float(np.linalg.norm((np.asarray(p, float) - np.asarray(q, float)) * sp))
    res = {}
    for name, roots in (('atlas', a_roots), ('bridge', b_roots), ('delta', d_roots)):
        for rt in roots:
            sd = side_of(rt); key = f'{name}_{sd}'
            if key in res: key += '_2'
            res[key] = dict(pt=[int(x) for x in rt], r_mm=float(rad[tuple(rt)]),
                            to_truth_mm=dist(rt, truth[sd]) if sd in truth else None)
    out['roots'] = res
    # RCA endpoints vs the left start point: the true RCA ostium sits on the aortic root, near the left one
    pts0 = np.argwhere(rsk); lab0 = ref[tuple(pts0.T)]
    nb0 = ndi.convolve(rsk.astype(np.uint8), np.ones((3, 3, 3), np.uint8), mode='constant') - 1
    e = pts0[(lab0 == 4) & (nb0[tuple(pts0.T)] == 1)]
    if len(e) and 'left' in truth:
        dl = [dist(p, truth['left']) for p in e]
        h = e[int(np.argmin(dl))]
        out['rca_heur'] = dict(pt=[int(x) for x in h], to_left_mm=float(min(dl)), r_mm=float(rad[tuple(h)]),
                               to_truth_mm=dist(h, truth['right']) if 'right' in truth else None)
        for name in ('atlas', 'bridge', 'delta'):
            k = f'{name}_right'
            if k in res:
                res[k]['to_heur_mm'] = dist(res[k]['pt'], h)
                res[k]['to_left_mm'] = dist(res[k]['pt'], truth['left'])
    # endpoints of the RCA skeleton: how many, and radius ranks near the thickest
    pts = np.argwhere(rsk); lab = ref[tuple(pts.T)]
    nb = ndi.convolve(rsk.astype(np.uint8), np.ones((3, 3, 3), np.uint8), mode='constant') - 1
    deg = nb[tuple(pts.T)]
    for c, nm in ((4, 'rca'), (1, 'lm')):
        e = pts[(lab == c) & (deg == 1)]
        out[f'n_end_{nm}'] = int(len(e))
    # reference components and ImageCAS-X pieces outside the (1 mm dilated) mask
    S26 = np.ones((3, 3, 3), bool)
    out['ref_components'] = int(ndi.label(mask, structure=S26)[1])
    rc, nrc = ndi.label(mask, structure=S26); sz = np.bincount(rc.ravel())[1:]
    out['ref_comp_sizes'] = sorted([int(x) for x in sz], reverse=True)[:6]
    grown = ndi.binary_dilation(mask, structure=atf._ball(1.0, sp))
    extra = (icx > 0) & ~grown
    el, ne = ndi.label(extra, structure=S26)
    if ne:
        esz = np.bincount(el.ravel())[1:]
        # pieces whose ICX component (whole ICX tree piece) does not touch the mask at all
        il, ni = ndi.label(icx > 0, structure=S26)
        touch = set(np.unique(il[mask]).tolist()) - {0}
        isz = np.bincount(il.ravel())
        detached = [int(isz[k]) for k in range(1, ni + 1) if k not in touch and isz[k] >= 100]
    else:
        esz = np.array([]); detached = []
    out['icx_outside_vox'] = int(extra.sum()); out['icx_outside_pieces_ge100'] = int((esz >= 100).sum())
    out['icx_detached_pieces_ge100'] = len(detached)
    out['icx_outside_frac'] = float(extra.sum() / max((icx > 0).sum(), 1))
    out['mask_vox'] = int(mask.sum()); out['sp'] = sp.tolist(); out['near_frac'] = st.near_frac
    return out

if __name__ == '__main__':
    outp = sys.argv[1]
    done = set()
    if os.path.exists(outp):
        done = {json.loads(l)['case'] for l in open(outp)}
    for c in sys.argv[2:]:
        if c in done: continue
        try: r = run(c)
        except Exception as e: r = dict(case=c, error=repr(e))
        with open(outp, 'a') as f: f.write(json.dumps(r) + '\n')
        print(c, flush=True)
