"""Round 9 (Delta): is the pinned tree-F1 ready to score icx4 against its own reference, without a CT?

Per non-sealed ImageCAS-X case (labels collapsed to LM/LAD/LCx/RCA exactly as icx4 trains on them,
trillium/icx4/lib/territory.py):

  Q1  reference audit for tF1: classes present, pieces per class, "Other" voxels re-assigned, classes with no
      centreline (A1c fallback cases), LM centreline length;
  Q2  expert ostium: ImageCAS-X's released centrelines give a left ostium (free end of the LM line) and a right
      ostium (free end of the RCA line). Passed to segtrain.tf1.find_ostia as a pseudo-aorta (a 1 mm ball at each
      expert ostium), the A1 rule of record ("reference centreline voxel nearest the aorta") becomes "nearest the
      expert ostium" with no change to tf1.py. Compared with the CT-free "thick" rule;
  Q3  a cut the metric must see: remove all reference voxels within 2.5 mm of the expert centreline point 3 mm
      (left) and 15 mm (right) downstream of each ostium, i.e. a ~5 mm gap (> D3's 1.5 mm). Dice (as
      trillium/icx4/lib/score.py computes it) vs tF1 with thick ostia vs tF1 with expert ostia.

Uses src/segtrain/tf1.py at the pinned hash (checked at start). Output: one JSON line per case.
Usage: r9_icx4_reference.py <data_dir> <out.jsonl> [n_proc]
"""
import hashlib, json, os, sys
from multiprocessing import Pool

