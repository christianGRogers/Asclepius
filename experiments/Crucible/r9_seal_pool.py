"""Round 9 (proposal A14-pool): a sealed acceptance set drawn from the SegQueue14 pool (D23), by patient.
Rule (pre-registered here, before any pool read exists):
  * candidates: the 'QC annotatable' and 'QC limited' sections of configs/segqueue14/pool-2026-10.txt (not the
    'header spacing suspect' tail, which may never be read or may be re-gridded);
  * a patient group = <Source>__<Case> for three-field names (D22: <Source>__<Case>__<Part>); for two-field names the
    case with a phase/timepoint/frame suffix removed (_diast, _syst, _tpN, _fNN, _phN). Every volume of a sealed
    patient is sealed, so no patient is on both sides;
  * within each source, groups are ranked by sha256('asclepius-sealed-round9-pool:' + group) and the first
    round(frac x n_groups) are sealed (frac = target patients / candidate patients), so each source is represented in
    proportion; a source with one group is never sealed (its only patient would leave training entirely);
  * every volume of a sealed patient leaves training; A10 scores ONE volume per sealed patient (the first in serve
    order), so n counts independent patients, not phases of one heart.
Usage: r9_seal_pool.py <pool.txt> <target_patients> <out.json>"""
import hashlib, json, re, sys
from collections import defaultdict

pool, target, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
section, vols = None, []
for line in open(pool):
    s = line.strip()
    if s.startswith('# ---'):
        section = 'suspect' if 'suspect' in s else ('annotatable' if 'annotatable' in s else 'limited')
    elif s and not s.startswith('#'):
        vols.append((s, section))
cand = [v for v, sec in vols if sec in ('annotatable', 'limited')]


def group(name):
    parts = name[:-len('.nii.gz')].split('__')
    if len(parts) >= 3:
        return f'{parts[0]}__{parts[1]}'
    return f'{parts[0]}__' + re.sub(r'_(diast|syst|tp\d+|f\d+|ph\d+)$', '', parts[1])


by_src = defaultdict(lambda: defaultdict(list))
for v in cand:
    by_src[v.split('__')[0]][group(v)].append(v)
n_groups = sum(len(g) for g in by_src.values())
frac = target / n_groups
sealed, scored, per_src = [], [], {}
order = {v: i for i, v in enumerate(cand)}
for src, groups in sorted(by_src.items()):
    ranked = sorted(groups, key=lambda g: hashlib.sha256(('asclepius-sealed-round9-pool:' + g).encode()).hexdigest())
    k = 0 if len(ranked) < 2 else int(round(frac * len(ranked)))
    chosen = ranked[:k]
    sv = [v for g in chosen for v in sorted(groups[g])]
    sealed += sv
    scored += [min(groups[g], key=order.get) for g in chosen]
    per_src[src] = {'groups': len(ranked), 'volumes': sum(map(len, groups.values())),
                    'sealed_groups': k, 'sealed_volumes': len(sv)}
json.dump({'rule': __doc__.split('Usage')[0].strip(), 'target_patients': target, 'candidates': len(cand),
           'candidate_groups': sum(len(g) for g in by_src.values()), 'n_sealed_volumes': len(sealed), 'n_scored': len(scored),
           'per_source': per_src, 'scored_pool': sorted(scored), 'sealed_pool': sorted(sealed)}, open(out, 'w'), indent=1)
print(f'candidates {len(cand)} volumes in {n_groups} patient groups; sealed {len(sealed)} volumes, scored {len(scored)}')
for s, d in per_src.items():
    print(f"  {s:34s} groups {d['groups']:4d} vols {d['volumes']:4d} -> sealed {d['sealed_groups']:3d} groups / {d['sealed_volumes']:3d} vols")
