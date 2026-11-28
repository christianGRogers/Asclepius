"""Janus 1-F round 3 (Atlas): the branch scorer of record (F-A16), with SegQueue's collapse imported (F-A17).

This is round 2's `experiments/Atlas/j1f_r2/j1f_scorer.py` (sha256 2da3cb1a...886c) with three changes and nothing
else moved:
  1. `collapse4` no longer has its own one-voxel-ring rule. It calls `segqueue14.labels.collapse_to_four`, the code
     that collapses pool reads (F-A17): D1-D3 -> LAD; OM1, OM2, Ramus -> LCx; each PDA/PLB component -> the vessel it
     has the most face contact with, with the chain rule; RCA on a tie or no contact, counted. `labels.py` is pinned
     by sha256 at import, as `tf1.py` is.
  2. `aggregate` and `gate`: the pooled per-piece statistics of F-A15/F-A16 and the "4 of 6" verdict, in exact
     rational arithmetic, against the lines in `j1f_gates.json` (whose sha256 the launcher checks separately).
  3. The self-test adds the F-A17 cases (a left PDA reached only through its PLB goes to the LCx; an unattached PDA
     falls back to the RCA and is counted).

Module 1, `stage1_labels`: ImageCAS-X 14 classes -> 1-F stage-1 labels (F-A3, D47 Q1 = (A): L-PDA/L-PLA -> PDA/PLB).
Stage-1 values: 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA, 5 D1, 6 D2, 7 D3, 8 OM1, 9 OM2, 10 Ramus, 11 PDA, 12 PLB, 255 ignore.

Frozen definitions (every constant is a module-level name, so the hash freezes it):
  * PIECE: a 26-connected component of one branch class with >= MIN_PIECE_VOX voxels. R-PDA in two pieces is two
    pieces, each with its own root.
  * CENTRELINE of a piece: the skeleton of the WHOLE reference tree (ref in 1..12) restricted to the piece; if empty,
    the piece's maximal-EDT voxels (A1c's fallback, as tf1._fallback_points).
  * LENGTH: the minimum spanning forest of the centreline points' 26-graph, edge lengths in mm.
  * ROOT (origin) of a piece: its centreline point nearest (mm) to any reference voxel of the piece's PARENT class set
    (LAD for D1-D3; LCx for OM1, OM2, Ramus; LCx or RCA, whichever is nearer, for PDA/PLB).
  * PRESENCE of class c in a map: the total centreline length of c's pieces >= PRESENCE_MM (5 mm).
  * DETECTION of a reference piece: >= DETECT_FRACTION (0.5) of its centreline points lie within TOL_MM (1.5 mm, D3) of
    a predicted vessel voxel of ANY class (prediction cleaned of 26-components < MIN_PRED_VOX).
  * NAMING of a detected piece: each covered centreline point takes the label of its nearest predicted voxel; the piece
    is NAMED RIGHT if strictly more than half of its covered points carry the piece's class (a tie is wrong).
  * BRANCH tF1 of class c (report): segtrain.tf1.tree_f1 on (ref == c, pred == c), one ostium per reference piece at
    its ROOT, min_component_voxels = MIN_PRED_VOX, tol 1.5 mm.
  * POOLED STATISTICS over the locked cases (F-A15): recall_c = detected pieces / reference pieces; naming_c = named
    pieces / detected pieces; presence agreement_c = cases where reference and prediction are both present or both
    absent / all cases. A class passes when all three are >= its lines; the verdict needs >= K_OF_6 classes passing.

Nothing here reads a volume: callers pass arrays. Self-test: python j1f_scorer.py selftest
"""
import hashlib
import json
import os
import sys
from fractions import Fraction

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, '../../../src')
sys.path.insert(0, _SRC)
TF1_SHA256 = '24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254'
LABELS_SHA256 = '5f69b5bef59ad1346c5877a43c65daf7bdf1329b0ca7e427b6addd55d0000a4b'
assert hashlib.sha256(open(os.path.join(_SRC, 'segtrain/tf1.py'), 'rb').read()).hexdigest() == TF1_SHA256, \
    'tf1.py is not the A1c scorer'
assert hashlib.sha256(open(os.path.join(_SRC, 'segqueue14/labels.py'), 'rb').read()).hexdigest() == LABELS_SHA256, \
    'segqueue14/labels.py is not the pinned SegQueue collapse (F-A17)'
