"""Janus 1-F round 4 (Bridge): tests of the J1F-2 freeze script (`j1f2_freeze.py`). CPU, no pool read.

Part A  the script's own self-test (D47 Q4 and D54 labels, the scorer wrapper, refusals).
Part B  refusals on whole exports, before any read file is opened: every read directory below holds a corrupt
        read.json and corrupt masks, so opening one would crash the run.
          B1 a sealed pool patient's read -> exit 3;   B2 an --acceptance-scoring manifest -> exit 3;
          B3 a --four-class export -> exit 2;           B4 D35 and reserve reads are never opened (no --d35-tiers).
Part C  the freeze rules on synthetic rows (`freeze()` is a pure function of per-read rows): each number at, above
        and below its edge.
Part D  the two stand-in exports (make_standins.py, 620-derived), against truth measured independently (k-d trees):
          nominal: 3 mm, 0.02 and 30 mm stay; bands equal an independent percentile; counts and floors pass;
          stress:  long ostia raise the run, 38 mm gaps move L2d to 40 mm, a 45 % omission rate fails the floor.
Usage: python test_freeze.py <standins dir holding nominal/ and stress/> [np=4]
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import nibabel as nb
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1f2_freeze as F  # noqa: E402

FREEZE = os.path.join(HERE, 'j1f2_freeze.py')
RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append((name, bool(ok)))
    print(('ok   ' if ok else 'FAIL ') + name + (f'  [{detail}]' if detail else ''), flush=True)


def run(export, out, *extra):
    p = subprocess.run([sys.executable, FREEZE, '--export', export, '--out', out, '--np', '2', *extra],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def poison_export(root, names, source):
    os.makedirs(root, exist_ok=True)
    for n in names:
        d = os.path.join(root, n, 'segmentations')
        os.makedirs(d, exist_ok=True)
        open(os.path.join(root, n, 'read.json'), 'w').write('{not json')
        for c in ('LAD', 'S1'):
            open(os.path.join(d, c + '.nii.gz'), 'wb').write(b'not a nifti')
    json.dump({'version': 1, 'source': source, 'cases': []}, open(os.path.join(root, 'manifest.json'), 'w'))


def part_b():
    from segtrain import pool_seal
    seal = pool_seal.load_pool_seal()
    sealed = sorted(seal.patients)[0]
    d35 = json.load(open(F.D35_PATH))['patients'][0]
    from janusm import guard
    g = guard.load_guard()
    reserve = next(p for p in json.load(open(os.path.join(F.REPO, 'configs', 'segqueue14',
                                                           'sealed-pool-2026-10.json')))['primary']['extension_order']
                   if p not in set(json.load(open(F.D35_PATH))['patients']) and g.reason(p))
    ok_src = {'classes': 'read', 'replicas': 'all', 'pool_seal': {'mode': 'exclude'}}
    with tempfile.TemporaryDirectory() as t:
        e = os.path.join(t, 'b1')
        poison_export(e, [sealed, 'StandinA__p9000'], ok_src)
        rc, out = run(e, os.path.join(t, 'b1.json'))
        check('B1 a sealed pool patient in the export: refused, exit 3, nothing opened', rc == 3 and 'REFUSE' in out
              and 'JSONDecodeError' not in out, f'rc {rc}')
        e = os.path.join(t, 'b2')
        poison_export(e, ['StandinA__p9000'], dict(ok_src, pool_seal={'mode': 'acceptance'}))
        rc, out = run(e, os.path.join(t, 'b2.json'))
        check('B2 an --acceptance-scoring export: refused, exit 3', rc == 3, f'rc {rc}')
        e = os.path.join(t, 'b3')
        poison_export(e, ['StandinA__p9000'], dict(ok_src, classes='four'))
        rc, out = run(e, os.path.join(t, 'b3.json'))
        check('B3 a --four-class export: refused, exit 2', rc == 2, f'rc {rc}')
        e = os.path.join(t, 'b4')
        poison_export(e, [d35, d35 + '__r2', reserve], ok_src)
        rc, out = run(e, os.path.join(t, 'b4.json'))
        res = json.load(open(os.path.join(t, 'b4.json'))) if os.path.exists(os.path.join(t, 'b4.json')) else {}
        inp = res.get('inputs', {})
        check('B4 D35 and reserve reads are counted and never opened', 'JSONDecodeError' not in out
              and inp.get('d35_reads') == 2 and inp.get('held_out_reads') == 1 and inp.get('trainable_reads') == 0,
              f"rc {rc}, d35 {inp.get('d35_reads')}, held out {inp.get('held_out_reads')}")


def row(runs=(), cl=1000, gap=0.0, present=('S1',), band=None, ticks=False):
    rp = {g: [int(round(x / 0.5)) for x in runs] if g == 'LAD' else [] for g in F.GROUPS}
    return {'read': 'StandinA__p0000', 'extended': True, 'defect': False, 'ticks': ticks,
            'present': {F.S2NAMES[c]: (F.S2NAMES[c] in present) for c in F.BRANCHES2},
            'runs': {g: list(runs) if g == 'LAD' else [] for g in F.GROUPS}, 'run_pts': rp,
            'cl_pts': {g: cl for g in F.GROUPS}, 'gaps': [{'class': 'S1', 'gap_mm': gap}],
            'band': band or {}, 'far_mm': {}, 'no_branch_drawn': not present}


def hist_of(values):
    h = np.bincount(np.round(np.asarray(values) * 10).astype(int), minlength=1001)
    return {'n_vox': len(values), 'hist01': h.tolist()}


def part_c():
    # run length: 100 reads, runs up to 2.5 mm -> 3.0; one percent at 5.2 mm -> P99 decides
    rows = [row(runs=[2.0, 2.5]) for _ in range(100)]
    check('C1 short reader ostia keep L1r at 3 mm', F.freeze(rows, [])['l1r_run']['run_mm'] == 3.0)
    rows = [row(runs=[2.0]) for _ in range(90)] + [row(runs=[5.2]) for _ in range(10)]
    r = F.freeze(rows, [])['l1r_run']
    check('C2 10 % of reads with a 5.2 mm ostium: L1r run rises to 5.5 mm', r['run_mm'] == 5.5, r)
    rows = [row(runs=[9.0]) for _ in range(100)]
    res = F.freeze(rows, [])
    check('C3 9 mm reader ostia: STOP (the PM decides)', any('L1r run' in s for s in res['stop']), res['stop'])
    # theft: readers' runs above the run length, as a share of the centreline
    rows = [row(runs=[2.0], cl=1000) for _ in range(100)]
    check('C4 no reader theft: the line stays 0.02', F.freeze(rows, [])['theft']['line'] == 0.02)
    rows = [row(runs=[2.0] * 99 + [6.0] * 1, cl=200) for _ in range(100)]     # runs of 6 mm = 12 pts of 200 = 6 %
    res = F.freeze(rows, [])
    check('C5 reader theft above 2.5 %: line > 0.05 -> STOP', any('theft line' in s for s in res['stop']),
          res['theft'])
    # gap: 3 % of reads with a 32 mm gap -> 35 mm; 1 % -> 30 mm
    rows = [row(gap=1.0) for _ in range(97)] + [row(gap=32.0) for _ in range(3)]
    g = F.freeze(rows, [])['l2d_gap']
    check('C6 3 % of reads with a 32 mm gap: L2d moves to 35 mm', g['gap_mm'] == 35.0, g['gap_mm'])
    rows = [row(gap=1.0) for _ in range(99)] + [row(gap=32.0)]
    check('C7 1 % of reads with a 32 mm gap: L2d stays at 30 mm', F.freeze(rows, [])['l2d_gap']['gap_mm'] == 30.0)
    rows = [row(gap=float('inf')) for _ in range(10)] + [row() for _ in range(90)]
    check('C8 10 % of reads with an island > 60 mm: STOP', any('L2d' in s for s in F.freeze(rows, [])['stop']))
    # band: P95 of the pooled drawn distances, rounded up to 0.5 mm, clamped to [8, 25], >= 10 reads
    rng = np.random.default_rng(0)
    rows = [row(band={'LAD': hist_of(rng.uniform(0, 20, 400))}) for _ in range(12)]
    b = F.freeze(rows, [])['band']['LAD']
    check('C9 drawn distances U(0, 20 mm): band 19.0 mm', b['width_mm'] == 19.0, b)
    rows = [row(band={'LAD': hist_of(rng.uniform(0, 40, 400))}) for _ in range(12)]
    check('C10 band clamped at 25 mm', F.freeze(rows, [])['band']['LAD']['width_mm'] == 25.0)
    rows = [row(band={'LAD': hist_of(rng.uniform(0, 5, 400))}) for _ in range(12)]
    check('C11 band clamped at 8 mm', F.freeze(rows, [])['band']['LAD']['width_mm'] == 8.0)
    rows = [row(band={'LAD': hist_of(rng.uniform(0, 20, 400))}) for _ in range(9)]
    check('C12 nine reads: the band keeps 15 mm', F.freeze(rows, [])['band']['LAD']['width_mm'] == 15.0)
    # counts: 30 patients from 3 sources of >= 5; 29 fails; 2 sources fail; the 1.5x rule
    def rows_for(n, sources):
        out = []
        for i in range(n):
            r = row()
            r['read'] = f'Standin{sources[i % len(sources)]}__p{i:04d}'
            out.append(r)
        return out
    pair = {'classes': {k: {'pieces': 2, 'detected': 2, 'named': 2, 'present': [True, True]}
                        for k in F.S2NAMES[5:]}}
    pairs = [pair] * 10
    c = F.freeze(rows_for(30, 'ABC'), pairs)['classes']['S1']
    check('C13 30 patients, 3 sources of 10, 10 pairs at floor 1.0: S1 trainable', c['trainable'] is True, c)
    c = F.freeze(rows_for(29, 'ABC'), pairs)['classes']['S1']
    check('C14 29 patients: not trainable', c['trainable'] is False)
    c = F.freeze(rows_for(30, 'AB'), pairs)['classes']['S1']
    check('C15 two sources: not trainable', c['trainable'] is False)
    c = F.freeze(rows_for(40, 'ABC'), pairs, raised={'S1'})['classes']['S1']
    check('C16 after a near miss (F-A23, 1.5x): 40 patients fail, 45 are needed; 45 pass',
          c['trainable'] is False and c['need_patients'] == 45 and c['need_pairs'] == 10
          and F.freeze(rows_for(45, 'ABC'), pairs, raised={'S1'})['classes']['S1']['trainable'] is True, c)
    # floor: symmetric pooling counts a reader's omission (D54: absent is a label)
    half = {'classes': {k: {'pieces': 2, 'detected': 1, 'named': 1, 'present': [True, False]}
                        for k in F.S2NAMES[5:]}}
    c = F.freeze(rows_for(30, 'ABC'), [half] * 10)['classes']['S1']
    check('C17 one reader omits the class in every pair: floor 0.5, not trainable',
          c['floor_det_x_naming'] == 0.5 and c['trainable'] is False and c['presence_agreement_pairs'] == 0.0, c)
    # D54 report: stage-1 classes drawn far less often than in ImageCAS-X are flagged; ticks are only counted
    rows = [row(present=('S1',), ticks=(i % 2 == 0)) for i in range(50)]
    res = F.freeze(rows, [])
    check('C18 D1 never drawn in 50 extended reads: flagged under-drawn (D54 report)',
          res['d54']['stage1_drawn_vs_icx620']['D1']['flag_under_drawn'] is True
          and res['d54']['reads_with_old_ticks'] == 25)
    rows_t = [row(present=('S1', 'D1'), ticks=True) for _ in range(20)]
    rows_n = [row(present=('S1', 'D1'), ticks=False) for _ in range(20)]
    a, b = F.freeze(rows_t, []), F.freeze(rows_n, [])
    for x in (a, b):
        x['d54'].pop('reads_with_old_ticks')
    check('C19 ticks change no number (D54)', json.dumps(a, sort_keys=True, default=str)
          == json.dumps(b, sort_keys=True, default=str))


def truth_band(export, read, gname):
    """Independent band truth: k-d-tree distance of each drawn voxel from the host channels (whole hosts only)."""
    gd = F.BAND_GROUPS[gname]
    d = os.path.join(export, read, 'segmentations')
    z = np.array(nb.load(os.path.join(d, 'LAD.nii.gz')).header.get_zooms()[:3], float)
    host = sum(np.asarray(nb.load(os.path.join(d, h + '.nii.gz')).dataobj) for h in gd['host']) > 0
    ch = {n: np.asarray(nb.load(os.path.join(d, n.replace(' ', '_') + '.nii.gz')).dataobj) > 0
          for n in F.VESSELS + tuple(F.PARENTS)}
    lab = F.labels_d54(ch)
    drawn = np.zeros(host.shape, bool)
    for c in gd['classes']:
        drawn |= lab == F.V[c]
    if not drawn.any():
        return []
    return cKDTree(np.argwhere(host) * z).query(np.argwhere(drawn) * z)[0].tolist()


def part_d(root, npr):
    out = {}
    for scen in ('nominal', 'stress'):
        e = os.path.join(root, scen)
        fj = os.path.join(root, f'freeze_{scen}.json')
        p = subprocess.run([sys.executable, FREEZE, '--export', e, '--out', fj, '--np', str(npr)],
                           capture_output=True, text=True)
        print(p.stdout[-3000:], p.stderr[-2000:], flush=True)
        res = json.load(open(fj))
        truth = json.load(open(os.path.join(root, f'{scen}_truth.json')))
        rows = {json.loads(x)['read']: json.loads(x) for x in open(os.path.splitext(fj)[0] + '_rows.jsonl')}
        out[scen] = (res, truth, rows, e, p.returncode)
    res, truth, rows, e, rc = out['nominal']
    check('D1 nominal: exit 0, no STOP', rc == 0 and not res['stop'], res['stop'])
    check('D2 nominal: the defect read is left out', res['n_reads'] == len(truth['reads']) - 1, res['n_reads'])
    check('D3 nominal: L1r stays 3 mm (reader ostia <= 2.5 mm)', res['l1r_run']['run_mm'] == 3.0, res['l1r_run'])
    check('D4 nominal: the theft line stays 0.02', res['theft']['line'] == 0.02, res['theft'])
    check('D5 nominal: L2d stays 30 mm (gaps <= 10 mm in 3 % of tubes)', res['l2d_gap']['gap_mm'] == 30.0,
          res['l2d_gap']['by_step']['30.0'])
    # gaps: freeze (EDT) vs truth (k-d tree), per read, the largest gap
    diffs = []
    for rn, t in truth['reads'].items():
        if t['defect']:
            continue
        tg = max([g for c in t['far'].values() for g in c['gaps']], default=0.0)
        fg = max([x['gap_mm'] for x in rows[rn]['gaps']], default=0.0)
        diffs.append(abs(tg - fg))
    check('D6 nominal: every read\'s largest gap equals the k-d-tree truth within 0.05 mm', max(diffs) <= 0.05,
          f'max diff {max(diffs):.4f} mm over {len(diffs)} reads')
    # band: freeze's pooled P95 (0.1 mm histogram) vs the k-d-tree pooled P95, for the whole-host groups
    for g in ('LAD', 'RCA'):
        vals = [x for rn, t in truth['reads'].items() if not t['defect'] for x in truth_band(e, rn, g)]
        p95 = float(np.percentile(vals, 95))
        fb = res['band'][g]
        exp = min(max(F.ceil_to(p95, 0.5), 8.0), 25.0)
        check(f'D7 nominal: band {g} = clamp(ceil_0.5(P95)) of the k-d-tree distances',
              fb['width_mm'] == exp and abs(fb['p95_pooled_mm'] - p95) <= 0.1,
              f"freeze {fb['width_mm']} (P95 {fb['p95_pooled_mm']}), truth P95 {p95:.2f} -> {exp}")
    # counts: a patient has the class if any non-defect read drew it (>= 5 mm by the scorer)
    for k in F.STAGE2_NAMES:
        tp = {t['case'] for rn, t in truth['reads'].items() if not t['defect']
              and any(x['class'] == k and not x['omitted'] and x.get('L_drawn', 0) >= 5 for x in t['tubes'])}
        fc = res['classes'][k]
        check(f'D8 nominal: {k} patient count equals truth', fc['patients'] == len(tp),
              f"freeze {fc['patients']}, truth {len(tp)}, floor {fc['floor_det_x_naming']}, "
              f"trainable {fc['trainable']}")
    check('D9 nominal: every stage-2 class with >= 30 patients passes its floor',
          all(c['floor_det_x_naming'] >= 0.6 for c in res['classes'].values() if c['stage'] == 2
              and c['pairs_with_class'] >= 10))
    res, truth, rows, e, rc = out['stress']
    ovs = [x['ov'] for t in truth['reads'].values() if not t['defect'] for x in t['tubes'] if not x['omitted']]
    check('D10 stress: reader ostia of 3.5-5.5 mm raise L1r above 3 mm and no further than 6.5 mm',
          3.0 < res['l1r_run']['run_mm'] <= 6.5, f"{res['l1r_run']} (ov max {max(ovs):.2f})")
    check('D11 stress: 38 mm gaps in ~8 % of tubes move L2d to 40 mm', res['l2d_gap']['gap_mm'] == 40.0,
          {k: v['rate'] for k, v in res['l2d_gap']['by_step'].items()})
    check('D12 stress: a 45 % omission rate in second reads fails every stage-2 floor',
          all(c['floor_det_x_naming'] is not None and c['floor_det_x_naming'] < 0.6 and c['trainable'] is False
              for c in res['classes'].values() if c['stage'] == 2),
          {k: c['floor_det_x_naming'] for k, c in res['classes'].items() if c['stage'] == 2})
    json.dump({s: v[0] for s, v in out.items()}, open(os.path.join(HERE, 'standin_freeze_summary.json'), 'w'),
              indent=1, sort_keys=True, default=str)


if __name__ == '__main__':
    root = sys.argv[1]
    npr = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    print('Part A'); F.selftest()
    print('Part B'); part_b()
    print('Part C'); part_c()
    print('Part D'); part_d(root, npr)
    bad = [n for n, ok in RESULTS if not ok]
    print(f'{len(RESULTS) - len(bad)} of {len(RESULTS)} checks pass')
    print('ALL PASS' if not bad else 'FAILED: ' + '; '.join(bad))
