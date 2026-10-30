"""Janus-M Job JM-0, optional CPU add-on (Juliet v2; Round 1 ruling section 6 item 1): Hotel's half-maximum edge
offsets of the `heartchambers_highres` borders on native ImageCAS.

For each JM-0 case, at up to 4000 boundary points of each LV border:
  - endocardial: myocardium voxels touching the LV blood pool;
  - epicardial: myocardium voxels touching neither the LV, RV nor LA pool (the free wall, where fat lies outside);
the CT is sampled along the outward normal (away from the myocardium; from a smoothed signed distance) from -4 to
+4 mm in 0.25 mm steps. Plateaus: myocardium = median at -3.0 to -1.5 mm, other side = median at +1.5 to +3.0 mm. The
half-maximum crossing nearest 0 is the image edge. **Label bias = -crossing (mm): positive means the label's
myocardium reaches past the image edge (too thick on that side).** Hotel v1 measured +0.86 mm (median, epicardium) for
TotalSegmentator v1 at 1.5 mm.

Reads only the JM-0 cases (ImageCAS-X training) that geometry_m0.py reads, plus their CT. Prints aggregates.

Usage (Fir login node, CPU, after Job JM-0's GPU step):
  python edges_m0.py --cases $SCRATCH/janusm/m0_cases.txt --hc $SCRATCH/janusm/hc \
      --layout $SCRATCH/icx4/layout.json --out $SCRATCH/janusm/m0_edges.json
Self-test on a synthetic phantom (no data): python edges_m0.py --selftest
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

STEPS = np.arange(-4.0, 4.0001, 0.25)


def offsets(ct, myo, lv, rv, la, sp, rng, npts=4000):
    sd = ndimage.distance_transform_edt(~myo, sampling=sp) - ndimage.distance_transform_edt(myo, sampling=sp)
    g = np.stack(np.gradient(ndimage.gaussian_filter(sd, 1.0), *sp))
    nb = lambda m: ndimage.binary_dilation(m, structure=ndimage.generate_binary_structure(3, 1))  # noqa: E731
    pools = lv | rv | la
    sets = {'endo': myo & nb(lv), 'epi': myo & nb(~(myo | pools)) & ~nb(pools)}
    out = {}
    for name, m in sets.items():
        pts = np.argwhere(m)
        if len(pts) < 50:
            out[name] = None
            continue
        pts = pts[rng.choice(len(pts), min(npts, len(pts)), replace=False)]
        n = g[:, pts[:, 0], pts[:, 1], pts[:, 2]].T
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
        # boundary voxel centre -> label surface is about half a voxel outward along n
        base = pts + 0.5 * n / 1.0
        coords = base[:, None, :] + STEPS[None, :, None] * n[:, None, :] / sp[None, None, :]
        prof = ndimage.map_coordinates(ct.astype(np.float32), coords.reshape(-1, 3).T, order=1,
                                       mode='nearest').reshape(len(pts), len(STEPS))
        a = np.median(prof[:, (STEPS >= -3.0) & (STEPS <= -1.5)], axis=1)
        b = np.median(prof[:, (STEPS >= 1.5) & (STEPS <= 3.0)], axis=1)
        half = (a + b) / 2
        ok = np.abs(a - b) >= 40                                   # a visible step only
        x = (prof - half[:, None]) * np.sign(a - b)[:, None]       # > 0 on the myocardium side
        cross = np.full(len(pts), np.nan)
        for i in np.flatnonzero(ok):
            s = np.flatnonzero((x[i, :-1] > 0) & (x[i, 1:] <= 0))
            if len(s):
                j = s[np.argmin(np.abs(STEPS[s]))]
                t = x[i, j] / (x[i, j] - x[i, j + 1])
                cross[i] = STEPS[j] + t * (STEPS[j + 1] - STEPS[j])
        bias = -cross[np.isfinite(cross)]
        out[name] = {'n_points': int(len(pts)), 'n_with_edge': int(len(bias)),
                     'bias_median_mm': round(float(np.median(bias)), 3) if len(bias) else None,
                     'bias_iqr_mm': [round(float(q), 3) for q in np.percentile(bias, [25, 75])] if len(bias) else None,
                     'step_median_hu': round(float(np.median(np.abs(a - b)[ok])), 1) if ok.any() else None}
    return out


def selftest():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import register_lie as R
    rng = np.random.default_rng(3)
    img, t = R.render(R.FP, np.zeros(18), (np.eye(3), np.zeros(3)), 0.0, R.FP['scar'], 30.0, rng, want_truth=True)
    lab, sp = t['lab'], np.array([R.V] * 3)
    myo, lv, rv, la = lab == 1, lab == 2, lab == 3, lab == 4
    res = {'exact': offsets(img, myo, lv, rv, la, sp, rng)}
    thick = ndimage.binary_dilation(myo, iterations=1) & ~lv & ~rv & ~la      # epicardium 1 voxel outward
    res['epi_dilated_1mm'] = offsets(img, thick, lv, rv, la, sp, rng)
    out = Path(__file__).resolve().parents[1] / 'edges_selftest.json'
    out.write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps(res, indent=1))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--cases')
    ap.add_argument('--hc')
    ap.add_argument('--layout')
    ap.add_argument('--out')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    import nibabel as nib
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from geometry_m0 import hc_map
    ids = hc_map()
    ct_paths = json.load(open(a.layout))['cases']
    rng = np.random.default_rng(0)
    rows = []
    for c in Path(a.cases).read_text().split():
        try:
            hi = nib.as_closest_canonical(nib.load(str(Path(a.hc) / f'{c}.nii.gz')))
            ci = nib.as_closest_canonical(nib.load(ct_paths[c]['ct']))
            if ci.shape != hi.shape:
                rows.append({'id': c, 'usable': False, 'reason': 'grid mismatch'})
                continue
            hc = np.asarray(hi.dataobj).astype(np.int16)
            sp = np.asarray(hi.header.get_zooms()[:3], float)
            r = offsets(np.asarray(ci.dataobj), hc == ids['heart_myocardium'], hc == ids['heart_ventricle_left'],
                        hc == ids['heart_ventricle_right'], hc == ids['heart_atrium_left'], sp, rng)
            rows.append({'id': c, 'usable': True, **r})
        except Exception as e:  # noqa: BLE001
            rows.append({'id': c, 'usable': False, 'reason': repr(e)[:200]})
        print(c, rows[-1].get('usable'), {k: (rows[-1].get(k) or {}).get('bias_median_mm') for k in ('endo', 'epi')},
              flush=True)
    ok = [r for r in rows if r.get('usable')]
    summ = {'n_cases': len(rows), 'n_usable': len(ok)}
    for k in ('endo', 'epi'):
        v = [r[k]['bias_median_mm'] for r in ok if r.get(k) and r[k]['bias_median_mm'] is not None]
        summ[f'{k}_bias_median_of_case_medians_mm'] = round(float(np.median(v)), 3) if v else None
        summ[f'{k}_bias_case_iqr_mm'] = [round(float(q), 3) for q in np.percentile(v, [25, 75])] if v else None
    json.dump({'summary': summ, 'cases': rows}, open(a.out, 'w'), indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    main()
