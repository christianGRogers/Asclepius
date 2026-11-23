"""Janus 1-F round 3 (Foxtrot): fetch the ImageCAS-X segmentations of D45's 620 TRAINING cases only, sharded.
Same refusal logic as experiments/Atlas/j1f_r2/fetch_620.py (pin of the 620, no locked-100 / sealed / quality-0 member
is ever requested), plus `--shard k/n` so several processes can fetch disjoint subsets.
Usage: python fetch_620.py <split_j1l.json> <dest_dir> [k/n]"""
import hashlib, json, os, sys, time
from remotezip import RemoteZip
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
split, dest = json.load(open(sys.argv[1])), sys.argv[2]
k, n = map(int, (sys.argv[3] if len(sys.argv) > 3 else '0/1').split('/'))
train = sorted(split['train620'])
assert hashlib.sha256('\n'.join(train).encode()).hexdigest() == \
    '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
nums = {str(int(c[1:]) + 1) for c in train}
assert not nums & {str(int(c[1:]) + 1) for c in split['locked100']}
os.makedirs(dest, exist_ok=True)
for attempt in range(30):
    try:
        with RemoteZip(URL) as z:
            names = sorted(m for m in z.namelist() if '/segmentations/' in m and os.path.basename(m).split('.')[0] in nums)
            assert len(names) == 620, len(names)
            todo = [m for i, m in enumerate(names) if i % n == k and not os.path.exists(os.path.join(dest, os.path.basename(m)))]
            print(f'shard {k}/{n}: {len(todo)} to fetch', flush=True)
            for m in todo:
                assert os.path.basename(m).split('.')[0] in nums
                p = os.path.join(dest, os.path.basename(m))
                open(p + '.part', 'wb').write(z.read(m)); os.replace(p + '.part', p)
        break
    except Exception as e:
        print('retry', repr(e)[:150], flush=True); time.sleep(10)
