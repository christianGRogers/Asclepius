"""Rule-based coronary branch namer: amendments A4 (QA of proxy and read labels), A7 (renaming a
prediction, "R"), A8 (ramus switch), under the human decisions D1 (territory: a side branch takes its
parent's class) and D1b (ramus intermedius -> LCx).

Why rules and not a network: once the lumen is fixed, the four classes are decided by a handful of
discrete choices per case -- which tree is left, where the left ostium is, where the left main ends, which
child is the LAD, where a ramus goes -- and every other voxel inherits its name through connectivity. The
rules make those choices consistently for the whole tree, so every class is a connected sub-tree by
construction. Measured (vault, Bridge experiment notes): 88.2 % of 76 held-out thick-mask cases fully right
(all four classes Dice >= 0.8) against ImageCAS-X names under D1b; on real stage-1 output within 0.010 tree-F1
of perfect naming. Those numbers were produced by the experiment copy (`experiments/Bridge/label.py`, TEASAR
skeletons from kimimaro); this port uses scikit-image skeletons and is re-validated in the implementation note.

API
    name_tree(mask, affine)            -> NamingResult   binary or 4-class tree -> 4-class labels + decisions
    rename(labels4, affine)            -> NamingResult   A7 "R": re-name a 4-class prediction's foreground
    extract_decisions(labels4, affine) -> Decisions      ostium / LM end / tree identity of any labelling
    compare(reference, named, affine)  -> Disagreement   A4/A11: `ignore` mask + wholesale flags (+ ramus exemption)

Everything is in the input voxel grid; the affine supplies spacing and patient directions (RAS: +x patient
right... more precisely nibabel's RAS+, so the left tree has the more negative x, anterior is +y).
Dependencies: numpy, scipy, scikit-image (skeletonisation, imported lazily).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, minimum_spanning_tree
from scipy.spatial import cKDTree

LM, LAD, LCX, RCA = 1, 2, 3, 4
CLASS_NAMES = {LM: "left_main", LAD: "left_anterior_descending", LCX: "left_circumflex",
               RCA: "right_coronary_artery"}

# ImageCAS-X 14 segment classes -> the project's 4 (D1 territory, D1b ramus -> LCx). 14 ("Other":
# D3/D4/OM3/OM4) has no fixed parent, so it maps to 0 and is named by the tree it hangs from.
ICX_TO_4 = {1: LM, 2: LAD, 4: LAD, 5: LAD, 3: LCX, 6: LCX, 7: LCX, 8: LCX, 12: LCX, 13: LCX,
            9: RCA, 10: RCA, 11: RCA, 14: 0}

# ---- frozen parameters (experiments/Bridge/label.py, md5 06f53291..., Round 3) ---------------------
MIN_COMPONENT_VOXELS = 100   # smaller components get no skeleton; they take the nearest named class
TREE_MIN_MM = 30.0           # skeleton length for a component to count as a tree
MAJOR_MIN_MM = 20.0          # downstream skeleton for a child to count as a major branch
BIF_WINDOW_MM = 40.0         # the LM bifurcation is searched along the heavy path within this distance
RAMUS_WINDOW_MM = 6.0        # a ramus leaves the LAD/LCx within this distance of the bifurcation
RAMUS_MIN_MM = 20.0
RAMUS_CANDIDATE_WINDOW_MM = 10.0   # looser region used only for the A11 ramus exemption
FUSED_TREE_MM = 800.0        # one tree this long = left and right trees fused (flag)
SPUR_SCALE, SPUR_CONST_MM = 1.5, 2.0  # spur pruning ~ TEASAR's invalidation sphere (scale 1.5, const 2 mm)
N_RERANK = 5

# learned ostium score (logistic regression on endpoint features, fit on 79 development cases; vault note
# "Finding the left ostium is the crux of naming"). Standardised features are clipped to +-5.
_OST_F = ['r6', 'r3', 'rmax6', 'h', 'sl', 'beyond', 'dR', 'r6_rk', 'r3_rk', 'h_rk', 'dR_rk']
_OST_MEAN = np.array([1.2260055587372005, 1.0132613248828564, 1.6357369771988115, 0.5495513811425237,
                      30.1229775443098, 0.9998746521729002, 45.651009351771286, 0.5, 0.5, 0.5, 0.5])
_OST_SCALE = np.array([0.209151543865291, 0.1778348075599815, 0.36604398711788555, 0.3234323899884134,
                       36.287147238657184, 0.00042258801628693485, 15.236790745060588, 0.3173992111756212,
                       0.3173992111756212, 0.3173992111756212, 0.3173992111756212])
_OST_COEF = np.array([-0.064966171223464, -0.5001573960311001, 1.1166941835083288, 2.088543257427978,
                      -0.09785911296058337, -1.1985929834244, -1.028112411343153, 1.4916330195017398,
                      -0.45314176063777406, 0.10962521518841653, -0.7717144014035534])


# ---------------------------------------------------------------------------------- data classes

@dataclass
class Decisions:
    """The discrete naming decisions of one case (voxel coordinates in the input grid)."""
    ostium_vox: Optional[tuple] = None      # left-tree ostium
    lm_end_vox: Optional[tuple] = None      # LM bifurcation (end of the left main)
    lm_length_mm: Optional[float] = None
    left_component: Optional[int] = None    # skeleton component holding LM/LAD/LCx
    right_component: Optional[int] = None   # skeleton component holding the RCA
    n_ramus: int = 0                        # ramus-like branches renamed by the A8 switch
    fused_trees: bool = False               # left and right trees in one component (flag for a human)
    failure: Optional[str] = None           # 'empty', 'no_tree', 'single_tree', 'no_bifurcation'


@dataclass
class NamingResult:
    labels: np.ndarray                      # uint8, 0..4, same shape as the input mask
    decisions: Decisions
    ramus_candidates: np.ndarray            # bool: side branches near the LM end (used by the ramus exemption)
    info: dict = field(default_factory=dict)


@dataclass
class Disagreement:
    """A4 / A11 comparison of a reference labelling against the namer (or of two reads)."""
    ignore: np.ndarray                      # bool: voxels both call vessel but name differently
    ignore_fraction: float                  # of the reference's vessel voxels
    ignore_within_10mm_of_carina: float     # share of the ignore voxels within 10 mm of the LM end
    ostium_distance_mm: Optional[float]
    lm_dice: Optional[float]
    lad_lcx_swap: float                     # share of reference LAD+LCx voxels named the other one
    tree_swap: bool                         # a whole tree named left by one, right by the other
    flags: list                             # wholesale triggers that fired: 'ostium', 'lm', 'swap', 'tree'
    ramus_only: bool                        # the swap is confined to a ramus-like branch (exempt: D1b, A11)
    wholesale: bool                         # any flag after the ramus exemption -> review the case, don't mask


# ---------------------------------------------------------------------------------- geometry

def _spacing(affine):
    return np.sqrt((np.asarray(affine, float)[:3, :3] ** 2).sum(0))


class _Skel:
    """Skeleton graph of a vessel mask: vertices (voxel coords), radius (mm), edges, per-vertex component,
    and for every mask voxel the vertex that owns it."""

    def __init__(self, mask: np.ndarray, sp: np.ndarray):
        from skimage.morphology import skeletonize  # lazy: only the namer needs scikit-image

        self.sp = sp
        st = np.ones((3, 3, 3), bool)
        comp, n = ndimage.label(mask, structure=st)
        sizes = np.bincount(comp.ravel(), minlength=n + 1)
        big = np.zeros(n + 1, bool); big[1:] = sizes[1:] >= MIN_COMPONENT_VOXELS
        keep = big[comp]
        sk = skeletonize(keep.astype(np.uint8)).astype(bool) if keep.any() else np.zeros_like(keep)
        # a component whose skeleton vanished (tiny blob) gets one vertex at its deepest voxel
        edt = ndimage.distance_transform_edt(mask, sampling=sp)
        have = np.zeros(n + 1, bool); have[np.unique(comp[sk])] = True
        for k in np.nonzero(big & ~have)[0]:
            cv = np.argwhere(comp == k)
            sk[tuple(cv[np.argmax(edt[tuple(cv.T)])])] = True
        V = np.argwhere(sk)
        self.V = V
        self.R = edt[tuple(V.T)] if len(V) else np.zeros(0)
        self.P = V * sp
        self.cid = comp[tuple(V.T)] if len(V) else np.zeros(0, int)
        # 26-neighbour edges between skeleton voxels
        idx = -np.ones(mask.shape, np.int64)
        idx[tuple(V.T)] = np.arange(len(V))
        rows, cols = [], []
        for off in [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1), (0, 1, 1),
                    (0, 1, -1), (1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1)]:
            q = V + np.array(off)
            ok = np.all((q >= 0) & (q < np.array(mask.shape)), axis=1)
            j = np.full(len(V), -1)
            j[ok] = idx[tuple(q[ok].T)]
            m = j >= 0
            rows.append(np.nonzero(m)[0]); cols.append(j[m])
        r = np.concatenate(rows) if rows else np.zeros(0, int)
        c = np.concatenate(cols) if cols else np.zeros(0, int)
        w = np.linalg.norm(self.P[r] - self.P[c], axis=1) if len(r) else np.zeros(0)
        self.adj = self._tree_adjacency(len(V), r, c, w)
        self._prune_spurs()
        # owners: every mask voxel -> nearest kept vertex of its own component
        self.comp = comp
        self.owner = -np.ones(mask.shape, np.int64)
        alive = np.array(sorted(self.adj), int)
        for k in np.unique(self.cid[alive]) if len(alive) else []:
            vs = alive[self.cid[alive] == k]
            vox = np.argwhere(comp == k)
            _, j = cKDTree(self.P[vs]).query(vox * sp)
            self.owner[tuple(vox.T)] = vs[j]
        self.orphans = [k for k in range(1, n + 1) if sizes[k] > 0 and not (big[k])]

    @staticmethod
    def _tree_adjacency(nv, r, c, w) -> Dict[int, Dict[int, float]]:
        """minimum spanning forest of the 26-neighbour graph (skeletons have small cycles at junction blobs)"""
        adj: Dict[int, Dict[int, float]] = {i: {} for i in range(nv)}
        if nv == 0 or len(r) == 0:
            return adj
        g = coo_matrix((w + 1e-9, (r, c)), shape=(nv, nv)).tocsr()
        t = minimum_spanning_tree(g).tocoo()
        for a, b, x in zip(t.row, t.col, t.data):
            adj[int(a)][int(b)] = float(x); adj[int(b)][int(a)] = float(x)
        return adj

    def _prune_spurs(self, passes: int = 2):
        """drop terminal twigs shorter than TEASAR's invalidation radius at their junction (one or two voxels of
        skimage boundary noise); TEASAR (the experiment's skeletoniser) never produces them"""
        adj = self.adj
        for _ in range(passes):
            removed = False
            for e in [n for n, nb in adj.items() if len(nb) == 1]:
                if e not in adj or len(adj[e]) != 1:
                    continue
                path, prev, cur, acc = [e], None, e, 0.0
                while True:
                    nxt = [x for x in adj[cur] if x != prev]
                    if len(nxt) != 1:
                        break
                    acc += adj[cur][nxt[0]]; prev, cur = cur, nxt[0]
                    if len(adj[cur]) != 2:
                        break
                    path.append(cur)
                if len(adj.get(cur, {})) >= 3 and acc < SPUR_SCALE * self.R[cur] + SPUR_CONST_MM:
                    for p in path:
                        for q in list(adj[p]):
                            adj[q].pop(p, None)
                        adj.pop(p, None)
                    removed = True
            if not removed:
                break

    def components(self) -> Dict[int, List[int]]:
        out: Dict[int, List[int]] = {}
        for v in self.adj:
            out.setdefault(int(self.cid[v]), []).append(v)
        # a component pruned/split into pieces keeps its largest connected piece as the tree
        for k, vs in list(out.items()):
            pieces = self._pieces(vs)
            if len(pieces) > 1:
                out[k] = max(pieces, key=len)
        return out

    def _pieces(self, vs):
        seen, pieces = set(), []
        for s in vs:
            if s in seen:
                continue
            comp, q = [], deque([s]); seen.add(s)
            while q:
                u = q.popleft(); comp.append(u)
                for x in self.adj[u]:
                    if x not in seen:
                        seen.add(x); q.append(x)
            pieces.append(comp)
        return pieces


def _length(adj, nodes) -> float:
    s = set(nodes)
    return sum(w for u in nodes for v, w in adj[u].items() if v in s) / 2


class _Rooted:
    """a tree rooted at `root`: parent, children, BFS order, downstream length L, length-weighted
    position sum S, distance from root"""

    def __init__(self, adj, root, P):
        self.root = root
        self.parent = {root: None}
        self.children: Dict[int, List[int]] = {root: []}
        self.order = [root]
        self.dist = {root: 0.0}
        q = deque([root])
        while q:
            u = q.popleft()
            for v, w in adj[u].items():
                if v not in self.parent:
                    self.parent[v] = u; self.children[v] = []; self.children[u].append(v)
                    self.dist[v] = self.dist[u] + w
                    self.order.append(v); q.append(v)
        self.L = {n: 0.0 for n in self.order}
        self.S = {n: np.zeros(3) for n in self.order}
        for n in reversed(self.order):
            for c in self.children[n]:
                w = adj[n][c]
                self.L[n] += self.L[c] + w
                self.S[n] += self.S[c] + w * (P[n] + P[c]) / 2

    def subtree(self, c):
        out, st = [], [c]
        while st:
            u = st.pop(); out.append(u); st.extend(self.children[u])
        return out


# ---------------------------------------------------------------------------------- ostium

def _endpoint_features(sk: _Skel, nodes, shape, other_P=None):
    adj, P, R, V = sk.adj, sk.P, sk.R, sk.V
    t0 = _Rooted(adj, nodes[0], P)
    L0, tot, par = t0.L, t0.L[nodes[0]], t0.parent

    def beyond(cur, x):
        return L0[x] if par.get(x) == cur else tot - L0[cur]

    def walk(e, max_mm):
        prev, cur, acc, path = None, e, 0.0, [e]
        while acc < max_mm:
            nxt = [x for x in adj[cur] if x != prev]
            if not nxt:
                break
            x = max(nxt, key=lambda y: beyond(cur, y))
            acc += adj[cur][x]; prev, cur = cur, x; path.append(cur)
        return path

    zs = V[nodes, 2]; zmin, zmax = zs.min(), zs.max()
    okd = cKDTree(other_P) if other_P is not None and len(other_P) else None
    feats = []
    for e in nodes:
        if len(adj[e]) != 1:
            continue
        p6, p3 = walk(e, 6.0), walk(e, 3.0)
        prev, cur, sl = None, e, 0.0
        while True:
            nxt = [x for x in adj[cur] if x != prev]
            if len(nxt) != 1:
                break
            sl += adj[cur][nxt[0]]; prev, cur = cur, nxt[0]
        f = dict(e=int(e), r6=float(np.mean(R[p6])), r3=float(np.mean(R[p3])), rmax6=float(np.max(R[p6])),
                 h=float((V[e, 2] - zmin) / max(zmax - zmin, 1e-6)), sl=sl,
                 edge=bool(np.any(V[e] < 2.5) or np.any(V[e] > np.array(shape) - 3.5)),
                 beyond=float(beyond(e, next(iter(adj[e])))) / max(tot, 1e-6),
                 dR=float(okd.query(P[e])[0]) if okd is not None else 0.0)
        feats.append(f)
    for key in ('r6', 'r3', 'h', 'dR'):
        vals = np.array([f[key] for f in feats])
        order = vals.argsort().argsort() / max(len(vals) - 1, 1)
        for f, o in zip(feats, order):
            f[key + '_rk'] = float(o)
    return feats


def _ostium_score(f) -> float:
    if f['edge']:
        return -1e9
    x = np.clip((np.array([f[k] for k in _OST_F]) - _OST_MEAN) / _OST_SCALE, -5, 5)
    return float(x @ _OST_COEF)


# ---------------------------------------------------------------------------------- left tree

def _label_left(sk: _Skel, nodes, root, A, ramus):
    P, sp = sk.P, sk.sp
    t = _Rooted(sk.adj, root, P)
    R3 = A[:3, :3] / sp                      # physical displacement -> RAS displacement
    lab = {n: LM for n in t.order}
    cur, best = root, None
    while t.dist[cur] <= BIF_WINDOW_MM:      # 'apsplit': big second branch, one child anterior one posterior
        ch = sorted(t.children[cur], key=lambda c: -t.L[c])
        if not ch:
            break
        if len(ch) >= 2 and t.L[ch[1]] >= MAJOR_MIN_MM:
            y = [float((R3 @ (t.S[c] / t.L[c] - P[cur]))[1]) for c in ch[:2]]
            sc = t.L[ch[1]] / max(t.L[root], 1) + max(0.0, -y[0] * y[1]) ** 0.5 / 25 - t.dist[cur] / 100
            if best is None or sc > best[0]:
                best = (sc, cur)
        cur = ch[0]
    bif = best[1] if best else None
    info = dict(bif=bif, lm_len=float(t.dist[bif]) if bif is not None else None, ramus=[])
    if bif is None:
        for n in t.order:
            lab[n] = LAD
        info['fail'] = 'no_bifurcation'
        return lab, info, t
    ch = t.children[bif]
    major = [c for c in ch if t.L[c] >= MAJOR_MIN_MM]
    feats = np.array([R3 @ (t.S[c] / t.L[c] - P[bif]) for c in major])
    ant = feats[:, 1]
    i_lad, i_lcx = int(np.argmax(ant)), int(np.argmin(ant))
    cls = {}
    for i, c in enumerate(major):
        cls[c] = LAD if i == i_lad else LCX if i == i_lcx else \
            (LAD if (ant[i] - ant[i_lcx]) > (ant[i_lad] - ant[i]) else LCX)
    for c in ch:
        if c not in cls:
            dv = R3 @ ((t.S[c] / t.L[c]) if t.L[c] > 0 else P[c]) - R3 @ P[bif]
            j = int(np.argmax([np.dot(dv, f) / (np.linalg.norm(dv) * np.linalg.norm(f) + 1e-9) for f in feats]))
            cls[c] = cls[major[j]]
    for c, k in cls.items():
        for n in t.subtree(c):
            lab[n] = k
    # A8 ramus switch: a major branch leaving within RAMUS_WINDOW_MM of the bifurcation (or a third major child)
    # whose subtree lies between the LAD and the LCx in the anterior direction
    lo_a, hi_a = ant[i_lcx], ant[i_lad]
    ram, cand = [], []
    for i, c in enumerate(major):
        if i not in (i_lad, i_lcx):
            ram.append(c)
    for c0 in (major[i_lad], major[i_lcx]):
        cur = c0
        while t.dist[cur] - t.dist[bif] <= RAMUS_CANDIDATE_WINDOW_MM:
            kids = sorted(t.children[cur], key=lambda c: -t.L[c])
            if not kids:
                break
            for side in kids[1:]:
                if t.L[side] >= 10.0:
                    cand.append(side)
                if t.dist[cur] - t.dist[bif] <= RAMUS_WINDOW_MM and t.L[side] >= RAMUS_MIN_MM:
                    a_ = float((R3 @ (t.S[side] / t.L[side] - P[bif]))[1])
                    if lo_a + 0.15 * (hi_a - lo_a) < a_ < hi_a - 0.15 * (hi_a - lo_a):
                        ram.append(side)
            cur = kids[0]
    if ramus in ('LCx', 'LAD'):
        k = LCX if ramus == 'LCx' else LAD
        for c in ram:
            for n in t.subtree(c):
                lab[n] = k
    elif ramus != 'inherit':
        raise ValueError(f"ramus must be 'LCx', 'LAD' or 'inherit', not {ramus!r}")
    info['ramus'] = ram
    info['ramus_candidates'] = [n for c in set(cand) | set(ram) for n in t.subtree(c)]
    info.update(lad_dir=feats[i_lad].tolist(), lcx_dir=feats[i_lcx].tolist())
    return lab, info, t


def _plausibility_penalty(sk, inf, e, A):
    if inf.get('bif') is None:
        return 10.0
    pen, lm = 0.0, inf['lm_len']
    if lm > 30:
        pen += (lm - 30) / 10
    if lm < 1.5:
        pen += 0.5
    if inf['lad_dir'][1] < 0:
        pen += 0.5
    if inf['lcx_dir'][1] > 0:
        pen += 0.5
    zo = (A[:3, :3] @ sk.V[e] + A[:3, 3])[2]; zb = (A[:3, :3] @ sk.V[inf['bif']] + A[:3, 3])[2]
    if zo < zb - 5:
        pen += (zb - 5 - zo) / 10
    return pen


def _bridge(comps: Dict[int, List[int]], sk: _Skel, thr: float):
    """naming bridges: join a component to its nearest neighbour when one of its endpoints lies within thr mm
    (graph only -- no voxel is added or removed; A7/A2 audit records the joins)"""
    comps = {k: list(v) for k, v in comps.items()}
    joins = []
    changed = True
    while changed and len(comps) > 1:
        changed = False
        for k in sorted(comps, key=lambda k: len(comps[k])):
            ends = [n for n in comps[k] if len(sk.adj[n]) <= 1]
            others = [j for j in comps if j != k]
            on = np.concatenate([np.array(comps[j]) for j in others])
            oc = np.concatenate([np.full(len(comps[j]), j) for j in others])
            dd, jj = cKDTree(sk.P[on]).query(sk.P[ends])
            i = int(np.argmin(dd))
            if dd[i] <= thr:
                a, b, j = ends[i], int(on[jj[i]]), int(oc[jj[i]])
                sk.adj[a][b] = float(dd[i]); sk.adj[b][a] = float(dd[i])
                comps[j] = comps[j] + comps[k]; del comps[k]
                joins.append(dict(from_vox=tuple(int(x) for x in sk.V[a]), to_vox=tuple(int(x) for x in sk.V[b]),
                                  gap_mm=float(dd[i])))
                changed = True
                break
    return comps, joins


# ---------------------------------------------------------------------------------- public API

def name_tree(mask, affine, *, ramus: str = "LCx", bridge_mm: float = 4.0) -> NamingResult:
    """Name a coronary tree.

    mask   : 3D array, nonzero = vessel (a binary lumen mask or a 4-class labelling; names are ignored).
    affine : voxel -> world (RAS+) 4x4 matrix of the NIfTI. Spacing and patient directions come from it.
    ramus  : A8 switch. 'LCx' (D1b, the project rule), 'LAD', or 'inherit' (the branch keeps its parent's class).
    bridge_mm : naming bridges between components (graph only; 0 disables).

    Returns labels (uint8 0..4, every class a connected sub-tree of the skeleton), the decisions taken, and
    the ramus-candidate mask used by `compare`'s ramus exemption.
    """
    m = np.asarray(mask) > 0
    A = np.asarray(affine, float)
    out = np.zeros(m.shape, np.uint8)
    empty_ram = np.zeros(m.shape, bool)
    if not m.any():
        return NamingResult(out, Decisions(failure='empty'), empty_ram)
    # crop to the tree (+3 voxels) for speed; results are mapped back
    nz = np.argwhere(m)
    lo = np.maximum(nz.min(0) - 3, 0); hi = np.minimum(nz.max(0) + 4, m.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    sp = _spacing(A)
    Ac = A.copy(); Ac[:3, 3] = A[:3, :3] @ lo + A[:3, 3]
    sk = _Skel(m[sl], sp)
    comps = sk.components()
    joins = []
    if bridge_mm > 0 and len(comps) > 1:
        comps, joins = _bridge(comps, sk, bridge_mm)
    tl = {k: _length(sk.adj, v) for k, v in comps.items()}
    trees = sorted([k for k in comps if tl[k] >= TREE_MIN_MM], key=lambda k: -tl[k])
    dec = Decisions()
    info = dict(n_components=len(comps), tree_lengths_mm=[round(tl[k], 1) for k in trees[:4]], bridges=joins)
    vlab = np.zeros(len(sk.V), np.uint8)
    ram_vertices: List[int] = []
    if not trees:
        dec.failure = 'no_tree'
    else:
        ras_x = {k: float((sk.V[comps[k]] @ Ac[:3, :3].T + Ac[:3, 3])[:, 0].mean()) for k in trees}
        if len(trees) >= 2:
            left = min(trees[:2], key=lambda k: ras_x[k]); right = max(trees[:2], key=lambda k: ras_x[k])
        else:
            left, right = trees[0], None
            dec.failure = 'single_tree'
        dec.fused_trees = tl[left] > FUSED_TREE_MM
        dec.left_component, dec.right_component = left, right
        other = sk.P[comps[right]] if right is not None else None
        ef = _endpoint_features(sk, comps[left], m[sl].shape, other)
        cands = sorted([f for f in ef if not f['edge']], key=lambda f: -_ostium_score(f))[:N_RERANK] or ef[:1]
        best = None
        for f in cands:
            lb, inf, t = _label_left(sk, comps[left], f['e'], Ac, ramus)
            sc = _ostium_score(f) - _plausibility_penalty(sk, inf, f['e'], Ac)
            if best is None or sc > best[0]:
                best = (sc, f['e'], lb, inf)
        if best is not None:
            _, root, labL, inf = best
            for n, k in labL.items():
                vlab[n] = k
            dec.ostium_vox = tuple(int(x) for x in sk.V[root] + lo)
            if inf.get('bif') is not None:
                dec.lm_end_vox = tuple(int(x) for x in sk.V[inf['bif']] + lo)
                dec.lm_length_mm = inf['lm_len']
            dec.n_ramus = len(inf.get('ramus', []))
            if inf.get('fail'):
                dec.failure = dec.failure or inf['fail']
            ram_vertices = inf.get('ramus_candidates', [])
        if right is not None:
            vlab[comps[right]] = RCA
        # every other component: majority class of the nearest named vertices
        named = np.nonzero(vlab)[0]
        if len(named):
            kd = cKDTree(sk.P[named])
            for k, vs in comps.items():
                if k in (left, right):
                    continue
                _, j = kd.query(sk.P[vs])
                vlab[vs] = np.bincount(vlab[named][j], minlength=5).argmax()
            rest = np.array([v for v in sk.adj if vlab[v] == 0], int)
            if len(rest):
                _, j = kd.query(sk.P[rest]); vlab[rest] = vlab[named][j]
    # voxels: class of the owning vertex; orphan blobs (and vertices dropped by pruning): nearest named voxel
    oc = np.zeros(m[sl].shape, np.uint8)
    own = sk.owner >= 0
    oc[own] = vlab[sk.owner[own]]
    rest = m[sl] & (oc == 0)
    if rest.any() and (oc > 0).any():
        _, ind = ndimage.distance_transform_edt(oc == 0, sampling=sp, return_indices=True)
        oc[rest] = oc[tuple(ind)][rest]
    out[sl] = oc
    ram = np.zeros(m.shape, bool)
    if ram_vertices:
        rv = np.zeros(len(sk.V), bool); rv[ram_vertices] = True
        rc = np.zeros(oc.shape, bool); rc[own] = rv[sk.owner[own]]
        ram[sl] = rc
    return NamingResult(out, dec, ram, info)


def rename(labels4, affine, **kw) -> NamingResult:
    """A7 'R': name the foreground of a 4-class prediction (its own names are discarded)."""
    return name_tree(np.asarray(labels4) > 0, affine, **kw)


def extract_decisions(labels4, affine) -> Decisions:
    """Read the decisions off an existing 4-class labelling (a team read, a proxy, a prediction):
    ostium = LM-labelled skeleton point farthest from LAD/LCx; LM end = LM point nearest LAD/LCx;
    left/right components = those holding most LM+LAD+LCx / most RCA centreline."""
    lab = np.asarray(labels4)
    A = np.asarray(affine, float)
    sp = _spacing(A)
    dec = Decisions()
    if not (lab > 0).any():
        dec.failure = 'empty'
        return dec
    sk = _Skel(lab > 0, sp)
    vl = lab[tuple(sk.V.T)] if len(sk.V) else np.zeros(0)
    lm = np.nonzero(vl == LM)[0]; ll = np.nonzero((vl == LAD) | (vl == LCX))[0]
    if len(lm) and len(ll):
        d = cKDTree(sk.P[ll]).query(sk.P[lm])[0]
        dec.ostium_vox = tuple(int(x) for x in sk.V[lm[np.argmax(d)]])
        dec.lm_end_vox = tuple(int(x) for x in sk.V[lm[np.argmin(d)]])
    elif not len(lm):
        dec.failure = 'no_lm'
    left = np.nonzero(np.isin(vl, (LM, LAD, LCX)))[0]; right = np.nonzero(vl == RCA)[0]
    if len(left):
        dec.left_component = int(np.bincount(sk.cid[left]).argmax())
    if len(right):
        dec.right_component = int(np.bincount(sk.cid[right]).argmax())
    dec.fused_trees = dec.left_component is not None and dec.left_component == dec.right_component
    return dec


def compare(reference, named, affine, *, ostium_mm: float = 5.0, lm_dice_min: float = 0.5,
            swap_max: float = 0.05, ramus_candidates: Optional[np.ndarray] = None,
            ramus_share: float = 0.8) -> Disagreement:
    """A4 (proxy vs namer) and A11 (read vs read) comparison of two 4-class labellings of one case.

    ignore   : voxels both call vessel but name differently (A4: set to nnU-Net's ignore label in a proxy;
               A11: ignore in both read samples). Extent differences are NOT in it (A11 keeps each read's extent).
    flags    : wholesale triggers (Atlas/A11 thresholds): 'ostium' (decisions > ostium_mm apart), 'lm'
               (LM Dice < lm_dice_min), 'swap' (> swap_max of reference LAD+LCx voxels named the other one),
               'tree' (left and right trees exchanged).
    ramus_only : when `ramus_candidates` (NamingResult.ramus_candidates) is given and >= ramus_share of the
               swapped voxels lie in it, the 'swap' flag is a ramus-only disagreement: resolved by D1b, not by a
               third read (A11) -> exempt from `wholesale`.
    """
    ref = np.asarray(reference); nm = np.asarray(named)
    A = np.asarray(affine, float); sp = _spacing(A)
    both = (ref > 0) & (nm > 0)
    ignore = both & (ref != nm)
    nref = max(int((ref > 0).sum()), 1)
    dr, dn = extract_decisions(ref, A), extract_decisions(nm, A)
    near = 0.0
    if ignore.any() and dr.lm_end_vox is not None:
        iv = np.argwhere(ignore) * sp
        near = float((np.linalg.norm(iv - np.array(dr.lm_end_vox) * sp, axis=1) <= 10.0).mean())
    ost = None
    if dr.ostium_vox is not None and dn.ostium_vox is not None:
        ost = float(np.linalg.norm((np.array(dr.ostium_vox) - np.array(dn.ostium_vox)) * sp))
    a, b = ref == LM, nm == LM
    lm_dice = float(2 * (a & b).sum() / (a.sum() + b.sum())) if (a.any() or b.any()) else None
    ll = (ref == LAD) | (ref == LCX)
    swapped = ((ref == LAD) & (nm == LCX)) | ((ref == LCX) & (nm == LAD))
    swap = float(swapped.sum() / max(ll.sum(), 1))
    rv, nv = ref > 0, nm > 0
    tree_swap = bool(((ref == RCA) & nv & (nm != RCA)).sum() > 0.5 * max((ref == RCA).sum(), 1)
                     or (((ref > 0) & (ref < RCA)) & (nm == RCA)).sum() > 0.5 * max(((ref > 0) & (ref < RCA)).sum(), 1))
    flags = []
    if ost is not None and ost > ostium_mm:
        flags.append('ostium')
    if lm_dice is not None and lm_dice < lm_dice_min:
        flags.append('lm')
    if swap > swap_max:
        flags.append('swap')
    if tree_swap:
        flags.append('tree')
    ramus_only = False
    if 'swap' in flags and ramus_candidates is not None and swapped.any():
        ramus_only = float((swapped & np.asarray(ramus_candidates, bool)).sum() / swapped.sum()) >= ramus_share
    wholesale = bool([f for f in flags if not (f == 'swap' and ramus_only)])
    del rv
    return Disagreement(ignore=ignore, ignore_fraction=float(ignore.sum() / nref),
                        ignore_within_10mm_of_carina=near, ostium_distance_mm=ost, lm_dice=lm_dice,
                        lad_lcx_swap=swap, tree_swap=tree_swap, flags=flags, ramus_only=ramus_only,
                        wholesale=wholesale)


def icx_to_four(icx_labels) -> np.ndarray:
    """ImageCAS-X 14-class map -> 4 classes (D1 territory, D1b ramus -> LCx). 'Other' (14) -> 0."""
    lut = np.zeros(256, np.uint8)
    for k, v in ICX_TO_4.items():
        lut[k] = v
    return lut[np.clip(np.asarray(icx_labels), 0, 255).astype(np.int64)]
