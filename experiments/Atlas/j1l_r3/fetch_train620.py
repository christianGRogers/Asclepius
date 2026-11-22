"""Atlas, Janus 1-L round 3: fetch the ImageCAS-X segmentations of the 620 D45 training cases, and nothing else.

ImageCAS-X's labels are public (Zenodo record 21887809, the same zip `experiments/Atlas/fetch_icx_segs.py` reads).
This reads only the 620 files named by `experiments/Crucible/j1l_r1/lists.json` `train620`, by HTTP range request.

Guards, before any byte is fetched:
  * the 620 ids hash to the pin of record (L-A1): sha256 of the sorted ids joined by '\\n' = 1350cb1f...1152;
  * none is in `trillium/sealed_test.json` (sealed ImageCAS-X 80, quality-0 20), and none is in the locked 100;
  * the file name is ImageCAS id = case number + 1 (`<id>.coronary.nii.gz`, as icx4's scorer reads it).
Output: <out>/<id>.coronary.nii.gz. Keep <out> in a scratch directory: labels are never committed.

Usage: python fetch_train620.py <out_dir>
"""
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
PIN_620 = '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'


def train620():
    L = json.load(open(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    ids = sorted(L['train620'])
    h = hashlib.sha256('\n'.join(ids).encode()).hexdigest()
    bad = set(ids) & (set(S['sealed_icx_test']) | set(S['sealed_quality0']) | set(L['locked100']))
    if h != PIN_620 or len(ids) != 620 or bad:
        sys.exit(f'[fetch620] REFUSING: pin {h}, n {len(ids)}, sealed/locked {sorted(bad)[:5]}')
    return ids


def main(out):
    from remotezip import RemoteZip
    ids = train620()
    os.makedirs(out, exist_ok=True)
    want = {f'{int(c[1:]) + 1}.coronary.nii.gz' for c in ids}
    for attempt in range(30):
        try:
            with RemoteZip(URL) as z:
                names = {os.path.basename(n): n for n in z.namelist() if '/segmentations/' in n}
                todo = sorted(w for w in want if not os.path.exists(os.path.join(out, w)))
                missing = sorted(w for w in todo if w not in names)
                if missing:
                    sys.exit(f'[fetch620] not in the zip: {missing[:5]}')
                for w in todo:
                    data = z.read(names[w])
                    open(os.path.join(out, w + '.part'), 'wb').write(data)
                    os.replace(os.path.join(out, w + '.part'), os.path.join(out, w))
            break
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001 - network retries
            print('[fetch620] retry', attempt, repr(e)[:200], flush=True)
            time.sleep(10)
    have = sorted(f for f in os.listdir(out) if f.endswith('.coronary.nii.gz'))
    extra = set(have) - want
    if extra:
        sys.exit(f'[fetch620] REFUSING: files outside the 620 in {out}: {sorted(extra)[:5]}')
    print(f'[fetch620] {len(have)} of 620 in {out}')


if __name__ == '__main__':
    main(sys.argv[1])
