"""Stream CT scans from any source into the Girder collection ``CCTA-Pool`` (parallel to SegQueue; touches
nothing else). One scan at a time: convert to NIfTI, take a few light quality notes (never rejects), upload,
delete the local copy. Idempotent: a scan whose sha256 is already in the pool is skipped.

Layout in Girder:  CCTA-Pool/<dataset>/<case>/ct.nii.gz   (folder + item metadata: dataset, source_case,
licence, tier, source_url, shape, spacing_mm, hu_p99, contrast_likely, sha256, ingested)

As a library (adapters call this per scan):
    from ccta_ingest import Pool
    pool = Pool()                       # token from $GIRDER_TOKEN_FILE (never committed)
    pool.dataset('ASOCA', licence='CC BY 4.0', tier='T1', source_url='...', description='...')
    pool.ingest('ASOCA', 'Normal_1', '/tmp/x/Normal_1.nrrd')   # file (nii/nrrd/mha/...) or a DICOM directory
CLI:
    ccta_ingest.py <dataset> <case> <path> --licence L --tier T1 --source-url U
"""
import argparse, datetime, glob, hashlib, json, os, shutil, subprocess, sys, tempfile, urllib.parse, urllib.request

API = os.environ.get('GIRDER_API', 'https://janus.bradensbay.com/api/v1')
COLLECTION = 'CCTA-Pool'
CHUNK = 1 << 20   # janus's nginx rejects request bodies above a few MB (5 MB fails, 1 MB works)


def _token():
    path = os.environ.get('GIRDER_TOKEN_FILE')
    if not path:
        sys.exit('set GIRDER_TOKEN_FILE to a file holding a Girder token')
    return open(path).read().strip()


