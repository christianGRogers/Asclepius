"""Janus 1-F round 4 (Atlas): fetch ImageCAS-X segmentations for a hash-chosen SUBSET of the D45 training 620 only.

Same guard as j1f_r3/fetch_620.py (the 620's pin 1350cb1f...1152; no locked-100 member), then the N training cases with
the smallest sha256('asclepius-j1f-r4-atlas-standin:' + id). No locked-100, sealed, quality-0 or D60 label is fetched;
Descriptors.xlsx is not fetched.
Usage: python fetch_subset.py <split_j1l.json> <dest_dir> <N>"""
import hashlib, json, os, sys, time
from remotezip import RemoteZip
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
SALT = 'asclepius-j1f-r4-atlas-standin:'
split, dest, n = json.load(open(sys.argv[1])), sys.argv[2], int(sys.argv[3])
train = sorted(split['train620'])
assert hashlib.sha256('\n'.join(train).encode()).hexdigest() == \
    '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
locked = set(split['locked100'])
assert not set(train) & locked
chosen = sorted(train, key=lambda c: hashlib.sha256((SALT + c).encode()).hexdigest())[:n]
nums = {str(int(c[1:]) + 1) for c in chosen}
assert not nums & {str(int(c[1:]) + 1) for c in locked}
os.makedirs(dest, exist_ok=True)
json.dump(sorted(chosen), open(os.path.join(dest, 'chosen.json'), 'w'))
for attempt in range(30):
    try:
        with RemoteZip(URL) as z:
            names = [m for m in z.namelist() if '/segmentations/' in m and os.path.basename(m).split('.')[0] in nums]
            assert len(names) <= n, names
            todo = [m for m in names if not os.path.exists(os.path.join(dest, os.path.basename(m)))]
            print(f'{len(names)} files, {len(todo)} to fetch', flush=True)
            for m in todo:
                p = os.path.join(dest, os.path.basename(m))
                open(p + '.part', 'wb').write(z.read(m)); os.replace(p + '.part', p)
        break
    except Exception as e:  # noqa: BLE001
        print('retry', repr(e)[:150], flush=True); time.sleep(10)
