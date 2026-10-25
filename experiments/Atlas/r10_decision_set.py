"""Atlas, Round 10 (#113): the D35 decision set -- pool accounting on real patients, and the draw.

D35 (2026-10-25): about 15 % of the non-sealed, non-ImageCHD pool patients are held out as the decision set for
wave-1 fine-tune and recipe questions, drawn at patient level by salted hash within source, frozen before any read
of them is looked at or trained on, never trained on. Round 10 sets the size, salt and draw.

What this script does (CPU, no image is opened, no read exists or is read):

1. Accounting. Every pool volume (configs/segqueue14/pool-2026-10.txt) is grouped into its real patient by the
   project's rule (segtrain.pool_seal.ingest_patient, D32/D33) and placed in exactly one bucket:
     sealed_primary / sealed_report_only (D27/D32: the 150 + 20 ImageCHD),
     reserve (the first 100 patients of the seal's pre-registered extension order: the seal grows into them at
              200 and 250, D27/A31.1, so they stay unread-by-analysis and untrained until the extension is decided),
     ext_tail (extension-order entries after the first 100),
     open_primary (primary, in none of the above),
     imagechd_open, spacing_suspect (ImageALCAPA, HOCMvalvesSeg, CCA200-HF; D29: out of A10 until re-gridded).
   It reconciles the two counts the issue quotes (#43's "about 50 of about 347" and the wave-1 note's 198).

2. The draw. The decision set is drawn from the primary stratum only (it decides what is best for the population
   A10 scores), outside the seal and the 100-patient reserve, so it changes neither D27's seal nor its 200-250
   extension. Allocation across sources is proportional to the eligible patients per source (largest remainder);
   within a source, patients are ranked by sha256(SALT + patient). A pre-registered top-up order over the reserve
   (same salt) says which released reserve patients join the decision set if the seal does not grow to 250.

Usage:
    python experiments/Atlas/r10_decision_set.py --n 35 --out experiments/Atlas/r10/decision_set_proposal.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))

from segtrain.pool_seal import ingest_patient, load_pool_seal  # noqa: E402

POOL = os.path.join(REPO, 'configs', 'segqueue14', 'pool-2026-10.txt')
SEAL = os.path.join(REPO, 'configs', 'segqueue14', 'sealed-pool-2026-10.json')
SALT = 'asclepius-decision-round10-pool:'
RESERVED = 100                       # the seal can grow to 250 = 150 + the first 100 of the extension order
REPORT_ONLY = {'ImageCHD'}           # D29 / the seal file's report-only stratum
SPACING_SUSPECT = {'ImageALCAPA', 'HOCMvalvesSeg', 'CCA200-HF'}   # D29: out of A10 until re-gridded


def stem(v: str) -> str:
    return v[:-len('.nii.gz')] if v.endswith('.nii.gz') else v


def source(v: str) -> str:
    return v.split('__')[0]


def rank(p: str) -> str:
    return hashlib.sha256((SALT + p).encode()).hexdigest()


def sha256_file(path: str) -> str:
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def accounting():
    vols = [l.strip() for l in open(POOL) if l.strip() and not l.startswith('#')]
    serve_pos = {v: i for i, v in enumerate(vols)}             # the list is in serve order (D23, D30)
    seal = load_pool_seal(SEAL)                                 # sha256-pinned; refuses a changed file
    d = json.load(open(SEAL))
    sealed_prim = set(d['primary']['patients'])
    sealed_rep = set(d['report_only']['patients'])
    ext = list(d['primary']['extension_order'])
    reserve, tail = set(ext[:RESERVED]), set(ext[RESERVED:])
    members = defaultdict(list)
    for v in vols:
        members[ingest_patient(stem(v))].append(v)
    bucket = {}
    for p, vs in members.items():
        s = source(vs[0])
        if p in sealed_prim:
            b = 'sealed_primary'
        elif p in sealed_rep:
            b = 'sealed_report_only'
        elif s in REPORT_ONLY:
            b = 'imagechd_open'
        elif s in SPACING_SUSPECT:
            b = 'spacing_suspect'
        elif p in reserve:
            b = 'reserve'
        elif p in tail:
            b = 'ext_tail'
        else:
            b = 'open_primary'
        # every volume of a sealed patient must be refused by the guard, and none of an open one
        for v in vs:
            assert seal.is_sealed(v) == b.startswith('sealed'), (v, b)
        bucket[p] = b
    return vols, serve_pos, members, bucket, ext


def draw(members, bucket, n: int):
    """Capped proportional allocation. Each source's target is its share of the whole primary stratum (sealed,
    reserve and open alike: the population A10 scores), capped at the eligible patients it has left; the shortfall
    is re-spread over the uncapped sources, then largest remainder. Within a source, the lowest salted ranks."""
    eligible = sorted(p for p, b in bucket.items() if b in ('open_primary', 'ext_tail'))
    by_src = defaultdict(list)
    for p in eligible:
        by_src[source(members[p][0])].append(p)
    for s in by_src:
        by_src[s].sort(key=rank)
    weight = Counter(source(members[p][0]) for p, b in bucket.items()
                     if b in ('sealed_primary', 'reserve', 'ext_tail', 'open_primary'))
    cap = {s: len(v) for s, v in by_src.items()}
    alloc, free, left = {}, set(by_src), n
    while True:                                   # water-filling: fix capped sources, re-spread the rest
        w = sum(weight[s] for s in free)
        quota = {s: left * weight[s] / w for s in free}
        over = {s for s in free if quota[s] >= cap[s]}
        if not over:
            break
        for s in over:
            alloc[s] = cap[s]
            left -= cap[s]
        free -= over
    base = {s: int(quota[s]) for s in free}
    rem = left - sum(base.values())
    for s in sorted(free, key=lambda s: (-(quota[s] - base[s]), rank(s)))[:rem]:
        base[s] += 1
    alloc.update(base)
    chosen = sorted(p for s, v in by_src.items() for p in v[:alloc.get(s, 0)])
    alloc_out = {s: [alloc.get(s, 0), len(v)] for s, v in sorted(by_src.items())}
    return chosen, alloc_out, eligible


def topup(members, bucket, ext, chosen, to: int):
    """The second tranche, pre-registered now for each way the seal can end (A31.1: 150, 200 or 250 patients).
    The seal extends along the *front* of its order (entries 1-50 at 200, 51-100 at 250), so what is released is
    the back of the 100-patient reserve: all 100 if it stays at 150, entries 51-100 at 200, none at 250. Released
    patients join the decision set one at a time until it holds ``to``: each step takes the source furthest below
    its share of the primary stratum (weight x size - current count), and within it the lowest salted rank.
    Every released patient not taken is trainable. No read of a reserve patient is looked at before release."""
    weight = Counter(source(members[p][0]) for p, b in bucket.items()
                     if b in ('sealed_primary', 'reserve', 'ext_tail', 'open_primary'))
    tot = sum(weight.values())
    reserve = [p for p in ext[:RESERVED] if bucket.get(p) == 'reserve']
    out = {}
    for seal_size, released in ((150, reserve), (200, reserve[50:]), (250, [])):
        pool = defaultdict(list)
        for p in released:
            pool[source(members[p][0])].append(p)
        for v in pool.values():
            v.sort(key=rank)
        have = Counter(source(members[p][0]) for p in chosen)
        added = []
        while len(chosen) + len(added) < to and any(pool.values()):
            size = len(chosen) + len(added) + 1
            s = max((s for s in pool if pool[s]),
                    key=lambda s: (weight[s] / tot * size - have[s], weight[s], rank(s)))
            added.append(pool[s].pop(0))
            have[s] += 1
        out[str(seal_size)] = {'n_released': len(released), 'joins_decision_set': added,
                               'by_source': dict(Counter(source(members[p][0]) for p in added))}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=35)
    ap.add_argument('--topup-to', type=int, default=50,
                    help='decision-set size to reach from released reserve patients, if the seal stops below 250')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    vols, serve_pos, members, bucket, ext = accounting()
    counts = Counter(bucket.values())
    vcounts = Counter()
    for p, b in bucket.items():
        vcounts[b] += len(members[p])
    chosen, alloc, eligible = draw(members, bucket, a.n)
    top = topup(members, bucket, ext, chosen, a.topup_to)

    # serve-order position (fraction of the 675-volume queue) of the first volume of each patient
    def first_pos(p):
        return min(serve_pos[v] for v in members[p]) / len(vols)

    def q(xs):
        xs = sorted(xs)
        return [round(xs[int(f * (len(xs) - 1))], 3) for f in (0.1, 0.5, 0.9)] if xs else None

    non_sealed = [p for p, b in bucket.items() if not b.startswith('sealed')]
    non_sealed_non_chd = [p for p in non_sealed if bucket[p] != 'imagechd_open']
    out = {
        'what': 'Atlas Round 10 proposal for the D35 decision set (not binding until the judge and the lead adopt it)',
        'salt': SALT,
        'pool_list': os.path.relpath(POOL, REPO), 'pool_list_sha256': sha256_file(POOL),
        'seal': os.path.relpath(SEAL, REPO), 'seal_sha256': sha256_file(SEAL),
        'patient_rule': 'segtrain.pool_seal.ingest_patient (D32/D33)',
        'drawn_from': 'primary stratum, not sealed, not among the first 100 of the seal extension order',
        'allocation': 'each source at its share of the whole primary stratum, capped at its eligible patients '
                      '(water-filling, then largest remainder); within source by sha256(salt + patient)',
        'accounting_patients': dict(sorted(counts.items())),
        'accounting_volumes': dict(sorted(vcounts.items())),
        'n_patients_total': len(bucket),
        'n_non_sealed': len(non_sealed),
        'n_non_sealed_non_imagechd': len(non_sealed_non_chd),
        'fifteen_percent_of_non_sealed_non_imagechd': round(0.15 * len(non_sealed_non_chd), 1),
        'n_eligible': len(eligible),
        'decision_set': {
            'n_patients': len(chosen),
            'n_volumes': sum(len(members[p]) for p in chosen),
            'allocation_[drawn,eligible]_by_source': alloc,
            'patients': chosen,
            'volumes': sorted(v for p in chosen for v in members[p]),
            'serve_position_p10_p50_p90': q([first_pos(p) for p in chosen]),
        },
        'trainable_before_extension_decision': {
            'primary_patients': sorted(p for p in eligible if p not in set(chosen)),
            'serve_position_p10_p50_p90': q([first_pos(p) for p in eligible if p not in set(chosen)]),
        },
        'topup': {
            'rule': f'second tranche: if the seal ends below 250 patients (A31.1), released reserve patients join the '
                    f'decision set until it holds {a.topup_to}, the most under-represented source first; the rest '
                    f'of the released reserve is trainable',
            'to': a.topup_to,
            'by_final_seal_size': top,
        },
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w') as f:
        json.dump(out, f, indent=1)
        f.write('\n')
    print(json.dumps({k: out[k] for k in ('accounting_patients', 'accounting_volumes', 'n_patients_total',
                                          'n_non_sealed', 'n_non_sealed_non_imagechd',
                                          'fifteen_percent_of_non_sealed_non_imagechd', 'n_eligible')}, indent=1))
    print('decision set:', out['decision_set']['n_patients'], 'patients,', out['decision_set']['n_volumes'],
          'volumes; serve position', out['decision_set']['serve_position_p10_p50_p90'])
    print('allocation:', alloc)
    print('trainable primary before the extension decision:',
          len(out['trainable_before_extension_decision']['primary_patients']),
          out['trainable_before_extension_decision']['serve_position_p10_p50_p90'])
    print('sha256', sha256_file(a.out))


if __name__ == '__main__':
    main()