from segtrain import tf1 as _tf1  # noqa: E402
from segqueue14 import labels as _sq  # noqa: E402

NAMES = ['bg', 'LM', 'LAD', 'LCx', 'RCA', 'D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB']
BRANCHES = (5, 6, 7, 8, 9, 10, 11, 12)
GATED = (5, 6, 8, 9, 11, 12)                      # D1, D2, OM1, OM2, PDA, PLB (F-A6)
K_OF_6 = 4
IGNORE = 255
PARENT = {5: (2,), 6: (2,), 7: (2,), 8: (3,), 9: (3,), 10: (3,), 11: (3, 4), 12: (3, 4)}
MIN_PIECE_VOX = 20
MIN_PRED_VOX = 20
PRESENCE_MM = 5.0
DETECT_FRACTION = 0.5
TOL_MM = 1.5
S26 = np.ones((3, 3, 3), bool)
# ImageCAS-X: 1 LM 2 LAD 3 LCx 4 D1 5 D2 6 OM1 7 OM2 8 IM 9 RCA 10 R-PDA 11 R-PLA 12 L-PDA 13 L-PLA 14 Other
_ICX_DIRECT = {1: 1, 2: 2, 3: 3, 4: 5, 5: 6, 6: 8, 7: 9, 8: 10, 9: 4, 10: 11, 11: 12, 12: 11, 13: 12}
_ICX_LAD_SIDE, _ICX_LCX_SIDE = (2, 4, 5), (3, 6, 7, 8, 12, 13)
_ICX_LEFT = (1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14)


# ------------------------------------------------------------------------------------------- labels (F-A3)
def _geodesic(mask, seeds, sp):
    from skimage.graph import MCP_Geometric
    d, _ = MCP_Geometric(np.where(mask, 1.0, np.inf), sampling=tuple(sp)).find_costs([tuple(s) for s in seeds])
    return d


def stage1_labels(icx, zooms):
    """F-A3 with D47 Q1 (A). Returns (labels uint8, info). 'Other' pieces: >= 20 voxels touching the LAD side more ->
    the first along the left tree (geodesic from the LM) is D3, later ones LAD; touching the LCx side more -> LCx;
    touching only the RCA or nothing -> 255; small or tied pieces touching the left tree -> nearest LAD/LCx."""
    icx = np.asarray(icx)
    sp = np.asarray(zooms[:3], float)
    out = np.zeros(icx.shape, np.uint8)
    for k, v in _ICX_DIRECT.items():
        out[icx == k] = v
    info = {'d3': 0, 'd4_to_lad': 0, 'other_lcx': 0, 'other_nearest': 0, 'other_ignore': 0}
    o = icx == 14
    if not o.any():
        return out, info
    comp, nc = ndi.label(o, S26)
    lad_pieces, near = [], np.zeros_like(o)
    for i in range(1, nc + 1):
        p = comp == i
        ring = ndi.binary_dilation(p, S26, iterations=2) & ~p
        v = icx[ring]
        nl, ncx = int(np.isin(v, _ICX_LAD_SIDE).sum()), int(np.isin(v, _ICX_LCX_SIDE).sum())
        big = p.sum() >= MIN_PIECE_VOX
        if big and nl > ncx:
            lad_pieces.append(p)
        elif big and ncx > nl:
            out[p] = 3; info['other_lcx'] += 1
        elif nl + ncx > 0:
            near |= p; info['other_nearest'] += 1
        else:
            out[p] = IGNORE; info['other_ignore'] += 1
    if lad_pieces:
        left = np.isin(icx, _ICX_LEFT)
        src = np.argwhere(icx == 1) if (icx == 1).any() else np.argwhere(icx == 2)[:1]
        d = _geodesic(left, src, sp)
        att = [float(np.min(d[p])) for p in lad_pieces]
        for r, j in enumerate(np.argsort(att)):
            out[lad_pieces[j]] = 7 if r == 0 else 2
        info['d3'] = 1
        info['d4_to_lad'] = len(lad_pieces) - 1
    if near.any():
        srcm = np.isin(out, (2, 3))
        if srcm.any():
            pts, op = np.argwhere(srcm), np.argwhere(near)
            _, ii = cKDTree(pts * sp).query(op * sp)
            out[tuple(op.T)] = out[tuple(pts[ii].T)]
    return out, info


