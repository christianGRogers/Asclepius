"""Janus 1-F round 4 (Atlas): Foxtrot's round-2 stage-2 loss check (`experiments/Foxtrot/j1f_r2/dice_terms.py`) re-run
under D54 (an undrawn branch class in an extended read is confirmed absent).

Foxtrot's extended-read sample had no "complete" flag (D47 Q3), so its LAD-group voxels carried the set
{LAD-group, S1} and the ImageCAS-X band {bg, S1} stayed on its background. Under D54 an extended read is a full label:
LAD-group voxels are the singleton {LAD-group}, background is {bg}, the drawn septal is {S1}. Both samples are built
here on the same cases and scored with Foxtrot's own `terms` (leaf, ignore and merged Dice; marginal CE), unchanged.
Scenarios as Foxtrot's: A right (tube -> S1), B miss (tube -> LAD-group), C sprawl (S1 at 0.5 on every LAD-group
voxel), D intrude (OM1 at 0.5 on every LAD-group voxel).
Data: ImageCAS-X labels of D45 training cases only (fetch_subset.py's hash-chosen subset; the first n by id).
Usage: python dice_terms_d54.py <label_dir> <out.json> [n_cases]
"""
import json, os, sys
import numpy as np, nibabel as nb
from scipy import ndimage as ndi

FOX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../Foxtrot/j1f_r2')
sys.path.insert(0, FOX)
import dice_terms as DT  # noqa: E402  (Foxtrot's terms(), C = 5 channels)
L = DT.L
TRAIN = DT.TRAIN


def case(path):
    cid = 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1); assert cid in TRAIN
    im = nb.load(path); z = np.array(im.header.get_zooms()[:3], float)
    raw = np.asarray(im.dataobj).astype(np.uint8)
    lab, _ = L.map13(raw[L.crop(raw, 4)], z)
    lad = lab == 2
    pts = np.argwhere(lad); c0 = pts[len(pts) // 3]
    h = np.round(32 / z).astype(int)
    sl = tuple(slice(max(c - hh, 0), c + hh) for c, hh in zip(c0, h))
    lab = lab[sl]; lad = lab == 2
    grp = np.isin(lab, [2, 5, 6, 7]); om1 = lab == 8; oth = (lab > 0) & ~grp & ~om1 & (lab != 255)
    dS = ndi.distance_transform_edt(~lad, sampling=z)
    p0 = np.argwhere(lad)[np.argmin(np.linalg.norm((np.argwhere(lad) - np.array(lab.shape) / 2) * z, axis=1))] * z
    u = -(np.argwhere(lab > 0).mean(0) * z - p0); u = u / (np.linalg.norm(u) + 1e-9)
    grid = np.stack(np.meshgrid(*[np.arange(s) * zz for s, zz in zip(lab.shape, z)], indexing='ij'), -1)
    v = grid - p0
    tube = (np.linalg.norm(v - np.clip(v @ u, 0, 30)[..., None] * u, axis=-1) <= .6) & (lab == 0) & \
           ((v @ u) > 0) & ((v @ u) <= 30)
    C, n = DT.C, lab.size
    f = lambda m: m.reshape(-1)
    base = np.zeros((C, n)); base[0] = 1 - 4e-4; base[1:] = 1e-4

    def put(P, m, k, val):
        mm = f(m); P[:, mm] = (1 - val) / (C - 1); P[k, mm] = val
    P0 = base.copy(); put(P0, grp, 1, .9); put(P0, om1, 3, .9); put(P0, oth, 4, .9)
    S_icx = np.zeros((C, n), bool)
    S_icx[0] = f(lab == 0); S_icx[2] |= f((lab == 0) & (dS <= DT.W))
    S_icx[1] = f(grp); S_icx[3] = f(om1); S_icx[4] = f(oth); S_icx[:, f(lab == 255)] = True
    # round 2 (no flag): Foxtrot's extended sample, unchanged
    S_old = S_icx.copy(); S_old[:, f(tube)] = False; S_old[2, f(tube)] = True; S_old[2, f(grp)] = True
    # D54: a full label. Tube {S1}; LAD-group {LAD-group}; background {bg}; ignore stays ignore
    S_d54 = np.zeros((C, n), bool)
    S_d54[0] = f((lab == 0) & ~tube); S_d54[2] = f(tube); S_d54[1] = f(grp); S_d54[3] = f(om1); S_d54[4] = f(oth)
    S_d54[:, f(lab == 255)] = True
    assert (S_d54.sum(0)[f(lab != 255)] == 1).all()                       # every labelled voxel a singleton
    PA = P0.copy(); put(PA, tube, 2, .9)
    PB = P0.copy(); put(PB, tube, 1, .9)
    g = f(grp)
    PC = P0.copy(); PC[2, g] = .5; PC[1, g] = .4; PC[0, g] = .1 / 3; PC[3, g] = .1 / 3; PC[4, g] = .1 / 3; put(PC, tube, 2, .9)
    PD = P0.copy(); PD[3, g] = .5; PD[1, g] = .4; PD[0, g] = .1 / 3; PD[2, g] = .1 / 3; PD[4, g] = .1 / 3; put(PD, tube, 2, .9)
    sc = (('A_right', PA), ('B_miss', PB), ('C_sprawl', PC), ('D_intrude', PD))
    return {'case': cid, 'tube_vox': int(tube.sum()),
            'old': {k: DT.terms(P, S_old) for k, P in sc}, 'd54': {k: DT.terms(P, S_d54) for k, P in sc}}


if __name__ == '__main__':
    d, outp = sys.argv[1], sys.argv[2]; k = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    files = sorted((x for x in os.listdir(d) if x.endswith('.nii.gz')), key=lambda s: int(s.split('.')[0]))
    files = [x for x in files if 'c%04d' % (int(x.split('.')[0]) - 1) in TRAIN][:k]
    res = [case(os.path.join(d, x)) for x in files]
    names = ['LADgrp', 'S1', 'OM1', 'other']
    summ = {}
    for rule in ('old', 'd54'):
        for s in res[0][rule]:
            summ[f'{rule}:{s}'] = {o: dict(zip(names, np.mean([r[rule][s][o] for r in res], 0).round(4).tolist()))
                                   for o in ('leaf', 'ignore', 'merged')}
            summ[f'{rule}:{s}']['ce'] = round(float(np.mean([r[rule][s]['ce'] for r in res])), 5)
    json.dump({'cases': res, 'mean': summ}, open(outp, 'w'), indent=1)
    for k2, v in summ.items():
        print(k2, 'leaf', v['leaf'], 'ce', v['ce'])
