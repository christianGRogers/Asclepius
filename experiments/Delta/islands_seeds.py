"""E5b: label repair on random label islands, several seeds per case, to see the spread and catch
failure modes. Usage: python islands_seeds.py <out.jsonl> nseeds case [case ...]"""
import json, sys
import numpy as np
import perturb_metrics as P
import postproc
out, ns = sys.argv[1], int(sys.argv[2])
with open(out, 'a') as f:
    for case in sys.argv[3:]:
        gt = P.GT(case, 'icx')
        for seed in range(ns):
            P.RNG = np.random.default_rng(100 + seed)
            lab = P.perturb_labels(gt, 'islands')
            v = postproc.segment_vote(gt.m, lab, gt.sp)
            a = postproc.absorb_islands(gt.m, v, gt.sp)
            conf = lambda x: {f'{t}->{p}': int(((gt.lab == t) & (x == p)).sum()) for t in range(1, 5) for p in range(1, 5)
                              if t != p and ((gt.lab == t) & (x == p)).sum()}
            r = dict(case=case, seed=seed, wrong_pert=int((lab != gt.lab).sum()), wrong_vote=int((v != gt.lab).sum()),
                     wrong_after=int((a != gt.lab).sum()), conf_pert=conf(lab), conf_after=conf(a))
            f.write(json.dumps(r) + '\n'); f.flush()
        print(case, 'done', flush=True)
