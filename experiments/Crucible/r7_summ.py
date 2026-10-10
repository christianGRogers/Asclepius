# Summarise r7_proxy_calib.py: per scenario, tF1 vs reads (A10) and vs truth of the raw proxy, the habit-calibrated
# proxy and the read-mode, with paired bootstrap CIs (calibrated - proxy, read_mode - proxy).
import json, glob, collections, numpy as np
W = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad/work/Crucible/r7calib'
rows = collections.defaultdict(list)
for f in glob.glob(W + '/*.json'):
    r = json.load(open(f)); rows[r['scenario']].append(r)
rng = np.random.default_rng(0)
for sc in ('indep', 'team_bias', 'annot_bias'):
    R = rows.get(sc)
    if not R: continue
    print(f"\n## {sc} n={len(R)} sh_hat {R[0]['sh_hat']:+.2f} mm rt_hat {R[0]['rt_hat']:.2f} mm inter-read {np.mean([r['inter_read'] for r in R]):.3f}")
    for k in ('proxy', 'calibrated', 'read_mode'):
        print(f"  {k:10s} vs reads {np.mean([r[k+'_vs_reads'] for r in R]):.3f}  vs truth {np.mean([r[k+'_vs_T'] for r in R]):.3f}")
    for k in ('calibrated', 'read_mode'):
        for ref in ('reads', 'T'):
            d = np.array([r[f'{k}_vs_{ref}'] - r[f'proxy_vs_{ref}'] for r in R])
            bs = [rng.choice(d, len(d)).mean() for _ in range(4000)]
            print(f"  {k}-proxy vs {ref}: {d.mean():+.3f} [{np.percentile(bs,2.5):+.3f}, {np.percentile(bs,97.5):+.3f}] better {int((d>0).sum())}/{len(d)}")
    d = np.array([r['proxy_vs_reads'] - r['inter_read'] for r in R])
    print(f"  proxy vs reads minus inter-read: {d.mean():+.3f}")
