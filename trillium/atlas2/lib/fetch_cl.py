"""Login node only (internet): fetch the ImageCAS-X left/right centreline files (start_points = expert ostia) for
the given cases, by HTTP range reads of the Zenodo zip (record 10.5281/zenodo.21887809, CC BY 4.0). Idempotent.
Used only as a validation column of the A1 ostium (Round 5, A16), never to score.
Usage: fetch_cl.py <dest_dir> <case list file (one cNNNN per line)>"""
import os, sys, time
from remotezip import RemoteZip
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
dest = sys.argv[1]; os.makedirs(dest, exist_ok=True)
ids = {str(int(c.strip()[1:]) + 1) for c in open(sys.argv[2]) if c.strip()}


def wanted(n):
    b = os.path.basename(n)
    return b.endswith('_centerline.vtk') and b.split('.')[0] in ids


for attempt in range(30):
    try:
        with RemoteZip(URL) as z:
            names = [n for n in z.namelist() if wanted(n)]
            todo = [n for n in names if not os.path.exists(os.path.join(dest, os.path.basename(n)))]
            print(f'ImageCAS-X centrelines: {len(names)} files for {len(ids)} cases, {len(todo)} to fetch', flush=True)
            for n in todo:
                p = os.path.join(dest, os.path.basename(n)); data = z.read(n)
                with open(p + '.part', 'wb') as f:
                    f.write(data)
                os.replace(p + '.part', p)
        sys.exit(0)
    except Exception as e:  # connection resets are common on Zenodo range reads
        print('retry after error:', repr(e)[:160], flush=True); time.sleep(15)
print('WARNING: could not fetch the centrelines; the start-point validation column will be empty')
