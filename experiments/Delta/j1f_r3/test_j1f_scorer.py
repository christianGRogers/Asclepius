"""Janus 1-F round 3 (Delta): the scorer of record's tests (F-A16), on training fixtures only.

  1. Atlas's synthetic self-test (j1f_scorer.selftest) and the converter's (j1f_labels.selftest).
  2. Delta's round-2 checks (test_branch_score.py), ported to the per-piece scorer and F-A15's gate file, on six
     training cases chosen by sha256('asclepius-j1f-r2-scorertest:' + id) from the D45 620 (the same six as round 2):
     identity, a one-voxel dilation, D1<->D2 swap, PDA<->PLB swap, OM2 -> LCx, OM2 -> background, and the collapse
     (SegQueue's, on the 1-F reference) equal to ImageCAS-X's D25 territories on every non-"Other", non-255 voxel.
  3. Added this round: a prediction holding 255 scores as background; an OM2 truncated to its root 30 % of
     centreline is not detected.

Usage: python test_j1f_scorer.py <icx620_dir> <split_j1l.json>
"""
import hashlib, json, os, sys
import nibabel as nb
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1f_scorer as S     # noqa: E402
import j1f_labels as L     # noqa: E402
import j1f_gate as G       # noqa: E402

icx, split = sys.argv[1], json.load(open(sys.argv[2]))
train = sorted(split['train620'])
assert hashlib.sha256('\n'.join(train).encode()).hexdigest() == \
    '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
locked = set(split['locked100'])
pick = sorted(train, key=lambda c: hashlib.sha256(('asclepius-j1f-r2-scorertest:' + c).encode()).hexdigest())[:6]
assert not set(pick) & locked
V = {n: i for i, n in enumerate(S.NAMES)}
fails = []


def check(name, cond):
    print(('PASS ' if cond else 'FAIL ') + name, flush=True)
    if not cond:
        fails.append(name)


S.selftest(); L.selftest(); G.selftest()
gates = G.load()
rows = {k: [] for k in ('identity', 'swap_D1_D2', 'OM2_to_LCx', 'OM2_to_bg', 'dilate1', 'PDA_PLB_swap', 'with255',
                        'OM2_trunc')}
for c in pick:
    im = nb.load(os.path.join(icx, '%d.coronary.nii.gz' % (int(c[1:]) + 1)))
    lab = np.asarray(im.dataobj).astype(np.uint8); z = tuple(float(v) for v in im.header.get_zooms()[:3])
    nz = np.argwhere(lab > 0); lo = np.maximum(nz.min(0) - 8, 0); hi = nz.max(0) + 9
    lab = lab[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    ref, _ = L.map13(lab, z)
    rp = S.pieces_of(ref, z)
    p = np.where(ref == S.IGNORE, 0, ref).astype(np.uint8)
    sc = lambda q, t=False: S.score_case(ref, q, z, with_tf1=t, ref_pieces=rp)
    rows['identity'].append(sc(p, True))
    q = p.copy(); q[p == V['D1']] = V['D2']; q[p == V['D2']] = V['D1']; rows['swap_D1_D2'].append(sc(q))
    q = p.copy(); q[p == V['OM2']] = V['LCx']; rows['OM2_to_LCx'].append(sc(q))
    q = p.copy(); q[p == V['OM2']] = 0; rows['OM2_to_bg'].append(sc(q))
    grow = ndi.grey_dilation(p, size=(3, 3, 3)); q = p.copy(); m = (p == 0) & (grow > 0); q[m] = grow[m]
    rows['dilate1'].append(sc(q))
    q = p.copy(); q[p == V['PDA']] = V['PLB']; q[p == V['PLB']] = V['PDA']; rows['PDA_PLB_swap'].append(sc(q))
    q = p.copy(); q[ref == S.IGNORE] = S.IGNORE; rows['with255'].append(sc(q))
    q = p.copy()                           # OM2 cut back to the 30 % of its centreline nearest its root
    for pc in rp[V['OM2']]:
        d = np.linalg.norm((pc['pts'] - np.array(pc['root'])) * np.array(z), axis=1)
        far = pc['pts'][d > np.quantile(d, 0.30)]
        om = (ref == V['OM2'])
        if len(far):
            mk = np.zeros(ref.shape, bool); mk[tuple(far.T)] = True
            mk = ndi.binary_dilation(mk, np.ones((3, 3, 3), bool), iterations=6) & om
            q[mk] = 0
    rows['OM2_trunc'].append(sc(q))
    four = S.collapse4(np.where(ref == S.IGNORE, 0, ref))
    d25 = np.zeros(lab.shape, np.uint8)
    d25[lab == 1] = 1; d25[np.isin(lab, (2, 4, 5))] = 2; d25[np.isin(lab, (3, 6, 7, 8, 12, 13))] = 3
    d25[np.isin(lab, (9, 10, 11))] = 4
    m = (lab > 0) & (lab != 14) & (ref != S.IGNORE)
    check(f'{c} SegQueue collapse = D25 on every non-Other voxel ({int((four[m] != d25[m]).sum())} differ)',
          bool((four[m] == d25[m]).all()))

A = {k: G.aggregate(v, gates)['classes'] for k, v in rows.items()}
TF = {cl: [r[cl]['tf1'] for r in rows['identity'] if 'tf1' in r[cl]] for cl in G.GATED}
for cl in G.GATED:
    a = A['identity'][cl]
    if a['pieces'] == 0:
        continue
    check(f'identity {cl}: recall, presence, naming = 1', a['recall'] == 1 and a['presence'] == 1 and a['naming'] == 1)
    check(f'identity {cl}: branch tF1 = 1 ({np.mean(TF[cl]):.3f})', abs(np.mean(TF[cl]) - 1) < 1e-6)
    d = A['dilate1'][cl]
    check(f'dilate by 1 voxel {cl}: recall 1, naming 1', d['recall'] == 1 and d['naming'] == 1)
    w = A['with255'][cl]
    check(f'255 in the prediction scores as background {cl}: identity numbers', w['recall'] == 1 and w['naming'] == 1)
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
    check('OM2 -> LCx: detected (recall 1), not named (naming 0), presence drops',
          a['recall'] == 1 and a['naming'] == 0 and a['presence'] < 1)
    check('OM2 -> background: recall 0', A['OM2_to_bg']['OM2']['recall'] == 0)
    check(f"OM2 cut to its root 30 %: not detected (recall {A['OM2_trunc']['OM2']['recall']:.2f})",
          A['OM2_trunc']['OM2']['recall'] == 0)
print('cases', pick)
print(json.dumps({k: {c: {m: (round(x, 3) if isinstance(x, float) else x) for m, x in v.items()
                          if m in ('pieces', 'recall', 'presence', 'naming')}
                      for c, v in A[k].items()} for k in A}))
print('scorer sha256', S.scorer_sha256())
print('ALL PASS' if not fails else f'{len(fails)} FAIL')
sys.exit(1 if fails else 0)
