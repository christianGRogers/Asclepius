"""Delta, Round 10 (report only; P2 is closed): which val cases carry the 0.0079 left-tree tF1 gap between ImageCAS-X's
expert start points and A1's TotalSegmentator-aorta ostium (A29 on #43), and where the A1 ostium sits in them.

Stage 1 reads the A29 run's own output, `$SCRATCH/icx4/delta_p2/per_case.jsonl` (experiments/Delta/r9_fir/score_tf1.py
with --aorta-dir). It opens no image and computes no new score:
  per val case and left class, the gap = tf1_<class> (expert start) - tf1_aorta_<class> (A1 as written), the ostium
  distance, and the cases that carry the mean.
Stage 2 (--icx, --aorta, --pred) opens only the cases stage 1 lists (val only; sealed refused). For each left
ostium of record it records:
  - its class in the reference (LM, or LAD/LCx: does A1 root the left tree past the bifurcation?);
  - the geodesic distance along the reference from the expert start (mm), and the LM's length;
  - the aorta's contact with the reference: voxels within 5 mm, and the number of contact components;
  - whether the prediction covers the ostium of record within 1.5 mm, and with which class.

Usage (Fir login node, after `source $HOME/icx14-venv/bin/activate && cd $SCRATCH/asclepius/repo`):
  python experiments/Delta/r10/ostium_residual.py --rows $SCRATCH/icx4/delta_p2/per_case.jsonl \
      --icx $SCRATCH/icx4/icx --aorta $SCRATCH/icx4/aorta --pred $SCRATCH/icx4/predictions \
      --out $SCRATCH/icx4/r10_ostium_residual.json
  python experiments/Delta/r10/ostium_residual.py --selftest
Exit 0; the JSON and a short table are the report."""
import argparse
import hashlib
import json
import os
import sys

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
PIN = '24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254'
LEFT = ('LM', 'LAD', 'LCx')
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}


def stage1(rows, sealed):
    out = []
    for r in rows:
        if r.get('error') or r.get('split') != 'val':
            continue
        if r['case'] in sealed:
            raise SystemExit(f'sealed case {r["case"]} in the rows: refusing')
        g = {}
        for c in LEFT + ('RCA',):
            a, b = r.get(f'tf1_{c}'), r.get(f'tf1_aorta_{c}')
            if a is not None and b is not None:
                g[c] = round(a - b, 4)
        out.append(dict(case=r['case'], gap=g, gap_macro=round(r['tf1'] - r['tf1_aorta'], 4)
                        if r.get('tf1_aorta') is not None else None,
                        ostium_mm=r.get('ostium_expert_vs_aorta_mm'), flagged_aorta=r.get('flagged_aorta')))
    n = len(out)
    tot = sum(x['gap_macro'] or 0 for x in out)
    carriers = sorted((x for x in out if (x['gap_macro'] or 0) > 1e-6), key=lambda x: -x['gap_macro'])
    neg = [x for x in out if (x['gap_macro'] or 0) < -1e-6]
    cum, top = 0.0, []
    for x in carriers:
        cum += x['gap_macro']
        top.append(dict(x, share_of_gap=round(cum / tot, 3) if tot else None))
    per_class = {c: round(float(np.mean([x['gap'][c] for x in out if c in x['gap']])), 4)
                 for c in LEFT + ('RCA',)}
    return dict(n_val=n, mean_gap_macro=round(tot / n, 4) if n else None, per_class_mean_gap=per_class,
                n_cases_positive=len(carriers), n_cases_negative=len(neg), carriers=top)


def _geodesic(mask, sp, start):
    from skimage.graph import MCP_Geometric
    cost = np.where(mask, 1.0, np.inf)
    d, _ = MCP_Geometric(cost, sampling=tuple(sp)).find_costs([tuple(int(v) for v in start)])
    return d


def locate(ref, pred, aorta, sp, start_vox, T):
    """Where A1's left ostium of record sits relative to the expert start, on one case's arrays (same grid)."""
    rep = T.find_ostia(ref, sp, aorta=aorta)
    m = ref > 0
    near = np.argwhere(m)
    s = near[np.argmin(np.linalg.norm((near - np.asarray(start_vox)) * sp, axis=1))]
    geo = _geodesic(m, sp, s)
    lm = ref == 1
    lm_len = float(np.nanmax(np.where(lm & np.isfinite(geo), geo, np.nan))) if lm.any() else 0.0
    from scipy import ndimage
    contact = m & (ndimage.distance_transform_edt(~aorta, sampling=sp) <= T.AORTA_CONTACT_MM) if aorta.any() else m & False
    ncomp = int(ndimage.label(contact, structure=np.ones((3, 3, 3)))[1])
    res = []
    for o in rep.ostia:
        p = np.asarray(o.point)
        if not np.isfinite(geo[tuple(p)]):
            continue           # another tree (the right one)
        win = tuple(slice(max(int(p[k] - np.ceil(1.5 / sp[k])), 0), int(p[k] + np.ceil(1.5 / sp[k])) + 1)
                    for k in range(3))
        pv = pred[win][pred[win] > 0]
        res.append(dict(rule=o.rule, flagged=bool(o.flagged), class_at_ostium=NAMES.get(int(ref[tuple(p)]), '-'),
                        geodesic_from_start_mm=round(float(geo[tuple(p)]), 2),
                        euclid_from_start_mm=round(float(np.linalg.norm((p - s) * sp)), 2),
                        pred_covers=bool(pv.size), pred_class=NAMES.get(int(np.bincount(pv).argmax()), '-') if pv.size else '-'))
    return dict(lm_length_mm=round(lm_len, 2), contact_voxels=int(contact.sum()), contact_components=ncomp,
                left_ostia=res)


