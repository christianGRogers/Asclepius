"""Stage D: results/SUMMARY.md, results.json and per_case_test.json from the per-case tables in the workdir.
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


def build(W):
    S = sealed.load(f'{W}/sealed_test.json')
    dice_rows = json.load(open(f'{W}/dice_per_case.json'))
    sealed.refuse_sealed([r['case'] for r in dice_rows], S, 'report')
    res = {'sealed_filter': {'sealed_icx_test_excluded': len(S['sealed_icx_test']),
                             'sealed_quality0_excluded': len(S['sealed_quality0']),
                             'rule': 'A14: sealed cases are predicted but never scored (trillium/sealed_test.json)'},
           'groups': {}}
    for g in sealed.GROUPS:
        rows = [r for r in dice_rows if r['group'] == g]
        res['groups'][g] = {'n_listed': len(S['open_icx_test' if g == 'open36' else 'excluded_dev_cases_in_test']),
                            'n_scored': len(rows), 'dice': dice_summary(rows)}
    return res, dice_rows


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
