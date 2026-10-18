"""Delta v9: the decisive score of an icx4 model on Fir (CPU job, after icx4's chain is DONE).

Scores icx4's predictions ($W/predictions/cNNNN.nii.gz) against ImageCAS-X collapsed to four classes exactly as icx4
trains (trillium/icx4/lib/territory.py), with the pinned tree-F1 (src/segtrain/tf1.py, A1c hash checked at start):

  * cases: ImageCAS-X val (80) and the 80 NON-sealed ImageCAS-X test cases (36 clean + 44 development).
    The 80 sealed cases (trillium/sealed_test.json, A14) are refused, whatever is asked;
  * ostium of record: ImageCAS-X's centreline start points (experiments/Delta/r9_expert_ostia.json), passed to
    segtrain.tf1.find_ostia as the "aorta" (1 mm balls). ImageCAS-X defines each start as the end within 5 mm of a
    TotalSegmentator aorta, so this is A1's rule with the aorta contact already resolved. With --aorta-dir
    (<case>_aorta.nii.gz from segtrain aorta / TotalSegmentator) the case is also scored with A1 as written and both
    are reported, paired (Delta v9 P2's check);
  * per case: decisive tF1 and per class (fallback centreline default), A1b flags, classes without centreline,
    FP components on the raw prediction (A2/A15 gate), per-class Dice as icx4's score.py computes it (for
    comparison with published Dice only; it decides nothing).

Writes <out>/per_case.jsonl (resumable), <out>/summary.json and <out>/SUMMARY.md.
Usage: score_tf1.py <W> <icx_dir> <repo_root> <out_dir> [--aorta-dir D] [--nproc N] [--only c0001,...]
"""
import argparse, hashlib, json, os, sys
from multiprocessing import Pool

import nibabel as nib
import numpy as np

PIN = '24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254'
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
MARGIN_MM = 8.0   # crop margin; > the 5 mm aorta contact and the 0.75 mm tolerance dilation
A = None          # parsed args, set in main (fork-inherited by the pool)


def dice(a, b):
    s = int(a.sum()) + int(b.sum())
    return None if s == 0 else 2.0 * int((a & b).sum()) / s


def balls(shape, pts_vox, sp, T, r_mm=1.0):
    m = np.zeros(shape, bool)
    b = T._ball(r_mm, sp)
    h = np.array(b.shape) // 2
    for v in pts_vox:
        c = np.round(v).astype(int)
        lo, hi = c - h, c + h + 1
        if np.any(hi <= 0) or np.any(lo >= shape):
            continue
        w = tuple(slice(max(lo[k], 0), min(hi[k], shape[k])) for k in range(3))
        bw = b[tuple(slice(w[k].start - lo[k], w[k].stop - lo[k]) for k in range(3))]
        m[w] |= bw
    return m


