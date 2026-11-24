"""Janus 1-F round 2 (Foxtrot), §5 item 4: the three candidate Dice terms for stage 2, evaluated on real 620 label
geometry with scripted predictions (CPU; labels only, no network).

Label sets (F-A11): traced classes are singletons; ImageCAS-X background within w of the parent regions -> {bg, S};
an extended pool read (simulated on the same case) draws one septal S1 as a singleton tube, and, without D47 Q3's
"complete" flag, its LAD-group voxels become the set {LAD, D1-D3, S1-S3}.
Channels here: 0 bg, 1 LAD-group (LAD, D1-D3), 2 S1, 3 OM1 (a non-member stand-in), 4 other traced.
Dice terms, per sample and class (nnU-Net's soft Dice: do_bg False, smooth 1e-5, batch_dice False for 3d_fullres):
  leaf   (Fidon et al. 2021, as I read it): class k's target is 1 on voxels whose set is {k}; voxels whose set holds k
         and something else are dropped from k's sums; voxels whose set lacks k count as negatives;
  ignore (Foxtrot v1): every non-singleton voxel is dropped from every class's sums;
  merged (marginal Dice): target 1 wherever k is in the set; there the prediction is the set's summed probability.
CE is the marginal -log sum_{k in set} p_k, the same for all three. Scenarios on the extended-read sample:
  A right  : the tube predicted S1 (0.9);          B miss   : the tube predicted LAD-group (0.9);
  C sprawl : S1 at 0.5 on every LAD-group voxel;    D intrude: OM1 at 0.5 on every LAD-group voxel.
On the ImageCAS-X sample: E true septal predicted as S1 (no S1 singleton exists there), and the size of the Dice
gradient for an absent class compared with CE's.
Usage: python3 dice_terms.py <label_dir> <out.json> [n_cases]
"""
import json, os, sys
import numpy as np, nibabel as nb
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import labels_r2 as L  # noqa
from pass1 import TRAIN  # noqa
EPS = 1e-5; W = 15.0; C = 5


def dice(P, G, keep):
    """P, G: (C, n) arrays; keep: (C, n) bool. Returns per-class dc (classes 1..C-1)."""
    out = []
    for k in range(1, C):
        p, g, m = P[k][keep[k]], G[k][keep[k]], keep[k]
        out.append((2 * (p * g).sum() + EPS) / max(g.sum() + p.sum() + EPS, 1e-8))
    return np.array(out)


def terms(P, sets):
    """sets: (C, n) bool membership. Returns dict of mean Dice loss (1 - mean dc over classes with a target or a
    prediction) per option, and the marginal CE."""
    single = sets.sum(0) == 1
    res = {}
    # leaf
    G = sets & single[None]
    keep = ~(sets & ~single[None])
    res['leaf'] = dice(P, G.astype(float), keep)
    # ignore
    keep2 = np.broadcast_to(single[None], sets.shape)
    res['ignore'] = dice(P, G.astype(float), keep2)
    # merged
    mass = (P * sets).sum(0)
    Pm = np.where(sets, mass[None], P)
    res['merged'] = dice(Pm, sets.astype(float), np.ones_like(sets))
    ce = -np.log(np.clip(mass, 1e-12, None)).mean()
    return {k: (1 - v).round(4).tolist() for k, v in res.items()} | {'ce': round(float(ce), 5)}


