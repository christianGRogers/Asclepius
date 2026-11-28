"""Janus 1-F stage 2 (J1F-2): the freeze. Crucible, round 4 (track 1-F, #303).

Reads ONE SegQueue14 export (`segqueue14-export --out <dir> --replicas all`, never `--acceptance-scoring`, never
`--four-class`) and writes every number [[Janus 1-F Round 3]] §5 leaves to the freeze, by rules fixed here before any
read exists:
  1. the band per class group (F-A21): the 95th percentile of the drawn stage-2 voxels' distance from their host,
     reads weighted equally, >= MIN_BAND_READS reads per group, clamped to [BAND_MIN_MM, BAND_MAX_MM]; otherwise the
     provisional BAND_PROVISIONAL_MM, flagged;
  2. L1r's run length (F-A30): the 99th percentile of the ostium runs a read paints over its parent's centreline;
     kept at 3 mm when that is <= 3 mm, else raised to it (rounded up to 0.5 mm) up to RUN_MAX_MM, else STOP;
  3. K1r's and L1r's 0.02 (F-A30): a model that reproduces the reads must pass it (pooled, one-sided 1.25 % bootstrap
     upper bound over patients), else STOP;
  4. L2d's 30 mm (F-A30): the smallest of L2D_CANDIDATES_MM such that at most L2D_MAX_SHARE of reads hold a stage-2
     component farther than it from every other coronary voxel, else STOP;
  5. read counts per class (F-A23): trainable patients with the class drawn (presence >= 5 mm), from >= 3 sources with
     >= 5 each; the line is 30, or 45 for a class named in --raised (F-A23's 1.5x rule);
  6. the inter-read floor per class (F-A23, amended for D54): on >= 10 trainable patients with two branch-drawn
     extended reads and the class in either, pooled named/pieces in both directions >= 0.6 AND presence agreement
     >= 0.6, measured with the scorer of record (F-A28) through a slot map.

D54 (2026-11-27): in an extended read a branch class the annotator did not draw is CONFIRMED ABSENT: its voxels are
background for that branch (or the parent where the parent is drawn), never ignore. `d54_target` is the one
definition of a stage-2 training label from an extended read; the J1F-2 `prep` imports it (as `stage1_labels` is the
one stage-1 converter, F-A28). There are no complete groups anywhere in this file.
  * one claim -> that class; a branch over its OWN parent -> the branch (D47 Q4); any other overlap -> IGNORE;
  * materials (stent, plaques) are dropped first: a vessel voxel also marked plaque stays vessel, a voxel marked only
    as a material is background (as D46 Q8 for 1-L);
  * PDA, PLB and SN: "own parent" is the vessel the component leaves, by SegQueue's own contact rule (D47 Q1).
An extended read with NO branch class drawn (extended through plaque work, D53, or a flagged case, D47 Q6) is
classed 'nobranch' and handled by NO_BRANCH_POLICY ('four': read as a four-class read for branches; Crucible v4 Q-F4-1,
recommended; the lead may choose otherwise). 'nobranch' and four-class reads never enter 1-6.

Guards (refusals exit 3 BEFORE any file of the offending case is opened):
  * any case name of a D27 sealed pool patient (segtrain.pool_seal, sha256-pinned; refused by patient) -- D55 Q-F2-1:
    sealed extended reads are scored only inside D27's single look, never here;
  * a manifest whose pool seal mode is 'acceptance', or with no pool-seal record, or written `--four-class`;
  * an annotator benchmark case (D43) or an ImageCAS case name;
  * a scorer of record or labels.py whose sha256 is not F-A28's / F-A17's.
Excluded, counted, never opened: D35 decision patients (Delta r10 list, sha256-pinned), the seal's extension-order
reserve, and the 74 header-spacing-suspect volumes (mm statistics would be wrong; D29).

Output: <out>/freeze.json (every number, its rule, its inputs' counts), <out>/j1f2_band.json (the band alone, whose
sha256 is printed and posted), <out>/per_read.jsonl (no voxel data; geometry summaries per read). Usage:
  python j1f2_freeze.py --export <dir> --out <dir> [--raised S1,SN] [--np 8]
  python j1f2_freeze.py --standins --export <dir> --out <dir>    # stand-in exports only (names Standin*__c####)
"""
import argparse
import hashlib
import json
import os
import re
import sys
from multiprocessing import Pool

import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path[:0] = [os.path.join(ROOT, 'trillium', 'janus1f', 'lib'), os.path.join(ROOT, 'src')]
import j1f_scorer as S  # noqa: E402  (checks tf1.py and labels.py by sha256 at import)
from segqueue14 import labels as SQ  # noqa: E402
from segtrain import pool_seal  # noqa: E402

