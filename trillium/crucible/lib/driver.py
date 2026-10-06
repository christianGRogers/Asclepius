"""Crucible GPU experiment driver (runs INSIDE the SLURM job; also has a CPU smoke mode).

Question: every case will be read twice (D2). Given two reads per case, which training target makes the best model:
  single : one read only (what a single-read project would have)
  both   : both reads as two separate training samples
  agree  : voxels where the reads agree; disagreement -> nnU-Net ignore label
  union  : vessel if either read says vessel; class conflicts -> ignore
  oracle : the truth the reads were simulated from (upper bound)
Reads are SIMULATED from truth with a calibrated error model (lib/sim.py) because no team labels exist yet.
Scored on held-out cases with tree-F1 @ 1.5 mm against (i) the truth, (ii) each read, plus the inter-read ceiling.

All state lives in $CRUCIBLE_WORK (default $SCRATCH/crucible_2reads); every stage is skipped when its marker exists.
"""
import json, os, subprocess, sys, time, shutil, glob
import multiprocessing as mp
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim, tf1  # noqa: E402

SMOKE = os.environ.get('CRUCIBLE_SMOKE') == '1'
WORK = os.environ.get('CRUCIBLE_WORK') or os.path.join(os.environ.get('SCRATCH', '/tmp'), 'crucible_2reads')
N_TRAIN, N_TEST = (4, 2) if SMOKE else (int(os.environ.get('CRUCIBLE_NTRAIN', 200)), int(os.environ.get('CRUCIBLE_NTEST', 50)))
ARMS = ['single', 'both', 'agree', 'union', 'oracle']
DSID = {'single': 951, 'both': 952, 'agree': 953, 'union': 954, 'oracle': 955}
MARGIN_MM = 15.0
JOB_END = float(os.environ.get('CRUCIBLE_JOB_END', time.time() + 24 * 3600))
RESERVE = 1200 if SMOKE else 5400  # seconds kept for prediction + evaluation
NPROC = int(os.environ.get('SLURM_CPUS_PER_TASK', os.environ.get('CRUCIBLE_NPROC', 4)))
os.environ.setdefault('nnUNet_raw', os.path.join(WORK, 'nnUNet_raw'))
os.environ.setdefault('nnUNet_preprocessed', os.path.join(WORK, 'nnUNet_preprocessed'))
os.environ.setdefault('nnUNet_results', os.path.join(WORK, 'nnUNet_results'))
STATE = os.path.join(WORK, 'state.json')


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def save_state(s):
    json.dump(s, open(STATE + '.tmp', 'w'), indent=1); os.replace(STATE + '.tmp', STATE)


def run(cmd, env=None, ok=(0,)):
    log('$', ' '.join(map(str, cmd)))
    r = subprocess.run([str(c) for c in cmd], env={**os.environ, **(env or {})})
    if r.returncode not in ok:
        raise RuntimeError(f'command failed ({r.returncode}): {cmd}')
    return r.returncode


# ------------------------------------------------------------------ stage 1: labels, reads, crops, raw datasets
def select_cases():
    man = json.load(open(os.path.join(WORK, 'manifest.json')))
    icx = os.path.join(WORK, 'icx')
    split = {k: [int(x) for x in open(os.path.join(icx, f'{k}.txt')).read().split()] for k in ('train', 'val', 'test')}
    have = man['cases']
    pick = lambda ids, n: [f'c{i - 1:04d}' for i in sorted(ids) if f'c{i - 1:04d}' in have
                           and os.path.exists(os.path.join(icx, f'{i}.coronary.nii.gz'))][:n]
    # ImageCAS-X *test* (160) is never touched: it is the master plan's sealed-test pool.
    return pick(split['train'], N_TRAIN), pick(split['val'], N_TEST), have


