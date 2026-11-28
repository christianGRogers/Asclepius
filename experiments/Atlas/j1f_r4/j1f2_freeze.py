"""Janus 1-F round 4 (Atlas): the J1F-2 freeze. Every stage-2 number, from one SegQueue14 export, by fixed rules.

What it computes (Round 3 §5 items 1-3; F-A21, F-A23, F-A30; D54; D55):
  1. BAND per class group: the 95th percentile of the drawn voxels' distance (mm) from their host, each read weighted
     equally, rounded up to 0.5 mm and clamped to [8, 25] mm; needs >= 10 reads with the group drawn, else 15 mm stays.
  2. TAU_L1, L1r's run length: the 99th percentile over drawn stage-2 pieces of the longest run of the parent group's
     own centreline inside the piece dilated by one voxel (a correct model's ostium with one voxel of bleed), rounded
     up to 0.5 mm, never below 3 mm. Above 6 mm: STOP (L1r would lose the thief). < 30 pieces: 3 mm stays.
  3. TAU_L2, L2d's gap: the smallest of 30, 35, 40, 45, 50 mm such that <= 1 % of reads have a stage-2 26-component
     (>= 20 voxels) whose nearest voxel is farther than it from every other drawn coronary voxel. None: STOP.
     < 30 reads: 30 mm stays.
  4. LINE_L1 (= K1r's line, F-A30: one statistic): the pooled share of each parent group's centreline inside stage-2
     pieces (one-voxel bleed) in runs > TAU_L1, its one-sided 1.25 % upper bound by patient bootstrap, worst group.
     <= 0.01: 0.02 stays; else 2 x the bound rounded up to 0.005; above 0.04: STOP.
  5. READ COUNTS (F-A23): per class, trainable patients with the class present in >= 1 trainable extended read, and
     sources with >= 5 of them. Train iff >= 30 patients (45 after a near miss, --raised) from >= 3 such sources and
     the floor holds.
  6. FLOOR (F-A23): on trainable patients with two extended reads of one volume and the class present in >= 1, both
     directions pooled, detection x naming by the scorer of record's definitions; >= 0.6 on >= 10 patients.
  7. D35 TIERS (F-A22 S): per class, D35 patients (A33's list) with the class present in >= 1 extended read: decide
     >= 30, report >= 20, else counts. Counts only: no prediction exists or is read.

D54 (confirmed absence) is how every read is read here: in an extended read, a branch class the annotator did not draw
is ABSENT, never "not looked for"; `completeGroups` ticks are recorded and change nothing. So a parent is a singleton,
an empty class is a negative, and a reader who drew a branch the other did not is a disagreement.

Data rules, enforced before any file is opened:
  * a sealed pool patient (D27/D32/D33, segtrain.pool_seal) anywhere in the export: REFUSE, exit 3 (D55 Q-F2-1);
    an export written with --acceptance-scoring: REFUSE;
  * the annotator benchmark (D43): REFUSE;
  * the A34 reserve, every Round-10 D35 draw outside A33's list, and anything else janusm.guard holds out: not opened,
    counted by reason;
  * A33's D35 patients: opened for the tier counts only (step 7), never for steps 1-6;
  * geometry (steps 1-4) leaves out D29's anomalous strata (ImageCHD, ImageALCAPA) and the header-spacing-suspect
    sets (ImageALCAPA, HOCMvalvesSeg, CCA200-HF): their millimetres are not trusted. They still count in step 5.

Usage:
  python j1f2_freeze.py <export_dir> <out_dir> [--raised S1,SN] [--d35 FILE] [--np 8]
  python j1f2_freeze.py selftest
Writes <out_dir>/j1f2_freeze.json (post it and its sha256), <out_dir>/rows.jsonl (per read; stays with the lead),
<out_dir>/excluded.json (counts by reason). Exit 0 FROZEN, 2 STOP (a number out of range: the PM), 3 REFUSED.
"""
import argparse
import hashlib
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy import ndimage as ndi

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '../../..'))
sys.path[:0] = [os.path.join(_ROOT, 'src'), os.path.join(_ROOT, 'experiments/Atlas/j1f_r3')]
SCORER_SHA256 = '5221032f3dc086d686b63fa946149a215ac00738a87fd9669d7faa15962b2e5b'   # F-A28
_scorer_path = os.path.join(_ROOT, 'experiments/Atlas/j1f_r3/j1f_scorer.py')
assert hashlib.sha256(open(_scorer_path, 'rb').read()).hexdigest() == SCORER_SHA256, 'not the scorer of record'
import j1f_scorer as S  # noqa: E402  (pins tf1.py and labels.py itself)
from segqueue14 import labels as SQ  # noqa: E402
from segqueue14 import benchmark as SQB  # noqa: E402
from segtrain import pool_seal  # noqa: E402

