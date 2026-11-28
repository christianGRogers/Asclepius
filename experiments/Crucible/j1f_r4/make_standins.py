"""Janus 1-F round 4 (Crucible): 620-derived stand-in extended reads, written as a SegQueue14 export.

No pool read exists that this round may open (and the sealed pool never may). The freeze script is therefore tested on
stand-ins built from D45 TRAINING labels only (ImageCAS-X, fetched by fetch_standin_cases.py):
  * the vessels and the eight traced branches as ImageCAS-X draws them, through the scorer of record's
    `stage1_labels` (F-A28), named as SegQueue names them (PDA/PLB keep their names, D47 Q1);
  * the six untraced classes as synthetic tubes leaving their host, painted CHILD OVER PARENT (the tube starts on the
    host's centreline, so its first ~radius of length lies inside the host's lumen, D47 Q4):
      S1-S3   off the LAD at 15/30/45 % of its arc, aimed at the nearest PDA voxel (the septum), 10-45 mm;
      Conus   off the RCA at 4 mm of arc, aimed at the proximal LAD (the RV outflow), 12-30 mm;
      SN      off the RCA at 8 mm (or, in 1 of 4 cases, off the LCx at 6 mm), away from the tree, 12-30 mm;
      RMA     off the RCA at 50 % of its arc, away from the tree, 15-40 mm;
    each class is left undrawn in some cases (hash-chosen), so D54's "confirmed absent" has negatives to count;
  * 4 cases draw S2 in two pieces with a 4-8 mm gap (D47 Q7: traced beyond the seed);
  * 16 cases get a second read `<name>__r2` (D11/D23's two reads): the same tree with each tube's length x U(0.7, 1),
    radius +-0.15 mm, and each stage-2 class dropped with p = 0.15 (a reader who did not draw it: under D54 that read
    says "absent");
  * 2 reads are extended with no branch drawn (one calcified plaque blob: D53's plaque-only work), 2 are four-class.
Names are `Standin<A-D>__c####` (four synthetic sources). The layout is segqueue14-export's: <case>/segmentations/
<Class>.nii.gz (all 21 for an extended read, empties included, D53), <case>/read.json, and manifest.json at the root
built by segqueue.manifest with a pool-seal record of mode 'exclude'. No CT is written (the freeze never opens one).
Usage: python make_standins.py <icx_label_dir> <out_export_dir>
"""
import hashlib, json, os, sys
import numpy as np, nibabel as nb
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path[:0] = [HERE, os.path.join(ROOT, 'trillium', 'janus1f', 'lib'), os.path.join(ROOT, 'src')]
import j1f_scorer as S  # noqa
from segqueue14 import labels as SQ  # noqa
from segtrain import pool_seal  # noqa
import j1f2_freeze as F  # noqa
from fetch_standin_cases import chosen, TRAIN620_SHA256  # noqa

SALT = 'asclepius-j1f-r4-crucible-standin-geometry:'
S1NAME = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA', 5: 'D1', 6: 'D2', 7: 'D3', 8: 'OM1', 9: 'OM2', 10: 'Ramus',
          11: 'PDA', 12: 'PLB'}


def u01(*key):
    return int(hashlib.sha256((SALT + ':'.join(map(str, key))).encode()).hexdigest()[:12], 16) / 16 ** 12


def tube(p0, u, length, r, z, shape):
    p1 = p0 + length * u
    lo = np.maximum(np.floor((np.minimum(p0, p1) - r) / z).astype(int), 0)
    hi = np.minimum(np.ceil((np.maximum(p0, p1) + r) / z).astype(int) + 1, shape)
    m = np.zeros(shape, bool)
    if np.any(hi <= lo):
        return m
    g = np.stack(np.meshgrid(*[np.arange(a, b) for a, b in zip(lo, hi)], indexing='ij'), -1).reshape(-1, 3)
    x = g * z - p0
    t = np.clip(x @ u, 0, length)
    d = np.linalg.norm(x - t[:, None] * u[None], axis=1)
    g = g[d <= r]
    m[tuple(g.T)] = True
    return m


def unit(v):
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-6 else None


