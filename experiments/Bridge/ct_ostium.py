"""Does the CT find the left ostium where the mask alone cannot?
For every endpoint of the left tree: fraction of NON-mask voxels within 4 mm that are as bright as the
contrast-filled lumen (HU >= 0.75 * median lumen HU near the endpoint). The ostium end abuts the
contrast-filled aortic root; distal ends abut myocardium / fat.
Cases: those with a cached CT (every 25th case) that also have ImageCAS-X labels.
usage: ct_ostium.py EXDIR OUT.jsonl
"""
import sys, os, glob, json, numpy as np, nibabel as nib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import label as Lb
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools'); from girder import mask_path
ex, outp = sys.argv[1:3]
cts = sorted(os.path.basename(p)[:5] for p in glob.glob(SCR + '/data/ct/c*.nii.gz'))
with open(outp, 'w') as fo:
    for c in cts:
        f = os.path.join(ex, c + '.npz')
        if not os.path.exists(f):
            continue
        d = Lb.load_case(f)
        if d['icx_stats'] is None:
            continue
        ct = nib.load(SCR + f'/data/ct/{c}.nii.gz')
        m = nib.load(mask_path(c))
        assert np.allclose(ct.affine, m.affine, atol=1e-3)
        CT = np.asarray(ct.dataobj).astype(np.int16)
        M = (np.asarray(m.dataobj) > 0.5)
        lab, olab, res, ef = Lb.label_case(d, 'combo')
        z = d['zooms']
        rad = float(os.environ.get('RAD', 4.0))
        rv = np.ceil(rad / z).astype(int)
        for fe in ef:
            p = np.round(d['V'][fe['e']]).astype(int)
            lo = np.maximum(p - rv, 0); hi = np.minimum(p + rv + 1, d['shape'])
            sl = tuple(slice(a, b) for a, b in zip(lo, hi))
            hu = np.asarray(CT[sl], np.float32); mk = np.asarray(M[sl]) > 0.5
            g = np.stack(np.meshgrid(*[np.arange(a, b) for a, b in zip(lo, hi)], indexing='ij'), -1)
            ball = np.linalg.norm((g - p) * z, axis=-1) <= rad
            lum = hu[ball & mk]
            ref = np.median(lum) if len(lum) else 300.0
            nm = hu[ball & ~mk]
            fe['bright'] = float((nm >= 0.75 * ref).mean()) if len(nm) else 0.0
            fe['lum_hu'] = float(ref)
        # ICX truth
        cnt = d['CNT'][:, 1:4]; maj = np.where(cnt.sum(1) > 0, cnt.argmax(1) + 1, 0)
        from scipy.spatial import cKDTree
        Mv = np.where(maj == 1)[0]; Bv = np.where((maj == 2) | (maj == 3))[0]
        if not len(Mv) or not len(Bv):
            continue
        dist = cKDTree(d['P'][Bv]).query(d['P'][Mv])[0]; ost = d['P'][Mv[np.argmax(dist)]]
        for fe in ef:
            fe['d_true'] = float(np.linalg.norm(d['P'][fe['e']] - ost))
        fo.write(json.dumps(dict(case=c, ef=ef)) + '\n'); fo.flush()
