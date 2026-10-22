"""Round 10 (#86): the pre-registered reading of icx4's first result, mechanically, with no choice made after the data.

Inputs (Fir login node, CPU; the Master plan's step 4 produces them):
  * `results/` from `./icx4 collect`: tf1_per_case.json (in-job decisive tF1 on open-36 + dev-44), per_case_test.json
    (in-job Dice), results.json;
  * `r9_open36_check.json` and `r9_tf1_val.json` from `experiments/Atlas/r9_score_icx4.py`;
  * optional: Delta's P2 run (`experiments/Delta/r9_fir/score_tf1.py ... --aorta-dir $W/aorta`) -> its summary.json;
  * optional: the A15 census of icx4's val (`r10_read_icx4.py census`, below) -> census JSON.

`read` prints, in this order, and writes a JSON verdict (and fills the vault note template):
  1. **A26 identity check** (Round 9 A26, verbatim below): r9_score_icx4.py's open-36 rows must equal the in-job
     tf1_per_case.json per case and per class (tF1, per-class tF1, flagged classes, provisional, FP components).
     If not: STOP. Nothing below decides anything.
  2. **A27**: every row of the reading table that fires on val 80, printed in A27's wording (verbatim, checked by a
     test against `vault/Plans/Judgements/Round 9.md`). For a class < 0.80, its 10 worst val cases are listed.
  3. **A29**: Delta's pre-registered P2 rule (ostia within 2 mm in >= 95 % of trees AND |delta macro tF1| <= 0.005), read
     on val 80 (Delta v9 §5: "read on val 80"); A26 says a rule is "validated on open-36, never set on it", so the
     same rule is also read on open-36: pass on both -> adopted; val only -> reported, not adopted; val fails ->
     withdrawn.
  4. **A15**: FP components per case on val 80 (raw, A2): <= 1 or > 1; with > 1, atlas2's census categories and its
     majority rule (`trillium/atlas2/lib/score.py`, categories fixed in Round 5).

`census` runs atlas2's own `census()` (icx_vessel / low_confidence / confident_other, fixed before any result) on
icx4's val 80. Its confidence split needs the softmax: icx4 does not save it, so without `--npz-dir` every component
not near ImageCAS-X is `unknown_no_softmax`, and the command for a val-80 re-prediction with probabilities
(about 1 GPU-h) is printed. Sealed cases are never read (val 80 has none; the list is refused if it did).

Usage:
  python r10_read_icx4.py read --results DIR --open36 r9_open36_check.json --val r9_tf1_val.json \
      [--delta DELTA/summary.json] [--census CENSUS.json] [--out VERDICT.json] \
      [--note-template "vault/.../icx4 - Results (pending).md" --note-out NOTE.md]
  python r10_read_icx4.py census --W $SCRATCH/icx4 --out CENSUS.json [--npz-dir DIR] [--np 8]
Exit codes (read): 0 read complete; 2 A26 STOP; 3 A27 Stop; 4 inputs missing or sealed case present.
"""
import argparse
import datetime
import importlib.util
import json
import math
import os
import re
import sys
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
LIB = os.path.join(ROOT, 'trillium', 'icx4', 'lib')
NAMES = ['LM', 'LAD', 'LCx', 'RCA']
COMPARED = ('tf1', 'per_class', 'flagged_classes', 'provisional', 'fp_components')

# ---- Round 9 wording, verbatim (tests/test_atlas_r10_read_icx4.py checks every string against Round 9.md) ----------
A26_RULE = ('Before its val numbers decide anything, it must reproduce the in-job `tf1_per_case.json` on open-36, '
            'given the same predictions and the in-job aortas (`$SCRATCH/icx4/aorta`): identical per case and per class.')
