"""How many read patients with a class present are needed before a per-class detection or naming rate can be
reported, and what a 35-patient D35 set gives at a given prevalence. Wilson 95 % intervals; pure arithmetic."""
import math


def wilson_half(p, n, z=1.96):
    d = 1 + z * z / n
    return z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d


def n_for(p, h):
    n = 2
    while wilson_half(p, n) > h:
        n += 1
    return n


if __name__ == '__main__':
    print('| rate p | n for +/-0.15 | n for +/-0.10 | n for +/-0.05 |')
    print('|---|---|---|---|')
    for p in (0.6, 0.7, 0.8, 0.9):
        print(f'| {p} | {n_for(p, .15)} | {n_for(p, .10)} | {n_for(p, .05)} |')
    print('\nHalf-width on D35 (35 patients) and on the seal (150) by prevalence, p = 0.8:')
    for prev in (1.0, 0.68, 0.5, 0.2, 0.07):
        print(f'prevalence {prev}: D35 n={round(35*prev)} +/-{wilson_half(.8, max(round(35*prev),1)):.2f}; '
              f'seal n={round(150*prev)} +/-{wilson_half(.8, max(round(150*prev),1)):.2f}')
    # difference between two models on the same branches (paired, discordant-pair share q): MDE ~ z*sqrt(q/n)
    print('\nPaired naming-rate difference, MDE at 80 % power, discordant share q = 0.2:')
    for n in (35, 50, 100, 200):
        print(f'n={n}: {(1.96+0.84)*math.sqrt(0.2/n):.3f}')