def at_arc(mask, skel, z, src, frac=None, mm=None):
    arc = F.arc_from(mask, z, src)
    fin = np.isfinite(arc)
    if not fin.any():
        return None
    La = float(arc[fin].max())
    target = frac * La if frac is not None else min(mm, La * 0.9)
    cand = np.argwhere(mask & skel & (np.abs(arc - target) < 1.5))
    if not len(cand):
        cand = np.argwhere(mask & (np.abs(arc - target) < 1.5))
    return cand[0] if len(cand) else None


def build_case(path, cid):
    im = nb.load(path); z = np.array(im.header.get_zooms()[:3], float)
    icx = np.asarray(im.dataobj).astype(np.uint8)
    sl0 = ndi.find_objects((icx > 0).astype(np.uint8))[0]
    mg = np.ceil(48 / z).astype(int)
    sl = tuple(slice(max(s.start - m, 0), min(s.stop + m, n)) for s, m, n in zip(sl0, mg, icx.shape))
    icx = icx[sl]
    lab, _ = S.stage1_labels(icx, z)
    shape = lab.shape
    masks = {S1NAME[v]: lab == v for v in S1NAME}
    tree = (lab > 0) & (lab != S.IGNORE)
    skel = S._skeleton(tree)
    centroid = np.argwhere(tree).mean(0) * z
    lad, rca, lcx, lm = masks['LAD'], F.largest(masks['RCA']), F.largest(masks['LCx']), masks['LM']
    pda = np.argwhere(masks['PDA']) * z
    plan = {}
    # septals
    if lad.any():
        touch = lad & ndi.binary_dilation(lm, F.S26, iterations=2)
        src = np.argwhere(touch) if touch.any() else [F.ostium_end(lad, z)]
        for k, (nm, fr) in enumerate((('S1', .15), ('S2', .30), ('S3', .45))):
            if u01(cid, nm, 'skip') < (0.05, 0.15, 0.45)[k]:
                continue
            c0 = at_arc(lad, skel, z, src, frac=fr)
            if c0 is None:
                continue
            p0 = c0 * z
            tgt = pda[np.argmin(np.linalg.norm(pda - p0, axis=1))] if len(pda) else centroid
            u = unit(tgt - p0)
            if u is None:
                continue
            plan[nm] = (p0, u, 10 + 35 * u01(cid, nm, 'L'), 0.6 + 0.3 * u01(cid, nm, 'r'))
    # RCA side
    if rca.sum() > 10:
        o = F.ostium_end(rca, z)
        lad_prox = at_arc(lad, skel, z, [F.ostium_end(lad, z)], mm=10) if lad.any() else None
        c = at_arc(rca, skel, z, [o], mm=4)
        if c is not None and lad_prox is not None and u01(cid, 'Conus', 'skip') >= 0.25:
            u = unit(lad_prox * z - c * z)
            if u is not None:
                plan['Conus'] = (c * z, u, 12 + 18 * u01(cid, 'Conus', 'L'), 0.6 + 0.3 * u01(cid, 'Conus', 'r'))
        sn_lcx = u01(cid, 'SN', 'side') < 0.25 and lcx.sum() > 10
        if u01(cid, 'SN', 'skip') >= 0.35:
            if sn_lcx:
                touch = lcx & ndi.binary_dilation(lm | lad, F.S26, iterations=2)
                c = at_arc(lcx, skel, z, np.argwhere(touch) if touch.any() else [F.ostium_end(lcx, z)], mm=6)
            else:
                c = at_arc(rca, skel, z, [o], mm=8)
            if c is not None:
                u = unit(c * z - centroid)
                if u is not None:
                    u = unit(u + np.array([0.0, 0.0, 0.6]))
                    plan['SN'] = (c * z, u, 12 + 18 * u01(cid, 'SN', 'L'), 0.6 + 0.2 * u01(cid, 'SN', 'r'))
        c = at_arc(rca, skel, z, [o], frac=0.5)
        if c is not None and u01(cid, 'RMA', 'skip') >= 0.3:
            u = unit(c * z - centroid)
            if u is not None:
                plan['RMA'] = (c * z, u, 15 + 25 * u01(cid, 'RMA', 'L'), 0.6 + 0.3 * u01(cid, 'RMA', 'r'))
    return masks, plan, z, shape