# ------------------------------------------------------------------------------------------- frozen constants
STAGE2 = {'S1': 13, 'S2': 14, 'S3': 15, 'SN': 16, 'Conus': 17, 'RMA': 18}
VALUES = {'LM': 1, 'LAD': 2, 'LCx': 3, 'RCA': 4, 'D1': 5, 'D2': 6, 'D3': 7, 'OM1': 8, 'OM2': 9, 'Ramus': 10,
          'PDA': 11, 'PLB': 12, **STAGE2}
NAME_OF = {v: k for k, v in VALUES.items()}
IGNORE = 255
# own parents for D47 Q4 (a child over its own parent is the child); PDA, PLB, SN by D47 Q1 leave LCx or RCA
OWN_PARENTS = {'D1': ('LAD',), 'D2': ('LAD',), 'D3': ('LAD',), 'S1': ('LAD',), 'S2': ('LAD',), 'S3': ('LAD',),
               'OM1': ('LCx',), 'OM2': ('LCx',), 'Ramus': ('LCx', 'LM'), 'Conus': ('RCA',), 'RMA': ('RCA',),
               'SN': ('LCx', 'RCA'), 'PDA': ('LCx', 'RCA'), 'PLB': ('LCx', 'RCA')}
PARENT_GROUP = {'LAD': (2, 5, 6, 7), 'LCx': (3, 8, 9, 10), 'RCA': (4,)}          # L1r's parent groups (vessel values)
CLASS_PARENT = {'S1': 'LAD', 'S2': 'LAD', 'S3': 'LAD', 'Conus': 'RCA', 'RMA': 'RCA', 'SN': None}  # SN: nearer of LCx/RCA
BAND_GROUPS = {'LAD': ('S1', 'S2', 'S3'), 'RCA': ('RMA',), 'pRCA': ('Conus', 'SN@RCA'), 'pLCx': ('SN@LCx',)}
BAND_HOST = {'LAD': (2, 5, 6, 7), 'RCA': (4,), 'pRCA': (4,), 'pLCx': (1, 3)}
BAND_Q, BAND_MIN_READS, BAND_PROVISIONAL, BAND_CLAMP = 0.95, 10, 15.0, (8.0, 25.0)
TAU1_Q, TAU1_FLOOR, TAU1_STOP, TAU1_MIN_PIECES = 0.99, 3.0, 6.0, 30
TAU2_STEPS, TAU2_SHARE, TAU2_MIN_READS = (30.0, 35.0, 40.0, 45.0, 50.0), 0.01, 30
LINE1_KEEP, LINE1_RULED, LINE1_STOP, LINE1_Q = 0.01, 0.02, 0.04, 0.9875
TRAIN_PATIENTS, RAISE, SRC_MIN, SRC_N = 30, 1.5, 5, 3
FLOOR, FLOOR_MIN = 0.6, 10
TIER_DECIDE, TIER_REPORT = 30, 20
NBOOT, BOOT_SEED = 2000, 20261128
MIN_COMP_VOX = 20
D29_SOURCES = ('ImageCHD', 'ImageALCAPA')
SPACING_SUSPECT = ('ImageALCAPA', 'HOCMvalvesSeg', 'CCA200-HF')
D35_OF_RECORD = 'experiments/Delta/r10/d35_decision_set_proposal.json'     # A33
D35_SHA256 = '1a75fe41ffe44aa37c884b723c066a6b8cd3669164e0c670b6439028c2b966b1'
MATERIALS = tuple(SQ.MATERIALS)


def ceil_to(x, step):
    return math.ceil(round(x / step, 9)) * step


def source_of(name):
    return name.split('__')[0]


def patient_of(name):
    base = name.split('/')[-1]
    for suf in ('__r2', '__r3', '__r4', '__r5'):
        if base.endswith(suf):
            base = base[:-len(suf)]
    return pool_seal.ingest_patient(base) or base


