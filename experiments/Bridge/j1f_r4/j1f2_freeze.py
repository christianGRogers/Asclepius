"""Janus 1-F round 4 (Bridge): the J1F-2 freeze script.

It computes, from a SegQueue14 export of extended pool reads, every number Round 3 §5 leaves to the freeze:
  1. the band width per class group (F-A21);
  2. L1r's run length (3 mm), L2d's gap (30 mm) and the theft line of L1r / K1r (0.02) (F-A30);
  3. each stage-2 class's read counts and inter-read floor (F-A23), with the scorer of record (F-A28);
and writes them to one json whose sha256 it prints. Nothing here trains, predicts or looks at the locked 100.

Data rules (D27, D35, D54, D55 Q-F2-1), applied before any read file is opened:
  * any read of a sealed pool patient (D27; primary or report-only) -> REFUSE, exit 3. So is an export made with
    `--acceptance-scoring`. The freeze never sets a number from a sealed read (D55 Q-F2-1).
  * every other held-out name (A34 reserve, the Round 10 D35 draws, TotalSegmentator twins, ImageCAS-X test/val:
    `janusm.guard`) is left out of every number, by patient, and counted. If the guard cannot load: exit 5.
  * the frozen D35 patients (Delta's r10 draw, the list the master plan names) are left out of every number too. With
    `--d35-tiers` their reads are opened for one thing only: per-class presence counts, printed as F-A22's S tiers.
Labels (D47 Q4, D54): in an extended read every voxel is a singleton.
  * a voxel in exactly one class is that class;
  * a branch over its own parent vessel is the branch (D47 Q4); PDA, PLB and SN have RCA and LCx as parents;
  * any other overlap is ignore (255);
  * a branch class the annotator did not draw is confirmed absent (D54): its would-be voxels are whatever the read
    says they are (its parent, or background). There is no set and no "complete group": `completeGroups` in read.json
    is read only to count reads that carry old ticks, and changes nothing;
  * materials are dropped (a vessel voxel also marked plaque stays vessel; a material-only voxel is background), as
    D46 Q8 rules for 1-L.
Stage-2 values: stage 1's 0-12 (`j1f_scorer.NAMES`), then 13 S1, 14 S2, 15 S3, 16 SN, 17 Conus, 18 RMA; 255 ignore.

Usage:
  python j1f2_freeze.py --export <segqueue14-export dir> --out <freeze.json> [--np 4] [--d35-tiers]
                        [--raised CLASS ...]
  python j1f2_freeze.py selftest
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
from contextlib import contextmanager
from multiprocessing import Pool

import numpy as np
import nibabel as nb
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))

# ----------------------------------------------------------------------------------------------- pins
SCORER_PATH = os.path.join(REPO, 'experiments', 'Atlas', 'j1f_r3', 'j1f_scorer.py')
SCORER_SHA256 = '5221032f3dc086d686b63fa946149a215ac00738a87fd9669d7faa15962b2e5b'      # F-A28
D35_PATH = os.path.join(REPO, 'experiments', 'Delta', 'r10', 'd35_decision_set_proposal.json')
D35_SHA256 = '1a75fe41ffe44aa37c884b723c066a6b8cd3669164e0c670b6439028c2b966b1'          # as janusm.guard pins it


def _sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def load_scorer():
    got = _sha(SCORER_PATH)
    if got != SCORER_SHA256:
        raise SystemExit(f'REFUSE: {SCORER_PATH} sha256 {got} is not the scorer of record {SCORER_SHA256} (F-A28)')
    spec = importlib.util.spec_from_file_location('j1f_scorer', SCORER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


J = load_scorer()

# ----------------------------------------------------------------------------------------------- classes
STAGE2_NAMES = ['S1', 'S2', 'S3', 'SN', 'Conus', 'RMA']
S2NAMES = list(J.NAMES) + STAGE2_NAMES                     # values 0..18
V = {n: i for i, n in enumerate(S2NAMES)}
STAGE2 = tuple(V[n] for n in STAGE2_NAMES)                 # 13..18
BRANCHES2 = tuple(range(5, 19))                            # every branch class, stage 1 and 2
IGNORE = J.IGNORE                                          # 255 in the scorer; the trainer writes max+1 on disk
VESSELS = ('LM', 'LAD', 'LCx', 'RCA')
PARENTS = {'D1': ('LAD',), 'D2': ('LAD',), 'D3': ('LAD',), 'S1': ('LAD',), 'S2': ('LAD',), 'S3': ('LAD',),
           'OM1': ('LCx',), 'OM2': ('LCx',), 'Ramus': ('LCx',),
           'PDA': ('RCA', 'LCx'), 'PLB': ('RCA', 'LCx'), 'SN': ('RCA', 'LCx'),
           'Conus': ('RCA',), 'RMA': ('RCA',)}
PARENT_VALUES2 = {V[c]: tuple(V[p] for p in ps) for c, ps in PARENTS.items()}
MATERIAL_FILES = ('Stent', 'Calcified_plaque', 'Non-calcified_plaque')
# L1r's parent groups on the four-class collapse (F-A30): 2 LAD, 3 LCx, 4 RCA
GROUPS = {'LAD': 2, 'LCx': 3, 'RCA': 4}
# F-A21's band groups: which stage-2 classes, measured from which host, proximal how far
BAND_GROUPS = {
    'LAD':  {'classes': ('S1', 'S2', 'S3'), 'host': ('LAD', 'D1', 'D2', 'D3'), 'prox_mm': None, 'sn_side': None},
    'RCA':  {'classes': ('RMA',), 'host': ('RCA',), 'prox_mm': None, 'sn_side': None},
    'pRCA': {'classes': ('SN', 'Conus'), 'host': ('RCA',), 'prox_mm': 30.0, 'sn_side': 'RCA'},
    'pLCx': {'classes': ('SN',), 'host': ('LCx',), 'prox_mm': 20.0, 'sn_side': 'LCx'},
}

# ----------------------------------------------------------------------------------------------- rules (frozen here)
RULED = {'band_mm': 15.0, 'run_mm': 3.0, 'gap_mm': 30.0, 'theft_line': 0.02}
BAND_CLAMP = (8.0, 25.0)            # F-A21
BAND_MIN_READS = 10                 # F-A21
BAND_Q = 95                         # F-A21: the 95th percentile of the drawn distance
RUN_Q = 99                          # L1r: the run filter must pass 99 % of the readers' own child-over-parent runs
RUN_STOP_MM = 8.0                   # above this a reader's ostium is longer than a thief's minimum: the PM decides
GAP_STEPS = (30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0)
GAP_RATE = 0.02                     # L2d: share of reads with any gap > D. At 0.02, P(>= 6 of 100 cases) = 1.6 %
THEFT_MARGIN = 2.0                  # the line must be >= 2x the readers' own theft (upper bound)
THEFT_STOP = 0.05                   # above this a theft line no longer separates a thief (0.137-0.142, Foxtrot)
N_BOOT = 2000
TRAIN_MIN = {'patients': 30, 'sources': 3, 'per_source': 5, 'pairs': 10, 'floor': 0.6}   # F-A11, F-A23
TIERS = {'decide': 30, 'report': 20}                                                     # F-A22 S
# D54 omission report: ImageCAS-X's own presence (centreline >= 5 mm) on the D45 620, counts only
# (experiments/Delta/j1f_r1/census.json, train560 + dev44 + train_open16)
PRIOR_620 = {'D1': 610, 'D2': 356, 'OM1': 538, 'OM2': 227, 'PDA': 605, 'PLB': 600, 'Ramus': 148}
UNDER_RATIO = 0.8                   # a class drawn in fewer than 0.8x ImageCAS-X's share of hearts (upper bound) is flagged
WINDOW_MM = 62.0                    # L2d's search radius (> the last gap step)


def ceil_to(x, step):
    return float(math.ceil(x / step - 1e-9) * step)


# ----------------------------------------------------------------------------------------------- held-out names
class Refusal(SystemExit):
    pass


def read_stem(name):
    """`<case>__r2` -> `<case>` (a SegQueue14 replica is the same volume read again)."""
    base = os.path.basename(os.path.normpath(name))
    if '__r' in base and base.rsplit('__r', 1)[1].isdigit():
        return base.rsplit('__r', 1)[0]
    return base


def patient_of(stem):
    from segtrain import pool_seal
    return pool_seal.ingest_patient(stem) or stem


def source_of(stem):
    return stem.split('__', 1)[0] if '__' in stem else 'unknown'


def classify_names(names, manifest_source=None):
    """Split read names into trainable / D35 / held-out, by patient, before any file is opened.
    Raises Refusal(3) on any sealed pool read (D27, D55 Q-F2-1); Refusal(5) if a guard cannot load."""
    from segtrain import pool_seal
    if manifest_source:
        ps = manifest_source.get('pool_seal') or {}
        if ps.get('mode') == 'acceptance':
            raise Refusal(3)
    seal = pool_seal.load_pool_seal()
    sealed = [n for n in names if seal.is_sealed(read_stem(n))]
    if sealed:
        print(f'REFUSE: {len(sealed)} of {len(names)} read(s) are of sealed pool patients (D27). The J1F-2 freeze '
              'never reads a sealed pool read (D55 Q-F2-1). Re-export without --acceptance-scoring.', flush=True)
        raise Refusal(3)
    try:
        from janusm import guard
        g = guard.load_guard()
    except Exception as exc:  # noqa: BLE001 - fail closed
        print(f'REFUSE: the held-out guard (janusm.guard) cannot load ({exc})', flush=True)
        raise Refusal(5)
    if _sha(D35_PATH) != D35_SHA256:
        print('REFUSE: the D35 list is not the pinned one', flush=True)
        raise Refusal(5)
    d35 = set(json.load(open(D35_PATH))['patients'])
    out = {'trainable': [], 'd35': [], 'held_out': [], 'held_out_reasons': {}}
    for n in names:
        stem = read_stem(n)
        pat = patient_of(stem)
        if pat in d35 or stem in d35:
            out['d35'].append(n)
            continue
        why = g.reason(stem)
        if why:
            out['held_out'].append(n)
            key = why.split(': ', 1)[-1].split(' (')[0].split(',')[0][:60]
            out['held_out_reasons'][key] = out['held_out_reasons'].get(key, 0) + 1
            continue
        out['trainable'].append(n)
    return out


# ----------------------------------------------------------------------------------------------- reading a read
def _mask_path(case_dir, name):
    return os.path.join(case_dir, 'segmentations', name.replace(' ', '_').replace('/', '_') + '.nii.gz')


def read_info(case_dir):
    p = os.path.join(case_dir, 'read.json')
    return json.load(open(p)) if os.path.exists(p) else {}


def bbox_of(case_dirs, pad=3):
    """Union bounding box of every vessel/branch channel of these reads (same grid)."""
    lo = hi = shape = None
    for d in case_dirs:
        for n in VESSELS + tuple(PARENTS):
            p = _mask_path(d, n)
            if not os.path.exists(p):
                continue
            a = np.asarray(nb.load(p).dataobj) > 0
            if shape is None:
                shape = a.shape
            assert a.shape == shape, f'{p}: grid differs'
            if not a.any():
                continue
            idx = np.argwhere(a)
            l, h = idx.min(0), idx.max(0)
            lo = l if lo is None else np.minimum(lo, l)
            hi = h if hi is None else np.maximum(hi, h)
    if lo is None:
        return None, shape
    return tuple(slice(max(int(a) - pad, 0), min(int(b) + pad + 1, s)) for a, b, s in zip(lo, hi, shape)), shape


def load_channels(case_dir, box):
    """{class name: bool array on `box`} for the 4 vessels and 14 branches; zooms. Materials are not loaded."""
    ch, z = {}, None
    for n in VESSELS + tuple(PARENTS):
        p = _mask_path(case_dir, n)
        if os.path.exists(p):
            im = nb.load(p)
            if z is None:
                z = np.array(im.header.get_zooms()[:3], float)
            ch[n] = np.asarray(im.dataobj)[box] > 0
    return ch, z


def labels_d54(ch):
    """Channels -> stage-2 label map (D47 Q4, D54). Returns uint8 map with 255 for unrelated overlaps."""
    names = [n for n in S2NAMES[1:] if n in ch]
    shape = next(iter(ch.values())).shape
    count = np.zeros(shape, np.uint8)
    lab = np.zeros(shape, np.uint8)
    for n in names:
        count += ch[n]
        lab[ch[n]] = V[n]                                    # exact where count == 1
    multi = count > 1
    if multi.any():
        lab[multi] = IGNORE
        for b, ps in PARENTS.items():                        # a branch over its own parent, nothing else -> branch
            if b not in ch:
                continue
            for p in ps:
                if p in ch:
                    lab[(count == 2) & ch[b] & ch[p]] = V[b]
    return lab


def stage1_part(lab):
    """The stage-1 map underneath a stage-2 map: each stage-2 voxel back to its parent's label is not knowable from
    the label alone, so callers use the channels (`stage1_from_channels`)."""
    return np.where(np.isin(lab, STAGE2), 0, lab)


def stage1_from_channels(ch):
    """The read as an ImageCAS-X-like stage-1 reference: stage-1 channels only, the same overlap rule."""
    return labels_d54({n: m for n, m in ch.items() if n not in STAGE2_NAMES})


@contextmanager
def stage2_scorer():
    """The scorer of record with its class tables widened to the 14 branch classes, nothing else changed: the same
    piece, centreline, presence, detection and naming code and constants (F-A28), run on stage-2 values."""
    saved = (J.NAMES, J.BRANCHES, J.PARENT)
    J.NAMES = S2NAMES
    J.BRANCHES = BRANCHES2
    J.PARENT = dict(PARENT_VALUES2)
    try:
        yield J
    finally:
        J.NAMES, J.BRANCHES, J.PARENT = saved


# ----------------------------------------------------------------------------------------------- geometry
def _ostium_seed(mask, z, start=None):
    """Seed points of a vessel's ostium: the voxels touching `start` (e.g. the LM) if any, else the skeleton endpoint
    with the largest radius (the ostium is a vessel's thick end; no aorta exists for pool CTs)."""
    if start is not None and start.any():
        touch = mask & ndi.binary_dilation(start, iterations=2)
        if touch.any():
            return np.argwhere(touch)
    sk = J._skeleton(mask)
    pts = np.argwhere(sk)
    if not len(pts):
        return np.argwhere(mask)[:1]
    nb_ = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3, 3), np.uint8), mode='constant')
    ends = np.argwhere(sk & (nb_ == 2))
    if not len(ends):
        ends = pts
    edt = ndi.distance_transform_edt(mask, sampling=z)
    return ends[[int(np.argmax(edt[tuple(ends.T)]))]]