def one(case):
    from segtrain import tf1 as T
    from territory import to_four
    i = int(case[1:]) + 1
    li = nib.load(os.path.join(A.icx, f'{i}.coronary.nii.gz'))
    sp = np.asarray(li.header.get_zooms()[:3], float)
    ref = to_four(np.asarray(li.dataobj).astype(np.int64), sp).astype(np.uint8)
    pi = nib.load(os.path.join(A.w, 'predictions', f'{case}.nii.gz'))
    pred = np.asarray(pi.dataobj).astype(np.uint8)
    if pred.shape != ref.shape or not np.allclose(pi.affine, li.affine, atol=1e-3):
        return {'case': case, 'error': f'grid mismatch {pred.shape} vs {ref.shape}'}
    row = {'case': case, 'split': A.split_of[case]}
    # ostia from ImageCAS-X start points (LPS mm -> RAS -> voxel)
    o = A.ostia.get(case, {})
    inv = np.linalg.inv(li.affine)
    pts = [nib.affines.apply_affine(inv, np.asarray(q) * [-1, -1, 1]) for s in ('left', 'right') for q in o.get(s, [])]
    row['expert_ostia'] = {s: len(o.get(s, [])) for s in ('left', 'right')}
    aorta = None
    if A.aorta_dir:
        ap = os.path.join(A.aorta_dir, f'{case}_aorta.nii.gz')
        if os.path.exists(ap):
            aorta = np.asarray(nib.load(ap).dataobj) > 0
    # crop to everything that matters (reference, prediction, ostia), margin in mm
    fg = (ref > 0) | (pred > 0)
    nz = np.argwhere(fg)
    lo = nz.min(0); hi = nz.max(0) + 1
    for v in pts:
        lo = np.minimum(lo, np.floor(v).astype(int)); hi = np.maximum(hi, np.ceil(v).astype(int) + 1)
    mv = np.ceil(MARGIN_MM / sp).astype(int)
    lo = np.maximum(lo - mv, 0); hi = np.minimum(hi + mv, ref.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    r, p = ref[sl], pred[sl]
    for c in (1, 2, 3, 4):
        if (r == c).any() or (p == c).any():
            row[f'dice_{NAMES[c]}'] = dice(p == c, r == c)
    row['dice_tree'] = dice(p > 0, r > 0)
    row['fp_components'] = T.fp_components(r, p)
    if not (r > 0).any():
        row['empty_reference'] = True
        return row
    pseudo = balls(r.shape, [v - lo for v in pts], sp, T) if pts else None
    rep = T.find_ostia(r, sp, aorta=pseudo) if pseudo is not None and pseudo.any() else T.find_ostia(r, sp)
    t = T.tree_f1(r, p, sp, ostia=rep)
    flagged_classes = set()
    if rep.flagged:   # A1b: every class of a flagged tree (or of its side) is reported apart
        comp = T.components(r > 0)[0]
        for o_ in rep.flagged:
            cls = {int(x) for x in np.unique(r[comp == o_.tree]) if x}
            if o_.side == 'left':
                cls &= {1, 2, 3}
            elif o_.side == 'right':
                cls &= {4}
            flagged_classes |= cls
    # P2 flag rule: with an ImageCAS-X start point as the ostium, a tree is flagged only when its ostium of record
    # is not within 2 mm of a start point (no start point for that tree, or a start point off the reference
    # centreline). Disagreement with the CT-free 'thick' rule alone does not flag it (Delta v9 P2).
    p2_classes = set()
    pts_crop = [v - lo for v in pts]
    comp2 = None
    for o_ in rep.ostia:
        ok = o_.rule == 'aorta' and any(float(np.linalg.norm((np.array(o_.point) - v) * sp)) <= 2.0 for v in pts_crop)
        if not ok:
            comp2 = T.components(r > 0)[0] if comp2 is None else comp2
            cls = {int(x) for x in np.unique(r[comp2 == o_.tree]) if x}
            if o_.side == 'left':
                cls &= {1, 2, 3}
            elif o_.side == 'right':
                cls &= {4}
            p2_classes |= cls
    row['flagged_classes_p2'] = sorted(p2_classes)
    row.update({'tf1': t.tf1, **{f'tf1_{NAMES[c]}': v for c, v in t.per_class.items()},
                **{f'recall_{NAMES[c]}': v for c, v in t.recall.items()},
                **{f'precision_{NAMES[c]}': v for c, v in t.precision.items()},
                'provisional': t.provisional, 'flagged': t.flagged,
                'flagged_classes': sorted(flagged_classes),
                'classes_without_centreline': [NAMES[c] for c in t.classes_without_centreline],
                'ostia': [o_.as_row() for o_ in rep.ostia]})
    if aorta is not None:
        rep_a = T.find_ostia(r, sp, aorta=aorta[sl])
        ta = T.tree_f1(r, p, sp, ostia=rep_a)
        row['tf1_aorta'] = ta.tf1
        row.update({f'tf1_aorta_{NAMES[c]}': v for c, v in ta.per_class.items()})
        row['flagged_aorta'] = ta.flagged
        d = []
        for oe in rep.ostia:
            dd = [float(np.linalg.norm((np.array(oa.point) - np.array(oe.point)) * sp)) for oa in rep_a.ostia]
            d.append(round(min(dd), 2) if dd else None)
        row['ostium_expert_vs_aorta_mm'] = d
    return row


def boot_ci(x, n=2000, seed=0):
    x = np.asarray([v for v in x if v is not None and not np.isnan(v)], float)
    if len(x) == 0:
        return None, None, 0
    rng = np.random.default_rng(seed)
    m = rng.choice(x, (n, len(x))).mean(1)
    return round(float(x.mean()), 4), [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)], len(x)


