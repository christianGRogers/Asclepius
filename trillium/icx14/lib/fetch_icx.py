"""Login node only (needs internet): fetch the ImageCAS-X label files (~14 MB of the 1.44 GB Zenodo zip) by HTTP
range requests. Zenodo record 10.5281/zenodo.21887809, CC BY 4.0 (Bransby et al., arXiv:2608.30404).
Idempotent: skips files already present; retries on connection resets. Usage: fetch_icx.py <dest_dir>"""
import os, sys, time
from remotezip import RemoteZip
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
dest = sys.argv[1]; os.makedirs(dest, exist_ok=True)
for attempt in range(30):
    try:
        with RemoteZip(URL) as z:
            names = [n for n in z.namelist() if ('/segmentations/' in n and n.endswith('.nii.gz')) or '/filelist/' in n]
            todo = [n for n in names if not os.path.exists(os.path.join(dest, os.path.basename(n)))]
            print(f'ImageCAS-X: {len(names)} files, {len(todo)} to fetch (attempt {attempt})', flush=True)
            for n in todo:
                p = os.path.join(dest, os.path.basename(n)); data = z.read(n)
                with open(p + '.part', 'wb') as f: f.write(data)
                os.replace(p + '.part', p)
        segs = [f for f in os.listdir(dest) if f.endswith('.coronary.nii.gz')]
        if len(segs) < 800:
            raise RuntimeError(f'only {len(segs)} segmentations present')
        print(f'ImageCAS-X labels complete: {len(segs)} segmentations in {dest}'); sys.exit(0)
    except Exception as e:
        print('retry after error:', repr(e)[:160], flush=True); time.sleep(15)
sys.exit('could not fetch ImageCAS-X labels from Zenodo after 30 attempts')
