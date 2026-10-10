"""Phase B setup (compute node, CPU): the A2 window ablation dataset. Identical to run 1 (same raw images and proxy
labels, same plans: ResEnc, 0.5 mm iso, 256^3, batch 2; same split) except the CT window, which is nnU-Net's
default: the fingerprint's own foreground percentiles / mean / sd (run 1 overwrote them with the fixed
[-300, 1300] HU, mean 100, sd 400). Then nnU-Net preprocessing. Idempotent (marker files).
Usage: prepare_b.py <workdir> <run1 manifest.json> <n_proc>"""
import json
import os
import shutil
import subprocess
import sys
import time

W, man_path, NP = sys.argv[1], sys.argv[2], int(sys.argv[3])
M = json.load(open(man_path))
DS_A, DS_B, ID_B = M['dataset_name'], 'Dataset714_AtlasProxyDefaultWindow', 714
PLANS = M['plans']
raw_a = os.path.join(M['env']['nnUNet_raw'], DS_A)
pp_a = os.path.join(M['env']['nnUNet_preprocessed'], DS_A)
raw_b, pp_b = f'{W}/nnunet_raw/{DS_B}', f'{W}/nnunet_preprocessed/{DS_B}'
os.environ.update(nnUNet_raw=f'{W}/nnunet_raw', nnUNet_preprocessed=f'{W}/nnunet_preprocessed',
                  nnUNet_results=f'{W}/nnunet_results')

if not os.path.exists(f'{W}/.b_plan_done'):
    os.makedirs(raw_b, exist_ok=True); os.makedirs(pp_b, exist_ok=True)
    for d in ('imagesTr', 'labelsTr'):
        if not os.path.lexists(f'{raw_b}/{d}'):
            os.symlink(f'{raw_a}/{d}', f'{raw_b}/{d}')
    shutil.copy(f'{raw_a}/dataset.json', f'{raw_b}/dataset.json')
    shutil.copy(f'{pp_a}/dataset_fingerprint.json', f'{pp_b}/dataset_fingerprint.json')
    shutil.copy(f'{pp_a}/splits_final.json', f'{pp_b}/splits_final.json')
    fp = json.load(open(f'{pp_a}/dataset_fingerprint.json'))['foreground_intensity_properties_per_channel']
    p = json.load(open(f'{pp_a}/{PLANS}.json'))
    fixed = dict(p['foreground_intensity_properties_per_channel']['0'])
    p['dataset_name'] = DS_B
    p['foreground_intensity_properties_per_channel'] = fp
    json.dump(p, open(f'{pp_b}/{PLANS}.json', 'w'), indent=1)
    c3 = p['configurations']['3d_fullres']
    rec = dict(window_run1=[fixed['percentile_00_5'], fixed['percentile_99_5']], norm_run1=[fixed['mean'], fixed['std']],
               window_b=[fp['0']['percentile_00_5'], fp['0']['percentile_99_5']], norm_b=[fp['0']['mean'], fp['0']['std']],
               patch=c3['patch_size'], batch=c3['batch_size'], spacing=c3['spacing'])
    if rec['window_run1'] != [-300.0, 1300.0]:
        sys.exit(f"[prepare_b] run 1's plans do not carry the fixed window: {rec['window_run1']}")
    json.dump(rec, open(f'{W}/window_b.json', 'w'), indent=1)
    print('[prepare_b] plans for the default window:', rec, flush=True)
    open(f'{W}/.b_plan_done', 'w').write('ok')

if os.environ.get('ATLAS2_STOP_AFTER_PLAN'):   # CPU self-test only
    sys.exit(0)
if not os.path.exists(f'{W}/.b_preprocess_done'):
    t = time.time()
    cmd = ['nnUNetv2_preprocess', '-d', str(ID_B), '-plans_name', PLANS, '-c', '3d_fullres', '-np', str(min(NP, 10))]
    print('[prepare_b] +', ' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True)
    shutil.copy(f'{pp_a}/splits_final.json', f'{pp_b}/splits_final.json')
    open(f'{W}/.b_preprocess_done', 'w').write(str(time.time() - t))
    print(f'[prepare_b] preprocessing done in {time.time() - t:.0f}s', flush=True)
