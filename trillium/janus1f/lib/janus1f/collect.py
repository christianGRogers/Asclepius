"""`collect` (CPU job): J1F-A's one look on the locked 100 (master plan §3; Delta v3 §3.4; F-A27 to F-A35).

  python -m janus1f.collect gate   <work>     # login node: may collect start now? (D55 Q-F3-1's 14-day wait)
  python -m janus1f.collect run    <work> <janus0> <icx_dir> <aorta_dir> <layout.json> <n_proc>

In this order:
  0. the four pins (F-A36); the split; every locked case has a1's decoded maps with their marker, and Janus 0's Fir
     prediction (a missing one refuses: never re-predicted); 1-L's maps when F-A32 applies;
  1. the look is opened in results/looks.json BEFORE anything is scored; a second run refuses (F-A22);
  2. T (and T_L) rebuilt from G and the four-class map, checked byte for byte (F-A31);
  3. V on F: F collapsed by the scorer's `collapse4`, scored with the A1c scorer (r9_score_icx4.py, icx4's aortas),
     paired with Janus 0's Fir predictions, one-sided 2.5 % (V = 1-L's H1);
  4. B on F and on T (and T_L): the scorer of record's `score_case` per case (references by its `stage1_labels`:
     the locked labels are read here and nowhere else), `aggregate`, `gate` with configs/janus1/j1f_gates.json;
  5. the verdict table (F-A6, F-A32), DECISION.md, verdict.json; reports: contact fallbacks, D3 and Ramus with n
     and CI, a2, V_L / T_L when they are reports.

Environment (the lead's; D55): J1F_Q_F2_3 (default "yes", D55), J1F_JANUS1L_ADOPTED=1 and J1F_JANUS1L_MAPS=<dir>
(1-L adopted, its 100 maps on Fir), J1F_JANUS1L_COLLECT_SUBMITTED=1 (1-L's collect was submitted when a1's predict
ended: allows the wait).
"""
import datetime
import json
import math
import os
import subprocess
import sys

import numpy as np

from . import decode, ledger, pins, split, verdict as V

WAIT_DAYS = 14


class CollectError(RuntimeError):
    pass


def dirs(work):
    return {'maps_a1': os.path.join(work, 'maps_a1'), 'maps_a2': os.path.join(work, 'maps_a2'),
            'results': os.path.join(work, 'results'), 'tmp': os.path.join(work, 'collect_tmp'),
            'looks': os.path.join(work, 'results', 'looks.json'),
            'predict_done_a1': os.path.join(work, '.predict_done_a1'), 'wait': os.path.join(work, 'collect_wait.json')}


def env_state(env=None):
    env = os.environ if env is None else env
    q3 = env.get('J1F_Q_F2_3', 'yes')
    if q3 not in ('yes', 'no'):
        raise CollectError(f'J1F_Q_F2_3 must be yes or no, not {q3!r}')
    adopted = env.get('J1F_JANUS1L_ADOPTED') == '1'
    maps = env.get('J1F_JANUS1L_MAPS') or None
    if adopted and not maps:
        raise CollectError('J1F_JANUS1L_ADOPTED=1 needs J1F_JANUS1L_MAPS (its 100 locked maps on Fir)')
    return {'q3': q3, 'l_adopted': adopted, 'l_maps': maps,
            'l_collect_submitted': env.get('J1F_JANUS1L_COLLECT_SUBMITTED') == '1'}


def wait_gate(work, st, now=None):
    """D55 Q-F3-1. Returns ('go', why) or ('wait', why). Waiting is allowed only when Q-F2-3 is yes, 1-L is not yet
    adopted, and 1-L's collect was submitted when a1's predict ended; it lasts at most 14 days from that moment."""
    d = dirs(work)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if st['q3'] != 'yes':
        return 'go', 'Q-F2-3 is no: F-A32 is void; V_L and T_L are reports'
    if st['l_adopted']:
        return 'go', 'Janus 1-L adopted with its maps on Fir: F-A32 applies'
    if not os.path.exists(d['predict_done_a1']):
        raise CollectError("a1's predict has not finished (no .predict_done_a1); collect cannot start")
    if os.path.exists(d['wait']):
        w = pins.load_json(d['wait'])
    else:
        ended = datetime.datetime.fromtimestamp(os.path.getmtime(d['predict_done_a1']), datetime.timezone.utc)
        w = {'a1_predict_ended': ended.strftime('%Y-%m-%dT%H:%M:%SZ'),
             'janus1l_collect_submitted_then': st['l_collect_submitted']}
        with open(d['wait'], 'w') as f:
            json.dump(w, f, indent=1)
    if not w['janus1l_collect_submitted_then']:
        return 'go', "1-L's collect was not submitted when a1's predict ended: no wait (D55 Q-F3-1); T_L is a report"
    ended = datetime.datetime.strptime(w['a1_predict_ended'], '%Y-%m-%dT%H:%M:%SZ').replace(
        tzinfo=datetime.timezone.utc)
    until = ended + datetime.timedelta(days=WAIT_DAYS)
    if now < until:
        return 'wait', (f"waiting for Janus 1-L's verdict until {until:%Y-%m-%d %H:%M} UTC (D55 Q-F3-1); set "
                        'J1F_JANUS1L_ADOPTED=1 J1F_JANUS1L_MAPS=<dir> once it is adopted, or re-run after that date')
    return 'go', f'{WAIT_DAYS} days passed without a Janus 1-L verdict: collect runs; T_L is a report (D55 Q-F3-1)'


