"""Janus 1-F round 3 (Atlas): J1F-A's verdict table, with T_L written for both answers to Q-F2-3 (ruling §5 item 6).

Inputs, all from the ONE look on the locked 100 (F-A22: J1F-A is the track's first candidate look):
  v_F        V (track 1-L's H1 rule) of F's collapsed vessels against Janus 0's Fir predictions: pass/fail
  b_F, b_T   B (F-A15, >= 4 of 6) on F and on T: pass/fail
  l_adopted  Janus 1-L was adopted, and its locked-100 maps were on Fir, before `collect` started
  v_L        only if l_adopted: V's rule for F's collapsed vessels against Janus 1-L's maps (F non-inferior to 1-L)
  b_TL       only if l_adopted: B on T_L = compose(1-L's map, NAMES)
  q3         the lead's answer to Q-F2-3: 'yes', 'no' or None (unanswered when J1F-A is submitted = 'no')

Rule when q3 != 'yes' or not l_adopted (as ruled, F-A6/F-A19/F-A24): F if v_F and b_F; else T if b_T; else not
adopted. V_L and T_L, when 1-L is adopted, are reports.

Rule when q3 == 'yes' and l_adopted (Q-F2-3's recommendation, written as a rule):
  1. v_F and b_F and v_L      -> F        (1-F's own vessels are non-inferior to the best vessel model)
  2. v_F and b_F and not v_L  -> T_L if b_TL, else F
  3. not (v_F and b_F)        -> T_L if b_TL, else T if b_T, else not adopted
  V_L is tested only after V and B have passed on F (a fixed sequence), at the same one-sided 2.5 %. It never decides
  WHETHER a branch model is adopted, only WHOSE vessels ship. T_L's vessels are 1-L's adopted vessels, which already
  passed 1-L's own guard against Janus 0, so T_L needs no V. No new look: T_L is a third reading inside J1F-A's look.
If Janus 1-L is adopted only after `collect`: T_L can still be composed from the NAMES files, but it is a report,
like a2, and never ships (scoring it to ship would be a new look on the locked 100).
Self-test: python verdict.py selftest
"""
import itertools
import sys


def verdict(v_F, b_F, b_T, l_adopted=False, v_L=None, b_TL=None, q3=None):
    if q3 == 'yes' and l_adopted:
        if v_L is None or b_TL is None:
            raise ValueError('1-L adopted under Q-F2-3 = yes: V_L and B(T_L) must both be computed')
        if v_F and b_F:
            if v_L:
                return 'F'
            return 'T_L' if b_TL else 'F'
        if b_TL:
            return 'T_L'
        return 'T' if b_T else 'not adopted'
    if v_F and b_F:
        return 'F'
    return 'T' if b_T else 'not adopted'


def selftest():
    B = (True, False)
    # as ruled, whatever 1-L does, when q3 is not 'yes'
    for q3 in ('no', None):
        for v, bf, bt, la in itertools.product(B, B, B, B):
            r = verdict(v, bf, bt, la, v_L=True, b_TL=True, q3=q3)
            assert r == ('F' if v and bf else 'T' if bt else 'not adopted'), (q3, v, bf, bt, la, r)
    # q3 yes but 1-L not adopted before collect: as ruled
    assert verdict(True, True, True, False, q3='yes') == 'F'
    assert verdict(False, True, True, False, q3='yes') == 'T'
    # q3 yes and 1-L adopted
    assert verdict(True, True, True, True, v_L=True, b_TL=True, q3='yes') == 'F'
    assert verdict(True, True, True, True, v_L=False, b_TL=True, q3='yes') == 'T_L'
    assert verdict(True, True, True, True, v_L=False, b_TL=False, q3='yes') == 'F'
    assert verdict(False, True, True, True, v_L=False, b_TL=True, q3='yes') == 'T_L'
    assert verdict(False, True, True, True, v_L=False, b_TL=False, q3='yes') == 'T'
    assert verdict(True, False, False, True, v_L=True, b_TL=False, q3='yes') == 'not adopted'
    try:
        verdict(True, True, True, True, q3='yes'); raise AssertionError('accepted missing V_L')
    except ValueError:
        pass
    # never adopts a model whose branch reading failed B on every reading
    for v, vl in itertools.product(B, B):
        assert verdict(v, False, False, True, v_L=vl, b_TL=False, q3='yes') == 'not adopted'
    print('verdict selftest ok')


if __name__ == '__main__':
    if sys.argv[1:] == ['selftest']:
        selftest()
