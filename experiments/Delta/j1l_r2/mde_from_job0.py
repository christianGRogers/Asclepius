"""Delta, Janus 1-L round 2: restate the locked-100 MDE from Janus 0's own per-case spread (Round 1 ruling §5 item 4).

Reads only Job 0's baseline file, Janus 0 at argmax on the locked 100 (`scores/locked100_janus0_argmax.json`, the
r9 scorer's rows). L-A7 allows this: Janus 0's baseline is not a candidate look, and its per-case SD may update the
*stated* MDE, never a margin or a rule. No candidate model exists when it runs.

  SD_case   = SD over decisive cases of Janus 0's macro tF1 (A1a/A1b), and of its whole-tree Dice;
  SD_delta  = ratio x SD_case, with ratio 0.54 (warm siblings) and 0.64 (scratch pair), the two measured values
              (experiments/Delta/j1l_r1/power_locked100.json);
  MDE       = 2.802 x SD_delta / sqrt(n)   (80 % power, two-sided 5 %);
  for E     x 0.87 (ensemble_power.py: SD(E - J0) / SD(a1 - J0) at lam = 1, phi = 0.5; 1.0 if phi = 1).

Usage: python mde_from_job0.py $W/scores/locked100_janus0_argmax.json
"""
import json
import math
import statistics
import sys

RATIOS = {'warm siblings': 0.543, 'scratch pair': 0.637}
E_FACTOR = (0.87, 1.0)


def decisive(r):
    if r.get('provisional'):
        return None
    v = [x for c, x in r['per_class'].items() if c not in r.get('flagged_classes', [])]
    return statistics.mean(v) if v else None


def main(path):
    rows = [r for r in json.load(open(path))['rows'] if 'error' not in r]
    tf = [d for d in (decisive(r) for r in rows) if d is not None]
    dc = [r['dice']['tree'] for r in rows if r.get('dice', {}).get('tree') is not None]
    out = {'n_decisive': len(tf), 'sd_case_tf1': round(statistics.stdev(tf), 4),
           'sd_case_dice': round(statistics.stdev(dc), 4), 'mde': {}}
    for name, k in RATIOS.items():
        for metric, sd in (('tf1', out['sd_case_tf1']), ('dice', out['sd_case_dice'])):
            m = 2.802 * k * sd / math.sqrt(len(tf))
            out['mde'][f'{metric}, {name}'] = {'a1': round(m, 4), 'E': [round(m * f, 4) for f in E_FACTOR]}
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
