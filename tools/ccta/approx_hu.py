"""Convert the non-HU scans in CCTA-Pool to an approximate HU scale (project lead's request, 2026-10-12).

Two sources were released without Hounsfield units:
  HOCMvalvesSeg         uint8, display-windowed by the authors (window unknown). Its labels give tissue anchors:
                        myocardium (6) median -> 110 HU, LV blood pool (5) median -> 420 HU (aorta 3 if LV is
                        missing). Values at 0 were below the window (fat, lung, air) and become -1000 HU; values at
                        255 were above it and stay at the window top (bone and the brightest contrast are lost).
  Figshare-CardiacCT15  normalised float. No labels: a 3-component Gaussian mixture on body voxels finds the soft
                        tissue peak (-> 50 HU) and the contrast blood peak (-> 400 HU); the clipped minimum -> -1000.

Approximate only: the anchors are typical values, not measurements of these scans. A linear map cannot restore
what the windowing cut off. The original file is kept on Girder as ct_source.nii.gz; the converted volume
becomes ct.nii.gz (int16) with hu_calibrated='approximate' and the fit in hu_mapping. Idempotent.

Usage: GIRDER_TOKEN_FILE=... approx_hu.py [--dataset HOCMvalvesSeg|Figshare-CardiacCT15] [--dry-run DIR]"""
import argparse, json, os, shutil, sys, tempfile
import numpy as np, nibabel as nib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ccta_ingest

MYO_HU, BLOOD_HU = 110.0, 420.0          # HOCM anchors (contrast-enhanced myocardium, LV blood pool)
TISSUE_HU, BLOOD_HU_FIG = 50.0, 400.0    # Figshare anchors (soft-tissue peak, contrast blood peak)


def map_hocm(img, lab):
    a = img.astype(np.float32)
    myo = a[lab == 6]
    blood = a[lab == 5] if (lab == 5).sum() > 1000 else a[lab == 3]
    if myo.size < 1000 or blood.size < 1000:
        raise ValueError('labels lack myocardium or blood pool; cannot anchor')
    m, b = float(np.median(myo)), float(np.median(blood))
    if b - m < 30:
        raise ValueError(f'blood ({b}) and myocardium ({m}) too close to anchor')
    slope = (BLOOD_HU - MYO_HU) / (b - m)
    hu = MYO_HU + (a - m) * slope
    hu[img == 0] = -1000.0
    return hu, dict(method='two tissue anchors from the case labels', myocardium_value=m, blood_value=b,
                    anchors_hu=[MYO_HU, BLOOD_HU], slope_hu_per_unit=round(slope, 4),
                    window_hu=[round(MYO_HU - m * slope, 1), round(MYO_HU + (255 - m) * slope, 1)],
                    clipped_low_to=-1000, clipped_high_note='values at 255 stay at the window top')


def map_figshare(img):
    from sklearn.mixture import GaussianMixture
    a = img.astype(np.float32)
    lo = float(a.min())
    v = a[::3, ::3, ::3].ravel()
    v = v[v > lo + 0.3 * (np.median(v) - lo)]          # drop the clipped air/lung floor
    g = GaussianMixture(3, random_state=0).fit(v[:, None])
    mu, w = g.means_.ravel(), g.weights_
    tissue = float(mu[np.argmax(w)])
    hi = [i for i in range(3) if mu[i] > tissue and w[i] >= 0.04]
    if not hi:
        raise ValueError(f'no contrast peak above the tissue peak (means {mu}, weights {w})')
    blood = float(mu[max(hi, key=lambda i: mu[i])])
    slope = (BLOOD_HU_FIG - TISSUE_HU) / (blood - tissue)
    hu = TISSUE_HU + (a - tissue) * slope
    hu[a <= lo + 1e-4] = -1000.0
    return hu, dict(method='3-component Gaussian mixture: soft-tissue and contrast peaks', tissue_value=round(tissue, 4),
                    blood_value=round(blood, 4), anchors_hu=[TISSUE_HU, BLOOD_HU_FIG], slope_hu_per_unit=round(slope, 3),
                    gmm_means=[round(float(x), 4) for x in mu], gmm_weights=[round(float(x), 4) for x in w],
                    clipped_low_to=-1000)