# ------------------------------------------------------------------------------------------------ pins
SCORER_SHA256 = '5221032f3dc086d686b63fa946149a215ac00738a87fd9669d7faa15962b2e5b'   # F-A28
LABELS_SHA256 = '5f69b5bef59ad1346c5877a43c65daf7bdf1329b0ca7e427b6addd55d0000a4b'   # F-A17
D35_RELPATH = 'experiments/Delta/r10/d35_decision_set_proposal.json'                  # Round 10, the list of record
D35_SHA256 = '1a75fe41ffe44aa37c884b723c066a6b8cd3669164e0c670b6439028c2b966b1'
POOL_RELPATH = 'configs/segqueue14/pool-2026-10.txt'
SPACING_SUSPECT_MARK = '# --- header spacing suspect'

# ------------------------------------------------------------------------------------------------ classes
VESSELS = ('LM', 'LAD', 'LCx', 'RCA')
STAGE1_BRANCHES = ('D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB')
STAGE2 = ('S1', 'S2', 'S3', 'SN', 'Conus', 'RMA')
BRANCHES = STAGE1_BRANCHES + STAGE2                     # the 14 of D44/D45
MATERIALS = tuple(SQ.MATERIALS)
#: J1F-2's label values (scorer convention: IGNORE 255; on disk the trainer writes max + 1 = 19, as F-A29).
VALUE = {'LM': 1, 'LAD': 2, 'LCx': 3, 'RCA': 4, 'D1': 5, 'D2': 6, 'D3': 7, 'OM1': 8, 'OM2': 9, 'Ramus': 10,
         'PDA': 11, 'PLB': 12, 'S1': 13, 'S2': 14, 'S3': 15, 'SN': 16, 'Conus': 17, 'RMA': 18}
IGNORE = 255
IGNORE_ON_DISK = 19
FIXED_PARENT = {'D1': 'LAD', 'D2': 'LAD', 'D3': 'LAD', 'S1': 'LAD', 'S2': 'LAD', 'S3': 'LAD',
                'OM1': 'LCx', 'OM2': 'LCx', 'Ramus': 'LCx', 'Conus': 'RCA', 'RMA': 'RCA'}
CONTACT = ('SN', 'PDA', 'PLB')                           # parent decided per component (D47 Q1)
NO_BRANCH_POLICY = 'four'                                # Q-F4-1 (B); 'absent' = D54 literally; 'exclude'

# ------------------------------------------------------------------------------------------------ rules
BAND_PROVISIONAL_MM = 15.0
BAND_MIN_MM, BAND_MAX_MM = 8.0, 25.0
BAND_Q = 95.0
MIN_BAND_READS = 10
PROX_RCA_MM, PROX_LCX_MM = 30.0, 20.0                    # F-A21's proximal hosts
BAND_GROUPS = ('LAD', 'RCA', 'pRCA', 'pLCx')             # S1-S3; RMA; SN(RCA) + Conus; SN(LCx)
RUN_MM = 3.0
RUN_Q = 99.0
RUN_MAX_MM = 5.0                                         # half the 10 mm thief run (Foxtrot v3)
L1R_LINE = 0.02
BOUND_Q = 98.75                                          # one-sided 1.25 %
N_BOOT = 2000
BOOT_SEED = 20261128
L2D_CANDIDATES_MM = (30.0, 40.0, 50.0)
L2D_MAX_SHARE = 0.01
MIN_COMPONENT_VOX = 20                                   # = S.MIN_PIECE_VOX
LONG_SEPTAL_MM = 40.0                                    # Round 3 §7's trigger, reported
COUNT_LINE, COUNT_RAISED = 30, 45
MIN_SOURCES, MIN_PER_SOURCE = 3, 5
FLOOR_LINE, FLOOR_MIN_PAIRS = 0.6, 10
PRESENCE_MM = S.PRESENCE_MM
#: The scorer of record scores classes 5..12 only; each class is scored in a slot whose name is fixed here.
SLOT_STAGE1 = {c: VALUE[c] for c in STAGE1_BRANCHES}
SLOT_STAGE2 = {'S1': 5, 'S2': 6, 'S3': 7, 'SN': 8, 'Conus': 9, 'RMA': 10}

S26 = np.ones((3, 3, 3), bool)
_READ_SUFFIX = re.compile(r'__r\d+$')


class Refuse(SystemExit):
    def __init__(self, msg):
        print('REFUSE: ' + msg, file=sys.stderr)
        super().__init__(3)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ D54 label
