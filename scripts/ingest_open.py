"""Download + convert adapters for the openly downloadable CCTA sources (CCTA sourcing summary, section 1),
streamed one case at a time into Girder CCTA-Pool through ccta_ingest.Pool.

    ingest_open.py <source> --dry-run [--case ID] [--stage DIR]   # stage ONE case locally, print shape/spacing/HU
    ingest_open.py <source> [--case ID ...] [--limit N]           # upload mode (needs GIRDER_TOKEN_FILE)

Sources: imagechd, imagealcapa, hocm, cadrs (Kaggle younesselbrag), vmr, figshare15, mendeley.
Nothing is ever held locally beyond the case being converted (plus, for the two split-zip Kaggle sets, the
last archive part, 0.1-0.4 GB, which holds the central directory). Dry-run never touches Girder.

Source quirks handled here (see the sourcing agent reports for how they were found):
- Kaggle per-file download works without an account; big files come back wrapped in a one-entry zip
  (deflated, so no random access: such files are streamed); the whole-dataset bundle is a normal zip on GCS
  and is read by HTTP range requests (only the wanted members are fetched).
- ImageCHD / ImageALCAPA: a 13-part (resp. 4-part) split zip; each part is streamed in turn and members are
  cut out of the byte stream using the central directory of the last part. Stored values are HU+1024; the
  header spacing is a 1 mm placeholder with an identity affine. ImageCHD's real spacing comes from the bundled
  xlsx (whose birth/scan dates are never stored); ImageALCAPA has none (flagged spacing_known=false).
- Axis conventions differ between these releases (ImageCHD arrays are in DICOM LPS order, ImageALCAPA and
  HOCM already RAS, VMR varies per contributor). Every converted case gets an automatic anatomy check (spine
  posterior; LV left and anterior where a label exists) and the other convention is applied when the first
  one looks rotated by 180 degrees; results are stored in `orientation_check` / `array_convention`.
- HOCMvalvesSeg: uint8 windowed (no HU) and 1 mm placeholder spacing, stored as is and flagged.
- VMR: .vti volumes with spacing in cm (most) or mm; converted to mm.
- figshare 1379059: RAR archives (extracted with bsdtar) of MetaImage volumes, normalised (not HU) floats.
- Mendeley 9wv3fkxstx: GE/Philips DICOM with series descriptions stripped; the gated cardiac series are
  picked by acquisition mode (CINE) and slice count.
Each dataset folder gets licence, tier, source_url and citation; each case gets source ids in `source_ids`.
"""
import argparse, csv, glob, io, json, mmap, os, re, shutil, struct, subprocess, sys, tempfile, time, urllib.error
import urllib.parse, urllib.request, zipfile, zlib
import numpy as np, nibabel as nib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ccta_ingest  # noqa: E402  (Pool is only constructed in upload mode)

UA = {'User-Agent': 'curl/8.5.0'}   # data.mendeley.com answers 403 to Python's default agent
KAGGLE = 'https://www.kaggle.com/api/v1/datasets'
CC_BY_NC = 'CC BY-NC 4.0'
GUANGDONG = ('Guangdong Provincial People\'s Hospital (same hospital as ImageCAS: different cohort, '
             'patient overlap cannot be ruled out). Non-commercial use only; derived labels must keep '
             'attribution and the NC restriction.')


def log(*a):
    print(*a, flush=True)


# ====================================================================== HTTP
def _open(url, headers=None, timeout=300):
    return urllib.request.urlopen(urllib.request.Request(url, headers=dict(UA, **(headers or {}))), timeout=timeout)


def download(url, path, tries=5):
    """Plain GET to a file, resumed with Range after a dropped connection."""
    for attempt in range(tries):
        have = os.path.getsize(path) if os.path.exists(path) else 0
        try:
            with _open(url, {'Range': f'bytes={have}-'} if have else None) as r, open(path, 'ab' if have else 'wb') as f:
                if have and r.status != 206:
                    f.truncate(0)
                shutil.copyfileobj(r, f, 1 << 20)
            return path
        except urllib.error.HTTPError as e:
            if e.code == 416:
                return path
            if e.code < 500 or attempt == tries - 1:
                raise
        except OSError:
            if attempt == tries - 1:
                raise
        time.sleep(2 ** attempt)


class HTTPFile(io.RawIOBase):
    """Seekable read-only view of a URL through Range requests: block cache, retries, and re-resolution of
    expiring signed redirects (Kaggle -> GCS). Good enough for zipfile.ZipFile."""

    def __init__(self, url, block=8 << 20):
        self.src, self.block, self.pos, self._blk = url, block, 0, (None, b'')
        self._resolve()

    def _resolve(self):
        with _open(self.src, {'Range': 'bytes=0-0'}, timeout=120) as r:
            self.url = r.geturl()
            self.size = int(r.headers['Content-Range'].split('/')[1])

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def _fetch(self, k):
        if self._blk[0] == k:
            return self._blk[1]
        a, b = k * self.block, min((k + 1) * self.block, self.size) - 1
        for attempt in range(8):
            try:
                with _open(self.url, {'Range': f'bytes={a}-{b}'}) as r:
                    d = r.read()
                if len(d) == b - a + 1:
                    self._blk = (k, d)
                    return d
            except urllib.error.HTTPError as e:
                if e.code in (400, 401, 403):   # signed URL expired
                    try:
                        self._resolve()
                    except OSError:
                        pass
                elif e.code < 500:
                    raise
            except OSError:
                pass
            time.sleep(min(60, 2 ** attempt))
        raise IOError(f'range {a}-{b} of {self.src} failed')

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        out = []
        while n > 0:
            k, o = divmod(self.pos, self.block)
            d = self._fetch(k)[o:o + n]
            out.append(d)
            self.pos += len(d)
            n -= len(d)
        return b''.join(out)

    def readinto(self, b):
        d = self.read(len(b))
        b[:len(d)] = d
        return len(d)


# ====================================================================== Kaggle
def kaggle_files(ref):
    files, tok = [], ''
    while True:
        with _open(f'{KAGGLE}/list/{ref}?pageSize=200' + (f'&pageToken={tok}' if tok else '')) as r:
            d = json.load(r)
        files += d['datasetFiles']
        tok = d.get('nextPageToken')
        if not tok:
            return {f['name']: f['totalBytes'] for f in files}


