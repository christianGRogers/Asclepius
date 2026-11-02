"""Juliet v1, E4: the derived-layer pipeline on real myocardium labels (TotalSegmentator v1 dataset).

Question: from three labels only (LV cavity, LV myocardium, RV cavity), can AHA segments, wall thickness and
transmural thirds be computed automatically on real anatomy, and at what voxel count per third? This is the
pipeline Juliet v1 proposes for Janus-M (the network learns borders; layers and segments are computed).

Data: 12 subjects of the TotalSegmentator v1 dataset (Zenodo 10.5281/zenodo.6802614, CC BY 4.0), cardiac study
types, chosen by a pre-registered salted hash (`selection.json` next to the data), excluding the 16 subject ids
the coronary pool holds. Labels used: heart_ventricle_left (LV cavity), heart_myocardium (LV myocardium),
heart_ventricle_right, heart_atrium_left, aorta. Images are not used.

Method (per subject, RAS-canonical):
  - base plane: centroid of LV-cavity voxels within 3 mm of the left atrium or aorta (mitral/aortic valve);
    apex: the myocardial voxel farthest from that centroid; long axis = base -> apex.
  - long-axis position s in [0, 1] (0 base plane, 1 apex point); AHA rings: basal s < 1/3, mid < 2/3, apical
    < 0.9, apex cap above (Cerqueira 2002 divides the LV into thirds along the long axis plus the apex).
  - circumferential angle around the axis, 0 at the RV centroid direction (the septum's centre); anterior is
    the side of the patient's anterior (+A in RAS). Basal/mid: six 60-degree sectors, septum = +/-60 degrees
    around the RV direction; apical: four 90-degree sectors.
  - transmural depth = d_endo / (d_endo + d_epi) (mm, anisotropic EDT); thickness = d_endo + d_epi at
    mid-wall voxels (|depth - 0.5| < 1/6); voxels within 3 mm of the atrium/aorta are left out (valve plane).
Outputs: per subject and segment, median thickness (mm and voxels), voxels per third, and segment counts.

Run: python3 experiments/JanusM/Juliet/real_labels.py <dir holding Totalsegmentator_dataset/>
"""
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage

OUT = Path(__file__).with_name('real_labels.json')
NAMES_BM = ['anterior', 'anteroseptal', 'inferoseptal', 'inferior', 'inferolateral', 'anterolateral']
NAMES_AP = ['anterior', 'septal', 'inferior', 'lateral']


def load(p):
    im = nib.as_closest_canonical(nib.load(str(p)))
    return np.asarray(im.dataobj) > 0, im.header.get_zooms()[:3], im.affine


def subject(root, sid):
    d = Path(root) / 'Totalsegmentator_dataset' / sid / 'segmentations'
    myo, sp, aff = load(d / 'heart_myocardium.nii.gz')
    lv, _, _ = load(d / 'heart_ventricle_left.nii.gz')
    rv, _, _ = load(d / 'heart_ventricle_right.nii.gz')
    la, _, _ = load(d / 'heart_atrium_left.nii.gz')
    ao, _, _ = load(d / 'aorta.nii.gz')
    return geometry(sid, myo, lv, rv, la, ao, sp)[0]