import nibabel as nib
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))
sys.path.insert(0, os.path.join(ROOT, 'trillium', 'icx4', 'lib'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segtrain import tf1 as T  # noqa: E402
from territory import to_four  # noqa: E402
from r9_vtkcl import read, endpoint_degree  # noqa: E402

PIN = '24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254'
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
Q3_CASES = set()  # filled in main() from <data_dir>/val.txt
MARGIN = 12  # voxels of crop margin around the tree (skeletons are local; the crop changes nothing)


def dice(a, b):
    s = int(a.sum()) + int(b.sum())
    return None if s == 0 else 2.0 * int((a & b).sum()) / s


def expert_ostia(path_l, path_r, inv_aff):
    """Expert ostia in voxel coordinates (float) and the centreline polylines (voxel coords) for the cut."""
    out = {}
    for side, path, lab_root in (('left', path_l, 1), ('right', path_r, 9)):
        if not os.path.exists(path):
            continue
        pts, lab, _, lines, _starts = read(path)
        vox = nib.affines.apply_affine(inv_aff, pts * [-1, -1, 1])  # VTK points are LPS; nibabel is RAS
        deg = endpoint_degree(lines)
        leaves = [e for e, d in deg.items() if d == 1 and lab[e] == lab_root]
        out[side] = {'n_candidates': len(leaves), 'vox': vox, 'lines': lines, 'labels': lab, 'leaves': leaves}
    # left: the LM leaf (none when there is no LM); right: the RCA leaf nearest the left ostium if several
    res = {}
    lft = out.get('left')
    if lft and len(lft['leaves']) >= 1:
        res['left'] = (lft['leaves'][0], lft)
    rgt = out.get('right')
    if rgt and rgt['leaves']:
        cand = rgt['leaves']
        if len(cand) > 1 and 'left' in res:
            lo = lft['vox'][res['left'][0]]
            cand = sorted(cand, key=lambda e: np.linalg.norm(rgt['vox'][e] - lo))
        res['right'] = (cand[0], rgt)
    return res, {s: out[s]['n_candidates'] for s in out}


def path_point(info, leaf, dist_mm, sp):
    """The expert centreline point dist_mm (arc length) downstream of the leaf, following the polyline that starts
    or ends at the leaf and continuing through junctions along the longest remaining line."""
    vox, lines = info['vox'], info['lines']
    cur, walked, used = leaf, 0.0, set()
    for _ in range(50):
        cands = [(k, l if l[0] == cur else l[::-1]) for k, l in enumerate(lines)
                 if k not in used and cur in (l[0], l[-1])]
        if not cands:
            return vox[cur]
        k, line = max(cands, key=lambda kl: len(kl[1]))
        used.add(k)
        for a, b in zip(line[:-1], line[1:]):
            step = float(np.linalg.norm((vox[b] - vox[a]) * sp))
            if walked + step >= dist_mm:
                return vox[b]
            walked += step
        cur = line[-1]
    return vox[cur]


def one(args):
    data, i = args
    seg = f'{data}/{i}.coronary.nii.gz'
    img = nib.load(seg)
    raw = np.asarray(img.dataobj).astype(np.int64)
    sp = np.asarray(img.header.get_zooms()[:3], float)
    ref_full = to_four(raw, sp).astype(np.uint8)
    r = {'case': f'c{i - 1:04d}', 'icx_id': i, 'spacing': sp.round(4).tolist(),
         'other_voxels': int((raw == 14).sum())}
    if not (ref_full > 0).any():
        r['empty'] = True
        return r
    # crop
    nz = np.argwhere(ref_full > 0)
    lo = np.maximum(nz.min(0) - MARGIN, 0)
    hi = np.minimum(nz.max(0) + MARGIN + 1, ref_full.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    ref = ref_full[sl]
    r['present'] = [NAMES[c] for c in (1, 2, 3, 4) if (ref == c).any()]
    r['pieces'] = {NAMES[c]: T.components(ref == c)[1] for c in (1, 2, 3, 4) if (ref == c).any()}
    r['trees'] = T.components(ref > 0)[1]
    cl = T._Centreline(ref > 0, sp)
    lab_cl = ref[tuple(cl.pts.T)]
    r['centreline_voxels'] = {NAMES[c]: int((lab_cl == c).sum()) for c in (1, 2, 3, 4)}
    r['classes_without_centreline'] = [NAMES[c] for c in (1, 2, 3, 4)
                                       if (ref == c).any() and not (lab_cl == c).any()]
    # LM centreline length ~ voxels x mean step
    r['lm_centreline_mm'] = round(float((lab_cl == 1).sum() * sp.mean()), 1)

    inv = np.linalg.inv(img.affine)
    ex, ncand = expert_ostia(f'{data}/{i}.coronary_left_centerline.vtk',
                             f'{data}/{i}.coronary_right_centerline.vtk', inv)
    r['expert_leaf_candidates'] = ncand
    pseudo = np.zeros(ref.shape, bool)
    ost_vox = {}
    for side, (leaf, info) in ex.items():
        v = info['vox'][leaf] - lo
        ost_vox[side] = v
        ball = T._ball(1.0, sp)
        c = np.round(v).astype(int)
        h = np.array(ball.shape) // 2
        w = tuple(slice(max(c[k] - h[k], 0), min(c[k] + h[k] + 1, ref.shape[k])) for k in range(3))
        bw = ball[tuple(slice(w[k].start - (c[k] - h[k]), w[k].stop - (c[k] - h[k])) for k in range(3))]
        pseudo[w] |= bw
        # distance from the expert ostium to the nearest reference centreline voxel
        r[f'{side}_expert_to_centreline_mm'] = round(float(np.min(np.linalg.norm((cl.pts - v) * sp, axis=1))), 2)
    thick = T.find_ostia(ref, sp, _centreline=cl)
    expert = T.find_ostia(ref, sp, aorta=pseudo, _centreline=cl) if pseudo.any() else None

    def summ(rep):
        return [{'side': o.side, 'rule': o.rule, 'point': list(o.point), 'flagged': o.flagged,
                 'disagreement_mm': round(o.disagreement_mm, 2), 'tree': o.tree} for o in rep.ostia]
    r['ostia_thick'] = summ(thick)
    r['ostia_expert'] = summ(expert) if expert else None
    # thick-rule ostium vs expert ostium, per side (nearest thick ostium to each expert ostium)
    for side, v in ost_vox.items():
        d = [float(np.linalg.norm((np.array(o.point) - v) * sp)) for o in thick.ostia]
        r[f'{side}_thick_vs_expert_mm'] = round(min(d), 2) if d else None

    if not Q3_CASES or i not in Q3_CASES:
        return r
    # Q3: the cut (ImageCAS-X val cases only: three tree_f1 calls cost ~45 s of CPU per case)
    pred = ref.copy()
    cuts = {}
    for side, dist in (('left', 3.0), ('right', 15.0)):
        if side not in ex:
            continue
        leaf, info = ex[side]
        info = dict(info, vox=info['vox'] - lo)
        p = path_point(info, leaf, dist, sp)
        cuts[side] = p
        g = np.ogrid[tuple(slice(0, s) for s in ref.shape)]
        d2 = sum(((g[k] - p[k]) * sp[k]) ** 2 for k in range(3))
        pred[d2 <= 2.5 ** 2] = 0
    r['cut_sides'] = sorted(cuts)
    r['cut_removed_voxels'] = int(((ref > 0) & (pred == 0)).sum())
    r['dice_cut'] = {NAMES[c]: dice(pred == c, ref == c) for c in (1, 2, 3, 4) if (ref == c).any()}
    r['dice_cut_tree'] = dice(pred > 0, ref > 0)
    t_self = T.tree_f1(ref, ref, sp, ostia=expert or thick)
    r['tf1_self'] = round(t_self.tf1, 4)
    for name, rep in (('thick', thick), ('expert', expert)):
        if rep is None:
            continue
        t = T.tree_f1(ref, pred, sp, ostia=rep)
        r[f'tf1_cut_{name}'] = {NAMES[c]: round(v, 4) for c, v in t.per_class.items()}
        r[f'tf1_cut_{name}_macro'] = round(t.tf1, 4)
    return r


def main():
    data, out = sys.argv[1], sys.argv[2]
    nproc = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    h = hashlib.sha256(open(os.path.join(ROOT, 'src/segtrain/tf1.py'), 'rb').read()).hexdigest()
    assert h == PIN, f'tf1.py hash {h} != pinned {PIN}'
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)['icx_id'] for l in open(out)}
    ids = sorted(int(f.split('.')[0]) for f in os.listdir(data) if f.endswith('.coronary.nii.gz')
                 and os.path.exists(f'{data}/{f.split(".")[0]}.coronary_right_centerline.vtk'))
    global Q3_CASES
    if os.path.exists(f'{data}/val.txt'):
        Q3_CASES = {int(x) for x in open(f'{data}/val.txt').read().split()}
    todo = [(data, i) for i in ids if i not in done]
    todo.sort(key=lambda t: (t[1] not in Q3_CASES, t[1]))
    print(f'{len(ids)} cases available, {len(todo)} to do', flush=True)
    with Pool(nproc) as p, open(out, 'a') as f:
        for r in p.imap_unordered(one, todo):
            f.write(json.dumps(r) + '\n'); f.flush()


if __name__ == '__main__':
    main()