def kaggle_member(ref, path):
    """Readable stream of one dataset file. Large files arrive wrapped in a one-entry zip; unwrap it."""
    f = HTTPFile(f'{KAGGLE}/download/{ref}/{urllib.parse.quote(path)}')
    if f.read(4) == b'PK\x03\x04':
        f.seek(0)
        z = zipfile.ZipFile(f)
        names = z.namelist()
        if len(names) == 1 and names[0] == os.path.basename(path):
            return z.open(names[0])
    f.seek(0)
    return f


def kaggle_bundle(ref):
    """The whole-dataset zip (on GCS), read lazily by range requests."""
    return zipfile.ZipFile(HTTPFile(f'{KAGGLE}/download/{ref}'))


def copy_member(src, dst, n=None):
    with open(dst, 'wb') as f:
        if n is None:
            shutil.copyfileobj(src, f, 1 << 20)
        else:
            while n > 0:
                d = src.read(min(n, 1 << 20))
                if not d:
                    raise IOError('short read')
                f.write(d)
                n -= len(d)
    return dst


# ====================================================================== split zip (z01..zNN + last part)
def central_directory(buf):
    """Entries of a (split, zip64) zip from the bytes of its last part: name, disk, off, cs, method."""
    e = buf.rfind(b'PK\x05\x06')
    _, disk, cddisk, _, ntot, cdsize, cdoff, _ = struct.unpack('<IHHHHIIH', buf[e:e + 22])
    z = buf.rfind(b'PK\x06\x06', 0, e)
    if z >= 0:
        v = struct.unpack('<IQHHIIQQQQ', buf[z:z + 56])
        cddisk, ntot, cdoff = v[5], v[7], v[9]
    if cddisk != disk:
        raise RuntimeError('central directory not in the last part')
    out, p = [], cdoff
    for _ in range(ntot):
        (_, _, _, _, meth, _, _, _, cs, us, nl, el, cl, dstart, _, _, lho) = struct.unpack(
            '<IHHHHHHIIIHHHHHII', buf[p:p + 46])
        name = buf[p + 46:p + 46 + nl].decode('utf8', 'replace')
        ex, q = buf[p + 46 + nl:p + 46 + nl + el], 0
        while q + 4 <= len(ex):
            hid, hs = struct.unpack('<HH', ex[q:q + 4])
            if hid == 1:   # zip64 extra: only the fields that overflowed, in this order
                dat, k = ex[q + 4:q + 4 + hs], 0
                if us == 0xFFFFFFFF:
                    us = struct.unpack('<Q', dat[k:k + 8])[0]; k += 8
                if cs == 0xFFFFFFFF:
                    cs = struct.unpack('<Q', dat[k:k + 8])[0]; k += 8
                if lho == 0xFFFFFFFF:
                    lho = struct.unpack('<Q', dat[k:k + 8])[0]; k += 8
                if dstart == 0xFFFF:
                    dstart = struct.unpack('<I', dat[k:k + 4])[0]
            q += 4 + hs
        out.append(dict(name=name, disk=dstart, off=lho, cs=cs, us=us, method=meth))
        p += 46 + nl + el + cl
    return out


class SplitZip:
    """Kaggle split zip: parts <stem>.z01 ... .zNN plus the last part (renamed .change2zip by the authors).
    The last part is downloaded once (it holds the central directory and, for ImageCHD, the xlsx);
    members are then cut out of the sequential stream of parts, skipping parts that hold nothing wanted."""

    def __init__(self, ref, work):
        self.ref, self.work = ref, work
        files = kaggle_files(ref)
        last = [n for n in files if n.endswith('.change2zip') or n.endswith('.zip')]
        if len(last) != 1:
            raise RuntimeError(f'cannot find the last part among {sorted(files)}')
        stem = last[0].rsplit('.', 1)[0]
        nums = sorted(int(n.rsplit('.z', 1)[1]) for n in files if re.fullmatch(re.escape(stem) + r'\.z\d+', n))
        self.parts = [f'{stem}.z{k:02d}' for k in nums] + last
        self.sizes = [files[p] for p in self.parts]
        self.cum = [0]
        for s in self.sizes:
            self.cum.append(self.cum[-1] + s)
        self.last_path = os.path.join(work, 'last_part.zip')
        if not (os.path.exists(self.last_path) and os.path.getsize(self.last_path) == self.sizes[-1]):
            log(f'downloading last part {last[0]} ({self.sizes[-1] / 1e6:.0f} MB) for the central directory')
            copy_member(kaggle_member(ref, last[0]), self.last_path)
        self._fh = open(self.last_path, 'rb')
        self.buf = mmap.mmap(self._fh.fileno(), 0, access=mmap.ACCESS_READ)
        self.entries = [e for e in central_directory(self.buf) if not e['name'].endswith('/')]
        for e in self.entries:
            e['g'] = self.cum[e['disk']] + e['off']

    def _open_part(self, i):
        if i == len(self.parts) - 1:
            return open(self.last_path, 'rb')
        log(f'  streaming part {self.parts[i]} ({self.sizes[i] / 1e6:.0f} MB)')
        return kaggle_member(self.ref, self.parts[i])

    def read_small(self, name):
        """A member that lies wholly in the last part (e.g. the xlsx), decompressed into memory."""
        e = next(x for x in self.entries if x['name'] == name)
        if e['disk'] != len(self.parts) - 1:
            raise RuntimeError(f'{name} is not in the last part')
        o = e['off']
        nl, el = struct.unpack('<HH', self.buf[o + 26:o + 30])
        d = self.buf[o + 30 + nl + el:o + 30 + nl + el + e['cs']]
        return zlib.decompress(d, -15) if e['method'] == 8 else d

    def extract(self, want, out_dir):
        """Yield (entry, local path) for each wanted entry in archive order; the caller deletes the file."""
        todo = sorted((e for e in self.entries if want(e['name'])), key=lambda e: e['g'])
        part, fh, pos = None, None, None
        for e in todo:
            j = max(i for i in range(len(self.parts)) if self.cum[i] <= e['g'])
            if part is None or j > part and pos < self.cum[j]:   # jump straight to the part holding it
                if fh:
                    fh.close()
                part, fh, pos = j, self._open_part(j), self.cum[j]

            def read(n):
                nonlocal part, fh, pos
                out = []
                while n > 0:
                    d = fh.read(min(n, 1 << 20))
                    if not d:
                        fh.close()
                        part += 1
                        if part >= len(self.parts):
                            raise IOError('unexpected end of split archive')
                        fh = self._open_part(part)
                        continue
                    out.append(d); n -= len(d); pos += len(d)
                return b''.join(out)

            while pos < e['g']:
                read(min(e['g'] - pos, 8 << 20))
            hdr = read(30)
            if hdr[:4] != b'PK\x03\x04':
                raise IOError(f'bad local header for {e["name"]}')
            nl, el = struct.unpack('<HH', hdr[26:30])
            read(nl + el)
            dst = os.path.join(out_dir, os.path.basename(e['name']))
            inf = zlib.decompressobj(-15) if e['method'] == 8 else None
            left = e['cs']
            with open(dst, 'wb') as f:
                while left > 0:
                    d = read(min(left, 4 << 20))
                    left -= len(d)
                    f.write(inf.decompress(d) if inf else d)
                if inf:
                    f.write(inf.flush())
            yield e, dst
        if fh:
            fh.close()


