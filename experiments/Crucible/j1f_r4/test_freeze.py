"""Tests of j1f2_freeze.py (Crucible, j1f round 4). No data: synthetic arrays and tiny fake export trees only.
Each refusal is tested on a tree that should refuse AND on its twin that should pass, so a test cannot pass by
refusing everything. Usage: python test_freeze.py  (prints one line per check, then ALL PASS or exits 1)."""
import io, json, os, shutil, sys, tempfile, contextlib
import numpy as np, nibabel as nb

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1f2_freeze as F  # noqa
from segtrain import pool_seal  # noqa

FAIL = []


def check(name, ok):
    print(('PASS ' if ok else 'FAIL ') + name)
    if not ok:
        FAIL.append(name)


Z = np.array([0.5, 0.5, 0.5])


def tube(shape, p0, u, L, r):
    g = np.stack(np.meshgrid(*[np.arange(s) * 0.5 for s in shape], indexing='ij'), -1)
    u = np.asarray(u, float) / np.linalg.norm(u); v = g - np.asarray(p0, float); t = v @ u
    return (np.linalg.norm(v - np.clip(t, 0, L)[..., None] * u, axis=-1) <= r) & (t >= 0) & (t <= L)


def toy(septal_len=20.0, gap=None, thief=0.0, shape=(40, 140, 140)):
    """An LAD along y with one septal off it (child over parent: it starts on the LAD's axis), an RCA elsewhere."""
    lad = tube(shape, (10, 2, 10), (0, 1, 0), 65, 1.5)
    s1 = tube(shape, (10, 30, 10), (0, 0, 1), septal_len, 0.7)
    if gap:
        s1 &= ~tube(shape, (10, 30, 10 + septal_len / 2), (0, 0, 1), gap, 1.5)
    if thief:
        s1 |= tube(shape, (10, 30, 10), (0, 1, 0), thief, 1.5)
    rca = tube(shape, (10, 2, 62), (0, 1, 0), 60, 1.5)
    return {'LAD': lad, 'S1': s1, 'RCA': rca, 'LM': np.zeros(shape, bool), 'LCx': np.zeros(shape, bool)}


# ------------------------------------------------------------------ D54 label rule
m = toy()
t = F.d54_target(m)
check('d54: a septal over its own parent (LAD) is the septal (D47 Q4)', bool((t[m['S1'] & m['LAD']] == F.VALUE['S1']).all()))
check('d54: LAD voxels outside the septal are LAD singletons (no {parent+children} set: confirmed absent)',
      bool((t[m['LAD'] & ~m['S1']] == F.VALUE['LAD']).all()))
check('d54: background stays background (no band set in an extended read)', bool((t[~(m['LAD'] | m['S1'] | m['RCA'])] == 0).all()))
m2 = dict(m); m2['D1'] = m['S1'].copy()
t2 = F.d54_target(m2)
check('d54: two branches on one voxel (S1 and D1 over LAD) are IGNORE', bool((t2[m['S1'] & m['LAD']] == F.IGNORE).all()))
m3 = dict(m); m3['Calcified plaque'] = np.zeros_like(m['LAD']); m3['Calcified plaque'][20, 60:70, 15:25] = True
_, _, = None, None
keep = {k: v for k, v in m3.items() if k in F.VESSELS + F.BRANCHES}
t3 = F.d54_target(keep)
check('d54: materials are dropped before the rule (a vessel voxel marked plaque stays vessel)',
      bool((t3[m3['Calcified plaque'] & m['LAD'] & ~m['S1']] == F.VALUE['LAD']).all()))
check('d54: a material-only voxel is background', bool((t3[m3['Calcified plaque'] & ~m['LAD'] & ~m['S1']] == 0).all()))
# PDA off the LCx overlapping the LCx -> PDA
sh = (30, 80, 60)
lcx = tube(sh, (10, 2, 10), (0, 1, 0), 30, 1.5); pda = tube(sh, (10, 30, 10), (0, 0, 1), 20, 0.8)
rca = tube(sh, (20, 2, 50), (0, 1, 0), 30, 1.5)
t4 = F.d54_target({'LCx': lcx, 'PDA': pda, 'RCA': rca})
check('d54: a PDA leaving the LCx, over the LCx, is the PDA (contact parent, D47 Q1)', bool((t4[pda & lcx] == F.VALUE['PDA']).all()))
# read kinds
check('kind: four-class read', F.read_kind({'extended': False}, {'LAD': m['LAD']}) == 'four')
check('kind: extended with a branch drawn', F.read_kind({'extended': True}, m) == 'branch')
nob = {k: m[k] for k in ('LM', 'LAD', 'LCx', 'RCA')}; nob['S1'] = np.zeros_like(m['S1']); nob['Calcified plaque'] = m3['Calcified plaque']
check('kind: extended, plaque only, no branch drawn -> nobranch', F.read_kind({'extended': True}, nob) == 'nobranch')

