"""E6 (Juliet, Janus-M Round 2, path jm/paired-scar): carrying first-pass (CCTA) borders onto the late-iodine scan.

Question. JA11 grades late enhancement inside the first-pass borders, registered to the late scan. The two scans are
taken minutes apart in one session; the heart can sit in a different place (another breath-hold) while the spine,
chest wall and lungs move less. How much misregistration can Kim-bin grading tolerate, and which registration
method gets under that tolerance?

Synthetic 3-D phantom only: no public or project case is opened (the gate in guard_r2.py runs first anyway).

Phantom (1 mm grid, 144 mm field, each voxel the mean of 2x2x2 sub-samples). Static: soft tissue, two lungs, spine,
descending aorta. Heart (moves rigidly between scans): LV cavity (half-ellipsoid, a=25, b=45 mm), LV wall 10 mm,
3 mm epicardial fat, RV cavity crescent, LA. 18 wall segments (6 sectors x base/mid/apical); a contiguous patch of
2-6 segments carries subendocardial scar with transmurality from {0.15, 0.35, 0.6, 0.9} (one per Kim bin).

  first-pass (CCTA)  blood 450 (RV 350), myocardium 110, scar 70, fat -90, soft 40, lung -800, bone 500; noise 30 HU
  late (LIE, ~7 min)  blood 130, myocardium 90, scar 90+C, fat -90, soft 50, lung -800, bone 500; noise sd
  both: Gaussian PSF FWHM 1.0 mm.

Motion of the heart between scans: translation of d mm (mostly cranio-caudal) and rotation up to 0.4*d degrees,
d in {0, 2, 4, 6, 8, 10}. Optionally a cardiac-phase change: LV cavity scaled by (1-e), wall thickened to keep its
volume (non-rigid; rigid registration cannot fix it).

Registration (rigid, 6 parameters, LIE moved onto the first-pass grid; Mattes-style mutual information, 48 bins,
Powell, 2 levels, 150k sampled points):
  R0 none (scanner coordinates);
  R1 MI over the whole field;
  R2 MI inside a heart mask: the first-pass labels (LV wall, LV, RV, LA) dilated by 10 mm.

Grading (E3's best rule, carried forward): resample LIE to the first-pass grid; Gaussian smoothing FWHM 1.5 mm;
remote = the scar-free-looking segment (lowest mean); threshold = remote mean + 1/2 (myocardial 99th pct - remote);
per segment, transmurality = mean over chords (3-degree x 2 mm columns) of the scar fraction of the chord;
scar present if >= tau (0.10; E7 sets it); Kim bin otherwise 0. Truth = the same chord measure on the exact scar mask.

Also two QC numbers needing no truth: the share of first-pass myocardium voxels whose registered LIE value is
fat-like (< 0 HU after smoothing), and the same for blood-like (> remote + 0.8 x (blood - remote)).

Usage: python register_lie.py [--quick]   -> e6_registration.json
"""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy import ndimage, optimize

HERE = Path(__file__).resolve().parent
OUT = HERE / 'e6_registration.json'
V, N, SS = 1.0, 144, 2                     # voxel mm, grid size, sub-samples per axis
A_CAV, B_CAV, WALL, FAT = 25.0, 45.0, 10.0, 3.0
BASE_W = 12.0                               # LV truncated at w <= BASE_W (heart frame; apex at w = -B)
TS = (0.15, 0.35, 0.6, 0.9)
BINS = (0.0, 0.01, 0.26, 0.51, 0.76, 1.01)
TAU = 0.10


def rot(ax, ay, az):
    cx, sx, cy, sy, cz, sz = np.cos(ax), np.sin(ax), np.cos(ay), np.sin(ay), np.cos(az), np.sin(az)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


R_HEART = rot(0.0, np.deg2rad(50), np.deg2rad(-35))   # LV long axis tilted as in a chest
C_HEART = np.array([4.0, -6.0, 0.0])


def world_points(ss=SS):
    h = V / ss
    ax = (np.arange(N * ss) + 0.5) * h - N * V / 2
    return ax


