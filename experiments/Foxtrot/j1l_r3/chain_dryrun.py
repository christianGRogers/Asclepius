"""Foxtrot, Janus 1-L round 3 (#302, Round 2 section 5 item 6): run the plan's own command lines end to end on
synthetic phantoms, so every interface between the scripts of record is exercised before the lead runs them.

No image, label or score of any real case is read. Every volume is a synthetic coronary phantom (the r9 scorer's own
fixture tree, with per-case perturbations); the case ids are those of the plan's lists only because the scripts of
record refuse any other id. Nothing is trained or predicted: the "nnU-Net outputs" are probabilities made from the
phantom, in nnU-Net 2.8.1's on-disk form (`<case>.npz` with `probabilities` in SimpleITK axis order, plus the argmax
`<case>.nii.gz`).

Steps, each the master plan's command (section 5) or this candidate's (Foxtrot v3 section 6), run as a subprocess
from the plan's text with the plan's variables ($W, $J0, $R):
  J0   Job 0 after inference: threshold_export -> r9 scorer x 5 t on the tuning 60 -> decide.py select -> r9 scorer on
       the locked 100 at argmax -> the job's own print block.
  L0   the identity check: split_val80.json -> r9 scorer --pair Fir -> l0_check.py (clause 3 is in no posted block).
  T    the master plan's line T=$(python -c "...'%.2f' % ...['chosen_t']") as written, then as corrected.
  DC   error_decomp.py at t = 0.50 and t*, mde_from_job0.py.
  RT   Rule T: threshold_export on Janus 0's D60 probabilities at t* and on C's at Rule T's 8-step grid, then
       rule_t.py. C's phantom is drawn wider than Janus 0's, so t_C must land between t* and 0.50.

Each step's result (ok or the exact error) goes to chain_dryrun.json. Usage: python chain_dryrun.py [--keep DIR]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(R, 'experiments', 'Atlas'))
import r9_score_icx4 as r9  # noqa: E402
from scipy import ndimage  # noqa: E402

LISTS = json.load(open(os.path.join(R, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))
D60 = json.load(open(os.path.join(R, 'experiments', 'Delta', 'j1l_r2', 'drift60.json')))['drift60']
SEALED = json.load(open(os.path.join(R, 'trillium', 'sealed_test.json')))
assert not (set(LISTS['job0']) | set(D60)) & (set(SEALED['sealed_icx_test']) | set(SEALED['sealed_quality0']))


def probs_from(ref, shift_mm, rng, soft=0.25, sp=0.5):
    """5-class probabilities whose 0.5 iso-surface sits shift_mm inside the phantom's wall (shift < 0: outside)."""
    inside = ndimage.distance_transform_edt(ref > 0) * sp
    outside = ndimage.distance_transform_edt(ref == 0) * sp
    s = np.where(ref > 0, inside - 0.5 * sp, -(outside - 0.5 * sp))          # signed distance to the wall, mm
    s = s + rng.normal(0, 0.05, ref.shape)
    pfg = 1.0 / (1.0 + np.exp(-(s - shift_mm) / soft))
    _, idx = ndimage.distance_transform_edt(ref == 0, return_indices=True)
    near = ref[tuple(idx)]                                                    # nearest vessel class, everywhere
    p = np.zeros((5,) + ref.shape, np.float32)
    p[0] = 1 - pfg
    for k in range(1, 5):
        p[k] = np.where(near == k, 0.94 * pfg, 0.02 * pfg)
    return p


def variant(ref, i, rng):
    """Per-case phantom: a random short cut or a truncation on a few cases, so scores and decompositions vary."""
    v = ref.copy()
    k = i % 6
    if k == 1:
        a = 50 + rng.integers(0, 20)
        s = v[a:a + 3]
        s[s == 2] = 0
    elif k == 2:
        s = v[90:]
        s[s == 3] = 0
    return v


def write_nnunet(dirp, c, p, aff):
    import nibabel as nib
    os.makedirs(dirp, exist_ok=True)
    seg = p.argmax(0).astype(np.uint8)
    np.savez_compressed(os.path.join(dirp, f'{c}.npz'), probabilities=p.transpose(0, 3, 2, 1).astype(np.float16))
    nib.save(nib.Nifti1Image(seg, aff), os.path.join(dirp, f'{c}.nii.gz'))
    return seg


