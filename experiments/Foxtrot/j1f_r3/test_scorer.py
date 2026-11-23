"""Janus 1-F round 3 (Foxtrot): the scorer of record's tests on TRAINING fixtures only (F-A16: "Delta's checks and
Atlas's self-test both become the scorer's tests").

Fixtures: the 6 training cases Delta v2 chose (smallest sha256('asclepius-j1f-r2-scorertest:' + id) over the 620),
reference = the scorer's stage1_labels (D47 (A), F-A3). Perturbations of the reference, each scored with the amended
scorer and pooled per piece with gates.pool():
  Delta v2 (test_branch_score.py): identity; swap D1/D2; OM2 -> LCx; OM2 -> background; one-voxel dilation into
    background; swap PDA/PLB; the collapse equals D25 (territory.to_four) on every non-Other, non-255 voxel.
  Atlas v2 (selftest + validate_scorer.py): one-voxel 6-erosion; OM1+OM2 folded into the LCx; PLB dropped; PDA
    truncated to 40 % of its length from its root; plus the synthetic self-test (`j1f_scorer.selftest`).
  New (F-A17): collapse fallbacks are 0 on every reference; a left PDA touching only a left PLB that touches the LCx
    collapses to the LCx (SegQueue's chain rule); a PDA/PLB with no contact falls back to the RCA and is counted.
Usage: python test_scorer.py <icx620_dir> <split_j1l.json> [out.json]   (exit 1 on any FAIL)"""
import hashlib, json, os, sys
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '../j1f_r2'), os.path.join(HERE, '../../../trillium/icx4/lib'),
                os.path.join(HERE, '../../Atlas/j1f_r2')]
import j1f_scorer as S  # noqa: E402
import gates as G  # noqa: E402
import labels_r2 as L  # noqa: E402
import territory  # noqa: E402
from validate_scorer import truncate  # noqa: E402  (Atlas's truncation; it calls its own scorer's pieces_of, unchanged)

V = {n: i for i, n in enumerate(S.NAMES)}
fails, log = [], []


def check(name, cond):
    log.append(('PASS ' if cond else 'FAIL ') + name); print(log[-1], flush=True)
    if not cond:
        fails.append(name)


def synthetic_chain():
    sp = (0.5, 0.5, 0.5)
    a = np.zeros((30, 60, 60), np.uint8)
    a[5, 5:40, 5] = 3                     # LCx
    a[5, 40:50, 5] = 12                   # left PLB, face contact with the LCx tip
    a[5:20, 49, 5] = 11                   # left PDA, face contact with the PLB only
    a[25, 10:50, 50] = 4                  # RCA elsewhere
    four, st = S.collapse4(a, sp)
    check('chain rule: a left PDA touching only its PLB collapses to the LCx', bool((four[a == 11] == 3).all()))
    check('chain rule: no fallback counted', st['fallback'] == 0)
    b = a.copy(); b[5, 40:50, 5] = 0      # the PLB removed: the PDA now touches nothing
    four, st = S.collapse4(b, sp)
    check('no contact: falls back to the RCA, counted', bool((four[b == 11] == 4).all()) and st['fallbackUnattached'] == 1)


