# Summarise r5_corr.py: per scenario, mean tF1 of each scheme's converged target vs truth and vs reads (A10),
# inter-read tF1, and paired differences (a11 / agree / union minus single_or_both) with bootstrap 95% CI.
import json, glob, numpy as np, collections
W = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad/work/Crucible/r5corr'
rows = collections.defaultdict(list)
for f in sorted(glob.glob(W + '/*.json')):
    r = json.load(open(f)); rows[r['scenario']].append(r)
rng = np.random.default_rng(0)
P = ['single_or_both', 'a11', 'agree', 'union', 'truth']
for sc in ['indep', 'corr_trunc', 'corr_carina', 'annot_bias', 'team_bias', 'jitter']:
    R = rows.get(sc)
    if not R: continue
    print(f'\n## {sc} (n={len(R)}) inter-read {np.mean([r["inter_read"] for r in R]):.3f}')
    for p in P:
        print(f'  {p:15s} vsT {np.mean([r[p+"_vs_T"] for r in R]):.3f}  vsReads {np.mean([r[p+"_vs_reads"] for r in R]):.3f}  fg {np.mean([r[p+"_fg"] for r in R]):.3f}')
    for p in ['a11', 'agree', 'union']:
        for ref in ('T', 'reads'):
            d = np.array([r[f'{p}_vs_{ref}'] - r[f'single_or_both_vs_{ref}'] for r in R])
            bs = [rng.choice(d, len(d)).mean() for _ in range(4000)]
            print(f'  {p}-both vs{ref}: {d.mean():+.4f} [{np.percentile(bs,2.5):+.4f},{np.percentile(bs,97.5):+.4f}]')
    d = np.array([r['single_or_both_vs_reads'] - r['inter_read'] for r in R])
    print(f'  model(both) vs reads minus inter-read: {d.mean():+.3f}, positive in {(d>0).sum()}/{len(d)}')