def summarise(rows):
    out = {}
    for split in ('val', 'open_clean', 'open_dev', 'open_all'):
        rs = [r for r in rows if 'tf1' in r and (r['split'] == split or (split == 'open_all' and r['split'].startswith('open')))]
        if not rs:
            continue
        s = {'n': len(rs), 'tf1_all_trees': boot_ci([r['tf1'] for r in rs])}
        # decisive per class: flagged trees reported separately (A1b)
        for c, n in NAMES.items():
            key = f'tf1_{n}'
            un = [r[key] for r in rs if key in r and c not in r['flagged_classes']]
            fl = [r[key] for r in rs if key in r and c in r['flagged_classes']]
            s[n] = {'decisive': boot_ci(un), 'flagged': boot_ci(fl)[:1] + (len(fl),),
                    'dice_mean': boot_ci([r.get(f'dice_{n}') for r in rs if r.get(f'dice_{n}') is not None])[0]}
        dec = [np.mean([r[f'tf1_{n}'] for c, n in NAMES.items() if f'tf1_{n}' in r and c not in r['flagged_classes']])
               for r in rs if any(f'tf1_{n}' in r and c not in r['flagged_classes'] for c, n in NAMES.items())]
        s['decisive_macro'] = boot_ci(dec)
        # the same with Delta v9's P2 flag rule (flag only trees without a usable ImageCAS-X start point)
        for c, n in NAMES.items():
            key = f'tf1_{n}'
            s[n]['decisive_p2'] = boot_ci([r[key] for r in rs if key in r and c not in r['flagged_classes_p2']])
        dec2 = [np.mean([r[f'tf1_{n}'] for c, n in NAMES.items() if f'tf1_{n}' in r and c not in r['flagged_classes_p2']])
                for r in rs if any(f'tf1_{n}' in r and c not in r['flagged_classes_p2'] for c, n in NAMES.items())]
        s['decisive_macro_p2'] = boot_ci(dec2)
        s['cases_flagged_p2'] = sum(bool(r['flagged_classes_p2']) for r in rs)
        s['fp_components_per_case'] = boot_ci([r['fp_components'] for r in rs])
        s['cases_flagged'] = sum(bool(r['flagged_classes']) for r in rs)
        s['classes_without_centreline'] = sum(len(r['classes_without_centreline']) for r in rs)
        s['dice_tree_mean'] = boot_ci([r['dice_tree'] for r in rs])[0]
        if any('tf1_aorta' in r for r in rs):
            pairs = [(r['tf1'], r['tf1_aorta']) for r in rs if 'tf1_aorta' in r]
            s['tf1_expert_minus_aorta'] = boot_ci([a - b for a, b in pairs])
            dd = [d for r in rs for d in r.get('ostium_expert_vs_aorta_mm', []) if d is not None]
            s['ostium_expert_vs_aorta_mm'] = {'n': len(dd), 'median': float(np.median(dd)) if dd else None,
                                              'share_le_2mm': float(np.mean(np.array(dd) <= 2)) if dd else None,
                                              'share_le_5mm': float(np.mean(np.array(dd) <= 5)) if dd else None}
        out[split] = s
    return out


