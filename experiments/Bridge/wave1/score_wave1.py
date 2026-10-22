"""Wave-1 per-volume scores (Round 9 A31), on **non-sealed** pool reads only. CPU.

For every exported pool volume with team reads, this writes one JSON line with per-class tF1 @ 1.5 mm
(pinned ``segtrain.tf1``, A1c) for three comparisons:

* ``inter``: read A vs read B, the mean of both directions (A as reference, then B), as ``segtrain.reads``
  does for A10;
* ``model``: the model's prediction scored against each read, averaged over the reads (A10's left side);
* ``seed``:  the TotalSegmentator seed against each read (A31.2, Crucible P2). The seed is binary, and D26 starts
  every class as a full copy of it, so the seed is first **named with the read's own classes** (each seed voxel
  takes the class of the nearest read voxel, in mm). Naming then agrees by construction, and the score measures
  only how much of the read's **extent** is the seed's: 1.0 means the read is the seed with nothing added or
  removed. It is symmetric (both directions), like ``inter``, and averaged over the reads.

A1: the ostium comes from a TotalSegmentator aorta (``--aorta``). Without one, a row is ``provisional`` and the
report leaves it out of every decisive number (A1a). A1b: classes on a tree with a flagged ostium (on the
reference side of a comparison) are listed per comparison, and the report leaves them out.

Refusal (D27, A30): before any file of a volume is opened, its name is checked against the seal, the reserved
extension patients and the pool list (``common.Seal``). Default: an error. ``--skip-sealed``: skip and count.

Layout (``segqueue14-export --replicas all``): ``<reads>/<volume>[__rK]/segmentations/{LM,LAD,LCx,RCA}.nii.gz``.
Seeds: ``<seeds>/<volume>__totalseg-coronary.nii.gz`` (``SegQueue/seeds-totalseg``) or ``<seeds>/<volume>.nii.gz``.
Predictions: ``<pred>/<volume>.nii.gz`` (labels 1-4). Aortas: ``<aorta>/<volume stem>_aorta.nii.gz`` or
``<aorta>/<volume>.nii.gz``. Everything is brought onto the first read's grid (axis flips/permutations only).

Usage: score_wave1.py --reads R --out per_volume.jsonl [--seeds S] [--pred P] [--aorta A] [--nproc N]
       [--skip-sealed] [--seal FILE]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from multiprocessing import Pool

import nibabel as nib
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

sys.path.insert(0, os.path.join(C.REPO, 'src'))
from segtrain import tf1 as T  # noqa: E402
from segtrain.convert import align_to_reference  # noqa: E402

SEGMENTS = {'LM': 1, 'LAD': 2, 'LCx': 3, 'RCA': 4}
MARGIN_MM = 8.0   # crop margin: more than the 5 mm aorta contact and the tolerance dilation
A = None


def load_read(seg_dir):
    lab, img0 = None, None
    for name, val in SEGMENTS.items():
        p = os.path.join(seg_dir, name + '.nii.gz')
        if not os.path.exists(p):
            continue
        img = nib.load(p)
        v = np.asarray(img.dataobj) > 0.5
        if lab is None:
            lab, img0 = np.zeros(v.shape, np.uint8), img
        lab[v & (lab == 0)] = val
    return lab, img0


def on_grid(path, ref_img, what):
    data, problem = align_to_reference(nib.load(path), ref_img)
    if data is None:
        raise ValueError(f'{what} {path}: not on the read grid ({problem})')
    return np.asarray(data)


def find(d, volume, patterns):
    if not d:
        return None
    stem = volume[:-len('.nii.gz')]
    for p in patterns:
        f = os.path.join(d, p.format(stem=stem, volume=volume))
        if os.path.exists(f):
            return f
    return None


def name_seed(seed_bin, read, sp):
    """The seed's components that touch the read (26-connectivity), each voxel named with the class of the nearest
    read voxel (mm). Seed components the reader deleted whole (a vein, a stray blob) are left out: removing a false
    component is not a sign of independence, and A31.2 asks about the extent of the vessels that were kept.
    Empty read -> empty named seed."""
    from scipy import ndimage
    out = np.zeros(read.shape, np.uint8)
    src = np.argwhere(read > 0)
    lab, _ = ndimage.label(seed_bin, structure=np.ones((3, 3, 3), bool))
    keep = np.unique(lab[(read > 0) & (lab > 0)])
    pts = np.argwhere(np.isin(lab, keep[keep > 0]))
    if len(src) == 0 or len(pts) == 0:
        return out
    _, i = cKDTree(src * sp).query(pts * sp)
    out[tuple(pts.T)] = read[tuple(src[i].T)]
    return out


def flagged_classes(ref, rep):
    out = set()
    if rep.flagged:
        comp = T.components(ref > 0)[0]
        for o in rep.flagged:
            cls = {int(x) for x in np.unique(ref[comp == o.tree]) if x}
            if o.side == 'left':
                cls &= {1, 2, 3}
            elif o.side == 'right':
                cls &= {4}
            out |= cls
    return out


def one_way(ref, pred, sp, aorta):
    rep = T.find_ostia(ref, sp, aorta=aorta) if aorta is not None else T.find_ostia(ref, sp)
    t = T.tree_f1(ref, pred, sp, ostia=rep)
    per = {int(c): float(v) for c, v in t.per_class.items() if np.isfinite(v)}
    return per, flagged_classes(ref, rep), bool(t.provisional)


def pair(a, b, sp, aorta, symmetric=True):
    """Per-class tF1 of b against reference a (and, if symmetric, the mean with a against b)."""
    ways = [one_way(a, b, sp, aorta)] + ([one_way(b, a, sp, aorta)] if symmetric else [])
    per = {}
    for c in C.CLASSES:
        v = [w[0][c] for w in ways if c in w[0]]
        if v:
            per[c] = float(np.mean(v))
    flags = set().union(*[w[1] for w in ways])
    return per, flags, any(w[2] for w in ways)


def mean_over(results):
    per = {}
    for c in C.CLASSES:
        v = [r[0][c] for r in results if c in r[0]]
        if v:
            per[c] = float(np.mean(v))
    return per, set().union(*[r[1] for r in results]) if results else set(), any(r[2] for r in results)


def crop_box(masks, sp):
    m = np.zeros(masks[0].shape, bool)
    for x in masks:
        if x is not None:
            m |= x > 0
    if not m.any():
        return tuple(slice(None) for _ in m.shape)
    idx = np.argwhere(m)
    pad = np.ceil(MARGIN_MM / np.asarray(sp)).astype(int)
    lo = np.maximum(idx.min(0) - pad, 0)
    hi = np.minimum(idx.max(0) + pad + 1, m.shape)
    return tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))


def as_names(d):
    return {C.CLASSES[c]: round(v, 6) for c, v in d.items()}


def score_volume(item):
    volume, dirs = item
    row = {'volume': volume, 'patient': C.corrected_key(volume), 'source': C.source_of(volume),
           'reads': [os.path.basename(d) for d in dirs]}
    try:
        reads, ref_img = [], None
        for d in dirs:
            lab, img = load_read(os.path.join(d, 'segmentations'))
            if lab is None:
                continue
            if ref_img is None:
                ref_img = img
                reads.append(lab)
            else:
                reads.append(_read_on_grid(d, ref_img))
        if not reads:
            row['error'] = 'no readable read'
            return row
        sp = np.asarray(ref_img.header.get_zooms()[:3], float)
        sf = find(A.seeds, volume, ('{stem}__totalseg-coronary.nii.gz', '{volume}'))
        pf = find(A.pred, volume, ('{volume}',))
        af = find(A.aorta, volume, ('{stem}_aorta.nii.gz', '{volume}'))
        seed = on_grid(sf, ref_img, 'seed') > 0 if sf else None
        pred = on_grid(pf, ref_img, 'prediction').astype(np.uint8) if pf else None
        aorta = on_grid(af, ref_img, 'aorta') > 0 if af else None
        sl = crop_box(reads + [seed, pred], sp)
        reads = [r[sl] for r in reads]
        seed = seed[sl] if seed is not None else None
        pred = pred[sl] if pred is not None else None
        aorta = aorta[sl] if aorta is not None else None
        row['n_reads'] = len(reads)
        row['provisional'] = aorta is None
        row['classes_in_reads'] = [sorted(C.CLASSES[int(c)] for c in np.unique(r) if c) for r in reads]
        if len(reads) >= 2:
            per, fl, prov = pair(reads[0], reads[1], sp, aorta)
            row['inter'] = {'per_class': as_names(per), 'flagged': sorted(C.CLASSES[c] for c in fl)}
        if pred is not None:
            per, fl, prov = mean_over([pair(r, pred, sp, aorta, symmetric=False) for r in reads])
            row['model'] = {'per_class': as_names(per), 'flagged': sorted(C.CLASSES[c] for c in fl)}
        if seed is not None:
            per, fl, prov = mean_over([pair(r, name_seed(seed, r, sp), sp, aorta) for r in reads])
            row['seed'] = {'per_class': as_names(per), 'flagged': sorted(C.CLASSES[c] for c in fl)}
            # report only: how far each read moved from the seed (voxels), D26's cut-down workflow
            row['seed_edit'] = [{'added_share_of_read': round(float(((r > 0) & ~seed).sum() / max(1, (r > 0).sum())), 4),
                                 'removed_share_of_seed': round(float((seed & ~(r > 0)).sum() / max(1, seed.sum())), 4)}
                                for r in reads]
    except Exception as e:   # one bad volume must not stop the wave; the report counts errors
        row['error'] = f'{type(e).__name__}: {e}'
    return row


def _read_on_grid(d, ref_img):
    lab = None
    for name, val in SEGMENTS.items():
        p = os.path.join(d, 'segmentations', name + '.nii.gz')
        if not os.path.exists(p):
            continue
        v = on_grid(p, ref_img, 'read') > 0.5
        if lab is None:
            lab = np.zeros(v.shape, np.uint8)
        lab[v & (lab == 0)] = val
    return lab


def collect(root, seal, skip):
    groups, refused = {}, []
    for entry in sorted(os.listdir(root)):
        d = os.path.join(root, entry)
        if not os.path.isdir(d):
            continue
        vol = C.volume_name(entry)
        why = seal.reason(vol)
        if why:
            refused.append({'entry': entry, 'reason': why})
            continue
        groups.setdefault(vol, []).append(d)
    if refused and not skip:
        raise C.SealedVolumeError(f'{len(refused)} export folders are sealed, reserved or unknown, e.g. '
                                  f'{refused[0]}; pass --skip-sealed to skip and count them (nothing was opened)')
    return groups, refused


def main(argv=None):
    global A
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--reads', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--seeds')
    ap.add_argument('--pred')
    ap.add_argument('--aorta')
    ap.add_argument('--nproc', type=int, default=1)
    ap.add_argument('--skip-sealed', action='store_true')
    ap.add_argument('--seal', help='seal file (default: canonical, else the Round 9 proposal)')
    ap.add_argument('--pool-list', default=C.POOL_LIST)
    A = ap.parse_args(argv)
    h = C.check_tf1_pin()
    seal = C.Seal(A.seal, A.pool_list)
    groups, refused = collect(A.reads, seal, A.skip_sealed)
    done = set()
    if os.path.exists(A.out):
        done = {json.loads(l)['volume'] for l in open(A.out) if l.strip()}
    todo = [(v, d) for v, d in sorted(groups.items()) if v not in done]
    with open(A.out, 'a') as f:
        if A.nproc > 1:
            with Pool(A.nproc) as p:
                for row in p.imap_unordered(score_volume, todo):
                    f.write(json.dumps(row) + '\n'); f.flush()
        else:
            for it in todo:
                f.write(json.dumps(score_volume(it)) + '\n'); f.flush()
    meta = {'tf1_sha256': h, 'seal': os.path.relpath(seal.path, C.REPO), 'seal_sha256': C.sha256(seal.path),
            'volumes_scored': len(groups), 'refused': len(refused),
            'refused_by_reason': {r: sum(x['reason'] == r for x in refused) for r in {x['reason'] for x in refused}}}
    json.dump(meta, open(A.out + '.meta.json', 'w'), indent=1)
    print(json.dumps(meta))
    return 0


if __name__ == '__main__':
    sys.exit(main())