def ray_depth(p, e):
    """Fractional depth along the ray from the LV centre: 0 at endocardium, 1 at epicardium. e = phase change."""
    a, b = A_CAV * (1 - e), B_CAV * (1 - e)
    # outer surface keeps the myocardial volume of the e=0 heart (approximately: same outer ellipsoid)
    ao, bo = A_CAV + WALL, B_CAV + WALL
    r = np.sqrt((p ** 2).sum(0)) + 1e-9
    d = p / r
    q_in = np.sqrt((d[0] ** 2 + d[1] ** 2) / a ** 2 + d[2] ** 2 / b ** 2)
    q_out = np.sqrt((d[0] ** 2 + d[1] ** 2) / ao ** 2 + d[2] ** 2 / bo ** 2)
    t_in, t_out = 1 / q_in, 1 / q_out
    return (r - t_in) / (t_out - t_in), r, t_out


def heart_labels(pw, motion, e):
    """pw: (3, n) world points. motion = (R, t): heart frame pose change. Returns label codes and depth/segment."""
    R, t = motion
    ph = (R_HEART @ R).T @ (pw - (C_HEART + t)[:, None])        # heart frame (u, v, w)
    u, r, t_out = ray_depth(ph, e)
    w = ph[2]
    inside_lv = (w <= BASE_W)
    lab = np.zeros(pw.shape[1], np.int8)                         # 0 soft tissue (or static, set later)
    fat = inside_lv & (r <= t_out + FAT * 1.0) & (u > 1)
    myo = inside_lv & (u >= 0) & (u <= 1)
    cav = inside_lv & (u < 0)
    rv = (((ph[0] + 33) / 20) ** 2 + (ph[1] / 30) ** 2 + ((ph[2] + 5) / 42) ** 2 <= 1) & ~myo & ~cav & ~(
        inside_lv & (u <= 1.0))
    la = ((ph[0] ** 2 + ph[1] ** 2 + (ph[2] - BASE_W - 20) ** 2) <= 20 ** 2) & ~myo & ~cav
    lab[fat] = 5
    lab[rv] = 3
    lab[la] = 4
    lab[cav] = 2
    lab[myo] = 1
    # segment index: 6 sectors x 3 levels along the cavity length (base/mid/apical)
    phi = (np.degrees(np.arctan2(ph[1], ph[0])) + 360) % 360
    sector = (phi // 60).astype(np.int16)
    level = np.clip(((BASE_W - w) / (BASE_W + B_CAV) * 3).astype(np.int16), 0, 2)
    seg = level * 6 + sector
    return lab, u, seg, phi, w


def static_labels(pw):
    x, y, z = pw
    lab = np.zeros(pw.shape[1], np.int8)
    lung = (((np.abs(x) - 58) / 20) ** 2 + ((y + 0) / 45) ** 2 <= 1)
    spine = ((x - 0) ** 2 + (y - 58) ** 2 <= 13 ** 2)
    aorta = ((x - 20) ** 2 + (y - 45) ** 2 <= 11 ** 2)
    lab[lung] = 10
    lab[spine] = 11
    lab[aorta] = 12
    return lab


FP = {0: 40, 1: 110, 2: 450, 3: 350, 4: 430, 5: -90, 10: -800, 11: 500, 12: 450, 'scar': 70}
LIE = {0: 50, 1: 90, 2: 130, 3: 130, 4: 130, 5: -90, 10: -800, 11: 500, 12: 130}


def render(tab, scar_T, motion, e, scar_val, sd, rng, want_truth=False):
    """Returns the image on the 1 mm grid; if want_truth also the 1 mm label map, segment map, scar mask, depth."""
    ax = world_points()
    img = np.zeros((N, N, N), np.float32)
    keep = {}
    n_ss = N * SS
    for iz in range(N):                                           # slab by slab to bound memory
        zz = ax[iz * SS:(iz + 1) * SS]
        X, Y, Z = np.meshgrid(ax, ax, zz, indexing='ij')
        pw = np.stack([X.ravel(), Y.ravel(), Z.ravel()])
        hl, u, seg, phi, w = heart_labels(pw, motion, e)
        sl = static_labels(pw)
        lab = np.where(hl > 0, hl, sl)
        val = np.array([tab[k] for k in KEYS], np.float32)[np.searchsorted(KEYS, lab)]
        scar = (lab == 1) & (u < scar_T[np.clip(seg, 0, 17)])
        val[scar] = scar_val
        vb = val.reshape(n_ss, n_ss, SS).reshape(N, SS, N, SS, SS).mean(axis=(1, 3, 4))
        img[:, :, iz] = vb
        if want_truth:
            # labels / segments / scar at the centre sub-sample of each voxel block (deterministic)
            lc = lab.reshape(n_ss, n_ss, SS)[SS // 2::SS, SS // 2::SS, SS // 2]
            keep.setdefault('lab', np.zeros((N, N, N), np.int8))[:, :, iz] = lc
            keep.setdefault('seg', np.zeros((N, N, N), np.int16))[:, :, iz] = seg.reshape(n_ss, n_ss, SS)[
                SS // 2::SS, SS // 2::SS, SS // 2]
            keep.setdefault('scar', np.zeros((N, N, N), bool))[:, :, iz] = scar.reshape(n_ss, n_ss, SS)[
                SS // 2::SS, SS // 2::SS, SS // 2]
            keep.setdefault('phi', np.zeros((N, N, N), np.float32))[:, :, iz] = phi.reshape(n_ss, n_ss, SS)[
                SS // 2::SS, SS // 2::SS, SS // 2]
            keep.setdefault('w', np.zeros((N, N, N), np.float32))[:, :, iz] = w.reshape(n_ss, n_ss, SS)[
                SS // 2::SS, SS // 2::SS, SS // 2]
            keep.setdefault('u', np.zeros((N, N, N), np.float32))[:, :, iz] = u.reshape(n_ss, n_ss, SS)[
                SS // 2::SS, SS // 2::SS, SS // 2]
    img = ndimage.gaussian_filter(img, 1.0 / 2.355 / V)
    img += rng.normal(0, sd, img.shape).astype(np.float32)
    return img, keep


KEYS = np.array([0, 1, 2, 3, 4, 5, 10, 11, 12])


# ------------------------------------------------------------------ registration
def mi(a, b, bins=48, lo=-900.0, hi=700.0):
    a = np.clip(a, lo, hi)
    b = np.clip(b, lo, hi)
    h, _, _ = np.histogram2d(a, b, bins=bins, range=[[lo, hi], [lo, hi]])
    p = h / h.sum()
    px, py = p.sum(1), p.sum(0)
    nz = p > 0
    return float((p[nz] * np.log(p[nz] / (px[:, None] * py[None, :])[nz])).sum())


def params_to_affine(q, centre):
    R = rot(*np.deg2rad(q[:3]))
    t = np.asarray(q[3:6])
    return R, t, centre


def warp_points(q, pts_mm, centre):
    R, t, c = params_to_affine(q, centre)
    return (R @ (pts_mm - c[:, None])) + c[:, None] + t[:, None]


def sample(img, pts_mm, order=1):
    idx = pts_mm / V + N / 2 - 0.5
    return ndimage.map_coordinates(img, idx, order=order, mode='nearest')


def register(fixed, moving, mask, rng, npts=150_000):
    """Find q (rx, ry, rz deg; tx, ty, tz mm) so that moving(T(x)) matches fixed(x) for x in mask."""
    ii = np.argwhere(mask)
    centre = (ii.mean(0) + 0.5 - N / 2) * V
    out_q = np.zeros(6)
    for level, sm in ((0, 2.0), (1, 0.0)):
        f = ndimage.gaussian_filter(fixed, sm) if sm else fixed
        m = ndimage.gaussian_filter(moving, sm) if sm else moving
        sel = ii[rng.choice(len(ii), min(npts, len(ii)), replace=False)]
        pts = ((sel + 0.5 - N / 2) * V).T
        fv = f[sel[:, 0], sel[:, 1], sel[:, 2]]

        def cost(q):
            return -mi(fv, sample(m, warp_points(q, pts, centre)))
        res = optimize.minimize(cost, out_q, method='Powell',
                                options={'xtol': 0.05, 'ftol': 1e-5, 'maxfev': 1500,
                                         'direc': np.diag([2, 2, 2, 4, 4, 4]) if level == 0 else np.eye(6)})
        out_q = res.x
    return out_q, centre


# ------------------------------------------------------------------ grading
def grade(lie_on_fp, truth, seg_present_tau=TAU):
    lab, seg, phi, w = truth['lab'], truth['seg'], truth['phi'], truth['w']
    myo = lab == 1
    img = ndimage.gaussian_filter(lie_on_fp, 1.5 / 2.355 / V)
    segs = np.arange(18)
    means = np.array([img[myo & (seg == s)].mean() for s in segs])
    remote = int(np.argmin(means))
    mu = img[myo & (seg == remote)].mean()
    p99 = np.percentile(img[myo], 99)
    thr = mu + 0.5 * (p99 - mu)
    sc = img > thr
    col = (np.floor(phi / 3).astype(np.int64) * 1000 + np.floor(w / 2).astype(np.int64) + 500) * 10 + \
        np.clip(np.floor(truth['u'] * 10), 0, 9).astype(np.int64)
    est, tru = np.zeros(18), np.zeros(18)
    for s in segs:
        m = myo & (seg == s)
        c = col[m]
        uc, inv, cnt = np.unique(c, return_inverse=True, return_counts=True)
        e_db = (np.bincount(inv, weights=sc[m]) / cnt) > 0.5        # depth bin (of 10) called scar, per column
        t_db = (np.bincount(inv, weights=truth['scar'][m]) / cnt) > 0.5
        colid = uc // 10
        uq, cinv, ccnt = np.unique(colid, return_inverse=True, return_counts=True)
        ok = ccnt >= 6                                               # columns that span most of the wall
        est[s] = (np.bincount(cinv, weights=e_db) / ccnt)[ok].mean()
        tru[s] = (np.bincount(cinv, weights=t_db) / ccnt)[ok].mean()
    fatlike = float((img[myo] < 0).mean())
    bloodlike = float((img[myo] > mu + 0.8 * (130 - mu)).mean()) if mu < 130 else float('nan')
    return est, tru, fatlike, bloodlike


def kim(x, present):
    return np.where(present, np.clip(np.digitize(x, BINS) - 1, 1, 4), 0)


def score(est, tru, tau=TAU):
    pe, pt = est >= tau, tru >= 0.01
    be, bt = kim(est, pe), kim(tru, pt)
    return {'bin_acc': float((be == bt).mean()),
            'bin_acc_scarred': float((be[pt] == bt[pt]).mean()) if pt.any() else None,
            'sens': float(pe[pt].mean()) if pt.any() else None,
            'spec': float((~pe[~pt]).mean()) if (~pt).any() else None,
            'mae_T_scarred': float(np.abs(est - tru)[pt].mean()) if pt.any() else None,
            'est': [round(float(x), 3) for x in est], 'true': [round(float(x), 3) for x in tru]}


# ------------------------------------------------------------------ one run
def scar_pattern(rng):
    T = np.zeros(18)
    s0, lv0 = rng.integers(6), rng.integers(1, 3)
    ns, nl = rng.integers(1, 3) + 1, rng.integers(1, 3)          # 2-3 sectors x 1-2 levels (mid/apical)
    patch = [(lv0 + j) % 3 * 6 + (s0 + i) % 6 for i in range(ns) for j in range(nl)]
    for k, s in enumerate(patch):
        T[s] = TS[k % 4] if k < 4 else TS[rng.integers(4)]
    return T


def motion_for(d, rng):
    if d == 0:
        return np.eye(3), np.zeros(3)
    v = rng.normal(0, 1, 3) * np.array([0.35, 0.35, 1.0])
    v = v / np.linalg.norm(v) * d
    ang = rng.uniform(-1, 1, 3) * 0.4 * d
    return rot(*np.deg2rad(ang)), v


def run(cfg):
    d, seed, C, sd, e = cfg[:5]
    methods = cfg[5] if len(cfg) > 5 else ('R0', 'R1', 'R2')
    rng = np.random.default_rng(1000 * seed + 17)
    T = scar_pattern(rng)
    mot = motion_for(d, rng)
    fp, truth = render(FP, T, (np.eye(3), np.zeros(3)), 0.0, FP['scar'], 30.0, rng, want_truth=True)
    lie, _ = render(LIE, T, mot, e, 90.0 + C, sd, rng)
    lab = truth['lab']
    heart = np.isin(lab, (1, 2, 3, 4))
    myo_idx = np.argwhere(lab == 1)
    myo_mm = ((myo_idx + 0.5 - N / 2) * V).T
    # true map: first-pass heart point x (heart pose 0) -> LIE point, with the heart moved by (R, t) about C_HEART
    R, t = mot
    hp = R_HEART.T @ (myo_mm - C_HEART[:, None])
    true_pts = (R_HEART @ R) @ hp + (C_HEART + t)[:, None]
    rows = {}
    masks = {'R1': np.ones_like(heart), 'R2': ndimage.binary_dilation(heart, iterations=int(10 / V))}
    allpts = np.indices((N, N, N)).reshape(3, -1)
    allmm = (allpts + 0.5 - N / 2) * V
    for meth in methods:
        t0 = time.time()
        if meth == 'R0':
            q, centre = np.zeros(6), np.zeros(3)
        else:
            q, centre = register(fp, lie, masks[meth], np.random.default_rng(seed))
        est_pts = warp_points(q, myo_mm, centre)
        tre = float(np.linalg.norm(est_pts - true_pts, axis=0).mean())
        lie_on_fp = sample(lie, warp_points(q, allmm, centre)).reshape(N, N, N)
        est, tru, fatlike, bloodlike = grade(lie_on_fp, truth)
        rows[meth] = {'tre_mm': round(tre, 3), 'fatlike': round(fatlike, 4), 'bloodlike': round(bloodlike, 4),
                      'q': [round(float(x), 3) for x in q], 'sec': round(time.time() - t0, 1), **score(est, tru)}
    print(f'E6 d={d} seed={seed} C={C} sd={sd} e={e}',
          {m: (r['tre_mm'], r['bin_acc'], r['sens'], r['spec']) for m, r in rows.items()}, flush=True)
    return {'d_mm': d, 'seed': seed, 'contrast_HU': C, 'noise_sd_HU': sd, 'phase_e': e, 'T_segments': T.tolist(),
            'methods': rows}


def summarise(res):
    out = []
    keys = sorted({(r['d_mm'], r['contrast_HU'], r['noise_sd_HU'], r['phase_e']) for r in res})
    for k in keys:
        rr = [r for r in res if (r['d_mm'], r['contrast_HU'], r['noise_sd_HU'], r['phase_e']) == k]
        row = {'d_mm': k[0], 'contrast_HU': k[1], 'noise_sd_HU': k[2], 'phase_e': k[3], 'n': len(rr)}
        for m in ('R0', 'R1', 'R2'):
            g = [r['methods'][m] for r in rr if m in r['methods']]
            if not g:
                continue
            for f in ('tre_mm', 'bin_acc', 'bin_acc_scarred', 'sens', 'spec', 'mae_T_scarred', 'fatlike',
                      'bloodlike'):
                vals = [x[f] for x in g if x[f] is not None and x[f] == x[f]]
                row[f'{m}_{f}'] = round(float(np.mean(vals)), 3) if vals else None
            row[f'{m}_tre_max'] = round(float(max(x['tre_mm'] for x in g)), 3)
        out.append(row)
    return out


if __name__ == '__main__':
    sys.path.insert(0, str(HERE))
    import guard_r2
    guard_r2.gate([])                                    # synthetic: no case is opened
    quick = '--quick' in sys.argv
    ds = (0, 4) if quick else (0, 2, 4, 6, 8, 10)
    seeds = range(1) if quick else range(4)
    cfgs = [(d, s, 60.0, 15.0, 0.0) for d in ds for s in seeds]
    if not quick:
        cfgs += [(d, s, 60.0, 15.0, 0.0, ('R0',)) for d in (0.5, 1.0, 1.5, 3.0) for s in seeds]   # tolerance, R0 only
        cfgs += [(d, s, 40.0, 20.0, 0.0) for d in (0, 4, 8) for s in seeds]      # harder LIE contrast/noise
        cfgs += [(d, s, 60.0, 15.0, 0.05) for d in (0, 4) for s in seeds]        # cardiac-phase change, 5 %
    t0 = time.time()
    with Pool(4) as p:
        res = p.map(run, cfgs, chunksize=1)
    out = {'config': {'voxel_mm': V, 'grid': N, 'supersample': SS, 'cavity_ab_mm': [A_CAV, B_CAV], 'wall_mm': WALL,
                      'tau': TAU, 'kim_bins': BINS, 'first_pass': {str(k): v for k, v in FP.items()},
                      'lie': {str(k): v for k, v in LIE.items()}, 'seconds': round(time.time() - t0)},
           'summary': summarise(res), 'runs': res}
    path = OUT.with_name('e6_quick.json') if quick else OUT
    path.write_text(json.dumps(out, indent=1) + '\n')
    guard_r2.scan_outputs([path])
    print('wrote', path)
