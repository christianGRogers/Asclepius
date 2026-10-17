"""Login node: find and check what run 3 reuses, and write the case lists. Fails loudly.

From run 2 ($SCRATCH/atlas2, results/results.json): arm B's fold folder and checkpoint_final.pth (the warm source,
default window), its plans, dataset.json and splits (dataset 714 preprocessed), the TotalSegmentator aortas of the
80 val cases (reused, never recomputed). From run 1 ($SCRATCH/atlas, results/manifest.json): the 80 val reference
labels. ImageCAS-X labels (run 1's). No sealed case is involved (A14).
Usage: check_run2.py <run1 workdir> <run2 workdir> <run3 workdir> <layout.json> <sealed_test.json>"""
import json
import os
import sys

R1, R2, W, layout_json, sealed_json = sys.argv[1:6]
problems = []


def need(path, what):
    if not path or not os.path.exists(path):
        problems.append(f"{what}: {path}")
    return path


res2 = need(f'{R2}/results/results.json', "run 2 results.json")
man1 = need(f'{R1}/results/manifest.json', "run 1 manifest")
if problems:
    sys.exit('[atlas3] run 1 / run 2 outputs not found:\n  ' + '\n  '.join(problems)
             + '\n[atlas3] run 3 reuses run 1 (./atlas) and run 2 (./atlas2) and must run after them.')
R = json.load(open(res2)); M = json.load(open(man1))
S = json.load(open(sealed_json)); L = json.load(open(layout_json))
sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
fold_b = (R.get('b_training') or {}).get('fold_dir')
need(fold_b, "run 2 arm B fold folder")
ckpt = need(os.path.join(fold_b or '', 'checkpoint_final.pth'), "run 2 arm B checkpoint_final.pth")
model_dir = os.path.dirname(fold_b or '')
need(os.path.join(model_dir, 'plans.json'), "run 2 arm B plans.json")
need(os.path.join(model_dir, 'dataset.json'), "run 2 arm B dataset.json")
pp = f'{R2}/nnunet_preprocessed'
ds = os.path.basename(os.path.dirname(model_dir))           # Dataset714_...
need(f'{pp}/{ds}/splits_final.json', "dataset 714 splits_final.json")
need(f'{pp}/{ds}/nnUNetResEncUNetPlans_60G_iso05.json', "dataset 714 plans")
win = json.load(open(f'{R2}/window_b.json')) if os.path.exists(f'{R2}/window_b.json') else None
if win is None:
    problems.append(f"run 2 window_b.json: {R2}/window_b.json")
val = sorted(M['val_cases'])
ref_dir = M['reference_labels_dir']
nref = sum(os.path.exists(f'{ref_dir}/{c}.nii.gz') for c in val)
nao = sum(os.path.exists(f'{R2}/aorta/{c}_aorta.nii.gz') for c in val)
if len(val) != 80 or nref < 80:
    problems.append(f'run 1 val references: {nref}/80 in {ref_dir}')
if nao < 80:
    problems.append(f'run 2 aortas: {nao}/80 in {R2}/aorta (run 3 reuses them; it never recomputes)')
if set(val) & sealed:
    problems.append('sealed case among the val cases')
absent = [c for c in val if c not in L['cases']]
if absent:
    problems.append(f'{len(absent)} val cases not in cases/: {absent[:5]}')
if problems:
    sys.exit('[atlas3] run 3 inputs incomplete:\n  ' + '\n  '.join(problems))
json.dump(val, open(f'{W}/val_cases.json', 'w'))
s_epoch = (R.get('b_training') or {}).get('s_per_epoch_median') or 176.0
json.dump(dict(source_checkpoint=ckpt, fold_b=fold_b, dataset=ds, window=win['window_b'],
               s_per_epoch_b=s_epoch, reference_labels_dir=ref_dir, aorta_dir=f'{R2}/aorta',
               nnUNet_raw=f'{R2}/nnunet_raw', nnUNet_preprocessed=pp),
          open(f'{W}/run2_inputs.json', 'w'), indent=1)
print(f"[atlas3] run 2 OK: B checkpoint {ckpt} (window {win['window_b']}, {s_epoch} s/epoch); "
      f"80 references; 80 aortas reused; no sealed case involved")
print(f"SOURCE={ckpt}")
print(f"DATASET={ds}")
print(f"WINDOW={win['window_b'][0]},{win['window_b'][1]}")
print(f"S_EPOCH={s_epoch}")
print(f"REF={ref_dir}")
