"""Janus 1-F round 3 (Atlas): `j1f_gates.json` against F-A15, and the gate arithmetic (ruling §5 item 2).

* The file's lines equal F-A15's table exactly; k_of_6 is 4.
* A fixture locked-100 aggregate where every class sits exactly on its lines passes 6 of 6.
* OM2 recall 59/100 fails OM2; 60/100 passes (the line is inclusive); 61/100 passes.
* With OM2 failing and two more classes failing (3 of 6), the verdict fails; with OM2 failing alone (5 of 6) it passes.
* A class with no detected piece (naming undefined) fails.
Prints the file's sha256 (to be posted on #303 with the scorer's).
Usage: python test_gates.py
"""
import hashlib
import json
import os
import sys
from fractions import Fraction as F

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1f_scorer as S  # noqa: E402

PATH = os.path.join(HERE, 'j1f_gates.json')
FA15 = {'D1': (0.81, 0.94, 0.83), 'D2': (0.76, 0.84, 0.86), 'OM1': (0.75, 0.90, 0.78), 'OM2': (0.60, 0.81, 0.78),
        'PDA': (0.89, 0.97, 0.90), 'PLB': (0.89, 0.94, 0.92)}   # recall, presence agreement, naming


def on_lines(g):
    """Exact counts sitting on each line: 100 pieces, 100 cases, detected = named denominators chosen to hit it."""
    agg = {}
    for k, ln in g['lines'].items():
        det = round(ln['recall'] * 100)
        named = round(ln['naming'] * 100)
        agg[k] = {'recall': F(det, 100), 'presence': F(round(ln['presence'] * 100), 100), 'naming': F(named, 100)}
    return agg


def main():
    g = S.load_gates(PATH)
    assert {k: (v['recall'], v['presence'], v['naming']) for k, v in g['lines'].items()} == FA15, 'not F-A15'
    assert g['k_of_6'] == 4
    agg = on_lines(g)
    r = S.gate(agg, g)
    assert r['n_pass'] == 6 and r['verdict_pass'], r
    for det, want in ((59, False), (60, True), (61, True)):
        a = on_lines(g); a['OM2']['recall'] = F(det, 100)
        r = S.gate(a, g)
        assert r['classes']['OM2']['pass'] is want, (det, r['classes']['OM2'])
        print(f'OM2 recall {det}/100 ->', 'pass' if want else 'FAIL')
    a = on_lines(g); a['OM2']['recall'] = F(59, 100)
    assert S.gate(a, g)['n_pass'] == 5 and S.gate(a, g)['verdict_pass']
    a['D2']['naming'] = F(85, 100); a['PLB']['presence'] = F(93, 100)
    r = S.gate(a, g)
    assert r['n_pass'] == 3 and not r['verdict_pass'], r
    a = on_lines(g); a['D1']['naming'] = None
    assert not S.gate(a, g)['classes']['D1']['pass']
    print('test_gates ok; j1f_gates.json sha256', hashlib.sha256(open(PATH, 'rb').read()).hexdigest(),
          '; scorer sha256', S.scorer_sha256())


if __name__ == '__main__':
    main()
