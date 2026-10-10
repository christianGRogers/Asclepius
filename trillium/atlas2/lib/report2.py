"""Write results/ for Atlas run 2 (SUMMARY.md, results.json, small per-case tables). Runs on partial results too.
Usage: report2.py <workdir> <results_dir>"""
import glob
import json
import os
import re
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score  # noqa: E402

W, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)


def load(p):
    return json.load(open(p)) if os.path.exists(p) else None


res = dict(generated=time.strftime('%Y-%m-%d %H:%M:%S'), workdir=W, sealed_cases_touched=False)
for k in ('tf1_hash.json', 'window_b.json', 'timings.json', 'layout_summary.json'):
    v = load(f'{W}/{k}')
    if v is not None:
        res[k[:-5]] = v
A, B = load(f'{W}/score_run1.json'), load(f'{W}/score_b.json')


def compact(arm, S):
    if not S:
        return None
    rows = []
    for p in S['per_case']:
        a1 = p['a1']
        rows.append(dict(case=p['case'], tf1=a1['tf1'], tf1_tol0=a1['tf1_tol0'], per_class=a1['per_class'],
                         decisive=score.decisive_case_score(dict(a1, per_class={int(k): v for k, v in a1['per_class'].items()},
                                                                 flagged_classes=[int(c) for c in a1['flagged_classes']])),
                         flagged_classes=a1['flagged_classes'], provisional=a1['provisional'],
                         fp_components=a1['fp_components'], ostia=a1['ostia'],
                         sweep=p.get('sweep'), has_aorta=p['has_aorta']))
    json.dump(rows, open(f'{OUT}/per_case_{arm}.json', 'w'), indent=0)
    cen = [dict(case=p['case'], **r) for p in S['per_case'] for r in p['census']]
    json.dump(cen, open(f'{OUT}/census_{arm}.json', 'w'), indent=0)
    return S['summary']


res['run1'] = compact('run1', A)
res['run1_errors'] = A['errors'] if A else None
res['b'] = compact('b', B)
res['b_errors'] = B['errors'] if B else None
if A and B:
    pr = score.paired(A['per_case'], B['per_case'])
    res['paired_b_minus_run1'] = pr
    res['window_decision'] = score.decide_window(pr)
M36 = load(f'{W}/open36/manifest_open36.json')
if M36:
    res['open36'] = dict(n=len(M36['cases']), predicted=len(M36['predicted']), manifest='open36_manifest.json')
    json.dump(M36, open(f'{OUT}/open36_manifest.json', 'w'), indent=1)
fold_b = glob.glob(f'{W}/nnunet_results/Dataset714_*/nnUNetTrainerAtlas__*/fold_0')
if fold_b:
    txt = ''.join(open(f).read() for f in sorted(glob.glob(f'{fold_b[0]}/training_log_*.txt')))
    et = [float(x) for x in re.findall(r'Epoch time: ([0-9.]+) s', txt)]
    res['b_training'] = dict(epochs_completed=len(et), s_per_epoch_median=float(np.median(et)) if et else None,
                             stopped_at_deadline='ATLAS: stopping' in txt, fold_dir=fold_b[0],
                             paired_412=len(et) == 412)
json.dump(res, open(f'{OUT}/results.json', 'w'), indent=1)


def f(x, nd=3):
    return 'n/a' if x is None else (f'{x:.{nd}f}' if isinstance(x, float) else str(x))


def arm_lines(name, s):
    if not s:
        return [f'*{name}: not scored.*', '']
    c = s.get('census', {})
    L = [f'| {name} | {f(s["decisive_macro_tf1"])} (n={s["n_decisive_cases"]}) | '
         + ' / '.join(f(s['decisive_per_class'][k]) for k in ('LM', 'LAD', 'LCx', 'RCA'))
         + f' | {s["n_flagged_class_trees"]}/{s["n_class_trees"]} | {f(s["all_macro_tf1_incl_flagged"])} | '
         f'{f(s["fp_components_mean"], 2)} ({s["fp_cases_le_1"]}/{s["n"]} ≤ 1) | {s["n_provisional"]} |']
    return L, c, s.get('sweep'), s.get('ostium_validation')


