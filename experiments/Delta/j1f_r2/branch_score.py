"""Janus 1-F branch scorer (round 2, Delta; item 2 of the Round 1 ruling's section 5). The definitions of record for
B1/B2 (F-A6) and the reports (F-A9), as code to be copied byte-identical into `trillium/janus1f/lib/` and pinned by
sha256. CPU, labels only. Not decisive for the vessels: V is A1c's `tf1.py` on the four-class collapse.

Label values (1-F stage 1, F-A3): 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA, 5 D1, 6 D2, 7 D3, 8 OM1, 9 OM2, 10 Ramus, 11 PDA,
12 PLB; 255 ignore (reference only).

Definitions (all per locked case, per branch class c; a "branch" is class c in one case, all its pieces together,
because ImageCAS-X names one D1, one D2, ... per case):
* centreline     skimage `skeletonize` of the class mask (3-D). Length = skeleton voxels x the geometric mean
                 voxel side (a deterministic estimate; ~1.0-1.2 x a graph path length).
* present        centreline length >= PRESENCE_MM (5 mm). Same rule for reference and prediction.
* detected       a present reference branch with >= DETECT_COVER (50 %) of its centreline voxels within TOL_MM
                 (1.5 mm, D3's tolerance) of predicted foreground of ANY class.
* named          a detected branch whose covered centreline voxels take, by majority (> 50 %), the label c from
                 their nearest predicted foreground voxel (Euclidean, anisotropic spacing).
* recall_c       detected / present reference branches.         -> B1 (>= RECALL_LINE)
* agreement_c    share of the 100 cases where reference and prediction are both present or both absent
                 (ImageCAS-X Table 1's own measure).            -> B1 (>= Table 1 - MARGIN)
* naming_c       named / detected.                               -> B2 (>= NAMING_LINE)
* branch tF1_c   report only: `segtrain.tf1.tree_f1` on class c alone (binary), one ostium per reference piece at
                 its centreline voxel nearest the parent (LAD for D1-D3, LCx for OM1, OM2, Ramus, the collapsed
                 vessel the piece leaves for PDA/PLB), tol 1.5 mm.
* four-class collapse  `segqueue14.labels.collapse_to_four` (SegQueue 0.20.0, D47 Q1): D1-D3 -> LAD; OM1, OM2,
                 Ramus -> LCx; each PDA/PLB component -> the vessel it has most face contact with, RCA on a tie or
                 no contact. One implementation for pool reads and for 1-F. The vessel scorer reads its output.
Gate lines (Delta v2 section 1): RECALL_LINE 0.75, NAMING_LINE 0.80, MARGIN 0.05 below Table 1; a class passes B if
B1 and B2 hold; >= 4 of the 6 gated classes must pass (F-A6's read rule, unchanged).
"""
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

import os, sys
_ROOT = os.path.dirname(os.path.abspath(__file__)) + '/../../..'
sys.path.insert(0, f'{_ROOT}/src')
from segqueue14.labels import collapse_to_four, NAMES as SQ_NAMES   # noqa: E402
from segtrain import tf1 as _tf1                                     # noqa: E402

NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA', 5: 'D1', 6: 'D2', 7: 'D3', 8: 'OM1', 9: 'OM2', 10: 'Ramus',
         11: 'PDA', 12: 'PLB'}
VAL = {v: k for k, v in NAMES.items()}
IGNORE = 255
GATED = ('D1', 'D2', 'OM1', 'OM2', 'PDA', 'PLB')
REPORTED = ('Ramus', 'D3')
PARENT = {'D1': 'LAD', 'D2': 'LAD', 'D3': 'LAD', 'OM1': 'LCx', 'OM2': 'LCx', 'Ramus': 'LCx'}
PRESENCE_MM, DETECT_COVER, TOL_MM = 5.0, 0.5, 1.5
RECALL_LINE, NAMING_LINE, MARGIN = 0.75, 0.80, 0.05
TABLE1_AGREEMENT = {'D1': 0.969, 'D2': 0.894, 'OM1': 0.944, 'OM2': 0.875, 'PDA': 0.988, 'PLB': 0.962}
MIN_PASSING = 4


def collapse4(lab13):
    """13-class map -> 4-class map (0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA) by SegQueue 0.20.0's collapse."""
    names = [NAMES[v] for v in sorted(NAMES)]
    masks = np.stack([lab13 == v for v in sorted(NAMES)])
    st = {}
    four = collapse_to_four(masks, names, stats=st)          # SegQueue knows D3 and Ramus as extended names
    out = np.zeros(lab13.shape, np.uint8)
    for k, n in enumerate(SQ_NAMES):
        out[four[k].astype(bool)] = {'LM': 1, 'LAD': 2, 'LCx': 3, 'RCA': 4}[n]
    st.pop('masks', None)
    return out, st


def _cl(mask):
    return skeletonize(mask) if mask.any() else np.zeros(mask.shape, bool)


def length_mm(skel, spacing):
    return float(skel.sum() * np.prod(spacing) ** (1 / 3))


