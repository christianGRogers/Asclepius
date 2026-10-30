#!/usr/bin/env python3
"""Job M0, step 3 (Fir login node, CPU): Kilo's layer geometry on TotalSegmentator `heartchambers_highres` output.

For each <name>/ folder of TotalSegmentator masks (heart_myocardium, heart_ventricle_left, heart_ventricle_right,
heart_atrium_left, aorta) and the CT it came from, writes one line of numbers: native spacing, LV cavity and
myocardium median HU, myocardium volume, wall thickness p10/p50/p90 (mm), voxels across the wall, Laplace-vs-distance
third agreement and the per-segment median thickness. Numbers only: no image, no mask, no identifier beyond the
pool volume name leaves Fir.

    python3 m0_geometry.py --masks DIR --cts DIR --out OUT.jsonl [--np 8]
"""
import argparse, json, os, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np, nibabel as nib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from layers import laplace_depth, distance_depth, thirds, aha17  # noqa: E402

KEYS = ('heart_myocardium', 'heart_ventricle_left', 'heart_ventricle_right', 'heart_atrium_left', 'aorta')


def one(a):
    mdir, ct = a
    try:
        img = nib.load(ct); sp = np.array(img.header.get_zooms()[:3], float)
        L = {k: np.asanyarray(nib.load(os.path.join(mdir, f'{k}.nii.gz')).dataobj) > 0 for k in KEYS}
        myo, cav, rv, la, ao = (L[k] for k in KEYS)
        if myo.sum() < 1000 or cav.sum() < 1000:
            return {'name': os.path.basename(mdir), 'skip': 'no LV'}
        box = np.argwhere(myo | cav); lo = np.maximum(box.min(0) - 8, 0); hi = box.max(0) + 9
        sl = tuple(slice(x, y) for x, y in zip(lo, hi))
        myo, cav, rv, la, ao = (m[sl] for m in (myo, cav, rv, la, ao))
        aff = img.affine.copy(); aff[:3, 3] = aff[:3, :3] @ lo + aff[:3, 3]
        hu = np.asanyarray(img.dataobj)[sl].astype(np.float32)
        nf = la | ao
        t, _ = laplace_depth(myo, cav, nf)
        td, th = distance_depth(myo, cav, nf, sp)
        seg, info = aha17(myo, cav, rv, la, aff)
        tr = thirds(t)
        return {'name': os.path.basename(mdir), 'spacing': sp.tolist(),
                'lv_cavity_HU_median': float(np.median(hu[cav])), 'myo_HU_median': float(np.median(hu[myo])),
                'myo_ml': float(myo.sum() * np.prod(sp) / 1000),
                'thick_mm_p10_50_90': np.nanpercentile(th[myo], [10, 50, 90]).tolist(),
                'vox_across_wall_median': float(np.nanmedian(th[myo]) / sp.mean()),
                'laplace_vs_distance_same_third': float((tr[myo] == thirds(td)[myo]).mean()),
                'cavity_length_mm': info['cavity_length_mm'],
                'seg_thick_mm': {int(s): float(np.nanmedian(th[myo & (seg == s)])) for s in range(1, 18)
                                 if (myo & (seg == s)).sum() > 20}}
    except Exception as e:  # noqa: BLE001 - report and go on
        return {'name': os.path.basename(mdir), 'error': repr(e)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--masks', required=True); ap.add_argument('--cts', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--np', type=int, default=8)
    a = ap.parse_args()
    jobs = [(os.path.join(a.masks, d), os.path.join(a.cts, d + '.nii.gz')) for d in sorted(os.listdir(a.masks))
            if os.path.exists(os.path.join(a.cts, d + '.nii.gz'))]
    with ProcessPoolExecutor(a.np) as ex, open(a.out, 'w') as f:
        for r in ex.map(one, jobs):
            f.write(json.dumps(r) + '\n')
    rows = [json.loads(x) for x in open(a.out)]
    ok = [r for r in rows if 'thick_mm_p10_50_90' in r]
    print(f'[m0] {len(ok)} of {len(rows)} volumes measured; median wall {np.median([r["thick_mm_p10_50_90"][1] for r in ok]):.1f} mm, '
          f'median voxels across the wall {np.median([r["vox_across_wall_median"] for r in ok]):.1f}')


if __name__ == '__main__':
    main()
