"""Stage D (compute node, CPU): score the val-fold predictions with tree-F1 and write results/ (SUMMARY.md,
results.json). Also runs on partial results (missing stages are reported as missing).
Usage: report.py <workdir> <results_dir> <n_proc>"""
import os, sys, json, glob, re, time
from multiprocessing import Pool
import numpy as np, nibabel as nib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tf1

W, OUT, NP = sys.argv[1], sys.argv[2], int(sys.argv[3])
os.makedirs(OUT, exist_ok=True)
DS = 'Dataset713_AtlasProxy'; PLANS = 'nnUNetResEncUNetPlans_60G_iso05'
fold_dir = f'{W}/nnunet_results/{DS}/nnUNetTrainerAtlas__{PLANS}__3d_fullres/fold_0'
res = dict(generated=time.strftime('%Y-%m-%d %H:%M:%S'), workdir=W)
for k in ('layout.json',):
    if os.path.exists(f'{W}/{k}'):
        L = json.load(open(f'{W}/{k}')); res['layout'] = L['layout']; res['cases_found'] = len(L['cases'])
for k in ('planner_output.json', 'proxy_summary.json', 'schedule.json'):
    if os.path.exists(f'{W}/{k}'):
        res[k[:-5]] = json.load(open(f'{W}/{k}'))
if os.path.exists(f'{W}/proxy_stats.json'):
    S = json.load(open(f'{W}/proxy_stats.json'))
    res['proxy'] = dict(n=len(S), near_frac_median=float(np.median([s['near_frac'] for s in S.values() if 'near_frac' in s])),
                        unreached_frac_median=float(np.median([s['unreached_frac'] for s in S.values() if 'unreached_frac' in s])))
bench = {}
for f in sorted(glob.glob(f'{W}/bench_*.json')):
    b = json.load(open(f)); ep = b['epochs'][1:] or b['epochs']  # drop warm-up epoch
    bench[os.path.basename(f)[6:-5]] = dict(
        n_proc_DA=b['n_proc_DA'], gpu=b['gpu'], torch=b['torch'], patch=b['patch'], batch=b['batch_size'],
        epochs_measured=len(ep), s_per_epoch=float(np.median([e['epoch_s'] for e in ep])),
        loader_wait_frac=float(np.median([e['loader_wait_s'] / e['train_s'] for e in ep])),
        gpu_step_s_median=float(np.median([e['median_step'] for e in ep])),
        peak_alloc_gib=max(e['peak_alloc_gib'] for e in b['epochs']), peak_reserved_gib=max(e['peak_reserved_gib'] for e in b['epochs']))
res['r0_benchmark'] = bench
if bench:
    best = min(bench.values(), key=lambda b: b['s_per_epoch'])
    res['r0_forecast_1000_epochs_h'] = best['s_per_epoch'] * 1000 / 3600
    res['r0_acceptance'] = dict(s_per_epoch_le_306=best['s_per_epoch'] <= 306, peak_reserved_le_75GB=best['peak_reserved_gib'] * 1.0737 <= 75)
logs = sorted(glob.glob(f'{fold_dir}/training_log_*.txt'))
if logs:
    txt = ''.join(open(f).read() for f in logs)
    et = [float(x) for x in re.findall(r'Epoch time: ([0-9.]+) s', txt)]
    pd = re.findall(r'Pseudo dice \[([^\]]*)\]', txt)
    res['training'] = dict(epochs_completed=len(et), s_per_epoch_median=float(np.median(et)) if et else None,
                           last_pseudo_dice=[float(x.replace('np.float32(', '').replace(')', '')) for x in pd[-1].split(',')] if pd else None,
                           stopped_early='ATLAS: stopping' in txt)
pred_dir = f'{fold_dir}/validation'
refs = f'{W}/nnunet_raw/{DS}/labelsTr'

def score_one(f):
    c = os.path.basename(f)[:-7]
    p = nib.load(f); r = nib.load(f'{refs}/{c}.nii.gz')
    sp = np.array(r.header.get_zooms()[:3], float)
    P = np.asarray(p.dataobj).astype(np.uint8); R = np.asarray(r.dataobj).astype(np.uint8)
    s = tf1.score(R, P, sp, tol=1.5); s0 = tf1.score(R, P, sp, tol=0.0)
    s['case'] = c; s['tf1_tol0'] = s0['tf1']
    return s
preds = sorted(glob.glob(f'{pred_dir}/c*.nii.gz'))
if preds:
    with Pool(NP) as pool:
        per = pool.map(score_one, preds)
    json.dump(per, open(f'{OUT}/per_case_val.json', 'w'), indent=1)
    names = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
    def m(key): return float(np.mean([p[key] for p in per]))
    def cls(key): return {names[c]: float(np.mean([p[key][c] for p in per if c in p[key]])) for c in names}
    # a cut tree: some class whose centreline is found (clDice) but not reachable from the ostium (tF1)
    cut = [p['case'] for p in per if any(p['cldice_per_class'][c] - p['tf1_per_class'][c] > 0.10 for c in p['tf1_per_class'])]
    res['val'] = dict(n=len(per), tf1_at_1p5=m('tf1'), tf1_at_0=m('tf1_tol0'), tf1_per_class=cls('tf1_per_class'),
                      class_cldice=m('class_cldice'), macro_dice=m('macro_dice'), dice_per_class=cls('dice_per_class'),
                      fp_components_mean=float(np.mean([p['fp_components'] for p in per if p['fp_components'] >= 0] or [float('nan')])),
                      degenerate_predictions=sum(bool(p.get('degenerate_prediction')) for p in per), swap_rate=m('swap_rate'),
                      cases_with_cut_tree=len(cut), cut_cases=cut,
                      tf1_min=float(min(p['tf1'] for p in per)))
