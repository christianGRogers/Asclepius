"""Janus 1-F round 2 (Crucible): one pass over the 620 D45 training labels (no CT, no other case) for items 1, 2, 4, 10.

Per case:
  * 1-F labels (`branch_score.to_1f`, D47 Q1 (A), F-A3) and the check collapse4(1-F) == territory.to_four(ICX) outside
    ignore and Other;
  * reference branches per class: piece lengths (centreline mm) at the 5 mm presence line, and pieces of 3-5 mm;
  * presence at 3 mm and at 5 mm per class;
  * self-score (reference scored against itself: detection = naming = presence agreement = branch tF1 = 1 expected),
    and three perturbations whose scores are known in advance: D1<->D2 swapped (naming of D1, D2 -> 0), OM2 deleted
    (OM2 detection -> 0, presence agreement of OM2 -> 1 - prevalence), PDA renamed RCA (PDA detected, naming 0);
    tF1 is run on the first N_TF1 cases only (it is the slow part);
  * the background band (item 4): background voxels within 8 and 15 mm of each host (LAD tree = LAD+D1-D3; RCA;
    proximal RCA = RCA within 30 mm of its thickest endpoint; proximal LCx = LCx within 20 mm of the LM), in mm^3,
    their overlaps, and the tree volume;
  * trunk twigs (item 10): see `twigs` below.
Usage: census620.py <icx_dir> <split.json> <out.jsonl> [workers] [n_tf1]"""
import json, os, sys
from multiprocessing import Pool

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'trillium', 'icx4', 'lib'))
import branch_score as B  # noqa: E402
import territory  # noqa: E402
from skan import Skeleton, summarize  # noqa: E402

BANDS = (8.0, 15.0)
MARGIN_MM = 20.0


def crop(lab, sp, margin_mm):
    sl = ndi.find_objects((lab > 0).astype(np.uint8))[0]
    m = np.ceil(margin_mm / sp).astype(int)
    return tuple(slice(max(s.start - m[k], 0), min(s.stop + m[k], lab.shape[k])) for k, s in enumerate(sl))


def twigs(m1f, sp):
    """Unnamed side branches inside a trunk class (2 LAD, 3 LCx, 4 RCA) of the 1-F reference.
    Definition of record (proposed): a skan branch of the whole-tree skeleton that (i) ends in a free endpoint
    (type 1, junction-to-endpoint), (ii) has every skeleton voxel in one trunk class, (iii) is >= L mm long, and
    (iv) is not the trunk's own distal end, defined as the endpoint of that class farthest (geodesic, along the tree
    skeleton) from the tree's root (the LM's thickest end for LAD/LCx, the RCA's thickest end for the RCA).
    Returned: per trunk, the list of twig lengths >= 3 mm."""
    sk = B.skeleton_labels(m1f) > 0
    if sk.sum() < 10:
        return {}
    skel = Skeleton(sk, spacing=sp)
    st = summarize(skel, separator='_')
    lab_at = m1f[sk]
    coords = np.argwhere(sk)
    # map coordinate -> skeleton node id
    nid = {tuple(c): i for i, c in enumerate(skel.coordinates.astype(int))}
    edt = ndi.distance_transform_edt((m1f > 0) & (m1f != 255), sampling=sp)
    out = {}
    import scipy.sparse.csgraph as csg
    G = skel.graph
    for trunk, root_cls in ((2, 1), (3, 1), (4, 4)):
        rows = []
        for _, r in st.iterrows():
            if int(r['branch_type']) != 1:
                continue
            path = skel.path_coordinates(int(r.name)).astype(int)
            vals = m1f[tuple(path.T)]
            # the junction voxel may carry the parent's label; judge on interior voxels
            inner = vals[1:-1] if len(vals) > 2 else vals
            if len(inner) and np.all(inner == trunk):
                end = path[-1] if m1f[tuple(path[-1])] == trunk and _is_end(skel, path[-1], nid) else path[0]
                rows.append((float(r['branch_distance']), tuple(end)))
        if not rows:
            out[B.NAMES[trunk]] = []
            continue
        # root: thickest skeleton voxel of root class (LM) or of RCA
        rc = np.argwhere(sk & (m1f == root_cls))
        if not len(rc):
            rc = np.argwhere(sk & (m1f == trunk))
        root = tuple(rc[np.argmax(edt[tuple(rc.T)])])
        dist = csg.dijkstra(G, indices=nid[root])
        ends = [(dist[nid[e]] if e in nid else -1, L, e) for L, e in rows]
        far = max(ends)[2] if ends else None
        out[B.NAMES[trunk]] = sorted(round(L, 2) for d, L, e in ends if e != far and L >= 3.0)
    return out


def _is_end(skel, p, nid):
    i = nid.get(tuple(p))
    return i is not None and skel.degrees[i] == 1