# ====================================================================== conversion + reporting
def save_fixed(src, dst, spacing=None, hu_offset=0, flip_xy=True):
    """Guangdong NIfTI (identity affine, 1 mm placeholder) -> proper RAS affine with the given spacing (x, y, z
    mm; None keeps 1 mm), centred on the origin; optionally subtract an intensity offset. flip_xy=True when the
    array is in DICOM LPS order (ImageCHD), False when it is already RAS (ImageALCAPA, HOCM); established by
    inspecting cases visually (spine posterior, heart/descending aorta on the left, arch superior)."""
    im = nib.load(src)
    a = np.asanyarray(im.dataobj)
    if hu_offset:
        a = a.astype(np.int16) - np.int16(hu_offset)
    sp = spacing or (1.0, 1.0, 1.0)
    s = -1.0 if flip_xy else 1.0
    aff = np.diag([s * sp[0], s * sp[1], sp[2], 1.0])
    aff[:3, 3] = -aff[:3, :3] @ ((np.array(a.shape[:3]) - 1) / 2)
    out = nib.Nifti1Image(a, aff)
    out.header.set_qform(aff, 1)
    out.header.set_sform(aff, 1)
    out.header.set_xyzt_units('mm')
    nib.save(out, dst)
    return dst


def anatomy_check(ct, label=None, lv=None, hu=True):
    """Automatic orientation flags on a converted case (world RAS+: +x = patient right, +y = anterior): is dense
    bone (mostly spine) posterior of the body centre, is the LV label on the patient's left of it and
    anterior of it? A False
    flags a wrong axis convention (or genuine anatomy such as dextrocardia: look before flipping anything)."""
    im = nib.load(ct)
    a = np.asarray(im.dataobj, dtype=np.float32)[::2, ::2, ::2]
    aff = im.affine.copy()
    aff[:3, :3] *= 2
    w = lambda m: nib.affines.apply_affine(aff, np.argwhere(m).mean(0))
    body = w(a > (-300 if hu else np.percentile(a, 60)))
    r = {}
    if hu:   # windowed data saturate blood and bone alike, so the bone test needs HU
        bone = (a > 900) & (a < 2000)   # cortical bone; metal (sternal wires, valves) excluded
        if bone.sum() > 200:
            r['spine_posterior'] = bool(w(bone)[1] < body[1])
    if label is not None and lv is not None:
        l = np.asarray(nib.load(label).dataobj)[::2, ::2, ::2]
        if (l == lv).any():
            c = w(l == lv)
            r['lv_on_patient_left'] = bool(c[0] < body[0])
            r['lv_anterior'] = bool(c[1] > body[1])
    return r


def report(nii, hu=True, png=None):
    """Shape, spacing, intensity stats and an orientation sanity check: the centroid of the bright blood pool
    (250-700 HU, or the top 3 % when not HU) as fractions of the canonical RAS axes, 0 = the patient's
    left / posterior / inferior edge, 1 = right / anterior / superior (expect ~0.4-0.6 / >0.4 / ~0.5), plus
    the automatic anatomy check. Also writes a 3-view preview PNG (radiological display) to look at."""
    im = nib.as_closest_canonical(nib.load(nii))
    a = np.asarray(im.dataobj, dtype=np.float32)
    sub = a[::2, ::2, ::2]
    p = np.percentile(sub, [1, 50, 95, 99, 99.9])
    r = {'shape': list(a.shape), 'spacing_mm': [round(float(z), 4) for z in im.header.get_zooms()[:3]],
         'orientation_codes': ''.join(nib.aff2axcodes(nib.load(nii).affine)),
         'p1_p50_p95_p99_p999': [round(float(x), 2) for x in p], 'min': float(sub.min()), 'max': float(sub.max())}
    if hu:
        blood = (a > 250) & (a < 700)
        r['blood_250_700HU_frac'] = round(float(blood.mean()), 4)
        r['median_HU_of_250_700'] = round(float(np.median(a[blood])), 1) if blood.any() else None
    else:
        thr = np.percentile(sub, 97)
        blood = a > thr
    if blood.any():
        idx = np.argwhere(blood[::2, ::2, ::2]) * 2
        c = idx.mean(0) / (np.array(a.shape) - 1)
        r['bright_centroid_RAS_frac'] = [round(float(x), 2) for x in c]
    r['anatomy_check'] = anatomy_check(nii, hu=hu)
    r['qc_as_stored'] = ccta_ingest.qc(nii)
    if png:
        _preview(a, im.header.get_zooms()[:3], png, (-200, 800) if hu else tuple(np.percentile(sub, [1, 99.5])))
        r['preview_png'] = png
    return r


