# Summarise r6_anchor_floor.py: convention floor of the carina anchor and the detection thresholds it implies.
import json, glob, sys, numpy as np
W = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad/work/Crucible/'
R = [json.load(open(f)) for f in glob.glob(W + 'r6anchor/*.json')]
ok = [r for r in R if 'skip' not in r]
print('cases', len(R), 'scored', len(ok), 'skipped', [(r['case'], r['skip']) for r in R if 'skip' in r][:10])
def desc(name, v):
    v = np.array(v); mad = 1.4826 * np.median(np.abs(v - np.median(v)))
    print(f'{name}: n={len(v)} mean {v.mean():+.2f} median {np.median(v):+.2f} SD {v.std(ddof=1):.2f} robustSD {mad:.2f} '
          f'p5 {np.percentile(v,5):+.2f} p95 {np.percentile(v,95):+.2f} |x|>2mm {np.mean(np.abs(v)>2):.2f}')
    return v.std(ddof=1), mad
desc('proxy - icx (mm)', [r['proxy_minus_icx'] for r in ok])
sd, mad = desc('thick skeleton bifurcation - icx carina (mm)', [r['skelbif_minus_icx'] for r in ok if 'skelbif_minus_icx' in r])
desc('icx LM length (mm)', [r['icx_lm_len_mm'] for r in ok])
for s in (sd, mad):
    # team-wide mean bias on n cases: detectable if |mean| > 1.96*s/sqrt(n) (+ floor mean subtracted)
    print(f'with per-case SD {s:.2f}: 95% CI half-width of a mean offset, n=50: {1.96*s/np.sqrt(50):.2f} mm; '
          f'two annotators x 25 cases each, difference: {1.96*s*np.sqrt(2/25):.2f} mm')
I = [json.load(open(f)) for f in glob.glob(W + 'r6inject/*.json')]
I = [r for r in I if 'skip' not in r]
if I:
    for k in ('inject_-2', 'inject_-1', 'inject_+1', 'inject_+2'):
        v = np.array([r[k] for r in I if r.get(k) is not None]); print(f'{k}: n={len(v)} read {v.mean():+.2f} ± {v.std(ddof=1):.2f} mm')
