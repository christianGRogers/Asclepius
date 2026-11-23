"""Round 2 ruling §5 item 5: false-fail of F-A22's stage-2 numbers (L1 theft <= 0.02, L2 far paint 30 mm in >= 95 %
of cases, K1 <= 0.05), on ImageCAS-X references of the 620 TRAINING cases treated as predictions.

(a) The reference itself as the prediction: it holds no stage-2 voxel, so L1 = 0, L2 passes and K1 = 0 in every
    case. That is a necessary check, not an informative one: the lines bite only on stage-2 paint.
(b) A CORRECT stage-2 model, simulated: the reference plus straight synthetic tubes where the six untraced classes
    leave their hosts (S1-S3 off the proximal LAD at 10/25/40 mm from its start, heading into the heart; Conus and SN
    off the proximal RCA at 5/12 mm; RMA off the RCA at 40 mm (Euclidean from its ostium)). Every tube is a correct branch of length L (swept),
    radius R_MM. Straight tubes are the worst case for L2 (a curved branch's tip stays nearer its host).
    Two junction models:
      out   tube voxels are painted only where the reference is background (a model that never paints a traced voxel);
      junc  the tube also paints the host's lumen along its first JUNC_MM (it starts at the host centreline), as a
            model trained on pool reads would under D47 Q4 (a child drawn over its parent trains as the child).
Measures, exactly as F-A22 words them:
  L1 per parent group (LAD+D1-D3, LCx+OM1/OM2/Ramus, RCA+PDA/PLB): share of the group's reference centreline points
     whose nearest predicted voxel within 1.5 mm is a stage-2 class (the scorer's naming rule);
  L2 per case: the largest distance (mm) from a stage-2 voxel to predicted stage-1 coronary foreground; also the
     proposed L2' (largest distance from a stage-2 26-COMPONENT's nearest voxel to stage-1 foreground: an island);
  K1 per class: share of its predicted voxels inside the reference's traced lumen.
No array beyond the case's own box is built: tubes are point sets in voxel index space, distances by KD-tree.
Usage: python3 stage2_sim.py <icx_dir> <out.jsonl> [n_cases=120] [n_proc=3]"""
import hashlib, json, os, sys
from multiprocessing import Pool
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1f_scorer as S  # noqa: E402
import importlib.util  # noqa: E402
_sp = importlib.util.spec_from_file_location('atlas_scorer', os.path.join(HERE, '../../Atlas/j1f_r2/j1f_scorer.py'))
A = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(A)

R_MM = 0.6
JUNC_MM = 2.5
LENGTHS = (10, 20, 30, 40, 50)
GROUPS = {'LAD': (2, 5, 6, 7), 'LCx': (3, 8, 9, 10), 'RCA': (4, 11, 12)}
S2 = {'S1': ('LAD', 10), 'S2': ('LAD', 25), 'S3': ('LAD', 40), 'Conus': ('RCA', 5), 'SN': ('RCA', 12),
      'RMA': ('RCA', 40)}
INWARD = {'S1': 1, 'S2': 1, 'S3': 1, 'Conus': -1, 'SN': 1, 'RMA': -1}   # +1 toward the tree's centroid, -1 away


def trunk_path(ref, cls, sk, sp):
    """Skeleton points of one trunk, ordered by Euclidean distance (mm) from its ostial end. The ostial end is the
    trunk's skeleton point nearest the left main (or the LAD/LCx voxels nearest the aortic root when there is no LM):
    both ostia sit on the aortic root, while the distal RCA and LAD lie far from it."""
    pts = np.argwhere(sk & (ref == cls))
    if len(pts) < 5:
        return None, None
    anchor = np.argwhere(ref == 1) if (ref == 1).any() else np.argwhere(np.isin(ref, (2, 3)))
    if not len(anchor):
        return None, None
    dist_to_anchor, _ = cKDTree(anchor * sp).query(pts * sp)
    start = pts[int(np.argmin(dist_to_anchor))]
    d = np.linalg.norm((pts - start) * sp, axis=1)
    o = np.argsort(d)
    return pts[o], d[o]


def tube(origin, direction, L, sp, r=R_MM):
    """Voxel-index points of a straight tube (mm geometry) from origin (index) along direction (mm unit)."""
    o = origin * sp
    step = min(sp) / 2
    ts = np.arange(0, L + 1e-9, step)
    axis = o[None] + ts[:, None] * direction[None]
    rr = int(np.ceil(r / min(sp))) + 1
    off = np.argwhere(np.ones((2 * rr + 1,) * 3, bool)) - rr
    cand = (np.round(axis / sp).astype(int)[:, None, :] + off[None]).reshape(-1, 3)
    cand = np.unique(cand, axis=0)
    # keep voxels within r of the axis segment
    pm = cand * sp
    v = pm - o
    t = np.clip(v @ direction, 0, L)
    dist = np.linalg.norm(v - t[:, None] * direction[None], axis=1)
    keep = dist <= r
    return cand[keep], t[keep]


