"""Delta's Trillium experiment -- the pipeline that runs inside the GPU job (and, in smoke mode,
on a CPU). Steps are idempotent (marker files) so a re-submitted job resumes.

  prepare   : find cases, build thick-convention 4-class proxy labels (ImageCAS mask split by
              ImageCAS-X names, territory rule, ramus -> LCx; Human decisions D0/D1/D1b), write the
              nnU-Net raw dataset (train = ImageCAS-X train+val, test = ImageCAS-X test)
  plan      : fingerprint, ResEnc-L planner at 0.5 mm isotropic, fixed CT window, preprocess, split
  train     : nnUNetTrainerDelta (no mirroring, 250 epochs, deadline-aware)
  evaluate  : every test case predicted at tile step 0.5 (nnU-Net default) and 0.75; gap-centred
              re-inference (P1'), support-gated 3 mm bridging, label repair; scored by tree-F1 @1.5 mm
              on the thick reference, with the bridge audit and the raw FP gate
  summarize : results.json + SUMMARY.md

Usage: python pipeline.py <step|all>     (configuration via environment, see job.sh / delta)
"""
import glob
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

WORK = os.environ['DELTA_WORK']                      # $SCRATCH/delta_exp
CASES = os.environ.get('DELTA_CASES', '')
ICX = os.environ.get('DELTA_ICX', os.path.join(WORK, 'icx'))
SMOKE = os.environ.get('DELTA_SMOKE') == '1'
NPROC = int(os.environ.get('DELTA_NPROC', '16'))
DEVICE = os.environ.get('DELTA_DEVICE', 'cuda')
JOB_END = float(os.environ.get('DELTA_JOB_END', '0')) or (time.time() + 24 * 3600)
EVAL_RESERVE_H = float(os.environ.get('DELTA_EVAL_RESERVE_H', '5.0'))
DID, DNAME = 760, 'Dataset760_DeltaThick'
PLANS = 'DeltaResEncL_iso05'
TR = 'nnUNetTrainerDelta'
RAW = os.environ.setdefault('nnUNet_raw', os.path.join(WORK, 'nnUNet_raw'))
PRE = os.environ.setdefault('nnUNet_preprocessed', os.path.join(WORK, 'nnUNet_preprocessed'))
RES = os.environ.setdefault('nnUNet_results', os.path.join(WORK, 'nnUNet_results'))
OUT = os.path.join(WORK, 'results')
for d in (RAW, PRE, RES, OUT):
    os.makedirs(d, exist_ok=True)

# ImageCAS-X 14 classes -> project 4 classes, territory rule (D1) with ramus -> LCx (D1b).
# 14 = "Other" (D3/D4/OM3/OM4) takes its nearest named neighbour.
ICX_TO_4 = {1: 1, 2: 2, 4: 2, 5: 2, 3: 3, 6: 3, 7: 3, 8: 3, 12: 3, 13: 3, 9: 4, 10: 4, 11: 4}


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def marker(name):
    return os.path.join(WORK, f'.done_{name}')


# ------------------------------------------------------------------------------------- cases
from layout import find_cases  # noqa: E402


def icx_lists():
    fl = os.path.join(ICX, 'ImageCAS-X_dataset', 'filelist')
    res = {}
    for k in ('train', 'val', 'test'):
        ids = [int(x) for x in open(os.path.join(fl, f'{k}.txt')).read().split()]
        res[k] = [f'c{n - 1:04d}' for n in ids]
    return res


def icx_seg(case):
    return os.path.join(ICX, 'ImageCAS-X_dataset', 'segmentations', f'{int(case[1:]) + 1}.coronary.nii.gz')