# ------------------------------------------------------------------------------------------- labels (D47 Q4, D40, D54)
def read_labels(masks):
    """A read's class masks ({SegQueue name: bool array}) -> stage-2 1-F labels (uint8; 255 ignore).
    Materials are dropped first (D46 Q8 as for 1-L). One class: that class. A branch over one of its own parents only:
    the branch (D47 Q4). Any other overlap: ignore (D40). Under D54 there is no third state: every other voxel of an
    extended read is a singleton label, a drawn class or background."""
    names = [n for n in masks if n in VALUES]
    shape = next(iter(masks.values())).shape
    count = np.zeros(shape, np.uint8)
    for n in names:
        count += masks[n].astype(np.uint8)
    lab = np.zeros(shape, np.uint8)
    for n in names:
        lab[masks[n] & (count == 1)] = VALUES[n]
    multi = count >= 2
    if multi.any():
        lab[multi] = IGNORE
        for b, parents in OWN_PARENTS.items():
            if b not in masks:
                continue
            for p in parents:
                if p not in masks:
                    continue
                m = multi & masks[b] & masks[p] & (count == 2)
                lab[m] = VALUES[b]
    return lab


def training_sets_d54(lab, extended):
    """The stage-2 label set of each voxel of a POOL read, as the trainer must build it (spec; used by the selftest).
    Extended read (D54): every non-ignore voxel is the singleton {its label}. Four-class read (F-A11, unchanged): a
    parent's voxels are {parent and its children}; background is {bg}. Returns {value: frozenset} per label value."""
    if extended:
        return {int(v): frozenset({int(v)}) for v in np.unique(lab) if v != IGNORE}
    kids = {2: {2, 5, 6, 7, 13, 14, 15}, 3: {3, 8, 9, 10, 11, 12, 16}, 4: {4, 11, 12, 16, 17, 18}, 1: {1, 10}}
    return {int(v): frozenset(kids.get(int(v), {int(v)})) for v in np.unique(lab) if v != IGNORE}


# ------------------------------------------------------------------------------------------- per-read geometry
def _crop(lab, pad=4):
    nz = np.argwhere(lab > 0)
    lo = np.maximum(nz.min(0) - pad, 0)
    hi = np.minimum(nz.max(0) + pad + 1, lab.shape)
    return tuple(slice(a, b) for a, b in zip(lo, hi))


def _runs_longest_and_long(pts, sp, tau):
    """26-connected runs of `pts`; (longest run in mm, number of points in runs longer than tau)."""
    if not len(pts):
        return 0.0, 0
    m = np.zeros(pts.max(0) + 1, bool)
    m[tuple(pts.T)] = True
    comp, nc = ndi.label(m, S.S26)
    longest, n_long = 0.0, 0
    for i in range(1, nc + 1):
        q = np.argwhere(comp == i)
        L = S._graph_length(q, sp)
        longest = max(longest, L)
        if L > tau:
            n_long += len(q)
    return longest, n_long


def sn_side(lab, piece_mask, sp):
    """'LCx' or 'RCA': the vessel an SN piece is nearer to (D47 Q1)."""
    d = {}
    for side, vals in (('LCx', (1, 3)), ('RCA', (4,))):
        host = np.isin(lab, vals)
        d[side] = float(ndi.distance_transform_edt(~host, sampling=sp)[piece_mask].min()) if host.any() else np.inf
    return 'LCx' if d['LCx'] < d['RCA'] else 'RCA'


