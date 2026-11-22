"""Janus 1-F round 2 (Atlas): one pass over the D45 training 620 (labels only, no CT). Feeds four §5 items.

Per case (ImageCAS-X label -> j1f_scorer.stage1_labels, D47 Q1 = A):
  * item 2 / F-A4: the origin collapse of the stage-1 labels against territory.to_four (icx4's D25 collapse), voxel
    mismatches outside 255; and the stage-1 'Other' handling counts (D3, D4 -> LAD, LCx-side, nearest, ignore).
  * item 1: every reference branch piece (j1f_scorer definitions): class, voxels, centreline length (mm) -> presence at
    3 and 5 mm, piece counts per class (R-PDA in two pieces etc.).
  * item 4: background released by a band of 4, 8, 15 mm around the traced tree (mm^3, and the share nearer the LAD /
    LCx / RCA territory); and, as the proxy for where an untraced side branch runs, the distance (mm) of each traced
    side branch's centreline from its parent trunk (p50, p90, max per piece).
  * item 10: unnamed twigs on each trunk (skeleton spurs of the trunk's own class with length >= 3 / 5 mm, the two
    longest spurs being the trunk's own ends), and dominance by labels and by Descriptors.xlsx.

Usage: python census_r2.py <icx620_dir> <split_j1l.json> <out.jsonl> [n_proc]
"""
import hashlib
import json
import os
import sys
from multiprocessing import Pool

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '../../../trillium/icx4/lib'))
import j1f_scorer as S  # noqa: E402
import territory  # noqa: E402

BANDS = (4.0, 8.0, 15.0)
TRUNK = {'LAD': 2, 'LCx': 3, 'RCA': 4}


def _spurs(mask, sp):
    """Spur lengths (mm) of a skeleton: walk from each endpoint to the first junction."""
    sk = S._skeleton(mask)
    pts = np.argwhere(sk)
    if len(pts) < 2:
        return []
    idx = {tuple(p): i for i, p in enumerate(pts)}
    offs = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1) if (a, b, c) != (0, 0, 0)]
    nb = [[idx[t] for o in offs if (t := (p[0] + o[0], p[1] + o[1], p[2] + o[2])) in idx] for p in pts]
    deg = np.array([len(n) for n in nb])
    out = []
    for e in np.where(deg == 1)[0]:
        prev, cur, L = -1, int(e), 0.0
        while True:
            nxt = [n for n in nb[cur] if n != prev]
            if deg[cur] >= 3 or not nxt:
                break
            n = nxt[0]
            L += float(np.linalg.norm((pts[n] - pts[cur]) * sp))
            prev, cur = cur, n
        out.append(L)
    return sorted(out, reverse=True)


