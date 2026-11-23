"""Round 2 ruling §5 item 1: Delta's 31 checks (`experiments/Delta/j1f_r2/test_branch_score.py`) and Atlas's real-case
perturbations (`experiments/Atlas/j1f_r2/validate_scorer.py`), ported to the scorer of record (`j1f_scorer.py`,
this directory), on the SAME six training cases Delta's test names (hash-chosen from the 620; never a locked, sealed
or quality-0 case). Delta's per-case aggregation is replaced by the scorer's per-piece `aggregate`; the checks are
otherwise Delta's, and Atlas's four perturbations (fold_OM, drop_PLB, trunc_PDA_40, erode1) are added as checks.
Usage: python3 test_scorer_cases.py <icx_dir>   (exit 1 on any FAIL)"""
import hashlib, json, os, sys
import nibabel as nb
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1f_scorer as S  # noqa: E402
sys.path.insert(0, os.path.join(HERE, '../../../trillium/icx4/lib'))
import territory  # noqa: E402
import importlib.util  # noqa: E402
_sp = importlib.util.spec_from_file_location('atlas_scorer', os.path.join(HERE, '../../Atlas/j1f_r2/j1f_scorer.py'))
A = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(A)
_sp = importlib.util.spec_from_file_location('atlas_val', os.path.join(HERE, '../../Atlas/j1f_r2/validate_scorer.py'))

icx_dir = sys.argv[1]
train = sorted(json.load(open(os.path.join(icx_dir, 'split.json')))['train620'])
assert len(train) == 620
pick = sorted(train, key=lambda c: hashlib.sha256(('asclepius-j1f-r2-scorertest:' + c).encode()).hexdigest())[:6]
V = {n: i for i, n in enumerate(S.NAMES)}
fails = []


def check(name, cond):
    print(('PASS ' if cond else 'FAIL ') + name, flush=True)
    if not cond:
        fails.append(name)


def truncate(lab, c, frac, z):
    """Atlas's: keep a class only within `frac` of each piece's centreline length from its root (geodesic)."""
    out = lab.copy()
    comp, _ = ndi.label(lab == c, S.S26)
    for p in S.pieces_of(lab, z)[c]:
        piece = comp == comp[p['root']]
        d = A._geodesic(piece, [p['root']], z)
        out[piece & (d > frac * max(p['length_mm'], 1e-6))] = 0
    return out


KINDS = ('identity', 'swap_D1_D2', 'OM2_to_LCx', 'OM2_to_bg', 'dilate1', 'PDA_PLB_swap',
         'fold_OM', 'drop_PLB', 'trunc_PDA_40', 'erode1')