def make_proxy(args):
    """Thick reference/target: every voxel of the ImageCAS (Girder) mask takes the 4-class name of
    the nearest ImageCAS-X voxel (territory mapping). Returns (case, status)."""
    case, ct, mask, dst = args
    import nibabel as nib
    from scipy import ndimage as ndi
    if os.path.exists(dst):
        return case, 'exists'
    try:
        mi = nib.load(mask); xi = nib.load(icx_seg(case))
        m = np.asanyarray(mi.dataobj) > 0.5
        raw = np.asanyarray(xi.dataobj).astype(np.uint8)
        if m.shape != raw.shape or not np.allclose(mi.affine, xi.affine, atol=1e-2):
            return case, 'grid-mismatch'
        sp = np.array(mi.header.get_zooms()[:3], float)
        u = m | (raw > 0)
        idx = [np.nonzero(u.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
        sl = tuple(slice(max(a[0] - 4, 0), a[-1] + 5) for a in idx)
        r = raw[sl]; mm = m[sl]
        lut = np.zeros(256, np.uint8)
        for k, v in ICX_TO_4.items():
            lut[k] = v
        lab4 = lut[r]
        if (r == 14).any():
            _, ind = ndi.distance_transform_edt(lab4 == 0, sampling=sp, return_indices=True)
            fill = lab4[tuple(ind)]
            lab4[r == 14] = fill[r == 14]
        if not (lab4 > 0).any():
            return case, 'empty-icx'
        _, ind = ndi.distance_transform_edt(lab4 == 0, sampling=sp, return_indices=True)
        proxy = np.zeros(m.shape, np.uint8)
        proxy[sl][mm] = lab4[tuple(ind)][mm]
        nib.save(nib.Nifti1Image(proxy, mi.affine), dst)
        return case, 'ok'
    except Exception as e:  # noqa
        return case, f'error {e!r}'


def step_prepare():
    layout, cases = find_cases(CASES)
    if not cases:
        raise SystemExit(f'no cases found under {CASES}')
    log(f'layout {layout}: {len(cases)} cases')
    lists = icx_lists()
    if SMOKE:
        avail = [c for c in lists['train'] + lists['val'] if c in cases]
        lists = dict(train=avail[:3], val=avail[3:4], test=[c for c in lists['test'] if c in cases][:1])
    base = os.path.join(RAW, DNAME)
    for d in ('imagesTr', 'labelsTr', 'imagesTs', 'labelsTs'):
        os.makedirs(os.path.join(base, d), exist_ok=True)
    jobs = []
    for split in ('train', 'val', 'test'):
        tr = split != 'test'
        for c in lists[split]:
            if c not in cases:
                continue
            ct, mask = cases[c]
            img = os.path.join(base, 'imagesTr' if tr else 'imagesTs', f'{c}_0000.nii.gz')
            if not os.path.lexists(img):
                os.symlink(os.path.abspath(ct), img)
            jobs.append((c, ct, mask, os.path.join(base, 'labelsTr' if tr else 'labelsTs', f'{c}.nii.gz')))
    status = {}
    with ProcessPoolExecutor(NPROC) as ex:
        for c, s in ex.map(make_proxy, jobs, chunksize=4):
            status[c] = s
    bad = {c: s for c, s in status.items() if s not in ('ok', 'exists')}
    for c in bad:  # drop unusable cases from the dataset
        for p in glob.glob(os.path.join(base, '*', f'{c}*')):
            os.remove(p)
    ntr = len(glob.glob(os.path.join(base, 'labelsTr', '*.nii.gz')))
    json.dump(dict(channel_names={'0': 'CT'},
                   labels=dict(background=0, left_main=1, left_anterior_descending=2, left_circumflex=3,
                               right_coronary_artery=4),
                   numTraining=ntr, file_ending='.nii.gz'), open(os.path.join(base, 'dataset.json'), 'w'), indent=1)
    have = lambda L: [c for c in L if c in status and c not in bad]
    json.dump(dict(layout=layout, n_cases_found=len(cases), train=have(lists['train']), val=have(lists['val']),
                   test=have(lists['test']), bad=bad), open(os.path.join(WORK, 'split.json'), 'w'), indent=1)
    log(f'proxy labels: {sum(s in ("ok", "exists") for s in status.values())} ok, {len(bad)} unusable: {list(bad.items())[:5]}')


def run(cmd):
    log('$', ' '.join(cmd))
    subprocess.run(cmd, check=True)


def step_plan():
    sp = json.load(open(os.path.join(WORK, 'split.json')))
    run(['nnUNetv2_extract_fingerprint', '-d', str(DID), '-np', str(NPROC)])
    run(['nnUNetv2_plan_experiment', '-d', str(DID), '-pl', 'nnUNetPlannerResEncL',
         '-overwrite_target_spacing', '0.5', '0.5', '0.5', '-overwrite_plans_name', PLANS])
    pf = os.path.join(PRE, DNAME, f'{PLANS}.json')
    plans = json.load(open(pf))
    # Fixed CT window (master plan, Atlas): clip [-300, 1300] HU, normalise with mean 100 / sd 400.
    plans['foreground_intensity_properties_per_channel'] = {'0': {
        'max': 3000.0, 'min': -1024.0, 'mean': 100.0, 'median': 100.0, 'std': 400.0,
        'percentile_00_5': -300.0, 'percentile_99_5': 1300.0}}
    if SMOKE:
        c = plans['configurations']['3d_fullres']
        c['patch_size'] = [64, 64, 64]; c['batch_size'] = 1
    json.dump(plans, open(pf, 'w'), indent=1)
    run(['nnUNetv2_preprocess', '-d', str(DID), '-plans_name', PLANS, '-c', '3d_fullres', '-np', str(NPROC)])
    json.dump([dict(train=sp['train'], val=sp['val'])], open(os.path.join(PRE, DNAME, 'splits_final.json'), 'w'))
    log('patch', plans['configurations']['3d_fullres']['patch_size'], 'batch',
        plans['configurations']['3d_fullres']['batch_size'], 'spacing', plans['configurations']['3d_fullres']['spacing'])


def model_dir():
    return os.path.join(RES, DNAME, f'{TR}__{PLANS}__3d_fullres')


def step_train():
    fold = os.path.join(model_dir(), 'fold_0')
    if os.path.exists(os.path.join(fold, 'checkpoint_final.pth')):
        log('training already finished'); return
    os.environ['DELTA_TRAIN_DEADLINE'] = str(JOB_END - EVAL_RESERVE_H * 3600)
    cmd = ['nnUNetv2_train', str(DID), '3d_fullres', '0', '-tr', TR, '-p', PLANS, '-device', DEVICE]
    if os.path.exists(os.path.join(fold, 'checkpoint_latest.pth')):
        cmd.append('--c')
    run(cmd)


# ------------------------------------------------------------------------------------- evaluate
def score_case(npz_path):
    try:
        return _score_case(npz_path)
    except Exception as e:  # noqa -- one bad case must not stop the evaluation
        z = np.load(npz_path)
        return dict(case=str(z['case']), base=str(z['base']), error=repr(e))


def _score_case(npz_path):
    """CPU worker: all post-processing variants + metrics for one case and one base tile step."""
    import deltalib as D
    from scipy import ndimage as ndi
    z = np.load(npz_path)
    sp = z['sp']; ref = D.RefTree(z['ref'], sp, ct=z['ct'])
    d_pool = ndi.distance_transform_edt(~z['pool'], sampling=sp) if z['pool'].any() else None
    out = dict(case=str(z['case']), base=str(z['base']), n_sites=int(z['n_sites']), ostium_flags=ref.flags,
               ref_trees=len(ref.roots), pool_found=d_pool is not None)
    nfg = int((z['lab_raw'] > 0).sum())
    if nfg > 4 * max(int(ref.m.sum()), 1):
        # degenerate prediction (e.g. an untrained model): skeletonising it would take tens of GB
        out['degenerate'] = True
        out['raw'] = dict(dice=D.macro_dice(ref, z['lab_raw']), fp_after=D.fp_components(ref, z['lab_raw'] > 0),
                          tf1_15=0.0, tf1_0=0.0, rooted_15=0.0, per_class_15={})
        out['fp_gate_raw'] = out['raw']['fp_after']
        os.remove(npz_path)
        return out
    variants = {}
    for src in ('raw', 'regap'):
        lab = z[f'lab_{src}'].astype(np.uint8)
        variants[src] = (lab, None)
        # anchors: components touching the blood pool, or the 2 largest if no pool was found
        anc = D.anchor_components(lab > 0, d_pool)
        for name, elig in (('bridge3', None), ('bridge3sup', z['second'] if src == 'regap' else None)):
            if name == 'bridge3sup' and src == 'raw':
                continue
            lb, br = D.bridge(lab, anc, sp, max_gap_mm=3.0, min_vox=100, eligible=elig)
            variants[f'{src}+{name}'] = (lb, D.audit(br, lab > 0, ref))
        rep = D.relabel(lab > 0, lab, sp)
        variants[f'{src}+repair'] = (rep, None)
        if f'{src}+bridge3sup' in variants:
            lb = variants[f'{src}+bridge3sup'][0]
            variants[f'{src}+bridge3sup+repair'] = (D.relabel(lb > 0, lb, sp), variants[f'{src}+bridge3sup'][1])
    out['fp_gate_raw'] = D.fp_components(ref, z['lab_raw'] > 0)
    for k, (lab, aud) in variants.items():
        sk = D.skeletonise(lab > 0) if (lab > 0).any() else None
        t15 = D.tree_f1(ref, lab, 1.5, sk=sk); t0 = D.tree_f1(ref, lab, 0.0, sk=sk)
        r = dict(tf1_15=t15['tf1'], tf1_0=t0['tf1'], rooted_15=t15['rooted'], per_class_15=t15['per_class'],
                 dice=D.macro_dice(ref, lab), fp_after=D.fp_components(ref, lab > 0))
        if ref.roots_pool:
            r['tf1_15_poolroots'] = D.tree_f1(ref, lab, 1.5, roots=ref.roots_pool, sk=sk)['tf1']
        if aud is not None:
            r['bridges'] = aud
        out[k] = r
    os.remove(npz_path)
    return out


def step_evaluate():
    import nibabel as nib
    import torch
    from scipy import ndimage as ndi
    import deltalib as D
    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
    sp_ = json.load(open(os.path.join(WORK, 'split.json')))
    test = sp_['test']
    resf = os.path.join(OUT, 'per_case.jsonl')
    done = set()
    if os.path.exists(resf):
        done = {(r['case'], r['base']) for r in map(json.loads, open(resf))}
    fold = os.path.join(model_dir(), 'fold_0')
    chk = next(c for c in ('checkpoint_final.pth', 'checkpoint_latest.pth', 'checkpoint_best.pth')
               if os.path.exists(os.path.join(fold, c)))
    log('evaluating with', chk)
    pred = nnUNetPredictor(tile_step_size=0.5, use_gaussian=True, use_mirroring=False,
                           perform_everything_on_device=(DEVICE == 'cuda'), device=torch.device(DEVICE),
                           verbose=False, verbose_preprocessing=False, allow_tqdm=False)
    pred.initialize_from_trained_model_folder(model_dir(), use_folds=(0,), checkpoint_name=chk)
    patch_vox = np.array(pred.configuration_manager.patch_size)[::-1]  # (z,y,x) -> (x,y,z) at 0.5 mm
    tmp = os.path.join(WORK, 'eval_tmp'); os.makedirs(tmp, exist_ok=True)
    base_dir = os.path.join(RAW, DNAME)
    ex = ProcessPoolExecutor(NPROC)
    futs = []
    t_start = time.time()
    for i, case in enumerate(test):
        if all((case, b) in done for b in ('s05', 's075')):
            continue
        if time.time() > JOB_END - 1800:
            log('eval: out of time, stopping submission'); break
        img = nib.load(os.path.join(base_dir, 'imagesTs', f'{case}_0000.nii.gz'))
        sp = np.array(img.header.get_zooms()[:3], float)
        ct = np.asanyarray(img.dataobj).astype(np.float32)
        ref = np.asanyarray(nib.load(os.path.join(base_dir, 'labelsTs', f'{case}.nii.gz')).dataobj).astype(np.uint8)
        props = {'spacing': [float(sp[2]), float(sp[1]), float(sp[0])]}

        def predict(arr, step):
            pred.tile_step_size = step
            _, prob = pred.predict_single_npy_array(arr.transpose(2, 1, 0)[None], props, None, None, True)
            return prob.transpose(0, 3, 2, 1)  # (C, x, y, z)

        win = np.ceil(patch_vox * 0.5 / sp).astype(int)  # gap window in native voxels
        for base, step in (('s05', 0.5), ('s075', 0.75)):
            if (case, base) in done:
                continue
            prob = predict(ct, step)
            lab = prob.argmax(0).astype(np.uint8)
            fg = D.remove_small(lab > 0); lab[~fg] = 0
            # crop for the CPU side: union of reference and prediction, + 10 mm
            u = (ref > 0) | fg
            idx = [np.nonzero(u.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
            mv = np.ceil(10.0 / sp).astype(int)
            lo = np.maximum([a[0] for a in idx] - mv, 0); hi = np.minimum([a[-1] + 1 for a in idx] + mv, ref.shape)
            sl = tuple(slice(lo[k], hi[k]) for k in range(3))
            pool = D.blood_pool(ct[sl], sp, exclude=(ref[sl] > 0) | fg[sl])
            d_pool = ndi.distance_transform_edt(~pool, sampling=sp) if pool.any() else None
            sites = []
            prob_r = prob.copy(); second = np.zeros(ref.shape, bool)
            # anchors: components touching the blood pool, or the 2 largest if no pool was found
            anc = D.anchor_components(fg[sl], d_pool)
            sites = D.gap_sites(fg[sl], anc, sp)
            for s in sites:   # gap-centred re-inference (P1'), max fusion on vessel probability
                c = np.array(s['mid']) + lo
                a = np.clip(c - win // 2, 0, np.maximum(np.array(ref.shape) - win, 0))
                b = np.minimum(a + win, ref.shape)
                wsl = tuple(slice(a[k], b[k]) for k in range(3))
                pw = predict(ct[wsl], 0.5)
                take = (1 - pw[0]) > (1 - prob_r[(slice(None),) + wsl][0])
                sub = prob_r[(slice(None),) + wsl]
                sub[:, take] = pw[:, take]
                second[wsl] |= (1 - pw[0]) >= 0.5
            lab_r = prob_r.argmax(0).astype(np.uint8)
            fg_r = D.remove_small(lab_r > 0); lab_r[~fg_r] = 0
            if SMOKE and base == 's075':
                # smoke only: replace the (untrained) prediction by the reference with two 2 mm cuts,
                # so the full scoring path (bridging, re-inference fields, repair, tF1) is exercised
                lab = ref.copy(); pts = np.argwhere(ref > 0)
                for q in pts[np.random.default_rng(0).choice(len(pts), 2, replace=False)]:
                    b = D.ball(2.0, sp); r_ = np.array(b.shape) // 2
                    a0 = np.maximum(q - r_, 0); a1 = np.minimum(q + r_ + 1, ref.shape)
                    lab[a0[0]:a1[0], a0[1]:a1[1], a0[2]:a1[2]] = 0
                lab_r = lab.copy(); second = lab > 0
            npz = os.path.join(tmp, f'{case}_{base}.npz')
            np.savez_compressed(npz, case=case, base=base, sp=sp, ref=ref[sl], ct=ct[sl].astype(np.int16),
                                pool=pool, lab_raw=lab[sl], lab_regap=lab_r[sl], second=second[sl],
                                n_sites=len(sites))
            futs.append(ex.submit(score_case, npz))
            del prob, prob_r
        log(f'eval GPU {i + 1}/{len(test)} {case}  ({(time.time() - t_start) / 60:.0f} min)')
        # drain finished futures
        for f in [f for f in futs if f.done()]:
            futs.remove(f)
            with open(resf, 'a') as fh:
                fh.write(json.dumps(f.result()) + '\n')
    for f in as_completed(futs):
        with open(resf, 'a') as fh:
            fh.write(json.dumps(f.result()) + '\n')
    ex.shutdown()


# ------------------------------------------------------------------------------------- summary
def boot_ci(d, n=10000, seed=0):
    d = np.asarray(d, float)
    if len(d) < 2:
        return [float('nan')] * 2
    rng = np.random.default_rng(seed)
    bs = [rng.choice(d, len(d)).mean() for _ in range(n)]
    return [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))]


def step_summarize():
    rows = [json.loads(l) for l in open(os.path.join(OUT, 'per_case.jsonl'))]
    errors = [r for r in rows if 'error' in r]
    rows = [r for r in rows if 'error' not in r]
    by = {}
    for r in rows:
        by.setdefault(r['base'], {})[r['case']] = r
    cases = sorted(set(by.get('s05', {})) & set(by.get('s075', {})))
    V = ['raw', 'raw+bridge3', 'raw+repair', 'regap', 'regap+bridge3', 'regap+bridge3sup',
         'regap+bridge3sup+repair', 'regap+repair']
    table = {}
    for base in ('s05', 's075'):
        for v in V:
            vals = [by[base][c][v] for c in cases if v in by[base][c]]
            if not vals:
                continue
            table[f'{base}:{v}'] = dict(n=len(vals), tf1_15=float(np.mean([x['tf1_15'] for x in vals])),
                                        tf1_0=float(np.mean([x['tf1_0'] for x in vals])),
                                        rooted_15=float(np.mean([x['rooted_15'] for x in vals])),
                                        dice=float(np.mean([x['dice'] for x in vals])),
                                        fp_after=float(np.mean([x['fp_after'] for x in vals])))
            br = [b for x in vals for b in x.get('bridges', [])]
            if br:
                table[f'{base}:{v}'].update(bridges=len(br), fp_joins=sum(not b['true_join'] for b in br),
                                            cross_tree=sum(b['cross_tree'] for b in br))

    def paired(a, b):
        d = [by[b[0]][c][b[1]]['tf1_15'] - by[a[0]][c][a[1]]['tf1_15'] for c in cases
             if a[1] in by[a[0]][c] and b[1] in by[b[0]][c]]
        return dict(mean=float(np.mean(d)) if d else None, ci95=boot_ci(d), n=len(d),
                    better=int(sum(x > 0.001 for x in d)), worse=int(sum(x < -0.001 for x in d)))
    comps = {
        'C1 tile 0.5 vs 0.75 (raw)': paired(('s075', 'raw'), ('s05', 'raw')),
        "C2 P1' on default overlap: s05 regap+bridge3sup vs s05 raw": paired(('s05', 'raw'), ('s05', 'regap+bridge3sup')),
        "C3 P1' on 0.75 vs default 0.5 raw": paired(('s05', 'raw'), ('s075', 'regap+bridge3sup')),
        'C4 bridging alone (s05)': paired(('s05', 'raw'), ('s05', 'raw+bridge3')),
        'C5 support rule: s05 regap+bridge3sup vs regap+bridge3': paired(('s05', 'regap+bridge3'), ('s05', 'regap+bridge3sup')),
        'C6 label repair (s05 raw)': paired(('s05', 'raw'), ('s05', 'raw+repair')),
        'C7 full stage (s05 regap+bridge3sup+repair) vs raw': paired(('s05', 'raw'), ('s05', 'regap+bridge3sup+repair')),
    }
    raw = [by['s05'][c]['raw'] for c in cases]
    facts = dict(n_test_cases=len(cases), n_errors=len(errors),
                 n_degenerate=int(sum(by['s05'][c].get('degenerate', False) for c in cases)),
                 cut_cases_rooted15_lt_0_9=int(sum(x['rooted_15'] < 0.9 for x in raw)),
                 fp_gate_raw_mean=float(np.mean([by['s05'][c]['fp_gate_raw'] for c in cases])),
                 ostium_flagged_trees=int(sum(len(by['s05'][c]['ostium_flags']) for c in cases)),
                 reference_trees=int(sum(by['s05'][c]['ref_trees'] for c in cases)),
                 mean_gap_sites_s05=float(np.mean([by['s05'][c]['n_sites'] for c in cases])),
                 per_class_tf1_s05_raw={k: float(np.mean([x['per_class_15'].get(k, np.nan) for x in raw
                                                          if k in x['per_class_15']])) for k in ('1', '2', '3', '4')})
    split = json.load(open(os.path.join(WORK, 'split.json')))
    res = dict(table=table, comparisons=comps, facts=facts, split_sizes={k: len(split[k]) for k in ('train', 'val', 'test')},
               layout=split['layout'], smoke=SMOKE)
    tl = glob.glob(os.path.join(model_dir(), 'fold_0', 'training_log_*.txt'))
    if tl:
        txt = open(sorted(tl)[-1]).read()
        res['epochs_trained'] = len(re.findall(r'Epoch time', txt))
        res['epoch_seconds_median'] = float(np.median([float(x) for x in re.findall(r'Epoch time: ([\d.]+) s', txt)] or [np.nan]))
    json.dump(res, open(os.path.join(OUT, 'results.json'), 'w'), indent=1)
    L = ['# Delta Trillium experiment — results', '',
         'One 4-class nnU-Net (ResEnc-L planner, 0.5 mm iso, fixed window, no mirroring, ~250 epochs) trained on the',
         'thick convention (ImageCAS mask split by ImageCAS-X names, territory, ramus->LCx), tested on the',
         f"{facts['n_test_cases']} ImageCAS-X test cases. Deciding metric: macro tree-F1 @ 1.5 mm.", '',
         '## Variants (mean over test cases)', '',
         '| variant | tF1@1.5 | tF1@0 | rooted@1.5 | macro Dice | FP comps after | bridges (FP joins, cross-tree) |',
         '|---|---|---|---|---|---|---|']
    for k, t in table.items():
        L.append(f"| {k} | {t['tf1_15']:.3f} | {t['tf1_0']:.3f} | {t['rooted_15']:.3f} | {t['dice']:.3f} | "
                 f"{t['fp_after']:.2f} | {t.get('bridges', '')} ({t.get('fp_joins', '')}, {t.get('cross_tree', '')}) |")
    L += ['', '## Paired comparisons (tF1@1.5, per-case difference, bootstrap 95 % CI)', '']
    for k, c in comps.items():
        L.append(f"- **{k}**: {c['mean']:+.4f} [{c['ci95'][0]:+.4f}, {c['ci95'][1]:+.4f}], n={c['n']}, "
                 f"better {c['better']}, worse {c['worse']}" if c['mean'] is not None else f'- {k}: n/a')
    L += ['', '## Facts', '', '```', json.dumps(facts, indent=1), '```', '',
          '## How to read it', '',
          "- C1 ~ 0 and C3 <= C2: tile overlap is not the issue; P1' stands or falls on C2.",
          "- C2 CI excluding 0 in favour: adopt P1' (gap-centred re-inference + support-gated bridging).",
          "- C2 CI including 0, or 'worse' > 0 cases: drop P1' (keep nnU-Net default inference).",
          '- C5: the support rule should block FP joins (see bridges column) without losing tF1.',
          '- cut_cases: how often the master-class model cuts trees on the decided thick convention.']
    open(os.path.join(OUT, 'SUMMARY.md'), 'w').write('\n'.join(L) + '\n')
    log('summary written to', OUT)


STEPS = dict(prepare=step_prepare, plan=step_plan, train=step_train, evaluate=step_evaluate,
             summarize=step_summarize)

if __name__ == '__main__':
    which = sys.argv[1]
    for name in (list(STEPS) if which == 'all' else [which]):
        if name in ('prepare', 'plan') and os.path.exists(marker(name)):
            log(f'step {name}: already done'); continue
        log(f'step {name} ...')
        STEPS[name]()
        if name in ('prepare', 'plan'):
            open(marker(name), 'w').write(time.ctime())