A27 = {   # key: (Result cell, Then cell)
    'stop': ('Macro < 0.80', '**Stop.** Something is wrong with the job, the collapse, the resume or the scorer, not '
             'the recipe. Check 5 val cases end to end before more GPU is spent (Bridge, Crucible)'),
    'reopen': ('0.80 ≤ macro < 0.85', 'The recipe reopens. First: the flagged and provisional share, the per-class '
               'split, and a cut census on ImageCAS-X (Atlas R2)'),
    'class': ('Any class < 0.80, or LCx < 0.80', "Review that class's 10 worst val cases (calcified and "
              'side-branch-heavy LCx first) before any fine-tune. The Round 8 LCx guard of 0.83 was set on the thick '
              'mask and is replaced by 0.80 (Atlas R3). On ImageCAS-X the LCx class is 35 % side branch (Crucible, '
              'Atlas), and its human inter-observer DSC is 84.8 ± 19.8'),
    'flagged': ('Flagged trees > 30 % in any class', 'The A1b review comes first, and decisions on that class wait '
                'for it (Bridge)'),
    'dice': ('Whole-tree Dice on the open 80 < 88.3', 'Report only: check preprocessing, collapse and window before '
             "the predictions are used (Foxtrot F7.1). Indicative, not paired: ImageCAS-X's Table 2 includes our "
             'sealed 80'),
    'fp_ok': ('FP per case ≤ 1 (A15 met)', "A24's FP-loss line is closed (Delta row 5)"),
    'fp_high': ('FP per case > 1', "Run atlas2's census script on icx4's val. If confident components beside the tree "
                'dominate again, a properly weighted FP term (5–20 % of the loss) becomes a two-seed candidate (A22), '
                'not a single run'),
}
A29_PASS = ('if it passes, P2 becomes the rule of record **for ImageCAS-X references only**, together with its flag '
            'rule;')
A29_FAIL = 'if it fails, P2 is withdrawn.'
A29_RULE = 'ostia within 2 mm in ≥ 95 % of trees, **and** |Δ macro tF1| ≤ 0.005;'
A26_OPEN = 'A decision whose sign reverses on open-36 is reported, not adopted.'
A26_RULES = 'Any **rule or threshold** (post-processing, P2 below) is validated on open-36, never set on it'
# thresholds, as written in A27 / A29 (none is new)
MACRO_STOP, MACRO_REOPEN, CLASS_MIN, FLAG_MAX, DICE_MIN, FP_MAX = 0.80, 0.85, 0.80, 0.30, 88.3, 1.0
P2_SHARE, P2_DELTA = 0.95, 0.005


class InputError(RuntimeError):
    pass


def _load(path, what):
    if not path or not os.path.exists(path):
        raise InputError(f'{what} not found: {path}')
    with open(path) as f:
        return json.load(f)


def _sealed():
    with open(os.path.join(ROOT, 'trillium', 'sealed_test.json')) as f:
        S = json.load(f)
    return S, set(S['sealed_icx_test']) | set(S['sealed_quality0'])


def _refuse_sealed(cases, where):
    _, sealed = _sealed()
    bad = sorted(set(cases) & sealed)
    if bad:
        raise InputError(f'{where} holds sealed cases {bad[:5]}: refusing to read it (A14)')


def _same(a, b):
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


# ------------------------------------------------------------------------------------------------------- A26
def a26_identity(job_tf1, check):
    """Per case and per class: the r9 open-36 rows against the in-job tf1_per_case.json rows."""
    S, _ = _sealed()
    open36 = sorted(S['open_icx_test'])
    job = {r['case']: r for r in job_tf1.get('per_case', [])}
    mine = {r['case']: r for r in check.get('rows', []) if 'error' not in r}
    problems = []
    if job_tf1.get('tf1_sha256') != check.get('tf1_sha256'):
        problems.append(f"metric hash differs: job {job_tf1.get('tf1_sha256')} vs check {check.get('tf1_sha256')}")
    if check.get('set') != 'open36':
        problems.append(f"the check was run with --set {check.get('set')}, not open36")
    for c in open36:
        if c not in job:
            problems.append(f'{c}: no in-job tF1 row')
            continue
        if c not in mine:
            problems.append(f'{c}: no r9_score_icx4 row' + (' (error)' if any(r['case'] == c for r in check.get('rows', [])) else ''))
            continue
        for k in COMPARED:
            if not _same(job[c].get(k), mine[c].get(k)):
                problems.append(f'{c}: {k} differs (job {job[c].get(k)!r} vs check {mine[c].get(k)!r})')
    return {'ok': not problems, 'n_open36': len(open36), 'n_compared': sum(c in job and c in mine for c in open36),
            'fields': list(COMPARED), 'problems': problems}


