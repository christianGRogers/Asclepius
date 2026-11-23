"""Janus 1-F round 3 (judge): the gate file of record (F-A27) against the scorer of record's gate arithmetic.

Atlas's round-3 test (`experiments/Atlas/j1f_r3/test_gates.py`) with the table swapped for F-A27's, plus the three
moved cells' edges. No data is read. Prints the file's and the scorer's sha256 (posted on #303).
Usage: python test_gates.py"""
import hashlib, os, sys
from fractions import Fraction as F

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../Atlas/j1f_r3'))
import j1f_scorer as S  # noqa: E402

PATH = os.path.join(HERE, 'j1f_gates.json')
SCORER = '5221032f3dc086d686b63fa946149a215ac00738a87fd9669d7faa15962b2e5b'
FA27 = {'D1': (0.81, 0.93, 0.83), 'D2': (0.76, 0.84, 0.86), 'OM1': (0.75, 0.90, 0.78), 'OM2': (0.60, 0.81, 0.78),
        'PDA': (0.89, 0.97, 0.90), 'PLB': (0.90, 0.95, 0.92)}   # recall, presence agreement, naming


def on_lines(g):
    return {k: {'recall': F(round(v['recall'] * 100), 100), 'presence': F(round(v['presence'] * 100), 100),
                'naming': F(round(v['naming'] * 100), 100)} for k, v in g['lines'].items()}


def check(g, cls, stat, num, want):
    a = on_lines(g); a[cls][stat] = F(num, 100)
    r = S.gate(a, g)
    assert r['classes'][cls]['pass'] is want, (cls, stat, num, r['classes'][cls])
    print(f'{cls} {stat} {num}/100 ->', 'pass' if want else 'FAIL')


def main():
    assert S.scorer_sha256() == SCORER, 'not the scorer of record'
    g = S.load_gates(PATH)
    assert {k: (v['recall'], v['presence'], v['naming']) for k, v in g['lines'].items()} == FA27, 'not F-A27'
    r = S.gate(on_lines(g), g)
    assert r['n_pass'] == 6 and r['verdict_pass'], r
    for args in (('OM2', 'recall', 59, False), ('OM2', 'recall', 60, True), ('OM2', 'recall', 61, True),
                 ('D1', 'presence', 92, False), ('D1', 'presence', 93, True),
                 ('PLB', 'recall', 89, False), ('PLB', 'recall', 90, True),
                 ('PLB', 'presence', 94, False), ('PLB', 'presence', 95, True)):
        check(g, *args)
    a = on_lines(g); a['OM2']['recall'] = F(59, 100)
    assert S.gate(a, g)['n_pass'] == 5 and S.gate(a, g)['verdict_pass']
    a['D2']['naming'] = F(85, 100); a['PLB']['presence'] = F(94, 100)
    r = S.gate(a, g)
    assert r['n_pass'] == 3 and not r['verdict_pass'], r
    a = on_lines(g); a['D1']['naming'] = None
    assert not S.gate(a, g)['classes']['D1']['pass']
    print('test_gates ok; j1f_gates.json sha256', hashlib.sha256(open(PATH, 'rb').read()).hexdigest(),
          '; scorer sha256', S.scorer_sha256())


if __name__ == '__main__':
    main()