def score_case(ref, pred, spacing, with_tf1=True):
    """ref, pred: 13-class maps on one grid (ref may hold 255). Returns {class: {...}}."""
    sp = np.asarray(spacing, float)
    pfg = (pred > 0) & (pred != IGNORE)
    if pfg.any():
        d, idx = ndi.distance_transform_edt(~pfg, sampling=sp, return_indices=True)
    out = {}
    ref4 = collapse4(np.where(ref == IGNORE, 0, ref).astype(np.uint8))[0] if with_tf1 else None
    for c in GATED + REPORTED:
        v = VAL[c]
        rmask, pmask = ref == v, pred == v
        rsk, psk = _cl(rmask), _cl(pmask)
        r = {'ref_present': length_mm(rsk, sp) >= PRESENCE_MM, 'pred_present': length_mm(psk, sp) >= PRESENCE_MM,
             'detected': False, 'named': False, 'cover': 0.0, 'name_share': 0.0, 'tf1': None}
        if r['ref_present'] and pfg.any():
            pts = np.argwhere(rsk)
            dd = d[tuple(pts.T)]
            cov = dd <= TOL_MM
            r['cover'] = float(cov.mean())
            r['detected'] = r['cover'] >= DETECT_COVER
            if cov.any():
                near = idx[(slice(None),) + tuple(pts[cov].T)]
                lab_near = pred[tuple(near)]
                r['name_share'] = float((lab_near == v).mean())
                r['named'] = r['detected'] and r['name_share'] > 0.5
        if with_tf1 and r['ref_present']:
            r['tf1'] = branch_tf1(rmask, pmask, ref, ref4, c, sp)
        out[c] = r
    return out


def branch_tf1(rmask, pmask, ref, ref4, c, sp):
    """Report-only branch tF1: class c alone, one ostium per reference piece at its centreline voxel nearest the
    parent vessel (for PDA/PLB: the collapsed vessel, LCx or RCA, that the piece touches most)."""
    if c in PARENT:
        par = (ref == VAL[PARENT[c]])
    else:
        lcx, rca = ref4 == 3, ref4 == 4
        par = None
    lab, n = ndi.label(rmask, np.ones((3, 3, 3), bool))
    ostia = []
    for k in range(1, n + 1):
        piece = lab == k
        sk = _cl(piece)
        pts = np.argwhere(sk) if sk.any() else np.argwhere(piece)
        p = par
        if p is None:
            g = ndi.binary_dilation(piece)
            p = lcx if (g & lcx).sum() > (g & rca).sum() else rca
        if p.any():
            dp = ndi.distance_transform_edt(~p, sampling=sp)
            j = int(np.argmin(dp[tuple(pts.T)]))
        else:
            j = 0
        ostia.append(_tf1.Ostium(tree=k, point=tuple(int(x) for x in pts[j]), rule='branch-origin'))
    rep = _tf1.OstiumReport(ostia, provisional=False, rules=('branch-origin',))
    try:
        t = _tf1.tree_f1(rmask.astype(np.uint8), pmask.astype(np.uint8), sp, tol_mm=TOL_MM, ostia=rep)
        return None if t.tf1 != t.tf1 else float(t.tf1)
    except Exception as e:   # report-only: never let it break the gated numbers
        return f'error: {e!r}'[:120]


def aggregate(rows):
    """rows: [score_case(...)] over the locked cases -> per-class metrics and the B verdict."""
    out = {}
    for c in GATED + REPORTED:
        rs = [r[c] for r in rows]
        npres = sum(r['ref_present'] for r in rs)
        ndet = sum(r['detected'] for r in rs)
        m = {'n_cases': len(rs), 'n_ref': npres,
             'recall': ndet / npres if npres else float('nan'),
             'agreement': sum(r['ref_present'] == r['pred_present'] for r in rs) / len(rs),
             'naming': sum(r['named'] for r in rs) / ndet if ndet else float('nan'),
             'pred_present_when_ref_absent': sum((not r['ref_present']) and r['pred_present'] for r in rs)}
        tf = [r['tf1'] for r in rs if isinstance(r['tf1'], float)]
        m['branch_tf1_mean'] = float(np.mean(tf)) if tf else float('nan')
        if c in GATED:
            m['line_agreement'] = round(TABLE1_AGREEMENT[c] - MARGIN, 3)
            m['B1'] = bool(m['recall'] >= RECALL_LINE and m['agreement'] >= m['line_agreement'])
            m['B2'] = bool(m['naming'] >= NAMING_LINE)
            m['pass'] = m['B1'] and m['B2']
        out[c] = m
    npass = sum(out[c]['pass'] for c in GATED)
    return {'classes': out, 'n_pass': npass, 'B': npass >= MIN_PASSING,
            'lines': {'recall': RECALL_LINE, 'naming': NAMING_LINE, 'margin': MARGIN, 'presence_mm': PRESENCE_MM,
                      'detect_cover': DETECT_COVER, 'tol_mm': TOL_MM, 'min_passing': MIN_PASSING}}
