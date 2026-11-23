"""Crucible, Janus 1-L round 3, §5 item 3: what S needs if Job 0 sets the 0.45 mm trigger (L-A23). CPU only.

Two modes.

plans   Derive the 0.45 mm configuration from Janus 0's plans (the file Step T copies), without re-planning:
          a new configuration `3d_fullres_045` that `inherits_from` 3d_fullres (nnU-Net 2.8.1 plans_handler l. 237)
          and changes only `spacing` -> [0.45]*3, `data_identifier` (so preprocessing cannot overwrite the 0.5 mm
          folder) and `median_image_size_in_voxels` (informational, scaled by 0.5/0.45). Patch 256^3, batch 2,
          network, normalisation and everything else are inherited, so S differs from Janus 0's recipe only in the
          grid. Writes the new plans file and prints its sha256.
            python s045.py plans --in plans.json --out plans.json   (in place is fine: 3d_fullres is untouched)

view    The 115 mm view check (Bridge v2 §6). At 0.45 mm a 256^3 patch spans 115.2 mm instead of 128 mm. Per
        training case (the 620 ONLY; any other id is refused), from its label (`labelsTr/<id>.nii.gz` of dataset
        718, written by `prepare`), it computes:
          extent    the tree's bounding-box size per axis, in mm;
          cover(v)  the largest share of the tree's voxels that one axis-aligned v-mm cube can hold (summed-area
                    table on a 2 mm occupancy grid), at v = 128 and v = 115.2.
        A tree larger than the patch is normal at both spacings (sliding-window inference tiles it). What changes is
        how much of the tree, and of the ostium-to-branch context, one training patch can see. The pre-registered
        reading, fixed before the check runs:
          PASS  median cover(115.2) >= median cover(128) - 0.05, AND 10th percentile cover(115.2) >= that at 128 - 0.08;
          FAIL  otherwise. Then S is 0.5 mm (its warm-start question only), and the 0.45 mm question goes to the
                round after the verdict with the view as an explicit second change (a 288^3 patch keeps 129.6 mm
                but costs about 1.42x activation memory, which a 2-batch 60G plan does not have on an 80 GB H100).
            python s045.py view --labels $nnUNet_raw/Dataset718_Janus1L/labelsTr --np 8 --out view_check.json
        Prints the summary only (no per-case row leaves Trillium).

Cost (from Trillium's 181 s/epoch at 256^3, batch 2): the iteration cost depends on the patch, not the spacing, so
1000 epochs are ~50.3 h, as at 0.5 mm. The volumes have (0.5/0.45)^3 = 1.37x the voxels, so preprocessing (~1 -> ~1.4
GPU-node-h, CPU-bound) and sliding-window inference (~1.37x patches) grow. Total ~= 55 GPU-h (three chained jobs),
inside L-A25's 55-60.

  python s045.py --selftest
"""
import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
NEW = '3d_fullres_045'
VIEWS = (128.0, 115.2)
CELL = 2.0


def derive(plans, s=0.45):
    p = copy.deepcopy(plans)
    base = p['configurations']['3d_fullres']
    if NEW in p['configurations']:
        raise SystemExit(f'[s045] {NEW} already present')
    old = base['spacing']
    p['configurations'][NEW] = {
        'inherits_from': '3d_fullres',
        'data_identifier': f"{p['plans_name']}_{NEW}",
        'spacing': [s, s, s],
        'median_image_size_in_voxels': [int(round(m * o / s)) for m, o in
                                        zip(base['median_image_size_in_voxels'], old)],
    }
    return p


def check_derived(old, new):
    """Everything but the new block is unchanged; the new block changes only the three keys."""
    a = copy.deepcopy(new); blk = a['configurations'].pop(NEW)
    assert a == old, 'plans changed outside the new configuration'
    assert set(blk) == {'inherits_from', 'data_identifier', 'spacing', 'median_image_size_in_voxels'}, blk
    assert blk['data_identifier'] != old['configurations']['3d_fullres']['data_identifier']
    return True


def cover(mask, sp, view):
    """Largest share of mask voxels inside one axis-aligned view-mm cube (2 mm cells, summed-area table)."""
    idx = np.argwhere(mask)
    if len(idx) == 0:
        return float('nan'), [0.0, 0.0, 0.0]
    mm = idx * np.asarray(sp)
    lo = mm.min(0)
    ext = (mm.max(0) - lo + np.asarray(sp)).tolist()
    cells = np.floor((mm - lo) / CELL).astype(int)
    shape = cells.max(0) + 1
    occ = np.zeros(shape, float)
    np.add.at(occ, tuple(cells.T), 1.0)
    w = int(round(view / CELL))
    S = np.zeros(tuple(s + 1 for s in shape))
    S[1:, 1:, 1:] = occ.cumsum(0).cumsum(1).cumsum(2)
    wx, wy, wz = (min(w, s) for s in shape)
    tot = (S[wx:, wy:, wz:] - S[:-wx, wy:, wz:] - S[wx:, :-wy, wz:] - S[wx:, wy:, :-wz]
           + S[:-wx, :-wy, wz:] + S[:-wx, wy:, :-wz] + S[wx:, :-wy, :-wz] - S[:-wx, :-wy, :-wz])
    return float(tot.max() / len(idx)), ext


def one(path):
    import nibabel as nib
    img = nib.load(path)
    m = np.asarray(img.dataobj) > 0
    sp = img.header.get_zooms()[:3]
    out = {f'{v:g}': cover(m, sp, v)[0] for v in VIEWS}
    out['extent_mm'] = cover(m, sp, VIEWS[0])[1]
    return out


