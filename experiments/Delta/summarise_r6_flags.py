"""Summarise r6_flags.py (A1b): flag rate of the revised A1 rule per tree, by side and CT availability, and the
ostium accuracy of flagged vs unflagged trees. Usage: python summarise_r6_flags.py flags.jsonl"""
import json
import sys

rows = [json.loads(line) for line in open(sys.argv[1])]
trees = [dict(t, case=r['case'], has_ct=r['has_ct']) for r in rows if 'trees' in r for t in r['trees']]
print('cases', len(rows), 'errors', [r['case'] for r in rows if 'error' in r], 'trees', len(trees))
for name, sub in (('all', trees), ('with CT (pool_thick cross-check)', [t for t in trees if t['has_ct']]),
                  ('no CT', [t for t in trees if not t['has_ct']]),
                  ('left', [t for t in trees if t['side'] == 'left']), ('right', [t for t in trees if t['side'] == 'right'])):
    if not sub:
        continue
    f = [t for t in sub if t['flagged']]
    u = [t for t in sub if not t['flagged']]
    ok = lambda ts: sum(t['d_true_mm'] is not None and t['d_true_mm'] <= 5 for t in ts)  # noqa: E731
    known = lambda ts: sum(t['d_true_mm'] is not None for t in ts)  # noqa: E731
    print(f'{name}: {len(sub)} trees, flagged {len(f)} ({len(f) / len(sub):.0%}); '
          f'unflagged right {ok(u)}/{known(u)}, flagged right {ok(f)}/{known(f)}; '
          f'rule=thick (no aorta contact) {sum(t["rule"] == "thick" for t in sub)}')
silent = [(t['case'], t['side'], t['d_true_mm']) for t in trees if not t['flagged'] and t['d_true_mm'] is not None
          and t['d_true_mm'] > 5]
print('silent errors (unflagged, > 5 mm):', len(silent), silent)
