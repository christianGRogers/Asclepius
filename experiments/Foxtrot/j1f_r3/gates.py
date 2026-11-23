"""Janus 1-F round 3 (Foxtrot): B's decision layer on top of the scorer of record (F-A15, F-A16). Reference code for
`janus1f collect`: pools `j1f_scorer.score_case` outputs over cases and applies `j1f_gates.json`.

  recall_c   = detected pieces / reference pieces (pooled over cases)
  naming_c   = named pieces / detected pieces (pooled); a class with no detected piece has naming 0
  presence_c = share of cases where reference and prediction agree on presence (5 mm)
  class passes  <=> recall >= line and presence >= line and naming >= line (equality passes; EPS guards float sums)
  B passes      <=> at least k_of_6 (4) of the six gated classes pass
Self-test (`python gates.py selftest`): the file's lines, OM2 recall 0.59 fails / 0.60 and 0.61 pass, every line's
edge, the 4-of-6 edge, and a refusal of a gates file whose sha256 is not the posted one.
"""
import hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GATED = ('D1', 'D2', 'OM1', 'OM2', 'PDA', 'PLB')
EPS = 1e-12
F_A15 = {'D1': (0.81, 0.94, 0.83), 'D2': (0.76, 0.84, 0.86), 'OM1': (0.75, 0.90, 0.78),
         'OM2': (0.60, 0.81, 0.78), 'PDA': (0.89, 0.97, 0.90), 'PLB': (0.89, 0.94, 0.92)}


def load(path, sha256=None):
    raw = open(path, 'rb').read()
    if sha256 is not None and hashlib.sha256(raw).hexdigest() != sha256:
        raise SystemExit(f'refuse: {path} sha256 {hashlib.sha256(raw).hexdigest()} != posted {sha256}')
    g = json.loads(raw)
    assert g['k_of_6'] == 4 and set(g['classes']) == set(GATED), 'gates file malformed'
    return g


def pool(cases):
    """cases: list of score_case() outputs (one per locked case). Returns {class: {...}}."""
    out = {}
    for c in GATED:
        pcs = [p for s in cases for p in s[c]['pieces']]
        det = sum(p['detected'] for p in pcs)
        nam = sum(p['named'] for p in pcs)
        agree = sum(s[c]['present_ref'] == s[c]['present_pred'] for s in cases)
        out[c] = {'pieces': len(pcs), 'detected': det, 'named': nam, 'cases': len(cases),
                  'recall': det / len(pcs) if pcs else float('nan'),
                  'naming': nam / det if det else 0.0,
                  'presence_agreement': agree / len(cases)}
    return out


def decide(pooled, gates):
    res = {}
    for c in GATED:
        L, v = gates['classes'][c], pooled[c]
        ok = {k: bool(v[k] >= L[k] - EPS) for k in ('recall', 'presence_agreement', 'naming')}
        res[c] = {'values': {k: v[k] for k in ok}, 'lines': L, 'pass_by_stat': ok, 'pass': all(ok.values())}
    n = sum(r['pass'] for r in res.values())
    return {'classes': res, 'n_pass': n, 'B_pass': n >= gates['k_of_6']}


def _fix(over=None):
    """A pooled fixture at every line exactly, with `over` = {class: {stat: value}} replacing values."""
    p = {c: {'recall': F_A15[c][0], 'presence_agreement': F_A15[c][1], 'naming': F_A15[c][2]} for c in GATED}
    for c, d in (over or {}).items():
        p[c].update(d)
    return p


def selftest(path=os.path.join(HERE, 'j1f_gates.json')):
    g = load(path)
    for c in GATED:
        L = g['classes'][c]
        assert (L['recall'], L['presence_agreement'], L['naming']) == F_A15[c], c
    assert decide(_fix(), g)['n_pass'] == 6                                       # every line exactly: passes
    assert not decide(_fix({'OM2': {'recall': 0.59}}), g)['classes']['OM2']['pass']
    assert decide(_fix({'OM2': {'recall': 0.61}}), g)['classes']['OM2']['pass']
    assert decide(_fix({'OM2': {'recall': 24 / 40}}), g)['classes']['OM2']['pass']   # 24 of 40 pieces = 0.60
    for c in GATED:
        for k in ('recall', 'presence_agreement', 'naming'):
            r = decide(_fix({c: {k: g['classes'][c][k] - 0.01}}), g)
            assert not r['classes'][c]['pass'] and r['n_pass'] == 5 and r['B_pass'], (c, k)
    two = _fix({'D1': {'naming': 0.0}, 'D2': {'recall': 0.0}})
    assert decide(two, g)['n_pass'] == 4 and decide(two, g)['B_pass']
    three = _fix({'D1': {'naming': 0.0}, 'D2': {'recall': 0.0}, 'OM2': {'presence_agreement': 0.5}})
    assert decide(three, g)['n_pass'] == 3 and not decide(three, g)['B_pass']
    try:
        load(path, sha256='0' * 64); raise AssertionError('wrong sha256 accepted')
    except SystemExit:
        pass
    # pool(): pieces pooled across cases, naming over detected only
    case = lambda d, n, pr, pp: {c: {'pieces': [{'detected': x, 'named': y} for x, y in zip(d, n)],
                                     'present_ref': pr, 'present_pred': pp} for c in GATED}
    P = pool([case([1, 1], [1, 0], True, True), case([0], [0], True, False), case([], [], False, False)])
    assert P['OM2']['recall'] == 2 / 3 and P['OM2']['naming'] == 1 / 2 and P['OM2']['presence_agreement'] == 2 / 3
    print('gates selftest ok; j1f_gates.json sha256', hashlib.sha256(open(path, 'rb').read()).hexdigest())


if __name__ == '__main__':
    if sys.argv[1:] == ['selftest']:
        selftest()