def main(d, split, outp=None):
    S.selftest(); check('Atlas self-test (synthetic tree, amended collapse)', True)
    synthetic_chain()
    train = sorted(json.load(open(split))['train620'])
    assert hashlib.sha256('\n'.join(train).encode()).hexdigest().startswith('1350cb1f')
    pick = sorted(train, key=lambda c: hashlib.sha256(('asclepius-j1f-r2-scorertest:' + c).encode()).hexdigest())[:6]
    names = ('identity', 'swap_D1D2', 'OM2_to_LCx', 'OM2_to_bg', 'dilate1', 'swap_PDAPLB', 'erode1', 'fold_OM',
             'drop_PLB', 'trunc_PDA_40')
    rows = {k: [] for k in names}
    for c in pick:
        im = nib.load(os.path.join(d, f'{int(c[1:]) + 1}.coronary.nii.gz'))
        icx = np.asarray(im.dataobj).astype(np.uint8); icx = icx[L.crop(icx, 12)]
        z = np.array(im.header.get_zooms()[:3], float)
        ref, _ = S.stage1_labels(icx, z)
        four, st = S.collapse4(ref, z)
        d25 = territory.to_four(icx, z)
        m = (icx > 0) & (icx != 14) & (ref != S.IGNORE)
        check(f'{c} collapse = D25 on every non-Other voxel ({int((four[m] != d25[m]).sum())} differ)',
              bool((four[m] == d25[m]).all()))
        check(f'{c} collapse fallbacks 0 ({st.get("fallback", 0)})', st.get('fallback', 0) == 0)
        p = np.where(ref == S.IGNORE, 0, ref).astype(np.uint8)
        rp = S.pieces_of(ref, z)
        preds = {'identity': p}
        q = p.copy(); q[p == V['D1']] = V['D2']; q[p == V['D2']] = V['D1']; preds['swap_D1D2'] = q
        q = p.copy(); q[p == V['OM2']] = V['LCx']; preds['OM2_to_LCx'] = q
        q = p.copy(); q[p == V['OM2']] = 0; preds['OM2_to_bg'] = q
        grow = ndi.grey_dilation(p, size=(3, 3, 3)); q = p.copy(); q[(p == 0) & (grow > 0)] = grow[(p == 0) & (grow > 0)]
        preds['dilate1'] = q
        q = p.copy(); q[p == V['PDA']] = V['PLB']; q[p == V['PLB']] = V['PDA']; preds['swap_PDAPLB'] = q
        preds['erode1'] = np.where(ndi.binary_erosion(p > 0), p, 0).astype(np.uint8)
        q = p.copy(); q[np.isin(p, (V['OM1'], V['OM2']))] = V['LCx']; preds['fold_OM'] = q
        q = p.copy(); q[p == V['PLB']] = 0; preds['drop_PLB'] = q
        preds['trunc_PDA_40'] = truncate(p, V['PDA'], 0.4, z)
        for k in names:
            rows[k].append(S.score_case(ref, preds[k], z, with_tf1=(k == 'identity'), ref_pieces=rp))
        print(c, 'scored', flush=True)
    A = {k: G.pool(v) for k, v in rows.items()}
    tf1 = {cl: [s[cl]['tf1'] for s in rows['identity'] if 'tf1' in s[cl]] for cl in G.GATED}
    for cl in G.GATED:
        a = A['identity'][cl]
        if not a['pieces']:
            continue
        check(f'identity {cl}: recall, agreement, naming = 1', a['recall'] == 1 and a['presence_agreement'] == 1 and a['naming'] == 1)
        check(f'identity {cl}: branch tF1 = 1 (min {min(tf1[cl]):.3f})', min(tf1[cl]) > 1 - 1e-6)
        dd = A['dilate1'][cl]
        check(f'dilate by 1 voxel {cl}: recall 1, naming 1', dd['recall'] == 1 and dd['naming'] == 1)
        e = A['erode1'][cl]
        check(f'erode by 1 voxel {cl}: recall >= 0.8 ({e["recall"]:.3f}), naming of detected = 1 ({e["naming"]:.3f})',
              e['recall'] >= 0.8 and e['naming'] == 1)
    for cl in ('D1', 'D2'):
        a = A['swap_D1D2'][cl]
        if a['pieces']:
            check(f'swap D1/D2 {cl}: recall 1, naming 0', a['recall'] == 1 and a['naming'] == 0)
    for cl in ('PDA', 'PLB'):
        a = A['swap_PDAPLB'][cl]
        if a['pieces']:
            check(f'swap PDA/PLB {cl}: recall 1, naming 0', a['recall'] == 1 and a['naming'] == 0)
    a, b = A['OM2_to_LCx']['OM2'], A['OM2_to_bg']['OM2']
    if a['pieces']:
        check('OM2 -> LCx: recall 1, naming 0, agreement < 1', a['recall'] == 1 and a['naming'] == 0 and a['presence_agreement'] < 1)
        check('OM2 -> background: recall 0', b['recall'] == 0)
    for cl in ('OM1', 'OM2'):
        f = A['fold_OM'][cl]
        if f['pieces']:
            check(f'OM folded into LCx {cl}: recall 1, naming 0', f['recall'] == 1 and f['naming'] == 0)
    a = A['drop_PLB']['PLB']
    check(f'PLB dropped: recall 0 ({a["recall"]})', a['recall'] == 0)
    a = A['trunc_PDA_40']['PDA']
    check(f'PDA truncated to 40 %: recall <= 0.2 ({a["recall"]:.3f})', a['recall'] <= 0.2)
    others = [A['drop_PLB'][cl]['recall'] == 1 for cl in G.GATED if cl != 'PLB' and A['drop_PLB'][cl]['pieces']]
    check('PLB dropped: every other class keeps recall 1', all(others))
    print('cases', pick)
    res = {'cases': pick, 'scorer_sha256': S.scorer_sha256(), 'pooled': A, 'checks': log, 'n_fail': len(fails)}
    if outp:
        json.dump(res, open(outp, 'w'), indent=1, default=float)
    print('ALL PASS' if not fails else f'{len(fails)} FAIL', f'({len(log)} checks)')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main(*sys.argv[1:4])