# ------------------------------------------------------------------------------------------------------- A27
def decisive_trees(rows, cls):
    """(case, tF1) of the decisive trees of a class: non-provisional case, class present, its tree not flagged."""
    return [(r['case'], r['per_class'][cls]) for r in rows
            if 'error' not in r and not r['provisional'] and cls in r['per_class'] and cls not in r['flagged_classes']]


def flagged_share(rows, cls):
    trees = [r for r in rows if 'error' not in r and not r['provisional'] and cls in r['per_class']]
    n_flag = sum(cls in r['flagged_classes'] for r in trees)
    return (n_flag / len(trees) if trees else None), n_flag, len(trees)


def open80_tree_dice(results_dir):
    p = os.path.join(results_dir, 'per_case_test.json')
    if os.path.exists(p):
        with open(p) as f:
            rows = json.load(f)
        _refuse_sealed([r['case'] for r in rows], 'per_case_test.json')
        xs = [r['tree'] for r in rows if r.get('tree') is not None]
        return (100.0 * sum(xs) / len(xs), len(xs)) if xs else (None, 0)
    res = _load(os.path.join(results_dir, 'results.json'), 'results.json')
    g = [res['groups'][k]['dice'] for k in ('open36', 'dev44')]
    n = sum(d['n'] for d in g)
    return (100.0 * sum(d['tree_dice'] * d['n'] for d in g) / n, n) if n else (None, 0)


def a27_reading(val, dice_open80):
    """Which A27 rows fire on val 80, with the evidence for each."""
    s, rows = val['summary'], val['rows']
    _refuse_sealed([r['case'] for r in rows], 'r9_tf1_val.json')
    macro = s.get('decisive_macro_tf1')
    fired, info = [], {'macro': macro, 'macro_ci': s.get('decisive_macro_tf1_ci'),
                       'n_decisive_cases': s.get('n_decisive_cases'), 'n_scored': s.get('n_scored'),
                       'provisional_cases': s.get('provisional_cases'), 'errors': s.get('errors'),
                       'per_class': {}, 'fp_val': s.get('fp_components_mean'), 'fp_cases_le_1': s.get('fp_cases_le_1'),
                       'dice_open80': dice_open80[0], 'n_dice_open80': dice_open80[1]}
    if macro is None:
        raise InputError('r9_tf1_val.json has no decisive macro tF1')
    if macro < MACRO_STOP:
        fired.append({'row': 'stop'})
    elif macro < MACRO_REOPEN:
        fired.append({'row': 'reopen'})
    low = []
    for n in NAMES:
        t = s['decisive_per_class'][n]['tf1']
        share, nf, nt = flagged_share(rows, n)
        info['per_class'][n] = {'tf1': t, 'n_trees': s['decisive_per_class'][n]['n_trees'],
                                'flagged_share': None if share is None else round(share, 4), 'n_flagged': nf,
                                'n_trees_all': nt, 'flagged_tf1': s['flagged_per_class'][n]['tf1']}
        if t is not None and t < CLASS_MIN:
            worst = sorted(decisive_trees(rows, n), key=lambda x: (x[1], x[0]))[:10]
            low.append({'class': n, 'tf1': t, 'worst10': [{'case': c, 'tf1': round(v, 4)} for c, v in worst]})
    if low:
        fired.append({'row': 'class', 'classes': low})
    hi = [n for n in NAMES if info['per_class'][n]['flagged_share'] is not None
          and info['per_class'][n]['flagged_share'] > FLAG_MAX]
    if hi:
        fired.append({'row': 'flagged', 'classes': hi})
    if dice_open80[0] is not None and dice_open80[0] < DICE_MIN:
        fired.append({'row': 'dice'})
    fp = s.get('fp_components_mean')
    if fp is not None:
        fired.append({'row': 'fp_ok' if fp <= FP_MAX else 'fp_high'})
    return fired, info


# ------------------------------------------------------------------------------------------------------- A29
def p2_one(split_summary):
    if not split_summary or 'tf1_expert_minus_aorta' not in split_summary:
        return None
    d = split_summary['tf1_expert_minus_aorta']
    o = split_summary['ostium_expert_vs_aorta_mm']
    share, delta = o.get('share_le_2mm'), d[0]
    ok = share is not None and delta is not None and share >= P2_SHARE and abs(delta) <= P2_DELTA
    return {'share_ostia_le_2mm': share, 'n_ostia': o.get('n'), 'delta_macro_tf1': delta, 'delta_ci': d[1],
            'n_cases': d[2], 'pass': bool(ok)}


