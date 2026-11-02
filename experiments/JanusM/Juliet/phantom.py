"""Juliet v1 CPU experiments: a short-axis LV phantom (2-D) for three Janus-M questions.

E1  Layers from borders: if transmural thirds are computed from a myocardium mask (Laplace depth), how
    good are they at CT voxel sizes and realistic border errors? (Dice per third, thickness error.)
E2  Perfusion: how much do blood-pool and epicardial-fat spill (the scanner's blur) bias a subendocardial /
    subepicardial attenuation ratio (TPR), and does a guard band fix it?
E3  Late iodine enhancement (LIE): how well can scar transmurality be binned (Kim 2000 bins) from a CT
    LIE image, given borders, contrast, noise and blur?

Everything is synthetic: no patient data is read. Geometry: endocardial radius 25 mm; wall 10 mm, with
a 60-degree sector thinned to 5 mm (cosine taper). Images are made on a fine grid (voxel/8), blurred by a
Gaussian point-spread function (FWHM f), then block-averaged to the voxel grid (partial volume).

Run: python3 experiments/JanusM/Juliet/phantom.py  (about 10 minutes on 4 CPU cores); writes results.json.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage, sparse
from scipy.sparse.linalg import spsolve

OUT = Path(__file__).with_name('results.json')
R_ENDO = 25.0
T_NORM, T_THIN = 10.0, 5.0
THIN_LO, THIN_HI, TAPER = 0.0, 60.0, 15.0     # degrees
FOV = 80.0                                    # mm, square field
SS = 8                                        # supersampling factor


def thickness(theta_deg):
    """Wall thickness (mm) at angle theta: 5 mm in [0, 60), 10 mm elsewhere, cosine taper of 15 deg."""
    th = np.mod(theta_deg, 360.0)
    # distance (deg) into the thinned sector, measured from its nearest edge (negative outside)
    d = np.minimum(th - THIN_LO, THIN_HI - th)
    d = np.where(th >= THIN_HI, -np.minimum(th - THIN_HI, 360.0 - th + THIN_LO), d)
    w = np.clip((d + TAPER / 2) / TAPER, 0, 1)        # 0 outside, 1 inside, taper across the edge
    w = 0.5 - 0.5 * np.cos(np.pi * w)
    return T_NORM + (T_THIN - T_NORM) * w


def smooth_noise(rng, rms, n_modes=36, corr_deg=10.0):
    """A smooth random radial perturbation e(theta) with the given RMS (mm)."""
    if rms == 0:
        return lambda th: np.zeros_like(th)
    k = np.arange(1, n_modes + 1)
    amp = np.exp(-0.5 * (k * math.radians(corr_deg)) ** 2)
    a = rng.normal(size=n_modes) * amp
    b = rng.normal(size=n_modes) * amp
    norm = math.sqrt(0.5 * np.sum(a ** 2 + b ** 2))
    a, b = a * rms / norm, b * rms / norm

    tg = np.linspace(0.0, 360.0, 7201)
    tr = np.radians(tg)[:, None]
    table = np.sum(a * np.cos(k * tr) + b * np.sin(k * tr), axis=-1)

    def f(th):
        return np.interp(th, tg, table)
    return f


def grid(v, ss=1):
    n = int(round(FOV / v)) * ss
    c = (np.arange(n) + 0.5) * (v / ss) - FOV / 2
    x, y = np.meshgrid(c, c, indexing='xy')
    r = np.hypot(x, y)
    th = np.degrees(np.arctan2(y, x)) % 360.0
    return r, th


def block_mean(a, ss):
    n = a.shape[0] // ss
    return a.reshape(n, ss, n, ss).mean(axis=(1, 3))


def true_depth(r, th):
    """Normalised transmural depth along radial lines (0 endo, 1 epi); <0 cavity, >1 outside."""
    return (r - R_ENDO) / thickness(th)


def masks_from_borders(v, e_endo, e_epi):
    """Voxelised cavity and myocardium (area fraction >= 0.5) for perturbed borders."""
    r, th = grid(v, SS)
    re = R_ENDO + e_endo(th)
    rp = R_ENDO + thickness(th) + e_epi(th)
    cav = block_mean((r < re).astype(np.float32), SS) >= 0.5
    inside_epi = block_mean((r < rp).astype(np.float32), SS) >= 0.5
    myo = inside_epi & ~cav
    return cav, myo


def laplace_depth(cav, myo):
    """Solve Laplace on the myocardium: u=0 on the cavity side, 1 outside. Returns u (nan off myocardium)."""
    idx = -np.ones(myo.shape, dtype=np.int64)
    pts = np.argwhere(myo)
    idx[myo] = np.arange(len(pts))
    n = len(pts)
    rows, cols, vals = [], [], []
    rhs = np.zeros(n)
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ni, nj = pts[:, 0] + di, pts[:, 1] + dj
        nb = idx[ni, nj]
        inmyo = nb >= 0
        rows.append(np.arange(n)[inmyo]); cols.append(nb[inmyo]); vals.append(-np.ones(inmyo.sum()))
        out = ~inmyo & ~cav[ni, nj]          # outside (epicardial side) -> 1
        rhs += out
    rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(4.0 * np.ones(n))
    A = sparse.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
    u = np.full(myo.shape, np.nan)
    u[myo] = spsolve(A, rhs)
    return u


def distance_depth(cav, myo, v):
    """Equal-thickness depth: d_endo / (d_endo + d_epi), Euclidean distances (mm) from each myocardial voxel
    centre to the nearest cavity voxel and to the nearest outside voxel (both minus half a voxel)."""
    d_in = ndimage.distance_transform_edt(~cav) * v - v / 2
    d_out = ndimage.distance_transform_edt(myo | cav) * v - v / 2
    u = np.full(myo.shape, np.nan)
    u[myo] = d_in[myo] / (d_in[myo] + d_out[myo])
    return u, d_in, d_out


def thirds(u):
    lab = np.zeros(u.shape, dtype=np.int8)
    ok = ~np.isnan(u)
    lab[ok] = 1 + np.minimum((u[ok] * 3).astype(int), 2)      # 1 sub-endo, 2 mid, 3 sub-epi
    return lab


def dice(a, b):
    s = a.sum() + b.sum()
    return float(2 * (a & b).sum() / s) if s else float('nan')


def sector_masks(v):
    r, th = grid(v)
    thin = (th >= THIN_LO + TAPER) & (th < THIN_HI - TAPER)
    norm = (th >= 120) & (th < 300)
    return thin, norm, r, th


# ---------------------------------------------------------------- E1 layers from borders
def e1(voxels=(0.25, 0.4, 0.75, 1.5), errors=(0.0, 0.25, 0.5, 1.0), seeds=12):
    res = []
    for v in voxels:
        thin, norm, r, th = sector_masks(v)
        d_true = true_depth(r, th)
        myo_true = (d_true >= 0) & (d_true < 1)
        lab_true = np.zeros(r.shape, np.int8)
        lab_true[myo_true] = 1 + np.minimum((d_true[myo_true] * 3).astype(int), 2)
        for eps in errors:
            rows = []
            for s in range(seeds if eps > 0 else 1):
                rng = np.random.default_rng(1000 * s + int(eps * 100))
                cav, myo = masks_from_borders(v, smooth_noise(rng, eps), smooth_noise(rng, eps))
                u, d_in, d_out = distance_depth(cav, myo, v)
                lab = thirds(u)
                lab_lap = thirds(laplace_depth(cav, myo))
                # thickness: d_endo + d_epi on mid-wall voxels, per sector, median
                tk = np.where(myo & (np.abs(u - 0.5) < 0.17), d_in + d_out, np.nan)
                row = {'myo': dice(myo, myo_true),
                       'laplace_subendo_normal': dice((lab_lap == 1) & norm, (lab_true == 1) & norm),
                       'laplace_mid_normal': dice((lab_lap == 2) & norm, (lab_true == 2) & norm)}
                for k, name in ((1, 'subendo'), (2, 'mid'), (3, 'subepi')):
                    for sec, sm in (('thin', thin), ('normal', norm)):
                        row[f'{name}_{sec}'] = dice((lab == k) & sm, (lab_true == k) & sm)
                row['thick_err_thin'] = float(np.nanmedian(tk[thin]) - T_THIN)
                row['thick_err_normal'] = float(np.nanmedian(tk[norm]) - T_NORM)
                rows.append(row)
            agg = {k: [float(np.mean([r_[k] for r_ in rows])), float(np.std([r_[k] for r_ in rows]))] for k in rows[0]}
            res.append({'voxel_mm': v, 'border_rms_mm': eps, 'n_seeds': len(rows), 'voxels_per_third_thin':
                        round(T_THIN / 3 / v, 1), 'voxels_per_third_normal': round(T_NORM / 3 / v, 1), **agg})
            print('E1', v, eps, {k: round(a[0], 3) for k, a in agg.items()}, flush=True)
    return res


# ---------------------------------------------------------------- image synthesis
def synth(v, fwhm, values, depth_fn=None, scar=None, fat_mm=3.0):
    """Fine-grid image: cavity=blood, myocardium=myo (optionally modified), epicardial fat ring, outside=0 HU
    soft tissue-ish (lung/pericardium mix not modelled). Blur on the fine grid, block-average to v."""
    r, th = grid(v, SS)
    d = true_depth(r, th)
    img = np.full(r.shape, values['outside'], np.float32)
    rp = R_ENDO + thickness(th)
    img[(r >= rp) & (r < rp + fat_mm)] = values['fat']
    img[(d >= 0) & (d < 1)] = values['myo']
    img[d < 0] = values['blood']
    if scar is not None:                    # scar: subendocardial, depth < T, within a sector
        lo, hi, T, val = scar
        sm = (th >= lo) & (th < hi) & (d >= 0) & (d < T)
        img[sm] = val
    if depth_fn is not None:
        m = (d >= 0) & (d < 1)
        img[m] = depth_fn(d[m], th[m])
    sig = fwhm / 2.355 / (v / SS)
    img = ndimage.gaussian_filter(img, sig) if fwhm > 0 else img
    return block_mean(img, SS)


# ---------------------------------------------------------------- E2 perfusion ratio bias
def e2(v=0.5, fwhms=(0.0, 0.6, 0.8, 1.0, 1.5), guards=(0.0, 0.5, 1.0), noise=25.0, seeds=20):
    """Static stress CTP-like image. Normal: myocardium 110 HU. Ischaemic sector (normal-thickness wall,
    120-180 deg): inner half of the wall at 80 HU. Blood 400 HU, epicardial fat -90 HU, outside 30 HU.
    TPR = mean(sub-endo third) / mean(sub-epi third) per 60-degree sector, with a guard band g (mm)
    removed from the endocardial and epicardial sides of the measurement."""
    vals = {'blood': 400.0, 'myo': 110.0, 'fat': -90.0, 'outside': 30.0}

    def isch(dd, tt):
        out = np.full(dd.shape, 110.0, np.float32)
        out[(tt >= 120) & (tt < 180) & (dd < 0.5)] = 80.0
        return out
    r, th = grid(v)
    d = true_depth(r, th)
    tk = thickness(th)
    res = []
    sectors = {'normal': (240, 300), 'ischaemic': (130, 170), 'thin_normal': (THIN_LO + TAPER, THIN_HI - TAPER)}
    truth = {'normal': 1.0, 'ischaemic': 80.0 / ((80 + 110) / 2 * 0 + 110.0), 'thin_normal': 1.0}
    # true TPR of the ischaemic sector: sub-endo third all 80, sub-epi third all 110
    truth['ischaemic'] = 80.0 / 110.0
    for f in fwhms:
        clean = synth(v, f, vals, depth_fn=isch)
        for g in guards:
            gd = g / tk                                # guard as a fraction of the wall
            endo = (d >= gd) & (d < 1 / 3)
            epi = (d >= 2 / 3) & (d < 1 - gd)
            row = {'voxel_mm': v, 'fwhm_mm': f, 'guard_mm': g}
            for name, (lo, hi) in sectors.items():
                sm = (th >= lo) & (th < hi)
                tprs = []
                for s in range(seeds):
                    img = clean + np.random.default_rng(s).normal(0, noise, clean.shape)
                    tprs.append(img[endo & sm].mean() / img[epi & sm].mean())
                row[f'tpr_{name}'] = [float(np.mean(tprs)), float(np.std(tprs))]
                row[f'n_endo_vox_{name}'] = int((endo & sm).sum())
                row[f'true_tpr_{name}'] = truth[name]
            row['separation'] = row['tpr_normal'][0] - row['tpr_ischaemic'][0]
            res.append(row)
            print('E2', f, g, {k: (round(x[0], 3) if isinstance(x, list) else x) for k, x in row.items()}, flush=True)
    return res


# ---------------------------------------------------------------- E3 LIE transmurality
BINS = (0.0, 0.01, 0.26, 0.51, 0.76, 1.01)   # Kim 2000: 0, 1-25, 26-50, 51-75, 76-100 %


def tbin(x):
    return int(np.digitize(x, BINS) - 1)


def e3(v=0.5, fwhm=1.0, contrasts=(30.0, 50.0, 80.0), noises=(8.0, 15.0, 25.0), Ts=(0.0, 0.2, 0.4, 0.6, 0.9),
       smooth_mm=(0.0, 1.5), border_err=(0.0, 0.5), seeds=8):
    """LIE image: remote myocardium 90 HU, blood pool 130 HU, scar 90+C HU, fat -90, outside 30. Scar is
    subendocardial with transmurality T in a 60-degree sector (180-240 deg, normal 10 mm wall). Borders come
    from a co-registered CCTA segmentation (truth, or perturbed with RMS error). After optional Gaussian
    smoothing, a voxel is scar if above a threshold set on a remote mid-wall ROI (270-330 deg, depth 0.25-0.75):
      sd2 / sd3: remote mean + 2 / 3 SD;  half: remote mean + half of (sector 99th percentile - remote mean).
    Transmurality per radial chord (1-degree bins) = fraction of chord voxels above threshold; sector value =
    mean over chords (185-235 deg). Bin accuracy uses Kim 2000's bins (0, 1-25, 26-50, 51-75, 76-100 %)."""
    res = []
    r, th = grid(v)
    methods = ('sd2', 'sd3', 'half')
    cache, mcache = {}, {}
    for C in contrasts:
        for T in Ts:
            vals = {'blood': 130.0, 'myo': 90.0, 'fat': -90.0, 'outside': 30.0}
            cache[C, T] = synth(v, fwhm, vals, scar=(180, 240, T, 90.0 + C))
    for C in contrasts:
        for sd in noises:
            for sm_mm in smooth_mm:
                for be in border_err:
                    for T in Ts:
                        est = {m: [] for m in methods}
                        for s in range(seeds):
                            rng = np.random.default_rng(7 * s + 1)
                            img = cache[C, T] + rng.normal(0, sd, cache[C, T].shape)
                            if sm_mm > 0:
                                img = ndimage.gaussian_filter(img, sm_mm / 2.355 / v)
                            if (s, be) not in mcache:
                                mrng = np.random.default_rng(97 * s + 5)
                                cav, myo = masks_from_borders(v, smooth_noise(mrng, be), smooth_noise(mrng, be))
                                mcache[s, be] = (cav, myo, distance_depth(cav, myo, v)[0])
                            cav, myo, u = mcache[s, be]
                            remote = myo & (th >= 270) & (th < 330) & (u >= 0.25) & (u <= 0.75)
                            mu, sdv = img[remote].mean(), img[remote].std()
                            sec = myo & (th >= 185) & (th < 235)
                            thr = {'sd2': mu + 2 * sdv, 'sd3': mu + 3 * sdv,
                                   'half': mu + 0.5 * (np.percentile(img[sec], 99) - mu)}
                            chords = np.floor(th[sec]).astype(int)
                            cnt = np.bincount(chords, minlength=360)
                            ok = cnt > 0
                            for m in methods:
                                frac = np.bincount(chords, weights=img[sec] > thr[m], minlength=360)
                                est[m].append(float(np.mean(frac[ok] / cnt[ok])))
                        row = {'contrast_HU': C, 'noise_sd_HU': sd, 'smooth_fwhm_mm': sm_mm, 'border_rms_mm': be,
                               'true_T': T}
                        for m in methods:
                            row[f'est_{m}'] = [float(np.mean(est[m])), float(np.std(est[m]))]
                            row[f'binacc_{m}'] = float(np.mean([tbin(x) == tbin(T) for x in est[m]]))
                        res.append(row)
                        print('E3', C, sd, sm_mm, be, T, {m: round(row[f'est_{m}'][0], 2) for m in methods}, flush=True)
    return res


if __name__ == '__main__':
    which = sys.argv[1:] or ['E1', 'E2', 'E3']
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    out = {'geometry': {'r_endo_mm': R_ENDO, 'wall_mm': T_NORM, 'thin_wall_mm': T_THIN,
                        'thin_sector_deg': [THIN_LO, THIN_HI], 'taper_deg': TAPER, 'supersampling': SS},
           **{k: prev[k] for k in ('E1', 'E2', 'E3') if k in prev}}
    for k, fn in (('E1', e1), ('E2', e2), ('E3', e3)):
        if k in which:
            out[k] = fn()
            OUT.write_text(json.dumps(out, indent=1) + '\n')
    print('wrote', OUT)
