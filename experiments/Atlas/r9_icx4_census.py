"""Round 9: what the D25 four-class labels look like, on ImageCAS-X collapsed exactly as icx4 trains on them
(trillium/icx4/lib/territory.py, Other -> nearest LAD/LCx in mm).
Per case and class: presence, voxels, mm^3, share contributed by side branches, and connectivity (26-connected
components per class; voxels outside the largest one). Also: does each class touch the rest of the tree, and is
the ramus (IM) a separate LCx-class component. Labels only; no CT needed.
Usage: python r9_icx4_census.py <icx_dir> <repo_root> <out.json> [n_proc]"""
import os, sys, json, glob
from multiprocessing import Pool
import numpy as np, nibabel as nib
from scipy import ndimage as ndi

ICX, ROOT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
NP = int(sys.argv[4]) if len(sys.argv) > 4 else 3
sys.path.insert(0, os.path.join(ROOT, 'trillium/icx4/lib'))
from territory import to_four  # noqa: E402

NAMES = ['LM', 'LAD', 'LCx', 'RCA']
MAIN = {1: 1, 2: 2, 3: 3, 4: 9}   # four-class value -> ImageCAS-X value of its main vessel
S26 = np.ones((3, 3, 3), bool)


def one(path):
    cid = int(os.path.basename(path).split('.')[0])
    im = nib.load(path)
    lab = np.asarray(im.dataobj).astype(np.int64)
    nz = np.argwhere(lab > 0)   # crop to the labels (+2 voxels): nothing outside changes any number below
    lo, hi = np.maximum(nz.min(0) - 2, 0), nz.max(0) + 3
    lab = lab[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    z = im.header.get_zooms()[:3]
    vox = float(np.prod(z))
    four = to_four(lab, z)
    r = {'icx_id': cid, 'case': 'c%04d' % (cid - 1), 'zooms': [round(float(v), 3) for v in z],
         'other_vox': int((lab == 14).sum()), 'im_present': bool((lab == 8).any()), 'cls': {}}
    tree, ntree = ndi.label(four > 0, S26)
    r['tree_components'] = int(ntree)
    for k, n in enumerate(NAMES, 1):
        m = four == k
        nv = int(m.sum())
        d = {'vox': nv, 'mm3': round(nv * vox, 1)}
        if nv:
            d['side_share'] = round(1 - float((lab[m] == MAIN[k]).sum()) / nv, 4)
            cc, ncc = ndi.label(m, S26)
            sizes = np.bincount(cc.ravel())[1:]
            d['components'] = int(ncc)
            d['outside_largest_share'] = round(1 - sizes.max() / nv, 4)
            # components of this class that are >= 20 voxels (ignore specks)
            d['components_ge20'] = int((sizes >= 20).sum())
        r['cls'][n] = d
    # ramus: is the IM (-> LCx) its own LCx-class component, i.e. not 26-connected to the LCx main vessel?
    if r['im_present']:
        lcx = four == 3
        cc, _ = ndi.label(lcx, S26)
        im_ids = set(np.unique(cc[lab == 8])) - {0}
        main_ids = set(np.unique(cc[lab == 3])) - {0}
        r['im_separate_from_lcx_main'] = bool(im_ids and not (im_ids & main_ids))
    return r


if __name__ == '__main__':
    files = sorted(glob.glob(os.path.join(ICX, '*.coronary.nii.gz')), key=lambda p: int(os.path.basename(p).split('.')[0]))
    with Pool(NP) as p:
        rows = p.map(one, files, chunksize=4)
    split = {}
    for s in ('train', 'val', 'test'):
        f = os.path.join(ICX, f'{s}.txt')
        if os.path.exists(f):
            for x in open(f).read().split():
                split[int(x)] = s
    for r in rows:
        r['split'] = split.get(r['icx_id'], '?')
    # A14: the sealed ImageCAS-X test cases are never inspected, not even their labels; drop them from the output
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    rows = [r for r in rows if r['case'] not in sealed]
    json.dump(rows, open(OUT, 'w'))
    print(f'{len(rows)} cases')
