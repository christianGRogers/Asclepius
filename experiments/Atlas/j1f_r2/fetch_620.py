"""Janus 1-F round 2 (Atlas): fetch ImageCAS-X segmentations (Zenodo 10.5281/zenodo.21887809) and Descriptors.xlsx
for the D45 training 620 ONLY (experiments/Atlas/j1l/split_j1l.json 'train620', sha256 1350cb1f...1152, = L-A1/F-A1).
Every member name is checked against the 620 before it is read; no locked-100, sealed or quality-0 label is fetched.
Usage: python fetch_620.py <split_j1l.json> <dest_dir>"""
import os, sys, json, time, hashlib
from remotezip import RemoteZip
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
split, dest = json.load(open(sys.argv[1])), sys.argv[2]
train = sorted(split['train620'])
assert hashlib.sha256('\n'.join(train).encode()).hexdigest() == \
    '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
locked = set(split['locked100'])
nums = {str(int(c[1:]) + 1) for c in train}          # ImageCAS file number = case index + 1
assert not nums & {str(int(c[1:]) + 1) for c in locked}
os.makedirs(dest, exist_ok=True)
for attempt in range(30):
    try:
        with RemoteZip(URL) as z:
            allnames = z.namelist()
            names = [n for n in allnames if '/segmentations/' in n and os.path.basename(n).split('.')[0] in nums]
            names += [n for n in allnames if os.path.basename(n) == 'Descriptors.xlsx']
            todo = [n for n in names if not os.path.exists(os.path.join(dest, os.path.basename(n)))]
            print(f'{len(names)} files, {len(todo)} to fetch', flush=True)
            for n in todo:
                p = os.path.join(dest, os.path.basename(n))
                open(p + '.part', 'wb').write(z.read(n)); os.replace(p + '.part', p)
        break
    except Exception as e:
        print('retry', repr(e)[:150], flush=True); time.sleep(10)