def proximal(mask, z, mm, start=None):
    if not mask.any():
        return mask
    d = J._geodesic(mask, _ostium_seed(mask, z, start), z)
    return mask & (d <= mm)


def _sn_side(comp, ch):
    """SN component -> 'RCA' or 'LCx' by face contact (RCA on a tie or none), as SegQueue's collapse decides it."""
    ring = ndi.binary_dilation(comp) & ~comp
    r = int((ring & ch.get('RCA', np.zeros_like(comp))).sum())
    l = int((ring & ch.get('LCx', np.zeros_like(comp))).sum())
    return 'LCx' if l > r else 'RCA'


def stolen_runs(skel_group, child_any, z):
    """Lengths (mm) of the 26-connected runs of parent-centreline points inside any stage-2 class: L1r's runs, measured
    as Foxtrot's `runs` (points x mean voxel side)."""
    st = skel_group & child_any
    if not st.any():
        return []
    comp, nc = ndi.label(st, J.S26)
    sizes = np.bincount(comp.ravel())[1:]
    return [float(s * float(np.mean(z))) for s in sizes]


def component_gaps(lab, z):
    """L2d on a read: for each stage-2 26-component of >= 20 voxels, the distance (mm) from its nearest voxel to every
    other coronary voxel of the read (any class, other stage-2 components included). inf when none lies within
    WINDOW_MM."""
    fg = (lab > 0) & (lab != IGNORE)
    s2 = np.isin(lab, STAGE2)
    out = []
    if not s2.any():
        return out
    for c in STAGE2:
        comp, nc = ndi.label(lab == c, J.S26)
        objs = ndi.find_objects(comp)
        for i in range(1, nc + 1):
            sl = objs[i - 1]
            if int((comp[sl] == i).sum()) < J.MIN_PIECE_VOX:
                continue
            r = np.ceil(WINDOW_MM / z).astype(int)
            win = tuple(slice(max(s.start - k, 0), min(s.stop + k, n)) for s, k, n in zip(sl, r, lab.shape))
            me = comp[win] == i
            rest = fg[win] & ~me
            if not rest.any():
                out.append({'class': S2NAMES[c], 'gap_mm': float('inf')}); continue
            d = ndi.distance_transform_edt(~rest, sampling=z)
            out.append({'class': S2NAMES[c], 'gap_mm': round(float(d[me].min()), 3)})
    return out


