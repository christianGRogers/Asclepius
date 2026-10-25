"""Atlas, Round 10 (#113): where P2's 0.0079 lives (report only; P2 is closed, A1 stands).

Reads Delta's per-case output of the A29 test (experiments/Delta/r9_fir/score_tf1.py -> <out>/per_case.jsonl), which
holds per case both tF1 versions: expert start-point ostia (tf1_<class>) and the TotalSegmentator-aorta ostium of
record (tf1_aorta_<class>), with the ostium distance between them (ostium_expert_vs_aorta_mm). Lists the cases that
carry the left-tree gap and how much of the val mean each carries. Decides nothing (Round 10 issue: report only).
No sealed case is in the file (Delta's scorer refuses them); this script refuses one anyway.

    python experiments/Atlas/r10_ostium_residual.py $SCRATCH/icx4/delta_p2/per_case.jsonl --split val
    python experiments/Atlas/r10_ostium_residual.py --selftest
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
CLS = ('LM', 'LAD', 'LCx', 'RCA')


def sealed_ids():
    d = json.load(open(os.path.join(REPO, 'trillium', 'sealed_test.json')))
    ids = list(d['sealed_icx_test']) + list(d['sealed_quality0'])
    if not ids:
        raise SystemExit('trillium/sealed_test.json lists no sealed case; refusing')
    return {str(x) for x in ids}


def analyse(rows, split='val'):
    sealed = sealed_ids()
    rs = [r for r in rows if r.get('split') == split and 'tf1' in r]
    bad = [r['case'] for r in rs if r['case'] in sealed]
    if bad:
        raise SystemExit(f'sealed case(s) in the input: {bad[:5]}; refusing')
    out = []
    for r in rs:
        flagged = set(r.get('flagged_classes', []))
        d = {}
        for i, c in enumerate(CLS, 1):
            a, b = r.get(f'tf1_{c}'), r.get(f'tf1_aorta_{c}')
            if a is not None and b is not None and i not in flagged:
                d[c] = a - b
        macro = sum(d.values()) / len(d) if d else 0.0
        out.append({'case': r['case'], 'delta_macro': round(macro, 4),
                    'delta_per_class': {k: round(v, 4) for k, v in d.items() if abs(v) > 1e-9},
                    'ostium_mm': r.get('ostium_expert_vs_aorta_mm')})
    n = len(out)
    tot = sum(x['delta_macro'] for x in out) / n if n else 0.0
    carriers = sorted([x for x in out if abs(x['delta_macro']) > 1e-9], key=lambda x: -abs(x['delta_macro']))
    for x in carriers:
        x['share_of_mean'] = round(x['delta_macro'] / n / tot, 3) if tot else None
    return {'split': split, 'n': n, 'mean_delta_macro': round(tot, 4), 'n_cases_carrying': len(carriers),
            'carriers': carriers}


def selftest():
    rows = [{'case': f'c9{i:03d}', 'split': 'val', 'tf1': 0.9, 'flagged_classes': [],
             **{f'tf1_{c}': 0.9 for c in CLS}, **{f'tf1_aorta_{c}': 0.9 for c in CLS},
             'ostium_expert_vs_aorta_mm': [0.0, 0.0]} for i in range(10)]
    rows[3]['tf1_aorta_LAD'] = 0.5
    rows[3]['ostium_expert_vs_aorta_mm'] = [6.1, 0.0]
    res = analyse(rows)
    assert res['n_cases_carrying'] == 1 and res['carriers'][0]['case'] == 'c9003', res
    assert abs(res['mean_delta_macro'] - 0.01) < 1e-9 and res['carriers'][0]['share_of_mean'] == 1.0, res
    print('selftest ok')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('per_case', nargs='?')
    ap.add_argument('--split', default='val')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        selftest(); sys.exit(0)
    rows = [json.loads(l) for l in open(a.per_case) if l.strip()]
    print(json.dumps(analyse(rows, a.split), indent=1))