# ------------------------------------------------------------------------------------------- collapse (F-A17)
_SQ_ORDER = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)           # stage-1 values, named as SegQueue names them
_SQ_NAME = {v: NAMES[v] for v in _SQ_ORDER}
assert list(_sq.NAMES) == ['LM', 'LAD', 'LCx', 'RCA'], _sq.NAMES
assert all(_sq.PARENT.get(NAMES[v]) for v in (5, 6, 7, 8, 9, 10)), 'SegQueue lost a D/OM/Ramus parent'
assert set(_sq.CONTACT_BRANCHES) >= {'PDA', 'PLB'}


def collapse4(lab, zooms=None, stats=None):
    """1-F map -> 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA by `segqueue14.labels.collapse_to_four` (F-A17). 255 -> 0. Runs on
    the map's foreground bounding box (2 voxels wider), which changes nothing: SegQueue's contact is face contact.
    `stats`, when a dict, receives SegQueue's counts (components, byParent, fallback, ...) without the masks."""
    lab = np.asarray(lab)
    out = np.zeros(lab.shape, np.uint8)
    fg = (lab > 0) & (lab != IGNORE)
    if stats is not None:
        stats.clear()
    if not fg.any():
        return out
    box = _sq._bbox(fg, pad=2)
    sub = lab[box]
    present = [v for v in _SQ_ORDER if (sub == v).any()]
    masks = np.stack([(sub == v) for v in present]) if present else np.zeros((0,) + sub.shape, bool)
    st = {}
    four = _sq.collapse_to_four(masks, [_SQ_NAME[v] for v in present], stats=st)
    if (four.sum(0) > 1).any():
        raise AssertionError('collapse_to_four put one voxel in two vessels')
    out[box] = (four * np.arange(1, 5, dtype=np.uint8)[:, None, None, None]).sum(0).astype(np.uint8)
    if stats is not None:
        stats.update({k: v for k, v in st.items() if k != 'masks'})
    return out


# ------------------------------------------------------------------------------------------- geometry
def _skeleton(mask):
    return _tf1._skeletonise(mask)


def _graph_length(pts, sp):
    """Length (mm) of the 26-graph on the point set: its minimum spanning forest."""
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


# ------------------------------------------------------------------------------------------- pooling and gate
def aggregate(cases):
    """`cases`: list of score_case outputs (one per locked case). Returns, per gated class, exact counts and the three
    pooled statistics as Fractions (None when the denominator is 0)."""
    out = {}
    for c in GATED:
        k = NAMES[c]
        npc = ndet = nnamed = agree = 0
        for s in cases:
            r = s[k]
            npc += len(r['pieces'])
            ndet += sum(p['detected'] for p in r['pieces'])
            nnamed += sum(p['named'] for p in r['pieces'])
            agree += int(r['present_ref'] == r['present_pred'])
        out[k] = {'cases': len(cases), 'pieces': npc, 'detected': ndet, 'named': nnamed, 'agree': agree,
                  'recall': Fraction(ndet, npc) if npc else None,
                  'naming': Fraction(nnamed, ndet) if ndet else None,
                  'presence': Fraction(agree, len(cases)) if cases else None}
    return out


def load_gates(path):
    g = json.load(open(path))
    assert sorted(g['lines']) == sorted(NAMES[c] for c in GATED), g['lines'].keys()
    assert g['k_of_6'] == K_OF_6
    for k, v in g['lines'].items():
        assert sorted(v) == ['naming', 'presence', 'recall'], (k, v)
    return g


def gate(agg, gates):
    """F-A15: a class passes when recall, presence agreement and naming are each >= its line (a missing statistic
    fails). The verdict passes when >= k_of_6 classes pass. Lines are compared exactly (Fraction of their decimal
    text), so 0.60 passes 0.60."""
    res = {}
    for k, ln in gates['lines'].items():
        a = agg[k]
        ok = {m: (a[m] is not None and a[m] >= Fraction(str(ln[m]))) for m in ('recall', 'presence', 'naming')}
        res[k] = {'pass': all(ok.values()), **{m + '_ok': v for m, v in ok.items()},
                  **{m: (None if a[m] is None else float(a[m])) for m in ('recall', 'presence', 'naming')}}
    n = sum(r['pass'] for r in res.values())
    return {'classes': res, 'n_pass': n, 'verdict_pass': n >= gates['k_of_6']}


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
    a[15, 60, 60:85] = 12                      # PLB off the RCA (face contact at its origin)
    return a


