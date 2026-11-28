"""Janus 1-F round 4 (Atlas): a stand-in SegQueue14 export built from ImageCAS-X TRAINING labels only, to test
j1f2_freeze.py where no extended pool read can be read (the pool's reads are the lead's).

Each training case becomes one extended "read" (21 classes, `read.json` extended true, no ticks: D54) plus a second
read `__r2`, in SegQueue14's export layout (`<case>/segmentations/<class>.nii.gz`, `read.json`, `manifest.json`).
Stand-ins, from the scorer of record's stage-1 labels: D2 -> S1 (a LAD-side stage-2 class), OM2 -> SN (an SN off the
LCx), a PLB touching the RCA -> RMA. Every other branch keeps its name. Each child is drawn over its parent where its
one-voxel dilation meets the parent (D47 Q4; the parent stays whole, D39).
The second read: each branch piece is dropped with probability P_DROP (left in its parent, as an annotator who did not
separate it does; under D54 that branch is then absent) and each class grows by one voxel with probability P_GROW.
Mode `thief`: every first read also paints the 10 mm of LAD centreline nearest the S1 stand-in's origin as S1 (the
round-3 thief), so the L1r/K1r statistic must jump.
Sources: five fake ones by hash (StandIn-A..E). Names never collide with a pool name.
Usage: python make_standins.py <icx_seg_dir> <out_export> [normal|thief] [n_four_class]
"""
import hashlib, json, os, sys
import numpy as np, nibabel as nb
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1f2_freeze as F  # noqa: E402  (pins the scorer of record)
S = F.S
SQ = F.SQ
P_DROP, P_GROW, SEED = 0.10, 0.30, 4
TRAIN_PIN = '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'


def stand_in(lab13, sp):
    """stage-1 13-class labels -> {SegQueue name: mask} with the stand-ins."""
    out = {n: np.zeros(lab13.shape, bool) for n in SQ.ALL_NAMES}
    direct = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA', 5: 'D1', 6: 'S1', 7: 'D3', 8: 'OM1', 9: 'SN', 10: 'Ramus',
              11: 'PDA'}
    for v, n in direct.items():
        out[n] |= lab13 == v
    comp, nc = ndi.label(lab13 == 12, S.S26)
    rca = ndi.binary_dilation(lab13 == 4, S.S26)
    for i in range(1, nc + 1):
        p = comp == i
        out['RMA' if (p & rca).any() else 'PLB'] |= p
    for b, parents in F.OWN_PARENTS.items():                       # child drawn over its own parent (D47 Q4)
        if not out[b].any():
            continue
        ring = ndi.binary_dilation(out[b], S.S26)
        for p in parents:
            out[b] |= ring & out[p]
    return out


def second_read(masks, rng):
    m = {k: v.copy() for k, v in masks.items()}
    for b, parents in F.OWN_PARENTS.items():
        if not m[b].any():
            continue
        comp, nc = ndi.label(m[b], S.S26)
        for i in range(1, nc + 1):
            if rng.random() < P_DROP:
                p = comp == i
                m[b] &= ~p
                host = max(parents, key=lambda q: int((ndi.binary_dilation(p, S.S26) & m[q]).sum()))
                m[host] |= p
    for k in list(m):
        if m[k].any() and rng.random() < P_GROW:
            m[k] = ndi.binary_dilation(m[k], S.S26)
    return m


def thief(masks, sp):
    """Paint the 10 mm of LAD centreline nearest the S1 stand-in's origin as S1 (over the LAD)."""
    if not masks['S1'].any() or not masks['LAD'].any():
        return masks
    skel = S._skeleton(masks['LAD'])
    pts = np.argwhere(skel)
    s1 = np.argwhere(masks['S1'])
    d = np.min(np.linalg.norm((pts[:, None, :] - s1[None, ::max(1, len(s1) // 200), :]) * sp, axis=2), axis=1)
    o = pts[np.argmin(d)]
    near = pts[np.linalg.norm((pts - o) * sp, axis=1) <= 5.0]
    tube = np.zeros_like(skel)
    tube[tuple(near.T)] = True
    tube = ndi.binary_dilation(tube, S.S26) & masks['LAD']
    masks = dict(masks)
    masks['S1'] = masks['S1'] | tube
    return masks


def write_read(root, name, masks, affine, extended=True):
    d = os.path.join(root, name, 'segmentations')
    os.makedirs(d, exist_ok=True)
    names = SQ.ALL_NAMES if extended else SQ.NAMES
    if not extended:
        masks = {k: v for k, v in zip(SQ.NAMES, SQ.collapse_to_four(np.stack([masks[n] for n in SQ.ALL_NAMES]),
                                                                       SQ.ALL_NAMES))}
    for n in names:
        nb.save(nb.Nifti1Image(masks[n].astype(np.uint8), affine), os.path.join(d, n.replace(' ', '_') + '.nii.gz'))
    json.dump({'classes': list(names), 'extended': extended, 'completeGroups': None, 'written': 'read'},
              open(os.path.join(root, name, 'read.json'), 'w'), indent=1)


def main(src, out, mode='normal', n4=5):
    rng = np.random.default_rng(SEED)
    files = sorted(f for f in os.listdir(src) if f.endswith('.nii.gz'))
    split = json.load(open(os.path.join(F._ROOT, 'experiments/Atlas/j1l/split_j1l.json')))
    train = sorted(split['train620'])
    assert hashlib.sha256('\n'.join(train).encode()).hexdigest() == TRAIN_PIN
    train = set(train)
    os.makedirs(out, exist_ok=True)
    done = []
    for f in files:
        cid = 'c%04d' % (int(f.split('.')[0]) - 1)
        assert cid in train, cid                                           # training labels only
        im = nb.load(os.path.join(src, f))
        sp = np.array(im.header.get_zooms()[:3], float)
        raw = np.asarray(im.dataobj).astype(np.uint8)
        raw = raw[F._crop(raw, pad=8)]                                     # speed; the freeze reads spacing only
        lab13, _ = S.stage1_labels(raw, sp)
        lab13 = np.where(lab13 == S.IGNORE, 0, lab13)
        masks = stand_in(lab13, sp)
        src_name = 'StandIn-' + 'ABCDE'[int(hashlib.sha256(cid.encode()).hexdigest(), 16) % 5]
        name = f'{src_name}__{cid}'
        first = thief(masks, sp) if mode == 'thief' else masks
        ext = len(done) >= n4
        write_read(out, name, first, im.affine, extended=ext)
        write_read(out, name + '__r2', second_read(masks, rng), im.affine, extended=ext)
        done.append(name)
        print(name, 'extended' if ext else 'four-class', flush=True)
    json.dump({'source': {'kind': 'standin', 'classes': 'read', 'replicas': 'all',
                          'pool_seal': {'mode': 'exclude'}}, 'cases': done},
              open(os.path.join(out, 'manifest.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'normal',
         int(sys.argv[4]) if len(sys.argv) > 4 else 5)
