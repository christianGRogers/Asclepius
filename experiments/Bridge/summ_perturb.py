import sys, json, numpy as np
R = [json.loads(l) for l in open(sys.argv[1])]
for kind, lvl in [('gaps', 0), ('gaps', 1), ('gaps', 3), ('gaps', 6), ('prune', 10), ('prune', 25)]:
    S = [r for r in R if r['kind'] == kind and r['lvl'] == lvl and r['dice']]
    if not S: continue
    ok = np.mean([all(r['dice'][k] >= 0.8 for k in ('LM', 'LAD', 'LCx', 'RCA') if r['dice'][k] is not None) for r in S])
    acc = np.mean([r['dice']['acc'] for r in S])
    m = {k: np.nanmean([r['dice'][k] if r['dice'][k] is not None else np.nan for r in S]) for k in ('LM', 'LAD', 'LCx', 'RCA')}
    print(f'{kind:5s} {lvl:2d}  n={len(S)} comps={np.mean([r["ncomp"] for r in S]):.1f} kept_vox={np.mean([r["kept_vox"] for r in S]):.3f} acc={acc:.3f} all>=0.8={ok:.3f} ' + ' '.join(f'{k}={v:.3f}' for k, v in m.items()) + f' fails={sum(1 for r in R if r["kind"]==kind and r["lvl"]==lvl and r.get("fail"))}')
