"""D32/D33: rebuild the pool seal on real patients (A30 grouping QC, #87). Deterministic; no data is read.

Input: the D27 seal (``sealed_pool_proposal.json``, sha256 8f529842...1183) and the pool list. A patient is
``segtrain.pool_seal.ingest_patient``: the ingest code's patient id where it differs from the name rule (the four
single-patient Mendeley-SDN records; Slicer 4D frames), merged by ``PATIENT_ALIASES`` (D33, the RIDER pair).

D32 option A, applied in this order:
1. **Seal every volume of every sealed patient.** A sealed patient is the real patient of any sealed key
   (primary or report-only); D33 merges RIDER-2551730224 (extension entry #79) into sealed RIDER-2522924559.
2. **Top up to exactly 150 real primary patients** from the pre-registered extension order, in its order,
   skipping entries whose real patient is already sealed.
3. **Recompute the extension order on real patients:** the old order mapped to real patients, first occurrence
   kept, sealed patients dropped. The salted ranking is untouched, so this is not a redraw.
The scoring volume of each patient is the lowest-ranked of its volumes, by the same salted sha256 as before.

Usage: python3 reseal_d32.py <D27 seal json> <pool list> > new.json   (prints a before/after table to stderr)
Reproduce: git show 4469ed4:experiments/Bridge/r9/sealed_pool_proposal.json > d27.json, then run on d27.json.
"""
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
from segtrain.pool_seal import PATIENT_ALIASES, _patient_key, ingest_patient  # noqa: E402

N_PRIMARY = 150
old_path, pool_path = sys.argv[1], sys.argv[2]
raw = open(old_path, 'rb').read()
D27_SHA256 = '8f529842934bfb72883a7da593b128ad6c091aecb8228005e9792cd8d92c1183'
if hashlib.sha256(raw).hexdigest() != D27_SHA256:
    sys.exit(f'{old_path} is not the D27 seal (sha256 {D27_SHA256}); this script rebuilds that file only. '
             'Reproduce with: git show 4469ed4:experiments/Bridge/r9/sealed_pool_proposal.json > d27.json')
old = json.loads(raw)
SALT = old['salt']
vols = [ln.strip() for ln in open(pool_path) if ln.strip() and not ln.startswith('#')]
stem = lambda v: v[:-len('.nii.gz')]  # noqa: E731
real = {v: ingest_patient(stem(v)) for v in vols}
members = defaultdict(list)
for v in vols:
    members[real[v]].append(v)
rank = lambda s: hashlib.sha256((SALT + s).encode()).hexdigest()  # noqa: E731
key_vols = defaultdict(list)          # old (name-rule) key -> its volumes
for v in vols:
    key_vols[_patient_key(stem(v))].append(v)


def real_of_key(k):
    return real[key_vols[k][0]]


# 1. sealed real patients
prim_real = []
for k in old['primary']['patients']:
    r = real_of_key(k)
    if r not in prim_real:
        prim_real.append(r)
rep_real = []
for k in old['report_only']['patients']:
    r = real_of_key(k)
    if r not in rep_real:
        rep_real.append(r)
assert not set(prim_real) & set(rep_real)
n_before_topup = len(prim_real)
# D33: the merged RIDER patient is sealed already (2522924559 is a sealed key); check and record
merged = {a: b for a, b in PATIENT_ALIASES.items()}
for a, b in merged.items():
    assert b in prim_real, f'D33 target {b} is not sealed'
# 2. top up from the extension order, 3. new extension order
sealed_all = set(prim_real) | set(rep_real)
added, new_ext = [], []
for k in old['primary']['extension_order']:
    r = real_of_key(k)
    if r in sealed_all or r in added or r in new_ext:
        continue
    if len(prim_real) + len(added) < N_PRIMARY:
        added.append(r)
    else:
        new_ext.append(r)
