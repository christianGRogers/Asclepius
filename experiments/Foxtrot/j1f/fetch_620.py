"""Fetch ImageCAS-X label maps for D45's 620 training cases ONLY, by HTTP range requests on the Zenodo zip
(record 10.5281/zenodo.21887809, CC BY 4.0). The file lists are fetched first; the 620 are computed with split620.py;
no sealed, locked-100 or other test segmentation is ever downloaded or opened.
Usage: python3 fetch_620.py <dest_dir> <sealed_test.json>"""
import os, sys, time
from remotezip import RemoteZip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from split620 import split

URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
dest, sealed_json = sys.argv[1], sys.argv[2]
os.makedirs(dest, exist_ok=True)
for attempt in range(20):
    try:
        with RemoteZip(URL) as z:
            names = z.namelist()
            for n in names:
                if '/filelist/' in n and n.endswith('.txt'):
                    p = os.path.join(dest, os.path.basename(n))
                    if not os.path.exists(p):
                        open(p, 'wb').write(z.read(n))
            keep = set(split(dest, sealed_json)['train620'])
            segs = {'c%04d' % (int(os.path.basename(n).split('.')[0]) - 1): n for n in names
                    if '/segmentations/' in n and n.endswith('.coronary.nii.gz')}
            todo = [segs[c] for c in sorted(keep) if not os.path.exists(os.path.join(dest, os.path.basename(segs[c])))]
            print(f'{len(keep)} training cases; {len(todo)} to fetch (attempt {attempt})', flush=True)
            for n in todo:
                p = os.path.join(dest, os.path.basename(n))
                open(p + '.part', 'wb').write(z.read(n)); os.replace(p + '.part', p)
        have = [f for f in os.listdir(dest) if f.endswith('.coronary.nii.gz')]
        assert {'c%04d' % (int(f.split('.')[0]) - 1) for f in have} <= keep, 'a non-training label is on disk'
        print('done:', len(have)); sys.exit(0)
    except AssertionError:
        raise
    except Exception as e:
        print('retry:', repr(e)[:160], flush=True); time.sleep(10)
sys.exit('failed')