# ------------------------------------------------------------------ per-read geometry
r = F.measure_read(toy(20.0), Z)
check(f"measure: septal length ~ 20 mm minus the LAD radius ({r['length_mm']['S1']})", 15 <= r['length_mm']['S1'] <= 21)
check(f"measure: the LAD band p95 sits near the septal's far end ({r['band']['LAD'][95]} mm)", 15 <= r['band']['LAD'][95] <= 20.5)
runs = r['runs']['LAD']
check(f'measure: a correct child-over-parent ostium paints a run < 3 mm over the LAD centreline ({runs})', all(x < 3 for x in runs))
check(f"measure: a connected septal leaves no L2d gap beyond one voxel ({r['l2d_gap_mm']})", max(r['l2d_gap_mm']) <= 0.87)
rg = F.measure_read(toy(30.0, gap=8.0), Z)
check(f"measure: a septal drawn in two pieces leaves its gap ({rg['l2d_gap_mm']})", 6.5 <= max(rg['l2d_gap_mm']) <= 9.0)
rt = F.measure_read(toy(20.0, thief=10.0), Z)
check(f"measure: a thief that calls 10 mm of LAD a septal makes a run >= 9 mm ({rt['runs']['LAD']})", max(rt['runs']['LAD']) >= 9)

# ------------------------------------------------------------------ rules (decide) on synthetic rows
def row(pid, src, band=None, runs=(1.0,), gaps=(0.0,), present=(), pts=500, stolen_big=0):
    q = lambda v: list(np.full(101, v)) if v is not None else None
    rr = {'name': pid, 'patient': pid, 'source': src, 'kind': 'branch', 'zooms': [0.5, 0.5, 0.5],
          'band': {g: q(band) for g in ('LAD',)} if band is not None else {},
          'runs': {'LAD': list(runs), 'LCx': [], 'RCA': []},
          'l1r': {'LAD': {'pts': pts, 'stolen': 0, 'run_sizes_pts': [int(x / 0.5) for x in runs] + ([stolen_big] if stolen_big else [])},
                  'LCx': {'pts': pts, 'stolen': 0, 'run_sizes_pts': []}, 'RCA': {'pts': pts, 'stolen': 0, 'run_sizes_pts': []}},
          'l2d_gap_mm': list(gaps), 'present': {c: c in present for c in F.BRANCHES},
          'length_mm': {c: (20.0 if c in present else 0.0) for c in F.BRANCHES}}
    return rr


rows = [row(f'p{i}', 'ABCD'[i % 4], band=12.0, present=('S1',)) for i in range(40)]
d = F.decide(rows, [])
check(f"band: 40 reads at 12 mm -> 12 mm, re-set ({d['band']['LAD']})", d['band']['LAD']['mm'] == 12.0 and d['band']['LAD']['reset'])
check('band: a group with < 10 reads keeps the provisional 15 mm, flagged', d['band']['RCA'] == {'mm': 15.0, 'raw_mm': None, 'reads': 0, 'reset': False})
d = F.decide([row(f'p{i}', 'A', band=31.0) for i in range(12)], [])
check('band: clamped to 25 mm above', d['band']['LAD']['mm'] == 25.0 and d['band']['LAD']['raw_mm'] == 31.0)
d = F.decide([row(f'p{i}', 'A', band=4.0) for i in range(12)], [])
check('band: clamped to 8 mm below', d['band']['LAD']['mm'] == 8.0)
d = F.decide(rows, [])
check('L1r: ostium runs of 1 mm keep 3 mm', d['l1r_run']['mm'] == 3.0 and not d['stop'])
d = F.decide([row(f'p{i}', 'A', runs=(3.7,)) for i in range(40)], [])
check(f"L1r: runs of 3.7 mm raise the run length to 4.0 mm ({d['l1r_run']})", d['l1r_run']['mm'] == 4.0)
d = F.decide([row(f'p{i}', 'A', runs=(7.0,)) for i in range(40)], [])
check('L1r: runs of 7 mm (> 5 mm) STOP the freeze', d['l1r_run']['mm'] is None and any(s.startswith('L1r:') for s in d['stop']))
d = F.decide([row(f'p{i}', 'A', stolen_big=(40 if i < 6 else 0)) for i in range(40)], [])
check(f"L1r/K1r: read-faithful theft above 0.02 STOPs ({d['l1r_k1r']['groups']['LAD']})", not d['l1r_k1r']['kept'])
d = F.decide([row(f'p{i}', 'A') for i in range(100)], [])
check('L2d: no gaps keep 30 mm', d['l2d']['mm'] == 30.0)
d = F.decide([row(f'p{i}', 'A', gaps=((35.0,) if i < 3 else (0.0,))) for i in range(100)], [])
check(f"L2d: 3 % of reads with a 35 mm gap move it to 40 mm ({d['l2d']})", d['l2d']['mm'] == 40.0)
d = F.decide([row(f'p{i}', 'A', gaps=((60.0,) if i < 3 else (0.0,))) for i in range(100)], [])
check('L2d: 3 % of reads with a 60 mm gap STOP', d['l2d']['mm'] is None and any(s.startswith('L2d') for s in d['stop']))
# counts
rows = [row(f'p{i}', 'ABC'[i % 3], present=('S1',)) for i in range(30)]
d = F.decide(rows, [])
check('counts: 30 patients from 3 sources with 10 each -> met', d['counts']['S1']['met'])
check('counts: the other classes are confirmed absent in those 30 (D54 negatives)', d['counts']['SN']['absent_patients'] == 30)
d = F.decide(rows, [], raised=('S1',))
check('counts: after a near miss the line is 45 (F-A23 1.5x) -> not met', not d['counts']['S1']['met'] and d['counts']['S1']['line'] == 45)
rows2 = [row(f'p{i}', 'A' if i < 26 else 'BC'[i % 2], present=('S1',)) for i in range(30)]
check('counts: 30 patients but only one source with >= 5 -> not met', not F.decide(rows2, [])['counts']['S1']['met'])
# floor
def pr(pieces, named, pa, pb):
    return {'res': {c: {'pieces': pieces, 'named': named, 'present_a': pa, 'present_b': pb} for c in F.BRANCHES}}
