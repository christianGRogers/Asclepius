"""Round 5: what do the 17 'cut trees' of Atlas's short R1 look like on the reference side?

Atlas's per-case validation data (trillium-results/round5/atlas/results/per_case_val.json) has, per
class, tF1 and clDice that share the same precision, so clDice_c - tF1_c > 0 means reference
centreline that is predicted (with the right name) but not in a piece connected to Atlas's ostium.
Predictions stay on Trillium $SCRATCH, so this script asks the question that can be answered on CPU:
for every val case, rebuild Atlas's reference (its own proxy.make_label on the local ImageCAS mask and
ImageCAS-X names), locate Atlas's ostia (its own tf1._ostia, `thick` per class set) and the
segtrain.tf1 per-component ostia, and measure both against the ImageCAS-X centreline start points
(the expert's ostia). If the zero-recall classes sit on misplaced ostia, the 'cuts' are a metric
artefact; if the ostia are right, the model really fails to reach the ostium.

Usage: python r5_cut_anatomy.py <out.jsonl> case [case ...]
"""
import importlib.util
import json
import sys

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

REPO = '/home/user/Asclepius'
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, REPO + '/experiments/Delta')
import treelib as T  # noqa: E402
from ostium_eval import starts  # noqa: E402
from segtrain import tf1 as S  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AP = _load('atlas_proxy', REPO + '/trillium/atlas/lib/proxy.py')
AT = _load('atlas_tf1', REPO + '/trillium/atlas/lib/tf1.py')


def run(case):
    icx_id = int(case[1:]) + 1
    mpath = f'{SCR}/data/masks/{case}.nii.gz'
    lab_full, A, stats = AP.make_label(mpath, T.icx_path(case))
    sp = np.array(nib.load(mpath).header.get_zooms()[:3], float)
    idx = np.nonzero(lab_full > 0)
    m = np.ceil(4.0 / sp).astype(int)
    lo = np.maximum([i.min() for i in idx] - m, 0)
    hi = np.minimum([i.max() + 1 for i in idx] + m, lab_full.shape)
    R = lab_full[tuple(slice(a, b) for a, b in zip(lo, hi))].copy()
    del lab_full
    Rm = R > 0
    rsk = skeletonize(Rm)
    rad = ndi.distance_transform_edt(Rm, sampling=sp)
    roots = AT._ostia(R, rsk, rad, sp)
    mine = S.find_ostia(R, sp)
    comps, n = S.components(Rm)
    sizes = np.bincount(comps.ravel())
    # expert ostia: ImageCAS-X centreline start points, world RAS -> crop voxel
    true = {}
    for side in ('left', 'right'):
        p = f'{SCR}/work/Bridge/icx/centerlines/{icx_id}.coronary_{side}_centerline.vtk'
        try:
            P = np.array(starts(p))
        except Exception:  # noqa
            P = np.zeros((0, 3))
        if len(P):
            true[side] = (np.linalg.inv(A) @ np.c_[P, np.ones(len(P))].T).T[:, :3] - lo
    d_ref = ndi.distance_transform_edt(~Rm, sampling=sp)
    out = dict(case=case, ref_components=int(n), comp_sizes=sorted(sizes[1:].tolist(), reverse=True),
               classes={int(c): int((R == c).sum()) for c in range(1, 5)}, lm_present=bool((R == 1).any()),
               proxy=dict(near=stats.get('near_frac'), geo=stats.get('geodesic_frac')),
               true={s: [[round(float(v), 1) for v in p] for p in P] for s, P in true.items()},
               true_to_ref_mm={s: [round(float(d_ref[tuple(np.clip(np.round(p).astype(int), 0,
                                                                      np.array(R.shape) - 1))]), 2) for p in P]
                               for s, P in true.items()},
               atlas_roots=[], mine=[])

    def judge(pt):
        pt = np.asarray(pt, float)
        c = int(R[tuple(pt.astype(int))])
        side = 'right' if c == 4 else 'left'
        P = true.get(side, np.zeros((0, 3)))
        d = float(np.min(np.linalg.norm((P - pt) * sp, axis=1))) if len(P) else float('nan')
        return dict(point=[int(v) for v in pt], cls=c, side=side, d_true_mm=round(d, 2),
                    radius_mm=round(float(rad[tuple(pt.astype(int))]), 2),
                    comp=int(comps[tuple(pt.astype(int))]))
    out['atlas_roots'] = [judge(r) for r in roots]
    out['mine'] = [dict(judge(o.point), tree=o.tree) for o in mine.ostia]
    return out


if __name__ == '__main__':
    out = sys.argv[1]
    with open(out, 'a') as f:
        for c in sys.argv[2:]:
            try:
                r = run(c)
            except Exception as e:  # noqa
                r = dict(case=c, error=repr(e))
            f.write(json.dumps(r) + '\n')
            f.flush()
            print(c, r.get('error', ''), flush=True)
