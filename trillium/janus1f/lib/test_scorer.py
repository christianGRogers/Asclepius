"""Janus 1-F round 3 (Atlas): the scorer of record's tests on training fixtures (F-A16: "Delta's 31 checks and Atlas's
self-test both become the scorer's tests, on training fixtures only").

Part A, Delta's `test_branch_score.py` (commit 4e49be9; 30 checks, its log's 31st line is "ALL PASS"), ported to
`j1f_scorer.py`: the same six training cases, chosen by sha256('asclepius-j1f-r2-scorertest:' + id), the same
perturbations, the same assertions, pooled with `j1f_scorer.aggregate`:
  * per case: SegQueue's collapse of the stage-1 reference equals D25 (icx4 `territory.to_four`) on every voxel that is
    neither ImageCAS-X "Other" nor 255;
  * per gated class: identity -> recall, presence agreement, naming = 1 and branch tF1 = 1; a one-voxel grey dilation
    -> recall 1, naming 1;
  * D1/D2 swapped and PDA/PLB swapped -> recall 1, naming 0; OM2 drawn as LCx -> recall 1, naming 0, agreement < 1;
    OM2 removed -> recall 0.
Part B, Atlas's round-2 real-case checks (`validate_scorer.py`, case c0217), as assertions:
  identity all 1; D1/D2 swapped -> detected, misnamed; OM1/OM2 folded into the LCx -> detected, misnamed, presence
  lost; PLB removed -> missed; PDA kept to 40 % of its length from its root -> missed.
Part C, the synthetic self-test (`j1f_scorer.selftest`).

Every case is asserted to be one of the D45 training 620 before its label is opened.
Usage: python test_scorer.py <icx620_dir> <split_j1l.json>
"""
import hashlib
import json
import os
import sys

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '../../../trillium/icx4/lib'))
import j1f_scorer as S  # noqa: E402
import territory  # noqa: E402

V = {n: i for i, n in enumerate(S.NAMES)}
fails = []


def check(name, cond):
    print(('PASS ' if cond else 'FAIL ') + name, flush=True)
    if not cond:
        fails.append(name)


