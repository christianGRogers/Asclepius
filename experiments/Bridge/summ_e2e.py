"""Summarise e2e.jsonl: per arm mean tF1 @0 / @1.5 mm / @1.5 excluding ramus, swaps, paired namer-vs-oracle gap."""
import sys, json, numpy as np
R = [json.loads(l) for l in open(sys.argv[1])]
arms = ['oracle', 'namer', 'namer_nb', 'ceiling']
cases = sorted({r['case'] for r in R})
by = {(r['case'], r['arm']): r for r in R}
print('cases', len(cases))
for a in arms:
    S = [by[(c, a)] for c in cases if (c, a) in by]
    f = lambda k: np.mean([s[k] for s in S])
    print(f"{a:9s} tF1@0 {f('tf1'):.3f}  tF1@1.5 {f('tf1_tol1.5'):.3f}  noIM {f('tf1_tol1.5_noIM'):.3f}  per-class clDice {f('class_cldice'):.3f}  macroDice {f('macro_dice'):.3f}  label-acc {f('cl_label_acc'):.3f}  cases-with-swap {sum(1 for s in S if s['swapped_classes'])}/{len(S)}")
print('paired namer - oracle (tF1@1.5):', [round(by[(c, 'namer')]['tf1_tol1.5'] - by[(c, 'oracle')]['tf1_tol1.5'], 3) for c in cases])
print('paired namer - oracle (noIM):   ', [round(by[(c, 'namer')]['tf1_tol1.5_noIM'] - by[(c, 'oracle')]['tf1_tol1.5_noIM'], 3) for c in cases])
for c in cases:
    print(c, ' '.join(f"{a}={by[(c, a)]['tf1_tol1.5']:.3f}/{by[(c, a)]['tf1_tol1.5_noIM']:.3f}" for a in arms if (c, a) in by), 'IM' if by[(c, 'oracle')]['has_IM'] else '')