def contact_parents(masks):
    """{name: per-voxel parent mask decision} for SN/PDA/PLB: a dict name -> (RCA part, LCx part), by SegQueue's
    `assign_contact_branches` against the vessels with their fixed branches folded in."""
    shape = next(iter(masks.values())).shape
    par = {p: masks.get(p, np.zeros(shape, bool)).astype(bool).copy() for p in ('RCA', 'LCx')}
    for b, p in FIXED_PARENT.items():
        if p in par and b in masks:
            par[p] |= masks[b].astype(bool)
    out = {}
    for b in CONTACT:
        m = masks.get(b)
        if m is None or not m.any():
            continue
        d = SQ.assign_contact_branches([(b, m)], par)['masks']
        out[b] = {'RCA': d['RCA'] & m.astype(bool), 'LCx': d['LCx'] & m.astype(bool)}
    return out


def d54_target(masks):
    """An extended read's stage-2 training label (D54 + D47 Q4 + D40). `masks`: {class name: 0/1 array}, any subset
    of the 21 (absent names are empty = confirmed absent). Returns uint8 in VALUE's space, IGNORE where unresolved."""
    names = [n for n in VESSELS + BRANCHES if n in masks]
    shape = masks[names[0]].shape
    claims = np.zeros(shape, np.uint8)
    for n in names:
        claims += masks[n].astype(bool)
    out = np.zeros(shape, np.uint8)
    for n in names:
        m = masks[n].astype(bool) & (claims == 1)
        out[m] = VALUE[n]
    multi = claims >= 2
    if not multi.any():
        return out
    out[multi] = IGNORE
    cp = contact_parents(masks)
    for b in BRANCHES:
        if b not in masks:
            continue
        mb = masks[b].astype(bool) & multi
        if not mb.any():
            continue
        # voxels claimed by exactly the branch and its own parent: the branch wins (D47 Q4)
        if b in CONTACT:
            parts = cp.get(b, {})
            for p in ('RCA', 'LCx'):
                own = parts.get(p, np.zeros(shape, bool)) & multi
                if p in masks:
                    own &= masks[p].astype(bool) & (claims == 2)
                    out[own] = VALUE[b]
        else:
            p = FIXED_PARENT[b]
            if p in masks:
                own = mb & masks[p].astype(bool) & (claims == 2)
                out[own] = VALUE[b]
    return out


def read_kind(read_json, masks):
    """'four' (no extended class), 'branch' (extended, >= 1 branch class drawn) or 'nobranch' (extended, none)."""
    extended = bool(read_json.get('extended')) or any(n in masks for n in BRANCHES + MATERIALS)
    if not extended:
        return 'four'
    drawn = [b for b in BRANCHES if b in masks and masks[b].any()]
    return 'branch' if drawn else 'nobranch'


# ------------------------------------------------------------------------------------------------ geometry
def arc_from(mask, z, src):
    from skimage.graph import MCP_Geometric
    d, _ = MCP_Geometric(np.where(mask, 1.0, np.inf), sampling=tuple(z)).find_costs([tuple(s) for s in src])
    d[~mask] = np.inf
    return d


def ostium_end(mask, z):
    """The end of a vessel's longest geodesic with the larger lumen (the ostium end; Foxtrot v2's heuristic)."""
    pts = np.argwhere(mask)
    d1 = arc_from(mask, z, pts[:1]); a = np.unravel_index(np.argmin(np.where(np.isfinite(d1), -d1, np.inf)), mask.shape)
    d2 = arc_from(mask, z, [a]); b = np.unravel_index(np.argmin(np.where(np.isfinite(d2), -d2, np.inf)), mask.shape)
    e = ndi.distance_transform_edt(mask, sampling=z)
    return a if e[a] >= e[b] else b


def largest(mask):
    if not mask.any():
        return mask
    comp, n = ndi.label(mask, S26)
    if n == 1:
        return mask
    return comp == (np.argmax(np.bincount(comp.ravel())[1:]) + 1)


