"""Janus 1-F round 1 (Atlas): can ordinal branch names (D1/D2/D3, OM1/OM2) be assigned by a rule, so that a network
only has to learn branch TYPES (diagonal, obtuse marginal, ...)? Measured on ImageCAS-X's own labels, training cases
only (split.json 'training_620_both'); no CT, no prediction, no locked/sealed case.

Reference (D44 classes as ImageCAS-X can give them; D45 1-F numbering below): LM, LAD, LCx, RCA; D1, D2; D3 = the
most proximal LAD-side 'Other' component (>= 20 voxels), further LAD-side 'Other' -> LAD (D4+ have no D44 class);
OM1, OM2; LCx-side 'Other' -> LCx (OM3+); IM -> Ramus; R-PDA, L-PDA -> PDA; R-PLA, L-PLA -> PLB.
'Other' components touching both sides or neither, and the < 20-voxel specks, are left out of both (label 0 in both).

Rule: take the union of each type (D = D1 + D2 + LAD-side Other; OM = OM1 + OM2 + LCx-side Other), split it into
26-connected components (>= 20 voxels), order them by origin = the smallest geodesic distance from the LM along the
left tree, and name them D1, D2, D3 (then LAD) and OM1, OM2 (then LCx). Everything else is copied from the reference.
So the rule's only freedom is the ordinal, and the score difference is the cost of naming ordinals by rule.

Score: tree-F1 @ 1.5 mm per class with the pinned src/segtrain/tf1.py (sha256 24441cf8...5254, unchanged): its
module-level CLASSES is set to 1..12 at run time. Ostia from the reference alone (provisional; the same in both arms).
Usage: python ordinal_rule.py <data_dir> <split.json> <repo_root> <out.jsonl> [n_proc]"""
import os, sys, json, hashlib
from multiprocessing import Pool
import numpy as np, nibabel as nib
from scipy import ndimage as ndi

DATA, SPLIT, ROOT, OUT = sys.argv[1:5]
NP = int(sys.argv[5]) if len(sys.argv) > 5 else 4
TF1 = os.path.join(ROOT, 'src', 'segtrain', 'tf1.py')
assert hashlib.sha256(open(TF1, 'rb').read()).hexdigest() == \
    '24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254', 'tf1.py is not the pinned A1c file'
sys.path.insert(0, os.path.join(ROOT, 'src'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segtrain import tf1  # noqa: E402
from census import geodesic_from, S26  # noqa: E402  (pure functions; census's CLI does not run on import)

F = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA', 5: 'D1', 6: 'D2', 7: 'D3', 8: 'OM1', 9: 'OM2', 10: 'Ramus', 11: 'PDA', 12: 'PLB'}
tf1.CLASSES = tuple(F)
tf1.CLASS_NAMES = dict(F)
ICX = {1: 1, 2: 2, 3: 3, 9: 4, 4: 5, 5: 6, 6: 8, 7: 9, 8: 10, 10: 11, 12: 11, 11: 12, 13: 12}  # ImageCAS-X -> F
LAD_SIDE, LCX_SIDE = {2, 4, 5}, {3, 6, 7, 12, 13}
LEFT = [1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14]


def reference(lab):
    ref = np.zeros(lab.shape, np.uint8)
    for a, b in ICX.items():
        ref[lab == a] = b
    cc, n = ndi.label(lab == 14, S26)
    lad_side, lcx_side = [], []
    for k in range(1, n + 1):
        c = cc == k
        if c.sum() < 20:
            continue
        t = set(np.unique(lab[ndi.binary_dilation(c, S26) & ~c]).tolist()) - {0, 14}
        if t & LAD_SIDE and not t & LCX_SIDE:
            lad_side.append(c)
        elif t & LCX_SIDE and not t & LAD_SIDE:
            ref[c] = 3   # OM3+ -> LCx
    return ref, lad_side


def one(cid):
    im = nib.load(os.path.join(DATA, f'{int(cid[1:]) + 1}.coronary.nii.gz'))
    lab = np.asarray(im.dataobj).astype(np.uint8)
    nz = np.argwhere(lab > 0); lo, hi = np.maximum(nz.min(0) - 3, 0), nz.max(0) + 4
    lab = lab[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    sp = np.array(im.header.get_zooms()[:3], float)
    if not (lab == 1).any():
        return {'case': cid, 'skipped': 'no LM'}
    ref, lad_side = reference(lab)
    g = geodesic_from(np.isin(lab, LEFT), lab == 1)
    origin = lambda c: float(g[c & (g >= 0)].min()) if (c & (g >= 0)).any() else 1e9
    if lad_side:   # D3 = most proximal LAD-side Other; the rest -> LAD
        lad_side.sort(key=origin)
        ref[lad_side[0]] = 7
        for c in lad_side[1:]:
            ref[c] = 2
    rule = ref.copy()
    info = {}
    for typ, members, names, parent in (('D', (5, 6, 7), (5, 6, 7), 2), ('OM', (8, 9), (8, 9), 3)):
        u = np.isin(ref, members)
        cc, n = ndi.label(u, S26)
        comps = [cc == k for k in range(1, n + 1) if (cc == k).sum() >= 20]
        comps.sort(key=origin)
        rule[u] = parent   # specks and surplus components fall back to the parent
        for i, c in enumerate(comps):
            rule[c] = names[i] if i < len(names) else parent
        info[typ] = {'ref_branches': int(len(set(np.unique(ref[u]).tolist()) - {0})), 'rule_components': len(comps)}
    ost = tf1.find_ostia(ref, sp)
    s = tf1.tree_f1(ref, rule, sp, ostia=ost)
    identical = {F[c]: bool(((ref == c) == (rule == c)).all()) for c in F if (ref == c).any()}
    return {'case': cid, 'tf1_per_class': {F[c]: round(v, 4) for c, v in s.per_class.items()},
            'identical_class_masks': identical, 'branches': info}


if __name__ == '__main__':
    cases = json.load(open(SPLIT))['training_620_both']
    done = {json.loads(l)['case'] for l in open(OUT)} if os.path.exists(OUT) else set()
    todo = [c for c in cases if c not in done]
    print(f'{len(cases)} cases, {len(todo)} to do', flush=True)
    with Pool(NP) as p, open(OUT, 'a') as f:
        for i, r in enumerate(p.imap_unordered(one, todo, chunksize=2)):
            f.write(json.dumps(r) + '\n'); f.flush()
            if i % 50 == 0:
                print(i, flush=True)