prim_final = prim_real + added
assert len(prim_final) == N_PRIMARY
prim_vols = sorted(v for p in prim_final for v in members[p])
rep_vols = sorted(v for p in rep_real for v in members[p])
# strata and allocation, on real patients
src_of = {p: vs[0].split('__')[0] for p, vs in members.items()}
REPORT_ONLY = {'ImageCHD', 'ImageALCAPA'}
SPACING = {'ImageALCAPA', 'HOCMvalvesSeg', 'CCA200-HF'}
stratum = {p: 'excluded' if s in SPACING else 'report_only' if s in REPORT_ONLY else 'primary'
           for p, s in src_of.items()}
assert all(stratum[p] == 'primary' for p in prim_final) and all(stratum[p] == 'report_only' for p in rep_real)


def alloc(chosen, name):
    tot = Counter(src_of[p] for p in members if stratum[p] == name)
    got = Counter(src_of[p] for p in chosen)
    return {s: [got.get(s, 0), tot[s]] for s in sorted(tot)}


new = {
    'salt': SALT, 'pool_list': old['pool_list'], 'n_volumes': len(vols), 'n_patients': len(members),
    'patient_rule': ('segtrain.pool_seal.ingest_patient: the ingest code\'s patient id (single-patient '
                     'Mendeley-SDN records; Slicer 4D frames), else the name rule, then PATIENT_ALIASES'),
    'd32': {'decision': 'D32 option A and D33 (vault/Plans/Human decisions.md)',
            'from_sha256': hashlib.sha256(raw).hexdigest(),
            'real_patients_in_old_primary_keys': n_before_topup,
            'added_from_extension_order': added,
            'merged_aliases': merged,
            'dropped_extension_entries': [k for k in old['primary']['extension_order']
                                          if real_of_key(k) in sealed_all]},
    'patients_per_stratum': {k: sum(1 for p in members if stratum[p] == k)
                             for k in ('primary', 'report_only', 'excluded')},
    'primary': {'n_patients': len(prim_final), 'n_volumes': len(prim_vols),
                'allocation_[sealed,total]_by_source': alloc(prim_final, 'primary'),
                'patients': sorted(prim_final), 'volumes': prim_vols,
                'scoring_volume': {p: min(members[p], key=rank) for p in sorted(prim_final)},
                'extension_order': new_ext},
    'report_only': {'n_patients': len(rep_real), 'allocation_[sealed,total]_by_source': alloc(rep_real, 'report_only'),
                    'patients': sorted(rep_real), 'volumes': rep_vols,
                    'scoring_volume': {p: min(members[p], key=rank) for p in sorted(rep_real)}},
    'multi_volume_patients': {p: sorted(v) for p, v in sorted(members.items()) if len(v) > 1},
}
json.dump(new, sys.stdout, indent=1)
# ---- before / after (stderr)
ob = old
leaked = [v for p in prim_real for v in members[p] if v not in set(ob['primary']['volumes'])]
print('\n'.join([
    '| | D27 file (before) | D32/D33 (after) |', '|---|---|---|',
    f"| Patients in the pool | {ob['n_patients']} (name rule) | {len(members)} (ingest + D33) |",
    f"| Primary-stratum patients | {ob['patients_per_stratum']['primary']} | {new['patients_per_stratum']['primary']} |",
    f"| Sealed primary entries | {ob['primary']['n_patients']} keys = {n_before_topup} real patients | {len(prim_final)} real patients |",
    f"| Sealed primary volumes | {ob['primary']['n_volumes']} | {len(prim_vols)} |",
    f"| Report-only (ImageCHD) | {ob['report_only']['n_patients']} patients, {len(ob['report_only']['volumes'])} volumes | "
    f"{len(rep_real)} patients, {len(rep_vols)} volumes |",
    f"| Volumes of sealed patients outside the file | {len(leaked)} | 0 |",
    f"| Extension order | {len(ob['primary']['extension_order'])} entries | {len(new_ext)} real patients |",
    f"| Added from the extension order | — | {len(added)} |",
]), file=sys.stderr)
