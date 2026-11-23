"""Janus 1-F round 3 (Foxtrot): one CPU pass over D45's 620 TRAINING labels with the amended scorer (§5 items 1, 2).

Per case (ImageCAS-X label, full volume, no CT):
  * converters (F-A18): Atlas's `stage1_labels` (inside the scorer) vs Foxtrot's `labels_r2.map13` (F0-r2's converter,
    Delta's map + D47 (A) + F-A3's 255): voxel disagreements, and the 'Other' counts of each;
  * collapse (F-A17): the scorer's `collapse4` (SegQueue's collapse_to_four, imported) against icx4's
    `territory.to_four` (D25), on every voxel outside 255, with the mismatches split by ImageCAS-X class; and the
    contact statistics (components, fallbacks);
  * pieces (F-A16): every reference piece by the amended scorer's `pieces_of` (vox, length mm), to compare with the
    piece distribution F-A15's lines were simulated on (Atlas's `census_r2.jsonl`).
Reads only the 620 (pin asserted). Usage: python pass_r3.py <icx620_dir> <split_j1l.json> <out.jsonl> [n_proc]"""
import hashlib, json, os, sys
from multiprocessing import Pool
import nibabel as nib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '../j1f_r2'), os.path.join(HERE, '../../../trillium/icx4/lib')]
import j1f_scorer as S  # noqa: E402
import labels_r2 as L  # noqa: E402
import territory  # noqa: E402


def one(path):
    c = 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1)
    im = nib.load(path)
    icx = np.asarray(im.dataobj).astype(np.uint8)
    icx = icx[L.crop(icx, 12)]       # the tree's box + 12 voxels: every rule here is local (<= 12 voxels) or geodesic
    z = np.array(im.header.get_zooms()[:3], float)
    lab, info = S.stage1_labels(icx, z)
    labF, infoF = L.map13(icx, z)
    four, st = S.collapse4(lab, z)
    ref4 = territory.to_four(icx, z)
    valid = lab != S.IGNORE
    mm = (four != ref4) & valid
    pcs = S.pieces_of(lab, z)
    return {'case': c, 'other_atlas': info, 'other_foxtrot': infoF,
            'converter_diff_vox': int((lab != labF).sum()),
            'collapse_mismatch_vox': int(mm.sum()),
            'collapse_mismatch_by_icx': {int(k): int((mm & (icx == k)).sum()) for k in np.unique(icx[mm])},
            'contact': {k: v for k, v in st.items()},
            'ignore_vox': int((~valid).sum()),
            'pieces': {S.NAMES[k]: [{'vox': p['vox'], 'len': round(p['length_mm'], 2)} for p in v]
                       for k, v in pcs.items()}}


def main(d, split, out, npr=4):
    train = sorted(json.load(open(split))['train620'])
    assert hashlib.sha256('\n'.join(train).encode()).hexdigest() == \
        '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
    paths = [os.path.join(d, f'{int(c[1:]) + 1}.coronary.nii.gz') for c in train]
    done = {json.loads(l)['case'] for l in open(out)} if os.path.exists(out) else set()
    todo = [p for p in paths if 'c%04d' % (int(os.path.basename(p).split('.')[0]) - 1) not in done]
    with Pool(npr, maxtasksperchild=10) as pool, open(out, 'a') as f:
        for i, r in enumerate(pool.imap_unordered(one, todo)):
            f.write(json.dumps(r) + '\n'); f.flush()
            if i % 50 == 0:
                print(i, len(todo), flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], a[1], a[2], int(a[3]) if len(a) > 3 else 4)
