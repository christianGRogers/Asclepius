"""Janus 1-F: the branch scorer of record (F-A16), round 3 (Delta). Atlas's round-2 `j1f_scorer.py`
(sha256 2da3cb1a...886c) with F-A16/F-A17's one change and F-A18's consequence:

  * `collapse4` is SegQueue's: `segqueue14.labels.collapse_to_four` / `assign_contact_branches`, imported and pinned by
    the sha256 of `src/segqueue14/labels.py` (F-A17). Atlas's one-voxel-ring collapse is deleted.
  * `stage1_labels` is deleted. The converter of record is `j1f_labels.py` (F-A18); one converter, not two.
  * Every other line is Atlas's, byte for byte, so the definitions F-A15's lines were simulated on are unchanged.

Stage-1 values: 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA, 5 D1, 6 D2, 7 D3, 8 OM1, 9 OM2, 10 Ramus, 11 PDA, 12 PLB, 255 ignore.

Frozen definitions (every constant is a module-level name, so the hash freezes it):
  * PIECE: a 26-connected component of one branch class with >= MIN_PIECE_VOX voxels. R-PDA in two pieces is two
    pieces, each with its own root.
  * CENTRELINE of a piece: the skeleton of the WHOLE reference tree (ref in 1..12) restricted to the piece; if empty,
    the piece's maximal-EDT voxels (A1c's fallback, as tf1._fallback_points).
  * LENGTH: the minimum-spanning-forest length (mm) of the 26-graph on the centreline points.
  * ROOT of a piece: its centreline point nearest (mm) to any voxel of the piece's PARENT class set (LAD for D1-D3;
    LCx for OM1, OM2, Ramus; LCx or RCA, whichever is nearer, for PDA/PLB); else its first point.
  * PRESENCE of class c in a map: total centreline length of c's pieces >= PRESENCE_MM (5 mm). The prediction's
    centreline is the skeleton of the prediction's own tree.
  * DETECTION of a reference piece: >= DETECT_FRACTION (0.5) of its centreline points lie within TOL_MM (1.5 mm, D3)
    of a predicted vessel voxel of ANY class (prediction cleaned of 26-components < MIN_PRED_VOX).
  * NAMING of a detected piece: each covered centreline point takes the label of its nearest predicted voxel; the
    piece is named right if STRICTLY more than half of its covered points carry the piece's class (ties wrong).
  * BRANCH tF1 of class c (report): segtrain.tf1.tree_f1 on (ref == c, pred == c), one ostium per reference piece at
    its ROOT, min_component_voxels = MIN_PRED_VOX, tol 1.5 mm. tf1.py's sha256 is checked at import.
  * FOUR-CLASS COLLAPSE: SegQueue's, D47 Q1. D1-D3 -> LAD; OM1, OM2, Ramus -> LCx; each PDA/PLB 26-component -> the
    vessel (LCx or RCA) with the most face contact, the chain rule for a component reached only through another, RCA
    on a tie or no contact (counted in `stats`). 255 -> 0.

Gate lines are not in this file: they are `j1f_gates.json` (F-A15), read by `j1f_gate.py`.
Nothing here reads a file: callers pass arrays. Self-test: python j1f_scorer.py selftest
"""
import hashlib
import os
import sys

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '../../../src'))
_TF1 = os.path.join(_HERE, '../../../src/segtrain/tf1.py')
TF1_SHA256 = '24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254'
assert hashlib.sha256(open(_TF1, 'rb').read()).hexdigest() == TF1_SHA256, 'tf1.py is not the A1c scorer'
from segtrain import tf1 as _tf1  # noqa: E402
_SQL = os.path.join(_HERE, '../../../src/segqueue14/labels.py')
SQ_LABELS_SHA256 = '5f69b5bef59ad1346c5877a43c65daf7bdf1329b0ca7e427b6addd55d0000a4b'
assert hashlib.sha256(open(_SQL, 'rb').read()).hexdigest() == SQ_LABELS_SHA256, 'labels.py is not the pinned SegQueue'
from segqueue14 import labels as _sq  # noqa: E402

