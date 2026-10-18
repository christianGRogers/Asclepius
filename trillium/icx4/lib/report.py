"""Stage D: results/SUMMARY.md, results.json and per_case_test.json from the per-case tables in the workdir:
the decisive tF1 (tf1_score.py: A1 with the TotalSegmentator ostium, A1a provisional apart, A1b flagged trees
apart, A1c frozen metric) and Dice as a secondary column (score.py).
Two groups, always apart (sealed.py, A14): open-36 (never sealed, never used in development) and dev-44 (never
sealed, inspected by an advocate). The 80 sealed test cases are not in any input and never appear here; the
report re-checks that.
Usage: report.py <workdir> <results_dir>   (exit 3 = an input holds a sealed case)"""
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sealed  # noqa: E402

NAMES = ['LM', 'LAD', 'LCx', 'RCA']
TITLE = {'open36': 'open-36 (clean: never sealed, never used in development)',
         'dev44': 'dev-44 (not sealed, but inspected in development: biased, never decisive alone)'}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return (round(statistics.mean(xs), 4), len(xs)) if xs else (None, 0)


def dice_summary(rows):
    s = {'n': len(rows), 'tree_dice': mean(r['tree'] for r in rows)[0], 'per_class': {}}
    for n in NAMES:
        d, _ = mean(r['cls'][n]['dice'] for r in rows if r['cls'][n]['in_ref'] and r['cls'][n]['in_pred'])
        s['per_class'][n] = {
            'dice_when_both_present': d, 'cases_in_ref': sum(r['cls'][n]['in_ref'] for r in rows),
            'found': sum(r['cls'][n]['in_ref'] and r['cls'][n]['in_pred'] for r in rows),
            'predicted_but_absent': sum(r['cls'][n]['in_pred'] and not r['cls'][n]['in_ref'] for r in rows),
            'dice_all_ref_cases': mean((r['cls'][n]['dice'] or 0.0) for r in rows if r['cls'][n]['in_ref'])[0]}
    macro = [v['dice_all_ref_cases'] for v in s['per_class'].values() if v['dice_all_ref_cases'] is not None]
    s['macro_dice_4'] = round(statistics.mean(macro), 4) if macro else None
    return s


def _f(x):
    return None if x is None else round(float(x), 4)


def decisive_case_score(r):
    """A1a/A1b: macro tF1 @ 1.5 mm over the unflagged classes of a non-provisional case (None: decides nothing)."""
    if r['provisional']:
        return None
    v = [x for c, x in r['per_class'].items() if c not in r['flagged_classes']]
    return statistics.mean(v) if v else None


def tf1_summary(rows, errors=()):
    """Per group: the decisive macro and per-class tF1, flagged trees apart, provisional cases apart."""
    dec = [decisive_case_score(r) for r in rows]
    ok = [d for d in dec if d is not None]
    nonprov = [r for r in rows if not r['provisional']]
    out = {'n_scored': len(rows), 'n_errors': len(errors), 'errors': sorted(e['case'] for e in errors),
           'n_with_aorta': sum(r['has_aorta'] for r in rows),
           'provisional_cases': sorted(r['case'] for r in rows if r['provisional']),
           'n_decisive_cases': len(ok), 'decisive_macro_tf1': _f(statistics.mean(ok)) if ok else None,
           'decisive_per_class': {}, 'flagged_per_class': {}, 'classes_without_centreline': {}}
    for n in NAMES:
        un = [r['per_class'][n] for r in nonprov if n in r['per_class'] and n not in r['flagged_classes']]
        fg = [r['per_class'][n] for r in nonprov if n in r['per_class'] and n in r['flagged_classes']]
        out['decisive_per_class'][n] = {'tf1': _f(statistics.mean(un)) if un else None, 'n_trees': len(un)}
        out['flagged_per_class'][n] = {'n_trees': len(fg), 'tf1': _f(statistics.mean(fg)) if fg else None}
        out['classes_without_centreline'][n] = sum(n in r['classes_without_centreline'] for r in rows)
    t0 = [r['tf1_tol0'] for r in nonprov if r['tf1_tol0'] == r['tf1_tol0']]
    allm = [r['tf1'] for r in nonprov if r['tf1'] == r['tf1']]
    out['macro_tf1_incl_flagged_not_decisive'] = _f(statistics.mean(allm)) if allm else None
    out['macro_tf1_tol0_not_decisive'] = _f(statistics.mean(t0)) if t0 else None
    fp = [r['fp_components'] for r in rows]
    out['fp_components_mean'] = _f(statistics.mean(fp)) if fp else None
    out['fp_cases_le_1'] = sum(x <= 1 for x in fp)
    return out


