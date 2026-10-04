# Score r2_train.py predictions with the master plan's deciding metric (tree-F1, Delta's definition re-implemented on
# our crops): per class c, recall = reference (ICX lumen) centreline of class c predicted as c AND in a predicted
# component touching the reference ostium (within 1.5 mm); precision = predicted centreline labelled c lying in
# reference voxels of class c; macro over classes present. Gap tolerance d: predicted pieces within d mm count as
# connected (prediction dilated by d/2 before components). Ostia = thickest reference skeleton endpoint of LM (left)
# and of RCA (right) -- Delta's heuristic, NOT the aorta-contact rule (limit stated in the note).
# Usage: python r2_eval.py RUN [RUN ...]   (RUN = directory name under r2pred/)
import sys, json, numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
D = SCR + '/work/Crucible/r2data'; P = SCR + '/work/Crucible/r2pred'
TERR = np.zeros(15, np.uint8); TERR[[1]] = 1; TERR[[2, 4, 5]] = 2; TERR[[3, 6, 7, 12, 13]] = 3; TERR[[9, 10, 11]] = 4
meta = json.load(open(D + '/meta.json')); test = sorted(c for c, v in meta.items() if v['test'])
S26 = np.ones((3, 3, 3))
import os
REF = os.environ.get('REF', 'thin')  # reference convention: thin (ICX lumen) or thick (Girder proxy)


def thin4(lab):
    L = lab & 15; t = TERR[L]; amb = (L == 8) | (L == 14)
    return np.where(amb, np.where(lab >> 7, 3, 2), t).astype(np.uint8)


def drop_small(p4, n=100):
    lab, k = ndi.label(p4 > 0, S26)
    if k == 0: return p4
    sz = np.bincount(lab.ravel()); keep = sz >= n; keep[0] = False
    return np.where(keep[lab], p4, 0).astype(np.uint8)


def roots(ref, sk, sp):
    rad = ndi.distance_transform_edt(ref > 0, sampling=sp)
    nb = ndi.convolve(sk.astype(np.uint8), S26.astype(np.uint8), mode='constant') - 1
    end = sk & (nb == 1)
    radn = ndi.uniform_filter(np.where(sk, rad, 0), 5) / np.maximum(ndi.uniform_filter(sk.astype(float), 5), 1e-6)
    out = []
    for cs in ((1,), (4,)):
        cand = np.argwhere(end & np.isin(ref, cs))
        if len(cand) == 0 and cs == (1,): cand = np.argwhere(end & np.isin(ref, (1, 2, 3)))
        if len(cand): out.append(cand[np.argmax(radn[tuple(cand.T)])])
    return out


def score(ref, p4, sp, refsk, rts, tol):
    pm = p4 > 0
    if tol > 0:
        pd = ndi.distance_transform_edt(~pm, sampling=sp) <= tol / 2
    else:
        pd = pm
    comp, _ = ndi.label(pd, S26)
    rc = set()
    r = np.ceil(1.5 / sp).astype(int)
    for rt in rts:
        sl = tuple(slice(max(a - b, 0), a + b + 1) for a, b in zip(rt, r))
        g = np.stack(np.meshgrid(*[np.arange(s.start, min(s.stop, n)) for s, n in zip(sl, ref.shape)], indexing='ij'), -1)
        d = np.sqrt((((g - rt) * sp) ** 2).sum(-1)); sub = comp[sl][: d.shape[0], : d.shape[1], : d.shape[2]]
        rc |= set(np.unique(sub[(d <= 1.5) & (sub > 0)]).tolist())
    pts = np.argwhere(refsk); gl = ref[tuple(pts.T)]; pl = p4[tuple(pts.T)]
    rooted = np.isin(comp[tuple(pts.T)], list(rc)) if rc else np.zeros(len(pts), bool)
    psk = skeletonize(pm) if pm.any() else pm
    pp = np.argwhere(psk); ppl = p4[tuple(pp.T)]; ppr = ref[tuple(pp.T)]
    res = {}
    for c in (1, 2, 3, 4):
        g = gl == c
        if not g.any(): continue
        rec = float(((pl == c) & rooted & g).sum() / g.sum()); rec_u = float(((pl == c) & g).sum() / g.sum())
        pc = ppl == c; prec = float((ppr[pc] == c).mean()) if pc.any() else 0.0
        res[c] = dict(rec=rec, rec_unrooted=rec_u, prec=prec,
                      tf1=2 * rec * prec / (rec + prec) if rec + prec else 0.0,
                      cl=2 * rec_u * prec / (rec_u + prec) if rec_u + prec else 0.0)
    return res


out = []
for run in sys.argv[1:]:
    for c in test:
        lab0 = np.load(f'{D}/{c}_lab.npy')
        ref = ((lab0 >> 4) & 7).astype(np.uint8) if REF == 'thick' else thin4(lab0); sp = np.array(meta[c]['spacing'])
        p4 = drop_small(np.load(f'{P}/{run}/{c}_pred4.npy'))
        refsk = skeletonize(ref > 0); rts = roots(ref, refsk, sp)
        row = {'run': run, 'case': c, 'ref': REF}
        for tol in (0.0, 1.5):
            s = score(ref, p4, sp, refsk, rts, tol)
            row[f'tf1@{tol}'] = float(np.mean([v['tf1'] for v in s.values()]))
            row[f'rec@{tol}'] = float(np.mean([v['rec'] for v in s.values()]))
            row[f'perclass@{tol}'] = {k: round(v['tf1'], 3) for k, v in s.items()}
        row['class_cldice'] = float(np.mean([v['cl'] for v in s.values()]))
        row['rec_unrooted'] = float(np.mean([v['rec_unrooted'] for v in s.values()]))
        row['prec'] = float(np.mean([v['prec'] for v in s.values()]))
        pm = p4 > 0; lab, k = ndi.label(pm, S26); row['ncomp'] = int(k)
        near = ndi.distance_transform_edt(ref == 0, sampling=sp) <= 2.0
        row['fp_comp'] = int(sum(1 for i in range(1, k + 1) if not near[lab == i].any()))
        rm = ref > 0; row['dice_bin'] = float(2 * (pm & rm).sum() / (pm.sum() + rm.sum()))
        row['vol_ratio'] = float(pm.sum() / rm.sum())
        # 'cut' = some class keeps < 80 % of its unrooted recall once rooting is required (at 1.5 mm)
        row['cut'] = bool(any(v['rec'] < 0.8 * v['rec_unrooted'] for v in s.values() if v['rec_unrooted'] > 0.2))
        out.append(row); print(json.dumps(row), flush=True)
json.dump(out, open(P + f'/eval_ref{REF}_' + '_'.join(sys.argv[1:]) + '.json', 'w'))