NAMES = ['bg', 'LM', 'LAD', 'LCx', 'RCA', 'D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB']
BRANCHES = (5, 6, 7, 8, 9, 10, 11, 12)
GATED = (5, 6, 8, 9, 11, 12)                      # D1, D2, OM1, OM2, PDA, PLB (F-A6)
IGNORE = 255
PARENT = {5: (2,), 6: (2,), 7: (2,), 8: (3,), 9: (3,), 10: (3,), 11: (3, 4), 12: (3, 4)}
LCX_TERR, RCA_TERR = (3, 8, 9, 10), (4,)
MIN_PIECE_VOX = 20
MIN_PRED_VOX = 20
PRESENCE_MM = 5.0
DETECT_FRACTION = 0.5
TOL_MM = 1.5
S26 = np.ones((3, 3, 3), bool)


# ------------------------------------------------------------------------------------------- collapse (F-A17)
_SQ_NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA', 5: 'D1', 6: 'D2', 7: 'D3', 8: 'OM1', 9: 'OM2', 10: 'Ramus',
             11: 'PDA', 12: 'PLB'}
_TO_VAL = {'LM': 1, 'LAD': 2, 'LCx': 3, 'RCA': 4}


def collapse4(lab, zooms=None, stats=None):
    """1-F map -> 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA by SegQueue's `collapse_to_four` (F-A17). 255 -> 0. `zooms` is
    unused (contact is counted in voxels); kept for the call signature. `stats`, when a dict, receives SegQueue's
    counts without the masks (components, byParent, fallback, fallbackTie, fallbackUnattached, perClass)."""
    lab = np.asarray(lab)
    vals = sorted(_SQ_NAMES)
    masks = np.stack([lab == v for v in vals])
    st = {}
    four = _sq.collapse_to_four(masks, [_SQ_NAMES[v] for v in vals], stats=st)
    out = np.zeros(lab.shape, np.uint8)
    for k, n in enumerate(_sq.NAMES):
        out[four[k] != 0] = _TO_VAL[n]
    if stats is not None:
        stats.clear()
        stats.update({k: v for k, v in st.items() if k != 'masks'})
    return out


# ------------------------------------------------------------------------------------------- geometry
def _skeleton(mask):
    return _tf1._skeletonise(mask)


def _graph_length(pts, sp):
    """Length (mm) of the 26-graph on the point set: each edge counted once."""
    if len(pts) < 2:
        return 0.0
    tree = cKDTree(pts * sp)
    pairs = tree.query_pairs(r=float(np.linalg.norm(sp)) + 1e-6, output_type='ndarray')
    if not len(pairs):
        return 0.0
    dv = np.abs(pts[pairs[:, 0]] - pts[pairs[:, 1]])
    pairs = pairs[(dv <= 1).all(1)]
    if not len(pairs):
        return 0.0
    # keep a spanning forest so diagonal + axial triangles are not double-counted
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import minimum_spanning_tree
    w = np.linalg.norm((pts[pairs[:, 0]] - pts[pairs[:, 1]]) * sp, axis=1)
    g = coo_matrix((w, (pairs[:, 0], pairs[:, 1])), shape=(len(pts), len(pts)))
    return float(minimum_spanning_tree(g).sum())