def hosts(masks, z):
    """F-A21's hosts: LAD group (LAD + D1-D3), RCA, proximal RCA (30 mm), proximal LCx (20 mm from the LM)."""
    shape = next(iter(masks.values())).shape
    g = lambda n: masks[n].astype(bool) if n in masks else np.zeros(shape, bool)
    lad = g('LAD') | g('D1') | g('D2') | g('D3')
    rca, lcx, lm = g('RCA'), g('LCx'), g('LM')
    out = {'LAD': lad, 'RCA': rca, 'pRCA': np.zeros(shape, bool), 'pLCx': np.zeros(shape, bool)}
    r = largest(rca)
    if r.sum() >= 2:
        arc = arc_from(r, z, [ostium_end(r, z)])
        out['pRCA'] = r & (arc <= PROX_RCA_MM)
    c = largest(lcx)
    if c.sum() >= 2:
        touch = c & ndi.binary_dilation(lm | lad, S26, iterations=2)
        src = np.argwhere(touch) if touch.any() else [ostium_end(c, z)]
        arc = arc_from(c, z, src)
        out['pLCx'] = c & (arc <= PROX_LCX_MM)
    return out


def class_length(mask, skel, z):
    pts = np.argwhere(mask & skel)
    return S._graph_length(pts, np.asarray(z, float)) if len(pts) else 0.0


def run_sizes(stolen):
    """Foxtrot's `runs` (F-A30): the point counts of the 26-connected runs of stolen centreline points. A run's
    length in mm is its point count x the mean voxel side."""
    if not stolen.any():
        return []
    comp, nc = ndi.label(stolen, S26)
    return [int(s) for s in np.bincount(comp.ravel())[1:]]


def measure_read(masks, z):
    """Every per-read quantity the freeze needs, as plain numbers. `masks` cropped to the tree's box."""
    z = np.asarray(z, float)
    shape = next(iter(masks.values())).shape
    g = lambda n: masks[n].astype(bool) if n in masks else np.zeros(shape, bool)
    tree = np.zeros(shape, bool)
    for n in VESSELS + BRANCHES:
        tree |= g(n)
    skel = S._skeleton(tree)
    tgt = d54_target(masks)
    cp = contact_parents(masks)
    row = {'present': {}, 'length_mm': {}, 'band': {}, 'runs': {}, 'l1r': {}, 'l2d_gap_mm': [], 'ignore_vox': int((tgt == IGNORE).sum())}
    for b in BRANCHES:
        L = class_length(g(b), skel, z)
        row['length_mm'][b] = round(L, 2)
        row['present'][b] = L >= PRESENCE_MM
    # band: distance of drawn stage-2 voxels (outside the host) from the host, per group
    H = hosts(masks, z)
    sn_rca = cp.get('SN', {}).get('RCA', np.zeros(shape, bool))
    sn_lcx = cp.get('SN', {}).get('LCx', np.zeros(shape, bool))
    drawn = {'LAD': g('S1') | g('S2') | g('S3'), 'RCA': g('RMA'), 'pRCA': sn_rca | g('Conus'), 'pLCx': sn_lcx}
    for grp in BAND_GROUPS:
        d = drawn[grp] & ~H[grp]
        if d.sum() < MIN_COMPONENT_VOX or not H[grp].any():
            continue
        dist = ndi.distance_transform_edt(~H[grp], sampling=z)[d]
        row['band'][grp] = [round(float(x), 3) for x in np.percentile(dist, np.arange(0, 101))]   # 101 quantiles
    # L1r on the read: parent-group centreline (what ImageCAS-X would trace: parent + stage-1 children) taken by a
    # stage-2 class in the D54 training label
    s2v = [VALUE[c] for c in STAGE2]
    groups = {'LAD': g('LAD') | g('D1') | g('D2') | g('D3'),
              'LCx': g('LCx') | g('OM1') | g('OM2') | g('Ramus'),
              'RCA': g('RCA')}
    for b in ('PDA', 'PLB'):
        for p in ('RCA', 'LCx'):
            groups['LCx' if p == 'LCx' else 'RCA'] |= cp.get(b, {}).get(p, np.zeros(shape, bool))
    for grp, m in groups.items():
        pts = skel & m
        stolen = pts & np.isin(tgt, s2v)
        rs = run_sizes(stolen)
        row['runs'][grp] = [round(float(x * np.mean(z)), 3) for x in rs]
        row['l1r'][grp] = {'pts': int(pts.sum()), 'stolen': int(stolen.sum()), 'run_sizes_pts': rs}
    # L2d on the read: each stage-2 26-component's gap to every other coronary voxel (all classes, other components)
    s2 = np.isin(tgt, s2v)
    comp, nc = ndi.label(s2, S26)
    objs = ndi.find_objects(comp)
    mg = np.ceil((max(L2D_CANDIDATES_MM) + 1.0) / z).astype(int)
    fg = tree
    for i in range(1, nc + 1):
        sl = objs[i - 1]
        box = tuple(slice(max(s.start - m, 0), min(s.stop + m, n)) for s, m, n in zip(sl, mg, shape))
        p = comp[box] == i
        if p.sum() < MIN_COMPONENT_VOX:
            continue
        other = fg[box] & ~p
        gap = float(ndi.distance_transform_edt(~other, sampling=z)[p].min()) if other.any() else 99.0
        row['l2d_gap_mm'].append(round(min(gap, 99.0), 2))
    return row