def case(path):
    cid = 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1); assert cid in TRAIN
    im = nb.load(path); z = np.array(im.header.get_zooms()[:3], float)
    raw = np.asarray(im.dataobj).astype(np.uint8)
    lab, _ = L.map13(raw[L.crop(raw, 4)], z)
    lad = lab == 2
    # a 64 mm cube around the proximal third of the LAD (a patch the network would see)
    pts = np.argwhere(lad); c0 = pts[len(pts) // 3]
    h = np.round(32 / z).astype(int)
    sl = tuple(slice(max(c - hh, 0), c + hh) for c, hh in zip(c0, h))
    lab = lab[sl]; lad = lab == 2
    grp = np.isin(lab, [2, 5, 6, 7]); om1 = lab == 8; oth = (lab > 0) & ~grp & ~om1 & (lab != 255)
    dS = ndi.distance_transform_edt(~lad, sampling=z)
    # synthetic septal: 30 mm, radius 0.6 mm, from the LAD point nearest the cube centre, away from the tree's centroid
    p0 = np.argwhere(lad)[np.argmin(np.linalg.norm((np.argwhere(lad) - np.array(lab.shape) / 2) * z, axis=1))] * z
    u = -(np.argwhere(lab > 0).mean(0) * z - p0); u = u / (np.linalg.norm(u) + 1e-9)
    grid = np.stack(np.meshgrid(*[np.arange(s) * zz for s, zz in zip(lab.shape, z)], indexing='ij'), -1)
    v = grid - p0; t = np.clip(v @ u, 0, 30)
    tube = (np.linalg.norm(v - t[..., None] * u, axis=-1) <= .6) & (lab == 0) & ((v @ u) > 0) & ((v @ u) <= 30)
    n = lab.size
    f = lambda m: m.reshape(-1)
    base = np.zeros((C, n)); base[0] = 1 - 4e-4; base[1:] = 1e-4
    def put(P, m, k, val):
        mm = f(m); P[:, mm] = (1 - val) / (C - 1); P[k, mm] = val
    P0 = base.copy(); put(P0, grp, 1, .9); put(P0, om1, 3, .9); put(P0, oth, 4, .9)
    # ImageCAS-X sample sets
    S_icx = np.zeros((C, n), bool)
    S_icx[0] = f(lab == 0); S_icx[2] |= f((lab == 0) & (dS <= W))
    S_icx[1] = f(grp); S_icx[3] = f(om1); S_icx[4] = f(oth); S_icx[:, f(lab == 255)] = True
    # extended-read sample sets: tube singleton S1; LAD group -> {LAD-group, S1}; band as above outside the tube
    S_ext = S_icx.copy(); S_ext[:, f(tube)] = False; S_ext[2, f(tube)] = True; S_ext[2, f(grp)] = True
    out = {'case': cid, 'tube_vox': int(tube.sum()), 'band_vox': int(((lab == 0) & (dS <= W)).sum()), 'n': n}
    PA = P0.copy(); put(PA, tube, 2, .9)
    PB = P0.copy(); put(PB, tube, 1, .9)
    PC = P0.copy(); g = f(grp); PC[2, g] = .5; PC[1, g] = .4; PC[0, g] = .1 / 3; PC[3, g] = .1 / 3; PC[4, g] = .1 / 3; put(PC, tube, 2, .9)
    PD = P0.copy(); PD[3, g] = .5; PD[1, g] = .4; PD[0, g] = .1 / 3; PD[2, g] = .1 / 3; PD[4, g] = .1 / 3; put(PD, tube, 2, .9)
    out['ext'] = {k: terms(P, S_ext) for k, P in (('A_right', PA), ('B_miss', PB), ('C_sprawl', PC), ('D_intrude', PD))}
    # ImageCAS-X sample: a true (untraced) septal predicted as S1 vs not; tube voxels are bg singletons beyond W
    out['icx'] = {k: terms(P, S_icx) for k, P in (('E_septal_predicted', PA), ('E_septal_not', P0))}
    # Dice gradient for an absent class (S1 on the ImageCAS-X sample) vs the CE gradient, per voxel
    sp = P0[2].sum()
    out['grad_ratio_absent_dice_over_ce'] = float((EPS / (sp + EPS) ** 2) / (1.0 / n))
    return out


if __name__ == '__main__':
    d, outp = sys.argv[1], sys.argv[2]; k = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    files = sorted((f for f in os.listdir(d) if f.endswith('.coronary.nii.gz')), key=lambda s: int(s.split('.')[0]))
    files = [f for f in files if 'c%04d' % (int(f.split('.')[0]) - 1) in TRAIN][::62][:k]
    res = [case(os.path.join(d, f)) for f in files]
    names = ['LADgrp', 'S1', 'OM1', 'other']
    summ = {}
    for smp in ('ext', 'icx'):
        for sc in res[0][smp]:
            summ[f'{smp}:{sc}'] = {opt: dict(zip(names, np.mean([r[smp][sc][opt] for r in res], 0).round(4).tolist()))
                                   for opt in ('leaf', 'ignore', 'merged')}
            summ[f'{smp}:{sc}']['ce'] = round(float(np.mean([r[smp][sc]['ce'] for r in res])), 5)
    summ['grad_ratio_absent_dice_over_ce_median'] = float(np.median([r['grad_ratio_absent_dice_over_ce'] for r in res]))
    json.dump({'cases': res, 'mean': summ}, open(outp, 'w'), indent=1)
    for k2, v in summ.items():
        print(k2, v)