class Pool:
    def __init__(self):
        self.tok = _token()
        self._folders = {}
        self._hashes = None
        self.coll = self._collection()

    # ------------------------------------------------------------------ REST
    def req(self, method, path, params=None, body=None, ctype=None, raw=False):
        url = f'{API}/{path}' + ('?' + urllib.parse.urlencode(params) if params else '')
        h = {'Girder-Token': self.tok}
        if ctype:
            h['Content-Type'] = ctype
        for attempt in range(5):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h, method=method),
                                            timeout=600) as r:
                    d = r.read()
                return d if raw else json.loads(d or b'null')
            except urllib.error.HTTPError as e:
                if e.code < 500 or attempt == 4:
                    raise RuntimeError(f'{method} {path}: HTTP {e.code} {e.read()[:300]!r}')
            except OSError:
                if attempt == 4:
                    raise

    def _collection(self):
        for c in self.req('GET', 'collection', {'text': COLLECTION, 'limit': 50}):
            if c['name'] == COLLECTION:
                return c
        return self.req('POST', 'collection', {
            'name': COLLECTION, 'public': 'false',
            'description': 'Unlabelled and labelled CT scans of the coronary arteries gathered for annotation, '
                           'parallel to SegQueue (nothing here is served to annotators until validated). '
                           'One folder per source dataset; see each folder description for licence and origin.'})

    def _folder(self, parent, ptype, name, desc=''):
        key = (parent, name)
        if key not in self._folders:
            self._folders[key] = self.req('POST', 'folder', {'parentType': ptype, 'parentId': parent, 'name': name,
                                                             'reuseExisting': 'true', 'description': desc})
        return self._folders[key]

    def dataset(self, name, licence, tier, source_url, description=''):
        f = self._folder(self.coll['_id'], 'collection', name, description or f'{name}: {source_url}')
        self.req('PUT', f'folder/{f["_id"]}/metadata', body=json.dumps(
            {'dataset': name, 'licence': licence, 'tier': tier, 'source_url': source_url}).encode(),
            ctype='application/json')
        return f

    def known_hashes(self):
        if self._hashes is None:
            self._hashes = set()
            for it in self._all_items():
                h = (it.get('meta') or {}).get('sha256')
                if h:
                    self._hashes.add(h)
        return self._hashes

    def _all_items(self):
        # every item under the pool (folders are shallow: dataset/case/item)
        for ds in self.req('GET', 'folder', {'parentType': 'collection', 'parentId': self.coll['_id'], 'limit': 0}):
            for case in self.req('GET', 'folder', {'parentType': 'folder', 'parentId': ds['_id'], 'limit': 0}):
                for it in self.req('GET', 'item', {'folderId': case['_id'], 'limit': 0}):
                    yield it

    def case_done(self, dataset, case):
        ds = self._folder(self.coll['_id'], 'collection', dataset)
        for f in self.req('GET', 'folder', {'parentType': 'folder', 'parentId': ds['_id'], 'name': case}):
            if any(i['name'] == 'ct.nii.gz' for i in self.req('GET', 'item', {'folderId': f['_id']})):
                return True
        return False

    def upload(self, folder_id, path, name, meta):
        size = os.path.getsize(path)
        with open(path, 'rb') as fh:
            doc = self.req('POST', 'file', {'parentType': 'folder', 'parentId': folder_id, 'name': name, 'size': size})
            off = 0
            while off < size:
                data = fh.read(CHUNK)
                doc = self.req('POST', 'file/chunk', {'uploadId': doc['_id'], 'offset': off}, body=data,
                               ctype='application/octet-stream')
                off += len(data)
        self.req('PUT', f'item/{doc["itemId"]}/metadata', body=json.dumps(meta).encode(), ctype='application/json')
        return doc

    # ------------------------------------------------------------------ ingest
    def ingest(self, dataset, case, path, extra=None):
        """Convert ``path`` (a volume file or a DICOM directory) and upload it as <dataset>/<case>/ct.nii.gz.
        Returns 'uploaded', 'exists' or 'duplicate'."""
        if self.case_done(dataset, case):
            return 'exists'
        work = tempfile.mkdtemp(prefix='ccta-')
        try:
            nii = to_nifti(path, work)
            sha = sha256(nii)
            if sha in self.known_hashes():
                return 'duplicate'
            meta = dict(qc(nii), dataset=dataset, source_case=case, sha256=sha,
                        ingested=datetime.date.today().isoformat(), **(extra or {}))
            ds = self._folder(self.coll['_id'], 'collection', dataset)
            ds_meta = ds.get('meta') or self.req('GET', f'folder/{ds["_id"]}').get('meta') or {}
            for k in ('licence', 'tier', 'source_url'):
                meta.setdefault(k, ds_meta.get(k))
            cf = self._folder(ds['_id'], 'folder', case)
            self.upload(cf['_id'], nii, 'ct.nii.gz', meta)
            self.known_hashes().add(sha)
            return 'uploaded'
        finally:
            shutil.rmtree(work, ignore_errors=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def to_nifti(path, work):
    """Any CT input -> one .nii.gz in ``work``. DICOM dirs go through dcm2niix (largest output kept)."""
    if os.path.isdir(path):
        subprocess.run(['dcm2niix', '-z', 'y', '-b', 'n', '-o', work, '-f', 'ct_%s', path], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        outs = sorted(glob.glob(os.path.join(work, '*.nii.gz')), key=os.path.getsize)
        if not outs:
            raise RuntimeError(f'dcm2niix produced nothing for {path}')
        return outs[-1]
    low = path.lower()
    if low.endswith('.nii.gz'):
        return path
    import SimpleITK as sitk
    out = os.path.join(work, 'ct.nii.gz')
    sitk.WriteImage(sitk.ReadImage(path), out, useCompression=True)
    return out


def qc(nii):
    """Light notes only; nothing is rejected (project lead: don't be too strict on quality)."""
    import nibabel as nib, numpy as np
    im = nib.load(nii)
    a = np.asarray(im.dataobj, dtype=np.float32)
    sub = a[::4, ::4, ::4]
    p99 = float(np.percentile(sub, 99))
    return {'shape': list(map(int, im.shape[:3])), 'spacing_mm': [round(float(z), 4) for z in im.header.get_zooms()[:3]],
            'hu_p99': round(p99, 1), 'hu_min': round(float(sub.min()), 1),
            'contrast_likely': bool(p99 > 250)}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('dataset'); ap.add_argument('case'); ap.add_argument('path')
    ap.add_argument('--licence', required=True); ap.add_argument('--tier', required=True)
    ap.add_argument('--source-url', required=True); ap.add_argument('--description', default='')
    a = ap.parse_args()
    p = Pool(); p.dataset(a.dataset, a.licence, a.tier, a.source_url, a.description)
    print(p.ingest(a.dataset, a.case, a.path))
