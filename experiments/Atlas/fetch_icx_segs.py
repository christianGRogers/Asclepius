"""Fetch only the ImageCAS-X segmentation files + filelists + descriptors (~14 MB) from the
Zenodo zip via HTTP range requests (remotezip). Output: $SCR/work/Atlas/icx/"""
import os, sys
from remotezip import RemoteZip
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
OUT = sys.argv[1]
with RemoteZip(URL) as z:
    names = [n for n in z.namelist() if ('/segmentations/' in n and n.endswith('.nii.gz'))
             or '/filelist/' in n or n.endswith('.xlsx')]
    for i, n in enumerate(names):
        dest = os.path.join(OUT, os.path.basename(n))
        if os.path.exists(dest): continue
        with open(dest, 'wb') as f: f.write(z.read(n))
        if i % 100 == 0: print(i, n, flush=True)
print('done', len(names))
