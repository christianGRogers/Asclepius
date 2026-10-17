"""Write results/ for Atlas run 3, the FP-aware loss pilot (SUMMARY.md, results.json, small per-case tables).
Runs on partial results too. Usage: report3.py <workdir> <results_dir>"""
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
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}


def load(p):
    return json.load(open(p)) if os.path.exists(p) else None


res = dict(generated=time.strftime('%Y-%m-%d %H:%M:%S'), workdir=W, sealed_cases_touched=False)
for k in ('tf1_hash.json', 'schedule.json', 'timings.json', 'run2_inputs.json'):
    v = load(f'{W}/{k}')
    if v is not None:
        res[k[:-5]] = v
arms = {a: load(f'{W}/score_{a}.json') for a in ('F0', 'F1')}


def epochs_of(arm):
    fs = glob.glob(f'{W}/nnunet_results/*/nnUNetTrainer_segtrain_fppilot_{arm}__*/fold_0/training_log_*.txt')
    txt = ''.join(open(f).read() for f in sorted(fs))
    et = [float(x) for x in re.findall(r'Epoch time: ([0-9.]+) s', txt)]
    fp = [float(x) for x in re.findall(r'FP term \(epoch mean\): ([0-9.]+)', txt)]
    return dict(epochs_completed=len(et), s_per_epoch_median=float(np.median(et)) if et else None,
                paused='wall-clock budget reached' in txt, fp_term_first=fp[0] if fp else None,
                fp_term_last=fp[-1] if fp else None)


def split_means(S, key, sub=None):
    out = {}
    for c in (1, 2, 3, 4):
        v = []
        for p in S['per_case']:
            d = (p.get('split') or {}).get(key) or {}
            d = d.get(sub) if sub else d
            if d is None:
                continue
            x = d.get(str(c), d.get(c))
            if x is not None:
                v.append(x)
        out[NAMES[c]] = dict(n=len(v), mean=float(np.mean(v)) if v else None)
    return out


