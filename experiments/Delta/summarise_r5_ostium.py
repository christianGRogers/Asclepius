"""Summarise r5_ostium_thick.py: per rule, how often each expert ostium is within 5 mm on the thick
reference, by side, and how often a > 5 mm disagreement between rules flags the misses.

Usage: python summarise_r5_ostium.py out.jsonl [out.jsonl ...]"""
import collections
import json
import sys

RULES = ('thick', 'pool_thick', 'pool_near', 'pool_near_r')
rows = [json.loads(line) for p in sys.argv[1:] for line in open(p)]
ms = [dict(m, case=r['case']) for r in rows if 'matches' in r for m in r['matches'] if not m.get('missing')]
print('cases', len(rows), 'errors', sum('error' in r for r in rows), 'expert ostia matched', len(ms),
      'missing', sum(m.get('missing', False) for r in rows if 'matches' in r for m in r['matches']))
for side in ('left', 'right', None):
    sub = [m for m in ms if side is None or m['side'] == side]
    print(side or 'all', len(sub), {r: sum(m.get(r, 1e9) <= 5.0 for m in sub) for r in RULES})
# cross-check: thick vs pool_thick disagreement as the flag (what segtrain.tf1 does with a CT)
ok = collections.Counter()
for m in ms:
    t_ok, p_ok = m['thick'] <= 5, m.get('pool_thick', 1e9) <= 5
    agree = abs(m['thick'] - m.get('pool_thick', m['thick'])) < 1e-6  # same point chosen
    ok[(('agree' if agree else 'differ'), ('thick_ok' if t_ok else 'thick_bad'),
        ('pool_ok' if p_ok else 'pool_bad'))] += 1
for k, v in sorted(ok.items()):
    print(k, v)
print('misses of pool_thick:', [(m['case'], m['side'], m['thick'], m.get('pool_thick')) for m in ms
                                if m.get('pool_thick', 1e9) > 5])
