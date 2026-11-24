"""Janus 1-F: the branch scorer of record (F-A16, F-A17), round 3 (Bridge). Atlas's round-2 `j1f_scorer.py`
(sha256 2da3cb1a...886c) with exactly the changes the Round 2 ruling asks for, and nothing else in the definitions:

  * `collapse4` is SegQueue's `collapse_to_four` (`src/segqueue14/labels.py`, pinned by sha256 at import), not
    Atlas's one-voxel ring (F-A17). It returns the fallback counts, which `collect` reports for F and T.
  * `stage1_labels` is removed: the converter of record is `j1f_labels.py` (F-A18). One implementation each.
  * `aggregate` and `verdict` are added: per-piece recall and naming, presence agreement over the cases, and the
    F-A15 lines read from `j1f_gates.json` (pinned by sha256), ">= 4 of 6" (F-A6).

Jobs:
  1. `collapse4`      1-F labels -> LM/LAD/LCx/RCA (D25, D47 Q1) by SegQueue's own function.
  2. `score_case`     per-class branch measures of a 1-F prediction against a 1-F reference (F-A6 B1/B2, F-A9):
                      reference pieces, detection, naming, presence, and branch tF1 rooted at each piece's origin.
  3. `aggregate`, `verdict`  the B reading over the locked cases.

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

Nothing here reads a label file: callers pass arrays. `load_gates` reads the gate file and checks its sha256.
Self-test: python j1f_scorer.py selftest
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
_LABELS = os.path.join(_HERE, '../../../src/segqueue14/labels.py')
LABELS_SHA256 = '5f69b5bef59ad1346c5877a43c65daf7bdf1329b0ca7e427b6addd55d0000a4b'
assert hashlib.sha256(open(_LABELS, 'rb').read()).hexdigest() == LABELS_SHA256, 'labels.py is not SegQueue 0.20.0'
from segqueue14.labels import collapse_to_four as _sq_collapse, NAMES as _SQ4  # noqa: E402

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
def collapse4(lab, zooms=None, stats=None):
    """D25 under D47 Q1, by SegQueue's own `collapse_to_four`: D1-D3 -> LAD; OM1, OM2, Ramus -> LCx; each PDA/PLB
    26-component -> the vessel with the most face contact, the chain rule, RCA on a tie or no contact (counted in
    `stats`). 255 -> 0. Works inside the foreground's box, one voxel wider: contact never reaches further. `zooms`
    is unused (kept for the old signature). Returns uint8 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA."""
    lab = np.asarray(lab)
    out = np.zeros(lab.shape, np.uint8)
    fg = (lab > 0) & (lab != IGNORE)
    st = {}
    if fg.any():
        nz = np.argwhere(fg)
        box = tuple(slice(max(int(l) - 1, 0), int(h) + 2) for l, h in zip(nz.min(0), nz.max(0)))
        sub = lab[box]
        vals = [v for v in range(1, len(NAMES)) if (sub == v).any()]
        four = _sq_collapse(np.stack([sub == v for v in vals]), [NAMES[v] for v in vals], stats=st)
        o = out[box]
        for k, n in enumerate(_SQ4):
            o[four[k].astype(bool)] = k + 1
        st.pop('masks', None)
    if stats is not None:
        stats.clear(); stats.update({'components': st.get('components', 0), 'fallback': st.get('fallback', 0),
                                     'fallbackTie': st.get('fallbackTie', 0),
                                     'fallbackUnattached': st.get('fallbackUnattached', 0),
                                     'byParent': st.get('byParent', {'RCA': 0, 'LCx': 0})})
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


# ------------------------------------------------------------------------------------------- the B reading (F-A15)
GATE_KEYS = ('recall', 'presence', 'naming')
EPS = 1e-12                                       # a line is met at equality: 24/40 meets 0.60


def load_gates(path, sha256=None):
    """The F-A15 lines. Refuses a file whose sha256 differs from the posted one, a missing class or a line outside
    [0, 1]."""
    raw = open(path, 'rb').read()
    if sha256 is not None and hashlib.sha256(raw).hexdigest() != sha256:
        raise SystemExit(f'REFUSE: {path} sha256 is not the posted {sha256}')
    g = __import__('json').loads(raw)
    gated = [NAMES[c] for c in GATED]
    if sorted(g['classes']) != sorted(gated):
        raise SystemExit(f'REFUSE: gate classes {sorted(g["classes"])} != {sorted(gated)}')
    for c, d in g['classes'].items():
        if sorted(d) != sorted(GATE_KEYS) or not all(0 <= d[k] <= 1 for k in GATE_KEYS):
            raise SystemExit(f'REFUSE: bad lines for {c}: {d}')
    if g.get('k_of_6') != 4 or g.get('presence_mm') != PRESENCE_MM or g.get('tol_mm') != TOL_MM:
        raise SystemExit('REFUSE: k_of_6, presence_mm or tol_mm differs from the scorer of record')
    return g


def aggregate(rows):
    """rows: one score_case() result per locked case. Per class: recall and naming pooled over reference PIECES
    (F-A16), presence agreement over CASES (Table 1's measure)."""
    out = {}
    for c in BRANCHES:
        k = NAMES[c]
        pcs = [p for r in rows for p in r[k]['pieces']]
        n, det = len(pcs), sum(p['detected'] for p in pcs)
        named = sum(p['named'] for p in pcs)
        agree = sum(r[k]['present_ref'] == r[k]['present_pred'] for r in rows)
        tf = [r[k]['tf1'] for r in rows if 'tf1' in r[k] and r[k]['pieces']]
        out[k] = {'cases': len(rows), 'cases_present_ref': sum(r[k]['present_ref'] for r in rows),
                  'pieces': n, 'detected': det, 'named': named,
                  'recall': det / n if n else float('nan'), 'naming': named / det if det else float('nan'),
                  'presence': agree / len(rows) if rows else float('nan'),
                  'branch_tf1_mean': float(np.mean(tf)) if tf else float('nan')}
    return out


def verdict(agg, gates):
    """B: each gated class passes when all three of its lines are met; >= k_of_6 classes must pass."""
    per = {}
    for c in GATED:
        k = NAMES[c]
        ln, a = gates['classes'][k], agg[k]
        ok = {m: bool(a[m] == a[m] and a[m] >= ln[m] - EPS) for m in GATE_KEYS}     # nan fails
        per[k] = {'pass': all(ok.values()), **{f'{m}_ok': v for m, v in ok.items()}}
    npass = sum(v['pass'] for v in per.values())
    return {'classes': per, 'n_pass': npass, 'B': npass >= gates['k_of_6'],
            'folded': [k for k, v in per.items() if not v['pass']]}


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
    # collapse by SegQueue's function: the chain rule (a PLB off a left PDA that touches only the PDA -> LCx)
    # (the toy's right PLB meets the RCA only diagonally: no face contact, so it is one counted RCA fallback)
    st = {}
    collapse4(ref, sp, st)
    base = st['fallback']
    assert base == 1 and st['byParent'] == {'RCA': 1, 'LCx': 1}, st
    ch = ref.copy(); ch[38, 35, 10:30] = 12                       # PLB hanging off the left PDA's tip
    c4 = collapse4(ch, sp, st)
    assert (c4[38, 35, 10:30] == 3).all() and st['fallback'] == base, st
    # an unattached PDA falls back to RCA and is counted
    un = ref.copy(); un[2, 80, 70:85] = 11
    c4 = collapse4(un, sp, st)
    assert (c4[2, 80, 70:85] == 4).all() and st['fallback'] == base + 1, st
    # 255 is background in the collapse
    ig = ref.copy(); ig[1, 1, 1:5] = IGNORE
    assert (collapse4(ig)[1, 1, 1:5] == 0).all()
    # the B reading: OM2 recall 24/40 = 0.60 passes, 23/40 fails, 25/40 passes (exactly at and either side)
    g = {'k_of_6': 4, 'presence_mm': PRESENCE_MM, 'tol_mm': TOL_MM,
         'classes': {NAMES[c]: {'recall': 0.6, 'presence': 0.8, 'naming': 0.8} for c in GATED}}
    def rows_with(k_det, n=40):
        rr = []
        for i in range(100):
            r = {NAMES[c]: {'pieces': [], 'present_ref': False, 'present_pred': False} for c in BRANCHES}
            for c in GATED:
                if i < n:
                    det = NAMES[c] != 'OM2' or i < k_det
                    r[NAMES[c]] = {'pieces': [{'detected': det, 'named': det}], 'present_ref': True,
                                   'present_pred': True}
            rr.append(r)
        return rr
    for k_det, want in ((23, False), (24, True), (25, True)):
        v = verdict(aggregate(rows_with(k_det)), g)
        assert v['classes']['OM2']['pass'] is want and v['n_pass'] == 5 + want, (k_det, v)
    nan = aggregate(rows_with(0))
    assert nan['OM2']['naming'] != nan['OM2']['naming'] and not verdict(nan, g)['classes']['OM2']['pass']
    print('selftest ok; scorer sha256', scorer_sha256())


if __name__ == '__main__':
    if sys.argv[1:] == ['selftest']:
        selftest()
