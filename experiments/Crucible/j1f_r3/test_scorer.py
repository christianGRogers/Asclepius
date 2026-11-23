"""§5 item 1: Delta's 31 checks (experiments/Delta/j1f_r2/test_branch_score.py) and Atlas's self-test, ported to the
scorer of record (j1f_scorer.py: Atlas's definitions + SegQueue's collapse). Training fixtures only: the same six
cases Delta's test names (hash-chosen from the 620 with 'asclepius-j1f-r2-scorertest:'), never a locked or sealed
case. Each perturbation of the reference must move exactly the measure it should.
Usage: python test_scorer.py <icx620_dir>"""
import hashlib
import json
import os
import sys

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1f_scorer as S  # noqa: E402

icx = sys.argv[1]
train = json.load(open(os.path.join(icx, 'split.json')))['train620']
assert hashlib.sha256('\n'.join(sorted(train)).encode()).hexdigest() == \
    '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
pick = sorted(train, key=lambda c: hashlib.sha256(('asclepius-j1f-r2-scorertest:' + c).encode()).hexdigest())[:6]
assert pick == ['c0585', 'c0875', 'c0987', 'c0287', 'c0920', 'c0761'], pick     # Delta's six
V = {n: i for i, n in enumerate(S.NAMES)}
fails = []


def check(name, cond):
    print(('PASS ' if cond else 'FAIL ') + name)
    if not cond:
        fails.append(name)


print('Atlas self-test:'); S.selftest()
rows = {k: [] for k in ('identity', 'swap_D1_D2', 'OM2_to_LCx', 'OM2_to_bg', 'dilate1', 'PDA_PLB_swap')}
for c in pick:
    im = nib.load(os.path.join(icx, '%d.coronary.nii.gz' % (int(c[1:]) + 1)))
    lab = np.asarray(im.dataobj).astype(np.uint8); z = tuple(float(x) for x in im.header.get_zooms()[:3])
    nz = np.argwhere(lab > 0); lo = np.maximum(nz.min(0) - 8, 0); hi = nz.max(0) + 9
    lab = lab[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    ref, _ = S.stage1_labels(lab, z)
    rp = S.pieces_of(ref, z)
    p = np.where(ref == S.IGNORE, 0, ref).astype(np.uint8)
    rows['identity'].append(S.score_case(ref, p, z, True, rp))
    q = p.copy(); q[p == V['D1']] = V['D2']; q[p == V['D2']] = V['D1']
    rows['swap_D1_D2'].append(S.score_case(ref, q, z, False, rp))
    q = p.copy(); q[p == V['OM2']] = V['LCx']; rows['OM2_to_LCx'].append(S.score_case(ref, q, z, False, rp))
    q = p.copy(); q[p == V['OM2']] = 0; rows['OM2_to_bg'].append(S.score_case(ref, q, z, False, rp))
    q = p.copy(); g = ndi.grey_dilation(p, size=(3, 3, 3)); m = (p == 0) & (g > 0); q[m] = g[m]
    rows['dilate1'].append(S.score_case(ref, q, z, False, rp))
    q = p.copy(); q[p == V['PDA']] = V['PLB']; q[p == V['PLB']] = V['PDA']
    rows['PDA_PLB_swap'].append(S.score_case(ref, q, z, False, rp))
    # collapse (F-A17): the 1-F reference collapses to ImageCAS-X's D25 territories outside "Other" and 255
    st = {}
    four = S.collapse4(p, z, st)
    d25 = np.zeros(lab.shape, np.uint8)
    d25[lab == 1] = 1; d25[np.isin(lab, (2, 4, 5))] = 2; d25[np.isin(lab, (3, 6, 7, 8, 12, 13))] = 3
    d25[np.isin(lab, (9, 10, 11))] = 4
    mm = (lab > 0) & (lab != 14) & (ref != S.IGNORE)
    check(f'{c} collapse = D25 on every non-Other voxel ({int((four[mm] != d25[mm]).sum())} differ), '
          f'fallback {st.get("fallback", 0)}', bool((four[mm] == d25[mm]).all()) and st.get('fallback', 0) == 0)

A = {k: S.aggregate(v) for k, v in rows.items()}
for cl in [S.NAMES[c] for c in S.GATED]:
    a = A['identity'][cl]
    if a['n_pieces'] == 0:
        continue
    check(f'identity {cl}: recall, presence, naming = 1', a['recall'] == 1 and a['presence'] == 1 and a['naming'] == 1)
    check(f'identity {cl}: branch tF1 = 1 ({a["branch_tf1_mean"]:.3f})', abs(a['branch_tf1_mean'] - 1) < 1e-6)
    d = A['dilate1'][cl]
    check(f'dilate by 1 voxel {cl}: recall 1, naming 1', d['recall'] == 1 and d['naming'] == 1)
for cl in ('D1', 'D2'):
    a = A['swap_D1_D2'][cl]
    if a['n_pieces']:
        check(f'swap D1/D2 {cl}: recall 1, naming 0', a['recall'] == 1 and a['naming'] == 0)
for cl in ('PDA', 'PLB'):
    a = A['PDA_PLB_swap'][cl]
    if a['n_pieces']:
        check(f'swap PDA/PLB {cl}: recall 1, naming 0', a['recall'] == 1 and a['naming'] == 0)
a = A['OM2_to_LCx']['OM2']
if a['n_pieces']:
    check('OM2 -> LCx: detected (recall 1), not named (naming 0), presence drops',
          a['recall'] == 1 and a['naming'] == 0 and a['presence'] < 1)
    check('OM2 -> background: recall 0', A['OM2_to_bg']['OM2']['recall'] == 0)
print('cases', pick)
print('ALL PASS' if not fails else f'{len(fails)} FAIL', '; scorer sha256', S.scorer_sha256())
sys.exit(1 if fails else 0)
