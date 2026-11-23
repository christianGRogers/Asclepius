"""Janus 1-F round 3 (Delta): apply F-A15's B lines (j1f_gates.json) to per-case scorer output (j1f_scorer.score_case).

`aggregate(rows, gates)` -> per-class recall / presence agreement / naming, pass flags, the 4-of-6 verdict.
`check_gates_file(path, sha)` refuses a gates file whose sha256 differs from the posted value, or whose scorer pin
differs from the scorer on disk. Self-test (synthetic counts only): python j1f_gate.py selftest
"""
import hashlib
import json
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
GATED = ('D1', 'D2', 'OM1', 'OM2', 'PDA', 'PLB')
REPORTED = ('D3', 'Ramus')


def load(path=os.path.join(HERE, 'j1f_gates.json')):
    return json.load(open(path))


def check_gates_file(path, posted_sha256, scorer_path=os.path.join(HERE, 'j1f_scorer.py')):
    got = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    if got != posted_sha256:
        raise SystemExit(f'REFUSE: {path} sha256 {got} != posted {posted_sha256}')
    g = json.load(open(path))
    s = hashlib.sha256(open(scorer_path, 'rb').read()).hexdigest()
    if g['scorer_sha256'] != s:
        raise SystemExit(f'REFUSE: gates pin scorer {g["scorer_sha256"]}, scorer on disk is {s}')
    return g


def _ge(k, n, line):
    """k/n >= line, exactly (line in hundredths)."""
    return n > 0 and Fraction(k, n) >= Fraction(round(line * 100), 100)


def counts(rows, cls):
    pieces = [p for r in rows for p in r[cls]['pieces']]
    n, det = len(pieces), sum(p['detected'] for p in pieces)
    named = sum(p['named'] for p in pieces)
    agree = sum(r[cls]['present_ref'] == r[cls]['present_pred'] for r in rows)
    return {'n_cases': len(rows), 'pieces': n, 'detected': det, 'named': named, 'presence_agree': agree,
            'cases_ref_present': sum(r[cls]['present_ref'] for r in rows)}


def classify(k, gates):
    out = {}
    for c in GATED:
        x, L = k[c], gates['lines'][c]
        r = {'recall': x['detected'] / x['pieces'] if x['pieces'] else float('nan'),
             'presence': x['presence_agree'] / x['n_cases'],
             'naming': x['named'] / x['detected'] if x['detected'] else float('nan')}
        r['B1'] = _ge(x['detected'], x['pieces'], L['recall']) and _ge(x['presence_agree'], x['n_cases'], L['presence'])
        r['B2'] = _ge(x['named'], x['detected'], L['naming'])
        r['pass'] = bool(r['B1'] and r['B2'])
        out[c] = {**x, **r}
    npass = sum(out[c]['pass'] for c in GATED)
    return {'classes': out, 'n_pass': npass, 'B': npass >= gates['min_passing']}


def aggregate(rows, gates):
    """rows: [score_case(ref, pred, zooms)] over the locked cases."""
    k = {c: counts(rows, c) for c in GATED + REPORTED}
    res = classify(k, gates)
    res['reported'] = {c: k[c] for c in REPORTED}
    return res


def selftest():
    g = load()
    base = {c: {'n_cases': 100, 'pieces': 100, 'detected': 100, 'named': 100, 'presence_agree': 100}
            for c in GATED}
    assert classify(base, g)['B'] and classify(base, g)['n_pass'] == 6
    # F-A15 / ruling §5 item 2: OM2 recall 0.59 fails, 0.61 passes (40 reference pieces is not enough to hit both,
    # so 100 pieces); 0.60 exactly passes (inclusive)
    for det, want in ((59, False), (60, True), (61, True)):
        k = {c: dict(v) for c, v in base.items()}
        k['OM2'].update(pieces=100, detected=det, named=det)
        r = classify(k, g)['classes']['OM2']
        assert r['B1'] is want and r['pass'] is want, (det, r)
    # the same on the locked-100 piece count for OM2 (about 41 pieces): 24/41 = 0.585 fails, 25/41 = 0.610 passes
    for det, want in ((24, False), (25, True)):
        k = {c: dict(v) for c, v in base.items()}
        k['OM2'].update(pieces=41, detected=det, named=det)
        assert classify(k, g)['classes']['OM2']['pass'] is want, det
    # naming and presence lines bite independently
    k = {c: dict(v) for c, v in base.items()}; k['PLB']['named'] = 91
    assert not classify(k, g)['classes']['PLB']['B2']
    k = {c: dict(v) for c, v in base.items()}; k['PDA']['presence_agree'] = 96
    assert not classify(k, g)['classes']['PDA']['B1']
    # the read rule: 4 of 6
    k = {c: dict(v) for c, v in base.items()}
    for c in ('D1', 'D2'):
        k[c]['detected'] = k[c]['named'] = 10
    assert classify(k, g)['B'] and classify(k, g)['n_pass'] == 4
    k['OM1']['detected'] = k['OM1']['named'] = 10
    assert not classify(k, g)['B']
    print('j1f_gate selftest ok; gates sha256', hashlib.sha256(open(os.path.join(HERE, 'j1f_gates.json'), 'rb').read()).hexdigest())


if __name__ == '__main__':
    if sys.argv[1:] == ['selftest']:
        selftest()
