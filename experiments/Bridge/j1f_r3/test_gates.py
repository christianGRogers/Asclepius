"""Round 2 ruling §5 item 2: `configs/j1f_gates.json` holds F-A15's lines, and a fixture with OM2 recall 0.59 fails
while 0.61 passes. Also: the file is refused under any other sha256, and each of the 18 lines bites at 0.01 below.
No data is read. Usage: python3 test_gates.py"""
import copy, json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1f_scorer as S  # noqa: E402

GATES = os.path.join(HERE, 'configs', 'j1f_gates.json')
SHA = '16ce89544323414291401f3c1fb167d7db7af484a8f89b45e7279a15aac01b6b'
F_A15 = {'D1': (0.81, 0.94, 0.83), 'D2': (0.76, 0.84, 0.86), 'OM1': (0.75, 0.90, 0.78),
         'OM2': (0.60, 0.81, 0.78), 'PDA': (0.89, 0.97, 0.90), 'PLB': (0.89, 0.94, 0.92)}
N = 100


def fixture(metric_vals):
    """100 cases, one piece per case per gated class; metric_vals {class: (recall, presence, naming)} as hundredths
    of 100 (recall over 100 pieces; presence over 100 cases; naming over the detected)."""
    rows = [{S.NAMES[c]: {'pieces': [], 'present_ref': False, 'present_pred': False} for c in S.BRANCHES}
            for _ in range(N)]
    for k, (rec, pres, nam) in metric_vals.items():
        ndet = round(rec * N)
        nnamed = round(nam * ndet)
        nagree = round(pres * N)
        for i in range(N):
            rows[i][k] = {'pieces': [{'detected': i < ndet, 'named': i < nnamed}],
                          'present_ref': True, 'present_pred': i < nagree}
    return rows


fails = []
def check(name, cond):
    print(('PASS ' if cond else 'FAIL ') + name)
    if not cond: fails.append(name)


g = S.load_gates(GATES, SHA)
check('file lines == F-A15', all(tuple(g['classes'][c][m] for m in ('recall', 'presence', 'naming')) == v
                                  for c, v in F_A15.items()))
base = {c: (0.95, 0.99, 0.99) for c in F_A15}
check('all-good fixture: 6 of 6, B passes', S.verdict(S.aggregate(fixture(base)), g)['n_pass'] == 6)
for r, want in ((0.59, False), (0.60, True), (0.61, True)):
    m = dict(base); m['OM2'] = (r, 0.99, 0.99)
    a = S.aggregate(fixture(m))
    v = S.verdict(a, g)
    check(f'OM2 recall {a["OM2"]["recall"]:.2f}: OM2 {"passes" if want else "fails"}, B still passes (5 of 6 ok)',
          v['classes']['OM2']['pass'] is want and v['B'])
# every line bites one hundredth below, and holds at the line
for c, lines in F_A15.items():
    for j, mname in enumerate(('recall', 'presence', 'naming')):
        for delta, want in ((0.0, True), (-0.01, False)):
            m = dict(base); vals = list(base[c]); vals[j] = round(lines[j] + delta, 2)
            if j == 2: vals[0] = 1.0          # naming over 100 detected pieces, so 0.78 is 78/100
            m[c] = tuple(vals)
            a = S.aggregate(fixture(m))
            ok = S.verdict(a, g)['classes'][c]['pass']
            if ok is not want:
                check(f'{c} {mname} at {vals[j]}: pass={want}', False)
check('each of the 18 lines holds at its value and fails 0.01 below', not any('pass=' in f for f in fails))
# 3 classes failing -> B fails (< 4 of 6)
m = dict(base); m['OM2'] = (0.5, 0.99, 0.99); m['D2'] = (0.5, 0.99, 0.99); m['OM1'] = (0.5, 0.99, 0.99)
v = S.verdict(S.aggregate(fixture(m)), g)
check('3 classes fail -> 3 of 6, B fails', v['n_pass'] == 3 and not v['B'])
# refusals
with tempfile.TemporaryDirectory() as d:
    bad = copy.deepcopy(json.load(open(GATES))); bad['classes']['OM2']['recall'] = 0.55
    p = os.path.join(d, 'g.json'); json.dump(bad, open(p, 'w'))
    try:
        S.load_gates(p, SHA); check('changed file refused by sha256', False)
    except SystemExit:
        check('changed file refused by sha256', True)
    bad = copy.deepcopy(json.load(open(GATES))); bad['k_of_6'] = 3; json.dump(bad, open(p, 'w'))
    try:
        S.load_gates(p, None); check('k_of_6 != 4 refused', False)
    except SystemExit:
        check('k_of_6 != 4 refused', True)
print('ALL PASS' if not fails else f'{len(fails)} FAIL')
sys.exit(1 if fails else 0)
