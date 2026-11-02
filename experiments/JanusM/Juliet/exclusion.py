"""Janus-M exclusion guard (Juliet v1).

Every pool patient Janus-M must never read, score or train on:
  - the D27/D32/D33 pool seal (150 primary patients) and its extension order / reserve (A34);
  - the ImageCHD report-only seal (20);
  - every Round 10 D35 candidate draw (Delta, Atlas, Bridge, Crucible, Foxtrot), not only the adopted one,
    so the guard stays safe whichever draw the lead adopts (Q1).
Patients merged by D33 are both listed. A volume is excluded if it belongs to an excluded patient key.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SEAL = 'configs/segqueue14/sealed-pool-2026-10.json'
POOL = 'configs/segqueue14/pool-2026-10.txt'


def _load(p):
    return json.loads((ROOT / p).read_text())


def forbidden_patients(mode='strict'):
    """strict: today's rule (seal + reserve + every D35 candidate draw).
    after_q1: the lead adopts Delta's draw (Round 10 Q1 recommendation); reserve still held (A34).
    after_a35: as after_q1, and A35 keeps the seal at 150 and releases the reserve."""
    s = _load(SEAL)
    f = set(s['primary']['patients']) | set(s['report_only']['patients'])
    if mode != 'after_a35':
        f |= set(s['primary']['extension_order'])
    for a, b in s['d32']['merged_aliases'].items():
        if a in f or b in f:
            f |= {a, b}
    f |= set(_load('experiments/Delta/r10/d35_decision_set_proposal.json')['patients'])
    if mode != 'strict':
        return f
    f |= set(_load('experiments/Atlas/r10/decision_set_proposal.json')['decision_set']['patients'])
    f |= set(_load('experiments/Bridge/r10/decision_set_proposal.json')['patients'])
    f |= set(_load('experiments/Crucible/r10/d35_proposal.json')['patients'])
    fox = _load('experiments/Foxtrot/r10/d35_proposal.json')
    for k in ('proposed_d35', 'seal_extension_to_200', 'alternative_not_proposed_open_draw_30'):
        f |= set(fox[k]['patients'])
    return f


def is_forbidden(volume, forbidden):
    for k in forbidden:
        if volume == k + '.nii.gz' or volume.startswith(k + '_') or volume.startswith(k + '.'):
            return True
    return False


def pool_volumes():
    return [l.strip() for l in (ROOT / POOL).read_text().splitlines() if '__' in l and not l.startswith('#')]


def free_volumes(source=None, mode='strict'):
    f = forbidden_patients(mode)
    vols = pool_volumes()
    return [v for v in vols if (source is None or v.startswith(source + '__')) and not is_forbidden(v, f)]


if __name__ == '__main__':
    import collections
    allv = pool_volumes()
    out = {}
    for mode in ('strict', 'after_q1', 'after_a35'):
        free = free_volumes(mode=mode)
        by = collections.Counter(v.split('__')[0] for v in free)
        out[mode] = {'excluded_patient_keys': len(forbidden_patients(mode)), 'pool_volumes': len(allv),
                     'free_volumes': len(free), 'free_by_source': dict(sorted(by.items()))}
        print(mode, out[mode])
    (Path(__file__).parent / 'pool_free.json').write_text(json.dumps(out, indent=1) + '\n')
