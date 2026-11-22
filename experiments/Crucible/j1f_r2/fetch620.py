"""Fetch only the 620 D45 training label files of ImageCAS-X (Zenodo 10.5281/zenodo.21887809, CC BY 4.0) by HTTP range
requests. Filelists first; the split is then built from ids alone (j1f_r1/split.py), and only train620's segmentation
files are downloaded. No label file of the locked 100, the sealed 80 or the sealed quality-0 20 is ever fetched.
Usage: fetch620.py <dest_dir>"""
import os, sys, time, json
from remotezip import RemoteZip
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'j1f_r1'))
import split  # noqa: E402
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
dest = sys.argv[1]; os.makedirs(dest, exist_ok=True)
for attempt in range(30):
    try:
        with RemoteZip(URL) as z:
            names = z.namelist()
            for n in [n for n in names if '/filelist/' in n and not n.endswith('/')]:
                p = os.path.join(dest, os.path.basename(n))
                if not os.path.exists(p): open(p, 'wb').write(z.read(n))
            S = split.build(dest)
            json.dump(S, open(os.path.join(dest, 'split.json'), 'w'), indent=1)
            want = {'%d.coronary.nii.gz' % (int(c[1:]) + 1) for c in S['train620']}
            segs = [n for n in names if '/segmentations/' in n and os.path.basename(n) in want]
            todo = [n for n in segs if not os.path.exists(os.path.join(dest, os.path.basename(n)))]
            print(f'{len(segs)} train620 segmentations, {len(todo)} to fetch', flush=True)
            for n in todo:
                p = os.path.join(dest, os.path.basename(n)); data = z.read(n)
                open(p + '.part', 'wb').write(data); os.replace(p + '.part', p)
        got = [f for f in os.listdir(dest) if f.endswith('.coronary.nii.gz')]
        assert len(got) == 620 and set(got) == want, len(got)
        print('done: 620'); sys.exit(0)
    except Exception as e:
        print('retry:', repr(e)[:200], flush=True); time.sleep(15)
sys.exit('failed')
