"""Crucible, Janus 1-L round 3: the seams between the merged scripts that #306's predict / transfer / collect chain.

No image, label or score of any real case is read. Synthetic tubes stand in for nnU-Net outputs; three D60 *ids*
are used as file names only (rule_t.py refuses any other id).

Checks, each printed PASS/FAIL:
  S1  nnU-Net's `--save_probabilities` layout (`<case>.npz` key `probabilities`, SimpleITK axis order, + `<case>.nii.gz`)
      -> `nnUNetv2_ensemble --save_npz` (mean of the members' `probabilities`, same key; read from nnU-Net 2.8.1's
      ensembling/ensemble.py, emulated here) -> threshold_export.py accepts E (its argmax/orientation guard holds).
  S2  threshold_export.py must be given Rule T's whole grid (0.60 ... 0.25) for C, else rule_t.py stops at the first
      missing t: the predict/transfer command must pass `--t 0.6 0.55 0.5 0.45 0.4 0.35 0.3 0.25`.
  S3  decide.py select -> select.json ('chosen_t' a string, per_threshold keyed '0.50' ...) is what rule_t.py's
      dice_bound() and t* parsing read.
  S4  rule_t.py on E carries the width: a candidate already as wide at 0.50 as Janus 0 at t* gets t_C = 0.50, a
      candidate as thin as Janus 0 keeps t*.
  S5  gate.py's self-tests fail when the gate's logic is broken (mutation test, L-A21 "each self-test must fail on a
      broken fixture"): removing Q-R2-3, moving -0.015, dropping FP from H1, or replacing L3 with G3 as written.

Usage: python pipeline_check.py   (writes pipeline_check.json)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1'))
sys.path.insert(0, os.path.join(ROOT, 'experiments', 'Delta', 'j1l_r2'))
import nibabel as nib  # noqa: E402
import threshold_export as TE  # noqa: E402
import rule_t as RT  # noqa: E402
import decide as DC  # noqa: E402

SHAPE = (24, 30, 40)          # nibabel (x, y, z) order
SP = (0.5, 0.5, 0.5)
RES = {}


def report(name, ok, detail=''):
    RES[name] = dict(passed=bool(ok), detail=detail)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def tube_probs(r_half):
    """(5, x, y, z) softmax-like probabilities of one vessel (class 2) along z; P(vessel) = 0.5 at radius r_half mm,
    falling linearly over 1.5 mm around it, so the export radius at threshold t is r_half + 1.5 (0.5 - t)."""
    x, y, z = np.indices(SHAPE) * 0.5
    d = np.hypot(x - 6, y - 7.5)
    pv = np.clip(0.5 - (d - r_half) / 1.5, 0.0, 1.0)
    p = np.zeros((5,) + SHAPE, np.float32)
    p[2] = pv * 0.9; p[3] = pv * 0.1; p[0] = 1 - pv
    return p


def write_member(folder, case, prob):
    """What nnUNetv2_predict --save_probabilities writes: npz in SimpleITK (z, y, x) order + the argmax segmentation."""
    os.makedirs(folder, exist_ok=True)
    np.savez_compressed(os.path.join(folder, case + '.npz'), probabilities=prob.transpose(0, 3, 2, 1))
    nib.save(nib.Nifti1Image(prob.argmax(0).astype(np.uint8), np.diag(list(SP) + [1])),
             os.path.join(folder, case + '.nii.gz'))


def ensemble(folders, out):
    """nnU-Net 2.8.1 ensemble.py merge_files: mean of np.load(f)['probabilities'] (float32), argmax segmentation via
    write_seg, and with --save_npz the mean saved under the same key. Without --save_npz no .npz is written."""
    os.makedirs(out, exist_ok=True)
    for f in sorted(os.listdir(folders[0])):
        if not f.endswith('.npz'):
            continue
        avg = np.mean([np.load(os.path.join(d, f))['probabilities'].astype(np.float32) for d in folders], 0)
        np.savez_compressed(os.path.join(out, f), probabilities=avg)
        seg = avg.argmax(0).transpose(2, 1, 0).astype(np.uint8)
        nib.save(nib.Nifti1Image(seg, np.diag(list(SP) + [1])), os.path.join(out, f[:-4] + '.nii.gz'))


def export(folder, out, ts):
    for f in sorted(os.listdir(folder)):
        if f.endswith('.npz'):
            TE.one((os.path.join(folder, f), out, ts))


def main():
    D60 = json.load(open(os.path.join(ROOT, 'experiments', 'Delta', 'j1l_r2', 'drift60.json')))['drift60'][:3]
    grid = list(RT.GRID)
    W = tempfile.mkdtemp()
    try:
        # Janus 0 thin (P = 0.5 at 1.2 mm); a1, a2 already wider (1.6, 1.8 mm); E their mean.
        for c in D60:
            write_member(f'{W}/j0', c, tube_probs(1.2))
            write_member(f'{W}/a1', c, tube_probs(1.6))
            write_member(f'{W}/a2', c, tube_probs(1.8))
        ensemble([f'{W}/a1', f'{W}/a2'], f'{W}/E')
        try:
            export(f'{W}/E', f'{W}/E_thr', grid)
            report('S1 ensemble -> threshold_export', True, 'E npz (key probabilities, SimpleITK order) accepted; '
                   'argmax/orientation guard holds on the mean')
        except Exception as e:  # noqa: BLE001
            report('S1 ensemble -> threshold_export', False, repr(e))

        # S3: select.json from decide.py select, on fake scorer rows where Dice peaks at 0.40 and every guard holds
        rows = lambda dice: [dict(case=f'c{i:04d}', provisional=False, flagged_classes=[],  # noqa: E731
                                  per_class={k: 0.9 for k in DC.CLASSES}, recall={k: 0.9 for k in DC.CLASSES},
                                  fp_components=0, dice={'tree': dice}) for i in range(60)]
        sc = {}
        for t, dice in (('0.50', 0.880), ('0.45', 0.895), ('0.40', 0.905), ('0.35', 0.901), ('0.30', 0.890)):
            p = f'{W}/sc_{t}.json'; json.dump({'rows': rows(dice)}, open(p, 'w')); sc[t] = p
        sel = DC.select(sc)
        json.dump(sel, open(f'{W}/select.json', 'w'))
        tstar = round(float(json.load(open(f'{W}/select.json'))['chosen_t']), 2)
        ok3 = tstar == 0.40 and RT.dice_bound(f'{W}/select.json', tstar)
        report('S3 decide.py select -> rule_t.py', ok3, f"chosen_t={sel['chosen_t']!r} parsed as {tstar}; "
               f"dice_bound={RT.dice_bound(f'{W}/select.json', tstar)}")

        export(f'{W}/j0', f'{W}/j0_thr', [tstar, 0.50])
        # S2: the candidate exported on Rule W's grid only (as Job 0 does for Janus 0) is not enough for Rule T
        export(f'{W}/E', f'{W}/E_thr_wgrid', [0.5, 0.45, 0.4, 0.35, 0.3])
        try:
            RT.run(f'{W}/j0_thr', f'{W}/E_thr_wgrid', tstar, D60, 2)
            report('S2 Rule T needs its whole grid', False, 'rule_t ran without t0.60/t0.55/t0.25 (unexpected)')
        except Exception as e:  # noqa: BLE001
            report('S2 Rule T needs its whole grid', 'No such file' in repr(e) or 'FileNotFound' in repr(e),
                   'with Rule W\'s grid only, rule_t.py stops: ' + repr(e)[:90])

        # S4: width carried; E (P=0.5 at ~1.7 mm) is wider at 0.50 than Janus 0 at t*=0.40 (1.2 + 0.15 = 1.35 mm)
        res = RT.run(f'{W}/j0_thr', f'{W}/E_thr', tstar, D60, 2)
        shutil.rmtree(f'{W}/E_thr')
        for c in D60:   # a candidate exactly as thin as Janus 0
            write_member(f'{W}/same', c, tube_probs(1.2))
        export(f'{W}/same', f'{W}/same_thr', grid)
        res2 = RT.run(f'{W}/j0_thr', f'{W}/same_thr', tstar, D60, 2)
        report('S4 Rule T on E', res['t_C'] == 0.50 and res2['t_C'] == tstar,
               f"wider E -> t_C {res['t_C']} (dr {res['dr_mm']}); unchanged width -> t_C {res2['t_C']} (t* {tstar})")
        RES['S4 Rule T on E']['dr_wide'] = res['dr_mm']; RES['S4 Rule T on E']['dr_same'] = res2['dr_mm']
    finally:
        shutil.rmtree(W, ignore_errors=True)

    # S5: mutation test of gate.py's self-test
    src = open(os.path.join(HERE, 'gate.py')).read()
    mutants = {
        'Q-R2-3 removed': ("elif tf1['lo'] > -0.015 and dice_guard['hi'] >= 0:", "elif tf1['lo'] > -0.015:"),
        'Q4 bound -0.015 -> -0.02': ("elif tf1['lo'] > -0.015 and dice_guard", "elif tf1['lo'] > -0.02 and dice_guard"),
        'FP dropped from H1': ("if not fp <= 1.0:", "if False:"),
        'L3 -> G3 as written (plain mean >= -0.02)': ("return bool(tm < -0.02 or (mean < -0.02 and ub < 0))",
                                                      "return bool(mean < -0.02)"),
        'class guard dropped': ("if cls[c]['n'] and cls[c]['mean'] < -0.03]", "if False]"),
        'S alpha = C alpha': ("ALPHA = {'C': 0.025, 'S': 0.0125}", "ALPHA = {'C': 0.025, 'S': 0.025}"),
    }
    killed = {}
    with tempfile.TemporaryDirectory() as M:
        for name, (old, new) in mutants.items():
            assert src.count(old) == 1, name
            p = os.path.join(M, 'gate.py')
            open(p, 'w').write(src.replace(old, new))
            env = dict(os.environ, PYTHONPATH='')
            # run the mutant from the repo location's parents so ROOT resolves: copy into this directory's sibling
            tgt = os.path.join(HERE, '_mutant_gate.py')
            shutil.copy(p, tgt)
            try:
                r = subprocess.run([sys.executable, tgt, '--selftest'], capture_output=True, text=True, env=env)
            finally:
                os.remove(tgt)
            killed[name] = r.returncode != 0
    report('S5 gate self-test kills every mutant', all(killed.values()),
           ', '.join(f"{k}: {'killed' if v else 'SURVIVED'}" for k, v in killed.items()))
    RES['S5 gate self-test kills every mutant']['mutants'] = killed
    json.dump(RES, open(os.path.join(HERE, 'pipeline_check.json'), 'w'), indent=1, default=float)
    if not all(v['passed'] for v in RES.values()):
        sys.exit(1)


if __name__ == '__main__':
    main()