def main():
    global A
    ap = argparse.ArgumentParser()
    ap.add_argument('w'); ap.add_argument('icx'); ap.add_argument('root'); ap.add_argument('out')
    ap.add_argument('--aorta-dir'); ap.add_argument('--nproc', type=int, default=8)
    ap.add_argument('--only', default='', help='comma-separated case ids (self-test); sealed still refused')
    A = ap.parse_args()
    sys.path.insert(0, os.path.join(A.root, 'src'))
    sys.path.insert(0, os.path.join(A.root, 'trillium', 'icx4', 'lib'))
    h = hashlib.sha256(open(os.path.join(A.root, 'src/segtrain/tf1.py'), 'rb').read()).hexdigest()
    if h != PIN:
        sys.exit(f'[delta9] tf1.py sha256 {h} is not the pinned A1c hash {PIN}; refusing to score')
    S = json.load(open(os.path.join(A.root, 'trillium/sealed_test.json')))
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    clean = set(S['open_icx_test'])

    def ids(name):
        return ['c%04d' % (int(x) - 1) for x in open(os.path.join(A.icx, f'{name}.txt')).read().split()]
    val, test = ids('val'), ids('test')
    A.split_of = {c: 'val' for c in val}
    A.split_of.update({c: ('open_clean' if c in clean else 'open_dev') for c in test if c not in sealed})
    cases = sorted(A.split_of)
    assert not set(cases) & sealed, 'sealed case in the scoring list'
    if A.only:
        want = set(A.only.split(','))
        if want & sealed:
            sys.exit('[delta9] refusing: sealed case requested')
        cases = [c for c in cases if c in want]
    A.ostia = json.load(open(os.path.join(A.root, 'experiments/Delta/r9_expert_ostia.json')))['ostia']
    os.makedirs(A.out, exist_ok=True)
    pc = os.path.join(A.out, 'per_case.jsonl')
    done = {json.loads(l)['case'] for l in open(pc)} if os.path.exists(pc) else set()
    todo = [c for c in cases if c not in done]
    missing = [c for c in todo if not os.path.exists(os.path.join(A.w, 'predictions', f'{c}.nii.gz'))]
    if missing:
        sys.exit(f'[delta9] {len(missing)} predictions missing (first {missing[:5]}); is icx4 DONE?')
    nv = sum(A.split_of[c] == 'val' for c in cases)
    print(f'[delta9] {len(cases)} cases ({nv} val, {len(cases) - nv} open test; sealed refused), '
          f'{len(todo)} to score, aorta: {"yes" if A.aorta_dir else "no"}', flush=True)
    with Pool(A.nproc) as p, open(pc, 'a') as f:
        for k, r in enumerate(p.imap_unordered(one, todo), 1):
            f.write(json.dumps(r) + '\n'); f.flush()
            if k % 20 == 0:
                print(f'[delta9] {k}/{len(todo)}', flush=True)
    rows = [json.loads(l) for l in open(pc)]
    errs = [r for r in rows if 'error' in r]
    summ = {'tf1_sha256': h, 'n_rows': len(rows), 'errors': errs, 'splits': summarise(rows)}
    json.dump(summ, open(os.path.join(A.out, 'summary.json'), 'w'), indent=1)
    L = ['# Delta v9 decisive score of icx4 (tF1 @ 1.5 mm, A1c hash pinned; ostia = ImageCAS-X start points)', '',
         f'tf1.py sha256 `{h}`. Sealed cases refused. Flagged trees (A1b) are reported separately, not in "decisive".', '']
    for split, s in summ['splits'].items():
        L += [f'## {split} (n = {s["n"]})', '',
              f'- Decisive macro tF1: **{s["decisive_macro"][0]}** (95 % bootstrap CI {s["decisive_macro"][1]}); '
              f'all trees: {s["tf1_all_trees"][0]}; with the P2 flag rule: {s["decisive_macro_p2"][0]} '
              f'(CI {s["decisive_macro_p2"][1]}, {s["cases_flagged_p2"]} cases flagged)',
              f'- FP components per case (raw, A15 gate ≤ 1): {s["fp_components_per_case"][0]} '
              f'(CI {s["fp_components_per_case"][1]})',
              f'- Cases with a flagged tree: {s["cases_flagged"]}; classes without centreline (fallback used): '
              f'{s["classes_without_centreline"]}; whole-tree Dice {s["dice_tree_mean"]}', '',
              '| Class | Decisive tF1 (CI, n) | P2 flags: tF1 (CI, n) | Flagged trees: mean (n) | Dice (report only) |',
              '|---|---|---|---|---|']
        for n in NAMES.values():
            d = s[n]['decisive']
            d2 = s[n]['decisive_p2']
            L.append(f'| {n} | {d[0]} ({d[1]}, {d[2]}) | {d2[0]} ({d2[1]}, {d2[2]}) | {s[n]["flagged"][0]} '
                     f'({s[n]["flagged"][1]}) | {s[n]["dice_mean"]} |')
        if 'tf1_expert_minus_aorta' in s:
            L += ['', f'- Expert-ostium minus TotalSegmentator-ostium tF1: {s["tf1_expert_minus_aorta"]}; '
                      f'ostium distance: {s["ostium_expert_vs_aorta_mm"]}']
        L.append('')
    if errs:
        L.append(f'**{len(errs)} cases failed**: {[e["case"] for e in errs[:10]]}')
    open(os.path.join(A.out, 'SUMMARY.md'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))
    sys.exit(1 if errs else 0)


if __name__ == '__main__':
    main()