def geometry(lab, masks, sp, taus=TAU2_STEPS, tau1_grid=(3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0)):
    """Everything steps 1-4 need from one read. Distances in mm."""
    sl = _crop(lab)
    lab = lab[sl]
    masks = {k: v[sl] for k, v in masks.items()}
    tree = (lab > 0)
    skel = S._skeleton((lab > 0) & (lab != IGNORE))
    out = {'band': {}, 'pieces': [], 'gaps': [], 'parent_pts': {}, 'stolen': {}, 'present': {}}
    # parent groups' own centrelines (each group's mask as drawn, whole: D39)
    pg_mask = {}
    for g, vals in PARENT_GROUP.items():
        u = np.isin(lab, vals)
        for v in vals:
            if NAME_OF[v] in masks:
                u |= masks[NAME_OF[v]]
        pg_mask[g] = u
    pg_skel = {g: (S._skeleton(m) if m.any() else np.zeros_like(m)) for g, m in pg_mask.items()}
    for g in PARENT_GROUP:
        out['parent_pts'][g] = int(pg_skel[g].sum())
        out['stolen'][g] = {str(t): 0 for t in tau1_grid}
    host_dt = {g: ndi.distance_transform_edt(~np.isin(lab, vals), sampling=sp) if np.isin(lab, vals).any() else None
               for g, vals in BAND_HOST.items()}
    band_d = {g: [] for g in BAND_GROUPS}
    for name, v in STAGE2.items():
        pcs = S._pieces(lab, v, skel, sp, None)
        out['present'][name] = float(sum(p['length_mm'] for p in pcs)) >= S.PRESENCE_MM
        comp, nc = ndi.label(lab == v, S.S26)
        for i in range(1, nc + 1):
            pm = comp == i
            nvox = int(pm.sum())
            if nvox < MIN_COMP_VOX:
                continue
            # L2d: nearest voxel of this component to every other drawn coronary voxel
            other = tree & ~pm
            gap = float(ndi.distance_transform_edt(~other, sampling=sp)[pm].min()) if other.any() else np.inf
            out['gaps'].append(gap)
            parent = CLASS_PARENT[name] or sn_side(lab, pm, sp)
            # band
            key = {'S1': 'LAD', 'S2': 'LAD', 'S3': 'LAD', 'RMA': 'RCA', 'Conus': 'pRCA'}.get(name)
            if name == 'SN':
                key = 'pRCA' if parent == 'RCA' else 'pLCx'
            if host_dt[key] is not None:
                band_d[key].append(host_dt[key][pm])
            # L1r: the parent group's own centreline inside the piece with one voxel of bleed
            bleed = ndi.binary_dilation(pm, S.S26)
            pts = np.argwhere(pg_skel[parent] & bleed)
            longest, _ = _runs_longest_and_long(pts, sp, 0.0)
            length = S._graph_length(np.argwhere(pm & skel), sp)
            out['pieces'].append({'class': name, 'parent': parent, 'vox': nvox, 'length_mm': round(length, 2),
                                  'longest_run_mm': round(longest, 3), 'gap_mm': round(gap, 2)})
            for t in tau1_grid:
                out['stolen'][parent][str(t)] += _runs_longest_and_long(pts, sp, t)[1]
    for g, arrs in band_d.items():
        if arrs:
            d = np.concatenate(arrs)
            out['band'][g] = {'n_vox': int(d.size), 'q': [float(x) for x in np.quantile(d, np.linspace(0, 1, 201))]}
    return out


def pair_agreement(lab_a, lab_b, sp):
    """Reader A's stage-2 pieces scored against reader B's read, by the scorer of record's definitions: detection
    (>= 50 % of the centreline within 1.5 mm of B's vessel of any class) and naming (strict majority of the covered
    points' nearest B label). Returns {class: [pieces, detected, named]} and presence per class."""
    sl = _crop(np.maximum(lab_a, lab_b), pad=6)
    a, b = lab_a[sl], lab_b[sl]
    a = np.where(a == IGNORE, 0, a)
    b = np.where(b == IGNORE, 0, b)
    skel = S._skeleton(a > 0)
    bm = S._tf1.remove_small_components(b > 0, S.MIN_PRED_VOX)
    res = {}
    if bm.any():
        dist, idx = ndi.distance_transform_edt(~bm, sampling=sp, return_indices=True)
    for name, v in STAGE2.items():
        npc = ndet = nnamed = 0
        for p in S._pieces(a, v, skel, sp, None):
            npc += 1
            if not bm.any():
                continue
            q = tuple(p['pts'].T)
            cov = dist[q] <= S.TOL_MM
            if cov.mean() >= S.DETECT_FRACTION:
                ndet += 1
                nn = tuple(idx[:, q[0][cov], q[1][cov], q[2][cov]])
                nnamed += int((b[nn] == v).sum() * 2 > cov.sum())
        res[name] = [npc, ndet, nnamed]
    return res


# ------------------------------------------------------------------------------------------- reading an export
def load_read(d):
    import nibabel as nb
    info = json.load(open(os.path.join(d, 'read.json')))
    segdir = os.path.join(d, 'segmentations')
    masks, sp = {}, None
    for f in sorted(os.listdir(segdir)):
        if not f.endswith('.nii.gz'):
            continue
        name = f[:-7].replace('_', ' ')
        name = {'Calcified plaque': 'Calcified plaque', 'Non-calcified plaque': 'Non-calcified plaque'}.get(name, name)
        im = nb.load(os.path.join(segdir, f))
        if sp is None:
            sp = np.array(im.header.get_zooms()[:3], float)
        masks[name] = np.asarray(im.dataobj) > 0
    for m in MATERIALS:
        masks.pop(m, None)
    return info, masks, sp


