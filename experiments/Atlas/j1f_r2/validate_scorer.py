"""Janus 1-F round 2 (Atlas): the branch scorer on real 620 references with known perturbations (training cases only).

For each case: reference = stage1_labels(ImageCAS-X). Predictions:
  identity        the reference itself: every piece detected and named, tF1 1, presence agrees
  erode1          one-voxel 6-erosion of the whole tree (a thinner model): detection should hold (1.5 mm tolerance)
  swap_D1D2       D1 and D2 names exchanged: detected, misnamed
  fold_OM         OM1, OM2 drawn as LCx (a model that never learned OM): detected, misnamed, OM presence 0
  drop_PLB        PLB removed (background): missed
  trunc_PDA_40    PDA kept only within 40 % of its centreline length from its root: mostly missed (< 50 % cover)
Also the timing per case, for the launcher's costing.
Usage: python validate_scorer.py <icx620_dir> <split_j1l.json> <n_cases> <out.json>"""
import json
import os
import sys
import time

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import j1f_scorer as S  # noqa: E402


def truncate(lab, c, frac, z):
    out = lab.copy()
    for p in S.pieces_of(lab, z)[c]:
        m = lab == c
        comp, _ = ndi.label(m, S.S26)
        k = comp[p['root']]
        piece = comp == k
        d = S._geodesic(piece, [p['root']], z)
        out[piece & (d > frac * max(p['length_mm'], 1e-6))] = 0
    return out


def main(d, split, n, outp):
    train = sorted(json.load(open(split))['train620'])
    rng = np.random.default_rng(20261122)
    cases = sorted(rng.choice(train, size=n, replace=False))
    res = []
    for c in cases:
        im = nib.load(os.path.join(d, f'{int(c[1:]) + 1}.coronary.nii.gz'))
        icx = np.asarray(im.dataobj).astype(np.uint8)
        z = np.array(im.header.get_zooms()[:3], float)
        ref, _ = S.stage1_labels(icx, z)
        t0 = time.time()
        rp = S.pieces_of(ref, z)
        tp = time.time() - t0
        er = np.where(ndi.binary_erosion(ref > 0), ref, 0).astype(np.uint8)
        sw = ref.copy(); sw[ref == 5] = 6; sw[ref == 6] = 5
        fo = ref.copy(); fo[np.isin(ref, (8, 9))] = 3
        dp = ref.copy(); dp[ref == 12] = 0
        tr = truncate(ref, 11, 0.4, z)
        row = {'case': c, 't_pieces_s': round(tp, 1)}
        for name, pred in (('identity', ref), ('erode1', er), ('swap_D1D2', sw), ('fold_OM', fo),
                           ('drop_PLB', dp), ('trunc_PDA_40', tr)):
            t0 = time.time()
            s = S.score_case(ref, pred, z, ref_pieces=rp)
            row[name] = {k: {'n': len(v['pieces']), 'det': sum(p['detected'] for p in v['pieces']),
                             'named': sum(p['named'] for p in v['pieces']), 'pres_ref': v['present_ref'],
                             'pres_pred': v['present_pred'], 'tf1': round(v.get('tf1', float('nan')), 3)}
                         for k, v in s.items()}
            row[name]['t_s'] = round(time.time() - t0, 1)
        res.append(row)
        print(c, {k: row[k]['t_s'] for k in ('identity', 'erode1')}, flush=True)
    json.dump(res, open(outp, 'w'), indent=0)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4])
