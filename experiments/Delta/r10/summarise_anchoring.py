"""Summarise anchoring_sim.py's per-case rows: per condition and class, mean inter-read tF1, model-vs-read tF1 (M0 =
ImageCAS-X exactly, M1 = Janus 0's width), the A10 contrast d = model - inter with a case-bootstrap CI, and
model recall and precision against the reads.

A (case, class) is left out of a condition when the reads lost that class's tree, i.e. inter-read tF1 is exactly 0:
a trimmed short tree below segtrain.tf1's 1000-voxel minimum has no ostium. These are counted.
Usage: summarise_anchoring.py <rows.jsonl> [--out summary.json]"""
import argparse
import json

import numpy as np

CL = ['LM', 'LAD', 'LCx', 'RCA']
CONDS = ['indep', 'indep_wide', 'anch0', 'anch5', 'anch10', 'anch20']


def ci(x, n=2000, seed=0):
    x = np.asarray(x, float)
    if len(x) < 3:
        return [None, None]
    rng = np.random.default_rng(seed)
    b = x[rng.integers(0, len(x), (n, len(x)))].mean(1)
    return [round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rows')
    ap.add_argument('--out')
    a = ap.parse_args()
    rows = [json.loads(ln) for ln in open(a.rows) if ln.strip()]
    errs = [r for r in rows if 'error' in r]
    rows = [r for r in rows if 'error' not in r]
    out = dict(n_cases=len(rows), n_errors=len(errs), errors=[e['error'][:120] for e in errs[:3]], conditions={})
    for cond in CONDS:
        res, dropped = {}, 0
        for c in CL:
            inter, m0, m1, d0, d1, rec, prec = [], [], [], [], [], [], []
            for r in rows:
                x = r.get(cond)
                if not x or c not in x['inter'] or c not in x['M0']:
                    continue
                if x['inter'][c] == 0.0:
                    dropped += 1
                    continue
                inter.append(x['inter'][c]); m0.append(x['M0'][c]); d0.append(x['M0'][c] - x['inter'][c])
                rec.append(x['M0_recall'][c]); prec.append(x['M0_precision'][c])
                if 'M1' in x and c in x['M1']:
                    m1.append(x['M1'][c]); d1.append(x['M1'][c] - x['inter'][c])
            if not inter:
                continue
            res[c] = dict(n=len(inter), inter=round(float(np.mean(inter)), 4), M0=round(float(np.mean(m0)), 4),
                          d_M0=round(float(np.mean(d0)), 4), d_M0_ci=ci(d0), sd_d_M0=round(float(np.std(d0, ddof=1)), 4),
                          M0_recall=round(float(np.mean(rec)), 4), M0_precision=round(float(np.mean(prec)), 4))
            if m1:
                res[c].update(M1=round(float(np.mean(m1)), 4), d_M1=round(float(np.mean(d1)), 4), d_M1_ci=ci(d1),
                              M1_minus_M0=round(float(np.mean(np.array(m1) - np.array(m0))), 4))
        out['conditions'][cond] = dict(per_class=res, dropped_lost_tree=dropped)
    seeds = {}
    for L in (0, 5, 10, 20):
        k = f'seed{L}_vs_indep'
        seeds[k] = {c: round(float(np.mean([r[k][c] for r in rows if c in r.get(k, {})])), 4) for c in CL
                    if any(c in r.get(k, {}) for r in rows)}
    out['seed_vs_independent_read'] = seeds
    s = json.dumps(out, indent=1)
    if a.out:
        open(a.out, 'w').write(s)
    print(f"{out['n_cases']} cases, {out['n_errors']} errors")
    print('| condition | class | n | inter | M0 | d (M0) [CI] | M0 recall | M0 precision | M1 - M0 |')
    for cond, v in out['conditions'].items():
        for c, x in v['per_class'].items():
            print(f"| {cond} | {c} | {x['n']} | {x['inter']} | {x['M0']} | {x['d_M0']} {x['d_M0_ci']} | "
                  f"{x['M0_recall']} | {x['M0_precision']} | {x.get('M1_minus_M0', '')} |")
        print(f"|   ({cond}: {v['dropped_lost_tree']} (case, class) pairs dropped, lost tree) |")
    print('seed vs an independent read:', json.dumps(seeds))


if __name__ == '__main__':
    main()