# ----------------------------------------------------------------------------------------------- one read
def measure_read(case_dir):
    """Everything the freeze needs from one trainable extended read."""
    info = read_info(case_dir)
    row = {'read': os.path.basename(os.path.normpath(case_dir)), 'extended': bool(info.get('extended')),
           'defect': bool(info.get('defect')), 'ticks': bool(info.get('completeGroups'))}
    if not row['extended'] or row['defect']:
        return row
    box, _ = bbox_of([case_dir])
    if box is None:
        row['empty'] = True
        return row
    ch, z = load_channels(case_dir, box)
    lab = labels_d54(ch)
    row['zooms'] = [float(v) for v in z]
    row['ignore_vox'] = int((lab == IGNORE).sum())
    # presence of every branch class, by the scorer of record's definition (centreline >= 5 mm)
    with stage2_scorer():
        pcs = J.pieces_of(lab, z)
        pres = J.presence(pcs)
    row['present'] = {S2NAMES[c]: bool(pres[c]) for c in BRANCHES2}
    row['pieces_len_mm'] = {S2NAMES[c]: [round(p['length_mm'], 2) for p in pcs[c]] for c in STAGE2 if pcs[c]}
    row['no_branch_drawn'] = not any(row['present'].values())
    # L1r on the read: the readers' own child-over-parent runs along the stage-1 centreline
    lab1 = stage1_from_channels(ch)
    tree1 = (lab1 > 0) & (lab1 != IGNORE)
    four = J.collapse4(lab1, z)
    skel = J._skeleton(tree1)
    child_any = np.zeros(lab.shape, bool)
    for n in STAGE2_NAMES:
        if n in ch:
            child_any |= ch[n]
    row['runs'] = {}
    row['cl_pts'] = {}
    row['run_pts'] = {}
    for g, v in GROUPS.items():
        sg = skel & (four == v)
        row['cl_pts'][g] = int(sg.sum())
        st = sg & child_any
        if st.any():
            comp, nc = ndi.label(st, J.S26)
            sizes = np.bincount(comp.ravel())[1:]
            row['runs'][g] = [round(float(s * float(np.mean(z))), 3) for s in sizes]
            row['run_pts'][g] = [int(s) for s in sizes]
        else:
            row['runs'][g], row['run_pts'][g] = [], []
    # L2d on the read
    row['gaps'] = component_gaps(lab, z)
    # band: distance of each group's drawn voxels from its host (quantised to 0.1 mm, as a histogram)
    row['band'] = {}
    row['far_mm'] = {}
    for gname, gd in BAND_GROUPS.items():
        host = np.zeros(lab.shape, bool)
        for h in gd['host']:
            if h in ch:
                host |= ch[h]
        drawn = np.zeros(lab.shape, bool)
        for c in gd['classes']:
            m = lab == V[c]
            if not m.any():
                continue
            if c == 'SN':
                comp, nc = ndi.label(m, J.S26)
                keep = np.zeros_like(m)
                for i in range(1, nc + 1):
                    ci = comp == i
                    if _sn_side(ci, ch) == gd['sn_side']:
                        keep |= ci
                m = keep
            drawn |= m
        if not drawn.any() or not host.any():
            continue
        if gd['prox_mm']:
            host = proximal(host, z, gd['prox_mm'], start=ch.get('LM') if gname == 'pLCx' else None)
            if not host.any():
                continue
        d = ndi.distance_transform_edt(~host, sampling=z)[drawn]
        hist = np.bincount(np.minimum(np.round(d * 10).astype(int), 1000))
        row['band'][gname] = {'n_vox': int(drawn.sum()), 'hist01': hist.tolist()}
        row['far_mm'][gname] = round(float(d.max()), 2)
    row['lab_shape'] = list(lab.shape)
    return row


