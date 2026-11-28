"""Janus 1-F round 4 (Bridge): fetch the ImageCAS-X segmentations of N hash-chosen cases of the D45 training 620 ONLY.

The 620 is Atlas's `experiments/Atlas/j1l/split_j1l.json` 'train620' (sha256 1350cb1f...1152, = F-A1). Cases are the N
with the smallest sha256('asclepius-j1f-r4-bridge-standins:' + id). Every member name is checked against the chosen
training ids before it is read; no locked-100, sealed-80, quality-0 or D60 label is requested.
Usage: python fetch_subset.py <split_j1l.json> <dest_dir> [N=40]
"""
import hashlib
import json
import os
import sys
import time

from remotezip import RemoteZip

URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
SALT = 'asclepius-j1f-r4-bridge-standins:'


def chosen(split, n):
    train = sorted(split['train620'])
    assert hashlib.sha256('\n'.join(train).encode()).hexdigest() == \
        '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152', 'not the D45 620'
    assert not set(train) & set(split['locked100'])
    return sorted(train, key=lambda c: hashlib.sha256((SALT + c).encode()).hexdigest())[:n]


if __name__ == '__main__':
    split, dest = json.load(open(sys.argv[1])), sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    ids = chosen(split, n)
    nums = {str(int(c[1:]) + 1) for c in ids}             # ImageCAS file number = case index + 1
    os.makedirs(dest, exist_ok=True)
    json.dump(ids, open(os.path.join(dest, 'ids.json'), 'w'))
    for attempt in range(30):
        try:
            with RemoteZip(URL) as z:
                names = [m for m in z.namelist() if '/segmentations/' in m
                         and os.path.basename(m).endswith('.coronary.nii.gz')
                         and os.path.basename(m).split('.')[0] in nums]
                assert len(names) <= n
                todo = [m for m in names if not os.path.exists(os.path.join(dest, os.path.basename(m)))]
                print(f'{len(names)} files, {len(todo)} to fetch', flush=True)
                for m in todo:
                    p = os.path.join(dest, os.path.basename(m))
                    open(p + '.part', 'wb').write(z.read(m))
                    os.replace(p + '.part', p)
            break
        except Exception as e:  # noqa: BLE001 - Zenodo rate limits; retry
            print('retry', repr(e)[:150], flush=True)
            time.sleep(15)
    print('done', len([f for f in os.listdir(dest) if f.endswith('.nii.gz')]))