# ------------------------------------------------------------------------------------------------ the floor
def slot_maps(masks):
    """Two 1-F maps (values 1..12) for the scorer of record: A scores the 8 stage-1 branches in their own slots, B the
    6 stage-2 classes in SLOT_STAGE2; in each, every branch not scored is folded into its parent by SegQueue's
    collapse (D47 Q1), and a scored branch wins over its parent."""
    shape = next(iter(masks.values())).shape
    out = []
    for scored, slot in ((STAGE1_BRANCHES, SLOT_STAGE1), (STAGE2, SLOT_STAGE2)):
        rest = {n: m for n, m in masks.items() if n in VESSELS + BRANCHES and n not in scored}
        names = list(rest)
        four = SQ.collapse_to_four(np.stack([rest[n].astype(np.uint8) for n in names]), names) if names else \
            np.zeros((4,) + shape, np.uint8)
        lab = np.zeros(shape, np.uint8)
        for k in range(4):
            lab[four[k] != 0] = k + 1
        for b in scored:
            if b in masks:
                lab[masks[b].astype(bool)] = slot[b]
        out.append(lab)
    return out


def floor_pair(ma, mb, z):
    """Reader against reader, both directions, every branch class: pieces, named, presence of each read."""
    A, B = slot_maps(ma), slot_maps(mb)
    res = {}
    for k, (scored, slot) in enumerate(((STAGE1_BRANCHES, SLOT_STAGE1), (STAGE2, SLOT_STAGE2))):
        ab = S.score_case(A[k], B[k], z, with_tf1=False)
        ba = S.score_case(B[k], A[k], z, with_tf1=False)
        for c in scored:
            key = S.NAMES[slot[c]]
            ra, rb = ab[key], ba[key]
            res[c] = {'pieces': len(ra['pieces']) + len(rb['pieces']),
                      'named': sum(p['named'] for p in ra['pieces']) + sum(p['named'] for p in rb['pieces']),
                      'present_a': bool(ra['present_ref']), 'present_b': bool(rb['present_ref'])}
    return res


# ------------------------------------------------------------------------------------------------ io
def load_read(case_dir):
    import nibabel as nb
    rj = json.load(open(os.path.join(case_dir, 'read.json')))
    seg = os.path.join(case_dir, 'segmentations')
    files = {f[:-len('.nii.gz')].replace('_', ' '): f for f in os.listdir(seg) if f.endswith('.nii.gz')}
    masks, z = {}, None
    for name, f in files.items():
        if name not in VESSELS + BRANCHES + MATERIALS:
            continue
        im = nb.load(os.path.join(seg, f))
        z = z if z is not None else np.array(im.header.get_zooms()[:3], float)
        m = np.asarray(im.dataobj) != 0
        masks[name] = m
    # materials dropped first (D46 Q8's analogue): only vessels and branches below
    kind = read_kind(rj, masks)
    keep = {n: m for n, m in masks.items() if n in VESSELS + BRANCHES}
    tree = np.zeros(next(iter(keep.values())).shape, bool)
    for m in keep.values():
        tree |= m
    if not tree.any():
        return rj, kind, {}, z
    sl = ndi.find_objects(tree.astype(np.uint8))[0]
    sl = tuple(slice(max(s.start - 3, 0), s.stop + 3) for s in sl)
    return rj, kind, {n: m[sl] for n, m in keep.items()}, z


def patient_of(name):
    stem = _READ_SUFFIX.sub('', name)
    return pool_seal.ingest_patient(stem) or stem


def holdouts(seal):
    p = os.path.join(ROOT, D35_RELPATH)
    if sha256_file(p) != D35_SHA256:
        raise Refuse(f'{D35_RELPATH} is not the D35 list of record ({D35_SHA256[:12]})')
    d = json.load(open(p))
    d35 = set(d['patients']) | {pool_seal.ingest_patient(v[:-len('.nii.gz')]) for v in d['volumes']}
    reserve = set(seal.extension_order)
    reserve |= {pool_seal.ingest_patient(str(v)) for v in seal.extension_order if pool_seal.ingest_patient(str(v))}
    suspect, on = set(), False
    for ln in open(os.path.join(ROOT, POOL_RELPATH)):
        if ln.startswith(SPACING_SUSPECT_MARK):
            on = True; continue
        if ln.startswith('# ---'):
            on = False
        if on and ln.strip() and not ln.startswith('#'):
            suspect.add(ln.strip()[:-len('.nii.gz')] if ln.strip().endswith('.nii.gz') else ln.strip())
    return d35, reserve, suspect


