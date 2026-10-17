"""Repos3: list TotalSegmentator v3 zip (Zenodo 22688904) by range reads, extract meta.csv."""
import sys, os, zipfile, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from ingest_open import HTTPFile
URL = 'https://zenodo.org/api/records/22688904/files/Totalsegmentator_dataset_v300.zip/content'
out = sys.argv[1]
hf = HTTPFile(URL, block=4 << 20)
z = zipfile.ZipFile(hf)
names = z.namelist()
json.dump([(i.filename, i.file_size, i.compress_size) for i in z.infolist()], open(os.path.join(out, 'listing.json'), 'w'))
print(len(names), names[:5])
for n in names:
    if n.endswith('.csv') or n.endswith('.md') or n.endswith('.txt'):
        print('meta file', n)
        open(os.path.join(out, os.path.basename(n)), 'wb').write(z.read(n))
