"""Janus 1-F round 2 (Atlas): the branch scorer, proposed for freezing by hash (Round 1 ruling §5, item 2).

One module, three jobs:
  1. `stage1_labels`  ImageCAS-X 14 classes -> 1-F stage-1 labels (F-A3, with D47 Q1 = (A): L-PDA/L-PLA -> PDA/PLB).
  2. `collapse4`      1-F labels -> LM/LAD/LCx/RCA by ORIGIN (F-A4 under D47 Q1): D1-D3 -> LAD; OM1, OM2, Ramus -> LCx;
                      each PDA/PLB 26-component -> the trunk territory (LCx or RCA) it touches most.
  3. `score_case`     per-class branch measures of a 1-F prediction against a 1-F reference (F-A6 B1/B2, F-A9):
                      reference pieces, detection, naming, presence, and branch tF1 rooted at each piece's origin.

Stage-1 values: 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA, 5 D1, 6 D2, 7 D3, 8 OM1, 9 OM2, 10 Ramus, 11 PDA, 12 PLB, 255 ignore.

Frozen definitions (every constant is a module-level name, so the hash freezes it):
  * PIECE: a 26-connected component of one branch class with >= MIN_PIECE_VOX voxels. R-PDA in two pieces is two
    pieces, each with its own root (ruling §5 item 2).
  * CENTRELINE of a piece: the skeleton of the WHOLE reference tree (ref in 1..12) restricted to the piece; if empty,
    the piece's maximal-EDT voxels (A1c's fallback, as tf1._fallback_points).
  * LENGTH: sum over skeleton 26-edges inside the piece of the edge length in mm, halved per endpoint pair (graph
    length); a one-point centreline has length 0.
  * ROOT (origin) of a piece: its centreline point nearest (mm) to any reference voxel of the piece's PARENT class set
    (LAD for D1-D3; LCx for OM1, OM2, Ramus; LCx or RCA, whichever is nearer, for PDA/PLB); falls back to the nearest
    tree voxel outside the piece.
  * PRESENCE of class c in a map: the total centreline length of c's pieces in that map >= PRESENCE_MM (5 mm, as Delta
    v1; Foxtrot used 3 mm). The prediction's centreline is the skeleton of the prediction's own tree.
  * DETECTION of a reference piece: >= DETECT_FRACTION (0.5) of its centreline points lie within TOL_MM (1.5 mm, D3) of
    a predicted vessel voxel of ANY class (prediction cleaned of 26-components < MIN_PRED_VOX).
  * NAMING of a detected piece: each covered centreline point takes the label of its nearest predicted voxel; the piece
    is NAMED RIGHT if strictly more than half of its covered points carry the piece's class.
  * BRANCH tF1 of class c: segtrain.tf1.tree_f1 on the binary maps (ref == c, pred == c), with one ostium per reference
    piece at its ROOT, min_component_voxels = MIN_PRED_VOX, tol 1.5 mm. tf1.py's sha256 is checked at import.

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
    touching only the RCA or nothing -> 255 (Foxtrot); small or tied pieces touching the left tree -> nearest LAD/LCx
    (as territory.py)."""
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


# ------------------------------------------------------------------------------------------- collapse (F-A4)
_TO4 = np.zeros(256, np.uint8)
_TO4[[1]] = 1; _TO4[[2, 5, 6, 7]] = 2; _TO4[[3, 8, 9, 10]] = 3; _TO4[[4]] = 4


def collapse4(lab, zooms):
    """By origin (D25, D47 Q1). PDA/PLB: per 26-component of (PDA | PLB), the territory (LCx or RCA) with more voxels in
    its one-voxel ring; a tie or no contact -> the nearer of the two in mm. 255 -> 0."""
    lab = np.asarray(lab)
    out = _TO4[lab]
    pp = np.isin(lab, (11, 12))
    if pp.any():
        sp = np.asarray(zooms[:3], float)
        comp, nc = ndi.label(pp, S26)
        objs = ndi.find_objects(comp)
        for i in range(1, nc + 1):
            sl = tuple(slice(max(s.start - 2, 0), s.stop + 2) for s in objs[i - 1])
            p = comp[sl] == i
            ring = ndi.binary_dilation(p, S26) & ~p
            v = lab[sl][ring]
            nl, nr = int(np.isin(v, LCX_TERR).sum()), int(np.isin(v, RCA_TERR).sum())
            if nl == nr:
                q = np.argwhere(comp == i)
                dl = dr = np.inf
                for terr, name in ((LCX_TERR, 'l'), (RCA_TERR, 'r')):
                    t = np.argwhere(np.isin(lab, terr))
                    if len(t):
                        dd = cKDTree(t * sp).query(q * sp)[0].min()
                        if name == 'l':
                            dl = dd
                        else:
                            dr = dd
                tgt = 3 if dl < dr else 4
            else:
                tgt = 3 if nl > nr else 4
            out[sl][p] = tgt
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
    # stage1_labels on a toy ImageCAS-X map: L-PDA -> PDA, first LAD-side Other -> D3, RCA-only Other -> 255
    icx = np.zeros((40, 90, 90), np.uint8)
    icx[20, 10:14, 10] = 1; icx[20, 14:70, 10] = 2; icx[20, 25, 11:32] = 4; icx[20, 45, 11:32] = 5
    icx[20, 60, 11:32] = 14; icx[20, 66, 11:32] = 14            # two LAD-side Others: D3 then LAD
    icx[21:38, 13, 10] = 3; icx[37, 14:36, 10] = 12
    icx[5:15, 60, 60] = 9; icx[15, 60, 61:85] = 14              # Other touching only the RCA
    lab, info = stage1_labels(icx, sp)
    assert (lab[icx == 12] == 11).all() and (lab[20, 60, 11:32] == 7).all() and (lab[20, 66, 11:32] == 2).all()
    assert (lab[15, 60, 61:85] == IGNORE).all() and info['other_ignore'] == 1, info
    print('selftest ok; scorer sha256', scorer_sha256())


if __name__ == '__main__':
    if sys.argv[1:] == ['selftest']:
        selftest()
