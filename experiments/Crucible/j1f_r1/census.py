"""Janus 1-F round 1 (Crucible): what ImageCAS-X's 14 classes give 1-F on the 620 D45 training cases.

Per case, on the label file only (no CT):
  * voxels and mm^3 per ImageCAS-X class (1 LM, 2 LAD, 3 LCx, 4 D1, 5 D2, 6 OM1, 7 OM2, 8 IM, 9 RCA, 10 R-PDA,
    11 R-PLA, 12 L-PDA, 13 L-PLA, 14 Other);
  * "Other" pieces (26-connected, >= 10 voxels) and the family each touches: D (LAD, D1, D2) or OM (LCx, OM1, OM2, IM,
    L-PDA, L-PLA). A D-family Other piece is a 3rd-or-later diagonal (D3/D4): the only place D3 exists in ImageCAS-X;
  * calibre: the whole tree's skeleton (skimage), each skeleton voxel's distance to background in mm (EDT with the
    file's spacing) as its radius, grouped by class;
  * unnamed branches inside the trunk classes: skan branches of the whole-tree skeleton whose voxels are all one trunk
    class (LAD 2, LCx 3, RCA 9) and that end in a free endpoint (skan type 1), >= 5 mm. These are side branches drawn
    in ImageCAS-X's lumen but given the parent's name: septals and D4+ in LAD, SN/conus/RMA/RV branches in RCA, atrial
    and later marginal branches in LCx. The trunk's own distal end (and, for the RCA, its ostial stub) is one of them,
    so the summary subtracts the longest one per class (the raw counts are printed too).
Only cases in split.py's train620 are opened. Usage: census.py <icx_dir> <out.jsonl> [workers]"""
import json, os, sys
from multiprocessing import Pool
import numpy as np
import nibabel as nib
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
from skan import Skeleton, summarize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import split  # noqa: E402

D_FAM, OM_FAM, TRUNK = (2, 4, 5), (3, 6, 7, 8, 12, 13), (2, 3, 9)


def one(args):
    icx_dir, case = args
    f = os.path.join(icx_dir, '%d.coronary.nii.gz' % (int(case[1:]) + 1))
    im = nib.load(f)
    lab = np.asarray(im.dataobj).astype(np.uint8)
    sp = np.array(im.header.get_zooms()[:3], float)
    vox = np.bincount(lab.ravel(), minlength=15)[:15]
    out = {'case': case, 'spacing': sp.round(4).tolist(), 'voxels': vox.tolist(),
           'mm3': (vox * sp.prod()).round(2).tolist()}
    # skeleton, calibre and branches, on the tree's bounding box (+2)
    fg = lab > 0
    sl = ndi.find_objects(fg.astype(np.uint8))[0]
    sl = tuple(slice(max(s.start - 2, 0), s.stop + 2) for s in sl)
    sub, fgs = lab[sl], fg[sl]
    # Other pieces and their family
    pieces = []
    oth, n = ndi.label(sub == 14, structure=np.ones((3, 3, 3)))
    if n:
        sizes = np.bincount(oth.ravel())
        for k in range(1, n + 1):
            if sizes[k] < 10:
                continue
            m = oth == k
            ring = ndi.binary_dilation(m, np.ones((3, 3, 3))) & ~m
            touch = set(np.unique(sub[ring]).tolist()) - {0, 14}
            fam = ('D' if touch & set(D_FAM) else '') + ('OM' if touch & set(OM_FAM) else '') or \
                  ('RCA' if touch else 'none')
            pieces.append({'voxels': int(sizes[k]), 'touch': sorted(touch), 'family': fam})
    out['other_pieces'] = pieces
    edt = ndi.distance_transform_edt(fgs, sampling=sp)
    sk = skeletonize(fgs)
    rad = {}
    for c in range(1, 15):
        r = edt[sk & (sub == c)]
        if r.size:
            rad[c] = {'n': int(r.size), 'p10': float(np.percentile(r, 10)), 'p50': float(np.median(r)),
                      'p90': float(np.percentile(r, 90))}
    out['radius_mm'] = rad
    twigs = {c: [] for c in TRUNK}
    length = {c: 0.0 for c in range(1, 15)}
    try:
        S = Skeleton(sk, spacing=sp)
        df = summarize(S, separator='_')
        # per skeleton voxel: its path (branch) id; majority class and purity per path by bincount
        pid = np.asarray(S.path_label_image())[sk]
        cls = sub[sk].astype(np.int64)
        keep = (pid > 0) & (cls > 0)
        pid, cls = pid[keep] - 1, cls[keep]
        npath = len(df)
        tab = np.zeros((npath, 15), np.int64)
        np.add.at(tab, (pid, cls), 1)
        for i, row in enumerate(df.itertuples(index=False)):
            if i >= npath or not tab[i].sum():
                continue
            maj = int(tab[i].argmax())
            L = float(row.branch_distance)
            length[maj] += L
            if row.branch_type == 1 and maj in TRUNK and tab[i, maj] == tab[i].sum() and L >= 5.0:
                twigs[maj].append(round(L, 2))
    except Exception as e:  # a degenerate skeleton; recorded, not hidden
        out['skeleton_error'] = repr(e)[:200]
    out['twigs_mm'] = {str(c): sorted(v, reverse=True) for c, v in twigs.items()}
    out['length_mm'] = {str(c): round(v, 1) for c, v in length.items() if v}
    return out


if __name__ == '__main__':
    icx_dir, dest = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    cases = split.build(icx_dir)['train620']
    done = set()
    if os.path.exists(dest):
        done = {json.loads(l)['case'] for l in open(dest)}
    todo = [(icx_dir, c) for c in cases if c not in done]
    with Pool(workers) as p, open(dest, 'a') as fo:
        for i, r in enumerate(p.imap_unordered(one, todo)):
            fo.write(json.dumps(r) + '\n'); fo.flush()
            if i % 50 == 0:
                print(i, len(todo), flush=True)