def interread(pair_dirs):
    """Both directions of the scorer of record on two reads of one volume: per branch class, pooled pieces, detected,
    named, and whether each read has the class present."""
    box, _ = bbox_of(pair_dirs)
    if box is None:
        return None
    labs, z = [], None
    for d in pair_dirs:
        ch, z = load_channels(d, box)
        labs.append(labels_d54(ch))
    out = {'pair': [os.path.basename(os.path.normpath(d)) for d in pair_dirs], 'classes': {}}
    with stage2_scorer():
        s_ab = J.score_case(labs[0], labs[1], z, with_tf1=False)
        s_ba = J.score_case(labs[1], labs[0], z, with_tf1=False)
    for c in BRANCHES2:
        k = S2NAMES[c]
        a, b = s_ab[k], s_ba[k]
        rows = a['pieces'] + b['pieces']
        out['classes'][k] = {'pieces': len(rows), 'detected': sum(r['detected'] for r in rows),
                             'named': sum(r['named'] for r in rows),
                             'present': [bool(a['present_ref']), bool(a['present_pred'])]}
    return out


def presence_only(case_dir):
    """D35 reads (`--d35-tiers`): per-class presence, nothing else is kept."""
    info = read_info(case_dir)
    if not info.get('extended') or info.get('defect'):
        return {'read': os.path.basename(case_dir), 'present': {}}
    box, _ = bbox_of([case_dir])
    if box is None:
        return {'read': os.path.basename(case_dir), 'present': {}}
    ch, z = load_channels(case_dir, box)
    lab = labels_d54(ch)
    with stage2_scorer():
        pres = J.presence(J.pieces_of(lab, z))
    return {'read': os.path.basename(case_dir), 'present': {S2NAMES[c]: bool(pres[c]) for c in BRANCHES2}}