# ---------------------------------------------------------------------------- inputs
def check_inputs(work, janus0, sp, st):
    d = dirs(work)
    locked = sp['locked100']
    maps = decode.collect_inputs(d['maps_a1'], locked)
    miss = [c for c in locked if not os.path.exists(os.path.join(janus0, 'pred_fir', c + '.nii.gz'))]
    if miss:
        raise CollectError(f"refusing: no Janus 0 Fir prediction for {len(miss)} locked case(s), e.g. {miss[:3]}")
    l_maps = None
    if st['l_maps']:
        l_maps = {c: os.path.join(st['l_maps'], c + '.nii.gz') for c in locked}
        lm = [c for c, p in l_maps.items() if not os.path.exists(p)]
        if lm:
            raise CollectError(f'J1F_JANUS1L_MAPS lacks {len(lm)} locked map(s), e.g. {lm[:3]}; refusing')
    a2 = None
    if os.path.isdir(d['maps_a2']):
        try:
            a2 = decode.collect_inputs(d['maps_a2'], locked)
        except decode.DecodeError as e:
            print(f'[janus1f] a2 report skipped: {e}', flush=True)
    return maps, l_maps, a2


# ---------------------------------------------------------------------------- per case
def _load(p):
    import nibabel as nib
    im = nib.load(p)
    return np.asarray(im.dataobj).astype(np.uint8), im


def _case(args):
    """One locked case: rebuild T (and T_L), write F's four-class map, score F, T (and T_L) on B."""
    c, paths, j0_path, l_path, icx_dir, tmp, a2_paths = args
    import nibabel as nib
    sys.path.insert(0, pins.LIB)
    import j1f_scorer as S
    F, imF = _load(paths['F'])
    T, _ = _load(paths['T'])
    G = {2: _load(paths['G2'])[0], 3: _load(paths['G3'])[0], 4: _load(paths['G4'])[0]}
    j0, _ = _load(j0_path)
    if j0.shape != F.shape:
        raise CollectError(f"{c}: Janus 0's map {j0.shape} is not on F's grid {F.shape}")
    decode.check_t(T, j0, G)
    li = nib.load(os.path.join(icx_dir, f'{int(c[1:]) + 1}.coronary.nii.gz'))
    icx = np.asarray(li.dataobj).astype(np.uint8)
    z = np.array(li.header.get_zooms()[:3], float)
    if icx.shape != F.shape:
        raise CollectError(f'{c}: ImageCAS-X label {icx.shape} is not on F\'s grid {F.shape}')
    ref, _ = S.stage1_labels(icx, z)
    rp = S.pieces_of(ref, z)
    out = {'case': c}
    stF, stT = {}, {}
    F4 = S.collapse4(F, z, stF)
    S.collapse4(T, z, stT)
    nib.save(nib.Nifti1Image(F4, imF.affine, imF.header), os.path.join(tmp, 'F4', c + '.nii.gz'))
    out['B_F'] = S.score_case(ref, F, z, True, rp)
    out['B_T'] = S.score_case(ref, T, z, True, rp)
    out['fallback'] = {'F': stF.get('fallback', 0), 'T': stT.get('fallback', 0)}
    if l_path:
        jl, _ = _load(l_path)
        if jl.shape != F.shape:
            raise CollectError(f"{c}: Janus 1-L's map {jl.shape} is not on Janus 0's grid {F.shape}")
        TL = decode.decode_t(jl, G)
        stL = {}
        S.collapse4(TL, z, stL)
        out['B_TL'] = S.score_case(ref, TL, z, True, rp)
        out['fallback']['T_L'] = stL.get('fallback', 0)
    if a2_paths:
        F2, im2 = _load(a2_paths['F'])
        st2 = {}
        F24 = S.collapse4(F2, z, st2)
        nib.save(nib.Nifti1Image(F24, im2.affine, im2.header), os.path.join(tmp, 'F4_a2', c + '.nii.gz'))
        out['B_F_a2'] = S.score_case(ref, F2, z, True, rp)
    return out