def sh(cmd, env, log, name, expect_fail=False):
    t = time.time()
    p = subprocess.run(['bash', '-c', cmd], env=env, capture_output=True, text=True)
    ok = (p.returncode != 0) if expect_fail else (p.returncode == 0)
    tail = (p.stdout + p.stderr).strip().splitlines()[-4:]
    log.append(dict(step=name, ok=ok, returncode=p.returncode, expect_fail=expect_fail,
                    seconds=round(time.time() - t, 1), tail=tail))
    print(f"[dryrun] {'OK  ' if ok else 'FAIL'} {name} (rc {p.returncode})", flush=True)
    if not ok:
        print('\n'.join(tail), flush=True)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keep')
    a = ap.parse_args()
    base = a.keep or tempfile.mkdtemp(prefix='j1l_dryrun_')
    W, J0 = os.path.join(base, 'j1l_job0'), os.path.join(base, 'janus0')
    rng = np.random.default_rng(302)
    ref0, aorta, _ = r9.synthetic()
    aff = np.diag([0.5, 0.5, 0.5, 1.0])
    # --- inputs in Step T's layout: $J0/icx, $J0/aorta, $J0/pred_fir; CTs as Trillium's cases/<c>/ct.nii.gz ----------
    import nibabel as nib
    cases_dir = os.path.join(base, 'cases')
    for i, c in enumerate(LISTS['job0']):
        ref = variant(ref0, i, rng)
        tmp = os.path.join(base, 'tmp')
        ctp = r9.write_case(tmp, c, ref, ref, aorta)       # icx = the phantom itself
        os.makedirs(os.path.join(J0, 'icx'), exist_ok=True)
        os.makedirs(os.path.join(J0, 'aorta'), exist_ok=True)
        os.makedirs(os.path.join(cases_dir, c), exist_ok=True)
        n = int(c[1:]) + 1
        shutil.move(os.path.join(tmp, 'icx', f'{n}.coronary.nii.gz'), os.path.join(J0, 'icx', f'{n}.coronary.nii.gz'))
        shutil.move(os.path.join(tmp, 'aorta', f'{c}_aorta.nii.gz'), os.path.join(J0, 'aorta', f'{c}_aorta.nii.gz'))
        shutil.move(ctp, os.path.join(cases_dir, c, 'ct.nii.gz'))
        # Janus 0 draws the lumen 0.25 mm thin (the inward rim); its probabilities as Job 0 saves them
        p = probs_from(ref, 0.25, rng)
        seg = write_nnunet(os.path.join(W, 'probs'), c, p, aff)
        if c in LISTS['locked100']:
            # Fir's own prediction: the same argmax, except two cases with a few flipped rim voxels (GPU noise)
            f = seg.copy()
            if c in LISTS['locked100'][:2]:
                rim = (ndimage.binary_dilation(f > 0) & (f == 0))
                zz = np.argwhere(rim)[rng.choice(int(rim.sum()), 20, replace=False)]
                f[tuple(zz.T)] = 2
            os.makedirs(os.path.join(J0, 'pred_fir'), exist_ok=True)
            nib.save(nib.Nifti1Image(f, aff), os.path.join(J0, 'pred_fir', f'{c}.nii.gz'))
    shutil.rmtree(os.path.join(base, 'tmp'), ignore_errors=True)
    # D60: no label exists; Janus 0's and C's probabilities on unlabelled phantoms. C is drawn 0.15 mm wider.
    for i, c in enumerate(D60):
        ref = variant(ref0, i + 3, rng)
        write_nnunet(os.path.join(W, 'd60_probs_j0'), c, probs_from(ref, 0.25, rng), aff)
        write_nnunet(os.path.join(W, 'd60_probs_C'), c, probs_from(ref, 0.10, rng), aff)
    env = dict(os.environ, W=W, J0=J0, R=R, SCRATCH=base, E=os.path.join(R, 'experiments', 'Crucible', 'j1l_r1'))
    log = []
    # ---- J0: Job 0's lines after nnUNetv2_predict, verbatim from job0_janus0_probs.sh (steps 2-4) -------------------
    sh('python $E/threshold_export.py --probs $W/probs --out $W/thr --t 0.5 0.45 0.4 0.35 0.3 --np 4', env, log,
       'J0.threshold_export')
    sh(f'''mkdir -p $W/scores && python - "$E/lists.json" "$W" "{cases_dir}" <<'PY'
import json, sys
L = json.load(open(sys.argv[1])); W = sys.argv[2]; C = sys.argv[3]
json.dump({{'val': L['tuning60']}}, open(f'{{W}}/split_tuning60.json', 'w'))
json.dump({{'val': L['locked100']}}, open(f'{{W}}/split_locked100.json', 'w'))
json.dump({{'cases': {{c: {{'ct': f'{{C}}/{{c}}/ct.nii.gz'}} for c in L['job0']}}}}, open(f'{{W}}/layout.json', 'w'))
PY''', env, log, 'J0.splits_layout')
    SC = 'python $R/experiments/Atlas/r9_score_icx4.py --icx $J0/icx --aorta $J0/aorta --layout $W/layout.json --set val --np 4'
    for t in ('0.50', '0.45', '0.40', '0.35', '0.30'):
        sh(f'{SC} --pred $W/thr/t{t} --splits $W/split_tuning60.json --out $W/scores/tuning60_t{t}.json > /dev/null',
           env, log, f'J0.score_tuning60_t{t}')
    sh('python $E/decide.py select --scores t0.50=$W/scores/tuning60_t0.50.json t0.45=$W/scores/tuning60_t0.45.json '
       't0.40=$W/scores/tuning60_t0.40.json t0.35=$W/scores/tuning60_t0.35.json t0.30=$W/scores/tuning60_t0.30.json '
       '> $W/select.json', env, log, 'J0.decide_select')
    sh(f'{SC} --pred $W/thr/t0.50 --splits $W/split_locked100.json --out $W/scores/locked100_janus0_argmax.json > /dev/null',
       env, log, 'J0.score_locked100_argmax')
    sh('''python - $W <<'PY'
import json, sys
W = sys.argv[1]; s = json.load(open(f'{W}/select.json'))
print('[job0] chosen t =', s['chosen_t'])
for t, v in s['per_threshold'].items():
    print(f"[job0] tuning60 t={t}: tF1 {v['tf1']:.4f} Dice {v['dice']:.4f} FP {v['fp']:.2f} qualifies {v['qualifies']}")
b = json.load(open(f'{W}/scores/locked100_janus0_argmax.json'))['summary']
print('[job0] locked100 Janus 0 argmax: decisive macro', b.get('decisive_macro_tf1'), b.get('decisive_macro_tf1_ci'),
      'Dice', b['dice_mean'].get('tree'))
PY''', env, log, 'J0.print_block')
    # ---- L0: the master plan's identity commands, then l0_check.py --------------------------------------------------
    sh('''python -c "
import json; L = json.load(open('$R/experiments/Crucible/j1l_r1/lists.json'))
json.dump({'val': [c for c in L['locked100'] if c not in L['locked20_of_open36']]}, open('$W/split_val80.json', 'w'))"''',
       env, log, 'L0.split_val80')
    sh('python $R/experiments/Atlas/r9_score_icx4.py --pred $W/thr/t0.50 --pair $J0/pred_fir --icx $J0/icx '
       '--aorta $J0/aorta --layout $W/layout.json --splits $W/split_val80.json --set val --np 4 '
       '--out $W/scores/identity_val80.json > /dev/null', env, log, 'L0.score_pair')
    sh('python $R/experiments/Foxtrot/j1l_r3/l0_check.py --scores $W/scores/identity_val80.json '
       '--mode fir-determinism --out $W/l0.json', env, log, 'L0.l0_check (phantoms are not Janus 0: clauses 1-2 must FAIL)',
       expect_fail=True)
    # ---- T: the post-Job-0 threshold line, as written and as corrected ---------------------------------------------
    sh('''T=$(python -c "import json;print('%.2f' % json.load(open('$W/select.json'))['chosen_t'])") && echo "T=$T"''',
       env, log, 'T.as_written_in_master_plan', expect_fail=True)
    p = sh('''T=$(python -c "import json;print('%.2f' % float(json.load(open('$W/select.json'))['chosen_t']))") && echo $T''',
           env, log, 'T.corrected')
    T = p.stdout.strip().splitlines()[-1] if p.returncode == 0 else '0.50'
    env['T'] = T
    # ---- DC: decomposition and MDE (master plan section 5, after Job 0) --------------------------------------------
    for t in sorted({'0.50', T}):
        sh(f'python $R/experiments/Bridge/j1l_r2/error_decomp.py --pred $W/thr/t{t} --icx $J0/icx --aorta $J0/aorta '
           f'--layout $W/layout.json --np 4 --out $W/scores/error_decomp_tuning60_t{t}.json > /dev/null',
           env, log, f'DC.error_decomp_t{t}')
    sh('python $R/experiments/Delta/j1l_r2/mde_from_job0.py $W/scores/locked100_janus0_argmax.json > $W/scores/mde.json',
       env, log, 'DC.mde_from_job0')
    # ---- RT: Rule T exports and rule_t.py ---------------------------------------------------------------------------
    sh('python $E/threshold_export.py --probs $W/d60_probs_j0 --out $W/d60_j0 --t $T --np 4', env, log,
       'RT.export_janus0_at_tstar')
    sh('python $E/threshold_export.py --probs $W/d60_probs_C --out $W/d60_C --t 0.60 0.55 0.50 0.45 0.40 0.35 0.30 0.25 '
       '--np 4', env, log, 'RT.export_C_grid')
    sh('python $R/experiments/Delta/j1l_r2/rule_t.py --j0 $W/d60_j0 --cand $W/d60_C --select $W/select.json '
       '--out $W/rule_t.json --np 4 > /dev/null', env, log, 'RT.rule_t')
    # ---- J0T: this candidate's D50 job (j0t_trillium.sh) with DRYRUN=1, on the same phantom probabilities ----------
    import hashlib
    V = os.path.join(base, 'j1l_j0t')
    for sub, src, ids in (('probs_l100', 'probs', LISTS['locked100']), ('probs_d60', 'd60_probs_j0', D60)):
        os.makedirs(os.path.join(V, sub), exist_ok=True)
        for c in ids:
            for ext in ('.npz', '.nii.gz'):
                shutil.copy(os.path.join(W, src, c + ext), os.path.join(V, sub, c + ext))
    env2 = dict(env, DRYRUN='1', JOB0=W, V=V, CASES=cases_dir,
                SELECT_SHA256=hashlib.sha256(open(os.path.join(W, 'select.json'), 'rb').read()).hexdigest())
    # phantoms are not Janus 0, so L0-T must FAIL (clauses 1-2) and stop the job before step 3 (exit 3)
    p = sh('bash $R/experiments/Foxtrot/j1l_r3/j0t_trillium.sh', env2, log, 'J0T.job_stops_at_L0_fail',
           expect_fail=True)
    log[-1]['ok'] = log[-1]['ok'] and p.returncode == 3 and not os.path.exists(os.path.join(V, 'd60_j0'))
    sh('SELECT_SHA256=0000 bash $R/experiments/Foxtrot/j1l_r3/j0t_trillium.sh', env2, log,
       'J0T.refuses_wrong_select_sha256', expect_fail=True)
    # step 3 alone (what runs after a PASS), then Rule T on its output: t_C must equal the RT step's
    step3 = os.path.join(base, 'step3.sh')
    open(step3, 'w').write(
        "set -euo pipefail\n"
        "T=$(python -c \"import json;print('%.2f' % float(json.load(open('$JOB0/select.json'))['chosen_t']))\")\n"
        "python $E/threshold_export.py --probs $V/probs_d60 --out $V/d60_j0 --t $T --np 4\n"
        "python $R/experiments/Delta/j1l_r2/rule_t.py --j0 $V/d60_j0 --cand $W/d60_C --select $W/select.json "
        "--out $V/rule_t.json --np 4 > /dev/null\n"
        "python -c \"import json,sys;a=json.load(open('$V/rule_t.json'))['t_C'];b=json.load(open('$W/rule_t.json'))['t_C'];"
        "print('t_C', a, b);sys.exit(a!=b)\"\n")
    sh(f'bash {step3}', env2, log, 'J0T.step3_then_rule_t_same_t_C')
    # ---- results ----------------------------------------------------------------------------------------------------
    out = dict(note='synthetic phantoms only; no real image, label or score was read', steps=log)
    rd = lambda p: json.load(open(p)) if os.path.exists(p) else None  # noqa: E731
    sel = rd(os.path.join(W, 'select.json'))
    if sel:
        out['select'] = dict(chosen_t=sel['chosen_t'], chosen_t_type=type(sel['chosen_t']).__name__,
                             per_threshold={t: dict(dice=round(v['dice'], 4), tf1=round(v['tf1'], 4),
                                                    qualifies=v['qualifies']) for t, v in sel['per_threshold'].items()})
    l0 = rd(os.path.join(W, 'l0.json'))
    if l0:
        out['l0'] = dict(verdict=l0['verdict'], clause3=l0['clause3_cases'])
        ident = rd(os.path.join(W, 'scores', 'identity_val80.json'))
        out['l0']['posted_blocks_keys'] = dict(summary=sorted(ident['summary']), paired=sorted(ident['paired']))
    rt = rd(os.path.join(W, 'rule_t.json'))
    if rt:
        out['rule_t'] = dict(t_star=rt['t_star'], t_C=rt['t_C'], dr_mm=rt['dr_mm'],
                             t_star_dice_bound=rt['t_star_dice_bound'])
    mde = os.path.join(W, 'scores', 'mde.json')
    if os.path.exists(mde):
        out['mde_keys'] = sorted(json.load(open(mde)))
    out['all_ok'] = all(s['ok'] for s in log)
    json.dump(out, open(os.path.join(HERE, 'chain_dryrun.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'steps'}, indent=1))
    if not a.keep:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == '__main__':
    main()