# ----------------------------------------------------------------------------------------------- the freeze rules
def pct_from_hist(hist, q):
    h = np.asarray(hist, float)
    if h.sum() == 0:
        return None
    cdf = np.cumsum(h) / h.sum()
    return float(np.searchsorted(cdf, q / 100.0) / 10.0)


def clopper_upper(k, n, alpha):
    from scipy.stats import beta
    return 1.0 if k >= n else float(beta.ppf(1 - alpha, k + 1, n - k))


def freeze(rows, pairs, raised=(), d35_rows=None):
    rows = [r for r in rows if r.get('extended') and not r.get('defect') and not r.get('empty')]
    res = {'n_reads': len(rows)}
    # 1. the band, per group
    band = {}
    for g in BAND_GROUPS:
        rs = [r for r in rows if g in r.get('band', {})]
        hist = np.zeros(1001)
        for r in rs:
            h = r['band'][g]['hist01']
            hist[:len(h)] += h
        p = pct_from_hist(hist, BAND_Q)
        rw = [pct_from_hist(r['band'][g]['hist01'], BAND_Q) for r in rs]
        if len(rs) >= BAND_MIN_READS and p is not None:
            w = min(max(ceil_to(p, 0.5), BAND_CLAMP[0]), BAND_CLAMP[1])
            status = 'set'
        else:
            w, status = RULED['band_mm'], f'kept (fewer than {BAND_MIN_READS} reads)'
        band[g] = {'width_mm': w, 'status': status, 'reads': len(rs), 'p95_pooled_mm': p,
                   'p95_read_median_mm': float(np.median(rw)) if rw else None,
                   'far_p99_mm': float(np.percentile([r['far_mm'][g] for r in rs if g in r.get('far_mm', {})], 99))
                   if any(g in r.get('far_mm', {}) for r in rs) else None}
    res['band'] = band
    # 2a. L1r's run length
    runs = [x for r in rows for g in GROUPS for x in r['runs'].get(g, [])]
    p99 = float(np.percentile(runs, RUN_Q)) if runs else 0.0
    run_mm = max(RULED['run_mm'], ceil_to(p99, 0.5))
    stop = []
    if run_mm > RUN_STOP_MM:
        stop.append(f'L1r run {run_mm} mm > {RUN_STOP_MM} mm: readers draw ostia over the parent longer than a thief '
                    'is assumed to steal; the PM decides')
    res['l1r_run'] = {'run_mm': run_mm, 'ruled_mm': RULED['run_mm'], 'n_runs': len(runs),
                      'p99_mm': round(p99, 3), 'max_mm': round(max(runs), 3) if runs else 0.0}
    # 2b. the theft line (L1r at the look, K1r in training): the readers' own theft at run_mm, upper bound
    rng = np.random.default_rng(20261128)
    theft = {}
    worst_up = 0.0
    for g in GROUPS:
        num = np.array([sum(p for p, L in zip(r['run_pts'].get(g, []), r['runs'].get(g, [])) if L > run_mm)
                        for r in rows], float)
        den = np.array([r['cl_pts'].get(g, 0) for r in rows], float)
        share = float(num.sum() / den.sum()) if den.sum() else 0.0
        if len(rows):
            idx = rng.integers(0, len(rows), (N_BOOT, len(rows)))
            bs = num[idx].sum(1) / np.maximum(den[idx].sum(1), 1)
            up = float(np.quantile(bs, 0.975))
        else:
            up = 0.0
        worst_up = max(worst_up, up)
        theft[g] = {'share': round(share, 5), 'upper975': round(up, 5)}
    need = THEFT_MARGIN * worst_up
    line = RULED['theft_line'] if need <= RULED['theft_line'] else ceil_to(need, 0.005)
    if line > THEFT_STOP:
        stop.append(f'theft line {line} > {THEFT_STOP}: the readers themselves paint stage-2 classes along the parent')
    res['theft'] = {'line': line, 'ruled': RULED['theft_line'], 'per_group': theft,
                    'rule': f'max(0.02, ceil_0.005({THEFT_MARGIN} x worst upper bound))'}
    # 2c. L2d's gap
    maxgap = [max([x['gap_mm'] for x in r['gaps']], default=0.0) for r in rows]
    rate = {}
    gap_mm = None
    for D in GAP_STEPS:
        k = sum(1 for m in maxgap if m > D)
        rate[str(D)] = {'reads_over': k, 'rate': round(k / len(rows), 4) if rows else 0.0,
                        'upper95': round(clopper_upper(k, len(rows), 0.05), 4) if rows else 1.0}
        if gap_mm is None and rows and k / len(rows) <= GAP_RATE:
            gap_mm = D
    if gap_mm is None:
        gap_mm = GAP_STEPS[-1]
        stop.append(f'L2d: more than {GAP_RATE:.0%} of reads have a stage-2 piece > {GAP_STEPS[-1]} mm from the rest')
    from scipy.stats import binom
    pr = sum(1 for m in maxgap if m > gap_mm) / len(rows) if rows else 0.0
    res['l2d_gap'] = {'gap_mm': gap_mm, 'ruled_mm': RULED['gap_mm'], 'by_step': rate,
                      'false_fail_at_95_of_100': round(float(binom.sf(5, 100, pr)), 4),
                      'stage2_components': sum(len(r['gaps']) for r in rows)}
    # 3. counts and the inter-read floor, per class
    by_pat = {}
    for r in rows:
        stem = read_stem(r['read'])
        by_pat.setdefault(patient_of(stem), {'source': source_of(stem), 'present': set()})
        by_pat[patient_of(stem)]['present'] |= {k for k, v in r['present'].items() if v}
    cls = {}
    for c in BRANCHES2:
        k = S2NAMES[c]
        pats = [p for p, d in by_pat.items() if k in d['present']]
        per_src = {}
        for p in pats:
            per_src[by_pat[p]['source']] = per_src.get(by_pat[p]['source'], 0) + 1
        mult = 1.5 if k in raised else 1.0
        need_p = int(math.ceil(TRAIN_MIN['patients'] * mult))
        need_pairs = TRAIN_MIN['pairs']                       # F-A23 raises the read count only
        pr_ = [q['classes'][k] for q in pairs if q and any(q['classes'][k]['present'])]
        pieces = sum(q['pieces'] for q in pr_)
        named = sum(q['named'] for q in pr_)
        both = [q['present'] for q in (x['classes'][k] for x in pairs if x)]
        floor = named / pieces if pieces else None
        ok_src = sum(1 for v in per_src.values() if v >= TRAIN_MIN['per_source'])
        trainable = (len(pats) >= need_p and ok_src >= TRAIN_MIN['sources'] and len(pr_) >= need_pairs
                     and floor is not None and floor >= TRAIN_MIN['floor'])
        cls[k] = {'stage': 2 if c in STAGE2 else 1, 'patients': len(pats), 'need_patients': need_p,
                  'sources': dict(sorted(per_src.items())), 'sources_ge5': ok_src,
                  'pairs_with_class': len(pr_), 'need_pairs': need_pairs,
                  'floor_det_x_naming': round(floor, 4) if floor is not None else None,
                  'presence_agreement_pairs': round(sum(a == b for a, b in both) / len(both), 4) if both else None,
                  'trainable': bool(trainable) if c in STAGE2 else None}
    res['classes'] = cls
    res['n_patients'] = len(by_pat)
    res['n_pairs'] = sum(1 for q in pairs if q)
    # D54 reports (never deciding)
    omit = {}
    for k, n620 in PRIOR_620.items():
        k_ = sum(1 for r in rows if r['present'].get(k))
        prior = n620 / 620
        up = clopper_upper(k_, len(rows), 0.025) if rows else 1.0
        omit[k] = {'reads_drawn': k_, 'reads': len(rows), 'rate': round(k_ / len(rows), 4) if rows else None,
                   'icx620_rate': round(prior, 4), 'upper975': round(up, 4),
                   'flag_under_drawn': bool(rows) and up < UNDER_RATIO * prior}
    res['d54'] = {'stage1_drawn_vs_icx620': omit,
                  'reads_with_old_ticks': sum(1 for r in rows if r.get('ticks')),
                  'reads_no_branch_drawn': sum(1 for r in rows if r.get('no_branch_drawn')),
                  'ignore_vox_total': int(sum(r.get('ignore_vox', 0) for r in rows))}
    if d35_rows is not None:
        d = {}
        for c in STAGE2:
            k = S2NAMES[c]
            pats = {patient_of(read_stem(r['read'])) for r in d35_rows if r['present'].get(k)}
            n = len(pats)
            d[k] = {'d35_patients': n, 'tier': 'decide' if n >= TIERS['decide'] else
                    'report' if n >= TIERS['report'] else 'counts'}
        res['s_tiers_d35'] = d
    res['stop'] = stop
    return res