def _preview(a, z, png, win):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    x, y, s = [d // 2 for d in a.shape]
    f, ax = plt.subplots(1, 3, figsize=(15, 5))
    for k, (sl, asp, t) in enumerate([(a[:, :, s], z[1] / z[0], 'axial: anterior up, patient R on left'),
                                       (a[:, y, :], z[2] / z[0], 'coronal: superior up, patient R on left'),
                                       (a[x, :, :], z[2] / z[1], 'sagittal: superior up, anterior on left')]):
        ax[k].imshow(sl.T[::-1, ::-1], cmap='gray', vmin=win[0], vmax=win[1], aspect=asp)
        ax[k].set_title(t)
    plt.tight_layout()
    plt.savefig(png, dpi=55)
    plt.close(f)


class Sink:
    """Dry-run: keep the first converted case in the stage dir and report it. Upload: Pool.ingest."""

    def __init__(self, args, dataset, licence, tier, source_url, description, citation, hu=True):
        self.args, self.dataset, self.hu, self.n = args, dataset, hu, 0
        self.ds_meta = dict(licence=licence, tier=tier, source_url=source_url, citation=citation)
        if args.dry_run:
            os.makedirs(args.stage, exist_ok=True)
            log(json.dumps(dict(dataset=dataset, description=description, **self.ds_meta), indent=1))
            self.pool = None
        else:
            self.pool = ccta_ingest.Pool()
            self.pool.dataset(dataset, licence, tier, source_url, description, citation=citation)

    def done(self, case):
        return False if self.pool is None else self.pool.case_done(self.dataset, case)

    def full(self):
        lim = 1 if self.args.dry_run else self.args.limit
        return bool(lim) and self.n >= lim

    def put(self, case, path, extra, files=None):
        """path: NIfTI (or other volume) or DICOM dir. Returns once the case is staged/uploaded."""
        self.n += 1
        bad = [k for k, v in (extra.get('orientation_check') or {}).items() if v is False]
        if bad:
            log(f'WARNING {self.dataset}/{case}: orientation check failed: {bad} (check the preview / anatomy)')
        if self.pool is not None:
            log(self.pool.ingest(self.dataset, case, path, extra, files=files), self.dataset, case)
            return
        out = os.path.join(self.args.stage, f'{self.dataset}__{case}.nii.gz')
        work = tempfile.mkdtemp(dir=self.args.stage)
        try:
            shutil.copy(ccta_ingest.to_nifti(path, work), out)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        for name, fp in (files or {}).items():
            shutil.copy(fp, os.path.join(self.args.stage, f'{self.dataset}__{case}__{name}'))
        r = report(out, self.hu, out[:-7] + '.png')
        log(json.dumps({'case': case, 'staged': out, 'extra': extra, 'files': sorted(files or {}), **r}, indent=1))


def tmpdir(args):
    return tempfile.mkdtemp(prefix='ccta-open-', dir=args.work)


def selected(args, case):
    return not args.case or case in args.case


# ====================================================================== 1-2. ImageCHD, ImageALCAPA
def _xlsx_rows(data):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]


def chd_tables(sz):
    """Per case id: spacing (x, y, z mm), sex, age at scan (years), scanner, diagnoses. Dates are read only to
    compute the age and are then dropped."""
    info = {}
    for row in _xlsx_rows(sz.read_small('ImageCHD_dataset/imagechd_dataset_image_info.xlsx')):
        kv, i = {}, 0
        while i < len(row):
            k = row[i].strip() if isinstance(row[i], str) else None
            if k == 'PixelSpacing':
                kv[k] = (float(row[i + 1]), float(row[i + 2])); i += 3
            elif k:
                kv[k] = row[i + 1].strip() if isinstance(row[i + 1], str) else row[i + 1]; i += 2
            else:
                i += 1
        cid = 1000 + int(kv['idx'])
        age = None
        try:
            b, s = (time.strptime(str(int(kv[k])), '%Y%m%d') for k in ('PatientBirthDate', 'AcquisitionDate'))
            age = round((time.mktime(s) - time.mktime(b)) / (365.25 * 86400), 1)
        except (KeyError, ValueError, TypeError):
            pass
        info[cid] = dict(spacing=(kv['PixelSpacing'][1], kv['PixelSpacing'][0], float(kv['calculate_z_thick'])),
                         patient_sex=kv.get('PatientSex'), patient_age_years=age,
                         scanner=kv.get('ManufacturerModelName'))
    rows = _xlsx_rows(sz.read_small('ImageCHD_dataset/imageCHD_dataset_info.xlsx'))
    head = [str(h).strip() for h in rows[0]]
    for r in rows[1:]:
        if r[0] is None:
            continue
        cid = int(r[0])
        if cid in info:
            info[cid]['chd_diagnoses'] = [h for h, v in zip(head[1:], r[1:]) if v not in (None, 0, '')]
    return info


def convert_pair(img, lab, work, spacing, hu_offset, flip_xy, lv, hu=True):
    """Fix one Guangdong image + label pair (see save_fixed) and check the anatomy. If the result looks rotated
    by 180 degrees about the body axis (LV on the patient's right AND spine anterior / heart posterior), the
    other axis convention is applied instead: that is the LPS-vs-RAS mix-up, which flips x and y together,
    whereas dextrocardia moves only the heart. Returns (ct, label, extra fields)."""
    ct, lb = os.path.join(work, 'ct.nii.gz'), os.path.join(work, 'label.nii.gz')
    for attempt, flip in enumerate((flip_xy, not flip_xy)):
        save_fixed(img, ct, spacing, hu_offset, flip)
        save_fixed(lab, lb, spacing, 0, flip)
        chk = anatomy_check(ct, lb, lv, hu)
        rotated = chk.get('lv_on_patient_left') is False and (
            chk.get('spine_posterior') is False if hu else chk.get('lv_anterior') is False)
        if not rotated:
            break
    if rotated:   # neither convention looks normal: keep the documented one and let the warning speak
        save_fixed(img, ct, spacing, hu_offset, flip_xy)
        save_fixed(lab, lb, spacing, 0, flip_xy)
        chk = anatomy_check(ct, lb, lv, hu)
    os.remove(img); os.remove(lab)
    return ct, lb, {'orientation_check': chk, 'array_convention': 'LPS' if flip else 'RAS',
                    'orientation_autocorrected': bool(attempt and not rotated)}


