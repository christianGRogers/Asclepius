"""Summarise r5_aorta_rule.py: per rule, expert ostia within 5 mm on the thick reference; silent errors.

Rules: thick (endpoint), aorta_end (segtrain.tf1 as implemented: endpoint within 5 mm of the aorta,
else thick + flag), aorta_any (nearest centreline voxel to the aorta per component),
aorta_any_side (same, per component and side).
Usage: python summarise_r5_aorta.py ao.jsonl [ao.jsonl ...]"""
import json
import sys

rows = {}
for p in sys.argv[1:]:
    for line in open(p):
        r = json.loads(line)
        rows[r['case']] = r  # last wins (reruns)
ms = [dict(m, case=c) for c, r in rows.items() if 'matches' in r for m in r['matches'] if not m.get('missing')]
print('cases', len(rows), 'errors', [c for c, r in rows.items() if 'error' in r], 'expert ostia', len(ms))
for side in ('left', 'right', None):
    sub = [m for m in ms if side is None or m['side'] == side]
    res = {}
    for rule in ('thick', 'aorta_end_or_thick', 'aorta_any', 'aorta_any_side'):
        if rule == 'aorta_end_or_thick':
            ok = [m.get('aorta_end', m['thick']) <= 5 for m in sub]
        else:
            ok = [m.get(rule, 1e9) <= 5 for m in sub]
        res[rule] = f'{sum(ok)}/{len(sub)}'
    print(side or 'all', res)
# segtrain.tf1 as implemented: rule of record aorta_end (else thick, flagged)
silent = [m for m in ms if m.get('aorta_end', m['thick']) > 5 and not m['flagged']]
flag_ok = [m for m in ms if m['flagged'] and m.get('aorta_end', m['thick']) <= 5]
print('as implemented: wrong & unflagged (silent)', len(silent), [(m['case'], m['side']) for m in silent])
print('as implemented: flagged', sum(m['flagged'] for m in ms), 'of which actually right', len(flag_ok))
bad_side = [(m['case'], m['side'], m.get('aorta_any_side'), m.get('ao_side_mm')) for m in ms
            if m.get('aorta_any_side', 1e9) > 5]
print('aorta_any_side misses (case, side, mm to expert, its aorta distance):', bad_side)
