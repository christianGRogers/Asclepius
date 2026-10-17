"""Stage A (compute node, CPU): build and preprocess the nnU-Net dataset for the icx4 run. Idempotent (markers).
  * labels: ImageCAS-X segmentations as drawn (D8), collapsed to four classes by territory (D25 = D1/D1b):
    LM; LAD + D1 + D2; LCx + OM1 + OM2 + IM + L-PDA + L-PLA; RCA + R-PDA + R-PLA. ImageCAS-X "Other" (D3/D4,
    OM3/OM4) takes the class of the nearest LAD/LCx voxel, as segtrain.reads.icx_to_territory does (copied here:
    the venv has no segtrain). The ImageCAS masks are not used.
  * cases: ImageCAS-X train (560) -> training, ImageCAS-X val (80) -> validation (fold 0). The ImageCAS-X test (160)
    is held out for the score; the 200 cases ImageCAS-X excluded have no labels and are only predicted.
  * plans: ResEncUNetPlanner, -gpu_memory_target 60, 0.5 mm isotropic, patch 256^3 / batch 2, nnU-Net's own CT
    window (Round 8: the default window tied the fixed one).
Usage: prepare.py <workdir> <layout.json> <icx_dir> <n_proc>"""
import os, sys, json, subprocess, time
from multiprocessing import Pool
import numpy as np, nibabel as nib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from territory import to_four  # noqa: E402

W, layout_json, ICX, NP = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
DS_ID, DS = 715, 'Dataset715_ICX4'
PLANS = 'nnUNetResEncUNetPlans_60G_iso05'
LABELS = {'background': 0, 'LM': 1, 'LAD': 2, 'LCx': 3, 'RCA': 4}
raw = f'{W}/nnunet_raw/{DS}'; pp = f'{W}/nnunet_preprocessed'
os.environ.update(nnUNet_raw=f'{W}/nnunet_raw', nnUNet_preprocessed=pp, nnUNet_results=f'{W}/nnunet_results')
L = json.load(open(layout_json)); cases = L['cases']


def ids(name):
    return ['c%04d' % (int(x) - 1) for x in open(os.path.join(ICX, f'{name}.txt')).read().split()]


def icx_path(c):
    return os.path.join(ICX, f'{int(c[1:]) + 1}.coronary.nii.gz')


train = [c for c in ids('train') if c in cases]; val = [c for c in ids('val') if c in cases]
test = [c for c in ids('test') if c in cases]
print(f'[prepare] layout={L["layout"]} cases_found={len(cases)} train={len(train)} val={len(val)} test={len(test)}',
      flush=True)