def run_imagechd(args):
    ref = 'xiaoweixumedicalai/imagechd'
    sink = Sink(args, 'ImageCHD', CC_BY_NC, 'T2', f'https://www.kaggle.com/datasets/{ref}',
                'ImageCHD: 110 congenital heart disease cardiac CTA (Siemens SOMATOM Definition Flash, a few '
                'Philips iCT 256), 2017-18, mostly children. ' + GUANGDONG + ' Values converted from HU+1024 to '
                'HU; real voxel spacing taken from the bundled imagechd_dataset_image_info.xlsx (birth and scan '
                'dates in it are not stored). label.nii.gz: 1 LV, 2 RV, 3 LA, 4 RA, 5 myocardium, 6 aorta, '
                '7 pulmonary artery (ignore other values).',
                'Xu X, Wang T, Yuan H, Jia Q, Ceng J, Dong Y, Huang M, Zhuang J, Shi Y. ImageCHD: A 3D Computed '
                'Tomography Image Dataset for Classification of Congenital Heart Disease. MICCAI 2020. '
                'Data: Kaggle xiaoweixumedicalai/imagechd, CC BY-NC 4.0.')
    work = tmpdir(args)
    try:
        sz = SplitZip(ref, work)
        tab = chd_tables(sz)
        ids = sorted(int(m.group(1)) for e in sz.entries if (m := re.search(r'ct_(\d+)_image', e['name'])))
        todo = [c for c in ids if selected(args, str(c)) and not sink.done(str(c))]
        todo = todo[:1] if args.dry_run else todo[:args.limit] if args.limit else todo
        want = {f'ImageCHD_dataset/ct_{c}_{k}.nii.gz' for c in todo for k in ('image', 'label')}
        log(f'ImageCHD: {len(ids)} cases, {len(todo)} to do')
        have = {}
        for e, path in sz.extract(lambda n: n in want, work):
            cid, kind = re.search(r'ct_(\d+)_(image|label)', e['name']).groups()
            have.setdefault(cid, {})[kind] = (path, e['name'])
            if len(have[cid]) < 2:
                continue
            (img, imn), (lab, lbn) = have[cid].pop('image'), have.pop(cid)['label']
            t = tab[int(cid)]
            ct, lb, fix = convert_pair(img, lab, work, t['spacing'], 1024, True, lv=1)
            extra = dict(source_ids={'kaggle': ref, 'archive_member': imn, 'label_member': lbn,
                                     'xlsx_idx': int(cid) - 1000, 'case_id': int(cid)},
                         hu_calibrated=True, hu_conversion='stored value - 1024', spacing_known=True,
                         spacing_source='imagechd_dataset_image_info.xlsx (PixelSpacing, calculate_z_thick)',
                         label_file='label.nii.gz', label_classes='1 LV,2 RV,3 LA,4 RA,5 Myo,6 Ao,7 PA',
                         **fix, **{k: t.get(k) for k in ('patient_sex', 'patient_age_years', 'scanner', 'chd_diagnoses')})
            sink.put(cid, ct, extra, files={'label.nii.gz': lb})
            os.remove(ct); os.remove(lb)
            if sink.full():
                break
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_imagealcapa(args):
    ref = 'xiaoweixumedicalai/imagealcapa'
    sink = Sink(args, 'ImageALCAPA', CC_BY_NC, 'T2', f'https://www.kaggle.com/datasets/{ref}',
                'ImageALCAPA: 30 pre-operative CTA of anomalous left coronary artery from the pulmonary artery '
                '(Siemens SOMATOM Definition Flash, 2016-2021, mostly children). ' + GUANGDONG + ' Values '
                'converted from HU+1024 to HU. VOXEL SPACING IS UNKNOWN: the release carries a 1 mm placeholder '
                'and no spacing table (spacing_known=false); orientation fixed to RAS. label.nii.gz: 1 Myo, 2 LV, '
                '3 RV, 4 PA, 5 Ao, 6 LCA, 7 RCA (the Kaggle order; checked on cases 1 and 30 by size and position).',
                'Zeng et al. (Xu X lab), ImageALCAPA, IEEE BIBM 2022, https://ieeexplore.ieee.org/document/9994951/. '
                'Data: Kaggle xiaoweixumedicalai/imagealcapa, CC BY-NC 4.0.')
    work = tmpdir(args)
    try:
        sz = SplitZip(ref, work)
        ids = sorted(int(m.group(1)) for e in sz.entries
                     if (m := re.fullmatch(r'ImageALCAPA_BIBM_Publish/(\d+)_image\.nii\.gz', e['name'])))
        todo = [c for c in ids if selected(args, str(c)) and not sink.done(str(c))]
        todo = todo[:1] if args.dry_run else todo[:args.limit] if args.limit else todo
        want = {f'ImageALCAPA_BIBM_Publish/{c}_{k}.nii.gz' for c in todo for k in ('image', 'label')}
        log(f'ImageALCAPA: {len(ids)} cases, {len(todo)} to do (members are scattered: an image may wait on '
            f'disk for its label, up to ~1 GB)')
        have = {}
        for e, path in sz.extract(lambda n: n in want, work):
            cid, kind = re.search(r'/(\d+)_(image|label)', e['name']).groups()
            os.rename(path, keep := os.path.join(work, f'raw_{cid}_{kind}.nii.gz'))
            have.setdefault(cid, {})[kind] = (keep, e['name'])
            if len(have[cid]) < 2:
                continue
            (img, imn), (lab, lbn) = have[cid].pop('image'), have.pop(cid)['label']
            ct, lb, fix = convert_pair(img, lab, work, None, 1024, False, lv=2)
            vals, counts = np.unique(np.asanyarray(nib.load(lb).dataobj), return_counts=True)
            extra = dict(source_ids={'kaggle': ref, 'archive_member': imn, 'label_member': lbn, 'case_id': int(cid)},
                         hu_calibrated=True, hu_conversion='stored value - 1024', spacing_known=False,
                         spacing_note='release has a 1 mm placeholder and no spacing table; true spacing unknown',
                         label_file='label.nii.gz', label_classes='1 Myo,2 LV,3 RV,4 PA,5 Ao,6 LCA,7 RCA',
                         label_voxels={str(int(v)): int(n) for v, n in zip(vals, counts) if v}, **fix)
            sink.put(cid, ct, extra, files={'label.nii.gz': lb})
            os.remove(ct); os.remove(lb)
            if sink.full():
                break
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ====================================================================== 3. HOCMvalvesSeg
def run_hocm(args):
    ref = 'xiaoweixumedicalai/hocmvalvesseg'
    sink = Sink(args, 'HOCMvalvesSeg', CC_BY_NC, 'T2', f'https://www.kaggle.com/datasets/{ref}',
                'HOCMvalvesSeg: 27 adult hypertrophic obstructive cardiomyopathy cardiac CT (Siemens SOMATOM '
                'Definition Flash, age 38-76). ' + GUANGDONG + ' STORED AS RELEASED: uint8 windowed intensities '
                '(not HU, lossy; hu_calibrated=false) and a 1 mm placeholder spacing (typical true voxel '
                '0.25 x 0.25 x 0.5 mm per the authors; spacing_known=false); orientation fixed to RAS. '
                'label.nii.gz: 1 AV, 2 MV, 3 AO, 4 LA, 5 LV, 6 myocardium, 7 excised myocardium.',
                'Zheng et al. (Xu X lab), MLR Press v222 (ACML 2023), '
                'https://proceedings.mlr.press/v222/zheng24a/zheng24a.pdf. Data: Kaggle '
                'xiaoweixumedicalai/hocmvalvesseg, CC BY-NC 4.0.', hu=False)
    files = kaggle_files(ref)
    ids = sorted(int(n.split('_')[0]) for n in files if n.endswith('_image.nii'))
    log(f'HOCMvalvesSeg: {len(ids)} cases')
    for cid in ids:
        case = str(cid)
        if not selected(args, case) or sink.done(case):
            continue
        work = tmpdir(args)
        try:
            raw = {k: copy_member(kaggle_member(ref, f'{cid}_{k}.nii'), os.path.join(work, f'raw_{k}.nii'))
                   for k in ('image', 'label')}
            ct, lb, fix = convert_pair(raw['image'], raw['label'], work, None, 0, False, lv=5, hu=False)
            extra = dict(source_ids={'kaggle': ref, 'file': f'{cid}_image.nii', 'label_file': f'{cid}_label.nii',
                                     'case_id': cid},
                         hu_calibrated=False, intensity='uint8 windowed by the authors (window unknown)',
                         spacing_known=False, spacing_note='1 mm placeholder; typical 0.25x0.25x0.5 mm (authors)',
                         label_file='label.nii.gz', label_classes='1 AV,2 MV,3 AO,4 LA,5 LV,6 Myo,7 excised Myo',
                         **fix)
            sink.put(case, ct, extra, files={'label.nii.gz': lb})
        finally:
            shutil.rmtree(work, ignore_errors=True)
        if sink.full():
            break