def geometry(sid, myo, lv, rv, la, ao, sp):
    """Returns (summary dict, detail) where detail holds the crop box, myocardial voxel indices (in the crop),
    their AHA segment (1-17), the keep mask (off the valve band) and the depth, for callers that need them."""
    sp = np.array(sp, float)
    if myo.sum() < 1000 or lv.sum() < 1000 or rv.sum() < 1000:
        return {'id': sid, 'usable': False, 'reason': 'heart labels missing or tiny',
                'n_myo': int(myo.sum()), 'n_lv': int(lv.sum()), 'n_rv': int(rv.sum())}, None
    # crop to the heart
    box = ndimage.find_objects((myo | lv | rv | la).astype(np.int8))[0]
    box = tuple(slice(max(s.start - 10, 0), s.stop + 10) for s in box)
    myo, lv, rv, la, ao = (a[box] for a in (myo, lv, rv, la, ao))
    valve = ndimage.distance_transform_edt(~(la | ao), sampling=sp) < 3.0
    base_vox = np.argwhere(lv & valve)
    if len(base_vox) < 20:
        return {'id': sid, 'usable': False, 'reason': 'no valve plane (LV not adjacent to LA/aorta)'}, None
    mm = lambda ijk: ijk * sp
    base_c = mm(base_vox).mean(0)
    myo_vox = np.argwhere(myo)
    P = mm(myo_vox)
    apex = P[np.argmax(np.linalg.norm(P - base_c, axis=1))]
    ax = apex - base_c
    L = np.linalg.norm(ax)
    ax /= L
    s = (P - base_c) @ ax / L
    # circumferential frame: e1 = RV direction projected off the axis; e2 chosen toward anterior (+A = +y in RAS)
    rv_c = mm(np.argwhere(rv)).mean(0)
    e1 = (rv_c - base_c) - ((rv_c - base_c) @ ax) * ax
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(ax, e1)
    if e2[1] < 0:
        e2 = -e2
    rel = P - base_c
    ang = np.degrees(np.arctan2(rel @ e2, rel @ e1)) % 360.0     # 0 = septum centre, +90 = anterior side
    # depth and thickness
    d_in = ndimage.distance_transform_edt(~lv, sampling=sp)
    d_out = ndimage.distance_transform_edt(myo | lv, sampling=sp)
    half = sp.mean() / 2
    di = d_in[myo] - half
    do = d_out[myo] - half
    depth = di / np.maximum(di + do, 1e-6)
    thick = di + do
    keep = ~valve[myo] & (s >= 0)
    mid = keep & (np.abs(depth - 0.5) < 1 / 6)
    # AHA assignment: septum spans -60..+60 around e1 (anteroseptal on the anterior side, 0..60)
    seg = np.zeros(len(P), int)
    ring = np.where(s < 1 / 3, 0, np.where(s < 2 / 3, 1, np.where(s < 0.9, 2, 3)))
    # basal/mid sectors, counter-clockwise from the anterior side: septum split at 0
    sec6 = np.select([(ang >= 0) & (ang < 60), (ang >= 300) | (ang < 0), (ang >= 240) & (ang < 300),
                      (ang >= 180) & (ang < 240), (ang >= 120) & (ang < 180), (ang >= 60) & (ang < 120)],
                     [1, 2, 3, 4, 5, 0])   # index into NAMES_BM
    sec4 = np.select([(ang >= 45) & (ang < 135), (ang >= 315) | (ang < 45), (ang >= 225) & (ang < 315)], [0, 1, 2], 3)
    seg = np.where(ring == 0, 1 + sec6, np.where(ring == 1, 7 + sec6, np.where(ring == 2, 13 + sec4, 17)))
    out = {'id': sid, 'usable': True, 'spacing_mm': [round(float(x), 3) for x in sp], 'lv_axis_mm': round(float(L), 1),
           'n_myo_vox': int(myo.sum()), 'segments': {}}
    for k in range(1, 17):
        m = mid & (seg == k)
        if m.sum() < 10:
            out['segments'][k] = None
            continue
        t = float(np.median(thick[m]))
        out['segments'][k] = {'thick_mm': round(t, 2), 'thick_vox': round(t / float(sp.mean()), 1),
                              'n_mid_vox': int(m.sum()), 'n_myo_vox': int((keep & (seg == k)).sum())}
    allt = thick[mid]
    out['median_thick_mm'] = round(float(np.median(allt)), 2)
    out['p10_p90_thick_mm'] = [round(float(np.percentile(allt, 10)), 2), round(float(np.percentile(allt, 90)), 2)]
    out['frac_mid_vox_thinner_than_5p5mm'] = round(float(np.mean(allt < 5.5)), 3)
    out['median_vox_per_third'] = round(float(np.median(allt)) / 3 / float(sp.mean()), 2)
    out['frac_myo_in_valve_band'] = round(float(np.mean(valve[myo])), 3)
    return out, {'box': box, 'myo_vox': myo_vox, 'seg': seg, 'keep': keep, 'depth': depth}


if __name__ == '__main__':
    root = sys.argv[1]
    sel = json.loads((Path(root) / 'selection.json').read_text())
    res = [subject(root, s) for s in sel['selected']]
    for r in res:
        print(json.dumps({k: v for k, v in r.items() if k != 'segments'}))
    OUT.write_text(json.dumps({'selection': sel, 'subjects': res}, indent=1) + '\n')
    print('wrote', OUT)