def per_read(args):
    d, role, geom = args
    info, masks, sp = load_read(d)
    extended = bool(info.get('extended'))
    lab = read_labels(masks)
    row = {'read': os.path.basename(d), 'role': role, 'extended': extended,
           'ticks': info.get('completeGroups') or [], 'present': {},
           'branches_drawn': sorted(n for n in SQ.PARENT if n in masks and int(masks[n].sum()) >= MIN_COMP_VOX)}
    sl = _crop(lab) if (lab > 0).any() else None
    if sl is None:
        row['present'] = {n: False for n in STAGE2}
        return row, None
    if extended and role == 'trainable' and geom:
        g = geometry(lab, masks, sp)
        row.update({k: g[k] for k in ('present', 'pieces', 'gaps', 'parent_pts', 'stolen', 'band')})
    else:
        skel = S._skeleton((lab[sl] > 0) & (lab[sl] != IGNORE))
        row['present'] = {n: float(sum(p['length_mm'] for p in S._pieces(lab[sl], v, skel, sp, None)))
                          >= S.PRESENCE_MM for n, v in STAGE2.items()}
    return row, None


def pair_job(args):
    da, db = args
    _, ma, sp = load_read(da)
    _, mb, _ = load_read(db)
    la, lb = read_labels(ma), read_labels(mb)
    if not (la > 0).any() and not (lb > 0).any():
        return os.path.basename(da), {n: [0, 0, 0] for n in STAGE2}, {n: [0, 0, 0] for n in STAGE2}
    return os.path.basename(da), pair_agreement(la, lb, sp), pair_agreement(lb, la, sp)


def classify(names, seal, guard, d35_patients):
    """name -> role, before any file is opened. Raises SystemExit(3) on a sealed or benchmark name."""
    roles, refused = {}, []
    for n in names:
        if seal.is_sealed(n):
            refused.append(seal.reason(n))
            continue
        if SQB.is_benchmark_name(n.split('__r')[0]):
            refused.append(f'{n}: annotator benchmark (D43)')
            continue
        if patient_of(n) in d35_patients:
            roles[n] = 'd35'
            continue
        why = guard.reason(n.split('/')[-1]) if guard is not None else None
        roles[n] = ('held_out: ' + why.split(': ', 1)[1].split(',')[0]) if why else 'trainable'
    if refused:
        print(f'REFUSED (D27/D55): {len(refused)} read(s) of the export are sealed or the benchmark, e.g. '
              f'{refused[:3]}. Export again WITHOUT --acceptance-scoring; nothing was opened.', file=sys.stderr)
        raise SystemExit(3)
    return roles


# ------------------------------------------------------------------------------------------- the rules
def wquantile(rows, group, q):
    """q-quantile of the drawn voxels' distance, each read weighted equally (its 201-point quantile curve)."""
    curves = [np.array(r['band'][group]['q']) for r in rows if group in r.get('band', {})]
    if not curves:
        return None, 0
    grid = np.linspace(0, 1, 201)
    samples = np.concatenate([np.interp(np.linspace(0, 1, 2001), grid, c) for c in curves])
    return float(np.quantile(samples, q)), len(curves)


def boot_upper(rows, group, tau, q, rng):
    pats = sorted({patient_of(r['read']) for r in rows})
    by = {p: [r for r in rows if patient_of(r['read']) == p] for p in pats}
    num = np.array([sum(r['stolen'][group][str(tau)] for r in by[p]) for p in pats], float)
    den = np.array([sum(r['parent_pts'][group] for r in by[p]) for p in pats], float)
    if den.sum() == 0:
        return 0.0, 0.0
    point = num.sum() / den.sum()
    idx = rng.integers(0, len(pats), size=(NBOOT, len(pats)))
    bs = num[idx].sum(1) / np.maximum(den[idx].sum(1), 1)
    return float(point), float(np.quantile(bs, q))