# ====================================================================== 4. Kaggle younesselbrag (DICOM)
def dicom_extra(dcm_dir):
    """Non-identifying acquisition tags of the first DICOM file (no names, ids, dates or times)."""
    import pydicom
    for f in sorted(os.listdir(dcm_dir)):
        try:
            d = pydicom.dcmread(os.path.join(dcm_dir, f), stop_before_pixels=True)
        except Exception:
            continue
        keys = ('Manufacturer', 'ManufacturerModelName', 'SeriesDescription', 'StudyDescription', 'ProtocolName',
                'SliceThickness', 'KVP', 'ContrastBolusAgent', 'ConvolutionKernel', 'PatientSex', 'PatientAge',
                'CardiacNumberOfImages', 'NominalPercentageOfCardiacPhase')
        return {k: str(getattr(d, k)) for k in keys if getattr(d, k, None) not in (None, '')}
    return {}


def run_cadrs(args):
    ref = 'younesselbrag/cases-coronaries-altries-diseases-cases-ct'
    sink = Sink(args, 'Kaggle-CAD-RandomSamples', 'CC0 1.0 (as stated by the uploader; provenance unverified)', 'T1',
                f'https://www.kaggle.com/datasets/{ref}',
                '"Coronary Artery Diseases Random Samples" (Kaggle, Youness EL BRAG, 2022): ~28 coronary CTA '
                'studies, Philips iCT 256, "Coronary CTA" protocol, 0.9 mm. Institution and consent basis are '
                'NOT documented (provenance_verified=false): check with the project lead before sharing labels.',
                'Youness EL BRAG, "Coronary Artery Diseases Random Samples", Kaggle 2022, '
                'https://www.kaggle.com/datasets/younesselbrag/cases-coronaries-altries-diseases-cases-ct (CC0 as stated).')
    z = kaggle_bundle(ref)
    by_case = {}
    for i in z.infolist():
        m = re.match(r'data3Dicom/(case\d+)/DATA/', i.filename)
        if m and not i.is_dir():
            by_case.setdefault(m.group(1), []).append(i)
    log(f'{len(by_case)} cases in the bundle: ' + ', '.join(f'{k}:{len(v)}' for k, v in sorted(by_case.items())))
    for case, members in sorted(by_case.items()):
        if len(members) < 40:
            log(f'skip {case}: only {len(members)} files (incomplete upload)')
            continue
        if not selected(args, case) or sink.done(case):
            continue
        work = tmpdir(args)
        try:
            dcm = os.path.join(work, 'dcm')
            os.makedirs(dcm)
            for i in members:
                with z.open(i) as src:
                    copy_member(src, os.path.join(dcm, re.sub(r'[^A-Za-z0-9._-]', '_', i.filename.split('/DATA/')[1])))
            extra = dict(source_ids={'kaggle': ref, 'case_dir': f'data3Dicom/{case}',
                                     'series_path': os.path.dirname(members[0].filename)},
                         provenance_verified=False, n_dicom_files=len(members), hu_calibrated=True, **dicom_extra(dcm))
            sink.put(case, dcm, extra)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        if sink.full():
            break


# ====================================================================== 5. Vascular Model Repository
VMR = 'https://www.vascularmodel.com'


def vti_to_nifti(vti, dst):
    """VTK image data -> NIfTI in mm. Spacing/origin are in cm for most VMR cases (detected: voxel < 0.2
    units). The .vti has no direction matrix and the axis convention varies by contributor: most volumes are
    stored in RAS index order, some (e.g. the saphenous vein graft set) in DICOM LPS order. Both are tried and
    the one with the spine posterior wins (checked visually on 0066, 0067, 0069, 0075, 0146)."""
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    r = vtk.vtkXMLImageDataReader()
    r.SetFileName(vti)
    r.Update()
    im = r.GetOutput()
    nx, ny, nz = im.GetDimensions()
    a = vtk_to_numpy(im.GetPointData().GetScalars()).reshape(nz, ny, nx).transpose(2, 1, 0)
    sp, org = np.array(im.GetSpacing(), float), np.array(im.GetOrigin(), float)
    unit = 'cm' if sp.max() < 0.2 else 'mm'
    if unit == 'cm':
        sp, org = sp * 10, org * 10
    if a.dtype.kind == 'f' and np.allclose(a, np.round(a)):
        a = a.astype(np.int16)
    for conv in ('RAS', 'LPS'):
        s = 1.0 if conv == 'RAS' else -1.0
        aff = np.diag([s * sp[0], s * sp[1], sp[2], 1.0])
        aff[:3, 3] = [s * org[0], s * org[1], org[2]]
        out = nib.Nifti1Image(a, aff)
        out.header.set_qform(aff, 1); out.header.set_sform(aff, 1); out.header.set_xyzt_units('mm')
        nib.save(out, dst)
        chk = anatomy_check(dst)
        if chk.get('spine_posterior') is not False:
            break
    if chk.get('spine_posterior') is False:   # neither: keep RAS and flag
        conv = 'RAS'
        aff = np.diag([sp[0], sp[1], sp[2], 1.0]); aff[:3, 3] = org
        out = nib.Nifti1Image(a, aff)
        out.header.set_qform(aff, 1); out.header.set_sform(aff, 1); out.header.set_xyzt_units('mm')
        nib.save(out, dst)
    return dst, dict(vti_spacing_unit=unit, array_convention=conv, orientation_check=chk,
                     orientation_verified='spine_posterior' in chk and chk['spine_posterior'])


