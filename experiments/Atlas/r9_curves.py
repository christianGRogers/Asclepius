"""Round 9: per-class validation pseudo-Dice against epoch and learning rate, from the nnU-Net training logs
returned from Trillium (run 1 = round5/atlas, run 2 B = round6/atlas2, run 3 F0/F1 = round7/atlas3, icx14 jobs 1-2).
Question: how many epochs does a 4-class (or 14-class main-vessel) model need before pseudo-Dice stops rising,
and how much does the low-LR tail of the poly schedule add? Output: JSON + a markdown table on stdout.
Usage: python r9_curves.py <repo_root> <out.json>"""
import json, re, sys, statistics, glob, os

ROOT, OUT = sys.argv[1], sys.argv[2]
LOGS = {
    'run1 (round5 atlas, thick proxy 4-class)': 'trillium-results/round5/atlas/results/training_log_2026_10_8_12_53_18.txt',
    'run2 B (round6 atlas2, thick 4-class)': 'trillium-results/round6/atlas2/results/training_log_2026_10_10_04_26_01.txt',
    'run3 F0 (warm from B, 200 ep)': 'trillium-results/round7/atlas3/training_log_F0.txt',
    'icx14 job1 (14-class)': 'trillium-results/icx14/results/training_log_2026_10_11_18_52_59.txt',
    'icx14 job2 (14-class, restarted)': 'trillium-results/icx14/job2/results/training_log_2026_10_13_18_46_59.txt',
}
num = re.compile(r'np\.float32\(([-0-9.e]+)\)')


def parse(path):
    ep, rows, cur = None, [], {}
    for line in open(path, errors='replace'):
        m = re.search(r': Epoch (\d+)\s*$', line)
        if m:
            if cur.get('dice') is not None:
                rows.append(cur)
            cur = {'epoch': int(m.group(1))}
            continue
        if 'Current learning rate' in line:
            cur['lr'] = float(line.rsplit(':', 1)[1].split()[0])
        elif 'Pseudo dice' in line:
            body = line.split('Pseudo dice', 1)[1]
            vals = num.findall(body) or re.findall(r'[-0-9.]+', body.split('[', 1)[1])
            cur['dice'] = [float(v) for v in vals]
        elif 'Epoch time' in line:
            cur['t'] = float(line.split('Epoch time:')[1].split()[0])
    if cur.get('dice') is not None:
        rows.append(cur)
    return rows


def window(rows, lo, hi, k):
    xs = [r['dice'][k] for r in rows if lo <= r['epoch'] < hi]
    return round(statistics.mean(xs), 3) if xs else None


res = {}
for name, rel in LOGS.items():
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    rows = parse(p)
    n_cls = len(rows[-1]['dice'])
    # LM, LAD, LCx, RCA: the first four in the 4-class sets; in ImageCAS-X's 14 classes RCA is value 9 (index 8)
    main = [0, 1, 2, 3] if n_cls == 4 else [0, 1, 2, 8]
    last = rows[-1]['epoch']
    marks = [e for e in (50, 100, 150, 200, 250, 300, 350, 400, 450) if e <= last + 1]
    tab = {}
    for e in marks:
        lo = max(0, e - 20)
        tab[e] = [window(rows, lo, e, k) for k in main]
    # first epoch at which the 20-epoch mean of each class reaches 98 % of its final 20-epoch mean
    final = [window(rows, last - 19, last + 1, k) for k in main]
    fin = dict(zip(main, final))
    reach = []
    for k in main:
        tgt = 0.98 * fin[k]
        hit = None
        for e in range(20, last + 2):
            v = window(rows, e - 20, e, k)
            if v is not None and v >= tgt:
                hit = e; break
        reach.append(hit)
    ts = [r['t'] for r in rows if 't' in r][1:]
    res[name] = dict(epochs=last + 1, n_classes=n_cls, lr_first=rows[0].get('lr'), lr_last=rows[-1].get('lr'),
                     median_epoch_s=round(statistics.median(ts), 1) if ts else None,
                     mean20_at=tab, final20=final, epoch_reaching_98pct_of_final=reach)
json.dump(res, open(OUT, 'w'), indent=1)
for name, r in res.items():
    print(f"\n### {name}: {r['epochs']} epochs, lr {r['lr_first']} -> {r['lr_last']}, median {r['median_epoch_s']} s/epoch")
    print('| 20-epoch mean ending at | LM | LAD | LCx | RCA |\n|---|---|---|---|---|')
    for e, v in r['mean20_at'].items():
        print(f'| {e} | ' + ' | '.join(str(x) for x in v) + ' |')
    print('| final 20 | ' + ' | '.join(str(x) for x in r['final20']) + ' |')
    print('| epoch reaching 98 % of final | ' + ' | '.join(str(x) for x in r['epoch_reaching_98pct_of_final']) + ' |')