def prep_case(args):
    c, paths, is_test = args
    import nibabel as nib
    out = os.path.join(WORK, 'cases', c); done = os.path.join(out, 'done')
    if os.path.exists(done):
        return c
    os.makedirs(out, exist_ok=True)
    mimg = nib.load(paths['mask']); m = np.asarray(mimg.dataobj) > 0.5
    icx = np.asarray(nib.load(os.path.join(WORK, 'icx', f"{paths['imagecas_id']}.coronary.nii.gz")).dataobj).astype(np.uint8)
    assert icx.shape == m.shape, (c, icx.shape, m.shape)
    sp = np.array(mimg.header.get_zooms()[:3], float)
    u = np.argwhere(m); mg = np.ceil(MARGIN_MM / sp).astype(int)
    lo = np.maximum(u.min(0) - mg, 0); hi = np.minimum(u.max(0) + mg + 1, m.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    m, icx = m[sl], icx[sl]
    T, near14 = sim.truth(m, icx)
    rl = sim.local_radius(T > 0, sp); roots = sim.ostia(T, sp)
    rng = np.random.default_rng(int(c[1:]))
    A = sim.make_read(T, near14, sp, rl, roots, rng); B = sim.make_read(T, near14, sp, rl, roots, rng)
    ctimg = nib.load(paths['ct'])
    ct = np.asarray(ctimg.dataobj[sl]).astype(np.int16)
    aff = mimg.slicer[sl].affine
    nib.save(nib.Nifti1Image(ct, aff), os.path.join(out, 'ct_0000.nii.gz'))
    for name, arr in (('T', T), ('A', A), ('B', B), ('agree', sim.fuse(A, B, 'agree')), ('union', sim.fuse(A, B, 'union'))):
        nib.save(nib.Nifti1Image(arr.astype(np.uint8), aff), os.path.join(out, f'{name}.nii.gz'))
    json.dump({'spacing': sp.tolist(), 'roots': [list(map(int, r)) for r in roots], 'test': is_test,
               'lo': lo.tolist(), 'shape': list(T.shape)}, open(os.path.join(out, 'meta.json'), 'w'))
    open(done, 'w').write('1')
    return c


def write_raw(train, test):
    labels = {'background': 0, 'left_main': 1, 'left_anterior_descending': 2, 'left_circumflex': 3, 'right_coronary_artery': 4}
    for arm in ARMS:
        d = os.path.join(os.environ['nnUNet_raw'], f'Dataset{DSID[arm]}_Crucible{arm.capitalize()}')
        for sub in ('imagesTr', 'labelsTr'):
            os.makedirs(os.path.join(d, sub), exist_ok=True)
        n = 0
        for c in train:
            src = os.path.join(WORK, 'cases', c)
            items = {'single': [(c, 'A')], 'both': [(c + 'A', 'A'), (c + 'B', 'B')], 'agree': [(c, 'agree')],
                     'union': [(c, 'union')], 'oracle': [(c, 'T')]}[arm]
            for name, lab in items:
                for s, t in ((os.path.join(src, 'ct_0000.nii.gz'), os.path.join(d, 'imagesTr', f'{name}_0000.nii.gz')),
                             (os.path.join(src, f'{lab}.nii.gz'), os.path.join(d, 'labelsTr', f'{name}.nii.gz'))):
                    if not os.path.lexists(t): os.symlink(s, t)
                n += 1
        lab = dict(labels)
        if arm in ('agree', 'union'):
            lab['ignore'] = sim.IGNORE
        json.dump({'channel_names': {'0': 'CT'}, 'labels': lab, 'numTraining': n, 'file_ending': '.nii.gz'},
                  open(os.path.join(d, 'dataset.json'), 'w'), indent=1)
    ts = os.path.join(WORK, 'imagesTs'); os.makedirs(ts, exist_ok=True)
    for c in test:
        t = os.path.join(ts, f'{c}_0000.nii.gz')
        if not os.path.lexists(t): os.symlink(os.path.join(WORK, 'cases', c, 'ct_0000.nii.gz'), t)


def stage_prep(st):
    if st.get('prep'): return
    train, test, have = select_cases()
    log(f'prep: {len(train)} train (ImageCAS-X train list), {len(test)} test (ImageCAS-X val list), {NPROC} workers')
    jobs = [(c, have[c], False) for c in train] + [(c, have[c], True) for c in test]
    with mp.Pool(max(1, NPROC - 2)) as pool:
        for i, c in enumerate(pool.imap_unordered(prep_case, jobs)):
            if i % 20 == 0: log('prepped', i + 1, '/', len(jobs))
    write_raw(train, test)
    st.update(prep=True, train=train, test=test); save_state(st)


# ------------------------------------------------------------------ stage 2: one plan for all arms, fixed CT window
def stage_plan(st):
    if st.get('plan'): return
    src = DSID['oracle']
    run(['nnUNetv2_extract_fingerprint', '-d', src, '-np', NPROC])
    run(['nnUNetv2_plan_experiment', '-d', src])
    pdir = glob.glob(os.path.join(os.environ['nnUNet_preprocessed'], f'Dataset{src}_*'))[0]
    pf = os.path.join(pdir, 'nnUNetPlans.json'); plans = json.load(open(pf))
    # master plan's fixed CT window [-300, 1300] HU, mean 100 / sd 400 (nnU-Net's default would derive it from labels)
    plans['foreground_intensity_properties_per_channel'] = {'0': {
        'max': 1300.0, 'mean': 100.0, 'median': 100.0, 'min': -300.0, 'percentile_00_5': -300.0,
        'percentile_99_5': 1300.0, 'std': 400.0}}
    json.dump(plans, open(pf, 'w'), indent=1)
    for arm in ARMS:
        if DSID[arm] == src: continue
        run(['nnUNetv2_extract_fingerprint', '-d', DSID[arm], '-np', NPROC])
        run(['nnUNetv2_move_plans_between_datasets', '-s', src, '-t', DSID[arm], '-sp', 'nnUNetPlans', '-tp', 'nnUNetPlans'])
    st.update(plan=True, plans_3d=plans['configurations']['3d_fullres'].get('patch_size'),
              spacing=plans['configurations']['3d_fullres'].get('spacing')); save_state(st)


def stage_preprocess(st):
    if st.get('preprocess'): return
    run(['nnUNetv2_preprocess', '-d'] + [DSID[a] for a in ARMS] + ['-c', '3d_fullres', '-np', max(1, NPROC - 2)])
    st.update(preprocess=True); save_state(st)


# ------------------------------------------------------------------ stage 3: probe epoch time, then train arms
def train_cmd(arm, cont):
    cmd = ['nnUNetv2_train', DSID[arm], '3d_fullres', 'all', '-tr', 'nnUNetTrainerCrucible']
    if cont: cmd.append('--c')
    if SMOKE: cmd += ['-device', 'cpu']
    return cmd


def out_dir(arm, results=None):
    r = results or os.environ['nnUNet_results']
    g = glob.glob(os.path.join(r, f'Dataset{DSID[arm]}_*', 'nnUNetTrainerCrucible__nnUNetPlans__3d_fullres', 'fold_all'))
    return g[0] if g else None


def stage_probe(st):
    if st.get('epochs'): return
    if SMOKE:
        st.update(epochs=1, t_epoch=None); save_state(st); return
    pres = os.path.join(WORK, 'probe_results')
    run(train_cmd('single', False), env={'nnUNet_results': pres, 'CRUCIBLE_EPOCHS': '4'})
    times = [float(l.split()[1]) for l in open(os.path.join(out_dir('single', pres), 'epoch_times.txt'))]
    t = float(np.mean(times[1:])) if len(times) > 1 else times[0]
    remaining = JOB_END - time.time() - RESERVE
    e = int(remaining / (len(ARMS) * t * 1.06))
    e = max(20, min(300, e))
    log(f'probe: {t:.1f} s/epoch -> {e} epochs per arm for {len(ARMS)} arms')
    st.update(t_epoch=t, epochs=e); save_state(st)


def stage_train(st):
    env = {'CRUCIBLE_EPOCHS': str(st['epochs']), 'CRUCIBLE_DEADLINE': str(JOB_END - RESERVE)}
    if SMOKE: env.update(CRUCIBLE_ITERS='2', CRUCIBLE_VAL_ITERS='1')
    for arm in ARMS:
        if st.get(f'train_{arm}'): continue
        od = out_dir(arm)
        cont = bool(od and os.path.exists(os.path.join(od, 'checkpoint_latest.pth')))
        code = run(train_cmd(arm, cont), env=env, ok=(0, 75))
        if code == 75:
            log(f'arm {arm}: deadline reached; stopping training here (re-run ./crucible to resume)')
            st[f'unfinished_{arm}'] = True; save_state(st); return False
        st[f'train_{arm}'] = True; save_state(st)
    return True


# ------------------------------------------------------------------ stage 4: predict + evaluate
def stage_predict(st):
    for arm in ARMS:
        if not st.get(f'train_{arm}') or st.get(f'pred_{arm}'): continue
        o = os.path.join(WORK, 'pred', arm); os.makedirs(o, exist_ok=True)
        cmd = ['nnUNetv2_predict', '-i', os.path.join(WORK, 'imagesTs'), '-o', o, '-d', DSID[arm], '-c', '3d_fullres',
               '-tr', 'nnUNetTrainerCrucible', '-f', 'all', '-chk', 'checkpoint_final.pth', '--disable_tta',
               '-npp', '3', '-nps', '3']
        if SMOKE: cmd += ['-device', 'cpu']
        run(cmd); st[f'pred_{arm}'] = True; save_state(st)


def eval_case(c):
    import nibabel as nib
    d = os.path.join(WORK, 'cases', c); meta = json.load(open(os.path.join(d, 'meta.json')))
    sp = np.array(meta['spacing']); rts = [np.array(r) for r in meta['roots']]
    L = {k: np.asarray(nib.load(os.path.join(d, f'{k}.nii.gz')).dataobj).astype(np.uint8) for k in ('T', 'A', 'B')}
    row = {'case': c}
    s = tf1.score(L['A'], L['B'], sp, rts); row['inter_read'] = {'tf1': tf1.macro(s), 'dice': tf1.macro(s, 'dice'),
                                                                 'per_class_tf1': {k: v['tf1'] for k, v in s.items()}}
    for arm in ARMS:
        f = os.path.join(WORK, 'pred', arm, f'{c}.nii.gz')
        if not os.path.exists(f): continue
        p = tf1.drop_small(np.asarray(nib.load(f).dataobj).astype(np.uint8))
        r = {}
        for ref in ('T', 'A', 'B'):
            s = tf1.score(L[ref], p, sp, rts)
            r[f'vs_{ref}'] = {'tf1': tf1.macro(s), 'dice': tf1.macro(s, 'dice'), 'rec': tf1.macro(s, 'rec'),
                              'rec_unrooted': tf1.macro(s, 'rec_unrooted'), 'prec': tf1.macro(s, 'prec'),
                              'per_class_tf1': {k: v['tf1'] for k, v in s.items()}}
        r['fg_ratio_vs_T'] = float((p > 0).sum() / max(1, (L['T'] > 0).sum()))
        row[arm] = r
    return row


def stage_eval(st):
    with mp.Pool(max(1, NPROC - 2)) as pool:
        rows = pool.map(eval_case, st['test'])
    res = {'question': 'two reads per case: which training target', 'arms': ARMS, 'epochs_per_arm': st.get('epochs'),
           't_epoch_s': st.get('t_epoch'), 'n_train': len(st['train']), 'n_test': len(st['test']),
           'patch_size': st.get('plans_3d'), 'spacing': st.get('spacing'), 'noise_model': sim.PARAMS,
           'unfinished': [a for a in ARMS if st.get(f'unfinished_{a}')], 'smoke': SMOKE, 'cases': rows}
    rng = np.random.default_rng(0); summ = {}
    for arm in ARMS:
        ok = [r for r in rows if arm in r]
        if not ok: continue
        summ[arm] = {}
        for ref in ('T', 'A', 'B'):
            for k in ('tf1', 'dice', 'rec', 'rec_unrooted', 'prec'):
                summ[arm][f'{k}_vs_{ref}'] = float(np.mean([r[arm][f'vs_{ref}'][k] for r in ok]))
        summ[arm]['tf1_vs_reads'] = (summ[arm]['tf1_vs_A'] + summ[arm]['tf1_vs_B']) / 2
        summ[arm]['fg_ratio_vs_T'] = float(np.mean([r[arm]['fg_ratio_vs_T'] for r in ok]))
    summ['inter_read'] = {'tf1': float(np.mean([r['inter_read']['tf1'] for r in rows])),
                          'dice': float(np.mean([r['inter_read']['dice'] for r in rows]))}
    pairs = {}
    for a in ('both', 'agree', 'union', 'oracle'):
        for ref in ('T', 'reads'):
            ok = [r for r in rows if a in r and 'single' in r]
            if not ok: continue
            f = (lambda r, arm: r[arm][f'vs_{ref}']['tf1']) if ref == 'T' else \
                (lambda r, arm: (r[arm]['vs_A']['tf1'] + r[arm]['vs_B']['tf1']) / 2)
            dlt = np.array([f(r, a) - f(r, 'single') for r in ok])
            bs = [rng.choice(dlt, len(dlt)).mean() for _ in range(5000)]
            pairs[f'{a}-single_vs_{ref}'] = {'mean': float(dlt.mean()), 'ci95': [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                                             'wins': int((dlt > 0).sum()), 'n': len(dlt)}
    res['summary'] = summ; res['paired_vs_single'] = pairs
    rd = os.path.join(WORK, 'results'); os.makedirs(rd, exist_ok=True)
    json.dump(res, open(os.path.join(rd, 'results.json'), 'w'), indent=1)
    write_summary(res, os.path.join(rd, 'SUMMARY.md'))
    st['eval'] = True; save_state(st)


def write_summary(res, path):
    s = res['summary']; L = []
    L.append('# Crucible GPU experiment: training on two reads per case\n')
    L.append(f"{'SMOKE TEST (CPU, meaningless numbers). ' if res['smoke'] else ''}nnU-Net v2 3d_fullres, no mirroring, "
             f"{res['epochs_per_arm']} epochs x 250 iterations per arm ({res['t_epoch_s']} s/epoch), patch {res['patch_size']}, "
             f"spacing {res['spacing']}. {res['n_train']} training cases (ImageCAS-X train list), {res['n_test']} test cases "
             f"(ImageCAS-X val list). Reads simulated (noise model {res['noise_model']}). Unfinished arms: {res['unfinished'] or 'none'}.\n")
    L.append('| arm | tF1 vs truth | tF1 vs reads (mean of A, B) | Dice vs truth | rooted recall vs truth | precision vs truth | fg volume / truth |')
    L.append('|---|---|---|---|---|---|---|')
    for a in res['arms']:
        if a in s:
            x = s[a]
            L.append(f"| {a} | {x['tf1_vs_T']:.3f} | {x['tf1_vs_reads']:.3f} | {x['dice_vs_T']:.3f} | {x['rec_vs_T']:.3f} | {x['prec_vs_T']:.3f} | {x['fg_ratio_vs_T']:.3f} |")
    L.append(f"\nInter-read ceiling (read B scored against read A): tF1 {s['inter_read']['tf1']:.3f}, Dice {s['inter_read']['dice']:.3f}.\n")
    L.append('Paired differences against the single-read arm (per test case, bootstrap 95 % CI):\n')
    for k, v in res['paired_vs_single'].items():
        L.append(f"- {k}: {v['mean']:+.3f} [{v['ci95'][0]:+.3f}, {v['ci95'][1]:+.3f}], better in {v['wins']}/{v['n']}")
    L.append('\nReading guide: the scheme with the highest tF1 vs truth (CI excluding 0 vs single) is the recommended way to use '
             'the team\'s two reads; "vs reads" shows what the same model scores against an individual annotator, i.e. how '
             'evaluation against single reads under-states it. See vault/Plans/Experiments/Crucible - GPU experiment on '
             'training with two reads per case (pending).md for the decision rule.')
    open(path, 'w').write('\n'.join(L) + '\n')


def main():
    os.makedirs(WORK, exist_ok=True)
    st = state()
    stage_prep(st); stage_plan(st); stage_preprocess(st); stage_probe(st)
    stage_train(st)
    stage_predict(st)
    stage_eval(st)
    log('done; results in', os.path.join(WORK, 'results'))


if __name__ == '__main__':
    main()