def stage2(cases, a, ostia):
    import nibabel as nib
    sys.path.insert(0, os.path.join(REPO, 'src'))
    sys.path.insert(0, os.path.join(REPO, 'trillium', 'icx4', 'lib'))
    from segtrain import tf1 as T
    from territory import to_four
    out = {}
    for c in cases:
        i = int(c[1:]) + 1
        li = nib.load(os.path.join(a.icx, f'{i}.coronary.nii.gz'))
        sp = np.asarray(li.header.get_zooms()[:3], float)
        ref = to_four(np.asarray(li.dataobj).astype(np.int64), sp).astype(np.uint8)
        pred = np.asarray(nib.load(os.path.join(a.pred, f'{c}.nii.gz')).dataobj).astype(np.uint8)
        aorta = np.asarray(nib.load(os.path.join(a.aorta, f'{c}_aorta.nii.gz')).dataobj) > 0
        inv = np.linalg.inv(li.affine)
        starts = [nib.affines.apply_affine(inv, np.asarray(q) * [-1, -1, 1]) for q in ostia.get(c, {}).get('left', [])]
        if not starts:
            out[c] = dict(error='no left start point')
            continue
        out[c] = locate(ref, pred, aorta, sp, np.round(starts[0]).astype(int), T)
    return out


def _seg_dist(p, a, b):
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[..., None] * ab), axis=-1)


def selftest():
    sys.path.insert(0, os.path.join(REPO, 'src'))
    from segtrain import tf1 as T
    rows = [dict(case='c0001', split='val', tf1=0.9, tf1_aorta=0.8, tf1_LM=1.0, tf1_aorta_LM=0.7, tf1_LAD=0.9,
                 tf1_aorta_LAD=0.9, tf1_LCx=0.8, tf1_aorta_LCx=0.8, tf1_RCA=0.9, tf1_aorta_RCA=0.9),
            dict(case='c0002', split='val', tf1=0.9, tf1_aorta=0.9),
            dict(case='c0003', split='open_clean', tf1=0.5, tf1_aorta=0.1)]
    s = stage1(rows, set())
    assert s['n_val'] == 2 and s['n_cases_positive'] == 1 and s['carriers'][0]['case'] == 'c0001'
    assert abs(s['carriers'][0]['share_of_gap'] - 1.0) < 1e-9
    try:
        stage1([dict(rows[0], case='c0002x')], {'c0002x'})
        raise AssertionError('sealed row not refused')
    except SystemExit:
        pass
    # synthetic left tree: a round LM along y from an aorta, bifurcating into LAD (along y) and LCx (along x)
    sp = np.array([0.5, 0.5, 0.5])
    ref = np.zeros((40, 120, 70), np.uint8)
    zz, yy, xx = np.mgrid[:40, :120, :70]
    tube = lambda a, b: _seg_dist(np.stack([zz, yy, xx], -1) * sp, np.array(a) * sp, np.array(b) * sp) <= 1.5  # noqa: E731
    ref[tube((20, 20, 30), (20, 50, 30))] = 1          # LM, 15 mm
    ref[tube((20, 51, 30), (20, 110, 30)) & (ref == 0)] = 2
    ref[tube((20, 51, 31), (20, 51, 66)) & (ref == 0)] = 3
    aorta = np.zeros_like(ref, bool)
    aorta[10:30, 0:17, 20:40] = True                  # 1.5 mm short of the LM's proximal end
    pred = ref.copy()
    pred[:, :32] = 0                                  # the prediction misses the proximal 6 mm of the LM
    r = locate(ref, pred, aorta, sp, (20, 20, 30), T)
    o = r['left_ostia'][0]
    assert o['class_at_ostium'] == 'LM' and o['geodesic_from_start_mm'] < 2.0, r
    assert not o['pred_covers'] and r['contact_components'] == 1, r
    assert 14.0 <= r['lm_length_mm'] <= 17.5, r      # 15 mm segment + the round cap
    print('[residual] self-test passed:', json.dumps(r))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--rows'); ap.add_argument('--icx'); ap.add_argument('--aorta'); ap.add_argument('--pred')
    ap.add_argument('--out'); ap.add_argument('--top', type=int, default=12)
    a = ap.parse_args()
    h = hashlib.sha256(open(os.path.join(REPO, 'src/segtrain/tf1.py'), 'rb').read()).hexdigest()
    if h != PIN:
        sys.exit(f'tf1.py sha256 {h} is not the A1c pin')
    if a.selftest:
        return selftest()
    S = json.load(open(os.path.join(REPO, 'trillium/sealed_test.json')))
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    rows = [json.loads(ln) for ln in open(a.rows) if ln.strip()]
    s1 = stage1(rows, sealed)
    res = dict(tf1_sha256=h, stage1=s1)
    if a.icx and a.aorta and a.pred:
        ostia = json.load(open(os.path.join(REPO, 'experiments/Delta/r9_expert_ostia.json')))['ostia']
        cases = [x['case'] for x in s1['carriers'][:a.top]]
        res['stage2'] = stage2(cases, a, ostia)
    json.dump(res, open(a.out, 'w') if a.out else sys.stdout, indent=1)
    print(f"\nval {s1['n_val']}: mean gap {s1['mean_gap_macro']}, per class {s1['per_class_mean_gap']}; "
          f"{s1['n_cases_positive']} cases > 0, {s1['n_cases_negative']} < 0")
    for x in s1['carriers'][:a.top]:
        st = res.get('stage2', {}).get(x['case'], {})
        print(' ', x['case'], x['gap_macro'], x['gap'], 'ostium mm', x['ostium_mm'], 'cum', x['share_of_gap'],
              json.dumps(st.get('left_ostia', st.get('error', ''))), 'LM', st.get('lm_length_mm'))


if __name__ == '__main__':
    main()
