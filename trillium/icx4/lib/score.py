"""Stage D: check the 1000 predictions, score the held-out ImageCAS-X test cases, write results/.
  * every prediction must load; unreadable ones (a job killed mid-write) are deleted so the next chunk redoes them;
  * on the ImageCAS-X test split (never trained on), against ImageCAS-X collapsed to the four classes exactly as
    prepare.py collapses the training labels: per-class Dice and detection (class present in both), whole-tree Dice;
  * a per-case table of which classes each prediction contains (all 1000), for the SegQueue hand-off.
Usage: score.py <workdir> <icx_dir> <results_dir> <n_proc>   (exit 3 = predictions missing or broken)"""
import os, sys, json, statistics
from multiprocessing import Pool
import numpy as np, nibabel as nib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from territory import to_four  # noqa: E402

W, ICX, OUT, NP = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
NAMES = ['LM', 'LAD', 'LCx', 'RCA']
PRED = f'{W}/predictions'
cases = json.load(open(f'{W}/layout.json'))['cases']
splits = json.load(open(f'{W}/splits.json'))
os.makedirs(OUT, exist_ok=True)


def dice(a, b):
    s = int(a.sum()) + int(b.sum())
    return None if s == 0 else 2.0 * int((a & b).sum()) / s


def check(c):
    p = f'{PRED}/{c}.nii.gz'
    if not os.path.exists(p):
        return c, None
    try:
        a = np.asarray(nib.load(p).dataobj)
    except Exception:
        os.remove(p)
        return c, None
    return c, [int(v) for v in np.unique(a) if v]


def score(c):
    pr = np.asarray(nib.load(f'{PRED}/{c}.nii.gz').dataobj).astype(np.uint8)
    li = nib.load(os.path.join(ICX, f'{int(c[1:]) + 1}.coronary.nii.gz'))
    rf = to_four(np.asarray(li.dataobj).astype(np.int64), li.header.get_zooms()).astype(np.uint8)
    r = {'case': c, 'tree': dice(pr > 0, rf > 0), 'cls': {}}
    for k, n in enumerate(NAMES, 1):
        a, b = pr == k, rf == k
        r['cls'][n] = {'dice': dice(a, b), 'in_ref': bool(b.any()), 'in_pred': bool(a.any())}
    return r


with Pool(NP) as p:
    present = dict(p.map(check, sorted(cases)))
missing = [c for c, v in present.items() if v is None]
json.dump({'n_cases': len(present), 'missing': missing,
           'classes_per_case': {c: [NAMES[k - 1] for k in v] for c, v in present.items() if v is not None}},
          open(f'{OUT}/predictions_index.json', 'w'))
if missing:
    print(f'[score] {len(missing)} of {len(present)} predictions missing or unreadable (first {missing[:5]})')
    sys.exit(3)

test = [c for c in splits['test'] if c in cases]
with Pool(NP) as p:
    rows = p.map(score, test)
json.dump(rows, open(f'{OUT}/per_case_test.json', 'w'))


def mean(xs):
    xs = [x for x in xs if x is not None]
    return (round(statistics.mean(xs), 4), len(xs)) if xs else (None, 0)


summ = {'n_test': len(rows), 'tree_dice': mean(r['tree'] for r in rows)[0], 'per_class': {}}
for n in NAMES:
    d, k = mean(r['cls'][n]['dice'] for r in rows if r['cls'][n]['in_ref'] and r['cls'][n]['in_pred'])
    ref = sum(r['cls'][n]['in_ref'] for r in rows)
    hit = sum(r['cls'][n]['in_ref'] and r['cls'][n]['in_pred'] for r in rows)
    fp = sum(r['cls'][n]['in_pred'] and not r['cls'][n]['in_ref'] for r in rows)
    summ['per_class'][n] = {'dice_when_both_present': d, 'cases_in_ref': ref, 'found': hit, 'predicted_but_absent': fp,
                            'dice_all_ref_cases': mean((r['cls'][n]['dice'] or 0.0) for r in rows
                                                       if r['cls'][n]['in_ref'])[0]}
macro = [v['dice_all_ref_cases'] for v in summ['per_class'].values() if v['dice_all_ref_cases'] is not None]
summ['macro_dice_4'] = round(statistics.mean(macro), 4) if macro else None
json.dump(summ, open(f'{OUT}/results.json', 'w'), indent=1)

L = ['# icx4 results: 4-class model (LM, LAD, LCx, RCA) on ImageCAS-X', '',
     f'Held-out ImageCAS-X test split: {len(rows)} cases (never seen in training). Reference: ImageCAS-X as drawn, '
     'collapsed to the four classes by territory (D25).', '',
     f'- Whole-tree Dice (any vessel vs any vessel): **{summ["tree_dice"]}**',
     f'- Macro Dice over the 4 classes (a missed class scores 0): **{summ["macro_dice_4"]}**', '',
     '| Class | Cases with it (ref) | Found | Predicted but absent | Dice, all ref cases | Dice when both present |',
     '|---|---|---|---|---|---|']
for n, v in summ['per_class'].items():
    L.append(f'| {n} | {v["cases_in_ref"]} | {v["found"]} | {v["predicted_but_absent"]} | '
             f'{v["dice_all_ref_cases"]} | {v["dice_when_both_present"]} |')
L += ['', f'Predictions for all {len(present)} cases are in `{PRED}/` (uint8 NIfTI, labels 1-4 in the order above).']
for f in ('label_census.json', 'planner_output.json', 'timings.json'):
    if os.path.exists(f'{W}/{f}'):
        L.append(f'- `{f}`: ' + open(f'{W}/{f}').read().replace('\n', ' ')[:600])
open(f'{OUT}/SUMMARY.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