def read_rule(rows):
    c128 = np.array([r['128'] for r in rows]); c115 = np.array([r['115.2'] for r in rows])
    med = (float(np.median(c128)), float(np.median(c115)))
    p10 = (float(np.percentile(c128, 10)), float(np.percentile(c115, 10)))
    passed = med[1] >= med[0] - 0.05 and p10[1] >= p10[0] - 0.08
    ext = np.array([r['extent_mm'] for r in rows])
    return dict(n=len(rows), median_cover_128=round(med[0], 4), median_cover_115=round(med[1], 4),
                p10_cover_128=round(p10[0], 4), p10_cover_115=round(p10[1], 4),
                median_extent_mm=np.round(np.median(ext, 0), 1).tolist(),
                share_cases_any_axis_over_128=round(float((ext.max(1) > 128).mean()), 3),
                share_cases_any_axis_over_115=round(float((ext.max(1) > 115.2).mean()), 3),
                share_cover_below_095_128=round(float((c128 < 0.95).mean()), 3),
                share_cover_below_095_115=round(float((c115 < 0.95).mean()), 3),
                min_cover_128=round(float(c128.min()), 4), min_cover_115=round(float(c115.min()), 4),
                mean_cover_128=round(float(c128.mean()), 4), mean_cover_115=round(float(c115.mean()), 4),
                view_check='PASS' if passed else 'FAIL')


def train620():
    return set(json.load(open(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))['train620'])


def selftest():
    sp = (0.5, 0.5, 0.5)
    m = np.zeros((300, 300, 300), bool)
    m[10:290, 150, 150] = True                    # a 140 mm straight vessel
    c128, _ = cover(m, sp, 128.0); c115, _ = cover(m, sp, 115.2)
    assert abs(c128 - 128 / 140) < 0.03 and abs(c115 - 115.2 / 140) < 0.03, (c128, c115)
    small = np.zeros((200, 200, 200), bool); small[50:150, 50:150, 100] = True   # a 50 mm patch: fits either view
    assert cover(small, sp, 115.2)[0] == 1.0
    rows = [{'128': 0.9, '115.2': 0.87, 'extent_mm': [100, 110, 120]}] * 10
    assert read_rule(rows)['view_check'] == 'PASS'
    rows = [{'128': 0.9, '115.2': 0.80, 'extent_mm': [100, 110, 140]}] * 10
    assert read_rule(rows)['view_check'] == 'FAIL'
    plans = {'plans_name': 'nnUNetResEncUNetPlans_60G_iso05', 'dataset_name': 'Dataset715_ICX4',
             'configurations': {'3d_fullres': {'spacing': [0.5, 0.5, 0.5], 'patch_size': [256, 256, 256],
                                               'batch_size': 2, 'median_image_size_in_voxels': [400, 400, 400],
                                               'data_identifier': 'nnUNetResEncUNetPlans_60G_iso05_3d_fullres'}}}
    new = derive(plans)
    assert check_derived(plans, new) and new['configurations'][NEW]['median_image_size_in_voxels'] == [444] * 3
    bad = copy.deepcopy(new); bad['configurations']['3d_fullres']['batch_size'] = 1
    try:
        check_derived(plans, bad); raise RuntimeError('a changed 3d_fullres was not caught')
    except AssertionError:
        pass
    with tempfile.TemporaryDirectory() as W:
        import nibabel as nib
        nib.save(nib.Nifti1Image(np.zeros((4, 4, 4), np.uint8), np.eye(4)), os.path.join(W, 'c0068.nii.gz'))
        try:
            run_view(W, 1); raise RuntimeError('a locked-100 id was not refused')
        except SystemExit as e:
            assert 'REFUSING' in str(e)
    print(f'[s045] self-test passed: 140 mm vessel cover {c128:.3f} at 128 mm, {c115:.3f} at 115.2 mm; rule PASS/FAIL; '
          'derived plans change only the new block; a locked-100 id refused')


def run_view(labels, n):
    files = sorted(f for f in os.listdir(labels) if f.endswith('.nii.gz'))
    ids = [f[:-7] for f in files]
    allowed = train620()
    bad = [i for i in ids if i not in allowed]
    # dataset 718's labelsTr also holds the locked 100: they are skipped, never opened; anything else is refused
    locked = set(json.load(open(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))['locked100'])
    if [i for i in bad if i not in locked] or (bad and not [i for i in ids if i in allowed]):
        sys.exit(f'[s045] REFUSING: ids outside the 620: {bad[:3]}')
    use = [os.path.join(labels, f) for f, i in zip(files, ids) if i in allowed]
    if len(use) != 620:
        sys.exit(f'[s045] REFUSING: {len(use)} of the 620 labels found')
    with Pool(n) as p:
        return p.map(one, use, chunksize=4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', nargs='?'); ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--in', dest='inp'); ap.add_argument('--out'); ap.add_argument('--labels')
    ap.add_argument('--np', type=int, default=8)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.mode == 'plans':
        old = json.load(open(a.inp)); new = derive(old); check_derived(old, new)
        s = json.dumps(new, indent=4)
        open(a.out, 'w').write(s)
        print('[s045] wrote', a.out, 'sha256', hashlib.sha256(s.encode()).hexdigest())
    elif a.mode == 'view':
        res = read_rule(run_view(a.labels, a.np))
        json.dump(res, open(a.out, 'w'), indent=1)
        print(json.dumps(res, indent=1))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