def bands(m1f, sp, step=(3, 3, 2)):
    """On a coarse grid (label max-pooled by `step`, ~1 mm), so volumes are approximate (+/- one coarse voxel shell)."""
    st = tuple(step)
    sh = tuple(s // k * k for s, k in zip(m1f.shape, st))
    mm = m1f[:sh[0], :sh[1], :sh[2]]
    # majority-free pooling: a coarse voxel takes the highest-priority class inside it (branch/trunk over bg)
    v = mm.reshape(sh[0] // st[0], st[0], sh[1] // st[1], st[1], sh[2] // st[2], st[2])
    m1f = np.where(v == 255, 0, v).max(axis=(1, 3, 5)).astype(np.uint8)
    sp = np.asarray(sp, float) * np.array(st)
    fg = (m1f > 0)
    bg = ~fg
    hosts = {'LADtree': np.isin(m1f, (2, 5, 6, 7)), 'RCA': m1f == 4}
    # proximal RCA: within 30 mm of the thickest RCA voxel; proximal LCx: LCx within 20 mm of the LM
    edt = ndi.distance_transform_edt(fg & (m1f != 255), sampling=sp)
    rca = m1f == 4
    if rca.any():
        pts = np.argwhere(rca)
        o = pts[np.argmax(edt[tuple(pts.T)])]
        d = np.linalg.norm((pts - o) * sp, axis=1)
        pr = np.zeros_like(rca)
        pr[tuple(pts[d <= 30].T)] = True
        hosts['proxRCA'] = pr
    lm = m1f == 1
    lcx = m1f == 3
    if lm.any() and lcx.any():
        dlm = ndi.distance_transform_edt(~lm, sampling=sp)
        hosts['proxLCx'] = lcx & (dlm <= 20)
    vox = float(np.prod(sp))
    res = {'tree_mm3': round(float(fg.sum()) * vox, 1)}
    dist = {h: ndi.distance_transform_edt(~m, sampling=sp) for h, m in hosts.items() if m.any()}
    for b in BANDS:
        inb = {h: bg & (d <= b) for h, d in dist.items()}
        res[f'{b:g}'] = {h: round(float(m.sum()) * vox, 1) for h, m in inb.items()}
        if 'LADtree' in inb and 'RCA' in inb:
            res[f'{b:g}']['LADtree&RCA'] = round(float((inb['LADtree'] & inb['RCA']).sum()) * vox, 1)
        allb = np.zeros_like(bg)
        for m in inb.values():
            allb |= m
        # any traced vessel within b mm that is NOT a host (D1-D3/LM/LCx/OM near the RCA band etc. are fg, excluded)
        res[f'{b:g}']['union'] = round(float(allb.sum()) * vox, 1)
    return res


def perturb(m, kind):
    p = m.copy()
    if kind == 'swapD':
        p[m == 5], p[m == 6] = 6, 5
    elif kind == 'dropOM2':
        p[m == 9] = 0
    elif kind == 'PDAasRCA':
        p[m == 11] = 4
    return p


def one(args):
    path, case, do_tf1 = args
    im = nib.load(path)
    icx = np.asarray(im.dataobj).astype(np.uint8)
    sp = np.array(im.header.get_zooms()[:3], float)
    m1f, info = B.to_1f(icx, sp)
    ref4 = territory.to_four(icx, sp)
    c4 = B.collapse4(m1f)
    keep = (m1f != 255) & (icx != 14)
    row = {'case': case, 'spacing': sp.round(4).tolist(), 'map': info,
           'collapse_mismatch': int(((c4 != ref4) & keep).sum()),
           'collapse_mismatch_other': int(((c4 != ref4) & (icx == 14)).sum()),
           'ignore_voxels': int((m1f == 255).sum())}
    sl = crop(m1f, sp, MARGIN_MM)
    m = m1f[sl]
    rs = B.skeleton_labels(m)
    p5 = B.pieces(m, sp, rs, min_mm=B.PRESENT_MM)
    p3 = B.pieces(m, sp, rs, min_mm=3.0)
    row['pieces5'] = {B.NAMES[c]: [round(L, 1) for _, _, L in v] for c, v in p5.items()}
    row['pieces3'] = {B.NAMES[c]: [round(L, 1) for _, _, L in v] for c, v in p3.items()}
    row['class_mm'] = {B.NAMES[c]: round(B.length_mm(rs == c, sp), 1) for c in range(1, 13)}
    sc = {}
    for kind in (('self', 'swapD', 'dropOM2', 'PDAasRCA') if do_tf1 else ()):
        pr = m if kind == 'self' else perturb(m, kind)
        dn = B.detect_and_name(m, pr, sp, p5)
        pp = B.presence(pr, sp)
        pref = B.presence(m, sp, rs)
        e = {'dn': {B.NAMES[c]: v for c, v in dn.items()},
             'pres_agree': {B.NAMES[c]: bool(pp[c] == pref[c]) for c in B.BRANCHES}}
        if do_tf1 and kind in ('self', 'swapD'):
            e['tf1'] = {B.NAMES[c]: B.branch_tf1(m, pr, sp, c, p5) for c in (5, 6, 8, 11)}
        sc[kind] = e
    row['score'] = sc
    row['bands'] = bands(m, sp)
    try:
        row['twigs'] = twigs(m, sp)
    except Exception as ex:  # noqa: BLE001
        row['twigs_error'] = repr(ex)[:200]
    return row


def main(icx_dir, split_json, out, workers=4, n_tf1=40):
    S = json.load(open(split_json))
    cases = S['train620']
    assert len(cases) == 620 and not set(cases) & set(S['locked100'])
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)['case'] for l in open(out)}
    args = [(os.path.join(icx_dir, '%d.coronary.nii.gz' % (int(c[1:]) + 1)), c, i < n_tf1)
            for i, c in enumerate(cases) if c not in done]
    with Pool(int(workers)) as pool, open(out, 'a') as f:
        for r in pool.imap_unordered(one, args):
            f.write(json.dumps(r) + '\n')
            f.flush()


if __name__ == '__main__':
    main(*sys.argv[1:4], *[int(x) for x in sys.argv[4:]])
