"""Janus 1-F round 3 (Delta): one pass over the D45 620 training label maps (never a locked, sealed or quality-0 case).

Per case:
  1. the converter of record (j1f_labels.map13): its counts (F-A18 / F-A26's expected line);
  2. the scorer of record's reference pieces (j1f_scorer.pieces_of), in census_r2.jsonl's format, so Atlas's
     gate_sim.py can be re-run on them (ruling §5 item 1: does the scorer count what F-A15 was simulated on?);
  3. SegQueue's collapse (j1f_scorer.collapse4) against territory.to_four (D25) outside "Other" and 255 (F-A18's check),
     with SegQueue's fallback counts (F-A17: 0 expected);
  4. stage-2 proxies for F-A22 (ruling §5 item 5). ImageCAS-X has no stage-2 class, so its own traced side branches
     stand in for them: on the LAD, D1-D3 (for S1-S3); on the LCx, OM1, OM2, Ramus; on the RCA, PDA and PLB (for
     Conus, RMA, SN). The "prediction" is the reference with the stand-ins relabelled as stage-2 classes, and each
     stand-in bled k = 0, 1, 2 voxels (26-dilation) into the traced vessel it touches (an ostium painted too wide).
       L1 numerator/denominator per host group: host-trunk centreline points (skeleton of the whole tree, inside the
          trunk class) that the prediction labels as a stage-2 class / all host-trunk centreline points.
       L2: per stand-in group, the largest distance (mm) from a stage-2 voxel to the nearest stage-1 voxel (the rest
          of the tree) -- the ruling's literal L2 -- and the same for stage-2 voxels in a 26-component that touches
          no stage-1 voxel (the island form, proposed).
       K1 numerator/denominator per stand-in group: stage-2 voxels inside ImageCAS-X's traced lumen of another class
          / all stage-2 voxels.
Labels only, CPU. Usage: python census620.py <icx620_dir> <split_j1l.json> <out.jsonl> [n_proc]
"""
import hashlib, json, os, sys
from multiprocessing import Pool

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '../../../trillium/icx4/lib'))
import j1f_scorer as S      # noqa: E402
import j1f_labels as L      # noqa: E402
import territory            # noqa: E402

S26 = np.ones((3, 3, 3), bool)
# host trunk value -> stand-in classes (1-F values)
GROUPS = {'LAD': (2, (5, 6, 7)), 'LCx': (3, (8, 9, 10)), 'RCA': (4, (11, 12))}
BLEEDS = (0, 1, 2)


def stage2_proxies(lab, z, skel):
    out = {}
    valid = lab != S.IGNORE
    traced = (lab > 0) & valid
    for g, (trunk, proxies) in GROUPS.items():
        pm = np.isin(lab, proxies)
        if not pm.any():
            out[g] = None
            continue
        tr_cl = skel & (lab == trunk)
        n_cl = int(tr_cl.sum())
        res = {'trunk_cl_pts': n_cl}
        for k in BLEEDS:
            s2 = pm.copy()
            if k:
                s2 |= ndi.binary_dilation(pm, S26, iterations=k) & traced & ~pm
            stage1 = traced & ~s2
            r = {'theft_pts': int((tr_cl & s2).sum()),
                 's2_vox': int(s2.sum()), 's2_in_traced': int((s2 & ~pm).sum())}
            if stage1.any():
                bb = ndi.find_objects((s2 | stage1).astype(np.uint8))[0]
                d = ndi.distance_transform_edt(~stage1[bb], sampling=z)
                r['far_mm'] = round(float(d[s2[bb]].max()), 2)
                comp, nc = ndi.label(s2[bb], S26)
                touch = ndi.binary_dilation(stage1[bb], S26)
                isl = np.zeros_like(s2[bb])
                for i in range(1, nc + 1):
                    ci = comp == i
                    if not (ci & touch).any():
                        isl |= ci
                r['island_far_mm'] = round(float(d[isl].max()), 2) if isl.any() else 0.0
            res[f'bleed{k}'] = r
        out[g] = res
    return out


def one(path):
    c = 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1)
    im = nib.load(path)
    icx = np.asarray(im.dataobj).astype(np.uint8)
    z = np.array(im.header.get_zooms()[:3], float)
    nz = np.argwhere(icx > 0)                    # crop to the tree's box + 8 voxels (labels only; nothing is lost)
    lo, hi = np.maximum(nz.min(0) - 8, 0), nz.max(0) + 9
    icx = icx[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    lab, info = L.map13(icx, z)
    st = {}
    c4 = S.collapse4(lab, z, stats=st)
    ref4 = territory.to_four(icx, z)
    keep = (icx != 14) & (lab != S.IGNORE)
    mm = (c4 != ref4) & keep
    tree = (lab > 0) & (lab != S.IGNORE)
    skel = S._skeleton(tree)
    sp = np.asarray(z, float)
    pcs = {k: S._pieces(lab, k, skel, sp, np.isin(lab, S.PARENT[k])) for k in S.BRANCHES}
    return {'case': c, 'zooms': z.tolist(), 'other': info,
            'collapse_mismatch_vox_nonother': int(mm.sum()),
            'collapse_mismatch_other_vox': int(((c4 != ref4) & (icx == 14) & (lab != S.IGNORE)).sum()),
            'ignore_vox': int((lab == S.IGNORE).sum()),
            'contact': {k: v for k, v in st.items() if k != 'perClass'},
            'pieces': {S.NAMES[k]: [{'vox': p['vox'], 'len': round(p['length_mm'], 2)} for p in v]
                       for k, v in pcs.items()},
            'stage2': stage2_proxies(lab, z, skel)}


if __name__ == '__main__':
    icx, split, out = sys.argv[1:4]
    npr = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    sp = json.load(open(split))
    train = sorted(sp['train620'])
    assert hashlib.sha256('\n'.join(train).encode()).hexdigest() == \
        '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
    assert not set(train) & set(sp['locked100'])
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)['case'] for l in open(out)}
    paths = [os.path.join(icx, f'{int(c[1:]) + 1}.coronary.nii.gz') for c in train if c not in done]
    with Pool(npr, maxtasksperchild=10) as p, open(out, 'a') as f:
        for i, r in enumerate(p.imap_unordered(one, paths)):
            f.write(json.dumps(r) + '\n'); f.flush()
            if i % 25 == 0:
                print(i, r['case'], flush=True)
