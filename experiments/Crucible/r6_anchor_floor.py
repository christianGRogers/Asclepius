# Round 5 (A12b prerequisite): convention noise floor of the ImageCAS-X carina anchor.
# For each non-sealed ImageCAS-X train/val case:
#   thick mask m  = Girder/ImageCAS mask (D0 convention), crop to bbox
#   proxy P       = m split by nearest ImageCAS-X territory class (sim.truth; ramus -> LCx)  -- "a team that drew
#                   exactly ImageCAS-X's carina on the thick mask"
#   centreline    = 3-D skeleton of the LEFT tree of m; geodesic distance d from the ostium (skeleton point nearest the
#                   ImageCAS-X LM voxel farthest from LAD/LCx)
#   carina of a labelling = centroid of its LM voxels touching LAD/LCx, projected to the nearest skeleton point -> d
#   offsets (mm along the centreline):
#     proxy - icx      : the floor if the team reproduces ImageCAS-X's naming exactly (projection / geometry noise only)
#     skelbif - icx    : the floor if the team instead puts the carina at the thick tree's own skeleton bifurcation
#                        (nearest skeleton junction node to the ICX carina)
# Sealed cases (trillium/sealed_test.json) are refused. Usage: python r6_anchor_floor.py N
import sys, os, json, hashlib, numpy as np, nibabel as nib
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra, connected_components
from skimage.morphology import skeletonize
sys.path.insert(0, '/home/user/Asclepius/trillium/crucible/lib'); import sim  # noqa: E402
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools'); from girder import mask_path  # noqa: E402
ICX = SCR + '/work/Crucible/icx/ImageCAS-X_dataset'
OUT = SCR + '/work/Crucible/' + ('r6inject' if os.environ.get('INJECT') == '1' else 'r6anchor'); os.makedirs(OUT, exist_ok=True)
S26 = np.ones((3, 3, 3))
sealed = json.load(open('/home/user/Asclepius/trillium/sealed_test.json'))
SEALED = set(sealed['sealed_icx_test']) | set(sealed['sealed_quality0'])


def junction_centroid(L):
    lm = L == 1; lr = np.isin(L, (2, 3))
    j = lm & ndi.binary_dilation(lr, S26)
    return np.argwhere(j).mean(0) if j.any() else None


