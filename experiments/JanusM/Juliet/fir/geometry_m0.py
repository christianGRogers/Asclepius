"""Janus-M Job M0, CPU part (Juliet v1): native-resolution wall geometry and coronary territories.

For each drawn ImageCAS-X training case, from TotalSegmentator `heartchambers_highres` (multi-label, --ml) and the
ImageCAS-X coronary labels (collapsed to the four D25 classes by trillium/icx4/lib/territory.py):
  1. the E4 pipeline (experiments/JanusM/Juliet/real_labels.py): AHA 17 segments, wall thickness per segment
     (mm and voxels), voxels per transmural third, at the CT's native grid;
  2. patient-specific territories: each myocardial voxel takes the class (LAD, LCx or RCA) of the nearest coronary
     voxel of those classes (LM is left out: it feeds both). Per AHA segment, the majority class is compared with
     the AHA default assignment (Cerqueira 2002: LAD 1,2,7,8,13,14,17; RCA 3,4,9,10,15; LCx 5,6,11,12,16).
Nearest-vessel territories are a proxy (Cerci 2012 aligns territories by an expert-defined algorithm; Ortiz-Perez
2008 found 23 % of infarcted segments discordant with the default). This job measures how often the proxy and the
default disagree on CCTA, which decides whether Janus-M reports territories from Janus or from the AHA table.

Usage (Fir login node, CPU, about 20 min for 40 cases):
  python geometry_m0.py --cases $SCRATCH/janusm/m0_cases.txt --hc $SCRATCH/janusm/hc --icx $SCRATCH/icx4/icx \
      --out $SCRATCH/janusm/m0_geometry.json
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(REPO / 'trillium/icx4/lib'))
from real_labels import geometry  # noqa: E402
from territory import to_four  # noqa: E402

AHA_DEFAULT = {**{k: 'LAD' for k in (1, 2, 7, 8, 13, 14, 17)}, **{k: 'RCA' for k in (3, 4, 9, 10, 15)},
               **{k: 'LCx' for k in (5, 6, 11, 12, 16)}}
HC_FALLBACK = {1: 'heart_myocardium', 2: 'heart_atrium_left', 3: 'heart_ventricle_left', 4: 'heart_atrium_right',
               5: 'heart_ventricle_right', 6: 'aorta', 7: 'pulmonary_artery'}


def hc_map():
    try:
        from totalsegmentator.map_to_binary import class_map
        return {v: k for k, v in class_map['heartchambers_highres'].items()}
    except Exception:  # noqa: BLE001  (venv without totalsegmentator: use the published order)
        return {v: k for k, v in HC_FALLBACK.items()}


def one(c, hc_dir, icx_dir, ids):
    # RAS-canonical (the AHA frame needs anterior = +y); both images go through the same transform
    hi = nib.as_closest_canonical(nib.load(str(Path(hc_dir) / f'{c}.nii.gz')))
    li = nib.as_closest_canonical(nib.load(str(Path(icx_dir) / f'{int(c[1:]) + 1}.coronary.nii.gz')))
    if li.shape != hi.shape or not np.allclose(li.affine, hi.affine, atol=1e-3):
        return {'id': c, 'usable': False, 'reason': f'grid mismatch {hi.shape} vs {li.shape}'}
    hc = np.asarray(hi.dataobj).astype(np.int16)
    sp = np.asarray(hi.header.get_zooms()[:3], float)
    cor = to_four(np.asarray(li.dataobj).astype(np.int64), sp)
    m = {k: hc == ids[k] for k in ('heart_myocardium', 'heart_ventricle_left', 'heart_ventricle_right',
                                    'heart_atrium_left', 'aorta')}
    summ, det = geometry(c, m['heart_myocardium'], m['heart_ventricle_left'], m['heart_ventricle_right'],
                         m['heart_atrium_left'], m['aorta'], sp)
    if det is None:
        return summ
    corc = cor[det['box']]
    names = {2: 'LAD', 3: 'LCx', 4: 'RCA'}
    pts = np.argwhere(np.isin(corc, (2, 3, 4)))
    if len(pts) < 50:
        summ['territory'] = None
        return summ
    _, nn = cKDTree(pts * sp).query(det['myo_vox'] * sp)
    terr = np.array([names[v] for v in corc[tuple(pts[nn].T)]])
    seg, keep = det['seg'], det['keep']
    per = {}
    for k in range(1, 18):
        sel = keep & (seg == k)
        if sel.sum() < 20:
            continue
        cnt = Counter(terr[sel])
        maj, n = cnt.most_common(1)[0]
        per[k] = {'majority': maj, 'majority_share': round(n / sel.sum(), 3), 'default': AHA_DEFAULT[k],
                  'concordant': maj == AHA_DEFAULT[k]}
    vox_agree = np.mean([terr[i] == AHA_DEFAULT.get(int(seg[i]), '') for i in np.flatnonzero(keep)])
    summ['territory'] = {'segments': per, 'voxel_agreement_with_default': round(float(vox_agree), 3),
                         'n_segments_discordant': int(sum(not v['concordant'] for v in per.values()))}
    return summ


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', required=True)
    ap.add_argument('--hc', required=True)
    ap.add_argument('--icx', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ids = hc_map()
    need = ('heart_myocardium', 'heart_ventricle_left', 'heart_ventricle_right', 'heart_atrium_left', 'aorta')
    if any(k not in ids for k in need):
        sys.exit(f'heartchambers_highres class names differ from {need}: {sorted(ids)}; send this line back')
    print('label ids:', {k: ids[k] for k in need})
    rows = []
    for c in Path(a.cases).read_text().split():
        try:
            rows.append(one(c, a.hc, a.icx, ids))
        except Exception as e:  # noqa: BLE001
            rows.append({'id': c, 'usable': False, 'reason': repr(e)[:200]})
        r = rows[-1]
        print(c, r.get('usable'), r.get('median_thick_mm'), r.get('median_vox_per_third'),
              (r.get('territory') or {}).get('n_segments_discordant'), flush=True)
    ok = [r for r in rows if r.get('usable')]
    seg_disc = Counter()
    seg_n = Counter()
    for r in ok:
        for k, v in ((r.get('territory') or {}).get('segments') or {}).items():
            seg_n[k] += 1
            seg_disc[k] += not v['concordant']
    summary = {
        'n_cases': len(rows), 'n_usable': len(ok),
        'median_thick_mm': float(np.median([r['median_thick_mm'] for r in ok])) if ok else None,
        'median_vox_per_third': float(np.median([r['median_vox_per_third'] for r in ok])) if ok else None,
        'frac_mid_vox_thinner_than_5p5mm_median': float(np.median([r['frac_mid_vox_thinner_than_5p5mm'] for r in ok])) if ok else None,
        'segment_discordance': {k: round(seg_disc[k] / seg_n[k], 3) for k in sorted(seg_n)},
        'overall_segment_discordance': round(sum(seg_disc.values()) / max(sum(seg_n.values()), 1), 3),
        'voxel_agreement_median': float(np.median([r['territory']['voxel_agreement_with_default'] for r in ok
                                                   if r.get('territory')])) if ok else None,
    }
    json.dump({'summary': summary, 'cases': rows}, open(a.out, 'w'), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
