"""Quality-check helper for one Girder volume: download -> canonical orientation -> measurements + a 6-panel PNG.
Used by the QC agents so every volume is judged from the same picture and the same numbers.

  qc_render.py <item_id> <out_dir>     -> <out_dir>/<item_name>.png and prints one JSON line of measurements

Panels (radiological convention: patient's right on the image's left; anterior up in axial, superior up):
  1-3  axial slices at 30 %, 50 %, 70 % of the z extent           window W 800 / L 200
  4    coronal slice through the centre                            window W 800 / L 200
  5    sagittal slice through the centre                           window W 800 / L 200
  6    coronal maximum-intensity projection of the central 40 %    window 150..900 (contrast vessels)
Measurements: shape, spacing (mm), field of view (mm), HU percentiles of body voxels, fraction of body voxels
150..1000 HU (contrast-like), an aortic-root/LV proxy (99th percentile of the central third), dtype."""
import json, os, sys, tempfile
import numpy as np, nibabel as nib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ccta_ingest


def main(item_id, out_dir):
    pool = ccta_ingest.Pool()
    item = pool.req('GET', f'item/{item_id}')
    os.makedirs(out_dir, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix='.nii.gz', dir=out_dir); os.close(fd)
    try:
        open(tmp, 'wb').write(pool.req('GET', f'item/{item_id}/download', raw=True))
        im = nib.as_closest_canonical(nib.load(tmp))          # RAS+: +x patient right, +y anterior, +z superior
        a = np.asarray(im.dataobj, dtype=np.float32)
        sp = [float(z) for z in im.header.get_zooms()[:3]]
    finally:
        os.remove(tmp)
    if a.ndim > 3:
        a = a[..., 0]
    body = a[a > -500]
    pct = (np.percentile(body, [1, 5, 50, 95, 99]) if body.size else np.zeros(5)).round(1).tolist()
    cx = [slice(s // 3, 2 * s // 3) for s in a.shape]
    central = a[tuple(cx)]
    meas = dict(item=item['name'], item_id=item_id, shape=list(a.shape), spacing_mm=[round(s, 3) for s in sp],
                fov_mm=[round(n * s, 1) for n, s in zip(a.shape, sp)], hu_pct_1_5_50_95_99=pct,
                frac_contrast_like=round(float(((body > 150) & (body < 1000)).mean()) if body.size else 0, 4),
                central_p99=round(float(np.percentile(central, 99)), 1), dtype=str(im.get_data_dtype()),
                hu_calibrated=(item.get('meta') or {}).get('hu_calibrated', True), source=(item.get('meta') or {}).get('source'))
    # RAS+ arrays; radiological display puts +x (patient right) on the image's left -> fliplr
    def ax(z):  return np.fliplr(np.flipud(a[:, :, z].T))   # rows = y (anterior up), cols = x (patient right left)
    def cor(y): return np.fliplr(np.flipud(a[:, y, :].T))   # rows = z (superior up)
    def sag(x): return np.flipud(a[x, :, :].T)           # rows = z, cols = y (posterior->anterior)
    nz = a.shape[2]
    zs = [int(nz * f) for f in (0.3, 0.5, 0.7)]
    y0, y1 = int(a.shape[1] * 0.3), int(a.shape[1] * 0.7)
    mip = np.fliplr(np.flipud(a[:, y0:y1, :].max(axis=1).T))
    asp_c, asp_s = sp[2] / sp[0], sp[2] / sp[1]
    f, axs = plt.subplots(2, 3, figsize=(13, 9))
    panels = [(ax(z), f'axial z={z}/{nz}', 1.0) for z in zs] + [
        (cor(a.shape[1] // 2), 'coronal (centre)', asp_c), (sag(a.shape[0] // 2), 'sagittal (centre)', asp_s),
        (mip, 'coronal MIP, central 40 %', asp_c)]
    for k, (img, title, asp) in enumerate(panels):
        lo, hi = (150, 900) if k == 5 else (-200, 600)
        axs.flat[k].imshow(img, cmap='gray', vmin=lo, vmax=hi, aspect=asp, interpolation='nearest')
        axs.flat[k].set_title(title, fontsize=10); axs.flat[k].axis('off')
    f.suptitle(f"{item['name']}  shape {a.shape}  spacing {[round(s, 2) for s in sp]} mm", fontsize=10)
    plt.tight_layout()
    png = os.path.join(out_dir, item['name'].replace('.nii.gz', '') + '.png')
    plt.savefig(png, dpi=60); plt.close(f)
    meas['png'] = png
    print(json.dumps(meas))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
