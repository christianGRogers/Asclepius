"""Janus 1-F round 3 (Atlas): one pass over the D45 training 620 (labels only, no CT, no model output).

Per case, with the round-3 scorer (`j1f_scorer.py`, SegQueue's collapse):
  * item 1 (F-A16/F-A17): `collapse4` (SegQueue's `collapse_to_four`) of the stage-1 labels against icx4's
    `territory.to_four` (D25), voxel mismatches outside ImageCAS-X "Other" and 255, and SegQueue's counts
    (components, fallback). The stage-1 'Other' counts (F-A18's expected line).
  * item 1: every reference piece of the scorer (class, voxels, length, presence at 5 mm), to compare with the piece
    distribution F-A15's lines were simulated on (`experiments/Atlas/j1f_r2/census_r2.jsonl`).
  * item 5 (F-A22): stage 2's three leakage numbers under a SURROGATE. ImageCAS-X has none of the six stage-2 classes,
    so a reference "treated as a prediction" scores 0 on all three by construction. Instead each traced side-branch
    class of a host plays a stage-2 class of that host, predicted exactly (k = 0) or one/two voxels too wide (k = 1, 2,
    the width error a human-level model has: Table 1 DSC ~0.8):
      host LAD: D1, D2, D3 (stand in for S1-S3)          host LCx: OM1, OM2, Ramus (for SN off the LCx)
      host RCA: PDA and PLB pieces that collapse to the RCA (for SN, Conus, RMA)
    L1 (theft): share of the host trunk's centreline (whole-tree skeleton in the trunk class) whose predicted label is
       a surrogate class. Pooled numerator and denominator per host.
    K1: share of the surrogate's predicted voxels that lie in ImageCAS-X's traced lumen of OTHER classes (the
       surrogate's own reference voxels are not counted as traced, since a real stage-2 branch is untraced).
    L2 (far paint): per surrogate piece (k = 0), the max and the min distance (mm) of its voxels from the stage-1
       foreground (LM and the three trunks; every side-branch class excluded, as every stage-2 class would be).

Usage: python check_620.py <icx620_dir> <split_j1l.json> <out.jsonl> [n_proc] [only_case ...]
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

HOSTS = {'LAD': (2, (5, 6, 7)), 'LCx': (3, (8, 9, 10)), 'RCA': (4, (11, 12))}
KS = (0, 1, 2)
S6 = ndi.generate_binary_structure(3, 1)


def one(path):
    c = 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1)
    im = nib.load(path)
    icx = np.asarray(im.dataobj).astype(np.uint8)
    z = np.array(im.header.get_zooms()[:3], float)
    lab, info = S.stage1_labels(icx, z)
    st = {}
    c4 = S.collapse4(lab, z, st)
    ref4 = territory.to_four(icx, z)
    valid = lab != S.IGNORE
    mm = (c4 != ref4) & valid
    row = {'case': c, 'zooms': z.tolist(), 'shape': list(icx.shape), 'other': info,
           'collapse_mismatch_vox': int(mm.sum()),
           'collapse_mismatch_outside_other': int((mm & (icx != 14)).sum()),
           'sq_stats': st}
    pcs = S.pieces_of(lab, z)
    row['pieces'] = {S.NAMES[k]: [{'vox': p['vox'], 'len': round(p['length_mm'], 2)} for p in v]
                     for k, v in pcs.items()}
    row['present'] = {S.NAMES[k]: v for k, v in S.presence(pcs).items()}
    # ---- stage-2 surrogates, on the tree's box + 35 mm
    tree = (lab > 0) & valid
    bb = ndi.find_objects(tree.astype(np.uint8))[0]
    m = np.ceil(35.0 / z).astype(int)
    bb = tuple(slice(max(s.start - m[k], 0), min(s.stop + m[k], lab.shape[k])) for k, s in enumerate(bb))
    lb, tb, c4b = lab[bb], tree[bb], c4[bb]
    skel = S._skeleton(tb)
    side_all = np.isin(lb, S.BRANCHES)
    stage1_fg = tb & ~side_all
    dfg = ndi.distance_transform_edt(~stage1_fg, sampling=z) if stage1_fg.any() else None
    row['s2'] = {}
    for host, (trunk, cls) in HOSTS.items():
        sur = np.isin(lb, cls)
        if host == 'RCA':
            sur &= c4b == 4
        tpts = skel & (lb == trunk)
        h = {'trunk_pts': int(tpts.sum()), 'sur_vox': int(sur.sum())}
        for k in KS:
            sk = ndi.binary_dilation(sur, S6, iterations=k) if k else sur
            sk &= ~(side_all & ~sur)                       # never overwrite another host's surrogate
            h[f'l1_stolen_k{k}'] = int((tpts & sk).sum())
            other_traced = tb & ~sur
            h[f'k1_in_traced_k{k}'] = int((sk & other_traced).sum())
            h[f'k1_pred_vox_k{k}'] = int(sk.sum())
        pieces = []
        if sur.any() and dfg is not None:
            comp, nc = ndi.label(sur, S.S26)
            for i in range(1, nc + 1):
                p = comp == i
                if p.sum() < S.MIN_PIECE_VOX:
                    continue
                d = dfg[p]
                pieces.append([round(float(d.max()), 2), round(float(d.min()), 2)])
        h['l2_pieces_max_min_mm'] = pieces
        row['s2'][host] = h
    return row


def main(d, split, out, npr=4, only=None):
    sp = json.load(open(split))
    train = sorted(sp['train620'])
    assert hashlib.sha256('\n'.join(train).encode()).hexdigest() == \
        '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
    assert not set(train) & set(sp['locked100'])
    if only:
        assert set(only) <= set(train), 'only training cases may be read'
        train = only
    paths = [os.path.join(d, f'{int(c[1:]) + 1}.coronary.nii.gz') for c in train]
    missing = [p for p in paths if not os.path.exists(p)]
    assert not missing, missing[:3]
    done = set()
    if os.path.exists(out):                               # resume: keep complete rows, redo the rest
        rows = [json.loads(l) for l in open(out) if l.strip().endswith('}')]
        done = {r['case'] for r in rows}
        with open(out, 'w') as f:
            for r in rows:
                f.write(json.dumps(r) + '\n')
    paths = [p for c, p in zip(train, paths) if c not in done]
    with Pool(npr, maxtasksperchild=20) as pool, open(out, 'a') as f:
        for r in pool.imap_unordered(one, paths):
            f.write(json.dumps(r) + '\n'); f.flush()
    print('scorer', S.scorer_sha256())


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], a[1], a[2], int(a[3]) if len(a) > 3 else 4, a[4:] or None)
