"""Delta, Round 10: a proposed D35 decision set. Deterministic, and it reads names only: no image and no read.

Rule (pre-registered here, before any read exists):
- **Eligible:** primary-stratum real patients (segtrain.pool_seal.ingest_patient) that are not sealed (D27/D32).
  ImageCHD and ImageALCAPA are left out (D29/D35), and so are the spacing-suspect sets: tF1's 1.5 mm tolerance is in
  mm, so a wrong spacing makes the score meaningless.
- **Size:** N = 35, which is 15 % of the 235 non-sealed, non-ImageCHD real patients (D35's "about 15 %"; D35's
  "about 50 of about 347" counts name-rule keys from before D32; see pool_census.py).
- **Allocation by source:** proportional to the source's share of the *primary pool* (the seal's own population),
  by largest remainder, capped by how many eligible patients the source has. A source with >= 5 primary patients
  gets at least one. The decision set therefore has the seal's source mix.
- **Draw within source:** rank by sha256(SALT + patient), lowest first. The salt is new, so this is not the seal's
  ranking.
- **Interaction with A30's extension order:** the order is kept, and it skips decision-set patients, as D32 skipped
  patients who were already sealed. The seal can therefore grow to 150 + (extension entries not in D35).
Usage: python3 d35_draw.py [--n 35] [--out proposal.json]"""
import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pool_census import census, stratum  # noqa: E402

SALT = 'asclepius-decision-round10-pool:'


def rank(p):
    return hashlib.sha256((SALT + p).encode()).hexdigest()


def draw(n):
    c = census()
    members, state, src = c['members'], c['state'], c['src']
    primary = [p for p in members if stratum(src[p]) == 'primary']
    elig = sorted(p for p in primary if state[p] != 'sealed')
    pool_by_src = defaultdict(int)
    for p in primary:
        pool_by_src[src[p]] += 1
    el_by_src = defaultdict(list)
    for p in elig:
        el_by_src[src[p]].append(p)
    for s in el_by_src:
        el_by_src[s].sort(key=rank)
    tot = len(primary)
    quota = {s: n * pool_by_src[s] / tot for s in el_by_src}
    alloc = {s: min(int(q), len(el_by_src[s])) for s, q in quota.items()}
    for s in el_by_src:
        if pool_by_src[s] >= 5 and alloc[s] == 0 and el_by_src[s]:
            alloc[s] = 1
    left = n - sum(alloc.values())
    order = sorted(quota, key=lambda s: (-(quota[s] - int(quota[s])), s))
    while left > 0:
        moved = False
        for s in order:
            if left > 0 and alloc[s] < len(el_by_src[s]):
                alloc[s] += 1
                left -= 1
                moved = True
        if not moved:
            break
    chosen = sorted(p for s in el_by_src for p in el_by_src[s][:alloc[s]])
    seal = json.load(open(os.path.join(HERE, '..', '..', '..', 'configs/segqueue14/sealed-pool-2026-10.json')))
    ext = seal['primary']['extension_order']
    ext_left = [p for p in ext if p not in set(chosen)]
    out = dict(
        rule='experiments/Delta/r10/d35_draw.py (Delta v10): primary, non-sealed real patients; N by D35 15 %; '
             'source allocation proportional to the primary pool; within source by sha256(salt + patient)',
        salt=SALT, n_patients=len(chosen), n_eligible=len(elig),
        seal_sha256='e71141b407acb79eeff912eee21029d34edb677d984172d871eb5f02cb1d0690',
        allocation_by_source={s: [alloc[s], len(el_by_src[s]), pool_by_src[s]] for s in sorted(el_by_src)},
        allocation_columns='[drawn, eligible (non-sealed primary), primary pool]',
        patients=chosen,
        volumes=sorted(v for p in chosen for v in members[p]),
        scoring_volume={p: min(members[p], key=rank) for p in chosen},
        state_of_drawn={k: sum(1 for p in chosen if state[p] == k) for k in sorted(set(state.values()))},
        extension_order_after_skip=len(ext_left),
        max_seal_after_skip=150 + len(ext_left),
        trainable_primary_if_seal_150=len(elig) - len(chosen),
    )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=35)
    ap.add_argument('--out')
    a = ap.parse_args()
    out = draw(a.n)
    s = json.dumps(out, indent=1)
    if a.out:
        open(a.out, 'w').write(s + '\n')
        print('sha256', hashlib.sha256((s + '\n').encode()).hexdigest())
    print(json.dumps({k: v for k, v in out.items() if k not in ('patients', 'volumes', 'scoring_volume')}, indent=1))


if __name__ == '__main__':
    main()
