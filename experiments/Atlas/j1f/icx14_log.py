"""Janus 1-F round 1 (Atlas): what the cancelled 14-class run (trillium/icx14) learned, from its training logs.
Parses every 'Pseudo dice' line (nnU-Net's per-class validation pseudo-Dice, logged each epoch) in
trillium-results/icx14/job2/results/training_log_*.txt. Lines with 13 values (a NaN class, which the regex skips) are
dropped. The two log files overlap in epochs; every logged line counts once.
Usage: python icx14_log.py <repo_root>"""
import re, glob, os, sys, json
import numpy as np
ROOT = sys.argv[1]
NAMES = "LM LAD LCx D1 D2 OM1 OM2 IM RCA R-PDA R-PLA L-PDA L-PLA Other".split()
rows, dropped, times = [], 0, []
for f in sorted(glob.glob(os.path.join(ROOT, 'trillium-results/icx14/job2/results/training_log_*.txt'))):
    ep = None
    for line in open(f):
        m = re.search(r'Epoch (\d+)\s*$', line)
        if m:
            ep = int(m.group(1))
        m = re.search(r'Epoch time: ([\d.]+) s', line)
        if m:
            times.append(float(m.group(1)))
        if 'Pseudo dice' in line:
            v = [float(x) for x in re.findall(r'float32\(([-\d.e]+)\)', line)]
            if len(v) == 14:
                rows.append((ep, v))
            else:
                dropped += 1
a = np.array([r[1] for r in rows]); eps = [r[0] for r in rows]
census = json.load(open(os.path.join(ROOT, 'trillium-results/icx14/job2/results/label_census.json')))
out = {'lines': len(rows), 'dropped_lines': dropped, 'epochs': [min(eps), max(eps)],
       'median_epoch_time_s': float(np.median(times)), 'classes': {}}
for i, n in enumerate(NAMES):
    nz = [e for e, x in zip(eps, a[:, i]) if x > 0]
    out['classes'][n] = {'cases_with_class': census['cases_with_class'][n], 'epochs_gt0': len(nz),
                         'first_epoch_gt0': min(nz) if nz else None, 'max': round(float(a[:, i].max()), 3),
                         'mean_last50': round(float(a[-50:, i].mean()), 3)}
print(json.dumps(out, indent=1))
