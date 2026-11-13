"""Janus 1-F round 1 (Delta): write D45's ImageCAS-X split as a pinned JSON (no label or CT is read).
Locked 100 = val 80 + the 20 open-36 cases with the smallest sha256('asclepius-janus1-locked100:' + id); train 620 =
train 560 + dev 44 + the other 16 of open-36. The id is the project's ImageCAS-X id ('c0000' style, as in
sealed_test.json and D43). The ImageCAS-number reading ('1'-style) is computed too and its overlap printed, so the
judge can see whether the choice matters. Usage: python split_d45.py <icx filelist dir> <out.json>"""
import hashlib, json, os, sys
from census import S, SEALED, split

icx, out = sys.argv[1], sys.argv[2]
sp = split(icx)
key = lambda s: hashlib.sha256(('asclepius-janus1-locked100:' + s).encode()).hexdigest()
alt = sorted(S['open_icx_test'], key=lambda c: key(str(int(c[1:]) + 1)))[:20]
locked = sorted(sp['val80'] + sp['locked_open20'])
train = sorted(sp['train560'] + sp['dev44'] + sp['train_open16'])
assert len(locked) == 100 and len(train) == 620 and not set(locked) & set(train)
assert not (set(locked) | set(train)) & SEALED
doc = {'rule': "D45: locked 100 = ImageCAS-X val 80 + the 20 open-36 cases with the smallest "
               "sha256('asclepius-janus1-locked100:' + id), id = cNNNN; train 620 = train 560 + dev 44 + the other 16",
       'locked100': locked, 'locked_open20': sp['locked_open20'], 'train620': train,
       'train_open16': sp['train_open16'],
       'alt_reading_imagecas_number_locked_open20': sorted(alt),
       'alt_reading_overlap_with_locked_open20': len(set(alt) & set(sp['locked_open20']))}
blob = json.dumps(doc, indent=1, sort_keys=True)
open(out, 'w').write(blob)
print('locked open-20:', sp['locked_open20'])
print('overlap with the ImageCAS-number reading:', doc['alt_reading_overlap_with_locked_open20'], 'of 20')
print('sha256 of', out, hashlib.sha256(blob.encode()).hexdigest())