def screen(export, seal, standins=False):
    """Every refusal and exclusion, from names and the manifest only. Returns (kept names, excluded counts)."""
    if sha256_file(S.__file__) != SCORER_SHA256:
        raise Refuse('the scorer is not the scorer of record (F-A28)')
    if sha256_file(SQ.__file__) != LABELS_SHA256:
        raise Refuse('src/segqueue14/labels.py is not F-A17\'s pinned file')
    man = os.path.join(export, 'manifest.json')
    if not os.path.isfile(man):
        raise Refuse('no manifest.json: not a segqueue14-export tree')
    src = json.load(open(man)).get('source', {})
    ps = src.get('pool_seal') or {}
    if src.get('kind') != 'segqueue14-export':
        raise Refuse(f"manifest source kind {src.get('kind')!r}")
    if ps.get('mode') != 'exclude' or ps.get('sha256') != pool_seal.SEAL_SHA256:
        raise Refuse(f"the export's pool seal record is {ps!r}: only an export that left the D27 seal out "
                     f"(mode 'exclude', seal {pool_seal.SEAL_SHA256[:12]}) may set a stage-2 number (D55 Q-F2-1)")
    if src.get('classes') == 'four':
        raise Refuse('the export was written --four-class: extended reads were collapsed')
    names = sorted(n for n in os.listdir(export) if os.path.isdir(os.path.join(export, n)))
    sealed = [why for why in (seal.reason(n) for n in names) if why]
    if sealed:
        raise Refuse(f'{len(sealed)} sealed pool case(s) in the export (D27, D55 Q-F2-1); first: {sealed[0]}')
    bad = [n for n in names if n.startswith('annotator_benchmark_') or n.startswith('ImageCAS__')]
    if bad:
        raise Refuse(f'{len(bad)} benchmark/ImageCAS case(s): {bad[0]}')
    if standins and any(not n.startswith('Standin') for n in names):
        raise Refuse('--standins on an export with real pool names')
    if not standins and any(n.startswith('Standin') for n in names):
        raise Refuse('stand-in cases in a real export')
    d35, reserve, suspect = holdouts(seal)
    kept, excl = [], {'d35': 0, 'reserve': 0, 'spacing_suspect': 0}
    for n in names:
        p, stem = patient_of(n), _READ_SUFFIX.sub('', n)
        if p in d35:
            excl['d35'] += 1
        elif p in reserve or stem in reserve:
            excl['reserve'] += 1
        elif stem in suspect:
            excl['spacing_suspect'] += 1
        else:
            kept.append(n)
    return kept, excl


def one(args):
    export, name = args
    rj, kind, masks, z = load_read(os.path.join(export, name))
    row = {'name': name, 'patient': patient_of(name), 'source': name.split('__')[0], 'kind': kind,
           'zooms': [round(float(v), 5) for v in z] if z is not None else None}
    if kind == 'branch' and masks:
        row.update(measure_read(masks, z))
    return row


def pair(args):
    export, na, nb_ = args
    # two reads of one volume share the CT grid; their trees' boxes differ, so both are cropped on the union
    _, _, ma, z = load_read_union(os.path.join(export, na), os.path.join(export, nb_))
    mb = ma.pop('__other__')
    return {'a': na, 'b': nb_, 'res': floor_pair(ma, mb, z)}


def load_read_union(da, db):
    import nibabel as nb
    out = []
    for d in (da, db):
        seg = os.path.join(d, 'segmentations'); m = {}
        for f in os.listdir(seg):
            n = f[:-len('.nii.gz')].replace('_', ' ')
            if f.endswith('.nii.gz') and n in VESSELS + BRANCHES:
                im = nb.load(os.path.join(seg, f)); z = np.array(im.header.get_zooms()[:3], float)
                m[n] = np.asarray(im.dataobj) != 0
        out.append(m)
    tree = np.zeros(next(iter(out[0].values())).shape, bool)
    for m in out:
        for v in m.values():
            tree |= v
    sl = ndi.find_objects(tree.astype(np.uint8))[0]
    sl = tuple(slice(max(s.start - 3, 0), s.stop + 3) for s in sl)
    a = {n: v[sl] for n, v in out[0].items()}
    a['__other__'] = {n: v[sl] for n, v in out[1].items()}
    return None, 'branch', a, z


