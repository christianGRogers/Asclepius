"""Build a tiny real nnU-Net dataset (6 CT-cached cases, ImageCAS-X labels read out to 4 classes, territory)
and preprocess it exactly as the master plan specifies: ResEnc planner at 60 GB, 0.5 mm iso, fixed CT window
[-300, 1300] HU. Output feeds loader_benchmark.py. Usage: r0cpu_setup.py <workdir>"""
import os, sys, json, subprocess
import numpy as np, nibabel as nib
W = sys.argv[1]
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
os.environ.update(nnUNet_raw=W + '/raw', nnUNet_preprocessed=W + '/pp', nnUNet_results=W + '/res')
name = 'Dataset712_CCTAr0'; raw = f'{W}/raw/{name}'
os.makedirs(raw + '/imagesTr', exist_ok=True); os.makedirs(raw + '/labelsTr', exist_ok=True)
TER = np.zeros(256, np.uint8)
for k, v in {1: 1, 2: 2, 4: 2, 5: 2, 3: 3, 6: 3, 7: 3, 12: 3, 13: 3, 8: 2, 14: 2, 9: 4, 10: 4, 11: 4}.items(): TER[k] = v
cases = ['c0000', 'c0050', 'c0125', 'c0175', 'c0200', 'c0300']
for c in cases:
    dst = f'{raw}/imagesTr/{c}_0000.nii.gz'
    if not os.path.exists(dst): os.symlink(f'{SCR}/data/ct/{c}.nii.gz', dst)
    li = nib.load(f'{SCR}/work/Atlas/icx/{int(c[1:]) + 1}.coronary.nii.gz')
    lab = TER[np.asarray(li.dataobj).astype(np.uint8)]
    nib.save(nib.Nifti1Image(lab, nib.load(dst).affine), f'{raw}/labelsTr/{c}.nii.gz')
json.dump({'channel_names': {'0': 'CT'}, 'labels': {'background': 0, 'left_main': 1, 'left_anterior_descending': 2,
           'left_circumflex': 3, 'right_coronary_artery': 4}, 'numTraining': len(cases), 'file_ending': '.nii.gz'},
          open(raw + '/dataset.json', 'w'))
def run(cmd): print('+', ' '.join(cmd), flush=True); subprocess.run(cmd, check=True)
run(['nnUNetv2_extract_fingerprint', '-d', '712', '-np', '2'])
run(['nnUNetv2_plan_experiment', '-d', '712', '-pl', 'ResEncUNetPlanner', '-gpu_memory_target', '60',
     '-overwrite_target_spacing', '0.5', '0.5', '0.5', '-overwrite_plans_name', 'nnUNetResEncUNetPlans_60G_iso05'])
pf = f'{W}/pp/{name}/nnUNetResEncUNetPlans_60G_iso05.json'
p = json.load(open(pf))
p['foreground_intensity_properties_per_channel']['0'].update(percentile_00_5=-300.0, percentile_99_5=1300.0, mean=100.0, std=400.0)
c3 = p['configurations']['3d_fullres']
print('planned patch', c3['patch_size'], 'batch', c3['batch_size'], 'spacing', c3['spacing'])
c3['patch_size'] = [256, 256, 256]; c3['batch_size'] = 2  # the master's cohort-wide plan (6-case median shape differs slightly)
json.dump(p, open(pf, 'w'), indent=1)
run(['nnUNetv2_preprocess', '-d', '712', '-plans_name', 'nnUNetResEncUNetPlans_60G_iso05', '-c', '3d_fullres', '-np', '2'])
print('done')
