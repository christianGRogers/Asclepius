"""Janus 1-F round 2 (Foxtrot), pass 1 over D45's 620 training labels only (CPU).

Per case: (1) the 1-F stage-1 labels (labels_r2.map13) and their origin collapse checked against icx4's
territory.to_four (D25); (2) the branch scorer's identity and perturbation self-tests; (3) the census the gate
simulation needs (pieces, centreline length, presence at 3 and 5 mm, ordinal siblings); (4) unnamed trunk twigs by
the three round-1 methods (Delta, Foxtrot, Crucible) on the same cases; (5) dominance from labels.
Refuses any file that is not one of the 620 (split620.json, pinned to L-A1's train pin).
Usage: python3 pass1.py <label_dir> <out.jsonl> [nproc]          (census + identity, all 620)
       python3 pass1.py <label_dir> <out.jsonl> [nproc] selftest (tF1 + perturbations, the 20 fit-check cases)
"""
import hashlib, json, os, sys
from multiprocessing import Pool
import numpy as np, nibabel as nb

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, f'{HERE}/../../../trillium/icx4/lib', f'{HERE}/../../Delta/j1f_r1', f'{HERE}/../j1f']
import labels_r2 as L  # noqa
import branch_score as B  # noqa
import territory  # noqa
import census as dcen  # noqa  (Delta v1)
import census14 as fcen  # noqa  (Foxtrot v1)
from skimage.morphology import skeletonize  # noqa
from skan import Skeleton, summarize  # noqa

SPLIT = json.load(open(f'{HERE}/../j1f/split620.json'))
TRAIN = set(SPLIT['train620'])
assert hashlib.sha256('\n'.join(sorted(TRAIN)).encode()).hexdigest() == \
    '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
SELFTEST = set(json.load(open(f'{HERE}/results/fitcheck20.json'))['fitcheck20'])  # tF1 + perturbations here only


def crucible_twigs(lab, z):
    sk = skeletonize(lab > 0)
    out = {2: [], 3: [], 9: []}
    try:
        S = Skeleton(sk, spacing=z); df = summarize(S, separator='_')
        pid = np.asarray(S.path_label_image())[sk]; cls = lab[sk].astype(np.int64)
        keep = (pid > 0) & (cls > 0); pid, cls = pid[keep] - 1, cls[keep]
        tab = np.zeros((len(df), 15), np.int64); np.add.at(tab, (pid, cls), 1)
        for i, row in enumerate(df.itertuples(index=False)):
            if not tab[i].sum():
                continue
            maj = int(tab[i].argmax()); Ln = float(row.branch_distance)
            if row.branch_type == 1 and maj in out and tab[i, maj] == tab[i].sum() and Ln >= 3.0:
                out[maj].append(round(Ln, 2))
    except Exception as e:
        return {'error': repr(e)[:100]}
    # Crucible subtracts the longest per class (the trunk's own distal end)
    return {k: sorted(v, reverse=True)[1:] for k, v in out.items()}


def perturb(ref, kind):
    p = ref.copy(); p[p == 255] = 0
    if kind == 'swap_D1_D2':
        p[ref == 5] = 6; p[ref == 6] = 5
    elif kind == 'drop_OM2':
        p[ref == 9] = 0
    elif kind == 'types_to_parent':
        for c, par in {5: 2, 6: 2, 7: 2, 8: 3, 9: 3, 10: 3}.items():
            p[ref == c] = par
    elif kind == 'erode_branches':   # thin every branch to its skeleton +1 voxel: detection must survive
        from scipy import ndimage as ndi
        br = np.isin(ref, list(B.BRANCH))
        keep = ndi.binary_dilation(skeletonize(br), iterations=1) & br
        p[br & ~keep] = 0
    return p


def one(path, selftest=None):
    cid = 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1)
    assert cid in TRAIN, cid
    im = nb.load(path); z = np.array(im.header.get_zooms()[:3], float)
    raw = np.asarray(im.dataobj).astype(np.uint8)
    sl = L.crop(raw, 4); raw = raw[sl]
    lab13, info = L.map13(raw, z)
    four = L.collapse4(lab13, z); ref4 = territory.to_four(raw, z)
    m = (lab13 != 255)
    row = {'case': cid, 'info': info, 'collapse_mismatch': int(((four != ref4) & m).sum()),
           'collapse_mismatch_left_pda': int(((four != ref4) & m & np.isin(raw, [12, 13])).sum()),
           'ignore_voxels': int((~m).sum()), 'tree_voxels': int((raw > 0).sum())}
    tf = selftest if selftest is not None else False
    ident = B.score_case(lab13, np.where(lab13 == 255, 0, lab13), z, with_tf1=tf)
    row['identity'] = ident
    row['census'] = {k: {'pieces_mm': [p['mm'] for p in v['pieces']], 'ref_mm': v['ref_mm']} for k, v in ident.items()}
    if tf:
        row['perturb'] = {k: B.score_case(lab13, perturb(lab13, k), z, with_tf1=(k == 'swap_D1_D2'))
                          for k in ('swap_D1_D2', 'drop_OM2', 'types_to_parent', 'erode_branches')}
    dcen.MIN_BRANCH_MM = 3.0
    row['twigs'] = {'delta': {nm: [b['mm'] for b in dcen.side_branches(raw, k, z)] for nm, k in (('LAD', 2), ('RCA', 9), ('LCx', 3))},
                    'foxtrot': {nm: [t['len_mm'] for t in fcen.twigs(raw == k, z)['twigs']] for nm, k in (('LAD', 2), ('RCA', 9), ('LCx', 3))},
                    'crucible': {nm: v for nm, v in zip(('LAD', 'LCx', 'RCA'), (lambda d: [d.get(2, []), d.get(3, []), d.get(9, [])])(crucible_twigs(raw, z)))}}
    cnt = np.bincount(raw.ravel(), minlength=15)
    row['post'] = {k: bool(cnt[v]) for k, v in (('R-PDA', 10), ('R-PLA', 11), ('L-PDA', 12), ('L-PLA', 13))}
    return row


if __name__ == '__main__':
    d, out = sys.argv[1], sys.argv[2]
    npr = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    st = len(sys.argv) > 4 and sys.argv[4] == 'selftest'
    files = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith('.coronary.nii.gz'))
    if st:
        files = [f for f in files if 'c%04d' % (int(os.path.basename(f).split('.')[0]) - 1) in SELFTEST]
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)['case'] for l in open(out)}
    todo = [f for f in files if 'c%04d' % (int(os.path.basename(f).split('.')[0]) - 1) not in done]
    with Pool(npr) as p, open(out, 'a') as fo:
        from functools import partial
        for i, r in enumerate(p.imap_unordered(partial(one, selftest=st), todo)):
            fo.write(json.dumps(r) + '\n'); fo.flush()
            if i % 25 == 0:
                print(i, r['case'], flush=True)
