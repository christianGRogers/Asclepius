"""Janus 1-F round 3 (Foxtrot): false-fail of F-A22's stage-2 numbers on ImageCAS-X references treated as a
prediction (§5 item 5). CPU, D45's 620 TRAINING labels only.

ImageCAS-X traced no stage-2 class, so a "correct stage-2 prediction" is built on each reference in two ways:
  T (synthetic septals) three straight tubes leaving the LAD centreline at 15, 30 and 45 % of its arc, aimed at the
    nearest PDA voxel (through the septum), radius r in {0.6, 0.75, 1.0} mm, length L in {10, 20, 30, 40, 50, 60} mm,
    painted CHILD OVER PARENT (D47 Q4: a stage-2 model is trained to call its ostium voxels inside the LAD the child).
  R (real geometry) a traced branch relabelled as a stand-in stage-2 class: D2 (LAD group), OM2 (LCx group), PLB (RCA
    group), each grown by one voxel into its parent's lumen (child over parent at the ostium).
and, for power, one wrong model:
  X (thief) the T tubes at L = 30, r = 0.75 plus the LAD lumen within +-5 mm of arc of each tube's origin called S.
Per case it stores the raw counts; `summarise_stage2.py` resamples 100-case sets and applies the rules:
  L1  per parent group (LAD, LCx, RCA by SegQueue's collapse), the share of its REFERENCE centreline (skeleton of the
      whole reference tree) whose predicted label is a stage-2 class, pooled over cases; upper one-sided 1.25 % bound
      <= 0.02;
  L2  per case, the largest distance (mm) of a stage-2 voxel from coronary foreground of a traced class; >= 95 % of
      cases with none beyond 30 mm (point, and with a Clopper-Pearson lower bound at 1.25 %);
  K1  per stage-2 class, the share of its predicted voxels inside ImageCAS-X's traced lumen, pooled over the 20
      fit-check training cases; <= 0.05.
Usage: python stage2_falsefail.py <icx620_dir> <split_j1l.json> <out.jsonl> [n_proc]"""
import hashlib, json, os, sys
from multiprocessing import Pool
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.graph import MCP_Geometric

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '../j1f_r2')]
import j1f_scorer as S  # noqa: E402
import labels_r2 as L  # noqa: E402

FRACS = (.15, .30, .45)
LENS = (10, 20, 30, 40, 50, 60)
RADII = (0.6, 0.75, 1.0)
GROUP = {'LAD': 2, 'LCx': 3, 'RCA': 4}
PROXY = {'D2': (6, 'LAD'), 'OM2': (9, 'LCx'), 'PLB': (12, 'RCA')}


def arc_from(mask, z, src):
    d, _ = MCP_Geometric(np.where(mask, 1.0, np.inf), sampling=tuple(z)).find_costs([tuple(s) for s in src])
    d[~mask] = np.inf
    return d


def ostium_end(mask, z):
    pts = np.argwhere(mask)
    d1 = arc_from(mask, z, pts[:1]); a = np.unravel_index(np.argmin(np.where(np.isfinite(d1), -d1, np.inf)), mask.shape)
    d2 = arc_from(mask, z, [a]); b = np.unravel_index(np.argmin(np.where(np.isfinite(d2), -d2, np.inf)), mask.shape)
    e = ndi.distance_transform_edt(mask, sampling=z)
    return a if e[a] >= e[b] else b


def tube_voxels(p0, u, length, r, z, shape):
    """Voxel indices (N,3) within r mm of the segment p0 -> p0 + length*u (mm coordinates); may lie outside the array."""
    p1 = p0 + length * u
    lo = np.floor((np.minimum(p0, p1) - r) / z).astype(int); hi = np.ceil((np.maximum(p0, p1) + r) / z).astype(int) + 1
    g = np.stack(np.meshgrid(*[np.arange(a, b) for a, b in zip(lo, hi)], indexing='ij'), -1).reshape(-1, 3)
    x = g * z - p0
    t = np.clip(x @ u, 0, length)
    d = np.linalg.norm(x - t[:, None] * u[None], axis=1)
    return g[d <= r]


def inside(v, shape):
    return v[np.all((v >= 0) & (v < np.array(shape)), 1)]


