"""Stage A (compute node, CPU): build the nnU-Net dataset for the Atlas experiment and preprocess it exactly as the
master plan specifies. Idempotent (marker files).
  * cases: ImageCAS-X train (560) -> training, ImageCAS-X val (80) -> validation (fold 0). The ImageCAS-X test (160)
    and the 200 quality-0 cases are NOT touched (sealed / no proxy).
  * labels: projected proxy in the binding convention (proxy.py: ImageCAS mask split, territory, ramus -> LCx).
  * plans: ResEncUNetPlanner, -gpu_memory_target 60, 0.5 mm isotropic, fixed CT window [-300, 1300] HU,
    patch 256^3 / batch 2 enforced (the cohort-wide plan).
Usage: prepare.py <workdir> <layout.json> <icx_dir> <n_proc>"""
import os, sys, json, subprocess, time
from multiprocessing import Pool
import numpy as np, nibabel as nib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proxy

W, layout_json, ICX, NP = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
DS_ID, DS = 713, 'Dataset713_AtlasProxy'
PLANS = 'nnUNetResEncUNetPlans_60G_iso05'
raw = f'{W}/nnunet_raw/{DS}'; pp = f'{W}/nnunet_preprocessed'
os.environ.update(nnUNet_raw=f'{W}/nnunet_raw', nnUNet_preprocessed=pp, nnUNet_results=f'{W}/nnunet_results')
L = json.load(open(layout_json)); cases = L['cases']

def ids(name):
    return ['c%04d' % (int(x) - 1) for x in open(os.path.join(ICX, f'{name}.txt')).read().split()]
train = [c for c in ids('train') if c in cases]; val = [c for c in ids('val') if c in cases]
print(f'[prepare] layout={L["layout"]} cases_found={len(cases)} train={len(train)} val={len(val)}', flush=True)
MIN = int(os.environ.get('ATLAS_MIN_CASES', 100))  # lowered only by the CPU self-test
if len(train) < MIN or len(val) < max(1, MIN // 5):
    sys.exit('[prepare] too few ImageCAS-X train/val cases found in cases/; refusing to run')

def one(c):
    dst = f'{raw}/labelsTr/{c}.nii.gz'
    img = f'{raw}/imagesTr/{c}_0000.nii.gz'
    if not os.path.lexists(img):
        os.symlink(cases[c]['ct'], img)
    if os.path.exists(dst):
        return c, None
    lab, aff, st = proxy.make_label(cases[c]['mask'], os.path.join(ICX, f'{int(c[1:]) + 1}.coronary.nii.gz'))
    ct = nib.load(cases[c]['ct'])
    if ct.shape[:3] != lab.shape or not np.allclose(ct.affine, aff, atol=1e-2):
        raise ValueError(f'{c}: CT and mask grids differ')
    nib.save(nib.Nifti1Image(lab, ct.affine), dst + '.part.nii.gz'); os.replace(dst + '.part.nii.gz', dst)
    return c, st

def run(cmd):
    print('[prepare] +', ' '.join(cmd), flush=True); t = time.time()
    subprocess.run(cmd, check=True); print(f'[prepare]   done in {time.time() - t:.0f}s', flush=True)

if not os.path.exists(f'{W}/.labels_done'):
    os.makedirs(f'{raw}/imagesTr', exist_ok=True); os.makedirs(f'{raw}/labelsTr', exist_ok=True)
    t = time.time(); stats = {}
    with Pool(NP) as p:
        for c, st in p.imap_unordered(one, train + val):
            if st: stats[c] = st
    json.dump(stats, open(f'{W}/proxy_stats.json', 'w'))
    json.dump({'channel_names': {'0': 'CT'}, 'labels': {'background': 0, 'left_main': 1, 'left_anterior_descending': 2,
               'left_circumflex': 3, 'right_coronary_artery': 4}, 'numTraining': len(train) + len(val),
               'file_ending': '.nii.gz'}, open(f'{raw}/dataset.json', 'w'))
    open(f'{W}/.labels_done', 'w').write(str(time.time() - t))
    print(f'[prepare] proxy labels for {len(train) + len(val)} cases in {time.time() - t:.0f}s', flush=True)

if not os.path.exists(f'{W}/.plan_done'):
    run(['nnUNetv2_extract_fingerprint', '-d', str(DS_ID), '-np', str(NP)])
    run(['nnUNetv2_plan_experiment', '-d', str(DS_ID), '-pl', 'ResEncUNetPlanner', '-gpu_memory_target', '60',
         '-overwrite_target_spacing', '0.5', '0.5', '0.5', '-overwrite_plans_name', PLANS])
    pf = f'{pp}/{DS}/{PLANS}.json'; p = json.load(open(pf))
    c3 = p['configurations']['3d_fullres']
    planned = dict(patch=c3['patch_size'], batch=c3['batch_size'], spacing=c3['spacing'],
                   fingerprint_window=[p['foreground_intensity_properties_per_channel']['0'][k] for k in ('percentile_00_5', 'percentile_99_5')])
    json.dump(planned, open(f'{W}/planner_output.json', 'w'))
    print('[prepare] planner output', planned, flush=True)
    p['foreground_intensity_properties_per_channel']['0'].update(percentile_00_5=-300.0, percentile_99_5=1300.0, mean=100.0, std=400.0)
    c3['patch_size'] = [256, 256, 256]; c3['batch_size'] = 2
    json.dump(p, open(pf, 'w'), indent=1)
    open(f'{W}/.plan_done', 'w').write('ok')

if os.environ.get('ATLAS_STOP_AFTER_PLAN'):
    sys.exit(0)
if not os.path.exists(f'{W}/.preprocess_done'):
    # ~10 GB RAM per worker measured on CPU for one case at 0.5 mm (Atlas R0 note); 188 GiB per 1-GPU job
    run(['nnUNetv2_preprocess', '-d', str(DS_ID), '-plans_name', PLANS, '-c', '3d_fullres', '-np', str(min(NP, 10))])
    json.dump([{'train': sorted(train), 'val': sorted(val)}], open(f'{pp}/{DS}/splits_final.json', 'w'))
    open(f'{W}/.preprocess_done', 'w').write('ok')
print('[prepare] complete', flush=True)