def a29_reading(delta):
    sp = delta.get('splits', {})
    _refuse_sealed([r['case'] for r in delta.get('errors', [])], "Delta's summary.json")
    v, o = p2_one(sp.get('val')), p2_one(sp.get('open_clean'))
    if v is None:
        return {'verdict': 'not run', 'why': "Delta's summary has no paired aorta columns on val: was --aorta-dir given?",
                'val': v, 'open36': o}
    if not v['pass']:
        verdict, text = 'withdrawn', A29_FAIL
    elif o is not None and o['pass']:
        verdict, text = 'adopted', A29_PASS
    else:
        verdict, text = 'reported, not adopted', (A26_RULES + ' (A26): the rule passes on val 80 but not on open-36.')
    return {'verdict': verdict, 'text': text, 'val': v, 'open36': o}


# ------------------------------------------------------------------------------------------------------- A15
def census_reading(c):
    if not c:
        return None
    by = c.get('by_category', {})
    return {'n_components': c.get('n_components'), 'by_category': by, 'majority_by_count': c.get('majority_by_count'),
            'has_softmax': c.get('n_with_softmax', 0) > 0,
            'confident_majority': c.get('majority_by_count') == 'confident_other'}


# ------------------------------------------------------------------------------------------------------- output
def fmt(x, nd=3):
    return '—' if x is None else (f'{x:.{nd}f}' if isinstance(x, float) else str(x))


def render(a26, fired, info, a29, cen, inputs):
    L = ['# icx4: the pre-registered reading (A26, A27, A29, A15)', '',
         f"Read on {inputs['date']} by `experiments/Atlas/r10_read_icx4.py`. Val 80 decides (A26); "
         'decisive tF1 @ 1.5 mm at A1c `24441cf8…5254`, A1b flags apart.', '', '## A26: identity check', '',
         f'> {A26_RULE}', '']
    if a26['ok']:
        L.append(f"**PASS**: {a26['n_compared']} of {a26['n_open36']} open-36 cases identical in "
                 f"{', '.join(a26['fields'])}.")
    else:
        L += [f"**STOP**: {len(a26['problems'])} differences; r9_score_icx4.py's val numbers decide nothing.", '']
        L += [f'- {p}' for p in a26['problems'][:20]]
        return '\n'.join(L) + '\n'
    L += ['', '## A27: the reading table (val 80)', '',
          f"Decisive macro tF1: **{fmt(info['macro'])}** (95 % CI {info['macro_ci']}) over {info['n_decisive_cases']} "
          f"cases of {info['n_scored']}; provisional {info['provisional_cases']}; errors {info['errors']}.", '',
          '| Class | Decisive tF1 | Decisive trees | Flagged trees (share) | tF1, flagged |', '|---|---|---|---|---|']
    for n in NAMES:
        p = info['per_class'][n]
        L.append(f"| {n} | {fmt(p['tf1'])} | {p['n_trees']} | {p['n_flagged']} of {p['n_trees_all']} "
                 f"({fmt(p['flagged_share'])}) | {fmt(p['flagged_tf1'])} |")
    L += ['', f"FP components per case (val, raw): **{fmt(info['fp_val'])}** ({info['fp_cases_le_1']} cases ≤ 1). "
          f"Whole-tree Dice on the open 80: **{fmt(info['dice_open80'], 1)}** (n = {info['n_dice_open80']}; "
          'report only, A28).', '', '**Rows that fire** (A27, verbatim):', '']
    macro_rows = {'stop', 'reopen'}
    if not any(f['row'] in macro_rows for f in fired):
        L.append(f"- (macro {fmt(info['macro'])} ≥ 0.85: neither macro row of A27 fires)")
    for f in fired:
        res, then = A27[f['row']]
        L.append(f'- **{res}** → {then}')
        if f['row'] == 'class':
            for c in f['classes']:
                L.append(f"  - {c['class']} (decisive tF1 {fmt(c['tf1'])}), 10 worst val cases: "
                         + ', '.join(f"{w['case']} {w['tf1']:.3f}" for w in c['worst10']))
        if f['row'] == 'flagged':
            L.append(f"  - classes: {', '.join(f['classes'])}")
    L += ['', '## A29: P2 (ImageCAS-X start points as the ostium of record)', '', f'> {A29_RULE}', '']
    if a29 is None:
        L.append("Not read: pass Delta's summary.json with `--delta` (its run needs `--aorta-dir $SCRATCH/icx4/aorta`).")
    elif a29['verdict'] == 'not run':
        L.append(f"Not read: {a29['why']}")
    else:
        for k, lab in (('val', 'val 80 (decides, Delta v9 §5)'), ('open36', 'open-36 (validates, A26)')):
            v = a29[k]
            L.append(f'- {lab}: ' + ('not available' if v is None else
                     f"ostia ≤ 2 mm {fmt(v['share_ostia_le_2mm'])} of {v['n_ostia']}; Δ macro tF1 "
                     f"{fmt(v['delta_macro_tf1'], 4)} (CI {v['delta_ci']}, n {v['n_cases']}): "
                     f"{'pass' if v['pass'] else 'fail'}"))
        L += ['', f"**P2 {a29['verdict']}**: {a29['text']}"]
    L += ['', '## A15: FP gate and census (val 80)', '']
    if info['fp_val'] is not None and info['fp_val'] <= FP_MAX:
        L.append(f"FP per case {fmt(info['fp_val'])} ≤ 1: A15 met on val; no census needed.")
    elif cen is None:
        L.append(f"FP per case {fmt(info['fp_val'])} > 1: run `r10_read_icx4.py census` and read again with `--census`.")
    else:
        L += [f"{cen['n_components']} FP components; majority by count (atlas2's rule, > 50 %): "
              f"**{cen['majority_by_count']}**.", '', '| Category | n | share | mm³ |', '|---|---|---|---|']
        for k, v in cen['by_category'].items():
            L.append(f"| {k} | {v['n']} | {fmt(v['share_n'])} | {fmt(v['mm3'], 0)} |")
        if not cen['has_softmax']:
            L += ['', 'No softmax was supplied, so confident and low-confidence components cannot be told apart '
                  '(`unknown_no_softmax`). Re-predict val 80 with probabilities (command printed by `census`) and '
                  're-run it with `--npz-dir`.']
    return '\n'.join(L) + '\n'


