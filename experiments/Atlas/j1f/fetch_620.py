"""Fetch ImageCAS-X segmentations and centrelines (Zenodo 10.5281/zenodo.21887809) for the training cases only
(split.json 'training_620_both'). No locked, sealed or quality-0 case is downloaded.
Usage: python fetch_620.py <split.json> <dest_dir>"""
import os, sys, json, time
from remotezip import RemoteZip
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
split, dest = json.load(open(sys.argv[1])), sys.argv[2]
os.makedirs(dest, exist_ok=True)
nums = {str(int(c[1:]) + 1) for c in split['training_620_both']}
for attempt in range(30):
    try:
        with RemoteZip(URL) as z:
            names = [n for n in z.namelist() if ('/segmentations/' in n or '/centerlines/' in n)
                     and os.path.basename(n).split('.')[0] in nums]
            todo = [n for n in names if not os.path.exists(os.path.join(dest, os.path.basename(n)))]
            print(f'{len(names)} files, {len(todo)} to fetch', flush=True)
            for n in todo:
                p = os.path.join(dest, os.path.basename(n))
                open(p + '.part', 'wb').write(z.read(n)); os.replace(p + '.part', p)
        break
    except Exception as e:
        print('retry', repr(e)[:150], flush=True); time.sleep(10)