def vmr_cases(anatomy=('Coronary',), modality=('CT',)):
    with _open(f'{VMR}/dataset/dataset-svprojects.csv') as r:
        rows = list(csv.DictReader(io.TextIOWrapper(r, encoding='utf-8')))
    return [x for x in rows if x['Anatomy'] in anatomy and x['Image Modality'] in modality and x['Images'] == '1']


def run_vmr(args):
    sink = Sink(args, 'VMR-Coronary', 'VMR terms: free for research and development with acknowledgement '
                '(copyright Stanford/UC/OSMSC; commercial use not granted)', 'T1/T2', f'{VMR}/dataset.html',
                'Vascular Model Repository coronary CT image volumes (Anatomy=Coronary, Modality=CT, Images=1 in '
                'dataset-svprojects.csv): healthy, Kawasaki disease, CAD and saphenous vein graft cases from '
                'several US centres and scanners. Converted from .vti (spacing in cm for most) to NIfTI in mm; the axis '
                'convention differs between contributors and is chosen per case by the spine-posterior check '
                '(orientation_verified=false where the spine is outside the field of view). '
                'Each case also has a permanent Stanford Digital Repository DOI (sdr_doi) and its own citation.',
                'Wilson NM, Ortiz AK, Johnson AB. The Vascular Model Repository: A Public Resource of Medical Imaging '
                'Data and Blood Flow Simulation Results. J Med Device 2013;7(4):040923. https://www.vascularmodel.com '
                '(cite also the per-case paper and SDR DOI in each case\'s metadata).')
    rows = vmr_cases()
    log(f'VMR: {len(rows)} coronary CT cases with images')
    for x in rows:
        case = x['Name']
        if not selected(args, case) or sink.done(case):
            continue
        work = tmpdir(args)
        try:
            z = zipfile.ZipFile(HTTPFile(f'{VMR}/svprojects/{case}.zip'))
            vtis = [i for i in z.infolist() if '/Images/' in i.filename and i.filename.endswith('.vti')]
            if not vtis:
                log(f'{case}: no Images/*.vti in the project zip'); continue
            for k, i in enumerate(vtis):
                with z.open(i) as src:
                    v = copy_member(src, os.path.join(work, 'img.vti'))
                nii, conv = vti_to_nifti(v, os.path.join(work, 'ct.nii.gz'))
                os.remove(v)
                extra = dict(source_ids={'vmr_name': case, 'legacy_name': x['Legacy Name'], 'member': i.filename,
                                         'sdr_doi': x['SDR DOI'], 'paper_doi': x['DOI']},
                             hu_calibrated=True, disease=x['Disease'], patient_sex=x['Sex'],
                             patient_age=x['Age'], scanner=x['Image Manufacturer'], case_citation=x['Citation'].strip(),
                             **conv)
                sink.put(case if len(vtis) == 1 else f'{case}_{k}', nii, extra)
                os.remove(nii)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        if sink.full():
            break


# ====================================================================== 6. figshare 1379059
def run_figshare15(args):
    art = 1379059
    sink = Sink(args, 'Figshare-CardiacCT15', 'CC BY 4.0', 'T2', f'https://doi.org/10.6084/m9.figshare.{art}.v1',
                'figshare "cardiac ct data_15sets" (Xuesong Lu, 2015): 15 dual-source cardiac CT (Siemens Somatom '
                'Definition), one registered phase per patient as released, cropped around the heart. Intensities '
                'are normalised floats, NOT HU (hu_calibrated=false).',
                'Lu, Xuesong (2015). cardiac ct data_15sets. figshare. Dataset. '
                'https://doi.org/10.6084/m9.figshare.1379059.v1 (CC BY 4.0)', hu=False)
    with _open(f'https://api.figshare.com/v2/articles/{art}') as r:
        files = sorted(json.load(r)['files'], key=lambda f: int(re.sub(r'\D', '', f['name']) or 0))
    log(f'figshare: {len(files)} archives')
    for f in files:
        pid = os.path.splitext(f['name'])[0]
        if args.case and not any(c == pid or c.startswith(f'pat{pid}_') for c in args.case):
            continue
        if args.dry_run and not args.case and f is not min(files, key=lambda q: q['size']):
            continue   # dry-run: smallest archive
        work = tmpdir(args)
        try:
            rar = download(f['download_url'], os.path.join(work, f['name']))
            x = os.path.join(work, 'x')
            os.makedirs(x)
            subprocess.run(['bsdtar', '-xf', rar, '-C', x], check=True)
            os.remove(rar)
            for mhd in sorted(glob.glob(os.path.join(x, '**', '*.mhd'), recursive=True)):
                tp = re.search(r'tp(\d+)', os.path.basename(mhd))
                case = f'pat{pid}_tp{tp.group(1) if tp else "x"}'
                if sink.done(case):
                    continue
                extra = dict(source_ids={'figshare_article': art, 'figshare_file_id': f['id'], 'archive': f['name'],
                                         'member': os.path.relpath(mhd, x)},
                             hu_calibrated=False, intensity='normalised float as released (not HU)')
                sink.put(case, mhd, extra)
                if sink.full():
                    return
        finally:
            shutil.rmtree(work, ignore_errors=True)


# ====================================================================== 7. Mendeley 9wv3fkxstx
def is_cardiac_series(meta, shape):
    """The release strips series descriptions, so: a 3D volume of >= 100 slices acquired in GE 'CINE MODE'
    (prospectively gated axial cardiac) or named like a coronary/cardiac series, and not head/neck."""
    desc = ' '.join(str(meta.get(k, '')) for k in ('SeriesDescription', 'ProtocolName', 'BodyPartExamined'))
    named = re.search(r'coronar|cardiac|heart|ccta', desc, re.I)
    head = re.search(r'head|brain|cerebr|willis|neck|carotid', desc, re.I)
    return len(shape) == 3 and shape[2] >= 100 and not head and (named or 'CINE' in str(meta.get('ScanOptions')))