def _pieces(lab, c, skel, sp, parent_mask=None):
    """Pieces of class c: list of dicts {pts (N,3) centreline, length_mm, root (3,), vox}."""
    m = lab == c
    if not m.any():
        return []
    comp, nc = ndi.label(m, S26)
    out = []
    objs = ndi.find_objects(comp)
    for i in range(1, nc + 1):
        sl = objs[i - 1]
        p = comp[sl] == i
        nvox = int(p.sum())
        if nvox < MIN_PIECE_VOX:
            continue
        off = np.array([s.start for s in sl])
        pts = np.argwhere(p & skel[sl]) + off
        if not len(pts):
            pts = _tf1._fallback_points(p, sp) + off
        root = None
        if parent_mask is not None:
            win = tuple(slice(max(s.start - 12, 0), s.stop + 12) for s in sl)
            par = np.argwhere(parent_mask[win]) + np.array([s.start for s in win])
            if len(par):
                d, _ = cKDTree(par * sp).query(pts * sp)
                root = pts[int(np.argmin(d))]
        if root is None:
            root = pts[0]
        out.append({'pts': pts, 'length_mm': _graph_length(pts, sp), 'root': tuple(int(v) for v in root),
                    'vox': nvox})
    return out


def pieces_of(lab, zooms):
    """All branch pieces of a 1-F map, keyed by class."""
    lab = np.asarray(lab)
    sp = np.asarray(zooms[:3], float)
    tree = (lab > 0) & (lab != IGNORE)
    skel = _skeleton(tree)
    res = {}
    for c in BRANCHES:
        pm = np.isin(lab, PARENT[c])
        res[c] = _pieces(lab, c, skel, sp, pm)
    return res


def presence(pcs):
    return {c: float(sum(p['length_mm'] for p in pcs.get(c, []))) >= PRESENCE_MM for c in BRANCHES}


# ------------------------------------------------------------------------------------------- scoring
def score_case(ref, pred, zooms, with_tf1=True, ref_pieces=None):
    """Per-class branch measures of `pred` against `ref` (both 1-F maps, same grid)."""
    ref, pred = np.asarray(ref), np.asarray(pred)
    sp = np.asarray(zooms[:3], float)
    pred = np.where(pred == IGNORE, 0, pred)
    pm = _tf1.remove_small_components(pred > 0, MIN_PRED_VOX)
    pred = np.where(pm, pred, 0)
    rp = ref_pieces if ref_pieces is not None else pieces_of(ref, zooms)
    pp = pieces_of(pred, zooms)
    pres_r, pres_p = presence(rp), presence(pp)
    if pm.any():
        dist, idx = ndi.distance_transform_edt(~pm, sampling=sp, return_indices=True)
    out = {}
    for c in BRANCHES:
        rows = []
        for p in rp[c]:
            q = tuple(p['pts'].T)
            if not pm.any():
                rows.append({'len': p['length_mm'], 'detected': False, 'named': False, 'cover': 0.0}); continue
            cov = dist[q] <= TOL_MM
            frac = float(cov.mean())
            det = frac >= DETECT_FRACTION
            named = False
            if det:
                nn = tuple(idx[:, q[0][cov], q[1][cov], q[2][cov]])
                named = bool((pred[nn] == c).sum() * 2 > cov.sum())
            rows.append({'len': p['length_mm'], 'detected': det, 'named': named, 'cover': frac})
        r = {'pieces': rows, 'present_ref': pres_r[c], 'present_pred': pres_p[c]}
        if with_tf1 and rp[c]:
            ost = _tf1.OstiumReport([_tf1.Ostium(tree=i, point=p['root'], rule='origin')
                                     for i, p in enumerate(rp[c])], provisional=False, rules=('origin',))
            t = _tf1.tree_f1((ref == c).astype(np.uint8), (pred == c).astype(np.uint8), sp, tol_mm=TOL_MM,
                             ostia=ost, min_component_voxels=MIN_PRED_VOX)
            r['tf1'] = float(t.per_class.get(1, 0.0))
        out[NAMES[c]] = r
    return out


def scorer_sha256():
    return hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest()


