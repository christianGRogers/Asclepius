"""Labels for the two-reads experiment (self-contained copy of experiments/Crucible/r4_reads.py logic).

truth T  : the ImageCAS (Girder) binary mask, each voxel named by the nearest ImageCAS-X voxel's territory class
           (D0 thick convention, D1 territory, D1b ramus -> LCx; ImageCAS-X 'Other' -> nearest of LAD/LCx).
read     : one simulated annotator split of T. Error model per read (independent):
   carina shift s ~ N(0, SIG) mm; ramus slip (IM -> LAD) with prob P_RAMUS; side-branch slip (D1 or OM1 to the other
   left class) with prob P_SIDE; distal truncation at local radius r_t ~ U(R_LO, R_HI) mm, keeping only what stays
   connected to the ostia. Defaults calibrated on 49 cases to inter-read Dice LM 0.81 / LAD 0.93 / LCx 0.90 /
   RCA 0.96 (ImageCAS-X inter-observer: 0.92 / 0.92 / 0.85 / 0.95).
"""
import os
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

TERR = np.zeros(15, np.uint8)
TERR[[1]] = 1; TERR[[2, 4, 5]] = 2; TERR[[3, 6, 7, 8, 12, 13]] = 3; TERR[[9, 10, 11]] = 4   # 8 = ramus -> LCx (D1b)
S26 = np.ones((3, 3, 3))
PARAMS = dict(SIG=2.0, R_LO=0.6, R_HI=1.05, P_RAMUS=0.3, P_SIDE=0.15)


def nearest_fill(lab, region, allowed):
    src = np.isin(lab, allowed)
    _, ind = ndi.distance_transform_edt(~src, return_indices=True)
    out = lab.copy(); out[region] = lab[tuple(ind)][region]; return out


def truth(mask, icx14):
    """mask: bool ImageCAS mask; icx14: uint8 ImageCAS-X labels (same grid). Returns (T, near14)."""
    t = TERR[icx14]
    other = icx14 == 14
    if other.any():
        t = nearest_fill(t, other, (2, 3))
    _, ind = ndi.distance_transform_edt(t == 0, return_indices=True)
    T = np.where(mask, t[tuple(ind)], 0).astype(np.uint8)
    _, ind = ndi.distance_transform_edt(icx14 == 0, return_indices=True)
    return T, icx14[tuple(ind)]


def ostia(T, sp):
    o = []; rad = ndi.distance_transform_edt(T > 0, sampling=sp)
    lm = T == 1
    if lm.any():
        idx = np.argwhere(lm); o.append(idx[np.argmax(rad[lm])])
    r = T == 4
    if r.any():
        idx = np.argwhere(r); top = idx[idx[:, 2] >= np.percentile(idx[:, 2], 90)]
        o.append(top[np.argmax(rad[tuple(top.T)])])
    # every sizeable tree needs a root (absent LM / separate ostia, or a crop that cut the LM away):
    # a component with no root gets its thickest voxel
    lab, n = ndi.label(T > 0, S26)
    have = {lab[tuple(r)] for r in o}
    for k in range(1, n + 1):
        if k in have: continue
        sel = lab == k
        if sel.sum() < 1000: continue
        idx = np.argwhere(sel); o.append(idx[np.argmax(rad[sel])])
    return o


def local_radius(m, sp):
    rad = ndi.distance_transform_edt(m, sampling=sp); sk = skeletonize(m)
    _, ind = ndi.distance_transform_edt(~sk, return_indices=True)
    return rad[tuple(ind)] * m


# Read models. 'annot_bias' (default for the GPU run): two annotators with opposite, systematic habits -- X shifts the
# carina distally (s ~ N(+1.5, 1) mm) and stops early (r_t ~ U(0.8, 1.1) mm); Y shifts it proximally (N(-1.5, 1)) and
# traces further (U(0.55, 0.8)). Read A is always X, read B always Y. This is the regime where the CPU study
# (experiments/Crucible/r5_corr.py) found that fusion choices change the result; under 'indep' (round-3 model:
# s ~ N(0, 2), r_t ~ U(0.6, 1.05) for every read) all schemes converge to the same target.
READ_MODEL = os.environ.get('CRUCIBLE_READS', 'annot_bias')


def habit(who, rng, model=None):
    model = model or READ_MODEL
    if model == 'indep':
        return rng.normal(0, PARAMS['SIG']), rng.uniform(PARAMS['R_LO'], PARAMS['R_HI'])
    if model == 'annot_bias':
        return (rng.normal(1.5, 1.0), rng.uniform(0.8, 1.1)) if who == 'X' else (rng.normal(-1.5, 1.0), rng.uniform(0.55, 0.8))
    raise ValueError(model)


def make_read(T, near14, sp, rad_local, roots, rng, P=PARAMS, who='X'):
    R = T.copy(); m = T > 0
    s, rt = habit(who, rng)
    if s > 0:
        d = ndi.distance_transform_edt(R != 1, sampling=sp); R[np.isin(R, (2, 3)) & (d <= s)] = 1
    elif s < 0:
        d = ndi.distance_transform_edt(~np.isin(R, (2, 3)), sampling=sp); sel = (R == 1) & (d <= -s)
        if sel.any(): R = nearest_fill(R, sel, (2, 3))
    if rng.random() < P['P_RAMUS']: R[(near14 == 8) & m & (R == 3)] = 2
    if rng.random() < P['P_SIDE']:
        k = rng.choice([4, 6]); sel = (near14 == k) & m & np.isin(R, (2, 3)); R[sel] = 5 - R[sel]
    lab, _ = ndi.label(m & (rad_local >= rt), S26)
    rootc = {lab[tuple(r)] for r in roots if lab[tuple(r)] > 0}
    R[~np.isin(lab, list(rootc))] = 0
    return R


IGNORE = 5


def fuse(a, b, scheme):
    if scheme == 'agree':
        return np.where(a == b, a, IGNORE).astype(np.uint8)
    if scheme == 'union':
        u = np.where(a == b, a, 0).astype(np.uint8)
        oa = (a > 0) & (b == 0); ob = (b > 0) & (a == 0); u[oa] = a[oa]; u[ob] = b[ob]
        u[(a > 0) & (b > 0) & (a != b)] = IGNORE
        return u
    if scheme == 'a11':  # judge's A11: each read its own sample; name conflict inside shared vessel -> ignore
        conflict = (a > 0) & (b > 0) & (a != b)
        return np.where(conflict, IGNORE, a).astype(np.uint8), np.where(conflict, IGNORE, b).astype(np.uint8)
    raise ValueError(scheme)