# ---- A13: manifest for inference-only reuse by other experiments (weights and softmax stay on $SCRATCH)
pp_ds = f'{W}/nnunet_preprocessed/{DS}'
ck = f'{fold_dir}/checkpoint_final.pth'
manifest = dict(
    what='Atlas master-recipe model (ResEnc, 0.5 mm iso, 256^3, mirroring off, fixed window), fold 0 of the projected proxy',
    nnunetv2_version='2.8.1', dataset_id=713, dataset_name=DS, trainer='nnUNetTrainerAtlas', plans=PLANS,
    configuration='3d_fullres', fold=0,
    env=dict(nnUNet_raw=f'{W}/nnunet_raw', nnUNet_preprocessed=f'{W}/nnunet_preprocessed', nnUNet_results=f'{W}/nnunet_results'),
    checkpoint_final=ck if os.path.exists(ck) else None, model_dir=fold_dir,
    plans_json=f'{pp_ds}/{PLANS}.json', dataset_json=f'{pp_ds}/dataset.json', splits_json=f'{pp_ds}/splits_final.json',
    trainer_source=f'{W}/export/atlas_trainers.py',
    val_cases=sorted(os.path.basename(f)[:-7] for f in preds),
    val_segmentations_dir=pred_dir, val_softmax_dir=pred_dir,
    val_softmax_files=len(glob.glob(f'{pred_dir}/c*.npz')),
    val_softmax_format=("nnU-Net export: <case>.npz key 'probabilities', float32, shape (5, z, y, x) in SimpleITK axis order "
                        "on the case's native grid (channels: bg, LM, LAD, LCx, RCA); <case>.pkl holds the properties"),
    reference_labels_dir=f'{W}/nnunet_raw/{DS}/labelsTr', images_dir=f'{W}/nnunet_raw/{DS}/imagesTr',
    sealed_cases_touched=False,
    inference_only_recipe=('copy trainer_source into <venv>/lib/python3.11/site-packages/nnunetv2/training/nnUNetTrainer/variants/atlas/ '
                           '(with an empty __init__.py), export env, then: nnUNetv2_predict -i <dir of <case>_0000.nii.gz> -o <out> '
                           f'-d 713 -tr nnUNetTrainerAtlas -p {PLANS} -c 3d_fullres -f 0 -chk checkpoint_final.pth -step_size 0.5 '
                           '--save_probabilities'))
json.dump(manifest, open(f'{OUT}/manifest.json', 'w'), indent=1)
res['manifest'] = 'manifest.json'
json.dump(res, open(f'{OUT}/results.json', 'w'), indent=1)

def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d: return 'n/a'
        d = d[k]
    return f'{d:.3f}' if isinstance(d, float) else str(d)
lines = ['# Atlas Trillium experiment: R0 benchmark + short R1 on the projected proxy', '',
         f'Generated {res["generated"]}. Machine-readable: `results.json`; per val case: `per_case_val.json`.', '',
         '## R0 (amendment A6)', '', '| n_proc_DA | s/epoch | loader-wait share of train time | GPU step (median s) | peak reserved GiB |', '|---|---|---|---|---|']
for k, b in bench.items():
    lines.append(f"| {b['n_proc_DA']} | {b['s_per_epoch']:.1f} | {b['loader_wait_frac']:.2f} | {b['gpu_step_s_median']:.2f} | {b['peak_reserved_gib']:.1f} |")
lines += ['', f"1000-epoch forecast from the fastest setting: **{g(res, 'r0_forecast_1000_epochs_h')} h** "
          f"(plan's forecast 27–85 h, central 45). Acceptance (≤ 306 s/epoch, ≤ 75 GB): {g(res, 'r0_acceptance')}.",
          '', '## Short R1 (ImageCAS-X train 560 → val 80, projected proxy, territory, ramus → LCx)', '',
          f"Planner on the real data: {g(res, 'planner_output')}. Schedule: {g(res, 'schedule')}.",
          f"Epochs completed: {g(res, 'training', 'epochs_completed')} (median {g(res, 'training', 's_per_epoch_median')} s/epoch; stopped at deadline: {g(res, 'training', 'stopped_early')}).", '',
          '| val metric (80 cases, reference = projected proxy) | value |', '|---|---|',
          f"| **macro tF1 @ 1.5 mm** (provisional, A9: `thick` ostium) | **{g(res, 'val', 'tf1_at_1p5')}** |",
          f"| tF1 @ 0 mm | {g(res, 'val', 'tf1_at_0')} |", f"| tF1 per class | {g(res, 'val', 'tf1_per_class')} |",
          f"| per-class clDice | {g(res, 'val', 'class_cldice')} |", f"| macro Dice | {g(res, 'val', 'macro_dice')} |",
          f"| FP components per case (raw, gate ≤ 1) | {g(res, 'val', 'fp_components_mean')} |",
          f"| branch-swap rate (gate < 5 %) | {g(res, 'val', 'swap_rate')} |",
          f"| cases with a cut tree (some class: clDice − tF1 > 0.10) | {g(res, 'val', 'cases_with_cut_tree')} |", '',
          '## Reuse by other experiments (A13)', '', f"Checkpoint: `{manifest['checkpoint_final']}`  ", f"Plans: `{manifest['plans_json']}`  ", f"Val softmax ({manifest['val_softmax_files']} npz) and segmentations: `{manifest['val_softmax_dir']}`  ", 'Full paths, env and the inference-only command: `manifest.json`. Weights and softmax stay on $SCRATCH.', '', 'Reading: see `vault/Plans/Experiments/Atlas - Pending Trillium run, R0 benchmark and a short R1 scored by tree-F1.md`.']
open(f'{OUT}/SUMMARY.md', 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