def fill_template(tpl, keys, active):
    """{{key}} placeholders; <!-- if:X --> ... <!-- endif:X --> blocks kept only when X is active."""
    def keep(m):
        return m.group(2) if m.group(1) in active else ''
    out = re.sub(r'<!-- if:([a-z0-9_]+) -->\n?(.*?)<!-- endif:\1 -->\n?', keep, tpl, flags=re.S)
    for k, v in keys.items():
        out = out.replace('{{' + k + '}}', str(v))
    left = sorted(set(re.findall(r'\{\{([a-z0-9_]+)\}\}', out)))
    if left:
        raise InputError(f'note template placeholders not filled: {left}')
    return out


def note_keys(a26, fired, info, a29, cen, report_md, inputs):
    rows = {f['row'] for f in fired}
    active = set(rows)
    if a26['ok']:
        active.add('a26_pass')
    else:
        active.add('a26_stop')
    if a26['ok'] and not rows & {'stop', 'reopen'}:
        active.add('stands')
    if a29 and a29.get('verdict') in ('adopted', 'withdrawn', 'reported, not adopted'):
        active.add('p2_' + {'adopted': 'adopted', 'withdrawn': 'withdrawn', 'reported, not adopted': 'reported'}[a29['verdict']])
    else:
        active.add('p2_missing')
    if cen and cen.get('confident_majority'):
        active.add('fp_confident')
    pc = info.get('per_class', {}) if info else {}
    keys = {'date': inputs['date'], 'reading': report_md.strip(), 'status': f"read {inputs['date']} (r10_read_icx4.py)",
            'a26': 'PASS' if a26['ok'] else 'STOP', 'macro': fmt(info.get('macro')) if info else '—',
            'macro_ci': (info or {}).get('macro_ci'), 'fp_val': fmt((info or {}).get('fp_val')),
            'dice_open80': fmt((info or {}).get('dice_open80'), 1),
            'p2': a29['verdict'] if a29 else 'not read', 'inputs': json.dumps(inputs, indent=1)}
    for n in NAMES:
        keys[f'tf1_{n.lower()}'] = fmt(pc.get(n, {}).get('tf1'))
        keys[f'flag_{n.lower()}'] = fmt(pc.get(n, {}).get('flagged_share'))
    keys['fired'] = ', '.join(A27[f['row']][0] for f in fired) or 'none'
    return keys, active