def load(d, c, train):
    assert c in train, f'{c} is not a training case'
    im = nib.load(os.path.join(d, f'{int(c[1:]) + 1}.coronary.nii.gz'))
    icx = np.asarray(im.dataobj).astype(np.uint8)
    z = np.array(im.header.get_zooms()[:3], float)
    nz = np.argwhere(icx > 0)
    lo, hi = np.maximum(nz.min(0) - 8, 0), nz.max(0) + 9
    icx = icx[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    return icx, z


def truncate(lab, c, frac, z):
    out = lab.copy()
    for p in S.pieces_of(lab, z)[c]:
        comp, _ = ndi.label(lab == c, S.S26)
        piece = comp == comp[p['root']]
        dd = S._geodesic(piece, [p['root']], z)
        out[piece & (dd > frac * max(p['length_mm'], 1e-6))] = 0
    return out


def main(d, split):
    sp = json.load(open(split))
    train = set(sp['train620'])
    assert hashlib.sha256('\n'.join(sorted(train)).encode()).hexdigest() == \
        '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
    pick = sorted(train, key=lambda c: hashlib.sha256(('asclepius-j1f-r2-scorertest:' + c).encode()).hexdigest())[:6]
    assert pick == sorted(pick, key=lambda c: hashlib.sha256(('asclepius-j1f-r2-scorertest:' + c).encode()).hexdigest())
    print('Part A cases', pick)
    rows = {k: [] for k in ('identity', 'swap_D1_D2', 'OM2_to_LCx', 'OM2_to_bg', 'dilate1', 'PDA_PLB_swap')}
    for c in pick:
        icx, z = load(d, c, train)
        ref, _ = S.stage1_labels(icx, z)
        rp = S.pieces_of(ref, z)
        p = np.where(ref == S.IGNORE, 0, ref).astype(np.uint8)
        rows['identity'].append(S.score_case(ref, p, z, ref_pieces=rp))
        q = p.copy(); q[p == V['D1']] = V['D2']; q[p == V['D2']] = V['D1']
        rows['swap_D1_D2'].append(S.score_case(ref, q, z, False, rp))
        q = p.copy(); q[p == V['OM2']] = V['LCx']
        rows['OM2_to_LCx'].append(S.score_case(ref, q, z, False, rp))
        q = p.copy(); q[p == V['OM2']] = 0
        rows['OM2_to_bg'].append(S.score_case(ref, q, z, False, rp))
        q = p.copy(); grow = ndi.grey_dilation(p, size=(3, 3, 3)); g = (p == 0) & (grow > 0); q[g] = grow[g]
        rows['dilate1'].append(S.score_case(ref, q, z, False, rp))
        q = p.copy(); q[p == V['PDA']] = V['PLB']; q[p == V['PLB']] = V['PDA']
        rows['PDA_PLB_swap'].append(S.score_case(ref, q, z, False, rp))
        four = S.collapse4(ref, z)
        d25 = territory.to_four(icx, z)
        m = (icx > 0) & (icx != 14) & (ref != S.IGNORE)
        check(f'{c} collapse = D25 on every non-Other voxel ({int((four[m] != d25[m]).sum())} differ)',
              bool((four[m] == d25[m]).all()))
    A = {k: S.aggregate(v) for k, v in rows.items()}
    for cl in ('D1', 'D2', 'OM1', 'OM2', 'PDA', 'PLB'):
        a = A['identity'][cl]
        if a['pieces'] == 0:
            continue
        check(f'identity {cl}: recall, agreement, naming = 1', a['recall'] == 1 and a['presence'] == 1
              and a['naming'] == 1)
        t = [s[cl]['tf1'] for s in rows['identity'] if 'tf1' in s[cl]]
        check(f'identity {cl}: branch tF1 = 1 ({np.mean(t):.3f})', abs(np.mean(t) - 1) < 1e-6)
        dl = A['dilate1'][cl]
        check(f'dilate by 1 voxel {cl}: recall 1, naming 1', dl['recall'] == 1 and dl['naming'] == 1)
    for cl in ('D1', 'D2'):
        a = A['swap_D1_D2'][cl]
        if a['pieces']:
            check(f'swap D1/D2 {cl}: recall 1, naming 0', a['recall'] == 1 and a['naming'] == 0)
    for cl in ('PDA', 'PLB'):
        a = A['PDA_PLB_swap'][cl]
        if a['pieces']:
            check(f'swap PDA/PLB {cl}: recall 1, naming 0', a['recall'] == 1 and a['naming'] == 0)
    a = A['OM2_to_LCx']['OM2']
    if a['pieces']:
        check('OM2 -> LCx: detected (recall 1), not named (naming 0), agreement drops',
              a['recall'] == 1 and a['naming'] == 0 and a['presence'] < 1)
        check('OM2 -> background: recall 0', A['OM2_to_bg']['OM2']['recall'] == 0)
    nA = len([f for f in fails])
    # ---- Part B: c0217
    c = 'c0217'
    icx, z = load(d, c, train)
    ref, _ = S.stage1_labels(icx, z)
    rp = S.pieces_of(ref, z)
    s = S.score_case(ref, ref, z, ref_pieces=rp)
    check(f'{c} identity: every piece detected and named, tF1 1, presence agrees',
          all(all(p['detected'] and p['named'] for p in v['pieces']) and v['present_ref'] == v['present_pred']
              and abs(v.get('tf1', 1.0) - 1) < 1e-9 for v in s.values()))
    sw = ref.copy(); sw[ref == 5] = 6; sw[ref == 6] = 5
    s = S.score_case(ref, sw, z, False, rp)
    check(f'{c} D1/D2 swapped: detected, misnamed',
          all(p['detected'] and not p['named'] for k in ('D1', 'D2') for p in s[k]['pieces']))
    fo = ref.copy(); fo[np.isin(ref, (8, 9))] = 3
    s = S.score_case(ref, fo, z, False, rp)
    check(f'{c} OM folded into LCx: detected, misnamed, presence lost',
          all(p['detected'] and not p['named'] and not s[k]['present_pred'] for k in ('OM1', 'OM2')
              for p in s[k]['pieces']))
    dp = ref.copy(); dp[ref == 12] = 0
    s = S.score_case(ref, dp, z, False, rp)
    check(f'{c} PLB removed: missed', all(not p['detected'] for p in s['PLB']['pieces']) and s['PLB']['pieces'])
    tr = truncate(ref, 11, 0.4, z)
    s = S.score_case(ref, tr, z, False, rp)
    check(f'{c} PDA kept to 40 %: missed', all(not p['detected'] for p in s['PDA']['pieces']) and s['PDA']['pieces'])
    # ---- Part C
    S.selftest()
    print(f'Part A: {len(rows["identity"])} cases; checks failed: {nA}; total failed: {len(fails)}')
    print('ALL PASS' if not fails else f'{len(fails)} FAIL', '; scorer', S.scorer_sha256())
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
