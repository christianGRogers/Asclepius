# Round 4: simulate two independent annotator reads per case under the DECIDED protocol (D0/D4: split the
# original ImageCAS mask into LM/LAD/LCx/RCA; D1 territory; D1b ramus -> LCx; edits can only REMOVE seed voxels or
# change their class). Truth T = the Girder mask named by nearest ImageCAS-X territory class (thick4 in r2data).
# Error model per read (independent, seeded):
#   carina : LM/bifurcation boundary shifted by s ~ N(0, SIG_CARINA) mm
#   trunc  : "stop where the lumen is no longer confident" -- drop voxels whose local radius < r_t, r_t ~ U(R_LO,R_HI) mm,
#            then keep only what stays connected to that tree's ostium (distal tail beyond a thin point is dropped)
#   ramus  : ramus (ICX IM) labelled LAD instead of LCx with prob P_RAMUS (protocol slip)
#   side   : with prob P_SIDE one major side branch (D1 or OM1, ICX nearest class) given the other left class
# Saves, per case, the mask-voxel flat indices + T + read A + read B (uint8) -> r4reads/<case>.npz (tiny).
import os, sys, json, numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
D = SCR + '/work/Crucible/r2data'; OUT = SCR + '/work/Crucible/r4reads'; os.makedirs(OUT, exist_ok=True)
SIG_CARINA, R_LO, R_HI, P_RAMUS, P_SIDE = [float(x) for x in os.environ.get('R4P', '2.0 0.45 0.85 0.3 0.15').split()]
S26 = np.ones((3, 3, 3))
meta = json.load(open(D + '/meta.json'))


def nearest_fill(lab, region, allowed):
    """labels for `region` voxels = nearest voxel whose label is in `allowed`."""
    src = np.isin(lab, allowed)
    _, ind = ndi.distance_transform_edt(~src, return_indices=True)
    out = lab.copy(); out[region] = lab[tuple(ind)][region]; return out


def ostia(T, sp):
    o = []
    # left: LM voxel farthest from LAD/LCx; right: RCA voxel with the largest local radius among its most superior 10 %
    lm = T == 1
    rad = ndi.distance_transform_edt(T > 0, sampling=sp)
    if lm.any():  # left: the thickest LM voxel (inside the trunk, so truncation never removes it)
        idx = np.argwhere(lm); o.append(idx[np.argmax(rad[lm])])
    r = T == 4
    if r.any():
        idx = np.argwhere(r); top = idx[idx[:, 2] >= np.percentile(idx[:, 2], 90)]
        o.append(top[np.argmax(rad[tuple(top.T)])])
    return o


def make_read(T, near14, sp, rad_local, roots, rng):
    R = T.copy(); m = T > 0
    # carina shift
    s = rng.normal(0, SIG_CARINA)
    if s > 0:
        d = ndi.distance_transform_edt(R != 1, sampling=sp); R[np.isin(R, (2, 3)) & (d <= s)] = 1
    elif s < 0:
        d = ndi.distance_transform_edt(~np.isin(R, (2, 3)), sampling=sp); sel = (R == 1) & (d <= -s)
        if sel.any(): R = nearest_fill(R, sel, (2, 3))
    # ramus slip
    if rng.random() < P_RAMUS: R[(near14 == 8) & m & (R == 3)] = 2
    # side-branch slip
    if rng.random() < P_SIDE:
        k = rng.choice([4, 6]); sel = (near14 == k) & m & np.isin(R, (2, 3))
        R[sel] = 5 - R[sel]  # 2 <-> 3
    # truncation
    rt = rng.uniform(R_LO, R_HI)
    keep = m & (rad_local >= rt)
    lab, _ = ndi.label(keep, S26)
    rootc = {lab[tuple(r)] for r in roots if lab[tuple(r)] > 0}
    # thin voxels adjacent to kept trunk are kept only if their own radius is ok -> drop everything not rooted
    R[~np.isin(lab, list(rootc))] = 0
    return R, s, rt


if __name__ == '__main__':
    rows = []
    for c in sorted(meta):
        lab = np.load(f'{D}/{c}_lab.npy'); sp = np.array(meta[c]['spacing'])
        T = ((lab >> 4) & 7).astype(np.uint8); m = T > 0
        L14 = lab & 15
        _, ind = ndi.distance_transform_edt(L14 == 0, return_indices=True); near14 = L14[tuple(ind)]
        rad = ndi.distance_transform_edt(m, sampling=sp)
        sk = skeletonize(m)  # local vessel radius = lumen radius at the nearest centreline voxel
        _, ind2 = ndi.distance_transform_edt(~sk, return_indices=True)
        rad_local = rad[tuple(ind2)] * m
        roots = ostia(T, sp)
        rng = np.random.default_rng(int(c[1:]))
        A, sa, ra = make_read(T, near14, sp, rad_local, roots, rng)
        B, sb, rb = make_read(T, near14, sp, rad_local, roots, rng)
        idx = np.flatnonzero(m)
        np.savez_compressed(f'{OUT}/{c}.npz', idx=idx, T=T.ravel()[idx], A=A.ravel()[idx], B=B.ravel()[idx],
                            shape=np.array(T.shape), roots=np.array(roots))
        dA = {k: float(2 * ((A == k) & (B == k)).sum() / max(1, (A == k).sum() + (B == k).sum())) for k in (1, 2, 3, 4)}
        rows.append({'case': c, 'test': meta[c]['test'], 'sA': sa, 'sB': sb, 'rA': ra, 'rB': rb, 'AB_dice': dA,
                     'A_vs_T_fg': float((A > 0).sum() / m.sum()), 'B_vs_T_fg': float((B > 0).sum() / m.sum())})
        print(json.dumps(rows[-1]), flush=True)
    json.dump(rows, open(OUT + '/reads_meta.json', 'w'))