def freeze(rows, pairs, raised=(), seed=BOOT_SEED):
    rng = np.random.default_rng(seed)
    stop = []
    geo = [r for r in rows if r['role'] == 'trainable' and r['extended'] and 'gaps' in r]
    res = {'band_mm': {}, 'band_detail': {}}
    for g in BAND_GROUPS:
        q95, n = wquantile(geo, g, BAND_Q)
        if n >= BAND_MIN_READS:
            w = min(max(ceil_to(q95, 0.5), BAND_CLAMP[0]), BAND_CLAMP[1])
            src = 'reads'
        else:
            w, src = BAND_PROVISIONAL, f'provisional (only {n} reads < {BAND_MIN_READS})'
        res['band_mm'][g] = w
        res['band_detail'][g] = {'reads': n, 'q95_mm': None if q95 is None else round(q95, 3), 'rule': src}
    # TAU_L1
    runs = sorted(p['longest_run_mm'] for r in geo for p in r['pieces'])
    if len(runs) >= TAU1_MIN_PIECES:
        q99 = float(np.quantile(runs, TAU1_Q))
        tau1 = max(TAU1_FLOOR, ceil_to(q99, 0.5))
        if tau1 > TAU1_STOP:
            stop.append(f'TAU_L1 {tau1} mm > {TAU1_STOP} mm (q99 {q99:.2f})')
            tau1 = None
        rule1 = 'reads'
    else:
        q99, tau1, rule1 = None, TAU1_FLOOR, f'kept (only {len(runs)} pieces < {TAU1_MIN_PIECES})'
    res['tau_L1_mm'] = tau1
    res['tau_L1_detail'] = {'pieces': len(runs), 'q99_mm': None if q99 is None else round(q99, 3),
                            'max_mm': round(runs[-1], 3) if runs else None, 'rule': rule1}
    # TAU_L2
    worst = [max(r['gaps']) if r['gaps'] else 0.0 for r in geo]
    if len(worst) >= TAU2_MIN_READS:
        tau2 = next((t for t in TAU2_STEPS if np.mean(np.array(worst) > t) <= TAU2_SHARE), None)
        if tau2 is None:
            stop.append(f'TAU_L2: > {TAU2_SHARE:.0%} of reads leave a > {TAU2_STEPS[-1]} mm gap')
        rule2 = 'reads'
    else:
        tau2, rule2 = TAU2_STEPS[0], f'kept (only {len(worst)} reads < {TAU2_MIN_READS})'
    res['tau_L2_mm'] = tau2
    res['tau_L2_detail'] = {'reads': len(worst), 'rule': rule2,
                            'share_over': {str(t): round(float(np.mean(np.array(worst) > t)), 4) if worst else None
                                           for t in TAU2_STEPS}}
    # LINE_L1 = K1r
    tau_for_line = tau1 if tau1 is not None else TAU1_STOP
    ub = {}
    for g in PARENT_GROUP:
        pt, u = boot_upper(geo, g, tau_for_line, LINE1_Q, rng) if geo else (0.0, 0.0)
        ub[g] = {'point': round(pt, 5), 'upper_1.25%': round(u, 5)}
    worst_ub = max((v['upper_1.25%'] for v in ub.values()), default=0.0)
    if worst_ub <= LINE1_KEEP:
        line = LINE1_RULED
    else:
        line = max(LINE1_RULED, ceil_to(2 * worst_ub, 0.005))
        if line > LINE1_STOP:
            stop.append(f'LINE_L1 {line} > {LINE1_STOP}')
    res['line_L1_K1r'] = line
    res['line_L1_detail'] = ub
    # read counts, floor, tiers
    train_rows = [r for r in rows if r['role'] == 'trainable' and r['extended']]
    res['extended_trainable_reads'] = len(train_rows)
    res['four_class_trainable_reads'] = sum(r['role'] == 'trainable' and not r['extended'] for r in rows)
    res['ticked_reads'] = sum(bool(r['ticks']) for r in train_rows)
    # D54 QC (report only): extended reads with no branch drawn at all train every branch as absent
    res['branchless_extended_trainable_reads'] = sum(not r['branches_drawn'] for r in train_rows)
    res['stage1_branch_absent_share'] = {
        b: round(float(np.mean([b not in r['branches_drawn'] for r in train_rows])), 4) if train_rows else None
        for b in ('D1', 'D2', 'OM1', 'OM2', 'PDA', 'PLB')}
    res['classes'] = {}
    for c in STAGE2:
        pats = {}
        for r in train_rows:
            if r['present'].get(c):
                pats.setdefault(patient_of(r['read']), source_of(r['read']))
        by_src = {}
        for p, s in pats.items():
            by_src[s] = by_src.get(s, 0) + 1
        need = int(math.ceil(TRAIN_PATIENTS * (RAISE if c in raised else 1)))
        n_src = sum(v >= SRC_MIN for v in by_src.values())
        pr = [x for x in pairs if x['present'][0].get(c) or x['present'][1].get(c)]
        k = np.sum([x['ab'][c] for x in pr] + [x['ba'][c] for x in pr], axis=0) if pr else np.zeros(3)
        rec = k[1] / k[0] if k[0] else 0.0
        nam = k[2] / k[1] if k[1] else 0.0
        both = [x for x in pairs]
        pres_agree = (np.mean([x['present'][0].get(c) == x['present'][1].get(c) for x in both]) if both else None)
        floor_ok = len(pr) >= FLOOR_MIN and rec * nam >= FLOOR
        d35 = {patient_of(r['read']) for r in rows if r['role'] == 'd35' and r['extended'] and r['present'].get(c)}
        tier = 'decide' if len(d35) >= TIER_DECIDE else 'report' if len(d35) >= TIER_REPORT else 'counts'
        res['classes'][c] = {
            'patients_present': len(pats), 'needs': need, 'sources_with_5': n_src, 'by_source': by_src,
            'patients_extended_absent': len({patient_of(r['read']) for r in train_rows}) - len(pats),
            'floor_patients': len(pr), 'floor_pieces': int(k[0]), 'floor_recall': round(float(rec), 4),
            'floor_naming': round(float(nam), 4), 'floor': round(float(rec * nam), 4),
            'presence_agreement_double_read': None if pres_agree is None else round(float(pres_agree), 4),
            'floor_ok': bool(floor_ok),
            'train': bool(len(pats) >= need and n_src >= SRC_N and floor_ok),
            'd35_patients_present': len(d35), 'd35_tier': tier}
    res['stop'] = stop
    res['status'] = 'STOP' if stop else 'FROZEN'
    return res