def wilson(k, n, z=1.959964):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def report_classes(rows, key):
    """D3 and Ramus (report only): pieces, detected, named, with Wilson 95 % CIs."""
    out = {}
    for k in ('D3', 'Ramus'):
        pcs = [p for r in rows for p in r[key][k]['pieces']]
        n, det = len(pcs), sum(p['detected'] for p in pcs)
        nam = sum(p['named'] for p in pcs)
        out[k] = {'pieces': n, 'detected': det, 'named': nam, 'recall_ci95': wilson(det, n),
                  'naming_ci95': wilson(nam, det)}
    return out


def r9(pred, icx_dir, aorta_dir, layout, splits, out, n_proc):
    cmd = [sys.executable, os.path.join(pins.ROOT, 'experiments', 'Atlas', 'r9_score_icx4.py'), '--pred', pred,
           '--icx', icx_dir, '--aorta', aorta_dir, '--layout', layout, '--splits', splits, '--set', 'val',
           '--np', str(n_proc), '--out', out]
    print('[janus1f] +', ' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True)
    return pins.load_json(out)['rows']


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if hasattr(o, 'numerator') and hasattr(o, 'denominator') and not isinstance(o, (int, bool)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    return o


def run(work, janus0, icx_dir, aorta_dir, layout, n_proc, env=None):
    from multiprocessing import Pool
    sys.path.insert(0, pins.LIB)
    st = env_state(env)
    pin_lines = pins.check_four()
    import j1f_scorer as S
    if S.scorer_sha256() != pins.SCORER_SHA256:
        raise pins.PinError('the imported scorer is not the scorer of record')
    gates = S.load_gates(pins.GATES)
    sp = split.load()
    maps, l_maps, a2 = check_inputs(work, janus0, sp, st)
    fa32 = st['q3'] == 'yes' and st['l_adopted']
    d = dirs(work)
    os.makedirs(d['results'], exist_ok=True)
    # 1. the look, before any score
    look = ledger.open_look(d['looks'], 'J1F-A', ['F', 'T'] + (['T_L'] if fa32 else []), fa32, st['q3'])
    print(f'[janus1f] look opened: {look}', flush=True)
    for sub in ('F4', 'F4_a2'):
        os.makedirs(os.path.join(d['tmp'], sub), exist_ok=True)
    locked = sp['locked100']
    jobs = [(c, maps[c], os.path.join(janus0, 'pred_fir', c + '.nii.gz'), l_maps[c] if l_maps else None,
             icx_dir, d['tmp'], a2[c] if a2 else None) for c in locked]
    with Pool(n_proc) as pool:
        rows = sorted(pool.map(_case, jobs), key=lambda r: r['case'])
    # 3. V on F against Janus 0 (A1c scorer, icx4's aortas)
    splits = os.path.join(d['tmp'], 'split_locked100.json')
    with open(splits, 'w') as f:
        json.dump({'val': locked}, f)
    base = r9(os.path.join(janus0, 'pred_fir'), icx_dir, aorta_dir, layout, splits,
              os.path.join(d['tmp'], 'r9_janus0.json'), n_proc)
    candF = r9(os.path.join(d['tmp'], 'F4'), icx_dir, aorta_dir, layout, splits,
               os.path.join(d['tmp'], 'r9_F.json'), n_proc)
    vF = V.v_gate(base, candF, expect_cases=locked)
    # 4. B
    agg = {k: S.aggregate([r[k] for r in rows]) for k in ('B_F', 'B_T') + (('B_TL',) if l_maps else ())}
    B = {k: S.gate(a, gates) for k, a in agg.items()}
    vL = None
    if l_maps:
        l_rows = r9(st['l_maps'], icx_dir, aorta_dir, layout, splits, os.path.join(d['tmp'], 'r9_janus1l.json'),
                    n_proc)
        vL = V.v_gate(l_rows, candF, expect_cases=locked)
    ship = V.verdict(vF['passed'], B['B_F']['verdict_pass'], B['B_T']['verdict_pass'], fa32,
                     (vL['passed'] if (fa32 and vL) else None),
                     (B['B_TL']['verdict_pass'] if (fa32 and 'B_TL' in B) else None), st['q3'])
    reports = {'fallbacks': {k: sum(r['fallback'].get(k, 0) for r in rows) for k in ('F', 'T', 'T_L')},
               'D3_Ramus_F': report_classes(rows, 'B_F'), 'D3_Ramus_T': report_classes(rows, 'B_T')}
    if l_maps and not fa32:
        reports['V_L_report'] = vL
        reports['B_T_L_report'] = B.get('B_TL')
    if a2:
        cand2 = r9(os.path.join(d['tmp'], 'F4_a2'), icx_dir, aorta_dir, layout, splits,
                   os.path.join(d['tmp'], 'r9_F_a2.json'), n_proc)
        reports['a2'] = {'V': V.v_gate(base, cand2, expect_cases=locked),
                         'B': S.gate(S.aggregate([r['B_F_a2'] for r in rows]), gates)}
    res = {'look': look, 'pins': pin_lines, 'ships': ship, 'wording': V.wording(ship, vF['passed'],
                                                                                 vL['passed'] if vL else None),
           'V_F': vF, 'V_L': vL if fa32 else None, 'B': B, 'aggregates': agg, 'reports': reports,
           'fa32_applies': fa32, 'q_f2_3': st['q3']}
    with open(os.path.join(d['results'], 'verdict.json'), 'w') as f:
        json.dump(_jsonable(res), f, indent=1)
    with open(os.path.join(d['results'], 'DECISION.md'), 'w') as f:
        f.write(decision_md(res))
    print(f'[janus1f] verdict: {ship}. results/DECISION.md, results/verdict.json, results/looks.json written',
          flush=True)
    return res


def decision_md(res):
    vF, B = res['V_F'], res['B']
    L = ['# J1F-A: the decision on the locked 100', '',
         f"**Ships: {res['ships']}.** {res['wording']}.", '',
         f"Look {res['look']['look']} ({res['look']['candidate']}), readings {', '.join(res['look']['readings'])}, "
         f"opened {res['look']['opened']}. F-A32 {'applies' if res['fa32_applies'] else 'does not apply'} "
         f"(Q-F2-3 {res['q_f2_3']}).", '',
         '## V, the vessels (F against Janus 0; one-sided 2.5 %)', '',
         f"- lower bound of delta decisive macro tF1 {vF['tf1']['lb']} (line > -0.02): "
         f"{'pass' if vF['parts']['macro'] else 'FAIL'}; mean {vF['tf1']['mean']}, 95 % CI {vF['tf1']['ci95']}",
         f"- no class mean delta below -0.03: {'pass' if vF['parts']['classes'] else 'FAIL'}",
         f"- L3: {'pass' if vF['parts']['L3'] else 'FAIL'}",
         f"- FP components per case {vF['fp_per_case']} (line <= 1): {'pass' if vF['parts']['fp'] else 'FAIL'}",
         f"- **V {'passes' if vF['passed'] else 'fails'}**", '',
         '## B, the six gated classes (F-A27 lines; >= 4 of 6)', '']
    for k, g in B.items():
        L.append(f"### {k[2:]}: {g['n_pass']} of 6 pass, **{'pass' if g['verdict_pass'] else 'fail'}**")
        L.append('')
        L.append('| Class | recall | presence agreement | naming | pass |')
        L.append('|---|---|---|---|---|')
        for c, r in g['classes'].items():
            fmt = lambda x: 'n/a' if x is None else f'{x:.3f}'  # noqa: E731
            L.append(f"| {c} | {fmt(r['recall'])} | {fmt(r['presence'])} | {fmt(r['naming'])} | "
                     f"{'yes' if r['pass'] else 'no'} |")
        L.append('')
    L += ['B1 detection, read as written (F-A35): a reference piece is detected when >= 50 % of its centreline lies '
          'within 1.5 mm of predicted vessel, so a branch drawn for its proximal ~45 % can count as detected.', '',
          '## Reports (never deciding)', '', '```json', json.dumps(_jsonable(res['reports']), indent=1), '```', '',
          'Pins: ' + '; '.join(res['pins']), '']
    return '\n'.join(L)


def main(argv):
    if argv[:1] == ['gate']:
        state, why = wait_gate(argv[1], env_state())
        print(f'[janus1f] collect: {state}: {why}')
        return 0 if state == 'go' else 4
    if argv[:1] == ['run']:
        run(argv[1], argv[2], argv[3], argv[4], argv[5], int(argv[6]))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except (CollectError, ledger.LedgerError, decode.DecodeError, pins.PinError, split.SplitError) as e:
        sys.exit(f'[janus1f] {e}')