def cmd_read(a):
    inputs = {'date': datetime.date.today().isoformat(), 'results': a.results, 'open36': a.open36, 'val': a.val,
              'delta': a.delta, 'census': a.census}
    try:
        job_tf1 = _load(os.path.join(a.results, 'tf1_per_case.json'), 'results/tf1_per_case.json')
        _refuse_sealed([r['case'] for r in job_tf1.get('per_case', []) + job_tf1.get('errors', [])], 'tf1_per_case.json')
        check = _load(a.open36, 'r9_open36_check.json')
        _refuse_sealed([r['case'] for r in check.get('rows', [])], 'r9_open36_check.json')
        a26 = a26_identity(job_tf1, check)
        fired, info, a29, cen = [], {}, None, None
        if a26['ok']:
            val = _load(a.val, 'r9_tf1_val.json')
            fired, info = a27_reading(val, open80_tree_dice(a.results))
            a29 = a29_reading(_load(a.delta, "Delta's summary.json")) if a.delta else None
            cen = census_reading(_load(a.census, 'census JSON')) if a.census else None
    except InputError as e:
        print(f'[read] {e}', file=sys.stderr)
        return 4
    md = render(a26, fired, info, a29, cen, inputs)
    print(md)
    verdict = {'inputs': inputs, 'a26': a26, 'a27': {'fired': fired, 'info': info}, 'a29': a29, 'a15_census': cen}
    if a.out:
        json.dump(verdict, open(a.out, 'w'), indent=1)
    if a.note_template and a.note_out:
        keys, active = note_keys(a26, fired, info, a29, cen, md, inputs)
        open(a.note_out, 'w').write(fill_template(open(a.note_template).read(), keys, active))
        print(f'[read] note written: {a.note_out}')
    if not a26['ok']:
        return 2
    return 3 if any(f['row'] == 'stop' for f in fired) else 0


# ------------------------------------------------------------------------------------------------------- census
CEN = {}


