"""Foxtrot, Round 10: how noisy is a paired per-case comparison of two models, measured on the paired runs we have.

A D35 decision compares two models on the same patients. Its precision depends on the SD of the per-case
difference (case term) and on the model-level shift between trainings (seed term, A22). This measures the case
term on the three real paired runs in trillium-results (val 80, A1 ostia, pinned tF1; no sealed case):
  * atlas3 F1 - F0: two warm fine-tunes from one base (A17a trainer), same seed and data stream, 200 epochs, a
    near-zero loss term (0.0001): the closest thing we have to two fine-tunes that differ only by run noise;
  * atlas2 B - run 1: two from-scratch trainings that differ by recipe (window) and length (412 epochs each);
  * atlas3 F0 - atlas2 B: a 200-epoch warm fine-tune against its own base (what fine-tuning moves per case).
Per class: unflagged in both models. Macro: mean over the case's scored classes (as segtrain does).
Also prints each model's per-class SD (the spread the A10 power model resamples).
Output: results/paired_noise.json.
"""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
T = os.path.join(REPO, 'trillium-results')
FILES = {
    'run1': f'{T}/round6/atlas2/results/per_case_run1.json',
    'B': f'{T}/round6/atlas2/results/per_case_b.json',
    'F0': f'{T}/round7/atlas3/per_case_F0.json',
    'F1': f'{T}/round7/atlas3/per_case_F1.json',
}
CL = {'1': 'LM', '2': 'LAD', '3': 'LCx', '4': 'RCA'}
PAIRS = [('F1', 'F0', 'warm FT replicate (same base, seed, stream)'),
         ('B', 'run1', 'from-scratch, different recipe'),
         ('F0', 'B', 'warm FT vs its base')]


def load(name):
    rows = json.load(open(FILES[name]))
    out = {}
    for r in rows:
        fl = {str(x) for x in r.get('flagged_classes', [])}
        out[r['case']] = {c: v for c, v in r['per_class'].items() if v is not None and c not in fl}
    return out


def boot(x, rng, n=4000):
    x = np.asarray(x)
    b = x[rng.integers(0, len(x), (n, len(x)))].mean(1)
    return [round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)]


def main():
    rng = np.random.default_rng(20261025)
    M = {k: load(k) for k in FILES}
    res = {'model_sd': {}, 'pairs': {}}
    for k, d in M.items():
        res['model_sd'][k] = {CL[c]: [round(float(np.std([v[c] for v in d.values() if c in v], ddof=1)), 4),
                                      round(float(np.mean([v[c] for v in d.values() if c in v])), 4)]
                              for c in CL}
    for a, b, label in PAIRS:
        cases = sorted(set(M[a]) & set(M[b]))
        row = {'label': label, 'n_cases': len(cases)}
        macro = []
        for c in CL:
            d = [M[a][k][c] - M[b][k][c] for k in cases if c in M[a][k] and c in M[b][k]]
            row[CL[c]] = {'n': len(d), 'mean': round(float(np.mean(d)), 4), 'sd_diff': round(float(np.std(d, ddof=1)), 4),
                          'ci': boot(d, rng), 'share_exact_zero': round(float(np.mean(np.isclose(d, 0))), 3),
                          'corr': round(float(np.corrcoef([M[a][k][c] for k in cases if c in M[a][k] and c in M[b][k]],
                                                          [M[b][k][c] for k in cases if c in M[a][k] and c in M[b][k]])[0, 1]), 3)}
        for k in cases:
            common = [c for c in CL if c in M[a][k] and c in M[b][k]]
            if common:
                macro.append(np.mean([M[a][k][c] for c in common]) - np.mean([M[b][k][c] for c in common]))
        row['macro'] = {'n': len(macro), 'mean': round(float(np.mean(macro)), 4),
                        'sd_diff': round(float(np.std(macro, ddof=1)), 4), 'ci': boot(macro, rng)}
        res['pairs'][f'{a}-{b}'] = row
    os.makedirs(os.path.join(HERE, 'results'), exist_ok=True)
    json.dump(res, open(os.path.join(HERE, 'results', 'paired_noise.json'), 'w'), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