# ----------------------------------------------------------------------------------------------- driver
def list_reads(export):
    man = os.path.join(export, 'manifest.json')
    source = {}
    if os.path.exists(man):
        source = json.load(open(man)).get('source', {}) or {}
        if source.get('classes') == 'four':
            print('REFUSE: a --four-class export has no extended classes', flush=True)
            raise Refusal(2)
    names = sorted(d for d in os.listdir(export) if os.path.isdir(os.path.join(export, d)))
    return names, source


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--export', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--np', type=int, default=4)
    ap.add_argument('--d35-tiers', action='store_true')
    ap.add_argument('--raised', nargs='*', default=[], help='classes whose threshold rose 1.5x after a near miss')
    a = ap.parse_args(argv)
    names, source = list_reads(a.export)
    split = classify_names(names, source)                        # refuses before any read file is opened
    if source.get('replicas') != 'all':
        print('NOTE: export not made with --replicas all: no double reads, so no inter-read floor', flush=True)
    tr = split['trainable']
    dirs = [os.path.join(a.export, n) for n in tr]
    with Pool(a.np) as pool:
        rows = pool.map(measure_read, dirs, chunksize=1)
        groups = {}
        for n in tr:
            groups.setdefault(read_stem(n), []).append(n)
        pair_dirs = [[os.path.join(a.export, x) for x in sorted(v)[:2]] for v in groups.values() if len(v) >= 2]
        pairs = pool.map(interread, pair_dirs, chunksize=1)
        d35_rows = pool.map(presence_only, [os.path.join(a.export, n) for n in split['d35']]) if a.d35_tiers else None
    res = freeze(rows, pairs, raised=set(a.raised), d35_rows=d35_rows)
    res['inputs'] = {'export': os.path.abspath(a.export), 'reads_listed': len(names), 'trainable_reads': len(tr),
                     'd35_reads': len(split['d35']), 'held_out_reads': len(split['held_out']),
                     'held_out_reasons': split['held_out_reasons'], 'manifest_source': source,
                     'scorer_sha256': SCORER_SHA256, 'freeze_sha256': _sha(os.path.abspath(__file__)),
                     'raised': sorted(a.raised), 'd35_tiers': bool(a.d35_tiers)}
    res['rules'] = {'ruled': RULED, 'band_clamp': BAND_CLAMP, 'band_min_reads': BAND_MIN_READS, 'band_q': BAND_Q,
                    'run_q': RUN_Q, 'run_stop_mm': RUN_STOP_MM, 'gap_steps': GAP_STEPS, 'gap_rate': GAP_RATE,
                    'theft_margin': THEFT_MARGIN, 'theft_stop': THEFT_STOP, 'train_min': TRAIN_MIN, 'tiers': TIERS}
    blob = json.dumps(res, indent=1, sort_keys=True, default=float)
    open(a.out, 'w').write(blob + '\n')
    rowsp = os.path.splitext(a.out)[0] + '_rows.jsonl'
    with open(rowsp, 'w') as f:
        for r in rows:
            r = {k: v for k, v in r.items() if k != 'band'}
            f.write(json.dumps(r, sort_keys=True) + '\n')
    print_summary(res)
    print('freeze', a.out, 'sha256', _sha(a.out))
    return 4 if res['stop'] else 0


