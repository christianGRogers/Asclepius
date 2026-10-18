"""Round 9: what the D25 territory collapse does to ImageCAS-X's 800 label maps (trillium/icx4/lib/territory.py,
the exact code icx4 trains on). Per case:
  * presence and voxel count of LM/LAD/LCx/RCA after collapse; how much came from side-branch classes;
  * 'Other' (14): voxels, connected pieces (26-conn), and for each piece the class the nearest-voxel rule gives vs
    the collapsed class of the voxels it touches (its parent in the tree, when it touches one);
  * connected components per collapsed class (>= 10 voxels), i.e. territories that arrive in pieces;
  * contacts between classes that the protocol says should not touch (LM-RCA, LAD-RCA, LCx-RCA).
Usage: r9_territory_audit.py <icx_dir> <out.json> [n_proc]. CPU only."""
import os, sys, json
from multiprocessing import Pool
import numpy as np, nibabel as nib
from scipy import ndimage as ndi

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'trillium', 'icx4', 'lib'))
from territory import to_four, TERRITORY  # noqa: E402

ICX, OUT = sys.argv[1], sys.argv[2]
NP = int(sys.argv[3]) if len(sys.argv) > 3 else 4
S26 = np.ones((3, 3, 3), bool)
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
SPLIT = {}
for s in ('train', 'val', 'test'):
    for x in open(os.path.join(ICX, f'{s}.txt')).read().split():
        SPLIT[int(x)] = s


def one(fn):
    n = int(fn.split('.')[0])
    img = nib.load(os.path.join(ICX, fn))
    icx = np.asarray(img.dataobj).astype(np.int64)
    z = img.header.get_zooms()[:3]
    four = to_four(icx, z)
    nz = np.argwhere(icx > 0)   # crop to the tree's box (+2 voxels): same result, far less work
    lo = np.maximum(nz.min(0) - 2, 0); hi = nz.max(0) + 3
    icx = icx[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]; four = four[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    r = {'case': 'c%04d' % (n - 1), 'icx_id': n, 'split': SPLIT.get(n), 'voxel_mm3': float(np.prod(z))}
    r['icx_present'] = [int(v) for v in np.unique(icx) if v]
    r['vox'] = {NAMES[k]: int((four == k).sum()) for k in NAMES}
    # share of each territory that came from side-branch ICX classes (not the trunk class itself)
    trunk = {1: 1, 2: 2, 3: 3, 4: 9}
    r['side_share'] = {NAMES[k]: (round(float(((four == k) & (icx != trunk[k])).sum()) / max(1, r['vox'][NAMES[k]]), 4))
                       for k in NAMES}
    # components per class
    comps = {}
    for k in NAMES:
        lab, m = ndi.label(four == k, S26)
        if m:
            sizes = np.bincount(lab.ravel())[1:]
            comps[NAMES[k]] = {'n_ge10': int((sizes >= 10).sum()), 'largest_share': round(float(sizes.max() / sizes.sum()), 4),
                               'second_vox': int(np.sort(sizes)[-2]) if m > 1 else 0}
    r['components'] = comps
    # whole-tree components (any vessel), left vs right
    lab, m = ndi.label(four > 0, S26)
    sizes = np.bincount(lab.ravel())[1:] if m else np.array([])
    r['tree_components_ge10'] = int((sizes >= 10).sum())
    # forbidden contacts
    contacts = {}
    for a, b in ((1, 4), (2, 4), (3, 4), (1, 1)):
        if a == b:
            continue
        da = ndi.binary_dilation(four == a, S26)
        contacts[f'{NAMES[a]}-{NAMES[b]}'] = int((da & (four == b)).sum())
    r['contacts'] = contacts
    # Other pieces: nearest-voxel rule vs what the piece touches
    other = icx == 14
    r['other_vox'] = int(other.sum())
    pieces = []
    if other.any():
        base = TERRITORY[np.clip(icx, 0, 14)]  # Other -> 0 here
        lab, m = ndi.label(other, S26)
        for i, sl in enumerate(ndi.find_objects(lab), 1):
            sl = tuple(slice(max(a.start - 1, 0), a.stop + 1) for a in sl)
            p = lab[sl] == i
            ring = ndi.binary_dilation(p, S26) & ~p
            touch = base[sl][ring]; touch = touch[touch > 0]
            assigned = np.bincount(four[sl][p], minlength=5)
            got = int(assigned.argmax())
            if touch.size:
                t = np.bincount(touch, minlength=5); parent = int(t.argmax())
            else:
                parent = 0
            pieces.append({'vox': int(p.sum()), 'assigned': NAMES.get(got, '-'), 'touches': NAMES.get(parent, 'none'),
                           'mixed_assignment': bool((assigned[1:] > 0).sum() > 1)})
    r['other_pieces'] = pieces
    return r


if __name__ == '__main__':
    files = sorted(f for f in os.listdir(ICX) if f.endswith('.coronary.nii.gz'))
    with Pool(NP) as p:
        rows = p.map(one, files, chunksize=4)
    json.dump(rows, open(OUT, 'w'))
    print('cases', len(rows))
