"""Predict the 36 CLEAN open ImageCAS-X test cases (A14: non-sealed and never in any advocate's development set)
with run 1's checkpoint, saving softmax, for Bridge's out-of-sample test (Round 5 §5). Also writes their projected
proxy labels (the same convention as run 1's references) so the cases can be scored without re-deriving them.
Never touches a sealed case: the list is `open_icx_test` of sealed_test.json, every case is checked against both
sealed lists, and against the ImageCAS-X test split.
Usage: open36.py <workdir> <run1 manifest.json> <layout.json> <icx_dir> <sealed_test.json> [--labels-only]"""
import json
import os
import subprocess
import sys
import time

import numpy as np
import nibabel as nib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proxy  # noqa: E402

W, man_path, layout_json, ICX, sealed_json = sys.argv[1:6]
labels_only = '--labels-only' in sys.argv
M = json.load(open(man_path)); L = json.load(open(layout_json)); S = json.load(open(sealed_json))
sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
open36 = sorted(S['open_icx_test'])
icx_test = {'c%04d' % (int(x) - 1) for x in open(os.path.join(ICX, 'test.txt')).read().split()}
if len(open36) != 36 or set(open36) & sealed or not set(open36) <= icx_test:
    sys.exit('[open36] REFUSING: open list is not 36 non-sealed ImageCAS-X test cases')
missing = [c for c in open36 if c not in L['cases']]
if missing:
    print(f'[open36] WARNING: {len(missing)} open cases not found in cases/: {missing[:5]}', flush=True)
cases = [c for c in open36 if c in L['cases']]
D = f'{W}/open36'
for d in ('images', 'labels', 'pred'):
    os.makedirs(f'{D}/{d}', exist_ok=True)
for c in cases:
    img = f'{D}/images/{c}_0000.nii.gz'
    if not os.path.lexists(img):
        os.symlink(L['cases'][c]['ct'], img)
    dst = f'{D}/labels/{c}.nii.gz'
    if not os.path.exists(dst):
        lab, aff, st = proxy.make_label(L['cases'][c]['mask'], os.path.join(ICX, f'{int(c[1:]) + 1}.coronary.nii.gz'))
        ct = nib.load(L['cases'][c]['ct'])
        if ct.shape[:3] != lab.shape or not np.allclose(ct.affine, aff, atol=1e-2):
            raise ValueError(f'{c}: CT and mask grids differ')
        nib.save(nib.Nifti1Image(lab, ct.affine), dst + '.part.nii.gz'); os.replace(dst + '.part.nii.gz', dst)
print(f'[open36] {len(cases)} images linked and proxy labels written in {D}', flush=True)

cmd = ['nnUNetv2_predict', '-i', f'{D}/images', '-o', f'{D}/pred', '-d', str(M['dataset_id']), '-tr', M['trainer'],
       '-p', M['plans'], '-c', M['configuration'], '-f', str(M['fold']), '-chk', 'checkpoint_final.pth',
       '-step_size', '0.5', '--disable_tta', '--save_probabilities', '--continue_prediction', '-npp', '4', '-nps', '4']
done = len([c for c in cases if os.path.exists(f'{D}/pred/{c}.npz')])
if not labels_only and done < len(cases):
    env = dict(os.environ, **M['env'])
    t = time.time(); print('[open36] +', ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, env=env)
    print(f'[open36] nnUNetv2_predict exit {r.returncode} after {time.time() - t:.0f}s', flush=True)
done = sorted(c for c in cases if os.path.exists(f'{D}/pred/{c}.npz'))
man = dict(what="Run 1's master-recipe model (Atlas, A13) applied to the 36 clean open ImageCAS-X test cases (A14), "
                "for Bridge's out-of-sample gated-renaming test (Round 5 §5). Inference only; nothing was trained on these.",
           cases=cases, predicted=done, sealed_cases_touched=False,
           images_dir=f'{D}/images', predictions_dir=f'{D}/pred',
           softmax_format=M.get('val_softmax_format'), reference_labels_dir=f'{D}/labels',
           reference_convention='projected proxy (ImageCAS mask split by ImageCAS-X names; territory; ramus -> LCx), as run 1',
           aorta_dir=f'{W}/aorta', aorta_format='<case>_aorta.nii.gz, uint8, case grid (TotalSegmentator total fast, roi aorta)',
           model=dict(checkpoint=M['checkpoint_final'], plans_json=M['plans_json'], trainer_source=M['trainer_source'],
                      env=M['env']), command=' '.join(cmd))
json.dump(man, open(f'{D}/manifest_open36.json', 'w'), indent=1)
print(f'[open36] predicted {len(done)}/{len(cases)}; manifest {D}/manifest_open36.json', flush=True)
sys.exit(0 if labels_only or len(done) == len(cases) else 1)   # incomplete: the stage is retried on resubmission
