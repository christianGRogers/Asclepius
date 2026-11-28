"""Janus 1-F round 4 (Crucible): Foxtrot's round-2 `dice_terms.py` re-run under D54 (CPU, D45 training labels only).

Foxtrot's script built the extended-read sample WITHOUT D47 Q3's "complete" flag: the LAD group's voxels were the set
{LAD-group, S1} and the background near the LAD was the band set {bg, S1}. D54 withdraws the tick and makes an undrawn
branch class confirmed absent in every extended read, so the same sample is now fully labelled: the LAD group is the
singleton LAD-group, the background is the singleton bg, and the only set left in an extended read is D40/D47 Q4's
IGNORE on unresolved overlaps. ImageCAS-X's sample is unchanged (band set {bg, S1} within W of the LAD).
This script computes both labellings on the same 64 mm patches and the same scripted predictions:
  A right   the drawn septal tube predicted S1 (0.9);
  B miss    the tube predicted LAD-group (0.9)               -- a missed septal;
  C sprawl  S1 at 0.5 on every LAD-group voxel                -- a head that eats its parent;
  F phantom S1 (0.9) on a 30 mm tube in a read that drew NO septal there -- painting an absent branch;
with marginal CE (-log of the set's summed probability) and the three Dice terms of F-A11/F-A21 (leaf, as adopted;
ignore; merged). Channels: 0 bg, 1 LAD-group (LAD, D1-D3), 2 S1, 3 OM1, 4 other traced.
Cases: the 10 stand-in cases with the smallest sha256('asclepius-j1f-r4-crucible-dice:' + id), training only.
Usage: python dice_terms_d54.py <icx_label_dir> <out.json>
"""
import hashlib, json, os, sys
import numpy as np, nibabel as nb
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path[:0] = [HERE, os.path.join(ROOT, 'trillium', 'janus1f', 'lib')]
import j1f_scorer as S  # noqa
from fetch_standin_cases import chosen  # noqa
EPS, W, C = 1e-5, 15.0, 5


def dice(P, G, keep):
    out = []
    for k in range(1, C):
        p, g = P[k][keep[k]], G[k][keep[k]]
        out.append((2 * (p * g).sum() + EPS) / max(g.sum() + p.sum() + EPS, 1e-8))
    return np.array(out)


def terms(P, sets):
    single = sets.sum(0) == 1
    G = (sets & single[None]).astype(float)
    res = {'leaf': dice(P, G, ~(sets & ~single[None])),
           'ignore': dice(P, G, np.broadcast_to(single[None], sets.shape))}
    mass = (P * sets).sum(0)
    res['merged'] = dice(np.where(sets, mass[None], P), sets.astype(float), np.ones_like(sets))
    ce = -np.log(np.clip(mass, 1e-12, None)).mean()
    return {k: (1 - v).round(4).tolist() for k, v in res.items()} | {'ce': round(float(ce), 6)}


def tube_mask(lab, lad, z, p0, length, r, away=1.0):
    u = -(np.argwhere(lab > 0).mean(0) * z - p0) * away; u = u / (np.linalg.norm(u) + 1e-9)
    grid = np.stack(np.meshgrid(*[np.arange(s) * zz for s, zz in zip(lab.shape, z)], indexing='ij'), -1)
    v = grid - p0; t = v @ u
    return (np.linalg.norm(v - np.clip(t, 0, length)[..., None] * u, axis=-1) <= r) & (lab == 0) & (t > 0) & (t <= length)


