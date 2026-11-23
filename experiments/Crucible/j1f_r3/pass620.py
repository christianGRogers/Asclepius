"""Janus 1-F round 3 (Crucible): one pass of the scorer of record over the D45 training 620 (labels only, no CT).

Feeds §5 items 1 and 5 of the round-2 ruling. Per case (ImageCAS-X label -> j1f_scorer.stage1_labels, D47 (A)):

item 1 (the scorer):
  * pieces per gated class (26-components >= 20 voxels) and their centreline lengths, to compare with the piece
    distribution F-A15 was simulated on (Atlas's census_r2.jsonl);
  * the SegQueue collapse (F-A17): fallback count, and voxels where it differs from territory.to_four (D25) outside
    ImageCAS-X "Other" and 255;
  * identity: the reference scored against itself (recall, naming, presence must be 1);
  * erode1: the reference after a one-voxel (6-connected) erosion of its foreground, labels kept: a realistic thin
    prediction, to show what per-piece recall the scorer computes on real geometry.

item 5 (F-A22's stage-2 numbers), on ImageCAS-X references treated as predictions. ImageCAS-X traces no stage-2
class, so its traced side branches stand in for them, per host: D1-D3 for the LAD group (S1-S3), OM1/OM2/Ramus for
the LCx group (SN off the LCx), PDA/PLB for the RCA group (SN, Conus, RMA). For each case, with P = the proxy
classes of all three groups and G = the four-class trunk centreline (whole-tree skeleton points labelled LM, LAD,
LCx or RCA in the reference), two forms of each measure:
  * L1 (theft), nearest-label form: share of a group's trunk centreline points whose nearest predicted foreground
    voxel is a P class. Proximity form: share within TOL_MM (1.5 mm) of any P voxel. Each on the reference itself and
    on the reference with P dilated by one voxel into the trunk (a one-voxel ostium bleed).
  * L2 (far paint), voxel form: the largest distance (mm) of a P voxel from the predicted foreground that is not P.
    Component form: the largest, over 26-components of P, of the component's nearest distance to the non-P
    foreground (a detached blob's gap; 0 for anything attached).
  * K1 (leak into the traced lumen): the proxy classes are removed from the "traced" map (as ImageCAS-X would leave
    an untraced branch as background), and the share of the predicted P voxels inside the remaining traced lumen is
    measured for the exact branch and for the branch dilated by one voxel.

Usage: python pass620.py <icx620_dir> <out.jsonl> [n_proc]
"""
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '../../../trillium/icx4/lib'))
import j1f_scorer as S  # noqa: E402
import territory  # noqa: E402

GROUPS = {'LAD': ((2,), (5, 6, 7)), 'LCx': ((3,), (8, 9, 10)), 'RCA': ((4,), (11, 12))}
PROXY = (5, 6, 7, 8, 9, 10, 11, 12)
S6 = ndi.generate_binary_structure(3, 1)


def crop(a, pad=10):
    nz = np.argwhere(a > 0)
    lo = np.maximum(nz.min(0) - pad, 0)
    hi = np.minimum(nz.max(0) + pad + 1, a.shape)
    return tuple(slice(int(l), int(h)) for l, h in zip(lo, hi))


def pieces_row(pcs):
    return {S.NAMES[k]: [{'vox': p['vox'], 'len': round(p['length_mm'], 2)} for p in v] for k, v in pcs.items()}