def _census_init(ctx):
    CEN.update(ctx)
    sys.path.insert(0, LIB)
    import tf1_score
    tf1_score.load_metric()   # puts the pinned lib/segtrain_tf1.py in sys.modules before atlas2's score.py imports it
    spec = importlib.util.spec_from_file_location('atlas2_score', os.path.join(ROOT, 'trillium', 'atlas2', 'lib', 'score.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.T is sys.modules['segtrain_tf1'] and tf1_score.tf1_hash() == tf1_score.TF1_SHA256
    CEN['score'] = m


def _census_case(c):
    import numpy as np
    import nibabel as nib
    from territory import to_four
    m, W = CEN['score'], CEN['W']
    try:
        li = nib.load(os.path.join(W, 'icx', f'{int(c[1:]) + 1}.coronary.nii.gz'))
        sp = np.asarray(li.header.get_zooms()[:3], float)
        ref = to_four(np.asarray(li.dataobj).astype(np.int64), sp).astype(np.uint8)
        pred = np.asarray(nib.load(os.path.join(W, 'predictions', f'{c}.nii.gz')).dataobj).astype(np.uint8)
        ap = os.path.join(W, 'aorta', f'{c}_aorta.nii.gz')
        aorta = np.asarray(nib.load(ap).dataobj) > 0 if os.path.exists(ap) else None
        ctp = CEN['ct'].get(c)
        ct = np.asarray(nib.load(ctp).dataobj).astype(np.float32) if ctp and os.path.exists(ctp) else None
        npz = os.path.join(CEN['npz'], f'{c}.npz') if CEN['npz'] else None
        prob = m.load_probabilities(npz, ref.shape) if npz and os.path.exists(npz) else None
        sl = m._bbox([ref > 0, pred > 0], sp, ref.shape)
        rows = m.census(ref[sl], pred[sl], None if prob is None else prob[(slice(None),) + sl], sp,
                        ct=None if ct is None else ct[sl], aorta=None if aorta is None else aorta[sl], icx=ref[sl])
        return {'case': c, 'has_softmax': prob is not None, 'rows': rows}
    except Exception as e:  # noqa: BLE001
        return {'case': c, 'error': repr(e)[:300]}


def census_summary(per):
    rows = [dict(case=p['case'], **r) for p in per if 'error' not in p for r in p['rows']]
    cats = {}
    for r in rows:
        cats.setdefault(r['category'], []).append(r)
    n, v = len(rows), sum(r['mm3'] for r in rows)
    by = {k: {'n': len(x), 'share_n': len(x) / n, 'mm3': float(sum(r['mm3'] for r in x)),
              'share_mm3': float(sum(r['mm3'] for r in x)) / v if v else None,
              'median_dist_to_ref_mm': sorted(r['dist_to_ref_mm'] for r in x)[len(x) // 2]} for k, x in sorted(cats.items())}
    out = {'n_cases': len(per), 'n_with_softmax': sum(p.get('has_softmax', False) for p in per),
           'errors': [p['case'] for p in per if 'error' in p], 'n_components': n, 'mm3_total': v, 'by_category': by,
           'rule': 'atlas2 score.py census (Round 5): icx_vessel if >= 50 % of voxels within 1 mm of ImageCAS-X; else '
                   'low_confidence if p90 of 1 - p_background < 0.90; else confident_other; majority = > 50 % by count'}
    if n:
        top = max(by.items(), key=lambda kv: kv[1]['n'])
        out['majority_by_count'] = top[0] if top[1]['share_n'] > 0.5 else 'none (no category > 50 %)'
    out['components'] = rows
    return out


def cmd_census(a):
    W = a.W
    sp = _load(os.path.join(W, 'splits.json'), 'splits.json')
    val = sorted(sp['val'])
    try:
        _refuse_sealed(val, 'splits.json val')
    except InputError as e:
        print(f'[census] {e}', file=sys.stderr)
        return 4
    lay = os.path.join(W, 'layout.json')
    ct = {c: v.get('ct') for c, v in json.load(open(lay))['cases'].items()} if os.path.exists(lay) else {}
    sys.path.insert(0, LIB)
    with Pool(a.np, initializer=_census_init, initargs=({'W': W, 'ct': ct, 'npz': a.npz_dir},), maxtasksperchild=4) as p:
        per = p.map(_census_case, val, chunksize=1)
    out = census_summary(per)
    json.dump(out, open(a.out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'components'}, indent=1))
    if out['n_with_softmax'] == 0:
        print(CENSUS_SOFTMAX_HELP.format(W=W))
    return 1 if out['errors'] else 0


CENSUS_SOFTMAX_HELP = """
[census] no softmax: confidence (low_confidence vs confident_other) is unknown. To get it (about 1 GPU-h, val 80 only):
  mkdir -p {W}/val_in {W}/val_prob && python - <<'PY'
import json, os; W = '{W}'
for c in json.load(open(f'{{W}}/splits.json'))['val']:
    d = f'{{W}}/val_in/{{c}}_0000.nii.gz'
    os.path.lexists(d) or os.symlink(os.readlink(f'{{W}}/predict_in/{{c}}_0000.nii.gz'), d)
PY
  # then in a 1-GPU job (icx4's Fir header, --time=3:00:00), with icx4's venv and nnU-Net env (nnUNet_results={W}/nnunet_results):
  nnUNetv2_predict -i {W}/val_in -o {W}/val_prob -d 715 -c 3d_fullres -f 0 -tr nnUNetTrainerICX4 \\
      -p nnUNetResEncUNetPlans_60G_iso05 -chk checkpoint_final.pth --disable_tta --save_probabilities
  # and re-run: r10_read_icx4.py census --W {W} --npz-dir {W}/val_prob --out ...
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('read')
    r.add_argument('--results', required=True); r.add_argument('--open36', required=True)
    r.add_argument('--val', required=True); r.add_argument('--delta'); r.add_argument('--census')
    r.add_argument('--out'); r.add_argument('--note-template'); r.add_argument('--note-out')
    c = sub.add_parser('census')
    c.add_argument('--W', required=True); c.add_argument('--out', required=True)
    c.add_argument('--npz-dir'); c.add_argument('--np', type=int, default=8)
    a = ap.parse_args(argv)
    return cmd_read(a) if a.cmd == 'read' else cmd_census(a)


if __name__ == '__main__':
    sys.exit(main())