def paired_split(A, B, key, sub=None, n_boot=5000):
    a = {p['case']: p for p in A['per_case']}
    b = {p['case']: p for p in B['per_case']}
    rng = np.random.default_rng(0)
    out = {}
    for c in (1, 2, 3, 4):
        d = []
        for case in sorted(set(a) & set(b)):
            xa = ((a[case].get('split') or {}).get(key) or {})
            xb = ((b[case].get('split') or {}).get(key) or {})
            if sub:
                xa, xb = xa.get(sub) or {}, xb.get(sub) or {}
            va, vb = xa.get(str(c), xa.get(c)), xb.get(str(c), xb.get(c))
            if va is not None and vb is not None:
                d.append(vb - va)
        if d:
            d = np.asarray(d)
            bs = rng.choice(d, (n_boot, len(d))).mean(axis=1)
            out[NAMES[c]] = dict(n=len(d), mean=float(d.mean()),
                                 ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    return out


for a, S in arms.items():
    if S:
        res[a] = dict(summary=S['summary'], training=epochs_of(a), errors=S['errors'],
                      recall_icx_traced=split_means(S, 'recall_icx_traced'),
                      recall_maskonly_lowhu=split_means(S, 'recall_maskonly_lowhu'),
                      a23_per_class=split_means(S, 'a23', 'per_class'))
        rows = [dict(case=p['case'], tf1=p['a1']['tf1'], per_class=p['a1']['per_class'],
                     flagged_classes=p['a1']['flagged_classes'], fp_components=p['a1']['fp_components'],
                     split=p.get('split')) for p in S['per_case']]
        json.dump(rows, open(f'{OUT}/per_case_{a}.json', 'w'), indent=0)
        json.dump([dict(case=p['case'], **r) for p in S['per_case'] for r in p['census']],
                  open(f'{OUT}/census_{a}.json', 'w'), indent=0)
if arms['F0'] and arms['F1']:
    pr = score.paired(arms['F0']['per_case'], arms['F1']['per_case'])
    ep = [res['F0']['training']['epochs_completed'], res['F1']['training']['epochs_completed']]
    paused = res['F0']['training']['paused'] or res['F1']['training']['paused']
    res['paired_F1_minus_F0'] = pr
    res['decision'] = score.decide_fp_term(pr, epochs=ep if not paused else ep + [-1])
    res['paired_split'] = {k: paired_split(arms['F0'], arms['F1'], k, s) for k, s in
                           (('recall_icx_traced', None), ('recall_maskonly_lowhu', None), ('a23', 'per_class'))}
json.dump(res, open(f'{OUT}/results.json', 'w'), indent=1)


def f(x, nd=3):
    return 'n/a' if x is None else (f'{x:.{nd}f}' if isinstance(x, float) else str(x))


h = res.get('tf1_hash') or {}
L = ['# Atlas run 3: the FP-aware loss pilot (Round 8, A24)', '',
     f'Generated {res["generated"]}. Machine-readable: `results.json`; per case: `per_case_F0.json`, `per_case_F1.json`; '
     'FP components: `census_F0.json`, `census_F1.json`.', '',
     f'Metric: `segtrain.tf1` sha256 `{h.get("sha256", "n/a")}` (pinned: {h.get("match", "n/a")}); fallback centreline '
     'default; A1 ostium from atlas2\'s TotalSegmentator aortas. Both arms: warm from run 2\'s B (default window), '
     f'A17a trainer, seed {os.environ.get("SEGTRAIN_SEED", "12345")}, same data stream, '
     f'{(res.get("schedule") or {}).get("epochs", "n/a")} epochs each.', '',
     '| arm | epochs | decisive macro tF1 | LM / LAD / LCx / RCA (unflagged) | FP comps / case (≤ 1) | confident_other | FP term first → last |',
     '|---|---|---|---|---|---|---|']
for a in ('F0', 'F1'):
    r = res.get(a)
    if not r:
        L.append(f'| {a} | not scored | | | | | |')
        continue
    s, t = r['summary'], r['training']
    co = ((s.get('census') or {}).get('by_category') or {}).get('confident_other', {}).get('n')
    L.append(f"| {a} | {t['epochs_completed']}{' (paused)' if t['paused'] else ''} | {f(s['decisive_macro_tf1'])} | "
             + ' / '.join(f(s['decisive_per_class'][k]) for k in ('LM', 'LAD', 'LCx', 'RCA'))
             + f" | {f(s['fp_components_mean'], 2)} ({s['fp_cases_le_1']}/{s['n']}) | {co} | "
             f"{f(t['fp_term_first'], 4)} → {f(t['fp_term_last'], 4)} |")
L.append('')
d = res.get('decision')
if d:
    p = res['paired_F1_minus_F0']
    L += ['## Decision (A24.2, fixed before the run)', '',
          f"Paired F1 − F0 on {p['n_cases']} cases: decisive tF1 {f(d.get('tf1_mean'), 4)}, case CI "
          f"{f(p['tf1_b_minus_a']['ci'][0], 4)}..{f(p['tf1_b_minus_a']['ci'][1], 4)}, **seed-inclusive CI "
          f"{f((d.get('tf1_seed_ci') or [None])[0], 4)}..{f((d.get('tf1_seed_ci') or [None, None])[1], 4)}** "
          f"(σ_seed {d.get('sigma_seed')}); FP {f(d.get('fp_mean'), 3)} per case, CI "
          f"{f((d.get('fp_ci') or [None])[0], 3)}..{f((d.get('fp_ci') or [None, None])[1], 3)}. "
          f"Single-seed label: {d.get('single_seed_label')}.", '',
          f"**Verdict: {d['verdict']}** — {d['reason']}.", '']
    L += ['## Per class, alongside (A24.3; report only)', '',
          '| class | recall, ImageCAS-X-traced F0 → F1 (Δ, CI) | recall, mask-only low-HU F0 → F1 (Δ, CI) | A23 contrast-supported tF1 F0 → F1 (Δ, CI) |',
          '|---|---|---|---|']
    ps = res['paired_split']
    for c in ('LM', 'LAD', 'LCx', 'RCA'):
        cells = []
        for key, mk in (('recall_icx_traced', 'recall_icx_traced'), ('recall_maskonly_lowhu', 'recall_maskonly_lowhu'),
                        ('a23', 'a23_per_class')):
            m0 = res['F0'][mk][c]['mean']; m1 = res['F1'][mk][c]['mean']; q = ps[key].get(c)
            cells.append(f"{f(m0)} → {f(m1)} ({f(q['mean'], 3) if q else 'n/a'}, "
                         f"{f(q['ci'][0], 3) if q else ''}..{f(q['ci'][1], 3) if q else ''})")
        L.append(f'| {c} | ' + ' | '.join(cells) + ' |')
    L.append('')
L += ['Reading: `vault/Plans/Experiments/Atlas - Pending Trillium run 3, the FP-aware loss pilot.md`.']
open(f'{OUT}/SUMMARY.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