def run_mendeley(args):
    did = '9wv3fkxstx'
    sink = Sink(args, 'Mendeley-9wv3fkxstx', 'CC BY 4.0', 'T1', f'https://data.mendeley.com/datasets/{did}/1',
                'Mendeley Data 9wv3fkxstx v1 (2026): anonymised CT/CTA of one patient supporting a case report; the '
                'gated coronary CTA series (GE Revolution CT, two phases, series 403 and 404) are ingested; head CT and '
                'head/neck CTA are skipped.',
                'WANG, xuming (2026). Anonymized CT and CT Angiography Imaging Dataset Supporting a Case Report. '
                'Mendeley Data, V1. https://doi.org/10.17632/9wv3fkxstx.1 (CC BY 4.0)')
    with _open(f'https://data.mendeley.com/public-api/datasets/{did}/files?folder_id=root&version=1') as r:
        f = json.load(r)[0]
    work = tmpdir(args)
    try:
        z = zipfile.ZipFile(HTTPFile(f['content_details']['download_url']))
        dcm = os.path.join(work, 'dcm')
        os.makedirs(dcm)
        for i in z.infolist():
            if i.filename.lower().endswith('.dcm'):
                with z.open(i) as src:
                    copy_member(src, os.path.join(dcm, i.filename.replace('/', '__')))
        nii = os.path.join(work, 'nii')
        os.makedirs(nii)
        subprocess.run(['dcm2niix', '-z', 'y', '-b', 'y', '-ba', 'y', '-o', nii, '-f', '%s_%d', dcm], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(dcm)
        series, seen = [], set()
        for js in sorted(glob.glob(os.path.join(nii, '*.json'))):   # '403_' sorts before its variant '403_a'
            meta = json.load(open(js))
            vol = js[:-5] + '.nii.gz'
            if not os.path.exists(vol):
                continue
            shp = nib.load(vol).shape
            ok = is_cardiac_series(meta, shp)
            # dcm2niix splits each cardiac series in two near-identical volumes (a re-saved copy with stripped
            # tags, ~4 HU mean difference); keep the first per SeriesNumber
            dup = ok and meta.get('SeriesNumber') in seen
            log(f'  series {os.path.basename(vol)} {shp} {meta.get("ScanOptions")} '
                f'-> {"cardiac" if ok and not dup else "duplicate variant" if dup else "skip"}')
            if ok and not dup:
                seen.add(meta.get('SeriesNumber'))
                series.append((vol, meta))
        for vol, meta in series:
            case = f'P00001_s{meta.get("SeriesNumber")}'
            if not selected(args, case) or sink.done(case):
                continue
            keys = ('Manufacturer', 'ManufacturersModelName', 'ScanOptions', 'ConvolutionKernel', 'ImageType')
            extra = dict(source_ids={'mendeley_dataset': did, 'version': 1, 'file': f['filename'],
                                     'series_number': meta.get('SeriesNumber')},
                         hu_calibrated=True, **{k: str(meta[k]) for k in keys if k in meta})
            sink.put(case, vol, extra)
            if sink.full():
                break
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ====================================================================== 8. HeartSR (Kaggle victorsix)
def run_heartsr(args):
    """HeartSR: 10 Italian 0.6 mm ECG-gated CCTA (Siemens Force, 2025). Only the HR series is ingested; LR is a
    degraded copy of the same scan made for super-resolution research. No licence is stated on the page; the
    project lead approved including it (2026-10-12), flagged licence_stated=false."""
    ref = 'victorsix/cardiac-ct-lr-hr'
    sink = Sink(args, 'Kaggle-HeartSR', 'none stated on the Kaggle page (included with the project lead\'s approval)',
                'T1', f'https://www.kaggle.com/datasets/{ref}',
                'HeartSR (Kaggle victorsix, "cardiac-ct-lr-hr"): 10 patients, ECG-gated 0.6 mm CCTA, Siemens Force, '
                'Italy, 2025. Only the high-resolution (HR) series is stored. No licence stated: do not redistribute '
                'until clarified with the uploader.',
                f'victorsix, "HeartSR: cardiac CT LR-HR", Kaggle, https://www.kaggle.com/datasets/{ref}')
    z = kaggle_bundle(ref)
    by_case = {}
    for i in z.infolist():
        m = re.match(r'HeartSR/(P\d+)/HR/', i.filename)
        if m and not i.is_dir():
            by_case.setdefault(m.group(1), []).append(i)
    log(f'{len(by_case)} HR series: ' + ', '.join(f'{k}:{len(v)}' for k, v in sorted(by_case.items())))
    for case, members in sorted(by_case.items()):
        if not selected(args, case) or sink.done(case):
            continue
        work = tmpdir(args)
        try:
            dcm = os.path.join(work, 'dcm')
            os.makedirs(dcm)
            for i in members:
                with z.open(i) as src:
                    copy_member(src, os.path.join(dcm, re.sub(r'[^A-Za-z0-9._-]', '_', os.path.basename(i.filename))))
            extra = dict(source_ids={'kaggle': ref, 'series_path': f'HeartSR/{case}/HR'}, licence_stated=False,
                         n_dicom_files=len(members), hu_calibrated=True, **dicom_extra(dcm))
            sink.put(case, dcm, extra)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        if sink.full():
            break


# ====================================================================== CLI
RUN = {'imagechd': run_imagechd, 'imagealcapa': run_imagealcapa, 'hocm': run_hocm, 'cadrs': run_cadrs,
       'vmr': run_vmr, 'figshare15': run_figshare15, 'mendeley': run_mendeley, 'heartsr': run_heartsr}

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('source', choices=sorted(RUN))
    ap.add_argument('--dry-run', action='store_true', help='stage one case locally (no Girder) and report it')
    ap.add_argument('--stage', default='ccta-stage', help='dry-run output dir (NIfTI + preview PNG)')
    ap.add_argument('--work', default=None, help='scratch dir for downloads (default: system temp)')
    ap.add_argument('--case', action='append', help='only this case id (repeatable)')
    ap.add_argument('--limit', type=int, default=0, help='upload at most N cases')
    a = ap.parse_args()
    if a.work:
        os.makedirs(a.work, exist_ok=True)
    RUN[a.source](a)
