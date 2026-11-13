"""Fetch ImageCAS-X segmentations and centerlines for the 620 Janus 1 training cases ONLY (CC BY 4.0,
Zenodo 10.5281/zenodo.21887809), by HTTP range requests. Never requests a sealed or a locked-100 case.
Usage: fetch620.py <out_dir> <sealed_test.json>   (writes <out_dir>/filelist, segmentations, centerlines, split.json)"""
import json, os, sys, remotezip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import split620

OUT, SEALED = sys.argv[1], sys.argv[2]
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'


def get(z, n):
    dest = os.path.join(OUT, n.split('ImageCAS-X_dataset/')[1])
    if os.path.exists(dest):
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest + '.part', 'wb') as f:
        f.write(z.read(n))
    os.replace(dest + '.part', dest)


with remotezip.RemoteZip(URL) as z:
    names = z.namelist()
    for n in names:
        if '/filelist/' in n and n.endswith('.txt'):
            get(z, n)
    sp = split620.build(os.path.join(OUT, 'filelist'), SEALED)
    json.dump(sp, open(os.path.join(OUT, 'split.json'), 'w'), indent=1)
    allowed = {str(int(c[1:]) + 1) for c in sp['train620']}
    k = 0
    for n in names:
        b = os.path.basename(n)
        if ('/segmentations/' in n or '/centerlines/' in n) and b.split('.')[0] in allowed:
            get(z, n); k += 1
print('fetched', k, 'files for', len(allowed), 'training cases')
