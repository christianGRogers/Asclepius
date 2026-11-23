"""§5 item 2: the gates file and the verdict. A fixture with OM2 recall 0.59 fails, 0.61 passes; the boundary 0.60
passes; a tampered file is refused by sha256. Synthetic piece rows only (no image). Usage: python test_gates.py"""
import copy, hashlib, json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import j1f_scorer as S  # noqa: E402

GATES = os.path.join(HERE, 'j1f_gates.json')
SHA = hashlib.sha256(open(GATES, 'rb').read()).hexdigest()
g = S.load_gates(GATES, SHA)
fails = []


def check(name, cond):
    print(('PASS ' if cond else 'FAIL ') + name); cond or fails.append(name)


def cases(om2_detected, n=100):
    """100 cases, one piece per gated class each; every class perfect except OM2 recall = om2_detected / n."""
    out = []
    for i in range(n):
        r = {}
        for c in S.BRANCHES:
            k = S.NAMES[c]
            det = (i < om2_detected) if k == 'OM2' else True
            r[k] = {'pieces': [{'len': 20.0, 'detected': det, 'named': det, 'cover': 1.0 if det else 0.0}],
                    'present_ref': True, 'present_pred': True}
        out.append(r)
    return out


for d, want in ((59, False), (60, True), (61, True)):
    v = S.verdict(S.aggregate(cases(d)), g)
    check(f'OM2 recall {d / 100:.2f}: OM2 pass = {want}', v['classes']['OM2']['pass'] is want and
          v['classes']['OM2']['naming'] and v['classes']['OM2']['presence'])
    check(f'OM2 recall {d / 100:.2f}: B still passes on the other five (n_pass {v["n_pass"]})', v['B'])
# 3 classes failing -> B fails
cs = cases(59)
for r in cs[:30]:
    for k in ('D1', 'D2'):
        r[k]['pieces'][0]['detected'] = r[k]['pieces'][0]['named'] = False
v = S.verdict(S.aggregate(cs), g)
check(f'D1, D2, OM2 failing: n_pass {v["n_pass"]} < 4, B fails', v['n_pass'] == 3 and not v['B'])
# naming is named / detected, not named / pieces
cs = cases(61)
v = S.verdict(S.aggregate(cs), g)
check('naming of OM2 with 61 detected, 61 named = 1.0', S.aggregate(cs)['OM2']['naming'] == 1.0)
# presence agreement line
cs = cases(100)
for r in cs[:7]:
    r['PDA']['present_pred'] = False
a = S.aggregate(cs)
check(f'PDA presence 0.93 < 0.97 fails ({a["PDA"]["presence"]:.2f})', not S.verdict(a, g)['classes']['PDA']['pass'])
# tampered file refused
t = copy.deepcopy(json.load(open(GATES))); t['lines']['OM2']['recall'] = 0.59
fd, p = tempfile.mkstemp(suffix='.json'); os.write(fd, json.dumps(t).encode()); os.close(fd)
try:
    S.load_gates(p, SHA); check('tampered gates file refused', False)
except SystemExit:
    check('tampered gates file refused', True)
t['lines'].pop('PLB'); open(p, 'w').write(json.dumps(t))
try:
    S.load_gates(p); check('a file without PLB refused', False)
except AssertionError:
    check('a file without PLB refused', True)
os.unlink(p)
print('gates sha256', SHA)
print('ALL PASS' if not fails else f'{len(fails)} FAIL'); sys.exit(1 if fails else 0)