def print_summary(res):
    print(f"reads {res['n_reads']}  patients {res['n_patients']}  double-read pairs {res['n_pairs']}")
    for g, b in res['band'].items():
        print(f"band {g:5s} {b['width_mm']:5.1f} mm  ({b['status']}; reads {b['reads']}, P95 {b['p95_pooled_mm']})")
    print(f"L1r run   {res['l1r_run']['run_mm']} mm  (P99 of {res['l1r_run']['n_runs']} reader runs "
          f"{res['l1r_run']['p99_mm']} mm, max {res['l1r_run']['max_mm']})")
    print(f"theft line {res['theft']['line']}  (per group upper: "
          + ', '.join(f"{g} {v['upper975']}" for g, v in res['theft']['per_group'].items()) + ')')
    print(f"L2d gap   {res['l2d_gap']['gap_mm']} mm  (false-fail at 95 of 100: "
          f"{res['l2d_gap']['false_fail_at_95_of_100']})")
    for k, c in res['classes'].items():
        if c['stage'] == 2:
            print(f"{k:6s} patients {c['patients']:3d}/{c['need_patients']}  sources>=5 {c['sources_ge5']}  "
                  f"pairs {c['pairs_with_class']}/{c['need_pairs']}  floor {c['floor_det_x_naming']}  "
                  f"trainable {c['trainable']}")
    if 's_tiers_d35' in res:
        print('D35 tiers', {k: v['tier'] for k, v in res['s_tiers_d35'].items()})
    for s in res['stop']:
        print('STOP', s)


