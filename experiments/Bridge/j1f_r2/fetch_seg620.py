"""Fetch ImageCAS-X segmentations (CC BY 4.0, Zenodo 10.5281/zenodo.21887809) for the 620 Janus 1 training cases
ONLY, in parallel, plus Descriptors.xlsx (read later for the 620 rows only). Never requests a sealed or locked case.
Usage: fetch_seg620.py <out_dir> <sealed_test.json> [threads]"""
import json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
import remotezip
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'j1f_r1'))
import split620

OUT, SEALED = sys.argv[1], sys.argv[2]
TH = int(sys.argv[3]) if len(sys.argv) > 3 else 3
LOCAL = threading.local()   # one open archive per thread: re-opening re-reads the central directory
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'


def get(n):
    dest = os.path.join(OUT, n.split('ImageCAS-X_dataset/')[1])
    if os.path.exists(dest):
        return 0
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    for attempt in range(8):
        try:
            if not hasattr(LOCAL, 'z'):
                LOCAL.z = remotezip.RemoteZip(URL)
            data = LOCAL.z.read(n)
            break
        except remotezip.RemoteIOError:          # Zenodo answers 429 when pressed; back off
            time.sleep(15 * (attempt + 1))
            if hasattr(LOCAL, 'z'):
                del LOCAL.z
    else:
        raise RuntimeError('could not fetch ' + n)
    with open(dest + '.part', 'wb') as f:
        f.write(data)
    os.replace(dest + '.part', dest)
    return 1


with remotezip.RemoteZip(URL) as z:
    names = z.namelist()
for n in names:
    if '/filelist/' in n and n.endswith('.txt'):
        get(n)
sp = split620.build(os.path.join(OUT, 'filelist'), SEALED)
json.dump(sp, open(os.path.join(OUT, 'split.json'), 'w'), indent=1)
allowed = {str(int(c[1:]) + 1) for c in sp['train620']}
todo = [n for n in names if '/segmentations/' in n and os.path.basename(n).split('.')[0] in allowed]
todo.append([n for n in names if n.endswith('Descriptors.xlsx')][0])
with ThreadPoolExecutor(TH) as ex:
    k = sum(ex.map(get, todo))
print('fetched', k, 'of', len(todo), 'files for', len(allowed), 'training cases')
