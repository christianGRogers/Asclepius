"""Pull ImageCAS-X segmentations, centerlines and file lists (CC BY 4.0, Zenodo 10.5281/zenodo.21887809)
by HTTP range requests (remotezip) -- ~40 MB instead of the 1.4 GB zip."""
import os, sys, remotezip
OUT = sys.argv[1]
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
with remotezip.RemoteZip(URL) as z:
    for n in z.namelist():
        if n.endswith('/') or '/surfaces/' in n:
            continue
        dest = os.path.join(OUT, n.split('ImageCAS-X_dataset/')[1])
        if os.path.exists(dest):
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest + '.part', 'wb') as f:
            f.write(z.read(n))
        os.replace(dest + '.part', dest)
print('done')