def one(path):
    c = 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1)
    im = nib.load(path)
    icx = np.asarray(im.dataobj).astype(np.uint8)
    z = np.array(im.header.get_zooms()[:3], float)
    lab, info = S.stage1_labels(icx, z)
    # collapse check
    c4 = S.collapse4(lab, z)
    ref4 = territory.to_four(icx, z)
    valid = lab != S.IGNORE
    mm = (c4 != ref4) & valid
    row = {'case': c, 'zooms': z.tolist(), 'other': info,
           'collapse_mismatch_vox': int(mm.sum()),
           'collapse_mismatch_by_icx': {int(k): int((mm & (icx == k)).sum()) for k in np.unique(icx[mm])},
           'ignore_vox': int((~valid).sum())}
    # pieces
    pcs = S.pieces_of(lab, z)
    row['pieces'] = {S.NAMES[k]: [{'vox': p['vox'], 'len': round(p['length_mm'], 2)} for p in v] for k, v in pcs.items()}
    # crop to the tree's box + 20 mm for the distance maps
    tree = (lab > 0) & valid
    bb = ndi.find_objects(tree.astype(np.uint8))[0]
    m = np.ceil(20.0 / z).astype(int)
    bb = tuple(slice(max(s.start - m[k], 0), min(s.stop + m[k], lab.shape[k])) for k, s in enumerate(bb))
    lb, tb = lab[bb], tree[bb]
    vox_mm3 = float(np.prod(z))
    terr = S._TO4[lb]
    # band on a 2x coarser grid (block maximum): bands are 4-15 mm, voxels become 0.6-1.0 mm
    def coarse(a):
        a = ndi.maximum_filter(a, size=2, mode='constant')
        return a[::2, ::2, ::2]
    tb2, terr2, ig2 = coarse(tb.astype(np.uint8)) > 0, coarse(terr), coarse((lb == S.IGNORE).astype(np.uint8)) > 0
    z2 = z * 2
    vox2 = float(np.prod(z2))
    dtree, near_idx = ndi.distance_transform_edt(~tb2, sampling=z2, return_indices=True)
    near_terr = terr2[tuple(near_idx)]
    row['band'] = {}
    for b in BANDS:
        rel = (~tb2) & (dtree <= b) & ~ig2
        row['band'][str(b)] = {'mm3': round(rel.sum() * vox2, 1),
                               **{n: round(float((rel & (near_terr == k)).sum() * vox2), 1)
                                  for n, k in (('LM', 1), ('LAD', 2), ('LCx', 3), ('RCA', 4))}}
    row['tree_mm3'] = round(float(tb.sum() * vox_mm3), 1)
    # side-branch distance from the parent trunk (proxy for untraced side branches' course)
    skel = S._skeleton(tb)
    from scipy.spatial import cKDTree
    kd = {k: cKDTree(np.argwhere(lb == k) * z) for k in (2, 3, 4) if (lb == k).any()}
    row['branch_from_parent'] = {}
    for k in S.BRANCHES:
        comp, nc = ndi.label(lb == k, S.S26)
        rows = []
        for i in range(1, nc + 1):
            p = comp == i
            if p.sum() < S.MIN_PIECE_VOX:
                continue
            q = p & skel
            if not q.any():
                continue
            par = S.PARENT[k]
            qp = np.argwhere(q) * z
            ds = [kd[j].query(qp)[0] for j in par if j in kd]
            if not ds:
                continue
            d = np.min(ds, axis=0)
            rows.append([round(float(np.percentile(d, 50)), 2), round(float(np.percentile(d, 90)), 2),
                         round(float(d.max()), 2)])
        row['branch_from_parent'][S.NAMES[k]] = rows
    # trunk twigs
    row['trunk_spurs'] = {n: [round(s, 2) for s in _spurs(lb == k, z)] for n, k in TRUNK.items()}
    # dominance by labels
    has = {n: bool((icx == v).sum() >= S.MIN_PIECE_VOX) for n, v in
           (('R-PDA', 10), ('R-PLA', 11), ('L-PDA', 12), ('L-PLA', 13))}
    row['icx_posterior'] = has
    return row


def main(d, split, out, npr=4):
    sp = json.load(open(split))
    train = sorted(sp['train620'])
    assert hashlib.sha256('\n'.join(train).encode()).hexdigest().startswith('1350cb1f')
    paths = [os.path.join(d, f'{int(c[1:]) + 1}.coronary.nii.gz') for c in train]
    missing = [p for p in paths if not os.path.exists(p)]
    assert not missing, f'{len(missing)} missing'
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)['case'] for l in open(out)}
    todo = [p for p in paths if 'c%04d' % (int(os.path.basename(p).split('.')[0]) - 1) not in done]
    with Pool(npr, maxtasksperchild=10) as pool, open(out, 'a') as f:
        for i, r in enumerate(pool.imap_unordered(one, todo)):
            f.write(json.dumps(r) + '\n'); f.flush()
            if i % 25 == 0:
                print(i, len(todo), flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], a[1], a[2], int(a[3]) if len(a) > 3 else 4)