# ----------------------------------------------------------------------------------------------- self-test
def selftest():
    z = np.array([0.5, 0.5, 0.5])
    sh = (40, 40, 40)
    lad = np.zeros(sh, bool); lad[20, 20, 2:38] = True; lad = ndi.binary_dilation(lad, iterations=2)
    lcx = np.zeros(sh, bool); lcx[10, 5:35, 10] = True; lcx = ndi.binary_dilation(lcx, iterations=1)
    s1 = np.zeros(sh, bool); s1[20:34, 20, 15] = True; s1 = ndi.binary_dilation(s1, iterations=1)
    ch = {'LAD': lad, 'LCx': lcx, 'S1': s1}
    lab = labels_d54(ch)
    ok = []
    ok.append(('S1 over its parent LAD trains as S1 (D47 Q4)', bool((lab[s1 & lad] == V['S1']).all())))
    ok.append(('LAD alone is LAD: no {LAD, S1-S3} set exists (D54)', bool((lab[lad & ~s1] == V['LAD']).all())))
    s2 = np.zeros(sh, bool); s2[10, 18:22, 10] = True                       # S2 drawn over the LCx: unrelated
    lab2 = labels_d54({**ch, 'S2': s2})
    ok.append(('S2 over the LCx is ignore', bool((lab2[s2 & lcx] == IGNORE).all())))
    both = s1 & ndi.binary_dilation(s1, iterations=0)
    lab3 = labels_d54({**ch, 'S2': s1.copy()})
    ok.append(('S1 and S2 on the same voxels: ignore', bool((lab3[s1 & ~lad] == IGNORE).all()) and both.any()))
    pda = np.zeros(sh, bool); pda[10, 8:12, 10:14] = True
    lab4 = labels_d54({'LCx': lcx, 'PDA': pda})
    ok.append(('PDA over the LCx trains as PDA (contact parents RCA, LCx)', bool((lab4[pda & lcx] == V['PDA']).all())))
    ok.append(('values stay within 0..18 and 255', set(np.unique(lab4)) <= set(range(19)) | {IGNORE}))
    # ticks change nothing: labels_d54 takes no tick argument; measure_read only counts them
    import inspect
    ok.append(('no complete-group input to the label builder', 'complete' not in inspect.signature(labels_d54).parameters
               and 'complete' not in inspect.getsource(labels_d54).lower()))
    # the stage-2 scorer wrapper restores the scorer of record's tables
    before = (tuple(J.NAMES), J.BRANCHES, dict(J.PARENT))
    with stage2_scorer():
        p = J.presence(J.pieces_of(lab, z))
    ok.append(('S1 present by the scorer of record (>= 5 mm)', bool(p[V['S1']])))
    ok.append(('scorer tables restored', before == (tuple(J.NAMES), J.BRANCHES, dict(J.PARENT))))
    # stolen runs: the S1 crossing of the LAD centreline is short
    tree1 = labels_d54({'LAD': lad, 'LCx': lcx}) > 0
    sk = J._skeleton(tree1)
    runs = stolen_runs(sk & lad, s1, z)
    ok.append((f'S1 junction run is short ({runs} mm)', len(runs) >= 1 and max(runs) <= 3.0))
    # gaps: an S1 piece 10 mm away from everything
    far = np.zeros(sh, bool); far[2:6, 36, 36] = True; far = ndi.binary_dilation(far, iterations=1)
    lab5 = labels_d54({**ch, 'S3': far})
    g = {x['class']: x['gap_mm'] for x in component_gaps(lab5, z)}
    ok.append((f'S3 island gap measured ({g.get("S3")} mm)', g.get('S3', 0) > 5))
    # refusal of a sealed pool patient before any file is opened
    from segtrain import pool_seal
    seal = pool_seal.load_pool_seal()
    sealed_name = sorted(seal.patients)[0]
    try:
        classify_names([sealed_name, 'StandinA__p0001'])
        ok.append(('a sealed pool patient is refused', False))
    except Refusal as e:
        ok.append(('a sealed pool patient is refused (exit 3)', e.code == 3))
    try:
        classify_names(['StandinA__p0001'], {'pool_seal': {'mode': 'acceptance'}})
        ok.append(('an --acceptance-scoring export is refused', False))
    except Refusal as e:
        ok.append(('an --acceptance-scoring export is refused (exit 3)', e.code == 3))
    d35 = json.load(open(D35_PATH))['patients'][0]
    sp = classify_names([d35, d35 + '__r2', 'StandinA__p0001'])
    ok.append(('a D35 patient never reaches the trainable set', sp['d35'] == [d35, d35 + '__r2']
               and sp['trainable'] == ['StandinA__p0001']))
    for name, good in ok:
        print('ok  ' if good else 'FAIL', name)
    assert all(g for _, g in ok)
    print('selftest ok')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'selftest':
        selftest()
    else:
        try:
            sys.exit(main())
        except Refusal as e:
            sys.exit(e.code)