def stage2_proxy(lab, skel, z):
    """L1, L2 and K1 on the reference (and with P bled by one voxel), P = the proxy classes."""
    tree = (lab > 0) & (lab != S.IGNORE)
    P = np.isin(lab, PROXY)
    out = {}
    if not P.any():
        return {'has_proxy': False}
    bled = P | (ndi.binary_dilation(P, S6) & tree)          # P grows one voxel into the trunk/parent
    for tag, pm in (('exact', P), ('bleed1', bled)):
        nonp = tree & ~pm
        # nearest predicted voxel of each trunk centreline point: on the exact ref a trunk voxel is its own nearest
        _, idx = ndi.distance_transform_edt(~tree, sampling=z, return_indices=True)
        dP = ndi.distance_transform_edt(~pm, sampling=z)
        l1 = {}
        for g, (trunk, _) in GROUPS.items():
            pts = np.argwhere(skel & np.isin(lab, trunk + ((1,) if g != 'RCA' else ())))
            if not len(pts):
                l1[g] = None
                continue
            q = tuple(pts.T)
            near_is_p = pm[tuple(idx[:, q[0], q[1], q[2]])]
            l1[g] = {'n': int(len(pts)), 'nearest': float(near_is_p.mean()),
                     'prox': float((dP[q] <= S.TOL_MM).mean())}
        dn = ndi.distance_transform_edt(~nonp, sampling=z)
        comp, nc = ndi.label(pm, S.S26)
        gaps = ndi.minimum(dn, comp, index=np.arange(1, nc + 1)) if nc else []
        out[tag] = {'L1': l1, 'L2_voxel_max_mm': float(dn[pm].max()),
                    'L2_component_gap_max_mm': float(np.max(gaps)) if nc else 0.0}
    # K1: P untraced -> the traced lumen is tree & ~P
    traced = tree & ~P
    dil = ndi.binary_dilation(P, S6)
    out['K1'] = {'exact': float((P & traced).sum() / P.sum()), 'dilate1': float((dil & traced).sum() / dil.sum())}
    # per group, for K1 per class group
    out['K1_group'] = {}
    for g, (_, br) in GROUPS.items():
        pg = np.isin(lab, br)
        if pg.any():
            dg = ndi.binary_dilation(pg, S6)
            out['K1_group'][g] = float((dg & (tree & ~pg)).sum() / dg.sum())
    out['has_proxy'] = True
    return out


def one(path):
    t0 = time.time()
    c = 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1)
    im = nib.load(path)
    icx = np.asarray(im.dataobj).astype(np.uint8)
    z = np.array(im.header.get_zooms()[:3], float)
    sl = crop(icx)
    icx = icx[sl]
    lab, info = S.stage1_labels(icx, z)
    row = {'case': c, 'other': info}
    st = {}
    c4 = S.collapse4(lab, z, st)
    ref4 = territory.to_four(icx, z)
    m = (icx > 0) & (icx != 14) & (lab != S.IGNORE)
    row['collapse'] = {'components': st.get('components', 0), 'fallback': st.get('fallback', 0),
                       'mismatch_vox': int((c4[m] != ref4[m]).sum())}
    tree = (lab > 0) & (lab != S.IGNORE)
    skel = S._skeleton(tree)
    sp = z
    rp = {k: S._pieces(lab, k, skel, sp, np.isin(lab, S.PARENT[k])) for k in S.BRANCHES}
    row['pieces'] = pieces_row(rp)
    idn = S.score_case(lab, lab.copy(), z, with_tf1=False, ref_pieces=rp)
    er = np.where(ndi.binary_erosion(tree, S6), lab, 0).astype(np.uint8)
    ero = S.score_case(lab, er, z, with_tf1=False, ref_pieces=rp)

    def slim(s):
        return {k: {'det': [p['detected'] for p in v['pieces']], 'named': [p['named'] for p in v['pieces']],
                    'pr': v['present_ref'], 'pp': v['present_pred']} for k, v in s.items()}
    row['identity'], row['erode1'] = slim(idn), slim(ero)
    row['stage2'] = stage2_proxy(lab, skel, z)
    row['sec'] = round(time.time() - t0, 1)
    return row


if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    nproc = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    split = json.load(open(os.path.join(src, 'split.json')))
    train = split['train620']
    assert hashlib.sha256('\n'.join(sorted(train)).encode()).hexdigest() == \
        '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)['case'] for l in open(out)}
    paths = [os.path.join(src, '%d.coronary.nii.gz' % (int(c[1:]) + 1)) for c in train if c not in done]
    paths = [p for p in paths if os.path.exists(p)]          # resumable while the fetch runs
    with Pool(nproc) as pool, open(out, 'a') as f:
        for r in pool.imap_unordered(one, paths):
            f.write(json.dumps(r) + '\n'); f.flush()
            print(r['case'], r['sec'], flush=True)