# ------------------------------------------------------------------------------------------- main
def file_sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def run(export, out, raised=(), d35_file=None, nproc=8, guard=True):
    os.makedirs(out, exist_ok=True)
    man_path = os.path.join(export, 'manifest.json')
    man = json.load(open(man_path)) if os.path.exists(man_path) else {}
    src = man.get('source', {})
    if (src.get('pool_seal') or {}).get('mode') == 'acceptance':
        print('REFUSED: the export was written with --acceptance-scoring (D27/D55).', file=sys.stderr)
        raise SystemExit(3)
    if src and src.get('classes') == 'four':
        print('REFUSED: a --four-class export has no extended classes; export each read\'s own classes.',
              file=sys.stderr)
        raise SystemExit(3)
    names = sorted(n for n in os.listdir(export) if os.path.isdir(os.path.join(export, n)))
    seal = pool_seal.load_pool_seal(os.path.join(_ROOT, pool_seal.SEAL_RELPATH))
    g = None
    if not guard and not all(n.startswith('StandIn-') for n in names):
        print('REFUSED: --no-guard is for stand-in exports only (every read named StandIn-*).', file=sys.stderr)
        raise SystemExit(3)
    if guard:
        from janusm.guard import load_guard
        g = load_guard()
    d35_file = d35_file or os.path.join(_ROOT, D35_OF_RECORD)
    if d35_file == os.path.join(_ROOT, D35_OF_RECORD):
        assert file_sha(d35_file) == D35_SHA256, 'A33 list changed'
    d35 = {pool_seal.ingest_patient(p) or p for p in json.load(open(d35_file))['patients']}
    roles = classify(names, seal, g, d35)                      # refuses before anything is opened
    excluded = {}
    jobs = []
    for n in names:
        role = roles[n]
        if role.startswith('held_out'):
            excluded[role] = excluded.get(role, 0) + 1
            continue
        geom = role == 'trainable' and source_of(n) not in D29_SOURCES + SPACING_SUSPECT
        jobs.append((os.path.join(export, n), role, geom))
    with ProcessPoolExecutor(nproc) as ex:
        rows = [r for r, _ in ex.map(per_read, jobs)]
    byname = {r['read']: r for r in rows}
    # double reads: the first volume (sorted) of each trainable patient with two extended reads
    pair_jobs, seen = [], set()
    for n in names:
        if roles[n] != 'trainable' or '__r' in n[len(source_of(n)):]:
            continue
        r2 = n + '__r2'
        if r2 in byname and byname.get(n, {}).get('extended') and byname[r2]['extended']:
            p = patient_of(n)
            if p in seen:
                continue
            seen.add(p)
            pair_jobs.append((os.path.join(export, n), os.path.join(export, r2)))
    with ProcessPoolExecutor(nproc) as ex:
        pr = list(ex.map(pair_job, pair_jobs))
    pairs = [{'read': a, 'ab': ab, 'ba': ba,
              'present': (byname[a]['present'], byname[a + '__r2']['present'])} for a, ab, ba in pr]
    res = freeze(rows, pairs, raised=raised)
    res['inputs'] = {'script_sha256': file_sha(os.path.abspath(__file__)), 'scorer_sha256': SCORER_SHA256,
                     'seal_sha256': seal.sha256, 'manifest_sha256': file_sha(man_path) if man else None,
                     'd35_file_sha256': file_sha(d35_file), 'raised': sorted(raised),
                     'reads_in_export': len(names), 'reads_opened': len(jobs), 'double_read_patients': len(pairs)}
    res['excluded'] = excluded
    with open(os.path.join(out, 'rows.jsonl'), 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    json.dump(excluded, open(os.path.join(out, 'excluded.json'), 'w'), indent=1, sort_keys=True)
    p = os.path.join(out, 'j1f2_freeze.json')
    json.dump(res, open(p, 'w'), indent=1, sort_keys=True)
    print(json.dumps({k: res[k] for k in ('status', 'stop', 'band_mm', 'tau_L1_mm', 'tau_L2_mm', 'line_L1_K1r')}))
    for c, v in res['classes'].items():
        print(c, {k: v[k] for k in ('patients_present', 'needs', 'sources_with_5', 'floor_patients', 'floor',
                                    'train', 'd35_tier')})
    print('j1f2_freeze.json sha256', file_sha(p))
    return res


# ------------------------------------------------------------------------------------------- self-test
def selftest():
    sp = np.array([0.5, 0.5, 0.5])
    # 1. labels: child over own parent -> child; unrelated overlap -> ignore; materials dropped
    sh = (20, 20, 20)
    m = {k: np.zeros(sh, bool) for k in ('LAD', 'S1', 'D1', 'RCA', 'Calcified plaque')}
    m['LAD'][5:15, 10, 10] = True
    m['S1'][10:12, 10, 10:15] = True              # overlaps the LAD at (10..11, 10, 10)
    m['D1'][11, 10, 10] = True                    # S1 + D1 + LAD at one voxel -> ignore
    m['Calcified plaque'][3, 3, 3] = True
    mm = {k: v for k, v in m.items() if k not in MATERIALS}
    lab = read_labels(mm)
    assert lab[10, 10, 10] == 13, lab[10, 10, 10]
    assert lab[11, 10, 10] == IGNORE
    assert lab[3, 3, 3] == 0
    assert lab[5, 10, 10] == 2
    # 2. D54 sets: extended read -> every label a singleton; four-class read -> parent's set holds its children
    s_ext = training_sets_d54(lab, True)
    assert all(len(v) == 1 for v in s_ext.values())
    s4 = training_sets_d54(lab, False)
    assert s4[2] >= {2, 13, 14, 15} and s4[0] == {0}
    # 3. runs: a 4 mm run counts at tau 3, not at tau 5
    pts = np.array([[i, 0, 0] for i in range(9)])
    L, n3 = _runs_longest_and_long(pts, sp, 3.0)
    assert abs(L - 4.0) < 1e-6 and n3 == 9 and _runs_longest_and_long(pts, sp, 5.0)[1] == 0
    # 4. seal refusal before opening: a sealed volume name in a fake export
    seal = pool_seal.load_pool_seal(os.path.join(_ROOT, pool_seal.SEAL_RELPATH))
    sealed = sorted(seal.volumes)[0]
    try:
        classify([sealed, 'StandIn-A__x'], seal, None, set())
        raise AssertionError('sealed name not refused')
    except SystemExit as e:
        assert e.code == 3
    try:
        classify([sealed + '__r2'], seal, None, set())
        raise AssertionError('sealed replica not refused')
    except SystemExit as e:
        assert e.code == 3
    assert classify(['StandIn-A__x'], seal, None, set()) == {'StandIn-A__x': 'trainable'}
    # 5. rules: ceil and clamp
    assert ceil_to(3.01, 0.5) == 3.5 and ceil_to(3.0, 0.5) == 3.0 and ceil_to(0.0201, 0.005) == 0.025
    print('j1f2_freeze selftest ok')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'selftest':
        selftest(); sys.exit(0)
    ap = argparse.ArgumentParser()
    ap.add_argument('export'); ap.add_argument('out')
    ap.add_argument('--raised', default='', help='classes that failed a J1F-2 look near their count (F-A23)')
    ap.add_argument('--d35', default=None)
    ap.add_argument('--np', type=int, default=8)
    ap.add_argument('--no-guard', action='store_true', help='self-test exports only: skip janusm.guard')
    a = ap.parse_args()
    r = run(a.export, a.out, raised=tuple(x for x in a.raised.split(',') if x), d35_file=a.d35, nproc=a.np,
            guard=not a.no_guard)
    sys.exit(2 if r['status'] == 'STOP' else 0)
