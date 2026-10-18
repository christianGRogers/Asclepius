"""Round 9: per-class census of ImageCAS-X collapsed to the four classes (D25), and an estimate of the four-class
inter-observer Dice from ImageCAS-X's published per-segment agreement (arXiv:2608.30404, Table 1).

For each of the 800 ImageCAS-X label maps: volume (mm^3) of each of the 14 classes, presence, and the volume of each
of the four classes after trillium/icx4/lib/territory.py's collapse (Other -> nearest LAD/LCx voxel). Writes
census.json (per case) and summary.json.

Four-class agreement estimate. For one case and a territory T made of segments s, two reads A and B:
  |A_T & B_T| >= sum_s |A_s & B_s|   and   |A_T| + |B_T| = sum_s (|A_s| + |B_s|)
so Dice_T >= sum_s w_s Dice_s with w_s = (|A_s|+|B_s|) / sum (volume weights): collapsing can only raise agreement
(a voxel the two readers call D1 and LAD is a disagreement in 14 classes and an agreement in four). Only per-segment
means are published, so the estimate uses mean volume shares from this census as w_s and the published mean Dice_s;
it is an approximate floor, not a per-case bound.
Only ImageCAS-X's train and val cases (train.txt + val.txt, 640) are read. The 160 test cases, and with them
the 80 sealed under A14, are never opened: the census must not inspect a held-out case.
Usage: icx4_census.py <icx_label_dir> <territory.py dir> <out_dir> [n_proc]"""
import json, os, sys, statistics
from multiprocessing import Pool
import numpy as np, nibabel as nib

ICX, TERR, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
NP = int(sys.argv[4]) if len(sys.argv) > 4 else 2
sys.path.insert(0, TERR)
from territory import to_four, TERRITORY  # noqa: E402

SEG = ['LM', 'LAD', 'LCx', 'D1', 'D2', 'OM1', 'OM2', 'IM', 'RCA', 'R-PDA', 'R-PLA', 'L-PDA', 'L-PLA', 'Other']
FOUR = ['LM', 'LAD', 'LCx', 'RCA']
# ImageCAS-X Table 1 inter-observer DSC (mean over scans where present), as quoted in the vault note
# "How well two annotators agree on per-branch coronary labels" and re-read by Foxtrot's literature check.
IO_DSC = {'LM': 91.9, 'LAD': 92.3, 'LCx': 84.8, 'RCA': 95.3, 'D1': 79.9, 'D2': 82.9, 'OM1': 74.1, 'OM2': 77.7,
          'IM': 80.6, 'R-PDA': 82.6, 'R-PLA': 83.6, 'L-PDA': 75.1, 'L-PLA': 70.9, 'Other': 81.3}


def one(f):
    im = nib.load(os.path.join(ICX, f))
    a = np.asarray(im.dataobj).astype(np.int64)
    z = im.header.get_zooms()[:3]
    vox = float(np.prod(z))
    cnt = np.bincount(a.ravel(), minlength=15)[:15]
    four = to_four(a, z)
    c4 = np.bincount(four.ravel(), minlength=5)[:5]
    # where did 'Other' go: LAD or LCx
    oth = a == 14
    o_lad = int(((four == 2) & oth).sum()); o_lcx = int(((four == 3) & oth).sum())
    return {'case': f.split('.')[0], 'zooms': [float(x) for x in z],
            'seg_mm3': {SEG[k - 1]: round(cnt[k] * vox, 1) for k in range(1, 15)},
            'four_mm3': {FOUR[k - 1]: round(c4[k] * vox, 1) for k in range(1, 5)},
            'other_to_LAD_mm3': round(o_lad * vox, 1), 'other_to_LCx_mm3': round(o_lcx * vox, 1)}


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    keep = set()
    for split in ('train', 'val'):
        keep |= set(open(os.path.join(ICX, f'{split}.txt')).read().split())
    test = set(open(os.path.join(ICX, 'test.txt')).read().split())
    assert not keep & test, 'train/val overlap the test split'
    files = sorted(f for f in os.listdir(ICX) if f.endswith('.coronary.nii.gz') and f.split('.')[0] in keep)
    print(f'census on {len(files)} train+val cases; {len(test)} test cases not opened', flush=True)
    cj = os.path.join(OUT, 'census.json')
    if os.environ.get('REUSE_CENSUS') and os.path.exists(cj):   # rebuild the summary from a finished per-case census
        rows = json.load(open(cj))
        assert {r['case'] for r in rows} == {f.split('.')[0] for f in files}, 'census.json does not match train+val'
    else:
        with Pool(NP) as p:
            rows = p.map(one, files, chunksize=4)
        json.dump(rows, open(cj, 'w'))
    n = len(rows)
    S = {'n_cases': n, 'presence': {}, 'median_mm3': {}, 'mean_mm3': {}}
    for s in SEG:
        v = [r['seg_mm3'][s] for r in rows]
        S['presence'][s] = int(sum(x > 0 for x in v))
        S['mean_mm3'][s] = round(statistics.mean(v), 1)
        S['median_mm3'][s] = round(statistics.median([x for x in v if x > 0]), 1) if any(v) else 0
    S['four'] = {}
    for k, c in enumerate(FOUR, 1):
        v = [r['four_mm3'][c] for r in rows]
        tot = statistics.mean(sum(r['four_mm3'].values()) for r in rows)
        S['four'][c] = {'present': int(sum(x > 0 for x in v)), 'mean_mm3': round(statistics.mean(v), 1),
                        'share_of_tree': round(statistics.mean(v) / tot, 4)}
    S['other_cases'] = int(sum(r['seg_mm3']['Other'] > 0 for r in rows))
    S['other_to_LAD_mm3_total'] = round(sum(r['other_to_LAD_mm3'] for r in rows), 1)
    S['other_to_LCx_mm3_total'] = round(sum(r['other_to_LCx_mm3'] for r in rows), 1)
    # four-class agreement estimate
    est = {}
    for k, c in enumerate(FOUR, 1):
        members = [s for i, s in enumerate(SEG, 1) if TERRITORY[i] == k]
        if c in ('LAD', 'LCx'):
            # Other's volume split as it was assigned
            pass
        w = {s: S['mean_mm3'][s] for s in members}
        if c == 'LAD':
            w['Other'] = S['other_to_LAD_mm3_total'] / n
        if c == 'LCx':
            w['Other'] = S['other_to_LCx_mm3_total'] / n
        tw = sum(w.values())
        est[c] = {'members': list(w), 'weights': {s: round(x / tw, 3) for s, x in w.items()},
                  'parent_only_dsc': IO_DSC[c],
                  'territory_dsc_floor_estimate': round(sum(w[s] / tw * IO_DSC[s] for s in w), 1)}
    S['four_class_interobserver_estimate'] = est
    json.dump(S, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, default=float)
    print(json.dumps(S, indent=1, default=float))