def run(c):
    i = int(c[1:]) + 1
    icx = np.asarray(nib.load(f'{ICX}/segmentations/{i}.coronary.nii.gz').dataobj).astype(np.uint8)
    img = nib.load(mask_path(c)); m = np.asarray(img.dataobj) > 0.5; sp = np.array(img.header.get_zooms()[:3], float)
    u = np.argwhere(m | (icx > 0)); lo = np.maximum(u.min(0) - 3, 0); hi = u.max(0) + 4
    sl = tuple(slice(a, b) for a, b in zip(lo, hi)); m = m[sl]; icx = icx[sl]
    if not (icx == 1).any(): return {'case': c, 'skip': 'no LM in ImageCAS-X'}
    P, _ = sim.truth(m, icx)
    I4 = sim.TERR[icx]
    # left tree of the thick mask = component holding most proxy LM voxels
    lab, _ = ndi.label(m, S26); k = np.bincount(lab[P == 1]).argmax(); left = lab == k
    sk = skeletonize(left); pts = np.argwhere(sk); n = len(pts)
    idx = -np.ones(sk.shape, np.int64); idx[tuple(pts.T)] = np.arange(n)
    rows, cols, w = [], [], []
    for o in np.argwhere(np.ones((3, 3, 3))) - 1:
        if not o.any(): continue
        q = pts + o; ok = np.all((q >= 0) & (q < sk.shape), 1); q2 = q[ok]; j = idx[tuple(q2.T)]; good = j >= 0
        rows += list(np.nonzero(ok)[0][good]); cols += list(j[good]); w += [float(np.linalg.norm(o * sp))] * int(good.sum())
    G = coo_matrix((w, (rows, cols)), shape=(n, n)).tocsr()
    # ostium: ImageCAS-X LM voxel farthest from LAD/LCx -> nearest skeleton point
    d23 = ndi.distance_transform_edt(~np.isin(icx, (2, 3)), sampling=sp)
    lmv = np.argwhere(icx == 1); ost = lmv[np.argmax(d23[icx == 1])]
    near = lambda p: int(np.argmin((((pts - p) * sp) ** 2).sum(1)))
    o_node = near(ost)
    d, pred = dijkstra(G, indices=o_node, return_predecessors=True)
    out = {'case': c}
    cP = junction_centroid(P); cI = junction_centroid(I4)
    if cP is None or cI is None: return {'case': c, 'skip': 'no LM/LAD-LCx contact'}
    nP, nI = near(cP), near(cI)
    if not (np.isfinite(d[nP]) and np.isfinite(d[nI])): return {'case': c, 'skip': 'carina not reachable on skeleton'}
    out['proxy_minus_icx'] = float(d[nP] - d[nI])
    out['icx_carina_d'] = float(d[nI]); out['icx_proj_dist_mm'] = float(np.sqrt((((pts[nI] - cI) * sp) ** 2).sum()))
    # thick-tree bifurcation by topology, independent of where ImageCAS-X put its carina: lowest common ancestor (on the
    # shortest-path tree from the ostium) of the farthest LAD point and the farthest LCx point (proxy names, which are
    # correct far from the carina)
    lab_sk = P[tuple(pts.T)]
    def path(t):
        p = [];  # noqa: E702
        while t >= 0 and t != o_node: p.append(t); t = pred[t]
        return p[::-1]
    far = {}
    for k in (2, 3):
        cand = np.nonzero((lab_sk == k) & np.isfinite(d))[0]
        if len(cand): far[k] = cand[np.argmax(d[cand])]
    if len(far) == 2:
        pa, pb = path(far[2]), path(far[3]); lca = o_node
        for x, y in zip(pa, pb):
            if x != y: break
            lca = x
        out['skelbif_minus_icx'] = float(d[lca] - d[nI])
        out['skelbif_euclid_from_icx_mm'] = float(np.sqrt((((pts[lca] - cI) * sp) ** 2).sum()))
    out['icx_lm_len_mm'] = float(d[nI])
    # recovery of an injected carina shift (sim.py's operation on the proxy): what does the anchor read?
    if os.environ.get('INJECT') == '1':
        d_lm = ndi.distance_transform_edt(P != 1, sampling=sp); d_23 = ndi.distance_transform_edt(~np.isin(P, (2, 3)), sampling=sp)
        _, ind23 = ndi.distance_transform_edt(~np.isin(P, (2, 3)), return_indices=True)
        for shv in (-2.0, -1.0, 1.0, 2.0):
            R = P.copy()
            if shv > 0: R[np.isin(R, (2, 3)) & (d_lm <= shv)] = 1
            else:
                sel = (R == 1) & (d_23 <= -shv); R[sel] = P[tuple(ind23)][sel]
            cR = junction_centroid(R)
            out[f'inject_{shv:+.0f}'] = float(d[near(cR)] - d[nI]) if cR is not None and np.isfinite(d[near(cR)]) else None
    return out


if __name__ == '__main__':
    N = int(sys.argv[1])
    ids = [int(x) for f in ('train', 'val') for x in open(f'{ICX}/filelist/{f}.txt').read().split()]
    cases = sorted({f'c{i - 1:04d}' for i in ids} - SEALED, key=lambda c: hashlib.sha256(('crucible-anchor:' + c).encode()).hexdigest())[:N]
    for c in cases:
        assert c not in SEALED
        fn = f'{OUT}/{c}.json'
        if os.path.exists(fn): continue
        try: r = run(c)
        except Exception as e: r = {'case': c, 'skip': f'error {type(e).__name__}: {e}'}
        json.dump(r, open(fn, 'w')); print(json.dumps(r), flush=True)
