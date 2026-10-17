"""Summarise evaluate.py output(s)."""
import sys, json, numpy as np
for f in sys.argv[1:]:
    R = [json.loads(l) for l in open(f)]
    S = [r for r in R if r.get('dice')]
    print('==', f.split('/')[-1], 'cases', len(R), 'with ICX', len(S), 'fails', sum(1 for r in R if r.get('fail')))
    if not S:
        continue
    for k in ('LM', 'LAD', 'LCx', 'RCA', 'acc'):
        v = np.array([r['dice'][k] for r in S if r['dice'][k] is not None])
        print('  %-4s mean %.3f median %.3f p10 %.3f  >=0.9: %.3f  <0.5: %.3f' % (k, v.mean(), np.median(v), np.percentile(v, 10), (v >= .9).mean(), (v < .5).mean()))
    ok = [all(r['dice'][k] >= 0.8 for k in ('LM', 'LAD', 'LCx', 'RCA') if r['dice'][k] is not None) for r in S]
    print('  cases all 4 classes Dice>=0.8: %.3f' % np.mean(ok))
    oe = np.array([r['ostium_err'] for r in S if 'ostium_err' in r])
    print('  ostium within 5 mm of ICX ostium: %.3f (n=%d)' % ((oe < 5).mean(), len(oe)))
