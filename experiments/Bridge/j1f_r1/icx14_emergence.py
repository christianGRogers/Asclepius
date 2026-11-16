"""When did each class first get a non-zero validation pseudo-Dice in the cancelled 14-class run (icx14)?
Reads the two nnU-Net training logs returned from Trillium (trillium-results/icx14), no compute.
Usage: icx14_emergence.py <repo_root> <out.json>"""
import json, re, sys
R = sys.argv[1]
LOGS = {'job1 (from scratch)': 'trillium-results/icx14/results/training_log_2026_10_11_18_52_59.txt',
        'job2 (restart from scratch after the resume fix)': 'trillium-results/icx14/job2/results/training_log_2026_10_13_18_46_59.txt'}
NAMES = 'LM LAD LCx D1 D2 OM1 OM2 IM RCA R-PDA R-PLA L-PDA L-PLA Other'.split()
out = {}
for k, p in LOGS.items():
    ep, rows = None, []
    for l in open(f'{R}/{p}'):
        m = re.search(r'Epoch (\d+)', l)
        if m:
            ep = int(m.group(1))
        if 'Pseudo dice' in l:
            v = [float(x) for x in re.findall(r'np.float32\(([\d.]+|nan)\)', l)]
            rows.append((ep, v))
    first = {n: next((e for e, v in rows if v[i] == v[i] and v[i] > 0), None) for i, n in enumerate(NAMES)}
    nz = {n: sum(1 for e, v in rows if v[i] == v[i] and v[i] > 0) for i, n in enumerate(NAMES)}
    last = dict(zip(NAMES, rows[-1][1]))
    out[k] = dict(epochs=len(rows), first_nonzero_epoch=first, epochs_nonzero=nz,
                  last_epoch=rows[-1][0], last_pseudo_dice={n: round(x, 3) for n, x in last.items()})
census = json.load(open(f'{R}/trillium-results/icx14/job2/results/label_census.json'))
out['cases_with_class_train_val_640'] = census['cases_with_class']
json.dump(out, open(sys.argv[2], 'w'), indent=1)
print(json.dumps(out, indent=1))