def build(W):
    S = sealed.load(f'{W}/sealed_test.json')
    dice_rows = json.load(open(f'{W}/dice_per_case.json'))
    tf = json.load(open(f'{W}/tf1_per_case.json')) if os.path.exists(f'{W}/tf1_per_case.json') else None
    tf_rows = tf['per_case'] if tf else []
    tf_err = tf['errors'] if tf else []
    sealed.refuse_sealed([r['case'] for r in dice_rows + tf_rows + tf_err], S, 'report')
    res = {'sealed_filter': {'sealed_icx_test_excluded': len(S['sealed_icx_test']),
                             'sealed_quality0_excluded': len(S['sealed_quality0']),
                             'rule': 'A14: sealed cases are predicted but never scored (trillium/sealed_test.json)'},
           'tf1': {'computed': tf is not None, 'tf1_sha256': tf['tf1_sha256'] if tf else None,
                   'tolerance_mm': 1.5, 'rule': 'A1/A1a/A1b/A1c: decisive = tF1 @ 1.5 mm, TotalSegmentator ostium, '
                   'provisional cases and flagged trees left out'},
           'groups': {}}
    for g in sealed.GROUPS:
        rows = [r for r in dice_rows if r['group'] == g]
        res['groups'][g] = {'n_listed': len(S['open_icx_test' if g == 'open36' else 'excluded_dev_cases_in_test']),
                            'n_scored': len(rows), 'dice': dice_summary(rows),
                            'tf1': tf1_summary([r for r in tf_rows if r['group'] == g],
                                               [r for r in tf_err if r['group'] == g]) if tf else None}
    tfc = {r['case']: r for r in tf_rows}
    per_case = [dict(r, tf1=tfc.get(r['case'])) for r in dice_rows]
    return res, per_case


def summary_md(W, res):
    L = ['# icx4 results: 4-class model (LM, LAD, LCx, RCA) on ImageCAS-X', '',
         'Reference: ImageCAS-X as drawn, collapsed to the four classes by territory (D25), exactly as in training.',
         '', '## Which cases are scored (A14)', '',
         f'- **Not scored:** the {res["sealed_filter"]["sealed_icx_test_excluded"]} sealed ImageCAS-X test cases '
         f'and the {res["sealed_filter"]["sealed_quality0_excluded"]} sealed quality-0 cases '
         '(`trillium/sealed_test.json`). They are predicted for SegQueue, never scored or summarised.']
    for g in sealed.GROUPS:
        v = res['groups'][g]
        L.append(f'- **{TITLE[g]}:** {v["n_scored"]} of {v["n_listed"]} cases scored.')
    if not res['tf1']['computed']:
        L += ['', '**tF1 has not been computed yet: nothing here decides anything.**']
    for g in sealed.GROUPS:
        t = res['groups'][g]['tf1']
        if t is None:
            continue
        L += ['', f'## {TITLE[g]}: decisive tree-F1 @ 1.5 mm (A1)', '',
              f'- **Decisive macro tF1: {t["decisive_macro_tf1"]}** over {t["n_decisive_cases"]} cases '
              '(non-provisional; flagged trees left out, A1b)',
              f'- Aorta masks: {t["n_with_aorta"]} of {t["n_scored"]}; provisional (no aorta, decide nothing, A1a): '
              f'{len(t["provisional_cases"])} {t["provisional_cases"][:10]}',
              f'- Not decisive: macro tF1 incl. flagged {t["macro_tf1_incl_flagged_not_decisive"]}, '
              f'tF1 @ 0 mm {t["macro_tf1_tol0_not_decisive"]}',
              f'- Raw FP components per case (A15): {t["fp_components_mean"]}; cases with <= 1: {t["fp_cases_le_1"]}',
              f'- Scoring errors: {t["n_errors"]} {t["errors"][:10]}', '',
              '| Class | Decisive tF1 | Trees | Flagged trees (A1b) | tF1, flagged | No centreline (fallback) | '
              'Dice, all ref cases |', '|---|---|---|---|---|---|---|']
        dc = res['groups'][g]['dice']['per_class']
        for n in NAMES:
            L.append(f'| {n} | {t["decisive_per_class"][n]["tf1"]} | {t["decisive_per_class"][n]["n_trees"]} | '
                     f'{t["flagged_per_class"][n]["n_trees"]} | {t["flagged_per_class"][n]["tf1"]} | '
                     f'{t["classes_without_centreline"][n]} | {dc[n]["dice_all_ref_cases"]} |')
    if res['tf1']['computed']:
        L += ['', f'Metric: `lib/segtrain_tf1.py`, sha256 `{res["tf1"]["tf1_sha256"]}` (A1c).']
    for g in sealed.GROUPS:
        d = res['groups'][g]['dice']
        L += ['', f'## {TITLE[g]}: Dice (secondary; decides nothing)', '',
              f'- Whole-tree Dice (any vessel vs any vessel): **{d["tree_dice"]}**',
              f'- Macro Dice over the 4 classes (a missed class scores 0): **{d["macro_dice_4"]}**', '',
              '| Class | Cases with it (ref) | Found | Predicted but absent | Dice, all ref cases | Dice when both present |',
              '|---|---|---|---|---|---|']
        for n, v in d['per_class'].items():
            L.append(f'| {n} | {v["cases_in_ref"]} | {v["found"]} | {v["predicted_but_absent"]} | '
                     f'{v["dice_all_ref_cases"]} | {v["dice_when_both_present"]} |')
    L += ['', f'Predictions for every case are in `{W}/predictions/` (uint8 NIfTI, labels 1-4 in the order above).']
    for f in ('label_census.json', 'planner_output.json', 'timings.json'):
        if os.path.exists(f'{W}/{f}'):
            L.append(f'- `{f}`: ' + open(f'{W}/{f}').read().replace('\n', ' ')[:600])
    return '\n'.join(L) + '\n'


if __name__ == '__main__':
    W, OUT = sys.argv[1], sys.argv[2]
    try:
        res, rows = build(W)
    except sealed.SealedError as e:
        print(f'[report] {e}', flush=True)
        sys.exit(3)
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(f'{OUT}/results.json', 'w'), indent=1)
    json.dump(rows, open(f'{OUT}/per_case_test.json', 'w'))
    md = summary_md(W, res)
    open(f'{OUT}/SUMMARY.md', 'w').write(md)
    print(md)