MIN = int(os.environ.get('ICX4_MIN_CASES', 500))  # lowered only by the CPU self-test
if len(train) < MIN or len(val) < max(1, MIN // 7):
    sys.exit('[prepare] too few ImageCAS-X train/val cases found in cases/; refusing to run')
if set(test) & set(train + val):
    sys.exit('[prepare] ImageCAS-X test cases overlap train/val; refusing to run')


def one(c):
    img = f'{raw}/imagesTr/{c}_0000.nii.gz'; dst = f'{raw}/labelsTr/{c}.nii.gz'
    if not os.path.lexists(img):
        os.symlink(cases[c]['ct'], img)
    if os.path.exists(dst):
        return c, None
    ct, li = nib.load(cases[c]['ct']), nib.load(icx_path(c))
    if ct.shape[:3] != li.shape[:3] or not np.allclose(ct.affine, li.affine, atol=1e-2):
        raise ValueError(f'{c}: CT {ct.shape} and ImageCAS-X label {li.shape} grids differ')
    lab = np.asarray(li.dataobj).astype(np.int64)
    if lab.min() < 0 or lab.max() > 14:
        raise ValueError(f'{c}: ImageCAS-X label values {np.unique(lab).tolist()} outside 0..14')
    lab = to_four(lab, li.header.get_zooms())
    vals = np.unique(lab)
    nib.save(nib.Nifti1Image(lab.astype(np.uint8), ct.affine), dst + '.part.nii.gz')
    os.replace(dst + '.part.nii.gz', dst)
    return c, [int(v) for v in vals if v]


def run(cmd):
    print('[prepare] +', ' '.join(cmd), flush=True); t = time.time()
    subprocess.run(cmd, check=True); print(f'[prepare]   done in {time.time() - t:.0f}s', flush=True)


if not os.path.exists(f'{W}/.labels_done'):
    os.makedirs(f'{raw}/imagesTr', exist_ok=True); os.makedirs(f'{raw}/labelsTr', exist_ok=True)
    t = time.time(); present = {}
    with Pool(NP) as p:
        for c, v in p.imap_unordered(one, train + val):
            if v is not None:
                present[c] = v
    counts = {n: sum(LABELS[n] in v for v in present.values()) for n in LABELS if n != 'background'}
    json.dump({'cases_with_class': counts, 'n': len(present)}, open(f'{W}/label_census.json', 'w'), indent=1)
    json.dump({'channel_names': {'0': 'CT'}, 'labels': LABELS, 'numTraining': len(train) + len(val),
               'file_ending': '.nii.gz'}, open(f'{raw}/dataset.json', 'w'), indent=1)
    json.dump({'train': sorted(train), 'val': sorted(val), 'test': sorted(test)}, open(f'{W}/splits.json', 'w'))
    open(f'{W}/.labels_done', 'w').write(str(time.time() - t))
    print(f'[prepare] labels for {len(train) + len(val)} cases in {time.time() - t:.0f}s; cases per class {counts}',
          flush=True)

if not os.path.exists(f'{W}/.plan_done'):
    run(['nnUNetv2_extract_fingerprint', '-d', str(DS_ID), '-np', str(NP)])
    run(['nnUNetv2_plan_experiment', '-d', str(DS_ID), '-pl', 'ResEncUNetPlanner', '-gpu_memory_target', '60',
         '-overwrite_target_spacing', '0.5', '0.5', '0.5', '-overwrite_plans_name', PLANS])
    pf = f'{pp}/{DS}/{PLANS}.json'; p = json.load(open(pf))
    c3 = p['configurations']['3d_fullres']
    json.dump(dict(patch=c3['patch_size'], batch=c3['batch_size'], spacing=c3['spacing'],
                   window=[p['foreground_intensity_properties_per_channel']['0'][k]
                           for k in ('percentile_00_5', 'percentile_99_5')]),
              open(f'{W}/planner_output.json', 'w'))
    c3['patch_size'] = [256, 256, 256]; c3['batch_size'] = 2
    if os.environ.get('ICX4_TEST_PATCH'):  # CPU self-test only; never set on Trillium
        c3['patch_size'] = [int(os.environ['ICX4_TEST_PATCH'])] * 3; c3['batch_size'] = 1
    json.dump(p, open(pf, 'w'), indent=1)
    open(f'{W}/.plan_done', 'w').write('ok')
    print('[prepare] plans written:', open(f'{W}/planner_output.json').read(), flush=True)

if os.environ.get('ICX4_STOP_AFTER_PLAN'):
    sys.exit(0)
if not os.path.exists(f'{W}/.preprocess_done'):
    # ~10 GB RAM per worker at 0.5 mm (Atlas R0 note); a 1-GPU job has ~188 GiB
    run(['nnUNetv2_preprocess', '-d', str(DS_ID), '-plans_name', PLANS, '-c', '3d_fullres', '-np', str(min(NP, 10))])
    json.dump([{'train': sorted(train), 'val': sorted(val)}], open(f'{pp}/{DS}/splits_final.json', 'w'))
    open(f'{W}/.preprocess_done', 'w').write('ok')

# inputs for the final prediction: every case in cases/ (all 1000), as nnU-Net input names
inp = f'{W}/predict_in'
if not os.path.exists(f'{W}/.predict_in_done'):
    os.makedirs(inp, exist_ok=True)
    for c, f in cases.items():
        d = f'{inp}/{c}_0000.nii.gz'
        if not os.path.lexists(d):
            os.symlink(f['ct'], d)
    open(f'{W}/.predict_in_done', 'w').write(str(len(cases)))
print('[prepare] complete', flush=True)
