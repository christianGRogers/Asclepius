"""Login node: find and check run 1's outputs (A13 manifest) and write the case lists run 2 needs. Fails loudly.
Checks: checkpoint, plans, dataset fingerprint, splits, 80 val segmentations + softmax, reference labels; the val
and open-36 cases are present in cases/; none of them is sealed (A14).
Usage: check_run1.py <run1 workdir> <run2 workdir> <layout.json> <sealed_test.json>"""
import json
import os
import sys

R1, W, layout_json, sealed_json = sys.argv[1:5]
man = f'{R1}/results/manifest.json'
if not os.path.exists(man):
    sys.exit(f'[atlas2] run 1 manifest not found: {man}\n[atlas2] run 2 reuses run 1 (./atlas) and must run after it.')
M = json.load(open(man))
S = json.load(open(sealed_json)); L = json.load(open(layout_json))
sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
pp = os.path.dirname(M['plans_json'])
need = {'checkpoint_final': M.get('checkpoint_final'), 'plans_json': M['plans_json'],
        'dataset_fingerprint': f'{pp}/dataset_fingerprint.json', 'splits': M['splits_json'],
        'labelsTr': M['reference_labels_dir'], 'validation': M['val_segmentations_dir'],
        'trainer_source': M['trainer_source'],
        'model_dataset_json': os.path.join(os.path.dirname(M['model_dir']), 'dataset.json'),
        'model_plans_json': os.path.join(os.path.dirname(M['model_dir']), 'plans.json')}
miss = [f'{k}: {v}' for k, v in need.items() if not v or not os.path.exists(v)]
val = sorted(M['val_cases'])
vs = M['val_segmentations_dir']
nseg = sum(os.path.exists(f'{vs}/{c}.nii.gz') for c in val)
nnpz = sum(os.path.exists(f'{vs}/{c}.npz') for c in val)
nref = sum(os.path.exists(f"{M['reference_labels_dir']}/{c}.nii.gz") for c in val)
if len(val) != 80 or nseg < 80 or nnpz < 80 or nref < 80:
    miss.append(f'val: {len(val)} cases, {nseg} segmentations, {nnpz} softmax, {nref} references (need 80 each)')
if set(val) & sealed:
    miss.append(f'sealed case among run 1 val cases: {sorted(set(val) & sealed)[:5]}')
if miss:
    sys.exit('[atlas2] run 1 outputs incomplete:\n  ' + '\n  '.join(miss))
open36 = sorted(S['open_icx_test'])
if len(open36) != 36 or set(open36) & sealed or set(open36) & set(val):
    sys.exit('[atlas2] REFUSING: the open-36 list overlaps the sealed or val cases')
absent = [c for c in val + open36 if c not in L['cases']]
if absent:
    sys.exit(f'[atlas2] {len(absent)} needed cases not in cases/: {absent[:8]}')
json.dump(val, open(f'{W}/val_cases.json', 'w'))
json.dump({c: L['cases'][c]['ct'] for c in val + open36}, open(f'{W}/aorta_cases.json', 'w'), indent=0)
open(f'{W}/cl_cases.txt', 'w').write('\n'.join(val + open36) + '\n')
json.dump(dict(run1=R1, val=len(val), open36=len(open36), layout=json.load(open(layout_json))['layout']),
          open(f'{W}/layout_summary.json', 'w'))
print(f"[atlas2] run 1 OK: checkpoint, plans, fingerprint, 80 val segmentations + softmax + references "
      f"({M['dataset_name']}, {M['plans']}); 36 clean open test cases found; no sealed case involved")
print(f"RUN1_VAL={vs}")
print(f"RUN1_REF={M['reference_labels_dir']}")
print(f"PLANS={M['plans']}")