lines = ['# Atlas run 2: A1 re-score and FP census of run 1, and the A2 window ablation', '',
         f'Generated {res["generated"]}. Machine-readable: `results.json`; per case: `per_case_run1.json`, '
         '`per_case_b.json`; FP components: `census_run1.json`, `census_b.json`.', '',
         f'Metric: `segtrain.tf1` sha256 `{(res.get("tf1_hash") or {}).get("sha256", "n/a")}` '
         f'(frozen hash match: {(res.get("tf1_hash") or {}).get("match", "n/a")}). Ostium of record: centreline voxel '
         'nearest the TotalSegmentator aorta (A1). Decisive aggregate: aorta present (A1a), flagged trees left out (A1b).', '',
         '| arm | decisive macro tF1 @1.5 | per class LM / LAD / LCx / RCA (unflagged) | flagged trees | macro incl. flagged | FP comps / case | provisional cases |',
         '|---|---|---|---|---|---|---|']
extra = []
for name, key in (('run 1 (fixed window [−300, 1300])', 'run1'), ('B (default window)', 'b')):
    out = arm_lines(name, res.get(key))
    if isinstance(out, list):
        extra += out; continue
    L, c, sw, ov = out
    lines += L
    extra += [f'### FP census, {name}', '']
    if c.get('n_components'):
        extra += ['| category | components | share | mm³ | share of volume |', '|---|---|---|---|---|']
        for k, v in c['by_category'].items():
            extra.append(f"| {k} | {v['n']} | {f(v['share_n'], 2)} | {f(v['mm3'], 0)} | {f(v['share_mm3'], 2)} |")
        extra += ['', f"Majority by count: **{c.get('majority_by_count')}** (A15 routing: low_confidence → global threshold; "
                  'icx_vessel → question for the humans; confident_other → reopens the recipe).', '']
    if sw:
        extra += ['Global vessel-probability threshold (A15; val only, not yet chosen):', '',
                  '| t | macro tF1 (all trees) | FP comps / case |', '|---|---|---|']
        extra += [f"| {t} | {f(v['tf1'])} | {f(v['fp_components'], 2)} |" for t, v in sw.items()]
        extra.append('')
    if ov:
        extra += [f"Ostium validation (ImageCAS-X start points, validation only): {ov['n']} ostia, median "
                  f"{f(ov['median_mm'], 1)} mm, {ov['within_5mm']} within 5 mm, {ov['flagged']} flagged, "
                  f"{ov['silent_misses']} silent misses (> 5 mm, unflagged).", '']
lines.append('')
if res.get('paired_b_minus_run1'):
    p = res['paired_b_minus_run1']; t, q = p['tf1_b_minus_a'], p['fp_b_minus_a']
    lines += ['## Window decision (A16, rule fixed before the run)', '',
              f"Paired B − run 1 on {p['n_cases']} cases: decisive tF1 {f(t['mean'], 4)} "
              f"[{f(t['ci'][0], 4) if t['ci'] else 'n/a'}, {f(t['ci'][1], 4) if t['ci'] else 'n/a'}] "
              f"(better/worse {t.get('better')}/{t.get('worse')}); FP {f(q['mean'], 3)} "
              f"[{f(q['ci'][0], 3) if q['ci'] else 'n/a'}, {f(q['ci'][1], 3) if q['ci'] else 'n/a'}] per case.", '',
              f"**Winner: {res['window_decision']['winner']}** — {res['window_decision']['reason']}.", '']
    bt = res.get('b_training') or {}
    if not bt.get('paired_412'):
        lines += [f"Caution: B completed {bt.get('epochs_completed')} epochs, not 412; the pairing is weakened.", '']
lines += extra
if res.get('open36'):
    lines += ['## The 36 clean open test cases (for Bridge)', '',
              f"Predicted {res['open36']['predicted']}/{res['open36']['n']} with run 1's checkpoint, softmax saved; "
              'paths and command in `open36_manifest.json` (volumes stay on $SCRATCH). No sealed case was touched.', '']
lines += ['Reading: `vault/Plans/Experiments/Atlas - Pending Trillium run 2, A1 re-score, FP census and the window ablation.md`.']
open(f'{OUT}/SUMMARY.md', 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
