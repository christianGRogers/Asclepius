"""Janus 1-F round 2 (Delta): two CPU checks on ImageCAS-X's labels (620 train + locked 100; no sealed case, no CT).

1. collapse: does D47 Q1's four-class collapse -- SegQueue 0.20.0's own `collapse_to_four` (contact rule, imported,
   not re-implemented) -- reproduce ImageCAS-X's origin labels (D25: L-PDA/L-PLA -> LCx, R-PDA/R-PLA -> RCA) when
   1-F's PDA = R-PDA | L-PDA and PLB = R-PLA | L-PLA (D47 (A))? Per case: voxels whose collapsed vessel differs from
   the D25 territory, components decided, fallbacks.
2. band (item 4, stage 2): for w in WIDTHS mm around each host trunk (LAD for S1-S3; RCA for SN, conus, RMA; LCx for a
   circumflex SN), (a) the background volume a band would release into the set {bg, untraced classes}, and (b) the
   share of each *traced* side branch's voxels lying within w of its own trunk -- a proxy for how much of an
   untraced branch of similar size a band of w would cover. Run on a hash-chosen subset of the 620.
Usage: python label_checks.py <icx_dir> <census.json> <out.json> [n_band]
"""
import hashlib, json, os, sys
from multiprocessing import Pool

import nibabel as nb
import numpy as np
from scipy import ndimage as ndi

ROOT = os.path.dirname(os.path.abspath(__file__)) + '/../../..'
sys.path.insert(0, f'{ROOT}/src')
from segqueue14.labels import collapse_to_four, NAMES as SQ_NAMES   # noqa: E402

S = json.load(open(f'{ROOT}/trillium/icx4/sealed_test.json'))
SEALED = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
# ImageCAS-X ids: 1 LM, 2 LAD, 3 LCx, 4 D1, 5 D2, 6 OM1, 7 OM2, 8 IM, 9 RCA, 10 R-PDA, 11 R-PLA, 12 L-PDA, 13 L-PLA,
# 14 Other
LAD_SIDE, LCX_SIDE = (2, 4, 5), (3, 6, 7, 8, 12, 13)
WIDTHS = (4, 8, 15, 25)
STRUCT = np.ones((3, 3, 3), bool)


def case_file(icx, c):
    return os.path.join(icx, '%d.coronary.nii.gz' % (int(c[1:]) + 1))


def crop(lab, zooms, margin_mm):
    nz = np.argwhere(lab > 0)
    lo, hi = nz.min(0), nz.max(0) + 1
    m = np.ceil(margin_mm / np.asarray(zooms)).astype(int)
    lo, hi = np.maximum(lo - m, 0), np.minimum(hi + m, lab.shape)
    return lab[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]


def other_to_side(lab):
    """'Other' pieces go into the side they touch (LAD side / LCx side / RCA), as j1f_r1's census."""
    lad, lcx, rca = np.isin(lab, LAD_SIDE), np.isin(lab, LCX_SIDE), np.isin(lab, (9, 10, 11))
    lab_o, n = ndi.label(lab == 14, STRUCT)
    out = {'LAD': np.zeros(lab.shape, bool), 'LCx': np.zeros(lab.shape, bool), 'RCA': np.zeros(lab.shape, bool)}
    for k in range(1, n + 1):
        p = lab_o == k
        g = ndi.binary_dilation(p, STRUCT)
        t = {'LAD': int((g & lad).sum()), 'LCx': int((g & lcx).sum()), 'RCA': int((g & rca).sum())}
        if max(t.values()) > 0:
            out[max(t, key=t.get)] |= p
    return out