# ------------------------------------------------------------------------------------------- self-test
def _toy():
    """A synthetic left tree: LM -> LAD with D1, D2 off it; LCx with OM1 and a PDA; an RCA with a PLB."""
    a = np.zeros((40, 90, 90), np.uint8)
    a[20, 10:14, 10] = 1                       # LM
    a[20, 14:70, 10] = 2                       # LAD
    a[20, 25, 11:45] = 5                       # D1
    a[20, 45, 11:32] = 6                       # D2
    a[21:38, 13, 10] = 3                       # LCx (down in z)
    a[30, 13, 11:32] = 8                       # OM1
    a[37, 14:36, 10] = 11                      # left PDA, off the LCx tip
    a[5:15, 60, 60] = 4                        # RCA (separate tree)
    a[15, 60, 61:85] = 12                      # PLB off the RCA
    return a


def selftest():
    sp = (0.5, 0.5, 0.5)
    ref = _toy()
    s = score_case(ref, ref.copy(), sp)
    for k in ('D1', 'D2', 'OM1', 'PDA', 'PLB'):
        assert s[k]['present_ref'] and s[k]['present_pred'], k
        assert all(p['detected'] and p['named'] for p in s[k]['pieces']), k
        assert abs(s[k]['tf1'] - 1.0) < 1e-9, (k, s[k]['tf1'])
    c4 = collapse4(ref, sp)
    assert (c4[ref == 11] == 3).all(), 'left PDA must collapse to the LCx (D47 Q1)'
    assert (c4[ref == 12] == 4).all(), 'PLB off the RCA must collapse to the RCA'
    assert (c4[np.isin(ref, (5, 6))] == 2).all() and (c4[ref == 8] == 3).all()
    # swap D1/D2 names: detected, misnamed
    sw = ref.copy(); sw[ref == 5] = 6; sw[ref == 6] = 5
    s = score_case(ref, sw, sp)
    assert all(p['detected'] and not p['named'] for p in s['D1']['pieces'] + s['D2']['pieces'])
    # drop D2 entirely: not detected, presence disagrees
    dr = ref.copy(); dr[ref == 6] = 0
    s = score_case(ref, dr, sp)
    assert not s['D2']['pieces'][0]['detected'] and s['D2']['present_ref'] and not s['D2']['present_pred']
    # a D2 drawn as LAD (parent): detected, misnamed (a fold into the parent)
    fo = ref.copy(); fo[ref == 6] = 2
    s = score_case(ref, fo, sp)
    assert s['D2']['pieces'][0]['detected'] and not s['D2']['pieces'][0]['named']
    # truncate OM1 to its proximal 30 %: below the 0.5 detection line
    tr = ref.copy(); tr[30, 13, 17:30] = 0
    s = score_case(ref, tr, sp)
    assert not s['OM1']['pieces'][0]['detected'], s['OM1']['pieces']
    # a D1 cut off from its origin: tF1 recall falls (rooted at origin), detection does not
    cut = ref.copy(); cut[20, 25, 11:15] = 0
    s = score_case(ref, cut, sp)
    assert s['D1']['pieces'][0]['detected'] and s['D1']['tf1'] < 0.5, s['D1']
    # SegQueue's chain rule (F-A17): a PDA that touches only a PLB which leaves the LCx goes to the LCx
    ch = np.zeros((20, 40, 40), np.uint8)
    ch[2:12, 5, 5] = 3; ch[11, 6:20, 5] = 12; ch[11, 20, 5:20] = 11; ch[2:12, 30, 30] = 4
    st = {}
    c4 = collapse4(ch, sp, stats=st)
    assert (c4[ch == 11] == 3).all() and (c4[ch == 12] == 3).all() and st['fallback'] == 0, st
    # an unattached PDA: RCA fallback, counted
    st0, st = {}, {}
    collapse4(ref, sp, stats=st0)
    un = ref.copy(); un[2, 80:88, 80] = 11
    c4 = collapse4(un, sp, stats=st)
    assert (c4[2, 80:88, 80] == 4).all() and st['fallbackUnattached'] == st0['fallbackUnattached'] + 1, st
    print('selftest ok; scorer sha256', scorer_sha256())


if __name__ == '__main__':
    if sys.argv[1:] == ['selftest']:
        selftest()
