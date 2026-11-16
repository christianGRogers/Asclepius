"""Self-test of branch_score.py on 6 training cases (hash-chosen from the 620; never a locked or sealed case).
Each perturbation of the reference must move exactly the metric it should. Usage: python test_branch_score.py <icx>"""
import hashlib, json, os, sys
import nibabel as nb
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, f'{HERE}/../j1f_r1')
import branch_score as B            # noqa: E402
from j1f_labels import map_case     # noqa: E402

icx = sys.argv[1]
cen = json.load(open(f'{HERE}/../j1f_r1/census.json'))['rows']
train = [r['case'] for r in cen if r['group'] in ('train560', 'dev44', 'train_open16')]
assert len(train) == 620
pick = sorted(train, key=lambda c: hashlib.sha256(('asclepius-j1f-r2-scorertest:' + c).encode()).hexdigest())[:6]
V = B.VAL
fails = []


def check(name, cond):
    print(('PASS ' if cond else 'FAIL ') + name)
    if not cond: fails.append(name)


rows = {k: [] for k in ('identity', 'swap_D1_D2', 'OM2_to_LCx', 'OM2_to_bg', 'dilate1', 'PDA_PLB_swap')}
for c in pick:
    im = nb.load(os.path.join(icx, '%d.coronary.nii.gz' % (int(c[1:]) + 1)))
    lab = np.asarray(im.dataobj).astype(np.uint8); z = im.header.get_zooms()[:3]
    nz = np.argwhere(lab > 0); lo = np.maximum(nz.min(0) - 8, 0); hi = nz.max(0) + 9
    lab = lab[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    ref, _ = map_case(lab, z, 'name')                     # D47 (A): L-PDA/L-PLA -> PDA/PLB
    ref = ref.astype(np.uint8)
    p = ref.copy(); p[ref == IGN] = 0 if (IGN := B.IGNORE) else 0
    rows['identity'].append(B.score_case(ref, p, z))
    q = p.copy(); q[p == V['D1']] = V['D2']; q[p == V['D2']] = V['D1']; rows['swap_D1_D2'].append(B.score_case(ref, q, z, False))
    q = p.copy(); q[p == V['OM2']] = V['LCx']; rows['OM2_to_LCx'].append(B.score_case(ref, q, z, False))
    q = p.copy(); q[p == V['OM2']] = 0; rows['OM2_to_bg'].append(B.score_case(ref, q, z, False))
    q = p.copy(); grow = ndi.grey_dilation(p, size=(3, 3, 3)); q[(p == 0) & (grow > 0)] = grow[(p == 0) & (grow > 0)]
    rows['dilate1'].append(B.score_case(ref, q, z, False))
    q = p.copy(); q[p == V['PDA']] = V['PLB']; q[p == V['PLB']] = V['PDA']; rows['PDA_PLB_swap'].append(B.score_case(ref, q, z, False))
    # collapse: 1-F reference -> four classes equals ImageCAS-X's D25 territories (Other as census sides)
    four, st = B.collapse4(np.where(ref == B.IGNORE, 0, ref).astype(np.uint8))
    d25 = np.zeros(lab.shape, np.uint8)
    d25[lab == 1] = 1; d25[np.isin(lab, (2, 4, 5))] = 2; d25[np.isin(lab, (3, 6, 7, 8, 12, 13))] = 3
    d25[np.isin(lab, (9, 10, 11))] = 4
    m = (lab > 0) & (lab != 14) & (ref != B.IGNORE)
    check(f'{c} collapse = D25 on every non-Other voxel ({int((four[m] != d25[m]).sum())} differ)',
          bool((four[m] == d25[m]).all()))

A = {k: B.aggregate(v)['classes'] for k, v in rows.items()}
for cl in B.GATED:
    a = A['identity'][cl]
    if a['n_ref'] == 0: continue
    check(f'identity {cl}: recall, agreement, naming = 1', a['recall'] == 1 and a['agreement'] == 1 and a['naming'] == 1)
    check(f'identity {cl}: branch tF1 = 1 ({a["branch_tf1_mean"]:.3f})', abs(a['branch_tf1_mean'] - 1) < 1e-6)
    d = A['dilate1'][cl]
    check(f'dilate by 1 voxel {cl}: recall 1, naming 1', d['recall'] == 1 and d['naming'] == 1)
for cl in ('D1', 'D2'):
    a = A['swap_D1_D2'][cl]
    if a['n_ref']: check(f'swap D1/D2 {cl}: recall 1, naming 0', a['recall'] == 1 and a['naming'] == 0)
for cl in ('PDA', 'PLB'):
    a = A['PDA_PLB_swap'][cl]
    if a['n_ref']: check(f'swap PDA/PLB {cl}: recall 1, naming 0', a['recall'] == 1 and a['naming'] == 0)
a = A['OM2_to_LCx']['OM2']
if a['n_ref']:
    check('OM2 -> LCx: detected (recall 1), not named (naming 0), agreement drops',
          a['recall'] == 1 and a['naming'] == 0 and a['agreement'] < 1)
    b = A['OM2_to_bg']['OM2']
    check('OM2 -> background: recall 0', b['recall'] == 0)
print('cases', pick)
print(json.dumps({k: {c: {m: (round(x, 3) if isinstance(x, float) else x) for m, x in v.items()}
                      for c, v in A[k].items() if c in ('D1', 'D2', 'OM2', 'PDA', 'PLB')} for k in A}, indent=None)[:1500])
print('ALL PASS' if not fails else f'{len(fails)} FAIL')
