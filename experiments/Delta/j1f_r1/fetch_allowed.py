"""Janus 1-F round 1 (Delta): fetch ImageCAS-X label files from Zenodo (10.5281/zenodo.21887809) by HTTP range
requests, SKIPPING every sealed case (80 sealed test + 20 sealed quality-0, trillium/icx4/sealed_test.json) before
any byte of it is downloaded. Fetches filelists first, then only the allowed segmentations.
Usage: python fetch_allowed.py <dest_dir>"""
import json, os, re, sys, time
from remotezip import RemoteZip
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
ROOT = os.path.dirname(os.path.abspath(__file__)) + '/../../..'
S = json.load(open(f'{ROOT}/trillium/icx4/sealed_test.json'))
SEALED = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
dest = sys.argv[1]; os.makedirs(dest, exist_ok=True)

def cid(name):
    m = re.match(r'(\d+)\.', os.path.basename(name))
    return 'c%04d' % (int(m.group(1)) - 1) if m else None

for attempt in range(30):
    try:
        with RemoteZip(URL) as z:
            names = z.namelist()
            lists = [n for n in names if '/filelist/' in n and not n.endswith('/')]
            segs = [n for n in names if '/segmentations/' in n and n.endswith('.nii.gz')]
            allowed = [n for n in segs if cid(n) and cid(n) not in SEALED]
            print(f'{len(segs)} segmentations listed, {len(segs) - len(allowed)} sealed skipped', flush=True)
            for n in lists + allowed:
                p = os.path.join(dest, os.path.basename(n))
                if os.path.exists(p):
                    continue
                data = z.read(n)
                with open(p + '.part', 'wb') as f: f.write(data)
                os.replace(p + '.part', p)
        print('done'); break
    except Exception as e:
        print('retry', repr(e)[:200], flush=True); time.sleep(10)