rows = {k: [] for k in KINDS}
for c in pick:
    im = nb.load(os.path.join(icx_dir, 'segmentations', '%d.coronary.nii.gz' % (int(c[1:]) + 1)))
    lab = np.asarray(im.dataobj).astype(np.uint8); z = np.array(im.header.get_zooms()[:3], float)
    nz = np.argwhere(lab > 0); lo = np.maximum(nz.min(0) - 8, 0); hi = nz.max(0) + 9
    lab = lab[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    ref, _ = A.stage1_labels(lab, z)                       # D47 (A) + F-A3's 255 rule
    rp = S.pieces_of(ref, z)
    p = np.where(ref == S.IGNORE, 0, ref).astype(np.uint8)
    preds = {'identity': p}
    q = p.copy(); q[p == V['D1']] = V['D2']; q[p == V['D2']] = V['D1']; preds['swap_D1_D2'] = q
    q = p.copy(); q[p == V['OM2']] = V['LCx']; preds['OM2_to_LCx'] = q
    q = p.copy(); q[p == V['OM2']] = 0; preds['OM2_to_bg'] = q
    g = ndi.grey_dilation(p, size=(3, 3, 3)); q = p.copy(); m = (p == 0) & (g > 0); q[m] = g[m]; preds['dilate1'] = q
    q = p.copy(); q[p == V['PDA']] = V['PLB']; q[p == V['PLB']] = V['PDA']; preds['PDA_PLB_swap'] = q
    q = p.copy(); q[np.isin(p, (8, 9))] = 3; preds['fold_OM'] = q
    q = p.copy(); q[p == 12] = 0; preds['drop_PLB'] = q
    preds['trunc_PDA_40'] = truncate(p, 11, 0.4, z)
    preds['erode1'] = np.where(ndi.binary_erosion(p > 0), p, 0).astype(np.uint8)
    for k in KINDS:
        rows[k].append(S.score_case(ref, preds[k], z, with_tf1=(k == 'identity'), ref_pieces=rp))
    # collapse: 1-F reference -> four classes equals ImageCAS-X's D25 territories outside "Other" and 255
    st = {}
    four = S.collapse4(ref, z, st)
    d25 = territory.to_four(lab, z)
    m = (lab > 0) & (lab != 14) & (ref != S.IGNORE)
    check(f'{c} collapse = D25 on every non-Other voxel ({int((four[m] != d25[m]).sum())} differ), '
          f'fallbacks {st["fallback"]}', bool((four[m] == d25[m]).all()) and st['fallback'] == 0)

AG = {k: S.aggregate(v) for k, v in rows.items()}
for cl in ('D1', 'D2', 'OM1', 'OM2', 'PDA', 'PLB'):
    a = AG['identity'][cl]
    if a['pieces'] == 0:
        continue
    check(f'identity {cl}: recall, presence, naming = 1', a['recall'] == 1 and a['presence'] == 1 and a['naming'] == 1)
    check(f'identity {cl}: branch tF1 = 1 ({a["branch_tf1_mean"]:.3f})', abs(a['branch_tf1_mean'] - 1) < 1e-6)
    d = AG['dilate1'][cl]
    check(f'dilate by 1 voxel {cl}: recall 1, naming 1', d['recall'] == 1 and d['naming'] == 1)
for cl in ('D1', 'D2'):
    a = AG['swap_D1_D2'][cl]
    if a['pieces']:
        check(f'swap D1/D2 {cl}: recall 1, naming 0', a['recall'] == 1 and a['naming'] == 0)
for cl in ('PDA', 'PLB'):
    a = AG['PDA_PLB_swap'][cl]
    if a['pieces']:
        check(f'swap PDA/PLB {cl}: recall 1, naming 0', a['recall'] == 1 and a['naming'] == 0)
a = AG['OM2_to_LCx']['OM2']
if a['pieces']:
    check('OM2 -> LCx: recall 1, naming 0, presence drops', a['recall'] == 1 and a['naming'] == 0 and a['presence'] < 1)
    check('OM2 -> background: recall 0', AG['OM2_to_bg']['OM2']['recall'] == 0)
# Atlas's perturbations, as checks
for cl in ('OM1', 'OM2'):
    a = AG['fold_OM'][cl]
    if a['pieces']:
        check(f'fold OM -> LCx {cl}: recall 1, naming 0', a['recall'] == 1 and a['naming'] == 0)
a = AG['drop_PLB']['PLB']
check('drop PLB: recall 0', a['pieces'] == 0 or a['recall'] == 0)
a = AG['trunc_PDA_40']['PDA']
check(f'truncate PDA to 40 %: recall <= 0.5 ({a["recall"]:.2f})', a['pieces'] == 0 or a['recall'] <= 0.5)
e = AG['erode1']
check('erode by 1 voxel: recall >= 0.9 in every gated class (1.5 mm tolerance) ' +
      str({k: round(e[k]['recall'], 2) for k in ('D1', 'D2', 'OM1', 'OM2', 'PDA', 'PLB')}),
      all(e[k]['recall'] >= 0.9 for k in ('D1', 'D2', 'OM1', 'OM2', 'PDA', 'PLB') if e[k]['pieces']))
print('cases', pick)
print(json.dumps({k: {c: {m: (round(x, 3) if isinstance(x, float) else x) for m, x in AG[k][c].items()
                          if m in ('pieces', 'recall', 'presence', 'naming')}
                      for c in ('D1', 'D2', 'OM1', 'OM2', 'PDA', 'PLB')} for k in AG}))
print('scorer sha256', S.scorer_sha256())
print('ALL PASS' if not fails else f'{len(fails)} FAIL', f'({len(fails)} fail)')
sys.exit(1 if fails else 0)
