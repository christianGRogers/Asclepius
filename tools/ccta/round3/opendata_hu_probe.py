"""Download one IDC series (s5cmd, no login), convert, print shape/spacing/HU percentiles + blood-pool estimate,
save a preview PNG. Usage: opendata_hu_probe.py <s3 url> <workdir> <png>"""
import glob, os, shutil, subprocess, sys
import nibabel as nib, numpy as np
S5 = os.path.join(os.path.dirname(__import__('s5cmd').__file__), 'bin', 's5cmd')
url, work, png = sys.argv[1:4]
dcm, nii = os.path.join(work, 'dcm'), os.path.join(work, 'nii')
shutil.rmtree(work, ignore_errors=True); os.makedirs(dcm); os.makedirs(nii)
subprocess.run([S5, '--no-sign-request', '--endpoint-url', 'https://s3.amazonaws.com', 'cp', url, dcm + '/'], check=True, stdout=subprocess.DEVNULL)
subprocess.run(['dcm2niix', '-z', 'y', '-b', 'n', '-o', nii, '-f', 'v_%s_%t', dcm], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
shutil.rmtree(dcm)
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fs = sorted(glob.glob(nii + '/*.nii.gz'), key=os.path.getsize)
for f in fs:
    im = nib.load(f); a = np.asarray(im.dataobj, dtype=np.float32)
    if a.ndim == 4: a = a[..., 0]
    p = np.percentile(a[::2, ::2, ::2], [50, 95, 99, 99.9])
    bp = a[(a > 150) & (a < 800)]
    print(os.path.basename(f), a.shape, im.header.get_zooms()[:3], 'pct', p.round(0), 'n150-800', bp.size, 'med', np.median(bp) if bp.size else None)
f = fs[-1]; a = np.asarray(nib.load(f).dataobj, dtype=np.float32)
if a.ndim == 4: a = a[..., 0]
z = a.shape[2] // 2
fig, ax = plt.subplots(1, 2, figsize=(10, 5))
ax[0].imshow(np.rot90(a[:, :, z]), cmap='gray', vmin=-200, vmax=600); ax[1].imshow(np.rot90(a[:, a.shape[1]//2, :]), cmap='gray', vmin=-200, vmax=600, aspect='auto')
plt.savefig(png, dpi=60); shutil.rmtree(work)