def one(args):
    d, c = args
    im = nib.load(os.path.join(d, 'segmentations', f'{int(c[1:]) + 1}.coronary.nii.gz'))
    icx = np.asarray(im.dataobj).astype(np.uint8)
    sp = np.array(im.header.get_zooms()[:3], float)
    nz = np.argwhere(icx > 0)
    lo, hi = np.maximum(nz.min(0) - 4, 0), nz.max(0) + 5
    icx = icx[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    ref, _ = A.stage1_labels(icx, sp)
    ref = np.where(ref == S.IGNORE, 0, ref)
    fg = ref > 0
    sk = S._skeleton(fg)
    centroid = np.argwhere(fg).mean(0)
    fg_pts = np.argwhere(fg)
    fg_tree = cKDTree(fg_pts * sp)
    fg_set = set(map(tuple, fg_pts))
    # reference centreline points per group, and the stage-1 predicted voxels' KD-tree
    grp_pts = {g: np.argwhere(sk & np.isin(ref, v)) for g, v in GROUPS.items()}
    paths = {'LAD': trunk_path(ref, 2, sk, sp), 'RCA': trunk_path(ref, 4, sk, sp)}
    rng = np.random.default_rng(int(hashlib.sha256(c.encode()).hexdigest()[:8], 16))
    out = {'case': c, 'n_centreline': {g: int(len(v)) for g, v in grp_pts.items()}, 'runs': {}}
    origins = {}
    for k, (host, at) in S2.items():
        pts, dd = paths[host]
        if pts is None or dd[-1] < at:
            continue
        i = int(np.searchsorted(dd, at))
        p = pts[i]
        nb = pts[max(i - 6, 0):i + 7] * sp
        tan = np.linalg.svd(nb - nb.mean(0))[2][0] if len(nb) > 2 else np.array([1., 0, 0])
        w = (centroid - p) * sp * INWARD[k]
        w = w - (w @ tan) * tan
        if np.linalg.norm(w) < 1e-6:
            w = np.cross(tan, rng.normal(size=3))
        w /= np.linalg.norm(w)
        origins[k] = (p, w)
    for L in LENGTHS:
        for mode in ('out', 'junc'):
            painted = {}
            for k, (p, w) in origins.items():
                vox, t = tube(p.astype(float), w, L, sp)
                inref = np.array([tuple(v) in fg_set for v in vox]) if len(vox) else np.zeros(0, bool)
                if mode == 'out':
                    keep = ~inref
                else:
                    keep = ~inref | (t <= JUNC_MM)
                painted[k] = (vox[keep], inref[keep])
            allp = [v for v, _ in painted.values() if len(v)]
            if not allp:
                continue
            s2 = np.unique(np.concatenate(allp), axis=0)
            s2_set = set(map(tuple, s2))
            # stage-1 predicted voxels = reference foreground minus voxels painted stage-2
            keep1 = np.array([tuple(v) not in s2_set for v in fg_pts])
            p1 = fg_pts[keep1]
            t1, t2 = cKDTree(p1 * sp), cKDTree(s2 * sp)
            l1 = {}
            for g, q in grp_pts.items():
                if not len(q):
                    continue
                d1, _ = t1.query(q * sp); d2, _ = t2.query(q * sp)
                stolen = (np.minimum(d1, d2) <= S.TOL_MM) & (d2 < d1)
                l1[g] = [int(stolen.sum()), int(len(q))]
            dfar, _ = t1.query(s2 * sp)
            # L2': per stage-2 26-component (on the index grid), the distance of its NEAREST voxel to stage-1 fg
            mn = s2.min(0); box = np.zeros(tuple(s2.max(0) - mn + 1), bool); box[tuple((s2 - mn).T)] = True
            lab, n = ndi.label(box, np.ones((3, 3, 3), bool))
            comp = lab[tuple((s2 - mn).T)]
            island = max(float(dfar[comp == j].min()) for j in range(1, n + 1))
            k1 = {k: [int(ir.sum()), int(len(v))] for k, (v, ir) in painted.items()}
            out['runs'][f'{mode}_L{L}'] = {'L1': l1, 'L2_max_mm': round(float(dfar.max()), 2),
                                            'L2_island_mm': round(island, 2), 'K1': k1}
    return out


def main(d, outp, n, npr):
    ids = sorted(json.load(open(os.path.join(d, 'split.json')))['train620'])
    assert len(ids) == 620
    pick = sorted(ids, key=lambda c: hashlib.sha256(('asclepius-j1f-r3-bridge-stage2:' + c).encode()).hexdigest())[:n]
    done = {json.loads(l)['case'] for l in open(outp)} if os.path.exists(outp) else set()
    with open(outp, 'a') as f, Pool(npr) as p:
        for i, r in enumerate(p.imap_unordered(one, [(d, c) for c in pick if c not in done])):
            f.write(json.dumps(r) + '\n'); f.flush()
            print(i, r['case'], flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], a[1], int(a[2]) if len(a) > 2 else 120, int(a[3]) if len(a) > 3 else 3)
