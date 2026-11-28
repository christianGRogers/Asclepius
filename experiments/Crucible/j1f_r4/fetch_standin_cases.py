"""Janus 1-F round 4 (Crucible): fetch the ImageCAS-X label files of N hash-chosen D45 TRAINING cases only.

The ids come from configs/janus1/split-2026-11.json (train620, checked against F0-r2's pin 1350cb1f...1152). The N with
the smallest sha256('asclepius-j1f-r4-crucible-standins:' + id) are fetched by HTTP range request from the ImageCAS-X
zip (Zenodo 10.5281/zenodo.21887809, CC BY 4.0). No other member of the zip is read: no locked-100, sealed-80 or
quality-0 label, and no CT.
Usage: python3 fetch_standin_cases.py <dest_dir> [N=40]
"""
import hashlib, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SPLIT = os.path.join(ROOT, 'configs', 'janus1', 'split-2026-11.json')
TRAIN620_SHA256 = '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
SALT = 'asclepius-j1f-r4-crucible-standins:'
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'


def chosen(n):
    train = json.load(open(SPLIT))['train620']
    assert hashlib.sha256('\n'.join(sorted(train)).encode()).hexdigest() == TRAIN620_SHA256
    return sorted(train, key=lambda c: hashlib.sha256((SALT + c).encode()).hexdigest())[:n]


if __name__ == '__main__':
    dest = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    os.makedirs(dest, exist_ok=True)
    ids = chosen(n)
    json.dump(ids, open(os.path.join(dest, 'standin_ids.json'), 'w'))
    want = {'%d.coronary.nii.gz' % (int(c[1:]) + 1) for c in ids}
    from remotezip import RemoteZip
    for attempt in range(30):
        try:
            with RemoteZip(URL) as z:
                segs = [m for m in z.namelist() if '/segmentations/' in m and os.path.basename(m) in want]
                assert len(segs) == n, len(segs)
                for m in segs:
                    p = os.path.join(dest, os.path.basename(m))
                    if os.path.exists(p):
                        continue
                    data = z.read(m); open(p + '.part', 'wb').write(data); os.replace(p + '.part', p)
            got = {f for f in os.listdir(dest) if f.endswith('.coronary.nii.gz')}
            assert got == want, (len(got), len(want))
            print(f'done: {n} training cases'); sys.exit(0)
        except Exception as e:
            print('retry:', repr(e)[:200], flush=True); time.sleep(15)
    sys.exit('failed')
