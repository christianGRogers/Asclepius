"""In-plane spatial-frequency content of the CT around the coronary tree: how much signal power lies above the
Nyquist frequency of a 0.5 mm grid (1.0 cycle/mm) and of a 0.7 mm grid (0.714 cycle/mm), i.e. what isotropic
0.5 / 0.7 mm resampling cannot represent. Per case: 2D FFT of every axial slice of a 96 x 96 mm in-plane crop
centred on the coronary tree (ImageCAS-X label bbox centre), Hann-windowed; radial power profile vs frequency.
Also the same for slices of pure noise estimate: power in the outermost band (> 1.3 cyc/mm) is treated as noise floor.
Usage: ct_spectrum.py <out.json> [n_cases]"""
import os, sys, json
import numpy as np, nibabel as nib
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
W = SCR + '/work/Atlas'
excl = set(int(x) for x in open(W + '/icx/exclude.txt').read().split())
cases = sorted(f[:5] for f in os.listdir(SCR + '/data/ct') if f.endswith('.nii.gz') and int(f[1:5]) + 1 not in excl)
n = int(sys.argv[2]) if len(sys.argv) > 2 else len(cases)
out = []
for c in cases[:n]:
    li = nib.load(W + '/icx/%d.coronary.nii.gz' % (int(c[1:]) + 1)); lab = np.asarray(li.dataobj) > 0
    sp = float(li.header.get_zooms()[0])
    idx = np.nonzero(lab); cen = [int((i.min() + i.max()) / 2) for i in idx]
    half = int(round(48 / sp)); z0, z1 = idx[2].min(), idx[2].max() + 1
    ct = nib.load(SCR + '/data/ct/%s.nii.gz' % c)
    x0 = max(cen[0] - half, 0); y0 = max(cen[1] - half, 0)
    vol = np.asarray(ct.dataobj[x0:x0 + 2 * half, y0:y0 + 2 * half, z0:z1], dtype=np.float32)
    N = vol.shape[0]; M = vol.shape[1]
    win = np.outer(np.hanning(N), np.hanning(M))[:, :, None]
    v = (vol - vol.mean((0, 1), keepdims=True)) * win
    Pw = (np.abs(np.fft.fft2(v, axes=(0, 1))) ** 2).sum(2)
    fx = np.fft.fftfreq(N, d=sp); fy = np.fft.fftfreq(M, d=sp)
    fr = np.sqrt(fx[:, None] ** 2 + fy[None, :] ** 2)
    nyq = 0.5 / sp
    tot = Pw[(fr > 0.02)].sum()
    noise_density = Pw[(fr > 0.85 * nyq) & (fr <= nyq)].mean()  # outermost ring, treated as white-noise floor
    res = dict(case=c, sp=sp, native_nyquist=nyq)
    for nm, f0 in [('above_0.5mm_nyq', 1.0), ('above_0.7mm_nyq', 0.5 / 0.7)]:
        sel = (fr > f0) & (fr <= nyq)
        res[nm + '_frac'] = float(Pw[sel].sum() / tot)
        res[nm + '_frac_minus_noise'] = float(max(Pw[sel].sum() - noise_density * sel.sum(), 0) / tot)
    # radial profile (log10 power density) for reference
    edges = np.linspace(0, nyq, 15)
    res['profile_f'] = ((edges[:-1] + edges[1:]) / 2).round(3).tolist()
    res['profile_logP'] = [float(np.log10(Pw[(fr >= a) & (fr < b)].mean())) for a, b in zip(edges[:-1], edges[1:])]
    out.append(res); print(c, sp, {k: round(v, 5) for k, v in res.items() if 'frac' in k}, flush=True)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