d = F.decide(rows, [pr(2, 2, True, True) for _ in range(10)])
check('floor: 10 agreeing pairs -> met', d['floor']['S1']['met'] and d['floor']['S1']['detect_x_naming'] == 1.0)
d = F.decide(rows, [pr(2, 2, True, True) for _ in range(9)])
check('floor: 9 pairs -> not met (>= 10 needed)', not d['floor']['S1']['met'])
d = F.decide(rows, [pr(2, 2, True, True) for _ in range(5)] + [pr(1, 1, True, False) for _ in range(6)])
check(f"floor (D54): named/pieces 1.0 but presence agreement 5/11 < 0.6 -> not met ({d['floor']['S1']})", not d['floor']['S1']['met'])
check('trainable: S1 needs count AND floor', 'S1' not in d['trainable'])

# ------------------------------------------------------------------ the screen (refusals), on tiny fake export trees
seal = pool_seal.load_pool_seal()
sealed_vol = sorted(seal.volumes)[0]
tmp = tempfile.mkdtemp()


def tree(names, mode='exclude', kind='segqueue14-export', classes='read', manifest=True, sha=pool_seal.SEAL_SHA256):
    root = tempfile.mkdtemp(dir=tmp)
    for n in names:
        os.makedirs(os.path.join(root, n))   # empty dirs: a refusal must come before any file is opened
    if manifest:
        json.dump({'source': {'kind': kind, 'classes': classes,
                              'pool_seal': {'mode': mode, 'sha256': sha} if mode else None}},
                  open(os.path.join(root, 'manifest.json'), 'w'))
    return root


def refuses(root, standins=False):
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            F.screen(root, seal, standins)
        except SystemExit as e:
            return e.code == 3
    return False


ok_names = ['Standin-free__x1']  # not a pool name; real-mode screen
check('screen: a clean tree passes', not refuses(tree(['Figshare-X__a1', 'Figshare-X__a2__r2'])))
check(f'screen: a sealed pool volume ({sealed_vol}) refuses, before its (empty) directory is read',
      refuses(tree(['Figshare-X__a1', sealed_vol])))
check('screen: its second read (__r2) refuses too', refuses(tree([sealed_vol + '__r2'])))
pk = sorted(seal.patients)[0]
check(f'screen: another volume of a sealed patient ({pk}_tp9) refuses (by patient, D32)', refuses(tree([pk + '_tp9'])))
check('screen: an --acceptance-scoring export refuses (D55 Q-F2-1)', refuses(tree(['Figshare-X__a1'], mode='acceptance')))
check('screen: no pool-seal record refuses', refuses(tree(['Figshare-X__a1'], mode=None)))
check('screen: a different seal hash refuses', refuses(tree(['Figshare-X__a1'], sha='0' * 64)))
check('screen: no manifest refuses', refuses(tree(['Figshare-X__a1'], manifest=False)))
check('screen: a --four-class export refuses', refuses(tree(['Figshare-X__a1'], classes='four')))
check('screen: the annotator benchmark refuses (D43)', refuses(tree(['annotator_benchmark_0001'])))
check('screen: stand-in names in a real run refuse', refuses(tree(['StandinA__c0001'])))
check('screen: real names in a --standins run refuse', refuses(tree(['Figshare-X__a1']), standins=True))
d35 = json.load(open(os.path.join(F.ROOT, F.D35_RELPATH)))['volumes'][0][:-len('.nii.gz')]
kept, excl = F.screen(tree(['Figshare-X__a1', d35]), seal)
check(f'screen: a D35 decision volume ({d35}) is excluded and counted, not kept', kept == ['Figshare-X__a1'] and excl['d35'] == 1)
shutil.rmtree(tmp)

print('ALL PASS' if not FAIL else f'{len(FAIL)} FAILED')
sys.exit(1 if FAIL else 0)
