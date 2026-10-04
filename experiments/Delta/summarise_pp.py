"""Summarise pp2.jsonl (E5): label repair before/after, per perturbation."""
import json, sys
from collections import defaultdict
rows = [json.loads(l) for l in open(sys.argv[1])]
by = defaultdict(list)
for r in rows:
    by[r['kind']].append(r)
print('cases', sorted({r['case'] for r in rows}))
print('kind        n  wrong_vox before -> after   tF1 before -> after   macroDice before -> after   class-piece excess before -> after')
for k, rs in by.items():
    f = lambda key, ba: sum(r[ba][key] for r in rs) / len(rs)
    print(f"{k:11s} {len(rs)}  {sum(r['wrong_before'] for r in rs):6d} -> {sum(r['wrong_after'] for r in rs):6d}"
          f"     {f('tf1','before'):.3f} -> {f('tf1','after'):.3f}     {f('macro_dice','before'):.3f} -> {f('macro_dice','after'):.3f}"
          f"     {f('class_comp_excess','before'):.2f} -> {f('class_comp_excess','after'):.2f}")