def check(hu):
    body = hu[hu > -500]
    return {'p50': float(np.percentile(body, 50)), 'p95': float(np.percentile(body, 95)),
            'p99_5': float(np.percentile(body, 99.5))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', action='append', choices=['HOCMvalvesSeg', 'Figshare-CardiacCT15'])
    ap.add_argument('--dry-run', metavar='DIR', help='convert the first case of each dataset into DIR; no Girder writes')
    args = ap.parse_args()
    pool = ccta_ingest.Pool()
    for dsname in args.dataset or ['HOCMvalvesSeg', 'Figshare-CardiacCT15']:
        ds = [f for f in pool.req('GET', 'folder', {'parentType': 'collection', 'parentId': pool.coll['_id'], 'limit': 0})
              if f['name'] == dsname][0]
        for case in pool.req('GET', 'folder', {'parentType': 'folder', 'parentId': ds['_id'], 'limit': 0}):
            items = {it['name']: it for it in pool.req('GET', 'item', {'folderId': case['_id'], 'limit': 0})}
            if 'ct_source.nii.gz' in items and 'ct.nii.gz' in items:
                print('done already', dsname, case['name'], flush=True)
                continue
            src_item = items.get('ct_source.nii.gz') or items['ct.nii.gz']   # resume after an interrupted run
            work = tempfile.mkdtemp(prefix='hu-')
            try:
                src = os.path.join(work, 'src.nii.gz')
                open(src, 'wb').write(pool.req('GET', f"item/{src_item['_id']}/download", raw=True))
                im = nib.load(src)
                img = np.asarray(im.dataobj)
                if dsname == 'HOCMvalvesSeg':
                    lp = os.path.join(work, 'lab.nii.gz')
                    open(lp, 'wb').write(pool.req('GET', f"item/{items['label.nii.gz']['_id']}/download", raw=True))
                    hu, fit = map_hocm(img, np.asarray(nib.load(lp).dataobj))
                else:
                    hu, fit = map_figshare(img)
                fit['result_percentiles_hu'] = {k: round(v, 1) for k, v in check(hu).items()}
                hdr = im.header.copy(); hdr.set_data_dtype(np.int16); hdr.set_slope_inter(1, 0)
                out = os.path.join(work, 'ct.nii.gz')
                nib.save(nib.Nifti1Image(np.clip(np.rint(hu), -1024, 3071).astype(np.int16), im.affine, hdr), out)
                if args.dry_run:
                    os.makedirs(args.dry_run, exist_ok=True)
                    shutil.copy(out, os.path.join(args.dry_run, f'{dsname}__{case["name"]}.nii.gz'))
                    print(json.dumps({'case': case['name'], **fit}), flush=True)
                    break
                old = src_item
                meta = {k: v for k, v in (old.get('meta') or {}).items() if k not in ('role', 'superseded_by')}
                if old['name'] != 'ct_source.nii.gz':
                    # keep the original, renamed, then add the converted volume as ct.nii.gz
                    pool.req('PUT', f"item/{old['_id']}", {'name': 'ct_source.nii.gz'})
                    for f in pool.req('GET', f"item/{old['_id']}/files"):
                        pool.req('PUT', f"file/{f['_id']}", {'name': 'ct_source.nii.gz'})
                    pool.req('PUT', f"item/{old['_id']}/metadata", body=json.dumps(
                        {'role': 'original as released (not HU)', 'superseded_by': 'ct.nii.gz'}).encode(),
                        ctype='application/json')
                meta.update(hu_calibrated='approximate', hu_mapping=fit, intensity='approximate HU (int16), see hu_mapping',
                            source_file='ct_source.nii.gz', sha256=ccta_ingest.sha256(out),
                            hu_p99=round(float(np.percentile(hu[::4, ::4, ::4], 99)), 1), hu_min=-1000.0)
                pool.upload(case['_id'], out, 'ct.nii.gz', meta)
                print('converted', dsname, case['name'], fit['result_percentiles_hu'], flush=True)
            finally:
                shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