def selftest():
    sp = (0.5, 0.5, 0.5)
    ref = _toy()
    s = score_case(ref, ref.copy(), sp)
    for k in ('D1', 'D2', 'OM1', 'PDA', 'PLB'):
        assert s[k]['present_ref'] and s[k]['present_pred'], k
        assert all(p['detected'] and p['named'] for p in s[k]['pieces']), k
        assert abs(s[k]['tf1'] - 1.0) < 1e-9, (k, s[k]['tf1'])
    st = {}
    c4 = collapse4(ref, sp, st)
    assert (c4[ref == 11] == 3).all(), 'left PDA must collapse to the LCx (D47 Q1)'
    assert (c4[ref == 12] == 4).all(), 'PLB off the RCA must collapse to the RCA'
    assert (c4[np.isin(ref, (5, 6))] == 2).all() and (c4[ref == 8] == 3).all() and (c4[ref == 1] == 1).all()
    assert st['fallback'] == 0 and st['components'] == 2, st
    # F-A17's chain rule: a left PLB reached only through its PDA goes to the LCx, not the RCA
    ch = ref.copy(); ch[37, 36:50, 10] = 12
    st = {}
    c4 = collapse4(ch, sp, st)
    assert (c4[37, 36:50, 10] == 3).all() and st['fallback'] == 0, st
    # an unattached PDA falls back to the RCA and is counted
    un = ref.copy(); un[2, 80, 70:85] = 11
    st = {}
    c4 = collapse4(un, sp, st)
    assert (c4[2, 80, 70:85] == 4).all() and st['fallback'] == 1 and st['fallbackUnattached'] == 1, st
    # a PLB joined to the RCA only diagonally has no face contact: SegQueue falls back to the RCA and counts it
    dg = ref.copy(); dg[15, 60, 60] = 0
    st = {}
    c4 = collapse4(dg, sp, st)
    assert (c4[15, 60, 61:85] == 4).all() and st['fallbackUnattached'] == 1, st
    # 255 -> 0
    ig = ref.copy(); ig[1, 1, 1:30] = IGNORE
    assert (collapse4(ig, sp)[1, 1, 1:30] == 0).all()
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
    # stage1_labels on a toy ImageCAS-X map: L-PDA -> PDA, first LAD-side Other -> D3, RCA-only Other -> 255
    icx = np.zeros((40, 90, 90), np.uint8)
    icx[20, 10:14, 10] = 1; icx[20, 14:70, 10] = 2; icx[20, 25, 11:32] = 4; icx[20, 45, 11:32] = 5
    icx[20, 60, 11:32] = 14; icx[20, 66, 11:32] = 14            # two LAD-side Others: D3 then LAD
    icx[21:38, 13, 10] = 3; icx[37, 14:36, 10] = 12
    icx[5:15, 60, 60] = 9; icx[15, 60, 61:85] = 14              # Other touching only the RCA
    lab, info = stage1_labels(icx, sp)
    assert (lab[icx == 12] == 11).all() and (lab[20, 60, 11:32] == 7).all() and (lab[20, 66, 11:32] == 2).all()
    assert (lab[15, 60, 61:85] == IGNORE).all() and info['other_ignore'] == 1, info
    # the gate: exact comparison at the line, and the 4-of-6 count
    g = {'k_of_6': 4, 'lines': {NAMES[c]: {'recall': 0.6, 'presence': 0.8, 'naming': 0.8} for c in GATED}}
    agg = {NAMES[c]: {'recall': Fraction(3, 5), 'presence': Fraction(4, 5), 'naming': Fraction(4, 5)} for c in GATED}
    assert gate(agg, g)['verdict_pass'] and gate(agg, g)['n_pass'] == 6
    for k in ('D1', 'D2', 'OM1'):
        agg[k]['recall'] = Fraction(59, 100)
    r = gate(agg, g)
    assert r['n_pass'] == 3 and not r['verdict_pass'], r
    agg['D1']['recall'] = None
    assert not gate(agg, g)['classes']['D1']['pass']
    print('selftest ok; scorer sha256', scorer_sha256())


if __name__ == '__main__':
    if sys.argv[1:] == ['selftest']:
        selftest()