def one(path):
    cid = 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1)
    im = nib.load(path); z = np.array(im.header.get_zooms()[:3], float)
    icx = np.asarray(im.dataobj).astype(np.uint8)
    icx = icx[L.crop(icx, 12)]      # tubes may leave the box: voxels outside it are background (see `inside`)
    lab, _ = S.stage1_labels(icx, z)
    tree = (lab > 0) & (lab != S.IGNORE)
    four, _ = S.collapse4(lab, z)
    skel = S._skeleton(tree)
    grp_pts = {g: skel & (four == v) for g, v in GROUP.items()}
    row = {'case': cid, 'centreline_pts': {g: int(m.sum()) for g, m in grp_pts.items()}}
    lad, lm = lab == 2, lab == 1
    contact = lad & ndi.binary_dilation(lm, iterations=2)
    arc = arc_from(lad, z, np.argwhere(contact) if contact.any() else [ostium_end(lad, z)])
    La = float(np.max(arc[np.isfinite(arc)]))
    tk = cKDTree(np.argwhere(tree) * z)
    pda = np.argwhere(lab == 11) * z
    tubes = []
    for f in FRACS:
        cand = np.argwhere(lad & skel & (np.abs(arc - f * La) < 1.5))
        if not len(cand) or not len(pda):
            continue
        c0 = cand[0]; p0 = c0 * z
        tgt = pda[np.argmin(np.linalg.norm(pda - p0, axis=1))]
        u = tgt - p0; nu = float(np.linalg.norm(u))
        if nu < 5:
            continue
        u /= nu
        t = np.arange(0, max(LENS) + 0.25, 0.25)
        dist = tk.query(p0[None] + t[:, None] * u[None])[0]
        rec = {'frac': f, 'to_pda_mm': round(nu, 1),
               'L2_maxdist': {Ln: round(float(dist[t <= Ln].max()), 2) for Ln in LENS}}
        for r in RADII:
            for Ln in LENS:
                v = tube_voxels(p0, u, Ln, r, z, lab.shape)
                q = tuple(inside(v, lab.shape).T)
                stolen = grp_pts['LAD'][q]
                rec[f'r{r}_L{Ln}'] = {'vox': int(len(v)), 'in_lumen': int(tree[q].sum()),
                                      'stolen_LAD': int(stolen.sum())}
        # thief: + LAD lumen within +-5 mm of arc of the origin
        sw = lad & (np.abs(arc - arc[tuple(c0)]) <= 5)
        v = tube_voxels(p0, u, 30, 0.75, z, lab.shape)
        m = np.zeros(lab.shape, bool); m[tuple(inside(v, lab.shape).T)] = True; m |= sw
        rec['thief'] = {'vox': int(m.sum()) + int(len(v) - len(inside(v, lab.shape))), 'in_lumen': int((m & tree).sum()), 'stolen_LAD': int((m & grp_pts['LAD']).sum())}
        tubes.append(rec)
    row['tubes'] = tubes
    prox = {}
    for name, (val, g) in PROXY.items():
        p = lab == val
        if p.sum() < S.MIN_PIECE_VOX:
            continue
        paint = p | (ndi.binary_dilation(p, S.S26) & (four == GROUP[g]) & (lab != val))
        own = grp_pts[g] & ~p                      # the group's centreline without the stand-in's own points
        d = cKDTree(np.argwhere(tree & ~paint) * z).query(np.argwhere(paint) * z)[0]
        prox[name] = {'group_pts': int(own.sum()), 'stolen': int((own & paint).sum()),
                      'L2_maxdist': round(float(d.max()), 2), 'vox': int(paint.sum())}
    row['proxy'] = prox
    row['LAD_arc_mm'] = round(La, 1)
    return row


def main(d, split, out, npr=4):
    train = sorted(json.load(open(split))['train620'])
    assert hashlib.sha256('\n'.join(train).encode()).hexdigest() == \
        '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
    paths = [os.path.join(d, f'{int(c[1:]) + 1}.coronary.nii.gz') for c in train]
    done = {json.loads(l)['case'] for l in open(out)} if os.path.exists(out) else set()
    todo = [p for p in paths if 'c%04d' % (int(os.path.basename(p).split('.')[0]) - 1) not in done]
    with Pool(npr, maxtasksperchild=10) as pool, open(out, 'a') as f:
        for i, r in enumerate(pool.imap_unordered(one, todo)):
            f.write(json.dumps(r) + '\n'); f.flush()
            if i % 50 == 0:
                print(i, len(todo), flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], a[1], a[2], int(a[3]) if len(a) > 3 else 4)