def collapse_check(c, icx):
    im = nb.load(case_file(icx, c)); lab = crop(np.asarray(im.dataobj).astype(np.uint8), im.header.get_zooms(), 2)
    oth = other_to_side(lab)
    lad = np.isin(lab, (2, 4, 5)) | oth['LAD']
    lcx_fixed = np.isin(lab, (3, 6, 7, 8)) | oth['LCx']        # LCx with OM1, OM2, ramus; not L-PDA/L-PLA
    rca_fixed = (lab == 9) | oth['RCA']
    pda = np.isin(lab, (10, 12)); plb = np.isin(lab, (11, 13))
    masks = np.stack([lab == 1, lad, lcx_fixed, rca_fixed, pda, plb])
    st = {}
    four = collapse_to_four(masks, ['LM', 'LAD', 'LCx', 'RCA', 'PDA', 'PLB'], stats=st)
    ref_lcx = lcx_fixed | np.isin(lab, (12, 13)); ref_rca = rca_fixed | np.isin(lab, (10, 11))
    i = {n: k for k, n in enumerate(SQ_NAMES)}
    wrong_to_rca = int((four[i['RCA']].astype(bool) & ref_lcx).sum())
    wrong_to_lcx = int((four[i['LCx']].astype(bool) & ref_rca).sum())
    left_vox = int(np.isin(lab, (12, 13)).sum())
    st.pop('masks', None)
    return {'case': c, 'left_branch_voxels': left_vox, 'lcx_ref_voxels_sent_to_rca': wrong_to_rca,
            'rca_ref_voxels_sent_to_lcx': wrong_to_lcx, 'stats': st}


def band_check(c, icx):
    im = nb.load(case_file(icx, c)); z = im.header.get_zooms()[:3]
    lab = crop(np.asarray(im.dataobj).astype(np.uint8), z, max(WIDTHS) + 1)
    vox = float(np.prod(z)); bg = lab == 0
    out = {'case': c, 'tree_mm3': float((lab > 0).sum() * vox), 'release_mm3': {}, 'cover': {}}
    hosts = {'LAD': lab == 2, 'LCx': lab == 3, 'RCA': lab == 9}
    kids = {'LAD': (4, 5), 'LCx': (6, 7), 'RCA': (10, 11)}
    dist = {}
    for h, m in hosts.items():
        if not m.any(): continue
        dist[h] = ndi.distance_transform_edt(~m, sampling=z)
        for w in WIDTHS:
            out['release_mm3'][f'{h}_{w}'] = float((bg & (dist[h] <= w)).sum() * vox)
        for k in kids[h]:
            km = lab == k
            if km.sum() < 20: continue
            d = dist[h][km]
            out['cover'][f'{k}'] = {str(w): float((d <= w).mean()) for w in WIDTHS}
            out['cover'][f'{k}']['p90_mm'] = float(np.percentile(d, 90))
            out['cover'][f'{k}']['max_mm'] = float(d.max())
    if 'LAD' in dist and 'RCA' in dist:
        for w in WIDTHS:
            u = bg & ((dist['LAD'] <= w) | (dist['RCA'] <= w) | (dist.get('LCx', np.inf) <= w))
            out['release_mm3'][f'union_{w}'] = float(u.sum() * vox)
    return out


def _c(a): return collapse_check(*a)
def _b(a): return band_check(*a)


if __name__ == '__main__':
    icx, cen, out = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3]
    nband = int(sys.argv[4]) if len(sys.argv) > 4 else 120
    rows = cen['rows']
    grp = {r['case']: ('locked100' if r['group'] in ('val80', 'locked_open20') else 'train620') for r in rows}
    cases = sorted(grp)
    assert not (set(cases) & SEALED) and len(cases) == 720
    with Pool(4) as p:
        col = p.map(_c, [(c, icx) for c in cases], chunksize=4)
    key = lambda c: hashlib.sha256(('asclepius-j1f-r2-band:' + c).encode()).hexdigest()
    band_cases = sorted([c for c in cases if grp[c] == 'train620'], key=key)[:nband]
    with Pool(3) as p:
        band = p.map(_b, [(c, icx) for c in band_cases], chunksize=2)
    json.dump({'group': grp, 'collapse': col, 'band': band}, open(out, 'w'))
    print('done', len(col), len(band))