def paint(masks, plan, z, shape, gap=None, perturb=None):
    out = {k: v.copy() for k, v in masks.items()}
    for nm, (p0, u, L, r) in plan.items():
        if perturb:
            if perturb(nm, 'drop') < 0.15:
                continue
            L = L * (0.7 + 0.3 * perturb(nm, 'L')); r = max(0.45, r + 0.3 * (perturb(nm, 'r') - 0.5))
        t = tube(p0, u, L, r, z, shape)
        if gap and nm == 'S2':
            a, w = 0.5 * L, gap
            t &= ~tube(p0 + a * u, u, w, r + 1.0, z, shape)
        out[nm] = t
    return out


def write_read(out_dir, name, masks, z, kind, src_affine_z):
    seg = os.path.join(out_dir, name, 'segmentations'); os.makedirs(seg, exist_ok=True)
    aff = np.diag(list(src_affine_z) + [1.0])
    if kind == 'four':
        names = list(SQ.NAMES)
        stack = np.stack([masks.get(n, np.zeros_like(masks['LAD'])).astype(np.uint8) for n in F.VESSELS + F.BRANCHES
                          if n in masks])
        present = [n for n in F.VESSELS + F.BRANCHES if n in masks]
        four = SQ.collapse_to_four(stack, present)
        arrays = {n: four[i] for i, n in enumerate(SQ.NAMES)}
    else:
        names = list(SQ.ALL_NAMES)
        zero = np.zeros_like(masks['LAD'], np.uint8)
        arrays = {n: masks.get(n, zero).astype(np.uint8) for n in names}
    for n, a in arrays.items():
        nb.save(nb.Nifti1Image(a.astype(np.uint8), aff), os.path.join(seg, n.replace(' ', '_') + '.nii.gz'))
    rj = {'classes': names, 'extended': kind != 'four', 'completeGroups': [], 'written': 'read',
          'exportedRole': 'annotator', 'defect': False, 'defectReason': None}
    json.dump(rj, open(os.path.join(out_dir, name, 'read.json'), 'w'), indent=2, sort_keys=True)


def main(icx_dir, out):
    ids = chosen(40)
    os.makedirs(out, exist_ok=True)
    names = []
    for i, cid in enumerate(ids):
        src = 'Standin' + 'ABCD'[int(u01(cid, 'source') * 4)]
        name = f'{src}__{cid}'
        path = os.path.join(icx_dir, '%d.coronary.nii.gz' % (int(cid[1:]) + 1))
        masks, plan, z, shape = build_case(path, cid)
        if i >= 36:   # 2 nobranch extended, 2 four-class
            kind = 'nobranch' if i < 38 else 'four'
            m = dict(masks)
            if kind == 'nobranch':
                m = {k: masks[k] for k in ('LM', 'LAD', 'LCx', 'RCA')}
                for b in F.STAGE1_BRANCHES:   # the reader left every branch in its parent
                    par = F.FIXED_PARENT.get(b, 'RCA')
                    m[par] = m[par] | masks[b]
                c = np.argwhere(masks['LAD'])[len(np.argwhere(masks['LAD'])) // 5]
                blob = np.zeros(shape, bool); blob[tuple(c)] = True
                m['Calcified plaque'] = ndi.binary_dilation(blob, iterations=2)
            write_read(out, name, m, z, kind, z)
            names.append(name)
            print(name, kind, flush=True)
            continue
        gap = 4 + 4 * u01(cid, 'gap') if i % 10 == 3 else None
        a = paint(masks, plan, z, shape, gap=gap)
        write_read(out, name, a, z, 'branch', z)
        names.append(name)
        if i < 16:
            b = paint(masks, plan, z, shape, gap=gap, perturb=lambda nm, w: u01(cid, 'r2', nm, w))
            write_read(out, name + '__r2', b, z, 'branch', z)
            names.append(name + '__r2')
        print(name, sorted(plan), 'gap' if gap else '', flush=True)
    from segqueue.manifest import build
    man = build(out, cases=sorted(names), source={
        'kind': 'segqueue14-export', 'label_set': SQ.LABEL_SET_NAME, 'replicas': 'all', 'classes': 'read',
        'pool_seal': {'sha256': pool_seal.SEAL_SHA256, 'mode': 'exclude', 'excluded_cases': 0, 'included_reads': 0},
        'standins': 'Crucible j1f_r4 make_standins.py; D45 training labels only', 'train620_sha256': TRAIN620_SHA256})
    man.write(out)
    print('wrote', len(names), 'reads')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
