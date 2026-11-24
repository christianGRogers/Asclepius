"""Delta, Janus 1-L round 3 (#302, Round 2 ruling §5 item 6): the merged scripts, chained end to end on synthetic
fixtures, to confirm each interface (arguments, input files, outputs) before round 3 writes the lead's commands.

No data: every volume and score here is synthetic. Case ids are borrowed from the committed lists only so that the
scripts' own id guards (tuning 60, D60, sealed) see valid names; nothing is read for them.

Chain checked:
  1. scorer-shaped JSONs (experiments/Atlas/r9_score_icx4.py rows) -> decide.py select -> select.json;
  2. the master plan's §5 line that reads t* from select.json (it uses '%.2f' % <str>, and select.json stores
     chosen_t as a string) against the corrected line;
  3. rule_t.dice_bound on that select.json (string keys '0.50' ...);
  4. threshold_export.py on nnU-Net-shaped npz/nii pairs with Rule T's whole grid -> t0.60 ... t0.25 folders,
     the names rule_t.py reads;
  5. rule_t.run on those folders (Janus 0 at t*, C on the grid);
  6. mde_from_job0.py on a scorer-shaped locked-100 rows file.
Usage: python chain_check.py            (writes chain_check.json beside itself)
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import nibabel as nib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CRU = os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1')
D2 = os.path.join(ROOT, 'experiments', 'Delta', 'j1l_r2')
sys.path.insert(0, D2)
import rule_t  # noqa: E402

CLASSES = ('LM', 'LAD', 'LCx', 'RCA')
PY = sys.executable


def rows(rng, n, tf1, dice, fp, rec):
    out = []
    for i in range(n):
        pc = {c: float(np.clip(tf1 + 0.05 * rng.standard_normal(), 0, 1)) for c in CLASSES}
        out.append(dict(case=f'c{i:04d}', provisional=False, flagged_classes=[], per_class=pc,
                        recall={c: rec for c in CLASSES}, fp_components=fp,
                        dice={'tree': float(dice + 0.01 * rng.standard_normal())}))
    return out


def tube_probs(shape, R, soft, centre):
    """5-class probabilities of a tube along x: vessel prob falls off across the rim with width `soft` (mm)."""
    z, y, x = np.indices(shape) * 0.5
    d = np.hypot(z - centre[0], y - centre[1])
    pv = 1 / (1 + np.exp((d - R) / soft))
    p = np.zeros((5,) + shape, np.float32)
    p[0] = 1 - pv; p[2] = pv * 0.9; p[3] = pv * 0.1          # LAD dominant
    return p


def main():
    out = {}
    rng = np.random.default_rng(0)
    with tempfile.TemporaryDirectory() as W:
        # 1. select
        spec = {'0.50': (0.90, 0.880, 0.4), '0.45': (0.90, 0.895, 0.42), '0.40': (0.899, 0.905, 0.45),
                '0.35': (0.897, 0.904, 0.48), '0.30': (0.893, 0.900, 0.6)}
        args = []
        for t, (tf, dc, fp) in spec.items():
            p = os.path.join(W, f'tuning60_t{t}.json')
            json.dump({'rows': rows(np.random.default_rng(1), 60, tf, dc, fp, 0.95)}, open(p, 'w'))
            args.append(f't{t}={p}')
        sel = os.path.join(W, 'select.json')
        s = subprocess.run([PY, os.path.join(CRU, 'decide.py'), 'select', '--scores'] + args, capture_output=True,
                           text=True, check=True).stdout
        open(sel, 'w').write(s)
        S = json.loads(s)
        out['1_select'] = dict(chosen_t=S['chosen_t'], chosen_t_type=type(S['chosen_t']).__name__,
                               keys=sorted(S['per_threshold']))
        # 2. the master plan's t* line, and the corrected one
        plan_line = f"""python -c "import json;print('%.2f' % json.load(open('{sel}'))['chosen_t'])" """
        fixed_line = f"""python -c "import json;print('%.2f' % float(json.load(open('{sel}'))['chosen_t']))" """
        r1 = subprocess.run(['bash', '-c', plan_line.replace('python', PY, 1)], capture_output=True, text=True)
        r2 = subprocess.run(['bash', '-c', fixed_line.replace('python', PY, 1)], capture_output=True, text=True)
        out['2_tstar_line'] = dict(
            master_plan_line=dict(returncode=r1.returncode, stdout=r1.stdout.strip(),
                                  stderr_last=r1.stderr.strip().splitlines()[-1] if r1.stderr else ''),
            corrected_line=dict(returncode=r2.returncode, stdout=r2.stdout.strip()),
            consequence="with T empty, `for t in 0.50 $T` runs once: the decomposition at t* is silently skipped")
        # 3. rule_t.dice_bound
        tstar = round(float(S['chosen_t']), 2)
        out['3_dice_bound'] = dict(t_star=tstar, dice_bound=rule_t.dice_bound(sel, tstar))
        # 4. threshold_export on nnU-Net-shaped files, Rule T's grid
        D60 = json.load(open(os.path.join(D2, 'drift60.json')))['drift60'][:2]
        shape = (24, 24, 40)
        aff = np.diag([0.5, 0.5, 0.5, 1.0])
        for model, R, soft in (('j0', 1.3, 0.35), ('C', 1.5, 0.25)):
            pd = os.path.join(W, f'probs_{model}'); os.makedirs(pd)
            for c in D60:
                p = tube_probs(shape, R, soft, (6.0, 6.0))
                seg = p.argmax(0).astype(np.uint8)                       # nibabel (x, y, z) order here
                np.savez_compressed(os.path.join(pd, c + '.npz'), probabilities=p.transpose(0, 3, 2, 1))
                nib.save(nib.Nifti1Image(seg, aff), os.path.join(pd, c + '.nii.gz'))
            ts = ['0.60', '0.55', '0.50', '0.45', '0.40', '0.35', '0.30', '0.25'] if model == 'C' else [f'{tstar:.2f}']
            subprocess.run([PY, os.path.join(CRU, 'threshold_export.py'), '--probs', pd, '--out',
                            os.path.join(W, f'd60_{model}'), '--np', '2', '--t'] + ts, check=True,
                           capture_output=True)
        made = sorted(d for d in os.listdir(os.path.join(W, 'd60_C')) if d.startswith('t'))
        need = [f't{t:.2f}' for t in rule_t.GRID]
        out['4_threshold_export'] = dict(folders=made, rule_t_needs=sorted(need), match=sorted(need) == made)
        # 5. rule_t.run
        res = rule_t.run(os.path.join(W, 'd60_j0'), os.path.join(W, 'd60_C'), tstar, D60, 2)
        out['5_rule_t'] = dict(t_C=res['t_C'], dr_mm=res['dr_mm'], n_cases=res['n_cases'])
        # 6. mde_from_job0
        lp = os.path.join(W, 'locked100_janus0_argmax.json')
        json.dump({'rows': rows(rng, 100, 0.90, 0.88, 0.4, 0.95)}, open(lp, 'w'))
        m = subprocess.run([PY, os.path.join(D2, 'mde_from_job0.py'), lp], capture_output=True, text=True, check=True)
        out['6_mde_from_job0'] = json.loads(m.stdout)['mde']['tf1, warm siblings']
    ok = (out['2_tstar_line']['master_plan_line']['returncode'] != 0 and
          out['2_tstar_line']['corrected_line']['stdout'] == f'{tstar:.2f}' and out['4_threshold_export']['match'])
    out['verdict'] = ('chain runs; one defect: the master plan §5 t* line fails on select.json\'s string chosen_t'
                      if ok else 'UNEXPECTED: see above')
    json.dump(out, open(os.path.join(HERE, 'chain_check.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