def case(path, cid):
    im = nb.load(path); z = np.array(im.header.get_zooms()[:3], float)
    raw = np.asarray(im.dataobj).astype(np.uint8)
    lab, _ = S.stage1_labels(raw, z)
    lad = lab == 2
    pts = np.argwhere(lad); c0 = pts[len(pts) // 3]
    h = np.round(32 / z).astype(int)
    sl = tuple(slice(max(c - hh, 0), c + hh) for c, hh in zip(c0, h))
    lab = lab[sl]; lad = lab == 2
    grp = np.isin(lab, [2, 5, 6, 7]); om1 = lab == 8; oth = (lab > 0) & ~grp & ~om1 & (lab != 255)
    dS = ndi.distance_transform_edt(~lad, sampling=z)
    L = np.argwhere(lad)
    p0 = L[np.argmin(np.linalg.norm((L - np.array(lab.shape) / 2) * z, axis=1))] * z
    tube = tube_mask(lab, lad, z, p0, 30, .6)            # the drawn septal
    ghost = tube_mask(lab, lad, z, p0, 30, .6, away=-1.0)  # a septal-sized tube where the read drew none
    ghost &= ~tube
    n = lab.size; f = lambda m: m.reshape(-1)
    base = np.zeros((C, n)); base[0] = 1 - 4e-4; base[1:] = 1e-4

    def put(P, m, k, val):
        mm = f(m); P[:, mm] = (1 - val) / (C - 1); P[k, mm] = val
    P0 = base.copy(); put(P0, grp, 1, .9); put(P0, om1, 3, .9); put(P0, oth, 4, .9)
    # ImageCAS-X / four-class background: band set within W of the LAD
    icx = np.zeros((C, n), bool)
    icx[0] = f(lab == 0); icx[2] |= f((lab == 0) & (dS <= W)); icx[1] = f(grp); icx[3] = f(om1); icx[4] = f(oth)
    icx[:, f(lab == 255)] = True
    # extended read WITHOUT the tick (round 2): tube singleton S1; LAD group -> {LAD-group, S1}; band in background
    old = icx.copy(); old[:, f(tube)] = False; old[2, f(tube)] = True; old[2, f(grp)] = True
    # extended read under D54: every undrawn class confirmed absent -> singletons everywhere
    new = np.zeros((C, n), bool)
    new[0] = f(lab == 0) & ~f(tube); new[1] = f(grp); new[2] = f(tube); new[3] = f(om1); new[4] = f(oth)
    new[:, f(lab == 255)] = True
    PA = P0.copy(); put(PA, tube, 2, .9)
    PB = P0.copy(); put(PB, tube, 1, .9)
    g = f(grp)
    PC = P0.copy(); PC[2, g] = .5; PC[1, g] = .4; PC[0, g] = PC[3, g] = PC[4, g] = .1 / 3; put(PC, tube, 2, .9)
    PF = PA.copy(); put(PF, ghost, 2, .9)
    sc = (('A_right', PA), ('B_miss', PB), ('C_sprawl', PC), ('F_phantom', PF))
    return {'case': cid, 'tube_vox': int(tube.sum()), 'ghost_vox': int(ghost.sum()),
            'old_no_tick': {k: terms(P, old) for k, P in sc}, 'd54': {k: terms(P, new) for k, P in sc}}


if __name__ == '__main__':
    d, outp = sys.argv[1], sys.argv[2]
    ids = sorted(chosen(40), key=lambda c: hashlib.sha256(('asclepius-j1f-r4-crucible-dice:' + c).encode()).hexdigest())[:10]
    res = [case(os.path.join(d, '%d.coronary.nii.gz' % (int(c[1:]) + 1)), c) for c in ids]
    names = ['LADgrp', 'S1', 'OM1', 'other']
    summ = {}
    for lab in ('old_no_tick', 'd54'):
        for s in res[0][lab]:
            row = {o: dict(zip(names, np.mean([r[lab][s][o] for r in res], 0).round(4).tolist()))
                   for o in ('leaf', 'ignore', 'merged')}
            row['ce'] = round(float(np.mean([r[lab][s]['ce'] for r in res])), 6)
            summ[f'{lab}:{s}'] = row
    # what the loss says about each error: increase over A_right, leaf-Dice on S1 and LADgrp, and CE
    delta = {}
    for lab in ('old_no_tick', 'd54'):
        a = summ[f'{lab}:A_right']
        for s in ('B_miss', 'C_sprawl', 'F_phantom'):
            b = summ[f'{lab}:{s}']
            delta[f'{lab}:{s}'] = {'d_ce': round(b['ce'] - a['ce'], 6),
                                   'd_leaf_S1': round(b['leaf']['S1'] - a['leaf']['S1'], 4),
                                   'd_leaf_LADgrp': round(b['leaf']['LADgrp'] - a['leaf']['LADgrp'], 4)}
    json.dump({'cases': res, 'mean': summ, 'delta_vs_right': delta}, open(outp, 'w'), indent=1)
    for k, v in delta.items():
        print(k, v)
