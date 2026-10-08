"""Aorta-preferred ostium (Round 3 ruling §5, Bridge): does preferring left-tree endpoints that touch a large
contrast pool (aortic root stand-in, Delta's `blood_pool` rule: CT > 200 HU, 3 mm opening, >= 2 cm^3, coronary
mask excluded) fix the namer's ostium errors?

Per case with a cached CT + ImageCAS-X labels: frozen namer (ramus -> LCx, 4 mm naming bridges) with
  learned       : learned ostium + plausibility re-rank (as frozen)
  learned_pool  : same, + logit bonus 3 for endpoints within 3 mm of the pool
Scored by (i) distance of the chosen left ostium to ImageCAS-X's left start point (aorta-contact truth) and
(ii) naming vs ImageCAS-X names projected onto our thick mask (IM -> LCx; all-4 >= 0.8, swaps).
usage: pool_ostium.py EXDIR CL_DIR OSTIUM_W.json DEVSET OUT.jsonl
"""
import sys, os, glob, json
import numpy as np, nibabel as nib, cc3d
from scipy import ndimage as ndi
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import label as Lb
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'


def blood_pool(ct, sp, exclude, thr_hu=200.0, open_mm=3.0, min_cc_mm3=2000.0):
    """Delta's rule (experiments/Delta/treelib.py blood_pool), re-implemented here."""
    g = ndi.gaussian_filter(ct.astype(np.float32), sigma=0.7 / np.asarray(sp))
    m = (g > thr_hu) & ~ndi.binary_dilation(exclude, iterations=2)
    er = ndi.distance_transform_edt(m, sampling=sp) > open_mm
    m = ndi.distance_transform_edt(~er, sampling=sp) <= open_mm
    lab, n = cc3d.connected_components(m, connectivity=26, return_N=True)
    if n == 0:
        return m
    sz = np.bincount(lab.ravel()) * float(np.prod(sp)); sz[0] = 0
    return np.isin(lab, np.nonzero(sz >= min_cc_mm3)[0])


def start_point(cl_dir, case):
    f = f'{cl_dir}/{int(case[1:]) + 1}.coronary_left_centerline.vtk'
    if not os.path.exists(f):
        return None
    r = vtk.vtkPolyDataReader(); r.SetFileName(f); r.Update(); p = r.GetOutput()
    P = v2n(p.GetPoints().GetData()).astype(float); s = v2n(p.GetPointData().GetArray('start_points'))
    return P[s > 0] * np.array([-1, -1, 1])


def d1b_dice(C):
    C = np.array(C, float); C[3] += C[5]; M = C[1:5, 1:5]
    out = {}
    for k in range(4):
        den = M[k].sum() + M[:, k].sum()
        if den > 0:
            out[k] = 2 * M[k, k] / den
    return out


if __name__ == '__main__':
    ex, cl, ostw, devf, outp = sys.argv[1:6]
    w = json.load(open(ostw)); Lb.OSTIUM_W = dict(F=w['F'], mean=np.array(w['mean']), scale=np.array(w['scale']), coef=np.array(w['coef']))
    Lb.RAMUS = 'LCx'; Lb.BRIDGE = 4.0
    dev = set(open(devf).read().replace('\n', '').split(','))
    cts = sorted(os.path.basename(p)[:5] for p in glob.glob(SCR + '/data/ct/c*.nii.gz'))
    done = {json.loads(l)['case'] for l in open(outp)} if os.path.exists(outp) else set()
    with open(outp, 'a') as fo:
        for c in cts:
            if c in done:
                continue
            f = os.path.join(ex, c + '.npz')
            S = start_point(cl, c)
            if not os.path.exists(f) or S is None:
                continue
            d = Lb.load_case(f)
            if d['icx_stats'] is None:
                continue
            m_img = nib.load(f'{SCR}/data/masks/{c}.nii.gz'); A = m_img.affine
            sp = d['zooms']; shape = np.array(m_img.shape)
            mv = np.ceil(15.0 / sp).astype(int)   # crop from the skeleton's extent (avoids a full float64 mask in RAM)
            lo = np.maximum(np.floor(d['V'].min(0)).astype(int) - mv, 0)
            hi = np.minimum(np.ceil(d['V'].max(0)).astype(int) + mv + 1, shape)
            sl = tuple(slice(a, b) for a, b in zip(lo, hi))
            msk = (np.asanyarray(m_img.dataobj[sl]) > 0.5)
            ct = np.asanyarray(nib.load(f'{SCR}/data/ct/{c}.nii.gz').dataobj[sl]).astype(np.int16)
            pool = blood_pool(ct, sp, msk); del ct
            dpool = ndi.distance_transform_edt(~pool, sampling=sp) if pool.any() else np.full(pool.shape, 1e9)

            def hook(dd, ef):
                for fe in ef:
                    v = np.clip(np.round(dd['V'][fe['e']] - lo).astype(int), 0, np.array(pool.shape) - 1)
                    fe['dpool'] = float(dpool[tuple(v)])
            Lb.EP_HOOK = hook
            row = dict(case=c, dev=c in dev, pool_ml=float(pool.sum() * np.prod(sp) / 1000))
            for meth in ('rerank_learned', 'rerank_learned_pool'):
                lab, olab, res, ef = Lb.label_case(d, meth)
                o = A[:3, :3] @ np.array(res['ostium_vox']) + A[:3, 3]
                dice = d1b_dice(Lb.confusion(d, lab, olab))
                row[meth] = dict(ost_err=float(np.min(np.linalg.norm(S - o, axis=1))),
                                 all_ok=bool(all(v >= 0.8 for v in dice.values())), swap=bool(any(v < 0.5 for v in dice.values())),
                                 lm_len=res.get('L_lm_len'))
            ends_touch = sum(1 for fe in ef if fe.get('dpool', 1e9) <= 3)
            row['n_ends_touching_pool'] = ends_touch; row['n_ends'] = len(ef)
            fo.write(json.dumps(row) + '\n'); fo.flush()
            print(c, {k: (round(v['ost_err'], 1), v['all_ok']) for k, v in row.items() if isinstance(v, dict)}, ends_touch, flush=True)
