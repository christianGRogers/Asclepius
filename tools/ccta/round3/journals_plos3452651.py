"""Round 3 (agent Journals): PLOS ONE 2016 supplement, figshare 3452651 -> CCTA-Pool.

Peng C. et al., "The Impact of the Geometric Characteristics on the Hemodynamics in the Stenotic Coronary
Artery", PLoS ONE 11(6): e0157490 (2016), doi:10.1371/journal.pone.0157490 (CC BY 4.0). Supporting
Information S1-S15 File ("The CTA images of the patient N", RAR) = one coronary CTA series per patient,
exported as 8-bit RGB JPEG slices (512x512, windowed, no DICOM header, no HU, no spacing). Shenzhen Sun Yat-Sen
Cardiovascular Hospital, 2015, patients with invasive FFR. A red tick ruler is burnt in (left edge and bottom);
it is removed (set to 0) and its tick pitch gives the in-plane pixel size assuming 1 cm ticks. Slice spacing
is not stated; 0.5 mm is assumed (206-304 slices per series = at most 160 mm, as on a 320-row 0.5 mm
volume scanner; vertebral-pitch estimates on 17 cases mostly gave 0.42-0.6 mm). A first upload used the
noisy per-case vertebral estimate; --fix replaces the ct.nii.gz contents of already uploaded cases in place
(same item, new sha256/spacing metadata; nothing is deleted).

    python3 -I journals_plos3452651.py --dry-run [--case P01] [--stage DIR]
    python3 -I journals_plos3452651.py [--case ...] [--limit N]           # upload (needs GIRDER_TOKEN_FILE)
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, tempfile
import numpy as np, nibabel as nib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import ingest_open as io_  # noqa: E402

ART = 3452651
Z_MM = 0.5   # assumed slice spacing (not stated in the paper or files)
DATASET = 'PLOS-Peng2016-CCTA-JPEG'
URL = 'https://doi.org/10.6084/m9.figshare.3452651.v1'
CITATION = ('Peng C, Wang X, Xian Z, Liu X, Huang W, Xu P, Wang J (2016). The Impact of the Geometric '
            'Characteristics on the Hemodynamics in the Stenotic Coronary Artery. PLoS ONE 11(6): e0157490. '
            'https://doi.org/10.1371/journal.pone.0157490 ; Supporting Information S1-S15 File, figshare '
            'https://doi.org/10.6084/m9.figshare.3452651.v1 (CC BY 4.0)')
DESC = ('Coronary CTA (FFR patients, Shenzhen Sun Yat-Sen Cardiovascular Hospital, 2015) from the PLOS ONE '
        'supplement of Peng et al. 2016: one series per patient, released as 8-bit windowed JPEG slices. NOT HU '
        '(hu_calibrated=false, display-windowed grey values 0-255). Spacing is ESTIMATED: in-plane from the '
        'burnt-in 1 cm ruler ticks, slice spacing from the vertebral pitch (see spacing_method per case). The '
        'ruler overlay was zeroed. Heart-cropped FOV. Different hospital from ImageCAS (Guangdong Provincial).')


def files():
    import urllib.request
    d = json.load(urllib.request.urlopen(f'https://api.figshare.com/v2/articles/{ART}', timeout=120))
    out = []
    for f in d['files']:
        m = re.match(r'S(\d+) File\.RAR$', f['name'], re.I)
        if m:
            out.append((int(m.group(1)), f))
    return sorted(out)


def load_stack(d):
    from PIL import Image
    fs = sorted(p for p in glob.glob(os.path.join(d, '**', '*'), recursive=True) if p.lower().endswith(('.jpg', '.jpeg')))
    series = {}
    for p in fs:   # IMG-<series>-<slice>.jpg
        m = re.search(r'IMG-(\d+)-(\d+)\.jpe?g$', os.path.basename(p), re.I)
        series.setdefault((os.path.dirname(p), m.group(1) if m else ''), []).append((int(m.group(2)) if m else 0, p))
    out = []
    for key, lst in series.items():
        lst.sort()
        rgb = np.stack([np.asarray(Image.open(p).convert('RGB')) for _, p in lst]).astype(np.int16)  # z,y,x,3
        out.append((key, [os.path.relpath(p, d) for _, p in lst], rgb))
    return out


def ruler_mm_per_px(rgb):
    """Tick pitch of the red ruler on the left edge (1 cm ticks assumed) -> mm per pixel."""
    a = rgb[rgb.shape[0] // 2]
    red = (a[..., 0] - a[..., 1] > 60) & (a[..., 0] - a[..., 2] > 60)
    ys = np.unique(np.nonzero(red[:, :12])[0])
    if len(ys) < 4:
        return None, red
    # tick centres: groups of consecutive rows
    groups, cur = [], [ys[0]]
    for y in ys[1:]:
        if y - cur[-1] <= 2:
            cur.append(y)
        else:
            groups.append(np.mean(cur)); cur = [y]
    groups.append(np.mean(cur))
    if len(groups) < 4:
        return None, red
    pitch = float(np.median(np.diff(groups)))
    return 10.0 / pitch, red


def vertebral_pitch_slices(g):
    """Dominant period (slices) of the bright endplate/disc pattern in a posterior paramedian column box."""
    z, y, x = g.shape
    best = None
    # find the spine: brightest compact region in the lower-middle part of the image
    sub = g[:, int(y * 0.7):, int(x * 0.25):int(x * 0.75)].astype(np.float32)
    m = sub.mean(0)
    yy, xx = np.unravel_index(np.argmax(m), m.shape)
    yy += int(y * 0.7); xx += int(x * 0.25)
    prof = g[:, max(0, yy - 15):yy + 15, max(0, xx - 15):xx + 15].mean((1, 2))
    prof = prof - np.convolve(prof, np.ones(61) / 61, mode='same')
    prof = prof[30:-30] if len(prof) > 120 else prof
    prof = (prof - prof.mean()) / (prof.std() + 1e-6)
    # a cardiac CTA covers ~95-200 mm; with a ~27 mm vertebral pitch this bounds the period (in slices)
    lo, hi = max(8, int(z * 27 / 200)), min(len(prof) // 2, int(z * 27 / 95) + 1)
    ac = [float(np.mean(prof[:-k] * prof[k:])) for k in range(lo, hi + 1)]
    if ac:
        best = lo + int(np.argmax(ac))
    return best


def convert(rar, work, case):
    x = os.path.join(work, 'x')
    os.makedirs(x)
    subprocess.run(['bsdtar', '-xf', rar, '-C', x], check=True)
    os.remove(rar)
    stacks = load_stack(x)
    stacks.sort(key=lambda s: -len(s[1]))
    (key, names, rgb) = stacks[0]
    mmpx, red = ruler_mm_per_px(rgb)
    redall = (rgb[..., 0] - rgb[..., 1] > 60) & (rgb[..., 0] - rgb[..., 2] > 60)
    g = rgb.mean(-1)
    g[redall] = 0
    g = np.clip(np.rint(g), 0, 255).astype(np.uint8)       # z, y(rows: anterior->posterior), x(cols: R->L)
    pitch = vertebral_pitch_slices(g)
    sz_est = round(27.0 / pitch, 3) if pitch else None
    sz = Z_MM   # see Z_MM: the vertebral estimate is noisy (harmonics), kept only as a cross-check
    sxy = round(mmpx, 4) if mmpx else None
    a = np.ascontiguousarray(np.transpose(g, (2, 1, 0)))     # x, y, z
    sp = (sxy or 1.0, sxy or 1.0, sz or 1.0)
    aff = np.diag([-sp[0], -sp[1], -sp[2], 1.0])            # cols -> patient left, rows -> posterior, slices -> inferior
    aff[:3, 3] = -aff[:3, :3] @ ((np.array(a.shape) - 1) / 2)
    nii = os.path.join(work, 'ct.nii.gz')
    io_.save_nifti(a, aff, nii)
    extra = dict(source_ids={'figshare_article': ART, 'supplement': f'S{case[1:].lstrip("0")} File.RAR',
                             'series': key[1], 'n_slices': len(names), 'first_member': names[0]},
                 patient_id=case, hu_calibrated=False, intensity='8-bit display-windowed JPEG grey (0-255)',
                 lossy_jpeg=True, spacing_known=False,
                 spacing_method=(f'in-plane {sxy} mm from burnt-in ruler tick pitch assuming 1 cm ticks; slice '
                                 f'{sz} mm ASSUMED (all series have 206-304 slices, i.e. <=160 mm at 0.5 mm, '
                                 f'consistent with a 320-row 0.5 mm volume scan; vertebral-pitch cross-check '
                                 f'{sz_est} mm from {pitch and round(pitch, 1)} slices assuming a 27 mm pitch, '
                                 f'unreliable)'),
                 ruler_overlay_zeroed=bool(redall.any()), slice_order_assumed='first file = superior',
                 orientation_check=io_.anatomy_check(nii, hu=False))
    return nii, extra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--stage', default='ccta-stage')
    ap.add_argument('--work', default=None)
    ap.add_argument('--case', action='append')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--fix', action='store_true', help='rewrite contents of already uploaded cases with Z_MM')
    args = ap.parse_args()
    if args.fix:
        return fix(args)
    sink = io_.Sink(args, DATASET, 'CC BY 4.0', 'T1', URL, DESC, CITATION, hu=False)
    for n, f in files():
        case = f'P{n:02d}'
        if not io_.selected(args, case) or sink.done(case):
            continue
        work = io_.tmpdir(args)
        try:
            rar = io_.download(f['download_url'], os.path.join(work, 'p.rar'))
            nii, extra = convert(rar, work, case)
            extra['source_ids']['figshare_file_id'] = f['id']
            sink.put(case, nii, extra)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        if sink.full():
            break


def fix(args):
    import datetime
    pool = io_.ccta_ingest.Pool()
    ds = pool._folder(pool.coll['_id'], 'collection', DATASET)
    cases = {c['name']: c for c in pool.req('GET', 'folder', {'parentType': 'folder', 'parentId': ds['_id'], 'limit': 0})}
    for n, f in files():
        case = f'P{n:02d}'
        if case not in cases or not io_.selected(args, case):
            continue
        it = [i for i in pool.req('GET', 'item', {'folderId': cases[case]['_id']}) if i['name'] == 'ct.nii.gz'][0]
        if abs((it.get('meta') or {}).get('spacing_mm', [0, 0, 0])[2] - Z_MM) < 1e-6:
            io_.log('ok', case); continue
        fdoc = pool.req('GET', f'item/{it["_id"]}/files')[0]
        work = io_.tmpdir(args)
        try:
            rar = io_.download(f['download_url'], os.path.join(work, 'p.rar'))
            nii, extra = convert(rar, work, case)
            extra['source_ids']['figshare_file_id'] = f['id']
            size = os.path.getsize(nii)
            up = pool.req('PUT', f'file/{fdoc["_id"]}/contents', {'size': size})
            with open(nii, 'rb') as fh:
                off = 0
                while off < size:
                    data = fh.read(io_.ccta_ingest.CHUNK)
                    up = pool.req('POST', 'file/chunk', {'uploadId': up['_id'], 'offset': off}, body=data,
                                  ctype='application/octet-stream')
                    off += len(data)
            meta = dict(it.get('meta') or {})
            meta.update(io_.ccta_ingest.qc(nii), **extra, sha256=io_.ccta_ingest.sha256(nii),
                        spacing_fixed=datetime.date.today().isoformat())
            pool.req('PUT', f'item/{it["_id"]}/metadata', body=json.dumps(meta).encode(), ctype='application/json')
            io_.log('fixed', case, meta['spacing_mm'])
        finally:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
