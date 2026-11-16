"""Janus 1-F (Foxtrot v1): ImageCAS-X's 14 classes -> 1-F's round-1 label map, with set-valued codes where ImageCAS-X
does not decide the 1-F class. A set code is trained with the marginal CE of head_surgery_check.py
(-log sum_{c in set} p_c); 255 is D40/nnU-Net's ignore.

1-F values (round 1): 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA, 5 D1, 6 D2, 7 D3, 8 OM1, 9 OM2, 10 Ramus, 11 PDA, 12 PLB.
(S1-S3, SN, Conus, RMA: 13-18, added by head surgery once their read count passes the threshold; ImageCAS-X never
traced them, so on ImageCAS-X they are inside background and do not exist as a head in round 1.)
Rules:
  ICX LM, LAD, LCx, RCA, D1, D2, OM1, OM2, IM, R-PDA, R-PLA -> LM, LAD, LCx, RCA, D1, D2, OM1, OM2, Ramus, PDA, PLB
  ICX L-PDA -> set 20 = {PDA, LCx};  L-PLA -> set 21 = {PLB, LCx}   (until the lead answers Q1; then a plain value)
  ICX Other, diagonal side (touches only LAD/D1/D2): the component attached nearest the LM/LAD join -> D3 when the case
      also has D1 and D2; set 22 = {LAD, D3} when it lacks D2; every further diagonal-side component (D4) -> LAD
  ICX Other, marginal side (touches only LCx/OM1/OM2/IM) -> LCx (OM3/OM4 have no 1-F class; #280 unions them into LCx)
  ICX Other touching both sides or nothing -> 255
Usage: python3 make_labels_1f.py stats <label_dir> <split620.json> <out.json> [n_proc]
       python3 make_labels_1f.py write <in.nii.gz> <out.nii.gz>"""
import json, os, sys
from multiprocessing import Pool
import numpy as np, nibabel as nib
from scipy import ndimage as ndi

MAP = {1: 1, 2: 2, 3: 3, 9: 4, 4: 5, 5: 6, 6: 8, 7: 9, 8: 10, 10: 11, 11: 12, 12: 20, 13: 21}
DIAG = {2, 4, 5}; MARG = {3, 6, 7, 8}
SETS = {20: [11, 3], 21: [12, 3], 22: [2, 7]}
NAMES = ['bg', 'LM', 'LAD', 'LCx', 'RCA', 'D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB']
K = np.ones((3, 3, 3))


def convert(a, z):
    out = np.zeros(a.shape, np.uint8)
    for s, d in MAP.items():
        out[a == s] = d
    info = {'other_diag': 0, 'other_marg': 0, 'other_amb': 0, 'd3_from_other': 0, 'd3_set': 0, 'd4_to_lad': 0}
    if not (a == 14).any():
        return out, info
    lm = a == 1; lad = a == 2
    # the LM/LAD join: LAD voxels touching LM; without an LM, the LAD voxel nearest the LCx
    join = lad & ndi.binary_dilation(lm, K)
    if not join.any():
        lcx = a == 3
        d = ndi.distance_transform_edt(~lcx, sampling=z) if lcx.any() else None
        p = np.argwhere(lad)
        join_pt = p[np.argmin(d[tuple(p.T)])] if d is not None and len(p) else p[0]
    else:
        join_pt = np.argwhere(join).mean(0)
    ol, n = ndi.label(a == 14, structure=K)
    diag = []
    for i, sl in enumerate(ndi.find_objects(ol), start=1):
        s2 = tuple(slice(max(x.start - 2, 0), x.stop + 2) for x in sl)
        c = ol[s2] == i; ring = ndi.binary_dilation(c, K) & ~c
        touch = set(np.unique(a[s2][ring]).tolist()) - {0, 14}
        full = np.zeros(a.shape, bool); full[s2] = c
        if touch and touch <= DIAG:
            att = np.argwhere(ndi.binary_dilation(full, K) & np.isin(a, list(DIAG)))
            dist = np.min(np.sqrt((((att - join_pt) * np.asarray(z)) ** 2).sum(1)))
            diag.append((dist, full)); info['other_diag'] += 1
        elif touch and touch <= MARG:
            out[full] = 3; info['other_marg'] += 1
        else:
            out[full] = 255; info['other_amb'] += 1
    diag.sort(key=lambda t: t[0])
    has_d1, has_d2 = (a == 4).any(), (a == 5).any()
    for j, (_, full) in enumerate(diag):
        if j == 0 and has_d1 and has_d2:
            out[full] = 7; info['d3_from_other'] += 1
        elif j == 0:
            out[full] = 22; info['d3_set'] += 1
        else:
            out[full] = 2; info['d4_to_lad'] += 1
    return out, info


def stats(path):
    im = nib.load(path); a = np.asarray(im.dataobj).astype(np.int16); z = im.header.get_zooms()[:3]
    nz = np.argwhere(a > 0); lo = np.maximum(nz.min(0) - 3, 0); hi = nz.max(0) + 4
    a = a[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    out, info = convert(a, z)
    cnt = np.bincount(out.ravel(), minlength=256)
    vox = float(np.prod(z))
    info['case'] = 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1)
    info['mm3'] = {str(k): round(float(cnt[k] * vox), 1) for k in list(range(1, 13)) + [20, 21, 22, 255] if cnt[k]}
    info['fg_voxels_total'] = int(cnt[1:].sum())
    return info


if __name__ == '__main__':
    if sys.argv[1] == 'write':
        im = nib.load(sys.argv[2]); a = np.asarray(im.dataobj).astype(np.int16)
        out, _ = convert(a, im.header.get_zooms()[:3])
        nib.save(nib.Nifti1Image(out, im.affine, im.header), sys.argv[3]); sys.exit(0)
    lab, sj, oj = sys.argv[2], sys.argv[3], sys.argv[4]
    npr = int(sys.argv[5]) if len(sys.argv) > 5 else 4
    keep = set(json.load(open(sj))['train620'])
    files = sorted(os.path.join(lab, f) for f in os.listdir(lab) if f.endswith('.coronary.nii.gz')
                   and 'c%04d' % (int(f.split('.')[0]) - 1) in keep)
    with Pool(npr) as p:
        res = p.map(stats, files, chunksize=4)
    n = len(res); tot = {}
    for r in res:
        for k, v in r['mm3'].items():
            tot.setdefault(k, [0, 0.0]); tot[k][0] += 1; tot[k][1] += v
    allmm = sum(v[1] for v in tot.values())
    summ = {'n': n, 'per_value': {(NAMES[int(k)] if int(k) < 13 else {'20': 'set{PDA,LCx}', '21': 'set{PLB,LCx}',
                                   '22': 'set{LAD,D3}', '255': 'ignore'}[k]): {'cases': v[0], 'share_of_fg_volume_pct': round(100 * v[1] / allmm, 2)}
                                  for k, v in sorted(tot.items(), key=lambda kv: int(kv[0]))},
            'other': {k: sum(r[k] for r in res) for k in ('other_diag', 'other_marg', 'other_amb', 'd3_from_other', 'd3_set', 'd4_to_lad')}}
    summ['cases_with_D3'] = sum(r['d3_from_other'] > 0 for r in res)
    summ['cases_with_D3_set'] = sum(r['d3_set'] > 0 for r in res)
    json.dump({'summary': summ, 'per_case': res}, open(oj, 'w'))
    print(json.dumps(summ, indent=1))