# ------------------------------------------------------------------------------------------------ rules applied
def wquantile(quantiles_by_read, q):
    """The q-th percentile of the drawn voxels pooled over reads, each read weighted equally: every read is its 101
    quantiles, so a long branch counts as much as a short one, not by its voxel count."""
    v = np.concatenate([np.asarray(x, float) for x in quantiles_by_read]) if quantiles_by_read else np.array([])
    return float(np.percentile(v, q)) if len(v) else None


def boot_upper(num, den, q=BOUND_Q, n=N_BOOT, seed=BOOT_SEED):
    num, den = np.asarray(num, float), np.asarray(den, float)
    if den.sum() == 0:
        return None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(num), size=(n, len(num)))
    r = num[idx].sum(1) / np.maximum(den[idx].sum(1), 1)
    return float(np.percentile(r, q))


def decide(rows, pairs, raised=()):
    br = [r for r in rows if r['kind'] == 'branch']
    out = {'reads': {k: sum(r['kind'] == k for r in rows) for k in ('branch', 'nobranch', 'four')},
           'no_branch_policy': NO_BRANCH_POLICY, 'stop': []}
    # 1. band
    band = {}
    for g in BAND_GROUPS:
        v = [r['band'][g] for r in br if g in r.get('band', {})]
        if len(v) >= MIN_BAND_READS:
            raw = wquantile(v, BAND_Q)
            band[g] = {'mm': round(min(max(raw, BAND_MIN_MM), BAND_MAX_MM), 2), 'raw_mm': round(raw, 2),
                       'reads': len(v), 'reset': True}
        else:
            band[g] = {'mm': BAND_PROVISIONAL_MM, 'raw_mm': None, 'reads': len(v), 'reset': False}
    out['band'] = band
    # 2. L1r run length
    allruns = [x for r in br for g in r.get('runs', {}) for x in r['runs'][g]]
    p99 = float(np.percentile(allruns, RUN_Q)) if allruns else 0.0
    if p99 <= RUN_MM:
        run = RUN_MM
    elif p99 <= RUN_MAX_MM:
        run = float(np.ceil(p99 * 2) / 2)
    else:
        run = None
        out['stop'].append(f'L1r: 99th percentile ostium run {p99:.2f} mm > {RUN_MAX_MM} mm; a ruling must re-set it')
    out['l1r_run'] = {'mm': run, 'p99_mm': round(p99, 3), 'max_mm': round(max(allruns), 3) if allruns else 0.0,
                      'runs': len(allruns)}
    # 3. L1r / K1r 0.02 on read-faithful predictions, per group, pooled over patients
    l1 = {}
    for g in ('LAD', 'LCx', 'RCA'):
        num, den = [], []
        for r in br:
            e = r['l1r'][g]
            th = run if run is not None else RUN_MM
            num.append(sum(s for s in e['run_sizes_pts'] if s * np.mean(r['zooms']) > th))
            den.append(e['pts'])
        ub = boot_upper(num, den)
        l1[g] = {'point': round(sum(num) / max(sum(den), 1), 5), 'upper': None if ub is None else round(ub, 5)}
        if ub is not None and ub > L1R_LINE:
            out['stop'].append(f'L1r/K1r: read-faithful {g} upper bound {ub:.4f} > {L1R_LINE}')
    out['l1r_k1r'] = {'line': L1R_LINE, 'kept': not any(s.startswith('L1r/K1r') for s in out['stop']), 'groups': l1}
    # 4. L2d
    gaps = [max(r['l2d_gap_mm']) if r.get('l2d_gap_mm') else 0.0 for r in br]
    l2 = None
    shares = {}
    for t in L2D_CANDIDATES_MM:
        shares[t] = float(np.mean([gp > t for gp in gaps])) if gaps else 0.0
        if l2 is None and shares[t] <= L2D_MAX_SHARE:
            l2 = t
    if l2 is None:
        out['stop'].append(f'L2d: {shares[L2D_CANDIDATES_MM[-1]]:.3f} of reads leave a gap > {L2D_CANDIDATES_MM[-1]} mm')
    s_len = [r['length_mm'][c] for r in br for c in ('S1', 'S2', 'S3') if r['present'][c]]
    out['l2d'] = {'mm': l2, 'share_by_candidate': {str(k): round(v, 4) for k, v in shares.items()},
                  'max_gap_mm': round(max(gaps), 2) if gaps else 0.0,
                  'septal_len_p95_mm': round(float(np.percentile(s_len, 95)), 1) if s_len else None,
                  'septals_over_40mm': int(sum(x > LONG_SEPTAL_MM for x in s_len))}
    # 5. counts
    counts = {}
    for c in BRANCHES:
        pos, neg = {}, set()
        for r in br:
            (pos.setdefault(r['patient'], r['source']) if r['present'][c] else neg.add(r['patient']))
        neg -= set(pos)
        by_src = {}
        for p, s in pos.items():
            by_src[s] = by_src.get(s, 0) + 1
        line = COUNT_RAISED if c in raised else COUNT_LINE
        ok = len(pos) >= line and sum(v >= MIN_PER_SOURCE for v in by_src.values()) >= MIN_SOURCES
        counts[c] = {'positive_patients': len(pos), 'absent_patients': len(neg), 'by_source': by_src, 'line': line,
                     'met': ok}
    out['counts'] = counts
    # 6. floor
    floor = {}
    for c in BRANCHES:
        pc = [p['res'][c] for p in pairs if p['res'][c]['present_a'] or p['res'][c]['present_b']]
        pcs = sum(x['pieces'] for x in pc); nm = sum(x['named'] for x in pc)
        agree = sum(x['present_a'] == x['present_b'] for x in pc)
        stat = nm / pcs if pcs else None
        pres = agree / len(pc) if pc else None
        ok = len(pc) >= FLOOR_MIN_PAIRS and stat is not None and stat >= FLOOR_LINE and pres >= FLOOR_LINE
        floor[c] = {'pairs': len(pc), 'detect_x_naming': None if stat is None else round(stat, 4),
                    'presence_agreement': None if pres is None else round(pres, 4), 'met': ok}
    out['floor'] = floor
    out['trainable'] = [c for c in STAGE2 if counts[c]['met'] and floor[c]['met']]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--export', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--raised', default='', help='classes whose count line is 1.5x after a near miss (F-A23)')
    ap.add_argument('--np', type=int, default=4)
    ap.add_argument('--standins', action='store_true')
    a = ap.parse_args(argv)
    seal = pool_seal.load_pool_seal()
    kept, excl = screen(a.export, seal, a.standins)
    raised = tuple(x for x in a.raised.split(',') if x)
    assert all(x in STAGE2 for x in raised), raised
    os.makedirs(a.out, exist_ok=True)
    with Pool(a.np) as pool:
        rows = pool.map(one, [(a.export, n) for n in kept])
    by_pat = {}
    for r in rows:
        if r['kind'] == 'branch':
            by_pat.setdefault(r['patient'], []).append(r['name'])
    jobs = [(a.export, v[0], v[1]) for v in (sorted(v) for v in by_pat.values()) if len(v) >= 2]
    with Pool(a.np) as pool:
        pairs = pool.map(pair, jobs)
    res = decide(rows, pairs, raised)
    res.update({'script_sha256': sha256_file(os.path.abspath(__file__)), 'scorer_sha256': SCORER_SHA256,
                'seal_sha256': seal.sha256, 'd35_sha256': D35_SHA256, 'excluded': excl,
                'manifest_sha256': sha256_file(os.path.join(a.export, 'manifest.json')),
                'standins': bool(a.standins), 'raised': list(raised)})
    with open(os.path.join(a.out, 'per_read.jsonl'), 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    band = {g: v['mm'] for g, v in res['band'].items()}
    bp = os.path.join(a.out, 'j1f2_band.json')
    with open(bp, 'w') as f:
        json.dump({'band_mm': band, 'groups': {'LAD': 'S1-S3 around LAD+D1-D3', 'RCA': 'RMA around the RCA',
                                               'pRCA': 'SN (off RCA) and Conus around the first 30 mm of the RCA',
                                               'pLCx': 'SN (off LCx) around the first 20 mm of the LCx'}}, f,
                  indent=1, sort_keys=True)
    res['band_sha256'] = sha256_file(bp)
    with open(os.path.join(a.out, 'freeze.json'), 'w') as f:
        json.dump(res, f, indent=1, sort_keys=True)
    print(json.dumps({k: res[k] for k in ('reads', 'excluded', 'band', 'l1r_run', 'l1r_k1r', 'l2d', 'trainable',
                                          'stop', 'band_sha256', 'script_sha256')}, indent=1, sort_keys=True))
    for c in BRANCHES:
        print(c, 'count', res['counts'][c]['positive_patients'], 'absent', res['counts'][c]['absent_patients'],
              'met' if res['counts'][c]['met'] else '-', '| floor', res['floor'][c])
    return 4 if res['stop'] else 0


if __name__ == '__main__':
    sys.exit(main())
