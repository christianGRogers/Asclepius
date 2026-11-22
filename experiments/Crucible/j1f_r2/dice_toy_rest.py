"""Resume dice_toy's grid after an interrupted run: run the (dice, band, n_ext) rows missing from dice_toy.jsonl, with
the same seeds and the same band ratio, and append them. Usage: dice_toy_rest.py <census_head.jsonl>"""
import json, sys
import numpy as np
import dice_toy as D
done = {(r['dice'], r['band_mm'], r['n_ext']) for r in map(json.loads, open('dice_toy.jsonl'))}
ratio = D.band_ratio(sys.argv[1])
with open('dice_toy.jsonl', 'a') as f:
    for dice in ('oracle', 'naive', 'none', 'leaf', 'leaf_batch', 'leaf_skip', 'marginal', 'ignore'):
        for band in ('0', '8', '15'):
            for n_ext in (10, 30, 60):
                if (dice, band, n_ext) in done:
                    continue
                res = [D.run(dice, band, 0.0, n_ext, 100, ratio, seed=s) for s in range(5)]
                agg = {k: [round(float(np.mean([r[k] for r in res])), 3), round(float(np.std([r[k] for r in res])), 3)]
                       for k in res[0]}
                f.write(json.dumps({'dice': dice, 'band_mm': band, 'n_ext': n_ext, **agg}) + '\n'); f.flush()
